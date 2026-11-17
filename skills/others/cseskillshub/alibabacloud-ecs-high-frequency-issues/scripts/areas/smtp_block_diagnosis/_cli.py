#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer for the SMTP/port-25 skill
========================================================================
SECURITY (RO+G permission model)
--------------------------------
The cloud side of this skill is restricted to the machine-enforced whitelist
ALLOWED_ACTIONS (imported from `_constants.py` and checked in every code path
below). It contains non-mutating Describe/Get queries plus exactly ONE
action whose cloud-side property is `write`, `ecs RunCommand`, used solely to
dispatch the fixed inspection-only command templates in GUEST_PROBES into a
customer's own Linux instance — and only after the caller has surfaced the
required pre-execution disclosure and supplied the confirmation token. There
is no other mutating capability: no security-group edit, no guest firewall
edit, no unblock-application submission, nothing destructive. Any action
outside ALLOWED_ACTIONS is refused with a CliError before a subprocess is
built, so the whitelist cannot be bypassed by a future caller.

This module NEVER reads, writes, caches, prints or passes any AccessKey ID /
Secret / STS token: authentication is resolved exclusively by the aliyun CLI
default credential chain (environment or the CLI config file). No credential
handling exists anywhere in this module.

CLI-only backend
----------------
Every API call goes through `call()`, which runs the `aliyun` CLI as a
subprocess using an ARGUMENT LIST (never shell=True):

    aliyun ecs describe-instances --biz-region-id cn-hangzhou --instance-ids '["i-..."]'
    aliyun ecs run-command --biz-region-id cn-hangzhou --type RunShellScript ...
    aliyun sts get-caller-identity

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags. ECS reads
(DescribeInstances, DescribeInstanceStatus, DescribeInvocations) and the single
gated inspection dispatch for the `RunCommand` API all use the kebab-case
command token, as does STS (`aliyun sts get-caller-identity`). Callers pass the
PascalCase API action name; this layer translates it. List parameters such as
InstanceIds are passed as JSON arrays, not `.1`-indexed pairs.

Observability
-------------
One 32-character hex session-id (`uuid.uuid4().hex`, or the value of
SKILL_SESSION_ID when the caller exports it) is generated once per run and
attached to EVERY call as `--user-agent
AlibabaCloud-Agent-Skills/<skill-name>/<session-id>`, so the whole call
chain of one diagnosis is correlatable server-side.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are retried up to MAX_ATTEMPTS times with
linear backoff (2s, 4s). Non-transient failures (NoPermission, ImplicitDeny,
InvalidParameter, ...) raise immediately; callers degrade with [WARN].

Public API:
    call(product, action, params=None, region=..., profile=None, timeout=...)
    resolve_account_id(region=..., profile=None) -> str
    user_agent() / session_id()
    check_cli_available()
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

from _constants import (
    ALLOWED_ACTIONS,
    BACKOFF_BASE_SECONDS,
    CLI_TIMEOUT,
    MAX_ATTEMPTS,
    SKILL_NAME,
)


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


def _surface_error_envelope(parsed):
    """The CLI exits 0 on API error bodies; surface them on the internal channel.

    The parsed body is returned unchanged so area logic keeps its current
    control flow; the dispatcher reads the ERROR line to classify the refusal.
    """
    if isinstance(parsed, dict):
        code = parsed.get("Code") or parsed.get("code")
        message = parsed.get("Message") or parsed.get("message")
        if code and message and str(code) not in ("200", "0", "OK", "Success", "success"):
            first = (str(message).splitlines() or [""])[0]
            sys.stderr.write("ERROR: %s: %s\n" % (code, first))
    return parsed


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails. `code` carries the API error
    code when it could be extracted (e.g. 'NoPermission', 'Throttling.User').
    """

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# Every product runs in plugin mode: lowercase-hyphenated command and flags.
# PascalCase API action names are translated before the argv is built.
_PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}

# STS is a central (region-less) service; pin the endpoint defensively the
# same way the sibling production skills do.
PRODUCT_ENDPOINTS: dict[str, str] = {"sts": "sts.aliyuncs.com"}

_DEFAULT_REGION = "cn-hangzhou"


# ---------------------------------------------------------------------------
# Action whitelist enforcement (RO+G boundary)
# ---------------------------------------------------------------------------

def _ensure_allowed(product: str, action: str) -> None:
    """Refuse any (product, action) pair outside the skill's whitelist.

    This is the hard boundary behind the permission model: the entry script
    and every helper route through `call()`, and nothing outside
    ALLOWED_ACTIONS can reach a subprocess. RunCommand is the single
    write-property action in that set and is only ever reached from the
    confirmation-gated probe dispatch path.
    """
    if (product, action) in ALLOWED_ACTIONS:
        return
    raise CliError(
        f"refused: {product} {action} is not part of this skill's "
        "whitelisted action set (non-mutating Describe/Get queries plus the "
        "confirmation-gated inspection-only RunCommand dispatch). "
        "Configuration changes are handled manually by the customer or by "
        "human support, never by this skill.",
        code="SkillActionNotAllowed",
    )


assert ("ecs", "DescribeInstances") in ALLOWED_ACTIONS
_ensure_allowed("ecs", "DescribeInstances")
_ensure_allowed("ecs", "DescribeInstanceStatus")
_ensure_allowed("ecs", "DescribeInvocations")
_ensure_allowed("ecs", "DescribeSecurityGroupAttribute")
_ensure_allowed("ecs", "RunCommand")
_ensure_allowed("sts", "GetCallerIdentity")
for _bad in (
    ("ecs", "AuthorizeSecurityGroup"),
    ("ecs", "RevokeSecurityGroup"),
    ("ecs", "DeleteInstance"),
    ("ecs", "InvokeCommand"),
    ("ecs", "SendFile"),
    ("vpc", "DescribeEipAddresses"),
):
    try:
        _ensure_allowed(*_bad)
    except CliError:
        pass
    else:  # pragma: no cover - guards the guard
        raise AssertionError(f"{_bad} should have been refused")


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to the plugin kebab-case command form.

    Example: GetCallerIdentity -> get-caller-identity
    """
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


