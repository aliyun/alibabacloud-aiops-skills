"""
inspect_report.py - 阿里云网络产品全面巡检报告生成

汇总所有网络产品的巡检数据，生成中文 Markdown 格式的巡检报告。
报告包含：巡检概览、各产品详细分析（含指标解读）、风险评估和扩容建议。

所有内容均为中文，支持输出到文件或标准输出（供钉钉文档等使用）。

用法:
    python3 inspect_report.py --dir /tmp/net_inspect_xxx --days 3
    python3 inspect_report.py --dir /tmp/net_inspect_xxx --days 7 --output /path/to/report.md
"""

import argparse
import json
import os
import sys
import time


def load_json(filepath: str) -> dict:
    """加载 JSON 文件。"""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def risk_emoji(level: str) -> str:
    """风险等级标记。"""
    return {
        "critical": "🔴",
        "warning": "🟡",
        "ok": "🟢",
        "error": "⚠️",
    }.get(level, "⚪")


def risk_label(level: str) -> str:
    """风险等级中文标签。"""
    return {
        "critical": "严重",
        "warning": "告警",
        "ok": "正常",
        "error": "异常",
    }.get(level, "未知")


# ─── 各产品报告格式化函数 ──────────────────────────────────────────

def format_eip_section(data: dict) -> str:
    """格式化 EIP 巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 1. 弹性公网IP（EIP）\n")
    lines.append("**巡检说明**: 弹性公网IP（EIP）是独立的公网IP资源，可以绑定到ECS、NAT网关、SLB等实例。"
                 "巡检重点关注带宽利用率和限速丢包，带宽利用率过高说明接近购买带宽上限，"
                 "限速丢包表示已有流量因超出带宽限制而被丢弃。\n")

    if not instances:
        lines.append("> 该账号下巡检范围内没有 EIP 实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | IP地址 | 地域 | 带宽(Mbps) | 出峰值(Mbps) | 入峰值(Mbps) | 出利用率 | 入利用率 | 限速丢包 | 风险 |")
    lines.append("|--------|--------|------|-----------|-------------|-------------|---------|---------|---------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        out_drop = m.get("out_drop_max_pps", 0)
        in_drop = m.get("in_drop_max_pps", 0)
        drop_str = f"出{out_drop}/入{in_drop} pps" if m.get("has_drops") else "无"
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('ip_address', '')} "
            f"| {inst.get('region', '')} "
            f"| {inst.get('bandwidth', 0)} "
            f"| {m.get('tx_peak_mbps', 0)} "
            f"| {m.get('rx_peak_mbps', 0)} "
            f"| {m.get('tx_peak_pct', 0)}% "
            f"| {m.get('rx_peak_pct', 0)}% "
            f"| {drop_str} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    _add_risk_analysis(lines, instances, "EIP", _eip_risk_detail)
    return "\n".join(lines)


def _eip_risk_detail(inst: dict) -> str:
    m = inst.get("metrics", {})
    parts = [f"出方向峰值 {m.get('tx_peak_mbps', 0)} Mbps (利用率 {m.get('tx_peak_pct', 0)}%)"]
    parts.append(f"入方向峰值 {m.get('rx_peak_mbps', 0)} Mbps (利用率 {m.get('rx_peak_pct', 0)}%)")
    if m.get("has_drops"):
        parts.append(f"存在限速丢包: 出方向 {m.get('out_drop_max_pps', 0)} pps / 入方向 {m.get('in_drop_max_pps', 0)} pps")
    return "；".join(parts)


def format_cbwp_section(data: dict) -> str:
    """格式化共享带宽包巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 2. 共享带宽包（CBWP）\n")
    lines.append("**巡检说明**: 共享带宽包允许多个EIP共享一个带宽池，降低成本。"
                 "巡检重点关注出方向利用率（out_rate_percent）和限速丢包（ratelimit_drop_speed）。"
                 "利用率超过70%需要关注，超过90%或出现丢包需要立即扩容。\n")

    if not instances:
        lines.append("> 该账号下巡检范围内没有共享带宽包实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | 名称 | 地域 | 带宽上限(Mbps) | 出峰值(Mbps) | 出均值(Mbps) | 入峰值(Mbps) | 出利用率峰值 | 限速丢包 | 风险 |")
    lines.append("|--------|------|------|---------------|-------------|-------------|-------------|------------|---------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        drop_str = f"是 ({m.get('drop_max_pps', 0)} pps)" if m.get("has_ratelimit_drops") else "无"
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('region', '')} "
            f"| {inst.get('bandwidth_limit', 0)} "
            f"| {m.get('tx_peak_mbps', 0)} "
            f"| {m.get('tx_avg_mbps', 0)} "
            f"| {m.get('rx_peak_mbps', 0)} "
            f"| {m.get('tx_peak_pct', 0)}% "
            f"| {drop_str} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    _add_risk_analysis(lines, instances, "共享带宽包", _cbwp_risk_detail)
    return "\n".join(lines)


def _cbwp_risk_detail(inst: dict) -> str:
    m = inst.get("metrics", {})
    parts = [f"带宽上限 {inst.get('bandwidth_limit', 0)} Mbps"]
    parts.append(f"出方向峰值 {m.get('tx_peak_mbps', 0)} Mbps / 均值 {m.get('tx_avg_mbps', 0)} Mbps (利用率峰值 {m.get('tx_peak_pct', 0)}%)")
    if m.get("has_ratelimit_drops"):
        parts.append(f"存在限速丢包: {m.get('drop_max_pps', 0)} pps")
    return "；".join(parts)


def format_nat_section(data: dict) -> str:
    """格式化 NAT 网关巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 3. NAT网关\n")
    lines.append("**巡检说明**: NAT网关提供SNAT（源地址转换）和DNAT（目的地址转换）服务。"
                 "巡检重点关注SNAT并发连接数（SnatConnection）和带宽利用率。"
                 "不同规格的NAT网关有不同的SNAT连接数上限和带宽上限。"
                 "SessionLimitDropRate 指标表示因连接数达到规格上限而被丢弃的请求，"
                 "一旦出现丢包说明需要升级规格。\n")

    if not instances:
        lines.append("> 该账号下巡检范围内没有 NAT 网关实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | 名称 | 地域 | 规格 | 出峰值(Mbps) | SNAT连接数峰值 | SNAT利用率 | 带宽利用率 | 连接丢包 | 风险 |")
    lines.append("|--------|------|------|------|-------------|--------------|----------|----------|---------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        drop_str = f"是 ({m.get('session_drop_max_pps', 0)} pps)" if m.get("has_session_drop") else "无"
        snat_peak = int(m.get("snat_connections_peak", 0))
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('region', '')} "
            f"| {inst.get('spec', '-')} "
            f"| {m.get('tx_peak_mbps', 0)} "
            f"| {snat_peak:,} "
            f"| {m.get('snat_pct', 0)}% "
            f"| {m.get('bw_pct', 0)}% "
            f"| {drop_str} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    _add_risk_analysis(lines, instances, "NAT网关", _nat_risk_detail)
    return "\n".join(lines)


def _nat_risk_detail(inst: dict) -> str:
    m = inst.get("metrics", {})
    parts = [f"规格 {inst.get('spec', '-')}"]
    parts.append(f"SNAT连接数峰值 {int(m.get('snat_connections_peak', 0)):,} (上限 {m.get('snat_limit', 0):,}，利用率 {m.get('snat_pct', 0)}%)")
    parts.append(f"带宽利用率 {m.get('bw_pct', 0)}%")
    if m.get("has_session_drop"):
        parts.append(f"存在连接丢包: {m.get('session_drop_max_pps', 0)} pps")
    return "；".join(parts)


def format_cen_section(data: dict) -> str:
    """格式化 CEN 巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 4. 云企业网（CEN）\n")
    lines.append("**巡检说明**: 云企业网（CEN）用于实现不同VPC之间、VPC与本地数据中心之间的网络互通。"
                 "巡检重点关注跨地域带宽使用情况和带宽包容量。"
                 "跨地域互通需要购买 CEN 带宽包，同地域互通不消耗带宽包额度。\n")

    if not instances:
        lines.append("> 该账号下没有云企业网（CEN）实例。\n")
        return "\n".join(lines)

    lines.append("| CEN实例ID | 名称 | 状态 | 带宽包总容量(Mbps) | 跨域出峰值(Mbps) | 跨域入峰值(Mbps) | 利用率 | 风险 |")
    lines.append("|-----------|------|------|------------------|-----------------|-----------------|--------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        bw_packages = inst.get("bandwidth_packages", [])
        bw_info = f"{m.get('total_bw_limit_mbps', 0)}" if bw_packages else "无带宽包"
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('status', '-')} "
            f"| {bw_info} "
            f"| {m.get('tx_peak_mbps', 0)} "
            f"| {m.get('rx_peak_mbps', 0)} "
            f"| {m.get('peak_utilization_pct', 0)}% "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    # 带宽包详情
    for inst in instances:
        bw_packages = inst.get("bandwidth_packages", [])
        if bw_packages:
            lines.append(f"\n**{inst.get('instance_id', '')} 带宽包详情:**\n")
            lines.append("| 带宽包ID | 名称 | 带宽(Mbps) | 互通区域A | 互通区域B | 状态 |")
            lines.append("|----------|------|-----------|----------|----------|------|")
            for pkg in bw_packages:
                lines.append(
                    f"| {pkg.get('package_id', '')} "
                    f"| {pkg.get('name', '') or '-'} "
                    f"| {pkg.get('bandwidth_limit', 0)} "
                    f"| {pkg.get('geographic_region_a', '-')} "
                    f"| {pkg.get('geographic_region_b', '-')} "
                    f"| {pkg.get('status', '-')} |"
                )

    lines.append("")
    return "\n".join(lines)


def format_tr_section(data: dict) -> str:
    """格式化 TR 巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 5. 转发路由器（Transit Router）\n")
    lines.append("**巡检说明**: 转发路由器（TR）是云企业网 CEN 的核心组件，每个地域部署一个 TR。"
                 "TR 负责同地域内的 VPC/VBR/VPN 互通，以及跨地域连接的转发。"
                 "巡检重点关注 TR 的连接状态，异常连接可能导致网络不通。\n")

    if not instances:
        lines.append("> 该账号下没有转发路由器（TR）实例。\n")
        return "\n".join(lines)

    for inst in instances:
        risk = inst.get("risk_level", "unknown")
        lines.append(f"#### TR: {inst.get('instance_id', '')} ({inst.get('instance_name', '') or '-'}) {risk_emoji(risk)}\n")
        lines.append(f"- **地域**: {inst.get('region', '-')}")
        lines.append(f"- **所属CEN**: {inst.get('cen_id', '-')}")
        lines.append(f"- **状态**: {inst.get('status', '-')}")
        lines.append(f"- **类型**: {inst.get('type', '-')}")
        lines.append(f"- **路由表数量**: {inst.get('route_table_count', 0)}")

        vpc_atts = inst.get("vpc_attachments", [])
        lines.append(f"\n**VPC 连接 ({len(vpc_atts)} 个):**\n")
        if vpc_atts:
            lines.append("| 连接ID | 名称 | VPC ID | 状态 |")
            lines.append("|--------|------|--------|------|")
            for a in vpc_atts:
                lines.append(
                    f"| {a.get('attachment_id', '')} "
                    f"| {a.get('attachment_name', '') or '-'} "
                    f"| {a.get('vpc_id', '')} "
                    f"| {a.get('status', '-')} |"
                )
        else:
            lines.append("> 无 VPC 连接\n")

        vbr_atts = inst.get("vbr_attachments", [])
        lines.append(f"\n**VBR 连接 ({len(vbr_atts)} 个):**\n")
        if vbr_atts:
            lines.append("| 连接ID | 名称 | VBR ID | 状态 |")
            lines.append("|--------|------|--------|------|")
            for a in vbr_atts:
                lines.append(
                    f"| {a.get('attachment_id', '')} "
                    f"| {a.get('attachment_name', '') or '-'} "
                    f"| {a.get('vbr_id', '')} "
                    f"| {a.get('status', '-')} |"
                )
        else:
            lines.append("> 无 VBR 连接\n")

        lines.append("")

    return "\n".join(lines)


def format_physconn_section(data: dict) -> str:
    """格式化物理专线巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 6. 物理专线\n")
    lines.append("**巡检说明**: 物理专线提供本地数据中心到阿里云的专用物理链路连接。"
                 "物理专线本身无云监控流量指标，流量监控通过关联的 VBR（虚拟边界路由器）查看。"
                 "巡检重点关注专线状态（应为 Enabled）和业务状态（应为 Normal）。\n")

    if not instances:
        lines.append("> 该账号下巡检范围内没有物理专线实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | 名称 | 地域 | 带宽上限(Mbps) | 端口类型 | 运营商 | 状态 | 业务状态 | 风险 |")
    lines.append("|--------|------|------|---------------|---------|--------|------|---------|------|")

    for inst in instances:
        risk = inst.get("risk_level", "unknown")
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('region', '')} "
            f"| {inst.get('bandwidth_limit', 0)} "
            f"| {inst.get('port_type', '-')} "
            f"| {inst.get('line_operator', '-')} "
            f"| {inst.get('status', '-')} "
            f"| {inst.get('business_status', '-')} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    lines.append("> **提示**: 物理专线流量监控请查看关联 VBR 的监控数据。\n")
    return "\n".join(lines)


