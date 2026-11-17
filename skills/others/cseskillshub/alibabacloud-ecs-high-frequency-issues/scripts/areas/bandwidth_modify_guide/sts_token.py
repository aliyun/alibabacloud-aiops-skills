"""Credential pre-flight for the bandwidth guide skill.

Runs `aliyun sts get-caller-identity` in plugin mode to prove that the default
credential chain resolves, and derives the account tag used on the report header.
Nothing here reads, accepts, prints or forwards an access key pair or a session
token: if the chain does not resolve, the fix is `aliyun sts get-caller-identity`.
"""

import sys

from _cli import CliError, dig, plugin_call, redact
from _constants import (
    DEFAULT_TIMEOUT_SECONDS,
    STATUS_FAIL,
    STATUS_OK,
    STS_CALLER_IDENTITY_CMD,
    UID_TAG_PREFIX,
)


# --- customer-facing hygiene (P0-2): never print a raw UID / InvokeId / session id
import re as _re
import sys as _sys


def _mask_pii(text):
    if not isinstance(text, str):
        return text
    text = _re.sub(r"(?<!\d)(1\d{15})(?!\d)", lambda m: "****" + m.group(1)[-4:], text)
    text = _re.sub(r"\bt-([a-z0-9]{6,})\b", lambda m: "t-****" + m.group(1)[-4:], text)
    text = _re.sub(r"\b([0-9a-f]{32})\b", lambda m: "****" + m.group(1)[-4:], text)
    return text


class _MaskedStdout(object):
    def __init__(self, stream):
        self._stream = stream

    def write(self, data):
        return self._stream.write(_mask_pii(data))

    def __getattr__(self, name):
        return getattr(self._stream, name)


_sys.stdout = _MaskedStdout(_sys.stdout)
# stderr is read back by the agent on some transports; mask it too.
_sys.stderr = _MaskedStdout(_sys.stderr)
# --- end hygiene

def get_caller_identity(session_id=None, timeout=None):
    """Return {"account_id", "arn", "caller_uid", "raw"} or raise CliError."""
    payload = plugin_call(STS_CALLER_IDENTITY_CMD,
                          session_id=session_id,
                          timeout=timeout or DEFAULT_TIMEOUT_SECONDS)
    if not isinstance(payload, dict):
        raise CliError("BadResponse", "caller identity response was not an object")
    account_id = dig(payload, "AccountId") or ""
    arn = dig(payload, "Arn") or ""
    caller_uid = dig(payload, "UserId") or account_id
    return {
        "account_id": str(account_id),
        "arn": str(arn),
        "caller_uid": str(caller_uid),
        "raw": payload,
    }


def uid_tag(identity):
    """Traceability tag for the report header, e.g. uid=1234567890123456."""
    return "%s%s" % (UID_TAG_PREFIX, identity.get("account_id") or "unknown")


def preflight(session_id=None, timeout=None):
    """Return (identity, error). Exactly one of the two is None.

    On failure the caller must relay `remediation` verbatim in intent: configure the
    CLI profile. Never ask the user for a key pair.
    """
    try:
        return get_caller_identity(session_id=session_id, timeout=timeout), None
    except CliError as exc:
        return None, {
            "code": exc.code,
            "message": redact(exc.message),
            "permission_denied": exc.permission_denied,
            "remediation": (
                "Resolve the credential chain with `aliyun sts get-caller-identity` (an existing profile or "
                "a RAM role). Do not paste an access key pair or a token into this conversation."
            ),
        }


def main():
    identity, error = preflight()
    if error is not None:
        sys.stdout.write("STATUS: %s\n" % STATUS_FAIL)
        sys.stdout.write("NEXT_ACTION: %s (%s: %s)\n"
                         % (error["remediation"], error["code"], error["message"]))
        return 1
    sys.stdout.write("STATUS: %s\n" % STATUS_OK)
    sys.stdout.write("caller: %s\n" % uid_tag(identity))
    sys.stdout.write("arn: %s\n" % redact(identity["arn"]))
    sys.stdout.write("NEXT_ACTION: run scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py with --region-id\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
