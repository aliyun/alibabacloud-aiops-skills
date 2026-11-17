#!/usr/bin/env python3
"""Credential probe for the read-only ECS stop-mode billing guide.

Runs ``aliyun sts get-caller-identity`` (plugin mode, lowercase-hyphenated,
verified against aliyun CLI 3.4.5) through the shared CLI layer to confirm that
the default credential chain of this environment works, and derives a short
account tag so report lines can be traced back to the account that produced
them.

It never handles an access key pair: there is no parameter, prompt, file or
environment lookup for credentials anywhere in this skill.
"""

import argparse
import json
import sys

import _cli
import _constants as C


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

def _tail(value, keep=4):
    text = str(value or "")
    if not text:
        return "unknown"
    return text[-keep:] if len(text) > keep else text


def account_tag(caller):
    """Return a short, non-sensitive trace tag for the calling account."""
    return "acct-{0}".format(_tail(caller.get("AccountId") or caller.get("accountId")))


def get_caller_identity(session_id=None, timeout=C.STS_TIMEOUT_SECONDS):
    """Return the caller identity dict, or raise ``_cli.CliError``."""
    sid = session_id or _cli.new_session_id()
    caller = _cli.run_product_readonly(
        C.STS_PRODUCT,
        "GetCallerIdentity",
        [],
        sid,
        timeout=timeout,
        retries=0,
        allowed=C.ALLOWED_STS_ACTIONS,
    )
    if not isinstance(caller, dict) or not (caller.get("AccountId") or caller.get("accountId")):
        raise _cli.CliError(
            "UnexpectedIdentity",
            "the identity call did not return an account id; treat every downstream "
            "conclusion as unverified",
            action="GetCallerIdentity",
        )
    return caller


def credential_guidance(error):
    """Return the customer-facing next step for a failed credential probe."""
    if error is None:
        return []
    if error.is_auth_failure:
        return [
            "Credential or authorization check failed: {0}".format(error),
            "Required read-only actions: {0}".format(", ".join(C.RAM_READ_ONLY_ACTIONS)),
            "Ask the account administrator to attach the minimal policy in "
            "references/ram-policies.md, then run this script again.",
        ]
    return [
        "Credential probe failed: {0}".format(error),
        "Run 'aliyun sts get-caller-identity' in this environment so the default credential chain resolves; "
        "this skill never asks for an access key pair.",
    ]


def _parser():
    parser = argparse.ArgumentParser(
        prog="sts_token.py",
        description="Verify the default credential chain and print a short account tag.",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    session_id = _cli.new_session_id()
    try:
        caller = get_caller_identity(session_id)
    except _cli.CliError as exc:
        _cli.warn(exc)
        if args.json:
            print(json.dumps({"status": "FAIL", "error": str(exc), "session_id": session_id}))
        else:
            sys.stdout.write("STATUS: FAIL\n")
            for line in credential_guidance(exc):
                sys.stdout.write("- {0}\n".format(line))
            sys.stdout.write("NEXT_ACTION: fix the credential chain, then re-run this probe\n")
        return 2

    if args.json:
        print(json.dumps({
            "status": "OK",
            "session_id": session_id,
            "account_tag": account_tag(caller),
            "identity_type": caller.get("IdentityType") or caller.get("identityType") or "unknown",
            "arn": caller.get("Arn") or caller.get("arn") or "unknown",
        }))
    else:
        sys.stdout.write("Account tag : {0}\n".format(account_tag(caller)))
        sys.stdout.write("Identity    : {0}\n".format(caller.get("IdentityType") or "unknown"))
        sys.stdout.write("User-Agent  : {0}\n".format(_cli.user_agent_for(session_id)))
        sys.stdout.write("STATUS: OK\n")
        sys.stdout.write("NEXT_ACTION: none; proceed with the read-only assessment\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
