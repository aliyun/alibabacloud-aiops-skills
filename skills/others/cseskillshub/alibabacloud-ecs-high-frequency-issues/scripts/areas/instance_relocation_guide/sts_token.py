"""Credential probe for the relocation guide.

Resolves the caller identity through the plugin-style command
``aliyun sts get-caller-identity`` so that a report can be attributed to an
account. Authentication itself is left entirely to the default credential chain
of the CLI; this module never handles a key or a token value.
"""

import _cli
from _constants import (
    STS_API_VERSION,
    STS_PRODUCT,
    STS_TIMEOUT_SECONDS,
    USER_AGENT_PREFIX,
)

__all__ = ["get_caller_identity", "caller_tag"]


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

def get_caller_identity(session_id=None, timeout=STS_TIMEOUT_SECONDS):
    """Return ``{'account_id', 'principal_id', 'arn'}`` or ``None``.

    ``None`` means no usable credential; the caller degrades the report instead
    of guessing an account.
    """
    try:
        payload = _cli.run_json(
            STS_PRODUCT,
            "GetCallerIdentity",
            params=None,
            timeout=timeout,
            session_id=session_id,
        )
    except _cli.CliError as exc:
        _cli.warn("caller identity unavailable -> {0}".format(exc))
        return None

    if not isinstance(payload, dict):
        _cli.warn("caller identity payload was not an object")
        return None

    lowered = {str(key).lower(): value for key, value in payload.items()}
    return {
        "account_id": lowered.get("accountid") or lowered.get("uid") or "-",
        "principal_id": lowered.get("userid") or lowered.get("principalid") or "-",
        "arn": lowered.get("arn") or "-",
    }


def caller_tag(caller, session_id=None):
    """Build the traceability label printed with a report."""
    account = (caller or {}).get("account_id", "-")
    agent = _cli.user_agent(session_id)
    return "{0} account={1}".format(agent.replace(USER_AGENT_PREFIX + "/", ""),
                                    account)


if __name__ == "__main__":
    sid = _cli.new_session_id()
    identity = get_caller_identity(sid)
    print(_cli.user_agent(sid))
    if identity is None:
        print("STATUS: FAIL")
        print("NEXT_ACTION: run 'aliyun sts get-caller-identity' with the default credential "
              "chain, then repeat the identity check.")
    else:
        print("STATUS: OK")
        print(caller_tag(identity, sid))
