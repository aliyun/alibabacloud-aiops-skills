"""Shared transport layer for the Alibaba Cloud CLI used by this skill.

Responsibilities:
  * build one argument list per call, with no shell interpreter involved at all;
  * tag every single call with a per-run observability User-Agent;
  * enforce a timeout on every subprocess call;
  * retry only transient failures with backoff;
  * mask credential-looking material in any text that leaves this module.

Authentication comes from the CLI's own default credential chain. This module never
takes, reads, stores or prints an AccessKey pair or a security token.
"""

import sys
import json
import re
import subprocess
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

from _constants import (
    CLI_BACKOFF_BASE_SECONDS,
    CLI_BINARY,
    CLI_MAX_ATTEMPTS,
    CLI_POLL_TIMEOUT_SECONDS,
    CLI_TIMEOUT_SECONDS,
    ECS_PRODUCT,
    SKILL_NAME,
    UA_TEMPLATE,
)

# Text that must never appear in logs or reports.
_MASK_PATTERNS = (
    re.compile(r"(?i)(accesskeyid|accesskeysecret|access_key_secret|securitytoken|"
               r"sts_token|password|signature|privatekey)\s*[=:]\s*([^\s&,\"'}]+)"),
)

# Failures worth retrying: rate limiting, transport trouble, provider-side 5xx.
_TRANSIENT_MARKERS = (
    "throttling",
    "throttlingexception",
    "userflowcontrol",
    "serviceunavailable",
    "internalerror",
    "systembusy",
    "timed out",
    "timeout",
    "connection reset",
    "connection refused",
    "http 5",
    "500 ",
    "502 ",
    "503 ",
    "504 ",
)

_PERMISSION_MARKERS = ("nopermission", "implicitdeny", "accessdenied", "unauthorized", "not authorized")


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
    """A CLI call failed. str(error) is always 'Code: Message'."""

    def __init__(self, code: str, message: str, *, transient: bool = False) -> None:
        super().__init__("%s: %s" % (code, message))
        self.code = code
        self.message = message
        self.transient = transient
        self.is_permission_failure = any(marker in message.lower() for marker in _PERMISSION_MARKERS)


def new_session_id() -> str:
    """One 32-character hex id per skill run, reused for every CLI call of that run."""
    return uuid.uuid4().hex


def user_agent_for(session_id: str) -> str:
    return UA_TEMPLATE.format(skill_name=SKILL_NAME, session_id=session_id)

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


def mask_secrets(text: Any) -> str:
    """Replace credential-looking values with *** before anything is printed or stored."""
    value = text if isinstance(text, str) else str(text)
    for pattern in _MASK_PATTERNS:
        value = pattern.sub(lambda m: "%s=***" % m.group(1), value)
    return value


def _split_error(body: str) -> Tuple[str, str]:
    """Recover a Code/Message pair from CLI or API error output."""
    code_match = re.search(r'"(?:Code|ErrorCode)"\s*:\s*"([^"]+)"', body)
    message_match = re.search(r'"Message"\s*:\s*"([^"]+)"', body)
    if not code_match:
        code_match = re.search(r"(?:ErrorCode|Code)\s*:\s*(\S[^\n]*)", body)
    if not message_match:
        message_match = re.search(r"Message\s*:\s*(\S[^\n]*)", body)
    code = (code_match.group(1).strip() if code_match else "")
    message = (message_match.group(1).strip() if message_match else "")
    if code and message:
        return code, message
    if code:
        return code, message or "no message returned"
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("ERROR:"):
            return "CliInvocationFailed", stripped[len("ERROR:"):].strip() or body
    first = next((line.strip() for line in body.splitlines() if line.strip()), "no error text returned")
    return "CliInvocationFailed", first


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


def build_command(product: str, action: str, params: Optional[Dict[str, Any]],
                  session_id: str, region_id: Optional[str] = None) -> List[str]:
    """Assemble the argv list for a single RPC-style call."""
    argv: List[str] = [CLI_BINARY, product, _plugin_cmd(action)]
    merged: Dict[str, Any] = dict(params or {})
    if region_id and "RegionId" not in merged:
        merged["RegionId"] = region_id
    argv += _list_param_argv(action, merged, lambda key: _plugin_flag(key), _param_text, skip_empty=True)
    argv.extend(["--user-agent", user_agent_for(session_id)])
    return argv


