"""Credential provenance check for alibabacloud-ecs-marketplace-image-guide.

Runs the CLI in plugin mode (`aliyun sts get-caller-identity`, lower-case hyphenated
action) so that every report can state which account the read-only facts came from.

This module never asks for, reads, stores or prints an access key pair. Credentials are
resolved by the default credential chain of the locally configured CLI. When the identity
call fails, the caller degrades the report and the operator is pointed at
`aliyun configure`; nothing here guesses an account identifier.

Run directly for a standalone check:

    python3 sts_token.py
"""

import argparse
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
# --- end hygiene

def get_caller_identity(session_id=None, timeout=None):
    """Return {"account_id": ..., "arn": ..., "user_id": ..., "identity_type": ...}.

    Raises _cli.CliError when the identity cannot be resolved.
    """
    body = _cli.call(
        C.STS_ACTION_CALLER_IDENTITY,
        params=None,
        session_id=session_id,
        product=C.PRODUCT_STS,
        timeout=C.IDENTITY_TIMEOUT_SECONDS if timeout is None else timeout,
    )
    account_id = _cli.pick(body, ("AccountId", "accountId", "Account"))
    if isinstance(account_id, (dict, list)):
        account_id = _cli.pick(account_id, ("AccountId", "accountId"))
    return {
        "account_id": _cli.text(account_id),
        "arn": _cli.text(_cli.pick(body, ("Arn", "arn", "PrincipalArn"))),
        "user_id": _cli.text(_cli.pick(body, ("UserId", "userId", "PrincipalId"))),
        "identity_type": _cli.text(_cli.pick(body, ("IdentityType", "identityType"))),
        "raw": body,
    }


def describe_for_report(session_id=None):
    """Best-effort provenance line for the report; never raises."""
    try:
        info = get_caller_identity(session_id=session_id)
    except _cli.CliError as exc:
        _cli.warn("caller identity unavailable: {0}".format(exc))
        return {
            "available": False,
            "account_id": "",
            "note": (
                "Caller identity could not be resolved. Re-check the local CLI profile "
                "with `aliyun configure`; do not pass credentials on the command line."
            ),
            "error": _cli.mask_secrets(str(exc)),
        }
    return {
        "available": True,
        "account_id": info["account_id"],
        "arn": info["arn"],
        "note": "Facts below are scoped to this account and to the requested region only.",
        "error": "",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify the active credential and print its account id.")
    parser.add_argument("--timeout", type=int, default=C.IDENTITY_TIMEOUT_SECONDS,
                        help="Per-call timeout in seconds.")
    args = parser.parse_args(argv)

    session_id = _cli.new_session_id()
    print("session_id: {0}".format(session_id))
    print("user_agent: {0}".format(_cli.user_agent(session_id)))
    try:
        info = get_caller_identity(session_id=session_id, timeout=args.timeout)
    except _cli.CliError as exc:
        print("account_id: -")
        print("detail: {0}".format(exc))
        print("STATUS: FAIL")
        print("NEXT_ACTION: Fix the local CLI credential profile with `aliyun configure`, "
              "then re-run. Never place an access key pair in a command or file.")
        return 2
    print("account_id: {0}".format(info["account_id"] or "-"))
    print("arn: {0}".format(info["arn"] or "-"))
    print("identity_type: {0}".format(info["identity_type"] or "-"))
    print("STATUS: OK")
    print("NEXT_ACTION: Run ecs_marketplace_image_guide.py with --region-id to collect "
          "the read-only image facts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
