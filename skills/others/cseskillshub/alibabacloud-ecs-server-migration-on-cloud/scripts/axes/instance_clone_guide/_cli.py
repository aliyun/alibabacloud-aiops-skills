#!/usr/bin/env python3
"""
_cli.py -- shared aliyun-CLI invocation layer for the ECS instance clone
guide skill.

SECURITY: this skill is strictly READ-ONLY and guidance-only. All
authentication is resolved by the aliyun CLI default credential chain
(environment or ~/.aliyun/config.json). This module NEVER reads, prints,
caches or forwards any AccessKey ID / SecretKey / STS token; error text from
the CLI is credential-masked before it can surface anywhere. Only the
read-only (product, action) pairs in _constants.ALLOWED_ACTIONS
(ecs:DescribeInstances, ecs:DescribeInstanceStatus, sts:GetCallerIdentity)
can pass this layer; anything else raises CliError. No command is ever run
inside a customer instance; the customer performs every change in the
console.

Internal module (leading underscore). Do NOT run directly -- the entry
scripts import it so every Alibaba Cloud OpenAPI access goes through ONE
place with retry, timeout, masking, pagination and observability guarantees.

CLI-only transport
------------------
Every API call runs the `aliyun` CLI as a subprocess with an ARGUMENT LIST
and never through a shell interpreter, one timeout per call (MUST 7.6.1):

  * ecs -- built-in API metadata mode, PascalCase action and parameters:
        aliyun ecs describe-instances --region-id <region> ...
  * sts -- CLI plugin mode, lowercase-hyphenated command:
        aliyun sts get-caller-identity

Transient-error retry
---------------------
Throttling / 5xx / timeout failures are transient: up to 3 attempts with
linear backoff (2s, 4s). Non-transient errors (NoPermission, ImplicitDeny,
invalid parameter, ...) raise immediately.

Observability (MUST SA-2.11b/c)
-------------------------------
One 32-character hex session-id (uuid4().hex) per script run is attached to
EVERY CLI call as:  --user-agent AlibabaCloud-Agent-Skills/<skill>/<sid>
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
    ALLOWED_ACTIONS,
    DEFAULT_TIMEOUT,
    MAX_PAGES,
    MAX_RESULTS,
    SKILL_NAME,
    STS_ENDPOINT,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails or is not permitted."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Command-style registry (verified against aliyun CLI 3.x behaviour)
# ---------------------------------------------------------------------------
# ecs: built-in metadata mode -> PascalCase action + PascalCase params.
# sts: plugin mode -> lowercase-hyphenated command name.
_PLUGIN_STYLE_PRODUCTS = set()  # sts uses RPC PascalCase, not plugin kebab

# Region-less central endpoints; regional products (ecs) let the CLI resolve
# the endpoint from --region.
_PRODUCT_ENDPOINTS = {
    "sts": STS_ENDPOINT,
}


def _pascal_to_kebab(name: str) -> str:
    """PascalCase -> plugin kebab-case, e.g. GetCallerIdentity ->
    get-caller-identity."""
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
# API whitelist guardrail (deny by default)
# ---------------------------------------------------------------------------

def _check_whitelist(product: str, action: str) -> None:
    """Reject any action outside the verified read-only whitelist."""
    if (product, action) not in ALLOWED_ACTIONS:
        raise CliError(
            f"'{product} {action}' is outside this read-only skill's API "
            f"whitelist {sorted(a for _, a in ALLOWED_ACTIONS)}; the request "
            "was NOT sent."
        )


assert _pascal_to_kebab("GetCallerIdentity") == "get-caller-identity"
assert _command_tokens("ecs", "DescribeInstances") == ["ecs", "DescribeInstances"]
assert _command_tokens("sts", "GetCallerIdentity") == ["sts", "GetCallerIdentity"]
assert _param_flag("ecs", "RegionId") == "--RegionId"
assert _param_flag("sts", "RegionId") == "--RegionId"
try:
    _check_whitelist("ecs", "DeleteInstance")
    raise AssertionError("whitelist guard failed to block a mutating action")
except CliError:
    pass


# ---------------------------------------------------------------------------
# Session-id & User-Agent (observability, MUST SA-2.11c)
# ---------------------------------------------------------------------------
_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (lazy, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id()}"

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-server-migration-on-cloud"


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


# Shell-safety guard for every value placed into the subprocess argument
# list. Instance IDs / region IDs / instance names are short conservative
# tokens; anything else is refused so a malformed value can never become an
# option-injection vector (arguments are passed to the process directly and
# never interpreted by a shell).
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._:*@\-/ ]{1,200}$")


def esc(label: str, value: Any) -> str:
    """Validate one CLI parameter value and return it as a string."""
    text = str(value)
    if not text or text.startswith("-") or not _SAFE_TOKEN_RE.match(text):
        raise CliError(
            f"invalid {label}: refusing to pass a value that is empty, "
            "starts with '-', or contains characters outside "
            "letters/digits/._:*@-/space"
        )
    return text


assert esc("instance-id", "i-bp1a2b3c4d5e6f7g8h") == "i-bp1a2b3c4d5e6f7g8h"
assert esc("region", "cn-hangzhou") == "cn-hangzhou"
try:
    esc("instance-id", "--help")
    raise AssertionError("esc() must reject leading-dash values")
except CliError:
    pass
try:
    esc("name", "bad;rm")
    raise AssertionError("esc() must reject shell metacharacters")
except CliError:
    pass


def check_cli_available() -> None:
    """Ensure the aliyun CLI is installed; otherwise exit with guidance."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI to be installed and\n"
            "configured through its default credential chain.\n\n"
            "  Install: https://help.aliyun.com/document_detail/121541.html\n"
            "  Configure: aliyun configure\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Transient-error classification
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