def format_vbr_section(data: dict) -> str:
    """格式化 VBR 巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 7. VBR（虚拟边界路由器）\n")
    lines.append("**巡检说明**: VBR 是物理专线的虚拟路由终端，连接 IDC 和 VPC。"
                 "巡检重点关注带宽使用、健康检查延迟和丢包率。"
                 "健康检查延迟（VbrHealthyCheckLatency，单位微秒需转为毫秒）反映链路质量，"
                 "丢包率（VbrHealthyCheckLossRate）直接体现链路可靠性。"
                 "延迟 > 100ms 或丢包率 > 5% 为严重，延迟 > 50ms 或丢包率 > 1% 为告警。\n")

    if not instances:
        lines.append("> 该账号下巡检范围内没有 VBR 实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | 名称 | 地域 | 关联专线 | 出峰值(Mbps) | 入峰值(Mbps) | 延迟峰值(ms) | 丢包率峰值 | 丢包(pps) | 风险 |")
    lines.append("|--------|------|------|---------|-------------|-------------|------------|----------|----------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        drop_in = m.get("drop_in_peak_pps", 0)
        drop_out = m.get("drop_out_peak_pps", 0)
        drop_str = f"入{drop_in}/出{drop_out}" if (drop_in > 0 or drop_out > 0) else "无"
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('region', '')} "
            f"| {inst.get('physical_connection_id', '-')} "
            f"| {m.get('tx_peak_mbps', 0)} "
            f"| {m.get('rx_peak_mbps', 0)} "
            f"| {m.get('health_check_latency_peak_ms', 0)} "
            f"| {m.get('health_check_loss_peak_pct', 0)}% "
            f"| {drop_str} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    _add_risk_analysis(lines, instances, "VBR", _vbr_risk_detail)
    return "\n".join(lines)


def _vbr_risk_detail(inst: dict) -> str:
    m = inst.get("metrics", {})
    parts = []
    parts.append(f"出方向峰值 {m.get('tx_peak_mbps', 0)} Mbps / 入方向峰值 {m.get('rx_peak_mbps', 0)} Mbps")
    if m.get("health_check_latency_peak_ms", 0) > 0:
        parts.append(f"健康检查延迟峰值 {m.get('health_check_latency_peak_ms', 0)}ms / 均值 {m.get('health_check_latency_avg_ms', 0)}ms")
    if m.get("health_check_loss_peak_pct", 0) > 0:
        parts.append(f"健康检查丢包率峰值 {m.get('health_check_loss_peak_pct', 0)}% / 均值 {m.get('health_check_loss_avg_pct', 0)}%")
    return "；".join(parts)


def format_ga_section(data: dict) -> str:
    """格式化 GA 巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 8. 全球加速（GA）\n")
    lines.append("**巡检说明**: 全球加速（Global Accelerator）利用阿里云全球网络优化跨境/跨域网络访问质量。"
                 "巡检重点关注加速实例的带宽使用率，超过带宽上限将触发限速。\n")

    if not instances:
        lines.append("> 该账号下没有全球加速（GA）实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | 名称 | 带宽(Mbps) | 出峰值(Mbps) | 入峰值(Mbps) | 利用率 | 状态 | 风险 |")
    lines.append("|--------|------|-----------|-------------|-------------|--------|------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('bandwidth', 0)} "
            f"| {m.get('tx_peak_mbps', 0)} "
            f"| {m.get('rx_peak_mbps', 0)} "
            f"| {m.get('peak_utilization_pct', 0)}% "
            f"| {inst.get('state', '-')} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    return "\n".join(lines)


def format_clb_section(data: dict) -> str:
    """格式化 CLB 巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 9. 传统型负载均衡（CLB）\n")
    lines.append("**巡检说明**: CLB（原 SLB）提供四层和七层负载均衡服务。"
                 "巡检重点关注流量带宽、活跃连接数、新建连接数（CPS）、QPS 和丢包情况。"
                 "InstanceDropPacketRX/TX 表示因达到规格上限而丢弃的数据包。\n")

    if not instances:
        lines.append("> 该账号下巡检范围内没有 CLB 实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | 名称 | 地域 | 地址 | 出峰值(Mbps) | 活跃连接峰值 | QPS峰值 | 丢包 | 风险 |")
    lines.append("|--------|------|------|------|-------------|------------|---------|------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        has_drops = m.get("has_drops", False)
        drop_str = f"出{m.get('drop_tx_max_pps', 0)}/入{m.get('drop_rx_max_pps', 0)} pps" if has_drops else "无"
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('region', '')} "
            f"| {inst.get('address', '-')} "
            f"| {m.get('tx_peak_mbps', 0)} "
            f"| {int(m.get('active_conn_peak', 0)):,} "
            f"| {int(m.get('qps_peak', 0)):,} "
            f"| {drop_str} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    return "\n".join(lines)


def format_alb_section(data: dict) -> str:
    """格式化 ALB 巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 10. 应用型负载均衡（ALB）\n")
    lines.append("**巡检说明**: ALB 专注于七层（HTTP/HTTPS）负载均衡，支持丰富的内容路由规则。"
                 "巡检重点关注 QPS、HTTP 状态码分布（特别是 5XX 错误率）和连接数。"
                 "5XX 错误率反映后端服务健康状况，持续高 5XX 需要排查后端服务问题。\n")

    if not instances:
        lines.append("> 该账号下巡检范围内没有 ALB 实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | 名称 | 地域 | QPS峰值 | 2XX峰值 | 4XX峰值 | 5XX峰值 | 5XX错误率 | 活跃连接 | 风险 |")
    lines.append("|--------|------|------|---------|---------|---------|---------|----------|---------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('region', '')} "
            f"| {int(m.get('qps_peak', 0)):,} "
            f"| {int(m.get('http_2xx_peak', 0)):,} "
            f"| {int(m.get('http_4xx_peak', 0)):,} "
            f"| {int(m.get('http_5xx_peak', 0)):,} "
            f"| {m.get('error_5xx_pct', 0)}% "
            f"| {int(m.get('active_conn_peak', 0)):,} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    return "\n".join(lines)


def format_nlb_section(data: dict) -> str:
    """格式化 NLB 巡检报告段落。"""
    instances = data.get("instances", [])
    lines = []

    lines.append("### 11. 网络型负载均衡（NLB）\n")
    lines.append("**巡检说明**: NLB 专注于四层（TCP/UDP）负载均衡，提供超高性能和低延迟。"
                 "巡检重点关注带宽使用、活跃连接数（Flow）和新建连接数。"
                 "NLB 为全托管服务，无固定带宽上限，但仍需关注流量趋势。\n")

    if not instances:
        lines.append("> 该账号下巡检范围内没有 NLB 实例。\n")
        return "\n".join(lines)

    lines.append("| 实例ID | 名称 | 地域 | 出峰值(Mbps) | 入峰值(Mbps) | 活跃连接峰值 | 新建连接峰值 | 风险 |")
    lines.append("|--------|------|------|-------------|-------------|------------|------------|------|")

    for inst in instances:
        m = inst.get("metrics", {})
        risk = inst.get("risk_level", "unknown")
        lines.append(
            f"| {inst.get('instance_id', '')} "
            f"| {inst.get('instance_name', '') or '-'} "
            f"| {inst.get('region', '')} "
            f"| {m.get('tx_peak_mbps', 0)} "
            f"| {m.get('rx_peak_mbps', 0)} "
            f"| {int(m.get('active_flow_peak', 0)):,} "
            f"| {int(m.get('new_flow_peak', 0)):,} "
            f"| {risk_emoji(risk)} {risk_label(risk)} |"
        )

    lines.append("")
    return "\n".join(lines)


# ─── 通用辅助函数 ──────────────────────────────────────────────────

def _add_risk_analysis(lines: list, instances: list, product_name: str, detail_fn):
    """添加风险实例的详细分析。"""
    risk_instances = [i for i in instances if i.get("risk_level") in ("warning", "critical")]
    if not risk_instances:
        return

    lines.append(f"**{product_name}风险分析:**\n")
    for inst in risk_instances:
        risk = inst.get("risk_level", "")
        inst_id = inst.get("instance_id", "")
        inst_name = inst.get("instance_name", "")
        label = f"{inst_id}"
        if inst_name:
            label += f" ({inst_name})"
        detail = detail_fn(inst)
        lines.append(f"- {risk_emoji(risk)} **{label}** [{inst.get('region', '')}]: {detail}")
    lines.append("")


def generate_recommendations(all_data: dict) -> list:
    """生成扩容建议列表。"""
    recommendations = []

    type_configs = {
        "eip": {"name": "EIP", "check": _check_eip_rec},
        "cbwp": {"name": "共享带宽包", "check": _check_cbwp_rec},
        "nat": {"name": "NAT网关", "check": _check_nat_rec},
        "cen": {"name": "云企业网", "check": _check_cen_rec},
        "physconn": {"name": "物理专线", "check": _check_physconn_rec},
        "vbr": {"name": "VBR", "check": _check_vbr_rec},
        "ga": {"name": "全球加速", "check": _check_ga_rec},
        "clb": {"name": "CLB", "check": _check_clb_rec},
        "alb": {"name": "ALB", "check": _check_alb_rec},
    }

    for key, config in type_configs.items():
        data = all_data.get(key, {})
        for inst in data.get("instances", []):
            risk = inst.get("risk_level", "ok")
            if risk not in ("warning", "critical"):
                continue
            rec = config["check"](inst, config["name"])
            if rec:
                recommendations.append(rec)

    priority_order = {"critical": 0, "warning": 1}
    recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "warning"), 2))
    return recommendations


def _make_rec(inst, product_type, reason, suggestion):
    inst_id = inst.get("instance_id", "")
    inst_name = inst.get("instance_name", "")
    label = f"{inst_id} ({inst_name})" if inst_name else inst_id
    return {
        "priority": inst.get("risk_level", "warning"),
        "instance": label,
        "region": inst.get("region", ""),
        "type": product_type,
        "reason": reason,
        "suggestion": suggestion,
    }


