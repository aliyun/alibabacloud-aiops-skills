"""Shared aliyun-CLI layer for this skill.

Guarantees provided to every caller:
  * argument lists only (never a shell string), stdin detached, per-call timeout;
  * one 32-char hex session id per run, attached as the user agent on every call;
  * bounded retry with backoff for transient failures only;
  * credential masking on all error text;
  * a hard read-only whitelist: an action outside the whitelist is refused.

Credentials always come from the default credential chain of the aliyun CLI.
This module never reads, writes, prints or forwards an AccessKey pair.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    AUTH_DENIED_MARKERS,
    CLI_TIMEOUT_SECONDS,
    IDENTITY_TIMEOUT_SECONDS,
    READ_ONLY_ACTIONS,
    RETRY_BACKOFF_BASE_SECONDS,
    RETRY_MAX_ATTEMPTS,
    RETRYABLE_HTTP_STATUS,
    RETRYABLE_MARKERS,
    STS_IDENTITY_COMMAND,
    USER_AGENT_TEMPLATE,
)

_MASK_PATTERN = re.compile(
    r"(?i)\b(accesskeyid|access_key_id|accesskeysecret|access_key_secret|"
    r"securitytoken|security_token|password|signature)\b(\s*[=:]\s*)\S+"
)


class CliError(Exception):
    """A CLI failure rendered as `Code: Message`."""

    def __init__(self, code, message, retryable=False, stdout=""):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.retryable = retryable
        self.stdout = stdout

    def is_permission_denied(self):
        blob = f"{self.code} {self.message}".lower()
        return any(marker.lower() in blob for marker in AUTH_DENIED_MARKERS)


def new_session_id():
    """Return the per-run 32-char hex observability token."""
    return uuid.uuid4().hex


def user_agent_for(session_id):
    return USER_AGENT_TEMPLATE.format(session_id=session_id)

_user_agent_for_raw = user_agent_for



_PACKAGE_NAME = "alibabacloud-ecs-app-deploy-and-site-build"


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
def user_agent_for(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_for_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


def mask_credentials(text):
    """Redact credential-looking values before any text leaves this module."""
    return _MASK_PATTERN.sub(r"\1\2***", text or "")


def _classify_failure(stdout, stderr, returncode):
    blob = f"{stdout}\n{stderr}"
    code = f"CliExit{returncode}"
    message = stderr.strip() or stdout.strip() or "aliyun CLI returned no output"
    for line in blob.splitlines():
        match = re.search(r"([A-Za-z][A-Za-z0-9._-]{2,}(?:\.[A-Za-z][A-Za-z0-9._-]+)*)\s*:", line)
        if match and any(token in line for token in ("Code", "ERROR", "ErrorCode")):
            code = match.group(1)
            message = line.strip()
            break
    retryable = any(marker.lower() in blob.lower() for marker in RETRYABLE_MARKERS)
    retryable = retryable or any(status in blob for status in RETRYABLE_HTTP_STATUS)
    return code, mask_credentials(message), retryable


def _sleep_backoff(attempt):
    time.sleep(RETRY_BACKOFF_BASE_SECONDS * attempt)


def _warn(error, attempt):
    print(
        f"[WARN] attempt {attempt}/{RETRY_MAX_ATTEMPTS}: {error}",
        file=sys.stderr,
    )


def run_aliyun(argv, session_id, timeout=CLI_TIMEOUT_SECONDS, label=""):
    """Execute one aliyun CLI call and return its parsed JSON payload.

    `argv` is the base command, for example
    ["aliyun", "ecs", "DescribeImages", "--RegionId", "cn-hangzhou"].
    The skill user agent is appended so the call is traceable server side.
    """
    command = list(argv) + ["--user-agent", user_agent_for(session_id)]
    last_error = None
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError(
                "CliTimeout",
                f"{label or ' '.join(argv[:3])} exceeded {timeout}s on attempt {attempt}",
                retryable=True,
            )
            _warn(last_error, attempt)
            _sleep_backoff(attempt)
            continue
        except OSError as exc:
            raise CliError(
                "CliUnavailable",
                mask_credentials(
                    f"aliyun CLI could not be started: {exc}; run `aliyun configure` "
                    "with the default credential chain"
                ),
            ) from exc

        if proc.returncode == 0:
            stdout = proc.stdout or ""
            if proc.stderr and proc.stderr.strip():
                _warn(CliError("CliStderr", mask_credentials(proc.stderr.strip())), attempt)
            if not stdout.strip():
                return {}
            try:
                return json.loads(stdout)
            except ValueError as exc:
                raise CliError(
                    "CliUnparsableOutput",
                    mask_credentials(f"expected JSON, got: {stdout[:400]} ({exc})"),
                ) from exc

        code, message, retryable = _classify_failure(proc.stdout, proc.stderr, proc.returncode)
        last_error = CliError(code, message, retryable=retryable, stdout=proc.stdout or "")
        if not retryable:
            raise last_error
        _warn(last_error, attempt)
        _sleep_backoff(attempt)

    raise last_error or CliError("CliFailed", "aliyun CLI call did not complete")


def call_ecs_read(session_id, action, region_id, params=None, timeout=CLI_TIMEOUT_SECONDS):
    """Invoke one whitelisted read-only ECS action (product ecs, version 2014-05-26)."""
    if action not in READ_ONLY_ACTIONS:
        raise CliError(
            "ReadOnlyWhitelistViolation",
            f"'{action}' is not one of the read-only actions {list(READ_ONLY_ACTIONS)}; "
            "this skill never calls it",
        )
    argv = ["aliyun", "ecs", action, "--RegionId", region_id]
    for key, value in (params or {}).items():
        if value is None or value == "":
            continue
        argv.extend([f"--{key}", str(value)])
    return run_aliyun(argv, session_id, timeout=timeout, label=action)


def call_caller_identity(session_id, timeout=IDENTITY_TIMEOUT_SECONDS):
    """Resolve the caller identity using the plugin-mode lowercase-hyphenated form."""
    argv = ["aliyun", "sts", STS_IDENTITY_COMMAND]
    return run_aliyun(argv, session_id, timeout=timeout, label="caller identity")


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
