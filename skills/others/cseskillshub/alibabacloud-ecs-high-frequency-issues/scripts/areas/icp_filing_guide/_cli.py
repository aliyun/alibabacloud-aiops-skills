#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun CLI invocation layer for the ECS ICP filing guide
==========================================================================
SECURITY: This skill is strictly READ-ONLY. Every action routed through this
module is a `Describe*` read query (see API_WHITELIST in _constants.py); the
module refuses anything else. Authentication is resolved exclusively by the
aliyun CLI default credential chain (CLI config file or platform-injected
environment). This module NEVER reads, prints, caches, forwards or prompts for
an AccessKey / SecretKey / STS token, and it never passes a credential on a
command line.

Backend contract
----------------
Every OpenAPI call is executed as an `aliyun` CLI subprocess in argument-list
form (a sequence of tokens handed straight to the process, never a command
string interpreted by a shell), so the credential handling, endpoint resolution
and request signing all stay inside the CLI:

    aliyun <product> <action> --<param> <value> ... \
        --user-agent AlibabaCloud-Agent-Skills/<skill>/<session-id>

Every product here (`ecs`, `vpc`, `sts`) runs in plugin mode with
lowercase-hyphenated commands and flags (`aliyun sts get-caller-identity`);
regional calls carry `--biz-region-id`. The translation is done by this module
so callers always speak in PascalCase API action names.

Observability (MUST SA-2.11c)
-----------------------------
A 32-character hex session-id (`uuid.uuid4().hex`) is created once per script
run and attached to EVERY CLI invocation of that run as `--user-agent`, so all
calls of one diagnosis can be correlated. The value is a random label, not an
account identifier.

Robustness
----------
* Per-call timeout on every subprocess invocation (MUST 7.6.1).
* Transient failures (Throttling / 5xx / timeout) are retried with linear
  backoff; non-transient failures are raised immediately.
* Every stderr line is scrubbed: ANSI colour codes removed and any
  credential-shaped key/value pair masked to `***` before it can reach a
  [WARN] line, an exception message or a report field.
* `CliError` carries the `Code: Message` shape the callers relay.

Public API:
    call(product, action, params, region=None, profile=None, timeout=...)
    paginate_page_number(...)
    paginate_next_token(...)
    resolve_account_uid(...)
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
    API_WHITELIST,
    DEFAULT_TIMEOUT,
    MAX_PAGES,
    PAGE_SIZE,
    SKILL_NAME,
    STS_ENDPOINT,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails. `.code` holds the API code."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Read-only guard
# ---------------------------------------------------------------------------

_WRITE_VERB_RE = re.compile(
    r"^(?:Create|Delete|Modify|Update|Put|Attach|Detach|Add|Remove|Reset|"
    r"Release|Import|Export|Revoke|Grant|Bind|Unbind|Authorize|Accept|Reject|"
    r"Start|Stop|Reboot|Run|Invoke|Send|Set|Allocate|Assign|Unassign|"
    r"Convert|Replace|Terminate|Cancel|Open|Close|Join|Leave|Apply|Withdraw|"
    r"Copy|Install|Redeploy|Lock|Unlock|Enable|Disable|Renew|Convert)\w+$"
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


def assert_read_only(product: str, action: str) -> None:
    """Hard gate: refuse any action that is not on the declared read-only list.

    Two independent checks, both must pass:
      1. the action must be a `Describe*` read action (or STS GetCallerIdentity);
      2. the (product, action) pair must appear in API_WHITELIST.
    A mutation request therefore raises here before any subprocess exists.
    """
    if not (action.startswith("Describe") or action == "GetCallerIdentity"):
        raise CliError(
            f"REFUSED: '{action}' is not a read-only Describe-style action. "
            f"This skill is read-only and will not issue it."
        )
    if _WRITE_VERB_RE.match(action):
        raise CliError(f"REFUSED: '{action}' looks like a mutating action.")
    if (product, action) not in API_WHITELIST:
        raise CliError(
            f"REFUSED: {product} {action} is outside this skill's API "
            f"whitelist ({sorted(a for _p, a in API_WHITELIST)})."
        )


# ---------------------------------------------------------------------------
# Session-id and User-Agent (observability)
# ---------------------------------------------------------------------------

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Per-run 32-character hex session-id, generated lazily and cached."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id={_SESSION_ID}", file=sys.stderr)
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


# ---------------------------------------------------------------------------
# CLI command shaping
# ---------------------------------------------------------------------------

# Products served by CLI plugins whose commands are lowercase-hyphenated.
_PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}

# Products whose endpoint must be pinned because the service is central.
_CENTRAL_ENDPOINTS = {"sts": STS_ENDPOINT}


def _pascal_to_kebab(name: str) -> str:
    """PascalCase -> lowercase-hyphenated (GetCallerIdentity -> get-caller-identity)."""
    if name == "RegionId":
        return "biz-region-id"
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list[str]:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    if product in _PLUGIN_STYLE_PRODUCTS:
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


