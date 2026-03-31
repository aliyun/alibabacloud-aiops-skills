#!/usr/bin/env python3
"""按 UUID 查询云安全中心资产详情。

用法:
  python -m scripts.query_asset_detail --uuid <UUID>
  python -m scripts.query_asset_detail --uuid <UUID1>,<UUID2>,...
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
    parser = argparse.ArgumentParser(
        description="按 UUID 查询云安全中心资产详情"
    )
    parser.add_argument(
        "--uuid",
        required=True,
        help="资产 UUID，多个用逗号分隔",
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


def format_markdown(results: list[dict]) -> str:
    """将资产详情列表格式化为 Markdown。"""
    lines = [
        "# 资产详情查询结果",
        "",
        f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"查询数量: {len(results)}",
        "",
    ]

    for asset in results:
        uuid = asset.get("Uuid", "-")
        lines += [
            f"## {asset.get('HostName', '-')}  `{uuid}`",
            "",
            "| 字段 | 值 |",
            "|------|-----|",
            f"| 主机名 | `{asset.get('HostName', '-')}` |",
            f"| 实例 ID | `{asset.get('InstanceId', '-')}` |",
            f"| 实例名 | `{asset.get('InstanceName', '-')}` |",
            f"| 公网 IP | `{asset.get('InternetIp', '-')}` |",
            f"| 内网 IP | `{asset.get('IntranetIp', '-')}` |",
            f"| 操作系统 | {asset.get('OsName', '-')} |",
            f"| 内核 | `{asset.get('Kernel', '-')}` |",
            f"| CPU | {asset.get('Cpu', '-')} 核  ({asset.get('CpuInfo', '-')}) |",
            f"| 内存 | {asset.get('Mem', '-')} GB |",
            f"| 区域 | {asset.get('RegionName', '-')} (`{asset.get('RegionId', '-')}`) |",
            f"| 客户端状态 | `{asset.get('ClientStatus', '-')}` |",
            f"| 客户端版本 | `{asset.get('ClientVersion', '-')}` |",
            f"| 授权版本 | {asset.get('AuthVersion', '-')} |",
            f"| 分组 | {asset.get('GroupTrace', '-')} |",
            "",
        ]

        disk_list = asset.get("DiskInfoList", [])
        if disk_list:
            lines += [
                "**磁盘**",
                "",
                "| 设备 | 总容量(GB) | 已用(GB) |",
                "|------|-----------|---------|",
            ]
            for d in disk_list:
                lines.append(
                    f"| `{d.get('DiskName', '-')}` "
                    f"| {d.get('TotalSize', '-')} "
                    f"| {d.get('UseSize', '-')} |"
                )
            lines.append("")

        ip_list = asset.get("IpList", [])
        if ip_list:
            lines.append(f"**全部 IP**: {', '.join(f'`{ip}`' for ip in ip_list)}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    client = SasClient(region=args.region)

    uuids = [u.strip() for u in args.uuid.split(",") if u.strip()]
    print(f"[*] 查询 {len(uuids)} 个资产详情")

    results: list[dict] = []
    for uuid in uuids:
        print(f"    UUID: {uuid}")
        asset = client.get_asset_detail_by_uuid(uuid)
        results.append(asset)
        print(f"    主机名: {asset.get('HostName', '-')}  "
              f"IP: {asset.get('InternetIp') or asset.get('IntranetIp', '-')}  "
              f"状态: {asset.get('ClientStatus', '-')}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "asset_detail.json"
    json_path.write_text(
        json.dumps(
            {"queried_at": datetime.now().isoformat(), "assets": results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[+] JSON → {json_path}")

    md_path = out_dir / "asset_detail.md"
    md_path.write_text(format_markdown(results), encoding="utf-8")
    print(f"[+] Markdown → {md_path}")


if __name__ == "__main__":
    main()
