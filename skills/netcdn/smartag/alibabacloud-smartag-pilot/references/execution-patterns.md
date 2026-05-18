# SAG Execution Patterns Reference

实际执行过程中积累的关键模式（patterns），供 agent 在生成批量查询/巡检脚本时参考。本文件只提供模式片段和注意事项，**不是可直接运行的完整脚本**。

---

## Pattern 1: 区域动态遍历

**适用场景**: 用户请求"查询所有区域"的任何操作

**核心逻辑**: 先通过 `describe-regions` 获取区域列表，再遍历每个有效区域。

```python
def get_all_regions():
    """动态获取所有 SAG 可用区域"""
    result = run_cli("describe-regions", "cn-shanghai", {})
    regions = result.get("Regions", {}).get("Region", [])
    
    valid_regions = []
    for r in regions:
        name = r.get("LocalName", "")
        # 跳过已关停区域和内部测试区域
        if "已关停" in name or "内部测试" in name:
            continue
        valid_regions.append({
            "region_id": r["RegionId"],
            "endpoint": r["RegionEndpoint"],
            "name": name
        })
    return valid_regions
```

**注意事项**:
- `describe-regions` 的 endpoint 可以用任意已知区域（如 cn-shanghai）调用
- 返回结果中包含已关停区域（如 ap-southeast-2），必须过滤
- 可能包含内部测试区域（如 cn-hangzhou-test-306），也需过滤
- 区域列表会随时变化（如 cn-zhangjiakou-spe 是非标准命名），不可硬编码

---

## Pattern 2: 实例类型预判与查询分流

**适用场景**: 对多个实例批量执行配置查询时，避免无效 API 调用

**核心逻辑**: 根据 HardwareVersion 和 SerialNumber 决定跳过哪些查询。

```python
def classify_instance(instance):
    """
    对实例进行分类，返回适用的查询项集合。
    
    Returns:
        set of applicable function numbers (1-12)
    """
    hw = instance.get("HardwareVersion", "")
    sn = instance.get("SerialNumber", "")
    
    # 所有类型都适用的基础查询
    applicable = {1, 5, 6, 7, 9, 10}
    
    if hw == "sag-software":
        # 软件客户端：仅加 APP 客户端查询
        applicable.add(11)
    else:
        # 硬件设备：加 NAT 查询
        applicable.add(8)
        if sn:
            # 有设备绑定：加所有设备级查询
            applicable.update({2, 3, 4, 12})
    
    return applicable
```

**注意事项**:
- `sag-software` 类型没有物理设备，调用 WAN/路由/DNS 等设备级 API 必定失败
- SerialNumber 为空表示硬件实例未绑定物理设备，设备级 API 同样会失败
- 区域级查询（#5 CCN列表, #6, #7, #9）每个区域只需调用一次，不要重复

---

## Pattern 3: 多 SN 拆分查询

**适用场景**: HA 双机部署的实例，SerialNumber 包含逗号

**核心逻辑**: 拆分后对每个 SN 独立执行设备级 API。

```python
def split_serial_numbers(sn_field):
    """
    拆分可能包含多个 SN 的字段。
    HA 实例格式: "sag61dacczh,sag61daccq6"
    
    Returns:
        list of (sn, role) tuples
    """
    if not sn_field:
        return []
    
    sn_list = [s.strip() for s in sn_field.split(",") if s.strip()]
    
    result = []
    for idx, sn in enumerate(sn_list):
        role = "主设备" if idx == 0 else f"备设备{idx}"
        result.append((sn, role))
    return result


# 使用示例
sn_pairs = split_serial_numbers(instance.get("SerialNumber", ""))
for sn, role in sn_pairs:
    print(f"  查询 {role}: {sn}")
    device_info = run_cli("describe-sag-device-info", region, {
        "SmartAGId": sag_id,
        "SmartAGSn": sn
    })
    wan_config = run_cli("describe-sag-wan-list", region, {
        "SmartAGId": sag_id,
        "SmartAGSn": sn
    })
    # ... 其他设备级 API
```

