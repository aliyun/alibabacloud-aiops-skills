"""Shared aliyun-CLI transport layer for the snapshot I/O impact skill.

Responsibilities
    * Build argument-list invocations (never a shell string) for the aliyun CLI.
    * Attach one observability session id per run to every call via the
      ``--user-agent`` flag, built from the template
      AlibabaCloud-Agent-Skills/{skill}/{session-id}.
    * Retry transient failures (throttling / server-side / timeout) with
      jittered backoff; raise everything else immediately.
    * Mask credential-shaped material out of any error text before it is
      surfaced on stderr, in a report or in a JSON field.
    * Enforce a per-call timeout so one slow request cannot hang the report.

Credentials always come from the default credential chain of the locally
configured CLI (environment or the CLI config file). This module never reads,
stores, prints or passes key material, and it never asks the customer for it.

Only actions the skill's registry allows may be sent: :func:`call` refuses any
(product, action) pair outside CLOUD_READ_ACTIONS plus the two confirmation-
gated actions, and the gated ones additionally require the caller to pass
``gated=True`` after the confirmation flow has completed.
"""

from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from _constants import (
    CLOUD_READ_ACTIONS,
    CLI_BACKOFF_BASE_SECONDS,
    CLI_BACKOFF_MAX_SECONDS,
    CLI_BINARY,
    CLI_MAX_RETRIES,
    CLI_TIMEOUT_SECONDS,
    CODE_API_ERROR,
    CODE_CLI_TIMEOUT,
    CODE_CLI_UNAVAILABLE,
    CODE_IMPLICIT_DENY,
    CODE_INVALID_CREDENTIAL,
    CODE_NO_PERMISSION,
    CODE_PARSE_ERROR,
    CREDENTIAL_ERROR_MARKERS,
    GATED_ACTIONS,
    MASKED_VALUE,
    NON_RETRYABLE_MARKERS,
    PLUGIN_MODE_COMMANDS,
    RETRYABLE_MARKERS,
    SENSITIVE_KEY_PATTERNS,
    SKILL_NAME,
    USER_AGENT_TEMPLATE,
)


