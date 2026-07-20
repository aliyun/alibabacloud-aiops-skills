"""Response shape normalizer for EcsRunCommand / EcsRunCommandSync.

The backend API returns results with inconsistent nesting depending on the
code path (sync vs async poll, success vs failure). This module collapses
all variants into a single stable shape so that agents can always parse
``.data.instances`` (on success) or ``.data.instances`` (on failure details).

Canonical shape::

    {
        "success": true/false,
        "message": "...",
        "instances": {
            "i-xxx": {"status": "Success", "message": "Success", "output": "..."}
        }
    }
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional


def normalize_ecs_run_result(data: Any) -> Any:
    """Normalize EcsRunCommand output to a stable shape.

    Detects ``attributes.instances`` (or ``Arguments.attributes.instances``)
    at any nesting depth and collapses to ``{success, message, instances}``.

    Returns the original data untouched for non-EcsRunCommand shapes.
    """
    if not isinstance(data, dict):
        return data

    result = _extract_instances_shape(data)
    if result is None:
        return data
    return result


def _extract_instances_shape(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    candidates = [
        data,
        data.get("Arguments") if isinstance(data.get("Arguments"), dict) else None,
        data.get("arguments") if isinstance(data.get("arguments"), dict) else None,
        data.get("Data") if isinstance(data.get("Data"), dict) else None,
        data.get("data") if isinstance(data.get("data"), dict) else None,
    ]

    for c in candidates:
        if c is None:
            continue
        attrs = c.get("attributes") or c.get("Attributes")
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(attrs, dict):
            continue
        instances = attrs.get("instances") or attrs.get("Instances")
        if isinstance(instances, str):
            try:
                instances = json.loads(instances)
            except (json.JSONDecodeError, TypeError):
                continue
        if isinstance(instances, dict):
            success = c.get("success")
            if success is None:
                success = c.get("Success")
            message = c.get("message") or c.get("Message") or ""
            return {
                "success": success if isinstance(success, bool) else _coerce_bool(success),
                "message": str(message),
                "instances": instances,
            }
    return None


def _coerce_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)
