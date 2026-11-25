"""Shared Alibaba Cloud CLI layer used by every script in this skill.

Rules enforced here rather than at the call sites:
  * one request shape only: ``subprocess.run([...])`` with an argument list,
    ``stdin=subprocess.DEVNULL`` and an explicit ``timeout`` per call;
  * no request is ever handed to a shell interpreter; only argv lists are passed
    to the process launcher;
  * an Observability User-Agent on every call: ``--user-agent`` carrying
    ``AlibabaCloud-Agent-Skills/<skill-name>/<session-id>`` where the session id
    is ``uuid.uuid4().hex`` generated once per run;
  * only the default credential chain - this module never reads, writes or prints
    an AccessKey pair or a security token, and it masks such values if they show
    up in error text;
  * transient failures are retried with backoff, everything else is raised.
"""

import json
import re
import subprocess
import time
import uuid

from _constants import (
    API_WHITELIST,
    CLI_BACKOFF_BASE_SECONDS,
    CLI_MAX_RETRIES,
    CLI_TIMEOUT_SECONDS,
    SKILL_NAME,
    TRANSIENT_ERROR_MARKERS,
    UA_TEMPLATE,
)

# The CLI flag that fills the request's User-Agent header.
USER_AGENT_FLAG = "--user-agent"

_SECRET_PATTERNS = (
    (re.compile(r"(?i)(accesskeyid=)[^\s,&\"']+"), r"\1***"),
    (re.compile(r"(?i)(accesskeysecret=)[^\s,&\"']+"), r"\1***"),
    (re.compile(r"(?i)(securitytoken=)[^\s,&\"']+"), r"\1***"),
    (re.compile(r"(?i)(signature=)[^\s,&\"']+"), r"\1***"),
    (re.compile(r"(?i)(\"accesskeyid\"\s*:\s*\")[^\"]*(\")"), r"\1***\2"),
    (re.compile(r"(?i)(\"accesskeysecret\"\s*:\s*\")[^\"]*(\")"), r"\1***\2"),
    (re.compile(r"(?i)(\"securitytoken\"\s*:\s*\")[^\"]*(\")"), r"\1***\2"),
)

_ERROR_CODE_RE = re.compile(r"ErrorCode:\s*([A-Za-z0-9._\-]+)")
_MESSAGE_RE = re.compile(r"Message:\s*(.+)", re.DOTALL)


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

# Plugin-mode region refusal: the CLI names the flag it wants; supply it from
# the region the call already carries - once, and only for this exact refusal.
_REGION_FLAG_REQUIRED_RES = (
    re.compile(r"missing required parameter\(s\):\s*--biz-region-id"),
    re.compile(r"--biz-region-id is required"),
)


def _region_flag_retry(cmd, stderr, region=None):
    """The same call with the plugin's region parameter, or None if not applicable."""
    if "--biz-region-id" in cmd:
        return None
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", "replace")
    if not any(pattern.search(stderr or "") for pattern in _REGION_FLAG_REQUIRED_RES):
        return None
    if not region:
        for flag in ("--RegionId", "--region-id", "--region"):
            if flag in cmd:
                index = cmd.index(flag)
                if index + 1 < len(cmd):
                    region = cmd[index + 1]
                    break
    if not region:
        return None
    return list(cmd) + ["--biz-region-id", region]


def _run_with_region_retry(cmd, timeout=None, **kwargs):
    """subprocess.run with one plugin-region refusal retry; same exceptions."""
    completed = subprocess.run(_with_auto_plugin(cmd), timeout=timeout, **kwargs)
    if completed.returncode != 0:
        retry = _region_flag_retry(cmd, completed.stderr or "")
        if retry is not None:
            completed = subprocess.run(_with_auto_plugin(retry), timeout=timeout, **kwargs)
    return completed


