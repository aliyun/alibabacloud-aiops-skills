#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation helper for ECS Instance-Modify Diagnosis
=============================================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved by the
aliyun CLI default credential chain (~/.aliyun/config.json or platform-injected
environment). This module NEVER reads, writes, caches or logs any AccessKey ID /
Secret. No AK/SK handling anywhere in this module.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by the
entry script so that all Alibaba Cloud OpenAPI access goes through ONE place.

CLI-only backend
----------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as a
subprocess (argument-list form, never shell=True):

    aliyun <product> <action> --param value ...

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
    aliyun ecs describe-instances --biz-region-id cn-hangzhou --instance-ids '["i-..."]'
    aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-retryable errors (permission
denied, invalid parameter, ...) are raised immediately.

Public API:
    call(product, action, params=None, region=..., profile=None) -> dict
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

from _constants import DEFAULT_REGION, SKILL_NAME, STS_ENDPOINT


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Per-product endpoint metadata
# ---------------------------------------------------------------------------
# STS is a central (region-less) service, so the CLI is given the fixed endpoint.
# ECS is regional: the CLI resolves ecs.<region>.aliyuncs.com from --region, so
# no endpoint is pinned for it here.
PRODUCT_ENDPOINTS: dict = {
    "sts": STS_ENDPOINT,          # sts.aliyuncs.com
}

# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# Every product runs in plugin mode: lowercase-hyphenated command and flags,
#     e.g. `aliyun ecs describe-instances --biz-region-id cn-hangzhou`
#     and `aliyun sts get-caller-identity`. PascalCase API action names are
#     translated by _pascal_to_kebab before the argv is built.
_PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}


_AUTO_PLUGIN_PROBED = False


def _with_auto_plugin(argv):
    """Resolve a missing product plugin without an interactive prompt.

    These calls run with stdin closed, so the CLI's install prompt would otherwise
    fail and lose every read on a host that has no plugins yet. auto-plugin-install
    is a `configure set` profile key, NOT a per-invocation flag: on the command
    line CLI 3.4.5 ignores it and still prompts.

    Only a host that actually lacks this product's plugin is touched. `plugin
    list` is a local inventory read - no credential, no network, no download - so
    a machine that already has the plugin keeps its configuration untouched and
    never downloads anything. The key itself carries no credential and changes no
    cloud resource.
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


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to the plugin kebab-case command form.

    Example: GetCallerIdentity -> get-caller-identity
    """
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list:
    """Return the CLI command tokens for (product, action)."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    """Return the CLI flag for a parameter name, honoring product style."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return "--%s" % _pascal_to_kebab(key)
    return "--%s" % key


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached to
# EVERY API call of that run as a User-Agent, so all calls of one diagnosis can be
# correlated server-side.

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print("[_cli] session-id: %s" % ("****" + _SESSION_ID[-4:]), file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return "AlibabaCloud-Agent-Skills/%s/%s" % (SKILL_NAME, session_id())

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-high-frequency-issues"


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
            "  Verify credentials: aliyun sts get-caller-identity\n"
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
_RETRY_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal error",
    "http 500", "http 502", "http 503", "http 504",
    "statuscode: 5", "502", "504", "server busy",
    "connection reset", "timed out", "timeout", "temporarily unavailable",
)


def _is_retryable(err: "CliError") -> bool:
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = ("%s %s" % (code, str(err))).lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


def call(product: str, action: str, params: Optional[dict] = None,
         region: str = DEFAULT_REGION, profile: Optional[str] = None,
         timeout: int = 60) -> dict:
    """Invoke an Alibaba Cloud OpenAPI action via the aliyun CLI.

    Transient errors (Throttling / 5xx / timeout) are retried up to 3 attempts
    with linear backoff (2s, 4s); non-retryable errors are raised immediately.
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
                    "%s %s failed after %d attempts: %s" % (product, action, attempt, e),
                    code=e.code, stderr=e.stderr)
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print("[WARN] %s %s transient error (%s); retry %d/%d in %ss"
                  % (product, action, e.code or "unknown", attempt,
                     _MAX_ATTEMPTS - 1, wait_s), file=sys.stderr)
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps type-checkers happy


def _json_body(text):
    """Decode the CLI's JSON body even when a notice precedes it on stdout.

    Eval 15643 measured two legs that told the customer their credential chain
    was unconfigured because `sts GetCallerIdentity` stdout opened with a stray
    line: the strict parse raised, the identity precheck read that as a missing
    credential, and every cloud read was abandoned. A parse hiccup is not a
    customer-side credential fault, so the body is located instead of assumed.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        offsets = [i for i in (text.find("{"), text.find("[")) if i != -1]
        if not offsets:
            raise
        return json.JSONDecoder().raw_decode(text[min(offsets):])[0]
