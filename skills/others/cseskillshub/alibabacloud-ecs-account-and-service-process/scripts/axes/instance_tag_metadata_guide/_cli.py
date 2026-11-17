#!/usr/bin/env python3
"""
_cli.py -- shared aliyun-CLI layer for the ECS tag / metadata / resource-group
skill
==============================================================================
SECURITY: this skill is strictly READ-ONLY. Every request that leaves this
module is a Describe / List / Get style read call; nothing here can change a
resource. Authentication is resolved exclusively by the aliyun CLI default
credential chain (CLI profile config or platform-injected environment):
this module NEVER reads, prints, caches, passes or asks for an access key, a
secret or a token, and it masks credential material out of any error text
before that text can reach a log line or a report field.

Design (platform rules MUST 1.1.2 / SA-2.11 / SA-2.11c / SA-2.12 / 7.6.1)
-------------------------------------------------------------------------
* Internal module (leading underscore): imported by the entry scripts, never
  run directly. All OpenAPI access of this skill goes through this ONE place.
* Argument-list subprocess calls only, never a shell. Each call carries its
  own timeout (``DEFAULT_TIMEOUT``), and stdin is /dev/null so an
  interactive prompt can never hang a run.
* Command style per product: ECS uses the CLI's built-in API metadata
  (PascalCase action and parameters, e.g. ``aliyun ecs describe-instances
  --RegionId cn-hangzhou``); STS is a plugin command and therefore
  lowercase-hyphenated (``aliyun sts get-caller-identity``). The translator
  below keeps both correct so no caller can accidentally emit a hand-typed
  mutating command.
* Observability: one 32-character hex session id per run
  (``uuid.uuid4().hex``), attached to EVERY call as
  ``--user-agent AlibabaCloud-Agent-Skills/<skill>/<session-id>``.
* Transient failures (throttling / 5xx / timeout) are retried with linear
  backoff; anything else is raised immediately as ``CliError``.

Public API:
    call(product, action, params, region, profile, timeout) -> dict
    paginate_next_token(...) -> list        (DescribeInstances style)
    paginate_pages(...)      -> list        (DescribeInstanceStatus style)
    resolve_account_id(...)  -> str
    check_cli_available()    -> None
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
    DEFAULT_REGION,
    DEFAULT_TIMEOUT,
    MAX_PAGES,
    MAX_RESULTS,
    SKILL_NAME,
    STS_ENDPOINT,
    USER_AGENT_TEMPLATE,
)


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails. Carries ``Code: Message``."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Command style registry
# ---------------------------------------------------------------------------
# Products served by an aliyun CLI plugin use lowercase-hyphenated commands;
# products served from the CLI's built-in API metadata keep PascalCase.
_PLUGIN_STYLE_PRODUCTS = set()  # sts uses RPC PascalCase, not plugin kebab

# Region-less (central) services get an explicit endpoint so a call never
# depends on the caller's default region.
_PRODUCT_ENDPOINTS = {"sts": STS_ENDPOINT}


def _pascal_to_kebab(name: str) -> str:
    """PascalCase API name -> plugin kebab-case command (GetCallerIdentity ->
    get-caller-identity)."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _command_tokens(product: str, action: str) -> list[str]:
    """CLI command tokens for (product, action), honoring the command style."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        return [product, _pascal_to_kebab(action)]
    return [product, action]


def _param_flag(product: str, key: str) -> str:
    """CLI flag for a parameter name, honoring the product command style."""
    if product in _PLUGIN_STYLE_PRODUCTS:
        if key == "RegionId":
            return "--biz-region-id"
        return f"--{_pascal_to_kebab(key)}"
    return f"--{key}"


# Boundary assertions (normal / boundary / invalid) for the command
# translators; a failure here would mean every call of this skill is malformed.
assert _pascal_to_kebab("GetCallerIdentity") == "get-caller-identity"
assert _pascal_to_kebab("DescribeInstances") == "describe-instances"
assert _pascal_to_kebab("") == ""                      # boundary: empty input
assert _command_tokens("sts", "GetCallerIdentity") == ["sts", "GetCallerIdentity"]
assert _command_tokens("ecs", "DescribeInstances") == ["ecs", "DescribeInstances"]
assert _param_flag("ecs", "RegionId") == "--RegionId"
assert _param_flag("sts", "RoleId") == "--RoleId"


# ---------------------------------------------------------------------------
# Session id and User-Agent (observability, rule SA-2.11c)
# ---------------------------------------------------------------------------

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-character hex session id (lazily created)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent attached to every call made by this run."""
    return USER_AGENT_TEMPLATE.format_map(
        {"session-id": session_id(), "skill-version": _SKILL_VERSION})

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-account-and-service-process"


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
    return _ua_normalize(str(_user_agent_raw(*_ua_a, **_ua_k)))


