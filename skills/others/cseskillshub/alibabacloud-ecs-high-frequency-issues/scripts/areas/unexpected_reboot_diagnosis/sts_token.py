#!/usr/bin/env python3
"""Credential preflight for the unexpected-reboot diagnosis skill.

Runs ONE call, `aliyun sts get-caller-identity` (CLI plugin mode), to prove
the default credential chain resolves and to derive the account UID used
purely as a traceability label in reports.

SECURITY: this script never accepts, reads, stores, prints or forwards an
AccessKey pair or a security token. Credentials resolve automatically
through the aliyun CLI default chain. If it fails, the remedy is
`aliyun sts get-caller-identity` in the operator's own environment -- not pasting keys
into the conversation.

Usage:
    python3 scripts/areas/unexpected_reboot_diagnosis/sts_token.py [--profile <name>] [--json]

Exit codes: 0 = identity resolved, 1 = credential chain failed.
"""

import argparse
import sys

from _cli import CliError, call_sts, new_session_id


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

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify credentials via sts get-caller-identity "
                    "(read-only preflight).")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI profile name")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable result object")
    args = parser.parse_args(argv)

    session_id = new_session_id()
    try:
        body = call_sts(session_id, profile=args.profile)
    except CliError as err:
        print("account_id: (unresolved)", file=sys.stderr)
        print("identity: unresolved", file=sys.stderr)
        print("[WARN] credential preflight failed: {0}".format(err),
              file=sys.stderr)
        print("Remedy: configure the aliyun CLI default credential chain "
              "(run `aliyun sts get-caller-identity` in your own session). This skill "
              "never accepts an AccessKey pair or token as input.")
        print("STATUS: FAIL")
        print("NEXT_ACTION: ask the operator to fix the CLI credential "
              "chain, then rerun scripts/areas/unexpected_reboot_diagnosis/sts_token.py")
        return 1

    account_id = str(body.get("AccountId", "") or "")
    identity = str(body.get("Arn", "") or "")
    if args.json:
        print("{{\"session_id\": \"{0}\", \"account_id\": \"{1}\", "
              "\"identity\": \"{2}\"}}".format(session_id, account_id,
                                               identity))
    else:
        print("session_id: {0}".format(session_id))
        print("account_id: {0}".format(account_id))
        print("identity: {0}".format(identity))
        print("STATUS: OK")
        print("NEXT_ACTION: run scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py diagnose with "
              "--region-id and --instance-id")
    return 0


if __name__ == "__main__":
    sys.exit(main())
