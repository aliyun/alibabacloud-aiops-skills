"""Shared transport layer for read-only calls made through the local aliyun CLI.

Every call is a parameter-list subprocess run with its own timeout, carries the
skill-level User-Agent, retries only transient failures, and masks credential
material before surfacing any text. Credentials always come from the default
credential chain; this module never accepts, reads or prints key material.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from _constants import (
    ALIYUN_BIN,
    AUTH_FAILURE_CODES,
    BACKOFF_BASE_SECONDS,
    CLI_TIMEOUT_SECONDS,
    HELP_TIMEOUT_SECONDS,
    MAX_ATTEMPTS,
    RETRYABLE_CODES,
    SKILL_NAME,
    UA_TEMPLATE,
)

_SESSION_ID = uuid.uuid4().hex

_REDACT_KEYED = re.compile(
    r"(?i)\b(accesskeyid|accesskeysecret|securitytoken|signature|password|passwd)\b"
    r"(\s*[=:]\s*)(\S+)"
)
_REDACT_BLOB = re.compile(r"(?i)\b(security token|bearer)\b(\s+[A-Za-z0-9./+=_-]{8,})")
_CODE_CANDIDATE = re.compile(r"([A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)*)\s*[:=]\s*(.*)")
_CODE_LABELS = ("code", "errorcode", "errcode", "error")


class CliError(RuntimeError):
    """A CLI or API failure, carrying an error code and a masked message."""

    def __init__(self, code: str, message: str, action: str = "") -> None:
        super().__init__(f"{code}: {message}" if action else code)
        self.code = code
        self.message = message
        self.action = action

    def is_transient(self) -> bool:
        return any(token in self.code for token in RETRYABLE_CODES)

    def is_auth(self) -> bool:
        return any(token in self.code for token in AUTH_FAILURE_CODES)

    def __str__(self) -> str:
        return mask_credentials(f"{self.code}: {self.message}")

    def to_record(self, action: str = "") -> Dict[str, Any]:
        kind = "auth" if self.is_auth() else ("transient" if self.is_transient() else "failed")
        return {"code": self.code, "message": self.message, "kind": kind,
                "action": self.action or action}


def session_id() -> str:
    return _SESSION_ID


def user_agent() -> str:
    return UA_TEMPLATE.format(skill=SKILL_NAME, session_id=_SESSION_ID)

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-account-and-service-process"


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


def mask_credentials(value: Any) -> str:
    """Redact anything that looks like credential material before surfacing text."""
    if value is None:
        return ""
    text = str(value)
    text = _REDACT_KEYED.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)
    text = _REDACT_BLOB.sub(lambda m: f"{m.group(1)} ***", text)
    return text


def build_command(product: str, action: str, params: Optional[Dict[str, Any]] = None) -> List[str]:
    cmd: List[str] = [ALIYUN_BIN, product, action, "--user-agent", user_agent()]
    for key, raw in (params or {}).items():
        if raw is None:
            continue
        if isinstance(raw, bool):
            value = "true" if raw else "false"
        elif isinstance(raw, (list, tuple)):
            value = json.dumps(list(raw), separators=(",", ":"))
        else:
            value = str(raw)
        cmd.extend([f"--{key}", value])
    return cmd


def _warn(action: str, error: CliError) -> None:
    print(f"[WARN] {action}: {error}", file=sys.stderr)


def run_cli(product: str, action: str, params: Optional[Dict[str, Any]] = None,
            timeout: int = CLI_TIMEOUT_SECONDS, quiet: bool = False) -> Dict[str, Any]:
    """Run one read-only action and return the parsed JSON body, or raise CliError."""
    cmd = build_command(product, action, params)
    last_error = CliError("CliUnknown", "call did not complete", action)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            proc = _run_cli(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("CliTimeout", f"{ALIYUN_BIN} call exceeded {timeout}s", action)
        except OSError as exc:
            last_error = CliError("CliTransport", mask_credentials(exc), action)
            break
        else:
            stdout = mask_credentials(proc.stdout.decode("utf-8", "replace")).strip()
            stderr = mask_credentials(proc.stderr.decode("utf-8", "replace")).strip()
            if proc.returncode == 0:
                return _parse_body(stdout, action)
            last_error = _error_from_output(stderr or stdout, action)
            if not last_error.is_transient():
                break

        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_BASE_SECONDS * attempt)

    if not quiet:
        _warn(action, last_error)
    raise last_error


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
    except json.JSONDecodeError:
        offsets = [i for i in (text.find("{"), text.find("[")) if i != -1]
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


def run_help(product: str, action: str, timeout: int = HELP_TIMEOUT_SECONDS) -> Tuple[bool, str]:
    """Offline metadata check: does the installed CLI resolve this action?"""
    cmd = [ALIYUN_BIN, product, action, "--help"]
    try:
        proc = subprocess.run(
            _with_auto_plugin(cmd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "help lookup timed out"
    except OSError as exc:
        return False, mask_credentials(exc)
    output = mask_credentials(
        proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")
    ).strip()
    if proc.returncode == 0 and "not a valid api" not in output.lower():
        return True, output
    return False, output


def failure_record(error: BaseException, action: str) -> Dict[str, Any]:
    """Uniform degraded-record for a failed read-only call."""
    if isinstance(error, CliError):
        return error.to_record(action)
    return {"code": type(error).__name__, "message": mask_credentials(error),
            "kind": "failed", "action": action}


def _parse_body(stdout: str, action: str) -> Dict[str, Any]:
    if not stdout:
        return {}
    try:
        body = _json_body(stdout)
    except json.JSONDecodeError:
        raise CliError("CliParse", f"non-JSON output from {action}", action) from None
    if isinstance(body, dict):
        return body
    return {"Items": body}


def _error_from_output(output: str, action: str) -> CliError:
    code, message = _code_and_message(output)
    return CliError(code, message or f"{action} call failed", action)


def _code_and_message(output: str) -> Tuple[str, str]:
    """Take the real error code, which sits in the value of a Code or ErrorCode line."""
    fallback_code, fallback_message = "", ""
    for line in (raw.strip() for raw in output.splitlines()):
        if not line:
            continue
        body = line[6:].strip() if line.startswith("ERROR:") else line
        match = _CODE_CANDIDATE.match(body)
        if not match:
            continue
        key, value = match.group(1).strip().lower(), match.group(2).strip()
        if key in _CODE_LABELS:
            if value:
                return value.split(" ", 1)[0], value
            continue
        if not fallback_code:
            fallback_code, fallback_message = match.group(1), value
    if fallback_code:
        return fallback_code, fallback_message
    return "CliFailed", output.strip()[:300]


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
