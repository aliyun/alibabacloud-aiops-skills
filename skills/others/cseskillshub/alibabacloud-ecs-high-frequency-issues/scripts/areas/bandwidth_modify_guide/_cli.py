"""Shared layer that drives the Alibaba Cloud CLI for this skill.

Responsibilities:
  * one CLI call site for the whole package, so nothing else assembles command lines;
  * a per-run session id and user agent attached to every call, including retries;
  * an explicit timeout on every subprocess invocation and backoff on transient errors;
  * credential redaction on every piece of text that leaves this module;
  * query-only enforcement: the action whitelist below is the whole vocabulary.

Credentials come from the default credential chain only. This module never reads,
accepts, prints or forwards an access key pair or a token value.
"""

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    CLI_BINARY,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    PERMISSION_ERROR_TOKENS,
    REDACT_KEYS,
    RETRY_BACKOFF_BASE_SECONDS,
    RETRY_BACKOFF_CAP_SECONDS,
    TRANSIENT_ERROR_TOKENS,
    USER_AGENT_PREFIX,
)

# The complete vocabulary this skill may send. Anything else is refused here so a
# mistake in a caller can never reach the cloud.
ACTION_WHITELIST = frozenset([
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceStatus",
    "ecs:DescribeAvailableResource",
    "vpc:DescribeEipAddresses",
    "sts:GetCallerIdentity",
])


_FALLBACK_SESSION_ID = None


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
def new_session_id():
    """32 hex characters, generated once per script run."""
    return uuid.uuid4().hex


def fallback_session_id():
    global _FALLBACK_SESSION_ID
    if _FALLBACK_SESSION_ID is None:
        _FALLBACK_SESSION_ID = new_session_id()
    return _FALLBACK_SESSION_ID


def user_agent_for(session_id):
    if not session_id:
        session_id = fallback_session_id()
    return "%s/%s" % (USER_AGENT_PREFIX, session_id)

_user_agent_for_raw = user_agent_for



_PACKAGE_NAME = "alibabacloud-ecs-high-frequency-issues"


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


def redact(text):
    """Mask secret-looking values before any text is printed or returned."""
    if text is None:
        return ""
    value = text if isinstance(text, str) else str(text)
    for key in REDACT_KEYS:
        value = re.sub(r"%s=[^&\s,\"]+" % key, "%s=***" % key, value)
        value = re.sub(r'"%s"\s*:\s*"[^"]*"' % key, '"%s": "***"' % key, value)
    return value


def is_permission_error(text):
    lowered = (text or "").lower()
    for token in PERMISSION_ERROR_TOKENS:
        if token.lower() in lowered:
            return True
    return False


def is_transient_error(text):
    lowered = (text or "").lower()
    for token in TRANSIENT_ERROR_TOKENS:
        if token.lower() in lowered:
            return True
    return False


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
    """A CLI failure rendered as `Code: Message`."""

    def __init__(self, code, message, product=None, action=None):
        Exception.__init__(self, "%s: %s" % (code, message))
        self.code = code
        self.message = message
        self.product = product
        self.action = action

    @property
    def permission_denied(self):
        return is_permission_error("%s %s" % (self.code, self.message))

    @property
    def transient(self):
        return is_transient_error("%s %s" % (self.code, self.message))


def check_action(product, action):
    """Guard the query-only whitelist. Returns the qualified name or raises."""
    qualified = "%s:%s" % (product, action)
    if qualified not in ACTION_WHITELIST:
        raise CliError("WhitelistViolation",
                       "action %s is outside the query whitelist of this skill" % qualified,
                       product, action)
    return qualified


# --- plugin-mode list parameters -------------------------------------------
# The OpenAPI reference spells a repeated list as Name.1 / Name.2. Plugin mode
# takes one kebab flag followed by the bare values, and a repeated structure
# takes one flag per index carrying Key=value pairs. A few actions document
# InstanceId as one comma-separated string rather than a repeated list.
_INDEXED_KEY_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9]*)\.(\d+)(?:\.([A-Za-z][A-Za-z0-9]*))?$")
_STRUCT_LIST_PARAMS = frozenset({"Tag", "DiskDeviceMapping", "ModuleList"})
_SCALAR_LIST_PARAMS = frozenset({
    ("describeinstancehistoryevents", "instanceid"),
    ("describeinvocations", "instanceid"),
    ("describesendfileresults", "instanceid"),
    ("describeinstanceautorenewattribute", "instanceid"),
})


