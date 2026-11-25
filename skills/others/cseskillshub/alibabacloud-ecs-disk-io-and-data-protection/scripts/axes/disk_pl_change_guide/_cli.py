#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer for the disk PL change guide
==========================================================================
SECURITY: This module mutates no cloud resource. All authentication is
resolved by the aliyun CLI default credential chain (environment or
~/.aliyun/config.json). This module NEVER reads, writes, caches or logs any
AccessKey ID / Secret; there is no AK/SK handling anywhere. Callers invoke
the whitelisted Describe / List / Get queries, plus RunCommand -- used only to
dispatch ONE allowlisted non-mutating guest diagnostic command after the
customer was told what runs and confirmed that single call.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
disk_pl_advisor.py and sts_token.py so that all Alibaba Cloud OpenAPI access
goes through ONE place.

CLI-only transport
------------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess (argument-list form, never shell=True, always with a timeout):

    aliyun <product> <action> --param value ...

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
    aliyun ecs describe-disks --biz-region-id cn-hangzhou ...
    aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.

Transient-error retry
---------------------
Throttling / 5xx / timeout errors are transient and safe to retry: up to 3
attempts total with linear backoff (2s, 4s). Non-retryable errors (permission
denied, invalid parameter, ...) are raised immediately.

Observability
-------------
A 32-character hex session-id (uuid4().hex) is generated once per script run
and attached to EVERY CLI call of that run as
`--user-agent AlibabaCloud-Agent-Skills/<skill-name>/<session-id>`.

Public API:
    call(product, action, params, region, profile, timeout) -> dict
    paginate_next_token(...) / paginate_page_number(...) -> list
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

from _constants import (
    DEFAULT_TIMEOUT,
    MAX_PAGES,
    MAX_RESULTS,
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

# Plugin-mode region refusal: the CLI names the flag it wants; supply it from
# the region the call already carries - once, and only for this exact refusal.
_REGION_FLAG_REQUIRED_RES = (
    re.compile(r"missing required parameter\(s\):\s*--biz-region-id"),
    re.compile(r"--biz-region-id is required"),
)


def _region_flag_retry(cmd, stderr, region=None):
    """The same call with the plugin's region parameter, or None if not applicable."""
    if "--biz-region-id" in cmd:
        return None
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", "replace")
    if not any(pattern.search(stderr or "") for pattern in _REGION_FLAG_REQUIRED_RES):
        return None
    if not region:
        for flag in ("--RegionId", "--region-id", "--region"):
            if flag in cmd:
                index = cmd.index(flag)
                if index + 1 < len(cmd):
                    region = cmd[index + 1]
                    break
    if not region:
        return None
    return list(cmd) + ["--biz-region-id", region]


def _run_with_region_retry(cmd, timeout=None, **kwargs):
    """subprocess.run with one plugin-region refusal retry; same exceptions."""
    completed = subprocess.run(_with_auto_plugin(cmd), timeout=timeout, **kwargs)
    if completed.returncode != 0:
        retry = _region_flag_retry(cmd, completed.stderr or "")
        if retry is not None:
            completed = subprocess.run(_with_auto_plugin(retry), timeout=timeout, **kwargs)
    return completed


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
    """Raised when an OpenAPI invocation fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# Every product runs in plugin mode: lowercase-hyphenated command and flags,
#     e.g. `aliyun ecs describe-disks --biz-region-id cn-hangzhou`
#     and `aliyun sts get-caller-identity`. PascalCase API action names are
#     translated by _pascal_to_kebab before the argv is built.
_PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to the plugin kebab-case command form.

    Example: GetCallerIdentity -> get-caller-identity
    """
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


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
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------

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
# Credential masking (never let a signed URL / token leak into reports)
# ---------------------------------------------------------------------------
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce|x-oss-credential|x-oss-signature)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential key-value pairs in CLI error text.

    Pure function; replaces each matched credential VALUE with *** while
    keeping the key name for diagnosability. Never raises.
    """
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI codes, MASK CREDENTIALS and collapse blank runs in CLI
    stderr text -- the single choke point every stderr passes through."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the credential masking, executed on every
# import: a failure here means the mask is broken and the module must not run.
assert _clean_stderr("Error: request failed: connection refused") == \
    "Error: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
_env = (
    'GET "https://ecs.cn-hangzhou.aliyuncs.com/?AccessKeyId=STS.NYfakeKey1'
    "&Action=DescribeDisks&SecurityToken=" + "CAIS" + ("x" * 101) +
    '&Signature=abcd1234ef==&SignatureNonce=9e2f1" dial tcp: refused')
_masked = _clean_stderr(_env)
assert "STS.NYfakeKey1" not in _masked
assert ("x" * 101) not in _masked
assert "abcd1234ef" not in _masked
assert "AccessKeyId=***" in _masked and "SecurityToken=***" in _masked
_json = '{"AccessKeyId": "STS.NYfake", "SecurityToken": "CAISfake99"}'
_json_masked = _clean_stderr(_json)
assert "STS.NYfake" not in _json_masked
assert "CAISfake99" not in _json_masked
assert _json_masked.count("***") == 2
assert _clean_stderr(None) == ""
assert _clean_stderr("") == ""


# Shape guard for the legacy "ERROR: <Code>: <Message>" fallback: only
# letter-led alphanumeric tokens with optional dots count as API error codes.
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Handles the aliyun CLI 3.x failure envelope:

        Error: request execution failed: ... SDKError:
           StatusCode: 403
           Code: NoPermission
           Message: You are not authorized ...
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
# The one CLI invocation path
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: Optional[str] = None,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke one Alibaba Cloud OpenAPI action via the aliyun CLI.

    Args:
        product:  Product code, e.g. "ecs", "cms", "sts".
        action:   API action name in PascalCase, e.g. "DescribeDisks".
                  Translated to the product's CLI command style automatically.
        params:   Dict of request parameters (PascalCase keys); None skipped.
        region:   Region id (required by the regional ecs APIs; harmless for
                  sts/cms which resolve their own endpoints).
        profile:  Optional CLI credential profile name.
        timeout:  Per-attempt subprocess timeout in seconds (never unbounded).

    Returns:
        Parsed JSON response as a dict.

    Raises:
        CliError: On failure. Transient errors are retried up to 3 attempts
                  with linear backoff; other errors raise immediately.
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
                f"({e.code or 'unknown'}); retry {attempt}/"
                f"{_MAX_ATTEMPTS - 1} in {wait_s}s",
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
    region: Optional[str],
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    """Execute one CLI invocation (argument-list form, never shell=True)."""
    cmd = ["aliyun"] + _command_tokens(product, action)

    if region:
        cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]

    # Observability: one session-id UA shared by every call of this run.
    cmd += ["--user-agent", user_agent()]

    cmd += _list_param_argv(action, params, lambda key: _param_flag(product, key), _param_text)

    try:
        result = _run_with_region_retry(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
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
        body = _surface_error_envelope(_json_body(stdout))
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")
    if not isinstance(body, dict):
        raise CliError(f"aliyun {product} {action} returned a non-object JSON body")
    return body


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(profile: Optional[str] = None,
                       region: str = "cn-hangzhou") -> str:
    """Return the Alibaba Cloud UID (AccountId) of the active credential.

    Uses STS GetCallerIdentity, which needs no input beyond the configured
    credential (STS is a central service; the region is only the CLI's
    endpoint-resolution context). Returns "" when it cannot be resolved.
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region,
                    profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError:
        return ""