**注意事项**:
- 直接传入完整逗号字符串会返回 `Sag.DeviceNotExist` 或 `InstanceNotExit`
- 第一个 SN 通常是主设备，第二个是备设备
- 少数情况可能有 3 个以上 SN（理论上），代码应不限制数量

---

## Pattern 4: API 返回结构容错解析

**适用场景**: 所有 SAG API 的响应数据解析

**核心逻辑**: 阿里云 SAG API 返回的列表数据结构不一致，必须兼容多种格式。

```python
def safe_extract_list(data, container_key, item_key):
    """
    从 SAG API 响应中安全提取列表数据。
    
    兼容三种已知格式：
    1. {"Wans": {"Wan": [...]}}          — 标准嵌套
    2. {"Wans": {"Wan": {...}}}          — 单条记录未包装为数组
    3. {"Wans": [...]}                    — 容器直接是数组
    
    Args:
        data: API 返回的 JSON dict
        container_key: 外层容器键名 (如 "Wans", "StaticRoutes", "Acls")
        item_key: 内层列表键名 (如 "Wan", "StaticRoute", "Acl")
    
    Returns:
        list of dicts
    """
    if not isinstance(data, dict):
        return []
    
    container = data.get(container_key, {})
    
    # Pattern 3: 容器直接是 list
    if isinstance(container, list):
        return container
    
    # Pattern 1 & 2: 容器是 dict
    if isinstance(container, dict):
        items = container.get(item_key, [])
        if isinstance(items, dict):
            return [items]  # Pattern 2: 单条记录
        if isinstance(items, list):
            return items    # Pattern 1: 标准
    
    return []
```

**已知的 container_key / item_key 对应关系**:

| API | container_key | item_key |
|-----|--------------|----------|
| describe-smart-access-gateways | SmartAccessGateways | SmartAccessGateway |
| describe-sag-wan-list | Wans | Wan |
| describe-sag-static-route-list | StaticRoutes | StaticRoute |
| describe-sag-route-list | Routes | Route |
| describe-cloud-connect-networks | CloudConnectNetworks | CloudConnectNetwork |
| describe-grant-sag-rules | GrantRules | GrantRule |
| describe-acls | Acls | Acl |
| describe-qoses | Qoses | Qos |
| describe-dnat-entries | DnatEntries | DnatEntry |
| describe-snat-entries | SnatEntries | SnatEntry |
| describe-flow-logs | FlowLogs | FlowLogSetType |
| describe-health-checks | HealthChecks | HealthCheck |
| describe-smart-access-gateway-client-users | Users | User |
| describe-regions | Regions | Region |

**注意事项**:
- 当列表仅有 1 个元素时，部分 API 可能返回 dict 而非单元素 list
- 当列表为空时，container_key 可能直接不存在或为 `{}`
- 建议所有解析处加 try/except 兜底，避免因结构变化导致整个批量任务中断

---

## Pattern 5: 参数名陷阱防护

**适用场景**: 构建 CLI 调用参数时

**核心逻辑**: 部分 API 的参数命名与其他 API 不一致，需要特殊处理。

```python
# 参数名映射表 - 仅列出与常规不同的 API
PARAM_OVERRIDES = {
    "describe-dnat-entries": {
        "instance_id_param": "SagId",      # 其他 API 都用 SmartAGId
    },
    # 其他 API 统一使用 SmartAGId
}

def get_instance_id_param(action):
    """获取指定 API 的实例 ID 参数名"""
    override = PARAM_OVERRIDES.get(action, {})
    return override.get("instance_id_param", "SmartAGId")


# 使用示例
action = "describe-dnat-entries"
param_name = get_instance_id_param(action)  # -> "SagId"
params = {param_name: sag_id, "PageSize": "50"}
```

**已知陷阱清单**:

| API | 陷阱 | 正确写法 |
|-----|------|---------|
| describe-dnat-entries | 实例 ID 参数名不同 | `--sag-id sag-xxx`（非 --smart-ag-id） |
| describe-sag-wan-list | 必须传设备 SN | `--smart-ag-sn sagxxxx` |
| describe-sag-wan-4g | 必须传设备 SN | `--smart-ag-sn sagxxxx` |
| describe-sag-static-route-list | 必须传设备 SN | `--smart-ag-sn sagxxxx` |
| describe-sag-route-list | 必须传设备 SN | `--smart-ag-sn sagxxxx` |
| describe-sag-route-protocol-bgp | 必须传设备 SN | `--smart-ag-sn sagxxxx` |
| describe-sag-route-protocol-ospf | 必须传设备 SN | `--smart-ag-sn sagxxxx` |
| describe-sag-current-dns | 必须传设备 SN | `--smart-ag-sn sagxxxx` |

