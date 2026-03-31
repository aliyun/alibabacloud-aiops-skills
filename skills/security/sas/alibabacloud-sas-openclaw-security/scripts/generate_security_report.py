#!/usr/bin/env python3
"""生成 OpenClaw 安全日报。

汇总所有安全维度：实例、漏洞、基线、告警。

用法:
  python -m scripts.generate_security_report
  python -m scripts.generate_security_report \
      --output-dir output
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.sas_client import SasClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 OpenClaw 安全日报")
    parser.add_argument(
        "--name-pattern",
        default="openclaw",
        help="SCA 组件名称模糊匹配（默认: openclaw）",
    )
    parser.add_argument(
        "--biz",
        default="sca_ai",
        help="业务类型（默认: sca_ai）",
    )
    parser.add_argument(
        "--vuln-name",
        default="emg:SCA:AVD-2026-1860246",
        help="漏洞名称精确匹配" "（默认: emg:SCA:AVD-2026-1860246）",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="区域（默认: cn-shanghai）",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录（默认: output）",
    )
    return parser.parse_args()


def _safe_query(label: str, fn):
    """安全调用查询函数，失败返回空列表。"""
    try:
        result = fn()
        print(f"  [+] {label}: {len(result)} 条")
        return result
    except Exception as e:
        print(f"  [!] {label} 查询失败: {e}")
        traceback.print_exc()
        return []


def generate_report(
    instances: list[dict],
    vulns: list[dict],
    baseline: list[dict],
    alerts: list[dict],
) -> str:
    """生成 Markdown 安全日报。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# OpenClaw 安全日报 - {date_str}",
        "",
        f"生成时间: {now}",
        "",
        "---",
        "",
        "## 概览",
        "",
        "| 维度 | 数量 | 状态 |",
        "|------|------|------|",
    ]

    # 概览统计
    inst_status = "✅ 正常" if instances else "⚠️ 未发现实例"
    lines.append(f"| OpenClaw 实例 | {len(instances)} " f"| {inst_status} |")

    vuln_status = "🔴 存在风险" if vulns else "✅ 无漏洞"
    lines.append(f"| 未修复漏洞 | {len(vulns)} " f"| {vuln_status} |")

    base_at_risk = [
        m for m in baseline
        if int(m.get("HighWarningCount") or 0)
        + int(m.get("MediumWarningCount") or 0) > 0
    ]
    if base_at_risk:
        base_status = "🔴 存在风险"
    else:
        base_status = "✅ 基线合规"
    lines.append(
        f"| 基线风险项 | "
        f"{len(base_at_risk)}/{len(baseline)} "
        f"| {base_status} |"
    )

    alert_status = "🔴 存在告警" if alerts else "✅ 无告警"
    lines.append(f"| 未处理告警 | {len(alerts)} " f"| {alert_status} |")

    lines.append("")

    # 实例详情
    lines.append("---")
    lines.append("")
    lines.append("## 1. OpenClaw 实例")
    lines.append("")
    if instances:
        lines.append("| 主机名 | IP | 组件名 | 版本 |")
        lines.append("|--------|----|--------|------|")
        for inst in instances[:20]:
            host = inst.get("InstanceName", "-")
            ip = inst.get("Ip") or inst.get("InternetIp", "-")
            name = inst.get("Name", "-")
            ver = inst.get("Version", "-")
            lines.append(f"| {host} | {ip} | {name} | {ver} |")
        if len(instances) > 20:
            lines.append(f"\n> 仅显示前 20 条，" f"共 {len(instances)} 条")
    else:
        lines.append("未发现 OpenClaw 实例。")
    lines.append("")

    # 漏洞详情
    lines.append("---")
    lines.append("")
    lines.append("## 2. 漏洞风险")
    lines.append("")
    if vulns:
        high = [v for v in vulns if v.get("Necessity") == "asap"]
        med = [v for v in vulns if v.get("Necessity") == "later"]
        low = [v for v in vulns if v.get("Necessity") not in ("asap", "later")]
        lines.append(f"- 🔴 高危: {len(high)} 个")
        lines.append(f"- 🟡 中危: {len(med)} 个")
        lines.append(f"- 🟢 低危: {len(low)} 个")
        lines.append("")
        for v in vulns[:10]:
            vname = v.get("AliasName") or v.get("Name", "-")
            host = v.get("InstanceName", "-")
            nec = v.get("Necessity", "-")
            lines.append(f"- **{vname}** @ {host} " f"(紧急度: {nec})")
        if len(vulns) > 10:
            lines.append(f"\n> 仅显示前 10 条，" f"共 {len(vulns)} 条")
    else:
        lines.append("未发现相关漏洞。✅")
    lines.append("")

    # 基线详情
    lines.append("---")
    lines.append("")
    lines.append("## 3. 基线检查")
    lines.append("")
    if baseline:
        if base_at_risk:
            total_high = sum(int(m.get("HighWarningCount") or 0) for m in base_at_risk)
            total_med = sum(int(m.get("MediumWarningCount") or 0) for m in base_at_risk)
            lines.append(
                f"🔴 **{len(base_at_risk)} 个风险项未通过基线检查"
                f"（高危: {total_high}，中危: {total_med}）：**"
            )
            lines.append("")
            for m in base_at_risk[:10]:
                name = (
                    m.get("CheckName") or m.get("RiskName") or m.get("Name") or "-"
                )
                high = int(m.get("HighWarningCount") or 0)
                med = int(m.get("MediumWarningCount") or 0)
                lines.append(f"- **{name}**: 高危 {high} / 中危 {med}")
            if len(base_at_risk) > 10:
                lines.append(f"\n> 仅显示前 10 条，共 {len(base_at_risk)} 条")
            lines.append("")
        else:
            lines.append("基线检查通过。✅")
    else:
        lines.append("未发现基线检查记录。")
    lines.append("")

    # 告警详情
    lines.append("---")
    lines.append("")
    lines.append("## 4. 安全告警")
    lines.append("")
    if alerts:
        for a in alerts[:10]:
            aname = a.get("AlarmEventName") or a.get("Name", "-")
            host = a.get("InstanceName", "-")
            level = a.get("Level", "-")
            lines.append(f"- **{aname}** @ {host} " f"(级别: {level})")
        if len(alerts) > 10:
            lines.append(f"\n> 仅显示前 10 条，" f"共 {len(alerts)} 条")
    else:
        lines.append("未发现安全告警。✅")
    lines.append("")

    # 建议
    lines.append("---")
    lines.append("")
    lines.append("## 5. 安全建议")
    lines.append("")
    recommendations = []
    if vulns:
        recommendations.append(
            "1. **漏洞修复**: 优先处理高危漏洞，" "参考 remediation_guide.md"
        )
    if base_at_risk:
        recommendations.append(
            "2. **基线加固**: 修复基线不合规项，" "特别关注弱口令和权限配置"
        )
    if alerts:
        recommendations.append("3. **告警处置**: 及时处理安全告警，" "排查可疑行为")
    recommendations.append(
        f"{len(recommendations) + 1}. "
        "**安全护栏**: 安装阿里云安全护栏，"
        "实时拦截高危命令和异常行为"
    )
    if not any("漏洞" in r for r in recommendations):
        if not any("基线" in r for r in recommendations):
            if not any("告警" in r for r in recommendations):
                if len(recommendations) == 1:
                    recommendations.insert(0, "当前安全状态良好，" "建议保持定期巡检。")
    lines.extend(recommendations)
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    client = SasClient(region=args.region)

    print("[*] 开始生成 OpenClaw 安全日报...")

    # 依次查询
    instances = _safe_query(
        "实例",
        lambda: client.describe_property_sca_detail(
            biz=args.biz,
            sca_name_pattern=args.name_pattern,
        ),
    )

    vulns = _safe_query(
        "漏洞",
        lambda: client.describe_vul_list(
            vul_type="emg",
            dealed="n",
            name=args.vuln_name,
        ),
    )

    baseline = _safe_query(
        "基线",
        lambda: client.describe_check_warning_summary().get("WarningSummarys", []),
    )

    alerts = _safe_query(
        "告警",
        lambda: client.describe_susp_events(
            dealed="N",
        ),
    )

    # 生成报告
    report = generate_report(
        instances,
        vulns,
        baseline,
        alerts,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    md_path = out_dir / f"security_report_{date_str}.md"
    md_path.write_text(report, encoding="utf-8")
    print(f"[+] 安全日报 → {md_path}")

    # 同时保存原始数据
    raw = {
        "generated_at": datetime.now().isoformat(),
        "instances": instances,
        "vulns": vulns,
        "baseline": baseline,
        "alerts": alerts,
    }
    json_path = out_dir / f"security_report_{date_str}.json"
    json_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] 原始数据 → {json_path}")
    print("[+] 安全日报生成完成！")


if __name__ == "__main__":
    main()
