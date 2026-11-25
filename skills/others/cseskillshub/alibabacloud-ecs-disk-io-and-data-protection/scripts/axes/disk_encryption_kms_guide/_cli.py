"""Shared aliyun-CLI layer used by this skill's scripts.

Contract enforced here:

* one 32 hex ``session_id`` per run, carried by **every** call as
  ``--user-agent AlibabaCloud-Agent-Skills/<skill>/<session-id>``;
* list-form arguments, ``shell=False``, ``stdin=subprocess.DEVNULL``;
* an explicit timeout on every subprocess call;
* bounded backoff retries for transient failures only;
* credential material masked out of every error string that leaves this module;
* the caller's default credential chain only - this module never reads, writes or
  accepts an access key pair.
"""

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    ALIYUN_BIN,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS,
    USER_AGENT_TEMPLATE,
)

USER_AGENT_FLAG = "--user-agent"

# Codes worth retrying; anything else is raised to the caller immediately.
TRANSIENT_CODES = (
    "Throttling",
    "ThrottlingUser",
    "Throttling.User",
    "SystemBusy",
    "ServiceUnavailable",
    "InternalError",
    "RequestTimeout",
    "SDK.HttpError",
    "SDK.ServerUnreachable",
    "Timeout",
)

_TRANSIENT_FRAGMENTS = (
    "throttling",
    "system busy",
    "timed out",
    "timeout",
    "connection aborted",
    "connection refused",
    "temporarily unavailable",
    "service unavailable",
    "internal error",
    "bad gateway",
    "gateway timeout",
    "http status: 5",
)

# Authentication wording this skill is allowed to surface to a customer.
AUTH_DENY_CODES = ("NoPermission", "ImplicitDeny")

_MASK_RES = (
    re.compile(
        r"(?i)([^A-Za-z0-9_])"
        r"(access[-_]?key[-_]?(?:id|secret)|secret[-_]?key|security[-_]?token|signature|password|passwd)"
        r"([\"'\s]*[:=][\"'\s]*)"
        r"([^\s,;\"'}\\]+)"
    ),
    re.compile(r"\bLTAI[A-Za-z0-9]{4,}\b"),
)

_CODE_RES = (
    re.compile(r'"Code"\s*:\s*"([^"]+)"'),
    re.compile(r"\bCode:\s*([A-Za-z0-9._-]+)"),
    re.compile(r"\b(NoPermission|ImplicitDeny|InvalidParameter(?:\.[A-Za-z0-9]+)?|"
               r"MissingParameter|Throttling(?:\.\w+)?|InternalError|"
               r"ServiceUnavailable|InvalidRegionId|SignatureDoesNotMatch)\b"),
)


def mask(text):
    """Redact anything that looks like a credential before it reaches a transcript."""
    out = "" if text is None else str(text)
    out = _MASK_RES[0].sub(lambda m: m.group(1) + m.group(2) + m.group(3) + "***", out)
    out = _MASK_RES[1].sub("LTAI***", out)
    return out


def new_session_id():
    """A fresh 32 hex session id, used as the User-Agent trace tag."""
    return uuid.uuid4().hex


def user_agent(session_id):
    """Full User-Agent value for one call."""
    return USER_AGENT_TEMPLATE.format_map(
        {"session-id": session_id, "skill-version": _SKILL_VERSION})

_user_agent_raw = user_agent



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
def user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_raw(*_ua_a, **_ua_k)))


class CliError(Exception):
    """A CLI or API failure carried as ``Code: Message`` with the message masked."""

    def __init__(self, code, message, action=None):
        self.code = str(code)
        self.action = action
        self.message = mask(message)
        super(CliError, self).__init__("{0}: {1}".format(self.code, self.message))


def is_transient(code, text=""):
    """True for throttling, 5xx and transport hiccups - the only retryable class."""
    blob = "{0} {1}".format(code, text).lower()
    if str(code) in TRANSIENT_CODES:
        return True
    for fragment in _TRANSIENT_FRAGMENTS:
        if fragment in blob:
            return True
    return False


def extract_code(text):
    for pattern in _CODE_RES:
        match = pattern.search(text or "")
        if match:
            return match.group(1)
    return None


def _fmt_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def build_argv(product, action, params, session_id):
    """Compose one read-only CLI invocation; arguments stay a list, never a shell string."""
    argv = [ALIYUN_BIN, product, action]
    for key in sorted(params or {}):
        value = (params or {})[key]
        if value is None:
            continue
        argv.append("--{0}".format(key))
        argv.append(_fmt_value(value))
    argv.append(USER_AGENT_FLAG)
    argv.append(user_agent(session_id))
    return argv


def _error_body(body):
    if not isinstance(body, dict):
        return False
    if "Code" not in body:
        return False
    if any(key in body for key in ("Disks", "Snapshots", "Instances", "TotalCount")):
        return False
    return True


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


def _parse_body(action, stdout_text):
    payload = (stdout_text or "").strip()
    if not payload:
        return {}
    try:
        body = _json_body(payload)
    except ValueError:
        raise CliError("BadOutput", "{0} returned non-JSON output: {1}".format(
            action, payload[:400]), action=action)
    if not isinstance(body, dict):
        return {"data": body}
    if _error_body(body):
        raise CliError(body.get("Code"), "{0} {1}".format(
            action, body.get("Message", "")), action=action)
    return body


def _failure(action, proc):
    blob = "\n".join([proc.stderr or "", proc.stdout or ""]).strip()
    code = extract_code(blob) or "CliFailed"
    return CliError(code, blob[:800] or "{0} exited with {1}".format(
        action, proc.returncode), action=action)


def call(product, action, params=None, session_id=None, timeout=DEFAULT_TIMEOUT_SECONDS,
         retries=MAX_RETRIES):
    """Run one CLI read and return the parsed JSON body.

    Raises :class:`CliError` for a hard failure or once the transient retries run out.
    """
    sid = session_id or new_session_id()
    argv = build_argv(product, action, params or {}, sid)
    attempts = max(1, int(retries) + 1)
    error = None
    for attempt in range(attempts):
        try:
            proc = _run_cli(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                shell=False,
                region=(params or {}).get("RegionId"),
            )
        except subprocess.TimeoutExpired:
            error = CliError("Timeout", "{0} did not answer within {1}s".format(
                action, timeout), action=action)
        except FileNotFoundError:
            raise CliError("CliNotFound",
                           "the '{0}' CLI is not on PATH; ask the customer to install it and "
                           "configure a profile with their own credentials".format(ALIYUN_BIN),
                           action=action)
        else:
            error = None
            if proc.returncode == 0:
                return _parse_body(action, proc.stdout)
            error = _failure(action, proc)
        if attempt >= attempts - 1 or not is_transient(error.code, error.message):
            break
        time.sleep(RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)])
    raise error


def warn(message):
    """Surface a degradation without aborting the run."""
    print("[WARN] {0}".format(mask(message)), file=sys.stderr)


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
