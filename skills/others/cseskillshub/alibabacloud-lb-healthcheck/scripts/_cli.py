#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation helper for LB Health Check Diagnosis
==============================================================================
Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the diagnose scripts so that ALL Alibaba Cloud OpenAPI access goes through ONE
interceptable path.

CLI plugin-mode backend
-----------------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI in
plugin mode (lowercase-hyphenated commands):

    aliyun <product> <lowercase-hyphenated-action> --region <r> --<param> <v> ...

e.g.  aliyun slb describe-load-balancer-attribute --load-balancer-id lb-xxx
      aliyun alb list-listeners --load-balancer-ids '["alb-xxx"]'

Required plugins (install once): aliyun-cli-slb / aliyun-cli-alb /
aliyun-cli-nlb / aliyun-cli-vpc  (`aliyun plugin install --names <name>`).

Zero credential code: authentication is resolved entirely by the CLI default
credential chain (~/.aliyun/config.json or platform-injected environment).
This module never reads, caches, assumes or refreshes any AK/SK/STS token.

All calls are strictly READ-ONLY (Describe* / List* / Get* only).

Public API:
    call(product, action, params=None, region=..., timeout=60) -> dict
    paginate_page(product, action, params, region, ...) -> list[dict]      # CurrentPage/PageSize style
    paginate_next_token(product, action, params, region, ...) -> list[dict] # NextToken style
    resolve_region(arg_region) -> str
    check_cli_available() -> None
    ERROR_LOG -> list[str]   # graceful degradation ledger
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Optional


class CliError(RuntimeError):
    """Raised when an aliyun-CLI invocation fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Per-product metadata (informational; the CLI plugins resolve endpoints and
# API versions internally -- we never pass credentials or sign requests here)
# ---------------------------------------------------------------------------
PRODUCT_META: dict[str, dict[str, str]] = {
    "slb": {"endpoint_tmpl": "slb.{region}.aliyuncs.com", "version": "2014-05-15"},
    "alb": {"endpoint_tmpl": "alb.{region}.aliyuncs.com", "version": "2020-06-16"},
    "nlb": {"endpoint_tmpl": "nlb.{region}.aliyuncs.com", "version": "2022-04-30"},
    "vpc": {"endpoint_tmpl": "vpc.{region}.aliyuncs.com", "version": "2016-04-28"},
    "sts": {"endpoint": "sts.aliyuncs.com", "version": "2015-04-01"},
}

_DEFAULT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Session-ID & User-Agent (Observability)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per process and attached to
# every API call for platform-level tracing / correlation.

_SKILL_ID = "alibabacloud-lb-healthcheck"
_SESSION_ID: Optional[str] = None


def get_session_id() -> str:
    """Return the per-invocation 32-char hex session-id (generated lazily)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex  # 32-char hex string
        print(f"[_cli] session-id: {_SESSION_ID}", file=sys.stderr)
    return _SESSION_ID


def get_user_agent() -> str:
    """Return the User-Agent header value for all API calls."""
    return f"AlibabaCloud-Agent-Skills/{_SKILL_ID}/{get_session_id()}"


def _subprocess_env() -> dict:
    """Environment for subprocess calls: inherit current env untouched, plus
    the skill User-Agent exported via environment variables as well."""
    env = dict(os.environ)
    ua = get_user_agent()
    env["ALIBABACLOUD_USER_AGENT"] = ua
    env["ALIBABA_CLOUD_USER_AGENT"] = ua
    return env


