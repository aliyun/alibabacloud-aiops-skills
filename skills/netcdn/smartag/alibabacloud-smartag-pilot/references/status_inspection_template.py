#!/usr/bin/env python3
"""
SAG 全量状态巡检模板 v4.2

使用方式:
    Agent 读取本模板后，根据用户需求修改 [CUSTOMIZE] 标记的区域，
    将修改后的脚本写入 workspace 并执行。

可定制区域:
    - REPORT_OUTPUT_DIR: 报告输出目录
    - REGION_FILTER: 指定区域或 "all"
    - INSPECTION_ITEMS: 要执行的巡检项子集 (共 10 项: 1~9 为常规巡检，#10 为丢包率 DropTopN)
    - THRESHOLDS: 各巡检项阈值

依赖:
    - Python 3.6+
    - aliyun CLI >= 3.3.3 (已安装 smartag 插件, 已配置凭据)

变更记录:
    v4.2 - 重新加回丢包率巡检 (#10 DropTopN)，巡检项从 9 升为 10
         - 在主流区域（cn-shanghai/cn-hangzhou 等）正常返回数据
         - 边缘区域返回 SAG_QUERY_TOPN_ERROR 时优雅 skip，不中断全局巡检
         - 编号兼容 v4.1: 现有 1~9 编号保持不变，丢包率作为第 10 项追加
    v4.1 - 重命名为状态巡检, 移除丢包率巡检项(DropTopN), 巡检项从10减为9
         - 原 #6~#10 重编号为 #5~#9
    v4.0 - 迁移到 CLI 插件模式 (plugin mode)
         - 移除 --force / --version, 保留 --endpoint 用于精确区域路由
         - API 名称使用 kebab-case
         - 参数名使用 kebab-case (--biz-region-id, --smart-ag-id 等)
         - 移除所有函数中的 endpoint 函数参数 (改为 run_cli 内部自动构建)
         - 使用 --endpoint 而非 --region 做端点路由, 因为插件的 --region
           映射表不完整 (eu-west-1, us-east-1, cn-zhangjiakou-spe 无法识别)
    v3.0 - 增加重试机制, connect-timeout 提升到 15
    v2.0 - 移除 3 项巡检, 精简到 10 项
"""

import json
import subprocess
import re
import time
import os
import sys
from datetime import datetime, timezone, timedelta

# ============================================================
# [CUSTOMIZE] 可定制配置区 — Agent 根据用户需求修改以下变量
# ============================================================

# 报告输出目录 (Agent 应替换为用户的 workspace 路径)
REPORT_OUTPUT_DIR = "/path/to/workspace"

# 区域过滤: "all" 表示全部区域, 或指定列表如 ["cn-shanghai", "cn-hongkong"]
REGION_FILTER = "all"

# 巡检项过滤: "all" 或指定编号列表如 [1, 2, 4, 7, 10]
INSPECTION_ITEMS = "all"

# 巡检阈值 (可按需调整)
THRESHOLDS = {
    "expiry_red_days": 7,        # 到期 < 7 天 = red
    "expiry_yellow_days": 30,    # 到期 7-30 天 = yellow
}

# ============================================================
# 以下为核心逻辑，通常无需修改
# ============================================================

VERSION = "4.2"
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

api_call_count = 0
errors_log = []

# ============================================================
# CLI 插件模式 — API / 参数名称映射
# ============================================================

# API 名称映射 (PascalCase → plugin kebab-case)
API_NAME_MAP = {
    "DescribeRegions": "describe-regions",
    "DescribeSmartAccessGateways": "describe-smart-access-gateways",
    "DescribeSmartAccessGatewayAttribute": "describe-smart-access-gateway-attribute",
    "DescribeSmartAccessGatewayHa": "describe-smart-access-gateway-ha",
    "DescribeSagWan4G": "describe-sag-wan-4g",
    "DescribeGrantSagRules": "describe-grant-sag-rules",
    "DescribeSagRouteList": "describe-sag-route-list",
    "DescribeFlowLogs": "describe-flow-logs",
    "DescribeSagDropTopN": "describe-sag-drop-topn",
}

