#!/usr/bin/env python3
"""查询 OpenClaw 实例（SCA 组件）。

用法:
  python -m scripts.query_openclaw_instances
  python -m scripts.query_openclaw_instances \
      --name-pattern openclaw --biz sca_ai
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.sas_client import SasClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="查询 OpenClaw 实例（SCA 组件）")
    parser.add_argument(
        "--name-pattern",
        default="openclaw",
        help="组件名称模糊匹配（默认: openclaw）",
    )
    parser.add_argument(
        "--biz",
        default="sca_ai",
        help="业务类型（默认: sca_ai）",
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


def format_markdown(instances: list[dict]) -> str:
    """将实例列表格式化为 Markdown。"""
    lines = [
        "# OpenClaw 实例查询结果",
        "",
        f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"实例总数: {len(instances)}",
        "",
    ]

    if not instances:
        lines.append("未发现 OpenClaw 实例。")
        return "\n".join(lines)

    lines.append(
        "| 序号 | 主机名 | IP | "
        "ListenIp+Port | InstanceId | UUID | "
        "组件名 | 版本 | 路径 |"
    )
    lines.append(
        "|------|--------|-----|"
        "---------------|------------|------|"
        "--------|------|------|"
    )

    for i, inst in enumerate(instances, 1):
        host = inst.get("InstanceName", "-")
        ip = inst.get("Ip") or inst.get("InternetIp", "-")
        name = inst.get("Name", "-")
        ver = inst.get("Version", "-")
        path = inst.get("Path", "-")
        listen_ip = inst.get("ListenIp", "-")
        port = inst.get("Port", "-")
        listen = f"{listen_ip}:{port}"
        instance_id = inst.get("InstanceId", "-")
        uuid = inst.get("Uuid", "-")
        lines.append(
            f"| {i} | {host} | {ip} "
            f"| {listen} | {instance_id} | {uuid} "
            f"| {name} | {ver} | {path} |"
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    client = SasClient(region=args.region)

    print(f"[*] 查询 OpenClaw 实例 " f"(pattern={args.name_pattern}, biz={args.biz})")

    instances = client.describe_property_sca_detail(
        biz=args.biz,
        sca_name_pattern=args.name_pattern,
        max_pages=args.max_pages,
    )

    print(f"[+] 发现 {len(instances)} 个实例")

    # 输出
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "openclaw_instances.json"
    json_path.write_text(
        json.dumps(instances, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] JSON → {json_path}")

    md_path = out_dir / "openclaw_instances.md"
    md_path.write_text(format_markdown(instances), encoding="utf-8")
    print(f"[+] Markdown → {md_path}")


if __name__ == "__main__":
    main()
