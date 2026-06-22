"""
inspect_charts.py - 阿里云网络产品巡检监控曲线图生成

为每个网络产品实例的关键监控指标生成时间序列曲线图。
图表使用中文标签，DPI 200 确保清晰度。

所有 API 调用均为只读查询操作，不涉及任何写操作。

用法:
    python3 inspect_charts.py --dir /tmp/net_inspect_xxx --days 3 --output-dir /path/to/charts
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_common import query_metric, bits_to_mbps

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from datetime import datetime


# CMS 查询统一使用 cn-hangzhou 作为 endpoint（CMS 是全局服务）
CMS_ENDPOINT_REGION = "cn-hangzhou"

# 图表颜色方案
COLORS = {
    "blue": "#1890ff",
    "red": "#fa541c",
    "green": "#52c41a",
    "orange": "#faad14",
    "purple": "#722ed1",
    "cyan": "#13c2c2",
    "danger": "#f5222d",
}


def _setup_font():
    """查找并设置支持中文的字体。"""
    candidates = []
    for f in fm.findSystemFonts():
        try:
            prop = fm.FontProperties(fname=f)
            name = prop.get_name()
            if any(k in name for k in ["PingFang", "STHeiti", "Heiti", "Songti", "SimHei", "Microsoft YaHei"]):
                candidates.append((name, f))
        except Exception:
            pass

    if candidates:
        for name, path in candidates:
            if "PingFang" in name:
                fm.fontManager.addfont(path)
                plt.rcParams["font.sans-serif"] = [name] + plt.rcParams.get("font.sans-serif", [])
                return name
        name, path = candidates[0]
        fm.fontManager.addfont(path)
        plt.rcParams["font.sans-serif"] = [name] + plt.rcParams.get("font.sans-serif", [])
        return name
    return None


# 图表样式配置 - 高清中文
plt.rcParams.update({
    "figure.figsize": (14, 5),
    "figure.dpi": 200,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "lines.linewidth": 1.5,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
})

_font_name = _setup_font()
if _font_name:
    print(f"[图表] 使用中文字体: {_font_name}", file=sys.stderr)
else:
    print("[图表] 警告: 未找到中文字体，中文字符可能无法正常显示", file=sys.stderr)
plt.rcParams["axes.unicode_minus"] = False


def parse_datapoints(datapoints: list, convert_fn=None):
    """将 CloudMonitor datapoints 解析为 (timestamps, values) 列表。"""
    times = []
    values = []
    for dp in datapoints:
        ts = dp.get("timestamp", 0)
        v = dp.get("Value") or dp.get("Average") or dp.get("Maximum")
        if ts and v is not None:
            try:
                dt = datetime.fromtimestamp(ts / 1000)
                val = float(v)
                if convert_fn:
                    val = convert_fn(val)
                times.append(dt)
                values.append(val)
            except (ValueError, TypeError):
                pass
    return times, values


def _save_chart(fig, output_path: str):
    """保存图表并关闭。"""
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_bandwidth_chart(instance_id: str, instance_name: str, region: str,
                         in_data: list, out_data: list, output_path: str,
                         title_prefix: str = ""):
    """绘制带宽曲线图（入/出双线）。"""
    fig, ax = plt.subplots()

    in_times, in_vals = parse_datapoints(in_data, lambda v: bits_to_mbps(v))
    out_times, out_vals = parse_datapoints(out_data, lambda v: bits_to_mbps(v))

    if in_times:
        ax.plot(in_times, in_vals, label="入方向 (Mbps)", color=COLORS["blue"], alpha=0.8)
        ax.fill_between(in_times, in_vals, alpha=0.05, color=COLORS["blue"])
    if out_times:
        ax.plot(out_times, out_vals, label="出方向 (Mbps)", color=COLORS["red"], alpha=0.8)
        ax.fill_between(out_times, out_vals, alpha=0.05, color=COLORS["red"])

    label = instance_id
    if instance_name:
        label += f" ({instance_name})"
    ax.set_title(f"{title_prefix}带宽监控 - {label} [{region}]")
    ax.set_ylabel("带宽 (Mbps)")
    ax.legend(loc="upper right")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate()
    _save_chart(fig, output_path)


def plot_single_metric_chart(instance_id: str, instance_name: str, region: str,
                             data: list, output_path: str,
                             metric_label: str, unit: str, color: str = None,
                             convert_fn=None, title_prefix: str = ""):
    """绘制单指标曲线图。"""
    fig, ax = plt.subplots()
    color = color or COLORS["blue"]

    times, vals = parse_datapoints(data, convert_fn)
    if times:
        ax.plot(times, vals, label=metric_label, color=color, alpha=0.8)
        ax.fill_between(times, vals, alpha=0.1, color=color)

    label = instance_id
    if instance_name:
        label += f" ({instance_name})"
    ax.set_title(f"{title_prefix}{metric_label} - {label} [{region}]")
    ax.set_ylabel(f"{metric_label} ({unit})")
    ax.legend(loc="upper right")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate()
    _save_chart(fig, output_path)


def plot_dual_metric_chart(instance_id: str, instance_name: str, region: str,
                           data1: list, data2: list, output_path: str,
                           label1: str, label2: str, unit: str,
                           color1: str = None, color2: str = None,
                           convert_fn=None, title: str = ""):
    """绘制双指标曲线图。"""
    fig, ax = plt.subplots()
    color1 = color1 or COLORS["blue"]
    color2 = color2 or COLORS["red"]

    times1, vals1 = parse_datapoints(data1, convert_fn)
    times2, vals2 = parse_datapoints(data2, convert_fn)

    if times1:
        ax.plot(times1, vals1, label=label1, color=color1, alpha=0.8)
    if times2:
        ax.plot(times2, vals2, label=label2, color=color2, alpha=0.8)

    label = instance_id
    if instance_name:
        label += f" ({instance_name})"
    ax.set_title(f"{title} - {label} [{region}]")
    ax.set_ylabel(unit)
    ax.legend(loc="upper right")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate()
    _save_chart(fig, output_path)


# ─── 各产品图表生成函数 ──────────────────────────────────────────

def _fetch_metrics(namespace: str, metrics: list, instance_id: str, days: int,
                   period: int, dim_key: str = "instanceId") -> dict:
    """批量获取指标的原始 datapoints，自动分页拉取全部数据。"""
    end_time = int(time.time() * 1000)
    start_time = end_time - days * 24 * 3600 * 1000

    raw = {}
    for m_name in metrics:
        result = query_metric(namespace, m_name, instance_id,
                              start_time, end_time, period, dim_key)
        raw[m_name] = result.get("datapoints", [])
    return raw


def fetch_and_plot_eip(instance: dict, days: int, output_dir: str, period: int) -> list:
    """EIP 监控图表。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    region = instance.get("region", "")
    charts = []

    raw = _fetch_metrics("acs_vpc_eip",
                         ["net_tx.rate", "net_rx.rate", "out_ratelimit_drop_speed"],
                         inst_id, days)

    # 带宽图
    bw_path = os.path.join(output_dir, f"eip_{inst_id}_bandwidth.png")
    plot_bandwidth_chart(inst_id, inst_name, region,
                         raw["net_rx.rate"], raw["net_tx.rate"],
                         bw_path, title_prefix="EIP ")
    charts.append(("带宽", bw_path))

    # 丢包图（如果有数据）
    if raw.get("out_ratelimit_drop_speed"):
        drop_path = os.path.join(output_dir, f"eip_{inst_id}_drop.png")
        plot_single_metric_chart(inst_id, inst_name, region,
                                 raw["out_ratelimit_drop_speed"], drop_path,
                                 "出方向限速丢包", "pps", COLORS["danger"],
                                 title_prefix="EIP ")
        charts.append(("限速丢包", drop_path))

    return charts


