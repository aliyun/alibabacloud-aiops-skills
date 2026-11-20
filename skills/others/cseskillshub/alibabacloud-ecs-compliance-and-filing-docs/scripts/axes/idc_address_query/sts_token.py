#!/usr/bin/env python3
"""
sts_token.py -- Credential preflight via the STS read-only identity call.
==========================================================================
SECURITY: This module only calls the read-only "GetCallerIdentity" action.
It never reads, prints or stores any access-key id/secret; identity is
resolved by the aliyun CLI default credential chain. On failure it guides the
operator to run "aliyun configure"; it never asks the customer for keys.

Product/action style (SA-2.11): sts is used in plugin mode with the
lower-hyphen action name "GetCallerIdentity".
"""

import sys

from _cli import CliError, make_session_id, run_cli


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
# --- end hygiene

def get_caller_identity(session_id=None, timeout=None):
    """Return the decoded caller identity document for the active credential.

    Typical fields: AccountId, Arn, UserId, IdentityType, RequestId.
    Raises CliError when credentials are missing or the call fails."""
    sid = session_id or make_session_id()
    return run_cli("sts", "GetCallerIdentity", session_id=sid,
                   timeout=timeout)


def caller_uid(identity):
    """Best-effort account UID label derived from an identity document."""
    if not isinstance(identity, dict):
        return "unknown"
    return str(identity.get("AccountId") or identity.get("UserId") or "unknown")


def main(argv=None):
    """Standalone self-check: verify the default credential chain works."""
    argv = list(sys.argv[1:] if argv is None else argv)
    identity = None
    try:
        identity = get_caller_identity()
    except CliError as exc:
        sys.stderr.write(
            "[WARN] STS get-caller-identity failed: %s: %s\n"
            % (exc.code, exc.message))
        sys.stderr.write(
            "[NEXT_ACTION] Configure credentials by running 'aliyun configure' "
            "so the default credential chain resolves an identity. This tool "
            "never asks for an access key id or secret directly. If the "
            "failure is NoPermission / ImplicitDeny, grant the read-only "
            "actions listed in references/ram-policies.md.\n")
        print("STATUS: FAIL")
        print("NEXT_ACTION: Configure the default credential chain "
              "(aliyun configure) and retry.")
        return 2

    uid = caller_uid(identity)
    print("Credential preflight OK (read-only)")
    print("Account UID: %s" % uid)
    print("Arn        : %s" % identity.get("Arn", "unknown"))
    print("IdentityType: %s" % identity.get("IdentityType", "unknown"))
    print("STATUS: OK")
    print("NEXT_ACTION: None")
    return 0


if __name__ == "__main__":
    sys.exit(main())
