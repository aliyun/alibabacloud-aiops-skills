"""attrs serializer — Python dict ↔ aliyun bpstudio --attributes JSON string.

aliyun bpstudio expects --attributes as a single JSON object string:
  --attributes '{"uid":"123","region":"cn-beijing"}'

All values are serialized as strings in the JSON object (gateway convention).
"""
from __future__ import annotations

import json
import shlex
from typing import Any, Dict, List, Optional


# Internal-only keys that never reach aliyun CLI.
_CONTROL_KEYS = {"_no_wait", "_dry_run", "_timeout"}


def to_attrs_json(args: Dict[str, Any]) -> Optional[str]:
    """Convert args dict to a single JSON string for --attributes.

    Rules:
      - skip _control_keys (consumed by cadt-deploy-on-aliyun itself)
      - None values are omitted
      - All values rendered as strings (gateway convention)
      - Returns None if no effective attributes
    """
    obj: Dict[str, str] = {}
    for key, val in args.items():
        if key in _CONTROL_KEYS:
            continue
        if val is None:
            continue
        obj[key] = _render_value(val)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")) if obj else None


def to_attrs(args: Dict[str, Any]) -> List[str]:
    """Legacy: convert dict into list of `key=value` tokens.

    Kept for shell_preview and backward compat.
    """
    tokens: List[str] = []
    for key, val in args.items():
        if key in _CONTROL_KEYS:
            continue
        if val is None:
            continue
        tokens.append(f"{key}={_render_value(val)}")
    return tokens


def _render_value(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        return val
    # dict / list → compact JSON blob
    return json.dumps(val, ensure_ascii=False, separators=(",", ":"))


def shell_preview(op_name: str, attrs_tokens: List[str], *, async_mode: bool) -> str:
    """Build a human-readable command line preview (for --dry-run / debug)."""
    mode = "execute-operation-async" if async_mode else "execute-operation-sync"
    parts = ["aliyun", "bpstudio", mode, f"--operation={op_name}"]
    if attrs_tokens:
        joined = " ".join(shlex.quote(t) for t in attrs_tokens)
        parts.append(f"--attributes {joined}")
    return " ".join(parts)


def coerce_string_fields(args: Dict[str, Any], input_schema: Dict[str, Any]) -> None:
    """Auto-convert dict/list values for fields declared as ``"type":"string"``.

    For ``type: string`` properties:
    - dict values → compact JSON string (fields that expect a JSON object as string)
    - list values → comma-separated string (e.g. instanceIds ``["i-xxx"]`` → ``"i-xxx"``)

    For fields annotated with ``x-coerce: "csv"``:
    - JSON-array strings (e.g. ``'["i-xxx"]'``) are also normalized to
      comma-separated, so agents that pass a JSON-encoded array string
      instead of a plain CSV string are auto-corrected.

    Also normalizes deprecated field aliases (``x-deprecated-aliases``):
    if an alias key is found in args, it is migrated to the canonical field.

    Mutates ``args`` in-place.  No-op when the value is already a string or
    when the property is not present.
    """
    properties = (input_schema or {}).get("properties") or {}
    for key, prop in properties.items():
        aliases = prop.get("x-deprecated-aliases") or []
        for alias in aliases:
            if alias in args:
                old_val = args.pop(alias)
                if key not in args:
                    if isinstance(old_val, str) and prop.get("type") == "array":
                        args[key] = [old_val]
                    else:
                        args[key] = old_val
        if prop.get("type") != "string":
            continue
        val = args.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            if prop.get("x-coerce") == "csv":
                _normalize_csv_string(args, key, val)
            continue
        if isinstance(val, dict):
            args[key] = json.dumps(val, ensure_ascii=False, separators=(",", ":"))
        elif isinstance(val, list):
            args[key] = ",".join(str(v) for v in val)


def _normalize_csv_string(args: Dict[str, Any], key: str, val: str) -> None:
    """If a CSV string field holds a JSON-array string, convert to comma-separated."""
    stripped = val.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return
    if isinstance(parsed, list):
        args[key] = ",".join(str(v) for v in parsed)


def coerce_array_fields(args: Dict[str, Any], input_schema: Dict[str, Any]) -> None:
    """Convert ``type: array`` field values to comma-separated strings.

    The backend gateway expects all attribute values as plain strings.
    Array fields (e.g. ``instanceIds``) must arrive as ``"id1,id2"`` rather
    than JSON-encoded ``["id1","id2"]``, otherwise the backend treats the
    whole JSON blob as a single key.

    Handles four input shapes:
      - list ``["a", "b"]``        → ``"a,b"``
      - list ``["a"]``             → ``"a"``
      - JSON-array string ``'["a","b"]'`` → ``"a,b"``
      - plain string ``"a"``       → ``"a"`` (unchanged)

    Mutates ``args`` in-place.
    """
    properties = (input_schema or {}).get("properties") or {}
    for key, prop in properties.items():
        if prop.get("type") != "array":
            continue
        val = args.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            args[key] = ",".join(str(v) for v in val)
        elif isinstance(val, str):
            stripped = val.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        args[key] = ",".join(str(v) for v in parsed)
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass


def extract_control(args: Dict[str, Any]) -> Dict[str, Any]:
    """Pull out _no_wait / _dry_run / _timeout into a control dict."""
    return {k: args[k] for k in _CONTROL_KEYS if k in args}
