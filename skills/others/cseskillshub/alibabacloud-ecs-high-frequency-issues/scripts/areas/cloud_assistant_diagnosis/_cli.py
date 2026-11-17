"""Shared aliyun-CLI layer for Cloud Assistant diagnosis.

Contract enforced here rather than in prose:
  * one argument list per call, never a shell;
  * a per-call timeout, always;
  * a single session id per process, attached as a User-Agent to every call;
  * bounded retry for transient failures only;
  * secret material redacted before anything is surfaced.

This module never reads, accepts, stores or prints credential values. The
default aliyun credential chain is the only supported authentication.

Command style (verified against aliyun CLI 3.4.5): every product runs in
plugin mode, lowercase-hyphenated commands and flags:
  * ECS reads, e.g. `aliyun ecs describe-invocations --biz-region-id ...`;
  * the identity check: `aliyun sts get-caller-identity`.
Callers pass the PascalCase API action name; this layer translates it.
"""

import sys
import json
import re
import subprocess
import time
import uuid

from _constants import (
    AUTH_ERROR_TOKENS,
    CLI_BIN,
    CLI_TIMEOUT_SECONDS,
    CREDENTIAL_ERROR_TOKENS,
    MASKED,
    MAX_ATTEMPTS,
    PRODUCT_ECS,
    RETRY_BACKOFF_SECONDS,
    SECRET_VALUE_PATTERNS,
    SKILL_NAME,
    TRANSIENT_ERROR_TOKENS,
    USER_AGENT_FLAG,
    USER_AGENT_TEMPLATE,
)

_SESSION_ID = uuid.uuid4().hex

_COMPILED_SECRET_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE) for p in SECRET_VALUE_PATTERNS
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
def session_id():
    """32 hex characters, stable for the lifetime of one skill invocation."""
    return _SESSION_ID


def user_agent():
    return USER_AGENT_TEMPLATE.format(skill_name=SKILL_NAME, session_id=_SESSION_ID)

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
    """A failed CLI call, carrying the ``Code: Message`` shape."""

    def __init__(self, code, message, action=None, attempts=1):
        self.code = code
        self.action = action
        self.attempts = attempts
        super(CliError, self).__init__("{0}: {1}".format(code, message))


def mask_secrets(text):
    """Scrub credential-looking values. Applied to every stderr and error body."""
    if text is None:
        return ""
    text = str(text)
    for pattern in _COMPILED_SECRET_PATTERNS:
        text = pattern.sub(lambda m: m.group(1) + MASKED, text)
    return text


def _classify_failure(blob):
    """Return (code, message) parsed from whatever the CLI printed."""
    code = "CliCallFailed"
    message = blob.strip() or "no error detail returned by the CLI"
    match = re.search(r"Code:\s*([A-Za-z0-9_.\-]+)", blob)
    if match:
        code = match.group(1)
    else:
        # The CLI also prints bare "ERROR: ..." lines for local problems.
        for line in blob.splitlines():
            line = line.strip()
            if line.startswith("ERROR"):
                message = line
                break
    for token in TRANSIENT_ERROR_TOKENS + AUTH_ERROR_TOKENS + CREDENTIAL_ERROR_TOKENS:
        if token.lower() in blob.lower():
            code = token
            break
    return code, mask_secrets(message)


def _is_transient(code):
    return code in TRANSIENT_ERROR_TOKENS


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


def build_argv(action, params, product=PRODUCT_ECS):
    """Assemble one argument list. Values are passed as separate list items, so
    no string can ever be re-parsed by a shell."""
    argv = [CLI_BIN, product, _plugin_cmd(action)]
    argv += _list_param_argv(action, params, lambda key: _plugin_flag(key), _param_text)
    # The User-Agent is attached last so it cannot be displaced by a parameter
    # that happens to be named like a global flag.
    argv.extend([USER_AGENT_FLAG, user_agent()])
    return argv


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

