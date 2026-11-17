"""Lossless compact JSON shared by catalog outputs and byte budgets."""

import json
from decimal import Decimal

def _encode(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite JSON number")
        return str(value)
    if isinstance(value, dict):
        return "{" + ",".join(_encode(k) + ":" + _encode(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_encode(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def dumps(value):
    # Match Go encoding/json's compact UTF-8 and HTML escaping for output budgets.
    raw = _encode(value)
    for char in ("<", ">", "&", "\u2028", "\u2029"):
        raw = raw.replace(char, "\\u%04x" % ord(char))
    return raw


def size(value):
    return len(dumps(value).encode("utf-8"))
