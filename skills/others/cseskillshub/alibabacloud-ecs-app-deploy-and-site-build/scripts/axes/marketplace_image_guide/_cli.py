"""Shared Alibaba Cloud CLI transport layer for this skill.

Responsibilities
  * one place that builds the CLI command line, as an argument list (never a shell
    string), so no request is ever composed with shell interpolation;
  * a per-run session identifier and the AlibabaCloud-Agent-Skills User-Agent that is
    attached to every single call, for observability;
  * a bounded timeout on every subprocess call, backoff retry for transient errors;
  * credential masking on anything that leaves this module towards stderr;
  * a CliError that carries "Code: Message" so callers can degrade instead of guess.

Only the read-only Describe actions listed in references/ram-policies.md are reached
through this layer. Credentials come from the default credential chain; this module
never reads, accepts, prints or transmits an access key pair.
"""

import json
import re
import subprocess
import sys
import time
import uuid

import _constants as C


class CliError(Exception):
    """A CLI or API failure, carrying the remote error code when available."""

    def __init__(self, code, message, action=""):
        Exception.__init__(self, "{0}: {1}".format(code, message))
        self.code = code or "CliError"
        self.message = message or ""
        self.action = action or ""

    def __str__(self):
        if self.action:
            return "{0} -> {1}: {2}".format(self.action, self.code, self.message)
        return "{0}: {1}".format(self.code, self.message)


# ------------------------------------------------------------------ identity
def new_session_id():
    """32-character hex identifier, one per skill run."""
    return uuid.uuid4().hex


def user_agent(session_id):
    """User-Agent template: AlibabaCloud-Agent-Skills/<skill>/<session-id>."""
    return "{0}/{1}/{2}".format(C.UA_PREFIX, C.SKILL_NAME, session_id or new_session_id())

_user_agent_raw = user_agent



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
def user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


# The CLI flag that carries the observability User-Agent.
UA_FLAG = "--user-agent"


# ------------------------------------------------------------------ masking
_SECRET_RE = re.compile(
    r"(?i)(access[\s_-]?key[\s_-]?(?:id|secret)|security[\s_-]?token|signature|"
    r"password|secret|token|credential)([\"'\s:=]+)([^\s,;\"'}\\]+)"
)


def mask_secrets(text):
    """Redact anything that looks like a credential before it is surfaced."""
    if not text:
        return ""
    def _sub(match):
        return "{0}{1}***".format(match.group(1), match.group(2))
    return _SECRET_RE.sub(_sub, str(text))


def warn(message):
    """Non-fatal note for the operator channel; masked, never fatal."""
    sys.stderr.write("[WARN] {0}\n".format(mask_secrets(message)))
    sys.stderr.flush()


# ------------------------------------------------------------------- errors
def _error_from_text(text):
    body = (text or "").strip()
    if not body:
        return "UnknownError", "empty error output"
    match = re.search(r"ErrorCode:\s*([A-Za-z0-9_.\-]+)", body)
    code = match.group(1) if match else ""
    if not code:
        match = re.search(r"^\s*(?:ERROR:\s*)?([A-Za-z][A-Za-z0-9_.\-]*Error)\b", body)
        code = match.group(1) if match else "CliError"
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    message = ""
    for line in lines:
        if code and line.startswith("ErrorCode:"):
            continue
        if line.upper().startswith(code.upper()):
            continue
        message = line
        break
    return code, mask_secrets(message or body)[:500]


def is_retryable(error):
    """True for throttling, service-side and transport timeouts only."""
    if not isinstance(error, CliError):
        return False
    code = (error.code or "")
    if code in C.RETRYABLE_CODES:
        return True
    if code.startswith("Throttling"):
        return True
    if code in ("Timeout", "CliNotFound", "NoOutput"):
        return True
    return bool(re.search(r"\b5[0-9]{2}\b", error.message or ""))


# ------------------------------------------------------------------ calling
def _stringify(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return json.dumps(list(value), separators=(",", ":"))
    return str(value)


def build_argv(action, params=None, session_id=None, product=None):
    """Compose the argv list for one read-only call."""
    argv = [C.CLI_BINARY, product or C.PRODUCT_ECS, action]
    for key in sorted(params or {}):
        value = params[key]
        if value is None:
            continue
        argv += ["--{0}".format(key), _stringify(value)]
    # Appended last and never sourced from params, so a caller cannot override it.
    argv += [UA_FLAG, user_agent(session_id)]
    return argv


def call(action, params=None, session_id=None, product=None, timeout=None,
         retries=None):
    """Run one read-only CLI action and return the parsed JSON body.

    Raises CliError when every attempt failed. Callers are expected to catch it,
    emit a degraded note and continue with the rest of the report.
    """
    if action not in C.READ_ACTIONS and action != C.STS_ACTION_CALLER_IDENTITY:
        raise CliError("BlockedAction",
                       "action is not in the read-only whitelist: {0}".format(action),
                       action)
    budget = C.MAX_RETRIES if retries is None else max(1, int(retries))
    limit = C.CALL_TIMEOUT_SECONDS if timeout is None else timeout
    last = None
    for attempt in range(1, budget + 1):
        argv = build_argv(action, params, session_id, product)
        try:
            proc = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=limit,
                universal_newlines=True,
            )
        except subprocess.TimeoutExpired:
            last = CliError("Timeout",
                            "call exceeded {0}s on attempt {1}".format(limit, attempt),
                            action)
        except OSError as exc:
            # Binary missing or not executable: retrying cannot help.
            raise CliError("CliNotFound", mask_secrets(exc), action)
        else:
            if proc.returncode == 0:
                text = (proc.stdout or "").strip()
                if not text:
                    return {}
                try:
                    return json.loads(text)
                except ValueError as exc:
                    raise CliError("BadOutput", mask_secrets(exc), action)
            code, message = _error_from_text(proc.stderr or proc.stdout)
            last = CliError(code, message, action)
            if not is_retryable(last):
                raise last
        if attempt < budget:
            time.sleep(C.BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
            warn("retrying {0} (attempt {1}): {2}".format(action, attempt + 1, last))
    raise last


# ----------------------------------------------------------- parse helpers
def unwrap(node):
    """Return a list of dicts for a response node that may be dict/list/None."""
    if node is None:
        return []
    if isinstance(node, list):
        return [item for item in node if isinstance(item, dict)]
    if isinstance(node, dict):
        return [node]
    return []


def pick(mapping, keys, default=""):
    """First present key from a candidate list; tolerant of casing drift."""
    if not isinstance(mapping, dict):
        return default
    lowered = dict((str(k).lower(), v) for k, v in mapping.items())
    for key in keys:
        value = mapping.get(key, lowered.get(str(key).lower()))
        if value not in (None, ""):
            return value
    return default


def text(value):
    return "" if value is None else str(value)


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
