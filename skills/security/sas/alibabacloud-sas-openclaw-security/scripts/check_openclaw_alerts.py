#!/usr/bin/env python3
"""查询 OpenClaw 相关告警。

用法:
  python -m scripts.check_openclaw_alerts
  python -m scripts.check_openclaw_alerts \
      --uuids <UUID> --dealed N
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.sas_client import SasClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="查询 OpenClaw 相关告警")
    parser.add_argument(
        "--dealed",
        default="N",
        help="是否已处理: Y/N（默认: N）",
    )
    parser.add_argument(
        "--levels",
        default=None,
        help="告警级别过滤 (serious/suspicious/remind)",
    )
    parser.add_argument(
        "--uuids",
        default=None,
        help="指定主机 UUID（逗号分隔）",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="告警名称过滤",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="区域（默认: cn-shanghai）",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="最大翻页数（默认: 3）",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录（默认: output）",
    )
    return parser.parse_args()


def format_markdown(alerts: list[dict]) -> str:
    """将告警列表格式化为 Markdown。"""
    lines = [
        "# OpenClaw 告警查询结果",
        "",
        f"查询时间: " f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"告警总数: {len(alerts)}",
        "",
    ]

    if not alerts:
        lines.append("未发现相关告警。")
        return "\n".join(lines)

    # 按级别分组
    level_map = {
        "serious": ("🔴 紧急", []),
        "suspicious": ("🟡 可疑", []),
        "remind": ("🟢 提醒", []),
    }
    other = []

    for a in alerts:
        level = a.get("Level", "").lower()
        if level in level_map:
            level_map[level][1].append(a)
        else:
            other.append(a)

    for level_key in ["serious", "suspicious", "remind"]:
        label, group = level_map[level_key]
        if not group:
            continue
        lines.append(f"## {label}（{len(group)} 个）")
        lines.append("")
        lines.append("| 告警名称 | 主机名 | IP | " "首次发现 | 最近发现 |")
        lines.append("|----------|--------|-----|" "----------|----------|")
        for a in group:
            aname = a.get("AlarmEventName") or a.get("Name", "-")
            host = a.get("InstanceName", "-")
            ip = a.get("IntranetIp") or a.get("InternetIp") or "-"
            first = a.get("OccurrenceTime", "-")
            last = a.get("LastTime", "-")
            lines.append(f"| {aname} | {host} | {ip} " f"| {first} | {last} |")
        lines.append("")

    if other:
        lines.append(f"## 其他（{len(other)} 个）")
        lines.append("")
        for a in other:
            aname = a.get("Name", "-")
            host = a.get("InstanceName", "-")
            lines.append(f"- {aname} @ {host}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    client = SasClient(region=args.region)

    params = f"dealed={args.dealed}"
    if args.uuids:
        params += f", uuids={args.uuids}"
    if args.levels:
        params += f", levels={args.levels}"
    print(f"[*] 查询告警 ({params})")

    alerts = client.describe_susp_events(
        dealed=args.dealed,
        levels=args.levels,
        uuids=args.uuids,
        name=args.name,
        max_pages=args.max_pages,
    )

    print(f"[+] 发现 {len(alerts)} 个告警")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "openclaw_alerts.json"
    json_path.write_text(
        json.dumps(alerts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] JSON → {json_path}")

    md_path = out_dir / "openclaw_alerts.md"
    md_path.write_text(format_markdown(alerts), encoding="utf-8")
    print(f"[+] Markdown → {md_path}")

    if len(alerts) > 0:
        print()
        print(
            "[!] 安全加固建议: 当前存在未处理告警，"
            "请阅读 remediation_guide.md 进行修复"
        )
        print("[!] 修复指南: references/remediation_guide.md")


if __name__ == "__main__":
    main()