def check_cli_available() -> None:
    """Ensure the aliyun CLI is available; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI (>= 3.4) with the product\n"
            "plugins installed and configured.\n\n"
            "  Install CLI : https://help.aliyun.com/document_detail/121541.html\n"
            "  Plugins     : aliyun plugin install --names aliyun-cli-slb\n"
            "                aliyun plugin install --names aliyun-cli-alb\n"
            "                aliyun plugin install --names aliyun-cli-nlb\n"
            "                aliyun plugin install --names aliyun-cli-vpc\n"
            "  Configure   : aliyun configure\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Region resolution: --region arg > env aliases > CLI config current profile
# ---------------------------------------------------------------------------

_REGION_ENV_KEYS = (
    "ALIBABA_CLOUD_REGION_ID",
    "ALIBABACLOUD_REGION_ID",
    "ALIBABA_CLOUD_REGION",
    "REGION_ID",
)


def _region_from_cli_config() -> Optional[str]:
    """Read region_id of the current profile from ~/.aliyun/config.json."""
    cfg_path = os.path.expanduser(os.path.join("~", ".aliyun", "config.json"))
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return None
    current = cfg.get("current") or ""
    for profile in cfg.get("profiles") or []:
        if profile.get("name") == current:
            region = (profile.get("region_id") or "").strip()
            if region:
                return region
    return None


def resolve_region(arg_region: Optional[str]) -> str:
    """Resolve the effective RegionId.

    Fallback chain: explicit argument > environment variable aliases >
    ~/.aliyun/config.json current profile. Exits with guidance if none.
    """
    if arg_region and arg_region.strip():
        return arg_region.strip()
    for key in _REGION_ENV_KEYS:
        value = (os.environ.get(key) or "").strip()
        if value:
            return value
    region = _region_from_cli_config()
    if region:
        return region
    print(
        "[ERROR] Cannot determine RegionId. Provide --region <RegionId>, or set "
        "ALIBABA_CLOUD_REGION_ID, or configure a default region via "
        "'aliyun configure' (~/.aliyun/config.json).",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Graceful degradation ledger
# ---------------------------------------------------------------------------
# Central error ledger: every failed API attempt, INCLUDING transient errors
# later recovered by retry. The entry scripts surface these in the report's
# Graceful Degradation Log so operators can verify error handling.

ERROR_LOG: list[str] = []

# When the caller renders JSON on stdout, [WARN] lines are suppressed on
# stdout (they still reach stderr) so the JSON payload stays parseable.
_WARN_STDOUT = True


def set_warn_stdout(enabled: bool) -> None:
    """Enable/disable echoing [WARN] lines to stdout (default enabled)."""
    global _WARN_STDOUT
    _WARN_STDOUT = bool(enabled)


def _warn(msg: str) -> None:
    """Emit a [WARN] line to BOTH stdout and stderr so it survives any
    output-capture style (stdout-only redirection included). When JSON output
    is active, stdout echoing is disabled via set_warn_stdout(False)."""
    print(msg, file=sys.stderr)
    if _WARN_STDOUT:
        print(msg)


# ---------------------------------------------------------------------------
# Transient-error retry (ServiceUnavailable / Throttling / InternalError)
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 3

_RETRY_CODES = {
    "serviceunavailable", "throttling", "throttling.user", "throttling.api",
    "internalerror", "sdk.httperror", "unknownerror",
}
_RETRY_MARKERS = (
    "serviceunavailable", "throttling", "internal error", "internalerror",
    "http 503", "http 500", "http 502", "connection reset", "timed out",
    "timeout", "temporarily unavailable",
)


def _is_retryable(err: CliError) -> bool:
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    msg = str(err).lower()
    return any(m in msg for m in _RETRY_MARKERS)


def is_unauthorized(err: CliError) -> bool:
    """Whether the failure is a permission denial (403 / Forbidden)."""
    code = (getattr(err, "code", "") or "").lower()
    blob = f"{code} {err} {getattr(err, 'stderr', '')}".lower()
    return any(m in blob for m in (
        "forbidden", "nopermission", "not authorized", "unauthorized", "403",
    ))


# ---------------------------------------------------------------------------
# Parameter key -> plugin-mode flag conversion
# ---------------------------------------------------------------------------
# Plugin mode only accepts lowercase-hyphenated flags (PascalCase is rejected).
# Most keys convert mechanically (LoadBalancerId -> --load-balancer-id); a few
# product-specific names need explicit overrides.

_FLAG_OVERRIDES = {
    "VServerGroupId": "vserver-group-id",  # NOT v-server-group-id
}

# (product, param_key) pairs whose plugin flags expect space-separated bare
# values ("--flag v1 v2 v3") instead of a JSON array string. Passing a JSON
# array to these flags silently returns empty results (no error), so they
# must be expanded into repeated argv items.
_SPACE_LIST_PARAMS = {
    ("nlb", "LoadBalancerIds"),
    ("nlb", "ServerGroupIds"),
}


def _to_flag(key: str) -> str:
    if key in _FLAG_OVERRIDES:
        return "--" + _FLAG_OVERRIDES[key]
    out = re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", key)
    return "--" + out.lower()


def _format_value(value: Any) -> str:
    """Serialize a parameter value for the CLI command line.

    list/tuple -> JSON array string (plugin 'list' parameters, expanded to
    repeated query params like ServerGroupIds.1 / ServerGroupIds.2 by the CLI).
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return json.dumps(list(value))
    return str(value)


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = _DEFAULT_REGION,
    timeout: int = 60,
) -> dict[str, Any]:
    """Invoke an Alibaba Cloud OpenAPI action via the aliyun CLI (plugin mode).

    `action` is the lowercase-hyphenated plugin command, e.g.
    'describe-load-balancer-attribute'. Returns the parsed JSON response.
    Raises CliError on failure. Transient errors (ServiceUnavailable /
    Throttling / InternalError / timeout) are retried up to 3 attempts with
    linear backoff before raising.
    """
    last_err: Optional[CliError] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, timeout)
        except CliError as e:
            last_err = e
            if not _is_retryable(e):
                line = f"{product} {action} failed: {e.code or 'Error'} -- {e}"
                ERROR_LOG.append(line)
                _warn(f"[WARN] {line}")
                raise
            if attempt >= _MAX_ATTEMPTS:
                line = (f"{product} {action} failed after {attempt} attempts: "
                        f"{e.code or 'Error'} -- {e}")
                ERROR_LOG.append(line)
                _warn(f"[WARN] {line}")
                raise
            wait_s = attempt * 2
            line = (f"{product} {action} transient error ({e.code or 'unknown'}); "
                    f"retry {attempt}/{_MAX_ATTEMPTS - 1} in {wait_s}s")
            ERROR_LOG.append(line)
            _warn(f"[WARN] {line}")
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps type-checkers happy


