#!/usr/bin/env python3
"""Export selected SLS query records without executing or rewriting queries."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_record(path: Path) -> dict:
    if not path.is_absolute():
        raise ValueError(f"{path}: input path must be absolute")
    try:
        with open(path, encoding="utf-8") as src:
            record = json.load(src)
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"{path}: invalid UTF-8 JSON record") from error
    if not isinstance(record, dict) or record.get("success") is False:
        raise ValueError(f"{path}: expected a successful query record object")

    def field(obj: dict, key: str, kinds: tuple[type, ...], label: str):
        if key not in obj or type(obj[key]) not in kinds:
            raise ValueError(f"{path}: missing or invalid {label}")
        return obj[key]

    req = field(record, "request", (dict,), "request")
    meta = field(record, "meta", (dict,), "meta")
    window = field(record, "timeRange", (dict,), "timeRange")
    field(record, "logs", (list, type(None)), "logs")
    for key in ("query", "project", "logstore"):
        value = field(req, key, (str,), f"request.{key}")
        if not value.strip():
            raise ValueError(f"{path}: request.{key} must not be empty")
    field(req, "region", (str, type(None)), "request.region")
    for key in ("from", "to"):
        actual = field(req, key, (int,), f"request.{key}")
        reported = field(window, key, (int,), f"timeRange.{key}")
        if actual != reported:
            raise ValueError(f"{path}: request.{key} differs from timeRange.{key}")
    if req["from"] > req["to"]:
        raise ValueError(f"{path}: request.from exceeds request.to")
    for key in ("lines", "offset"):
        field(req, key, (int,), f"request.{key}")
    field(req, "powerSQL", (bool,), "request.powerSQL")
    progress = field(meta, "progress", (str,), "meta.progress")
    if progress.lower() != "complete":
        raise ValueError(f"{path}: meta.progress must be Complete")
    return record


def render_records(records: list[tuple[Path, dict]]) -> str:
    blocks = ["Query execution details\n"]
    for index, (path, record) in enumerate(records, 1):
        req = record["request"]
        query = req["query"]
        fence = "`" * max(3, 1 + max((len(run) for run in re.findall(r"`+", query)), default=0))
        region = "not recorded" if req["region"] is None else req["region"]
        power_sql = "true" if req["powerSQL"] else "false"
        blocks.append(
            f"Query {index}: {path.name}\n"
            f"Region: {region}\n"
            f"Project: {req['project']}\n"
            f"Logstore: {req['logstore']}\n"
            f"Time window: [{req['from']}, {req['to']}), Unix seconds\n"
            f"Execution parameters: lines={req['lines']}, offset={req['offset']}, powerSQL={power_sql}\n\n"
            f"{fence}text\n{query}\n{fence}\n"
        )
    return "\n".join(blocks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+", type=Path, help="Absolute paths to the selected query record JSON files")
    args = parser.parse_args(argv)
    try:
        records = [(path, load_record(path)) for path in args.records]
        body = render_records(records)
        sys.stdout.write(body)
        sys.stdout.flush()
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