def _check_eip_rec(inst, name):
    m = inst.get("metrics", {})
    bw = inst.get("bandwidth", 0)
    tx = m.get("tx_peak_mbps", 0)
    rx = m.get("rx_peak_mbps", 0)
    tx_avg = m.get("tx_avg_mbps", 0)
    tx_pct = m.get("tx_peak_pct", 0)
    rx_pct = m.get("rx_peak_pct", 0)
    if m.get("has_drops"):
        out_drop = m.get("out_drop_max_pps", 0)
        in_drop = m.get("in_drop_max_pps", 0)
        return _make_rec(inst, name,
                         f"存在限速丢包（出方向丢包峰值 {out_drop}pps，入方向丢包峰值 {in_drop}pps），"
                         f"出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，带宽上限 {bw}Mbps，"
                         f"出方向利用率 {tx_pct}%，出方向均值 {tx_avg}Mbps",
                         f"建议立即升级 EIP 带宽上限（当前 {bw}Mbps，建议至少 {max(bw, int(tx * 1.3))}Mbps）")
    peak_pct = max(tx_pct, rx_pct)
    if peak_pct >= 70:
        return _make_rec(inst, name,
                         f"带宽利用率峰值 {peak_pct}%（出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，"
                         f"带宽上限 {bw}Mbps，出方向均值 {tx_avg}Mbps）",
                         f"建议近期扩容 EIP 带宽（当前 {bw}Mbps，建议 {max(bw, int(tx * 1.3))}Mbps）")
    return None


def _check_cbwp_rec(inst, name):
    m = inst.get("metrics", {})
    bw = inst.get("bandwidth_limit", 0)
    tx = m.get("tx_peak_mbps", 0)
    rx = m.get("rx_peak_mbps", 0)
    tx_pct = m.get("tx_peak_pct", 0)
    if m.get("has_ratelimit_drops"):
        drop_pps = m.get("drop_max_pps", 0)
        return _make_rec(inst, name,
                         f"存在限速丢包（丢包峰值 {drop_pps}pps），出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，"
                         f"带宽上限 {bw}Mbps，出方向利用率 {tx_pct}%",
                         f"建议立即扩容带宽上限（当前 {bw}Mbps，建议至少 {max(bw, int(tx * 1.3))}Mbps）")
    if tx_pct >= 70:
        return _make_rec(inst, name,
                         f"出方向利用率峰值 {tx_pct}%（出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，带宽上限 {bw}Mbps）",
                         f"建议近期扩容带宽上限（当前 {bw}Mbps，建议 {max(bw, int(tx * 1.3))}Mbps）")
    return None


def _check_nat_rec(inst, name):
    m = inst.get("metrics", {})
    reasons = []
    if m.get("has_session_drop"):
        drop_pps = m.get("session_drop_max_pps", 0)
        snat_peak = m.get("snat_connections_peak", 0)
        snat_limit = m.get("snat_limit", 0)
        reasons.append(
            f"连接丢包（丢包峰值 {drop_pps}pps，SNAT并发峰值 {snat_peak:,}"
            + (f"，规格上限 {snat_limit:,}" if snat_limit else "") + "）"
        )
    if m.get("snat_pct", 0) >= 70:
        snat_peak = m.get("snat_connections_peak", 0)
        snat_limit = m.get("snat_limit", 0)
        reasons.append(
            f"SNAT连接数利用率 {m.get('snat_pct', 0)}%（峰值 {snat_peak:,}"
            + (f"，上限 {snat_limit:,}" if snat_limit else "") + "）"
        )
    if m.get("bw_pct", 0) >= 70:
        tx = m.get("tx_peak_mbps", 0)
        reasons.append(f"带宽利用率 {m.get('bw_pct', 0)}%（出方向峰值 {tx}Mbps）")
    if reasons:
        spec = inst.get("spec", "")
        suggestion = f"建议升级 NAT 网关规格" + (f"（当前规格: {spec}）" if spec else "")
        return _make_rec(inst, name, "；".join(reasons), suggestion)
    return None


def _check_cen_rec(inst, name):
    m = inst.get("metrics", {})
    pct = m.get("peak_utilization_pct", 0)
    if pct >= 70:
        tx = m.get("tx_peak_mbps", 0)
        rx = m.get("rx_peak_mbps", 0)
        return _make_rec(inst, name,
                         f"跨域带宽利用率峰值 {pct}%（出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps）",
                         "建议扩容 CEN 带宽包")
    return None


def _check_physconn_rec(inst, name):
    reasons = []
    if inst.get("status", "") != "Enabled":
        reasons.append(f"专线状态异常: {inst.get('status', '')}（正常应为 Enabled）")
    if inst.get("business_status", "") != "Normal":
        reasons.append(f"业务状态异常: {inst.get('business_status', '')}（正常应为 Normal）")
    if reasons:
        bw = inst.get("bandwidth", "")
        if bw:
            reasons.append(f"专线带宽: {bw}Mbps")
        return _make_rec(inst, name, "；".join(reasons), "建议检查物理专线状态，联系运营商确认")
    return None


def _check_vbr_rec(inst, name):
    m = inst.get("metrics", {})
    reasons = []
    loss_peak = m.get("health_check_loss_peak_pct", 0)
    loss_avg = m.get("health_check_loss_avg_pct", 0)
    lat_peak = m.get("health_check_latency_peak_ms", 0)
    lat_avg = m.get("health_check_latency_avg_ms", 0)
    tx = m.get("tx_peak_mbps", 0)
    rx = m.get("rx_peak_mbps", 0)
    if loss_peak > 1:
        reasons.append(f"健康检查丢包率峰值 {loss_peak}% / 均值 {loss_avg}%")
    if lat_peak > 50:
        reasons.append(f"健康检查延迟峰值 {lat_peak}ms / 均值 {lat_avg}ms")
    if inst.get("status", "").lower() != "active":
        reasons.append(f"VBR 状态异常: {inst.get('status', '')}")
    if reasons:
        if tx > 0 or rx > 0:
            reasons.append(f"带宽: VPC→IDC峰值 {tx}Mbps，IDC→VPC峰值 {rx}Mbps")
        return _make_rec(inst, name, "；".join(reasons), "建议检查物理链路质量和 VBR 配置")
    return None


def _check_ga_rec(inst, name):
    m = inst.get("metrics", {})
    pct = m.get("peak_utilization_pct", 0)
    if pct >= 70:
        bw = inst.get("bandwidth", 0)
        tx = m.get("tx_peak_mbps", 0)
        rx = m.get("rx_peak_mbps", 0)
        return _make_rec(inst, name,
                         f"带宽利用率峰值 {pct}%（出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，带宽上限 {bw}Mbps）",
                         f"建议扩容 GA 实例带宽（当前 {bw}Mbps）")
    return None


def _check_clb_rec(inst, name):
    m = inst.get("metrics", {})
    reasons = []
    if m.get("has_drops"):
        drop_tx = m.get("drop_tx_max_pps", 0)
        drop_rx = m.get("drop_rx_max_pps", 0)
        active = m.get("active_conn_peak", 0)
        qps = m.get("qps_peak", 0)
        reasons.append(
            f"存在丢包（出方向丢包峰值 {drop_tx}pps / 入方向丢包峰值 {drop_rx}pps），"
            f"活跃连接峰值 {int(active):,}，QPS峰值 {int(qps):,}"
        )
    if reasons:
        return _make_rec(inst, name, "；".join(reasons), "建议升级 CLB 规格或检查后端服务")
    return None


def _check_alb_rec(inst, name):
    m = inst.get("metrics", {})
    reasons = []

    # 运行状态异常（非 Active/Provisioning）
    alb_status = inst.get("status", "")
    if alb_status and alb_status not in ("Active", "Provisioning"):
        reasons.append(f"运行状态异常: {alb_status}")

    # 业务状态异常（残留锁定、欠费锁定等）
    biz_status = inst.get("business_status", "")
    if biz_status and biz_status not in ("Normal", ""):
        reasons.append(f"业务状态异常: {biz_status}（可能为欠费锁定或残留锁定，需在控制台确认并处理）")

    # 5XX 错误率
    error_pct = m.get("error_5xx_pct", 0)
    http5xx = m.get("http_5xx_peak", 0)
    http2xx = m.get("http_2xx_peak", 0)
    http4xx = m.get("http_4xx_peak", 0)
    qps_peak = m.get("qps_peak", 0)
    qps_avg = m.get("qps_avg", 0)
    active_conn = m.get("active_conn_peak", 0)

    if error_pct > 1 and http5xx >= 1:
        reasons.append(
            f"5XX错误率 {error_pct}%（5XX峰值 {http5xx:.1f}个/秒，2XX峰值 {http2xx:.1f}个/秒，"
            f"4XX峰值 {http4xx:.1f}个/秒），QPS峰值 {int(qps_peak)}，后端服务存在异常"
        )

    if reasons:
        suggestion = "建议排查后端服务健康状况" if error_pct > 1 else "建议在控制台检查实例状态并处理"
        if biz_status and biz_status not in ("Normal", ""):
            suggestion = "建议在控制台检查并处理实例异常状态（如释放残留锁定资源或续费）"
        return _make_rec(inst, name, "；".join(reasons), suggestion)
    return None



# ─── 图表检测与嵌入 ──────────────────────────────────────────────────

CHART_PREFIX_MAP = {
    "eip": "eip_", "cbwp": "cbwp_", "nat": "nat_", "cen": "cen_",
    "vbr": "vbr_", "clb": "clb_", "alb": "alb_", "nlb": "nlb_", "ga": "ga_",
}

CHART_TYPE_LABELS = {
    "bandwidth": "带宽监控曲线", "drop": "限速丢包曲线", "utilization": "利用率曲线",
    "snat": "SNAT连接数曲线", "traffic": "流量监控曲线", "connection": "连接数曲线",
    "qps": "QPS曲线", "http": "HTTP状态码分布", "latency": "健康检查延迟曲线",
    "lossrate": "健康检查丢包率曲线", "flow": "活跃连接数曲线",
}


def _find_product_charts(charts_dir: str, product_key: str) -> dict:
    """扫描 charts_dir 找到指定产品的所有图表文件。
    返回: {instance_id: [(chart_type, filepath, filename), ...]}
    """
    if not charts_dir or not os.path.isdir(charts_dir):
        return {}
    prefix = CHART_PREFIX_MAP.get(product_key, "")
    if not prefix:
        return {}

    result = {}
    for fname in sorted(os.listdir(charts_dir)):
        if not fname.endswith(".png") or not fname.startswith(prefix):
            continue
        body = fname[len(prefix):-4]  # remove prefix and .png
        parts = body.rsplit("_", 1)
        if len(parts) == 2:
            inst_id = parts[0]
            chart_type = parts[1]
        else:
            inst_id = body
            chart_type = "default"

        filepath = os.path.join(charts_dir, fname)
        if inst_id not in result:
            result[inst_id] = []
        result[inst_id].append((chart_type, filepath, fname))

    return result


