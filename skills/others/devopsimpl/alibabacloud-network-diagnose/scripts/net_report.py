"""Implementation detail."""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


STATUS_ICONS = {
    "ok": "正常",
    "warning": "警告",
    "critical": "异常",
    "error": "错误",
    "skipped": "跳过",
}


def generate_customer_report(analysis: dict, context: dict = None) -> str:
    """Implementation detail."""
    context = context or {}
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append("## 内网连通性诊断报告")
    lines.append("")
    lines.append(f"**诊断时间**: {now}")


    scenario = context.get("scenario", "")
    scenario_names = {
        "same_vpc": "同 VPC 实例互访",
        "cross_vpc": "跨 VPC 实例互访",
        "hybrid": "阿里云到 IDC",
    }
    if scenario:
        lines.append(f"**场景类型**: {scenario_names.get(scenario, scenario)}")


    source = context.get("source", {})
    destination = context.get("destination", {})
    if source:
        src_str = f"{source.get('instance_id', '')} ({source.get('ip', '')}) @ {source.get('vpc_id', '')}/{source.get('vswitch_id', '')}"
        lines.append(f"**源端**: {src_str}")
    if destination:
        dst_str = f"{destination.get('instance_id', '')} ({destination.get('ip', '')}) @ {destination.get('vpc_id', '')}/{destination.get('vswitch_id', '')}"
        lines.append(f"**目的端**: {dst_str}")

    proto = context.get("protocol", "")
    port = context.get("port", 0)
    if proto or port:
        lines.append(f"**协议/端口**: {proto or 'ALL'}/{port or 'ALL'}")

    lines.append("")


    severity = analysis.get("severity", "normal")
    conclusion = analysis.get("conclusion", "")
    severity_labels = {
        "critical": "**严重** - 存在阻断性配置问题",
        "warning": "**警告** - 存在需要关注的配置项",
        "normal": "**正常** - 未发现明显配置异常",
    }
    lines.append("### 诊断结论")
    lines.append("")
    lines.append(f"**严重级别**: {severity_labels.get(severity, severity)}")
    lines.append("")
    lines.append(conclusion)
    lines.append("")


    check_table = analysis.get("check_table", [])
    if check_table:
        lines.append("### 检查结果汇总")
        lines.append("")
        lines.append("| 检查项 | 状态 | 说明 |")
        lines.append("|--------|------|------|")
        for row in check_table:
            status_icon = STATUS_ICONS.get(row["status"], row["status"])
            lines.append(f"| {row['item']} | {status_icon} | {row['summary']} |")
        lines.append("")


    root_causes = analysis.get("root_causes", [])
    if root_causes:
        lines.append("### 发现的问题")
        lines.append("")
        for i, cause in enumerate(root_causes, 1):
            lines.append(f"{i}. {cause}")
        lines.append("")


    recommendations = analysis.get("recommendations", [])
    if recommendations:
        lines.append("### 建议操作")
        lines.append("")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
    elif severity == "normal":
        lines.append("### 建议操作")
        lines.append("")
        lines.append("当前网络配置未发现明显异常。如仍有连通性问题，建议：")
        lines.append("")
        lines.append("1. 检查实例内操作系统防火墙（iptables/firewalld/Windows 防火墙）")
        lines.append("2. 检查目标端口上的服务是否正常监听")
        lines.append("3. 如使用 ICMP (ping)，确认操作系统未禁用 ICMP 响应")
        lines.append("")

    return "\n".join(lines)




def main():
    import argparse

    parser = argparse.ArgumentParser(description="内网连通性诊断报告生成")
    parser.add_argument("--analysis", required=True, help="分析结果 JSON 文件路径")
    parser.add_argument("--context", help="诊断上下文 JSON 文件路径")

    args = parser.parse_args()

    try:
        with open(args.analysis, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"无法读取分析文件: {e}"}, ensure_ascii=False))
        return

    context = {}
    if args.context:
        try:
            with open(args.context, "r", encoding="utf-8") as f:
                context = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    report = generate_customer_report(analysis, context)
    print(report)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(json.dumps({"error": "用户中断"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(json.dumps({"error": f"未处理的异常: {type(e).__name__}: {e}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
