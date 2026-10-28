#!/usr/bin/env python3
"""
_cli.py -- Shared Alibaba Cloud CLI invocation layer for the
alibabacloud-ecs-snapshot-consistency-group skill.
================================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved by
the aliyun CLI default credential chain (environment, ~/.aliyun/config.json,
or an instance RAM role). This module NEVER reads, writes, caches or logs any
AccessKey ID / Secret, and it never accepts credential arguments. No AK/SK
handling anywhere in this module.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the entry script so that ALL Alibaba Cloud OpenAPI access goes through ONE
place (single choke point for timeouts, retry, observability and credential
masking).

CLI-only backend
----------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess (argument-list form, never shell=True):

    aliyun <product> <Action> --Param value ...

Command style is product-specific:
  * ecs -- RPC style, PascalCase action names, regional endpoint resolved
    by the CLI from the --region flag, e.g.
        aliyun ecs describe-snapshots --region-id cn-hangzhou
  * sts -- plugin mode, lowercase-hyphenated commands, central endpoint
    sts.aliyuncs.com, e.g.
        aliyun sts get-caller-identity

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-retryable errors (permission
denied such as NoPermission / ImplicitDeny, invalid parameter, ...) are raised
immediately as CliError so the caller can degrade with a [WARN] line.

Public API:
    call(product, action, params=None, region=..., profile=None, timeout=...)
    paginate_rpc(product, action, params, list_container, list_key, ...)
    resolve_account_id(...) -> str
    cli_available() -> bool / check_cli_available() -> None
    session_id() -> str / user_agent() -> str
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
    DEFAULT_TIMEOUT,
    MAX_PAGES,
    PAGE_SIZE,
    SKILL_NAME,
    STS_ENDPOINT,
    STS_REGION_FOR_IDENTITY,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails (`Code: Message` form)."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Per-product endpoint metadata
# ---------------------------------------------------------------------------
# STS is a central (region-less) service, so the CLI is given its fixed
# endpoint. ECS regional endpoints are resolved by the CLI from --region;
# no fixed ECS endpoint is hardcoded here.
PRODUCT_ENDPOINTS: dict = {
    "sts": STS_ENDPOINT,  # sts.aliyuncs.com
}

# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# sts runs in plugin mode: lowercase-hyphenated commands
#     (GetCallerIdentity -> get-caller-identity).
# ecs is RPC style: the PascalCase action name is passed through unchanged.
_PLUGIN_STYLE_PRODUCTS = set()  # sts uses RPC PascalCase, not plugin kebab


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to the plugin kebab-case command form.

    Example: GetCallerIdentity -> get-caller-identity
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list:
    """Return the CLI command tokens for (product, action)."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    """Return the CLI flag for a parameter name, honoring product style."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability, MUST SA-2.11b/c)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY API call of that run as a User-Agent, so all calls of one diagnosis
