"""Shared Alibaba Cloud CLI layer used by every script in this skill.

The rules that must hold for every cloud call are enforced once, here, instead
of at each call site:

* one subprocess per API call, argument-list form, never a shell string;
* a wall-clock timeout on every call;
* a per-run session id folded into the User-Agent of every call;
* backoff retries for transient failures only;
* credential masking applied to every byte of CLI text handed back to a caller;
* no credential is ever read, written, printed or passed by this layer - the
  CLI's own default credential chain decides who is calling.

Every product runs in plugin mode and uses the lowercase-hyphenated command
name (for example ``aliyun sts get-caller-identity``). Callers pass the
PascalCase API action name; this layer translates it.
"""

import sys
import base64
import binascii
import json
import random
import re
import subprocess
import time
import uuid

from _constants import (
    CLI_BIN,
    CLI_TIMEOUT_SECONDS,
    RETRY_BACKOFF_SECONDS,
    RETRY_JITTER_SECONDS,
    RETRY_MAX_ATTEMPTS,
    SKILL_NAME,
    USER_AGENT_FLAG,
    USER_AGENT_TEMPLATE,
)

PLAN_ONLY_KEY = "_plan_only"

TRANSIENT_ERROR_CODES = (
    "Throttling",
    "Throttling.User",
    "Throttling.Api",
    "ServiceUnavailable",
    "InternalError",
    "RequestTimeout",
    "SDK.HttpError",
    "SDK.ServerUnreachable",
    "SDK.RetryError",
)

TRANSIENT_MESSAGE_MARKERS = (
    "connection reset by peer",
    "connection refused by the endpoint",
    "tls handshake timeout",
    "i/o timeout",
    "eof",
    "temporary failure",
    "service unavailable",
    "try again later",
)


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
    """A failed cloud call, carrying the CLI's own code and message."""

    def __init__(self, code, message, product=None, action=None, retried=False):
        Exception.__init__(self, "%s: %s" % (code, message))
        self.code = code
        self.message = message
        self.product = product
        self.action = action
        self.retried = retried

    @property
    def is_permission_error(self):
        text = "%s %s" % (self.code or "", self.message or "")
        for marker in ("NoPermission", "ImplicitDeny"):
            if marker in text:
                return True
        return False


def new_session_id():
    """A 32-character hex id, one per skill run, used for traceability."""
    return uuid.uuid4().hex


def user_agent_for(session_id):
    return USER_AGENT_TEMPLATE.format(skill_name=SKILL_NAME, session_id=session_id)

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


_SECRET_PATTERNS = (
    (re.compile(r"(AccessKeyId=)([^\s&,;'\"]+)"), r"\1***"),
    (re.compile(r"(SecurityToken=)([^\s&,;'\"]+)"), r"\1***"),
    (re.compile(r"(AccessKeySecret=)([^\s&,;'\"]+)"), r"\1***"),
    (re.compile(r"(Signature=)([^\s&,;'\"]+)"), r"\1***"),
    (re.compile(r'("AccessKeySecret"\s*:\s*")[^"]*(")'), r"\1***\2"),
    (re.compile(r'("SecurityToken"\s*:\s*")[^"]*(")'), r"\1***\2"),
    (re.compile(r"(Password[=:]\s*)([^\s,;&]+)"), r"\1***"),
)


def mask_secrets(text):
    """Redact anything that looks like a credential before it reaches output."""
    if not text:
        return ""
    masked = text
    for pattern, replacement in _SECRET_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


