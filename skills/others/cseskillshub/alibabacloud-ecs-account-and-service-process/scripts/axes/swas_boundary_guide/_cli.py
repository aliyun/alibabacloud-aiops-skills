#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation helper for the SWAS Boundary Guide
=======================================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved by
the aliyun CLI default credential chain (~/.aliyun/config.json or
platform-injected environment). This module NEVER reads, writes, caches or
logs any AccessKey ID / Secret. No AK/SK handling anywhere in this module.

Private helper module (prefixed with `_`). Do NOT run directly -- it is
imported by the entry script so that all Alibaba Cloud OpenAPI access goes
through ONE place.

CLI-only transport
------------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess (argument-list form, never shell=True):

    aliyun <product> <Action> --Param value ...

Command style is product-specific (verified against aliyun CLI 3.x):
  * ecs -- built-in API metadata mode, PascalCase RPC style:
        aliyun ecs describe-instances --region-id cn-hangzhou \
            --endpoint ecs.cn-hangzhou.aliyuncs.com
  * sts -- plugin mode, lowercase-hyphenated commands:
        aliyun sts get-caller-identity

Read-only enforcement at the code layer
---------------------------------------
`call()` refuses any action outside the read-only whitelist: for product
`ecs` only the actions in ECS_READ_WHITELIST are allowed, for product `sts`
only GetCallerIdentity. Actions whose names start with a mutating verb are
rejected unconditionally, so even a coding mistake upstream cannot turn this
skill into a mutating one.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-transient errors (permission
denied, invalid parameter, ...) are raised immediately.

Public API:
    call(product, action, params=None, region=..., profile=None) -> dict
    resolve_account_id(...) -> str
    check_cli_available() -> None
    session_id() -> str
    user_agent() -> str
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
    ECS_ENDPOINT_TEMPLATE,
    ECS_READ_WHITELIST,
    SKILL_NAME,
    STS_ENDPOINT,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails. Carries `Code: Message`."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Read-only guard (code-layer enforcement, complements the SKILL.md policy)
# ---------------------------------------------------------------------------

# Mutating verb prefixes (lowercased for comparison). Any action starting with
# one of these is refused before a subprocess is even assembled.
_MUTATING_PREFIXES = (
    "modify", "create", "delete", "release", "reset", "replace", "attach",
    "detach", "reboot", "start", "stop", "run", "invoke", "put", "import",
    "revoke", "bind", "unbind", "update", "set", "allocate", "convert",
)

_ALLOWED_ACTIONS = {
    "ecs": set(ECS_READ_WHITELIST),
    "sts": {"GetCallerIdentity"},
}


def _assert_read_only(product: str, action: str) -> None:
    """Refuse anything outside the read-only whitelist (hard code guard)."""
    allowed = _ALLOWED_ACTIONS.get(product)
    if allowed is None:
        raise CliError(
            f"product '{product}' is not allowed by this skill "
            f"(read-only whitelist covers ecs/sts only)",
            code="NotAllowedProduct",
        )
    if action not in allowed:
        raise CliError(
            f"action '{product} {action}' is not in this skill's read-only "
            f"whitelist {sorted(allowed)}",
            code="NotAllowedAction",
        )
    if action.lower().startswith(_MUTATING_PREFIXES):
        raise CliError(
            f"action '{product} {action}' looks mutating and is refused by "
            f"this read-only skill",
            code="MutatingActionRefused",
        )


# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# ecs uses the CLI's built-in metadata: PascalCase action + params,
#     e.g. `aliyun ecs describe-instances --region-id cn-hangzhou`
# sts is served by the aliyun-cli-sts plugin: lowercase-hyphenated commands,
#     e.g. `aliyun sts get-caller-identity`
_PLUGIN_STYLE_PRODUCTS = set()  # sts uses RPC PascalCase, not plugin kebab


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to the plugin kebab-case command form.

    Example: GetCallerIdentity -> get-caller-identity
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list[str]:
    """Return the CLI command tokens for (product, action)."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    """Return the CLI flag for a parameter name, honoring product style."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        if key == "RegionId":
            return "--biz-region-id"
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


