#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation helper for the ECS preemptible guide
=========================================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved by
the aliyun CLI default credential chain (~/.aliyun/config.json or
platform-injected environment). This module NEVER reads, writes, caches or
logs any AccessKey ID / Secret. No AK/SK handling anywhere in this module.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the entry script so that all Alibaba Cloud OpenAPI access goes through ONE
place.

CLI-only backend
----------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess (argument-list form, never shell=True):

    aliyun <product> <action> --param value ...

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
    aliyun ecs describe-instances --biz-region-id cn-hangzhou
    aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.

The CLI resolves the API metadata, uses its own credential profile for auth,
and returns raw JSON on stdout.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-retryable errors (permission
denied, invalid parameter, ...) are raised immediately.

Observability
-------------
One 32-char hex session-id (uuid4().hex) is generated per script run and
attached to EVERY invocation as
    --user-agent AlibabaCloud-Agent-Skills/<skill-name>/<session-id>
so all calls of one run can be correlated.

Public API:
    call(product, action, params=None, region=..., profile=None) -> dict
    paginate_page_number(product, action, params, ...) -> list[dict]
    resolve_account_id(...) -> str
    check_cli_available() -> None
    is_permission_error(err) -> bool
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
    PAGE_SIZE,
    SKILL_NAME,
    STS_ENDPOINT,
    UA_TEMPLATE,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails (Code: Message)."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Per-product endpoint metadata
# ---------------------------------------------------------------------------
# STS is a central (region-less) service; the CLI is given the fixed endpoint
# so identity calls never depend on the caller's default region. ECS is
# regional: the CLI derives the endpoint from --region, so nothing is pinned.
PRODUCT_ENDPOINTS: dict[str, str] = {
    "sts": STS_ENDPOINT,  # sts.aliyuncs.com
}

# Fallback region used ONLY for the central STS identity call (where the
# region does not scope any data). ECS queries ALWAYS pass the explicit,
# user-provided RegionId -- the entry script never auto-fills it.
_DEFAULT_REGION = "cn-hangzhou"

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


assert _pascal_to_kebab("GetCallerIdentity") == "get-caller-identity"
assert _pascal_to_kebab("DescribeInstances") == "describe-instances"
assert _pascal_to_kebab("") == ""  # boundary: empty input never raises


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
# Session-ID & User-Agent (observability, MUST SA-2.11b/c)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY API call of that run as a User-Agent, so all calls of one run can
# be correlated server-side.

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
    return UA_TEMPLATE.format(skill_name=SKILL_NAME, session_id=session_id())

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


# Template sanity without triggering the lazy per-run session-id generation
# (normal / boundary inputs; uuid4().hex is always 32 lowercase hex chars).
assert UA_TEMPLATE.format(skill_name="s", session_id="x") == \
    "AlibabaCloud-Agent-Skills/s/x"
