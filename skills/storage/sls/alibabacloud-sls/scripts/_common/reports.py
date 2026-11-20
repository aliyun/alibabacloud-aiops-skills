"""Validation reports and process status; domain checks stay with each tool."""

import sys

from .json_io import ToolError, dumps, write


def issue(code, path, message, **details):
    return {"code": code, "path": path, "message": message, **details}


def result(errors, warnings=None, **extra):
    warnings = warnings or []
    return {
        "result": "error" if errors else "warning" if warnings else "valid",
        "errors": errors,
        "warnings": warnings,
        **extra,
    }


def exit_code(report, strict=False):
    return int(bool(report["errors"] or (strict and report["warnings"])))


def input_error(exc, **extra):
    return result([issue(getattr(exc, "code", "INPUT_ERROR"), "$", str(exc))], **extra)


def emit(report, output=None):
    if output:
        write(output, report)
    else:
        print(dumps(report))


def run(main):
    try:
        return main()
    except (ToolError, ValueError, OSError) as exc:
        report = result(
            [issue(getattr(exc, "code", "INVALID_INPUT"), "$", str(exc))],
            **getattr(exc, "details", {}),
        )
        print(dumps(report), file=sys.stderr)
        return 1
