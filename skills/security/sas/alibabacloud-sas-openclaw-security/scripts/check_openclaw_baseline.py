#!/usr/bin/env python3
"""查询 OpenClaw 基线检查结果（按 UUID）。

用法:
  python -m scripts.check_openclaw_baseline \
      --uuid xxxxxxxx
  python -m scripts.check_openclaw_baseline \
      --uuid xxxxxxxx --risk-id 320
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
    parser = argparse.ArgumentParser(description="按 UUID 查询 OpenClaw 基线检查结果")
    parser.add_argument(
        "--uuid",
        required=True,
        help="云安全中心实例 UUID",
    )
    parser.add_argument(
        "--risk-id",
        dest="risk_id",
        type=int,
        default=None,
        help="指定风险项 ID（RiskId）；不传仅查询汇总",
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


STATUS_MAP = {
    1: "未通过",
    2: "验证中",
    3: "已通过",
    6: "已忽略",
    8: "已通过",
}


def _append_summary_table(lines: list[str], summary_items: list[dict]) -> None:
    """追加汇总表格。"""
    lines.append("| 序号 | RiskID | 检查项 | 高危 | 中危 | 状态 |")
    lines.append("|------|---------|--------|------|------|------|")
    for i, item in enumerate(summary_items, 1):
        risk_id = item.get("CheckId") or item.get("RiskId") or item.get("Id") or "-"
        name = item.get("CheckName") or item.get("RiskName") or item.get("Name") or "-"
        high_count = int(item.get("HighWarningCount") or 0)
        medium_count = int(item.get("MediumWarningCount") or 0)
        status = "有风险" if (high_count + medium_count) > 0 else "无风险"
        lines.append(
            f"| {i} | {risk_id} | {name} | "
            f"{high_count} | {medium_count} | {status} |"
        )
    lines.append("")


def _extract_list(body: dict) -> list[dict]:
    """尽可能兼容地提取列表字段。"""
    if not isinstance(body, dict):
        return []
    candidates = [
        "WarningSummarys",
        "CheckWarningSummarys",
        "CheckWarningSummaries",
        "CheckWarningSummaryList",
        "CheckWarningSummary",
        "Warnings",
        "CheckWarnings",
        "List",
    ]
    for key in candidates:
        value = body.get(key)
        if isinstance(value, list):
            return value
    return []


def format_markdown(
    uuid: str,
    summary_items: list[dict],
    details: list[dict],
) -> str:
    """将基线检查结果格式化为 Markdown。"""

    def _risk_count(item: dict) -> int:
        return int(item.get("HighWarningCount") or 0) + int(
            item.get("MediumWarningCount") or 0
        )

    at_risk = [item for item in summary_items if _risk_count(item) > 0]
    fixed = [item for item in summary_items if _risk_count(item) == 0]

    detail_total = sum(len(item.get("warnings", [])) for item in details)
    summary_total = len(summary_items)
    if summary_total > 0:
        total_text = f"检查项总数: {summary_total}"
        risk_text = f"有风险: {len(at_risk)} 项 | " f"无风险: {len(fixed)} 项"
    else:
        total_text = f"检查记录总数: {detail_total}"
        risk_text = "按详情模式展示，不统计汇总项风险数"

    lines = [
        "# OpenClaw 基线检查结果",
        "",
        f"查询时间: " f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"UUID: {uuid}",
        total_text,
        risk_text,
        "",
    ]
    if summary_items:
        lines.append("## 汇总")
        lines.append("")
        _append_summary_table(lines, summary_items)
    else:
        lines.append("## 汇总")
        lines.append("")
        lines.append("本次未查询汇总数据（按 risk_id 查询详情模式）。")
        lines.append("")

    lines.append("## 检查项详情")
    lines.append("")
    if not details:
        lines.append("未返回检查项详情。")
        return "\n".join(lines)

    for item in details:
        risk_id = item.get("risk_id", "-")
        warnings = item.get("warnings", [])
        lines.append(f"### RiskId={risk_id}（{len(warnings)} 条）")
        lines.append("")
        if not warnings:
            lines.append("- 无详情记录")
            lines.append("")
            continue

        for w in warnings:
            item_name = (
                w.get("Item")
                or w.get("CheckName")
                or w.get("RiskName")
                or w.get("WarningName")
                or "-"
            )
            item_type = w.get("Type") or w.get("CheckType") or "-"
            check_name = (
                w.get("CheckName")
                or w.get("RiskName")
                or w.get("WarningName")
                or item_name
            )
            status_val = w.get("Status", -1)
            status = STATUS_MAP.get(status_val, str(status_val))
            fix_status_val = w.get("FixStatus", -1)
            fix_status_map = {
                0: "-",
                1: "已修复",
                -1: "-",
            }
            # 业务规则：Status=3（已修复）优先级高于 FixStatus。
            if status_val == 3:
                fix_status = "已修复"
            else:
                fix_status = fix_status_map.get(fix_status_val, str(fix_status_val))
            level = w.get("Level") or w.get("RiskLevel") or "-"
            desc = w.get("Description") or w.get("Desc") or "-"
            lines.append(
                f"- **{item_name}** | 类型: {item_type} | "
                f"级别: {level} | 检查状态: {status} | "
                f"修复状态: {fix_status}"
            )
            if desc != "-":
                lines.append(f"  - 描述: {desc}")
            if check_name != item_name and check_name != "-":
                lines.append(f"  - 检查项: {check_name}")
            check_warning_id = w.get("CheckWarningId")
            if check_warning_id is not None:
                lines.append(f"  - CheckWarningId: {check_warning_id}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    client = SasClient(region=args.region)

    summary_body: dict = {}
    summary_items: list[dict] = []
    details: list[dict] = []

    if args.risk_id is None:
        print(f"[*] 查询基线汇总 (uuid={args.uuid})")
        summary_body = client.describe_check_warning_summary(uuids=args.uuid)
        summary_items = _extract_list(summary_body)
        at_risk = [
            item
            for item in summary_items
            if (item.get("HighWarningCount") or 0)
            + (item.get("MediumWarningCount") or 0)
            > 0
        ]
        fixed = [
            item
            for item in summary_items
            if (item.get("HighWarningCount") or 0)
            + (item.get("MediumWarningCount") or 0)
            == 0
        ]
        print(
            f"[+] 共 {len(summary_items)} 项: "
            f"有风险 {len(at_risk)} 项, "
            f"无风险 {len(fixed)} 项"
        )
    else:
        print(f"[*] 查询基线详情 (uuid={args.uuid}, " f"risk_id={args.risk_id})")
        detail_body = client.describe_check_warnings(
            uuid=args.uuid,
            risk_id=args.risk_id,
        )
        detail_items = _extract_list(detail_body)
        details.append(
            {
                "risk_id": args.risk_id,
                "warnings": detail_items,
                "raw": detail_body,
            }
        )
        print(f"[+] risk_id={args.risk_id} " f"详情 {len(detail_items)} 条")
        at_risk = detail_items

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "openclaw_baseline.json"
    json_path.write_text(
        json.dumps(
            {
                "uuid": args.uuid,
                "query_mode": ("summary" if args.risk_id is None else "detail"),
                "summary": summary_body,
                "details": details,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[+] JSON → {json_path}")

    md_path = out_dir / "openclaw_baseline.md"
    md_path.write_text(
        format_markdown(
            uuid=args.uuid,
            summary_items=summary_items,
            details=details,
        ),
        encoding="utf-8",
    )
    print(f"[+] Markdown → {md_path}")

    if len(at_risk) > 0:
        print()
        print(
            "[!] 安全加固建议: 当前存在基线风险，"
            "请阅读 remediation_guide.md 进行修复"
        )
        print("[!] 修复指南: references/remediation_guide.md")


if __name__ == "__main__":
    main()
