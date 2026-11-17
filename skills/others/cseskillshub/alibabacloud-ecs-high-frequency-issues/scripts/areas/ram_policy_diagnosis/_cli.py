#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_cli.py -- shared aliyun-CLI invocation layer for
area:ram-policy-diagnosis
=====================================================================
SECURITY:
  * Every cloud call goes through this module as an `aliyun` CLI subprocess
    (argument-list form, NEVER shell=True) with a per-call timeout.
  * No explicit credential handling anywhere: authentication is resolved
    exclusively by the aliyun CLI default credential chain (CLI config or
    platform-injected environment). This module never reads, writes, caches
    or prints any AccessKey / Secret / token (SA-2.12).
  * All error text is credential-masked before it can reach stdout, stderr
    or a JSON report field.
  * Call surface discipline: the caller scripts pass ONLY the actions
    listed in _constants.VERIFIED_ACTIONS. ecs:run-command is reached only
    through the confirmation-gated --guest-check mode with an
    exact-match-whitelisted, observation-only command.

Observability (MUST SA-2.11b/c):
  Every invocation carries --user-agent set to the template
  "AlibabaCloud-Agent-Skills/{skill}/{session-id}" where {skill} is
  SKILL_NAME and {session-id} is a 32-character lowercase hex string
  (uuid.uuid4().hex) generated once per run, overridable via the
  SKILL_SESSION_ID environment variable, and shared by all calls of that
  run so the whole diagnosis is correlated.

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
        aliyun ecs describe-instances --biz-region-id cn-hangzhou
        aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.

Public API:
    call(product, action, params=None, region=..., profile=None, timeout=...)
    resolve_caller_identity(...) -> dict
    check_cli_available() -> None
    session_id() / user_agent()
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Optional

from _constants import DEFAULT_REGION, DEFAULT_TIMEOUT, SKILL_NAME, STS_ENDPOINT


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Per-product endpoint metadata (central services only; regional products
# are addressed through --region).
# ---------------------------------------------------------------------------
PRODUCT_ENDPOINTS: dict[str, str] = {
    "sts": STS_ENDPOINT,
}

# Every product is a plugin-mode product: lowercase-hyphenated commands and
# flags; PascalCase API action names are translated before the argv is built.
_PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}

# Permission-family error codes understood by the report layer. Vocabulary:
# NoPermission / ImplicitDeny family only (see the auth-failure literal rule
# in SKILL.md). Compared case-insensitively against extracted error codes.
PERMISSION_ERROR_CODES = {
    "nopermission", "accessdenied.nopermission", "nopermission.ram",
    "explicitdeny", "implicitdeny", "nodata.permission", "no.permission",
}

_PUBLIC_ERROR_CODE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")

# The aliyun CLI colors its stderr output; strip ANSI escapes so error text
# embedded in reports/JSON stays plain ASCII.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Credential-value masking: the CLI network-error envelope can embed a
# signed request URL whose query string carries credential parameters. Every
# <credentialKey>=<value> (query-string) or "<credentialKey>":"<value>"
# (JSON) pair is masked BEFORE the text can reach a [WARN] stderr line, a
# CliError message, or any JSON output field. Keys are matched
# case-insensitively; the value charset stops at whitespace, quotes,
# XML/HTML delimiters and the query-string separator '&'.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")

# LTAI*-prefixed key ids and long STS token shapes are masked standalone too.
_LTAI_AK_PATTERN = re.compile(r"LTAI[A-Za-z0-9]{12,}")
_STS_TOKEN_PATTERN = re.compile(r"STS\.[A-Za-z0-9]{20,}")


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


def _mask_credentials(text: str) -> str:
    """Mask credential key-value pairs and key shapes in error text.

    Pure function; replaces each matched credential value with *** while
    keeping the key name for diagnosability. Never raises.
    """
    if not text:
        return text or ""
    result = _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)
    result = _STS_TOKEN_PATTERN.sub(lambda m: m.group()[:8] + "****", result)
    result = _LTAI_AK_PATTERN.sub(lambda m: m.group()[:6] + "****", result)
    return result


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI color codes, mask credentials, collapse blank runs.

    Single choke point every CLI stderr passes through before it can surface
    in [WARN] lines, CliError messages or JSON fields.
    """
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the credential mask (MUST SA-2.12): normal
# text passes unchanged, credential-shaped payloads never do. A failure here
# means leaked material could reach a report, so the module must not run.
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
_mask_probe = _clean_stderr(
    'GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=FAKEVALUE123456789'
    "&SecurityToken=" + ("c" * 120) + '&Signature=abcd1234ef==" dial tcp')
assert "FAKEVALUE123456789" not in _mask_probe, _mask_probe
assert ("c" * 120) not in _mask_probe, _mask_probe
assert "abcd1234ef" not in _mask_probe, _mask_probe
assert "AccessKeyId=***" in _mask_probe
assert "SecurityToken=***" in _mask_probe
assert _clean_stderr(None) == ""
assert _clean_stderr("") == ""


# ---------------------------------------------------------------------------
# Command-style helpers
# ---------------------------------------------------------------------------

def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to its plugin-mode command form.

    Example: GetCallerIdentity -> get-caller-identity
    """
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


