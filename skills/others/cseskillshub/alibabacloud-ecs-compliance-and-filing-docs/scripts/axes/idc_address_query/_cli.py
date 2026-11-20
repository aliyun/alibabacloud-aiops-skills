#!/usr/bin/env python3
"""
_cli.py -- Shared, READ-ONLY aliyun-CLI layer for this skill.
=============================================================
SECURITY / SCOPE
    This module only issues read-only OpenAPI calls. It NEVER reads, prints,
    stores or transmits any credential material: authentication is resolved
    entirely by the aliyun CLI default credential chain. No access-key id or
    secret is ever passed on the command line by this code.

DESIGN CONTRACTS
    * Every call is a parameter-list subprocess.run(...) (never shell=True)
      with its own timeout -- platform MUST 7.6.1.
    * Observability (SA-2.11b/c): each CLI process run is tagged with a
      session User-Agent built from a 32-hex uuid4 value.
    * Transient errors (throttling / 5xx / timeouts) are retried with linear
      backoff; non-transient errors raise CliError.
    * All stderr / error text is credential-masked before it is surfaced.
    * Failures are reported to the caller as CliError; the entry script prints
      them as [WARN] to stderr and continues (degrade, do not abort).
"""

import json
import re
import subprocess
import time
import uuid

from _constants import (
    BACKOFF_BASE_SECONDS,
    DEFAULT_TIMEOUT,
    MAX_ATTEMPTS,
    SKILL_NAME,
)

# User-Agent template. {session_id} is a per-run 32-char hex value. This is
# the skill-level aggregation identity required by SA-2.11b/c.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"

# Error codes / fragments treated as transient and therefore retried.
_TRANSIENT_MARKERS = (
    "Throttling",
    "throttling",
    "ServiceUnavailable",
    "InternalError",
    "RequestTimeout",
    "SDK.HttpError",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
    "503",
    "500",
    "429",
)

# Best-effort scrub of anything that looks like a credential from text before
# it is surfaced or logged (defence in depth; this code never handles AK/SK).
_SECRET_RE = re.compile(
    r"(?i)(access[-_]?key[-_]?(?:id|secret)|security[-_]?token|accesskeysecret|"
    r"accesskeyid|password|signature)([\"'\s:=]+)(\S+)"
)


def make_session_id():
    """Return a fresh 32-character hex session id (uuid4) for a tool run."""
    return uuid.uuid4().hex


def user_agent_for(session_id):
    """Return the observability User-Agent string for a session id."""
    return USER_AGENT_TEMPLATE.format(skill=SKILL_NAME, session_id=session_id)

_user_agent_for_raw = user_agent_for



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
def user_agent_for(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_for_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


def mask_secrets(text):
    """Replace credential-looking values in text with ***."""
    if not text:
        return text
    return _SECRET_RE.sub(lambda m: m.group(1) + m.group(2) + "***", str(text))


class CliError(Exception):
    """Raised when a CLI invocation fails non-transiently or exhausts retries.

    Carries an error ``code`` (e.g. an OpenAPI error code) and a masked
    ``message``. ``transient`` marks whether the caller may treat it as retry
    noise. Authentication failures use the customer-facing literals
    ``NoPermission`` / ``ImplicitDeny`` (never the word used for a general
    HTTP 403 body)."""

    def __init__(self, code, message, transient=False):
        self.code = code or "CliError"
        self.message = mask_secrets(message or "")
        self.transient = transient
        super().__init__("%s: %s" % (self.code, self.message))


def _is_transient(code, message):
    blob = "%s %s" % (code or "", message or "")
    return any(marker in blob for marker in _TRANSIENT_MARKERS)


def _parse_error(stderr_text):
    """Extract an OpenAPI-style Code/Message from aliyun CLI error output."""
    text = stderr_text or ""
    code = ""
    message = ""
    m = re.search(r"(?:Code|ErrorCode)\s*:\s*(\S+)", text)
    if m:
        code = m.group(1)
    m = re.search(r"Message\s*:\s*(.+)", text)
    if m:
        message = m.group(1).strip()
    if not code:
        first = text.strip().splitlines()[0] if text.strip() else "CliError"
        code = first[:120]
    return code, (message or text.strip()[:400])


def run_cli(product, action, params=None, region=None,
            session_id=None, timeout=None):
    """Execute one read-only aliyun CLI call and return the parsed JSON body.

    ``product``   e.g. "ecs" (RPC product, PascalCase action) or "sts"
                  (plugin mode, lower-hyphen action such as
                  "GetCallerIdentity").
    ``action``    e.g. "DescribeInstances" or "GetCallerIdentity".
    ``params``    dict of CLI parameter name -> value (values coerced to str).
    ``region``    optional global --region selector.
    ``session_id`` observability id; generated here if omitted.
    Raises CliError on non-transient failure or after retries are exhausted.
    """
    timeout = timeout or DEFAULT_TIMEOUT
    session_id = session_id or make_session_id()

    cmd = ["aliyun", product, action]
    if region:
        cmd += ["--region", region]
    for key, value in (params or {}).items():
        if value is None:
            continue
        cmd += ["--" + key, str(value)]
    cmd += ["--user-agent", user_agent_for(session_id)]

    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_err = CliError("RequestTimeout",
                                "CLI call timed out after %ss" % timeout,
                                transient=True)
        except FileNotFoundError:
            # aliyun CLI not installed -- not transient, surface clearly.
            raise CliError(
                "CliNotInstalled",
                "The aliyun CLI executable was not found; install it and run "
                "'aliyun configure' using the default credential chain.",
            )
        else:
            if proc.returncode == 0:
                try:
                    return json.loads(proc.stdout or "{}")
                except (ValueError, TypeError) as exc:
                    raise CliError("BadResponse",
                                   "Could not parse CLI JSON output: %s" % exc)
            code, message = _parse_error(proc.stderr or proc.stdout)
            transient = _is_transient(code, message)
            last_err = CliError(code, message, transient=transient)
            if not transient:
                raise last_err

        if attempt < MAX_ATTEMPTS and last_err and last_err.transient:
            time.sleep(BACKOFF_BASE_SECONDS * attempt)

    raise last_err if last_err else CliError("Unknown", "CLI call failed")


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
