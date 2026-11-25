"""Shared aliyun-CLI layer for the ECS website build guide skill.

Every cloud read this skill performs goes through :func:`run_cli`, which owns
the guarantees the ad-hoc commands would otherwise lack:

* argument-list subprocess invocation only (never a shell) with a bounded
  per-call timeout;
* one 32-hex session id per process run, attached to *every* call through the
  CLI's ``--user-agent`` flag so the whole run correlates as one session;
* bounded backoff for transient service errors only;
* credential masking on all error text before it is surfaced or logged.

Credentials themselves are never touched here: the CLI resolves them from its
own default chain, and this module neither reads, stores, prints nor forwards
any credential value.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid

try:  # normal in-package import, with a path fallback for direct execution
    from . import _constants as C
except ImportError:  # pragma: no cover - executed when run as a plain script
    import _constants as C

# Observability User-Agent template, exported for report headers.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"

# One session id per process run, reused by every call of that run.
SESSION_ID = uuid.uuid4().hex

# Values matching these patterns are masked before any message leaves here.
_MASK_PATTERNS = [
    (re.compile(r"(AccessKeyId=)[^&\s]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(AccessKeySecret=)[^&\s]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(SecurityToken=)[^&\s]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(Signature=)[^&\s]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(SignatureNonce=)[^&\s]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(--password[ =])\S+", re.IGNORECASE), r"\1***"),
]

_ERROR_LINE = re.compile(r"Code:\s*(?P<code>[A-Za-z0-9._\-]+)")


def mask_credentials(text):
    """Redact credential-looking values from arbitrary CLI output."""
    safe = text or ""
    for pattern, replacement in _MASK_PATTERNS:
        safe = pattern.sub(replacement, safe)
    return safe


def build_user_agent(session_id=None, skill_name=None):
    """Return the ``AlibabaCloud-Agent-Skills/<skill>/<session-id>`` label.

    The value is a per-run random hex label, not an account identifier, so it
    is safe to send on every call and to echo into the report.
    """
    return USER_AGENT_TEMPLATE.format(
        skill_name=skill_name or C.SKILL_NAME,
        session_id=session_id or SESSION_ID,
    )

_build_user_agent_raw = build_user_agent



_PACKAGE_NAME = "alibabacloud-ecs-app-deploy-and-site-build"


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


class CliError(RuntimeError):
    """A CLI failure in ``Code: Message`` form, with credentials masked."""

    def __init__(self, code, message, returncode=None, stderr=""):
        self.code = code
        self.message = mask_credentials(message)
        self.returncode = returncode
        self.stderr = mask_credentials(stderr)
        super().__init__("{}: {}".format(self.code, self.message))


def _transient(code):
    return any(code == item or code.startswith(item + ".") for item in C.RETRYABLE_CODES)


def parse_error(stderr_text, returncode):
    """Derive a ``(code, message)`` pair from CLI stderr text."""
    text = mask_credentials((stderr_text or "").strip())
    if not text:
        return ("CliNoOutput", "command exited with code {}".format(returncode))
    match = _ERROR_LINE.search(text)
    code = match.group("code") if match else "CliCallFailed"
    return (code, text)


def run_cli(command, timeout=None, attempts=None, env=None):
    """Run one ``aliyun`` command and return its stdout text.

    ``command`` is an argument list such as ``["ecs", "DescribeInstances",
    "--RegionId", "cn-hangzhou"]``; the ``aliyun`` binary and the observability
    ``--user-agent`` flag are added here so no caller can forget them.

    Raises :class:`CliError` when the call cannot be completed. Never uses a
    shell, and always bounds the call with ``timeout``.
    """
    if timeout is None:
        timeout = C.DEFAULT_TIMEOUT
    if attempts is None:
        attempts = C.MAX_ATTEMPTS

    argv = ["aliyun"] + [str(part) for part in command]
    if "--user-agent" not in argv:
        argv += ["--user-agent", build_user_agent()]

    run_env = dict(os.environ)
    if env:
        run_env.update(env)

    last_error = None
    total = max(1, attempts)
    for attempt in range(1, total + 1):
        retryable = True
        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                env=run_env,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError(
                "CliTimeout",
                "command timed out after {}s (attempt {})".format(timeout, attempt),
            )
        except FileNotFoundError:
            # The CLI binary is absent: retrying cannot help, so stop at once.
            raise CliError(
                "CliNotFound",
                "the 'aliyun' command was not found in PATH; install the "
                "Alibaba Cloud CLI and configure its default credential chain",
                returncode=None,
                stderr="",
            )
        else:
            if completed.returncode == 0:
                return completed.stdout or ""
            code, message = parse_error(completed.stderr, completed.returncode)
            last_error = CliError(
                code, message, returncode=completed.returncode, stderr=completed.stderr
            )
            retryable = _transient(code)

        if not retryable:
            raise last_error
        if attempt < total:
            time.sleep(C.BACKOFF_BASE_SECONDS ** attempt)

    raise last_error if last_error else CliError("CliUnknown", "call did not run")


def call_read_api(product, action, params=None, timeout=None, profile=None):
    """Invoke one read-only RPC action through the CLI and decode its JSON body.

    ``params`` is a mapping of API parameter name to value; ``None`` entries
    are dropped. The caller supplies only parameters it has resolved from the
    conversation, so no value is silently invented here.
    """
    argv = [product, action]
    if profile:
        argv += ["--profile", profile]
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            argv += ["--{}".format(key), json.dumps(value, separators=(",", ":"))]
        else:
            argv += ["--{}".format(key), str(value)]

    raw = run_cli(argv, timeout=timeout)
    return decode_json(raw, action)


def decode_json(raw, label):
    """Parse a CLI JSON body, tolerating an empty payload."""
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except ValueError as exc:
        raise CliError("UnexpectedOutput", "{}: {}".format(label, mask_credentials(str(exc))))


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