def _call_cli(
    product: str,
    action: str,
    params: Optional[dict[str, Any]],
    region: str,
    timeout: int,
) -> dict[str, Any]:
    cmd = ["aliyun", product, action, "--region", region]

    # Observability: inject User-Agent for platform tracing (flag + env var).
    cmd += ["--user-agent", get_user_agent()]

    for key, value in (params or {}).items():
        if value is None:
            continue
        if (product, key) in _SPACE_LIST_PARAMS and isinstance(value, (list, tuple)):
            # Space-separated multi-value form: --flag v1 v2 v3
            cmd += [_to_flag(key)] + [str(v) for v in value]
            continue
        cmd += [_to_flag(key), _format_value(value)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=_subprocess_env(),
        )
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun {product} {action} timed out after {timeout}s")
    except FileNotFoundError:
        raise CliError("aliyun CLI not found on PATH")

    if result.returncode != 0:
        code, message = _parse_cli_error(result.stdout, result.stderr)
        stderr = (result.stderr or "").strip()
        raise CliError(
            f"{code}: {message}"[:600],
            code=code,
            stderr=stderr,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")
    # Some APIs return an in-body error payload with a 0 exit code.
    if isinstance(body, dict) and body.get("Code") and body.get("Message") is not None \
            and str(body.get("Code")) not in ("200", "OK", ""):
        raise CliError(
            f"aliyun {product} {action} failed: {body.get('Code')}: {body.get('Message')}",
            code=str(body.get("Code")),
        )
    return body if isinstance(body, dict) else {"_items": body}


def _parse_cli_error(stdout: str, stderr: str) -> tuple[str, str]:
    """Extract (Code, Message) from aliyun CLI error output (JSON or text).

    Handles both JSON error payloads and the plugin-mode multi-line SDKError
    format ('StatusCode:' / 'Code:' / 'Message:' lines).
    """
    for text in (stdout, stderr):
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict) and data.get("Code"):
            return str(data["Code"]), str(data.get("Message", ""))[:300]
    detail = (stderr or stdout or "").strip()
    code = message = ""
    for line in detail.splitlines():
        s = line.strip()
        if s.startswith("ErrorCode:"):
            return s.split(":", 1)[1].strip(), detail[:300]
        if s.startswith("Code:") and not code:
            code = s.split(":", 1)[1].strip()
        elif s.startswith("Message:") and not message:
            message = s.split(":", 1)[1].strip()
    if code:
        return code, (message or detail)[:300]
    for line in detail.splitlines():
        s = line.strip()
        if s.startswith("ERROR:") or s.startswith("Error:"):
            return "CliError", s.split(":", 1)[1].strip()[:300]
    return "CliError", detail[:300]


