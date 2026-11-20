#!/usr/bin/env python3
"""
_cli.py -- Shared aliyun-CLI invocation layer for the ECS compliance guide
==========================================================================
SECURITY: This skill is strictly READ-ONLY. All authentication is resolved
by the aliyun CLI default credential chain (environment or ~/.aliyun
profile). This module NEVER reads, writes, caches or logs any access key,
secret key or session token. No credential handling exists anywhere here.

Internal module (prefixed with `_`). Do NOT run directly: it is imported by
compliance_inventory.py so that every Alibaba Cloud OpenAPI access goes
through ONE guarded place.

Guarantees implemented here
---------------------------
1. API WHITELIST GUARD: only the actions in _constants.WHITELISTED_ACTIONS
   (the two verified read queries, product `ecs`, version 2014-05-26) can
   ever reach the subprocess; any other action raises immediately.
2. Argument-list subprocess only (never a shell string), per-call timeout
   (platform rule 7.6.1), stdin detached from any interactive prompt.
3. Observability (KB SA-2.11b/c): a 32-char hex session id is generated
   once per run (uuid4().hex) and attached as
   --user-agent AlibabaCloud-Agent-Skills/<skill-name>/<session-id>
   to EVERY CLI call of the run.
4. Transient-error retry with linear backoff; permanent errors raise.
5. Credential masking on every error string that could surface (codes and
   messages are also scrubbed of key/token values).
6. CliError carries `Code: Message` semantics; callers degrade with [WARN].
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
    BACKOFF_BASE_SECONDS,
    CLI_MAX_ATTEMPTS,
    DEFAULT_TIMEOUT,
    ECS_API_VERSION,
    ECS_PRODUCT,
    MAX_PAGES,
    PERMISSION_MARKERS,
    SKILL_NAME,
    TRANSIENT_MARKERS,
    WHITELISTED_ACTIONS,
)

# The two whitelisted actions are the whole API surface of this skill;
# ECS regional endpoint resolution is delegated to the aliyun CLI itself.
_CLI_TIMEOUT_SECONDS = DEFAULT_TIMEOUT


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails or is refused by the guard."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr

    @property
    def is_permission(self) -> bool:
        """True when the failure looks like a RAM grant gap (NoPermission /
        ImplicitDeny family literals; matched case-insensitively)."""
        return _matches(self.code, PERMISSION_MARKERS)


def _matches(text: str, markers) -> bool:
    low = (text or "").lower()
    return any(marker in low for marker in markers)


# ---------------------------------------------------------------------------
# Session id & User-Agent (observability, SA-2.11b/c)
# ---------------------------------------------------------------------------

_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the per-run 32-char hex session id (generated lazily, cached
    for the whole run so all calls of one diagnosis correlate)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_cli] session-id: ****{_SESSION_ID[-4:]}", file=sys.stderr)
    return _SESSION_ID


def user_agent() -> str:
    """The User-Agent attached to every API call of this run."""
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id()}"

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-compliance-and-filing-docs"


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
    """Ensure the aliyun CLI is installed; exit with guidance otherwise."""
    if shutil.which("aliyun") is None:
        print(
            "[ERROR] aliyun CLI not found. Install the Alibaba Cloud CLI "
            "3.x and configure it with `aliyun configure`; this skill never "
            "accepts credentials any other way.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Core guarded invocation
# ---------------------------------------------------------------------------

def call(action: str,
         params: Optional[dict[str, Any]] = None,
         region: str = "",
         profile: Optional[str] = None,
         timeout: int = _CLI_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Invoke one whitelisted ECS read action via the aliyun CLI.

    Command shape (built-in API metadata mode, PascalCase preserved):
        aliyun ecs <Action> --RegionId <region> ... \
            --user-agent AlibabaCloud-Agent-Skills/<skill>/<session-id>

    Raises:
        CliError: immediately for guard violations and permanent API errors;
            after CLI_MAX_ATTEMPTS tries for transient ones (throttling /
            5xx / timeout), with linear backoff.
    """
    if action not in WHITELISTED_ACTIONS:
        raise CliError(
            f"action '{action}' is outside this skill's read-only whitelist "
            f"{sorted(WHITELISTED_ACTIONS)} and was refused before any call",
            code="WhitelistRefused",
        )

    last_err: Optional[CliError] = None
    for attempt in range(1, CLI_MAX_ATTEMPTS + 1):
        try:
            return _call_cli(action, params, region, profile, timeout)
        except CliError as err:
            last_err = err
            if not _matches(str(err.code) + " " + str(err), TRANSIENT_MARKERS):
                raise
            if attempt >= CLI_MAX_ATTEMPTS:
                raise CliError(
                    f"ecs {action} failed after {attempt} attempts: {err}",
                    code=err.code, stderr=err.stderr,
                )
            wait_s = attempt * BACKOFF_BASE_SECONDS
            print(
                f"[WARN] ecs {action} transient error "
                f"({err.code or 'unknown'}); retry {attempt}/"
                f"{CLI_MAX_ATTEMPTS - 1} in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)
    raise last_err  # unreachable, keeps type checkers happy


def _call_cli(action: str,
              params: Optional[dict[str, Any]],
              region: str,
              profile: Optional[str],
              timeout: int) -> dict[str, Any]:
    """Execute exactly one CLI invocation (argument list, never a shell)."""
    cmd = ["aliyun", ECS_PRODUCT, action]
    if region:
        cmd += ["--RegionId", region, "--region", region]
    if profile:
        cmd += ["--profile", profile]
    cmd += ["--user-agent", user_agent()]
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        cmd += [f"--{key}", str(value)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # never hang on an interactive prompt
        )
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun ecs {action} timed out after {timeout}s",
                       code="ClientTimeout")

    if result.returncode != 0:
        stderr = _clean_stderr(result.stderr or "")
        raise CliError(
            f"aliyun ecs {action} failed: {stderr[:300]}",
            code=_extract_error_code(stderr),
            stderr=stderr,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        body = json.loads(stdout)
    except json.JSONDecodeError as err:
        raise CliError(f"aliyun ecs {action} returned non-JSON output: {err}",
                       code="BadResponse")
    if not isinstance(body, dict):
        raise CliError(f"aliyun ecs {action} returned a non-object payload",
                       code="BadResponse")
    # Defensive: some RPC envelopes report request-level failures inside a
    # 200 body; a non-Success Code there is an invocation failure.
    resp_code = str(body.get("Code") or "").strip()
    if resp_code and resp_code not in ("Success", "OK", "200"):
        message = _clean_stderr(str(body.get("Message") or ""))
        raise CliError(
            f"aliyun ecs {action} failed: Code={resp_code} "
            f"Message={message[:300]}",
            code=resp_code, stderr=message,
        )
    return body


# ---------------------------------------------------------------------------
# Error-text hygiene: ANSI strip + credential masking + code extraction
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_ERROR_CODE_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*$")

# Any <credentialKey>=<value> or "<credentialKey>":"<value>" pair is masked
# before error text can reach stderr, a CliError message, or a report field.
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|sessiontoken|"
    r"signature|signaturenonce)"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)")