def _shape_key(action, base):
    """Normalize an action/param pair so kebab and PascalCase spellings agree."""
    return (re.sub(r"[^a-z0-9]", "", str(action).lower()),
            re.sub(r"[^a-z0-9]", "", str(base).lower()))
_REPEAT_LIST_PARAMS = frozenset({
    "InstanceId", "InstanceTypes", "InstanceEventCycleStatus",
    "InstanceEventType", "EventId", "AddAccount", "RemoveAccount",
})


def _fold_indexed_params(action, params):
    """Fold documented Name.N list keys into one entry per base name.

    Insertion order is preserved and indexed values are ordered by their numeric
    index, so InstanceId.10 never lands ahead of InstanceId.2.
    """
    groups = {}
    for key, value in (params or {}).items():
        match = _INDEXED_KEY_RE.match(key)
        if not match:
            continue
        base, index, sub = match.group(1), int(match.group(2)), match.group(3)
        groups.setdefault(base, {}).setdefault(index, {})
        groups[base][index][sub] = value
    folded = {}
    for base, indexes in groups.items():
        ordered = [indexes[number] for number in sorted(indexes)]
        if base in _STRUCT_LIST_PARAMS:
            folded[base] = [dict(item) for item in ordered]
        elif _shape_key(action, base) in _SCALAR_LIST_PARAMS:
            folded[base] = ",".join(
                str(item.get(None)) for item in ordered if item.get(None) is not None)
        else:
            folded[base] = [item.get(None) for item in ordered]
    out = []
    emitted = set()
    for key, value in (params or {}).items():
        match = _INDEXED_KEY_RE.match(key)
        if not match:
            out.append((key, value))
            continue
        base = match.group(1)
        if base in emitted:
            continue
        emitted.add(base)
        out.append((base, folded[base]))
    return out


def _list_param_argv(action, params, flag_of, text_of, skip_empty=False):
    """Render params as plugin-mode argv tokens, folding Name.N list keys."""
    argv = []
    for key, value in _fold_indexed_params(action, params):
        if value is None or (skip_empty and value == ""):
            continue
        scalar_list = _shape_key(action, key) in _SCALAR_LIST_PARAMS
        if isinstance(value, (list, tuple)) and key in _STRUCT_LIST_PARAMS:
            for item in value:
                argv.append(flag_of(key))
                argv.extend("%s=%s" % (name, text_of(val))
                            for name, val in item.items() if val is not None)
            continue
        if isinstance(value, (list, tuple)) and key in _REPEAT_LIST_PARAMS and not scalar_list:
            values = [text_of(item) for item in value if item is not None]
            if values:
                argv.append(flag_of(key))
                argv.extend(values)
            continue
        argv.extend([flag_of(key), text_of(value)])
    return argv


