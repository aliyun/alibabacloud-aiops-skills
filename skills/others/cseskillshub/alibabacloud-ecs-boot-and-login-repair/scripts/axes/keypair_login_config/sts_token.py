#!/usr/bin/env python3
"""Caller identity for the ECS key pair and logon credential skill.

Answers one question before any instance is queried: *whose account is this, and
in which region does the CLI resolve it*. Mismatched accounts are a real and
repeated cause of "the instance does not exist" and "there is nothing to renew"
reports, and no amount of guest-side work will explain that away.

Usage::

    python3 scripts/sts_token.py
    python3 scripts/sts_token.py --json

Credentials are resolved by the aliyun CLI default credential chain. This script
never asks for, reads, stores or prints an AccessKey pair or a token. When the
identity call fails it prints the remediation instead of a workaround.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import (  # noqa: E402
    CliError,
    credential_remediation,
    mask_secrets,
    new_session_id,
    run_cli,
)
from _constants import (  # noqa: E402
    ACTION_GET_CALLER_IDENTITY,
    CODE_IMPLICIT_DENY,
    CODE_INVALID_CREDENTIAL,
    CODE_NO_PERMISSION,
    PRODUCT_STS,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
)

# The identity fields worth echoing back: all of them are public account
# identifiers, never secret material.
_IDENTITY_FIELDS = ("AccountId", "Arn", "UserId", "IdentityType", "PrincipalId")


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
    """Return the caller identity as a plain dict.

    Raises :class:`CliError` when the credential chain itself is broken, so the
    caller can decide between a hard stop and a degraded report.
    """
    kwargs = {"session_id": session_id or new_session_id()}
    if timeout:
        kwargs["timeout"] = timeout
    return run_cli(PRODUCT_STS, ACTION_GET_CALLER_IDENTITY, {}, **kwargs)


def derive_uid_tag(identity):
    """Build the short traceability tag used in reports: account plus id type."""
    if not identity:
        return "account=unknown"
    account = str(identity.get("AccountId") or "unknown")
    kind = str(identity.get("IdentityType") or "unknown")
    user = str(identity.get("UserId") or "")
    tag = "account=%s principal=%s" % (account, kind)
    if user and user != account:
        tag += " uid=%s" % user
    return tag


def _permission_hint(code):
    if code in (CODE_NO_PERMISSION, CODE_IMPLICIT_DENY):
        return ("The credential is valid but is not allowed to call "
                "sts:GetCallerIdentity. Attach that single action, or the four "
                "Describe actions listed in references/ram-policies.md, to the "
                "identity in use.")
    if code == CODE_INVALID_CREDENTIAL:
        return credential_remediation()
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sts_token.py",
        description="Confirm which Alibaba Cloud account the CLI is acting as.",
    )
    parser.add_argument("--json", action="store_true",
                        help="print the identity body as JSON")
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the per-call timeout in seconds")
    args = parser.parse_args(argv)

    session_id = new_session_id()
    try:
        identity = get_caller_identity(session_id=session_id, timeout=args.timeout)
    except CliError as exc:
        body = {"status": STATUS_FAIL, "code": exc.code, "error": exc.message,
                "session_id": session_id,
                "hint": _permission_hint(exc.code) or credential_remediation()}
        if args.json:
            print(json.dumps(body, indent=2, sort_keys=True))
        else:
            print("STATUS: %s" % STATUS_FAIL)
            print("IDENTITY: unavailable (%s)" % exc.code)
            print("DETAIL: %s" % mask_secrets(exc.message))
            print("NEXT_STEP: %s" % body["hint"])
            print("NEXT_ACTION: fix the credential chain or the granted policy, "
                  "then re-run this script before any instance query.")
        return 2

    if not identity or not identity.get("AccountId"):
        body_text = ("the identity response carried no account identifier, so no "
                     "value was inferred")
        if args.json:
            print(json.dumps({"status": STATUS_DEGRADED, "error": body_text,
                              "session_id": session_id}, indent=2, sort_keys=True))
        else:
            print("STATUS: %s" % STATUS_DEGRADED)
            print("IDENTITY: incomplete")
            print("DETAIL: %s" % body_text)
            print("NEXT_ACTION: confirm the profile in use with aliyun configure "
                  "list, then re-run.")
        return 1

    safe = dict((key, identity[key]) for key in _IDENTITY_FIELDS
                if identity.get(key) is not None)
    if args.json:
        print(json.dumps({"status": STATUS_OK, "session_id": session_id,
                          "identity": safe, "trace_tag": derive_uid_tag(identity)},
                         indent=2, sort_keys=True))
    else:
        print("STATUS: %s" % STATUS_OK)
        print("IDENTITY: %s" % derive_uid_tag(identity))
        for key in sorted(safe):
            print("  %s: %s" % (key, safe[key]))
        print("NEXT_ACTION: compare this account and the target region against the "
              "instance the customer expects before any credential conclusion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