def _mask_credentials(text: str) -> str:
    """Replace credential VALUES with *** (key names kept for diagnosability).
    Pure function; never raises."""
    if not text:
        return text or ""
    return _CREDENTIAL_VALUE_RE.sub(lambda m: f"{m.group(1)}=***", text)


def _clean_stderr(stderr: str) -> str:
    """Single choke point for every CLI stderr string."""
    text = _ANSI_RE.sub("", stderr or "")
    text = _mask_credentials(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_error_code(stderr: str) -> str:
    """Best-effort API error-code extraction from CLI failure text.

    Handles the CLI 3.x SDKError envelope (indented 'Code: <X>' lines and
    inline 'Data: {...}' JSON) plus the legacy 'ERROR: <Code>: <Message>'.
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


# Import-time self-check of the masking choke point: if these assertions
# ever fail, error text could leak credential values into reports.
assert "STS.NYfakeKey1" not in _clean_stderr(
    "GET https://ecs.aliyuncs.com/?AccessKeyId=STS.NYfakeKey1"
    "&Signature=abcd1234ef"), "credential masking is broken"
assert "AccessKeyId=***" in _clean_stderr("AccessKeyId = SHOULD_NOT_APPEAR")
assert _clean_stderr(None) == ""


# ---------------------------------------------------------------------------
# Pagination helpers (both shapes used by this skill)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def paginate_next_token(action: str,
                        params: dict[str, Any],
                        region: str,
                        items_path: list[str],
                        profile: Optional[str] = None,
                        page_size: int = 100,
                        max_pages: int = MAX_PAGES) -> list[Any]:
    """Walk a NextToken-style list query to exhaustion (guarded)."""
    items: list[Any] = []
    token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        page_params["MaxResults"] = page_size
        if token:
            page_params["NextToken"] = token
        body = call(action, page_params, region=region, profile=profile)
        chunk = _dig(body, items_path)
        if isinstance(chunk, list):
            items.extend(chunk)
        pages += 1
        token = body.get("NextToken")
        if not token:
            break
    if pages >= max_pages and token:
        print(f"[WARN] ecs {action}: stopped at the {max_pages}-page "
              f"guardrail; results may be incomplete", file=sys.stderr)
    return items


def paginate_page_number(action: str,
                         params: dict[str, Any],
                         region: str,
                         items_path: list[str],
                         profile: Optional[str] = None,
                         page_size: int = 100,
                         max_pages: int = MAX_PAGES) -> list[Any]:
    """Walk a PageNumber/PageSize-style list query to exhaustion (guarded)."""
    items: list[Any] = []
    total: Optional[int] = None
    for page in range(1, max_pages + 1):
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = page_size
        body = call(action, page_params, region=region, profile=profile)
        chunk = _dig(body, items_path)
        if isinstance(chunk, list):
            items.extend(chunk)
        if total is None:
            try:
                total = int(body.get("TotalCount") or 0)
            except (TypeError, ValueError):
                total = 0
        if not chunk or (total and len(items) >= total):
            break
    return items


def api_version_note() -> str:
    """Human-readable API identity for report headers (no inference)."""
    return f"{ECS_PRODUCT} / {ECS_API_VERSION}"


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
