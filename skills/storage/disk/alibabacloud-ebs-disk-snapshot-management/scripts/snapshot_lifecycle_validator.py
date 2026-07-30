#!/usr/bin/env python3
"""Validate preconditions for ECS snapshot lifecycle operations.

Performs local checks against a JSON state file. Does not call Alibaba Cloud APIs.
"""

import argparse
import json
import sys
from pathlib import Path


VALID_OPERATIONS = ["create", "delete", "rollback", "policy", "group"]
VALID_DISK_STATUSES = ["In_use", "Available"]
VALID_INSTANCE_STATUSES = ["Running", "Stopped"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate preconditions for snapshot operations."
    )
    parser.add_argument(
        "--operation", "-o", required=True, choices=VALID_OPERATIONS,
        help="Operation to validate."
    )
    parser.add_argument(
        "--disk-id", help="Disk ID for create/rollback operations."
    )
    parser.add_argument(
        "--snapshot-id", help="Snapshot ID for delete/rollback operations."
    )
    parser.add_argument(
        "--instance-id", help="Instance ID for group/rollback operations."
    )
    parser.add_argument(
        "--region", help="Region ID for policy/group/list operations."
    )
    parser.add_argument(
        "--input", "-i", type=Path,
        help="Optional JSON state file with disks, instances, snapshots."
    )
    parser.add_argument(
        "--output", choices=["table", "json"], default="table",
        help="Output format (default: table)."
    )
    return parser.parse_args()


def load_state(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_resource(state: dict, resource_type: str, resource_id: str):
    """Locate a resource in the state file."""
    if resource_type not in state:
        return None
    for item in state[resource_type]:
        if item.get(f"{resource_type[:-1].capitalize()}Id") == resource_id:
            return item
    return None


def validate_create(state: dict, disk_id: str) -> list:
    issues = []
    disk = find_resource(state, "disks", disk_id) if state else None
    if not disk:
        issues.append(f"Disk {disk_id} not found in state file; verify via DescribeDisks.")
        return issues
    if disk.get("Status") not in VALID_DISK_STATUSES:
        issues.append(f"Disk status is {disk.get('Status')}; must be In_use or Available.")
    if disk.get("Status") == "In_use":
        instance_id = disk.get("InstanceId")
        instance = find_resource(state, "instances", instance_id) if instance_id else None
        if instance and instance.get("Status") not in VALID_INSTANCE_STATUSES:
            issues.append(f"Attached instance {instance_id} status is {instance.get('Status')}; must be Running or Stopped.")
    return issues


def validate_delete(state: dict, snapshot_id: str) -> list:
    issues = []
    snapshot = find_resource(state, "snapshots", snapshot_id) if state else None
    if not snapshot:
        issues.append(f"Snapshot {snapshot_id} not found in state file; verify via DescribeSnapshots.")
        return issues
    usage = snapshot.get("Usage", "none")
    if usage in ("image", "image_disk"):
        issues.append(f"Snapshot is used by custom image; delete image first. Usage={usage}")
    if usage in ("disk", "image_disk"):
        issues.append(f"Snapshot is used by disk; Force=true and explicit confirmation required. Usage={usage}")
    if snapshot.get("Status") == "progressing":
        issues.append("Snapshot is still being created; deletion will cancel the task.")
    return issues


def validate_rollback(state: dict, disk_id: str, snapshot_id: str) -> list:
    issues = []
    disk = find_resource(state, "disks", disk_id) if state else None
    snapshot = find_resource(state, "snapshots", snapshot_id) if state else None

    if not disk:
        issues.append(f"Disk {disk_id} not found in state file; verify via DescribeDisks.")
    if not snapshot:
        issues.append(f"Snapshot {snapshot_id} not found in state file; verify via DescribeSnapshots.")
    if disk and snapshot:
        if snapshot.get("SourceDiskId") != disk_id:
            issues.append("Snapshot was not created from the target disk.")
        if snapshot.get("Status") != "accomplished":
            issues.append("Snapshot is not in accomplished state; wait for creation to finish.")
        if snapshot.get("Available") is False:
            issues.append("Snapshot is not available for rollback.")
        if disk.get("Encrypted") != snapshot.get("Encrypted"):
            issues.append("Encryption state mismatch between disk and snapshot.")
        instance_id = disk.get("InstanceId")
        if instance_id:
            instance = find_resource(state, "instances", instance_id)
            if instance and instance.get("Status") != "Stopped":
                issues.append(f"Instance {instance_id} must be Stopped before rollback.")
    return issues


def validate_policy(region: str) -> list:
    issues = []
    if not region:
        issues.append("RegionId is required for policy operations.")
    return issues


def validate_group(state: dict, instance_id: str, region: str) -> list:
    issues = []
    if not region:
        issues.append("RegionId is required for snapshot group operations.")
    instance = find_resource(state, "instances", instance_id) if state and instance_id else None
    if instance_id and not instance:
        issues.append(f"Instance {instance_id} not found in state file; verify via DescribeInstances.")
    return issues


def main():
    args = parse_args()
    state = load_state(args.input) if args.input else None

    issues = []
    if args.operation == "create":
        if not args.disk_id:
            issues.append("--disk-id is required for create validation.")
        else:
            issues.extend(validate_create(state, args.disk_id))
    elif args.operation == "delete":
        if not args.snapshot_id:
            issues.append("--snapshot-id is required for delete validation.")
        else:
            issues.extend(validate_delete(state, args.snapshot_id))
    elif args.operation == "rollback":
        if not args.disk_id or not args.snapshot_id:
            issues.append("--disk-id and --snapshot-id are required for rollback validation.")
        else:
            issues.extend(validate_rollback(state, args.disk_id, args.snapshot_id))
    elif args.operation == "policy":
        issues.extend(validate_policy(args.region))
    elif args.operation == "group":
        if not args.instance_id:
            issues.append("--instance-id is required for group validation.")
        else:
            issues.extend(validate_group(state, args.instance_id, args.region))

    result = {
        "operation": args.operation,
        "valid": len(issues) == 0,
        "issues": issues,
    }

    if args.output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status = "VALID" if result["valid"] else "INVALID"
        print(f"Validation result for '{args.operation}': {status}")
        if issues:
            print("Issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("No blocking issues found based on provided state.")

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
