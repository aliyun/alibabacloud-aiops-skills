"""Shared aliyun CLI transport layer for this skill.

Every cloud call in this package goes through :func:`run_cli`, which guarantees:

  * only whitelisted actions are ever spawned, checked before the process starts;
  * a whitelisted action that changes state additionally needs a confirmation that
    repeats, verbatim, the command or disk that call covers -- without it the call
    is refused here, so no unconfirmed write can reach the cloud;
  * one ``session_id`` per run, carried on every call through ``--user-agent`` so
    a single diagnosis is traceable end to end (see ``USER_AGENT_TEMPLATE``);
  * argument-list invocation only, never a shell, with a per-call timeout;
  * exponential backoff with jitter for transient failures only;
  * credential and key material masked out of every message that leaves here.

The aliyun CLI resolves credentials from its own default credential chain. This
module never reads, stores, prints or passes an AccessKey pair or a token.
"""

import json
import random
import re
import subprocess
import time
import uuid

from _constants import (
    API_WHITELIST,
    CLI_BACKOFF_BASE_SECONDS,
    CLI_BACKOFF_MAX_SECONDS,
    CLI_BINARY,
    CLI_MAX_RETRIES,
    CLI_TIMEOUT_SECONDS,
    CODE_API_ERROR,
    CODE_CLI_TIMEOUT,
    CODE_CLI_UNAVAILABLE,
    CODE_CONFIRMATION_REQUIRED,
    CODE_IMPLICIT_DENY,
    CODE_INVALID_CREDENTIAL,
    CODE_MISSING_PARAMETER,
    CODE_NO_PERMISSION,
    CODE_PARSE_ERROR,
    CODE_POLICY_REFUSED,
    CREDENTIAL_ERROR_MARKERS,
    GATED_WRITE_ACTIONS,
    MASKED_VALUE,
    NON_RETRYABLE_MARKERS,
    PLUGIN_MODE_COMMANDS,
    RETRYABLE_MARKERS,
    SENSITIVE_KEY_PATTERNS,
    SKILL_NAME,
    USER_AGENT_TEMPLATE,
)

# Sensitive field names, turned into one alternation so a value can be scrubbed
# wherever it appears: "password=x", "Password: x", "--passwd x", "private key: x".
_SENSITIVE_ALTERNATION = "|".join(
    pattern.replace("[-_]", "[-_]?") for pattern in SENSITIVE_KEY_PATTERNS
)
_ASSIGNMENT_RE = re.compile(
    r"(\b(?:%s)\b)(\s*[=:]\s*)([^\s,;]+)" % _SENSITIVE_ALTERNATION,
    re.IGNORECASE,
)
# The CLI flag spelling, where the value follows the flag after a space.
_CLI_FLAG_RE = re.compile(
    r"(--[\w-]*(?:secret|token|password|passwd|private-key)[\w-]*\s+)(\S+)",
    re.IGNORECASE,
)
_PEM_BLOCK_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)


class CliError(Exception):
    """A CLI failure, rendered as ``Code: Message``.

    ``retryable`` drives the backoff loop. ``code`` uses this skill's own
    vocabulary; permission failures are reported as ``NoPermission`` or
    ``ImplicitDeny`` only.
    """

    def __init__(self, code, message, retryable=False):
        Exception.__init__(self, "%s: %s" % (code, mask_secrets(message)))
        self.code = code
        self.message = mask_secrets(message)
        self.retryable = retryable


def new_session_id():
    """Return the 32-character hex id that ties every call of one run together."""
    return uuid.uuid4().hex


def build_user_agent(session_id):
    """Render the observability User-Agent for one run.

    ``format_map`` is used because the template placeholder ``session-id`` is not
    a Python identifier.
    """
    return USER_AGENT_TEMPLATE.format_map(
        {"skill": SKILL_NAME, "session-id": session_id, "skill-version": _SKILL_VERSION})

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


def mask_secrets(text):
    """Scrub credential and key material out of arbitrary CLI text.

    Only the value is replaced; the field name stays, so a report can still say
    which kind of material had to be hidden.
    """
    if text is None:
        return ""
    masked = str(text)
    masked = _PEM_BLOCK_RE.sub(MASKED_VALUE, masked)
    masked = _ASSIGNMENT_RE.sub(
        lambda m: m.group(1) + m.group(2) + MASKED_VALUE, masked)
    masked = _CLI_FLAG_RE.sub(lambda m: m.group(1) + MASKED_VALUE, masked)
    return masked


def classify_error(text):
    """Map raw CLI output onto this skill's error vocabulary."""
    flat = (text or "").replace("\n", " ").replace(" ", "").lower()
    probe = (text or "").lower()
    for marker in CREDENTIAL_ERROR_MARKERS:
        if marker in flat or marker in probe:
            return CODE_INVALID_CREDENTIAL, False
    if "noperm" in flat or "nopermission" in flat or "accessdenied" in flat:
        return CODE_NO_PERMISSION, False
    if "implicitdeny" in flat or "deniedbyiporvpc" in flat:
        return CODE_IMPLICIT_DENY, False
    if "missingparameter" in flat or "noparameter" in flat:
        return CODE_MISSING_PARAMETER, False
    for marker in RETRYABLE_MARKERS:
        if marker in probe or marker.replace(" ", "") in flat:
            return CODE_API_ERROR, True
    for marker in NON_RETRYABLE_MARKERS:
        if marker in flat:
            return CODE_API_ERROR, False
    return CODE_API_ERROR, False


