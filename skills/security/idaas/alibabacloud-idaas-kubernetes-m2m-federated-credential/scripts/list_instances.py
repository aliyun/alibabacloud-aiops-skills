#!/usr/bin/env python3
"""列出指定 Region 下的 IDaaS EIAM 实例（供用户选择）。

用法: list_instances.py <region>
"""
import sys

from common import run_aliyun


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法: list_instances.py <region>")
    region = sys.argv[1]

    d = run_aliyun(["eiam", "ListInstances", "--region", region,
                    "--PageNumber", "1", "--PageSize", "50"])
    insts = d.get("Instances", [])
    total = d.get("TotalCount", len(insts))
    print(f"共 {total} 个实例 (Region: {region})")
    if total > len(insts):
        print(f"WARNING: 仅展示前 {len(insts)} 个，请翻页 (PageNumber)", file=sys.stderr)
    for i in insts:
        ep = (i.get("DefaultEndpoint") or {}).get("Endpoint", "-")
        desc = (i.get("Description") or "").replace("\n", " ")[:50]
        mgd = " [托管]" if i.get("ServiceManaged") else ""
        print(f"{i['InstanceId']} | {i.get('Status', '?')}{mgd} | {ep} | {desc}")


if __name__ == "__main__":
    main()