---

## Pattern 6: 区域级资源与实例级资源分离

**适用场景**: 批量查询多个实例时的性能优化

**核心逻辑**: ACL、QoS、FlowLog、CCN 列表是区域维度的资源，与单个实例无关。

```python
def batch_query_region(region, instances):
    """
    按区域批量查询：先查区域级资源，再逐实例查实例级资源。
    """
    # ===== 区域级查询（只调一次）=====
    region_ccn = run_cli("describe-cloud-connect-networks", region, {"PageSize": "50"})
    region_acl = run_cli("describe-acls", region, {"PageSize": "50"})
    region_qos = run_cli("describe-qoses", region, {"PageSize": "50"})
    region_flowlog = run_cli("describe-flow-logs", region, {"PageSize": "50"})
    
    # ===== 实例级查询（逐实例）=====
    for inst in instances:
        sag_id = inst["SmartAGId"]
        applicable = classify_instance(inst)
        
        # 实例属性（#1）— 所有类型都查
        attr = run_cli("describe-smart-access-gateway-attribute", region, {
            "SmartAGId": sag_id
        })
        
        # 设备级查询（#2,3,4,12）— 仅有 SN 的硬件实例
        if 2 in applicable:
            sn_pairs = split_serial_numbers(inst.get("SerialNumber", ""))
            for sn, role in sn_pairs:
                # ... 逐设备查询
                pass
        
        # 实例级绑定关系（#5 部分）
        grant = run_cli("describe-grant-sag-rules", region, {
            "SmartAGId": sag_id, "PageSize": "50"
        })
        
        # NAT（#8）— 注意 DnatEntries 用 SagId
        if 8 in applicable:
            dnat = run_cli("describe-dnat-entries", region, {
                "SagId": sag_id, "PageSize": "50"  # ⚠️ SagId!
            })
            snat = run_cli("describe-snat-entries", region, {
                "SmartAGId": sag_id, "PageSize": "50"
            })
        
        # APP 客户端（#11）— 仅 sag-software
        if 11 in applicable:
            users = run_cli("describe-smart-access-gateway-client-users", region, {
                "SmartAGId": sag_id, "PageSize": "50"
            })
```

**性能对比**（以 65 实例为例）:
- 不做分层：65 × 4（ACL/QoS/FlowLog/CCN）= 260 次冗余调用
- 分层后：7 区域 × 4 = 28 次，节省 232 次 API 调用

**注意事项**:
- 区域级资源的报告展示应放在区域汇总部分，不要对每个实例重复显示
- 如果需要判断某个 ACL/QoS 是否绑定了当前实例，需要检查实例的 `AclIds` / `QosIds` 字段
- CCN 列表是区域级的，但 GrantSagRules 和 VbrRelations 是实例级的

---

## Pattern 7: 错误处理与优雅降级

**适用场景**: 批量执行中个别 API 失败时不中断整体流程

**核心逻辑**: 捕获错误、分类处理、记录到报告中。

```python
def run_cli_safe(action, region, params):
    """
    带容错的 CLI 调用封装。
    返回 (data, error_msg) 元组。
    """
    result = run_cli(action, region, params)
    
    if not isinstance(result, dict):
        return None, "非JSON响应"
    
    if "_error" in result:
        error = result["_error"]
        # 分类处理
        if "MissingSmartAGSn" in error or "MissingSn" in error:
            return None, "无设备绑定"
        elif "SmartAccessGatewayNotOnline" in error:
            return None, "设备离线"
        elif "Sag.DeviceNotExist" in error or "InstanceNotExit" in error:
            return None, "设备不存在（可能需拆分多SN）"
        elif "InvalidApi" in error:
            return None, "API当前不可用"
        elif "Throttling" in error:
            # 限流：等待后重试一次
            time.sleep(2)
            return run_cli_safe(action, region, params)
        else:
            return None, error[:80]
    
    return result, None
```

