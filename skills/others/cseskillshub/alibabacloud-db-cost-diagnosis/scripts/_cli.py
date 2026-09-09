#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation helper for DB Cost Diagnosis
==================================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved by
the aliyun CLI default credential chain (~/.aliyun/config.json or
platform-injected environment). This module NEVER reads, writes, caches or
logs any AccessKey ID / Secret. No AK/SK handling anywhere in this module.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the query scripts so that all Alibaba Cloud OpenAPI access goes through ONE
place.

CLI-only backend
----------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess (argument-list form, never shell=True).

Command style is product-specific, verified against the evaluated CLI build:
  * sts -- plugin mode, lowercase-hyphenated command:
        aliyun sts get-caller-identity
  * bssopenapi -- built-in API metadata mode: the RPC action name and its
    request parameters are passed exactly as the OpenAPI specification
    declares them (DescribeInstanceBill / DescribeSplitItemBill, with
    BillingCycle / InstanceID / Granularity / BillingDate parameters).
    The lowercase-hyphenated form is NOT accepted for this product -- the CLI
    prints its help text and exits 0, so the reply cannot be parsed as JSON
    and every billing query silently returns zero rows.

The CLI uses its own credential profile for auth and returns raw JSON on
stdout.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-retryable errors (permission
denied, invalid parameter, ...) are raised immediately.

Public API:
    call(product, action, params=None, region=..., profile=None) -> dict
    paginate_next_token(product, action, params, ...) -> list[dict]
    resolve_account_id(...) -> str
    check_cli_available() -> None
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

from _constants import (BSS_ENDPOINT, CMS_ENDPOINT, MAX_PAGES, MAX_RESULTS,
                        STS_ENDPOINT)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Per-product endpoint metadata
# ---------------------------------------------------------------------------
# BSS and STS are central (region-less) services; the CLI is given the fixed
# endpoint so calls never depend on the caller's default region.
PRODUCT_ENDPOINTS: dict[str, str] = {
    "bssopenapi": BSS_ENDPOINT,   # business.aliyuncs.com
    "sts": STS_ENDPOINT,          # sts.aliyuncs.com
    "cms": CMS_ENDPOINT,          # metrics.aliyuncs.com (CloudMonitor)
}

_DEFAULT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# Only products served by a CLI plugin take the lowercase-hyphenated command
# and flag form (sts: `aliyun sts get-caller-identity`).
#
# bssopenapi is deliberately NOT listed here: it is served by the CLI's
# built-in API metadata, where the action name and the request parameters must
# match the OpenAPI specification exactly. Sending the hyphenated form makes
# the CLI print its help text and exit 0, which surfaces as a non-JSON reply
# and drops every bill row (observed in evaluation request 7997).
_PLUGIN_STYLE_PRODUCTS = {"sts"}


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API/parameter name to the plugin command form.

    A hyphen is inserted only before an uppercase letter that follows a
    lowercase letter or a digit, so acronym tails stay glued together:
        GetCallerIdentity    -> get-caller-identity
        DescribeInstanceBill -> describe-instance-bill
        InstanceID           -> instance-id   (not instance-i-d)
    """
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", name).lower()


# Inline boundary assertions kept next to the function (no test framework):
# normal command names, acronym boundary, and degenerate input.
assert _pascal_to_kebab("DescribeInstanceBill") == "describe-instance-bill"
assert _pascal_to_kebab("DescribeSplitItemBill") == "describe-split-item-bill"
assert _pascal_to_kebab("GetCallerIdentity") == "get-caller-identity"
assert _pascal_to_kebab("InstanceID") == "instance-id"
assert _pascal_to_kebab("BillingCycle") == "billing-cycle"
assert _pascal_to_kebab("BillingDate") == "billing-date"
assert _pascal_to_kebab("ProductCode") == "product-code"
assert _pascal_to_kebab("Granularity") == "granularity"
assert _pascal_to_kebab("MaxResults") == "max-results"
assert _pascal_to_kebab("NextToken") == "next-token"
assert _pascal_to_kebab("") == ""


def _command_tokens(product: str, action: str, plugin_style: bool = True) -> list[str]:
    """Return the CLI command tokens for (product, action).

    plugin_style=False forces the built-in API metadata form (PascalCase
    action verbatim) even for plugin-style products; used by the automatic
    fallback when the CLI plugin is not installed in the environment.
    """
    if product in _PLUGIN_STYLE_PRODUCTS and plugin_style:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str, plugin_style: bool = True) -> str:
    """Return the CLI flag for a parameter name, honoring product style."""
    if product in _PLUGIN_STYLE_PRODUCTS and plugin_style:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY API call of that run as a User-Agent, so all calls of one diagnosis
# can be correlated server-side.

_SKILL_NAME = "alibabacloud-db-cost-diagnosis"
_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: {_SESSION_ID}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{session_id()}"


def check_cli_available() -> None:
    """Ensure the aliyun CLI is available; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI to be installed and configured.\n\n"
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
    """True when the failure looks transient (throttling / 5xx / timeout).

    The marker haystack covers BOTH the extracted error code and the full
    error message, because the real aliyun CLI 3.x failure text is an
    SDKError envelope whose code may only be recoverable from the message.
    """
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


def _is_plugin_missing(err: "CliError") -> bool:
    """True when the CLI rejected a plugin-style command because the plugin
    is not installed (sandbox images do not pre-install CLI plugins; observed
    in evaluation request 8291: "Plugin 'aliyun-cli-sts' is required for
    command 'sts get-caller-identity' but not installed")."""
    haystack = f"{err} {err.stderr or ''}"
    return "Plugin" in haystack and "not installed" in haystack


