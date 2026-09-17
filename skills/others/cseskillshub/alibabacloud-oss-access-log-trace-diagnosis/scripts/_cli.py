#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation helper for OSS Access-Log Trace Diagnosis
==============================================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved by
the aliyun CLI default credential chain (~/.aliyun/config.json or
platform-injected environment variables). This module NEVER reads, writes,
caches or logs any AccessKey ID / Secret. No AK/SK handling anywhere here.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the diagnosis scripts so that every Alibaba Cloud call goes through ONE place.

CLI-only backend
----------------
Every call is routed through `call()`, which invokes the `aliyun` CLI as a
subprocess in argument-list form (never shell=True):

    aliyun <product> <lowercase-hyphenated-action> --lowercase-hyphenated-flag value ...

This module serves ONLY POP-gateway products. Two consequences matter for the
evaluation contract: a CLI call can be intercepted by CLI Mock (so error paths
are testable), and it can be attributed to a popCode/popVersion (so it may be
declared in related_apis.yaml).

Command style: plugin mode only (lowercase-hyphenated)
------------------------------------------------------
Product plugins accept kebab-case commands and flags only; PascalCase is
rejected. Call sites still pass the OpenAPI action name in PascalCase
(`GetLogs`, `GetRole`) so they stay readable and stay 1:1 with
related_apis.yaml -- this module converts the action and every parameter flag
to kebab-case before spawning the CLI, so no PascalCase command can reach it.

    GetLogs              -> get-logs
    ListPoliciesForUser -> list-policies-for-user
    RoleName            -> --role-name

Products served here:

  * sls  -- realtime access-log reads
                aliyun sls get-logs --project p --logstore ls --from 1 --to 2
  * ram  -- identity-policy and role-trust reads
                aliyun ram get-role --role-name my-role

Plugin availability is NOT measured on the build host (no CLI installed here),
so treat these command names as derived from the documented naming rule rather
than verified. Two facts bound that risk: a plugin is resolved from the product
code and auto-installed when missing, and the naming rule is mechanical. To
confirm on a host that has the CLI:

    aliyun plugin list-remote
    aliyun plugin search "sls get"
    aliyun plugin search "ram get"

Should a product turn out to have no plugin, callers MUST degrade to
query-statement generation rather than fail -- see is_sls_channel_available().

OSS control-plane reads and the STS caller-identity check do NOT live here.
Measured conclusion for this skill family: the aliyun CLI carries no OSS
control-plane metadata and ossutil is not assumed to be installed, so OSS
metadata goes through the oss2 SDK in _oss_client.py, which also owns the
`aliyun sts get-caller-identity` subprocess call. Note: STS is a built-in
CLI product (not a plugin), so its CLI invocations may not be interceptable
by the CLI Mock system; the SDK-based OSS reads likewise cannot be mocked.
Both categories therefore stay out of related_apis.yaml and are covered by
evals cloud_interaction.skill_script assertions instead.

Exact command shapes assembled by this module
---------------------------------------------
Listed verbatim because they are the contract for CLI Mock fixtures and for
anyone reading a transcript. Everything after the action is a parameter flag.

    aliyun sls get-logs --project <p> --logstore oss-log-store --from <sec> --to <sec> --query <q> --line <n>
    aliyun ram list-policies-for-user --user-name <u>
    aliyun ram get-policy --policy-name <n> --policy-type <t>
    aliyun ram get-role --role-name <r>

Each invocation additionally carries --region, an optional --profile, and
always --user-agent.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-retryable errors (permission
denied, invalid parameter, resource not found) are raised immediately.

Expected-error tolerance
------------------------
Some non-2xx outcomes are valid findings rather than failures -- a bucket with
no policy returns NoSuchBucketPolicy. Callers pass `tolerate_codes=` so such
outcomes are returned as a structured result instead of raising.

