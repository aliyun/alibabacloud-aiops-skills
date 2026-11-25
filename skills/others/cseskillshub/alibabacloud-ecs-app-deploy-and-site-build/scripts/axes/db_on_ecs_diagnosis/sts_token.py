"""Credential preflight: confirm the default credential chain works and derive
the account label used to make each report traceable.

The CLI is called through its plugin form, ``aliyun sts get-caller-identity``.
No credential pair is ever requested, read or passed on the command line; if
this call fails, the remedy is always ``aliyun sts get-caller-identity`` (or the ambient role
the environment already provides), never a literal key.
"""

import json
import sys

from _cli import CliError, call_sts_plugin, new_session_id
from _constants import CLI_TIMEOUT_SECONDS, STS_API_VERSION, STS_PRODUCT

_IDENTITY_KEYS = ("AccountId", "UserId", "Arn", "IdentityType", "PrincipalId")


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

def get_caller_identity(session_id, timeout=CLI_TIMEOUT_SECONDS):
    """Return the decoded identity payload, or raise ``CliError``."""
    return call_sts_plugin(["GetCallerIdentity"], session_id, timeout=timeout)


def pick_identity(payload):
    """Select identity fields defensively.

    Field presence is not asserted: anything absent comes back as ``UNKNOWN``
    rather than being guessed, so a report never claims an account it did not
    actually read.
    """
    body = payload or {}
    if isinstance(body, dict):
        candidates = body.get("data") if isinstance(body.get("data"), dict) else body
    else:
        candidates = {}
    return dict((key, str(candidates.get(key) or "UNKNOWN")) for key in _IDENTITY_KEYS)


def account_label(payload):
    """Short traceable tag for reports: last four digits, rest masked."""
    identity = pick_identity(payload)
    account = identity.get("AccountId", "UNKNOWN")
    if account in ("UNKNOWN", ""):
        return "account:UNKNOWN"
    tail = account[-4:] if len(account) >= 4 else account
    return "account:****{0}".format(tail)


def masked_identity(payload):
    """The subset of the identity that is safe to put in a report.

    The raw identity body carries a full ARN and user id; reports need only to
    be traceable to an account, so the tail-styled label and the identity type
    are what gets echoed.
    """
    identity = pick_identity(payload)
    return {
        "IdentityType": identity.get("IdentityType"),
        "account": account_label(identity).split(":", 1)[1],
    }


def preflight(session_id):
    """Run the preflight and return ``(identity, error)``; never raises.

    A failure here downgrades the whole run instead of aborting it, because the
    offline guidance path is still useful without cloud access.
    """
    try:
        payload = get_caller_identity(session_id)
    except CliError as exc:
        return None, exc
    except Exception as exc:  # pragma: no cover - defensive boundary
        return None, CliError("UnexpectedIdentityFailure", str(exc))
    return pick_identity(payload), None


def main(argv=None):
    session_id = new_session_id()
    identity, error = preflight(session_id)
    result = {
        "product": STS_PRODUCT,
        "apiVersion": STS_API_VERSION,
        "session_id": session_id,
    }
    if error is not None:
        result["STATUS"] = "FAILED"
        result["NEXT_ACTION"] = "RUN_ALIYUN_CONFIGURE"
        result["error"] = "{0}: {1}".format(error.code, error.message)
        result["hint"] = (
            "Verify the default credential chain (or the role provided by the "
            "environment). Do not paste a key pair into this session."
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2

    result["STATUS"] = "OK"
    result["NEXT_ACTION"] = "NONE"
    result["identity"] = masked_identity(identity)
    result["account_label"] = account_label(identity)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