def call(action, params=None, product=PRODUCT_ECS, timeout=CLI_TIMEOUT_SECONDS):
    """Run one class-A query or one consented class-B/C call; return parsed JSON.

    Raises CliError on a permanent failure or after the retry budget.
    """
    params = params or {}
    argv = build_argv(action, params, product=product)
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            completed = subprocess.run(
                _with_auto_plugin(argv),
                input=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("RequestTimeout",
                                  "CLI call exceeded {0}s".format(timeout),
                                  action=action, attempts=attempt)
        else:
            out = (completed.stdout or b"").decode("utf-8", "replace")
            err = (completed.stderr or b"").decode("utf-8", "replace")
            if completed.returncode == 0:
                try:
                    return _surface_error_envelope(_json_body(out)) if out.strip() else {}
                except ValueError:
                    raise CliError("InvalidResponse",
                                   mask_secrets("CLI returned a non-JSON body"),
                                   action=action, attempts=attempt)
            code, message = _classify_failure(err or out)
            last_error = CliError(code, message, action=action, attempts=attempt)
            if not _is_transient(code):
                raise last_error

        if attempt < MAX_ATTEMPTS and _is_transient(last_error.code):
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise last_error


def call_soft(action, params=None, product=PRODUCT_ECS, timeout=CLI_TIMEOUT_SECONDS):
    """Call and degrade instead of raising.

    Returns (payload, error). Exactly one of them is None. Failures are the
    caller's responsibility to surface as [WARN] lines, so one unavailable
    query never aborts a whole diagnosis.
    """
    try:
        return call(action, params=params, product=product, timeout=timeout), None
    except CliError as exc:
        return None, exc


def paginate_page_number(action, params, items_path, list_key,
                         product=PRODUCT_ECS, page_size=50, max_pages=8):
    """Follow PageNumber/PageSize pagination for ECS list responses.

    items_path: nested keys to the container dict (e.g. ["Invocations",
    "Invocation"]). list_key: unused when items_path already resolves a list;
    kept for explicit call sites. Returns (items, error_message_or_None);
    a failed page degrades to what was collected plus a note, never a raise,
    and the page guard is a hard ceiling.
    """
    collected = []
    note = None
    page = 1
    while page <= max_pages:
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = page_size
        payload, error = call_soft(action, page_params, product=product)
        if error is not None:
            note = "page {0} failed: {1}".format(page, mask_secrets(str(error)))
            break
        node = payload
        for key in items_path:
            node = (node or {}).get(key) if isinstance(node, dict) else None
        items = node or []
        if not isinstance(items, list):
            items = [items] if items else []
        collected.extend(items)
        if len(items) < page_size:
            break
        page += 1
    else:
        note = "stopped at the {0}-page guardrail; older history may be missing".format(
            max_pages)
    return collected, note


# Boundary assertions for the masking contract (run at import; a broken mask
# must stop the module, because a leaked value in a report is unrecoverable):
# normal: credential-free text passes through unchanged.
assert mask_secrets("invoke timed out on instance i-bp1example") == \
    "invoke timed out on instance i-bp1example"
# boundary: key=value and key: value forms of each secret are scrubbed.
_masked_kv = mask_secrets("AccessKeyId=STS.fakevalue123 SecurityToken: fake.token"
                          " Signature=fake%2Bsig Password: hunter2")
assert "fakevalue123" not in _masked_kv
assert "fake.token" not in _masked_kv
assert "fake%2Bsig" not in _masked_kv
assert "hunter2" not in _masked_kv
assert "AccessKeyId" in _masked_kv and MASKED in _masked_kv
# invalid: None and empty degrade to "" and never raise.
assert mask_secrets(None) == ""
assert mask_secrets("") == ""
# a throttling envelope normalizes to the "Throttling" token (so the retry
# budget owns it) and the message survives masking.
_cf_code, _cf_message = _classify_failure("Code: Throttling.User\nMessage: flow control")
assert _cf_code == "Throttling"
assert "flow control" in _cf_message
assert _is_transient("Throttling") and not _is_transient("NoPermission")


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