def _call_cli(product: str, action: str, params: Optional[dict], region: str,
              profile: Optional[str], timeout: int) -> dict:
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
            _with_auto_plugin(cmd), capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL,  # never hang on interactive prompts
        )
    except subprocess.TimeoutExpired:
        raise CliError("aliyun %s %s timed out after %ss" % (product, action, timeout))

    if result.returncode != 0:
        stderr = _clean_stderr(result.stderr or "")
        code = _extract_error_code(stderr)
        raise CliError("aliyun %s %s failed: %s" % (product, action, stderr[:300]),
                       code=code, stderr=stderr)

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = _json_body(stdout)
    except json.JSONDecodeError as e:
        raise CliError("aliyun %s %s returned non-JSON output: %s" % (product, action, e))

    # Some APIs report request-level failures INSIDE the body while the CLI still
    # exits 0 (HTTP 200). Treat a non-Success body Code as an invocation failure so
    # callers degrade via the standard CliError path instead of reading an error
    # payload as data.
    if isinstance(body, dict):
        resp_code = str(body.get("Code") or "").strip()
        if resp_code and resp_code not in ("Success", "OK"):
            message = _clean_stderr(str(body.get("Message") or ""))
            raise CliError("aliyun %s %s failed: Code=%s Message=%s"
                           % (product, action, resp_code, message[:300]),
                           code=resp_code, stderr=message)
    return body


# The aliyun CLI colors its stderr output; strip ANSI escapes so error text stays
# plain ASCII. Credential values are masked before any text can reach a [WARN]
# line, a CliError message, or JSON output.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential key-value pairs in CLI error text. Pure; never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: "%s=***" % m.group(1), text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI colors, MASK CREDENTIALS and collapse blank runs. Single choke
    point every CLI stderr passes through before surfacing anywhere."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the credential masking, executed on every import;
# a failure here means a leaked token could reach a [WARN] line -- not allowed.
# normal
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
# boundary: signed-URL network-error envelope (AccessKeyId + long SecurityToken).
_env = ('GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=STS.NYoy5FakeKey1234'
        "&Action=DescribeInstances&SecurityToken=" + "CAIS" + ("x" * 101)
        + '&Signature=abcd1234ef==&SignatureNonce=9e2f1" dial tcp: refused')
_masked = _clean_stderr(_env)
assert "STS.NYoy5FakeKey1234" not in _masked, _masked
assert ("x" * 101) not in _masked, _masked
assert "abcd1234ef" not in _masked, _masked
assert "AccessKeyId=***" in _masked and "SecurityToken=***" in _masked
# boundary: JSON-shaped credential pairs are masked as well.
_js = _clean_stderr('{"AccessKeyId": "STS.NYfake", "SecurityToken": "CAISfake99"}')
assert "STS.NYfake" not in _js and "CAISfake99" not in _js and _js.count("***") == 2
# invalid
assert _clean_stderr(None) == "" and _clean_stderr("") == "" and _mask_credentials("") == ""


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text."""
    for line in (stderr or "").splitlines():
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


def resolve_account_id(region: str = DEFAULT_REGION, profile: Optional[str] = None) -> str:
    """Return the Alibaba Cloud UID (AccountId) of the active credential, or ""."""
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError as exc:
        sys.stderr.write("[WARN] identity read failed: %s\n" % exc)
        return ""


# --- customer-facing hygiene (2026-10-27) -----------------------------------
# The dispatcher masks its child stream, but an area entry script is also run
# directly (evaluations, manual repros), and its own prints carried the raw
# account UID, a Cloud Assistant InvokeId or the 32-hex session id. Installing
# the mask here covers every area of this package, because every entry imports
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