def fetch_and_plot_cbwp(instance: dict, days: int, output_dir: str, period: int) -> list:
    """共享带宽包监控图表。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    region = instance.get("region", "")
    charts = []

    raw = _fetch_metrics("acs_bandwidth_package",
                         ["bwp_tx_rate", "bwp_rx_rate", "out_rate_percent", "ratelimit_drop_speed"],
                         inst_id, days)

    bw_path = os.path.join(output_dir, f"cbwp_{inst_id}_bandwidth.png")
    plot_bandwidth_chart(inst_id, inst_name, region,
                         raw["bwp_rx_rate"], raw["bwp_tx_rate"],
                         bw_path, title_prefix="共享带宽包 ")
    charts.append(("带宽", bw_path))

    util_path = os.path.join(output_dir, f"cbwp_{inst_id}_utilization.png")
    plot_single_metric_chart(inst_id, inst_name, region,
                             raw["out_rate_percent"], util_path,
                             "出方向利用率", "%", COLORS["orange"],
                             title_prefix="共享带宽包 ")
    charts.append(("利用率", util_path))

    if raw.get("ratelimit_drop_speed"):
        drop_path = os.path.join(output_dir, f"cbwp_{inst_id}_drop.png")
        plot_single_metric_chart(inst_id, inst_name, region,
                                 raw["ratelimit_drop_speed"], drop_path,
                                 "限速丢包速率", "pps", COLORS["danger"],
                                 title_prefix="共享带宽包 ")
        charts.append(("限速丢包", drop_path))

    return charts


def fetch_and_plot_nat(instance: dict, days: int, output_dir: str, period: int) -> list:
    """NAT 网关监控图表。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    region = instance.get("region", "")
    charts = []

    raw = _fetch_metrics("acs_nat_gateway",
                         ["BWRateInFromOutside", "BWRateOutToOutside",
                          "SnatConnection", "SessionLimitDropRate"],
                         inst_id, days)

    bw_path = os.path.join(output_dir, f"nat_{inst_id}_bandwidth.png")
    plot_bandwidth_chart(inst_id, inst_name, region,
                         raw["BWRateInFromOutside"], raw["BWRateOutToOutside"],
                         bw_path, title_prefix="NAT网关 ")
    charts.append(("带宽", bw_path))

    snat_path = os.path.join(output_dir, f"nat_{inst_id}_snat.png")
    plot_single_metric_chart(inst_id, inst_name, region,
                             raw["SnatConnection"], snat_path,
                             "SNAT并发连接数", "个", COLORS["green"],
                             title_prefix="NAT网关 ")
    charts.append(("SNAT连接数", snat_path))

    if raw.get("SessionLimitDropRate"):
        drop_path = os.path.join(output_dir, f"nat_{inst_id}_drop.png")
        plot_single_metric_chart(inst_id, inst_name, region,
                                 raw["SessionLimitDropRate"], drop_path,
                                 "并发连接限速丢包", "pps", COLORS["danger"],
                                 title_prefix="NAT网关 ")
        charts.append(("连接丢包", drop_path))

    return charts