**注意事项**:
- 批量任务中单个 API 失败不应终止整个流程
- Throttling 可重试一次，其他错误直接记录并跳过
- 报告中应清晰标注哪些项目查询失败及原因，而非默默忽略
- 所有 error_msg 最终体现在报告中，帮助用户了解哪些信息缺失

---

## Pattern 8: 响应值规范化（Response Value Normalization）

**适用场景**: 将 API 原始响应字段转换为人可读的报告内容

**背景**: SAG API 的多个字段返回值格式不直观（如带宽带 "M" 后缀、时间用毫秒时间戳），直接输出会导致报告可读性差甚至出错（如 "10MMbps"）。应在报告生成层统一做规范化。

```python
from datetime import datetime

def fmt_bandwidth(raw):
    """
    规范化带宽值。API 返回如 "10M", "2M", "0M"。
    输出: "10Mbps", "2Mbps", "-"
    """
    if not raw or str(raw) in ("-", ""):
        return "-"
    s = str(raw).rstrip("Mm")  # 去掉 API 自带的 "M" 后缀
    if s == "0":
        return "-"
    return f"{s}Mbps"


def fmt_timestamp(ms_value):
    """
    毫秒时间戳 → "YYYY-MM-DD" 日期字符串。
    输入: 1780934405000, "-", "", 0, None
    输出: "2026-06-07", "-", "-", "-", "-"
    """
    if not ms_value or str(ms_value) in ("-", "", "0"):
        return "-"
    try:
        return datetime.fromtimestamp(int(ms_value) / 1000).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return str(ms_value)


def fmt_status(value, default="-"):
    """
    规范化状态/枚举字段。空字符串统一显示为 default。
    """
    if not value or str(value).strip() == "":
        return default
    return str(value)
```

**使用示例**:

```python
attr = run_cli_safe("describe-smart-access-gateway-attribute", ...)

vpn = fmt_status(attr.get("VpnStatus"))         # "" → "-", "up" → "up"
bw = fmt_bandwidth(attr.get("MaxBandwidth"))     # "10M" → "10Mbps"
end = fmt_timestamp(attr.get("EndTime"))         # 1780934405000 → "2026-06-07"
```

**注意事项**:
- `MaxBandwidth` 字段已包含 "M" 后缀（表示 Megabit），脚本不可再追加 "M" 或 "Mbps"
- 时间戳统一为**毫秒级**（13位数字），需除以 1000 再调用 `fromtimestamp()`
- `EndTime` 为空或 `0` 表示该实例可能是按量付费或未激活，显示为 "-" 而非报错
- `VpnStatus` 空字符串不等于 "down"，只是属性未返回，应显示 "-"

---

## Pattern 9: 分页处理与数据一致性断言

**适用场景**：任何返回结构包含 `TotalCount` 的 List 类 API（`describe-smart-access-gateways`、`describe-acls`、`describe-qoses`、`describe-cloud-connect-networks`、`describe-flow-logs` 等）。

**核心逻辑**：`--page-size` 上限 50，实际资源可能超过该值；仅取首页会造成漏抓（评测以 *Pagination not handled* 判失败）。必须迭代 `--page-number` 直至累计 ≥ `TotalCount`。

```bash
# Bash 骨架 — 以 DescribeSmartAccessGateways 为例
fetch_all_pages() {
  local API="$1"; local REGION="$2"; local OUT="$3"
  local PAGE=1; local PAGE_SIZE=50; local TOTAL=0; local FETCHED=0
  echo '[]' > "$OUT"
  while : ; do
    local TMP=$(mktemp)
    aliyun smartag "$API" --biz-region-id "$REGION" --page-size $PAGE_SIZE --page-number $PAGE > "$TMP" || break
    TOTAL=$(jq -r '.TotalCount // 0' "$TMP")
    # 列表字段名随 API 变，需适配：SmartAccessGateways/SmartAccessGateway, Acls/Acl, Qoses/Qos …
    jq -s '.[0] + (.[1].SmartAccessGateways.SmartAccessGateway // [])' "$OUT" "$TMP" > "$OUT.new" && mv "$OUT.new" "$OUT"
    FETCHED=$(jq 'length' "$OUT")
    rm -f "$TMP"
    [ "$FETCHED" -ge "$TOTAL" ] && break
    PAGE=$((PAGE + 1))
  done
  # 一致性断言：实际拼接条数必须等于 TotalCount
  [ "$FETCHED" -eq "$TOTAL" ] || { echo "FAIL: $API@$REGION fetched=$FETCHED total=$TOTAL"; exit 1; }
}
```

