#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation layer for host intrusion cleanup
======================================================================
SECURITY: This module is the single choke point for every cloud call the
skill makes. It enforces once, for all callers:

* a runtime ACTION WHITELIST (ALLOWED_ACTIONS in _constants.py): anything
  outside the set -- in particular every destructive or state-changing
  action -- cannot be dispatched even by a bug in a caller;
* argument-list subprocess execution only (never a shell string, never
  shell=True) with a wall-clock timeout on every call (MUST 7.6.1);
* one 32-character hex session-id per run, folded into the User-Agent of
  every call for observability (AlibabaCloud-Agent-Skills/{skill}/{session});
* backoff retries for transient failures only (throttling / 5xx / timeout);
* credential masking applied to every byte of CLI text handed back to a
  caller: AccessKeyId / SecurityToken / Signature style values become ***;
* NO credential is ever read, printed, cached or passed here -- the aliyun
  CLI's own default credential chain decides who is calling.

Command style (verified against aliyun CLI 3.4.5):
* plugin-mode products (ecs, sas, cms, sts, ...) use lowercase-hyphenated
  commands and flags:
      aliyun ecs describe-snapshots --biz-region-id cn-hangzhou ...
      aliyun sts get-caller-identity
* Cloud Backup (hbr) is the one exception: this CLI rejects the kebab form
  ("not a valid built-in command", it would need the separate aliyun-cli-hbr
  plugin), so product `hbr` keeps the built-in metadata form with the
  PascalCase action name `DescribeRestoreJobs2`.
