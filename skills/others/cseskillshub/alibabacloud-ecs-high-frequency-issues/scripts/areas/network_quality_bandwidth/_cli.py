"""Shared Alibaba Cloud CLI layer used by every script in this skill.

Responsibilities:
- one argument-list based invocation path (never a shell string), with a per-call timeout;
- one traceable User-Agent per run, carrying a random session id;
- bounded retries on transient failures only, with linear backoff;
- credential redaction on every piece of text that can reach a log, a report, or the console.

Credentials are resolved by the CLI itself from its configured profile. This module never reads,
assembles, or prints an AccessKey pair or a token.
"""

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    CLI_TIMEOUT_SECONDS,
    MAX_ATTEMPTS,
    PERMISSION_ERROR_TOKENS,
    RETRY_BACKOFF_SECONDS,
    RETRYABLE_ERROR_TOKENS,
    SKILL_NAME,
    SUCCESS_CODES,
    USER_AGENT_TEMPLATE,
)

SESSION_ID = uuid.uuid4().hex



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
USER_AGENT = _ua_normalize(USER_AGENT_TEMPLATE.format(skill=SKILL_NAME, session_id=SESSION_ID)) + " skill-version/" + _SKILL_VERSION

_SECRET_ASSIGNMENT = re.compile(
    r'(?i)\b(access[\s_-]?key[\s_-]?(?:id|secret)?|security[\s_-]?token|'
    r'password|signature|bearer)'
    r'\b[=: ]+[^,;"\s]+'
)
_SECRET_VALUE = re.compile(
    r'\b(?:LTAI[A-Za-z0-9]{6,}|STS\.[A-Za-z0-9]{6,}|TMP\.[A-Za-z0-9]{6,})\b'
)


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


class CliError(Exception):
    """A cloud call that did not succeed, carrying `Code: Message`."""

    def __init__(self, code, message):
        super(CliError, self).__init__("{0}: {1}".format(code, message))
        self.code = str(code)
        self.message = redact_text(message)

    def is_permission(self):
        probe = (self.code + " " + self.message).lower()
        probe = re.sub(r"[^a-z]", "", probe)
        return any(token in probe for token in PERMISSION_ERROR_TOKENS)

    def is_transient(self):
        probe = (self.code + " " + self.message).lower()
        return any(token in probe for token in RETRYABLE_ERROR_TOKENS)


def redact_text(text):
    """Mask anything that looks like a credential before it is stored or printed."""
    if not text:
        return ""
    masked = _SECRET_ASSIGNMENT.sub(lambda m: "{0}***".format(m.group(1)), str(text))
    return _SECRET_VALUE.sub("***", masked)


def announce():
    sys.stderr.write(
        "[info] skill={0} session_id={1} User-Agent={2}\n".format(SKILL_NAME, SESSION_ID, USER_AGENT)
    )


def build_argv(product, action, params=None):
    argv = ["aliyun", product, _plugin_cmd(action), "--user-agent", USER_AGENT]
    for key in sorted(params or {}):
        value = params[key]
        if value is None or value == "":
            continue
        argv.extend([_plugin_flag(key), str(value)])
    return argv


def _decode(raw):
    if not raw:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", "replace")
    return str(raw)


def _error_from_body(payload):
    if not isinstance(payload, dict):
        return None
    code = payload.get("Code")
    if not code or str(code).strip().lower() in SUCCESS_CODES:
        return None
    return CliError(code, payload.get("Message") or "cloud call returned an error body")


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

def call(product, action, params=None, timeout=CLI_TIMEOUT_SECONDS, attempts=MAX_ATTEMPTS):
    """Run one cloud call and return the parsed JSON body."""
    argv = build_argv(product, action, params)
    last_error = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            completed = subprocess.run(
                _with_auto_plugin(argv),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("CliTimeout", "{0} {1} exceeded {2}s".format(product, action, timeout))
        except OSError as exc:
            raise CliError("CliUnavailable", "aliyun CLI could not be started: {0}".format(exc))
        else:
            stdout = _decode(completed.stdout)
            stderr = redact_text(_decode(completed.stderr))
            if completed.returncode != 0:
                last_error = CliError(
                    "CliExit{0}".format(completed.returncode),
                    stderr or "cloud call exited with {0}".format(completed.returncode),
                )
            else:
                try:
                    payload = _surface_error_envelope(_json_body(stdout)) if stdout.strip() else {}
                except ValueError:
                    raise CliError("BadResponse", "{0} {1} returned a body that is not JSON".format(
                        product, action))
                body_error = _error_from_body(payload)
                if body_error is not None:
                    last_error = body_error
                else:
                    return payload
        if attempt >= attempts or last_error is None or not last_error.is_transient():
            break
        time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise last_error or CliError("CliFailed", "{0} {1} failed".format(product, action))


def call_optional(product, action, params=None, timeout=CLI_TIMEOUT_SECONDS, notes=None):
    """Same as call(), but a failure becomes a recorded limitation instead of stopping the run."""
    try:
        payload = call(product, action, params, timeout=timeout)
    except CliError as exc:
        hint = ""
        if exc.is_permission():
            hint = " (missing RAM action, see references/ram-policies.md)"
        message = "[WARN] {0} {1} did not return data: {2}{3}".format(product, action, exc, hint)
        sys.stderr.write(message + "\n")
        if notes is not None:
            notes.append(message)
        return None
    return payload


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