# ---------------------------------------------------------------------------
# Pagination helpers (both capped by max_pages to prevent runaway loops)
# ---------------------------------------------------------------------------

def _dig(body: dict, dotted_key: str) -> Any:
    """Fetch a possibly-nested value using a dotted key ('VSwitches.VSwitch')."""
    node: Any = body
    for part in dotted_key.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def paginate_page(
    product: str,
    action: str,
    params: dict[str, Any],
    region: str = _DEFAULT_REGION,
    items_key: str = "Items",
    page_req_key: str = "CurrentPage",
    page_size_key: str = "PageSize",
    page_size: int = 50,
    max_pages: int = 100,
    timeout: int = 60,
) -> list[Any]:
    """Follow CurrentPage/PageSize (or PageNumber/PageSize) pagination.

    Reads the item list under `items_key` (dotted paths supported) and the
    total count from `TotalCount` / `Count` when present. Stops when the
    accumulated count reaches the total, a page is empty/short, or
    `max_pages` is hit.
    """
    all_items: list[Any] = []
    page = 1
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        page_params[page_req_key] = page
        page_params[page_size_key] = page_size
        body = call(product, action, page_params, region=region, timeout=timeout)

        items = _dig(body, items_key)
        if not isinstance(items, list):
            items = []
        all_items.extend(items)
        pages += 1

        total = body.get("TotalCount") or body.get("Count") or 0
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = 0

        if not items:
            break
        if total and len(all_items) >= total:
            break
        if len(items) < page_size:
            break
        page += 1
    return all_items


def paginate_next_token(
    product: str,
    action: str,
    params: dict[str, Any],
    region: str = _DEFAULT_REGION,
    items_key: str = "Items",
    token_req_key: str = "NextToken",
    token_resp_key: str = "NextToken",
    max_results_key: str = "MaxResults",
    max_results: int = 100,
    max_pages: int = 200,
    timeout: int = 60,
) -> list[Any]:
    """Follow NextToken-based pagination (ALB/NLB List* style).

    Returns the concatenated list under `items_key` (dotted paths supported)
    across all pages, capped by `max_pages`.
    """
    all_items: list[Any] = []
    next_token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        if max_results:
            page_params[max_results_key] = max_results
        if next_token:
            page_params[token_req_key] = next_token
        body = call(product, action, page_params, region=region, timeout=timeout)
        items = _dig(body, items_key)
        if not isinstance(items, list):
            items = []
        all_items.extend(items)
        next_token = body.get(token_resp_key)
        pages += 1
        if not next_token:
            break
    return all_items