Public API:
    call(product, action, params=None, region=..., profile=None, tolerate_codes=())
    call_sls_get_logs(project, logstore, region, query, from_ts, to_ts, ...) -> dict
    is_channel_missing(err) -> bool
    resolve_account_id(...) -> str        (delegates to _oss_client)
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

from _constants import (
    API_VERSIONS,
    DEFAULT_TIMEOUT,
    LOG_QUERY_TIMEOUT,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails."""

    def __init__(self, message: str, code: str = "", stderr: str = "",
                 stdout: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr
        self.stdout = stdout


# ---------------------------------------------------------------------------
# Command-style registry (POP-gateway products only)
# ---------------------------------------------------------------------------

_STYLE_PLUGIN_KEBAB = "plugin-kebab"  # aliyun <p> <kebab-action> --kebab-flag

# Plugin mode is the only style the CLI accepts for product plugins, so every
# product maps to it. The registry is kept explicit so that onboarding a product
# stays a deliberate act, and _command_tokens() refuses any other style rather
# than silently emitting a PascalCase command.
PRODUCT_STYLES: dict[str, str] = {
    "sls": _STYLE_PLUGIN_KEBAB,
    "ram": _STYLE_PLUGIN_KEBAB,
}

# Neither SLS nor RAM needs a forced endpoint: both are addressed by region
# through the CLI's own metadata. Kept as an empty map so the call path stays
# uniform if a region-less product is added later.
PRODUCT_ENDPOINTS: dict[str, str] = {}

_DEFAULT_REGION = "cn-hangzhou"


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to kebab-case.

    GetBucketPolicy -> get-bucket-policy
    GetCallerIdentity -> get-caller-identity
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list[str]:
    """Return the plugin-mode command tokens for (product, action).

    `action` arrives as the PascalCase OpenAPI name and is converted here, so a
    PascalCase command can never reach the CLI.
    """
    style = PRODUCT_STYLES.get(product, _STYLE_PLUGIN_KEBAB)
    if style != _STYLE_PLUGIN_KEBAB:
        raise ValueError(
            f"unsupported CLI command style '{style}' for product '{product}': "
            "plugin mode (lowercase-hyphenated) is the only accepted style")
    return [product, _pascal_to_kebab(action)]


def _param_flag(product: str, key: str) -> str:
    """Return the plugin-mode flag for a parameter name.

    Plugin mode rejects PascalCase flags, so every key is converted. Keys that
    are already lowercase (the log query parameters) pass through unchanged.
    `product` is accepted for call-site symmetry and future per-product
    overrides; no override is needed today.
    """
    return f"--{_pascal_to_kebab(key)}"


# ---------------------------------------------------------------------------
# Session-ID and User-Agent (observability)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY call of that run as a User-Agent, so all calls belonging to one
# diagnosis can be correlated server-side.

_SKILL_NAME = "alibabacloud-oss-access-log-trace-diagnosis"


def session_id() -> str:
    """Return the per-run 32-char hex session-id.

    Delegated to _oss_client so that ONE run produces exactly ONE session-id
    across both channels (the oss2 SDK data plane and the aliyun CLI). Two
    independent globals would emit two different ids for the same diagnosis
    and break server-side correlation.
    """
    import _oss_client  # local import: avoids a load-order cycle
    return _oss_client.session_id()


def user_agent() -> str:
    """User-Agent attached to every call of this run.

    Delegated to _oss_client so the CLI channel and the SDK data plane emit an
    IDENTICAL versioned User-Agent from one source (rule UA-SKILL-VERSION); two
    independent implementations would drift apart.
    """
    import _oss_client  # local import: avoids a load-order cycle
    return _oss_client.user_agent()


def check_cli_available() -> None:
    """Ensure the aliyun CLI is reachable; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI, installed and "
            "configured.\n\n"
            "  Install:   https://help.aliyun.com/document_detail/121541.html\n"
            "  Configure: aliyun configure\n"
            "  Plugins:   aliyun plugin install --names aliyun-cli-sts\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Transient-error retry
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 2  # wait before retry N is N * 2s (2s, then 4s)

_RETRY_CODES = {
    "throttling", "throttling.user", "throttling.api",
    "serviceunavailable", "internalerror", "sdk.httperror", "unknownerror",
}

# Marker substrings searched in the lowercased error code AND message. Bare
# "500"/"503" are deliberately avoided because request-ID hex strings could
# false-positive; 5xx is matched through precise forms instead.
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
    params: Optional[dict[str, Any]] = None,
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    tolerate_codes: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Invoke an Alibaba Cloud API action through the aliyun CLI.

    Args:
        product:  Product code: "sts", "sls", "oss", "ram".
        action:   API action in PascalCase, e.g. "GetBucketPolicy". Translated
                  to the product's CLI command style automatically.
        params:   Request parameters. None values are skipped. Key casing must
                  are converted to plugin-mode flags (see _param_flag).
        region:   Region id, passed for regional products.
        profile:  Optional CLI credential profile name.
        timeout:  Per-attempt timeout in seconds.
        tolerate_codes: Error codes that are valid findings rather than
                  failures; such an outcome is returned as
                  {"_tolerated": True, "code": ..., "message": ...}.

    Returns:
        Parsed JSON response as a dict (empty dict when stdout is not JSON,
        with the raw text preserved under "_raw").

    Raises:
        CliError: On failure, after retrying transient errors up to 3 attempts.
    """
    last_err: Optional[CliError] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, profile,
                             timeout, tolerate_codes)
        except CliError as e:
            last_err = e
            if not _is_retryable(e):
                raise
            if attempt >= _MAX_ATTEMPTS:
                raise CliError(
                    f"{product} {action} failed after {attempt} attempts: {e}",
                    code=e.code, stderr=e.stderr, stdout=e.stdout,
                )
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({e.code or 'unknown'}); retry {attempt}/{_MAX_ATTEMPTS - 1} "
                f"in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps type checkers quiet


def _call_cli(
    product: str,
    action: str,
    params: Optional[dict[str, Any]],
    region: str,
    profile: Optional[str],
    timeout: int,
    tolerate_codes: tuple[str, ...],
) -> dict[str, Any]:
    """Execute one CLI invocation (argument-list form, never shell=True)."""
    cmd = ["aliyun"] + _command_tokens(product, action)

    endpoint = PRODUCT_ENDPOINTS.get(product)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    if region:
        cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]

    # Observability: one session-id User-Agent shared by every call of this run.
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
            stdin=subprocess.DEVNULL,  # never hang on an interactive prompt
        )
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun {product} {action} timed out after {timeout}s")

    stdout = (result.stdout or "").strip()

    if result.returncode != 0:
        stderr = _clean_stderr(result.stderr or "")
        code = _extract_error_code(stderr) or _extract_error_code(stdout)
        # An expected non-success outcome is a finding, not a failure.
        if code and code in tolerate_codes:
            return {
                "_tolerated": True,
                "code": code,
                "message": _extract_error_message(stderr),
                "_raw": stdout,
            }
        raise CliError(
            f"aliyun {product} {action} failed: {(stderr or stdout)[:300]}",
            code=code, stderr=stderr, stdout=stdout,
        )

    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # Several OSS configuration reads return XML rather than JSON. Preserve
        # the payload verbatim and let the caller parse it.
        return {"_raw": stdout}


# Shape guard for the legacy "ERROR: <Code>: <Message>" fallback: only
# letter-led alphanumeric tokens with optional dots count as API error codes.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")

# The CLI colors stderr; strip ANSI escapes so error text embedded in a report
# stays plain.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI color codes and collapse blank runs in CLI stderr text."""
    text = _ANSI_ESCAPE_RE.sub("", stderr)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_error_code(text: str) -> str:
    """Best-effort extraction of an API error code from CLI output.

    Handles the aliyun CLI 3.x failure envelope:

        Error: request execution failed: ... SDKError:
           StatusCode: 403
           Code: AccessDenied
           Message: ...
           Data: {"Code":"AccessDenied",...}

    and the OSS XML error body, which carries <Code>...</Code>.
    """
    for line in text.splitlines():
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
    # OSS XML error body.
    m = re.search(r"<Code>\s*([A-Za-z0-9.]+)\s*</Code>", text)
    if m:
        return m.group(1)
    return ""


def _extract_error_message(text: str) -> str:
    """Best-effort extraction of an API error message from CLI output."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Message:"):
            return line.split(":", 1)[1].strip()
    m = re.search(r"<Message>\s*(.*?)\s*</Message>", text, re.DOTALL)
    if m:
        return m.group(1)
    return ""


# ---------------------------------------------------------------------------
# Identity helper (delegated)
# ---------------------------------------------------------------------------

def resolve_account_id(
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
) -> str:
    """Return the account UID behind the active credential, or "".

    The STS caller-identity check is owned by _oss_client (it shares the
    credential-chain concerns of the oss2 data plane), so this is a thin
    delegation kept for call-site compatibility. `region` and `profile` are
    accepted but not used: STS is a region-less central service and the CLI
    resolves its own profile.
    """
    import _oss_client  # local import: avoids a load-order cycle
    return _oss_client.resolve_uid()


# ---------------------------------------------------------------------------
# Channel availability
# ---------------------------------------------------------------------------

# Error text indicating the CLI itself does not serve the requested product or
# sub-command, as opposed to a cloud-side rejection. When this matches, callers
# MUST degrade to generating query statements for the user instead of treating
# it as a permission or data problem.
_CHANNEL_MISSING_MARKERS = (
    "unknown command", "unknown product", "invalid product",
    "command not found", "no such command", "not a valid command",
    "unknown flag", "unknown shorthand", "invalid action",
    "api not found", "product not found", "plugin not found",
    "climissing",
)


def is_channel_missing(err) -> bool:
    """True when the failure means the CLI cannot serve this product at all.

    This is the guard behind the dual-mode design: when the sls channel is
    unavailable, the skill falls back to deriving the log target and generating
    query statements for the customer to run in the console, and says so
    plainly, instead of reporting a fabricated "no data" finding.
    """
    text = f"{getattr(err, 'code', '') or ''} {err}".lower()
    return any(marker in text for marker in _CHANNEL_MISSING_MARKERS)


assert is_channel_missing(CliError("unknown command 'sls'")) is True   # normal
assert is_channel_missing(CliError("Code: NoPermission")) is False
assert is_channel_missing(CliError("")) is False                       # invalid


# ---------------------------------------------------------------------------
# Product-specific convenience wrappers
# ---------------------------------------------------------------------------


def call_sls_get_logs(
    project: str,
    logstore: str,
    region: str,
    query: str,
    from_ts: int,
    to_ts: int,
    line: int = 20,
    offset: int = 0,
    reverse: bool = True,
    profile: Optional[str] = None,
    timeout: int = LOG_QUERY_TIMEOUT,
) -> dict[str, Any]:
    """Query a logstore through SLS GetLogs.

    `from_ts` / `to_ts` are Unix seconds (not milliseconds). `query` accepts
    the SLS search syntax, optionally followed by '|' and an SQL statement.
    """
    params = {
        "project": project,
        "logstore": logstore,
        "from": from_ts,
        "to": to_ts,
        "query": query,
        "line": line,
        "offset": offset,
        "reverse": reverse,
    }
    return call("sls", "GetLogs", params, region=region, profile=profile,
                timeout=timeout)


def api_version(product: str) -> str:
    """Return the declared API version for a product (used in reports)."""
    return API_VERSIONS.get(product, "")
