"""Shared local contracts, serialization, and resource identities."""

import copy
import hashlib
import json
from pathlib import Path

from _common.json_io import ToolError as SkillError, load, write

ROOT = Path(__file__).resolve().parents[3]
DATASOURCES = frozenset(
    {
        "logstore",
        "metricstore",
        "metricsql",
        "logstore_storeview",
        "metricstore_storeview",
    }
)
DASHBOARD_DATASOURCES = DATASOURCES | {"builtin"}
METRIC = frozenset({"metricstore", "metricstore_storeview"})


def encoded(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def schema_check(value, name):
    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:
        raise SkillError(
            "Plan construction requires jsonschema; install it with python3 -m pip install jsonschema",
            "MISSING_DEPENDENCY",
        ) from exc
    validator = Draft7Validator(
        load(ROOT / "references" / "dashboard" / "contracts" / f"{name}.schema.json")
    )
    errors = sorted(validator.iter_errors(value), key=lambda error: str(list(error.path)))
    if errors:
        raise SkillError(
            "; ".join(f"{'.'.join(map(str, e.path)) or '$'}: {e.message}" for e in errors[:12]),
            "CONTRACT_ERROR",
        )


def deep_merge(base, patch):
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def effective_datasource(query):
    value = query.get("datasource", "")
    if (
        isinstance(value, str)
        and query.get("type") == "storeview"
        and value in {"logstore", "metricstore", "metricsql"}
    ):
        value += "_storeview"
    return value
