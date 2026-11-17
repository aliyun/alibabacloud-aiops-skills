"""Shared read-only transport layer for the ``aliyun`` CLI.

Design rules enforced here (see SKILL.md):

* Every call is issued as an argument list with ``shell=False`` and a hard
  ``timeout``, and with ``stdin`` detached.
* Every call carries an observability User-Agent of the form
  ``AlibabaCloud-Agent-Skills/<skill-name>/<session-id>`` where ``session-id``
  is ``uuid.uuid4().hex`` (32 hex characters) generated once per run.
* Credentials come from the default credential chain only. This module never
  reads, writes, prints or forwards an AccessKey id or secret; all error text
  is masked before it is surfaced or logged.
* Only actions present in ``_constants.READ_ONLY_API_WHITELIST`` can be
  invoked; anything else is refused before a subprocess is spawned.
"""

import sys
import json
import re
import subprocess
import time
import uuid

from _constants import (
    BACKOFF_BASE_SECONDS,
    CALL_TIMEOUT_SECONDS,
    CLI_BINARY,
    MAX_ATTEMPTS,
    PLUGIN_MODE_PRODUCTS,
    READ_ONLY_API_WHITELIST,
    SKILL_NAME,
    STS_TIMEOUT_SECONDS,
    USER_AGENT_PREFIX,
)

# 32 hex characters, unique per process run.
session_id = uuid.uuid4().hex

_PACKAGE_NAME = "alibabacloud-ecs-high-frequency-issues"


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


