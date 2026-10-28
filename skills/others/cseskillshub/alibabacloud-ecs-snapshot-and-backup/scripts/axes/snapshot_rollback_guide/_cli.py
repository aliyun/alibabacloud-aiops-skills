#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation layer for the snapshot rollback guide
==========================================================================
SECURITY: Every call is routed through the aliyun CLI as a subprocess
(argument-list form, never shell=True) using the CLI DEFAULT credential
chain only. This module NEVER reads, prints, caches or forwards any AccessKey
ID / SecretKey / STS token; credential-looking key-value pairs found in CLI
error text are masked before they can surface anywhere. Only the actions
whitelisted in _constants.py may be invoked (enforced by require_allowed());
everything else raises immediately. The two state-changing actions
(RunCommand dispatch and the snapshot-creation action) are only ever reached
from confirmation-gated code paths inside the entry script.

Command styles (verified against aliyun CLI 3.x):
  * ecs   -- built-in API metadata mode, PascalCase RPC style:
        aliyun ecs describe-snapshots --region-id cn-hangzhou ...
  * sts   -- plugin mode, lowercase-hyphenated command:
        aliyun sts get-caller-identity

Observability: one 32-character lowercase hex session-id (uuid4().hex) is
generated lazily per script run and attached to EVERY CLI invocation of that
run as --user-agent, using the template
    AlibabaCloud-Agent-Skills/{skill-name}/{session-id}
with {skill-name} replaced by the SKILL_NAME constant.

Transient errors (Throttling / 5xx / timeout) are retried up to 3 attempts
with linear backoff; persistent errors raise CliError("Code: Message").
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
    GATED_ACTIONS,
    MAX_PAGES,
    MAX_RESULTS,
    QUERY_ACTIONS,
    SKILL_NAME,
    USER_AGENT_PREFIX,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails. Carries Code: Message."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# API whitelist enforcement
# ---------------------------------------------------------------------------

_ALLOWED: set[tuple[str, str]] = set()
for _product, _actions in QUERY_ACTIONS.items():
    for _a in _actions:
        _ALLOWED.add((_product, _a))
for _product, _actions in GATED_ACTIONS.items():
    for _a in _actions:
        _ALLOWED.add((_product, _a))


def require_allowed(product: str, action: str) -> None:
    """Reject any action outside the skill's declared whitelist."""
    if (product, action) not in _ALLOWED:
        raise CliError(
            f"action '{product}/{action}' is not in this skill's API "
            "whitelist and is absolutely prohibited"
        )


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability, MUST SA-2.11c)
# ---------------------------------------------------------------------------

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-character hex session-id (lazy, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return f"{USER_AGENT_PREFIX}/{SKILL_NAME}/{session_id()}"

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-snapshot-and-backup"


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


# ---------------------------------------------------------------------------
# CLI command construction (plugin mode for sts, metadata mode for ecs)
# ---------------------------------------------------------------------------

_PLUGIN_STYLE_PRODUCTS = set()  # sts uses RPC PascalCase, not plugin kebab


def _pascal_to_kebab(name: str) -> str:
    """PascalCase -> lowercase-hyphenated (plugin-mode command form)."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list[str]:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


def check_cli_available() -> None:
    """Ensure the aliyun CLI is on PATH; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n" + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI, installed and\n"
            "configured through its default credential chain.\n"
            "  Install:   https://help.aliyun.com/document_detail/121541.html\n"
            "  Configure: aliyun configure   (never pass keys on a command line)\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Credential masking (defense in depth for CLI error envelopes)
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Replace credential VALUES with *** while keeping key names visible."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI colors, mask credentials, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Import-time self-check that the mask holds (a broken mask would leak a
# temporary token from a CLI error envelope into a [WARN] line):
assert _mask_credentials("no secrets here") == "no secrets here"
_m = _mask_credentials(
    "GET https://x.aliyuncs.com/?AccessKeyId=FAKEEXAMPLEKEY123"
    "&SecurityToken=CAIS" + "x" * 120 + "&Signature=abc123sig")
assert "FAKEEXAMPLEKEY123" not in _m and ("x" * 120) not in _m
assert "abc123sig" not in _m and "AccessKeyId=***" in _m
assert _clean_stderr(None) == ""


# ---------------------------------------------------------------------------
# Transient-error classification and retry
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


def _extract_error_code(stderr: str) -> str:
    """Best-effort API error code from the CLI 3.x failure envelope."""
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("Code:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("Data:"):
            try:
                body = json.loads(line.split(":", 1)[1].strip())
                if isinstance(body, dict) and body.get("Code"):
                    return str(body["Code"])
            except json.JSONDecodeError:
                pass
        if line.startswith("{"):
            try:
                body = json.loads(line)
                if isinstance(body, dict) and body.get("Code"):
                    return str(body["Code"])
            except json.JSONDecodeError:
                pass
    return ""


# ---------------------------------------------------------------------------
# The single CLI call site (MUST 7.6.1: subprocess.run carries timeout=)
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = "cn-hangzhou",
    profile: Optional[str] = None,
    timeout: int = 60,
    retryable: bool = True,
) -> dict[str, Any]:
    """Invoke a whitelisted OpenAPI action through the aliyun CLI.

    retryable=False makes a single attempt: used for the confirmation-gated
    state-changing calls, where a blind retry could duplicate the write.

    Raises CliError for non-whitelisted actions and for failed calls after
    the transient-error retry budget is exhausted.
    """
    require_allowed(product, action)
    last_err: Optional[CliError] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, profile, timeout)
        except CliError as e:
            last_err = e
            if not _is_retryable(e) or not retryable:
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
    raise last_err  # pragma: no cover (loop always returns or raises)


def _call_cli(
    product: str,
    action: str,
    params: Optional[dict[str, Any]],
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    cmd = ["aliyun"] + _command_tokens(product, action)
    cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]
    # Observability UA on every single call (SA-2.11b/c).
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
        raise CliError(
            f"aliyun {product} {action} failed: {stderr[:300]}",
            code=_extract_error_code(stderr),
            stderr=stderr)

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")


# ---------------------------------------------------------------------------
# NextToken pagination for the ECS Describe* family
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def paginate(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: str = "cn-hangzhou",
    profile: Optional[str] = None,
    max_pages: int = MAX_PAGES,
) -> list[dict[str, Any]]:
    """Follow NextToken pagination; return all items across pages.

    ECS Describe* responses nest item lists as e.g. ["Snapshots", "Snapshot"]
    and carry the continuation token at the top level as "NextToken".
    """
    all_items: list[dict[str, Any]] = []
    next_token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        page_params["MaxResults"] = MAX_RESULTS
        if next_token:
            page_params["NextToken"] = next_token
        body = call(product, action, page_params, region=region, profile=profile)
        items = _dig(body, items_path)
        if isinstance(items, list):
            all_items.extend(items)
        pages += 1
        next_token = body.get("NextToken") if isinstance(body, dict) else None
        if not next_token:
            break
    if pages >= max_pages and next_token:
        print(
            f"[WARN] {product} {action}: stopped at the {max_pages}-page "
            "guardrail; results may be incomplete",
            file=sys.stderr)
    return all_items


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(region: str = "cn-hangzhou",
                       profile: Optional[str] = None) -> str:
    """Return the caller AccountId (traceability label), '' when unavailable."""
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
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
