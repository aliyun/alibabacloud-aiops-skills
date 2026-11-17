"""Shared aliyun CLI layer used by every call in this skill.

Responsibilities:
  * one ``session_id`` per run, attached as a User-Agent to every invocation;
  * an explicit timeout on every subprocess call;
  * bounded retry with exponential backoff for transient failures only;
  * redaction of credential-shaped values before any CLI output is echoed;
  * a single structured error type carrying ``Code: Message``.

Authentication relies solely on the default credential chain of the aliyun CLI.
This module never accepts, reads, stores or prints an AccessKey pair or a token.
"""

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    AUTH_DENIED_CODES,
    CLI_TIMEOUT_SECONDS,
    CLI_TIMEOUT_WRITE_SECONDS,
    ECS_PRODUCT,
    RETRY_BACKOFF_BASE_SECONDS,
    RETRY_MAX_ATTEMPTS,
    RETRYABLE_ERROR_CODES,
    SESSION_ID_LENGTH,
    SKILL_NAME,
    STS_PRODUCT,
    USER_AGENT_FLAG,
    USER_AGENT_TEMPLATE,
)

# Values that must never leave the process in clear text. These names are used
# exclusively to redact CLI output; no code path reads a credential of this kind.
_REDACTION_TARGETS = (
    "AccessKeyId",
    "AccessKeySecret",
    "SecurityToken",
    "Signature",
    "SignatureNonce",
    "SignatureVersion",
)

_TRANSIENT_STATUS_PATTERN = re.compile(r"\b(50[0234]|429)\b")


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
class CliError(RuntimeError):
    """A failed CLI call, carrying the remote error code when available."""

    def __init__(self, code, message, action=None):
        self.code = code or "Unknown"
        self.message = message or ""
        self.action = action or ""
        super(CliError, self).__init__("{0}: {1}".format(self.code, self.message))

    @property
    def is_auth_denied(self):
        return self.code in AUTH_DENIED_CODES or self.code.endswith(AUTH_DENIED_CODES)


def new_session_id():
    """Return the 32 character hex identifier used for one run of the skill."""
    return uuid.uuid4().hex[:SESSION_ID_LENGTH]


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


def redact(text):
    """Replace credential-shaped values in ``text`` with ``***``."""
    masked = text if isinstance(text, str) else str(text or "")
    for name in _REDACTION_TARGETS:
        masked = re.sub(
            r"({0}[\"']?\s*[=:]\s*[\"']?)[^\s,&\"'}}]+".format(name),
            r"\1***",
            masked,
            flags=re.IGNORECASE,
        )
    return masked


def _extract_code(message):
    for match in re.finditer(r"(?:Code|ERROR)\s*[::]?\s*[\"']?([A-Za-z0-9._-]+)", message):
        candidate = match.group(1)
        if candidate.lower() not in ("error", "failed"):
            return candidate, message
    for match in re.finditer(r"\"(?:code|Code)\"\s*:\s*\"([^\"]+)\"", message):
        return match.group(1), message
    return "CliExitNonZero", message


def _is_transient(code, message):
    if code in RETRYABLE_ERROR_CODES:
        return True
    for retryable in RETRYABLE_ERROR_CODES:
        if retryable in message:
            return True
    return bool(_TRANSIENT_STATUS_PATTERN.search(message))


def _sleep_before_retry(attempt):
    time.sleep(RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))


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

def _load_json(stdout, action):
    if not stdout:
        return {}
    try:
        return _json_body(stdout)
    except ValueError:
        raise CliError("UnparsableOutput", redact(stdout)[:400], action=action)


def run_cli(argv, session_id, timeout=CLI_TIMEOUT_SECONDS, parse_json=True, retry=True):
    """Execute one aliyun CLI call.

    ``argv`` is a full argument list, never a shell string, so no shell is
    involved and no metacharacter can be interpolated.
    """
    if not argv:
        raise CliError("EmptyCommand", "argv must not be empty")
    command = list(argv) + [USER_AGENT_FLAG, user_agent_for(session_id)]
    attempts = RETRY_MAX_ATTEMPTS if retry else 1
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            completed = subprocess.run(
                _with_auto_plugin(command),
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError(
                "ClientTimeout",
                "call exceeded {0}s on attempt {1}".format(timeout, attempt),
            )
            if attempt < attempts:
                _sleep_before_retry(attempt)
                continue
            raise last_error
        except FileNotFoundError:
            raise CliError(
                "AliyunCliMissing",
                "the aliyun CLI executable was not found on PATH; install it and "
                "run aliyun sts get-caller-identity",
            )

        if completed.returncode == 0:
            stdout = (completed.stdout or "").strip()
            stderr = redact((completed.stderr or "").strip())
            if stderr:
                print("[WARN] {0}".format(stderr.splitlines()[0]), file=sys.stderr)
            if not parse_json:
                return stdout
            payload = _load_json(stdout, argv[2] if len(argv) > 2 else "")
            # The CLI reports a refused or failed call as a JSON body on stdout with
            # exit code 0, so the return code cannot separate an error envelope from
            # a result. Reading `Code` here is what lets the caller see the refusal
            # at all; treating the envelope as data turns a denial into an empty
            # answer and an empty answer into a clean one.
            if not isinstance(payload, dict) or not payload.get("Code"):
                return payload
            code = str(payload.get("Code"))
            message = str(payload.get("Message") or "the service refused the call")
            last_error = CliError(
                code, message, action=argv[2] if len(argv) > 2 else "")
            if retry and _is_transient(code, message) and attempt < attempts:
                _sleep_before_retry(attempt)
                continue
            raise last_error

        detail = redact(((completed.stderr or "") + " " + (completed.stdout or "")).strip())
        code, message = _extract_code(detail)
        last_error = CliError(code, message, action=argv[2] if len(argv) > 2 else "")
        if retry and _is_transient(code, detail) and attempt < attempts:
            _sleep_before_retry(attempt)
            continue
        raise last_error

    raise last_error or CliError("CliFailed", "call failed without a reported reason")


def call_ecs(action, params, session_id, write=False, timeout=None):
    """Call an ECS OpenAPI action.

    ECS is an RPC product, so the action name stays in its documented
    PascalCase form while the product token stays lowercase.
    """
    if timeout is None:
        timeout = CLI_TIMEOUT_WRITE_SECONDS if write else CLI_TIMEOUT_SECONDS
    return run_cli(
        ["aliyun", ECS_PRODUCT, _plugin_cmd(action)] + _flatten_params(action, params),
        session_id,
        timeout=timeout,
        parse_json=True,
        retry=not write,
    )


def call_sts_plugin(subcommand_words, session_id, timeout=CLI_TIMEOUT_SECONDS):
    """Call an STS action through the CLI plugin form (lowercase-hyphenated)."""
    argv = ["aliyun", STS_PRODUCT] + list(subcommand_words)
    return run_cli(argv, session_id, timeout=timeout, parse_json=True, retry=True)


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
    return _list_param_argv(action, params, _plugin_flag, _param_text)
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
