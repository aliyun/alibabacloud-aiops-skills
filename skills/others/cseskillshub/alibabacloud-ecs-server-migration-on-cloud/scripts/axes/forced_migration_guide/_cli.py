"""Shared aliyun-CLI layer for the read-only migration guide skill.

Design rules enforced here:
  * Every call uses subprocess.run([...], timeout=..., stdin=DEVNULL) with an
    argument LIST (never shell=True).
  * Every call carries the per-run observability User-Agent:
        --user-agent AlibabaCloud-Agent-Skills/<skill>/<32-hex-session-id>
    where the session id is uuid.uuid4().hex generated once per process.
  * Only default-chain credentials are used. This module never reads, prints,
    stores, or forwards any access key or secret; all stderr/error text is run
    through mask_credentials() first.
  * Transient errors (throttling / 5xx / timeout) are retried with backoff;
    anything else is raised as CliError("Code: Message").
"""

import json
import re
import subprocess
import sys
import time
import uuid

from _constants import (
    ALLOWED_READ_ACTIONS,
    CLI_BACKOFF_BASE_SECONDS,
    CLI_MAX_RETRIES,
    CLI_TIMEOUT_SECONDS,
    ECS_PRODUCT,
    USER_AGENT_PREFIX,
)

# One stable session id per process run (32 lowercase hex chars).
SESSION_ID = uuid.uuid4().hex


def user_agent():
    """Full User-Agent string for this run."""
    return "{}/{}".format(USER_AGENT_PREFIX, SESSION_ID)

_user_agent_raw = user_agent



_PACKAGE_NAME = "alibabacloud-ecs-server-migration-on-cloud"


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


class CliError(Exception):
    """Raised for non-retryable CLI failures. Formats as 'Code: Message'."""

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super(CliError, self).__init__("{}: {}".format(code, message))


# Fields that must never leak into logs or reports.
_SECRET_PATTERNS = [
    re.compile(r"(AccessKeyId=)\S+", re.IGNORECASE),
    re.compile(r"(AccessKeySecret=)\S+", re.IGNORECASE),
    re.compile(r"(SecurityToken=)\S+", re.IGNORECASE),
    re.compile(r"(Signature=)\S+", re.IGNORECASE),
    re.compile(r'("(?:AccessKeyId|AccessKeySecret|SecurityToken|Signature)"\s*:\s*")[^"]+(")',
               re.IGNORECASE),
]


def mask_credentials(text):
    """Redact credential-looking substrings from arbitrary stderr/stdout text."""
    if not text:
        return text
    masked = text
    for pat in _SECRET_PATTERNS:
        masked = pat.sub(r"\1***", masked) if pat.groups == 1 else pat.sub(r"\1***\2", masked)
    return masked


_TRANSIENT_RE = re.compile(
    r"Throttling|TooManyRequests|ServiceUnavailable|InternalError|"
    r"RequestTimeout|ConnectionTimeout|timed out|500|502|503|504",
    re.IGNORECASE,
)


def _is_transient(code_or_msg):
    return bool(_TRANSIENT_RE.search(code_or_msg or ""))


def _warn(message):
    sys.stderr.write("[WARN] {}\n".format(mask_credentials(message)))
    sys.stderr.flush()


def _run(cmd):
    """Execute one CLI invocation with a hard per-call timeout. No shell."""
    return subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=CLI_TIMEOUT_SECONDS,
        text=True,
    )


def _base_cmd(product, action):
    """Plugin/RPC form keeps the PascalCase action; UA is attached to every call."""
    return [
        "aliyun",
        product,
        action,
        "--user-agent",
        user_agent(),
    ]


def _flatten_params(params):
    args = []
    for key, value in params.items():
        if value is None:
            continue
        args.append("--{}".format(key))
        args.append(str(value))
    return args


def call_readonly(action, params):
    """Invoke an allow-listed ECS read-only action and return parsed JSON.

    Raises CliError on a non-retryable failure and after retries are exhausted.
    """
    if action not in ALLOWED_READ_ACTIONS:
        raise CliError(
            "ReadOnlyWhitelist",
            "action '{}' is not in this read-only skill's whitelist {}".format(
                action, ", ".join(ALLOWED_READ_ACTIONS)),
        )

    cmd = _base_cmd(ECS_PRODUCT, action) + _flatten_params(params)

    last_error = None
    for attempt in range(CLI_MAX_RETRIES):
        try:
            proc = _run(cmd)
        except FileNotFoundError:
            raise CliError("CliNotFound",
                           "the 'aliyun' CLI was not found on PATH; install and configure it "
                           "via the default credential chain (aliyun configure)")
        except OSError as exc:
            raise CliError("CliInvokeError", mask_credentials(str(exc)))
        except subprocess.TimeoutExpired:
            last_error = "RequestTimeout: call exceeded {}s".format(CLI_TIMEOUT_SECONDS)
            _warn("{} (attempt {}/{})".format(last_error, attempt + 1, CLI_MAX_RETRIES))
            time.sleep(CLI_BACKOFF_BASE_SECONDS * (2 ** attempt))
            continue

        if proc.returncode == 0:
            stdout = (proc.stdout or "").strip()
            if not stdout:
                return {}
            try:
                return json.loads(stdout)
            except ValueError:
                raise CliError("ParseError", "response was not valid JSON")

        err_text = mask_credentials((proc.stderr or proc.stdout or "").strip())
        if _is_transient(err_text) and attempt < CLI_MAX_RETRIES - 1:
            last_error = err_text
            _warn("transient error, retrying: {} (attempt {}/{})".format(
                err_text, attempt + 1, CLI_MAX_RETRIES))
            time.sleep(CLI_BACKOFF_BASE_SECONDS * (2 ** attempt))
            continue

        code = _extract_code(err_text)
        raise CliError(code, err_text or "aliyun CLI exited with {}".format(proc.returncode))

    raise CliError("RetryExhausted", last_error or "retries exhausted")


def _extract_code(err_text):
    """Best-effort 'Code' token from a CLI error line, e.g. 'NoPermission: ...'."""
    match = re.match(r"^([A-Za-z0-9_.\-]+):", err_text or "")
    if match:
        return match.group(1)
    if re.search(r"NoPermission|ImplicitDeny|Unauthorized|InvalidAccessKey", err_text or "",
                 re.IGNORECASE):
        return "NoPermission"
    return "CliError"


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
