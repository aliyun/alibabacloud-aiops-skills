"""Shared `aliyun` CLI layer: one session id per run, per-call timeout, bounded
retries, credential masking. Credentials themselves are never handled here; the
CLI resolves them from the machine's existing default credential chain.
"""

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    AUTH_ERROR_CODES,
    BACKOFF_BASE_SECONDS,
    CALL_TIMEOUT_SECONDS,
    CLI_BIN,
    MAX_ATTEMPTS,
    RETRYABLE_ERROR_CODES,
    RETRYABLE_MESSAGE_FRAGMENTS,
    SKILL_NAME,
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
USER_AGENT = _ua_normalize(USER_AGENT_TEMPLATE.format(skill_name=SKILL_NAME, session_id=SESSION_ID)) + " skill-version/" + _SKILL_VERSION

_ERROR_CODE_CANDIDATES = (
    "NoPermission",
    "ImplicitDeny",
    "InvalidAccessKeyId",
    "SignatureDoesNotMatch",
    "Throttling",
    "InternalError",
    "ServiceUnavailable",
    "Unauthorized",
)

_MASK_PATTERN = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|password|passwd|signature|"
    r"privatekey|accesstoken|token)\b(\s*[:=]\s*)['\"]?[^'\"\s,&]+['\"]?"
)


class CliError(Exception):
    """A failed CLI call, carrying `Code: Message` and whether it was transient."""

    def __init__(self, code, message, product=None, action=None, retryable=False):
        self.code = code
        self.message = mask_secrets(message or "")
        self.product = product
        self.action = action
        self.retryable = retryable
        super(CliError, self).__init__(str(self))

    def __str__(self):
        prefix = "%s/%s: " % (self.product, self.action) if self.product else ""
        return "%s%s: %s" % (prefix, self.code, self.message)

    @property
    def is_auth(self):
        return self.code in AUTH_ERROR_CODES or "NoPermission" in self.message


def mask_secrets(text):
    """Redact anything that looks like a credential value from arbitrary text."""
    if not text:
        return ""
    return _MASK_PATTERN.sub(lambda m: "%s%s***" % (m.group(1), m.group(2)), str(text))


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
    return _list_param_argv(action, params, _plugin_flag, _param_text, skip_empty=True)
def build_command(product, action, params=None):
    cmd = [CLI_BIN, product, _plugin_cmd(action)]
    cmd.extend(_flatten_params(action, params))
    cmd.extend(["--user-agent", USER_AGENT])
    return cmd


def _error_from_output(stdout, stderr):
    blob = "%s %s" % (stderr or "", stdout or "")
    code = "CliCallFailed"
    for candidate in _ERROR_CODE_CANDIDATES:
        if candidate in blob:
            code = candidate
            break
    match = re.search(r"Code:\s*([A-Za-z0-9._-]+)", blob)
    if match:
        code = match.group(1)
    return code, blob.strip()


def _is_retryable(code, message):
    if code in RETRYABLE_ERROR_CODES:
        return True
    lowered = (message or "").lower()
    return any(fragment in lowered for fragment in RETRYABLE_MESSAGE_FRAGMENTS)


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

def run_cli(product, action, params=None, timeout=CALL_TIMEOUT_SECONDS,
            attempts=MAX_ATTEMPTS):
    """Run one whitelisted read-only call and return its parsed JSON payload.

    Raises `CliError` immediately on a non-transient failure, or after `attempts`
    tries when the failure looks transient.
    """
    cmd = build_command(product, action, params)
    last_error = None
    total = max(1, attempts)
    for attempt in range(1, total + 1):
        try:
            completed = subprocess.run(
                _with_auto_plugin(cmd),
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError(
                "ClientTimeout",
                "call exceeded %ds" % timeout,
                product=product,
                action=action,
                retryable=True,
            )
        except OSError as error:
            raise CliError(
                "CliUnavailable",
                mask_secrets(error),
                product=product,
                action=action,
                retryable=False,
            )
        else:
            payload = None
            if completed.returncode == 0:
                try:
                    payload = _json_body(completed.stdout or "{}")
                except ValueError:
                    payload = None
                if payload is None:
                    raise CliError(
                        "UnparsableOutput",
                        "response was not valid JSON",
                        product=product,
                        action=action,
                        retryable=False,
                    )
            if payload is not None and not payload.get("Code"):
                return payload
            code, message = _error_from_output(
                completed.stdout if payload is None else json.dumps(payload),
                completed.stderr,
            )
            if payload is not None and payload.get("Code"):
                code = str(payload.get("Code"))
                message = str(payload.get("Message") or message)
            last_error = CliError(
                code,
                message,
                product=product,
                action=action,
                retryable=_is_retryable(code, message),
            )
            if not last_error.retryable:
                raise last_error
        if attempt < total:
            time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
    raise last_error


def run_cli_quiet(product, action, params=None, timeout=CALL_TIMEOUT_SECONDS,
                  attempts=MAX_ATTEMPTS):
    """Same as run_cli but returns (payload, error) so one evidence source can
    degrade without aborting the whole diagnosis."""
    try:
        return run_cli(product, action, params, timeout=timeout, attempts=attempts), None
    except CliError as error:
        return None, error


def warn(message):
    """Degrade loudly on stderr; the report carries the same item as a gap."""
    print("[WARN] %s" % mask_secrets(message), file=sys.stderr)


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
