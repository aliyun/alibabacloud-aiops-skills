"""Shared transport layer for the `aliyun` CLI.

Every cloud call in this skill goes through run() so that it inherits the same
observability user agent, per-call timeout, bounded retry, credential masking and
error shape. Nothing here shells out through a command interpreter.
"""

import json
import random
import re
import subprocess
import sys
import time
import uuid

import _constants as C

_RETRYABLE_CODES = (
    "Throttling",
    "Throttling.User",
    "Throttling.Api",
    "InternalError",
    "ServiceUnavailable",
    "RequestTimeout",
    "SDK.ServerUnreachable",
    "SystemBusy",
)

_RETRYABLE_MESSAGE_FRAGMENTS = (
    "500", "502", "503", "504", "timed out", "timeout", "connection reset",
    "temporarily unavailable",
)

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(accesskeyid|access_key_id|access-key-id|accesskeysecret|access_key_secret|"
    r"access-key-secret|securitytoken|security_token|security-token|signature)\b"
    r"(\s*[=:]\s*)([^\s&,';]+)"
)
_SECRET_HEADER = re.compile(
    r"(?i)(x-acs-signature|x-acs-security-token)(\s*:\s*)([^\s,;]+)"
)
_POP_ERROR = re.compile(r"ERROR:\s*([A-Za-z0-9_.\-]+)\s*[::]\s*([^\n]*)")
_CODE_FIELD = re.compile(r'"Code"\s*:\s*"([A-Za-z0-9_.\-]+)"')
_MESSAGE_FIELD = re.compile(r'"Message"\s*:\s*"([^"]*)"')


class CliError(RuntimeError):
    """A failed cloud call, shaped as `Code: Message`."""

    def __init__(self, code, message, action=None):
        self.code = code
        self.action = action
        RuntimeError.__init__(self, "{0}: {1}".format(code, message))


def new_session_id():
    """Return a fresh 32 character hex identifier for one skill invocation."""
    return uuid.uuid4().hex


def build_user_agent(session_id, skill_name=None):
    return C.API_USER_AGENT_TEMPLATE.format_map(
        {"skill": skill_name or C.SKILL_NAME,
         "session-id": session_id,
         "skill-version": _SKILL_VERSION}
    )

_build_user_agent_raw = build_user_agent



_PACKAGE_NAME = "alibabacloud-ecs-disk-io-and-data-protection"


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


def mask_secrets(text):
    """Redact anything that looks like a credential before it reaches a log or report."""
    if text is None:
        return ""
    text = str(text)
    text = _SECRET_ASSIGNMENT.sub(lambda m: m.group(1) + m.group(2) + "***", text)
    text = _SECRET_HEADER.sub(lambda m: m.group(1) + m.group(2) + "***", text)
    return text


def warn(message):
    sys.stderr.write("[WARN] {0}\n".format(mask_secrets(message)))


def _is_retryable(error_code, error_message):
    if error_code in _RETRYABLE_CODES:
        return True
    haystack = "{0} {1}".format(error_code or "", error_message or "").lower()
    for fragment in _RETRYABLE_MESSAGE_FRAGMENTS:
        if fragment in haystack:
            return True
    return False


def _parse_error(stdout_text, stderr_text, returncode):
    for blob in (stderr_text, stdout_text):
        if not blob:
            continue
        match = _POP_ERROR.search(blob)
        if match:
            return match.group(1), mask_secrets(match.group(2))
        match = _CODE_FIELD.search(blob)
        if match:
            detail = _MESSAGE_FIELD.search(blob)
            message = detail.group(1) if detail else blob.strip()[:400]
            return match.group(1), mask_secrets(message)
    fallback = (stderr_text or stdout_text or "").strip()[:400]
    return "CliExit{0}".format(returncode), mask_secrets(fallback)


def _flatten(params):
    args = []
    for key in sorted(params or {}):
        value = params[key]
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        if isinstance(value, (list, tuple)):
            for index, item in enumerate(value, start=1):
                args.append("--{0}.{1}".format(key, index))
                args.append(str(item))
            continue
        args.append("--{0}".format(key))
        args.append(str(value))
    return args


def _hyphenate(action):
    """`GetCallerIdentity` -> `get-caller-identity`, the plugin-mode spelling."""
    parts = re.findall(r"[A-Z][a-z0-9]*", action or "")
    if not parts:
        return (action or "").lower()
    return "-".join(part.lower() for part in parts)


