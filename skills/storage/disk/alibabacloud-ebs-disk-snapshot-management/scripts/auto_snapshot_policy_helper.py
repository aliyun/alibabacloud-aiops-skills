#!/usr/bin/env python3
"""Helper for building and validating ECS automatic snapshot policy parameters.

Generates valid RepeatWeekdays, TimePoints, and RetentionDays values plus sample
Alibaba Cloud CLI and SDK calls.
"""

import argparse
import json
import sys


DAYS_OF_WEEK = {
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build and validate ECS auto snapshot policy parameters."
    )
    parser.add_argument(
        "--weekdays", "-w", required=True,
        help="Comma-separated weekdays: 1-7 or mon-sun (e.g., mon,wed,fri or 2,4,6)."
    )
    parser.add_argument(
        "--timepoints", "-t", required=True,
        help="Comma-separated hours 0-23 in UTC+8 (e.g., 2,14)."
    )
    parser.add_argument(
        "--retention-days", "-r", required=True, type=int,
        help="Retention days: -1 for permanent, or 1-65535."
    )
    parser.add_argument(
        "--name", "-n", default="my-auto-snapshot-policy",
        help="Policy name (default: my-auto-snapshot-policy)."
    )
    parser.add_argument(
        "--region", default="cn-hangzhou",
        help="Region for sample commands (default: cn-hangzhou)."
    )
    parser.add_argument(
        "--disk-ids", default="",
        help="Comma-separated disk IDs for the apply-auto-snapshot-policy sample."
    )
    parser.add_argument(
        "--output", "-o", choices=["table", "json"], default="table",
        help="Output format (default: table)."
    )
    return parser.parse_args()


def parse_weekdays(weekdays_str: str) -> list:
    values = []
    seen = set()
    for token in weekdays_str.split(","):
        token = token.strip().lower()
        if token not in DAYS_OF_WEEK:
            raise ValueError(f"Invalid weekday: {token}. Use 1-7 or mon-sun.")
        val = DAYS_OF_WEEK[token]
        if val not in seen:
            values.append(val)
            seen.add(val)
    return sorted(values)


def parse_timepoints(timepoints_str: str) -> list:
    values = []
    seen = set()
    for token in timepoints_str.split(","):
        token = token.strip()
        if not token.isdigit():
            raise ValueError(f"Invalid time point: {token}. Use integers 0-23.")
        val = int(token)
        if val < 0 or val > 23:
            raise ValueError(f"Time point out of range: {val}. Use 0-23.")
        if val not in seen:
            values.append(val)
            seen.add(val)
    return sorted(values)


def validate_retention_days(days: int):
    if days == -1:
        return
    if days < 1 or days > 65535:
        raise ValueError("RetentionDays must be -1 or between 1 and 65535.")


def build_policy_params(weekdays, timepoints, retention_days, name):
    return {
        "RegionId": "<region>",
        "AutoSnapshotPolicyName": name,
        "RepeatWeekdays": json.dumps([str(d) for d in weekdays], ensure_ascii=False),
        "TimePoints": json.dumps([str(t) for t in timepoints], ensure_ascii=False),
        "RetentionDays": retention_days,
    }


def print_table(params, region, disk_ids, weekdays, timepoints):
    print("=" * 60)
    print("Auto Snapshot Policy Parameters")
    print("=" * 60)
    print(f"Name:           {params['AutoSnapshotPolicyName']}")
    print(f"RepeatWeekdays: {params['RepeatWeekdays']}")
    print(f"TimePoints:     {params['TimePoints']}")
    print(f"RetentionDays:  {params['RetentionDays']}")
    print("-" * 60)
    print("Create policy (Alibaba Cloud CLI):")
    print(f"""
aliyun ecs create-auto-snapshot-policy \\
  --regionId {region} \\
  --autoSnapshotPolicyName {params['AutoSnapshotPolicyName']} \\
  --repeatWeekdays '{params['RepeatWeekdays']}' \\
  --timePoints '{params['TimePoints']}' \\
  --retentionDays {params['RetentionDays']} \\
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-snapshot-management/{{session-id}}
""".strip())
    if disk_ids:
        print("-" * 60)
        print("Apply policy to disks (Alibaba Cloud CLI):")
        print(f"""
aliyun ecs apply-auto-snapshot-policy \\
  --regionId {region} \\
  --autoSnapshotPolicyId <policy-id-from-create-response> \\
  --diskIds '{json.dumps(disk_ids, ensure_ascii=False)}' \\
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-snapshot-management/{{session-id}}
""".strip())
    print("=" * 60)
    print(f"Schedule summary: {len(weekdays)} day(s) per week at {timepoints} o'clock UTC+8.")


def main():
    args = parse_args()
    try:
        weekdays = parse_weekdays(args.weekdays)
        timepoints = parse_timepoints(args.timepoints)
        validate_retention_days(args.retention_days)
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    params = build_policy_params(weekdays, timepoints, args.retention_days, args.name)
    disk_ids = [d.strip() for d in args.disk_ids.split(",") if d.strip()]

    if args.output == "json":
        result = {
            "parameters": params,
            "sample_region": args.region,
            "sample_disk_ids": disk_ids,
            "schedule_summary": {
                "weekday_count": len(weekdays),
                "time_points": timepoints,
            },
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_table(params, args.region, disk_ids, weekdays, timepoints)


if __name__ == "__main__":
    main()