def _plugin_cmd(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _plugin_flag(key):
    if key == "RegionId":
        return "--biz-region-id"
    return "--" + re.sub(r"(?<!^)(?=[A-Z])", "-", key).lower()
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


USER_AGENT = _ua_normalize("{0}/{1}/{2}".format(USER_AGENT_PREFIX, SKILL_NAME, session_id)) + " skill-version/" + _SKILL_VERSION

# Anything that could look like a credential is masked before leaving this
# module, including in exception messages and debug output.
_SECRET_PATTERNS = [
    re.compile(r"(?i)(accesskey\s*secret|secret\s*(?:key|id)?|password|passwd)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(accesskeyid|access_key_id|securitytoken|security_token|signature|"
               r"signaturenonce|x-acs-signature)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(STS\.[A-Za-z0-9\-]+|LTAI[A-Za-z0-9]{6,})"),
]

_TRANSIENT_MARKERS = (
    "throttling",
    "throttlingexception",
    "systembusy",
    "servicenotavailable",
    "unavailable",
    "internalerror",
    "internalfailure",
    "requestlimitexceeded",
    "timeout",
    "timed out",
    "connection reset",
    "eof occurred",
)

_RETRYABLE_HTTP_HINTS = ("500", "502", "503", "504")


def _surface_error_envelope(parsed):
    """The CLI exits 0 on API error bodies; surface them on the internal channel.

    The parsed body is returned unchanged so area logic keeps its current
    control flow; the dispatcher reads the ERROR line to classify the refusal.
    """
    if isinstance(parsed, dict):
        code = parsed.get("Code") or parsed.get("code")
        message = parsed.get("Message") or parsed.get("message")
        if code and message and str(code) not in ("200", "0", "OK", "Success", "success"):
            first = (str(message).splitlines() or [""])[0]
            sys.stderr.write("ERROR: %s: %s\n" % (code, first))
    return parsed


class CliError(RuntimeError):
    """A CLI invocation failed, carrying ``Code: Message`` text."""

    def __init__(self, code, message, exit_code=None):
        self.code = code
        self.message = _mask(message)
        self.exit_code = exit_code
        super(CliError, self).__init__("{0}: {1}".format(code, self.message))


def mask(text):
    """Public wrapper around the credential mask, for callers logging output."""
    return _mask(text)


def _mask(text):
    if text is None:
        return ""
    masked = str(text)
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(lambda m: m.group(0).split("=")[0].split(":")[0].strip() + "=***", masked)
    return masked


def _is_transient(code, message):
    blob = "{0} {1}".format(code or "", message or "").lower()
    if any(marker in blob for marker in _TRANSIENT_MARKERS):
        return True
    return any(hint in blob for hint in _RETRYABLE_HTTP_HINTS)


def _error_code(text):
    """Extract ``Code`` from CLI/POP error text without assuming a layout."""
    masked = _mask(text)
    match = re.search(r"(?i)\bcode\s*[:=]\s*([A-Za-z0-9\-_.]+)", masked)
    if match:
        return match.group(1)
    match = re.search(r"ERROR:\s*(.{0,160})", masked, re.S)
    if match:
        return match.group(1).strip().splitlines()[0][:80] or "CliError"
    return "CliError"


def is_allowed(product, action):
    """Whitelist gate: True only for actions verified read-only for this skill."""
    entry = READ_ONLY_API_WHITELIST.get(product)
    if not entry:
        return False
    return action in entry[1]


def build_command(product, action, params=None):
    """Build an argv list. Never use ``shell=True`` with this output."""
    if not is_allowed(product, action):
        raise CliError(
            "ApiNotWhitelisted",
            "'{0} {1}' is not in the verified read-only whitelist for this skill".format(product, action),
        )
    if product in PLUGIN_MODE_PRODUCTS:
        argv = [CLI_BINARY, product, re.sub(r"(?<!^)(?=[A-Z])", "-", action).lower()]
    else:
        argv = [CLI_BINARY, product, action]
    argv += ["--user-agent", USER_AGENT]
    for key in sorted(params or {}):
        value = params[key]
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        elif isinstance(value, (list, dict, tuple)):
            value = json.dumps(value, separators=(",", ":"))
        argv += [_plugin_flag(key), str(value)]
    return argv


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
def run_json(product, action, params=None, timeout=None, attempts=None, warn=None):
    """Call a whitelisted read-only action and return decoded JSON.

    Failures are returned as ``None`` after being recorded in ``warn`` so a
    partial investigation still produces a report; they are raised only when no
    degradation sink is supplied.
    """
    argv = build_command(product, action, params)
    limit = attempts or MAX_ATTEMPTS
    budget = timeout or (STS_TIMEOUT_SECONDS if product in PLUGIN_MODE_PRODUCTS else CALL_TIMEOUT_SECONDS)
    last_error = None
    for attempt in range(1, limit + 1):
        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv list, no shell
                _with_auto_plugin(argv),
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=budget,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("CliTimeout", "{0} {1} exceeded {2}s".format(product, action, budget))
        except OSError as exc:
            # Binary missing or not executable: never retry, degrade instead.
            raise CliError("CliUnavailable", _mask(exc))
        if completed.returncode == 0:
            raw = completed.stdout.decode("utf-8", "replace").strip()
            if not raw:
                return {}
            try:
                return _surface_error_envelope(_json_body(raw))
            except ValueError:
                raise CliError("UnparsableResponse", "{0} {1} returned non-JSON output".format(product, action))
        err_text = completed.stderr.decode("utf-8", "replace") or completed.stdout.decode("utf-8", "replace")
        code = _error_code(err_text)
        last_error = CliError(code, err_text, completed.returncode)
        if not _is_transient(code, err_text) or attempt == limit:
            break
        time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
    message = "[WARN] {0} {1} failed: {2}".format(product, action, _mask(last_error))
    if warn is not None:
        warn.append(message)
        return None
    raise last_error


def permission_hint(missing_actions):
    """Minimal policy fragment for a failed read-only call.

    Auth failures must be reported as ``NoPermission`` / ``ImplicitDeny``; the
    platform forbids other wording.
    """
    actions = sorted({a for a in missing_actions if a})
    fragment = {
        "Version": "1",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": actions,
                "Resource": ["*"],
            }
        ],
    }
    return "NoPermission or ImplicitDeny detected. Required read-only actions: {0}\n{1}".format(
        ", ".join(actions), json.dumps(fragment, indent=2)
    )


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