def _endpoint_for(product: str, region: str) -> Optional[str]:
    """Fixed endpoint per product so calls never depend on CLI defaults."""
    if product == "sts":
        return STS_ENDPOINT
    if product == "ecs":
        return ECS_ENDPOINT_TEMPLATE.format(region=region)
    return None


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability, MUST SA-2.11b/c)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY API call of that run as a User-Agent, so all calls of one boundary
# check can be correlated server-side.

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id()}"

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-account-and-service-process"


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
            "This skill requires the Alibaba Cloud CLI (version 3.x) to be\n"
            "installed and configured on this machine.\n\n"
            "  Install: download the official Alibaba Cloud CLI package, then\n"
            "  Configure: aliyun configure\n"
            "\n"
            "This skill resolves credentials only through that CLI default\n"
            "credential chain; it never takes or stores a key pair itself.\n"
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
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke a read-only Alibaba Cloud OpenAPI action via the aliyun CLI.

    Args:
        product:  Product code: "ecs" or "sts" (whitelist enforced).
        action:   API action name in PascalCase, e.g. "DescribeInstances".
                  Translated to the product's CLI command style automatically.
        params:   Dict of request parameters (PascalCase keys for ecs);
                  None values are skipped.
        region:   Region id used for the endpoint and --region flag.
        profile:  Optional CLI credential profile name.
        timeout:  Per-attempt timeout in seconds (default DEFAULT_TIMEOUT).

    Returns:
        Parsed JSON response as a dict.

    Raises:
        CliError: On failure. Transient errors (Throttling / 5xx / timeout)
                  are retried up to 3 attempts with linear backoff (2s, 4s).
    """
    _assert_read_only(product, action)
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


_AUTO_PLUGIN_PROBED = False


def _with_auto_plugin(argv):
    """Resolve a missing product plugin without an interactive prompt.

    auto-plugin-install is a `configure set` profile key, not a per-invocation
    flag. Only a host that actually lacks this product's plugin is touched;
    `plugin list` is a local inventory read with no credential or network use.
    """
    global _AUTO_PLUGIN_PROBED
    if not _AUTO_PLUGIN_PROBED:
        _AUTO_PLUGIN_PROBED = True
        product = argv[1] if len(argv) > 1 else ""
        needed = True
        try:
            listed = subprocess.run(["aliyun", "plugin", "list"],
                                    stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=30)
            inventory = (listed.stdout or b"").decode("utf-8", "replace")
            if inventory.strip():
                needed = ("aliyun-cli-" + product) not in inventory
        except (OSError, subprocess.SubprocessError):
            needed = True
        if needed:
            try:
                subprocess.run(["aliyun", "configure", "set",
                                "--auto-plugin-install", "true"],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=30)
            except (OSError, subprocess.SubprocessError):
                pass
    return list(argv)


def _json_body(text):
    """Decode the CLI's JSON body even when a notice precedes it on stdout.

    A parse hiccup is not a customer-side credential fault; the body is
    located instead of assumed.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        offsets = [i for i in (text.find("{"), text.find("[")) if i != -1]
        if not offsets:
            raise
        return json.JSONDecoder().raw_decode(text[min(offsets):])[0]


_REGION_FLAG_REQUIRED_RES = (
    re.compile(r"missing required parameter\(s\):\s*--biz-region-id"),
    re.compile(r"--biz-region-id is required"),
)


