"""Shared Alibaba Cloud CLI layer for this skill.

One call shape for the whole skill:

* argument list only, never a shell, and ``stdin`` detached;
* a per-call timeout on every subprocess invocation;
* a traceable user agent on every invocation, carrying the run's session id;
* bounded backoff for transient service errors only;
* redaction of credential-looking values in anything that leaves this module.

Credentials come from the CLI's own default chain. Nothing here opens a profile
file, reads a key, or accepts a key on any argument.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    ALIYUN_BIN,
    BACKOFF_BASE_SECONDS,
    CALL_TIMEOUT_SECONDS,
    CREDENTIAL_ERROR_CODES,
    MAX_ATTEMPTS,
    PERMISSION_ERROR_CODES,
    RETRYABLE_ERROR_CODES,
    SKILL_NAME,
    UA_PREFIX,
)

SECRET_KEYS = (
    "accesskeyid",
    "accesskeysecret",
    "securitytoken",
    "bearer-token",
    "signature",
    "password",
    "passwd",
)

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)([{0}])(\s*[=:]\s*)(\S+)".format("|".join(re.escape(k) for k in SECRET_KEYS))
)
_SECRET_FLAG = re.compile(
    r"(?i)(--(?:{0}))(\s+)(\S+)".format("|".join(re.escape(k) for k in SECRET_KEYS))
)
_ERROR_CODE = re.compile(r"ErrorCode:\s*([A-Za-z0-9][A-Za-z0-9._\-]*)")
_JSON_PREFIX = re.compile(r"[{\[]")


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
    """Return the 32-hex id that ties every CLI call of one run together."""
    return uuid.uuid4().hex


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


def user_agent(session_id):
    """Build the user agent: <prefix>/<skill>/<session-id>."""
    return _ua_normalize("{0}/{1}/{2}".format(UA_PREFIX, SKILL_NAME, session_id)) + " skill-version/" + _SKILL_VERSION


def redact(text):
    """Mask any credential-looking value in ``text`` and return the safe form."""
    if not text:
        return ""
    safe = str(text)
    safe = _SECRET_ASSIGNMENT.sub(lambda m: m.group(1) + m.group(2) + "***", safe)
    safe = _SECRET_FLAG.sub(lambda m: m.group(1) + m.group(2) + "***", safe)
    return safe


def emit_warning(label, error):
    """Report a non-fatal failure on stderr with the required [WARN] marker."""
    sys.stderr.write("[WARN] {0}: {1}\n".format(label, redact(error)))


class CliError(RuntimeError):
    """A failed CLI invocation, rendered as ``Code: Message``."""

    def __init__(self, product, action, code, message):
        super().__init__("{0}: {1}".format(code, message))
        self.product = product
        self.action = action
        self.code = code
        self.message = redact(message)

    @property
    def is_permission(self):
        return self.code in PERMISSION_ERROR_CODES

    @property
    def is_credential(self):
        return self.code in CREDENTIAL_ERROR_CODES

    def as_dict(self):
        return {
            "product": self.product,
            "action": self.action,
            "code": self.code,
            "message": self.message,
        }


def _stringify(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(list(value) if isinstance(value, tuple) else value)
    return str(value)


def _first_line(*chunks):
    for chunk in chunks:
        for line in (chunk or "").splitlines():
            if line.strip():
                return line.strip()
    return "command failed"


def _error_code(stderr_text, stdout_text):
    for blob in (stderr_text, stdout_text):
        match = _ERROR_CODE.search(blob or "")
        if match:
            return match.group(1)
    joined = "{0} {1}".format(stderr_text or "", stdout_text or "")
    for known in RETRYABLE_ERROR_CODES:
        if known in joined:
            return known
    return "CliInvocationFailed"


def _parse(stdout_text, product, action):
    body = (stdout_text or "").strip()
    if not body:
        return {}
    try:
        return json.loads(body)
    except ValueError:
        pass
    match = _JSON_PREFIX.search(body)
    if match:
        try:
            return json.loads(body[match.start():])
        except ValueError:
            pass
    raise CliError(product, action, "UnparsableOutput", body[:200])


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


def call(product, action, params=None, session_id=None, timeout=CALL_TIMEOUT_SECONDS):
    """Invoke ``aliyun <product> <action>`` and return the decoded JSON body.

    ``params`` maps an API parameter name to a value; ``None`` values are skipped.
    Transient service errors are retried with backoff up to ``MAX_ATTEMPTS``;
    anything else raises :class:`CliError` immediately.
    """
    argv = [ALIYUN_BIN, product, _plugin_cmd(action), "--user-agent", user_agent(session_id or new_session_id())]
    argv += _list_param_argv(action, params, lambda key: _plugin_flag(key), _param_text)

    last_code = "CliInvocationFailed"
    last_message = "command failed"
    for attempt in range(MAX_ATTEMPTS):
        try:
            completed = subprocess.run(
                _with_auto_plugin(argv),
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_code, last_message = "CliTimeout", "call timed out after {0}s".format(timeout)
        except OSError as error:
            # FileNotFoundError subclasses OSError, so a missing binary lands here too.
            reason = error.strerror or error.__class__.__name__
            raise CliError(
                product,
                action,
                "CliUnavailable",
                "the aliyun CLI could not be run ({0}); install it and run "
                "'aliyun sts get-caller-identity'".format(redact(reason)),
            )
        else:
            if completed.returncode == 0:
                return _parse(completed.stdout, product, action)
            last_code = _error_code(completed.stderr, completed.stdout)
            last_message = _first_line(redact(completed.stderr), redact(completed.stdout))
            if last_code not in RETRYABLE_ERROR_CODES:
                raise CliError(product, action, last_code, last_message)
        if attempt + 1 < MAX_ATTEMPTS:
            time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))
    raise CliError(product, action, last_code, last_message)


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
