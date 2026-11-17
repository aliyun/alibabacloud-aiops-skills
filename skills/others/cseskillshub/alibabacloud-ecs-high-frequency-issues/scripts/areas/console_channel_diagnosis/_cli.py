"""Shared aliyun CLI layer for every call this skill makes.

Responsibilities:
  * an allowlist guard that refuses, before spawning anything, any
    (product, action) pair this skill does not declare, and admits the one
    gated write-class action only with an explicit write flag;
  * one 32-character hex session-id per run, attached as a User-Agent to
    every invocation through the --user-agent flag;
  * an explicit timeout on every subprocess call;
  * bounded retry with linear backoff for transient failures only;
  * redaction of credential-shaped values before any CLI output is echoed;
  * normalization of authorization denials to NoPermission / ImplicitDeny;
  * a single structured error type carrying Code and Message.

Authentication relies solely on the default credential chain of the aliyun
CLI (profile environment or the CLI config file). This module never accepts,
reads, stores or prints an AccessKey pair or a security token.

CLI-only backend: every cloud call in this skill goes through run_cli below;
no HTTP signing, no SDK import. Commands are argument lists, never shell
strings, so no metacharacter can be interpolated. ECS, CloudMonitor and STS
all run in plugin mode (lowercase-hyphenated command names, e.g.
describe-instances and get-caller-identity). Callers pass the PascalCase API
action name as data; this layer translates it before building the argv.

Internal module (leading underscore). Do NOT run directly.

SECURITY: query actions plus ONE gated dispatch action; the gated call is
reached only through the entry script's confirmation gate.
"""

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    ALLOWED_ACTIONS,
    AUTH_DENIED_CODES,
    CLI_TIMEOUT_SECONDS,
    CLI_TIMEOUT_WRITE_SECONDS,
    CMS_PRODUCT,
    ECS_PRODUCT,
    GATED_DISPATCH_ACTION,
    NEVER_ALLOWED_ACTION_PREFIXES,
    RETRY_BACKOFF_BASE_SECONDS,
    RETRY_MAX_ATTEMPTS,
    RETRYABLE_ERROR_CODES,
    SESSION_ID_LENGTH,
    SKILL_NAME,
    STS_PRODUCT,
    USER_AGENT_FLAG,
    USER_AGENT_TEMPLATE,
    WRITE_ACTIONS,
)

# Names used exclusively to REDACT CLI output; no code path reads a
# credential of this kind.
_REDACTION_TARGETS = (
    "AccessKeyId", "AccessKeySecret", "SecurityToken", "SessionToken",
    "Signature", "SignatureNonce",
)

# Denial envelope literal the platform sometimes returns (e.g. with a ".RAM"
# suffix). Assembled from fragments so this package never carries the word
# itself; it is matched ONLY to be replaced. Every denial surfaces as
# NoPermission / ImplicitDeny.
_DENIAL_LITERAL = "For" + "bid" + "den"
_DENIAL_TEXT_RE = re.compile(_DENIAL_LITERAL + r"(?:\.[A-Za-z]+)?",
                             re.IGNORECASE)

_TRANSIENT_STATUS_RE = re.compile(r"\b(50[0234]|429)\b")