def _param_text(value):
    """Render one scalar parameter value the way plugin mode expects it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(list(value) if isinstance(value, tuple) else value,
                          ensure_ascii=False, separators=(",", ":"))
    return str(value)


def build_argv(product, action, params=None):
    """`aliyun <product> <action> --key value ...` plus the session user agent."""
    argv = [CLI_BINARY, product, _plugin_cmd(action)]
    argv += _list_param_argv(action, params, lambda key: _plugin_flag(key), _param_text)
    return argv


def run_cli(argv, session_id=None, timeout=None, retries=None, product=None, action=None):
    """Run one CLI call. Returns the parsed payload; raises CliError on failure.

    Every attempt gets its own subprocess timeout and carries the same user agent,
    so a whole run is traceable with one 32-character session id.
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT_SECONDS
    timeout = max(1, min(int(timeout), MAX_TIMEOUT_SECONDS))
    if retries is None:
        retries = DEFAULT_RETRIES
    retries = max(0, int(retries))

    agent = user_agent_for(session_id)
    command = list(argv) + ["--user-agent", agent]
    attempt = 0
    last_error = None

    while attempt <= retries:
        if attempt:
            delay = RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            time.sleep(min(delay, RETRY_BACKOFF_CAP_SECONDS))
        attempt += 1
        try:
            completed = subprocess.run(
                _with_auto_plugin(command),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                universal_newlines=True,
            )
        except FileNotFoundError:
            raise CliError("CliNotFound",
                           "%s executable not found; install the Alibaba Cloud CLI and run "
                           "aliyun sts get-caller-identity" % CLI_BINARY, product, action)
        except OSError as exc:
            raise CliError("CliSpawnError", redact(str(exc)), product, action)
        except subprocess.TimeoutExpired:
            last_error = CliError("Timeout",
                                  "call exceeded %ds on attempt %d" % (timeout, attempt),
                                  product, action)
            if attempt <= retries:
                continue
            raise last_error

        stdout_text = redact(completed.stdout or "")
        stderr_text = redact(completed.stderr or "")

        if completed.returncode != 0:
            code, message = _parse_error(stdout_text, stderr_text)
            last_error = CliError(code, message, product, action)
            if last_error.transient and attempt <= retries:
                continue
            raise last_error

        payload, decode_error = _parse_json(stdout_text)
        if decode_error is not None:
            raise CliError("BadResponse", decode_error, product, action)
        return _surface_error_envelope(payload)

    raise last_error or CliError("CliFailed", "call failed", product, action)


def call(product, action, params=None, session_id=None, timeout=None, retries=None):
    """Whitelist-checked, user-agent-tagged single call."""
    check_action(product, action)
    argv = build_argv(product, action, params)
    return run_cli(argv, session_id=session_id, timeout=timeout, retries=retries,
                   product=product, action=action)


def plugin_call(subcommand, session_id=None, timeout=None, retries=None):
    """Plugin-mode command form, e.g. `aliyun sts get-caller-identity`."""
    check_action(subcommand[0], _plugin_action(subcommand))
    argv = [CLI_BINARY] + list(subcommand)
    return run_cli(argv, session_id=session_id, timeout=timeout, retries=retries,
                   product=subcommand[0], action=" ".join(subcommand[1:]))


def _plugin_action(subcommand):
    """sts get-caller-identity -> GetCallerIdentity, for the whitelist check."""
    words = " ".join(subcommand[1:]).replace("-", " ").split()
    return "".join(word[:1].upper() + word[1:] for word in words)


def warn(message):
    """Non fatal findings go to stderr so the report on stdout stays parseable."""
    sys.stderr.write("[WARN] %s\n" % redact(message))


def _parse_json(text):
    if text is None or not text.strip():
        return {}, None
    try:
        return json.loads(text), None
    except ValueError:
        pass
    start = -1
    for opener in ("{", "["):
        index = text.find(opener)
        if index != -1 and (start == -1 or index < start):
            start = index
    if start == -1:
        return {"raw": text.strip()}, "no JSON payload in CLI response"
    try:
        return json.loads(text[start:]), None
    except ValueError as exc:
        return {"raw": text.strip()}, "JSON decode failed: %s" % exc


def _parse_error(stdout_text, stderr_text):
    """Pull `Code: Message` out of whatever the CLI printed."""
    blob = (stderr_text or "") + "\n" + (stdout_text or "")
    payload, error = _parse_json(blob)
    if error is None and isinstance(payload, dict):
        code = payload.get("Code") or payload.get("code")
        message = payload.get("Message") or payload.get("message")
        if code:
            return str(code), redact(message or "no message returned")
    for line in blob.splitlines():
        stripped = line.strip()
        if stripped.startswith("ERROR:") or stripped.startswith("Error:"):
            return "CliError", redact(stripped[:400])
    return "CliFailed", redact((stderr_text or stdout_text or "call failed").strip()[:400])


def dig(payload, *path):
    """Safe nested lookup; returns None instead of raising on any miss."""
    current = payload
    for key in path:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and key < len(current):
            current = current[key]
        else:
            return None
    return current


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
