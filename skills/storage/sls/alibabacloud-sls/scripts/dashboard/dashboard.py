#!/usr/bin/env python3
"""Build, validate, compare or merge local SLS dashboard configurations.

Usage:
    python3 scripts/dashboard/dashboard.py validate --input FILE
"""

import argparse
import json
import sys
from pathlib import Path


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common.cli import add_input, add_validation_options, resolve_input
from _common.json_io import check_output_path
from _common.reports import emit, input_error, run
from lib import builder, changes
from lib.common import SkillError, load, write
from lib.chart_validator import validate_chart
from lib.validation import validate
from lib.validation_report import exit_code


def show_warnings(report):
    if report["warnings"]:
        print(
            json.dumps({"validation": report}, ensure_ascii=False, allow_nan=False), file=sys.stderr
        )


def artifact_report(value, args):
    """Keep the Dashboard artifact separate from its validation diagnostics."""
    if getattr(args, "baseline", None) and args.mode != "update":
        raise SkillError("A baseline requires --mode update", "BASELINE_MODE")
    report = validate(
        value,
        load(args.baseline) if getattr(args, "baseline", None) else None,
        mode=getattr(args, "mode", "standalone"),
    )
    if args.report:
        write(args.report, report)
    if report["errors"]:
        raise SkillError("Dashboard validation failed", "VALIDATION_FAILED", report=report)
    show_warnings(report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    commands = parser.add_subparsers(dest="command")
    commands.required = True
    for name in ("build", "validate", "diff", "merge-additions"):
        sub = commands.add_parser(name)
        if name == "validate":
            add_input(sub)
            add_validation_options(sub)
        else:
            sub.add_argument("--output", help="JSON output file; otherwise stdout")
        if name == "build":
            sub.add_argument("--plan", required=True)
        if name in ("build", "merge-additions"):
            sub.add_argument(
                "--report", help="Save the validation report separately from the Dashboard JSON"
            )
        if name in ("validate", "merge-additions"):
            sub.add_argument("--baseline", help="Original get response for update validation")
            sub.add_argument("--mode", choices=["standalone", "update"], default="standalone")
        if name == "validate":
            sub.add_argument(
                "--chart", action="store_true", help="Validate one chart instead of a Dashboard"
            )
            sub.add_argument(
                "--layout",
                choices=["grid", "free"],
                help="Layout context for --chart; omit to skip layout checks",
            )
        if name == "diff":
            sub.add_argument("--before", required=True)
            sub.add_argument("--after", required=True)
        if name == "merge-additions":
            sub.add_argument("--base", required=True)
            sub.add_argument("--additions", required=True)
    args = parser.parse_args(argv)
    if args.command == "validate":
        args.input = resolve_input(parser, args)
    inputs = [
        getattr(args, key, None)
        for key in ("plan", "base", "additions", "baseline", "before", "after")
    ]
    if args.command == "validate" and args.input != "-":
        inputs.append(args.input)
    check_output_path(args.output, inputs)
    if getattr(args, "report", None):
        inputs = [
            getattr(args, key, None) for key in ("output", "plan", "base", "additions", "baseline")
        ]
        if any(Path(args.report).resolve() == Path(path).resolve() for path in inputs if path):
            raise SkillError("Use a separate path for --report", "REPORT_PATH_CONFLICT")
    if args.command == "build":
        result = builder.build(load(args.plan))
        artifact_report(result, args)
    elif args.command == "validate":
        try:
            if args.chart:
                if args.baseline or args.mode != "standalone":
                    raise SkillError(
                        "Update comparison requires a complete Dashboard", "VALIDATION_SCOPE"
                    )
                result = validate_chart(load(args.input, allow_stdin=True), args.layout)
            else:
                if args.layout:
                    raise SkillError(
                        "Dashboard layout comes from attribute.type; --layout is for --chart",
                        "VALIDATION_SCOPE",
                    )
                result = validate(
                    load(args.input, allow_stdin=True),
                    load(args.baseline, "Baseline") if args.baseline else None,
                    mode=args.mode,
                )
        except (SkillError, ValueError, OSError) as exc:
            result = input_error(exc, unchecked=[])
    elif args.command == "diff":
        result = changes.diff(load(args.before), load(args.after))
    elif args.command == "merge-additions":
        base = load(args.base)
        result = changes.merge_additions(base, load(args.additions))
        artifact_report(result, args)
    emit(result, args.output)
    return exit_code(result, args.strict) if args.command == "validate" else 0


if __name__ == "__main__":
    raise SystemExit(run(main))
