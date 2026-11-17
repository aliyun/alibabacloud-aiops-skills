#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer for the ECS remote-connection
entry triage skill (internal module: `_` prefix, never run directly).

SECURITY: This skill is strictly READ-ONLY. Every OpenAPI call in this skill
goes through ONE place, `call()`, which enforces the read-only API whitelist
from _constants.API_WHITELIST BEFORE any subprocess is spawned: an action
outside the whitelist can never reach the CLI. Authentication is resolved
exclusively by the aliyun CLI default credential chain (platform-injected
environment or the local CLI config profile). This module NEVER reads,
writes, caches or logs any AccessKey ID / Secret or session token, and it
does not accept credential flags. No direct HTTP signing, no SDK.

CLI-only backend
----------------
Each call runs the `aliyun` CLI as a subprocess using an ARGUMENT LIST
(never shell=True), with stdin detached and a per-call timeout:

    aliyun <product> <action> --param value ... --user-agent <UA>

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags, e.g.
    aliyun ecs describe-instances --biz-region-id cn-hangzhou
    aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.

Observability
-------------
A 32-character lowercase hex session-id (`uuid.uuid4().hex`) is generated
once per script run and attached to EVERY CLI invocation of that run through
the `--user-agent` flag, using the template
    AlibabaCloud-Agent-Skills/{skill-name}/{session-id}
so the whole call chain of one diagnosis can be correlated. The session-id
is cached at module level; the User-Agent value itself is built by
`user_agent()` below.

Transient-error retry
---------------------
Throttling / 5xx / timeout failures are transient and safe to retry: up to 3
attempts with linear backoff (2s, 4s). Non-transient errors (permission
denied, invalid parameter, ...) raise immediately.

Credential masking
------------------
Every piece of CLI stderr passes through `_clean_stderr()`: ANSI codes are
stripped and any credential key=value / key:value pair in the text is
replaced by *** BEFORE it can surface in a [WARN] line, a CliError message,
or a JSON field. Boundary assertions for the mask run on import.
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
    API_WHITELIST,
    BACKOFF_BASE_SECONDS,
    DEFAULT_TIMEOUT,
    MAX_ATTEMPTS,
    SKILL_NAME,
    USER_AGENT_PREFIX,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails or is refused by the guard."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Session-id & User-Agent
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
    """Return the per-run 32-char hex session-id (lazy, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent value attached to every CLI call of this run."""
    return f"{USER_AGENT_PREFIX}/{SKILL_NAME}/{session_id()}"

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


# ---------------------------------------------------------------------------
# Command style: every product is served in plugin mode (lowercase-hyphenated
# commands and flags); PascalCase API action names are translated here.
# ---------------------------------------------------------------------------

_PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}


def _pascal_to_kebab(name: str) -> str:
    """GetCallerIdentity -> get-caller-identity (plugin command form)."""
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


# ---------------------------------------------------------------------------
# Read-only whitelist guard (enforced BEFORE any subprocess spawn)
# ---------------------------------------------------------------------------

def _guard_whitelist(product: str, action: str) -> None:
    """Refuse any (product, action) outside the embedded read-only set."""
    if (product, action) not in API_WHITELIST:
        raise CliError(
            f"refused: ({product}, {action}) is not in this skill's "
            "read-only API whitelist (see references/ram-policies.md)")


# ---------------------------------------------------------------------------
# Credential-value masking
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Any access-key / token / signature style key=value (query string) or
# "key":"value" (JSON) pair gets its VALUE replaced with *** while the key
# name stays visible for diagnosability. Keys matched case-insensitively;
# the value charset stops at whitespace, quotes and query separators.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|access_key_id|access_key_secret|"
    r"securitytoken|sessiontoken|password|signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential key-value pairs in error text. Pure, never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Single choke point for ALL CLI stderr text: strip ANSI, mask
    credentials, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the mask (normal / boundary / invalid).
assert _clean_stderr("ERROR: NoPermission: User not authorized") == \
    "ERROR: NoPermission: User not authorized"
