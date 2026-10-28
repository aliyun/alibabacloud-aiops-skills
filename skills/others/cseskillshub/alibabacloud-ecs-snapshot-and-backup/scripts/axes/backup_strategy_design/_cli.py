#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer for ECS Backup Strategy Design
============================================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved by
the aliyun CLI default credential chain (~/.aliyun/config.json or
platform-injected environment variables resolved by the CLI itself). This
module NEVER reads, writes, caches or logs any credential value: no AccessKey,
Secret, or token is ever handled explicitly anywhere in this module. Credential
KEY-VALUE pairs that the CLI may embed in its own error envelope are masked
before any error text can surface (see _mask_credentials).

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the entry scripts so that all Alibaba Cloud OpenAPI access goes through ONE
place, with the same timeout, retry, masking and observability guarantees.

CLI-only backend
----------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess (argument-list form, never shell=True):

    aliyun <product> <Action> --Param value ...

Command style is product-specific (verified against aliyun CLI 3.x):
  * ecs -- built-in API metadata mode, PascalCase action + parameters:
        aliyun ecs describe-instances --region-id cn-hangzhou
  * sts -- plugin mode, lowercase-hyphenated commands:
        aliyun sts get-caller-identity

Only read-only Describe/Get-class actions are ever invoked by this skill; the
API whitelist lives in SKILL.md and references/ram-policies.md.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-retryable errors (permission
denied, invalid parameter, ...) are raised immediately.

Public API:
    call(product, action, params=None, region=..., profile=None) -> dict
    list_instances(region, instance_ids=None, profile=None) -> list[dict]
    resolve_account_id(profile=None) -> str
"""

from __future__ import annotations

import json
import re
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
    STATUS_PAGE_SIZE,
    STS_ENDPOINT,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Per-product endpoint metadata
# ---------------------------------------------------------------------------
# STS is a central (region-less) service: pin the endpoint so calls never
# depend on the caller's default region. ECS resolves its own regional
# endpoint from the RegionId parameter, so no endpoint override is needed.
PRODUCT_ENDPOINTS: dict = {
    "sts": STS_ENDPOINT,  # sts.aliyuncs.com
}

# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# ecs uses the CLI's built-in metadata: PascalCase action + params,
#     e.g. `aliyun ecs describe-instances --region-id cn-hangzhou`
# sts is served by the aliyun CLI sts plugin: lowercase-hyphenated commands,
#     e.g. `aliyun sts get-caller-identity`
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
# Session-ID & User-Agent (observability, SA-2.11)
# ---------------------------------------------------------------------------
# A 32-character lowercase hex session-id is generated once per script run and
# attached to EVERY API call of that run as a --user-agent flag, so all calls
# of one advisory run can be correlated server-side:
#   AlibabaCloud-Agent-Skills/<skill-name>/<session-id>

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached).

    Generated exactly once per run with uuid.uuid4().hex and reused by every
    call of this run.
    """
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
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
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Invoke an Alibaba Cloud OpenAPI action via the aliyun CLI.

    Args:
        product:  Product code, e.g. "ecs", "sts".
        action:   API action name in PascalCase, e.g. "DescribeInstances".
                  Translated to the product's CLI command style automatically.
        params:   Dict of request parameters (PascalCase keys for ecs);
                  None values are skipped.
        region:   Region id passed to the CLI as the --region context.
        profile:  Optional CLI credential profile name.
        timeout:  Per-attempt timeout in seconds (MUST 7.6.1: every
                  subprocess call carries it).

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
    except FileNotFoundError:
        raise CliError(
            "aliyun CLI not found on this machine; install it (see "
            "https://help.aliyun.com/document_detail/121541.html) and run "
            "`aliyun configure`. This skill has no other API backend."
        )

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
    if not isinstance(body, dict):
        raise CliError(f"aliyun {product} {action} returned unexpected JSON shape")
    return body


# Shape guard for the legacy "ERROR: <Code>: <Message>" fallback: only
# letter-led alphanumeric tokens with optional dots count as API error codes.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")