"""

from __future__ import annotations

import base64
import binascii
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
    CLI_BIN,
    CLI_TIMEOUT_SECONDS,
    PLUGIN_STYLE_PRODUCTS,
    PRODUCT_ENDPOINTS,
    PRODUCT_ENDPOINT_TMPLS,
    RETRY_BACKOFF_SECONDS,
    RETRY_MAX_ATTEMPTS,
    SKILL_NAME,
    USER_AGENT_FLAG,
    USER_AGENT_TEMPLATE,
)

_DEFAULT_REGION = "cn-hangzhou"


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails or is refused locally."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr

    @property
    def is_permission_error(self) -> bool:
        text = "%s %s" % (self.code or "", self.args[0] if self.args else "")
        return any(marker in text for marker in ("NoPermission", "ImplicitDeny",
                                                 "AccessDenied", "NoAuth"))


# ---------------------------------------------------------------------------
# Session-id & User-Agent (observability)
# ---------------------------------------------------------------------------

_SESSION_ID: Optional[str] = None


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


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print("[_cli] session-id: %s" % ("****" + _SESSION_ID[-4:]), file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return USER_AGENT_TEMPLATE.format(skill_name=SKILL_NAME,
                                      session_id=session_id())

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
    """Ensure the aliyun CLI is on PATH; exit with guidance otherwise."""
    if shutil.which(CLI_BIN) is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill invokes every cloud API through the Alibaba Cloud CLI.\n"
            "  Install:  https://help.aliyun.com/document_detail/121541.html\n"
            "  Verify credentials: aliyun sts get-caller-identity   (default chain; never\n"
            "             pass credentials on the command line)\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------

def _pascal_to_kebab(name: str) -> str:
    """GetCallerIdentity -> get-caller-identity (plugin-mode command form)."""
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list:
    if product in PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    if product in PLUGIN_STYLE_PRODUCTS:
        return "--%s" % _pascal_to_kebab(key)
    return "--%s" % key


def _endpoint_for(product: str, region: str) -> str:
    """Central endpoint, region-templated endpoint, or '' (CLI resolves it)."""
    endpoint = PRODUCT_ENDPOINTS.get(product)
    if endpoint:
        return endpoint
    tmpl = PRODUCT_ENDPOINT_TMPLS.get(product)
    if tmpl:
        return tmpl.format(region=region)
    return ""


def _check_whitelist(product: str, action: str) -> None:
    """Local guardrail: only the declared action set can ever leave this host."""
    allowed = ALLOWED_ACTIONS.get(product)
    if not allowed or action not in allowed:
        raise CliError(
            "refused locally: action %s of product %s is not in this skill's "
            "whitelist (destructive operations and instance state changes are "
            "customer-executed steps (console or the equivalent OpenAPI))" % (action, product),
            code="Local.WhitelistViolation",
        )


# Inline boundary assertions for the guardrail: destructive names must never
# pass, a whitelisted Describe always does. Raises at import time if broken.
_check_whitelist("ecs", "DescribeSnapshots")
try:
    _check_whitelist("ecs", "DeleteSnapshot")
    raise AssertionError("whitelist guardrail failed to block a destructive op")
except CliError as _guard_err:
    assert _guard_err.code == "Local.WhitelistViolation"
try:
    _check_whitelist("ecs", "ResetDisk")
    raise AssertionError("whitelist guardrail failed to block a rollback op")
except CliError as _guard_err2:
    assert _guard_err2.code == "Local.WhitelistViolation"
try:
    _check_whitelist("sas", "HandleSecurityEvents")
    raise AssertionError("whitelist guardrail failed to block an alert handler")
except CliError as _guard_err3:
    assert _guard_err3.code == "Local.WhitelistViolation"


# ---------------------------------------------------------------------------
# Transient-error retry (Throttling / 5xx / timeout)
# ---------------------------------------------------------------------------

_RETRY_CODES = {
    "throttling", "throttling.user", "throttling.api",
    "serviceunavailable", "internalerror", "sdk.httperror", "unknownerror",
    "requesttimeout",
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
    haystack = ("%s %s" % (code, str(err))).lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


# ---------------------------------------------------------------------------
# Credential masking
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce|password)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def mask_credentials(text: str) -> str:
    """Mask credential key-value pairs in CLI text; pure, never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: "%s=***" % m.group(1), text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI colors, mask credentials, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Import-time boundary assertions for the credential mask (normal / boundary /
# invalid inputs). A broken mask would let a token reach a [WARN] line.
assert _clean_stderr("Error: connection refused") == "Error: connection refused"
_masked = _clean_stderr(
    "GET https://host/?AccessKeyId=STS.NYfakeKey1234&SecurityToken="
    + "CAIS" + ("x" * 101) + "&Signature=abcd1234ef== dial tcp")
assert "STS.NYfakeKey1234" not in _masked
assert ("x" * 101) not in _masked
assert "abcd1234ef" not in _masked
assert "AccessKeyId=***" in _masked
assert _clean_stderr(None) == ""
assert mask_credentials("") == ""


# ---------------------------------------------------------------------------
# Error-code extraction from CLI stderr envelopes
# ---------------------------------------------------------------------------

_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
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
# The one call path
# ---------------------------------------------------------------------------

_SUCCESS_BODY_CODES = {"Success", "OK", "200", "0"}

# Active per-call wall-clock timeout; overridable via set_call_timeout() but
# ALWAYS a positive number -- no call ever runs without a timeout (MUST 7.6.1).
_ACTIVE_TIMEOUT = CLI_TIMEOUT_SECONDS


def set_call_timeout(seconds) -> None:
    """Override the per-call CLI timeout (validated positive)."""
    global _ACTIVE_TIMEOUT
    if not isinstance(seconds, int) or isinstance(seconds, bool) \
            or not (5 <= seconds <= 600):
        raise CliError("--cli-timeout must be an integer between 5 and 600 "
                       "seconds; got %r" % (seconds,))
    _ACTIVE_TIMEOUT = seconds


def call(
    product: str,
    action: str,
    params: Optional[dict] = None,
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: Optional[int] = None,
) -> dict:
    """Invoke an allowed OpenAPI action via the aliyun CLI.

    Raises CliError for local refusals (whitelist), API failures and repeated
    transient failures. Transient errors (Throttling / 5xx / timeout) are
    retried up to RETRY_MAX_ATTEMPTS times with linear backoff.
    """
    timeout = timeout or _ACTIVE_TIMEOUT
    last_err: Optional[CliError] = None
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, profile, timeout)
        except CliError as e:
            last_err = e
            if getattr(e, "code", "") == "Local.WhitelistViolation":
                raise  # a refusal is never retried
            if not _is_retryable(e):
                raise
            if attempt >= RETRY_MAX_ATTEMPTS:
                raise CliError(
                    "%s %s failed after %d attempts: %s"
                    % (product, action, attempt, e),
                    code=e.code, stderr=e.stderr)
            wait_s = attempt * RETRY_BACKOFF_SECONDS
            print("[WARN] %s %s transient error (%s); retry %d in %ds"
                  % (product, action, e.code or "unknown", attempt, wait_s),
                  file=sys.stderr)
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps type checkers happy