def _chart_brief_analysis(product_key: str, chart_type: str, inst: dict) -> str:
    """为单张监控曲线图生成简要分析（1-2句话）。"""
    m = inst.get("metrics", {})

    if product_key == "eip":
        bw = inst.get("bandwidth", 0)
        if chart_type == "bandwidth":
            tx = m.get("tx_peak_mbps", 0)
            rx = m.get("rx_peak_mbps", 0)
            pct = m.get("tx_peak_pct", 0)
            if pct >= 90:
                return (f"出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，带宽上限 {bw}Mbps，"
                        f"出方向利用率 {pct}% 已接近上限，建议立即扩容。")
            elif pct >= 70:
                return (f"出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，带宽上限 {bw}Mbps，"
                        f"出方向利用率 {pct}%，处于告警水位，建议关注。")
            elif tx == 0 and rx == 0:
                return f"巡检期间无出入方向流量，带宽上限 {bw}Mbps，可能未绑定实例或业务无流量。"
            else:
                return (f"出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，带宽上限 {bw}Mbps，"
                        f"利用率 {pct}%，带宽余量充足。")
        elif chart_type == "drop":
            if m.get("has_drops"):
                out_drop = m.get("out_drop_max_pps", 0)
                in_drop = m.get("in_drop_max_pps", 0)
                return (f"检测到限速丢包（出方向丢包峰值 {out_drop}pps，入方向丢包峰值 {in_drop}pps），"
                        f"带宽上限 {bw}Mbps，已有流量被丢弃，建议立即扩容带宽。")
            return "巡检期间无限速丢包，带宽使用正常。"

    elif product_key == "cbwp":
        bw = inst.get("bandwidth_limit", 0)
        if chart_type == "bandwidth":
            tx = m.get("tx_peak_mbps", 0)
            rx = m.get("rx_peak_mbps", 0)
            pct = m.get("tx_peak_pct", 0)
            return (f"出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，带宽上限 {bw}Mbps，"
                    f"利用率 {pct}%。" + ("带宽余量充足。" if pct < 70 else " 建议关注。"))
        elif chart_type == "utilization":
            pct = m.get("tx_peak_pct", 0)
            return f"出方向利用率峰值 {pct}%。" + ("处于健康水位。" if pct < 70 else " 处于告警水位，建议扩容。")
        elif chart_type == "drop":
            if m.get("has_ratelimit_drops"):
                drop_pps = m.get("drop_max_pps", 0)
                return f"检测到限速丢包（丢包峰值 {drop_pps}pps），带宽包上限 {bw}Mbps，流量已触及上限，建议扩容。"
            return "巡检期间无限速丢包。"

    elif product_key == "nat":
        if chart_type == "bandwidth":
            tx = m.get("tx_peak_mbps", 0)
            rx = m.get("rx_peak_mbps", 0) if "rx_peak_mbps" in m else 0
            pct = m.get("bw_pct", 0)
            if tx == 0 and rx == 0:
                return "巡检期间无出入方向流量，NAT网关可能暂未使用。"
            return (f"出方向峰值 {tx}Mbps，入方向峰值 {rx}Mbps，"
                    f"带宽利用率 {pct}%。" + ("" if pct < 70 else " 建议关注带宽容量。"))
        elif chart_type == "snat":
            peak = m.get("snat_connections_peak", 0)
            pct = m.get("snat_pct", 0)
            limit = m.get("snat_limit", 0)
            if peak == 0:
                return "巡检期间 SNAT 并发连接数为 0，可能暂无出公网流量。"
            return (f"SNAT 并发连接数峰值 {peak}，"
                    + (f"上限 {limit}，利用率 {pct}%。" if limit else f"利用率 {pct}%。")
                    + ("" if pct < 70 else " 接近规格上限，建议升级规格。"))
        elif chart_type == "drop":
            if m.get("has_session_drop"):
                drop_pps = m.get("session_drop_max_pps", 0)
                snat_peak = m.get("snat_connections_peak", 0)
                return (f"检测到并发连接限速丢包（丢包峰值 {drop_pps}pps，SNAT并发峰值 {snat_peak:,}），"
                        f"NAT网关规格已成瓶颈，建议升级。")
            return "巡检期间无并发连接限速丢包。"

    elif product_key == "cen":
        if chart_type == "bandwidth":
            tx = m.get("tx_peak_mbps", 0)
            rx = m.get("rx_peak_mbps", 0)
            pct = m.get("peak_utilization_pct", 0)
            if tx == 0 and rx == 0:
                return "巡检期间无跨域流量。"
            return (f"跨域出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，"
                    f"利用率 {pct}%。" + ("带宽余量充足。" if pct < 70 else " 建议关注跨域带宽容量。"))

    elif product_key == "vbr":
        if chart_type == "bandwidth":
            tx = m.get("tx_peak_mbps", 0)
            rx = m.get("rx_peak_mbps", 0)
            return f"VPC→IDC 方向峰值 {tx}Mbps，IDC→VPC 方向峰值 {rx}Mbps。"
        elif chart_type == "latency":
            peak = m.get("health_check_latency_peak_ms", 0)
            avg = m.get("health_check_latency_avg_ms", 0)
            if peak > 100:
                return f"健康检查延迟峰值 {peak}ms / 均值 {avg}ms，延迟严重偏高，请检查物理链路。"
            elif peak > 50:
                return f"健康检查延迟峰值 {peak}ms / 均值 {avg}ms，延迟偏高，建议关注链路质量。"
            return f"健康检查延迟峰值 {peak}ms / 均值 {avg}ms，链路质量正常。"
        elif chart_type == "lossrate":
            peak = m.get("health_check_loss_peak_pct", 0)
            avg = m.get("health_check_loss_avg_pct", 0)
            if peak > 5:
                return f"健康检查丢包率峰值 {peak}% / 均值 {avg}%，丢包严重，请检查物理链路。"
            elif peak > 1:
                return f"健康检查丢包率峰值 {peak}% / 均值 {avg}%，存在轻微丢包，建议关注。"
            return f"健康检查丢包率峰值 {peak}% / 均值 {avg}%，链路质量正常。"

    elif product_key == "ga":
        if chart_type == "bandwidth":
            tx = m.get("tx_peak_mbps", 0)
            rx = m.get("rx_peak_mbps", 0)
            pct = m.get("peak_utilization_pct", 0)
            bw = inst.get("bandwidth", 0)
            if tx == 0 and rx == 0:
                return f"巡检期间无加速流量，带宽上限 {bw}Mbps。"
            return (f"出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps，带宽上限 {bw}Mbps，"
                    f"利用率 {pct}%。")

    elif product_key == "clb":
        if chart_type == "connection":
            active = m.get("active_conn_peak", 0)
            return f"活跃连接数峰值 {int(active):,}。" + ("连接数极低，可能暂无业务流量。" if active == 0 else "")
        elif chart_type == "traffic":
            tx = m.get("tx_peak_mbps", 0)
            qps = m.get("qps_peak", 0)
            active = m.get("active_conn_peak", 0)
            if m.get("has_drops"):
                drop_tx = m.get("drop_tx_max_pps", 0)
                drop_rx = m.get("drop_rx_max_pps", 0)
                return (f"出方向峰值 {tx}Mbps，QPS峰值 {int(qps):,}，活跃连接峰值 {int(active):,}，"
                        f"检测到丢包（出{drop_tx}pps/入{drop_rx}pps），建议关注。")
            return f"出方向峰值 {tx}Mbps，QPS峰值 {int(qps):,}。" + ("流量极低。" if tx == 0 and qps == 0 else "")
        elif chart_type == "qps":
            qps = m.get("qps_peak", 0)
            return f"QPS峰值 {qps}。" + ("暂无请求流量。" if qps == 0 else "")

    elif product_key == "alb":
        # 状态异常前缀
        status_note = ""
        alb_status = inst.get("status", "")
        biz_status = inst.get("business_status", "")
        if alb_status and alb_status not in ("Active", "Provisioning"):
            status_note = f"**注意: 实例运行状态异常({alb_status})。** "
        if biz_status and biz_status not in ("Normal", ""):
            status_note += f"**业务状态异常({biz_status})，可能为残留锁定或欠费锁定。** "

        if chart_type == "http":
            h2 = m.get("http_2xx_peak", 0)
            h4 = m.get("http_4xx_peak", 0)
            h5 = m.get("http_5xx_peak", 0)
            err = m.get("error_5xx_pct", 0)
            active_conn = m.get("active_conn_peak", 0)
            if h2 == 0 and h4 == 0 and h5 == 0:
                return status_note + "巡检期间无 HTTP 请求，可能暂无业务流量。"
            parts = [f"2XX峰值 {h2:.1f}个/秒，4XX峰值 {h4:.1f}个/秒，5XX峰值 {h5:.1f}个/秒，活跃连接峰值 {int(active_conn):,}"]
            if err > 5:
                parts.append(f"5XX错误率 {err}%，服务端错误严重，建议立即排查后端健康状况")
            elif err > 1:
                parts.append(f"5XX错误率 {err}%，后端服务存在异常，建议排查")
            else:
                parts.append(f"5XX错误率 {err}%，后端服务正常")
            return status_note + "。".join(parts) + "。"
        elif chart_type == "qps":
            qps = m.get("qps_peak", 0)
            avg = m.get("qps_avg", 0)
            if qps == 0:
                return status_note + "巡检期间 QPS 为 0，可能暂无业务流量。"
            return status_note + f"QPS峰值 {int(qps):,} / 均值 {int(avg):,}。"

    elif product_key == "nlb":
        if chart_type == "bandwidth":
            tx = m.get("tx_peak_mbps", 0)
            rx = m.get("rx_peak_mbps", 0)
            if tx == 0 and rx == 0:
                return "巡检期间无流量，NLB 可能暂未使用。"
            return f"出方向峰值 {tx}Mbps / 入方向峰值 {rx}Mbps。"
        elif chart_type == "flow":
            active = m.get("active_flow_peak", 0)
            new = m.get("new_flow_peak", 0)
            if active == 0 and new == 0:
                return "巡检期间无活跃连接，NLB 可能暂未使用。"
            return f"活跃连接峰值 {active}，新建连接峰值 {new}。"

    return ""


def _format_chart_section(charts_dir: str, product_key: str,
                          instances: list, report_dir: str = None,
                          image_url_map: dict = None) -> list:
    """生成产品图表引用段落。

    Args:
        image_url_map: 可选，图片文件名到云端URL的映射（如钉钉 OSS resourceUrl），
                       格式为 {"eip_xxx_bandwidth.png": "https://..."}。
                       提供时使用云端URL替代本地路径。
    """
    product_charts = _find_product_charts(charts_dir, product_key)
    if not product_charts:
        return []

    lines = []
    lines.append("#### 监控曲线图\n")

    for inst in instances:
        inst_id = inst.get("instance_id", "")
        inst_name = inst.get("instance_name", "")
        charts = product_charts.get(inst_id, [])

        label = inst_id
        if inst_name:
            label += f" ({inst_name})"

        if not charts:
            lines.append(f"> {label}: 暂无监控曲线数据（可能未绑定实例、无流量或新创建）\n")
            continue

        for chart_type, filepath, fname in charts:
            type_label = CHART_TYPE_LABELS.get(chart_type, chart_type)
            # 优先使用云端 URL 映射（用于钉钉文档等场景）
            if image_url_map and fname in image_url_map:
                img_ref = image_url_map[fname]
            elif report_dir:
                img_ref = os.path.relpath(filepath, report_dir)
            else:
                img_ref = filepath
            lines.append(f"**{label} — {type_label}:**\n")
            lines.append(f"![{type_label} - {inst_id}]({img_ref})\n")
            # 图表简要分析
            analysis = _chart_brief_analysis(product_key, chart_type, inst)
            if analysis:
                lines.append(f"> {analysis}\n")

    return lines


# ─── 各产品深度分析 ──────────────────────────────────────────────────

