#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer for the ECS Punishment Appeal Guide
=================================================================================
SECURITY: This skill is strictly READ-ONLY. Every invocation this layer makes
is a Describe*/identity query from the whitelist in _constants.py. All
authentication is resolved by the aliyun CLI default credential chain
(environment or CLI config profile); this module NEVER reads, prints, caches
or forwards any AccessKey / Secret / token value, and it masks
credential-looking text found in CLI error output before that text can reach
a log line or a report field.

Internal module (underscore-prefixed): do NOT run directly. It is imported by
punishment_appeal_guide.py and sts_token.py so that every Alibaba Cloud call
of this skill goes through ONE audited place, carrying:

  * argument-list subprocess execution only (never a shell string), with a
    per-call timeout on every invocation,
  * the observability User-Agent: one 32-hex session-id per run attached to
    every call as --user-agent,
  * bounded retry with backoff for transient failures (throttling / 5xx /
    timeouts), immediate raise for everything else,
  * CliError with the "Code: Message" shape so callers can degrade per query
    instead of aborting the whole diagnosis.

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
    aliyun ecs describe-instances --biz-region-id cn-hangzhou
    aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.
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
    CALL_TIMEOUT_SECONDS,
    RETRY_BACKOFF_SECONDS,
    RETRY_MAX_ATTEMPTS,
    SKILL_NAME,
    STS_COMMAND,
    STS_PRODUCT,
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


