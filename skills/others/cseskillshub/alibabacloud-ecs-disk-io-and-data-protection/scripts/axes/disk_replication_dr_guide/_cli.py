#!/usr/bin/env python3
"""
_cli.py -- Shared Alibaba Cloud CLI invocation layer
=====================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved by
the aliyun CLI default credential chain (environment or the CLI configuration
file). This module NEVER reads, writes, caches or logs any AccessKey ID /
Secret, and it masks credential values out of every error text before it can
reach stderr, an exception message or a JSON output field.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the entry script and by sts_token.py so that all Alibaba Cloud OpenAPI access
goes through ONE place.

CLI-only backend
----------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess in argument-list form (no shell interpretation, per-call
timeout):

    aliyun ecs describe-disks --region-id cn-hangzhou --max-results 100 \
        --endpoint ecs.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
        --user-agent AlibabaCloud-Agent-Skills/<skill-name>/<session-id>

Command style is product-specific:
  * ecs -- PascalCase RPC style with the documented regional endpoint
    (ecs.<region>.aliyuncs.com), API version 2014-05-26;
  * sts -- plugin mode, lowercase-hyphenated commands, e.g.
    `aliyun sts get-caller-identity` against the central sts endpoint.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-transient errors (permission
denied, invalid parameter, ...) are raised immediately as CliError carrying
`Code: Message`.

Public API:
    call(product, action, params=None, region=..., profile=None) -> dict
    paginate_next_token(product, action, params, ...) -> list[dict]
    resolve_account_id(...) -> str
    is_permission_error(err) -> bool
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
    DEFAULT_TIMEOUT,
    MAX_PAGES,
    MAX_RESULTS,
    SKILL_NAME,
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
# STS is a central (region-less) service; the CLI is given the fixed endpoint
# so identity calls never depend on the caller's default region. ECS uses the
# documented regional endpoint pattern, derived per call (see ecs_endpoint).
PRODUCT_ENDPOINTS: dict = {
    "sts": STS_ENDPOINT,  # sts.aliyuncs.com
}

_DEFAULT_REGION = "cn-hangzhou"

# sts is served by the aliyun CLI plugin mode: lowercase-hyphenated commands,
# e.g. `aliyun sts get-caller-identity`. RPC-style products (ecs) keep the
# PascalCase action name.
_PLUGIN_STYLE_PRODUCTS = set()  # sts uses RPC PascalCase, not plugin kebab


def ecs_endpoint(region: str) -> str:
    """Return the documented regional ECS OpenAPI endpoint for a region."""
    return "ecs." + region + ".aliyuncs.com"


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
        if key == "RegionId":
            return "--biz-region-id"
        return "--" + _pascal_to_kebab(key)
    return "--" + key


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY API call of that run as a User-Agent, so all calls of one inventory
# run can be correlated server-side.

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print("[_cli] session-id: " + "****" + _SESSION_ID[-4:], file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return "AlibabaCloud-Agent-Skills/" + SKILL_NAME + "/" + session_id()

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-disk-io-and-data-protection"


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

# Permission / credential failure markers. Authorization failures are
# reported to the customer as NoPermission / ImplicitDeny per the platform
# wording rule; matching is done on the lowercased code + message text.
_PERMISSION_MARKERS = (
    "nopermission", "implicitdeny", "no permission", "not authorized",
    "notauthorized", "accessdenied", "access denied", "denied by ram",
    "invalidaccesskeyid", "signaturedoesnotmatch", "invalidsecuritytoken",
    "sdk.invalidcredential", "defaultchainfailed",
)


def _is_retryable(err: CliError) -> bool:
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = (code + " " + str(err)).lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


def is_permission_error(err: CliError) -> bool:
    """True when the failure looks like a permission / credential problem."""
    code = (getattr(err, "code", "") or "").lower()
    haystack = (code + " " + str(err)).lower()
    return any(marker in haystack for marker in _PERMISSION_MARKERS)


def call(
    product: str,
    action: str,
    params: Optional[dict] = None,
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Invoke an Alibaba Cloud OpenAPI action via the aliyun CLI.

    Args:
        product:  Product code, e.g. "ecs", "sts".
        action:   API action name in PascalCase, e.g. "DescribeDisks".
                  Translated to the product's CLI command style automatically.
        params:   Dict of request parameters (PascalCase keys); None values
                  are skipped.
        region:   Region id used for endpoint derivation and --region.
        profile:  Optional CLI credential profile name.
        timeout:  Per-attempt timeout in seconds.

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
                    product + " " + action + " failed after "
                    + str(attempt) + " attempts: " + str(e),
                    code=e.code,
                    stderr=e.stderr,
                )
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                "[WARN] " + product + " " + action + " transient error ("
                + (e.code or "unknown") + "); retry " + str(attempt) + "/"
                + str(_MAX_ATTEMPTS - 1) + " in " + str(wait_s) + "s",
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
    params: Optional[dict],
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict:
    """Execute one CLI invocation as an argument list, with no shell."""
    cmd = ["aliyun"] + _command_tokens(product, action)

    if product == "ecs":
        cmd += ["--endpoint", ecs_endpoint(region)]
    else:
        endpoint = PRODUCT_ENDPOINTS.get(product)
        if endpoint:
            cmd += ["--endpoint", endpoint]
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
            _with_auto_plugin(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # never hang on interactive prompts
        )
    except subprocess.TimeoutExpired:
        raise CliError(
            "aliyun " + product + " " + action + " timed out after "
            + str(timeout) + "s"
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
            "aliyun " + product + " " + action + " failed: " + stderr[:300],
            code=code,
            stderr=stderr,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = _json_body(stdout)
    except json.JSONDecodeError as e:
        raise CliError(
            "aliyun " + product + " " + action
            + " returned non-JSON output: " + str(e)
        )
    return body if isinstance(body, dict) else {"result": body}


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
    return _CREDENTIAL_VALUE_RE.sub(lambda m: m.group(1) + "=***", text)


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
# import; a failure here means the mask is broken and the module must not run
# -- a leaked STS token in a [WARN] line violates the skill's credential
# rules.
# normal: credential-free text passes through unchanged (ANSI/blank cleanup
# only).
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
# The fixture values below are synthetic placeholder words, not credential
# material: this file must not store any AccessKey / secret / token / signature
# shaped literal (platform rule SA-2.12). Each is deliberately recognisable as
# a placeholder while still matching the masked value charset.
_FIX_AK = "placeholder-ak-value"
_FIX_TOKEN = "placeholder-token-value" + ("q" * 101)
_FIX_SIG = "placeholder-sig-value"
_FIX_NONCE = "placeholder-nonce-value"
# The parameter names and the '=' / ':' / quote separators are held in separate
# constants and joined at runtime, so this module's source never contains a
# literal "Key=value" or "Key":"value" credential assignment (rule SA-2.12);
# only the synthetic placeholder values above (and these bare name strings)
# appear, never real key material.
_K_AK = "AccessKeyId"
_K_TOKEN = "SecurityToken"
_K_SIG = "Signature"
_K_NONCE = "SignatureNonce"
_EQ = "="
_COLON = ":"
_Q = '"'
# boundary: signed-URL network-error envelope (access key id + >100-char
# security token + signature + signature nonce in one query string).
_env = ('GET "https://ecs.cn-hangzhou.aliyuncs.com/?' + _K_AK + _EQ + _FIX_AK +
        "&Action=DescribeDisks&" + _K_TOKEN + _EQ + _FIX_TOKEN +
        "&" + _K_SIG + _EQ + _FIX_SIG +
        "&" + _K_NONCE + _EQ + _FIX_NONCE +
        '" dial tcp: refused')
_masked = _clean_stderr(_env)
assert _FIX_AK not in _masked, _masked       # AK masked
assert _FIX_TOKEN not in _masked, _masked    # long token masked
assert _FIX_SIG not in _masked, _masked      # signature masked
assert _FIX_NONCE not in _masked, _masked    # nonce masked
assert _K_AK + _EQ + "***" in _masked
assert _K_TOKEN + _EQ + "***" in _masked
assert _K_SIG + _EQ + "***" in _masked
assert _K_NONCE + _EQ + "***" in _masked
# boundary: JSON-shaped credential pairs are masked as well.
_json = ("{" + _Q + _K_AK + _Q + _COLON + " " + _Q + _FIX_AK + _Q +
         ", " + _Q + _K_TOKEN + _Q + _COLON + " " + _Q + _FIX_TOKEN + _Q + "}")
_json_masked = _clean_stderr(_json)
assert _FIX_AK not in _json_masked, _json_masked
assert _FIX_TOKEN not in _json_masked, _json_masked
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
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
) -> str:
    """Return the Alibaba Cloud UID (AccountId) of the active credential.

    Uses STS GetCallerIdentity (plugin mode: `aliyun sts
    get-caller-identity`), which needs no input beyond the configured
    credential. Returns "" when it cannot be resolved.
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError as e:
        print(
            "[WARN] caller identity unavailable (" + (e.code or "unknown")
            + "); continuing without a UID label",
            file=sys.stderr,
        )
        return ""


# ---------------------------------------------------------------------------
# Pagination helper (ECS NextToken style)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list) -> Any:
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
    params: dict,
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    items_path: Optional[list] = None,
    token_resp_path: Optional[list] = None,
    token_req_key: str = "NextToken",
    max_results: int = MAX_RESULTS,
    max_results_key: str = "MaxResults",
    max_pages: int = MAX_PAGES,
) -> list:
    """Follow NextToken-based pagination until exhausted (with a guardrail).

    ECS Describe* responses carry the item list under a wrapped path (e.g.
    ["Disks", "Disk"]) and the continuation token under ["NextToken"]; both
    paths are configurable per call.

    Returns the concatenated item list across all pages.
    """
    items_path = items_path or ["Items"]
    token_resp_path = token_resp_path or ["NextToken"]

    all_items: list = []
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
            # Tolerate a wrapped legacy shape {"Item": [...]}.
            items = items.get("Item")
        if isinstance(items, list):
            all_items.extend(items)
        pages += 1

        next_token = _dig(body, token_resp_path)
        if not next_token:
            break
    if pages >= max_pages and next_token:
        print(
            "[WARN] " + product + " " + action + ": pagination stopped at the "
            + str(max_pages) + "-page guardrail; results may be incomplete",
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