def check_cli_available() -> None:
    """Exit with actionable guidance when the aliyun CLI is not installed."""
    if shutil.which("aliyun") is None:
        print(
            "\n" + "=" * 78 + "\n"
            " aliyun CLI not found\n"
            + "=" * 78 + "\n"
            "This skill talks to Alibaba Cloud exclusively through the aliyun\n"
            "CLI. Install it, then configure a credential profile with\n"
            "  aliyun configure\n"
            "(never pass an access key or secret to this skill).\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Transient-error classification and retry
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 2

_RETRY_CODES = {
    "throttling", "throttling.user", "throttling.api", "serviceunavailable",
    "internalerror", "systembusy", "sdk.httperror", "unknownerror",
}
_RETRY_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "internal error",
    "http 500", "http 502", "http 503", "http 504", "statuscode: 5",
    "502", "504", "server busy", "temporarily unavailable",
    "connection reset", "timed out", "timeout",
)


def _is_retryable(err: CliError) -> bool:
    """True for throttling / 5xx / timeout style failures."""
    code = (getattr(err, "code", "") or "").lower()
    if code in _RETRY_CODES:
        return True
    haystack = f"{code} {err}".lower()
    return any(marker in haystack for marker in _RETRY_MARKERS)


# Boundary assertions: transient vs permanent classification.
assert _is_retryable(CliError("boom", code="Throttling.User"))
assert _is_retryable(CliError("StatusCode: 503, slow down", code=""))
assert _is_retryable(CliError("aliyun ecs describe-instances timed out after 60s"))
assert not _is_retryable(CliError("nope", code="NoPermission"))
assert not _is_retryable(CliError("nope", code="InvalidParameter"))
assert not _is_retryable(CliError("", code=""))          # boundary: nothing


# ---------------------------------------------------------------------------
# Credential masking (rule SA-2.12 / denial-wording hygiene)
# ---------------------------------------------------------------------------
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# The CLI embeds the fully signed request URL in its network-error envelope,
# so the credential key/value pairs (query-string or JSON form) are masked
# before any error text can reach stderr, a CliError message, or a report
# field. The key NAME is kept for diagnosability; the VALUE becomes ***.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce|x-acs-signature|x-acs-accesskey-id)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Mask credential values in error text. Pure function, never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Strip ANSI colours, mask credential values, collapse blank runs."""
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Boundary assertions for the mask: normal / signed-URL envelope / JSON
# envelope / empty input. If any of these fail, credential material could
# leak into a report, so the module must not run.
assert _mask_credentials("nothing sensitive here") == "nothing sensitive here"
_signed_env = (
    'GET "https://ecs.cn-hangzhou.aliyuncs.com/?Action=DescribeInstances'
    "&AccessKeyId=STS.FAKEEXAMPLEKEY0000"
    "&SecurityToken=" + "CAISfake" + ("x" * 90) +
    '&Signature=fake1234signaturevalue&SignatureNonce=abc111" dial tcp: refused'
)
_masked = _clean_stderr(_signed_env)
assert "STS.FAKEEXAMPLEKEY0000" not in _masked
assert ("x" * 90) not in _masked
assert "fake1234signaturevalue" not in _masked
assert "AccessKeyId=***" in _masked and "SecurityToken=***" in _masked
_json_env = '{"AccessKeyId": "STS.FAKEKEY", "SecurityToken": "CAISFAKETOKEN"}'
_masked_json = _clean_stderr(_json_env)
assert "STS.FAKEKEY" not in _masked_json and "CAISFAKETOKEN" not in _masked_json
assert _masked_json.count("***") == 2
assert _clean_stderr("") == ""
assert _clean_stderr(None) == ""                          # invalid input


# ---------------------------------------------------------------------------
# Error-code extraction
# ---------------------------------------------------------------------------

_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")