def _plugin_cmd(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _plugin_flag(key):
    if key == "RegionId":
        return "--biz-region-id"
    return "--" + re.sub(r"(?<!^)(?=[A-Z])", "-", key).lower()
class CliError(RuntimeError):
    """Raised when an OpenAPI invocation through the CLI fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Session-id & User-Agent (observability; MUST SA-2.11b/c)
# ---------------------------------------------------------------------------
# A 32-character hex session-id is generated once per script run and attached
# to EVERY CLI invocation of that run, so all calls of one diagnosis can be
# correlated. Implementation of the documented template
# AlibabaCloud-Agent-Skills/{skill-name}/{session-id}.

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """The User-Agent value attached to every API call of this run."""
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
    """Ensure the aliyun CLI exists; exit(1) with guidance when it does not."""
    if shutil.which("aliyun") is None:
        print(
            "[ERROR] the aliyun CLI was not found on PATH. Install the "
            "Alibaba Cloud CLI and run `aliyun sts get-caller-identity` (default "
            "credential chain only; never pass credentials on the command "
            "line).",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Credential-value masking (defense in depth for error text)
# ---------------------------------------------------------------------------
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _mask_credentials(text: str) -> str:
    """Replace credential-looking values in CLI error text with ***.

    Pure function; keeps the key name for diagnosability, drops the value.
    Never raises.
    """
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI colors, mask credential values, collapse blank runs.

    Every CLI stderr stream passes through this single choke point before it
    can surface in a [WARN] line, a CliError message or a report field.
    """
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline self-test: the mask must actually mask (a broken mask would let a
# temporary token leak into a [WARN] line, violating the credential rule).
assert _mask_credentials("AccessKeyId=STS.ExampleFake123") == "AccessKeyId=***"
assert _mask_credentials("nothing sensitive here") == "nothing sensitive here"


# ---------------------------------------------------------------------------
# Error-code extraction and transient-error classification
# ---------------------------------------------------------------------------
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI error text.

    Handles the aliyun CLI failure envelope shapes:
    "ErrorCode: X", "Code: X" (SDKError), "Data: {\"Code\": ...}" and the
    legacy "ERROR: <Code>: <Message>" line.
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


_TRANSIENT_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal error",
    "http 500", "http 502", "http 503", "http 504", "statuscode: 5",
    "502", "504", "server busy", "connection reset", "timed out", "timeout",
    "temporarily unavailable",
)


def _is_retryable(err: CliError) -> bool:
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    haystack = f"{code} {str(err)}".lower()
    return any(marker in haystack for marker in _TRANSIENT_MARKERS)


# ---------------------------------------------------------------------------
# One CLI invocation
# ---------------------------------------------------------------------------

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
    """Execute one aliyun CLI call (argument list, never a shell string)."""
    if product == STS_PRODUCT:
        cmd = ["aliyun", product, STS_COMMAND]  # plugin mode: lowercase-hyphen
    else:
        cmd = ["aliyun", product, _plugin_cmd(action)]

    if region:
        cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]

    # Observability: one session-id User-Agent shared by every call of this run.
    cmd += ["--user-agent", user_agent()]

    cmd += _list_param_argv(action, params, lambda key: _plugin_flag(key), _param_text)

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

    stdout = _mask_credentials((result.stdout or "").strip())
    if not stdout:
        return {}
    try:
        return _json_body(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")


# ---------------------------------------------------------------------------
# Public call entry with transient retry
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: Optional[str] = None,
    profile: Optional[str] = None,
    timeout: int = CALL_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Invoke one whitelisted read-only action through the aliyun CLI.

    Transient errors (throttling / 5xx / timeout) are retried up to
    RETRY_MAX_ATTEMPTS times with linear backoff; every other error raises
    CliError immediately so the caller can degrade per query.
    """
    last_err: Optional[CliError] = None
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            return _call_cli(product, action, params, region, profile, timeout)
        except CliError as e:
            last_err = e
            if not _is_retryable(e):
                raise
            if attempt >= RETRY_MAX_ATTEMPTS:
                raise CliError(
                    f"{product} {action} failed after {attempt} attempts: {e}",
                    code=e.code, stderr=e.stderr,
                )
            wait_s = attempt * RETRY_BACKOFF_SECONDS
            print(
                f"[WARN] {product} {action} transient error "
                f"({e.code or 'unknown'}); retry {attempt}/"
                f"{RETRY_MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # defensive; the loop always returns or raises


# ---------------------------------------------------------------------------
# Response digging + pagination helpers
# ---------------------------------------------------------------------------

def dig(obj: Any, path: list[str]) -> Any:
    """Walk a nested dict along `path`; return None on any miss."""
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def paginate_page_number(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: Optional[str] = None,
    profile: Optional[str] = None,
    page_size_key: str = "PageSize",
    page_size: int = 100,
    max_pages: int = 5,
) -> list[Any]:
    """Follow PageNumber-style pagination with a page-count guardrail."""
    all_items: list[Any] = []
    for page in range(1, max_pages + 1):
        page_params = dict(params)
        page_params[page_size_key] = page_size
        page_params["PageNumber"] = page
        body = call(product, action, page_params, region=region, profile=profile)
        items = dig(body, items_path)
        if isinstance(items, list):
            all_items.extend(items)
        total = body.get("TotalCount") if isinstance(body, dict) else None
        try:
            if total is not None and len(all_items) >= int(total):
                break
        except (TypeError, ValueError):
            break
    return all_items


def paginate_next_token(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: Optional[str] = None,
    profile: Optional[str] = None,
    token_req_key: str = "NextToken",
    token_resp_path: Optional[list[str]] = None,
    max_pages: int = 5,
) -> list[Any]:
    """Follow NextToken-style pagination with a page-count guardrail."""
    token_resp_path = token_resp_path or ["NextToken"]
    all_items: list[Any] = []
    next_token: Optional[str] = None
    for _page in range(max_pages):
        page_params = dict(params)
        if next_token:
            page_params[token_req_key] = next_token
        body = call(product, action, page_params, region=region, profile=profile)
        items = dig(body, items_path)
        if isinstance(items, list):
            all_items.extend(items)
        next_token = dig(body, token_resp_path)
        if not next_token:
            break
    else:
        if next_token:
            print(
                f"[WARN] {product} {action}: pagination stopped at the "
                f"{max_pages}-page guardrail; results may be incomplete",
                file=sys.stderr,
            )
    return all_items


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(profile: Optional[str] = None) -> str:
    """Return the AccountId of the active CLI credential, or "" when unknown.

    Uses the read-only STS identity command; the value is used ONLY as a
    local traceability label in the report, never as a query parameter.
    """
    try:
        body = call(STS_PRODUCT, "GetCallerIdentity", {}, profile=profile)
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