def _deep_analysis_eip(data: dict) -> list:
    """EIP 深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### EIP 带宽使用深度分析\n")

    n = len(instances)
    bws = [i.get("bandwidth", 0) for i in instances]
    tx_pcts = [i.get("metrics", {}).get("tx_peak_pct", 0) for i in instances]
    rx_pcts = [i.get("metrics", {}).get("rx_peak_pct", 0) for i in instances]
    max_tx_pct = max(tx_pcts) if tx_pcts else 0
    avg_tx_pct = round(sum(tx_pcts) / len(tx_pcts), 1) if tx_pcts else 0
    drop_eips = [i for i in instances if i.get("metrics", {}).get("has_drops")]
    min_bw = min(bws) if bws else 0
    max_bw = max(bws) if bws else 0

    lines.append(
        f"本次巡检共发现 **{n}** 个弹性公网IP实例，带宽规格从 {min_bw}Mbps "
        f"到 {max_bw}Mbps 不等。整体来看，出方向带宽利用率最高为 {max_tx_pct}%，"
        f"平均利用率为 {avg_tx_pct}%。\n"
    )

    lines.append(
        "**出方向带宽分析:** 出方向带宽（从阿里云到互联网）是绝大多数业务场景的瓶颈所在，"
        "直接影响用户下载速度、API 响应速度和页面加载时间。"
    )
    if max_tx_pct >= 90:
        lines.append(
            f"当前有实例出方向利用率已达 {max_tx_pct}%，已接近带宽上限，"
            "任何流量波动都可能导致限速丢包，严重影响用户体验。**建议立即扩容。**\n"
        )
    elif max_tx_pct >= 70:
        lines.append(
            f"当前最高出方向利用率为 {max_tx_pct}%，处于告警水位。"
            "虽然暂未触发限速，但在流量高峰期或突发场景下存在限速风险。"
            "**建议在下一个业务周期前评估扩容。**\n"
        )
    else:
        lines.append(
            f"当前最高出方向利用率为 {max_tx_pct}%，整体处于健康水位，带宽资源充裕。\n"
        )

    max_rx_pct = max(rx_pcts) if rx_pcts else 0
    lines.append(
        f"**入方向带宽分析:** 入方向带宽（从互联网到阿里云）整体利用率最高为 {max_rx_pct}%。"
        "入方向带宽反映了用户上传、API 请求体、文件上传等场景的带宽需求。"
    )
    if max_rx_pct < 50:
        lines.append("入方向带宽使用较低，资源充裕。\n")
    else:
        lines.append("入方向带宽使用较高，如果业务涉及大量文件上传或数据同步，请关注入方向容量。\n")

    spike_eips = []
    for i in instances:
        m = i.get("metrics", {})
        peak = m.get("tx_peak_mbps", 0)
        avg = m.get("tx_avg_mbps", 0)
        if avg > 0 and peak / avg > 3:
            spike_eips.append((i, round(peak / avg, 1)))

    if spike_eips:
        lines.append(
            f"**流量模式分析:** 发现 {len(spike_eips)} 个 EIP 存在明显的流量尖刺特征"
            "（峰值/均值比超过3倍），说明流量存在明显的潮汐效应或突发场景。建议："
        )
        lines.append("- 评估是否适合使用共享带宽包，通过多 EIP 错峰复用降低成本")
        lines.append("- 考虑配置弹性带宽（增强型 EIP），自动适应流量波动")
        lines.append("- 分析流量高峰时段，评估是否可通过 CDN 分流降低源站带宽压力\n")
    else:
        lines.append(
            "**流量模式分析:** 各 EIP 的流量峰均比较为平稳，未发现明显的流量尖刺，"
            "说明业务流量分布较为均匀。\n"
        )

    if drop_eips:
        lines.append(
            f"**限速丢包分析:** 发现 **{len(drop_eips)}** 个 EIP 存在限速丢包，"
            "这意味着实际流量已超过购买带宽上限，超出部分的数据包被丢弃。"
            "限速丢包会导致 TCP 重传增加、延迟上升、用户感知到的下载/上传速度下降。"
            "**这是需要最优先处理的问题，建议立即升级相关 EIP 的带宽上限。**\n"
        )
        for eip in drop_eips:
            m = eip.get("metrics", {})
            lines.append(
                f"- `{eip.get('instance_id', '')}` (IP: {eip.get('ip_address', '')}): "
                f"出方向丢包峰值 {m.get('out_drop_max_pps', 0)} pps，"
                f"入方向丢包峰值 {m.get('in_drop_max_pps', 0)} pps"
            )
        lines.append("")
    else:
        lines.append("**限速丢包分析:** 巡检期间所有 EIP 均未出现限速丢包，带宽余量充足。\n")

    low_util_eips = [i for i in instances if max(i.get("metrics", {}).get("tx_peak_pct", 0),
                                                  i.get("metrics", {}).get("rx_peak_pct", 0)) < 20]
    if low_util_eips and len(low_util_eips) >= 2:
        lines.append(
            f"**成本优化提示:** 发现 {len(low_util_eips)} 个 EIP 的带宽利用率低于 20%，"
            "可能存在带宽资源浪费。建议评估是否可以降低带宽规格或合并到共享带宽包中。\n"
        )

    return lines


def _deep_analysis_cbwp(data: dict) -> list:
    """共享带宽包深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### 共享带宽包使用深度分析\n")

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 个共享带宽包实例。共享带宽包允许多个 EIP "
        "共享同一带宽池，通过不同 EIP 之间的流量错峰复用，有效提升带宽利用率并降低成本。\n"
    )

    for inst in instances:
        m = inst.get("metrics", {})
        bw = inst.get("bandwidth_limit", 0)
        tx_pct = m.get("tx_peak_pct", 0)
        tx_peak = m.get("tx_peak_mbps", 0)
        tx_avg = m.get("tx_avg_mbps", 0)

        lines.append(
            f"**{inst.get('instance_id', '')}** ({inst.get('instance_name', '') or '未命名'}): "
            f"带宽上限 {bw}Mbps，出方向峰值 {tx_peak}Mbps（利用率 {tx_pct}%），"
            f"出方向均值 {tx_avg}Mbps。"
        )
        if tx_pct >= 90:
            lines.append(
                "利用率接近上限，存在限速风险，建议立即扩容或迁移部分 EIP 到新带宽包。"
            )
        elif tx_pct >= 70:
            lines.append("利用率较高，建议关注趋势并提前规划扩容。")
        elif tx_pct < 30 and bw > 100:
            lines.append("利用率较低，可考虑降低带宽上限以优化成本。")
        if m.get("has_ratelimit_drops"):
            lines.append(
                f"**严重告警:** 出现限速丢包（峰值 {m.get('drop_max_pps', 0)} pps），需立即扩容。"
            )
        lines.append("")

    return lines


def _deep_analysis_nat(data: dict) -> list:
    """NAT网关深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### NAT 网关使用深度分析\n")

    nat_spec_snat = {"Small": 100000, "Medium": 500000, "Large": 2000000, "XLarge.1": 5000000}
    spec_upgrade_path = {"Small": "Medium", "Medium": "Large", "Large": "XLarge.1"}

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 个 NAT 网关实例。NAT 网关是 VPC 访问公网的核心组件，"
        "提供 SNAT 和 DNAT 能力。NAT 网关性能受规格限制，包括最大 SNAT 并发连接数和最大带宽。\n"
    )

    for inst in instances:
        m = inst.get("metrics", {})
        spec = inst.get("spec", "未知")
        snat_limit = nat_spec_snat.get(spec, 0)
        snat_peak = int(m.get("snat_connections_peak", 0))
        snat_pct = m.get("snat_pct", 0)
        bw_pct = m.get("bw_pct", 0)

        lines.append(
            f"**{inst.get('instance_id', '')}** ({inst.get('instance_name', '') or '未命名'}) "
            f"— 规格: {spec}:"
        )
        lines.append(
            f"- SNAT 并发连接数: 峰值 **{snat_peak:,}** / 上限 {snat_limit:,} "
            f"(利用率 **{snat_pct}%**)"
        )
        lines.append(f"- 带宽利用率: **{bw_pct}%**")

        if m.get("has_session_drop"):
            next_spec = spec_upgrade_path.get(spec, "更高规格")
            lines.append(
                f"- **严重:** 检测到连接丢包 ({m.get('session_drop_max_pps', 0)} pps)！"
                "SNAT 连接数已达规格上限，新连接被拒绝，直接影响业务。"
                f"**建议立即升级到 {next_spec} 规格。**"
            )
        elif snat_pct >= 90:
            lines.append(
                "- SNAT 连接数利用率已达 90% 以上，建议评估升级规格并优化连接复用。"
            )
        elif snat_pct >= 70:
            lines.append("- SNAT 连接数利用率较高，建议提前规划规格升级。")
        lines.append("")

    drop_nats = [i for i in instances if i.get("metrics", {}).get("has_session_drop")]
    if drop_nats:
        lines.append(
            f"**关键风险提示:** {len(drop_nats)} 个 NAT 网关出现连接丢包，"
            "这会导致 VPC 内 ECS 无法正常访问公网，可能引发服务降级或中断。"
            "建议立即升级规格并优化应用连接池策略。\n"
        )

    return lines


def _deep_analysis_clb(data: dict) -> list:
    """CLB 深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### CLB 使用深度分析\n")

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 个传统型负载均衡（CLB）实例。"
        "CLB 提供四层和七层负载均衡能力，重点关注流量、连接数、QPS 和丢包。\n"
    )

    for inst in instances:
        m = inst.get("metrics", {})
        lines.append(
            f"**{inst.get('instance_id', '')}** ({inst.get('instance_name', '') or '未命名'}) "
            f"[{inst.get('region', '')}]: "
            f"出方向 {m.get('tx_peak_mbps', 0)}Mbps，"
            f"活跃连接 {int(m.get('active_conn_peak', 0)):,}，"
            f"QPS {int(m.get('qps_peak', 0)):,}"
        )
        if m.get("has_drops"):
            lines.append(
                f"- **丢包:** 出{m.get('drop_tx_max_pps', 0)}/入{m.get('drop_rx_max_pps', 0)} pps，"
                "已达规格上限，建议升级 CLB 规格。"
            )
        lines.append("")

    drop_clbs = [i for i in instances if i.get("metrics", {}).get("has_drops")]
    if drop_clbs:
        lines.append(f"**风险提示:** {len(drop_clbs)} 个 CLB 出现丢包，需重点关注。\n")

    return lines


def _deep_analysis_alb(data: dict) -> list:
    """ALB 深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### ALB 使用深度分析\n")

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 个应用型负载均衡（ALB）实例。ALB 专注于七层负载均衡，"
        "重点关注 QPS、HTTP 状态码分布（特别是 5XX 错误率）和连接数。\n"
    )

    for inst in instances:
        m = inst.get("metrics", {})
        qps_peak = m.get("qps_peak", 0)
        qps_avg = m.get("qps_avg", 0)
        http2xx = m.get("http_2xx_peak", 0)
        http4xx = m.get("http_4xx_peak", 0)
        http5xx = m.get("http_5xx_peak", 0)
        err_pct = m.get("error_5xx_pct", 0)

        lines.append(
            f"**{inst.get('instance_id', '')}** ({inst.get('instance_name', '') or '未命名'}) "
            f"[{inst.get('region', '')}]:"
        )
        lines.append(
            f"- QPS: 峰值 **{int(qps_peak):,}** / 均值 {int(qps_avg):,}，"
            f"活跃连接: {int(m.get('active_conn_peak', 0)):,}"
        )

        total_req = http2xx + http4xx + http5xx
        if total_req >= 1:
            pct2xx = round(http2xx / total_req * 100, 1)
            pct4xx = round(http4xx / total_req * 100, 1)
            pct5xx = round(http5xx / total_req * 100, 1)
            lines.append(f"- HTTP 状态码: 2XX {pct2xx}% / 4XX {pct4xx}% / 5XX {pct5xx}%")
            if err_pct > 5:
                lines.append(
                    f"- **严重:** 5XX 错误率 {err_pct}%，后端服务存在问题。建议检查：后端 ECS/Pod 资源、"
                    "应用日志、健康检查配置、数据库连接池。"
                )
            elif err_pct > 1:
                lines.append(f"- **告警:** 5XX 错误率 {err_pct}%，建议排查后端服务。")
            elif pct4xx > 20:
                lines.append(f"- **提示:** 4XX 比例较高 ({pct4xx}%)，可能存在无效请求或路由配置问题。")
        else:
            lines.append("- 请求量极低（<1 QPS），可能暂无流量。")

        if qps_avg > 0 and qps_peak / qps_avg > 5:
            lines.append(
                f"- **流量特征:** 峰均比 {round(qps_peak / qps_avg, 1)}x，"
                "存在流量尖刺，建议配置限流保护。"
            )
        lines.append("")

    err_albs = [i for i in instances if i.get("metrics", {}).get("error_5xx_pct", 0) > 1]
    if err_albs:
        lines.append(
            f"**健康风险:** {len(err_albs)} 个 ALB 的 5XX 错误率超过 1%。排查方向："
        )
        lines.append("- 后端 ECS/Pod 的 CPU、内存使用率和应用日志")
        lines.append("- 连接池和处理能力是否达到瓶颈")
        lines.append("- 是否存在慢查询或外部依赖超时\n")

    return lines


def _deep_analysis_nlb(data: dict) -> list:
    """NLB 深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### NLB 使用深度分析\n")

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 个网络型负载均衡（NLB）实例。NLB 为全托管弹性四层负载均衡，"
        "无固定上限，性能随流量自动扩展。\n"
    )

    for inst in instances:
        m = inst.get("metrics", {})
        lines.append(
            f"**{inst.get('instance_id', '')}** ({inst.get('instance_name', '') or '未命名'}): "
            f"出 {m.get('tx_peak_mbps', 0)}Mbps / 入 {m.get('rx_peak_mbps', 0)}Mbps，"
            f"活跃连接 {int(m.get('active_flow_peak', 0)):,}，"
            f"新建连接 {int(m.get('new_flow_peak', 0)):,}"
        )
        lines.append("")

    return lines