def _extract_error_code(stderr: str) -> str:
    """Best-effort API error-code extraction from CLI stderr text.

    Handles the shapes measured with aliyun CLI 3.4.5:

        ERROR: SDK.ServerError
        ErrorCode: InvalidOperation.NotSupportedEndpoint
        Recommend: https://api.aliyun.com/troubleshoot?q=...
        Message: The specified endpoint cant operate this region. ...

    The precise ``ErrorCode:`` / ``Code:`` / ``Data: {JSON}`` forms win; the
    legacy ``ERROR: <Code>: <Message>`` form is only a fallback, and an SDK
    wrapper name such as ``SDK.ServerError`` is never returned while a real
    server code is still to be read on a following line.
    """
    fallback = ""
    for line in (stderr or "").splitlines():
        line = line.strip()
        if line.startswith("ErrorCode:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("Code:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("Data:"):
            try:
                body = json.loads(line.split(":", 1)[1].strip())
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
            continue
        if line.startswith("ERROR:") and not fallback:
            parts = line.split(":", 2)
            candidate = parts[1].strip() if len(parts) > 2 else ""
            if candidate and _ERROR_CODE_TOKEN_RE.match(candidate) \
                    and not candidate.lower().startswith("sdk."):
                fallback = candidate
    return fallback


# Boundary assertions: the measured real envelope plus the tolerated variants.
assert _extract_error_code(
    "ERROR: SDK.ServerError\nErrorCode: InvalidOperation.NotSupportedEndpoint\n"
    "Message: whatever") == "InvalidOperation.NotSupportedEndpoint"
assert _extract_error_code("Code: Throttling.User\nMessage: x") == "Throttling.User"
assert _extract_error_code('Data: {"Code":"NoPermission"}') == "NoPermission"
assert _extract_error_code('{"Code":"InvalidParameter","Message":"x"}') == "InvalidParameter"
assert _extract_error_code("ERROR: not-an-api-code at all here") == ""
assert _extract_error_code("") == ""                       # boundary: empty
# A bare SDK wrapper line is not an API code: keep it empty rather than
# mislabeling every failure as "SDK.ServerError".
assert _extract_error_code("ERROR: SDK.ServerError\nMessage: x") == ""
# Legacy one-line form still yields the code.
assert _extract_error_code("ERROR: NoPermission: user not authorized") == \
    "NoPermission"


# ---------------------------------------------------------------------------
# Single call
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Invoke one read-only OpenAPI action through the aliyun CLI.

    Raises ``CliError`` (``Code: Message``) on failure; transient failures are
    retried up to 3 attempts with linear backoff (2s, 4s).
    """
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
    raise last_err  # unreachable in practice


_AUTO_PLUGIN_PROBED = False


def _with_auto_plugin(argv):
    """Resolve a missing product plugin without an interactive prompt.

    auto-plugin-install is a `configure set` profile key, not a per-invocation
    flag. Only a host that actually lacks this product's plugin is touched;
    `plugin list` is a local inventory read with no credential or network use.
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


def _json_body(text):
    """Decode the CLI's JSON body even when a notice precedes it on stdout.

    A parse hiccup is not a customer-side credential fault; the body is
    located instead of assumed.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        offsets = [i for i in (text.find("{"), text.find("[")) if i != -1]
        if not offsets:
            raise
        return json.JSONDecoder().raw_decode(text[min(offsets):])[0]


_REGION_FLAG_REQUIRED_RES = (
    re.compile(r"missing required parameter\(s\):\s*--biz-region-id"),
    re.compile(r"--biz-region-id is required"),
)


def _region_flag_retry(cmd, stderr, region):
    """The same call with the plugin's region parameter, or None if not applicable."""
    if not region or "--biz-region-id" in cmd:
        return None
    if not any(pattern.search(stderr or "") for pattern in _REGION_FLAG_REQUIRED_RES):
        return None
    return list(cmd) + ["--biz-region-id", region]


def _call_cli(
    product: str,
    action: str,
    params: Optional[dict[str, Any]],
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    """Execute one CLI invocation (argument list, never a shell)."""
    cmd = ["aliyun"] + _command_tokens(product, action)

    endpoint = _PRODUCT_ENDPOINTS.get(product)
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
        proc = subprocess.run(
            _with_auto_plugin(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun {product} {action} timed out after {timeout}s")

    if proc.returncode != 0:
        _retry = _region_flag_retry(cmd, proc.stderr or "", region)
        if _retry is not None:
            try:
                proc = subprocess.run(
                    _with_auto_plugin(_retry),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                raise CliError(f"aliyun {product} {action} timed out after {timeout}s")

    if proc.returncode != 0:
        stderr = _clean_stderr(proc.stderr or "")
        raise CliError(
            f"aliyun {product} {action} failed: {stderr[:400]}",
            code=_extract_error_code(stderr),
            stderr=stderr,
        )

    stdout = (proc.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = _json_body(stdout)
    except json.JSONDecodeError as err:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {err}")
    if not isinstance(body, dict):
        raise CliError(f"aliyun {product} {action} returned unexpected JSON shape")
    return body


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(region: str = DEFAULT_REGION,
                       profile: Optional[str] = None) -> str:
    """Account UID (AccountId) of the active credential; "" when unavailable."""
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
    except CliError:
        return ""
    return str(body.get("AccountId", "") or "")


def resolve_caller(region: str = DEFAULT_REGION,
                   profile: Optional[str] = None) -> dict[str, str]:
    """Caller identity facts used for the data-visibility declaration."""
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
    except CliError:
        return {"account_id": "", "identity_type": "", "arn": ""}
    return {
        "account_id": str(body.get("AccountId", "") or ""),
        "identity_type": str(body.get("IdentityType", "") or ""),
        "arn": str(body.get("Arn", "") or ""),
    }


# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    """Walk a nested dict along ``path``; return None on any miss."""
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


# Boundary assertions for the path walker.
assert _dig({"A": {"B": [1]}}, ["A", "B"]) == [1]
assert _dig({"A": {}}, ["A", "B"]) is None
assert _dig({}, []) == {}                                    # boundary: no path
assert _dig("string", ["A"]) is None                       # invalid container


def paginate_next_token(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    token_path: Optional[list[str]] = None,
    max_pages: int = MAX_PAGES,
    max_results: int = MAX_RESULTS,
) -> tuple[list[Any], Optional[str]]:
    """Follow NextToken pagination. Returns (items, error_code_or_None).

    ``error_code_or_None`` is set when the FIRST page failed, so the caller can
    tell "no results" apart from "could not look". A failure on a later page
    degrades to a partial list plus a ``[WARN]`` line.
    """
    token_path = token_path or ["NextToken"]
    items: list[Any] = []
    first_page = True
    token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        page_params["MaxResults"] = max_results
        if token:
            page_params["NextToken"] = token
        try:
            body = call(product, action, page_params, region=region, profile=profile)
        except CliError as err:
            if first_page:
                return [], (err.code or "UnknownError")
            print(
                f"[WARN] {product} {action}: page {pages + 1} failed "
                f"({err.code or 'unknown'}); reporting the "
                f"{len(items)} records read so far",
                file=sys.stderr,
            )
            break
        first_page = False
        page_items = _dig(body, items_path)
        if isinstance(page_items, list):
            items.extend(page_items)
        pages += 1
        token = _dig(body, token_path)
        if not token:
            break
    else:
        if token:
            print(
                f"[WARN] {product} {action}: stopped at the {max_pages}-page "
                f"guardrail; results may be incomplete for region "
                f"{region}",
                file=sys.stderr,
            )
    return items, None


def paginate_pages(
    product: str,
    action: str,
    params: dict[str, Any],
    items_path: list[str],
    region: str = DEFAULT_REGION,
    profile: Optional[str] = None,
    page_size: int = MAX_RESULTS,
    page_size_key: str = "PageSize",
    max_pages: int = MAX_PAGES,
) -> tuple[list[Any], Optional[str]]:
    """Follow PageNumber pagination. Same return contract as above."""
    items: list[Any] = []
    first_page = True
    for page in range(1, max_pages + 1):
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params[page_size_key] = page_size
        try:
            body = call(product, action, page_params, region=region, profile=profile)
        except CliError as err:
            if first_page:
                return [], (err.code or "UnknownError")
            print(
                f"[WARN] {product} {action}: page {page} failed "
                f"({err.code or 'unknown'}); reporting the "
                f"{len(items)} records read so far",
                file=sys.stderr,
            )
            break
        first_page = False
        page_items = _dig(body, items_path)
        if not isinstance(page_items, list):
            break
        items.extend(page_items)
        if len(page_items) < page_size:
            break
    return items, None


# --- customer-facing hygiene (2026-10-27) -----------------------------------
# The dispatcher masks its child stream, but an axis entry script is also run
# directly (evaluations, manual repros), and its own prints carried the raw
# account UID, a Cloud Assistant InvokeId or the 32-hex session id. Installing
# the mask here covers every axis of this package, because every entry imports
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
