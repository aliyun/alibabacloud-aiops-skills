#!/usr/bin/env python3
"""查询 OpenClaw 相关漏洞。

用法:
  python -m scripts.check_openclaw_vulns
  python -m scripts.check_openclaw_vulns \
      --type emg --dealed n
  python -m scripts.check_openclaw_vulns \
      --name "emg:SCA:AVD-2026-1860246" --type emg
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
    parser = argparse.ArgumentParser(description="查询 OpenClaw 相关漏洞")
    parser.add_argument(
        "--name",
        default="emg:SCA:AVD-2026-1860246",
        help="漏洞名称精确匹配" "（默认: emg:SCA:AVD-2026-1860246）",
    )
    parser.add_argument(
        "--type",
        default="emg",
        help="漏洞类型: cve/sys/cms/emg（默认: emg）",
    )
    parser.add_argument(
        "--dealed",
        default="n",
        help="是否已处理: y/n（默认: n）",
    )
    parser.add_argument(
        "--necessity",
        default=None,
        help="修复紧急度过滤",
    )
    parser.add_argument(
        "--uuids",
        default=None,
        help="指定主机 UUID（逗号分隔）",
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


def format_markdown(vulns: list[dict]) -> str:
    """将漏洞列表格式化为 Markdown。"""
    lines = [
        "# OpenClaw 漏洞查询结果",
        "",
        f"查询时间: " f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"漏洞总数: {len(vulns)}",
        "",
    ]

    if not vulns:
        lines.append("未发现相关漏洞。")
        return "\n".join(lines)

    # 按严重程度分组
    high, medium, low = [], [], []
    for v in vulns:
        necessity = v.get("Necessity", "")
        if necessity == "asap":
            high.append(v)
        elif necessity == "later":
            medium.append(v)
        else:
            low.append(v)

    for label, group in [
        ("🔴 高危", high),
        ("🟡 中危", medium),
        ("🟢 低危", low),
    ]:
        if not group:
            continue
        lines.append(f"## {label}（{len(group)} 个）")
        lines.append("")
        lines.append(
            "| 漏洞名称 | 主机/IP | 区域 | 版本命中条件 | "
            "当前版本 | 首次发现 | 状态 |"
        )
        lines.append(
            "|----------|---------|------|--------------|"
            "----------|----------|------|"
        )
        for v in group:
            vname = v.get("AliasName") or v.get("Name", "-")
            host = v.get("InstanceName", "-")
            ip = v.get("InternetIp") or v.get("IntranetIp") or "-"
            host_ip = f"{host}/{ip}"
            region = v.get("RegionId", "-")
            first = _format_ts(v.get("FirstTs"))
            status = "已处理" if v.get("Status") == 0 else "未处理"
            if v.get("RealRisk") is True:
                status = f"{status}（真实风险）"

            match_expr, full_version = _extract_version_info(v)
            lines.append(
                f"| {vname} | {host_ip} | {region} | "
                f"{match_expr} | {full_version} | {first} | {status} |"
            )
        lines.append("")

        lines.append("### 详情")
        lines.append("")
        for i, v in enumerate(group, 1):
            vname = v.get("AliasName") or v.get("Name", "-")
            name = v.get("Name", "-")
            uuid = v.get("Uuid", "-")
            primary_id = v.get("PrimaryId", "-")
            last = _format_ts(v.get("LastTs"))
            match_expr, full_version = _extract_version_info(v)
            lines.append(f"{i}. **{vname}**")
            lines.append(f"   - 漏洞ID: `{name}` / PrimaryId: `{primary_id}`")
            lines.append(f"   - UUID: `{uuid}`，最近发现: {last}")
            lines.append(f"   - 命中条件: `{match_expr}`，当前版本: `{full_version}`")
        lines.append("")

    return "\n".join(lines)


def _format_ts(ts: object) -> str:
    """毫秒时间戳转可读时间。"""
    if ts is None:
        return "-"
    try:
        value = int(ts)
        # 返回为毫秒时间戳
        if value > 10_000_000_000:
            value = value // 1000
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return str(ts)


def _extract_version_info(vuln: dict) -> tuple[str, str]:
    """提取版本命中条件和当前版本。"""
    extend = vuln.get("ExtendContentJson", {})
    if not isinstance(extend, dict):
        return "-", "-"
    rpm_list = extend.get("RpmEntityList", [])
    if not isinstance(rpm_list, list) or not rpm_list:
        return "-", "-"
    entity = rpm_list[0] if isinstance(rpm_list[0], dict) else {}
    match_list = entity.get("MatchList", [])
    match_expr = "-"
    if isinstance(match_list, list) and match_list:
        match_expr = str(match_list[0])
    full_version = entity.get("FullVersion") or entity.get("Version") or "-"
    return match_expr, str(full_version)


def main() -> None:
    args = parse_args()
    client = SasClient(region=args.region)

    params = f"type={args.type}, dealed={args.dealed}"
    if args.name:
        params += f", name={args.name}"
    print(f"[*] 查询漏洞 ({params})")

    vulns = client.describe_vul_list(
        vul_type=args.type,
        dealed=args.dealed,
        name=args.name,
        necessity=args.necessity,
        uuids=args.uuids,
        max_pages=args.max_pages,
    )

    print(f"[+] 发现 {len(vulns)} 个漏洞")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "openclaw_vulns.json"
    json_path.write_text(
        json.dumps(vulns, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] JSON → {json_path}")

    md_path = out_dir / "openclaw_vulns.md"
    md_path.write_text(format_markdown(vulns), encoding="utf-8")
    print(f"[+] Markdown → {md_path}")

    if len(vulns) > 0:
        print()
        print(
            "[!] 安全加固建议: 当前存在未修复漏洞，"
            "请阅读 remediation_guide.md 进行修复"
        )
        print("[!] 修复指南: references/remediation_guide.md")


if __name__ == "__main__":
    main()
