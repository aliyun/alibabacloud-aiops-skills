#!/usr/bin/env python3
"""Detect cross-region resource mismatches in WAF cloud resource list.

Reads describe-cloud-resource-list JSON from stdin, compares each resource's
ResourceRegionId with the WAF instance region, and outputs [REGION_MISMATCH] lines.

Usage:
    echo "$RESULT" | python3 scripts/detect_region_mismatch.py \
        --region <waf_region> --instance-id <instance_id>

Output lines:
    [REGION_MISMATCH] waf_region=... resource_region=... resource_type=... resource_id=... instance_id=...
    [REGION_MISMATCH_SUMMARY] total=N waf_region=... instance_id=...

Exit 0 always (detection failures are non-fatal).
"""
import sys
import json
import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--region', required=True, help='WAF instance region (e.g. ap-southeast-1)')
parser.add_argument('--instance-id', required=True, dest='instance_id', help='WAF instance ID')
args = parser.parse_args()

raw = sys.stdin.read()
raw = re.sub(r'[\x00-\x1f\x7f]', '', raw)

try:
    d = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(0)  # Non-JSON output (e.g. CLI error) -- skip silently

resources = d.get('CloudResourceList', [])
mismatches = []

for r in resources:
    resource_region = r.get('ResourceRegionId', '')
    if resource_region and resource_region != args.region:
        mismatches.append({
            'waf_region': args.region,
            'resource_region': resource_region,
            'resource_type': r.get('ResourceProduct', 'unknown'),
            'resource_id': r.get('ResourceInstanceId', 'unknown'),
            'cloud_resource_id': r.get('CloudResourceId', ''),
            'instance_id': args.instance_id,
        })

for m in mismatches:
    print(
        f"[REGION_MISMATCH] "
        f"waf_region={m['waf_region']} "
        f"resource_region={m['resource_region']} "
        f"resource_type={m['resource_type']} "
        f"resource_id={m['resource_id']} "
        f"cloud_resource_id={m['cloud_resource_id']} "
        f"instance_id={m['instance_id']}"
    )

if mismatches:
    print(
        f"[REGION_MISMATCH_SUMMARY] "
        f"total={len(mismatches)} "
        f"waf_region={args.region} "
        f"instance_id={args.instance_id}"
    )