def fetch_and_plot_vbr(instance: dict, days: int, output_dir: str, period: int) -> list:
    """VBR 监控图表。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    region = instance.get("region", "")
    charts = []

    raw = _fetch_metrics("acs_physical_connection",
                         ["RateInFromIDCToVpc", "RateOutFromVpcToIDC",
                          "VbrHealthyCheckLatency", "VbrHealthyCheckLossRate"],
                         inst_id, days)

    bw_path = os.path.join(output_dir, f"vbr_{inst_id}_bandwidth.png")
    plot_bandwidth_chart(inst_id, inst_name, region,
                         raw["RateInFromIDCToVpc"], raw["RateOutFromVpcToIDC"],
                         bw_path, title_prefix="VBR ")
    charts.append(("带宽", bw_path))

    latency_path = os.path.join(output_dir, f"vbr_{inst_id}_latency.png")
    plot_single_metric_chart(inst_id, inst_name, region,
                             raw["VbrHealthyCheckLatency"], latency_path,
                             "健康检查延迟", "ms", COLORS["orange"],
                             convert_fn=lambda v: v / 1000,
                             title_prefix="VBR ")
    charts.append(("延迟", latency_path))

    loss_path = os.path.join(output_dir, f"vbr_{inst_id}_lossrate.png")
    plot_single_metric_chart(inst_id, inst_name, region,
                             raw["VbrHealthyCheckLossRate"], loss_path,
                             "健康检查丢包率", "%", COLORS["danger"],
                             title_prefix="VBR ")
    charts.append(("丢包率", loss_path))

    return charts


def fetch_and_plot_clb(instance: dict, days: int, output_dir: str, period: int) -> list:
    """CLB 监控图表。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    region = instance.get("region", "")
    charts = []

    raw = _fetch_metrics("acs_slb_dashboard",
                         ["InstanceTrafficRX", "InstanceTrafficTX",
                          "InstanceActiveConnection", "InstanceQps"],
                         inst_id, days)

    bw_path = os.path.join(output_dir, f"clb_{inst_id}_traffic.png")
    plot_bandwidth_chart(inst_id, inst_name, region,
                         raw["InstanceTrafficRX"], raw["InstanceTrafficTX"],
                         bw_path, title_prefix="CLB ")
    charts.append(("流量", bw_path))

    conn_path = os.path.join(output_dir, f"clb_{inst_id}_connection.png")
    plot_single_metric_chart(inst_id, inst_name, region,
                             raw["InstanceActiveConnection"], conn_path,
                             "活跃连接数", "个", COLORS["green"],
                             title_prefix="CLB ")
    charts.append(("连接数", conn_path))

    if raw.get("InstanceQps"):
        qps_path = os.path.join(output_dir, f"clb_{inst_id}_qps.png")
        plot_single_metric_chart(inst_id, inst_name, region,
                                 raw["InstanceQps"], qps_path,
                                 "QPS", "个/秒", COLORS["purple"],
                                 title_prefix="CLB ")
        charts.append(("QPS", qps_path))

    return charts


