#!/usr/bin/env python3
"""List ECS instances in a region for selection in specific-instance mode.

Usage: list_ecs.py <region>
Exit codes: 0 = success; 2 = no ECS read permission (ask for instance IDs manually
without blocking the flow).
"""
import sys

from common import CloudError, list_all_pages


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: list_ecs.py <region>")
    region = sys.argv[1]

    try:
        insts = list_all_pages(["ecs", "describe-instances", "--region", region, "--biz-region-id", region],
                               "Instances.Instance", "InstanceId")
    except CloudError as exc:
        if not exc.error_code.startswith(("Forbidden", "Unauthorized", "NoPermission")):
            raise
        print(f"NO_PERMISSION: {exc}", file=sys.stderr)
        print("Action: Ask the user to provide ECS instance IDs manually.", file=sys.stderr)
        sys.exit(2)
    print(f"Total ECS instances: {len(insts)} (Region: {region}):")
    for i in insts:
        ips = ((i.get("VpcAttributes") or {}).get("PrivateIpAddress") or {}).get("IpAddress") or []
        ip = ips[0] if ips else "-"
        print(f"{i['InstanceId']} | {i.get('InstanceName', '')} | {i.get('Status', '')}"
              f" | {ip} | {i.get('OSType', '')}")


if __name__ == "__main__":
    main()
