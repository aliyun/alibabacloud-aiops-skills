"""Shared Alibaba Cloud CLI layer for the site-migration skill.

Every cloud call in this package goes through :func:`call_api` or :func:`call_plugin`, which
enforce the inspection allow-list from ``_constants.py``, attach the per-session User-Agent, bound
each subprocess by timeout, retry only transient errors, and mask credential-looking substrings.
"""

import json
import random
import re
import subprocess
import sys
import time
import uuid

import _constants as C


class CliError(Exception):
    """A CLI or API failure, carrying the service ``Code: Message`` pair."""

    def __init__(self, code, message):
        super(CliError, self).__init__("%s: %s" % (code, message))
        self.code = str(code)
        self.message = str(message)

    def describe(self):
        return "%s: %s" % (self.code, self.message)


_SECRET_PATTERN = re.compile(
    r"(?i)\b(access[-_]?key[-_]?id|access[-_]?key[-_]?secret|security[-_]?token|"
    r"signature|password|secret)\b(['\"]?\s*[:=]\s*)([^&\s'\"]+)"
)


def new_session_id():
    """Return one 32-character hex identifier for the current run."""
    return uuid.uuid4().hex


def user_agent(session_id):
    """Return the User-Agent value that carries the skill name and session identifier."""
    return "%s/%s/%s" % (C.USER_AGENT_PREFIX, C.SKILL_NAME, session_id)

_user_agent_raw = user_agent



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
def user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


def mask_credentials(text):
    """Replace credential-looking values in arbitrary error text with ``***``."""
    if text is None:
        return ""

    def _replace(match):
        return "%s%s***" % (match.group(1), match.group(2))

    return _SECRET_PATTERN.sub(_replace, str(text))


def warn(message):
    """Report a non-fatal problem on stderr and keep going."""
    sys.stderr.write("[WARN] %s\n" % mask_credentials(message))


def _decode(raw):
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", "replace")
    return str(raw)


def _flag_pairs(params):
    flags = []
    for key in sorted((params or {}).keys()):
        value = params[key]
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (list, tuple)):
            rendered = json.dumps(list(value))
        else:
            rendered = str(value)
        flags.append("--%s" % key)
        flags.append(rendered)
    return flags


def _parse_error(text):
    safe = mask_credentials(text or "")
    code = ""
    message = ""
    for line in safe.splitlines():
        stripped = line.strip()
        if stripped.startswith("ErrorCode:"):
            code = stripped[len("ErrorCode:"):].strip()
        elif stripped.startswith("Message:"):
            message = stripped[len("Message:"):].strip()
    if not code:
        for line in safe.splitlines():
            if line.strip():
                code = line.strip().split(":")[0][:80]
                break
    if not code:
        code = "CliError"
    if not message:
        message = safe.strip() or "aliyun CLI call failed"
    return code, message


def _is_transient(code):
    if not code:
        return False
    for known in C.TRANSIENT_ERROR_CODES:
        if code == known or code.startswith(known):
            return True
    return False


def _backoff(attempt):
    delay = C.RETRY_BASE_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 0.3)
    time.sleep(min(delay, C.RETRY_MAX_SECONDS))


def _execute(argv, timeout):
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise CliError("ClientTimeout", "aliyun CLI call timed out after %s seconds" % timeout)
    except OSError as exc:
        raise CliError("CliUnavailable", "could not start the aliyun CLI: %s" % exc)
    return completed.returncode, _decode(completed.stdout), _decode(completed.stderr)


def _run(argv, timeout):
    attempts = 0
    last_code = "CliError"
    last_message = "aliyun CLI call failed"
    while attempts < C.CLI_MAX_RETRIES:
        attempts += 1
        try:
            returncode, out, err = _execute(argv, timeout)
        except CliError as exc:
            if exc.code == "ClientTimeout" and attempts < C.CLI_MAX_RETRIES:
                _backoff(attempts)
                continue
            raise
        if returncode == 0:
            text = out.strip()
            if not text:
                return {}
            try:
                return json.loads(text)
            except ValueError:
                raise CliError("BadCLIOutput", "aliyun CLI returned output that is not JSON")
        code, message = _parse_error(err or out)
        last_code, last_message = code, message
        if code == C.ERROR_CODE_MISSING_ACTION:
            raise CliError(
                code,
                "the CLI does not recognise this action, so the declared API surface and the local "
                "CLI metadata disagree: %s. Do not retry or substitute another action." % message,
            )
        if _is_transient(code) and attempts < C.CLI_MAX_RETRIES:
            _backoff(attempts)
            continue
        raise CliError(code, message)
    raise CliError(last_code, last_message)


def call_api(product, action, params=None, session_id=None, timeout=None):
    """Call one allow-listed RPC action and return the parsed response."""
    allowed = C.ALLOWED_ACTIONS.get(product)
    if not allowed or action not in allowed:
        raise CliError(
            "ActionNotAllowed",
            "%s %s is outside the inspection allow-list of this skill" % (product, action),
        )
    sid = session_id or new_session_id()
    argv = [C.CLI_BINARY, product, action]
    argv.extend(_flag_pairs(params))
    argv.extend(["--user-agent", user_agent(sid)])
    return _run(argv, timeout or C.CLI_TIMEOUT_SECONDS)


def call_plugin(product, verb, params=None, session_id=None, timeout=None):
    """Call one allow-listed plugin-mode verb such as ``get-caller-identity``."""
    verbs = C.PLUGIN_VERBS.get(product) or {}
    action = verbs.get(verb)
    if not action:
        raise CliError(
            "ActionNotAllowed",
            "%s %s is not an allow-listed plugin verb of this skill" % (product, verb),
        )
    sid = session_id or new_session_id()
    argv = [C.CLI_BINARY, product, verb]
    argv.extend(_flag_pairs(params))
    argv.extend(["--user-agent", user_agent(sid)])
    return _run(argv, timeout or C.CLI_TIMEOUT_SECONDS)


def extract_items(data, container, item_key):
    """Return records from a nested ``{container: {item: [...]}}` shape or a flat list."""
    if not isinstance(data, dict):
        return []
    block = data.get(container)
    if isinstance(block, dict):
        inner = block.get(item_key)
        if isinstance(inner, list):
            return inner
        if inner is None:
            return []
        return [inner]
    if isinstance(block, list):
        return block
    return []


def paginate(product, action, params, container, item_key, session_id, page_size=None):
    """Walk page numbers until a short page or the reported total is reached."""
    requested = int(page_size or C.DEFAULT_PAGE_SIZE)
    size = max(1, min(requested, C.MAX_PAGE_SIZE))
    items = []
    page = 1
    while page <= C.MAX_PAGES:
        query = dict(params or {})
        query["PageNumber"] = page
        query["PageSize"] = size
        data = call_api(product, action, query, session_id=session_id)
        batch = extract_items(data, container, item_key)
        items.extend(batch)
        total = None
        if isinstance(data, dict):
            total = data.get("TotalCount")
        if len(batch) < size:
            break
        if isinstance(total, int) and len(items) >= total:
            break
        page += 1
    return items


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
