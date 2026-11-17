"""Shared transport layer for OpenAPI calls made through the local Alibaba Cloud CLI.

The rules that matter are enforced once, here, and must not be re-implemented per call
site:

* every invocation is an argument vector executed without a shell, with its own timeout;
* every invocation carries the skill-level observability User-Agent built from a fresh
  32-character hex session id;
* only transient failures are retried, a bounded number of times, with backoff;
* credential material is masked out of every message this module can surface;
* callers receive :class:`CliError` carrying ``Code: Message``, and a failed call never
  aborts a whole run - the caller logs a ``[WARN]`` and keeps going.

Credentials come from the ambient credential chain only. Nothing in this module reads,
prints, stores or forwards an access key or a passphrase.
"""

import json
import re
import subprocess
import sys
import time
import uuid

import _constants as C

_SECRET_PATTERNS = (
    re.compile(r"(?i)(access\s*key\s*id|accesskey\s*id|accesskeyid)([\"'\s]*[:=][\"'\s]*)(\S+)"),
    re.compile(r"(?i)(access\s*key\s*secret|accesskey\s*secret|accesskeysecret)([\"'\s]*[:=][\"'\s]*)(\S+)"),
    re.compile(r"(?i)(security\s*token|session\s*token|securitytoken)([\"'\s]*[:=][\"'\s]*)(\S+)"),
    re.compile(r"(?i)(signature)([\"'\s]*[:=][\"'\s]*)(\S+)"),
    re.compile(r"(?i)(x-acs-signature[^=]*)=([^&\s]+)"),
    re.compile(r"(?i)(password|passwd|pwd)([\"'\s]*[:=][\"'\s]*)(\S+)"),
)

_ERROR_CODE_KEYS = ("ErrorCode:", "Code:", "ERROR:")


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
    """Return the per-run observability id (32 hex characters)."""
    return uuid.uuid4().hex


def user_agent(session_id):
    """Return the User-Agent value declared in SKILL.md -> Observability."""
    # replace(), not format(): the declared placeholder {session-id} has a hyphen, so it is
    # not a valid format field name.
    return C.UA_TEMPLATE.replace("{skill}", C.SKILL_NAME).replace("{session-id}", session_id)

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


def mask_secrets(text):
    """Replace anything that looks like a credential with a fixed placeholder."""
    if not text:
        return ""
    safe = str(text)
    for pattern in _SECRET_PATTERNS:
        safe = pattern.sub(lambda m: "%s%s***" % (m.group(1), m.group(2)), safe)
    return safe


def warn(message):
    sys.stderr.write("[WARN] %s\n" % mask_secrets(message))


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
    """A single failed call: ``Code: Message``. Non-fatal by construction."""

    def __init__(self, code, message, product=None, action=None):
        super(CliError, self).__init__("%s: %s" % (code, mask_secrets(message)))
        self.code = code
        self.message = mask_secrets(message)
        self.product = product
        self.action = action

    @property
    def is_denial(self):
        return self.code in C.DENIAL_ERROR_CODES or any(
            token in self.code for token in C.DENIAL_ERROR_CODES)

    @property
    def permission_point(self):
        """The exact action a denial refers to, for a minimal grant suggestion."""
        if self.product and self.action:
            return "%s:%s" % (self.product, self.action)
        return self.action or self.code


def _error_code_from(text):
    for line in (text or "").splitlines():
        stripped = line.strip()
        for key in _ERROR_CODE_KEYS:
            bare = stripped[len(key):].strip() if stripped.startswith(key) else None
            if bare:
                return bare.split(" ")[0].rstrip(",") or "Unknown"
    return "UnknownError"


def cli_action_name(action):
    """Return the CLI action token for a product call.

    ECS / VPC / Alidns / CMS / STS all use the CLI plugin form
    (lowercase-hyphenated), so ``DescribeInstances`` becomes
    ``describe-instances``. Callers keep using the OpenAPI action name, so
    ``related_apis.yaml``, the RAM table and the code all speak the same
    vocabulary.
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "-", str(action)).lower()


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


def build_args(product, action, params=None, session_id=None, region=None):
    """Assemble one argv tail for the CLI: product, plugin-mode action, named parameters."""
    args = [product, cli_action_name(action)]
    flat = {}
    if region:
        flat["RegionId"] = region
    for key, value in (params or {}).items():
        if value is None or value == "":
            continue
        flat[key] = value
    args += _list_param_argv(action, flat, _plugin_flag, _param_text, skip_empty=True)
    args.append("--user-agent")
    args.append(user_agent(session_id or new_session_id()))
    return args


def _attempt(args, timeout):
    return subprocess.run(
        _with_auto_plugin(["aliyun"] + list(args)),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


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

def call(product, action, params=None, region=None, session_id=None,
         timeout=None, retries=None, quiet=False):
    """Execute one API call and return the decoded payload.

    Raises :class:`CliError` when the call cannot be completed after the bounded retries.
    """
    args = build_args(product, action, params, session_id, region)
    budget = C.MAX_RETRIES if retries is None else max(0, int(retries))
    per_call = timeout or C.DEFAULT_TIMEOUT
    last_error = None

    for attempt in range(budget + 1):
        try:
            proc = _attempt(args, per_call)
        except FileNotFoundError:
            raise CliError("CliNotAvailable",
                           "the Alibaba Cloud CLI is not installed or not on PATH",
                           product, action)
        except subprocess.TimeoutExpired:
            last_error = CliError("ClientTimeout",
                                  "call exceeded %ss" % per_call, product, action)
            if not quiet:
                warn("%s %s timed out after %ss (attempt %d/%d)"
                     % (product, action, per_call, attempt + 1, budget + 1))
        else:
            stdout = (proc.stdout or b"").decode("utf-8", "replace")
            stderr = (proc.stderr or b"").decode("utf-8", "replace")
            if proc.returncode == 0:
                if not stdout.strip():
                    return {}
                try:
                    return _surface_error_envelope(_json_body(stdout))
                except ValueError:
                    return {"raw": stdout.strip()}
            code = _error_code_from(stderr or stdout)
            last_error = CliError(code, (stderr or stdout).strip() or "empty error",
                                  product, action)
            if code not in C.RETRYABLE_ERROR_CODES:
                raise last_error
            if not quiet:
                warn("%s %s failed with %s (attempt %d/%d)"
                     % (product, action, code, attempt + 1, budget + 1))

        if attempt < budget:
            time.sleep(C.BACKOFF_BASE_SECONDS ** attempt)

    raise last_error or CliError("UnknownError", "call failed", product, action)


def call_soft(product, action, params=None, **kwargs):
    """Call and degrade instead of raising; returns ``(payload, error_or_None)``.

    A single missing permission must not stop the remaining layers, so callers use this
    and turn ``error`` into a line in the *not excluded* section of the report.

    The CLI exits 0 on API error bodies, so an error envelope is converted into an
    error here: otherwise `Code: DomainNotBelongToUser` reaches the caller as an empty
    list and the tool concludes "no records" about a zone it could not read at all.
    """
    try:
        payload = call(product, action, params, **kwargs)
    except CliError as exc:
        warn("%s %s skipped: %s" % (product, action, exc))
        return {}, exc
    code = ""
    if isinstance(payload, dict):
        raw_code = payload.get("Code") or payload.get("code")
        if raw_code and str(raw_code) not in ("200", "0", "OK", "Success", "success"):
            code = str(raw_code)
    if code:
        message = str(payload.get("Message") or payload.get("message") or code)
        error = CliError(code, message, product, action)
        warn("%s %s skipped: %s" % (product, action, error))
        return {}, error
    return payload, None


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
