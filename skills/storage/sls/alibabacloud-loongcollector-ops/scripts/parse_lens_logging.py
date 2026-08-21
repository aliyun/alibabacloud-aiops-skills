#!/usr/bin/env python3
"""parse_lens_logging.py — extract Lens entry from `get-logging` JSON.

Deterministic parser for CloudLens / service-log discovery. Prefer this over
ad-hoc JSON grepping so agents emit a stable discovery result before querying
`logtail_alarm` / `loongcollector_metric`.

Protocol: stdout = single JSON object; stderr = diagnostics; exit code:
  0 = usable Lens entry found
  1 = no usable entry (caller should ask the user or continue without Lens)
  2 = usage / parse failure

Usage:
  python3 scripts/parse_lens_logging.py --file get-logging.json
  aliyun sls get-logging --project <biz> ... | python3 scripts/parse_lens_logging.py
"""
import argparse
import json
import os
import re
import sys

JSON_OBJECT_RE = re.compile(r"\{.*\}", re.S)
PREFERRED_TYPES = ("logtail_alarm", "logtail_status", "logtail_profile")


def _first_json_object(text: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = JSON_OBJECT_RE.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _pick_logstore(details):
    if not isinstance(details, list):
        return "", ""
    by_type = {}
    for item in details:
        if not isinstance(item, dict):
            continue
        detail_type = str(item.get("type") or item.get("Type") or "").strip()
        logstore = str(
            item.get("logstore")
            or item.get("Logstore")
            or item.get("loggingLogstore")
            or ""
        ).strip()
        if detail_type and logstore:
            by_type[detail_type] = logstore
    for preferred in PREFERRED_TYPES:
        if preferred in by_type:
            return by_type[preferred], preferred
    if by_type:
        detail_type, logstore = next(iter(by_type.items()))
        return logstore, detail_type
    return "", ""


def parse_logging(payload: dict):
    lens_project = str(
        payload.get("loggingProject")
        or payload.get("LoggingProject")
        or payload.get("logging_project")
        or ""
    ).strip()
    details = (
        payload.get("loggingDetails")
        or payload.get("LoggingDetails")
        or payload.get("logging_details")
        or []
    )
    lens_logstore, detail_type = _pick_logstore(details)
    # Common default when details omit logstore but project exists.
    if lens_project and not lens_logstore:
        lens_logstore = "internal-diagnostic_log"
        detail_type = detail_type or "default"
    usable = bool(lens_project and lens_logstore)
    return {
        "status": "found" if usable else "not_found",
        "lens_project": lens_project,
        "lens_logstore": lens_logstore,
        "detail_type": detail_type,
        "usable": usable,
    }


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--file", help="get-logging output file; omit to read stdin")
    args = ap.parse_args()

    if args.file:
        if not os.path.isfile(args.file):
            sys.stderr.write("[parse_lens_logging] file not found: %s\n" % args.file)
            return 2
        with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    else:
        raw = sys.stdin.read()

    payload = _first_json_object(raw)
    if payload is None:
        # Empty / ProjectNotExist style outputs still count as "attempted, not found".
        out = {
            "tool": "parse_lens_logging",
            "session_id": os.environ.get("SKILL_SESSION_ID", ""),
            "status": "not_found",
            "lens_project": "",
            "lens_logstore": "",
            "detail_type": "",
            "usable": False,
            "parse_error": "no JSON object found",
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        return 1

    parsed = parse_logging(payload)
    out = {
        "tool": "parse_lens_logging",
        "session_id": os.environ.get("SKILL_SESSION_ID", ""),
        **parsed,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0 if parsed["usable"] else 1


if __name__ == "__main__":
    sys.exit(main())
