#!/usr/bin/env python3
"""Generate a safe cleanup plan for ECS snapshots.

Identifies candidate snapshots for deletion or archiving based on age, retention
settings, and Usage dependencies. Does not perform any destructive actions.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a snapshot cleanup plan without deleting anything."
    )
    parser.add_argument(
        "--input", "-i", required=True, type=Path,
        help="Path to JSON file containing snapshot data."
    )
    parser.add_argument(
        "--retention-days", type=int, default=30,
        help="Number of days to retain snapshots (default: 30)."
    )
    parser.add_argument(
        "--min-age-days", type=int, default=7,
        help="Minimum age in days before a snapshot can be considered for deletion (default: 7)."
    )
    parser.add_argument(
        "--archive-threshold-days", type=int, default=60,
        help="Minimum age to consider archiving instead of deleting (default: 60)."
    )
    parser.add_argument(
        "--protect-tags", default="",
        help="Comma-separated list of tag keys that protect snapshots from deletion."
    )
    parser.add_argument(
        "--price-standard", type=float, default=0.12,
        help="Standard snapshot monthly unit price for savings estimate (default: 0.12)."
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


def parse_time(time_str: str) -> datetime:
    """Parse ISO 8601 timestamp."""
    if time_str.endswith("Z"):
        time_str = time_str[:-1] + "+00:00"
    return datetime.fromisoformat(time_str)


def snapshot_age_days(snapshot: dict) -> float:
    creation_time = snapshot.get("CreationTime")
    if not creation_time:
        return 0.0
    created = parse_time(creation_time)
    now = datetime.now(timezone.utc)
    return (now - created).total_seconds() / 86400


def snapshot_size_gib(snapshot: dict) -> float:
    size = snapshot.get("SourceDiskSize")
    if size is None:
        size_bytes = snapshot.get("FullSnapshotSizeInBytes", 0)
        return size_bytes / (1024 ** 3)
    return float(size)


def has_protected_tag(snapshot: dict, protected_keys: set) -> bool:
    tags = snapshot.get("Tags", {}).get("Tag", [])
    if isinstance(tags, dict):
        tags = [tags]
    for tag in tags:
        if tag.get("TagKey") in protected_keys:
            return True
    return False


def build_plan(snapshots, retention_days, min_age_days, archive_threshold_days, protected_keys, price_standard):
    candidates = []
    protected = []
    total_gib = 0.0
    savings_gib = 0.0

    for snap in snapshots:
        size = snapshot_size_gib(snap)
        age = snapshot_age_days(snap)
        total_gib += size
        usage = snap.get("Usage", "none")
        snap_id = snap.get("SnapshotId", "unknown")

        if has_protected_tag(snap, protected_keys):
            protected.append({"id": snap_id, "reason": "protected tag"})
            continue

        if usage in ("image", "disk", "image_disk"):
            protected.append({"id": snap_id, "reason": f"used by {usage}"})
            continue

        if age < min_age_days:
            protected.append({"id": snap_id, "reason": f"too young ({age:.1f} days)"})
            continue

        category = snap.get("Category", "standard")
        action = "delete"
        if category != "archive" and age >= archive_threshold_days:
            action = "archive"

        reason = f"age {age:.1f} days exceeds retention ({retention_days} days)"
        if action == "archive":
            reason += " and meets archive threshold"
        elif category == "archive":
            reason += "; already archived, consider deletion"

        candidates.append({
            "id": snap_id,
            "action": action,
            "age_days": round(age, 1),
            "size_gib": round(size, 2),
            "reason": reason,
        })
        savings_gib += size

    savings_cny_monthly = savings_gib * price_standard
    return {
        "summary": {
            "total_snapshots": len(snapshots),
            "total_capacity_gib": round(total_gib, 2),
            "candidates_count": len(candidates),
            "protected_count": len(protected),
            "potential_savings_gib": round(savings_gib, 2),
            "potential_savings_cny_monthly": round(savings_cny_monthly, 4),
        },
        "candidates": candidates,
        "protected": protected,
    }


def print_table(plan):
    s = plan["summary"]
    print("=" * 70)
    print("Snapshot Cleanup Plan")
    print("=" * 70)
    print(f"Total snapshots:     {s['total_snapshots']}")
    print(f"Total capacity:      {s['total_capacity_gib']} GiB")
    print(f"Candidates:          {s['candidates_count']}")
    print(f"Protected:           {s['protected_count']}")
    print(f"Potential savings:   {s['potential_savings_gib']} GiB (~{s['potential_savings_cny_monthly']} CNY/month at standard price)")
    print("-" * 70)
    if plan["candidates"]:
        print(f"{'Action':<10} {'SnapshotId':<30} {'Age':<10} {'Size':<8} Reason")
        print("-" * 70)
        for c in plan["candidates"]:
            print(f"{c['action']:<10} {c['id']:<30} {c['age_days']:<10} {c['size_gib']:<8} {c['reason']}")
    if plan["protected"]:
        print("\nProtected snapshots:")
        for p in plan["protected"]:
            print(f"  {p['id']}: {p['reason']}")
    print("=" * 70)
    print("This script does not delete or archive anything. Review the list before acting.")


def main():
    args = parse_args()
    protected_keys = {k.strip() for k in args.protect_tags.split(",") if k.strip()}

    try:
        snapshots = load_snapshots(args.input)
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    plan = build_plan(
        snapshots,
        args.retention_days,
        args.min_age_days,
        args.archive_threshold_days,
        protected_keys,
        args.price_standard,
    )

    if args.output == "json":
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        print_table(plan)


if __name__ == "__main__":
    main()
