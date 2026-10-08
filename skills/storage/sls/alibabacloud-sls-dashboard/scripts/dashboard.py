#!/usr/bin/env python3
"""Offline dashboard tools and explicit SLS publishing.

Usage (from the skill directory):
    python3 scripts/dashboard.py <command> --help
    python3 scripts/dashboard.py build --plan plan.json --output dashboard.json
    python3 scripts/dashboard.py validate --input dashboard.json
    python3 scripts/dashboard.py subscription <action> --help
Cloud operations accept --endpoint and --profile; writes require --execute.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.dont_write_bytecode = True
from lib import builder, changes, publisher, subscriptions
from lib.common import SkillError, load, write
from lib.sls_client import SlsClient
from lib.validation import require_valid, validate


def target_args(parser):
    for key in ("region", "project", "name"):
        parser.add_argument("--" + key, required=True)


def target(args):
    return {key: getattr(args, key) for key in ("region", "project", "name")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    subscriptions.configure_cli(commands)
    for name in ("build", "validate", "snapshot", "diff", "merge-additions", "publish", "delete"):
        sub = commands.add_parser(name)
        sub.add_argument("--output", help="JSON output file; otherwise stdout")
        if name in ("validate", "snapshot", "publish"):
            sub.add_argument("--input", required=True)
        if name == "build":
            sub.add_argument("--plan", required=True)
            sub.add_argument("--facts", action="append", default=[])
        if name == "validate":
            sub.add_argument("--baseline", help="Original dashboard JSON for preserving unchanged non-SLS content")
        if name == "diff":
            sub.add_argument("--before", required=True)
            sub.add_argument("--after", required=True)
        if name == "merge-additions":
            sub.add_argument("--base", required=True)
            sub.add_argument("--additions", required=True)
        if name in ("snapshot", "publish", "delete"):
            target_args(sub)
        if name in ("publish", "delete"):
            sub.add_argument("--snapshot", required=name == "delete")
            sub.add_argument("--profile")
            sub.add_argument("--endpoint", help="SLS service endpoint override (host or HTTP(S) base URL)")
            sub.add_argument("--aliyun", default="aliyun")
            sub.add_argument("--timeout", type=int, default=60)
            sub.add_argument("--execute", action="store_true")
        if name == "publish":
            sub.add_argument("--mode", choices=["create", "update"], required=True)
    args = parser.parse_args(argv)
    if args.command == "subscription":
        result = subscriptions.run_cli(args, SlsClient)
    elif args.command == "build":
        result = builder.build(load(args.plan), [load(path) for path in args.facts])
        require_valid(result)
    elif args.command == "validate":
        result = validate(load(args.input), load(args.baseline) if args.baseline else None)
    elif args.command == "snapshot":
        result = changes.snapshot(load(args.input), target(args))
    elif args.command == "diff":
        result = changes.diff(load(args.before), load(args.after))
    elif args.command == "merge-additions":
        base = load(args.base)
        result = changes.merge_additions(base, load(args.additions))
        require_valid(result, base)
    else:
        scope = target(args)
        snapshot = load(args.snapshot) if args.snapshot else None
        if args.command == "publish":
            root = load(args.input)
            payload, _ = publisher.prepare(root, scope, args.mode, snapshot)
            result = {"status": "prepared", "target": scope, "mode": args.mode, "payload": payload}
        else:
            changes.check_snapshot(snapshot, scope)
            result = {"status": "prepared", "target": scope, "mode": "delete"}
        if args.execute:
            client = SlsClient(args.region, args.profile, args.aliyun, args.timeout, endpoint=args.endpoint)
            result = (publisher.publish(client, root, scope, args.mode, snapshot)
                      if args.command == "publish" else publisher.delete(client, scope, snapshot))
    if args.output:
        write(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if args.command == "validate" and not result["valid"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SkillError, ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "code": getattr(exc, "code", "INVALID_INPUT"),
                          "message": str(exc), **getattr(exc, "details", {})}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