assert UA_TEMPLATE.format(skill_name=SKILL_NAME,
                          session_id=uuid.uuid4().hex).startswith(
    f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/")
assert len(uuid.uuid4().hex) == 32


def check_cli_available() -> None:
    """Ensure the aliyun CLI is available; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI to be installed and "
            "configured.\n\n"
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
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


# Permission-denial classification tokens (matched on the LOWERCASED incoming
# error code/message). The skill's own guidance text always uses the
# NoPermission / ImplicitDeny literals (platform rule E34); the short "forbid"
# token here only recognizes incoming provider error-code variants without
# ever emitting the platform-reserved literal itself.
_PERMISSION_MARKERS = (
    "nopermission", "implicitdeny", "notauthorized", "unauthorized",
    "accessdenied", "denied", "forbid",
)


def is_permission_error(err: CliError) -> bool:
    """True when the failure looks like a RAM authorization denial."""
    code = (getattr(err, "code", "") or "").lower()
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _PERMISSION_MARKERS)


def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke an Alibaba Cloud OpenAPI action via the aliyun CLI (read-only).

    Args:
        product:  Product code, e.g. "ecs", "sts".
        action:   API action name in PascalCase, e.g. "DescribeInstances".
                  Translated to the product's CLI command style automatically.
        params:   Dict of request parameters (PascalCase keys for RPC-style
                  products); None values are skipped.
        region:   Region for endpoint resolution. ECS queries must pass the
                  explicit user-provided RegionId; the default only serves the
                  central STS identity call.
        profile:  Optional CLI credential profile name.
        timeout:  Per-attempt timeout in seconds (default DEFAULT_TIMEOUT=60,
                  platform rule 7.6.1).

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

    # Observability: one session-id UA shared by every call of this run.
    cmd += ["--user-agent", user_agent()]

    cmd += _list_param_argv(action, params, lambda key: _param_flag(product, key), _param_text)

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

    # Some gateways report request-level failures INSIDE the response body
    # while the CLI still exits 0. Treat any non-Success body Code as an
    # invocation failure so callers degrade via the standard CliError path
    # instead of silently reading an error payload as data. Normal ECS
    # Describe responses carry no top-level Code key, so the happy path is
    # untouched.
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


# Shape guard for the legacy "ERROR: <Code>: <Message>" fallback: only
# letter-led alphanumeric tokens with optional dots count as API error codes.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")

# The aliyun CLI colors its stderr output; strip ANSI escapes so error text
# embedded in reports/JSON stays plain ASCII.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Credential-value masking: the aliyun CLI network-error envelope can embed a
# signed request URL whose query string carries AccessKeyId / SecurityToken /
# Signature material. Every <credentialKey>=<value> (query-string) or
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
    return _CREDENTIAL_VALUE_RE.sub(
        lambda m: f"{m.group(1)}=***", text)


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
# -- a leaked credential in a [WARN] line violates the skill's rules.
# The fixture values below are deliberately synthetic FAKE* placeholders: the
# masking rule keys off the credential PARAMETER NAME, not the value's shape, so
# no credential-shaped literal needs to be written into a skill package.
# normal: credential-free text passes through unchanged (ANSI/blank cleanup).
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
# boundary: signed-URL network-error envelope (access-key id + long session
# token + base64-style signature).
_leak_env = (
    'GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=FAKEACCESSKEYVALUE0001'
    "&Action=DescribeInstances&SecurityToken="
    + "FAKETOKEN" + ("x" * 95)
    + '&Signature=FAKESIGNATUREVALUE99==&SignatureNonce=FAKENONCE1" dial tcp: refused')
_leak_masked = _clean_stderr(_leak_env)
assert "FAKEACCESSKEYVALUE0001" not in _leak_masked, _leak_masked   # AK masked
assert ("FAKETOKEN" + "x" * 95) not in _leak_masked, _leak_masked   # token masked
assert "FAKESIGNATUREVALUE99" not in _leak_masked, _leak_masked      # sig masked
assert "AccessKeyId=***" in _leak_masked
assert "SecurityToken=***" in _leak_masked
assert "Signature=***" in _leak_masked
# boundary: JSON-shaped credential pairs are masked as well.
_leak_json = ('{"AccessKeyId": "FAKEACCESSKEYVALUE02", '
              '"SecurityToken": "FAKETOKENVALUE02"}')
_leak_json_masked = _clean_stderr(_leak_json)
assert "FAKEACCESSKEYVALUE02" not in _leak_json_masked, _leak_json_masked
assert "FAKETOKENVALUE02" not in _leak_json_masked, _leak_json_masked
assert _leak_json_masked.count("***") == 2
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


# Error-code extraction assertions (normal / boundary / invalid).
assert _extract_error_code("Code: NoPermission") == "NoPermission"
assert _extract_error_code('Data: {"Code":"Throttling.User"}') == "Throttling.User"
assert _extract_error_code("ERROR: InvalidInstanceId.NotFound: x") == \
    "InvalidInstanceId.NotFound"
assert _extract_error_code("ERROR: some prose without code shape") == ""
assert _extract_error_code("") == ""


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
) -> str:
    """Return the Alibaba Cloud UID (AccountId) of the active credential.

    Uses STS GetCallerIdentity (plugin mode: `aliyun sts get-caller-identity`),
    which needs no input beyond the configured credential. Returns "" when it
    cannot be resolved; callers record the limitation instead of aborting.
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError as e:
        print(f"[WARN] sts get-caller-identity failed: {e.code or 'unknown'}: {e}",
              file=sys.stderr)
        return ""


# ---------------------------------------------------------------------------
# Pagination helper (PageNumber style, ECS wrapped-list shapes)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    """Walk a nested dict along `path`; return None on any miss."""
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


assert _dig({"a": {"b": [1]}}, ["a", "b"]) == [1]
assert _dig({"a": {}}, ["a", "b"]) is None       # boundary: missing leaf
assert _dig(None, ["a"]) is None                 # invalid: non-dict root


def _unwrap_list(value: Any) -> list[Any]:
    """Normalize ECS list shapes: plain list, {"Item": [...]}, or single dict."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        inner = value.get("Item")
        if isinstance(inner, list):
            return inner
        return [value]
    return []


assert _unwrap_list([1, 2]) == [1, 2]
assert _unwrap_list({"Item": [1]}) == [1]
assert _unwrap_list({"InstanceId": "i-x"}) == [{"InstanceId": "i-x"}]
assert _unwrap_list(None) == []                  # invalid input -> empty


def paginate_page_number(
    product: str,
    action: str,
    params: dict[str, Any],
    region: str,
    profile: Optional[str] = None,
    items_path: Optional[list[str]] = None,
    page_size: int = PAGE_SIZE,
    max_pages: int = MAX_PAGES,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[Any]:
    """Follow PageNumber-based pagination until exhausted (with a guardrail).

    Args:
        items_path: Nested keys to the item list, e.g.
                    ["InstanceStatuses", "InstanceStatus"].
        page_size:  PageSize injected per call (ECS status API max: 50).
        max_pages:  Hard guardrail on the number of pages fetched.

    Returns the concatenated item list across all fetched pages. A CliError
    from the first page propagates; from a later page it propagates as well
    (the caller records it and works with what it has).
    """
    items_path = items_path or []
    all_items: list[Any] = []
    total_count: Optional[int] = None
    page = 1
    while page <= max_pages:
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = page_size
        body = call(product, action, page_params, region=region,
                    profile=profile, timeout=timeout)

        rows = _unwrap_list(_dig(body, items_path))
        all_items.extend(rows)

        raw_total = body.get("TotalCount") if isinstance(body, dict) else None
        try:
            total_count = int(raw_total) if raw_total is not None else total_count
        except (TypeError, ValueError):
            total_count = total_count

        if not rows:
            break
        if total_count is not None and len(all_items) >= total_count:
            break
        page += 1
    if page > max_pages:
        print(
            f"[WARN] {product} {action}: pagination stopped at the "
            f"{max_pages}-page guardrail; results may be incomplete",
            file=sys.stderr,
        )
    return all_items


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