class CliError(Exception):
    """A CLI or API failure rendered as ``Code: Message``."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        self.code = code
        self.message = mask_credentials(message)
        self.retryable = retryable
        super().__init__("{0}: {1}".format(self.code, self.message))


# ---------------------------------------------------------------------------
# Session id and User-Agent (observability)
# ---------------------------------------------------------------------------

def new_session_id() -> str:
    """Return a fresh 32-char lowercase hex id (one per skill run)."""
    return uuid.uuid4().hex


def build_user_agent(session_id: str) -> str:
    """Return the observability User-Agent string for this run."""
    return USER_AGENT_TEMPLATE.format_map(
        {"skill": SKILL_NAME, "session-id": session_id}
    )

_build_user_agent_raw = build_user_agent



_PACKAGE_NAME = "alibabacloud-ecs-snapshot-and-backup"


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
def build_user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_build_user_agent_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


# ---------------------------------------------------------------------------
# Credential masking (pure functions, boundary-asserted below)
# ---------------------------------------------------------------------------

_MASK_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SENSITIVE_KEY_PATTERNS]


def _masked_value(secret: str) -> str:
    """Return the masked stand-in for a secret value, keeping the quote
    character the value originally used so JSON-shaped payloads stay valid."""
    quote = secret[:1] if secret[:1] in ("\"", "'") else ""
    return quote + MASKED_VALUE + quote


def mask_credentials(text: Any) -> str:
    """Redact anything that looks like a credential pair from ``text``.

    ``key=value``, ``key: value`` and JSON ``"key": "value"`` spellings are all
    collapsed (the key's own surrounding quotes survive), and bare token-like
    strings following a sensitive key are dropped as well. The key name itself
    stays readable so an operator can still diagnose what leaked.
    """
    if text is None:
        return ""
    value = text if isinstance(text, str) else str(text)
    for pattern in _MASK_PATTERNS:
        value = re.sub(
            r"(?i)(" + pattern.pattern + r")(\"?\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&}]+)",
            lambda match: match.group(1) + match.group(2) + _masked_value(match.group(3)),
            value,
        )
        value = re.sub(
            r"(?i)(" + pattern.pattern + r")(\s+)(\"[^\"]*\"|'[^']*'|[A-Za-z0-9/+=_-]{8,})",
            lambda match: match.group(1) + match.group(2) + MASKED_VALUE,
            value,
        )
    return value


def classify_error(message: str) -> Tuple[str, bool]:
    """Map a raw failure message onto ``(error_code, retryable)``."""
    lowered = (message or "").lower()
    if CODE_IMPLICIT_DENY.lower() in lowered:
        return CODE_IMPLICIT_DENY, False
    if CODE_NO_PERMISSION.lower() in lowered or "accessdenied" in lowered:
        return CODE_NO_PERMISSION, False
    for marker in CREDENTIAL_ERROR_MARKERS:
        if marker in lowered:
            return CODE_INVALID_CREDENTIAL, False
    for marker in NON_RETRYABLE_MARKERS:
        if marker in lowered:
            return CODE_API_ERROR, False
    for marker in RETRYABLE_MARKERS:
        if marker in lowered:
            return CODE_API_ERROR, True
    return CODE_API_ERROR, False


# Inline boundary assertions for the two pure functions above (normal /
# boundary / invalid). A failure here means masking or classification is
# broken and the module must not run.
assert mask_credentials("plain error text") == "plain error text"
assert mask_credentials(None) == ""
assert mask_credentials("AccessKeyId=TESTFAKE000111222333") == "AccessKeyId=***"
assert mask_credentials('"AccessKeySecret": "TESTfake444555"') == '"AccessKeySecret": "***"'
assert mask_credentials("the value signature TESTSIG00111222333 was logged") != \
    "the value signature TESTSIG00111222333 was logged"
assert classify_error("") == (CODE_API_ERROR, False)
assert classify_error("Code: NoPermission.") == (CODE_NO_PERMISSION, False)
assert classify_error("Code: ImplicitDeny for this resource") == (CODE_IMPLICIT_DENY, False)
assert classify_error("Code: Throttling.User; try later") == (CODE_API_ERROR, True)
assert classify_error("Code: InternalError") == (CODE_API_ERROR, True)
assert classify_error("Code: InvalidAccessKeyId.NotFound") == (CODE_INVALID_CREDENTIAL, False)
assert classify_error("Code: InvalidParameter.RegionId") == (CODE_API_ERROR, False)


# ---------------------------------------------------------------------------
# Action registry guard
# ---------------------------------------------------------------------------

_ALLOWED_CALLS = {pair for pair in CLOUD_READ_ACTIONS}


def is_allowed(product: str, action: str, gated: bool = False) -> bool:
    """True when (product, action) is inside the skill's callable registry."""
    pair = (product.lower(), action)
    if pair in _ALLOWED_CALLS:
        return True
    return gated and pair in {pair for pair in GATED_ACTIONS}


# ---------------------------------------------------------------------------
# Command assembly and execution
# ---------------------------------------------------------------------------

def _action_token(product: str, action: str) -> str:
    """Resolve the CLI command form for an action.

    Plugin-style products use the lowercase-hyphenated subcommand, RPC-style
    products keep the PascalCase action name.
    """
    mapped = PLUGIN_MODE_COMMANDS.get((product.lower(), action))
    if mapped:
        return mapped
    return action


def build_command(
    product: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    session_id: str = "",
    profile: Optional[str] = None,
) -> List[str]:
    """Assemble the argv list for one CLI call, User-Agent included."""
    command = [CLI_BINARY, product, _action_token(product, action)]
    if profile:
        command.extend(["--profile", profile])
    for key in sorted((params or {}).keys()):
        value = (params or {})[key]
        if value is None or value == "":
            continue
        command.append("--{0}".format(key))
        command.append(str(value))
    command.append("--user-agent")
    command.append(build_user_agent(session_id))
    return command


def call(
    product: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    session_id: str = "",
    timeout: int = CLI_TIMEOUT_SECONDS,
    retries: int = CLI_MAX_RETRIES,
    profile: Optional[str] = None,
    gated: bool = False,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute one CLI call and return the decoded JSON payload.

    Transient failures are retried with jittered backoff. Any other failure
    raises :class:`CliError` carrying a ``Code: Message`` payload. The
    registry guard rejects any action this skill may not call.
    """
    if not is_allowed(product, action, gated=gated):
        raise CliError(
            CODE_API_ERROR,
            "action {0} {1} is outside this skill's callable registry".format(product, action),
            retryable=False,
        )
    if not session_id:
        session_id = new_session_id()
    params = dict(params or {})
    command = build_command(product, action, params, session_id, profile)
    last_error: Optional[CliError] = None

    for attempt in range(1, max(1, retries) + 1):
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
                universal_newlines=True,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError(
                CODE_CLI_TIMEOUT,
                "{0} {1} did not return within {2}s".format(product, action, timeout),
                retryable=True,
            )
            if warnings is not None:
                warnings.append(
                    "retry {0}/{1} after a {2}s timeout on {3} {4}".format(
                        attempt, retries, timeout, product, action
                    )
                )
            time.sleep(_backoff(attempt))
            continue
        except FileNotFoundError:
            raise CliError(
                CODE_CLI_UNAVAILABLE,
                "the aliyun CLI was not found on PATH; install it and configure "
                "credentials with aliyun configure (this skill never accepts key material)",
                retryable=False,
            )
        except OSError as exc:  # pragma: no cover - environment specific
            raise CliError(CODE_CLI_UNAVAILABLE, mask_credentials(exc), retryable=False)

        if completed.returncode == 0:
            stdout = completed.stdout or ""
            stderr = mask_credentials(completed.stderr or "")
            if stderr.strip() and warnings is not None:
                warnings.append(
                    "cli notice from {0} {1}: {2}".format(product, action, stderr.strip())
                )
            return parse_payload(stdout, product, action)

        detail = mask_credentials(
            (completed.stderr or "") + " " + (completed.stdout or "")
        ).strip()
        code, retryable = classify_error(detail)
        last_error = CliError(
            code, "{0} {1} failed: {2}".format(product, action, detail), retryable
        )
        if not retryable:
            raise last_error
        if warnings is not None:
            warnings.append(
                "retry {0}/{1} after transient failure on {2} {3}".format(
                    attempt, retries, product, action
                )
            )
        time.sleep(_backoff(attempt))

    assert last_error is not None
    raise last_error


def call_soft(
    product: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    session_id: str = "",
    timeout: int = CLI_TIMEOUT_SECONDS,
    profile: Optional[str] = None,
    gated: bool = False,
    warnings: Optional[List[str]] = None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Same as :func:`call` but degrade instead of raising.

    Returns ``(payload, "")`` on success and ``(None, masked error text)`` on
    failure; a degradation is always also appended to ``warnings``.
    """
    try:
        payload = call(
            product, action, params, session_id=session_id, timeout=timeout,
            profile=profile, gated=gated, warnings=warnings,
        )
        return payload, ""
    except CliError as exc:
        message = mask_credentials(str(exc))
        if warnings is not None:
            warnings.append("degraded call {0} {1}: {2}".format(product, action, message))
        return None, message


def check_cli_available() -> None:
    """Ensure the aliyun CLI exists; exit with guidance when it does not."""
    if shutil.which(CLI_BINARY) is None:
        print(
            "[FAIL] the aliyun CLI was not found on PATH. Install it and run "
            "aliyun configure; this skill resolves credentials from the default "
            "chain only.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def _backoff(attempt: int) -> float:
    """Exponential backoff with jitter, capped by CLI_BACKOFF_MAX_SECONDS."""
    delay = CLI_BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1))
    delay = min(delay, CLI_BACKOFF_MAX_SECONDS)
    return delay * (0.7 + 0.6 * random.random())


# ---------------------------------------------------------------------------
# Payload parsing helpers
# ---------------------------------------------------------------------------

def parse_payload(stdout: str, product: str, action: str) -> Dict[str, Any]:
    """Decode the JSON body printed by the CLI, tolerating stray log noise."""
    text = (stdout or "").strip()
    if not text:
        return {}
    start = _first_json_offset(text)
    if start is None:
        raise CliError(
            CODE_PARSE_ERROR,
            "{0} {1} returned no parsable JSON body".format(product, action),
            retryable=False,
        )
    try:
        decoded, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError as exc:
        raise CliError(
            CODE_PARSE_ERROR,
            mask_credentials("{0} {1} returned malformed JSON: {2}".format(product, action, exc)),
            retryable=False,
        )
    if isinstance(decoded, list):
        return {"items": decoded}
    if isinstance(decoded, dict):
        _raise_on_error_body(decoded, product, action)
        return decoded
    return {"value": decoded}


def _raise_on_error_body(body: Dict[str, Any], product: str, action: str) -> None:
    """Treat an in-body error Code as an invocation failure.

    Several RPC products report request-level failures inside a JSON body
    while the CLI still exits 0. Success codes are explicitly whitelisted so
    the happy path is untouched; an unknown non-empty Code raises through the
    standard CliError path instead of being read as data.
    """
    code = str(body.get("Code") or "").strip()
    if not code or code.lower() in ("success", "ok", "200"):
        return
    message = mask_credentials(str(body.get("Message") or ""))
    mapped, retryable = classify_error("{0} {1}".format(code, message))
    raise CliError(
        mapped or CODE_API_ERROR,
        "{0} {1} failed in-body: {2}: {3}".format(product, action, code, message[:300]),
        retryable,
    )


def _first_json_offset(text: str) -> Optional[int]:
    offsets = [index for index in (text.find("{"), text.find("[")) if index != -1]
    if not offsets:
        return None
    return min(offsets)


def dig(payload: Any, *keys: str) -> Any:
    """Walk nested dicts along ``keys``; return None on any miss."""
    node = payload
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def as_list(payload: Any, *keys: str) -> List[Dict[str, Any]]:
    """Extract a nested item list (RPC envelope shape {"A": {"B": [..]}})."""
    node = dig(payload, *keys) if keys else payload
    if isinstance(node, dict) and keys:
        node = node.get(keys[-1])
    if isinstance(node, list):
        return [item for item in node if isinstance(item, dict)]
    return []


def parse_datapoints(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Decode the CloudMonitor Datapoints JSON string into a list."""
    raw = dig(payload or {}, "Datapoints")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if not raw:
        return []
    try:
        decoded = json.loads(str(raw))
    except ValueError:
        return []
    if isinstance(decoded, list):
        return [item for item in decoded if isinstance(item, dict)]
    return []


def paginate(
    product: str,
    action: str,
    base_params: Dict[str, Any],
    envelope_key: str,
    session_id: str,
    warnings: List[str],
    profile: Optional[str] = None,
    timeout: int = CLI_TIMEOUT_SECONDS,
    page_size: int = 50,
    max_pages: int = 10,
) -> Tuple[List[Dict[str, Any]], str]:
    """Page a list action with PageNumber/PageSize (guard-railed).

    Returns ``(items, token)`` where token is ``ok`` or ``truncated``.
    """
    items: List[Dict[str, Any]] = []
    page = 1
    total_seen = 0
    while page <= max_pages:
        params = dict(base_params)
        params["PageSize"] = page_size
        params["PageNumber"] = page
        payload, error = call_soft(
            product, action, params, session_id=session_id,
            profile=profile, timeout=timeout, warnings=warnings,
        )
        if error:
            return items, "error"
        batch = as_list(payload or {}, envelope_key, envelope_key[:-1] if envelope_key.endswith("s") else envelope_key)
        items.extend(batch)
        try:
            total_seen = int(dig(payload or {}, "TotalCount") or 0)
        except (TypeError, ValueError):
            total_seen = 0
        if not batch or len(batch) < page_size:
            return items, "ok"
        if total_seen and len(items) >= total_seen:
            return items, "ok"
        page += 1
    warnings.append(
        "stopped paging {0} {1} at the {2}-page guard; results may be incomplete".format(
            product, action, max_pages
        )
    )
    return items, "truncated"


# ---------------------------------------------------------------------------
# Identity helper
# ---------------------------------------------------------------------------

def resolve_account_id(session_id: str = "", profile: Optional[str] = None) -> Tuple[str, str]:
    """Return ``(account_id, error_message)`` for the ambient credential."""
    payload, error = call_soft(
        "sts", "GetCallerIdentity", {}, session_id=session_id, profile=profile,
    )
    if error:
        return "", error
    return str(dig(payload or {}, "AccountId") or ""), ""


def warn(lines: Sequence[str], message: str) -> None:
    """Append a degradation line and echo it to stderr as ``[WARN]``."""
    masked = mask_credentials(message)
    lines.append(masked)
    print("[WARN] {0}".format(masked), file=sys.stderr)


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
