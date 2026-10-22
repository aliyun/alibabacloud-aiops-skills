#!/usr/bin/env python3
"""Validate confirmed query inputs and dependencies without making cloud requests."""
import argparse
import json
import re
import sys
import time

WAF_REGIONS = {"cn-hangzhou", "ap-southeast-1"}


def billing_cycle(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{3}-(0[1-9]|1[0-2])", value):
        raise ValueError("BillingCycle must be the confirmed month in YYYY-MM format")
    return value


def time_window(days, now_ms=None):
    if type(days) is not int or days <= 0:
        raise ValueError("Time range must be a confirmed positive whole number of days")
    end = int(time.time() * 1000) if now_ms is None else now_ms
    start = end - days * 86400000
    if start < 0:
        raise ValueError("Time range starts before the Unix epoch")
    return {"start_ms": start, "end_ms": end, "start_seconds": start // 1000, "end_seconds": end // 1000}


def waf_instance(region, discovery_region, response):
    if region not in WAF_REGIONS or discovery_region != region:
        raise ValueError("Use the confirmed WAF region and discovery from that same region")
    if not isinstance(response, dict):
        raise ValueError("Invalid WAF discovery response")
    value = response.get("InstanceId")
    if not isinstance(value, str) or not value.strip() or value.startswith("<"):
        raise ValueError("No usable InstanceId; do not call DescribeFlowChart")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="kind", required=True)
    window = sub.add_parser("window")
    window.add_argument("--days", type=int, required=True)
    window.add_argument("--unit", choices=["ms", "seconds"], required=True)
    billing = sub.add_parser("billing")
    billing.add_argument("--cycle", required=True)
    waf = sub.add_parser("waf-instance")
    waf.add_argument("--region", required=True)
    waf.add_argument("--discovery-region", required=True)
    args = parser.parse_args()
    try:
        if args.kind == "window":
            print(time_window(args.days)["start_" + args.unit])
        elif args.kind == "billing":
            print(billing_cycle(args.cycle))
        else:
            print(waf_instance(args.region, args.discovery_region, json.load(sys.stdin)))
        return 0
    except (ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