def _stringify(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    return "%s" % (value,)


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


def _flatten_params(action, params):
    """Render params as plugin-mode CLI tokens for one action."""
    return _list_param_argv(action, params, _plugin_flag, _stringify, skip_empty=True)
def build_argv(product, action, params, session_id):
    argv = [CLI_BIN, product, _plugin_cmd(action), USER_AGENT_FLAG, user_agent_for(session_id)]
    argv.extend(_flatten_params(action, params or {}))
    return argv


def _sleep_backoff(attempt):
    delay = RETRY_BACKOFF_SECONDS * attempt + random.uniform(0, RETRY_JITTER_SECONDS)
    time.sleep(delay)


def _parse_error(text):
    code = "CliError"
    message = "the CLI returned no message"
    stripped = (text or "").strip()
    if stripped:
        message = stripped[:800]
    code_match = re.search(r"ErrorCode:\s*(\S+)", stripped)
    if code_match:
        code = code_match.group(1)
    message_match = re.search(r"Message:\s*(.+)", stripped)
    if message_match:
        message = message_match.group(1).strip()[:800]
    if "is not a valid api" in stripped:
        code = "InvalidAction"
    return code, message


def _is_transient(code, message):
    if code in TRANSIENT_ERROR_CODES:
        return True
    lowered = (message or "").lower()
    for marker in TRANSIENT_MESSAGE_MARKERS:
        if marker in lowered:
            return True
    return False


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

def run_cli(product, action, params=None, session_id=None,
            timeout=CLI_TIMEOUT_SECONDS, attempts=RETRY_MAX_ATTEMPTS,
            plan_only=False):
    """Issue one cloud API call through the CLI and return the parsed payload.

    Raises :class:`CliError` for anything that is not transient; transient
    failures are retried with a backoff first. With ``plan_only`` no process is
    started and the planned call is returned instead, which is what lets the
    skill show its intent before touching a customer account.
    """
    session_id = session_id or new_session_id()
    argv = build_argv(product, action, params, session_id)
    if plan_only:
        return {PLAN_ONLY_KEY: True, "product": product, "action": action,
                "argv": list(argv), "session_id": session_id}

    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            completed = subprocess.run(
                _with_auto_plugin(argv),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError(
                "Timeout",
                "the CLI call did not return within %d seconds" % timeout,
                product, action, retried=(attempt > 1),
            )
            if attempt < attempts:
                _sleep_backoff(attempt)
                continue
            raise last_error
        except OSError as exc:
            raise CliError("CliUnavailable", mask_secrets("%s" % (exc,)), product, action)

        stdout = mask_secrets(completed.stdout or "")
        stderr = mask_secrets(completed.stderr or "")
        if completed.returncode != 0:
            code, message = _parse_error(stdout + "\n" + stderr)
            error = CliError(code, message, product, action, retried=(attempt > 1))
            if _is_transient(code, message) and attempt < attempts:
                _sleep_backoff(attempt)
                continue
            raise error

        try:
            return _surface_error_envelope(_json_body(stdout or "{}"))
        except ValueError:
            raise CliError(
                "BadResponse",
                "%s %s returned text that is not JSON: %s" % (product, action, stdout[:400]),
                product, action,
            )

    raise last_error or CliError("Unknown", "the CLI call failed", product, action)


def dig(payload, path, default=None):
    """Walk a nested response, returning ``default`` on any missing level."""
    current = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def is_plan_only(payload):
    return bool(isinstance(payload, dict) and payload.get(PLAN_ONLY_KEY))


def decode_invocation_output(text):
    """Cloud Assistant returns command output base64-encoded; never crash on it."""
    if not text:
        return ""
    try:
        decoded = base64.b64decode(text.strip())
    except (binascii.Error, ValueError):
        return mask_secrets("%s" % (text,))
    try:
        return mask_secrets(decoded.decode("utf-8", "replace"))
    except Exception:
        return mask_secrets("%s" % (decoded,))


def describe_cli_error(error):
    """Render a CliError as one evidence line, with the auth wording this
    skill is required to use for permission failures."""
    if isinstance(error, CliError) and error.is_permission_error:
        return (
            "permission denied (%s) for %s %s - the caller is missing that RAM "
            "action; see references/ram-policies.md for the least-privilege "
            "fragment" % (error.code, error.product or "", error.action or "")
        )
    return "call failed: %s" % (error,)


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