# 参数名称映射 (PascalCase → plugin kebab-case)
PARAM_NAME_MAP = {
    "SmartAGId": "smart-ag-id",
    "SmartAGSn": "smart-ag-sn",
    "PageSize": "page-size",
    "PageNumber": "page-number",
    "Size": "size",
    "SagId": "sag-id",
    "FlowLogId": "flow-log-id",
}


def strip_ansi(text):
    """清除 ANSI 颜色转义序列"""
    return ANSI_ESCAPE.sub('', text)


def run_cli(action, region_id, extra_params=None):
    """
    执行 aliyun CLI 插件模式调用并返回 JSON (网络失败自动重试一次)

    参数:
        action: PascalCase API 名称 (如 "DescribeSmartAccessGateways")
        region_id: 区域 ID (如 "cn-shanghai")
        extra_params: 额外参数 dict, key 为 PascalCase (如 {"SmartAGId": "sag-xxx"})
    """
    global api_call_count

    # 转换 API 名称为 kebab-case
    api_name = API_NAME_MAP.get(action, action)

    for attempt in range(2):  # 最多尝试2次 (首次 + 1次重试)
        api_call_count += 1

        cmd = [
            "aliyun", "smartag", api_name,
            "--endpoint", f"smartag.{region_id}.aliyuncs.com",
            "--read-timeout", "30",
            "--connect-timeout", "15",
        ]

        # 业务区域参数: DescribeRegions 不需要, 其余 API 用 --biz-region-id
        if action != "DescribeRegions":
            cmd.extend(["--biz-region-id", region_id])

        # 转换并添加额外参数
        if extra_params:
            for k, v in extra_params.items():
                param_name = PARAM_NAME_MAP.get(k, k.lower())
                cmd.extend([f"--{param_name}", str(v)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                error_msg = strip_ansi(result.stderr.strip() or result.stdout.strip())
                # 仅对网络类/瞬时错误重试, 业务错误直接返回不重试
                if attempt == 0 and _is_retryable_error(error_msg):
                    time.sleep(1)
                    continue
                return {"_error": error_msg}
        except subprocess.TimeoutExpired:
            if attempt == 0:
                time.sleep(1)
                continue
            return {"_error": "TIMEOUT"}
        except json.JSONDecodeError:
            return {"_error": "INVALID_JSON"}
        except Exception as e:
            if attempt == 0 and "connection" in str(e).lower():
                time.sleep(1)
                continue
            return {"_error": str(e)}

    return {"_error": "RETRY_EXHAUSTED"}


def _is_retryable_error(error_msg):
    """判断是否为可重试的网络/瞬时错误 (业务错误如权限不足、参数错误不重试)"""
    retryable_keywords = [
        "timeout", "connection refused", "connection reset",
        "i/o timeout", "EOF", "network is unreachable",
        "no such host", "Throttling", "ServiceUnavailable",
        "InternalError", "Get \"http"
    ]
    error_lower = error_msg.lower()
    return any(kw.lower() in error_lower for kw in retryable_keywords)


def safe_extract_list(data, container_key, item_key):
    """
    容错提取列表数据。
    兼容三种 SAG API 响应结构:
    1. {"Key": {"Item": [...]}}   — 标准嵌套
    2. {"Key": {"Item": {...}}}   — 单条未包装
    3. {"Key": [...]}             — 容器直接是数组
    """
    if not isinstance(data, dict):
        return []
    container = data.get(container_key, {})
    if isinstance(container, list):
        return container
    if isinstance(container, dict):
        items = container.get(item_key, [])
        if isinstance(items, dict):
            return [items]
        if isinstance(items, list):
            return items
    return []


def parse_endtime(end_time_raw):
    """
    解析 EndTime 字段，兼容:
    1. ISO 格式: "2027-05-09T00:00:00Z"
    2. 毫秒时间戳: 1809619206000 (张北SPE等区域)
    3. 带时区: "2027-05-09T08:00:00+08:00"
    """
    if not end_time_raw:
        return None

    if isinstance(end_time_raw, (int, float)):
        return datetime.fromtimestamp(end_time_raw / 1000, tz=timezone.utc)

    if isinstance(end_time_raw, str):
        if end_time_raw.isdigit():
            ts = int(end_time_raw)
            if ts > 2000000000:
                ts = ts / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)

        try:
            cleaned = end_time_raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(end_time_raw, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    return None


def get_all_regions():
    """动态获取所有 SAG 可用区域 (排除已关停和测试区域)"""
    data = run_cli("DescribeRegions", "cn-shanghai")
    if "_error" in data:
        print(f"  [ERROR] 获取区域列表失败: {data['_error'][:80]}")
        return []

    regions = safe_extract_list(data, "Regions", "Region")
    valid = []
    for r in regions:
        name = r.get("LocalName", "")
        if "已关停" in name or "内部测试" in name:
            continue
        region_id = r["RegionId"]
        # 应用区域过滤
        if REGION_FILTER != "all":
            if region_id not in REGION_FILTER:
                continue
        valid.append({
            "region_id": region_id,
            "name": name
        })
    return valid


def get_all_instances(region_id):
    """获取区域内所有实例 (自动翻页)"""
    all_instances = []
    page = 1
    while True:
        data = run_cli("DescribeSmartAccessGateways", region_id,
                       {"PageSize": "50", "PageNumber": str(page)})
        if "_error" in data:
            errors_log.append(f"[{region_id}] ListInstances: {data['_error'][:80]}")
            break
        instances = safe_extract_list(data, "SmartAccessGateways", "SmartAccessGateway")
        all_instances.extend(instances)
        total = data.get("TotalCount", 0)
        if len(all_instances) >= total:
            break
        page += 1
    return all_instances


def should_inspect(item_number):
    """检查指定巡检项是否在本次执行范围内"""
    if INSPECTION_ITEMS == "all":
        return True
    return item_number in INSPECTION_ITEMS


# ============================================================
# 巡检函数 (#1 - #10)
# ============================================================

def inspect_01_online_status(instance):
    """#1 设备在线状态"""
    status_raw = instance.get("Status", "Unknown")
    status = status_raw.lower().strip() if status_raw else "unknown"
    if status == "active":
        return "green", "Active"
    elif status == "offline":
        return "red", "Offline"
    elif status in ("arrearage", "stopped"):
        return "red", f"欠费停机 ({status_raw})"
    elif status == "ordered":
        return "yellow", "已下单(未激活)"
    else:
        return "yellow", status_raw


def inspect_02_vpn_tunnel(sag_id, region_id):
    """#2 VPN 隧道状态"""
    data = run_cli("DescribeSmartAccessGatewayAttribute", region_id,
                   {"SmartAGId": sag_id})
    if "_error" in data:
        return "yellow", f"查询失败: {data['_error'][:50]}"

    vpn_status = (data.get("VpnStatus", "") or "").lower()
    if vpn_status == "up":
        return "green", "UP"
    elif vpn_status == "down":
        return "red", "DOWN"

    # 备用: Links 结构
    links = data.get("Links", {})
    if isinstance(links, dict):
        link_list = links.get("Link", [])
        if isinstance(link_list, dict):
            link_list = [link_list]
        if link_list:
            up_count = sum(1 for l in link_list
                          if (l.get("Status", "") or "").lower() == "up")
            if up_count > 0:
                return "green", f"UP ({up_count}/{len(link_list)} links)"
            else:
                return "red", f"DOWN (all {len(link_list)} links)"

    return "yellow", "无VPN状态信息"


def inspect_03_ha_status(sag_id, region_id, sn_list):
    """
    #3 HA 主备状态
    判定逻辑:
    - API 不支持/设备不存在 → green (单设备无HA能力)
    - OFF 且单SN → green (单设备常态)
    - OFF 且多SN → yellow (有双设备但未开启HA, 可能配置遗漏)
    - ON 且多SN → 检查备设备状态:
        - Normal/Active/Standby → green
        - Switching → yellow
        - 其他异常 → yellow/red
    - ON 且单SN → yellow (HA开启但备设备可能脱落)
    """
    data = run_cli("DescribeSmartAccessGatewayHa", region_id,
                   {"SmartAGId": sag_id})
    if "_error" in data:
        err = str(data["_error"])
        if "NotExist" in err or "not support" in err.lower() or "NotFound" in err:
            return "green", "单设备(不支持HA)"
        return "yellow", f"查询失败: {data['_error'][:50]}"

    # 提取 HA 状态 (兼容多种字段名)
    ha_state = (data.get("DeviceLevelBackupState", "")
                or data.get("BackupState", "") or "")
    ha_mode = data.get("HaMode", "") or data.get("Mode", "") or ""

    # 提取备设备状态 (如果 API 返回了这些字段)
    backup_device_status = (data.get("BackupDeviceStatus", "")
                           or data.get("StandbyStatus", "") or "")

    # 统一转小写比较
    ha_state_lower = ha_state.lower().strip()
    backup_status_lower = backup_device_status.lower().strip()

    # Case 1: HA 未开启
    if ha_state_lower == "off" or (not ha_state and not ha_mode):
        if len(sn_list) > 1:
            return "yellow", f"多SN({len(sn_list)}台)但HA未开启"
        return "green", "单设备(HA未开启)"

    # Case 2: HA 已开启
    if ha_state_lower in ("on", "normal", "active", "standby"):
        # 检查: HA开启但只有单SN, 备设备可能已脱落
        if len(sn_list) <= 1 and ha_state_lower == "on":
            return "yellow", "HA已开启但仅检测到单设备(备设备可能脱落)"

        # 检查备设备状态 (如果有返回)
        if backup_status_lower:
            if backup_status_lower in ("normal", "active", "standby", "up"):
                return "green", f"HA正常 (主备均在线, state={ha_state})"
            elif backup_status_lower in ("offline", "down", "failed"):
                return "red", f"HA降级: 备设备异常 ({backup_device_status})"
            else:
                return "yellow", f"HA状态: {ha_state}, 备设备: {backup_device_status}"

        # 无备设备状态字段, 仅根据 ha_state 判断
        return "green", f"HA正常 ({ha_state})"

    # Case 3: 切换中
    if "switch" in ha_state_lower:
        return "yellow", f"HA切换中 ({ha_state})"

    # Case 4: 未知状态
    return "yellow", f"HA状态未知: {ha_state}"


def inspect_04_expiry(instance):
    """#4 到期检查"""
    end_time_raw = instance.get("EndTime", "")
    end_time = parse_endtime(end_time_raw)

    if end_time is None:
        if not end_time_raw:
            return "yellow", "到期时间为空(可能为测试实例)"
        return "yellow", f"无法解析到期时间: {str(end_time_raw)[:30]}"

    now = datetime.now(timezone.utc)
    days_left = (end_time - now).days
    display = end_time.strftime("%Y-%m-%d")

    if days_left < 0:
        return "red", f"已过期 {abs(days_left)} 天 ({display})"
    elif days_left < THRESHOLDS["expiry_red_days"]:
        return "red", f"剩余 {days_left} 天 ({display})"
    elif days_left <= THRESHOLDS["expiry_yellow_days"]:
        return "yellow", f"剩余 {days_left} 天 ({display})"
    else:
        return "green", f"剩余 {days_left} 天 ({display})"


def inspect_05_4g_link(sag_id, region_id, sn_list):
    """#5 4G 链路状态"""
    if not sn_list:
        return "skip", "无设备SN"

    results = []
    for sn in sn_list:
        data = run_cli("DescribeSagWan4G", region_id,
                       {"SmartAGId": sag_id, "SmartAGSn": sn})
        if "_error" in data:
            err = data["_error"]
            if "NotOnline" in err:
                results.append(("yellow", f"{sn}: 设备离线"))
            elif "DeviceNotExist" in err:
                results.append(("yellow", f"{sn}: 设备不存在"))
            else:
                results.append(("yellow", f"{sn}: 查询失败"))
            continue

        status = (data.get("Status", "") or "").lower()
        strength = data.get("SignalStrength", "") or data.get("Strength", "")

        if status in ("connected", "l_connected"):
            results.append(("green", f"{sn}: 连接(信号:{strength})"))
        elif status in ("disconnected", ""):
            results.append(("green", f"{sn}: 无4G或未插卡"))
        elif status == "abnormal":
            results.append(("yellow", f"{sn}: 4G异常"))
        else:
            results.append(("yellow", f"{sn}: {status}"))

    worst = "green"
    for level, _ in results:
        if level == "red":
            worst = "red"
            break
        elif level == "yellow" and worst == "green":
            worst = "yellow"

    detail = "; ".join([msg for _, msg in results])
    return worst, detail


def inspect_06_ccn_cen(sag_id, instance, region_id):
    """#6 CCN/CEN 绑定"""
    ccn_id = instance.get("AssociatedCcnId", "") or instance.get("CcnId", "")
    cen_id = instance.get("CenId", "")

    if not ccn_id and not cen_id:
        grant_data = run_cli("DescribeGrantSagRules", region_id,
                             {"SmartAGId": sag_id, "PageSize": "10"})
        if "_error" not in grant_data:
            rules = safe_extract_list(grant_data, "GrantRules", "GrantRule")
            if rules:
                cen_id = rules[0].get("CenInstanceId", "") or \
                         rules[0].get("CenId", "") or \
                         f"已授权(规则数:{len(rules)})"

    if ccn_id and cen_id:
        return "green", f"CCN: {ccn_id}, CEN: {cen_id}"
    elif ccn_id:
        return "yellow", f"CCN: {ccn_id}, CEN未绑定"
    elif cen_id:
        return "yellow", f"CCN未关联, CEN: {cen_id}"
    else:
        return "red", "未绑定CCN/CEN"


def inspect_07_route_health(sag_id, region_id, sn_list):
    """#7 路由健康 (遍历所有 SN 设备)"""
    if not sn_list:
        return "skip", "无设备SN"

    worst_level = "green"
    details = []

    for sn in sn_list:
        data = run_cli("DescribeSagRouteList", region_id,
                       {"SmartAGId": sag_id, "SmartAGSn": sn})
        if "_error" in data:
            err = data["_error"]
            if "NotOnline" in err:
                details.append(f"{sn[-6:]}: 离线")
                worst_level = "yellow" if worst_level == "green" else worst_level
            elif "DeviceNotExist" in err:
                details.append(f"{sn[-6:]}: 不存在")
                worst_level = "yellow" if worst_level == "green" else worst_level
            else:
                details.append(f"{sn[-6:]}: 查询失败")
                worst_level = "yellow" if worst_level == "green" else worst_level
            continue

        routes = safe_extract_list(data, "Routes", "Route")
        if not routes:
            details.append(f"{sn[-6:]}: 无路由")
            worst_level = "red"
            continue

        has_default = any(
            (r.get("DestinationCidr", "") or r.get("Destination", ""))
            in ("0.0.0.0/0", "default")
            for r in routes
        )

        if has_default:
            details.append(f"{sn[-6:]}: {len(routes)}条(含默认)")
        elif len(routes) >= 3:
            details.append(f"{sn[-6:]}: {len(routes)}条(无默认)")
            if worst_level == "green":
                worst_level = "yellow"
        else:
            details.append(f"{sn[-6:]}: 仅{len(routes)}条(无默认)")
            worst_level = "red"

    return worst_level, "; ".join(details) if details else "无结果"


def inspect_08_acl_qos(instance):
    """#8 ACL/QoS 合理性"""
    # 离线/欠费实例: ACL/QoS状态无运行时意义, 降为 skip
    status_raw = (instance.get("Status", "") or "").lower()
    if status_raw in ("offline", "arrearage", "stopped", "ordered"):
        return "skip", f"实例{status_raw}, 暂不评估"

    has_acl = bool(instance.get("AclIds", ""))
    has_qos = bool(instance.get("QosIds", ""))

    if has_acl and has_qos:
        return "green", "ACL+QoS 已绑定"
    elif has_acl:
        return "green", "ACL已绑定, QoS未绑定"
    elif has_qos:
        return "green", "QoS已绑定, ACL未绑定"
    else:
        return "yellow", "未绑定ACL和QoS"


def inspect_09_flow_logs(sag_id, instance, region_flowlogs):
    """
    #9 Flow Log 状态
    判定: 检查区域 FlowLog 是否绑定当前实例或通过 CCN/全局覆盖
    """
    # 离线/欠费实例: FlowLog 覆盖状态无运行时意义, 降为 skip
    status_raw = (instance.get("Status", "") or "").lower()
    if status_raw in ("offline", "arrearage", "stopped", "ordered"):
        return "skip", f"实例{status_raw}, 暂不评估"

    if not region_flowlogs:
        return "green", "区域无FlowLog配置(信息项)"

    bound_active = False
    covered_by_global = False
    bound_inactive = False

    for fl in region_flowlogs:
        status = (fl.get("Status", "") or "").lower()
        resource_id = fl.get("ResourceId", "")
        net_ids = fl.get("NetIds", "") or ""
        resource_type = fl.get("ResourceType", "")

        # 精确匹配: 按逗号分隔后逐个比较, 避免子串误命中
        net_id_list = [nid.strip() for nid in str(net_ids).split(",") if nid.strip()]
        is_bound = (sag_id in net_id_list) or (sag_id == resource_id)

        if is_bound:
            if status in ("active", "enabled"):
                bound_active = True
            else:
                bound_inactive = True
            continue

        # 全局/CCN 覆盖
        if resource_type in ("CCN", "VBR", "All") and status in ("active", "enabled"):
            covered_by_global = True

    if bound_active:
        return "green", "已启用(绑定实例)"
    if covered_by_global:
        return "green", f"已启用(通过全局/CCN覆盖)"
    if bound_inactive:
        return "yellow", "已关联FlowLog但状态未启用"

    active_count = sum(1 for fl in region_flowlogs
                       if (fl.get("Status", "") or "").lower() in ("active", "enabled"))
    if active_count > 0:
        return "yellow", f"区域有{active_count}个FlowLog但未绑定当前实例"
    else:
        return "yellow", "区域FlowLog均未启用"


def inspect_10_drop_topn(sag_id, region_id):
    """
    #10 丢包率 (DropTopN)
    在主流区域正常返回数据; 边缘区域 (如 cn-zhangjiakou-spe) 可能返回
    SAG_QUERY_TOPN_ERROR, 遇到时优雅 skip 不中断全局巡检。
    阈值: <1% green, 1%~5% yellow, >5% red
    """
    data = run_cli("DescribeSagDropTopN", region_id,
                   {"SmartAGId": sag_id, "Size": "10"})

    if "_error" in data:
        err = data["_error"]
        if "SAG_QUERY_TOPN_ERROR" in err or "NotFound" in err:
            return "skip", f"区域不支持 DropTopN ({region_id})"
        return "skip", f"查询失败: {err[:60]}"

    # 响应结构兼容: 可能是 dict 包着 list, 也可能是直接 list
    top_list = safe_extract_list(data, "DropTopN", "DropTopNType") \
        if "safe_extract_list" in globals() else []
    if not top_list:
        # 兜底: 手动找数组字段
        for key in ("DropTopN", "TopNList", "Data"):
            v = data.get(key)
            if isinstance(v, list):
                top_list = v
                break
            if isinstance(v, dict):
                for inner in v.values():
                    if isinstance(inner, list):
                        top_list = inner
                        break
                if top_list:
                    break

    if not top_list:
        return "green", "无丢包 TopN 记录"

    # 汇总丢包率: 取最大值作为代表性指标
    max_rate = 0.0
    for entry in top_list:
        if not isinstance(entry, dict):
            continue
        raw = entry.get("DropRate") or entry.get("Rate") or 0
        try:
            rate = float(str(raw).rstrip("%"))
            if rate > 1:  # 已经是百分数格式
                rate = rate / 100.0
            max_rate = max(max_rate, rate)
        except (ValueError, TypeError):
            continue

    pct = max_rate * 100
    if max_rate < 0.01:
        return "green", f"丢包率 {pct:.2f}% (健康)"
    elif max_rate < 0.05:
        return "yellow", f"丢包率 {pct:.2f}% (轻度)"
    else:
        return "red", f"丢包率 {pct:.2f}% (严重)"


# ============================================================
# 主流程
# ============================================================

def main():
    global api_call_count

    start_time = datetime.now()
    print(f"=== SAG 全量状态巡检 v{VERSION} (插件模式) ===")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"区域范围: {REGION_FILTER}")
    print(f"巡检项: {INSPECTION_ITEMS}")
    print()

    # Step 1: 动态获取区域
    print("[Step 1] 获取所有 SAG 可用区域...")
    regions = get_all_regions()
    if not regions:
        print("  ERROR: 无法获取区域列表, 退出")
        sys.exit(1)
    print(f"  → {len(regions)} 个目标区域")
    print()

    all_results = {}
    total_instances = 0
    summary_counts = {"green": 0, "yellow": 0, "red": 0, "skip": 0}

    for region_info in regions:
        region_id = region_info["region_id"]
        region_name = region_info["name"]

        print(f"[{region_id}] {region_name} - 获取实例...")
        instances = get_all_instances(region_id)

        if not instances:
            print(f"  → 无实例，跳过")
            continue

        print(f"  → {len(instances)} 个实例")
        total_instances += len(instances)

        # ===== 区域级查询 (每区域一次) =====
        region_flowlogs = []

        if should_inspect(9):
            flowlog_data = run_cli("DescribeFlowLogs", region_id,
                                   {"PageSize": "50"})
            if "_error" not in flowlog_data:
                region_flowlogs = safe_extract_list(
                    flowlog_data, "FlowLogs", "FlowLogSetType")

        # ===== 实例级巡检 =====
        region_results = []

        for idx, inst in enumerate(instances):
            sag_id = inst.get("SmartAGId", "")
            sag_name = inst.get("Name", "") or sag_id
            hw_version = inst.get("HardwareVersion", "")
            sn_field = inst.get("SerialNumber", "")
            is_software = (hw_version == "sag-software")
            sn_list = [s.strip() for s in sn_field.split(",") if s.strip()] \
                if sn_field else []

            print(f"  [{idx+1}/{len(instances)}] {sag_id}...")

            inspections = {}

            if should_inspect(1):
                inspections["01_在线状态"] = inspect_01_online_status(inst)

            if should_inspect(2):
                inspections["02_VPN隧道"] = inspect_02_vpn_tunnel(
                    sag_id, region_id)

            if should_inspect(3):
                if is_software:
                    inspections["03_HA状态"] = ("skip", "软件客户端(N/A)")
                else:
                    inspections["03_HA状态"] = inspect_03_ha_status(
                        sag_id, region_id, sn_list)

            if should_inspect(4):
                inspections["04_到期检查"] = inspect_04_expiry(inst)

            if should_inspect(5):
                if is_software:
                    inspections["05_4G链路"] = ("skip", "软件客户端(N/A)")
                elif not sn_list:
                    inspections["05_4G链路"] = ("skip", "无设备SN")
                else:
                    inspections["05_4G链路"] = inspect_05_4g_link(
                        sag_id, region_id, sn_list)

            if should_inspect(6):
                inspections["06_CCN/CEN"] = inspect_06_ccn_cen(
                    sag_id, inst, region_id)

            if should_inspect(7):
                if is_software:
                    inspections["07_路由健康"] = ("skip", "软件客户端(N/A)")
                elif not sn_list:
                    inspections["07_路由健康"] = ("skip", "无设备SN")
                else:
                    inspections["07_路由健康"] = inspect_07_route_health(
                        sag_id, region_id, sn_list)

            if should_inspect(8):
                inspections["08_ACL/QoS"] = inspect_08_acl_qos(inst)

            if should_inspect(9):
                inspections["09_FlowLog"] = inspect_09_flow_logs(
                    sag_id, inst, region_flowlogs)

            if should_inspect(10):
                inspections["10_丢包率"] = inspect_10_drop_topn(
                    sag_id, region_id)

            region_results.append({
                "sag_id": sag_id,
                "name": sag_name,
                "hw_version": hw_version,
                "serial_number": sn_field,
                "inspections": inspections
            })

            for _, (lv, _) in inspections.items():
                summary_counts[lv] = summary_counts.get(lv, 0) + 1

            time.sleep(0.15)

        all_results[f"{region_id}|{region_name}"] = region_results

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    effective_total = summary_counts["green"] + summary_counts["yellow"] + \
        summary_counts["red"]

    print(f"\n=== 巡检完成 ===")
    print(f"耗时: {duration:.0f}s | API: {api_call_count} 次 | 实例: {total_instances}")
    print(f"有效: {effective_total} (跳过: {summary_counts['skip']})")
    print(f"🟢 {summary_counts['green']} | 🟡 {summary_counts['yellow']} "
          f"| 🔴 {summary_counts['red']}")

    # 生成报告
    generate_report(all_results, total_instances, summary_counts,
                    effective_total, start_time, duration)


def generate_report(all_results, total_instances, summary_counts,
                    effective_total, start_time, duration):
    """生成 Markdown 格式巡检报告"""
    global api_call_count

    lines = []
    lines.append("# SAG 全量状态巡检报告")
    lines.append("")
    lines.append(f"**巡检时间**: {start_time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**脚本版本**: v{VERSION}")
    lines.append(f"**覆盖范围**: {len(all_results)} 个区域, "
                 f"{total_instances} 个实例, 10 项巡检")
    lines.append(f"**API 调用**: {api_call_count} 次 | **耗时**: {duration:.0f} 秒")
    lines.append(f"**调用模式**: CLI 插件模式 (aliyun-cli-smartag)")
    lines.append("")

    overall = "HEALTHY"
    if summary_counts["red"] > 0:
        overall = "CRITICAL"
    elif summary_counts["yellow"] > 0:
        overall = "ATTENTION NEEDED"

    lines.append(f"**Overall Status**: **{overall}**")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 级别 | 数量 | 占比(有效项) |")
    lines.append("|------|------|------|")
    for lv, label in [("green", "🟢 正常"), ("yellow", "🟡 注意"), ("red", "🔴 严重")]:
        count = summary_counts.get(lv, 0)
        pct = count / effective_total * 100 if effective_total else 0
        lines.append(f"| {label} | {count} | {pct:.1f}% |")
    lines.append(f"| ⏭️ 跳过 | {summary_counts.get('skip', 0)} | — |")
    lines.append(f"| **有效合计** | **{effective_total}** | 100% |")
    lines.append("")

    # 收集问题项
    red_items, yellow_items = [], []
    for region_key, results in all_results.items():
        rid = region_key.split("|")[0]
        for r in results:
            for item, (lv, detail) in r["inspections"].items():
                entry = (rid, r["sag_id"], r["name"], item, detail)
                if lv == "red":
                    red_items.append(entry)
                elif lv == "yellow":
                    yellow_items.append(entry)

    if red_items:
        lines.append(f"## 🔴 严重问题 ({len(red_items)} 项)")
        lines.append("")
        lines.append("| 区域 | 实例ID | 名称 | 巡检项 | 详情 |")
        lines.append("|------|--------|------|--------|------|")
        for rid, sid, name, item, detail in red_items:
            lines.append(f"| {rid} | {sid} | {name} | {item} | {detail} |")
        lines.append("")

    if yellow_items:
        lines.append(f"## 🟡 注意事项 ({len(yellow_items)} 项)")
        lines.append("")
        lines.append("| 区域 | 实例ID | 名称 | 巡检项 | 详情 |")
        lines.append("|------|--------|------|--------|------|")
        for rid, sid, name, item, detail in yellow_items:
            lines.append(f"| {rid} | {sid} | {name} | {item} | {detail} |")
        lines.append("")

    # 逐区域详细
    lines.append("## 逐区域详细结果")
    lines.append("")
    for region_key, results in all_results.items():
        rid, rname = region_key.split("|")
        lines.append(f"### {rname} ({rid}) — {len(results)} 实例")
        lines.append("")
        for r in results:
            lines.append(f"#### {r['sag_id']} ({r['name']})")
            lines.append("")
            lines.append(f"- **类型**: {r['hw_version'] or '未知'} | "
                         f"**SN**: {r['serial_number'] or '无'}")
            lines.append("")
            lines.append("| # | 巡检项 | 状态 | 详情 |")
            lines.append("|---|--------|------|------|")
            for item, (lv, detail) in r["inspections"].items():
                icon = {"green": "🟢", "yellow": "🟡",
                        "red": "🔴", "skip": "⏭️"}.get(lv, "⚪")
                lines.append(f"| {item[:2]} | {item[3:]} | {icon} | {detail} |")
            lines.append("")

    if errors_log:
        lines.append("## 执行错误日志")
        lines.append("")
        for err in errors_log:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("## 建议")
    lines.append("")
    if red_items:
        lines.append(f"1. **优先处理 {len(red_items)} 个严重问题**")
    if yellow_items:
        lines.append(f"2. **关注 {len(yellow_items)} 个注意事项**")
    lines.append("3. 定期执行巡检（建议每周一次）")
    lines.append("")

    # 写入
    report = "\n".join(lines)
    filename = f"SAG_状态巡检_{start_time.strftime('%Y%m%d')}.md"
    output_path = os.path.join(REPORT_OUTPUT_DIR, filename)

    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n报告: {output_path} ({len(lines)} 行)")


if __name__ == "__main__":
    main()
