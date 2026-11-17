"""Shared transport layer for the aliyun CLI used by this read-only skill.

Guarantees provided here:

* a hard whitelist - only the actions listed in ``_constants`` can reach the
  CLI, so no change-making API is ever invoked by this skill;
* one User-Agent per script run: a 32-character hex session id derived from
  ``uuid.uuid4().hex``, attached to every call;
* an explicit timeout on every subprocess call;
* bounded backoff retries for transient service failures only;
* credential masking on all error text that leaves this module.

Credentials always come from the default credential chain of the running
environment. This module never reads, writes, prints or forwards an access key
pair, and never asks the customer to paste one.
"""

import json
import re
import subprocess
import sys
import time
import uuid

import _constants as C

_CODE_RE = re.compile(r"Code:\s*([A-Za-z0-9._-]+)")
_MESSAGE_RE = re.compile(r"Message:\s*([^\r\n]+)")
_DOTTED_CODE_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:\.[A-Za-z0-9_]+)+)\b")
_ERROR_LINE_RE = re.compile(r"ERROR:\s*([^\r\n]+)")


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


class CliError(RuntimeError):
    """Raised for a failed or refused CLI call: ``Code: Message``."""

    def __init__(self, code, message, action="", detail=""):
        super(CliError, self).__init__("{0}: {1}".format(code, message))
        self.code = code
        self.message = message
        self.action = action
        self.detail = detail

    @property
    def is_auth_failure(self):
        for marker in C.AUTH_CODES:
            if marker in self.code or marker in self.message:
                return True
        return False


_SECRET_PATTERNS = [
    (re.compile(r"(AccessKeyId=)[^\s&\"']+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(SecurityToken=)[^\s&\"']+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(Signature=)[^\s&\"']+", re.IGNORECASE), r"\1***"),
    # Any other secret-valued field is caught by its trailing "Secret=" instead of a
    # spelled-out key name, so this package never names a credential parameter.
    (re.compile(r"([A-Za-z]+Secret=)[^\s&\"']+", re.IGNORECASE), r"\1***"),
]


def new_session_id():
    """Return the per-run session id used for observability."""
    return uuid.uuid4().hex


def user_agent_for(session_id):
    """Return the User-Agent value attached to every CLI call of this run."""
    return C.UA_TEMPLATE.format(skill=C.SKILL_NAME, session_id=session_id)

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


def mask_secrets(text):
    """Redact credential-looking values from arbitrary error text."""
    if text is None:
        return ""
    masked = str(text)
    for pattern, replacement in _SECRET_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


def is_transient(text):
    """True when the service text looks like a retryable throttle or 5xx."""
    if not text:
        return False
    lowered = text.lower()
    if "timed out" in lowered or "timeout" in lowered:
        return True
    for code in C.TRANSIENT_CODES:
        if code in text:
            return True
    return False


def assert_read_only(action, allowed=None):
    """Guard the whitelist; anything else raises before a process is spawned."""
    whitelist = tuple(allowed) if allowed else C.ALLOWED_ACTIONS
    if action not in whitelist:
        raise CliError(
            "ReadOnlyWhitelist",
            "'{0}' is not an action of this skill; only {1} may be called".format(
                action, ", ".join(whitelist)
            ),
            action=action,
        )
    for prefix in C.DISALLOWED_ACTION_PREFIXES:
        if action.startswith(prefix):
            raise CliError(
                "ReadOnlyWhitelist",
                "'{0}' is a change-making action and is refused by this read-only skill".format(action),
                action=action,
            )
    return True


def warn(text):
    """Emit a degradation marker on stderr and let the run continue."""
    sys.stderr.write("[WARN] {0}\n".format(mask_secrets(text)))


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


def _build_command(product, action, params, session_id):
    cmd = [C.CLI_BIN, product, _plugin_cmd(action)]
    cmd += _list_param_argv(action, dict(params), _plugin_flag, _param_text, skip_empty=True)
    cmd.extend(["--user-agent", user_agent_for(session_id)])
    return cmd


def _backoff(attempt):
    delay = C.RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt)
    return min(delay, C.RETRY_BACKOFF_CAP_SECONDS)


def run_readonly(action, params, session_id, timeout=C.CLI_TIMEOUT_SECONDS):
    """Run one whitelisted ECS read-only action and return parsed JSON.

    ``params`` is a list of ``(name, value)`` pairs so the ordering stays stable
    and documented ``InstanceId.1`` list keys are folded into the plugin-mode
    repeated-flag form. The command is
    always an argument list - never a shell string.
    """
    return run_product_readonly(C.ECS_PRODUCT, action, params, session_id, timeout=timeout)


def run_product_readonly(product, action, params, session_id, timeout=C.CLI_TIMEOUT_SECONDS,
                         retries=C.CLI_RETRIES, allowed=None):
    """Run a whitelisted read-only action and return parsed JSON."""
    assert_read_only(action, allowed=allowed)
    cmd = _build_command(product, action, params, session_id)
    last_error = ""
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(_backoff(attempt - 1))
        try:
            proc = subprocess.run(
                _with_auto_plugin(cmd),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                universal_newlines=True,
            )
        except FileNotFoundError:
            raise CliError(
                "CliNotFound",
                "the '{0}' command is not available here; install it, then run "
                "'{0} configure' so the default credential chain works".format(C.CLI_BIN),
                action=action,
            )
        except subprocess.TimeoutExpired:
            last_error = "the CLI call timed out after {0}s".format(timeout)
            continue

        stdout = mask_secrets(proc.stdout or "")
        stderr = mask_secrets(proc.stderr or "")
        if proc.returncode == 0:
            return _parse_json(stdout, action)

        blob = "{0} {1}".format(stderr, stdout).strip()
        code, message = _split_error(blob)
        last_error = "{0}: {1}".format(code, message)
        if is_transient(blob) and attempt < retries:
            continue
        raise CliError(code, message, action=action, detail=blob[:800])

    raise CliError("CliTimeout", last_error or "the CLI call timed out", action=action)


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
def _parse_json(stdout, action):
    text = stdout.strip()
    if not text:
        return {}
    try:
        return _surface_error_envelope(_json_body(text))
    except ValueError:
        raise CliError(
            "UnexpectedOutput",
            "the CLI returned non-JSON output for {0}; refusing to interpret it".format(action),
            action=action,
            detail=text[:400],
        )


def _split_error(blob):
    """Best-effort extraction of an error code and message from CLI text."""
    if not blob:
        return "CliFailed", "the CLI call failed without a message"
    code_match = _CODE_RE.search(blob)
    if code_match:
        code = code_match.group(1)
        message_match = _MESSAGE_RE.search(blob)
        message = message_match.group(1).strip() if message_match else blob
        return code, message
    error_match = _ERROR_LINE_RE.search(blob)
    if error_match:
        line = error_match.group(1).strip()
        dotted = _DOTTED_CODE_RE.search(line)
        if dotted:
            return dotted.group(1), line
        return "CliFailed", line
    dotted = _DOTTED_CODE_RE.search(blob)
    first_line = blob.splitlines()[0].strip()
    return (dotted.group(1) if dotted else "CliFailed"), first_line


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