# ---------------------------------------------------------------------------
# Credential masking (single choke point for all CLI stderr / error text)
# ---------------------------------------------------------------------------
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential key=value / key: value pairs in CLI error text.

    Pure function; keeps the key name, replaces the value with ***.
    Never raises.
    """
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI colors, mask credentials, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the masking pure function: normal /
# boundary / invalid inputs; a failure here means the mask is broken.
# The fixture is assembled from fragments on purpose: writing a real
# key=value pair here would leave credential-shaped text in shipped source.
assert _mask_credentials("no secrets here") == "no secrets here"
_AK_KEY = "Access" + "KeyId"
_TOK_KEY = "Security" + "Token"
_SIG_KEY = "Signature"
_FAKE_AK = "STS.fake" + "key123"
_FAKE_TOK = "CAIS" + ("x" * 101)
_FAKE_SIG = "abcd1234" + "ef=="
_ENV_HOST = "https://ecs.cn-hangzhou.aliyuncs.com/"
_env = (
    'GET "' + _ENV_HOST + "/?" + _AK_KEY + "=" + _FAKE_AK +
    "&Action=DescribeInstances&" + _TOK_KEY + "=" + _FAKE_TOK +
    "&" + _SIG_KEY + "=" + _FAKE_SIG +
    "&" + _SIG_KEY + "Nonce=9e2f1\" dial tcp: refused")
_masked = _clean_stderr(_env)
assert _FAKE_AK not in _masked
assert ("x" * 101) not in _masked
assert _FAKE_SIG not in _masked
assert _AK_KEY + "=***" in _masked and _TOK_KEY + "=***" in _masked
assert _clean_stderr(None) == ""
assert _clean_stderr("") == ""

_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort API error-code extraction from CLI stderr.

    Handles the aliyun CLI 3.x envelope:
        Error: request execution failed: ... SDKError:
           StatusCode: 403
           Code: NoPermission
           Message: ...
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
# Core invocation
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = "cn-hangzhou",
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke a whitelisted read-only OpenAPI action via the aliyun CLI.

    Raises CliError on whitelist violation, transport failure, non-zero
    exit or a non-JSON response. Transient errors retry up to 3 attempts.
    """
    _check_whitelist(product, action)
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
                    code=e.code, stderr=e.stderr,
                )
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({e.code or 'unknown'}); retry {attempt}/"
                f"{_MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr,
            )
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
    cmd = ["aliyun"] + _command_tokens(product, action)
    endpoint = _PRODUCT_ENDPOINTS.get(product)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    cmd += ["--region", esc("region", region)]
    if profile:
        cmd += ["--profile", esc("profile", profile)]
    # Observability: one session-id User-Agent shared by every call of the run.
    cmd += ["--user-agent", user_agent()]

    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        cmd += [_param_flag(product, key), esc(f"param {key}", value)]

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
            stderr=stderr,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")
    if not isinstance(body, dict):
        raise CliError(f"aliyun {product} {action} returned unexpected JSON type")
    return body


# ---------------------------------------------------------------------------
# Identity helper (traceability label only)
# ---------------------------------------------------------------------------

def resolve_account_id(region: str = "cn-hangzhou",
                       profile: Optional[str] = None) -> str:
    """Return the caller's account UID via sts get-caller-identity, or ''.

    The UID is used only as a report traceability label; it also documents
    the hard data boundary: every read-only query sees ONLY this account.
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region,
                    profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError:
        return ""


# ---------------------------------------------------------------------------
# Pagination helper (NextToken style, ECS shape)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def paginate_next_token(
    product: str,
    action: str,
    params: dict[str, Any],
    region: str = "cn-hangzhou",
    profile: Optional[str] = None,
    items_path: Optional[list[str]] = None,
    token_resp_path: Optional[list[str]] = None,
    max_results: int = MAX_RESULTS,
    max_pages: int = MAX_PAGES,
) -> list[Any]:
    """Follow NextToken pagination with a page-count guardrail.

    ECS DescribeInstances returns items at Instances.Instance and carries the
    continuation token at the top level as NextToken (verified response
    shape); both paths are configurable. Returns the concatenated list.
    """
    items_path = items_path or ["Instances", "Instance"]
    token_resp_path = token_resp_path or ["NextToken"]

    all_items: list[Any] = []
    next_token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        page_params["MaxResults"] = max_results
        if next_token:
            page_params["NextToken"] = next_token
        body = call(product, action, page_params, region=region,
                    profile=profile)
        items = _dig(body, items_path)
        if isinstance(items, dict):
            items = items.get("Item")
        if isinstance(items, list):
            all_items.extend(items)
        pages += 1
        next_token = _dig(body, token_resp_path)
        if not next_token:
            break
    if pages >= max_pages and next_token:
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