assert _mask_credentials("no secrets here") == "no secrets here"
_env = ('GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=FAKEKEY0001'
        "&Action=DescribeInstances&SecurityToken=" + "z" * 64 +
        '&Signature=abc123sig" dial tcp: refused')
_masked = _clean_stderr(_env)
assert "FAKEKEY0001" not in _masked and ("z" * 64) not in _masked
assert "abc123sig" not in _masked
assert "AccessKeyId=***" in _masked and "SecurityToken=***" in _masked
assert _clean_stderr(None) == ""
assert _mask_credentials("") == ""


# ---------------------------------------------------------------------------
# Transient-error classification
# ---------------------------------------------------------------------------

_RETRY_CODES = {
    "throttling", "throttling.user", "throttling.api",
    "serviceunavailable", "internalerror", "sdk.httperror", "unknownerror",
}
_RETRY_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal error",
    "http 500", "http 502", "http 503", "http 504", "statuscode: 5",
    "server busy", "connection reset", "timed out", "timeout",
    "temporarily unavailable",
)


def _is_retryable(err: CliError) -> bool:
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


# ---------------------------------------------------------------------------
# Availability pre-check
# ---------------------------------------------------------------------------

def check_cli_available() -> None:
    """Ensure the aliyun CLI exists; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "[ERROR] aliyun CLI not found. Install it "
            "(https://help.aliyun.com/document_detail/121541.html) and run "
            "`aliyun sts get-caller-identity` to set up the default credential chain.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Error-code extraction from CLI stderr envelopes
# ---------------------------------------------------------------------------

_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort API error code from CLI stderr (NoPermission,
    InvalidParameter, Throttling.User, ...)."""
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("ErrorCode:") or line.startswith("Code:"):
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
# The one and only invocation path
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: Optional[str] = None,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke a whitelisted read-only OpenAPI action via the aliyun CLI.

    Raises CliError (after whitelist refusal or after retries for transient
    errors). Returns the parsed JSON body ({} for an empty stdout).
    """
    _guard_whitelist(product, action)
    last_err: Optional[CliError] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, profile, timeout)
        except CliError as e:
            last_err = e
            if not _is_retryable(e):
                raise
            if attempt >= MAX_ATTEMPTS:
                raise CliError(
                    f"{product} {action} failed after {attempt} attempts: {e}",
                    code=e.code, stderr=e.stderr)
            wait_s = attempt * BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({e.code or 'unknown'}); retry {attempt}/"
                f"{MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # unreachable in practice; keeps type-flow complete


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
    params: Optional[dict[str, Any]],
    region: Optional[str],
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    """Execute ONE CLI invocation: argument list only, never shell=True."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        command = _pascal_to_kebab(action)
    else:
        command = action
    cmd = ["aliyun", product, command]
    if region:
        cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]
    # Observability: same session-id User-Agent on every call of this run.
    cmd += ["--user-agent", user_agent()]
    cmd += _list_param_argv(action, params, lambda key: "--" + _pascal_to_kebab(key), _param_text)

    try:
        result = subprocess.run(
            _with_auto_plugin(cmd),
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
        return _json_body(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")


# ---------------------------------------------------------------------------
# Small shape helpers (defensive parsing everywhere: absent fields -> None)
# ---------------------------------------------------------------------------

def dig(obj: Any, *keys: str) -> Any:
    """Walk nested dicts/lists along keys; return None on any miss."""
    node = obj
    for key in keys:
        if isinstance(node, dict):
            node = node.get(key)
        elif isinstance(node, list) and isinstance(key, int) and key < len(node):
            node = node[key]
        else:
            return None
    return node


def get_caller_identity(profile: Optional[str] = None,
                        timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Return {uid, arn, identity_type} via the whitelisted identity call."""
    body = call("sts", "GetCallerIdentity", {}, profile=profile,
                timeout=timeout)
    return {
        "uid": str(body.get("AccountId") or ""),
        "arn": str(body.get("Arn") or ""),
        "identity_type": str(body.get("IdentityType") or "Unknown"),
    }


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
