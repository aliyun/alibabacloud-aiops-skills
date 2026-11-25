#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer for the image detection /
repair-failure / boot-repair diagnosis skill
================================================================================
SECURITY: READ-ONLY by design. All authentication is resolved by the aliyun
CLI default credential chain (environment or the CLI's own profile store);
this module NEVER reads, writes, caches or logs any AccessKey ID / Secret and
never touches a credential configuration file. No AK/SK handling anywhere in
this module.

Internal module (prefixed with `_`). Do NOT run directly: it is imported by
the entry script and the identity helper so that every Alibaba Cloud OpenAPI
access goes through ONE place.

CLI-only backend
----------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess in argument-list form (never shell=True):

    aliyun <product> <Action> --Param value ... --user-agent <UA>

Command style is product-specific (verified against aliyun CLI 3.4.5):
  * ecs  -- built-in API metadata mode, PascalCase RPC actions, e.g.
        aliyun ecs describe-images --region-id cn-hangzhou
  * sts  -- plugin mode, lowercase-hyphenated command:
        aliyun sts get-caller-identity

Transients (Throttling / 5xx / timeout) retry up to 3 attempts with linear
backoff; other errors raise immediately. Every stderr/CLI-error string passes
through credential masking before it can surface anywhere.

Observability (MUST SA-2.11b/c)
-------------------------------
A 32-character hex session-id (`uuid.uuid4().hex`) is generated once per run
and attached to EVERY call through the `--user-agent` flag, using the
template declared in _constants.USER_AGENT_TEMPLATE.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Optional

from _constants import (
    DEFAULT_REGION,
    DEFAULT_TIMEOUT,
    MAX_PAGES,
    PAGE_SIZE,
    SKILL_NAME,
    USER_AGENT_TEMPLATE,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails. Carries `Code: Message`."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# ecs uses the CLI's built-in metadata (PascalCase action + params);
# sts is served by the sts plugin (lowercase-hyphenated commands).
_PLUGIN_STYLE_PRODUCTS = set()  # sts uses RPC PascalCase, not plugin kebab


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to the plugin kebab-case command form."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list[str]:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------
_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (lazy, then cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return USER_AGENT_TEMPLATE.format(skill=SKILL_NAME, session_id=session_id())

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-app-deploy-and-site-build"


def _manifest_meta():
    import json as _json
    import os as _os
    _d = _os.path.dirname(_os.path.abspath(__file__))
    for _ in range(6):
        _p = _os.path.join(_d, "references", "manifest.json")
        if _os.path.exists(_p):
            try:
                with open(_p, encoding="utf-8") as _fh:
                    return _json.load(_fh)
            except Exception:
                break
        _d = _os.path.dirname(_d)
    return {}


_MANIFEST = _manifest_meta()
if not _MANIFEST.get("version"):
    raise RuntimeError(
        "references/manifest.json is missing or unreadable; refusing to issue a "
        "User-Agent without a manifest-derived skill version"
    )
_SKILL_VERSION = _MANIFEST["version"]
_SKILL_PACKAGE_NAME = _PACKAGE_NAME


def _ua_normalize(ua):
    """Pin the UA skill segment to the package name the platform expects."""
    _prefix = "AlibabaCloud-Agent-Skills/"
    if not _SKILL_PACKAGE_NAME or not ua.startswith(_prefix):
        return ua
    _rest = ua[len(_prefix):]
    _head, _sep, _tail = _rest.partition("/")
    if not _sep:
        return ua
    return _prefix + _SKILL_PACKAGE_NAME + "/" + _tail
def user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


def check_cli_available() -> None:
    """Ensure the aliyun CLI is available; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI installed and\n"
            "configured through its own default credential chain.\n"
            "  Configure: aliyun configure\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Transient-error retry (Throttling / 5xx / timeout)
# ---------------------------------------------------------------------------
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 2

_RETRY_CODES = {
    "throttling", "throttling.user", "throttling.api",
    "serviceunavailable", "internalerror", "sdk.httperror", "unknownerror",
}
_RETRY_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal error",
    "http 500", "http 502", "http 503", "http 504",
    "statuscode: 5", "502", "504", "server busy",
    "connection reset", "timed out", "timeout", "temporarily unavailable",
)


def _is_retryable(err: CliError) -> bool:
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke one OpenAPI action via the aliyun CLI (retrying transients).

    Raises CliError (`Code: Message`) on failure; transient errors retry up
    to 3 attempts with linear backoff.
    """
    last_err: Optional[CliError] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, profile, timeout)
        except CliError as e:
            last_err = e
            if not _is_retryable(e):
                raise
            if attempt >= _MAX_ATTEMPTS:
                raise CliError(
                    f"{product} {action} failed after {attempt} attempts: {e}",
                    code=e.code, stderr=e.stderr)
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({e.code or 'unknown'}); retry {attempt}/"
                f"{_MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr)
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps type-checkers happy


def _call_cli(
    product: str,
    action: str,
    params: Optional[dict[str, Any]],
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    """Execute one CLI invocation (argument-list form, never shell=True)."""
    cmd = ["aliyun"] + _command_tokens(product, action)
    cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]
    # Observability: one session-id User-Agent shared by every call.
    cmd += ["--user-agent", user_agent()]

    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        cmd += [_param_flag(product, key), str(value)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # never hang on interactive prompts
        )
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun {product} {action} timed out after {timeout}s")

    if result.returncode != 0:
        stderr = _clean_stderr(result.stderr or "")
        code = _extract_error_code(stderr)
        raise CliError(
            f"aliyun {product} {action} failed: {stderr[:300]}",
            code=code, stderr=stderr)

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")
    return body if isinstance(body, dict) else {"value": body}


# ---------------------------------------------------------------------------
# Error-text hygiene: ANSI stripping + credential masking (SA-2.12)
# ---------------------------------------------------------------------------
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Every <credentialKey>=<value> / "<credentialKey>":"<value>" pair is masked
# BEFORE the text can reach a [WARN] line, a CliError message or any report
# field. Keys matched case-insensitively.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce|x-oss-credential|x-oss-signature)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential key-value pairs in CLI error text. Never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Single choke point for every CLI stderr: strip ANSI, mask credential
    values, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline self-tests for the mask (a broken mask would violate the skill's
# credential rules, so the module refuses to be trusted silently).
assert _mask_credentials("no secrets here") == "no secrets here"
_m = _clean_stderr(
    'GET "https://x/?AccessKeyId=STS.FakeKey123456&Signature=abcd1234=='
    '&SecurityToken=' + "CAIS" + ("y" * 120) + '" dial tcp')
assert "STS.FakeKey123456" not in _m and "CAIS" not in _m and "abcd1234" not in _m
assert _clean_stderr(None) == ""

_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort API error-code extraction from the CLI 3.x error envelope
    (`Code: <X>` / `ErrorCode: <X>` / inline JSON / legacy `ERROR: <X>: ...`).
    """
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("ErrorCode:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("Code:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("Data:"):
            payload = line.split(":", 1)[1].strip()
            try:
                body = json.loads(payload)
                if isinstance(body, dict) and body.get("Code"):
                    return str(body["Code"])
            except json.JSONDecodeError:
                pass
            continue
        if line.startswith("{"):
            try:
                body = json.loads(line)
                if isinstance(body, dict) and body.get("Code"):
                    return str(body["Code"])
            except json.JSONDecodeError:
                pass
        if line.startswith("ERROR:"):
            parts = line.split(":", 2)
            candidate = parts[1].strip() if len(parts) > 2 else ""
            return candidate if _ERROR_CODE_TOKEN_RE.match(candidate) else ""
    return ""


# ---------------------------------------------------------------------------
# Pagination helper (ECS list APIs use PageNumber / PageSize)
# ---------------------------------------------------------------------------
def _dig(obj: Any, path: list[str]) -> Any:
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def paginate_page_number(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    max_pages: int = MAX_PAGES,
    page_size: int = PAGE_SIZE,
) -> list[Any]:
    """Follow PageNumber pagination; returns all items across pages.

    A request-level failure on the FIRST page propagates (the evidence is
    then simply absent and the caller degrades); a failure on a later page
    stops the walk and keeps what was fetched, with a [WARN] trace.
    """
    all_items: list[Any] = []
    page = 1
    while page <= max_pages:
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = page_size
        try:
            body = call(product, action, page_params,
                        region=region, profile=profile)
        except CliError as e:
            if page == 1:
                raise
            print(f"[WARN] {product} {action} page {page} failed: {e}; "
                  f"keeping {len(all_items)} item(s) already fetched",
                  file=sys.stderr)
            break
        items = _dig(body, items_path)
        if isinstance(items, list):
            all_items.extend(items)
            if len(items) < page_size:
                break
        else:
            break
        page += 1
    else:
        print(f"[WARN] {product} {action}: stopped at the {max_pages}-page "
              f"guardrail; results may be incomplete", file=sys.stderr)
    return all_items


def resolve_account_id(
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
) -> str:
    """Return the AccountId behind the active credential ("" if unknown)."""
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region,
                    profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError:
        return ""


# --- customer-facing hygiene (2026-10-27) -----------------------------------
# The dispatcher masks its child stream, but an axis entry script is also run
# directly (evaluations, manual repros), and its own prints carried the raw
# account UID, a Cloud Assistant InvokeId or the 32-hex session id. Installing
# the mask here covers every axis of this package, because every entry imports
# this module before it prints anything.
import re as _hygiene_re
import sys as _hygiene_sys



def _hygiene_mask(text):
    if not isinstance(text, str):
        return text
    text = _hygiene_re.sub(r"(?<!\d)(1\d{15})(?!\d)",
                           lambda m: "****" + m.group(1)[-4:], text)
    text = _hygiene_re.sub(r"\bt-([a-z0-9]{6,})\b",
                           lambda m: "t-****" + m.group(1)[-4:], text)
    text = _hygiene_re.sub(r"\b([0-9a-f]{32})\b",
                           lambda m: "****" + m.group(1)[-4:], text)
    return text


class _HygieneStream(object):
    def __init__(self, stream):
        self._stream = stream

    def write(self, data):
        return self._stream.write(_hygiene_mask(data))

    def __getattr__(self, name):
        return getattr(self._stream, name)


if not isinstance(_hygiene_sys.stdout, _HygieneStream):
    _hygiene_sys.stdout = _HygieneStream(_hygiene_sys.stdout)
if not isinstance(_hygiene_sys.stderr, _HygieneStream):
    _hygiene_sys.stderr = _HygieneStream(_hygiene_sys.stderr)