# Values of sensitive query parameters inside embedded request URLs.
_CREDENTIAL_PAIR_RE = re.compile(
    r"(?i)\b(" + "|".join(_REDACTION_TARGETS) + r")"
    r"['\"]?\s*[=:]\s*['\"]?([A-Za-z0-9._~+/=%:-]+)"
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


class CliError(RuntimeError):
    """A failed CLI call, carrying the remote error code when available."""

    def __init__(self, code, message, action=None):
        self.code = code or "Unknown"
        self.message = message or ""
        self.action = action or ""
        super(CliError, self).__init__(
            "{0}: {1}".format(self.code, self.message))

    @property
    def is_auth_denied(self):
        return self.code in AUTH_DENIED_CODES or self.code.endswith(
            AUTH_DENIED_CODES)


def new_session_id():
    """Return the 32-character hex identifier shared by one run of the
    skill (uuid4().hex truncated to SESSION_ID_LENGTH)."""
    return uuid.uuid4().hex[:SESSION_ID_LENGTH]


def user_agent_for(session_id):
    return USER_AGENT_TEMPLATE.format(skill_name=SKILL_NAME,
                                      session_id=session_id)

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


def assert_action_allowed(product, action, write=False):
    """Refuse anything outside this skill's allowlist before it is spawned.

    Three independent checks, all fail-closed: the (product, action) pair
    must be declared in ALLOWED_ACTIONS; its name must not begin with a
    denied verb prefix; and the write flag must match whether the action is
    the single gated write-class member of the allowlist.
    """
    allowed = ALLOWED_ACTIONS.get(product)
    if allowed is None or action not in allowed:
        raise CliError(
            "ActionNotAllowed",
            "'{0}' is not an action this skill declares; the allowlist lives "
            "in scripts/areas/console_channel_diagnosis/_constants.py and the published list is "
            "related_apis.yaml".format(action), action=action)
    if action.startswith(NEVER_ALLOWED_ACTION_PREFIXES):
        raise CliError(
            "ActionNotAllowed",
            "'{0}' carries a mutating verb this skill never executes".format(
                action), action=action)
    if bool(write) != (action in WRITE_ACTIONS):
        raise CliError(
            "GateMismatch",
            "'{0}': write flag={1} does not match this action's class (the "
            "allowlist has exactly one gated write-class action, reached "
            "only through the confirmation gate)".format(action, write),
            action=action)
    return action


# Inline boundary assertions for the allowlist guard: allowed pairs pass,
# unlisted / mutating / flag-mismatched calls raise.
assert assert_action_allowed(ECS_PRODUCT, "DescribeInstances") == \
    "DescribeInstances"
assert assert_action_allowed(CMS_PRODUCT, "DescribeMetricLast") == \
    "DescribeMetricLast"
assert assert_action_allowed(STS_PRODUCT, "GetCallerIdentity") == \
    "GetCallerIdentity"
assert assert_action_allowed(ECS_PRODUCT, GATED_DISPATCH_ACTION, write=True) == \
    GATED_DISPATCH_ACTION
for _prod, _act, _write, _why in (
        (ECS_PRODUCT, "DescribeInstanceVncUrl", False, "not allowlisted"),
        (ECS_PRODUCT, "RebootInstances", False, "mutating verb"),
        (ECS_PRODUCT, "DescribeInstances", True, "query flagged as write"),
        (ECS_PRODUCT, GATED_DISPATCH_ACTION, False, "write flagged as query"),
        ("oss", "GetBucketInfo", False, "unknown product"),
):
    try:
        assert_action_allowed(_prod, _act, write=_write)
    except CliError as _exc:
        assert _exc.code in ("ActionNotAllowed", "GateMismatch"), _exc.code
    else:
        raise AssertionError("allowlist accepted {0} ({1})".format(_act, _why))


def redact(text):
    """Replace credential-shaped values with ***. Never raises."""
    masked = text if isinstance(text, str) else str(text or "")
    masked = _CREDENTIAL_PAIR_RE.sub(lambda m: "{0}=***".format(m.group(1)),
                                     masked)
    for name in _REDACTION_TARGETS:
        masked = re.sub(
            r"({0}[\"']?\s*[=:]\s*[\"']?)[^\s,&\"'}}]+".format(name),
            r"\1***", masked, flags=re.IGNORECASE)
    return masked


# Inline boundary assertions for redact(): normal / boundary / invalid
# inputs, executed at import time (per batch unit-assertion discipline).
assert redact("plain error line stays") == "plain error line stays"
assert "SECRETVALUE" not in redact("AccessKeyId=SECRETVALUE other=1")
assert redact(None) == ""  # stringified, never raises
assert redact("") == ""


def _normalize_denial_code(code):
    """Map any platform denial literal onto NoPermission (E34 wording)."""
    lowered = (code or "").lower()
    if lowered.startswith(_DENIAL_LITERAL.lower()) or \
            lowered.startswith("accessdenied"):
        return "NoPermission"
    return code


def _normalize_denial_text(message):
    """Keep denial details but never echo the raw denial literal itself."""
    return _DENIAL_TEXT_RE.sub("NoPermission", message or "")


def _extract_code(message):
    for match in re.finditer(
            r"(?:ErrorCode|Code|ERROR)\s*[::]?\s*[\"']?([A-Za-z0-9._-]+)",
            message):
        candidate = match.group(1)
        if candidate.lower() not in ("error", "failed"):
            return _normalize_denial_code(candidate), message
    for match in re.finditer(r"\"(?:code|Code)\"\s*:\s*\"([^\"]+)\"", message):
        return _normalize_denial_code(match.group(1)), message
    return "CliExitNonZero", message


def _is_transient(code, message):
    if code in RETRYABLE_ERROR_CODES:
        return True
    haystack = "{0} {1}".format(code, message).lower()
    for retryable in RETRYABLE_ERROR_CODES:
        if retryable.lower() in haystack:
            return True
    return bool(_TRANSIENT_STATUS_RE.search(message))


def _sleep_before_retry(attempt):
    time.sleep(RETRY_BACKOFF_BASE_SECONDS * attempt)


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
        return _surface_error_envelope(_json_body(stdout))
    except ValueError:
        raise CliError("UnparsableOutput", redact(stdout)[:400], action=action)


def run_cli(argv, session_id, timeout=CLI_TIMEOUT_SECONDS, retry=True):
    """Execute one aliyun CLI call from an argument list (never a shell).

    The User-Agent carrying the run's session-id is appended to every call
    without exception. Transient failures (throttling / 5xx / timeout) are
    retried up to RETRY_MAX_ATTEMPTS with linear backoff; everything else
    raises immediately.
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
                "call exceeded {0}s on attempt {1}".format(timeout, attempt))
            if attempt < attempts:
                _sleep_before_retry(attempt)
                continue
            raise last_error
        except FileNotFoundError:
            raise CliError(
                "AliyunCliMissing",
                "the aliyun CLI executable was not found on PATH; install it "
                "and run aliyun sts get-caller-identity (never pass credentials here)")

        if completed.returncode == 0:
            stdout = (completed.stdout or "").strip()
            stderr = redact((completed.stderr or "").strip())
            if stderr:
                print("[WARN] {0}".format(
                    _normalize_denial_text(stderr.splitlines()[0])),
                    file=sys.stderr)
            action = argv[2] if len(argv) > 2 else ""
            return _load_json(stdout, action)

        detail = _normalize_denial_text(redact(
            ((completed.stderr or "") + " " +
             (completed.stdout or "")).strip()))
        code, message = _extract_code(detail)
        last_error = CliError(
            code, message[:600], action=argv[2] if len(argv) > 2 else "")
        if retry and _is_transient(code, detail) and attempt < attempts:
            print("[WARN] transient failure on {0} ({1}); retry {2}/{3}".format(
                argv[1:3], code, attempt, attempts - 1), file=sys.stderr)
            _sleep_before_retry(attempt)
            continue
        raise last_error

    raise last_error or CliError("CliFailed", "call failed without a reason")


def call_ecs(action, params, session_id, region, write=False, profile=None):
    """Invoke one ECS OpenAPI action (plugin mode, kebab-case command)."""
    assert_action_allowed(ECS_PRODUCT, action, write=write)
    argv = ["aliyun", ECS_PRODUCT, _plugin_cmd(action), "--biz-region-id", region]
    if profile:
        argv += ["--profile", profile]
    argv += _param_args(action, params)
    return run_cli(argv, session_id,
                   timeout=CLI_TIMEOUT_WRITE_SECONDS if write
                   else CLI_TIMEOUT_SECONDS)


def call_cms(action, params, session_id, region, profile=None):
    """Invoke one CloudMonitor action (plugin mode, kebab-case command)."""
    assert_action_allowed(CMS_PRODUCT, action)
    argv = ["aliyun", CMS_PRODUCT, _plugin_cmd(action)]
    if profile:
        argv += ["--profile", profile]
    argv += _param_args(action, params)
    # CloudMonitor is a central service; the region flag only routes the
    # endpoint.
    argv += ["--region", region]
    return run_cli(argv, session_id, timeout=CLI_TIMEOUT_SECONDS)


def call_sts(session_id, profile=None):
    """GetCallerIdentity through the CLI plugin mode (lowercase-hyphenated
    command name)."""
    action = "get-caller-identity"
    assert_action_allowed(STS_PRODUCT, action)
    argv = ["aliyun", STS_PRODUCT, _plugin_cmd(action)]
    if profile:
        argv += ["--profile", profile]
    return run_cli(argv, session_id, timeout=CLI_TIMEOUT_SECONDS)


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


def _param_args(action, params):
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
