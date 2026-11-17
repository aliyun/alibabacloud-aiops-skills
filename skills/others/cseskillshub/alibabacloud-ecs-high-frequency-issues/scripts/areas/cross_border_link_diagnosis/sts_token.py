"""Credential-chain probe: confirm which account the read-only queries will run
against.

Uses the CLI's plugin-style lowercase form (`aliyun sts get-caller-identity`) and
the machine's existing default credential chain. It never asks for, reads, accepts,
or prints an AccessKey ID, AccessKey secret, or session token.
"""

import sys

if __package__ in (None, ""):
    import os

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import CliError, mask_secrets, run_cli  # noqa: E402
from _constants import STS_TIMEOUT_SECONDS  # noqa: E402


CALLER_FIELDS = ("AccountId", "Arn", "UserId", "IdentityType", "PrincipalId")


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

def get_caller_identity():
    """Return (identity_dict, None) or (None, CliError)."""
    try:
        payload = run_cli("sts", "GetCallerIdentity", timeout=STS_TIMEOUT_SECONDS)
    except CliError as error:
        return None, error
    if not isinstance(payload, dict):
        return None, CliError(
            "UnexpectedIdentityResponse",
            mask_secrets(payload),
            product="sts",
            action="GetCallerIdentity",
        )
    return {key: payload[key] for key in CALLER_FIELDS if payload.get(key)}, None


def trace_tag(identity):
    """Short, non-secret label used to attribute a report to one account."""
    if not identity:
        return "account:unresolved"
    account = identity.get("AccountId")
    return "account:%s" % account if account else "account:unresolved"


def guidance_for(error):
    """What to tell a human when identity cannot be resolved."""
    if error is None:
        return ""
    if error.is_auth:
        return (
            "Identity check was refused (%s). Ask the customer to run "
            "`aliyun sts get-caller-identity` locally, then attach the read-only actions listed "
            "in references/ram-policies.md. Do not request credentials in the "
            "conversation." % error.code
        )
    return (
        "Identity check failed (%s). Continue with console-side evidence and mark "
        "this item as a gap in the report." % error.code
    )


if __name__ == "__main__":
    identity, call_error = get_caller_identity()
    if call_error is not None:
        print("STATUS: DEGRADED")
        print(guidance_for(call_error))
        sys.exit(1)
    print("STATUS: OK")
    print(trace_tag(identity))
    for field, value in sorted(identity.items()):
        print("%s: %s" % (field, mask_secrets(value)))
