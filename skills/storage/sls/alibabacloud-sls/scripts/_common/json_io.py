"""Strict JSON input and atomic UTF-8 output."""

import json
import math
import os
from pathlib import Path
import sys
import tempfile


class ToolError(Exception):
    def __init__(self, message, code="INVALID_INPUT", **details):
        super().__init__(message)
        self.code = code
        self.details = details


def _reject_constant(value):
    raise ValueError("Non-finite constants are not valid JSON")


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON object keys are not allowed")
        value[key] = item
    return value


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON number exceeds the supported floating-point range")
    return number


def loads(text, parse_float=None):
    return json.loads(
        text,
        parse_float=parse_float or _finite_float,
        parse_constant=_reject_constant,
        object_pairs_hook=_unique_object,
    )


def load(path, label="Input", *, allow_stdin=False, parse_float=None):
    use_stdin = allow_stdin and str(path) == "-"
    source = "stdin" if use_stdin else str(path)
    try:
        text = sys.stdin.read() if use_stdin else Path(path).read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise ToolError(
            "{} ({}): expected UTF-8 text".format(label, source), "INPUT_ERROR"
        ) from exc
    except OSError as exc:
        raise ToolError("{} ({}): {}".format(label, source, exc.strerror), "INPUT_ERROR") from exc
    try:
        return loads(text, parse_float=parse_float)
    except json.JSONDecodeError as exc:
        message = "invalid JSON at line {}, column {}".format(exc.lineno, exc.colno)
        raise ToolError("{} ({}): {}".format(label, source, message), "INPUT_ERROR") from exc
    except ValueError as exc:
        raise ToolError("{} ({}): {}".format(label, source, exc), "INPUT_ERROR") from exc


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def write(path, value):
    """Replace the output atomically after serialization succeeds."""
    text = dumps(value) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def check_output_path(output, inputs, label="Output"):
    if output and any(
        Path(output).resolve() == Path(path).resolve() for path in inputs if path is not None
    ):
        raise ToolError(
            "{} must use a separate path from inputs and other outputs".format(label),
            "OUTPUT_PATH_CONFLICT",
        )
