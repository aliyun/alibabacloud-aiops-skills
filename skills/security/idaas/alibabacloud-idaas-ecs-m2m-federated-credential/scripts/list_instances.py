#!/usr/bin/env python3
"""List IDaaS EIAM instances in a region for the user to select.

Usage: list_instances.py <region> [--json]
"""
import json
import sys

from common import list_all_pages


def main() -> None:
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != '--json'):
        sys.exit("Usage: list_instances.py <region> [--json]")
    region = sys.argv[1]

    insts = list_all_pages(["eiam", "list-instances", "--region", region], "Instances", "InstanceId", 50)
    total = len(insts)
    if len(sys.argv) == 3:
        print(json.dumps({'RegionId': region, 'TotalCount': total, 'Instances': insts}, ensure_ascii=False))
        return
    print(f"Total instances: {total} (Region: {region})")
    for i in insts:
        ep = (i.get("DefaultEndpoint") or {}).get("Endpoint", "-")
        desc = (i.get("Description") or "").replace("\n", " ")[:50]
        mgd = " [managed]" if i.get("ServiceManaged") else ""
        print(f"{i['InstanceId']} | {i.get('Status', '?')}{mgd} | {ep} | {desc}")


if __name__ == "__main__":
    main()