# ---------------------------------------------------------------------------
# Pagination helpers (NextToken style and legacy PageNumber style)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
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
    params: dict[str, Any],
    items_path: list[str],
    region: Optional[str] = None,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_pages: int = MAX_PAGES,
) -> list[Any]:
    """Follow NextToken-based pagination until exhausted (with a guardrail).

    `items_path` locates the item list in the response body, e.g.
    ["Disks", "Disk"] for DescribeDisks. The request token key is NextToken
    and the response token key is NextToken.
    """
    all_items: list[Any] = []
    next_token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        page_params.setdefault("MaxResults", MAX_RESULTS)
        if next_token:
            page_params["NextToken"] = next_token
        body = call(product, action, page_params, region=region,
                    profile=profile, timeout=timeout)

        items = _dig(body, items_path)
        if isinstance(items, dict):
            items = items.get("Item")
        if isinstance(items, list):
            all_items.extend(items)
        pages += 1

        next_token = body.get("NextToken")
        if not next_token:
            break
    if pages >= max_pages and next_token:
        print(
            f"[WARN] {product} {action}: pagination stopped at the "
            f"{max_pages}-page guardrail; results may be incomplete",
            file=sys.stderr,
        )
    return all_items


def paginate_page_number(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: Optional[str] = None,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    page_size: int = MAX_RESULTS,
    max_pages: int = MAX_PAGES,
) -> list[Any]:
    """Follow legacy PageNumber/PageSize pagination until exhausted."""
    all_items: list[Any] = []
    for page in range(1, max_pages + 1):
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = page_size
        body = call(product, action, page_params, region=region,
                    profile=profile, timeout=timeout)

        items = _dig(body, items_path)
        if isinstance(items, dict):
            items = items.get("Item")
        if not isinstance(items, list) or not items:
            break
        all_items.extend(items)
        total = body.get("TotalCount")
        if isinstance(total, int) and len(all_items) >= total:
            break
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