# The aliyun CLI colors its stderr output; strip ANSI escapes so error text
# embedded in reports/JSON stays plain ASCII.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Credential-value masking: the aliyun CLI network-error envelope embeds a
# signed request URL whose query string carries credential values. Every
# <credential-key>=<value> (query-string) or "<credential-key>":"<value>"
# (JSON) pair is masked BEFORE the text can reach a [WARN] stderr line, a
# CliError message, or any JSON output field. Keys are matched
# case-insensitively; the value charset stops at whitespace, quotes, XML/HTML
# delimiters and the query-string separator '&'.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
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
    """Strip ANSI color codes, MASK CREDENTIALS, and collapse blank runs in
    CLI stderr text. This is the single choke point every CLI stderr passes
    through before it can surface in [WARN] lines, CliError messages or JSON
    fields."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the credential masking, executed on every
# import; a failure here means the mask is broken and the module must not run.
# normal: credential-free text passes through unchanged (ANSI/blank cleanup
# only).
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
# boundary: signed-URL network-error envelope (credential id + long token +
# base64 signature) -- the exact reproduction shape.
_bl3_env = (
    'GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=STS.NYoy5FakeKey1234'
    "&Action=DescribeInstances&SecurityToken="
    + "CAIS" + ("x" * 101)
    + '&Signature=abcd1234ef==&SignatureNonce=9e2f1" dial tcp: refused')
_bl3_masked = _clean_stderr(_bl3_env)
assert "STS.NYoy5FakeKey1234" not in _bl3_masked, _bl3_masked  # id masked
assert ("x" * 101) not in _bl3_masked, _bl3_masked             # token masked
assert "abcd1234ef" not in _bl3_masked, _bl3_masked            # sig masked
assert "AccessKeyId=***" in _bl3_masked
assert "SecurityToken=***" in _bl3_masked
assert "Signature=***" in _bl3_masked
# boundary: JSON-shaped credential pairs are masked as well.
_bl3_json = '{"AccessKeyId": "STS.NYfake", "SecurityToken": "CAISfake99"}'
_bl3_json_masked = _clean_stderr(_bl3_json)
assert "STS.NYfake" not in _bl3_json_masked, _bl3_json_masked
assert "CAISfake99" not in _bl3_json_masked, _bl3_json_masked
assert _bl3_json_masked.count("***") == 2
# invalid: None / empty degrade to "" (never raise).
assert _clean_stderr("") == ""


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Handles the real aliyun CLI 3.x failure envelope:

        Error: request execution failed: ... SDKError:
           StatusCode: 403
           Code: NoPermission
           Message: User not authorized to operate on the specified resource.
           Data: {"Code":"NoPermission",...}
    """
    for line in (stderr or "").splitlines():
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


# Inline boundary assertions for the error-code extractor (normal / boundary /
# invalid inputs), executed on every import.
assert _extract_error_code(
    "Error: SDKError:\n   StatusCode: 403\n   Code: NoPermission\n"
    "   Message: denied") == "NoPermission"
assert _extract_error_code(
    'ERROR: Throttling.User: Request was denied due to flow control'
) == "Throttling.User"
assert _extract_error_code("") == ""
assert _extract_error_code("some random prose without a code") == ""


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(region: str = DEFAULT_REGION,
                       profile: Optional[str] = None) -> str:
    """Return the Alibaba Cloud account UID (AccountId) of the active
    credential via STS GetCallerIdentity, or "" when it cannot be resolved.
    The UID is used only as a report traceability label."""
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError:
        return ""


# ---------------------------------------------------------------------------
# ECS instance facts (read-only; the ONLY ECS actions this skill calls)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list) -> Any:
    """Walk a nested dict along `path`; return None on any miss."""
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def list_instances(region: str, instance_ids: Optional[list] = None,
                   profile: Optional[str] = None) -> list:
    """Query instance facts via read-only DescribeInstances.

    Args:
        region:       Region id for the query (results are region-scoped).
        instance_ids: Optional list of instance ids to filter by; when None,
                      every instance visible to the credential in the region
                      is returned.
        profile:      Optional CLI credential profile name.

    Returns the (possibly empty) list of instance dicts. Raises CliError on
    a non-retryable failure (callers degrade gracefully around it).
    """
    params: dict = {"RegionId": region, "PageSize": PAGE_SIZE}
    if instance_ids:
        # DescribeInstances filters by a JSON-array string in InstanceIds.
        params["InstanceIds"] = json.dumps(list(instance_ids))
    out: list = []
    pages = 0
    while pages < MAX_PAGES:
        params["PageNumber"] = pages + 1
        body = call("ecs", "DescribeInstances", dict(params),
                    region=region, profile=profile)
        items = _dig(body, ["Instances", "Instance"])
        if not isinstance(items, list) or not items:
            break
        out.extend(items)
        pages += 1
        total = body.get("TotalCount")
        try:
            if total is not None and len(out) >= int(total):
                break
        except (TypeError, ValueError):
            pass
        if len(items) < PAGE_SIZE:
            break
    if pages >= MAX_PAGES:
        print(
            f"[WARN] DescribeInstances stopped at the {MAX_PAGES}-page "
            "guardrail; results may be incomplete",
            file=sys.stderr,
        )
    return out


def get_instance_statuses(region: str, instance_ids: list,
                          profile: Optional[str] = None) -> dict:
    """Query lightweight status facts via read-only DescribeInstanceStatus.

    Returns {instance_id: status} (possibly empty). Raises CliError on a
    non-retryable failure (callers degrade gracefully around it).
    """
    params: dict = {"RegionId": region, "PageSize": STATUS_PAGE_SIZE}
    for idx, iid in enumerate(instance_ids[:STATUS_PAGE_SIZE], start=1):
        params[f"InstanceId.{idx}"] = iid
    statuses: dict = {}
    body = call("ecs", "DescribeInstanceStatus", params,
                region=region, profile=profile)
    items = _dig(body, ["InstanceStatuses", "InstanceStatus"])
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                iid = str(item.get("InstanceId") or "")
                if iid:
                    statuses[iid] = str(item.get("Status") or "")
    return statuses


# Inline boundary assertion for the PascalCase-to-kebab plugin translation
# (SA-2.11: plugin-mode products use lowercase-hyphenated commands).
assert _pascal_to_kebab("GetCallerIdentity") == "get-caller-identity"
assert _command_tokens("sts", "GetCallerIdentity") == ["sts", "GetCallerIdentity"]
assert _command_tokens("ecs", "DescribeInstances") == ["ecs", "DescribeInstances"]


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