# can be correlated server-side.

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run.

    Template: AlibabaCloud-Agent-Skills/{skill-name}/{session-id}
    """
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id()}"

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


def cli_available() -> bool:
    """True when the aliyun CLI binary is on PATH."""
    return shutil.which("aliyun") is not None


def check_cli_available() -> None:
    """Ensure the aliyun CLI is available; exit with guidance otherwise."""
    if not cli_available():
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI to be installed and "
            "configured.\n\n"
            "  Install: https://help.aliyun.com/document_detail/121541.html\n"
            "  Configure: aliyun configure\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Transient-error retry (Throttling / 5xx / timeout)
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 2  # wait before retry N is N * 2s (2s, 4s)

_RETRY_CODES = {
    "throttling", "throttling.user", "throttling.api",
    "serviceunavailable", "internalerror", "sdk.httperror", "unknownerror",
}
# Marker substrings searched in the lowercased error code AND error message.
# Bare "500"/"503" are intentionally NOT used (RequestId hex strings could
# false-positive); 5xx is matched via precise forms. "502"/"504" stay bare on
# purpose: the real CLI 3.x SDKError envelope only carries them as
# "StatusCode: 502"-style lines, and bare matching is required to catch them.
_RETRY_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal error",
    "http 500", "http 502", "http 503", "http 504",
    "statuscode: 5", "502", "504", "server busy",
    "connection reset", "timed out", "timeout", "temporarily unavailable",
)


def _is_retryable(err: CliError) -> bool:
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


def call(
    product: str,
    action: str,
    params: Optional[dict] = None,
    region: str = STS_REGION_FOR_IDENTITY,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Invoke an Alibaba Cloud OpenAPI action via the aliyun CLI.

    Args:
        product:  Product code, e.g. "ecs", "sts".
        action:   API action name in PascalCase, e.g. "DescribeSnapshots".
                  Translated to the product's CLI command style automatically.
        params:   Dict of request parameters; None values are skipped.
        region:   Region id (ECS queries are region-scoped; STS is central).
        profile:  Optional CLI credential profile name.
        timeout:  Per-attempt timeout in seconds (MUST 7.6.1).

    Returns:
        Parsed JSON response as a dict.

    Raises:
        CliError: On failure. Transient errors (Throttling / 5xx / timeout)
                  are retried up to 3 attempts with linear backoff (2s, 4s).
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
                    code=e.code,
                    stderr=e.stderr,
                )
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({e.code or 'unknown'}); retry {attempt}/{_MAX_ATTEMPTS - 1} "
                f"in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps type-checkers happy


def _call_cli(
    product: str,
    action: str,
    params: Optional[dict],
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict:
    """Execute one CLI invocation (argument-list form, never shell=True)."""
    cmd = ["aliyun"] + _command_tokens(product, action)

    endpoint = PRODUCT_ENDPOINTS.get(product)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]

    # Observability: one session-id UA shared by every call of this run.
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

    # Defensive: some API families can report request-level failures INSIDE
    # the response body while the CLI still exits 0. Treat any non-success
    # body Code as an invocation failure so callers degrade via the standard
    # CliError path instead of silently reading an error payload as data.
    # Successful ECS describe responses carry no top-level Code key, so the
    # happy path is untouched.
    if isinstance(body, dict):
        resp_code = str(body.get("Code") or "").strip()
        if resp_code and resp_code not in ("Success", "OK"):
            message = _clean_stderr(str(body.get("Message") or ""))
            raise CliError(
                f"aliyun {product} {action} failed: Code={resp_code} "
                f"Message={message[:300]}",
                code=resp_code,
                stderr=message,
            )
    return body


# ---------------------------------------------------------------------------
# Credential masking & error-code extraction
# ---------------------------------------------------------------------------

# Shape guard for the legacy "ERROR: <Code>: <Message>" fallback: only
# letter-led alphanumeric tokens with optional dots count as API error codes.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")

# The aliyun CLI colors its stderr output; strip ANSI escapes so error text
# embedded in reports/JSON stays plain ASCII.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Credential-value masking: the aliyun CLI network-error envelope can embed a
# signed request URL whose query string carries AccessKeyId / SecurityToken /
# Signature values. Every <credentialKey>=<value> (query-string) or
# "<credentialKey>":"<value>" (JSON) pair is masked BEFORE the text can reach
# a [WARN] stderr line, a CliError message, or any JSON output field. Keys are
# matched case-insensitively; the value charset stops at whitespace, quotes,
# XML/HTML delimiters and the query-string separator '&'.
#
# Only values that can actually travel over the wire are listed. The signing
# secret is deliberately absent: it is never transmitted, so it cannot appear
# in CLI output, and this skill has no reason to name it.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential key-value pairs in CLI error text.

    Pure function; replaces each matched credential VALUE with *** while
    keeping the key name for diagnosability. Never raises.
    """
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI color codes, MASK CREDENTIALS and collapse blank runs in
    CLI stderr text. This is the single choke point every CLI stderr passes
    through before it can surface in [WARN] lines, CliError messages or JSON
    fields."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the credential masking, executed on every
# import; a failure here means the mask is broken and the module must not
# run -- a leaked temporary token in a [WARN] line violates the skill's
# credential rules.
# normal: credential-free text passes through unchanged (ANSI/blank cleanup).
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
# boundary: signed-URL network-error envelope (AccessKeyId + >100-char
# SecurityToken + base64 Signature).
_env = (
    'GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=STS.FakeKey123456'
    "&Action=DescribeSnapshots&SecurityToken="
    + "CAIS" + ("x" * 101)
    + '&Signature=abcd1234ef==&SignatureNonce=9e2f1" dial tcp: refused')
