"""Shared Alibaba Cloud CLI layer used by the triage entry point.

Every cloud call goes through call_aliyun(): argument lists only (never a shell), a
per-call timeout, bounded retry on transient errors, one per-run User-Agent attached to
each attempt for traceability, and credential masking on any text this module emits.
The read-only boundary is enforced here as well as in the documentation: actions outside
ALLOWED_ACTIONS are refused before a process is spawned.
"""

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    ALIYUN_BIN,
    ALLOWED_ACTIONS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES,
    PERMISSION_ERROR_CODES,
    RETRY_BACKOFF_SECONDS,
    SKILL_NAME,
    TRANSIENT_ERROR_CODES,
    UA_TEMPLATE,
)

_ERROR_CODE_RE = re.compile(r"(?im)^\s*(?:error)?code\s*:\s*([A-Za-z0-9._\-]+)")
_ERROR_MESSAGE_RE = re.compile(r"(?im)^\s*message\s*:\s*(.+?)\s*$")
_JSON_CODE_RE = re.compile(r"(?i)\"(?:code|errorcode|errcode)\"\s*:\s*\"([^\"]+)\"")
_INVALID_API_RE = re.compile(r"(?i)'?([A-Za-z0-9_.\-]+)'? is not a valid api")
_CREDENTIAL_RE = (
    re.compile(
        r"(?i)(access[_\-]?key[_\-]?(?:id|secret)?|security[_\-]?token|signature|password)"
        r"([\"'\s:=]+)([^\s,;&\"']+)"
    ),
    re.compile(r"\bLTAI[A-Za-z0-9]{4,}\b"),
)


class CliError(Exception):
    """A CLI failure, rendered as 'Code: Message' with credentials masked."""

    def __init__(self, code, message):
        self.code = str(code)
        self.message = mask_secrets(message)
        Exception.__init__(self, "%s: %s" % (self.code, self.message))

    @property
    def is_permission_error(self):
        return any(self.code == code or self.code.startswith(code + ".")
                   for code in PERMISSION_ERROR_CODES)


def new_session_id():
    """Return a fresh 32-hex id used as the observability label for one triage run."""
    return uuid.uuid4().hex


def user_agent(session_id):
    return UA_TEMPLATE.format(skill_name=SKILL_NAME, session_id=session_id or new_session_id())

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


def mask_secrets(text):
    """Redact anything credential-shaped before text reaches a log, report or error."""
    if text is None:
        return ""
    out = text if isinstance(text, str) else str(text)
    out = _CREDENTIAL_RE[0].sub(lambda m: "%s%s***" % (m.group(1), m.group(2)), out)
    out = _CREDENTIAL_RE[1].sub("LTAI***", out)
    return out


def warn(message):
    sys.stderr.write("[WARN] %s\n" % mask_secrets(message))


def _log_line(cmd):
    # The command is logged with the User-Agent visible: it carries the session label,
    # and no credential is ever part of the argument list.
    return " ".join(cmd[:4])


def _extract_error(stderr, stdout, returncode):
    blob = "%s\n%s" % (stderr or "", stdout or "")
    invalid_api = _INVALID_API_RE.search(blob)
    if invalid_api:
        return "InvalidApi", "%s is not available in the installed CLI for this product" % (
            invalid_api.group(1),)
    code_match = _ERROR_CODE_RE.search(blob) or _JSON_CODE_RE.search(blob)
    message_match = _ERROR_MESSAGE_RE.search(blob)
    code = code_match.group(1) if code_match else "CliExit%s" % returncode
    if message_match:
        message = message_match.group(1)
    else:
        tail = "\n".join([line for line in blob.splitlines() if line.strip()][-4:])
        message = tail or "the CLI returned no error detail"
    return code, message


def _parse_body(stdout, product, action):
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except ValueError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start < 0 or end <= start:
            continue
        for candidate in (text[start:end + 1], text[start:]):
            try:
                return json.loads(candidate)
            except ValueError:
                continue
    raise CliError("UnparseableResponse",
                   "%s %s returned a body that is not JSON" % (product, action))


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


def call_aliyun(product, action, params=None, session_id=None,
                timeout=DEFAULT_TIMEOUT_SECONDS, retries=MAX_RETRIES):
    """Run one allowlisted read-only action and return its parsed response body.

    Raises CliError on a refused action, a missing CLI, or an API error that survives
    the bounded retry.
    """
    if (product, action) not in ALLOWED_ACTIONS:
        allowed = ", ".join("%s:%s" % item for item in ALLOWED_ACTIONS)
        raise CliError("ReadOnlyPolicyViolation",
                       "refused %s:%s; this skill only calls %s" % (product, action, allowed))

    cmd = [ALIYUN_BIN, product, action]
    for key in sorted(params or {}):
        value = params[key]
        if value is None:
            continue
        cmd.extend(["--%s" % key, str(value)])
    cmd.extend(["--user-agent", user_agent(session_id)])

    attempts = max(1, int(retries))
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            proc = _run_cli(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("CliTimeout",
                                  "%s %s did not answer within %s seconds"
                                  % (product, action, timeout))
        except FileNotFoundError:
            raise CliError("CliNotFound",
                           "the '%s' command was not found; install the Alibaba Cloud CLI "
                           "and configure it with the default credential chain" % ALIYUN_BIN)
        except OSError as exc:
            raise CliError("CliExecFailed", exc)
        else:
            if proc.returncode == 0:
                return _parse_body(proc.stdout, product, action)
            code, message = _extract_error(proc.stderr, proc.stdout, proc.returncode)
            last_error = CliError(code, message)
            if code not in TRANSIENT_ERROR_CODES and not code.startswith("Throttling"):
                raise last_error

        if attempt < attempts:
            warn("%s: transient failure (%s), starting retry %s of %s"
                 % (_log_line(cmd), last_error, attempt, attempts - 1))
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise last_error


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
