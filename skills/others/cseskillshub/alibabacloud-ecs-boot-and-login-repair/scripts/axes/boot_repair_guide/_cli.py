"""Shared Alibaba Cloud CLI transport for the boot-repair guide.

Single responsibility: turn one allowlisted query action plus parameters into a
bounded, observable, credential-safe CLI invocation and a parsed JSON payload.

Design rules enforced here, and why:

* Parameter lists only, never a shell. Every invocation goes through
  ``subprocess.run([...])`` with an explicit ``timeout`` and ``stdin=DEVNULL``, so a
  hung credential prompt or a wedged endpoint cannot stall the agent.
* One action allowlist. :func:`call` refuses anything outside
  ``_constants.ALLOWED_ACTIONS`` before touching the process table, so a change-level
  action cannot be reached even if a caller asks for one.
* A per-run session id on every call as a user agent, so the customer can trace which
  traffic this skill produced.
* Credential masking on all error text, so an access key or token echoed by the tool
  never reaches a report or a transcript.
* Transient failures retry with backoff; anything deterministic fails fast and is
  reported as-is rather than being retried into a different answer.
"""

import json
import re
import subprocess
import time
import uuid

import _constants as C

# Values that must never appear in output. Matched loosely on purpose: the key name
# may arrive URL-encoded, quoted, or space-separated from a CLI error line.
_SECRET_PATTERNS = (
    re.compile(r"(?i)(access[\s_-]*key[\s_-]*id|access[\s_-]*key[\s_-]*secret|"
               r"accesskeyid|accesskeysecret|security[\s_-]*token|signature|password|"
               r"private[\s_-]*key)(\s*[=:]\s*)(\S+)"),
)

_REDACTED = "***"


class CliError(Exception):
    """A failed cloud call, carrying the service code when one was returned."""

    def __init__(self, code, message, action=None, retriable=False):
        super(CliError, self).__init__("{0}: {1}".format(code, message))
        self.code = code
        self.message = message
        self.action = action
        self.retriable = retriable

    @property
    def is_permission_denied(self):
        return self.code in ("NoPermission", "ImplicitDeny") or \
            "NoPermission" in self.message or "ImplicitDeny" in self.message


def new_session_id():
    """Return the 32 hex characters used to tag this script run."""
    return uuid.uuid4().hex


def user_agent(session_id):
    return C.USER_AGENT_TEMPLATE.format_map(
        {"skill": C.SKILL_NAME, "session-id": session_id,
         "skill-version": _SKILL_VERSION})

_user_agent_raw = user_agent



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
def user_agent(*_ua_a, **_ua_k):
    return _ua_normalize(str(_user_agent_raw(*_ua_a, **_ua_k)))


def mask_credentials(text):
    """Replace anything that looks like a credential with a fixed placeholder."""
    if text is None:
        return ""
    masked = str(text)
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(lambda m: m.group(1) + m.group(2) + _REDACTED, masked)
    return masked


def _validate(action):
    if action not in C.ALLOWED_ACTIONS:
        verb = next((v for v in C.CHANGE_VERB_PREFIXES if action.startswith(v)), None)
        if verb:
            raise CliError(
                "BlockedChangeAction",
                "'{0}' starts with the change-level verb '{1}'. This skill performs query "
                "calls only; the operation must be carried out by the customer in the "
                "console after reviewing the stated impact and reversibility.".format(action, verb),
                action=action,
            )
        raise CliError(
            "ActionNotAllowlisted",
            "'{0}' is not in this skill's query allowlist ({1}). Do not call it; report the "
            "gap instead.".format(action, ", ".join(sorted(C.ALLOWED_ACTIONS))),
            action=action,
        )
    return C.ALLOWED_ACTIONS[action]


def _render_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(list(value) if isinstance(value, tuple) else value,
                          ensure_ascii=False, separators=(",", ":"))
    return str(value)