def call(product: str, action: str, params: Optional[Dict[str, Any]] = None, *,
         session_id: str, region_id: Optional[str] = None,
         timeout: int = CLI_TIMEOUT_SECONDS, attempts: int = CLI_MAX_ATTEMPTS,
         dry_run: bool = False, sleep: Optional[Any] = None) -> Dict[str, Any]:
    """Invoke one OpenAPI action through the CLI and return the decoded payload.

    Raises CliError when the call ultimately fails. Permission failures are raised
    immediately; transient failures are retried with exponential backoff.
    """
    argv = build_command(product, action, params, session_id, region_id)
    if dry_run:
        return {"DryRun": True, "Command": " ".join(mask_secrets(part) for part in argv)}

    wait = sleep or time.sleep
    last_error: Optional[CliError] = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv list, no shell
                _with_auto_plugin(argv),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("CliTimeout",
                                  "%s did not return within %ss (attempt %d)" % (action, timeout, attempt),
                                  transient=True)
        else:
            stdout = mask_secrets(completed.stdout.decode("utf-8", "replace")).strip()
            stderr = mask_secrets(completed.stderr.decode("utf-8", "replace")).strip()
            if completed.returncode == 0:
                return _decode(stdout, action)
            code, message = _split_error(stderr or stdout)
            lowered = ("%s %s" % (code, message)).lower()
            transient = any(marker in lowered for marker in _TRANSIENT_MARKERS)
            last_error = CliError(code, message, transient=transient)

        if last_error is not None and not last_error.transient:
            raise last_error
        if attempt < max(1, attempts):
            wait(CLI_BACKOFF_BASE_SECONDS ** attempt)
    raise last_error if last_error else CliError("CliInvocationFailed", "%s failed without a reason" % action)


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

def _decode(stdout: str, action: str) -> Dict[str, Any]:
    if not stdout:
        return {}
    try:
        payload = _surface_error_envelope(_json_body(stdout))
    except ValueError:
        raise CliError("UnexpectedPayload", "%s returned output that is not JSON" % action)
    if isinstance(payload, list):
        return {"Items": payload}
    if not isinstance(payload, dict):
        raise CliError("UnexpectedPayload", "%s returned a scalar value" % action)
    return payload


def call_poll(action: str, params: Optional[Dict[str, Any]] = None, *, session_id: str,
              region_id: str, deadline_seconds: int = CLI_POLL_TIMEOUT_SECONDS,
              interval: int = 5, sleep: Optional[Any] = None,
              timeout: int = CLI_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Repeatedly call a Describe* action until the predicate-free payload changes.

    Used for Cloud Assistant results, which are only complete once the command has
    finished on the instance. Every individual call still carries its own timeout.
    """
    wait = sleep or time.sleep
    waited = 0
    payload: Dict[str, Any] = {}
    while waited <= deadline_seconds:
        payload = call(ECS_PRODUCT, action, params, session_id=session_id, region_id=region_id,
                       timeout=timeout, attempts=1)
        if _invocation_settled(payload):
            return payload
        wait(interval)
        waited += interval
    return payload


def _invocation_settled(payload: Dict[str, Any]) -> bool:
    """Settled means the invocation reached a terminal state, not that bytes arrived.

    Measured live on a real instance: Cloud Assistant streams partial output, so
    `df -h` had already returned 322 bytes while its InvocationStatus was still
    `Running`. The old order returned True on the first non-empty Output, and the
    probe then reported `status OK / result collected` over an unfinished read.
    No offline stub serves DescribeInvocations, so only a live run could show it.

    The invocation-specific status keys are preferred over a bare `Status`: a
    nested instance `Status: Running` describes the instance, not the command, and
    treating it as the command's state would poll forever.
    """
    statuses = [str(status).lower() for status in collect_values(
        payload, "InvocationStatus", "InvokeStatus", "InstanceInvokeStatus")]
    if not statuses:
        statuses = [str(status).lower() for status in collect_values(payload, "Status")]
    pending = {"running", "pending", "scheduled", "invoking", "stopping"}
    if statuses:
        return not any(status in pending for status in statuses)
    for key in ("Output", "InvocationOutput"):
        for value in collect_values(payload, key):
            if isinstance(value, str) and value.strip():
                return True
    return False


def collect_values(payload: Any, *keys: str) -> List[Any]:
    """Walk a decoded response and yield every value stored under any of `keys`.

    Response shapes are treated as data found at run time rather than assumed: callers
    report what came back instead of relying on a hard-coded path.
    """
    found: List[Any] = []
    targets = {key.lower() for key in keys}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in targets:
                    found.append(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def first_value(payload: Any, *keys: str, default: Any = None) -> Any:
    for value in collect_values(payload, *keys):
        if isinstance(value, (dict, list)):
            continue
        if value not in (None, ""):
            return value
    return default


def records(payload: Any, list_keys: Iterable[str]) -> List[Dict[str, Any]]:
    """Extract resource records without assuming one exact nesting shape.

    `list_keys` names the element key the response uses for a list of resources (for
    example Disk, Instance, Snapshot). An empty result means the API returned nothing,
    which callers report as such instead of inventing values.
    """
    elements = {str(key).lower() for key in list_keys}
    collected: List[Dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in elements and isinstance(value, list):
                    collected.extend(item for item in value if isinstance(item, dict))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return collected


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
