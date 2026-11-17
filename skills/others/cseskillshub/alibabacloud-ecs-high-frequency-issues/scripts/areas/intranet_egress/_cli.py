#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation layer for ECS intranet / egress diagnosis
==============================================================================
SECURITY: Authentication is resolved exclusively by the aliyun CLI default
credential chain (the CLI's own profile configuration or the standard
platform-injected environment). This module NEVER reads, writes, caches or logs
any access key, secret or session token, and no script in this skill may accept
them as parameters. Error text returned by the CLI is passed through a
credential mask before it can reach any report or log line.

Every cloud query routed through here is a non-mutating Describe/Get call, and
there is no exception: this skill holds no mutating or execute-class API path,
and guest_command_gate.py makes no cloud call at all. In-guest evidence is
collected only by the customer, running the printed checklist by hand.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the entry scripts so that all Alibaba Cloud OpenAPI access goes through ONE
place, with identical timeout, retry, masking and observability behavior.

CLI-only transport
------------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as a
subprocess using an argument list (never shell=True):

    aliyun <product> <action> --param value ...

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
    aliyun ecs describe-instances --biz-region-id cn-hangzhou
    aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.

Transient-error retry
---------------------
Throttling / 5xx / timeout failures are transient and safe to retry: up to 3
attempts with linear backoff (2s, 4s). Non-transient failures (permission
denied, invalid parameter) are raised immediately.

Public API:
    call(product, action, params=None, region=..., timeout=...) -> dict
    paginate(...)                                             -> list
    check_cli_available()                                     -> None
    mask_credentials(text)                                    -> str
    session_id() / user_agent()                               -> str
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
# STS is a central (region-less) service, so the CLI is given the fixed
# endpoint and the identity pre-check never depends on the caller's default
# region. ecs / vpc resolve regional endpoints from the CLI's own metadata.
PRODUCT_ENDPOINTS: dict = {
    "sts": STS_ENDPOINT,   # sts.aliyuncs.com
}

_DEFAULT_REGION = "cn-hangzhou"

# Every product is served by the lowercase-hyphenated plugin command form
# (e.g. `aliyun sts get-caller-identity`); PascalCase API names are translated.
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
    """Convert a PascalCase API name to the kebab-case command form.

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
    """Return the CLI flag for a parameter name, honoring the product style."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY API call of that run as a User-Agent, so all calls belonging to one
