"""Credential identity check for the ECS Linux permission skill.

Runs ``aliyun sts get-caller-identity`` (plugin mode: lower-case hyphenated
command) to confirm that the default credential chain works and to derive the
account tag used in reports. It never asks for, reads, stores or prints an
AccessKey pair or a security token; when the call fails, the guidance is always
``aliyun sts get-caller-identity`` and nothing else.
"""

import sys

from _cli import CliError, new_session_id, run_cli
from _constants import AUTH_DENIED_CODES, STS_API_VERSION, STS_POP_CODE


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

def get_caller_identity(session_id=None, timeout=20):
    """Return ``{'AccountId', 'Arn', 'UserId', 'identity_tag'}`` or raise CliError."""
    payload = run_cli("GetCallerIdentity", session_id=session_id, timeout=timeout)
    account_id = payload.get("AccountId") or payload.get("accountId") or ""
    arn = payload.get("Arn") or payload.get("arn") or ""
    user_id = payload.get("UserId") or payload.get("userId") or ""
    tag = "account:%s" % account_id if account_id else "account:unknown"
    return {
        "AccountId": account_id,
        "Arn": arn,
        "UserId": user_id,
        "identity_tag": tag,
        "api": "%s:%s" % (STS_POP_CODE, STS_API_VERSION),
    }


def identity_or_warning(session_id=None, writer=None):
    """Never abort the diagnosis on identity: return ``(identity, warning)``."""
    writer = writer or (lambda line: print(line, file=sys.stderr))
    try:
        return get_caller_identity(session_id=session_id), None
    except CliError as exc:
        hint = ("Credentials or RAM authorization could not be verified "
                "(%s). Refresh the default credential chain with `aliyun sts get-caller-identity`; "
                "do not place an AccessKey pair in this conversation, a file or a "
                "command line." % exc)
        if exc.code in AUTH_DENIED_CODES:
            hint = ("The current principal is missing the sts:GetCallerIdentity "
                    "action (%s). Attach the minimal policy from "
                    "references/ram-policies.md and retry." % exc.code)
        writer("[WARN] %s" % hint)
        return None, hint


if __name__ == "__main__":
    session = new_session_id()
    identity, warning = identity_or_warning(session_id=session)
    if identity:
        print("STATUS: OK")
        print("NEXT_ACTION: run `python3 scripts/axes/linux_permission_repair/permission_diagnosis.py preflight` "
              "with the customer's RegionId and InstanceId.")
        print("identity: %s  arn: %s" % (identity["identity_tag"], identity["Arn"]))
    else:
        print("STATUS: FAIL")
        print("NEXT_ACTION: repair the CLI credential chain via `aliyun sts get-caller-identity`, "
              "then retry the identity check.")
        print("detail: %s" % warning)
