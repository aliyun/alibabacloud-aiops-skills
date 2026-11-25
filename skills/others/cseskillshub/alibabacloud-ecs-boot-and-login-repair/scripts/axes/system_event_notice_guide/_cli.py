"""Shared layer that calls the Alibaba Cloud CLI for this skill.

Rules implemented here:
  * argument lists only, never a shell, so no customer text can be re-interpreted
  * a per-call timeout on every subprocess invocation
  * one 32 hex session id per run, attached as a user agent to every call
  * bounded retry with backoff for transient failures only
  * masking of credential-looking values in every message that leaves this module
  * no credential value is ever read, passed, printed or stored by this skill
"""

import json
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from _constants import (
    ALIYUN_BIN,
    ALLOWED_READ_ACTIONS,
    AUTH_ERROR_TOKENS,
    AUTH_FAIL_IMPLICIT_DENY,
    AUTH_FAIL_NO_PERMISSION,
    CLI_TIMEOUT_SECONDS,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE_SECONDS,
    RETRYABLE_ERROR_TOKENS,
    SENSITIVE_VALUE_TOKENS,
    SKILL_NAME,
    USER_AGENT_TEMPLATE,
)


def new_session_id() -> str:
    """Return the 32 hex character id that ties every call of one run together."""
    return uuid.uuid4().hex


def build_user_agent(session_id: str) -> str:
    return USER_AGENT_TEMPLATE.format_map(
        {"skill": SKILL_NAME, "session-id": session_id,
         "skill-version": _SKILL_VERSION})

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
    return _ua_normalize(str(_build_user_agent_raw(*_ua_a, **_ua_k)))


class CliError(Exception):
    """A failed call, carrying `Code: Message`."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(code + ": " + message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def is_authorization_failure(self) -> bool:
        return is_authorization_error(self.code + " " + self.message)

    def canonical_auth_label(self) -> Optional[str]:
        if not self.is_authorization_failure():
            return None
        lowered = (self.code + " " + self.message).lower()
        if "implicitdeny" in lowered:
            return AUTH_FAIL_IMPLICIT_DENY
        return AUTH_FAIL_NO_PERMISSION


_REDACT_RULES = []
for _token in SENSITIVE_VALUE_TOKENS:
    _escaped = re.escape(_token)
    _REDACT_RULES.append(
        (
            re.compile(r"(?i)(" + _escaped + r"\s*[=:]\s*)([^\s,;&\"']+)"),
            r"\g<1>***",
        )
    )
    _REDACT_RULES.append(
        (
            re.compile(r"(?i)\b(" + _escaped + r")(\s+)([A-Za-z0-9/+=_.\-]{6,})"),
            r"\g<1>\g<2>***",
        )
    )


_AUTO_PLUGIN_PROBED = False


def _with_auto_plugin(argv):
    """Resolve a missing product plugin without an interactive prompt.

    auto-plugin-install is a `configure set` profile key, not a per-invocation
    flag. Only a host that actually lacks this product's plugin is touched;
    `plugin list` is a local inventory read with no credential or network use.
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


def _json_body(text):
    """Decode the CLI's JSON body even when a notice precedes it on stdout."""
    try:
        return json.loads(text)
    except ValueError:
        offsets = [index for index in (text.find("{"), text.find("[")) if index != -1]
        if not offsets:
            raise
        return json.JSONDecoder().raw_decode(text[min(offsets):])[0]


_REGION_FLAG_REQUIRED_RES = (
    re.compile(r"missing required parameter\(s\):\s*--biz-region-id"),
    re.compile(r"--biz-region-id is required"),
)


def _region_flag_retry(cmd, stderr, region=None):
    """The same call with the plugin's region parameter, or None if not applicable."""
    if "--biz-region-id" in cmd:
        return None
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


def _run_cli(argv, timeout, region=None, **kwargs):
    """One CLI invocation; the plugin-region refusal is retried once."""
    completed = subprocess.run(_with_auto_plugin(argv), timeout=timeout, **kwargs)
    if completed.returncode != 0:
        stderr = completed.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        retry = _region_flag_retry(argv, stderr, region)
        if retry is not None:
            completed = subprocess.run(_with_auto_plugin(retry), timeout=timeout, **kwargs)
    return completed


def redact(text: str) -> str:
    """Mask values that follow a credential-looking field name."""
    safe = text or ""
    for pattern, replacement in _REDACT_RULES:
        safe = pattern.sub(replacement, safe)
    return safe


def warn(message: str) -> None:
    sys.stderr.write("[WARN] " + redact(message) + "\n")
    sys.stderr.flush()


def _contains(token: str, needles: Iterable[str]) -> bool:
    lowered = token.lower()
    for needle in needles:
        if needle in lowered:
            return True
    return False