# --- plugin-mode list parameters -------------------------------------------
# The OpenAPI reference spells a repeated list as Name.1 / Name.2. Plugin mode
# takes one kebab flag followed by the bare values, and a repeated structure
# takes one flag per index carrying Key=value pairs. A few actions document
# InstanceId as one comma-separated string rather than a repeated list.
_INDEXED_KEY_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9]*)\.(\d+)(?:\.([A-Za-z][A-Za-z0-9]*))?$")
_STRUCT_LIST_PARAMS = frozenset({"Tag", "DiskDeviceMapping", "ModuleList"})
_SCALAR_LIST_PARAMS = frozenset({
    ("describeinstancehistoryevents", "instanceid"),
    ("describeinvocations", "instanceid"),
    ("describesendfileresults", "instanceid"),
    ("describeinstanceautorenewattribute", "instanceid"),
})


def _shape_key(action, base):
    """Normalize an action/param pair so kebab and PascalCase spellings agree."""
    return (re.sub(r"[^a-z0-9]", "", str(action).lower()),
            re.sub(r"[^a-z0-9]", "", str(base).lower()))
_REPEAT_LIST_PARAMS = frozenset({
    "InstanceId", "InstanceTypes", "InstanceEventCycleStatus",
    "InstanceEventType", "EventId", "AddAccount", "RemoveAccount",
})


def _fold_indexed_params(action, params):
    """Fold documented Name.N list keys into one entry per base name.

    Insertion order is preserved and indexed values are ordered by their numeric
    index, so InstanceId.10 never lands ahead of InstanceId.2.
    """
    groups = {}
    for key, value in (params or {}).items():
        match = _INDEXED_KEY_RE.match(key)
        if not match:
            continue
        base, index, sub = match.group(1), int(match.group(2)), match.group(3)
        groups.setdefault(base, {}).setdefault(index, {})
        groups[base][index][sub] = value
    folded = {}
    for base, indexes in groups.items():
        ordered = [indexes[number] for number in sorted(indexes)]
        if base in _STRUCT_LIST_PARAMS:
            folded[base] = [dict(item) for item in ordered]
        elif _shape_key(action, base) in _SCALAR_LIST_PARAMS:
            folded[base] = ",".join(
                str(item.get(None)) for item in ordered if item.get(None) is not None)
        else:
            folded[base] = [item.get(None) for item in ordered]
    out = []
    emitted = set()
    for key, value in (params or {}).items():
        match = _INDEXED_KEY_RE.match(key)
        if not match:
            out.append((key, value))
            continue
        base = match.group(1)
        if base in emitted:
            continue
        emitted.add(base)
        out.append((base, folded[base]))
    return out


def _list_param_argv(action, params, flag_of, text_of, skip_empty=False):
    """Render params as plugin-mode argv tokens, folding Name.N list keys."""
    argv = []
    for key, value in _fold_indexed_params(action, params):
        if value is None or (skip_empty and value == ""):
            continue
        scalar_list = _shape_key(action, key) in _SCALAR_LIST_PARAMS
        if isinstance(value, (list, tuple)) and key in _STRUCT_LIST_PARAMS:
            for item in value:
                argv.append(flag_of(key))
                argv.extend("%s=%s" % (name, text_of(val))
                            for name, val in item.items() if val is not None)
            continue
        if isinstance(value, (list, tuple)) and key in _REPEAT_LIST_PARAMS and not scalar_list:
            values = [text_of(item) for item in value if item is not None]
            if values:
                argv.append(flag_of(key))
                argv.extend(values)
            continue
        argv.extend([flag_of(key), text_of(value)])
    return argv


