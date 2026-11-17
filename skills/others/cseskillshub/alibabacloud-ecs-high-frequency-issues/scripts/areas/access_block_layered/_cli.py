#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer
=============================================
SECURITY: authentication is resolved exclusively by the aliyun CLI default
credential chain (environment or ~/.aliyun/config.json). This module never
reads, prints, caches or passes any AccessKey ID / Secret / token, and it
never writes a credential file. All commands are built as argument lists and
executed with subprocess.run( ..., shell=False ) and a per-call timeout.

Every API call goes through ONE place so the guarantees below cannot be
bypassed:
  * per-call timeout                     (platform rule 7.6.1)
  * observability User-Agent on the call (platform rule SA-2.11c)
  * transient-error retry with backoff
  * credential masking of all error text (platform rule SA-2.12 hygiene)

Command style per product (verified against aliyun CLI 3.4.5 plugin metadata):
every product below runs in plugin mode, lowercase-hyphenated commands and flags:
  * ecs         aliyun ecs describe-instances --biz-region-id ...
  * sts         aliyun sts get-caller-identity
  * cloudfw     aliyun cloudfw describe-control-policy --current-page ...
  * waf-openapi aliyun waf-openapi describe-instance --biz-region-id ...
Callers pass the PascalCase API action name; this layer translates it.

Public API:
    call(product, action, params=None, region=..., profile=None, timeout=...)
    paginate_page_number(...)
    resolve_account_id(...)
    check_cli_available()
    session_id() / user_agent()
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
    CLI_TIMEOUT_SECONDS,
    DEFAULT_REGION,
    MAX_PAGES,
    PLUGIN_STYLE_PRODUCTS,
    SKILL_NAME,
    UA_PREFIX,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails. Carries Code: Message text."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Session-id & User-Agent (observability, SA-2.11c)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run (lazily) and
# attached to EVERY CLI call of that run, so the whole diagnosis is traceable:
#   User-Agent: AlibabaCloud-Agent-Skills/<skill-name>/<32-hex-session-id>

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
    return _SESSION_ID


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


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return _ua_normalize(f"{UA_PREFIX}/{SKILL_NAME}/{session_id()}") + " skill-version/" + _SKILL_VERSION


# ---------------------------------------------------------------------------
# Command / flag style helpers
# ---------------------------------------------------------------------------

def _pascal_to_kebab(name: str) -> str:
    """PascalCase -> lowercase-hyphenated (GetCallerIdentity -> get-caller-identity)."""
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list[str]:
    """CLI command tokens for (product, action), honoring command style."""
    if product in PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    """CLI flag name for a parameter, honoring command style."""
    if product in PLUGIN_STYLE_PRODUCTS:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


def check_cli_available() -> None:
    """Ensure the aliyun CLI exists; exit with clear guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 72 + "\n"
            " aliyun CLI not found\n" + "=" * 72 + "\n"
            "This skill runs all cloud queries through the Alibaba Cloud CLI.\n"
            "Install it, then verify the default credential chain with\n"
            "`aliyun sts get-caller-identity`. Never pass credentials to the tools.\n"
            "Installation guide: https://help.aliyun.com/document_detail/121541.html\n"
            + "=" * 72,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Transient-error retry
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 2  # retry N waits N * 2s (2s, 4s)

_RETRY_CODES = {
    "throttling", "throttling.user", "throttling.api",
    "serviceunavailable", "internalerror", "sdk.httperror", "unknownerror",
}
_RETRY_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal error",
    "http 500", "http 502", "http 503", "http 504", "statuscode: 5",
    "server busy", "connection reset", "timed out", "timeout",
    "temporarily unavailable", "service unavailable",
)


def _is_retryable(err: CliError) -> bool:
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {err}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


# ---------------------------------------------------------------------------
# Credential masking + stderr cleanup
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# CLI network-error envelopes can embed a signed request URL whose query
# string carries AccessKeyId / SecurityToken / Signature. Mask every such
# key=value (query style) or "key":"value" (JSON style) pair before the text
# can reach a [WARN] line, a CliError message or a JSON output field.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce|x-oss-credential|x-oss-signature)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")

_PASSWORD_VALUE_RE = re.compile(
    r"(?i)\b(password|passwd|instancepassword)\b\s*[=:]\s*['\"]?\S+")


def _mask_credentials(text: str) -> str:
    """Mask credential/password key-value pairs in error text. Never raises."""
    if not text:
        return text or ""
    text = _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)
    text = _PASSWORD_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)
    return text


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI codes, mask credentials, collapse blank runs. The single
    choke point every CLI stderr passes through."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Boundary assertions for the mask: a broken mask would leak a session
# credential into a report line, which the skill rules forbid.
assert _mask_credentials("no secrets here") == "no secrets here"
_probe = ("AccessKeyId=STS.NYfake1234567890&SecurityToken=" + "y" * 120 +
          '&Signature=sig123==" password= p@ssw0rd! x')
_masked = _mask_credentials(_probe)
assert "STS.NYfake1234567890" not in _masked
assert ("y" * 120) not in _masked
assert "sig123" not in _masked
assert "p@ssw0rd!" not in _masked
assert _clean_stderr(None) == ""


_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Handles the aliyun CLI 3.x failure envelope:
        Error: request execution failed: ... SDKError:
           StatusCode: 403
           Code: NoPermission
           Message: ...
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
# The one invocation entry point
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = CLI_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Invoke one OpenAPI action through the aliyun CLI (argument list only).

    Transient failures (throttling / 5xx / timeout) are retried up to 3
    attempts with linear backoff. Other failures raise CliError immediately.
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
                    f"aliyun {product} {action} failed after {attempt} attempts: {e}",
                    code=e.code, stderr=e.stderr)
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({e.code or 'unknown'}); retry {attempt}/{_MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # unreachable; keeps type checkers satisfied


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
    cmd = ["aliyun"] + _command_tokens(product, action)
    cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]
    # Observability: the same session-id UA on every call of this run.
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
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")
    if not isinstance(body, dict):
        raise CliError(f"aliyun {product} {action} returned unexpected JSON shape")
    return body


# ---------------------------------------------------------------------------
# Pagination helper (PageNumber/PageSize style used by ECS security-group
# rule queries and Cloud Firewall policy queries)
# ---------------------------------------------------------------------------

def paginate_page_number(
    product: str,
    action: str,
    params: dict[str, Any],
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    items_path: Optional[list[str]] = None,
    page_size: int = 50,
    max_pages: int = MAX_PAGES,
) -> list[Any]:
    """Follow PageNumber/PageSize pagination; return all items found.

    items_path walks the response JSON, e.g. ["Permissions", "Permission"].
    """
    items_path = items_path or []
    all_items: list[Any] = []
    page = 1
    while page <= max_pages:
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = page_size
        body = call(product, action, page_params, region=region, profile=profile)
        node: Any = body
        for key in items_path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if isinstance(node, dict):
            # tolerate wrapped {"Item": [...]} shapes
            for value in node.values():
                if isinstance(value, list):
                    node = value
                    break
        if isinstance(node, list):
            all_items.extend(node)
            if len(node) < page_size:
                break
        else:
            break
        page += 1
    else:
        print(
            f"[WARN] {product} {action}: pagination stopped at the {max_pages}-page "
            "guardrail; results may be incomplete",
            file=sys.stderr,
        )
    return all_items


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(region: str = DEFAULT_REGION, profile: Optional[str] = None) -> str:
    """Return the account UID behind the active CLI credential ('' on failure)."""
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
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