def cli_token(product, action):
    """Return the action token the CLI expects for this product.

    RPC products (``ecs``) take the PascalCase API name; plugin-mode products (``sts``)
    take a lowercase hyphenated token, e.g. ``get-caller-identity``.
    """
    if product == C.PRODUCT_STS:
        return "-" .join(part.lower() for part in re.findall(r"[A-Z][a-z0-9]*", action))
    return action


def build_args(product, action, params, session_id):
    args = [C.ALIYUN_BIN, product, cli_token(product, action)]
    for key in sorted(params or {}):
        value = params[key]
        if value is None:
            continue
        args.extend(["--" + key, _render_value(value)])
    args.extend(["--user-agent", user_agent(session_id)])
    return args


def _classify_failure(stdout, stderr):
    """Pick the service error code out of CLI output, if one is present."""
    blob = "\n".join([stderr or "", stdout or ""])
    match = re.search(r"Code:\s*([A-Za-z0-9._\-]+)", blob)
    if match:
        return match.group(1)
    match = re.search(r"(NoPermission|ImplicitDeny)", blob)
    if match:
        return match.group(1)
    return None


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


def call(action, params=None, timeout=None, retries=None, session_id=None, sleeper=time.sleep):
    """Invoke one allowlisted query action and return the decoded payload.

    Raises :class:`CliError` on any unrecovered failure. An empty payload is returned
    as ``{}`` rather than being synthesised into a result.
    """
    product, _version = _validate(action)
    session_id = session_id or new_session_id()
    timeout = timeout or C.CLI_TIMEOUT_SECONDS
    attempts = (retries if retries is not None else C.CLI_RETRIES) + 1
    args = build_args(product, action, params, session_id)

    last_error = None
    for attempt in range(attempts):
        try:
            proc = _run_cli(  # noqa: S603 - fixed argv, no shell
                args,
                timeout,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError:
            raise CliError(
                "CliNotInstalled",
                "the Alibaba Cloud CLI binary '{0}' was not found; install it and run "
                "'aliyun configure' (default credential chain, never access keys on the "
                "command line)".format(C.ALIYUN_BIN),
                action=action,
            )
        except subprocess.TimeoutExpired:
            last_error = CliError("Timeout", "call exceeded {0}s".format(timeout), action=action,
                                  retriable=True)
        else:
            stdout = proc.stdout.decode("utf-8", "replace")
            stderr = proc.stderr.decode("utf-8", "replace")
            if proc.returncode == 0:
                text = stdout.strip()
                if not text:
                    return {}
                try:
                    payload = _json_body(text)
                except ValueError:
                    raise CliError("UnparsableResponse",
                                   "the CLI returned non-JSON output", action=action)
                if isinstance(payload, dict) and payload.get("Code") and payload.get("Message"):
                    code = str(payload["Code"])
                    raise CliError(code, mask_credentials(payload.get("Message")),
                                   action=action, retriable=code in C.RETRYABLE_CODES)
                return payload
            code = _classify_failure(stdout, stderr) or "CliExit{0}".format(proc.returncode)
            last_error = CliError(code, mask_credentials(stderr.strip() or stdout.strip()),
                                  action=action, retriable=code in C.RETRYABLE_CODES)

        if last_error and last_error.retriable and attempt + 1 < attempts:
            sleeper(C.RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt))
            continue
        break

    raise last_error or CliError("UnknownCliFailure", "the call did not complete", action=action)


def call_soft(action, params=None, session_id=None, warn=lambda message: None, **kwargs):
    """Return ``(payload, error)``, reporting a failure as a warning instead of raising.

    Used where a report is still useful with one data source missing: the caller keeps
    going and the missing part is declared in the evidence gaps.
    """
    try:
        return call(action, params=params, session_id=session_id, **kwargs), None
    except CliError as exc:
        warn("[WARN] {0} failed: {1}".format(action, exc))
        return None, exc


def region_params(region_id, **extra):
    params = {"RegionId": region_id}
    params.update({k: v for k, v in extra.items() if v is not None})
    return params


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