def _deep_analysis_vbr(data: dict) -> list:
    """VBR 深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### VBR 链路质量深度分析\n")

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 个 VBR 实例。VBR 的健康检查延迟和丢包率"
        "直接反映物理专线链路质量，是混合云网络最关键的监控指标。\n"
    )

    lines.append("**链路质量评估标准:**\n")
    lines.append("| 指标 | 优秀 | 良好 | 告警 | 严重 |")
    lines.append("|------|------|------|------|------|")
    lines.append("| 延迟 | <10ms | <50ms | 50-100ms | >100ms |")
    lines.append("| 丢包率 | 0% | <1% | 1-5% | >5% |")
    lines.append("")

    for inst in instances:
        m = inst.get("metrics", {})
        latency_peak = m.get("health_check_latency_peak_ms", 0)
        latency_avg = m.get("health_check_latency_avg_ms", 0)
        loss_peak = m.get("health_check_loss_peak_pct", 0)

        lines.append(
            f"**{inst.get('instance_id', '')}** — 专线: {inst.get('physical_connection_id', '-')}: "
            f"延迟峰值 **{latency_peak}ms**(均值 {latency_avg}ms)，"
            f"丢包率峰值 **{loss_peak}%**"
        )
        if loss_peak > 5 or latency_peak > 100:
            lines.append("- **严重:** 链路质量劣化，建议立即联系运营商检查。")
        elif loss_peak > 1 or latency_peak > 50:
            lines.append("- **告警:** 链路质量波动，建议密切监控。")
        lines.append("")

    return lines


def _deep_analysis_ga(data: dict) -> list:
    """GA 深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### 全球加速使用深度分析\n")

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 个全球加速实例。"
        "GA 利用阿里云全球骨干网络为跨域业务提供网络加速，超过带宽将触发限速。\n"
    )

    for inst in instances:
        m = inst.get("metrics", {})
        util = m.get("peak_utilization_pct", 0)
        lines.append(
            f"**{inst.get('instance_id', '')}**: "
            f"带宽 {inst.get('bandwidth', 0)}Mbps，利用率 {util}%"
        )
        if util >= 70:
            lines.append("- 利用率较高，建议扩容带宽。")
        lines.append("")

    return lines


def _deep_analysis_cen(data: dict) -> list:
    """CEN 深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### 云企业网使用深度分析\n")

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 个 CEN 实例。CEN 用于跨地域/跨账号 VPC 互通，"
        "跨地域互通需购买带宽包。\n"
    )

    for inst in instances:
        bw_packages = inst.get("bandwidth_packages", [])
        util = inst.get("metrics", {}).get("peak_utilization_pct", 0)
        lines.append(
            f"**{inst.get('instance_id', '')}**: "
            f"带宽包 {len(bw_packages)} 个，跨域利用率 {util}%"
        )
        if bw_packages and util >= 70:
            lines.append("- 跨域带宽利用率较高，建议扩容带宽包。")
        elif not bw_packages:
            lines.append("- 未配置带宽包，仅支持同地域互通。")
        lines.append("")

    return lines


def _deep_analysis_physconn(data: dict) -> list:
    """物理专线深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### 物理专线状态深度分析\n")

    lines.append(
        f"本次巡检共发现 **{len(instances)}** 条物理专线。物理专线本身无云监控流量指标，"
        "流量监控通过关联 VBR 查看。\n"
    )

    abnormal = [i for i in instances if i.get("status", "") != "Enabled" or
                i.get("business_status", "") != "Normal"]
    if abnormal:
        for inst in abnormal:
            lines.append(
                f"- **异常:** `{inst.get('instance_id', '')}` 状态={inst.get('status', '-')}，"
                f"业务状态={inst.get('business_status', '-')}，建议联系运营商确认。"
            )
        lines.append("")
    else:
        lines.append("所有物理专线运行正常。\n")

    lines.append(
        "**冗余性建议:** 关键业务建议配置双条专线实现链路冗余，"
        "通过两条专线+两个 VBR+BGP 实现自动主备切换。\n"
    )
    return lines


def _deep_analysis_tr(data: dict) -> list:
    """TR 深度分析。"""
    instances = data.get("instances", [])
    if not instances:
        return []
    lines = []
    lines.append("#### 转发路由器连接深度分析\n")

    total_vpc = 0
    total_vbr = 0
    abnormal_atts = []
    for inst in instances:
        vpcs = inst.get("vpc_attachments", [])
        vbrs = inst.get("vbr_attachments", [])
        total_vpc += len(vpcs)
        total_vbr += len(vbrs)
        for a in vpcs:
            if a.get("status", "") not in ("Attached", ""):
                abnormal_atts.append((inst.get("instance_id", ""), "VPC", a))
        for a in vbrs:
            if a.get("status", "") not in ("Attached", ""):
                abnormal_atts.append((inst.get("instance_id", ""), "VBR", a))

    lines.append(
        f"共 {len(instances)} 个 TR，{total_vpc} 个 VPC 连接，{total_vbr} 个 VBR 连接。"
    )
    if abnormal_atts:
        lines.append(f"\n**异常连接 ({len(abnormal_atts)} 个):**\n")
        for tr_id, att_type, att in abnormal_atts:
            lines.append(
                f"- TR `{tr_id}` {att_type} 连接 `{att.get('attachment_id', '')}` "
                f"状态: {att.get('status', '-')}。"
            )
        lines.append("")
    else:
        lines.append("所有连接状态正常。\n")

    return lines


_DEEP_ANALYSIS_MAP = {
    "eip": _deep_analysis_eip, "cbwp": _deep_analysis_cbwp,
    "nat": _deep_analysis_nat, "cen": _deep_analysis_cen,
    "tr": _deep_analysis_tr, "physconn": _deep_analysis_physconn,
    "vbr": _deep_analysis_vbr, "ga": _deep_analysis_ga,
    "clb": _deep_analysis_clb, "alb": _deep_analysis_alb,
    "nlb": _deep_analysis_nlb,
}


# ─── 执行摘要与健康评分 ──────────────────────────────────────────────

def _calculate_health_score(total_all: dict) -> int:
    """计算整体网络健康评分（满分100）。
    - 每个 critical 实例扣 15 分
    - 每个 warning 实例扣 5 分
    - 每个 error 实例扣 3 分
    - 最低 0 分
    """
    total = total_all.get("total", 0)
    if total == 0:
        return 100
    deduction = (total_all.get("critical", 0) * 15
                 + total_all.get("warning", 0) * 5
                 + total_all.get("error", 0) * 3)
    return max(0, 100 - deduction)


def _health_grade(score: int) -> str:
    """健康等级。"""
    if score >= 90:
        return "优秀"
    elif score >= 75:
        return "良好"
    elif score >= 60:
        return "一般"
    else:
        return "较差"


def _generate_executive_summary(total_all: dict, attention_instances: list,
                                recommendations: list, all_regions: set,
                                days: int, all_data: dict, type_names: dict) -> list:
    """生成执行摘要。"""
    lines = []
    lines.append("## 执行摘要\n")

    score = _calculate_health_score(total_all)
    grade = _health_grade(score)

    lines.append(f"**网络健康评分: {score}/100 ({grade})**\n")

    # 总体结论
    total = total_all.get("total", 0)
    ok = total_all.get("ok", 0)
    warning = total_all.get("warning", 0)
    critical = total_all.get("critical", 0)
    error = total_all.get("error", 0)

    lines.append(f"本次巡检覆盖 **{len(all_regions)}** 个地域、**11** 类网络产品，共发现 **{total}** 个实例。"
                 f"其中 {ok} 个正常，{warning} 个告警，{critical} 个严重，{error} 个异常。\n")

    if critical > 0:
        lines.append(f"> **紧急**: 发现 **{critical}** 个严重风险实例，建议立即排查处理。\n")
    elif warning > 0:
        lines.append(f"> **提示**: 发现 **{warning}** 个告警实例，建议近期关注并评估扩容。\n")
    else:
        lines.append("> 所有网络资源运行状态良好，暂无紧急事项。\n")

    # 关键发现
    lines.append("**关键发现:**\n")

    findings = []

    # 公网带宽分析
    eip_data = all_data.get("eip", {})
    eip_insts = eip_data.get("instances", [])
    if eip_insts:
        eip_with_drops = [i for i in eip_insts if i.get("metrics", {}).get("has_drops")]
        max_tx = max((i.get("metrics", {}).get("tx_peak_pct", 0) for i in eip_insts), default=0)
        findings.append(
            f"- **公网出口**: {len(eip_insts)} 个 EIP 实例，最高出方向利用率 {max_tx}%"
            + (f"，**{len(eip_with_drops)} 个存在限速丢包**" if eip_with_drops else "，无限速丢包")
        )

    # NAT 网关分析
    nat_data = all_data.get("nat", {})
    nat_insts = nat_data.get("instances", [])
    if nat_insts:
        nat_drops = [i for i in nat_insts if i.get("metrics", {}).get("has_session_drop")]
        max_snat = max((i.get("metrics", {}).get("snat_pct", 0) for i in nat_insts), default=0)
        findings.append(
            f"- **NAT网关**: {len(nat_insts)} 个实例，SNAT连接数最高利用率 {max_snat}%"
            + (f"，**{len(nat_drops)} 个存在连接丢包**" if nat_drops else "")
        )

    # 负载均衡分析
    clb_count = len(all_data.get("clb", {}).get("instances", []))
    alb_count = len(all_data.get("alb", {}).get("instances", []))
    nlb_count = len(all_data.get("nlb", {}).get("instances", []))
    lb_total = clb_count + alb_count + nlb_count
    if lb_total > 0:
        lb_parts = []
        if clb_count > 0:
            lb_parts.append(f"CLB {clb_count} 个")
        if alb_count > 0:
            lb_parts.append(f"ALB {alb_count} 个")
        if nlb_count > 0:
            lb_parts.append(f"NLB {nlb_count} 个")
        findings.append(f"- **负载均衡**: 共 {lb_total} 个实例（{'、'.join(lb_parts)}）")

    # 混合云/专线分析
    physconn_count = len(all_data.get("physconn", {}).get("instances", []))
    vbr_count = len(all_data.get("vbr", {}).get("instances", []))
    if physconn_count > 0 or vbr_count > 0:
        findings.append(f"- **混合云连接**: 物理专线 {physconn_count} 条，VBR {vbr_count} 个")

    # CEN/TR 分析
    cen_count = len(all_data.get("cen", {}).get("instances", []))
    tr_count = len(all_data.get("tr", {}).get("instances", []))
    if cen_count > 0:
        findings.append(f"- **云企业网**: CEN {cen_count} 个，转发路由器(TR) {tr_count} 个")

    # GA 分析
    ga_count = len(all_data.get("ga", {}).get("instances", []))
    if ga_count > 0:
        findings.append(f"- **全球加速**: {ga_count} 个实例")

    if not findings:
        findings.append("- 当前巡检范围内未发现网络产品实例")

    lines.extend(findings)
    lines.append("")

    return lines


