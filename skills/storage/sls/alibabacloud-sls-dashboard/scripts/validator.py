#!/usr/bin/env python3
"""Validate an SLS chart or dashboard offline with Python 3.

Usage (from the skill directory):
    python3 scripts/validator.py --chart --json chart.json
    python3 scripts/validator.py --dashboard --json dashboard.json
Use --string instead of --json for literal JSON. Prints a JSON report; exits 0 if valid, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from lib.chart_validator import validate_chart, validate_dashboard


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--chart", action="store_true")
    scope.add_argument("--dashboard", action="store_true")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", type=Path, help="JSON input file")
    source.add_argument("--string", help="Literal JSON input")
    args = parser.parse_args(argv)
    def invalid_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")
    value = json.loads(args.json.read_text(encoding="utf-8") if args.json else args.string,
                       parse_constant=invalid_constant)
    report = validate_chart(value, "grid") if args.chart else validate_dashboard(value)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
