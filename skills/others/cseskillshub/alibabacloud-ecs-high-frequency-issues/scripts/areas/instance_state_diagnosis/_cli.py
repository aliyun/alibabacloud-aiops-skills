#!/usr/bin/env python3
"""
_cli.py -- shared Alibaba Cloud CLI layer for this skill.

Every cloud call in this package goes through call_cli() below; no other module
assembles an `aliyun` command line. Design rules enforced here:

* Argument lists only (never shell=True) with a per-call subprocess timeout.
* One 32-hex session id per run, attached as a User-Agent to every call so all
  traffic from one diagnosis session is attributable.
* Transient failures (throttling, 5xx, timeouts) are retried with backoff;
  anything else is raised immediately.
* All error text is credential-masked before it leaves this module.
* Credentials come only from the default credential chain; this module never
  reads, prints, caches or forwards any AccessKey or token value.
"""

from __future__ import annotations
import sys

import json
import re
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from _constants import DEFAULT_TIMEOUT, SKILL_NAME, STS_ENDPOINT

# ---------------------------------------------------------------------------
# Observability: session id and User-Agent template
# ---------------------------------------------------------------------------

SESSION_ID: str = uuid.uuid4().hex
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"



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
USER_AGENT = _ua_normalize(USER_AGENT_TEMPLATE.format(skill=SKILL_NAME, session_id=SESSION_ID)) + " skill-version/" + _SKILL_VERSION

MAX_ATTEMPTS = 3
RETRY_BASE_SECONDS = 1.5
RETRY_MAX_SECONDS = 8.0

TRANSIENT_MARKERS = (
    "throttling",
    "serviceunavailable",
    "internalerror",
    "systembusy",
    "requesttimeout",
    "please try again later",
    "i/o timeout",
    "connection reset",
    "connection refused",
    "unexpected eof",
    "no such host",
    "EOF",
    "500",
    "502",
    "503",
)

_SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b(access[_-]?key[_-]?id|access[_-]?key[_-]?secret|security[_-]?token|"
    r"sts[_-]?token|signature|password|passwd|private[_-]?key|bearer[_-]?token)"
    r"([\"']?\s*[:=]\s*)([^\s,;&\"'}]+)"
)
_SECRET_FLAG_RE = re.compile(
    r"(?i)(--(?:access-key-id|access-key-secret|sts-token|password))[=\s]+([^\s]+)"
)


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
    """A CLI failure, rendered as `Code: Message` with secrets masked."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = mask_secrets(message)
        super().__init__("%s: %s" % (self.code, self.message))

    @property
    def transient(self) -> bool:
        blob = ("%s %s" % (self.code, self.message)).lower()
        return any(marker.lower() in blob for marker in TRANSIENT_MARKERS)


def mask_secrets(text: Optional[str]) -> str:
    """Redact anything that looks like a credential from arbitrary text."""
    if not text:
        return ""
    masked = _SECRET_ASSIGN_RE.sub(lambda m: "%s%s***" % (m.group(1), m.group(2)), text)
    return _SECRET_FLAG_RE.sub(lambda m: "%s ***" % m.group(1), masked)


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(list(value) if isinstance(value, tuple) else value)
    return str(value)


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


def _flatten(action: str, params: Optional[Dict[str, Any]]) -> List[str]:
    """Turn a mapping into plugin-mode CLI tokens for one action."""
    return _list_param_argv(action, params, _plugin_flag, _stringify)


def build_command(
    product: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    endpoint: Optional[str] = None,
    region: Optional[str] = None,
) -> List[str]:
    """Compose the argv for one call. `action` keeps the product's own casing."""
    argv = ["aliyun", product, _plugin_cmd(action)]
    if region:
        argv.extend(["--region", region])
    if endpoint:
        argv.extend(["--endpoint", endpoint])
    argv.extend(_flatten(action, params))
    argv.extend(["--user-agent", USER_AGENT])
    return argv


def _extract_error(stdout: str, stderr: str) -> Tuple[str, str]:
    blob = "\n".join(part for part in (stderr, stdout) if part)
    code_match = re.search(r"ErrorCode:\s*([A-Za-z0-9._\-]+)", blob)
    message_match = re.search(r"Message:\s*(.+)", blob)
    if code_match:
        return code_match.group(1), message_match.group(1).strip() if message_match else blob
    if "is not a valid api" in blob or "unknown flag" in blob.lower():
        return "InvalidApiOrParameter", blob
    first = next((line.strip() for line in blob.splitlines() if line.strip()), "unknown error")
    return "CliCallFailed", first


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
def call_cli(
    product: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    endpoint: Optional[str] = None,
    region: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    attempts: int = MAX_ATTEMPTS,
) -> Dict[str, Any]:
    """Run one CLI call, retry transient failures, and return parsed JSON."""
    argv = build_command(product, action, params, endpoint, region)
    last_error: Optional[CliError] = None

    for attempt in range(1, max(1, attempts) + 1):
        try:
            completed = subprocess.run(
                _with_auto_plugin(argv),
                input=None,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("ClientTimeout", "%s timed out after %ss" % (action, timeout))
        except OSError as exc:
            raise CliError("CliNotAvailable", "aliyun CLI could not be executed: %s" % exc)
        else:
            if completed.returncode == 0:
                payload = (completed.stdout or "").strip()
                if not payload:
                    return {}
                try:
                    parsed = _json_body(payload)
                except ValueError:
                    raise CliError("InvalidResponse", "%s returned non-JSON output" % action)
                if isinstance(parsed, dict):
                    return _surface_error_envelope(parsed)
                return {"data": parsed}
            last_error = CliError(
                *_extract_error(completed.stdout or "", completed.stderr or "")
            )
            if not last_error.transient:
                raise last_error

        if attempt < max(1, attempts):
            time.sleep(min(RETRY_MAX_SECONDS, RETRY_BASE_SECONDS * (2 ** (attempt - 1))))

    if last_error is not None:
        raise last_error
    raise CliError("CliCallFailed", "%s failed without an error detail" % action)


def call_ecs(
    action: str,
    params: Dict[str, Any],
    region_id: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """One regional ECS call; RegionId is always passed explicitly."""
    merged: Dict[str, Any] = {"RegionId": region_id}
    merged.update(params or {})
    return call_cli("ecs", action, merged, region=region_id, timeout=timeout)


def caller_identity(timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """STS identity check (plugin-mode command name, lowercase-hyphenated)."""
    return call_cli("sts", "GetCallerIdentity", endpoint=STS_ENDPOINT, timeout=timeout)


def command_preview(argv: Sequence[str]) -> str:
    """Space-joined argv for logs, with any credential value masked."""
    return mask_secrets(" ".join(argv))


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
