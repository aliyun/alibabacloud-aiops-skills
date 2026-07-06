#!/usr/bin/env python3
"""Verify WAF inspection output log for data completeness and cert expiry.

Dependencies: Python 3 standard library only (json, re, time, sys).

Usage:
    python3 scripts/verify_output.py /tmp/waf_skill_output.log

Input:  Path to the WAF inspection output log file (concatenated JSON responses).
Output: Summary of discovered instances, domains, and certificate expiry status.
Exit 0 on success; exit 1 if log file not found or unreadable.
"""
import json
import re
import time
import sys

LOG_PATH = sys.argv[1] if len(sys.argv) > 1 else '/tmp/waf_skill_output.log'

try:
    raw = open(LOG_PATH).read()
except FileNotFoundError:
    print(f"[ERROR] verify_output: log file not found: {LOG_PATH}", file=sys.stderr)
    print(f"  Fix: Run the full inspection workflow (Phase 1-4) first.", file=sys.stderr)
    print(f"  Expected: A file containing concatenated JSON outputs from 'aliyun waf-openapi' commands.", file=sys.stderr)
    sys.exit(1)
except PermissionError:
    print(f"[ERROR] verify_output: permission denied reading: {LOG_PATH}", file=sys.stderr)
    print(f"  Fix: Check file permissions with 'ls -la {LOG_PATH}' and ensure read access.", file=sys.stderr)
    sys.exit(1)

if not raw.strip():
    print(f"[ERROR] verify_output: log file is empty: {LOG_PATH}", file=sys.stderr)
    print(f"  Fix: Ensure every 'aliyun waf-openapi' command appends output via '>> {LOG_PATH}'.", file=sys.stderr)
    sys.exit(1)

blocks, depth, start = [], 0, -1
parse_errors = 0
for i, c in enumerate(raw):
    if c == '{':
        if depth == 0:
            start = i
        depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0 and start >= 0:
            cleaned = re.sub(r'[\x00-\x1f\x7f]', '', raw[start:i+1])
            try:
                blocks.append(json.loads(cleaned))
            except json.JSONDecodeError:
                parse_errors += 1
            start = -1

if not blocks:
    print(f"[ERROR] verify_output: no valid JSON blocks found in {LOG_PATH}. File may contain only error messages.", file=sys.stderr)
    print("  Fix: Re-run the workflow and check that CLI commands output valid JSON. Verify credentials with: aliyun configure list", file=sys.stderr)

if parse_errors > 0:
    print(f"[WARN] verify_output: {parse_errors} JSON block(s) failed to parse in {LOG_PATH}", file=sys.stderr)

instances = set()
for b in blocks:
    if 'InstanceId' in b:
        instances.add(b['InstanceId'])
for line in raw.splitlines():
    if '"InstanceId"' in line and 'waf_' in line:
        val = line.split('"InstanceId"')[1].split('"')[1]
        if val.startswith('waf_'):
            instances.add(val)

domains = []
for b in blocks:
    for d in b.get('Domains', []):
        if 'DomainId' in d:
            domains.append(d.get('Domain', ''))

certs, seen_certs = [], set()
for b in blocks:
    for c in b.get('Certs', []):
        if 'AfterDate' in c:
            key = (c.get('Domain', c.get('CommonName', '')), c['AfterDate'])
            if key not in seen_certs:
                seen_certs.add(key)
                certs.append(key)

region_mismatches = []
for line in raw.splitlines():
    if line.startswith('[REGION_MISMATCH] '):
        region_mismatches.append(line)

print(f'[VERIFY] Instances={instances} Domains={domains} Certs={len(certs)} RegionMismatches={len(region_mismatches)}')

if region_mismatches:
    print(f'[WARN] verify_output: {len(region_mismatches)} cross-region resource mismatch(es) detected -- WAF instance region differs from resource region. Review the report "Cross-Region Resource Risk" section.')
    for m in region_mismatches:
        print(m)

if not instances:
    print("[WARN] verify_output: no WAF instances discovered. Check describe-instance output for errors.", file=sys.stderr)

now = int(time.time())
for name, ts in certs:
    t = ts // 1000 if ts > 9999999999 else ts
    days = (t - now) // 86400
    if days < 0:
        level = 'EXPIRED'
    elif days < 7:
        level = 'Critical'
    elif days < 30:
        level = 'Warning'
    else:
        level = 'Normal'
    print(f'[CERT] {name} days={days} level={level}')
