#!/usr/bin/env python3
"""Caller identity check for the public IP / EIP guide.

Runs the account-identity query through the CLI's default credential chain and
derives a short traceability tag for the report. Run it directly to answer the
question "which account am I about to describe?":

    python3 scripts/areas/public_ip_guide/sts_token.py

On failure it points at ``aliyun sts get-caller-identity``. It never reads, prints, stores, or
requests a key pair.
"""

from __future__ import annotations

import json
import sys

from _cli import CliError, call, new_session_id
from _constants import ACTION_GET_CALLER_IDENTITY, PRODUCT_STS


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

def get_caller_identity(session_id=None):
    """Return the caller identity as a dict with ``account_id``, ``arn`` and ``tag``.

    Raises :class:`CliError` when the query itself fails.
    """
    body = call(
        PRODUCT_STS,
        ACTION_GET_CALLER_IDENTITY,
        {},
        session_id=session_id or new_session_id(),
    )
    account_id = str(body.get("AccountId") or body.get("accountId") or "")
    arn = str(body.get("Arn") or body.get("arn") or "")
    return {
        "account_id": account_id,
        "arn": arn,
        "identity_type": str(body.get("IdentityType") or ""),
        "principal_id": str(body.get("PrincipalId") or ""),
        "tag": account_tag(account_id),
    }


def account_tag(account_id):
    """Short label for the report: only the tail of the account id is repeated."""
    if not account_id:
        return "account unknown"
    tail = account_id[-4:] if len(account_id) >= 4 else account_id
    return "account ****{0}".format(tail)


def guidance_for(error):
    """Customer-safe next step for a failed identity check."""
    if isinstance(error, CliError) and (error.is_credential or error.is_permission):
        return (
            "credential problem ({0}): sign in to the CLI with the default credential chain "
            "by running 'aliyun sts get-caller-identity'; check that the profile is allowed "
            "sts:GetCallerIdentity. Do not paste a key pair into this session.".format(error.code)
        )
    if isinstance(error, CliError) and error.code == "CliUnavailable":
        return "install the Alibaba Cloud CLI, then run 'aliyun sts get-caller-identity'."
    return "the identity query failed: {0}".format(error)


def main(argv=None):
    session_id = new_session_id()
    try:
        identity = get_caller_identity(session_id)
    except CliError as error:
        print("STATUS: FAIL")
        print("NEXT_ACTION: " + guidance_for(error))
        print(json.dumps({"error": error.as_dict(), "session_id": session_id}, indent=2))
        return 1
    print(json.dumps(identity, indent=2, sort_keys=True))
    print("STATUS: OK")
    print("NEXT_ACTION: continue with scripts/areas/public_ip_guide/public_ip_guide.py using this account context.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