def check_cli_available() -> None:
    """Exit with actionable guidance when the aliyun CLI is not installed."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 72 + "\n"
            " Alibaba Cloud CLI not found on PATH\n" + "=" * 72 + "\n"
            "Every query of this skill runs through the `aliyun` CLI.\n"
            "  Install:  https://help.aliyun.com/document_detail/121541.html\n"
            "  Verify credentials: aliyun sts get-caller-identity   (default chain; never\n"
            "             pass an AccessKey on the command line)\n"
            + "=" * 72 + "\n",
            file=sys.stderr,
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Credential scrubbing and error-code extraction
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Any `<credential-key> <value>` pair in CLI error text (query-string form or
# JSON form) is masked before it can surface anywhere. The CLI's network-error
# envelope embeds the fully signed request URL, which carries these keys.
_CREDENTIAL_PAIR_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|access[_-]key[_-]?(?:id|secret)|"
    r"securitytoken|sessiontoken|signature|signaturenonce|"
    r"bearer|password|privatekey)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:\-]{4,})"
)


def mask_credentials(text: str) -> str:
    """Replace credential VALUES with *** while keeping the key name legible."""
    if not text:
        return text or ""
    return _CREDENTIAL_PAIR_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Single choke point for CLI stderr: strip ANSI, mask credentials, tidy."""
    text = _ANSI_RE.sub("", stderr or "")
    text = mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_CODE_LINE_RE = re.compile(r"^\s*(?:ERROR CODE|ErrorCode|Code)\s*[:=]\s*(\S+)")
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def extract_error_code(text: str) -> str:
    """Best-effort API error-code extraction from CLI error output.

    Handles the real CLI 3.x envelope (verified against a live call):

        ERROR: SDK.ServerError
        ErrorCode: InvalidSecurityGroupId.NotFound
        Recommend: https://api.aliyun.com/troubleshoot?...
        RequestId: ...
        Message: The specified SecurityGroupId does not exist.
    """
    for line in (text or "").splitlines():
        stripped = line.strip()
        m = _CODE_LINE_RE.match(stripped)
        if m:
            candidate = m.group(1).strip().strip('"').rstrip(",")
            if candidate and candidate not in ("SDK.ServerError", "ServerError"):
                return candidate
        if stripped.startswith("Data:"):
            try:
                body = json.loads(stripped.split(":", 1)[1].strip())
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(body, dict) and body.get("Code"):
                return str(body["Code"])
            continue
        if stripped.startswith("ERROR:"):
            parts = stripped.split(":", 2)
            candidate = parts[1].strip() if len(parts) > 2 else ""
            if _ERROR_CODE_TOKEN_RE.match(candidate):
                return candidate
    return ""


# Inline proof that the mask holds on the exact envelope shape that can appear.
_probe = (
    "ERROR: request execution failed: https://ecs.aliyuncs.com/?Action=Describe"
    "Instances&AccessKeyId=STS.ExampleFakeValue1234&Signature=FakeSignatureValue"
    "&SecurityToken=CAISExampleFakeTokenValue"
)
_masked = mask_credentials(_probe)
assert "ExampleFakeValue1234" not in _masked, _masked
assert "FakeSignatureValue" not in _masked, _masked
assert "CAISExampleFakeTokenValue" not in _masked, _masked
assert "AccessKeyId=***" in _masked, _masked
assert mask_credentials("") == "" and _clean_stderr("") == ""

# Inline proof that the read-only gate refuses mutation and unknown actions.
for _rejected in ("CreateInstance", "RevokeSecurityGroup", "AuthorizeSecurityGroup",
                  "DeleteInstance", "ModifyInstanceSpec", "RunCommand"):
    try:
        assert_read_only("ecs", _rejected)
        raise AssertionError(f"read-only gate failed to refuse {_rejected}")
    except CliError:
        pass


# ---------------------------------------------------------------------------
# Transient-error classification
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 2

_RETRY_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal failure",
    "systembusy", "temporarily unavailable", "connection reset",
    "timed out", "timeout", "http 500", "http 502", "http 503", "http 504",
    "statuscode: 5", "eof occurred", "broken pipe", "dns", "no such host",
    "unavailable",
)

# Codes that are NEVER retried (they will not change on a second attempt).
_TERMINAL_MARKERS = (
    "nopermission", "implicitdeny", "unauthorized", "invalidaccesskeyid",
    "signaturedoesnotmatch", "invalidsecuritytoken", "expiredtoken",
    "invalidparameter", "missingparameter", "notfound", "nosuch",
    "invalidregionid", "illegalparam", "instancenotfound",
    "invalidsecuritygroupid.notfound", "invalidinstancename.malformed",
)


def _is_retryable(err: CliError) -> bool:
    code = (err.code or "").lower()
    haystack = f"{code} {str(err)}".lower()
    if any(marker in haystack for marker in _TERMINAL_MARKERS):
        return False
    if code in ("", ):
        return any(marker in haystack for marker in _RETRY_MARKERS)
    return any(marker in haystack for marker in _RETRY_MARKERS)