def fetch_and_plot_alb(instance: dict, days: int, output_dir: str, period: int) -> list:
    """ALB 监控图表。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    region = instance.get("region", "")
    charts = []

    raw = _fetch_metrics("acs_alb",
                         ["LoadBalancerQPS", "LoadBalancerHTTPCode2XX",
                          "LoadBalancerHTTPCode4XX", "LoadBalancerHTTPCode5XX",
                          "LoadBalancerActiveConnection"],
                         inst_id, days, dim_key="loadBalancerId")

    # QPS 图
    if raw.get("LoadBalancerQPS"):
        qps_path = os.path.join(output_dir, f"alb_{inst_id}_qps.png")
        plot_single_metric_chart(inst_id, inst_name, region,
                                 raw["LoadBalancerQPS"], qps_path,
                                 "QPS", "个/秒", COLORS["blue"],
                                 title_prefix="ALB ")
        charts.append(("QPS", qps_path))

    # HTTP 状态码分布
    if raw.get("LoadBalancerHTTPCode2XX") or raw.get("LoadBalancerHTTPCode5XX"):
        http_path = os.path.join(output_dir, f"alb_{inst_id}_http.png")
        fig, ax = plt.subplots()
        for metric, label, color in [
            ("LoadBalancerHTTPCode2XX", "2XX", COLORS["green"]),
            ("LoadBalancerHTTPCode4XX", "4XX", COLORS["orange"]),
            ("LoadBalancerHTTPCode5XX", "5XX", COLORS["danger"]),
        ]:
            times, vals = parse_datapoints(raw.get(metric, []))
            if times:
                ax.plot(times, vals, label=label, color=color, alpha=0.8)

        label_str = inst_id
        if inst_name:
            label_str += f" ({inst_name})"
        ax.set_title(f"ALB HTTP状态码 - {label_str} [{region}]")
        ax.set_ylabel("请求数 (个/秒)")
        ax.legend(loc="upper right")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        fig.autofmt_xdate()
        _save_chart(fig, http_path)
        charts.append(("HTTP状态码", http_path))

    return charts


def fetch_and_plot_nlb(instance: dict, days: int, output_dir: str, period: int) -> list:
    """NLB 监控图表。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    region = instance.get("region", "")
    charts = []

    raw = _fetch_metrics("acs_nlb",
                         ["LoadBalancerInBitsRate", "LoadBalancerOutBitsRate",
                          "LoadBalancerActiveFlowCount"],
                         inst_id, days, dim_key="loadBalancerId")

    if raw.get("LoadBalancerInBitsRate") or raw.get("LoadBalancerOutBitsRate"):
        bw_path = os.path.join(output_dir, f"nlb_{inst_id}_bandwidth.png")
        plot_bandwidth_chart(inst_id, inst_name, region,
                             raw.get("LoadBalancerInBitsRate", []),
                             raw.get("LoadBalancerOutBitsRate", []),
                             bw_path, title_prefix="NLB ")
        charts.append(("带宽", bw_path))

    if raw.get("LoadBalancerActiveFlowCount"):
        flow_path = os.path.join(output_dir, f"nlb_{inst_id}_flow.png")
        plot_single_metric_chart(inst_id, inst_name, region,
                                 raw["LoadBalancerActiveFlowCount"], flow_path,
                                 "活跃连接数", "个", COLORS["green"],
                                 title_prefix="NLB ")
        charts.append(("连接数", flow_path))

    return charts