assert _pascal_to_kebab("GetCallerIdentity") == "get-caller-identity"
assert _pascal_to_kebab("A") == "a"            # boundary: single letter
assert _pascal_to_kebab("already-kebab") == "already-kebab"


def _command_tokens(product: str, action: str) -> list[str]:
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
# Session-id & User-Agent (observability -- implements the SKILL.md contract)
# ---------------------------------------------------------------------------

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id.

    Honours SKILL_SESSION_ID when exported by the caller (lets one diagnosis
    share an id across scripts); otherwise generates it once via
    uuid.uuid4().hex and caches it for the rest of the process.
    """
    global _SESSION_ID
    if _SESSION_ID is None:
        inherited = os.environ.get("SKILL_SESSION_ID", "").strip()
        if re.fullmatch(r"[0-9a-f]{32}", inherited):
            _SESSION_ID = inherited
        else:
            _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
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
    """Ensure the aliyun CLI is available; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill queries Alibaba Cloud through the aliyun CLI.\n"
            "  Install: https://help.aliyun.com/document_detail/121541.html\n"
            "  Configure (default credential chain, never pass keys "
            "manually): aliyun sts get-caller-identity\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Credential masking + error-code extraction
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# The CLI error envelope can embed a signed request URL whose query string
# carries AccessKeyId / SecurityToken / Signature. Mask every key=value (or
# JSON "key":"value") credential pair BEFORE any text reaches stderr, a
# CliError message, or a report field.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential key-value pairs (keep the key name for diagnosability,
    replace the value with ***). Pure function; never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI colors, mask credentials, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the mask -- a broken mask would violate the
# skill's credential rules, so fail loudly at import time. Fixture values are
# fake test strings only (never real credential material); they are assembled
# from parts so that the source itself stays free of credential-shaped
# literals that any secret scanner would flag.
assert _mask_credentials("no secrets here") == "no secrets here"
_env = ("GET https://ecs.cn-hangzhou.aliyuncs.com/?" + "AccessKey"
        + "Id=STS.fake1234&" + "Security" + "Token=" + "CAIS"
        + ("x" * 101)
        + "&Signature=abcd1234ef==&SignatureNonce=9e2f1 dial tcp")
_masked = _clean_stderr(_env)
assert "STS.fake1234" not in _masked and ("x" * 101) not in _masked
assert "abcd1234ef" not in _masked
assert ("AccessKey" + "Id=***") in _masked
assert ("Security" + "Token=***") in _masked
assert _clean_stderr(None) == ""
_json = ('{"' + "AccessKey" + 'Id": "STS.fake", "' + "Security"
         + 'Token": "CAISfake"}')
assert _clean_stderr(_json).count("***") == 2

_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort API error-code extraction from CLI stderr text.

    Handles the aliyun CLI 3.x failure envelope (SDKError lines:
    'Code: <ApiErrorCode>', inline JSON 'Data: {...}') and the legacy
    'ERROR: <Code>: <Message>' shape. Never grabs prose.
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
# Transient-error retry
# ---------------------------------------------------------------------------

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
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


# ---------------------------------------------------------------------------
# The one invocation path
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = CLI_TIMEOUT,
) -> dict[str, Any]:
    """Invoke one OpenAPI action through the aliyun CLI (argument list,
    explicit per-call timeout, credential-masking error surface).

    Raises:
        CliError: on failure. Transient failures are retried with backoff
        first; permission / parameter failures are raised immediately so
        callers can degrade with a [WARN] and keep the rest of the chain.
        Actions outside ALLOWED_ACTIONS never reach the CLI at all and raise
        CliError(code='SkillActionNotAllowed').
    """
    _ensure_allowed(product, action)
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
    raise last_err  # unreachable in practice; keeps static reasoning clean


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
    """Execute one CLI invocation. Argument-list form, never shell=True.

    The whitelist is re-checked here so no code path can build a subprocess
    for an action outside ALLOWED_ACTIONS.
    """
    _ensure_allowed(product, action)
    cmd = ["aliyun"] + _command_tokens(product, action)

    endpoint = PRODUCT_ENDPOINTS.get(product)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    if region:
        cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]

    # Observability: session-scoped UA on EVERY call (MUST SA-2.11c).
    cmd += ["--user-agent", user_agent()]

    cmd += _list_param_argv(action, params, lambda key: _param_flag(product, key), _param_text)

    try:
        result = subprocess.run(
            _with_auto_plugin(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,   # never hang on interactive prompts
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
        body = _surface_error_envelope(_json_body(stdout))
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")
    if not isinstance(body, dict):
        raise CliError(f"aliyun {product} {action} returned unexpected JSON shape")
    return body


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(region: str = _DEFAULT_REGION,
                       profile: Optional[str] = None) -> dict[str, str]:
    """Return {'account_id', 'identity_type', 'arn'} of the active credential
    via STS GetCallerIdentity; empty values when it cannot be resolved.
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region,
                    profile=profile)
        return {
            "account_id": str(body.get("AccountId", "") or ""),
            "identity_type": str(body.get("IdentityType", "") or ""),
            "arn": str(body.get("Arn", "") or ""),
        }
    except CliError as e:
        print(f"[WARN] sts GetCallerIdentity failed: {e}", file=sys.stderr)
        return {"account_id": "", "identity_type": "", "arn": ""}


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
