#!/usr/bin/env python3
"""Verify that a result manifest accounts for every requested overview item."""
import argparse
import json
import sys

try:
    from .query_permissions import SCOPES
except ImportError:
    from query_permissions import SCOPES

STATES = {"success", "failed", "unknown", "not-applicable"}


def verify(expected, items):
    if not expected or len(expected) != len(set(expected)) or any(key not in SCOPES for key in expected):
        raise ValueError("Expected scope must contain distinct known items")
    if not isinstance(items, dict) or set(items) - set(expected):
        raise ValueError("Result items must match the requested scope")
    normalized = {}
    for key in expected:
        item = items.get(key, {"status": "unknown", "evidence": "Requested item has no result"})
        if not isinstance(item, dict) or item.get("status") not in STATES:
            raise ValueError(f"Invalid result state for {key}")
        if not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
            raise ValueError(f"Missing validation evidence/reason for {key}")
        normalized[key] = item
    states = {item["status"] for item in normalized.values()}
    if states <= {"not-applicable"}:
        overall = "not-applicable"
    elif states <= {"success", "not-applicable"}:
        overall = "complete"
    elif "success" in states:
        overall = "partial"
    else:
        overall = "incomplete"
    return {"overall": overall, "items": normalized}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", nargs="+", choices=list(SCOPES), required=True)
    args = parser.parse_args()
    try:
        result = verify(args.expected, json.load(sys.stdin))
    except (ValueError, TypeError) as exc:
        result = {"overall": "invalid", "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["overall"] in ("complete", "not-applicable") else 2


if __name__ == "__main__":
    sys.exit(main())