# diagnosis can be correlated server-side.

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
            "This skill requires the Alibaba Cloud CLI to be installed and\n"
            "configured. Install guide: "
            "https://help.aliyun.com/document_detail/121541.html\n"
            "Verify it with: aliyun sts get-caller-identity -- the scripts never\n"
            "accept key material as arguments.\n"
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
    "statuscode: 5", "server error", "server busy",
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
# Credential masking (defense in depth for any error text that may surface in
# a report or a [WARN] line: the CLI network-error envelope embeds the signed
# request URL, whose query string carries key/token values).
# ---------------------------------------------------------------------------
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce|x-oss-credential|x-oss-signature)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Credentials can also arrive from INSIDE the instance rather than from the
# CLI: proxy environment variables legitimately print as
# http://user:secret@proxy:3128, and a request dump prints an auth header.
_URL_USERINFO_RE = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:([^/\s@]+)(@)")
_AUTH_HEADER_RE = re.compile(
    r"(?i)\b(authorization|x-api-key|x-ca-key|proxy-authorization)"
    r"(['\"]?\s*[=:]\s*)(?:basic|bearer|token)?\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential key/value pairs in CLI error text.

    Pure function, never raises. Each matched credential VALUE becomes ***
    while the key name is kept for diagnosability.
    """
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def mask_credentials(text: str) -> str:
    """Mask every known credential shape in one text, CLI error or not.

    Applied to guest command output as well as to CLI error envelopes, because
    the skill must never record a customer account credential. Pure; never
    raises; keeps key names and hosts so the text stays diagnosable.
    """
    if not text:
        return text or ""
    masked = _mask_credentials(text)
    masked = _URL_USERINFO_RE.sub(lambda m: f"{m.group(1)}***{m.group(3)}",
                                  masked)
    masked = _AUTH_HEADER_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}***",
                                 masked)
    return masked


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI codes, mask credential pairs, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the credential mask, executed on every import:
# a failure here means the mask is broken and raw CLI error text must not be
# allowed to reach any report.
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("nothing sensitive here") == "nothing sensitive here"
_envelope = (
    'GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=STS.fakekey1234'
    "&Action=DescribeInstances&SecurityToken="
    + "CAIS" + ("x" * 101)
    + '&Signature=abcd1234ef==&SignatureNonce=9e2f1" dial tcp: refused')
_masked = _clean_stderr(_envelope)
assert "STS.fakekey1234" not in _masked, _masked    # key id masked
assert ("x" * 101) not in _masked, _masked          # token masked
assert "abcd1234ef" not in _masked, _masked         # signature value masked
assert "AccessKeyId=***" in _masked
assert "SecurityToken=***" in _masked
_json_body = '{"AccessKeyId": "STS.fakekey", "SecurityToken": "CAISfake99"}'
assert "STS.fakekey" not in _clean_stderr(_json_body)
assert "CAISfake99" not in _clean_stderr(_json_body)
assert _clean_stderr(None) == ""
assert _clean_stderr("") == ""
# guest-side shapes: a proxy URL carrying credentials, and an auth header
_proxy_env = "https_proxy=http://svc-acct:s3cr3tPass@proxy.corp.example:3128"
assert "s3cr3tPass" not in mask_credentials(_proxy_env), _proxy_env
assert "proxy.corp.example:3128" in mask_credentials(_proxy_env)
assert "s3cr3tPass" not in _clean_stderr(_proxy_env)
_auth_line = "Proxy-Authorization: Basic dXNlcjpnMDAkcw=="
assert "dXNlcjpnMDAkcw==" not in mask_credentials(_auth_line), _auth_line
assert mask_credentials("Proxy-Authorization: ***") == \
    "Proxy-Authorization: ***"
# boundary: nothing sensitive must survive, and ordinary text must not change
assert mask_credentials("") == ""
assert mask_credentials(None) == ""
assert mask_credentials("curl: (28) Connection timed out after 8001 "
                        "milliseconds") == ("curl: (28) Connection timed out "
                                            "after 8001 milliseconds")
assert mask_credentials("egress ip: 192.0.2.1 via http://cip.cc") == \
    "egress ip: 192.0.2.1 via http://cip.cc"


# Shape guard for the legacy "ERROR: <Code>: <Message>" fallback line: only a
# letter-led alphanumeric token with optional dots counts as an API error code.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Handles the aliyun CLI failure envelope (StatusCode / Code / Message /
    Data lines) plus a bare JSON error body.
    """
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("ErrorCode:") or line.startswith("Code:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("Data:"):
            payload = line.split(":", 1)[1].strip()
            try:
                body = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(body, dict) and body.get("Code"):
                return str(body["Code"])
            continue
        if line.startswith("{"):
            try:
                body = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(body, dict) and body.get("Code"):
                return str(body["Code"])
        if line.startswith("ERROR:"):
            parts = line.split(":", 2)
            candidate = parts[1].strip() if len(parts) > 2 else ""
            return candidate if _ERROR_CODE_TOKEN_RE.match(candidate) else ""
    return ""


# ---------------------------------------------------------------------------
# Core invocation
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict] = None,
    region: str = _DEFAULT_REGION,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Invoke one Alibaba Cloud OpenAPI action via the aliyun CLI.

    Args:
        product:  Product code: "ecs", "vpc" or "sts".
        action:   API action name in PascalCase, e.g. "DescribeInstances".
                  Translated to the product's CLI command style internally.
        params:   Dict of request parameters (PascalCase keys); None values
                  are skipped.
        region:   Region id forwarded to the CLI for endpoint resolution.
        timeout:  Per-attempt subprocess timeout in seconds (MUST 7.6.1).

    Returns:
        Parsed JSON response as a dict.

    Raises:
        CliError: On failure. Transient errors (Throttling / 5xx / timeout) are
                  retried up to 3 attempts with linear backoff; permission and
                  parameter errors are raised immediately.
    """
    last_err: Optional[CliError] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, timeout)
        except CliError as e:
            last_err = e
            if not _is_retryable(e):
                raise
            if attempt >= _MAX_ATTEMPTS:
                raise CliError(
                    f"{product} {action} failed after {attempt} attempts: {e}",
                    code=e.code, stderr=e.stderr,
                )
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({e.code or 'unknown'}); retry {attempt}/"
                f"{_MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps the return type honest


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


def _call_cli(
    product: str,
    action: str,
    params: Optional[dict],
    region: str,
    timeout: int,
) -> dict:
    """Execute one CLI invocation using an argument list, never shell=True."""
    cmd = ["aliyun"] + _command_tokens(product, action)

    endpoint = PRODUCT_ENDPOINTS.get(product)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    cmd += ["--region", region]

    # Observability: one 32-hex session-id User-Agent shared by every call.
    cmd += ["--user-agent", user_agent()]

    cmd += _list_param_argv(action, params, lambda key: _param_flag(product, key), _param_text)

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
        body = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")
    if not isinstance(body, dict):
        raise CliError(f"aliyun {product} {action} returned a non-object body")
    return body


# ---------------------------------------------------------------------------
# Paging helper for the RPC Describe* list APIs
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list) -> Any:
    """Walk a nested dict along `path`; return None on any miss."""
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _unwrap_items(items: Any) -> list:
    """Tolerate both a bare list and the {"Item": [...]} wrapped shape."""
    if items is None:
        return []
    if isinstance(items, dict):
        inner = items.get("Item")
        if isinstance(inner, list):
            return inner
        if not inner:
            return []
        return [inner]
    if isinstance(items, list):
        return items
    return []


def paginate(
    product: str,
    action: str,
    params: dict,
    list_path: list,
    mode: str = "pagenum",
    total_path: Optional[list] = None,
    page_size_key: str = "MaxResults",
    region: str = _DEFAULT_REGION,
    timeout: int = DEFAULT_TIMEOUT,
    max_pages: int = MAX_PAGES,
    page_size: int = PAGE_SIZE,
) -> list:
    """Collect all pages of one paginated RPC Describe* query.

    Two paging styles are supported, selected by `mode`:
      * mode="token"   -- NextToken style: a non-empty response NextToken
        continues the loop; the per-page size flag is `page_size_key`.
      * mode="pagenum" -- PageNumber style: increments PageNumber until the
        collected count reaches the total (when `total_path` is given) or a
        page comes back empty.

    `list_path` locates the item list in the response body. The page guardrail
    keeps the loop bounded in both modes.
    """
    all_items: list = []
    next_token: Optional[str] = None
    page = 1
    while page <= max_pages:
        page_params = dict(params)
        if mode == "token":
            page_params[page_size_key] = page_size
            if next_token:
                page_params["NextToken"] = next_token
        else:
            page_params["PageNumber"] = page
            page_params["PageSize"] = page_size
        body = call(product, action, page_params, region=region, timeout=timeout)
        items = _unwrap_items(_dig(body, list_path))
        all_items.extend(items)

        if mode == "token":
            next_token = body.get("NextToken") or None
            if not next_token:
                break
            page += 1
            continue

        total = _dig(body, total_path) if total_path else None
        try:
            total_n = int(total) if total is not None else None
        except (TypeError, ValueError):
            total_n = None
        if not items:
            break
        if total_n is not None and len(all_items) >= total_n:
            break
        page += 1
    else:
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
