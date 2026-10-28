"""Thin, observable wrapper around the ``aliyun`` CLI.

Responsibilities
    * build argv lists (never a shell string) and run them with a timeout
    * tag every single invocation with a per-run User-Agent session id
    * retry transient failures with backoff, fail fast otherwise
    * mask credential material before any error text leaves this module

Callers get parsed JSON back, or a :class:`CliError`. The RPC API versions each
action belongs to are recorded in ``related_apis.yaml`` and echoed in reports;
the CLI resolves routing from the product and action name itself.
"""

import base64
import json
import re
import subprocess
import sys
import time
import uuid

import _constants as C

# One session id per process, reused by every invocation so that a whole run is
# traceable in one hop.
SESSION_ID = uuid.uuid4().hex


def user_agent() -> str:
    return C.USER_AGENT_TEMPLATE.format(skill=C.SKILL_NAME, session_id=SESSION_ID)

_user_agent_raw = user_agent



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
def user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


class CliError(Exception):
    """CLI or API failure carrying an ``Code: Message`` rendering."""

    def __init__(self, code, message, retried=False):
        super(CliError, self).__init__("{0}: {1}".format(code, message))
        self.code = code
        self.message = message
        self.retried = retried


def mask_secrets(text):
    """Redact anything that looks like credential material from ``text``."""
    if text is None:
        return ""
    masked = str(text)
    for key in C.SECRET_KEY_MARKERS:
        masked = re.sub(r"(?i)(\b{0}\b\s*[=:]\s*)(\S+)".format(key), r"\1***", masked)
        masked = re.sub(r"(?i)(--{0}\s+)(\S+)".format(key), r"\1***", masked)
    masked = re.sub(r"(?i)(\bAuthorization\b\s*[=:]\s*)(\S+)", r"\1***", masked)
    return masked


def _is_retryable(blob: str) -> bool:
    lowered = blob.lower()
    for marker in C.RETRYABLE_MARKERS:
        if marker.lower() in lowered:
            return True
    if re.search(r"\bhttp\s*5\d\d\b", lowered):
        return True
    return re.search(r"\bstatus\s*code\s*:?\s*5\d\d\b", lowered) is not None


def parse_error(stdout, stderr):
    """Extract ``Code``/``Message`` from CLI output, falling back to raw text."""
    text = (stdout or "").strip() or (stderr or "").strip()
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        payload = None
    if isinstance(payload, dict) and (payload.get("Code") or payload.get("code")):
        code = payload.get("Code") or payload.get("code") or "CliError"
        message = payload.get("Message") or payload.get("message") or text
        return str(code), mask_secrets(str(message))
    first_line = text.splitlines()[0] if text else "empty error response"
    match = re.match(r"^ERROR:\s*([A-Za-z][A-Za-z0-9._\-]*):(?:\s*(.*))?$", first_line)
    if match:
        return match.group(1), mask_secrets(match.group(2) or first_line)
    return "CliError", mask_secrets(first_line)


def build_command(action, params=None, product=None):
    """Assemble the argv list for one API call, UA tag included."""
    argv = [C.CLI_BIN, product or C.ECS_PRODUCT, action]
    argv += ["--user-agent", user_agent()]
    argv += ["--connect-timeout", str(max(5, C.CLI_TIMEOUT_SECONDS // 6))]
    argv += ["--read-timeout", str(C.CLI_TIMEOUT_SECONDS)]
    for key, value in (params or {}).items():
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        argv += ["--" + key, str(value)]
    return argv


def run(argv, timeout=None):
    """Execute argv with a hard timeout and no shell interpolation."""
    limit = timeout or C.CLI_TIMEOUT_SECONDS
    try:
        proc = subprocess.run(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=limit,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise CliError("RequestTimeout", "aliyun CLI call exceeded {0}s".format(limit))
    except (OSError, ValueError) as exc:
        raise CliError(
            "CliUnavailable",
            "unable to run the aliyun CLI: {0}".format(mask_secrets(exc)),
        )
    stdout = (proc.stdout or b"").decode("utf-8", "replace")
    stderr = (proc.stderr or b"").decode("utf-8", "replace")
    return proc.returncode, stdout, stderr


def _emit_warning(action, detail):
    sys.stderr.write(
        "[WARN] {0} {1}: {2}\n".format(action, SESSION_ID[:8], mask_secrets(detail))
    )
    sys.stderr.flush()


def call(action, params=None, product=None, timeout=None, retries=None):
    """Invoke one allowlisted action through the CLI and return parsed JSON.

    Transient failures are retried with backoff. A hard failure raises
    :class:`CliError`; callers that can degrade should catch it and keep going.
    """
    if action not in C.ALLOWED_ACTIONS:
        raise CliError(
            "ActionNotPermitted",
            "action '{0}' is not in this skill's allowlist".format(action),
        )
    argv = build_command(action, params, product=product)
    attempts = C.MAX_RETRIES if retries is None else max(1, retries)
    limit = timeout or C.CLI_TIMEOUT_SECONDS
    last_error = None
    for attempt in range(attempts):
        returncode, stdout, stderr = run(argv, timeout=limit)
        if returncode == 0:
            if not stdout.strip():
                return {}
            try:
                return json.loads(stdout)
            except ValueError:
                raise CliError("MalformedResponse", "response is not valid JSON")
        code, message = parse_error(stdout, stderr)
        last_error = CliError(code, message, retried=attempt > 0)
        if not _is_retryable("{0} {1}".format(code, message)):
            break
        if attempt < attempts - 1:
            time.sleep(C.RETRY_BACKOFF_SECONDS * (attempt + 1))
    if last_error is None:
        last_error = CliError("Unknown", "call failed without an error payload")
    _emit_warning(action, str(last_error))
    raise last_error


def paginate(action, params, list_path, product=None, page_size=None, timeout=None):
    """Walk PageNumber pages of a list API.

    ``list_path`` is a dotted path such as ``Snapshots.Snapshot``. Paging stops
    on a short page, an empty page, or :data:`C.MAX_PAGES`.
    """
    size = page_size or C.PAGE_SIZE
    collected = []
    for page in range(1, C.MAX_PAGES + 1):
        scoped = dict(params or {})
        scoped["PageSize"] = size
        scoped["PageNumber"] = page
        payload = call(action, scoped, product=product, timeout=timeout)
        rows = dig(payload, list_path)
        if not isinstance(rows, list):
            break
        collected.extend(rows)
        if len(rows) < size:
            break
    return collected


def dig(payload, dotted_path):
    """Fetch a nested value by dotted path without assuming absent keys exist."""
    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def decode_maybe_base64(value):
    """Cloud Assistant output is base64; anything else passes through."""
    if not value:
        return ""
    try:
        return base64.b64decode(value, validate=True).decode("utf-8", "replace").strip()
    except Exception:  # not base64: keep the raw string, inventing nothing
        return str(value).strip()


def find_keys(payload, keys):
    """Recursively collect values for any of ``keys`` regardless of nesting."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in keys and value not in (None, "", [], {}):
                    found.append((key, value))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


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