def _plugin_cmd(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _plugin_flag(key):
    if key == "RegionId":
        return "--biz-region-id"
    return "--" + re.sub(r"(?<!^)(?=[A-Z])", "-", key).lower()
class CliError(Exception):
    """A CLI or API failure, rendered as ``Code: Message``."""

    def __init__(self, code, message):
        self.code = code
        self.message = redact_secrets(message or "")
        super(CliError, self).__init__("%s: %s" % (self.code, self.message))


def redact_secrets(text):
    """Mask credential-looking values in any text that may be shown or logged."""
    if not text:
        return text
    out = text
    for pattern, replacement in _SECRET_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def new_session_id():
    """One 32 character hex id per script run, used in the Observability UA."""
    return uuid.uuid4().hex


def build_user_agent(session_id=None):
    """Skill level aggregation: skill name plus the run's session id."""
    return UA_TEMPLATE.format(
        skill_name=SKILL_NAME,
        session_id=session_id or new_session_id(),
    )

_build_user_agent_raw = build_user_agent



_PACKAGE_NAME = "alibabacloud-ecs-boot-and-login-repair"


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
def build_user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_build_user_agent_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


def is_transient(code, message):
    haystack = "%s %s" % (code or "", message or "")
    return any(marker in haystack for marker in TRANSIENT_ERROR_MARKERS)


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


def flatten_params(api_name, params):
    """Render params as plugin-mode CLI tokens for one action."""
    return _list_param_argv(api_name, params, _plugin_flag, _param_text)
def _failure(raw_out, raw_err, returncode):
    text = (raw_err or "") + (raw_out or "")
    code_match = _ERROR_CODE_RE.search(text)
    message_match = _MESSAGE_RE.search(text)
    code = code_match.group(1) if code_match else "CliExit%s" % returncode
    message = message_match.group(1).strip() if message_match else text.strip()
    return code, redact_secrets(message)[:600]


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

def run_cli(api_name, params=None, session_id=None, timeout=CLI_TIMEOUT_SECONDS,
            retries=CLI_MAX_RETRIES, warn=None):
    """Call one whitelisted API and return its parsed JSON body.

    ``warn`` is an optional callable used to report a degraded step; the error is
    then re-raised so the caller decides how to continue.
    """
    meta = API_WHITELIST.get(api_name)
    if meta is None:
        raise CliError("ApiNotWhitelisted",
                       "%s is not on the API whitelist of %s" % (api_name, SKILL_NAME))

    user_agent = build_user_agent(session_id)
    argv = ["aliyun", meta["product"], _plugin_cmd(meta["cli_action"])] + flatten_params(api_name, params)
    argv.extend([USER_AGENT_FLAG, user_agent])

    attempts = max(1, int(retries) + 1)
    last_error = None
    for attempt in range(attempts):
        try:
            proc = _run_with_region_retry(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=timeout, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            last_error = CliError("CliTimeout",
                                  "%s did not answer within %ss" % (api_name, timeout))
            if attempt + 1 < attempts:
                time.sleep(CLI_BACKOFF_BASE_SECONDS * (2 ** attempt))
                continue
            break
        except OSError as exc:  # aliyun not installed, permission to fork, ...
            raise CliError("CliUnavailable", redact_secrets(str(exc)))

        if proc.returncode == 0:
            body = (proc.stdout or "").strip()
            if not body:
                return {}
            try:
                return _json_body(body)
            except ValueError:
                raise CliError("UnparsableResponse",
                               "response of %s is not JSON: %s"
                               % (api_name, redact_secrets(body)[:300]))

        code, message = _failure(proc.stdout, proc.stderr, proc.returncode)
        last_error = CliError(code, message)
        if not is_transient(code, message):
            break
        if attempt + 1 < attempts:
            time.sleep(CLI_BACKOFF_BASE_SECONDS * (2 ** attempt))

    if warn is not None:
        warn("[WARN] %s failed: %s" % (api_name, last_error))
    raise last_error


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
