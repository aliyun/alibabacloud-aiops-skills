#!/usr/bin/env python3
"""Read-only public SLS discovery and query operations.

Usage (from the skill directory):
    python3 scripts/sls.py <command> --help
    python3 scripts/sls.py list --region cn-hangzhou --project my-project --kind logstore
Cloud operations accept --endpoint and --profile; use --output to save JSON to a file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from lib.common import DATASOURCES, SkillError, digest, write
from lib.discovery import summarize
from lib.sls_client import SlsClient


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    operations = ("list", "describe", "index", "query", "metrics", "labels", "discover", "dashboard-get")
    for name in operations:
        sub = commands.add_parser(name)
        sub.add_argument("--region", required=True)
        sub.add_argument("--project", required=True)
        sub.add_argument("--profile")
        sub.add_argument("--endpoint", help="SLS service endpoint override (host or HTTP(S) base URL)")
        sub.add_argument("--aliyun", default="aliyun")
        sub.add_argument("--timeout", type=int, default=60)
        sub.add_argument("--output", required=name == "discover")
        if name == "list":
            sub.add_argument("--kind", choices=["logstore", "metricstore", "storeview", "dashboard"], required=True)
            sub.add_argument("--offset", type=int, default=0)
            sub.add_argument("--size", type=int, default=100)
        else:
            sub.add_argument("--name", required=True)
            if name != "dashboard-get":
                sub.add_argument("--type", choices=sorted(DATASOURCES), required=True)
                sub.add_argument("--id", default="source-1")
        if name in ("query", "metrics", "labels", "discover"):
            sub.add_argument("--from", dest="start", type=int, required=name != "discover")
            sub.add_argument("--to", dest="end", type=int, required=name != "discover")
            sub.add_argument("--limit", type=int, default=1000)
        if name == "query":
            sub.add_argument("--query", required=True)
            sub.add_argument("--language", choices=["sql", "spl", "promql", "search"], default="sql")
            sub.add_argument("--query-type", choices=["instant", "range"], default="range")
            sub.add_argument("--step", default="60s")
        if name == "metrics":
            sub.add_argument("--keyword", default="")
        if name == "labels":
            sub.add_argument("--metric", required=True)
        if name == "discover":
            sub.add_argument("--sample", action="store_true")
            sub.add_argument("--metric", help="Exact metric name when sampling a Metricstore")
    args = parser.parse_args(argv)
    client = SlsClient(args.region, args.profile, args.aliyun, args.timeout, endpoint=args.endpoint)
    if args.command == "list":
        result = {"result": client.list_resources(args.project, args.kind, args.offset, args.size),
                  "pagination": {"offset": args.offset, "size": args.size, "allPagesFetched": False}}
    elif args.command == "dashboard-get":
        result = client.get_dashboard(args.project, args.name)
    else:
        source = {"id": args.id, "type": args.type, "region": args.region, "project": args.project, "name": args.name}
        if args.command == "describe":
            result = client.describe(source)
        elif args.command == "index":
            result = client.index(source)
        elif args.command == "query":
            result = client.query(source, args.query, args.start, args.end, args.language,
                                  args.query_type, args.step, args.limit)
        elif args.command == "metrics":
            result = client.metrics(source, args.start, args.end, args.limit, args.keyword)
        elif args.command == "labels":
            result = client.labels(source, args.metric, args.start, args.end, args.limit)
        else:
            if args.sample and (args.start is None or args.end is None):
                raise SkillError("--sample requires --from and --to")
            metadata = client.describe(source)
            index = client.index(source) if args.type in {"logstore", "logstore_storeview"} else None
            sample = None
            metrics = None
            is_metric = args.type not in {"logstore", "logstore_storeview"}
            if args.sample:
                if is_metric and not args.metric:
                    raise SkillError("Metricstore --sample requires an exact --metric")
                sample = client.query(source, args.metric if is_metric else "* | select * limit 20",
                                      args.start, args.end, language="promql" if is_metric else "sql", limit=20)
            if is_metric and args.start is not None and args.end is not None:
                if args.metric:
                    metrics = {"metrics": [args.metric], "evidenceKind": "user",
                               "complete": bool(sample and sample["complete"]),
                               "window": {"from": args.start, "to": args.end}}
                else:
                    metrics = client.metrics(source, args.start, args.end, args.limit)
            result = summarize(source, index=index, sample=sample, metadata=metadata, metrics=metrics)
            directory = Path(args.output).resolve().with_suffix(".evidence")
            for kind, value in (("metadata", metadata), ("index", index), ("sample", sample), ("metrics", metrics)):
                if value is None:
                    continue
                path = directory / (kind + ".json")
                write(path, value)
                for evidence in result["evidence"]:
                    if evidence.get("sha256") == digest(value):
                        evidence["path"] = str(path)
    if args.output:
        write(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SkillError, ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "code": getattr(exc, "code", "INVALID_INPUT"),
                          "message": str(exc), **getattr(exc, "details", {})}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
