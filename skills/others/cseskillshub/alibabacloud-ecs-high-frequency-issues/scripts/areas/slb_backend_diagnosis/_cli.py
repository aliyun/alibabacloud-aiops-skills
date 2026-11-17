#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer for the ECS SLB backend skill
===========================================================================
SECURITY: This skill is strictly READ-ONLY. Every action issued through this
module is a Describe/Get/Query-class read call. Authentication is resolved by
the aliyun CLI default credential chain only -- this module NEVER reads,
prints, caches or passes any AccessKey ID / Secret / session token, and it
must never be extended to call a mutating API.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the entry scripts so that all Alibaba Cloud OpenAPI access goes through ONE
place with the guarantees below:

CLI-only backend
----------------
Every API call is routed through `call()`, which invokes the `aliyun` CLI as
a subprocess (argument-list form, never shell=True):

    aliyun <product> <action> --param value ... --user-agent <UA>

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
    aliyun ecs describe-instances --biz-region-id cn-hangzhou ...
    aliyun sts get-caller-identity
Callers pass the PascalCase API action name; this layer translates it.

Observability (SA-2.11)
-----------------------
A 32-character hex session-id (`uuid.uuid4().hex`) is generated once per
script run and attached to EVERY CLI call of that run as
`--user-agent AlibabaCloud-Agent-Skills/<skill-name>/<session-id>`.

Transient-error retry
---------------------
Throttling / 5xx / timeout failures are retried up to 3 attempts with linear
backoff; everything else (permission, parameter, not-found) raises at once.

Credential masking
------------------
All CLI stderr text passes through `_clean_stderr`, which strips ANSI codes
and masks AccessKeyId / SecurityToken / Signature values before they can
reach a [WARN] line, a CliError message or a report field.

Public API:
    call(product, action, params, region, profile, timeout) -> dict
    paginate_page_number(product, action, params, items_path, ...) -> list
    session_id() / user_agent()
    resolve_account_id(...) -> str
    check_cli_available() -> None
    CliError
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, List, Optional

from _constants import API_VERSIONS, DEFAULT_REGION, DEFAULT_TIMEOUT, MAX_PAGES, SKILL_NAME, PAGE_SIZE


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
    """Raised when an OpenAPI invocation fails. Carries `Code: Message`."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Command-style registry
# ---------------------------------------------------------------------------
# sts is served by the aliyun-cli-sts plugin (lowercase-hyphenated commands);
# ecs / vpc / cms / sts all run in plugin mode: lowercase-hyphenated commands
# and flags; PascalCase API action names are translated before the argv is built.
_PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}

# Products with a known OpenAPI version (informational; the CLI resolves the
# real endpoint/version internally for these RPC products).
KNOWN_PRODUCTS = {"ecs", "vpc", "cms", "sts"}


def _pascal_to_kebab(name: str) -> str:
    """Convert a PascalCase API name to the plugin kebab-case command form.

    Example: GetCallerIdentity -> get-caller-identity
    """
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> List[str]:
    """Return the CLI command tokens for (product, action)."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    """Return the CLI flag for a parameter name, honoring product style."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return "--" + _pascal_to_kebab(key)
    return "--" + key


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex  # 32-character lowercase hex string
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return "AlibabaCloud-Agent-Skills/" + SKILL_NAME + "/" + session_id()

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
# Marker substrings searched in the lowercased error code AND error message.
_RETRY_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal error",
    "http 500", "http 502", "http 503", "http 504",
    "statuscode: 5", "server busy",
    "connection reset", "timed out", "timeout", "temporarily unavailable",
)


def _is_retryable(err: CliError) -> bool:
    """True when the failure looks transient (throttling / 5xx / timeout)."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = "{} {}".format(code, str(err)).lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


# ---------------------------------------------------------------------------
# Credential masking (single choke point for all CLI stderr text)
# ---------------------------------------------------------------------------
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Mask every <credentialKey>=<value> (query string) or "<credentialKey>":
# "<value>" (JSON) pair so a signed-URL error envelope can never leak a
# credential into a [WARN] line, a CliError message or a report field.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)"
)


def _mask_credentials(text: str) -> str:
    """Mask credential key-value pairs in CLI error text. Never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: "{}=***".format(m.group(1)), text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI codes, mask credentials, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Inline boundary assertions for the masking (run on every import): a failure
# here means the mask is broken and this module must not be trusted.
# normal: credential-free text passes through unchanged.
assert _clean_stderr("ERROR: request failed: connection refused") == \
    "ERROR: request failed: connection refused"
assert _mask_credentials("no secrets here") == "no secrets here"
# boundary: signed-URL network-error envelope with fake (never real) values.
_bl3_env = (
    'GET "https://ecs.aliyuncs.com/?AccessKeyId=STS.ExampleFakeKey1234'
    "&Action=DescribeInstances&SecurityToken="
    + "CAIS" + ("x" * 101)
    + '&Signature=abcd1234ef==&SignatureNonce=9e2f1" dial tcp: refused')