assert _pascal_to_kebab("GetCallerIdentity") == "get-caller-identity"
assert _pascal_to_kebab("DescribeInstances") == "describe-instances"


def _command_tokens(product: str, action: str) -> list[str]:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


# ---------------------------------------------------------------------------
# Session-id & User-Agent (observability, MUST SA-2.11b/c)
# ---------------------------------------------------------------------------

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached).

    Overridable once via the SKILL_SESSION_ID environment variable so all
    scripts of one agent turn share the same id.
    """
    global _SESSION_ID
    if _SESSION_ID is None:
        env = os.environ.get("SKILL_SESSION_ID", "").strip()
        if re.fullmatch(r"[0-9a-f]{32}", env):
            _SESSION_ID = env
        else:
            _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent value attached to every API call of this run."""
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
    "statuscode: 5", "server busy", "connection reset", "timed out",
    "timeout", "temporarily unavailable",
)


def _is_retryable(err: CliError) -> bool:
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


def _permission_error(err: CliError) -> bool:
    """True when the failure is a RAM authorization rejection of the
    diagnostic credential itself (NoPermission family, or a code whose
    trailing segment names the RAM layer)."""
    code = (getattr(err, "code", "") or "").lower()
    return (code in PERMISSION_ERROR_CODES or "nopermission" in code
            or bool(re.search(r"\.ram$", code)))


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Handles the real aliyun CLI 3.x failure envelope:

        Error: request execution failed: ... SDKError:
           StatusCode: 403
           Code: NoPermission
           Message: User not authorized to operate on the specified resource.
           Data: {"Code":"NoPermission",...}
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
            return candidate if _PUBLIC_ERROR_CODE_RE.match(candidate) else ""
    return ""


# ---------------------------------------------------------------------------
# Core invocation
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke one allowed Alibaba Cloud OpenAPI action via the aliyun CLI.

    Raises:
        CliError: on failure. Transient errors (Throttling / 5xx / timeout)
            are retried up to 3 attempts with linear backoff (2s, 4s);
            permission and parameter errors are raised immediately.
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
                    code=e.code, stderr=e.stderr)
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(f"[WARN] {product} {action} transient error "
                  f"({e.code or 'unknown'}); retry {attempt}/"
                  f"{_MAX_ATTEMPTS - 1} in {wait_s}s", file=sys.stderr)
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps type-checkers happy


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
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    """Execute one CLI invocation (argument-list form, never shell=True)."""
    cmd = ["aliyun"] + _command_tokens(product, action)

    endpoint = PRODUCT_ENDPOINTS.get(product)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]

    # Observability: one session-id User-Agent shared by every call of this run.
    cmd += ["--user-agent", user_agent()]

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
        raise CliError(f"aliyun {product} {action} timed out after {timeout}s")

    if result.returncode != 0:
        stderr = _clean_stderr(result.stderr or "")
        code = _extract_error_code(stderr)
        raise CliError(
            f"aliyun {product} {action} failed: {stderr[:300]}",
            code=code, stderr=stderr)

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = _json_body(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")

    # Some products report request-level failures INSIDE a 200 body. Treat a
    # non-Success body-level Code as an invocation failure so callers degrade
    # through the standard CliError path instead of reading an error payload
    # as data. Happy-path ECS/STS bodies carry no Code key, so they are
    # untouched.
    if isinstance(body, dict):
        resp_code = str(body.get("Code") or "").strip()
        if resp_code and resp_code not in ("Success", "OK", "200"):
            message = _clean_stderr(str(body.get("Message") or ""))
            raise CliError(
                f"aliyun {product} {action} failed: Code={resp_code} "
                f"Message={message[:300]}", code=resp_code, stderr=message)
    return body


def is_permission_error(err: CliError) -> bool:
    """Public wrapper: did the failure deny the diagnostic credential?"""
    return _permission_error(err)


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_caller_identity(
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
) -> dict[str, Any]:
    """Call STS GetCallerIdentity and normalize the identity facts the
    diagnosis needs. Raises CliError on failure (caller degrades)."""
    body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
    arn = str(body.get("Arn") or "")
    parts = arn.split(":")
    root_from_arn = parts[3] if len(parts) >= 4 and parts[3].isdigit() else ""
    return {
        "account_id": str(body.get("AccountId") or ""),
        "identity_type": str(body.get("IdentityType") or "Unknown"),
        "principal_name": str(body.get("PrincipalId") or ""),
        "arn": arn,
        "root_account": str(body.get("RootUserId") or "") or root_from_arn,
    }


def check_cli_available() -> None:
    """Ensure the aliyun CLI exists; exit with guidance when it does not."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n aliyun CLI not found\n" + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI to be installed and "
            "configured.\n\n"
            "  Install: " + "https://help.aliyun.com/document_detail/121541.html"
            "\n  Verify credentials: aliyun sts get-caller-identity\n" + "=" * 78 + "\n"
            "Credentials come from the CLI default chain only; never pass key "
            "material to the scripts.",
            file=sys.stderr,
        )
        sys.exit(1)


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