def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = 60,
    _plugin_style: bool = True,
) -> dict[str, Any]:
    """Invoke an Alibaba Cloud OpenAPI action via the aliyun CLI.

    Args:
        product:  Product code, e.g. "bssopenapi", "cms", "sts".
        action:   API action name in PascalCase. Metadata-mode products
                  (bssopenapi / cms) pass it through VERBATIM
                  ("DescribeInstanceBill" stays "DescribeInstanceBill");
                  only plugin-style products (sts) get the
                  lowercase-hyphenated plugin command form
                  ("GetCallerIdentity" -> "get-caller-identity").
        params:   Dict of request parameters (PascalCase keys, emitted
                  verbatim as --PascalCase flags for metadata-mode
                  products; as lowercase-hyphenated flags for plugin-style
                  products); None values are skipped.
        region:   Region id passed defensively (BSS/STS are central services).
        profile:  Optional CLI credential profile name.
        timeout:  Per-attempt timeout in seconds (default 60).
        _plugin_style: Internal. When False, plugin-style products are
                  forced into the built-in API metadata form. Used by the
                  automatic fallback below; callers should not set it.

    Returns:
        Parsed JSON response as a dict.

    Raises:
        CliError: On failure. Transient errors (Throttling / 5xx / timeout)
                  are retried up to 3 attempts with linear backoff (2s, 4s).
                  For plugin-style products, a "plugin not installed"
                  failure transparently retries once through the built-in
                  API metadata form (same action/params, no plugin needed).
    """
    last_err: Optional[CliError] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, profile,
                             timeout, _plugin_style)
        except CliError as e:
            last_err = e
            if (_plugin_style
                    and product in _PLUGIN_STYLE_PRODUCTS
                    and _is_plugin_missing(e)):
                print(
                    f"[WARN] {product} CLI plugin not installed; falling "
                    f"back to the built-in API metadata mode for {action}",
                    file=sys.stderr,
                )
                return call(product, action, params, region, profile,
                            timeout, _plugin_style=False)
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
    params: Optional[dict[str, Any]],
    region: str,
    profile: Optional[str],
    timeout: int,
    plugin_style: bool = True,
) -> dict[str, Any]:
    """Execute one CLI invocation (argument-list form, never shell=True)."""
    cmd = ["aliyun"] + _command_tokens(product, action, plugin_style)

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
        cmd += [_param_flag(product, key, plugin_style), str(value)]

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
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")


# Shape guard for the legacy "ERROR: <Code>: <Message>" fallback: only
# letter-led alphanumeric tokens with optional dots count as API error codes.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")

# The aliyun CLI colors its stderr output; strip ANSI escapes so error text
# embedded in reports/JSON stays plain ASCII.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI color codes and collapse blank runs in CLI stderr text."""
    text = _ANSI_ESCAPE_RE.sub("", stderr)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Handles the real aliyun CLI 3.x failure envelope:

        Error: request execution failed: ... SDKError:
           StatusCode: 429
           Code: Throttling.User
           Message: Request was denied due to user flow control.
           Data: {"Code":"Throttling.User",...}

    and the CMS SDK.ServerError envelope, whose first line is a generic
    "ERROR: SDK.ServerError" followed by the real code on its own line:

        ERROR: SDK.ServerError
        ErrorCode: 400
        Message: ...

    The generic first line must NOT short-circuit extraction: a better
    code on a later line (ErrorCode:/Code:/Data:/JSON) always wins.
    """
    legacy_code = ""
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
        # when it matches the API-code shape (never grab prose). A generic
        # "ERROR: SDK.ServerError" first line must not stop the scan: the
        # real code may follow on an ErrorCode:/Code: line.
        if line.startswith("ERROR:"):
            parts = line.split(":", 2)
            candidate = parts[1].strip() if len(parts) > 2 else ""
            if _ERROR_CODE_TOKEN_RE.match(candidate):
                legacy_code = candidate
            continue
    return legacy_code


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
) -> str:
    """Return the Alibaba Cloud UID (AccountId) of the active credential.

    Uses STS GetCallerIdentity, which needs no input beyond the configured
    credential. Returns "" when it cannot be resolved.
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError:
        return ""


# ---------------------------------------------------------------------------
# Pagination helper (NextToken style, BSS Data.Items shape)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    """Walk a nested dict along `path`; return None on any miss."""
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
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    items_path: Optional[list[str]] = None,
    token_resp_path: Optional[list[str]] = None,
    token_req_key: str = "NextToken",
    max_results: int = MAX_RESULTS,
    max_results_key: str = "MaxResults",
    max_pages: int = MAX_PAGES,
) -> list[Any]:
    """Follow NextToken-based pagination until exhausted (with a guardrail).

    BSS bill APIs return items as a list directly under `Data.Items` and the
    continuation token under `Data.NextToken`; both paths are configurable.
    A legacy wrapped shape (`Data.Items.Item` list) is tolerated as fallback.

    Args:
        items_path:      Nested keys to the item list
                         (default: ["Data", "Items"]).
        token_resp_path: Nested keys to the response NextToken
                         (default: ["Data", "NextToken"]).
        max_results:     Page size injected as `MaxResults` (BSS max: 300).
        max_pages:       Hard guardrail on the number of pages fetched.

    Returns the concatenated item list across all pages.
    """
    items_path = items_path or ["Data", "Items"]
    token_resp_path = token_resp_path or ["Data", "NextToken"]

    all_items: list[Any] = []
    next_token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        if max_results_key:
            page_params[max_results_key] = max_results
        if next_token:
            page_params[token_req_key] = next_token
        body = call(product, action, page_params, region=region, profile=profile)

        items = _dig(body, items_path)
        if isinstance(items, dict):
            # Tolerate the wrapped legacy shape {"Items": {"Item": [...]}}.
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