**报告一致性断言**：生成 Markdown 报告前，验证 Summary 中红/黄/绿计数之和 ≡ 实际明细项总数：

```bash
RED=$(jq '[.[] | select(.level=="red")]   | length' /tmp/sag_findings.json)
YEL=$(jq '[.[] | select(.level=="yellow")]| length' /tmp/sag_findings.json)
GRN=$(jq '[.[] | select(.level=="green")] | length' /tmp/sag_findings.json)
ALL=$(jq 'length' /tmp/sag_findings.json)
[ $((RED + YEL + GRN)) -eq "$ALL" ] || { echo "FAIL: summary count mismatch"; exit 1; }
```

**注意事项**：
- `--page-size` 超过 50 会被 CLI 拒绝（见 common pitfalls）。
- 不同 API 的列表字段名不一致（`SmartAccessGateways.SmartAccessGateway` / `Acls.Acl` / `Qoses.Qos` / `CloudConnectNetworks.CloudConnectNetwork` …），使用 `// []` 兜底防 null。
- Summary 计数不能硬编码（如 `"normal: 8"`），必须从明细数组现算。

---

## Anti-Patterns（已知踩坑，务必避免）

| 错误做法 | 后果 | 正确做法 |
|---------|------|---------|
| 硬编码区域列表 | 遗漏 cn-zhangjiakou-spe 等非标准区域 | 调用 `describe-regions` 动态获取 |
| 对所有实例调用所有 12 项 | 大量 MissingSmartAGSn 无效请求 | 先分类再调用 |
| 多 SN 字段直接传入 API | 返回 DeviceNotExist | 按逗号拆分逐个查询 |
| `describe-dnat-entries` 用 --smart-ag-id | 返回 MissingSagId | 用 --sag-id |
| 假设 API 列表返回一定是 array | 单条时崩溃 | 用 safe_extract_list 容错 |
| 区域级 API 每实例调一次 | 65 实例 × 4 = 260 次冗余 | 每区域只调一次 |
| 报错直接 raise 中断 | 一个失败全部中止 | 优雅降级，继续下一个 |
| MaxBandwidth 直接拼接 "Mbps" | 显示 "10MMbps" | 先 rstrip("Mm") 再拼接单位 |
| EndTime 直接输出原始值 | 显示 13 位数字，用户无法理解 | fromtimestamp(int/1000) 转日期 |
| 空字符串字段不做兜底 | 报告出现空白或拼接异常 | 用 fmt_status() 统一转 "-" |
| 用 basic info 的 `VpnStatus` 字段判定隧道状态 | 丢失需调 `describe-smart-access-gateway-attribute` 才能拿到的详细属性 | 必须调 `describe-smart-access-gateway-attribute` 拿完整属性 |
| 用 `AssociatedCcnId` 字段代替 CCN 查询 | 缺失 CcnName / CenId / 绑定信息 | 必须调 `describe-cloud-connect-networks` |
| 用 `AclIds` 字段代替 ACL 查询 | 拿不到 rules / entries / 生效实例数 | 必须调 `describe-acls` |
| 仅看 `HardwareVersion` 字符串代替设备硬件信息 | 缺失固件版本、设备型号、序列号 | 必须调 `describe-sag-device-info` |
| 混淆分类与替代调用 | TestCase 期望 API 没命中 | basic info 是“分类器”不是“替代品”，遵守 **SKILL.md 的 Mandatory Call Contracts** |
| CLI JSON 响应直接 dump 到对话 | 结果出现大段 region id / key / 无关字段 | 重定向到 `/tmp/sag_*.json`，对话只给摘要 |
