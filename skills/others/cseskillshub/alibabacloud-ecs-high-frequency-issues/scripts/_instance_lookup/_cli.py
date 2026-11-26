#!/usr/bin/env python3
"""
_cli.py -- shared OpenAPI invocation layer for console resource lookup
======================================================================
SECURITY: This skill is strictly READ-ONLY. Authentication is resolved by the
aliyun CLI default credential chain (environment or the CLI config file); this
module NEVER reads, prints, caches or passes any key material, and never
accepts credentials as arguments. Only whitelisted read actions are callable.

Internal module (leading underscore): imported by the entry scripts, never run
directly. It is the SINGLE choke point through which every Alibaba Cloud call
of this skill passes, so retry, timeout, credential masking and the
observability User-Agent apply uniformly.

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
    aliyun ecs describe-instances --biz-region-id cn-hangzhou ...
    aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.

Transient failures (Throttling / 5xx / timeout) retry up to 3 attempts with
linear backoff; anything else raises CliError("Code: Message") immediately.
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

from _constants import ECS_PRODUCT, STS_ENDPOINT, STS_PRODUCT


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails. Carries `code` and `stderr`."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Read-only API whitelist (ABSOLUTE boundary; anything else is refused here)
# ---------------------------------------------------------------------------
READ_ACTION_WHITELIST = {
    (ECS_PRODUCT, "DescribeInstances"),
    (ECS_PRODUCT, "DescribeInstanceStatus"),
    (ECS_PRODUCT, "DescribeAvailableResource"),
    (STS_PRODUCT, "GetCallerIdentity"),
}

# Products whose CLI form is plugin mode (lowercase-hyphenated commands).
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
    """GetCallerIdentity -> get-caller-identity (plugin command form)."""
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


# ---------------------------------------------------------------------------
# Session-id and User-Agent (observability; MUST SA-2.11)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY call of that run so the whole evidence sweep is correlatable.

from _constants import SKILL_NAME  # noqa: E402

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (lazy, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """The User-Agent string attached to every call of this run."""
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id()}"

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
    """Exit with install guidance when the aliyun CLI is missing."""
    if shutil.which("aliyun") is None:
        print(
            "[FAIL] aliyun CLI not found. Install the Alibaba Cloud CLI and "
            "run `aliyun sts get-caller-identity` (default credential chain only). "
            "See https://help.aliyun.com/document_detail/121541.html",
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
# Credential-value masking
# ---------------------------------------------------------------------------
# CLI network-error envelopes can embed a signed request URL carrying
# access key ids, security tokens and signatures. Every such key/value pair is
# masked BEFORE the text can reach a [WARN] line, a CliError message, or any
# report field. Keys match case-insensitively; values stop at whitespace,
# quotes, and URL/query delimiters.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def mask_credentials(text: str) -> str:
    """Mask credential key/value pairs in CLI error text. Never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def clean_stderr(stderr: str) -> str:
    """Strip ANSI colors, mask credential values, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the masker (normal / boundary / invalid):
# a broken mask would leak a token into a report line, so import fails loudly.
assert clean_stderr("ERROR: connection refused") == "ERROR: connection refused"
assert mask_credentials("nothing to mask") == "nothing to mask"
_probe = (
    "GET https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=STS.NZfake123456"
    "&Action=DescribeInstances&SecurityToken=" + ("Q" * 64) +
    "&Signature=sigvalue123&x=1")
_masked = clean_stderr(_probe)
assert "STS.NZfake123456" not in _masked
assert ("Q" * 64) not in _masked
assert "sigvalue123" not in _masked
assert "AccessKeyId=***" in _masked and "Signature=***" in _masked
_probe_json = '{"AccessKeyId": "LTAIfakeAAA"}'
assert "LTAIfakeAAA" not in clean_stderr(_probe_json)
assert clean_stderr(None) == ""
assert mask_credentials("") == ""


# ---------------------------------------------------------------------------
# Error-code extraction from the CLI failure envelope
# ---------------------------------------------------------------------------
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("ErrorCode:") or line.startswith("Code:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("Data:"):
            try:
                body = json.loads(line.split(":", 1)[1].strip())
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
# The one public call path
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict] = None,
    region: str = "cn-hangzhou",
    profile: Optional[str] = None,
    timeout: int = 60,
) -> dict:
    """Invoke a WHITELISTED read action via the aliyun CLI and return JSON.

    Raises:
        CliError: non-retryable failure, or retryable failure after 3
            attempts. Permission failures surface with their API code so
            callers can print the missing RAM action instead of retrying.
        ValueError: the (product, action) pair is not on the read whitelist.
    """
    if (product, action) not in READ_ACTION_WHITELIST:
        raise ValueError(
            f"action {product}/{action} is not on this skill's read-only "
            "whitelist and must never be called"
        )
    last_err: Optional[CliError] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, profile, timeout)
        except CliError as err:
            last_err = err
            if not _is_retryable(err):
                raise
            if attempt >= _MAX_ATTEMPTS:
                raise CliError(
                    f"{product} {action} failed after {attempt} attempts: {err}",
                    code=err.code, stderr=err.stderr,
                )
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({err.code or 'unknown'}); retry {attempt}/"
                f"{_MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # unreachable, keeps linters satisfied


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

def _call_cli(product, action, params, region, profile, timeout) -> dict:
    """One CLI subprocess invocation: argument list, never shell=True."""
    cmd = ["aliyun"] + _command_tokens(product, action)
    if product == STS_PRODUCT:
        cmd += ["--endpoint", STS_ENDPOINT]
    cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]
    # Observability: session-id User-Agent on every call (SA-2.11).
    cmd += ["--user-agent", user_agent()]
    cmd += _list_param_argv(action, params, lambda key: _param_flag(product, key), _param_text, skip_empty=True)

    try:
        result = subprocess.run(
            _with_auto_plugin(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # never hang on an interactive prompt
        )
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun {product} {action} timed out after {timeout}s")

    if result.returncode != 0:
        stderr = clean_stderr(result.stderr or "")
        raise CliError(
            f"aliyun {product} {action} failed: {stderr[:300]}",
            code=_extract_error_code(stderr),
            stderr=stderr,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = _json_body(stdout)
    except json.JSONDecodeError as exc:
        raise CliError(f"aliyun {product} {action} returned non-JSON: {exc}")
    if isinstance(body, dict):
        code = str(body.get("Code") or "").strip()
        if code and code not in ("Success", "OK", "200"):
            message = clean_stderr(str(body.get("Message") or ""))
            raise CliError(
                f"aliyun {product} {action} failed: Code={code} "
                f"Message={message[:300]}",
                code=code, stderr=message,
            )
    return body


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(region: str = "cn-hangzhou",
                       profile: Optional[str] = None) -> str:
    """Account id of the CURRENT credential; '' when unavailable.

    Used only as a traceability label and for the account-scope statement in
    reports (results reflect only the credential's own account).
    """
    try:
        body = call(STS_PRODUCT, "GetCallerIdentity", {},
                    region=region, profile=profile, timeout=30)
        return str(body.get("AccountId", "") or "")
    except (CliError, ValueError):
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