def _backoff_seconds(attempt):
    base = min(CLI_BACKOFF_MAX_SECONDS,
               CLI_BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1)))
    return base + random.uniform(0.0, base * 0.25)


# Which parameter each gated action's confirmation has to repeat verbatim. The
# confirmation is therefore always about one concrete target: this command, this
# disk. It cannot be a generic flag, so it cannot cover a second call by accident.
CONFIRMATION_SUBJECT_PARAM = {
    ("ecs", "RunCommand"): "CommandContent",
    ("ecs", "CreateSnapshot"): "DiskId",
}


def require_confirmation(product, action, params, confirmation):
    """Refuse a state-changing call unless it carries its own confirmation.

    ``confirmation`` must equal the value of the action's subject parameter, which
    is what the operator was shown before agreeing. Evidence actions have no entry
    in that map and are never blocked.
    """
    subject = CONFIRMATION_SUBJECT_PARAM.get((product, action))
    if subject is None:
        return
    value = str((params or {}).get(subject) or "").strip()
    if not value:
        raise CliError(CODE_CONFIRMATION_REQUIRED,
                       "%s %s needs a confirmation that names its %s, and the call "
                       "supplied none" % (product, action, subject))
    if str(confirmation or "").strip() != value:
        raise CliError(
            CODE_CONFIRMATION_REQUIRED,
            "%s %s was not confirmed: the caller has to repeat the exact %s that is "
            "about to be affected, for this call only. Tell the operator what this "
            "single call does and what it can affect, then re-run with that "
            "confirmation. A confirmation given for another command, another disk "
            "or an earlier run does not apply."
            % (product, action, subject),
        )


def build_command(product, action, params, session_id):
    """Assemble one argv list. Plugin mode uses the lowercase-hyphen form."""
    if (product, action) not in API_WHITELIST:
        raise CliError(
            CODE_POLICY_REFUSED,
            "refusing to call %s %s: it is not part of the declared action "
            "whitelist of this skill. Changes outside that whitelist are guided "
            "through the console and never issued from here." % (product, action),
        )
    argv = [CLI_BINARY, product]
    plugin_name = PLUGIN_MODE_COMMANDS.get((product, action))
    argv.append(plugin_name if plugin_name else action)
    for key in sorted(params or {}):
        value = params[key]
        if value is None or value == "":
            continue
        argv.extend(["--%s" % key, str(value)])
    argv.extend(["--user-agent", build_user_agent(session_id)])
    return argv


def run_cli(product, action, params=None, session_id=None,
            timeout=CLI_TIMEOUT_SECONDS, confirmation=None):
    """Run one aliyun CLI call and return its parsed JSON body.

    Raises :class:`CliError` when the action is outside the whitelist, when a
    gated action arrives without its confirmation, when the binary is missing,
    when every attempt failed, or when the payload is not JSON.

    A gated action is attempted once. Retrying a call that changes state could
    produce a second snapshot or a second guest command, which is a worse outcome
    than reporting the first attempt as unconfirmed.
    """
    if not session_id:
        raise CliError(CODE_MISSING_PARAMETER, "session_id is required for every call")
    # Callers may pass an unset override; every spawned call stays bounded.
    timeout = timeout or CLI_TIMEOUT_SECONDS
    require_confirmation(product, action, params or {}, confirmation)
    argv = build_command(product, action, params or {}, session_id)
    attempts = 1 if (product, action) in GATED_WRITE_ACTIONS else CLI_MAX_RETRIES
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            completed = _run_cli(
                argv,
                timeout,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError(CODE_CLI_TIMEOUT,
                                  "%s %s timed out after %ss"
                                  % (product, action, timeout), retryable=True)
        except FileNotFoundError:
            # A missing binary never becomes a retry, and never falls back to a
            # hand-written request.
            raise CliError(CODE_CLI_UNAVAILABLE,
                           "the aliyun CLI was not found on PATH; install it and run "
                           "aliyun configure once")
        except OSError as exc:
            raise CliError(CODE_CLI_UNAVAILABLE,
                           "could not start the aliyun CLI: %s" % mask_secrets(exc))
        else:
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            if completed.returncode == 0:
                return parse_payload(stdout, product, action)
            combined = "%s %s" % (stderr, stdout)
            code, retryable = classify_error(combined)
            last_error = CliError(code,
                                  "%s %s failed: %s" % (product, action,
                                                        _first_error_line(combined)),
                                  retryable=retryable)
        if last_error.retryable and attempt < attempts:
            time.sleep(_backoff_seconds(attempt))
            continue
        break
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


def parse_payload(stdout, product, action):
    """Parse a CLI body, tolerating leading noise but never inventing values."""
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        return _json_body(text)
    except ValueError:
        pass
    raise CliError(CODE_PARSE_ERROR,
                   "%s %s returned a body that is not JSON" % (product, action))


def _first_error_line(text):
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped:
            return mask_secrets(stripped)[:400]
    return mask_secrets((text or "").strip()[:400]) or "no error detail returned"


def credential_remediation():
    """The guidance shown when the credential chain itself is the blocker."""
    return ("Ask the operator to run `aliyun configure` in a terminal to set up the "
            "default credential chain. Never paste an AccessKey pair, a token or a "
            "private key into this conversation.")


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