def _generate_region_summary(all_data: dict, type_names: dict) -> list:
    """生成地域维度的统计分析。"""
    lines = []
    lines.append("## 地域维度统计\n")

    # 按地域聚合实例数和风险数
    region_stats = {}
    for key, name in type_names.items():
        data = all_data.get(key, {})
        for inst in data.get("instances", []):
            region = inst.get("region", "全局")
            if region not in region_stats:
                region_stats[region] = {"total": 0, "ok": 0, "warning": 0, "critical": 0}
            region_stats[region]["total"] += 1
            risk = inst.get("risk_level", "ok")
            if risk in region_stats[region]:
                region_stats[region][risk] += 1

    if not region_stats:
        lines.append("> 无实例数据。\n")
        return lines

    lines.append("| 地域 | 实例数 | 🟢正常 | 🟡告警 | 🔴严重 | 健康度 |")
    lines.append("|------|-------|-------|-------|-------|--------|")

    for region in sorted(region_stats.keys()):
        s = region_stats[region]
        total = s["total"]
        ok_rate = round(s["ok"] / total * 100) if total > 0 else 100
        lines.append(
            f"| {region} | {total} | {s['ok']} | {s['warning']} | {s['critical']} | {ok_rate}% |"
        )

    lines.append("")
    return lines


def _generate_capacity_planning(all_data: dict) -> list:
    """生成容量规划建议。"""
    lines = []
    lines.append("## 容量规划建议\n")
    lines.append("基于当前巡检数据，以下为各产品的容量规划参考：\n")

    has_content = False

    # EIP 容量
    eip_insts = all_data.get("eip", {}).get("instances", [])
    high_util_eips = [i for i in eip_insts
                      if max(i.get("metrics", {}).get("tx_peak_pct", 0),
                             i.get("metrics", {}).get("rx_peak_pct", 0)) >= 50]
    if high_util_eips:
        has_content = True
        lines.append("### 公网带宽\n")
        for inst in high_util_eips:
            m = inst.get("metrics", {})
            bw = inst.get("bandwidth", 0)
            tx_pct = m.get("tx_peak_pct", 0)
            tx_peak = m.get("tx_peak_mbps", 0)
            # 按峰值 * 1.5 估算建议带宽
            suggested_bw = max(bw, int(tx_peak * 1.5))
            lines.append(
                f"- `{inst.get('instance_id', '')}` ({inst.get('ip_address', '')}) — "
                f"当前带宽 {bw}Mbps，出方向峰值 {tx_peak}Mbps (利用率 {tx_pct}%)"
            )
            if suggested_bw > bw:
                lines.append(f"  - 建议带宽: **{suggested_bw}Mbps** (按峰值1.5倍预留)")
        lines.append("")

    # NAT 容量
    nat_insts = all_data.get("nat", {}).get("instances", [])
    high_util_nats = [i for i in nat_insts if i.get("metrics", {}).get("snat_pct", 0) >= 50]
    if high_util_nats:
        has_content = True
        lines.append("### NAT网关规格\n")
        spec_upgrade = {"Small": "Medium", "Medium": "Large", "Large": "XLarge.1"}
        for inst in high_util_nats:
            m = inst.get("metrics", {})
            spec = inst.get("spec", "-")
            snat_pct = m.get("snat_pct", 0)
            snat_peak = int(m.get("snat_connections_peak", 0))
            next_spec = spec_upgrade.get(spec, "更高规格")
            lines.append(
                f"- `{inst.get('instance_id', '')}` ({inst.get('instance_name', '') or '-'}) — "
                f"规格 {spec}，SNAT连接数峰值 {snat_peak:,} (利用率 {snat_pct}%)"
            )
            if snat_pct >= 70:
                lines.append(f"  - 建议升级至: **{next_spec}**")
        lines.append("")

    # CBWP 容量
    cbwp_insts = all_data.get("cbwp", {}).get("instances", [])
    high_util_cbwps = [i for i in cbwp_insts if i.get("metrics", {}).get("tx_peak_pct", 0) >= 50]
    if high_util_cbwps:
        has_content = True
        lines.append("### 共享带宽包\n")
        for inst in high_util_cbwps:
            m = inst.get("metrics", {})
            bw = inst.get("bandwidth_limit", 0)
            tx_pct = m.get("tx_peak_pct", 0)
            tx_peak = m.get("tx_peak_mbps", 0)
            suggested_bw = max(bw, int(tx_peak * 1.3))
            lines.append(
                f"- `{inst.get('instance_id', '')}` — "
                f"当前带宽上限 {bw}Mbps，出方向峰值 {tx_peak}Mbps (利用率 {tx_pct}%)"
            )
            if suggested_bw > bw:
                lines.append(f"  - 建议带宽: **{suggested_bw}Mbps** (按峰值1.3倍预留)")
        lines.append("")

    # CEN 容量
    cen_insts = all_data.get("cen", {}).get("instances", [])
    high_util_cens = [i for i in cen_insts if i.get("metrics", {}).get("peak_utilization_pct", 0) >= 50]
    if high_util_cens:
        has_content = True
        lines.append("### 云企业网带宽\n")
        for inst in high_util_cens:
            m = inst.get("metrics", {})
            lines.append(
                f"- `{inst.get('instance_id', '')}` — "
                f"跨域带宽利用率峰值 {m.get('peak_utilization_pct', 0)}%，"
                f"建议扩容CEN带宽包"
            )
        lines.append("")

    if not has_content:
        lines.append("当前所有网络资源利用率均低于50%，暂无紧急扩容需求。\n")
        lines.append("**日常建议:**\n")
        lines.append("- 定期（每周/每月）执行巡检，持续跟踪水位变化趋势")
        lines.append("- 在大促/活动前提前评估容量，建议预留30%-50%的冗余")
        lines.append("- 关注业务增长趋势，提前规划网络资源扩容计划")
        lines.append("")

    return lines


def _generate_traffic_insights(all_data: dict) -> list:
    """生成流量洞察分析。"""
    lines = []
    lines.append("## 流量洞察\n")

    has_insight = False

    # EIP 流量排行
    eip_insts = all_data.get("eip", {}).get("instances", [])
    if len(eip_insts) > 1:
        has_insight = True
        sorted_eips = sorted(eip_insts,
                             key=lambda x: x.get("metrics", {}).get("tx_peak_mbps", 0),
                             reverse=True)
        lines.append("### 公网出口流量 TOP5\n")
        lines.append("| 排名 | 实例ID | IP地址 | 出方向峰值(Mbps) | 带宽上限(Mbps) | 利用率 |")
        lines.append("|------|--------|--------|-----------------|---------------|--------|")
        for rank, inst in enumerate(sorted_eips[:5], 1):
            m = inst.get("metrics", {})
            lines.append(
                f"| {rank} | {inst.get('instance_id', '')} "
                f"| {inst.get('ip_address', '')} "
                f"| {m.get('tx_peak_mbps', 0)} "
                f"| {inst.get('bandwidth', 0)} "
                f"| {m.get('tx_peak_pct', 0)}% |"
            )
        lines.append("")

    # ALB QPS 排行
    alb_insts = all_data.get("alb", {}).get("instances", [])
    if len(alb_insts) > 1:
        has_insight = True
        sorted_albs = sorted(alb_insts,
                             key=lambda x: x.get("metrics", {}).get("qps_peak", 0),
                             reverse=True)
        lines.append("### ALB QPS 排行\n")
        lines.append("| 排名 | 实例ID | 名称 | QPS峰值 | QPS均值 | 5XX错误率 |")
        lines.append("|------|--------|------|---------|---------|----------|")
        for rank, inst in enumerate(sorted_albs[:5], 1):
            m = inst.get("metrics", {})
            lines.append(
                f"| {rank} | {inst.get('instance_id', '')} "
                f"| {inst.get('instance_name', '') or '-'} "
                f"| {int(m.get('qps_peak', 0)):,} "
                f"| {int(m.get('qps_avg', 0)):,} "
                f"| {m.get('error_5xx_pct', 0)}% |"
            )
        lines.append("")

    # CLB 连接数排行
    clb_insts = all_data.get("clb", {}).get("instances", [])
    if len(clb_insts) > 1:
        has_insight = True
        sorted_clbs = sorted(clb_insts,
                             key=lambda x: x.get("metrics", {}).get("active_conn_peak", 0),
                             reverse=True)
        lines.append("### CLB 活跃连接数 TOP5\n")
        lines.append("| 排名 | 实例ID | 名称 | 活跃连接峰值 | QPS峰值 | 丢包 |")
        lines.append("|------|--------|------|------------|---------|------|")
        for rank, inst in enumerate(sorted_clbs[:5], 1):
            m = inst.get("metrics", {})
            drop_str = "有" if m.get("has_drops") else "无"
            lines.append(
                f"| {rank} | {inst.get('instance_id', '')} "
                f"| {inst.get('instance_name', '') or '-'} "
                f"| {int(m.get('active_conn_peak', 0)):,} "
                f"| {int(m.get('qps_peak', 0)):,} "
                f"| {drop_str} |"
            )
        lines.append("")

    # 峰值均值比分析（识别流量尖刺）
    spike_instances = []
    for inst in eip_insts:
        m = inst.get("metrics", {})
        tx_peak = m.get("tx_peak_mbps", 0)
        tx_avg = m.get("tx_avg_mbps", 0)
        if tx_avg > 0 and tx_peak / tx_avg > 5:
            spike_instances.append({
                "type": "EIP",
                "id": inst.get("instance_id", ""),
                "peak": tx_peak,
                "avg": tx_avg,
                "ratio": round(tx_peak / tx_avg, 1),
            })
    for inst in alb_insts:
        m = inst.get("metrics", {})
        qps_peak = m.get("qps_peak", 0)
        qps_avg = m.get("qps_avg", 0)
        if qps_avg > 0 and qps_peak / qps_avg > 5:
            spike_instances.append({
                "type": "ALB",
                "id": inst.get("instance_id", ""),
                "peak": qps_peak,
                "avg": qps_avg,
                "ratio": round(qps_peak / qps_avg, 1),
            })

    if spike_instances:
        has_insight = True
        lines.append("### 流量尖刺检测\n")
        lines.append("以下实例的峰值/均值比超过5倍，可能存在突发流量：\n")
        for s in spike_instances:
            if s["type"] == "EIP":
                lines.append(
                    f"- **{s['type']}** `{s['id']}` — 出方向峰值 {s['peak']}Mbps / 均值 {s['avg']}Mbps "
                    f"(峰均比 **{s['ratio']}x**)"
                )
            else:
                lines.append(
                    f"- **{s['type']}** `{s['id']}` — QPS峰值 {int(s['peak']):,} / 均值 {int(s['avg']):,} "
                    f"(峰均比 **{s['ratio']}x**)"
                )
        lines.append("")
        lines.append("> **说明**: 高峰均比表明流量存在明显尖刺，建议分析流量时间分布，"
                     "评估是否需要弹性带宽或限流保护。\n")

    if not has_insight:
        lines.append("当前实例数较少，暂无流量排行数据。\n")

    return lines


# ─── 报告生成主函数 ──────────────────────────────────────────────────