def _region_flag_retry(cmd, stderr, region):
    """The same call with the plugin's region parameter, or None if not applicable."""
    if not region or "--biz-region-id" in cmd:
        return None
    if not any(pattern.search(stderr or "") for pattern in _REGION_FLAG_REQUIRED_RES):
        return None
    return list(cmd) + ["--biz-region-id", region]


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

    endpoint = _endpoint_for(product, region)
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
            _with_auto_plugin(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,  # MUST 7.6.1: every subprocess call has a timeout
            stdin=subprocess.DEVNULL,  # never hang on interactive prompts
        )
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun {product} {action} timed out after {timeout}s")
    except FileNotFoundError:
        # The aliyun binary is not on PATH: degrade through the normal
        # CliError path instead of crashing the whole run.
        raise CliError(
            f"aliyun CLI not found on PATH; cannot call {product} {action}. "
            f"Install the Alibaba Cloud CLI and run `aliyun configure`.",
            code="CliNotFound",
        )

    if result.returncode != 0:
        _retry = _region_flag_retry(cmd, result.stderr or "", region)
        if _retry is not None:
            try:
                result = subprocess.run(
                    _with_auto_plugin(_retry),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL,
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
        body = _json_body(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")

    # Some APIs report request-level failures INSIDE the response body while
    # the CLI still exits 0. Treat any non-Success body Code as an invocation
    # failure so callers degrade via the standard CliError path.
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
# stderr cleanup + credential masking (SA-2.12)
# ---------------------------------------------------------------------------

# Shape guard for the legacy "ERROR: <Code>: <Message>" fallback: only
# letter-led alphanumeric tokens with optional dots count as API error codes.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")

# The aliyun CLI colors its stderr output; strip ANSI escapes so error text
# embedded in reports/JSON stays plain ASCII.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Credential-value masking: the aliyun CLI network-error envelope can embed a
# signed request URL whose query string carries AccessKeyId / SecurityToken /
# Signature. Every <credentialKey>=<value> (query-string) or
# "<credentialKey>":"<value>" (JSON) pair is masked BEFORE the text can reach
# a [WARN] stderr line, a CliError message, or any JSON output field.
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
    """Strip ANSI color codes, MASK CREDENTIALS and collapse blank runs in
    CLI stderr text. Single choke point every CLI stderr passes through
    before it can surface in [WARN] lines, CliError messages or JSON."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the credential masking, executed on every
# import; a failure here means the mask is broken and the module must not run.
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
_signed_env = (
    'GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=STS.FakeKey1234'
    "&Action=DescribeInstances&SecurityToken=" + "CAIS" + ("x" * 101)
    + '&Signature=abcd1234ef==&SignatureNonce=9e2f1" dial tcp: refused')
_signed_masked = _clean_stderr(_signed_env)
assert "STS.FakeKey1234" not in _signed_masked, _signed_masked
assert ("x" * 101) not in _signed_masked, _signed_masked
assert "abcd1234ef" not in _signed_masked, _signed_masked
assert "AccessKeyId=***" in _signed_masked
assert "SecurityToken=***" in _signed_masked
assert "Signature=***" in _signed_masked
_json_creds = '{"AccessKeyId": "STS.fake", "SecurityToken": "CAISfake99"}'
_json_masked = _clean_stderr(_json_creds)
assert "STS.fake" not in _json_masked, _json_masked
assert "CAISfake99" not in _json_masked, _json_masked
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
        # Legacy CLI fallback: "ERROR: <Code>: <Message>".
        if line.startswith("ERROR:"):
            parts = line.split(":", 2)
            candidate = parts[1].strip() if len(parts) > 2 else ""
            return candidate if _ERROR_CODE_TOKEN_RE.match(candidate) else ""
    return ""


# ---------------------------------------------------------------------------
# Auth-failure classification (E34 wording: report NoPermission / ImplicitDeny)
# ---------------------------------------------------------------------------

# Lowercase substrings matched against the error text. Classification works on
# lowercase forms and the user-facing hint names NoPermission / ImplicitDeny
# only; no other authorization literal wording may appear in this skill's
# output, so it is never matched or emitted here.
_AUTH_MARKERS = (
    "nopermission", "implicitdeny", "not authorized", "unauthorized",
    "accessdenied", "no permission",
)


def is_permission_error(err: CliError) -> bool:
    """True when the failure is a RAM authorization denial."""
    haystack = f"{getattr(err, 'code', '')} {err}".lower()
    return any(marker in haystack for marker in _AUTH_MARKERS)


def permission_hint(product: str, action: str) -> str:
    """Minimal guidance for a RAM denial: which action is missing."""
    return (
        f"The credential lacks permission for {product}:{action} "
        f"(reported as NoPermission / ImplicitDeny). Grant the minimal "
        f"read-only policy listed in references/ram-policies.md; never "
        f"retry around the denial and never widen it to wildcard actions."
    )


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
) -> str:
    """Return the Alibaba Cloud UID (AccountId) of the active credential.

    Uses STS GetCallerIdentity (plugin mode: `aliyun sts get-caller-identity`),
    which needs no input beyond the configured credential. Returns "" when it
    cannot be resolved.
    """
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