def fetch_and_plot_ga(instance: dict, days: int, output_dir: str, period: int) -> list:
    """GA 监控图表。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    region = instance.get("region", "global")
    charts = []

    raw = _fetch_metrics("acs_global_acceleration",
                         ["GaInBps", "GaOutBps"],
                         inst_id, days)

    if raw.get("GaInBps") or raw.get("GaOutBps"):
        bw_path = os.path.join(output_dir, f"ga_{inst_id}_bandwidth.png")
        plot_bandwidth_chart(inst_id, inst_name, region,
                             raw.get("GaInBps", []), raw.get("GaOutBps", []),
                             bw_path, title_prefix="全球加速 ")
        charts.append(("带宽", bw_path))

    return charts


def fetch_and_plot_cen(instance: dict, days: int, output_dir: str, period: int) -> list:
    """CEN 监控图表（跨域带宽）。"""
    inst_id = instance["instance_id"]
    inst_name = instance.get("instance_name", "")
    charts = []

    end_time = int(time.time() * 1000)
    start_time = end_time - days * 24 * 3600 * 1000

    # CEN 跨域带宽，使用 cenId 作为 dimension
    metrics = ["InterRegionOutBandwidth", "InterRegionInBandwidth"]
    raw = {}
    for m_name in metrics:
        result = query_metric("acs_cen", m_name, inst_id,
                              start_time, end_time, period, "cenId")
        raw[m_name] = result.get("datapoints", [])

    if raw.get("InterRegionOutBandwidth") or raw.get("InterRegionInBandwidth"):
        bw_path = os.path.join(output_dir, f"cen_{inst_id}_bandwidth.png")
        plot_bandwidth_chart(inst_id, inst_name, "global",
                             raw.get("InterRegionInBandwidth", []),
                             raw.get("InterRegionOutBandwidth", []),
                             bw_path, title_prefix="CEN跨域 ")
        charts.append(("跨域带宽", bw_path))

    return charts


# ─── 主函数 ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="阿里云网络产品巡检图表生成（只读操作）")
    parser.add_argument("--dir", required=True, help="巡检数据目录")
    parser.add_argument("--days", type=int, required=True, help="巡检天数（必须指定）")
    parser.add_argument("--period", type=int, required=True, help="监控数据聚合粒度（秒）")
    parser.add_argument("--output-dir", required=True, help="图表输出目录")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    all_charts = {}

    # 产品及对应的图表生成函数和文件名
    product_configs = [
        ("eip.json", "eip", fetch_and_plot_eip),
        ("cbwp.json", "共享带宽包", fetch_and_plot_cbwp),
        ("nat.json", "NAT网关", fetch_and_plot_nat),
        ("cen.json", "CEN", fetch_and_plot_cen),
        ("vbr.json", "VBR", fetch_and_plot_vbr),
        ("clb.json", "CLB", fetch_and_plot_clb),
        ("alb.json", "ALB", fetch_and_plot_alb),
        ("nlb.json", "NLB", fetch_and_plot_nlb),
        ("ga.json", "GA", fetch_and_plot_ga),
    ]

    for filename, product_name, plot_fn in product_configs:
        data_path = os.path.join(args.dir, filename)
        if not os.path.exists(data_path):
            continue

        with open(data_path) as f:
            data = json.load(f)

        instances = data.get("instances", [])
        for inst in instances:
            inst_id = inst.get("instance_id", "")
            print(f"[图表] 生成 {product_name} {inst_id} 的监控曲线图...", file=sys.stderr)
            try:
                charts = plot_fn(inst, args.days, args.output_dir, args.period)
                if charts:
                    all_charts[inst_id] = {"type": product_name, "charts": charts}
                    print(f"[图表] {product_name} {inst_id}: 生成 {len(charts)} 张图表", file=sys.stderr)
            except Exception as e:
                print(f"[图表] {product_name} {inst_id} 图表生成失败: {e}", file=sys.stderr)

    # 输出图表清单
    summary = {}
    for inst_id, info in all_charts.items():
        summary[inst_id] = {
            "type": info["type"],
            "charts": [(name, path) for name, path in info["charts"]],
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