def _param_text(value):
    """Render one scalar parameter value the way plugin mode expects it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(list(value) if isinstance(value, tuple) else value,
                          ensure_ascii=False, separators=(",", ":"))
    return str(value)


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
def _call_cli(
    product: str,
    action: str,
    params: Optional[dict],
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict:
    """Execute exactly one CLI invocation (argument list, never shell=True)."""
    _check_whitelist(product, action)

    cmd = [CLI_BIN] + _command_tokens(product, action)
    endpoint = _endpoint_for(product, region)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]

    # Observability: one session-id User-Agent shared by every call of a run.
    cmd += [USER_AGENT_FLAG, user_agent()]

    cmd += _list_param_argv(action, params, lambda key: _param_flag(product, key), _param_text)

    try:
        result = subprocess.run(
            _with_auto_plugin(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # never hang on interactive prompts
        )
    except subprocess.TimeoutExpired:
        raise CliError("%s %s timed out after %ds" % (product, action, timeout))

    if result.returncode != 0:
        stderr = _clean_stderr(result.stderr or "")
        raise CliError(
            "%s %s failed: %s" % (product, action, stderr[:300]),
            code=_extract_error_code(stderr),
            stderr=stderr,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = _json_body(stdout)
    except json.JSONDecodeError as e:
        raise CliError("%s %s returned non-JSON output: %s"
                       % (product, action, e))

    # Some products report request failures INSIDE a 200 body (CloudMonitor
    # is the known one). Non-success body codes must go through the standard
    # CliError path so callers degrade instead of reading an error payload
    # as data.
    if isinstance(body, dict):
        resp_code = str(body.get("Code") or "").strip()
        if resp_code and resp_code not in _SUCCESS_BODY_CODES:
            raise CliError(
                "%s %s failed: Code=%s Message=%s"
                % (product, action, resp_code,
                   _clean_stderr(str(body.get("Message") or ""))[:300]),
                code=resp_code,
                stderr=_clean_stderr(str(body.get("Message") or "")),
            )
    return body


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    return "%s" % (value,)


# ---------------------------------------------------------------------------
# Helpers used by the entry script
# ---------------------------------------------------------------------------

def dig(obj: Any, path: list, default: Any = None) -> Any:
    """Walk a nested dict along `path`; return default on any miss."""
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
        if node is None:
            return default
    return node


def as_list(value: Any) -> list:
    """Normalize RPC list shapes: [..], {Item:[..]} or a bare dict."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for inner in ("Item", "Items", "Snapshot", "SuspEvents", "List",
                      "RestoreJobs", "InvokeInstance", "Invocation",
                      "ExposedInstance", "Tag", "LockReason"):
            if inner in value:
                return as_list(value.get(inner))
        # Tolerate any other single-list wrapper shape returned by the API.
        for inner_value in value.values():
            if isinstance(inner_value, list):
                return list(inner_value)
        return [value]
    return [value]


def encode_command(content: str) -> str:
    """Base64 a guest command for transport (the documented encoding of the
    command-content field). Pure helper; the whitelist guarantees what can
    ever be encoded here."""
    return base64.b64encode(content.encode("utf-8")).decode("ascii")


def decode_guest_output(text: str) -> str:
    """Cloud Assistant returns command output base64-encoded; decode safely
    and mask anything credential-looking before it reaches the report."""
    if not text:
        return ""
    try:
        decoded = base64.b64decode(str(text).strip())
        return mask_credentials(decoded.decode("utf-8", "replace"))
    except (binascii.Error, ValueError, UnicodeError):
        return mask_credentials(str(text))


def collect_strings(obj: Any) -> list:
    """Flatten every string value inside a nested dict/list (used to match a
    customer-supplied public IP against an exposure record without assuming
    a fixed field layout)."""
    found: list = []
    if isinstance(obj, dict):
        for value in obj.values():
            found.extend(collect_strings(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(collect_strings(item))
    elif isinstance(obj, str):
        found.append(obj)
    return found


def pick(body: Any, *keys: str) -> Any:
    """First present key among `keys` on a response body (tolerant shape
    mapping: several list actions wrap their rows under different names)."""
    if isinstance(body, dict):
        for key in keys:
            if body.get(key) is not None:
                return body.get(key)
    return None


def resolve_account_id(region: str = _DEFAULT_REGION,
                       profile: Optional[str] = None) -> str:
    """AccountId of the active credential via STS GetCallerIdentity ('' on
    failure -- callers decide whether identity is fatal)."""
    try:
        body = call("sts", "GetCallerIdentity", {},
                    region=region, profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError:
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
