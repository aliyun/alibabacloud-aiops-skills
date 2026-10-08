"""Shared local contracts, serialization, and resource identities."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATASOURCES = frozenset({
    "logstore", "metricstore", "metricsql",
    "logstore_storeview", "metricstore_storeview",
})
DASHBOARD_DATASOURCES = DATASOURCES | {"builtin"}
METRIC = frozenset({"metricstore", "metricstore_storeview"})


class SkillError(Exception):
    def __init__(self, message, code="INVALID_INPUT", **details):
        super().__init__(message)
        self.code = code
        self.details = details


def resolve_user_agent(value=None):
    """Resolve the conversation's shared User-Agent against the skill manifest."""
    variable = "ALIBABACLOUD_SLS_DASHBOARD_USERAGENT"
    try:
        manifest = json.loads((ROOT / "references/manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SkillError("Missing or invalid references/manifest.json", "INVALID_MANIFEST") from exc
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
        raise SkillError("Skill manifest requires a valid version string", "INVALID_MANIFEST")
    value = os.environ.get(variable) if value is None else value
    pattern = (r"AlibabaCloud-Agent-Skills/alibabacloud-sls-dashboard/[0-9a-f]{32} skill-version/"
               + re.escape(version))
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise SkillError(f"Set {variable} as described in SKILL.md Observability before cloud operations",
                         "INVALID_USER_AGENT")
    return value


def sls_endpoint(endpoint, region, project):
    """Return scheme and service authority for SDK/HTTP transports."""
    value = endpoint if endpoint is not None else f"{region}.log.aliyuncs.com"
    if not isinstance(value, str) or not value.strip() or any(c.isspace() for c in value):
        raise SkillError("Endpoint must be a SLS service host or HTTP(S) base URL")
    try:
        parsed = urlsplit(value if "://" in value else "https://" + value)
        port = parsed.port
    except ValueError as exc:
        raise SkillError("Invalid SLS endpoint") from exc
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or
            parsed.username is not None or parsed.password is not None or
            parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise SkillError("Endpoint must be a SLS service host or HTTP(S) base URL without credentials or API path")
    hostname = parsed.hostname
    prefix = project.lower() + "."
    if hostname.startswith(prefix):
        hostname = hostname[len(prefix):]
    authority = hostname + (f":{port}" if port is not None else "")
    return parsed.scheme, authority


def load(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def write(path, value):
    """Atomic output; keep run artifacts private by default."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def schema_check(value, name):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise SkillError("Install jsonschema as described in references/cli-installation-guide.md#python-dependencies", "MISSING_DEPENDENCY") from exc
    validator = Draft202012Validator(load(ROOT / "references" / "contracts" / f"{name}.schema.json"))
    errors = sorted(validator.iter_errors(value), key=lambda error: str(list(error.path)))
    if errors:
        raise SkillError("; ".join(f"{'.'.join(map(str, e.path)) or '$'}: {e.message}" for e in errors[:12]),
                         "CONTRACT_ERROR")


def source_check(source):
    if not isinstance(source, dict):
        raise SkillError("Source must be an object")
    if source.get("type") not in DATASOURCES:
        raise SkillError("Unsupported SLS datasource", datasource=source.get("type"))
    for key in ("id", "region", "project", "name"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise SkillError(f"Source requires {key}")
    return source


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
    if isinstance(value, str) and query.get("type") == "storeview" and value in {"logstore", "metricstore", "metricsql"}:
        value += "_storeview"
    return value


def dashboard_payload(value):
    """Only server metadata is removed; chart payloads stay byte-semantically intact."""
    return {key: copy.deepcopy(value[key]) for key in
            ("dashboardName", "displayName", "description", "attribute", "charts") if key in value}


def compare_payload(value):
    payload = dashboard_payload(value)
    payload.setdefault("description", "")
    return payload
