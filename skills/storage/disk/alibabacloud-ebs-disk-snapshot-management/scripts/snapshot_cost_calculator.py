#!/usr/bin/env python3
"""Estimate Alibaba Cloud ECS snapshot storage costs.

Reads a JSON snapshot list (DescribeSnapshots response format) and calculates
estimated hourly, daily, and monthly costs for standard and archive snapshots.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


DEFAULT_PRICE_STANDARD = 0.12  # CNY/GiB/month (example price)
DEFAULT_PRICE_ARCHIVE = 0.06   # CNY/GiB/month (example price)
HOURS_PER_MONTH = 24 * 30


def parse_args():
    parser = argparse.ArgumentParser(
        description="Estimate ECS snapshot storage costs from a snapshot JSON list."
    )
    parser.add_argument(
        "--input", "-i", required=True, type=Path,
        help="Path to JSON file containing snapshot data."
    )
    parser.add_argument(
        "--region", "-r", default="cn-hangzhou",
        help="Region for pricing context (default: cn-hangzhou)."
    )
    parser.add_argument(
        "--price-standard", type=float, default=DEFAULT_PRICE_STANDARD,
        help=f"Standard snapshot monthly unit price in CNY/GiB (default: {DEFAULT_PRICE_STANDARD})."
    )
    parser.add_argument(
        "--price-archive", type=float, default=DEFAULT_PRICE_ARCHIVE,
        help=f"Archive snapshot monthly unit price in CNY/GiB (default: {DEFAULT_PRICE_ARCHIVE})."
    )
    parser.add_argument(
        "--hours", type=float, default=HOURS_PER_MONTH,
        help=f"Billing duration in hours (default: {HOURS_PER_MONTH})."
    )
    parser.add_argument(
        "--output", "-o", choices=["table", "json"], default="table",
        help="Output format (default: table)."
    )
    return parser.parse_args()


def load_snapshots(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    snapshots = data
    if isinstance(data, dict):
        if "Snapshots" in data:
            snapshots = data["Snapshots"]
            if isinstance(snapshots, dict) and "Snapshot" in snapshots:
                snapshots = snapshots["Snapshot"]
        elif "Snapshot" in data:
            snapshots = data["Snapshot"]

    if not isinstance(snapshots, list):
        raise ValueError("Input JSON does not contain a recognizable snapshot list.")
    return snapshots


def snapshot_size(snapshot: dict) -> float:
    """Return snapshot size in GiB."""
    size = snapshot.get("SourceDiskSize")
    if size is None:
        size_bytes = snapshot.get("FullSnapshotSizeInBytes", 0)
        return size_bytes / (1024 ** 3)
    return float(size)


def calculate_costs(snapshots, price_standard, price_archive, hours):
    by_category = defaultdict(lambda: {"count": 0, "gib": 0.0})
    by_disk = defaultdict(lambda: {"standard": 0.0, "archive": 0.0})

    for snap in snapshots:
        category = snap.get("Category", "standard").lower()
        if category not in ("standard", "archive"):
            category = "standard"
        size_gib = snapshot_size(snap)
        by_category[category]["count"] += 1
        by_category[category]["gib"] += size_gib

        disk_id = snap.get("SourceDiskId", "unknown")
        by_disk[disk_id][category] += size_gib

    standard_gib = by_category["standard"]["gib"]
    archive_gib = by_category["archive"]["gib"]

    monthly_standard = standard_gib * price_standard
    monthly_archive = archive_gib * price_archive
    monthly_total = monthly_standard + monthly_archive

    ratio = hours / HOURS_PER_MONTH
    cost_for_period = monthly_total * ratio

    return {
        "summary": {
            "region": None,
            "hours": hours,
            "price_standard_cny_per_gib_month": price_standard,
            "price_archive_cny_per_gib_month": price_archive,
            "standard_count": by_category["standard"]["count"],
            "archive_count": by_category["archive"]["count"],
            "standard_gib": round(standard_gib, 2),
            "archive_gib": round(archive_gib, 2),
            "total_gib": round(standard_gib + archive_gib, 2),
            "monthly_standard_cny": round(monthly_standard, 4),
            "monthly_archive_cny": round(monthly_archive, 4),
            "monthly_total_cny": round(monthly_total, 4),
            "period_total_cny": round(cost_for_period, 4),
        },
        "by_disk": {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in by_disk.items()},
    }


def print_table(result):
    s = result["summary"]
    print("=" * 60)
    print("ECS Snapshot Cost Estimate")
    print("=" * 60)
    print(f"Region:              {s.get('region', 'N/A')}")
    print(f"Billing duration:    {s['hours']} hours")
    print(f"Standard price:      {s['price_standard_cny_per_gib_month']} CNY/GiB/month")
    print(f"Archive price:       {s['price_archive_cny_per_gib_month']} CNY/GiB/month")
    print("-" * 60)
    print(f"Standard snapshots:  {s['standard_count']} ({s['standard_gib']} GiB)")
    print(f"Archive snapshots:   {s['archive_count']} ({s['archive_gib']} GiB)")
    print(f"Total capacity:      {s['total_gib']} GiB")
    print("-" * 60)
    print(f"Monthly standard:    {s['monthly_standard_cny']} CNY")
    print(f"Monthly archive:     {s['monthly_archive_cny']} CNY")
    print(f"Monthly total:       {s['monthly_total_cny']} CNY")
    print(f"Cost for period:     {s['period_total_cny']} CNY")
    print("=" * 60)
    print("Note: Prices are examples. See https://www.aliyun.com/price/detail for current rates.")


def main():
    args = parse_args()
    try:
        snapshots = load_snapshots(args.input)
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    result = calculate_costs(
        snapshots,
        args.price_standard,
        args.price_archive,
        args.hours,
    )
    result["summary"]["region"] = args.region

    if args.output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_table(result)


if __name__ == "__main__":
    main()
