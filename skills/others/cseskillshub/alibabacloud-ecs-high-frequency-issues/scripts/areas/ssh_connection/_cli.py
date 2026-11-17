"""Shared Alibaba Cloud CLI layer used by this skill's scripts.

Design rules this file implements:

* Every call is a fixed argument list handed to ``subprocess.run``. No shell
  string, no ``shell=True``, no string interpolation of user input into a
  command.
* Every call carries its own timeout, so a hung endpoint can never stall a
  diagnosis session.
* Every call is tagged with ``--user-agent`` built from
  ``AlibabaCloud-Agent-Skills/<skill>/<session-id>``; the session id is one
  32-character hex value generated per run, which makes each OpenAPI request
  traceable back to a single diagnosis.
* Only the actions in ``CLOUD_API_WHITELIST`` can be dispatched; anything else
  raises :class:`CliError` before a request is made.
* Credentials never enter this layer: the default credential chain of the local
  ``aliyun`` CLI profile is used, and all error text is masked before it is
  stored, printed or returned.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from _constants import (
    ALIYUN_BIN,
    AUTH_ERROR_MARKERS,
    CLI_MAX_ATTEMPTS,
    CLI_RETRY_BACKOFF_SECONDS,
    CLI_TIMEOUT_SECONDS,
    CLOUD_API_WHITELIST,
    CREDENTIAL_PATTERNS,
    MASKED,
    SKILL_NAME,
    TRANSIENT_ERROR_MARKERS,
    USER_AGENT_TEMPLATE,
)

_MASK_RES = [re.compile(pattern) for pattern in CREDENTIAL_PATTERNS]

TERMINAL_STATES = {
    "success", "finished", "failed", "error", "stopped", "cancelled",
    "canceled", "timeout", "partialfailed", "invalid", "deleted",
}


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
def new_session_id() -> str:
    """Return the 32-character hex id used for this diagnosis session."""
    return uuid.uuid4().hex


def build_user_agent(session_id: str) -> str:
    return USER_AGENT_TEMPLATE.format(skill=SKILL_NAME, session_id=session_id)

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


def mask_credentials(text: Any) -> str:
    """Redact anything that looks like a credential before it is surfaced."""
    value = text if isinstance(text, str) else str(text or "")
    for pattern in _MASK_RES:
        value = pattern.sub(MASKED, value)
    return value


def kebab(action: str) -> str:
    """Convert a PascalCase action to the hyphenated CLI sub-command form."""
    out = []
    for index, char in enumerate(action):
        if char.isupper() and index:
            out.append("-")
        out.append(char.lower())
    return "".join(out)


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
    """A CLI or service failure, with the service code kept separate."""

    def __init__(self, code: str, message: str, *, attempt: int = 1) -> None:
        self.code = code or "CliError"
        self.message = mask_credentials(message)
        self.attempt = attempt
        super().__init__("%s: %s" % (self.code, self.message))

    @property
    def is_auth_failure(self) -> bool:
        lowered = ("%s %s" % (self.code, self.message)).lower()
        return any(marker in lowered for marker in AUTH_ERROR_MARKERS)


def _is_transient(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in TRANSIENT_ERROR_MARKERS)


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

def _split_code(message: str) -> str:
    """Pull ``Code`` out of a ``Code: Message`` service error line."""
    head = message.strip().splitlines()[0] if message.strip() else ""
    if ":" in head:
        candidate = head.split(":", 1)[0].strip()
        if candidate and " " not in candidate:
            return candidate
    for token in head.replace(",", " ").split():
        if token.isalpha() and len(token) > 6 and token[0].isupper():
            return token
    return "CliError"


class AliyunCli:
    """Thin, auditable wrapper around the local ``aliyun`` CLI."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        *,
        timeout: int = CLI_TIMEOUT_SECONDS,
        max_attempts: int = CLI_MAX_ATTEMPTS,
        sleeper=time.sleep,
    ) -> None:
        self.session_id = session_id or new_session_id()
        self.user_agent = build_user_agent(self.session_id)
        self.timeout = timeout
        self.max_attempts = max(1, int(max_attempts))
        self._sleeper = sleeper
        self.call_log: List[Dict[str, Any]] = []

    # -- dispatch ------------------------------------------------------------
    def call(
        self,
        product: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        unchecked: bool = False,
    ) -> Dict[str, Any]:
        """Dispatch one OpenAPI call and return the parsed JSON body.

        ``product action`` must be in :data:`CLOUD_API_WHITELIST`; the check runs
        before any subprocess is started.
        """
        if not unchecked and (product, action) not in CLOUD_API_WHITELIST:
            raise CliError(
                "ApiNotAllowed",
                "'%s %s' is not part of the API whitelist of skill %s; this "
                "skill only calls Describe*/Get* actions plus the gated "
                "ecs RunCommand" % (product, action, SKILL_NAME),
            )

        argv: List[str] = [ALIYUN_BIN, product, _plugin_cmd(action)]
        argv += ["--user-agent", self.user_agent]
        argv += _flatten_params(action, params or {})

        last_error: Optional[CliError] = None
        for attempt in range(1, self.max_attempts + 1):
            started = time.time()
            try:
                completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
                    _with_auto_plugin(argv),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    stdin=subprocess.DEVNULL,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                last_error = CliError(
                    "CliTimeout",
                    "%s %s did not answer within %ss"
                    % (product, action, self.timeout),
                    attempt=attempt,
                )
                self._record(argv, attempt, started, "timeout", last_error)
                if _is_transient(last_error.message):
                    self._backoff(attempt)
                    continue
                raise last_error
            except FileNotFoundError:
                raise CliError(
                    "CliNotFound",
                    "the 'aliyun' command was not found; install the Alibaba "
                    "Cloud CLI and run 'aliyun sts get-caller-identity' with a valid profile",
                )
            except OSError as exc:  # pragma: no cover - defensive
                raise CliError("CliOsError", str(exc))

            stdout = mask_credentials(completed.stdout or "")
            stderr = mask_credentials(completed.stderr or "")
            if completed.returncode != 0:
                message = (stderr.strip() or stdout.strip() or
                           "no error detail returned")
                code = _split_code(message)
                last_error = CliError(code, message, attempt=attempt)
                self._record(argv, attempt, started, "error", last_error)
                if _is_transient(message) and attempt < self.max_attempts:
                    self._backoff(attempt)
                    continue
                raise last_error

            try:
                payload = _json_body(stdout) if stdout.strip() else {}
            except ValueError as exc:
                raise CliError(
                    "BadCliOutput",
                    "%s %s returned text that is not JSON: %s"
                    % (product, action, str(exc)),
                )
            if not isinstance(payload, dict):
                payload = {"Data": payload}
            self._record(argv, attempt, started, "ok", None)
            return _surface_error_envelope(payload)

        assert last_error is not None
        raise last_error

    # -- helpers -------------------------------------------------------------
    def _backoff(self, attempt: int) -> None:
        self._sleeper(CLI_RETRY_BACKOFF_SECONDS * attempt)

    def _record(
        self,
        argv: Sequence[str],
        attempt: int,
        started: float,
        outcome: str,
        error: Optional[CliError],
    ) -> None:
        self.call_log.append({
            "action": " ".join(argv[0:3]),
            "attempt": attempt,
            "duration_ms": int((time.time() - started) * 1000),
            "outcome": outcome,
            "code": error.code if error else "",
            "user_agent": self.user_agent,
        })

    def print_call_log(self, stream=None) -> None:
        """Emit the audited call list; used by the entry script footer."""
        target = stream or sys.stderr
        for entry in self.call_log:
            target.write(
                "[CALL] %s attempt=%s %s ms=%s%s\n"
                % (
                    entry["action"],
                    entry["attempt"],
                    entry["outcome"],
                    entry["duration_ms"],
                    " code=%s" % entry["code"] if entry["code"] else "",
                )
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


def _flatten_params(action, params):
    """Render params as plugin-mode CLI tokens for one action."""
    return _list_param_argv(action, params, _plugin_flag, _param_text)
def _as_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def dig(payload: Any, *candidates: Iterable[str]) -> Any:
    """Return the first present key, tolerating response shape differences.

    Field names of the ECS responses differ slightly across API versions, so the
    reader never asserts on one spelling: each step takes a candidate list and
    the caller decides what to do with ``None``.
    """
    current = payload
    for names in _candidate_groups(candidates):
        if isinstance(current, list):
            if len(current) == 1 and isinstance(current[0], dict):
                current = current[0]
            else:
                return None
        if not isinstance(current, dict):
            return None
        current = _pick(current, names)
        if current is None:
            return None
    return current


def _candidate_groups(candidates: Tuple[Any, ...]) -> List[Tuple[str, ...]]:
    groups: List[Tuple[str, ...]] = []
    for item in candidates:
        if isinstance(item, str):
            groups.append((item,))
        else:
            groups.append(tuple(item))
    return groups


def _pick(mapping: Dict[str, Any], names: Tuple[str, ...]) -> Any:
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for name in names:
        # A non-str entry means the caller nested a descent path into one
        # positional group instead of passing it as its own level. Skip it here
        # (never call .lower() on a tuple) so a missing key degrades to None
        # rather than crashing; the real multi-level path is walked by dig().
        if not isinstance(name, str):
            continue
        value = lowered.get(name.lower())
        if value is not None and value != "":
            return value
    return None


def dig_list(payload: Any, *candidates: Iterable[str]) -> List[Any]:
    """Like :func:`dig` but always returns a list."""
    value = dig(payload, *candidates)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def is_auth_error(error: CliError) -> bool:
    return error.is_auth_failure


def minimal_policy_snippet(actions: Iterable[str]) -> str:
    """Custom-policy JSON for exactly the listed actions, no wildcards."""
    policy = {
        "Version": "1",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": sorted(actions),
                "Resource": "*",
            }
        ],
    }
    return json.dumps(policy, indent=2, sort_keys=True)


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