_bl3_masked = _clean_stderr(_bl3_env)
assert "STS.ExampleFakeKey1234" not in _bl3_masked, _bl3_masked  # AK masked
assert ("x" * 101) not in _bl3_masked, _bl3_masked              # token masked
assert "abcd1234ef" not in _bl3_masked, _bl3_masked              # sig masked
assert "AccessKeyId=***" in _bl3_masked
assert "SecurityToken=***" in _bl3_masked
assert "Signature=***" in _bl3_masked
# boundary: JSON-shaped credential pairs are masked as well.
_bl3_json = '{"AccessKeyId": "STS.NYfake", "SecurityToken": "CAISfake99"}'
_bl3_json_masked = _clean_stderr(_bl3_json)
assert "STS.NYfake" not in _bl3_json_masked, _bl3_json_masked
assert "CAISfake99" not in _bl3_json_masked, _bl3_json_masked
assert _bl3_json_masked.count("***") == 2
# invalid: None / empty degrade to "" (never raise).
assert _clean_stderr(None) == ""
assert _clean_stderr("") == ""
assert _mask_credentials("") == ""


# ---------------------------------------------------------------------------
# Error-code extraction from the CLI failure envelope
# ---------------------------------------------------------------------------
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Handles the aliyun CLI 3.x SDKError envelope (Code: <ApiErrorCode>,
    Data: {"Code": ...}) and the legacy "ERROR: <Code>: <Message>" form.
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
            except (json.JSONDecodeError, ValueError):
                pass
            continue
        if line.startswith("{"):
            try:
                body = json.loads(line)
                if isinstance(body, dict) and body.get("Code"):
                    return str(body["Code"])
            except (json.JSONDecodeError, ValueError):
                pass
        if line.startswith("ERROR:"):
            parts = line.split(":", 2)
            candidate = parts[1].strip() if len(parts) > 2 else ""
            return candidate if _ERROR_CODE_TOKEN_RE.match(candidate) else ""
    return ""


# ---------------------------------------------------------------------------
# Public call entry point
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict] = None,
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Invoke a read-only Alibaba Cloud OpenAPI action via the aliyun CLI.

    Transient errors (Throttling / 5xx / timeout) are retried up to
    _MAX_ATTEMPTS times with linear backoff; other errors raise CliError
    immediately. Every invocation carries the per-run observability
    User-Agent.
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
                    "{} {} failed after {} attempts: {}".format(
                        product, action, attempt, e),
                    code=e.code,
                    stderr=e.stderr,
                )
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                "[WARN] {} {} transient error ({}); retry {}/{} in {}s".format(
                    product, action, e.code or "unknown",
                    attempt, _MAX_ATTEMPTS - 1, wait_s),
                file=sys.stderr,
            )
            time.sleep(wait_s)
    if last_err is None:  # defensive; unreachable in practice
        raise CliError("{} {} failed".format(product, action))
    raise last_err


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
    """Execute one CLI invocation (argument-list form, never shell=True)."""
    if product not in KNOWN_PRODUCTS:
        # Hard gate: this skill's whitelist is ecs / vpc / cms / sts only.
        raise CliError("product '{}' is not allowed by this skill's whitelist".format(product))
    cmd = ["aliyun"] + _command_tokens(product, action)
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
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # never hang on interactive prompts
        )
    except subprocess.TimeoutExpired:
        raise CliError("aliyun {} {} timed out after {}s".format(product, action, timeout))

    if result.returncode != 0:
        stderr = _clean_stderr(result.stderr or "")
        code = _extract_error_code(stderr)
        raise CliError(
            "aliyun {} {} failed: {}".format(product, action, stderr[:300]),
            code=code,
            stderr=stderr,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = _surface_error_envelope(_json_body(stdout))
    except json.JSONDecodeError as e:
        raise CliError("aliyun {} {} returned non-JSON output: {}".format(product, action, e))
    if not isinstance(body, dict):
        raise CliError("aliyun {} {} returned unexpected JSON shape".format(product, action))
    return body


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(region: str = DEFAULT_REGION, profile: Optional[str] = None) -> str:
    """Return the Alibaba Cloud account UID of the active credential ("" if unknown)."""
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError:
        return ""


def check_cli_available() -> None:
    """Ensure the aliyun CLI is available; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill requires the Alibaba Cloud CLI to be installed and configured.\n\n"
            "  Install: https://help.aliyun.com/document_detail/121541.html\n"
            "  Verify credentials: aliyun sts get-caller-identity\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Pagination helper (PageNumber/PageSize style used by ECS and VPC listings)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: List[str]) -> Any:
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
    params: dict,
    items_path: List[str],
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    page_size: int = PAGE_SIZE,
    max_pages: int = MAX_PAGES,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[Any]:
    """Follow PageNumber pagination until exhausted (hard page guardrail).

    `items_path` locates the item list in the response
    (e.g. ["Instances", "Instance"] for ECS, ["EipAddresses", "EipAddress"]
    for VPC EIP listings). Every page call carries the per-call timeout.
    """
    all_items: List[Any] = []
    page = 1
    while page <= max_pages:
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = page_size
        body = call(product, action, page_params, region=region, profile=profile,
                    timeout=timeout)
        items = _dig(body, items_path)
        if not isinstance(items, list):
            items = []
        all_items.extend(items)
        total = _dig(body, ["TotalCount"]) or _dig(body, ["totalCount"])
        try:
            total_n = int(total) if total is not None else None
        except (TypeError, ValueError):
            total_n = None
        if total_n is not None:
            if len(all_items) >= total_n:
                return all_items
        elif len(items) < page_size:
            return all_items
        page += 1
    if page > max_pages:
        print(
            "[WARN] {} {}: pagination stopped at the {}-page guardrail; "
            "results may be incomplete".format(product, action, max_pages),
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