def generate_report(diag_dir: str, days: int, output_path: str = None,
                    charts_dir: str = None, image_url_map: dict = None) -> str:
    """生成完整巡检报告。

    Args:
        image_url_map: 可选，图片文件名到云端URL的映射，
                       用于钉钉文档等需要云端图片引用的场景。
    """
    # 加载各产品巡检数据
    product_files = {
        "eip": "eip.json",
        "cbwp": "cbwp.json",
        "nat": "nat.json",
        "cen": "cen.json",
        "tr": "tr.json",
        "physconn": "physconn.json",
        "vbr": "vbr.json",
        "ga": "ga.json",
        "clb": "clb.json",
        "alb": "alb.json",
        "nlb": "nlb.json",
    }

    all_data = {}
    for key, filename in product_files.items():
        all_data[key] = load_json(os.path.join(diag_dir, filename))

    # 收集 Region 列表
    all_regions = set()
    for data in all_data.values():
        all_regions.update(data.get("regions", []))

    # 产品中文名映射
    type_names = {
        "eip": "弹性公网IP",
        "cbwp": "共享带宽包",
        "nat": "NAT网关",
        "cen": "云企业网",
        "tr": "转发路由器",
        "physconn": "物理专线",
        "vbr": "VBR",
        "ga": "全球加速",
        "clb": "传统型负载均衡",
        "alb": "应用型负载均衡",
        "nlb": "网络型负载均衡",
    }

    # 先计算汇总数据供执行摘要使用
    total_all = {"total": 0, "ok": 0, "warning": 0, "critical": 0, "error": 0}
    for key in type_names:
        s = all_data.get(key, {}).get("summary", {})
        total_all["total"] += s.get("total", 0)
        total_all["ok"] += s.get("ok", 0)
        total_all["warning"] += s.get("warning", 0)
        total_all["critical"] += s.get("critical", 0)
        total_all["error"] += s.get("error", 0)

    # 收集需要关注的实例
    attention_instances = []
    for key, name in type_names.items():
        data = all_data.get(key, {})
        for inst in data.get("instances", []):
            if inst.get("risk_level") in ("warning", "critical"):
                attention_instances.append((name, inst))

    # 生成扩容建议
    recommendations = generate_recommendations(all_data)

    # ── 开始生成报告 ──
    report_lines = []
    report_lines.append("# 阿里云网络产品全面巡检报告\n")
    report_lines.append(f"**巡检时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**巡检范围**: {', '.join(sorted(all_regions)) if all_regions else '未指定'}")
    report_lines.append(f"**巡检周期**: 最近 {days} 天")
    report_lines.append(f"**涵盖产品**: 11 类网络产品（EIP、CBWP、NAT、CEN、TR、物理专线、VBR、GA、CLB、ALB、NLB）")
    report_lines.append(f"**实例总数**: {total_all['total']} 个")
    report_lines.append(f"**报告说明**: 本报告涵盖11类网络产品的全面巡检，所有API调用均为只读查询操作。\n")

    # ── 执行摘要（新增） ──
    report_lines.extend(_generate_executive_summary(
        total_all, attention_instances, recommendations, all_regions, days, all_data, type_names
    ))

    # ── 概览表 ──
    report_lines.append("## 巡检概览\n")
    report_lines.append("| 序号 | 资源类型 | 实例数 | 🟢正常 | 🟡告警 | 🔴严重 | ⚠️异常 |")
    report_lines.append("|------|---------|-------|-------|-------|-------|-------|")

    for idx, (key, name) in enumerate(type_names.items(), 1):
        s = all_data.get(key, {}).get("summary", {})
        total = s.get("total", 0)
        ok = s.get("ok", 0)
        warning = s.get("warning", 0)
        critical = s.get("critical", 0)
        error = s.get("error", 0)
        report_lines.append(f"| {idx} | {name} | {total} | {ok} | {warning} | {critical} | {error} |")

    report_lines.append(
        f"| | **合计** | **{total_all['total']}** | **{total_all['ok']}** "
        f"| **{total_all['warning']}** | **{total_all['critical']}** | **{total_all['error']}** |"
    )
    report_lines.append("")

    # ── 地域维度统计（新增） ──
    report_lines.extend(_generate_region_summary(all_data, type_names))

    # ── 需要关注的实例 ──
    if attention_instances:
        report_lines.append("## 需要立即关注的实例\n")

        # 构建 instance_id → reason 的查找表
        reason_map = {}
        for rec in recommendations:
            inst_label = rec.get("instance", "")
            # inst_label 格式为 "id (name)" 或 "id"，提取 id
            iid = inst_label.split(" (")[0].strip() if " (" in inst_label else inst_label.strip()
            if iid:
                reason_map[iid] = rec.get("reason", "")

        critical_list = [(n, i) for n, i in attention_instances if i.get("risk_level") == "critical"]
        warning_list = [(n, i) for n, i in attention_instances if i.get("risk_level") == "warning"]

        if critical_list:
            report_lines.append("**严重 (需立即处理):**\n")
            for type_name, inst in critical_list:
                iid = inst.get("instance_id", "")
                reason = reason_map.get(iid, "")
                line = (f"- {risk_emoji('critical')} **{type_name}** `{iid}` "
                        f"({inst.get('instance_name', '') or '-'}) [{inst.get('region', '')}]")
                if reason:
                    line += f"\n  - **原因**: {reason}"
                report_lines.append(line)
            report_lines.append("")

        if warning_list:
            report_lines.append("**告警 (建议近期处理):**\n")
            for type_name, inst in warning_list:
                iid = inst.get("instance_id", "")
                reason = reason_map.get(iid, "")
                line = (f"- {risk_emoji('warning')} **{type_name}** `{iid}` "
                        f"({inst.get('instance_name', '') or '-'}) [{inst.get('region', '')}]")
                if reason:
                    line += f"\n  - **原因**: {reason}"
                report_lines.append(line)
            report_lines.append("")

    # ── 流量洞察（新增） ──
    report_lines.extend(_generate_traffic_insights(all_data))

    # ── 各产品详细报告 ──
    report_lines.append("## 各产品巡检详情\n")

    section_formatters = [
        ("eip", format_eip_section),
        ("cbwp", format_cbwp_section),
        ("nat", format_nat_section),
        ("cen", format_cen_section),
        ("tr", format_tr_section),
        ("physconn", format_physconn_section),
        ("vbr", format_vbr_section),
        ("ga", format_ga_section),
        ("clb", format_clb_section),
        ("alb", format_alb_section),
        ("nlb", format_nlb_section),
    ]

    # 计算报告目录（用于图表相对路径）
    report_dir = os.path.dirname(os.path.abspath(output_path)) if output_path else None

    for key, formatter in section_formatters:
        data = all_data.get(key, {})
        report_lines.append(formatter(data))

        # 深度分析
        deep_fn = _DEEP_ANALYSIS_MAP.get(key)
        if deep_fn:
            deep_lines = deep_fn(data)
            if deep_lines:
                report_lines.extend(deep_lines)

        # 图表引用
        if charts_dir:
            chart_lines = _format_chart_section(
                charts_dir, key, data.get("instances", []), report_dir,
                image_url_map=image_url_map
            )
            if chart_lines:
                report_lines.extend(chart_lines)

    # ── 扩容建议 ──
    report_lines.append("## 扩容建议与优化方向\n")
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            report_lines.append(
                f"{i}. {risk_emoji(rec['priority'])} **{rec['type']}** `{rec['instance']}` [{rec['region']}]\n"
                f"   - **问题**: {rec['reason']}\n"
                f"   - **建议**: {rec['suggestion']}\n"
            )
    else:
        report_lines.append("所有网络资源水位正常，暂无扩容需求。建议保持定期巡检习惯。\n")

    # ── 容量规划建议（新增） ──
    report_lines.extend(_generate_capacity_planning(all_data))

    # ── 错误汇总 ──
    all_errors = []
    for data in all_data.values():
        all_errors.extend(data.get("errors", []))
    if all_errors:
        report_lines.append("## 巡检过程中的异常\n")
        for err in all_errors:
            report_lines.append(f"- [{err.get('region', '-')}] {err.get('error', '未知错误')}")
        report_lines.append("")

    # ── 附录 ──
    report_lines.append("## 附录\n")

    report_lines.append("### 风险等级说明\n")
    report_lines.append("| 等级 | 标记 | 含义 | 建议动作 |")
    report_lines.append("|------|------|------|---------|")
    report_lines.append("| 严重 | 🔴 | 利用率 ≥90%、存在丢包、或关键状态异常 | 立即处理 |")
    report_lines.append("| 告警 | 🟡 | 利用率 ≥70%，接近容量上限 | 近期扩容或优化 |")
    report_lines.append("| 正常 | 🟢 | 利用率 <70%，资源水位健康 | 保持定期巡检 |")
    report_lines.append("| 异常 | ⚠️ | 巡检过程中发生错误，数据可能不完整 | 检查权限和配置 |")
    report_lines.append("")

    report_lines.append("### 各产品规格上限参考\n")
    report_lines.append("| 产品 | 规格 | 主要限制 |")
    report_lines.append("|------|------|---------|")
    report_lines.append("| NAT网关 | Small | 最大SNAT连接数 100,000，带宽上限 1Gbps |")
    report_lines.append("| NAT网关 | Medium | 最大SNAT连接数 500,000，带宽上限 5Gbps |")
    report_lines.append("| NAT网关 | Large | 最大SNAT连接数 2,000,000，带宽上限 10Gbps |")
    report_lines.append("| NAT网关 | XLarge.1 | 最大SNAT连接数 5,000,000，带宽上限 20Gbps |")
    report_lines.append("| VBR | - | 健康检查延迟 <50ms/丢包率 <1% 为正常 |")
    report_lines.append("| ALB | - | 5XX错误率 <1% 为正常，>5% 为严重 |")
    report_lines.append("")

    report_lines.append("### 巡检方法说明\n")
    report_lines.append("- **数据来源**: 阿里云云监控（CloudMonitor）DescribeMetricList API")
    report_lines.append("- **监控精度**: 取决于云监控的采集周期（通常为60秒）")
    report_lines.append("- **利用率计算**: 峰值利用率 = 监控周期内最大值 / 带宽上限 × 100%")
    report_lines.append("- **CMS查询端点**: 统一使用 cn-hangzhou（CMS为全局服务）")
    report_lines.append("")

    report_lines.append("### 声明\n")
    report_lines.append("- 本报告所有 API 调用均为**只读查询操作**，不涉及任何资源创建、修改或删除操作")
    report_lines.append("- 监控数据来源于阿里云云监控（CloudMonitor），数据精度取决于云监控的采集周期")
    report_lines.append("- 建议结合业务实际情况评估扩容需求，本报告仅供参考")
    report_lines.append("- 如需更精确的容量评估，请联系阿里云技术支持或架构师团队")
    report_lines.append("")

    report = "\n".join(report_lines)

    # 保存到文件
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(json.dumps({
            "saved_to": output_path,
            "summary": total_all,
            "health_score": _calculate_health_score(total_all),
            "recommendations_count": len(recommendations),
            "errors_count": len(all_errors),
        }, ensure_ascii=False, indent=2))
    else:
        output = {
            "report_markdown": report,
            "summary": total_all,
            "health_score": _calculate_health_score(total_all),
            "recommendations": recommendations,
            "errors": all_errors,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

    return report


def main():
    parser = argparse.ArgumentParser(description="阿里云网络产品全面巡检报告生成（只读操作）")
    parser.add_argument("--dir", required=True, help="巡检数据目录（存放各产品 JSON 文件）")
    parser.add_argument("--days", type=int, required=True, help="巡检天数（必须指定）")
    parser.add_argument("--output", default=None, help="报告输出文件路径（Markdown 格式）")
    parser.add_argument("--charts-dir", default=None,
                        help="图表目录路径（包含 PNG 文件，将嵌入报告中）")
    parser.add_argument("--image-url-map", default=None,
                        help="图片URL映射文件路径（JSON格式: {文件名: 云端URL}），"
                             "用于钉钉文档等需要云端图片引用的场景")
    args = parser.parse_args()

    image_url_map = None
    if args.image_url_map:
        image_url_map = load_json(args.image_url_map)

    generate_report(args.dir, args.days, args.output, args.charts_dir,
                    image_url_map=image_url_map)


if __name__ == "__main__":
    main()
    main()
