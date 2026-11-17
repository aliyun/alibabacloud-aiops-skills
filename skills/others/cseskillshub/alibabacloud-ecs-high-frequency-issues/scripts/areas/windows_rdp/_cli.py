"""Shared aliyun-CLI transport layer for the Windows RDP diagnosis skill.

Responsibilities
    * Build argument-list invocations (never a shell string) for the aliyun CLI.
    * Attach one observability session id per run to every call via User-Agent,
      built from the template AlibabaCloud-Agent-Skills/{skill}/{session-id}.
    * Retry transient failures (throttling / 5xx / timeout) with jittered
      backoff; raise everything else immediately.
    * Mask credential material out of every error string before it surfaces.
    * Enforce a per-call timeout so one slow request cannot hang the report.

Credentials always come from the default credential chain of the locally
configured CLI. This module never reads, stores, prints or passes key material.

The single write-class action this skill uses (the ECS Cloud Assistant command
dispatch) is reached through :func:`run_cli` like any other call; the *payload*
it sends is always a whitelisted, non-mutating query command, and the decision
to dispatch at all is made by the entry script behind an explicit confirmation
gate -- never here.
"""

import sys
import base64
import json
import random
import re
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from _constants import (
    CLI_BACKOFF_BASE_SECONDS,
    CLI_BACKOFF_MAX_SECONDS,
    CLI_BINARY,
    CLI_MAX_RETRIES,
    CLI_TIMEOUT_SECONDS,
    CODE_API_ERROR,
    CODE_CLI_TIMEOUT,
    CODE_CLI_UNAVAILABLE,
    CODE_IMPLICIT_DENY,
    CODE_INVALID_CREDENTIAL,
    CODE_NO_PERMISSION,
    CODE_PARSE_ERROR,
    CREDENTIAL_ERROR_MARKERS,
    MASKED_VALUE,
    NON_RETRYABLE_MARKERS,
    PLUGIN_MODE_COMMANDS,
    RETRYABLE_MARKERS,
    SENSITIVE_KEY_PATTERNS,
    SKILL_NAME,
    USER_AGENT_TEMPLATE,
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


class CliError(Exception):
    """A CLI or API failure rendered as ``Code: Message``."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        self.code = code
        self.message = mask_credentials(message)
        self.retryable = retryable
        super().__init__("{0}: {1}".format(self.code, self.message))


def new_session_id() -> str:
    """Return a fresh 32-char hex id, one per skill run."""
    return uuid.uuid4().hex


def build_user_agent(session_id: str) -> str:
    """Return the observability User-Agent for this run."""
    return USER_AGENT_TEMPLATE.format_map(
        {"skill": SKILL_NAME, "session-id": session_id}
    )

_build_user_agent_raw = build_user_agent



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
def build_user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_build_user_agent_raw(*_ua_a, **_ua_k))) + " skill-version/" + _SKILL_VERSION


_MASK_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_KEY_PATTERNS]


def mask_credentials(text: Any) -> str:
    """Redact anything that looks like a credential pair from ``text``.

    Both ``key=value`` and ``key: value`` spellings are collapsed, and bare
    token-like strings following a sensitive key are dropped too. The key name
    is kept so a permission or parameter problem stays diagnosable.
    """
    if text is None:
        return ""
    value = text if isinstance(text, str) else str(text)
    for pattern in _MASK_PATTERNS:
        value = re.sub(
            r"(?i)(" + pattern.pattern + r")(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&}]+)",
            lambda m: m.group(1) + m.group(2) + MASKED_VALUE,
            value,
        )
        value = re.sub(
            r"(?i)(" + pattern.pattern + r")(\s+)(\"[^\"]*\"|'[^']*'|[A-Za-z0-9/+=_-]{8,})",
            lambda m: m.group(1) + m.group(2) + MASKED_VALUE,
            value,
        )
    return value


def classify_error(message: str) -> Tuple[str, bool]:
    """Map a raw failure message onto ``(error_code, retryable)``."""
    lowered = (message or "").lower()
    if CODE_IMPLICIT_DENY.lower() in lowered:
        return CODE_IMPLICIT_DENY, False
    if CODE_NO_PERMISSION.lower() in lowered or "accessdenied" in lowered:
        return CODE_NO_PERMISSION, False
    for marker in CREDENTIAL_ERROR_MARKERS:
        if marker in lowered:
            return CODE_INVALID_CREDENTIAL, False
    for marker in NON_RETRYABLE_MARKERS:
        if marker in lowered:
            return CODE_API_ERROR, False
    for marker in RETRYABLE_MARKERS:
        if marker in lowered:
            return CODE_API_ERROR, True
    return CODE_API_ERROR, False


def _action_token(product: str, action: str) -> str:
    """Resolve the CLI command form for an action.

    Every product here (ecs, sts) runs in plugin mode, so the PascalCase API
    action name becomes a lowercase-hyphenated subcommand; PLUGIN_MODE_COMMANDS
    holds the explicit overrides.
    """
    mapped = PLUGIN_MODE_COMMANDS.get((product.lower(), action))
    if mapped:
        return mapped
    return re.sub(r"(?<!^)(?=[A-Z])", "-", action).lower()


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


def build_command(
    product: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    session_id: str = "",
) -> List[str]:
    """Assemble the argv list for one CLI call, User-Agent included."""
    command = [CLI_BINARY, product, _action_token(product, action)]
    command += _list_param_argv(action, params, lambda key: _plugin_flag(key), _param_text, skip_empty=True)
    command.append("--user-agent")
    command.append(build_user_agent(session_id))
    return command


def run_cli(
    product: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    timeout: int = CLI_TIMEOUT_SECONDS,
    retries: int = CLI_MAX_RETRIES,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute one CLI call and return the decoded JSON payload.

    Transient failures are retried with jittered backoff. A non-retryable
    failure raises :class:`CliError` carrying a ``Code: Message`` payload.
    """
    if session_id is None:
        session_id = new_session_id()
    params = dict(params or {})

    command = build_command(product, action, params, session_id)
    last_error: Optional[CliError] = None

    for attempt in range(1, max(1, retries) + 1):
        try:
            completed = subprocess.run(
                _with_auto_plugin(command),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
                universal_newlines=True,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError(
                CODE_CLI_TIMEOUT,
                "{0} {1} did not return within {2}s".format(product, action, timeout),
                retryable=True,
            )
            if warnings is not None:
                warnings.append(
                    "retry {0}/{1} after a {2}s timeout on {3} {4}".format(
                        attempt, retries, timeout, product, action
                    )
                )
            time.sleep(_backoff(attempt))
            continue
        except FileNotFoundError:
            raise CliError(
                CODE_CLI_UNAVAILABLE,
                "the aliyun CLI was not found on PATH; install it and run aliyun sts get-caller-identity",
                retryable=False,
            )
        except OSError as exc:  # pragma: no cover - environment specific
            raise CliError(CODE_CLI_UNAVAILABLE, mask_credentials(exc), retryable=False)

        if completed.returncode == 0:
            stdout = completed.stdout or ""
            stderr = mask_credentials(completed.stderr or "")
            if stderr.strip() and warnings is not None:
                warnings.append(
                    "cli notice from {0} {1}: {2}".format(product, action, stderr.strip())
                )
            return parse_payload(stdout, product, action)

        detail = mask_credentials(
            (completed.stderr or "") + " " + (completed.stdout or "")
        ).strip()
        code, retryable = classify_error(detail)
        last_error = CliError(
            code, "{0} {1} failed: {2}".format(product, action, detail), retryable
        )
        if not retryable:
            raise last_error
        if warnings is not None:
            warnings.append(
                "retry {0}/{1} after transient failure on {2} {3}".format(
                    attempt, retries, product, action
                )
            )
        time.sleep(_backoff(attempt))

    assert last_error is not None
    raise last_error


def _backoff(attempt: int) -> float:
    """Exponential backoff with jitter, capped by ``CLI_BACKOFF_MAX_SECONDS``."""
    delay = CLI_BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1))
    delay = min(delay, CLI_BACKOFF_MAX_SECONDS)
    return delay * (0.7 + 0.6 * random.random())


def encode_command_content(script: str) -> str:
    """Return the base64 form of a diagnostic script for ContentEncoding=Base64.

    The command text is data sent to a read API, never a credential; base64 is
    used only so the CLI argument survives spaces and quoting intact.
    """
    return base64.b64encode(script.encode("utf-8")).decode("ascii")


def parse_payload(stdout: str, product: str, action: str) -> Dict[str, Any]:
    """Decode the JSON body printed by the CLI, tolerating stray log noise."""
    text = (stdout or "").strip()
    if not text:
        return {}
    start = _first_json_offset(text)
    if start is None:
        raise CliError(
            CODE_PARSE_ERROR,
            "{0} {1} returned no parsable JSON body".format(product, action),
            retryable=False,
        )
    try:
        decoded, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError as exc:
        raise CliError(
            CODE_PARSE_ERROR,
            mask_credentials(
                "{0} {1} returned malformed JSON: {2}".format(product, action, exc)
            ),
            retryable=False,
        )
    if isinstance(decoded, list):
        return {"items": decoded}
    if isinstance(decoded, dict):
        return _surface_error_envelope(decoded)
    return {"value": decoded}


def _first_json_offset(text: str) -> Optional[int]:
    offsets = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not offsets:
        return None
    return min(offsets)


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
