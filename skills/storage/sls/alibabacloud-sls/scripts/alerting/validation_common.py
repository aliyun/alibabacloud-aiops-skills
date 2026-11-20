"""Shared value handling for alert rules and notification resources."""

import json
import re

from _common.reports import issue as report_issue


MISSING = object()


def without_null_fields(value):
    """Build a validation view without changing the input or array positions."""
    if isinstance(value, dict):
        return {key: without_null_fields(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [without_null_fields(item) for item in value]
    return value


def issue(code, path, message):
    return report_issue(code, path, message, origin="candidate")


def field_path(path, name):
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return path + "." + name
    return path + "[" + json.dumps(name, ensure_ascii=False) + "]"


def same(first, second):
    if first is MISSING or second is MISSING:
        return first is second
    try:
        return json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
            second, sort_keys=True, allow_nan=False
        )
    except (TypeError, ValueError):
        return False