def is_transient_error(code: str, message: str = "") -> bool:
    return _contains(code + " " + message, RETRYABLE_ERROR_TOKENS)


def is_authorization_error(text: str) -> bool:
    return _contains(text, AUTH_ERROR_TOKENS)


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(list(value) if isinstance(value, tuple) else value)
    return str(value)


def _first_match(patterns: Sequence[str], text: str) -> Optional[re.Match]:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match
    return None


def parse_cli_error(stderr_text: str, returncode: int) -> Tuple[str, str]:
    """Turn raw CLI stderr into an (error code, message) pair."""
    text = redact(stderr_text or "").strip()
    if not text:
        return ("CliExit" + str(returncode), "the command exited without a message")
    code_match = _first_match(
        (r"ErrorCode:\s*([^\r\n]+)", r"'([A-Za-z0-9._-]+)'\s+is\s+not"), text
    )
    message_match = _first_match(
        (r"Message:\s*([^\r\n]+)", r"ERROR:\s*([^\r\n]+)"), text
    )
    code = code_match.group(1).strip() if code_match else ""
    message = message_match.group(1).strip() if message_match else text.splitlines()[0]
    if not code:
        code = message.split(" ")[0][:64] if message else "CliExit" + str(returncode)
    return (code, message or text)


def run_aliyun(
    product: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    timeout: int = CLI_TIMEOUT_SECONDS,
    retries: int = MAX_RETRIES,
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one read-only CLI call and return the decoded JSON response.

    `action` keeps the PascalCase OpenAPI name for RPC products, and the
    lower-case hyphenated plug-in form where the product offers one.
    """
    if (product, action) not in ALLOWED_READ_ACTIONS:
        raise CliError(
            "ActionNotAllowlisted",
            product + " " + action + " is outside the read-only allowlist of this skill",
        )

    argv = [ALIYUN_BIN, product, action]
    if profile:
        argv += ["--profile", str(profile)]
    argv += ["--user-agent", build_user_agent(session_id or new_session_id())]
    for key, value in (params or {}).items():
        if value is None:
            continue
        argv += ["--" + str(key), _stringify(value)]

    last_error: Optional[CliError] = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            completed = _run_cli(  # noqa: S603 - fixed argv, no shell
                argv,
                timeout,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                region=(params or {}).get("RegionId"),
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("CliTimeout", "the CLI did not answer in " + str(timeout) + "s", True)
        except OSError as exc:
            raise CliError("CliUnavailable", redact(str(exc)))
        else:
            if completed.returncode != 0:
                code, message = parse_cli_error(completed.stderr, completed.returncode)
                last_error = CliError(code, message, is_transient_error(code, message))
                if not last_error.retryable:
                    raise last_error
            else:
                stdout = (completed.stdout or "").strip()
                if not stdout:
                    return {}
                try:
                    decoded = _json_body(stdout)
                except ValueError as exc:
                    raise CliError("InvalidResponse", redact(str(exc)))
                if isinstance(decoded, list):
                    return {"Items": decoded}
                if isinstance(decoded, dict):
                    return decoded
                raise CliError("InvalidResponse", "the response was not a JSON object")
        if attempt < max(1, retries) and last_error is not None and last_error.retryable:
            time.sleep(RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    if last_error is None:
        raise CliError("Unknown", "the call finished without a result")
    raise last_error


def flatten_instance_ids(instance_ids: Sequence[str]) -> Dict[str, str]:
    """Expand a list into the numbered parameter form used by RPC arrays."""
    return {
        "InstanceId." + str(index): instance_id
        for index, instance_id in enumerate(instance_ids, start=1)
    }


def chunked(items: Sequence[str], size: int) -> List[List[str]]:
    return [list(items[index : index + size]) for index in range(0, len(items), max(1, size))]


def describe_failure_for_customer(error: CliError, region_id: str) -> str:
    """A single sentence a support agent can paste, never a guessed cause."""
    common = (
        "region does not match the instance, the instance does not exist, "
        "or the credentials have no view on it (other account, other resource "
        "group, " + AUTH_FAIL_NO_PERMISSION + ")"
    )
    label = error.canonical_auth_label()
    if label:
        return (
            "Query failed: " + label + " for " + error.code + ". The credentials "
            "in use cannot read this region or these instances. Attach the "
            "read-only actions listed in references/ram-policies.md."
        )
    return (
        "Query failed: " + redact(error.code + " " + error.message)
        + ". Common causes: " + common + ". Region used: " + region_id + "."
    )


# --- customer-facing hygiene (2026-10-27) -----------------------------------
# The dispatcher masks its child stream, but an axis entry script is also run
# directly (evaluations, manual repros), and its own prints carried the raw
# account UID, a Cloud Assistant InvokeId or the 32-hex session id. Installing
# the mask here covers every axis of this package, because every entry imports
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