def build_command(action, product=None, params=None, session_id=None, hyphenated=False):
    """Assemble an argv list; RPC products keep the PascalCase action name."""
    argv = ["aliyun", product or C.ECS_PRODUCT]
    argv.append(_hyphenate(action) if hyphenated else action)
    argv.append("--user-agent")
    argv.append(build_user_agent(session_id or new_session_id()))
    argv.extend(_flatten(params))
    return argv


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


def _decode(completed, action):
    stdout_text = mask_secrets(completed.stdout or "")
    stderr_text = mask_secrets(completed.stderr or "")
    if stderr_text.strip():
        warn("{0} wrote to stderr: {1}".format(action, stderr_text.strip()[:400]))
    if not stdout_text.strip():
        return {}
    try:
        return _json_body(stdout_text)
    except ValueError:
        raise CliError("InvalidResponse",
                       "response was not valid JSON: {0}".format(stdout_text.strip()[:400]),
                       action)


def run(action, product=None, params=None, session_id=None, timeout=C.DEFAULT_TIMEOUT,
        max_attempts=C.MAX_ATTEMPTS, hyphenated=False, logger=None):
    """Call one OpenAPI action and return its decoded JSON body.

    Transient failures are retried with jittered exponential backoff; anything else
    raises CliError immediately so the caller can decide whether to degrade.
    """
    log = logger or warn
    attempts = max(1, max_attempts)
    argv = build_command(action, product=product, params=params,
                         session_id=session_id or new_session_id(), hyphenated=hyphenated)
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            completed = _run_cli(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                region=(params or {}).get("RegionId"),
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("ClientTimeout",
                                  "the CLI did not answer within {0}s".format(timeout), action)
            log("{0} attempt {1} of {2} timed out".format(action, attempt, attempts))
        except FileNotFoundError:
            raise CliError("CliNotFound", "the aliyun CLI is not installed or not on PATH", action)
        except OSError as exc:
            raise CliError("CliLaunchFailed", mask_secrets(exc), action)

        if completed.returncode == 0:
            return _decode(completed, action)

        error_code, error_message = _parse_error(
            mask_secrets(completed.stdout), mask_secrets(completed.stderr), completed.returncode)
        last_error = CliError(error_code, error_message, action)
        if not _is_retryable(error_code, error_message) or attempt >= attempts:
            raise last_error
        delay = min(C.RETRY_MAX_SECONDS, C.RETRY_BASE_SECONDS * (2 ** (attempt - 1)))
        delay = delay * (1.0 + random.random() * 0.25)
        log("{0} failed with {1}, retrying in {2:.1f}s".format(action, error_code, delay))
        time.sleep(delay)

    raise last_error or CliError("Unknown", "{0} failed without a reported error".format(action), action)


def run_optional(action, product=None, params=None, session_id=None, timeout=C.DEFAULT_TIMEOUT,
                 hyphenated=False, logger=None):
    """Call one action, downgrade any failure to a warning and return (data, error)."""
    try:
        data = run(action, product=product, params=params, session_id=session_id,
                   timeout=timeout, hyphenated=hyphenated, logger=logger)
        return data, None
    except CliError as exc:
        (logger or warn)(str(exc))
        return None, exc


def dig(payload, *keys):
    """Defensive nested lookup that tolerates PascalCase and camelCase spellings."""
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        if key in current:
            current = current[key]
            continue
        lowered = key[:1].lower() + key[1:]
        uppered = key[:1].upper() + key[1:]
        if lowered in current:
            current = current[lowered]
        elif uppered in current:
            current = current[uppered]
        else:
            return None
    return current


def as_list(payload, *keys):
    """Return a list for a wrapper such as {"Disk": [...]} or a bare list."""
    value = dig(payload, *keys) if keys else payload
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        inner = list(value.values())
        if len(inner) == 1 and isinstance(inner[0], list):
            return inner[0]
        return [value]
    return []


def collect_keys(payload, needles, path=""):
    """Find response fields whose name contains any needle.

    Used where a response field name has not been confirmed for this package: the
    value is reported together with its actual key path instead of being assumed.
    """
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = "{0}.{1}".format(path, key) if path else str(key)
            if isinstance(value, (dict, list)):
                found.extend(collect_keys(value, needles, child))
            else:
                for needle in needles:
                    if needle.lower() in str(key).lower():
                        found.append((child, value))
                        break
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            found.extend(collect_keys(item, needles, "{0}[{1}]".format(path, index)))
    return found


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