_masked = _clean_stderr(_env)
assert "STS.FakeKey123456" not in _masked, _masked      # key id masked
assert ("x" * 101) not in _masked, _masked              # token masked
assert "abcd1234ef" not in _masked, _masked             # signature masked
assert "AccessKeyId=***" in _masked
assert "SecurityToken=***" in _masked
assert "Signature=***" in _masked
# boundary: JSON-shaped credential pairs are masked as well.
_json_env = '{"AccessKeyId": "STS.NYfake", "SecurityToken": "CAISfake99"}'
_json_masked = _clean_stderr(_json_env)
assert "STS.NYfake" not in _json_masked, _json_masked
assert "CAISfake99" not in _json_masked, _json_masked
assert _json_masked.count("***") == 2
# invalid: None / empty degrade to "" (never raise).
assert _clean_stderr(None) == ""
assert _clean_stderr("") == ""
assert _mask_credentials("") == ""


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Handles the real aliyun CLI 3.x failure envelope:

        Error: request execution failed: ... SDKError:
           StatusCode: 429
           Code: Throttling.User
           Message: Request was denied due to user flow control.
           Data: {"Code":"Throttling.User",...}
    """
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("ErrorCode:"):
            return line.split(":", 1)[1].strip()
        # SDKError envelope: indented "Code: <ApiErrorCode>" line.
        if line.startswith("Code:"):
            return line.split(":", 1)[1].strip()
        # SDKError envelope: inline JSON payload carrying a Code field.
        if line.startswith("Data:"):
            payload = line.split(":", 1)[1].strip()
            try:
                body = json.loads(payload)
                if isinstance(body, dict) and body.get("Code"):
                    return str(body["Code"])
            except json.JSONDecodeError:
                pass
            continue
        # JSON error envelope: {"Code": "Throttling", ...}
        if line.startswith("{"):
            try:
                body = json.loads(line)
                if isinstance(body, dict) and body.get("Code"):
                    return str(body["Code"])
            except json.JSONDecodeError:
                pass
        # Legacy CLI fallback: "ERROR: <Code>: <Message>". Take only the
        # token between the first and the second colon, and accept it only
        # when it matches the API-code shape (never grab prose).
        if line.startswith("ERROR:"):
            parts = line.split(":", 2)
            candidate = parts[1].strip() if len(parts) > 2 else ""
            return candidate if _ERROR_CODE_TOKEN_RE.match(candidate) else ""
    return ""


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(
    region: str = STS_REGION_FOR_IDENTITY,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Return the Alibaba Cloud UID (AccountId) of the active credential.

    Uses STS GetCallerIdentity (plugin mode: get-caller-identity), which
    needs no input beyond the configured credential. Returns "" when it
    cannot be resolved.
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region,
                    profile=profile, timeout=timeout)
        return str(body.get("AccountId", "") or "")
    except CliError:
        return ""


# ---------------------------------------------------------------------------
# Pagination helper (PageNumber style, ECS RPC response shape)
# ---------------------------------------------------------------------------

def paginate_rpc(
    product: str,
    action: str,
    params: dict,
    list_container: str,
    list_key: str,
    region: str,
    profile: Optional[str] = None,
    page_size: int = PAGE_SIZE,
    max_pages: int = MAX_PAGES,
    timeout: int = DEFAULT_TIMEOUT,
) -> list:
    """Follow PageNumber-based pagination until exhausted (with a guardrail).

    ECS RPC describe APIs return records under a wrapped container, e.g.
    {"TotalCount": N, "Snapshots": {"Snapshot": [...]}}. Both the wrapped
    shape and a plain list under the container key are tolerated.

    Returns the concatenated record list across all pages.
    """
    all_items: list = []
    page = 1
    truncated = False
    while page <= max_pages:
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = page_size
        body = call(product, action, page_params, region=region,
                    profile=profile, timeout=timeout)
        container = body.get(list_container) if isinstance(body, dict) else None
        items = None
        if isinstance(container, dict):
            items = container.get(list_key)
        elif isinstance(container, list):
            items = container
        if not isinstance(items, list) or not items:
            break
        all_items.extend(items)
        total_raw = body.get("TotalCount") if isinstance(body, dict) else None
        try:
            total_n = int(total_raw) if total_raw is not None else None
        except (TypeError, ValueError):
            total_n = None
        if total_n is not None and len(all_items) >= total_n:
            break
        page += 1
        if page > max_pages:
            truncated = True
    if truncated:
        print(
            f"[WARN] {product} {action}: pagination stopped at the "
            f"{max_pages}-page guardrail; results may be incomplete",
            file=sys.stderr,
        )
    return all_items


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