# ---------------------------------------------------------------------------
# The one and only subprocess call site
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: Optional[str] = None,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke one whitelisted read-only OpenAPI action through the aliyun CLI.

    Raises:
        CliError: on refusal (non read-only / outside whitelist) or on failure
                  after the transient-error retries are exhausted.
    """
    assert_read_only(product, action)
    last_err: Optional[CliError] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _call_once(product, action, params, region, profile, timeout)
        except CliError as err:
            last_err = err
            if not _is_retryable(err) or attempt >= _MAX_ATTEMPTS:
                raise
            wait_s = attempt * _BACKOFF_BASE_SECONDS
            print(
                f"[WARN] {product} {action}: transient failure "
                f"({err.code or 'unclassified'}); retry {attempt}/"
                f"{_MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # unreachable in practice; keeps the contract total


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
def _call_once(
    product: str,
    action: str,
    params: Optional[dict[str, Any]],
    region: Optional[str],
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    """Execute one CLI invocation (argument list form, never a shell string)."""
    cmd = ["aliyun"] + _command_tokens(product, action)

    endpoint = _CENTRAL_ENDPOINTS.get(product)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    if region:
        cmd += ["--region", region]
    if profile:
        cmd += ["--profile", profile]

    # Observability: the same session-id UA on every call of this run.
    cmd += ["--user-agent", user_agent()]

    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        cmd += [_param_flag(product, key), str(value)]

    try:
        proc = subprocess.run(  # noqa: timeout-kept-inline
            _with_auto_plugin(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise CliError(
            f"aliyun {product} {action} timed out after {timeout}s "
            f"(no response was received; nothing was changed, this skill is "
            f"read-only)"
        )
    except OSError as exc:
        raise CliError(f"could not start the aliyun CLI: {exc}")

    if proc.returncode != 0:
        stderr = _clean_stderr(proc.stderr or "")
        stdout = _clean_stderr(proc.stdout or "")
        blob = f"{stderr}\n{stdout}".strip()
        raise CliError(
            f"aliyun {product} {action} failed: "
            f"{(blob or 'no error output')[:400]}",
            code=extract_error_code(blob),
            stderr=blob,
        )

    raw = (proc.stdout or "").strip()
    if not raw:
        return {}
    try:
        body = _json_body(raw)
    except json.JSONDecodeError as exc:
        raise CliError(
            f"aliyun {product} {action} returned non-JSON output: "
            f"{mask_credentials(raw[:200])} ({exc})"
        )
    if not isinstance(body, dict):
        raise CliError(f"aliyun {product} {action} returned unexpected JSON shape")
    return body


# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _unwrap(items: Any) -> list[Any]:
    """Tolerate both `{"Item": [...]}` and a bare list."""
    if isinstance(items, dict):
        items = items.get("Item")
    return items if isinstance(items, list) else []


def paginate_page_number(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: Optional[str] = None,
    profile: Optional[str] = None,
    page_size: int = PAGE_SIZE,
    max_pages: int = MAX_PAGES,
    total_path: Optional[list[str]] = None,
) -> list[Any]:
    """Page through a `PageNumber`/`PageSize` API until exhausted."""
    collected: list[Any] = []
    page = 1
    while page <= max_pages:
        page_params = dict(params)
        page_params["PageSize"] = page_size
        page_params["PageNumber"] = page
        body = call(product, action, page_params, region=region, profile=profile)
        items = _unwrap(_dig(body, items_path))
        collected.extend(items)
        total = _dig(body, total_path) if total_path else body.get("TotalCount")
        try:
            total_int = int(total) if total is not None else None
        except (TypeError, ValueError):
            total_int = None
        if total_int is not None and len(collected) >= total_int:
            return collected
        if not items:
            return collected
        page += 1
    else:
        print(
            f"[WARN] {product} {action}: stopped at the {max_pages}-page "
            f"guardrail; the list may be truncated",
            file=sys.stderr,
        )
    return collected


def paginate_next_token(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: Optional[str] = None,
    profile: Optional[str] = None,
    max_results: int = PAGE_SIZE,
    max_results_key: str = "MaxResults",
    max_pages: int = MAX_PAGES,
) -> list[Any]:
    """Page through a `NextToken` API until exhausted."""
    collected: list[Any] = []
    token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        if max_results_key:
            page_params[max_results_key] = max_results
        if token:
            page_params["NextToken"] = token
        body = call(product, action, page_params, region=region, profile=profile)
        collected.extend(_unwrap(_dig(body, items_path)))
        token = body.get("NextToken")
        pages += 1
        if not token:
            return collected
    print(
        f"[WARN] {product} {action}: stopped at the {max_pages}-page guardrail; "
        f"the list may be truncated",
        file=sys.stderr,
    )
    return collected


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

def resolve_account_uid(
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Return the account UID of the active credential, or "" if unavailable.

    STS GetCallerIdentity needs no input beyond the configured credential; the
    UID is used only as a report traceability label.
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, profile=profile, timeout=timeout)
    except CliError as err:
        print(f"[WARN] caller identity unavailable: {err}", file=sys.stderr)
        return ""
    return str(body.get("AccountId") or "").strip()


def describe_error(err: BaseException) -> dict[str, str]:
    """Normalise an exception into the report's error record."""
    code = getattr(err, "code", "") or extract_error_code(str(err))
    return {"code": code, "message": mask_credentials(str(err))[:500]}


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
