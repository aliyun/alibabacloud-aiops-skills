"""Envelope builder — produces uniform JSON response.

All cadt-deploy-on-aliyun subcommands MUST output via ok()/err() so that agents have a single
contract: {ok: bool, data?: ..., error?: {...}, meta: {...}}.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional


def _load_version() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(here, "..", "..", "..", "VERSION")
    try:
        with open(os.path.normpath(version_file), "r", encoding="utf-8") as f:
            return f.read().strip()
    except (OSError, IOError):
        return "unknown"


CADT_VERSION = _load_version()


class _Stopwatch:
    def __init__(self) -> None:
        self._start = time.monotonic()

    @property
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)


def stopwatch() -> _Stopwatch:
    return _Stopwatch()


def ok(data: Any, *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build success envelope."""
    return {
        "ok": True,
        "data": data,
        "meta": _meta(meta),
    }


def err(
    code: str,
    message: str,
    *,
    fix_hint: str = "",
    fields: Optional[list] = None,
    docs_ref: str = "",
    data: Any = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build failure envelope."""
    error: Dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if fix_hint:
        error["fixHint"] = fix_hint
    if fields:
        error["fields"] = fields
    if docs_ref:
        error["docsRef"] = docs_ref
    result = {
        "ok": False,
        "error": error,
        "meta": _meta(meta),
    }
    if data is not None:
        result["data"] = data
    return result


def _meta(meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = {"cadtVersion": CADT_VERSION}
    if meta:
        base.update(meta)
    return base


def emit(envelope: Dict[str, Any]) -> None:
    """Print envelope as single-line JSON to stdout."""
    print(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")))
