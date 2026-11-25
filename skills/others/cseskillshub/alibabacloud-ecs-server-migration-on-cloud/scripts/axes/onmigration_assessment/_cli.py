"""Shared layer for every aliyun CLI call made by this skill.

Responsibilities:
  * one CLI invocation per action, built as an argument list (never a shell string)
  * a per-run session id that is attached to every call as a User-Agent
  * bounded retries for transient failures, with a hard timeout on every call
  * credential masking on all error text
"""

import json
import random
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    ALIYUN_BIN,
    ALLOWED_ACTIONS,
    BACKOFF_BASE_SECONDS,
    BACKOFF_JITTER_SECONDS,
    CLI_TIMEOUT_SECONDS,
    MAX_ATTEMPTS,
    SECRET_PATTERN,
    SKILL_NAME,
    TRANSIENT_ERROR_CODES,
    TRANSIENT_MESSAGE_FRAGMENTS,
    USER_AGENT_PREFIX,
    USER_AGENT_TEMPLATE,
)

_SECRET_RE = re.compile(SECRET_PATTERN)


class CliError(Exception):
    """A CLI or API failure, carrying the API `Code: Message` pair."""

    def __init__(self, code, message, action="", attempt=0):
        self.code = code
        self.message = mask_secrets(message)
        self.action = action
        self.attempt = attempt
        super().__init__("{}: {}".format(self.code, self.message))


def mask_secrets(text):
    """Replace credential-looking substrings so they never reach an operator."""
    if not text:
        return ""
    return _SECRET_RE.sub(lambda m: "{}***".format(m.group(1)), str(text))


def new_session_id():
    """32 hex characters, stable for the whole script run."""
    return uuid.uuid4().hex


def build_user_agent(session_id):
    return USER_AGENT_TEMPLATE.format(
        prefix=USER_AGENT_PREFIX, skill=SKILL_NAME, session_id=session_id
    )

_build_user_agent_raw = build_user_agent



_PACKAGE_NAME = "alibabacloud-ecs-server-migration-on-cloud"


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


def is_transient(code, message):
    if code in TRANSIENT_ERROR_CODES:
        return True
    lowered = (message or "").lower()
    return any(fragment in lowered for fragment in TRANSIENT_MESSAGE_FRAGMENTS)


def build_argv(product, action, params=None, session_id="", cli_action=None):
    """Compose the argument list for one RPC-style aliyun CLI call.

    The product's API version comes from the CLI's own metadata; the version
    this skill was verified against is declared in `related_apis.yaml`.
    `cli_action` overrides the CLI token (plugin-mode products take a
    lowercase-hyphen action) without changing the canonical allow-list name.
    """
    argv = [ALIYUN_BIN, product, cli_action or action]
    for key, value in (params or {}).items():
        if value is None or value == "":
            continue
        argv += ["--{}".format(key), str(value)]
    argv += ["--user-agent", build_user_agent(session_id or new_session_id())]
    return argv


def _parse_json(stdout):
    try:
        return json.loads(stdout)
    except (TypeError, ValueError):
        return None


def _error_from_output(stdout, stderr, returncode):
    """Extract an API Code/Message pair from CLI output, if present."""
    payload = _parse_json(stdout)
    if isinstance(payload, dict):
        code = payload.get("Code") or payload.get("code")
        if code:
            return str(code), str(payload.get("Message") or payload.get("message") or "")
    text = "\n".join(blob for blob in (stderr, stdout) if blob)
    code_match = re.search(r"(?:ErrorCode|Code)\s*:\s*([A-Za-z0-9._\-]+)", text)
    message_match = re.search(r"Message\s*:\s*(.+)", text)
    if code_match:
        detail = message_match.group(1) if message_match else text
        return code_match.group(1), mask_secrets(detail.strip())
    if "is not a valid api" in text:
        return "InvalidApi", mask_secrets(text.strip())
    if text.strip():
        return "CliExit{}".format(returncode), mask_secrets(text.strip())
    return "UnknownError", "aliyun CLI exited with {}".format(returncode)


def call_cli(product, action, params=None, session_id="", timeout=CLI_TIMEOUT_SECONDS,
             max_attempts=MAX_ATTEMPTS, stream=None, cli_action=None):
    """Run one CLI action and return its decoded JSON payload.

    Returns a dict on success. Retries transient failures with backoff and
    raises CliError for anything else. Every failed attempt is logged once.
    """
    if "{}:{}".format(product, action) not in ALLOWED_ACTIONS:
        _warn(stream, product, action, 0, "ActionNotAllowed",
              "outside this skill's allow-list")
        raise CliError("ActionNotAllowed",
                       "{}:{} is outside this skill's allow-list".format(product, action),
                       action=action)
    argv = build_argv(product, action, params=params, session_id=session_id,
                      cli_action=cli_action)
    last_code, last_message = "", ""
    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_code, last_message = "CliTimeout", "call timed out after {}s".format(timeout)
            _warn(stream, product, action, attempt, last_code, last_message)
            _sleep_backoff(attempt)
            continue
        except OSError as exc:
            raise CliError("CliNotAvailable", mask_secrets(exc), action=action, attempt=attempt)

        if completed.returncode == 0:
            payload = _parse_json(completed.stdout)
            if payload is None:
                raise CliError("UnparseableOutput", mask_secrets(completed.stdout[:500]),
                               action=action, attempt=attempt)
            return payload

        last_code, last_message = _error_from_output(
            completed.stdout, completed.stderr, completed.returncode)
        _warn(stream, product, action, attempt, last_code, last_message)
        if not is_transient(last_code, last_message):
            raise CliError(last_code, last_message, action=action, attempt=attempt)
        _sleep_backoff(attempt)

    raise CliError(last_code or "CliFailed", last_message or "retries exhausted",
                   action=action, attempt=max_attempts)


def describe(product, action, params=None, session_id="", timeout=CLI_TIMEOUT_SECONDS,
             stream=None, cli_action=None):
    """Call a query action and return None on failure; call_cli already logged the cause."""
    try:
        return call_cli(product, action, params=params, session_id=session_id,
                        timeout=timeout, stream=stream, cli_action=cli_action)
    except CliError:
        return None


def _warn(stream, product, action, attempt, code, message):
    sink = stream if stream is not None else sys.stderr
    sink.write("[WARN] {}.{} attempt {}: {} {}\n".format(
        product, action, attempt, code, mask_secrets(message)))
    try:
        sink.flush()
    except Exception:  # pragma: no cover - a broken stream must not hide the report
        pass


def _sleep_backoff(attempt):
    delay = BACKOFF_BASE_SECONDS ** attempt + random.uniform(0, BACKOFF_JITTER_SECONDS)
    time.sleep(min(delay, 12.0))


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
