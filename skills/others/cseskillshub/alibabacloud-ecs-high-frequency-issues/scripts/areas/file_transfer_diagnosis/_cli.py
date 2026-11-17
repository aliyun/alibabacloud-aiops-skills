"""Shared Alibaba Cloud CLI layer used by this skill's scripts.

Responsibilities
----------------
* Build every call as an argument list (never a shell string) and bound it with
  a per-call timeout.
* Attach an observability user-agent carrying a run-scoped session id to each
  call.
* Retry only transient failures with bounded backoff.
* Redact credential-looking material from any text that leaves this module.
* Use the ambient CLI credential chain: this module never accepts, reads,
  echoes or stores a key or secret.
"""

import json
import random
import re
import shutil
import subprocess
import sys
import time
import uuid

import _constants as C

_ALIYUN_BINARY = "aliyun"

# (pattern, index of the group holding the sensitive value)
_REDACT_PATTERNS = (
    (re.compile(r"(?i)\b(accesskey[a-z]*|secretkey[a-z]*|securitytoken|"
                r"ststoken|signature|password|passwd)\b(\s*[=:]\s*)(\S+)"), 3),
    (re.compile(r"(?i)\b(LTAI[A-Za-z0-9]{8,})\b"), 1),
)


class CliError(RuntimeError):
    """A CLI call that did not succeed. Carries ``Code: Message`` text."""

    def __init__(self, code, message):
        super(CliError, self).__init__("{0}: {1}".format(code, message))
        self.code = code
        self.message = message


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


def new_session_id():
    """32-char hex id, unique per script run."""
    return uuid.uuid4().hex


def user_agent(session_id):
    return C.USER_AGENT_TEMPLATE.format(skill_name=C.SKILL_NAME,
                                        session_id=session_id)

_user_agent_raw = user_agent



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
def user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


def redact(text):
    """Mask anything that looks like a credential before it is printed."""
    if not text:
        return ""
    result = str(text)
    for pattern, value_group in _REDACT_PATTERNS:
        result = pattern.sub(
            lambda match, group=value_group:
            match.group(0).replace(match.group(group), "***"),
            result)
    return result


def is_transient(message):
    return any(marker in (message or "") for marker in C.TRANSIENT_MARKERS)


def is_permission_error(message):
    return any(marker in (message or "") for marker in C.PERMISSION_MARKERS)


def is_arrears(message):
    return any(marker in (message or "") for marker in C.ARREARS_MARKERS)


def cli_available():
    return shutil.which(_ALIYUN_BINARY) is not None


def _warn(message):
    sys.stderr.write("[WARN] {0}\n".format(redact(message)))


def _invoke(argv, timeout):
    """Run one argv list with a hard timeout and no shell."""
    return subprocess.run(
        _with_auto_plugin(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )


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


def _plugin_flag(key):
    """Return the plugin-mode flag for a documented parameter name."""
    if key == "RegionId":
        return "--biz-region-id"
    return "--" + re.sub(r"(?<!^)(?=[A-Z])", "-", key).lower()


def _plugin_cmd(name):
    """Return the plugin-mode command word for a documented action name.

    The CLI only accepts plugin-mode flags in plugin mode, and plugin mode is
    selected by the lowercase-hyphenated command word: the PascalCase action
    word selects RPC mode, which rejects `--biz-region-id` (reproduced on CLI
    3.4.5), while `describe-instances` accepts it. This area emitted plugin-mode
    flags under the PascalCase name, so every read died.
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def call(action, params=None, session_id=None, write=False, timeout=None):
    """Call one RPC action, for example ``ecs:DescribeInstances``.

    RPC actions keep their PascalCase name. Returns the decoded JSON payload,
    or ``{}`` when the call returned no body. Raises ``CliError`` on failure.
    """
    product, api_name = action.split(":", 1)
    if timeout is None:
        timeout = (C.CLI_TIMEOUT_WRITE_SECONDS if write
                   else C.CLI_TIMEOUT_SECONDS)

    argv = [_ALIYUN_BINARY, product, _plugin_cmd(api_name)]
    argv += _list_param_argv(api_name, params, _plugin_flag, _param_text, skip_empty=True)
    argv.extend(["--user-agent", user_agent(session_id or new_session_id())])
    return _execute(argv, timeout, api_name)


def call_plugin(product, verb, session_id=None, timeout=None):
    """Call a plugin-mode product command such as ``sts get-caller-identity``."""
    argv = [_ALIYUN_BINARY, product, _plugin_cmd(verb), "--user-agent",
            user_agent(session_id or new_session_id())]
    return _execute(argv, timeout or C.CLI_TIMEOUT_SECONDS, verb)


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

def _execute(argv, timeout, label):
    """Run one argv list with bounded retry and decode the JSON response."""
    attempt = 0
    last_error = None
    while attempt < C.RETRY_MAX_ATTEMPTS:
        attempt += 1
        try:
            completed = _invoke(argv, timeout)
        except subprocess.TimeoutExpired:
            last_error = "Timeout after {0}s".format(timeout)
            _warn("{0} timed out ({1}/{2})".format(label, attempt,
                                                   C.RETRY_MAX_ATTEMPTS))
            _sleep_backoff(attempt)
            continue

        if completed.returncode == 0:
            payload = (completed.stdout or "").strip()
            if not payload:
                return {}
            try:
                return _json_body(payload)
            except ValueError:
                raise CliError("InvalidResponse",
                               redact("could not decode CLI output for "
                                      "{0}".format(label)))

        error_text = redact(
            "{0} {1}".format(completed.stdout or "", completed.stderr or "")
        ).strip()
        if is_permission_error(error_text):
            raise CliError("AuthorizationDenied", error_text)
        if is_transient(error_text) and attempt < C.RETRY_MAX_ATTEMPTS:
            last_error = error_text
            _warn("{0} transient failure, retrying ({1}/{2})".format(
                label, attempt, C.RETRY_MAX_ATTEMPTS))
            _sleep_backoff(attempt)
            continue
        raise CliError("CliCallFailed", last_error or error_text)

    raise CliError("CliCallFailed",
                   last_error or "{0} failed after {1} attempts".format(
                       label, C.RETRY_MAX_ATTEMPTS))


def _sleep_backoff(attempt):
    delay = (C.RETRY_BACKOFF_BASE_SECONDS
             * (C.RETRY_BACKOFF_FACTOR ** (attempt - 1)))
    time.sleep(delay + random.uniform(0, 0.25))


def collect_paged(action, params, list_path, session_id=None, timeout=None):
    """Page through a Describe* call and return the concatenated items.

    ``list_path`` is a dotted path such as ``Instances.Instance``. Missing or
    malformed payloads degrade to an empty list rather than a guess.
    """
    items = []
    page_number = 1
    while page_number <= C.MAX_PAGE_ITEMS:
        paged = dict(params or {})
        paged["PageNumber"] = page_number
        paged["PageSize"] = C.PAGE_SIZE
        payload = call(action, paged, session_id=session_id, timeout=timeout)
        node = payload
        for part in list_path.split("."):
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(part)
        batch = node or []
        if isinstance(batch, dict):
            batch = [batch]
        items.extend(batch)
        if len(batch) < C.PAGE_SIZE:
            break
        page_number += 1
    return items


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
