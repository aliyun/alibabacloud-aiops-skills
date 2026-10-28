#!/usr/bin/env python3
"""sts_token.py - verify the ambient credential and derive the account label.

SECURITY: this script performs one identity check only (the STS
``get-caller-identity`` plugin-mode command, resolved through the shared CLI
layer). Credentials come exclusively from the aliyun CLI default chain
(environment or the CLI config file). This script never reads, accepts,
stores, prints or passes an access key id, an access key secret or a security
token, and it never asks the customer for any of them.

Output contract:
    STATUS: OK        an AccountId was resolved; NEXT_ACTION continues the run
    STATUS: FAIL      the identity check failed; nothing is concluded

Exit codes: 0 = OK, 2 = FAIL (or the CLI being unavailable).
"""

from __future__ import annotations

import argparse
import sys

import _cli
from _constants import CLI_TIMEOUT_SECONDS, STATUS_OK, STATUS_FAIL

_CLI_MISSING_MARKERS = ("cliunavailable", "not found on path")


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

def _is_cli_missing(error: str) -> bool:
    lowered = (error or "").lower()
    return any(marker in lowered for marker in _CLI_MISSING_MARKERS)


# boundary assertions for the pure classifier above
assert _is_cli_missing("CliUnavailable: the aliyun CLI was not found on PATH")
assert not _is_cli_missing("Code: NoPermission for sts identity")
assert not _is_cli_missing("")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sts_token.py",
        description="Verify the default-chain credential via the STS identity check.",
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI profile name (never a key pair).")
    parser.add_argument("--timeout", type=int, default=CLI_TIMEOUT_SECONDS,
                        help="Per-call timeout in seconds for the identity check.")
    args = parser.parse_args(argv)

    _cli.check_cli_available()
    session_id = _cli.new_session_id()
    print("# Identity check")
    print("- session-id: {0}".format(session_id))

    account_id, error = _cli.resolve_account_id(
        session_id=session_id, profile=args.profile,
    )
    if error:
        print("- The identity check failed: {0}".format(error))
        if _is_cli_missing(error):
            print("- Recovery: install the aliyun CLI, then run `aliyun configure`; "
                  "this skill never accepts key material directly.")
        else:
            print("- Recovery: run `aliyun configure` in this environment; this skill "
                  "never accepts key material directly.")
        print(STATUS_FAIL)
        print("NEXT_ACTION: repair the default credential chain, then re-run "
              "`python3 scripts/sts_token.py`.")
        return 2

    # The account id is a traceability label only.
    print("- AccountId (auto-derived from the default chain): {0}".format(
        account_id or "not returned"))
    print(STATUS_OK)
    print("NEXT_ACTION: continue with the diagnose subcommand of "
          "scripts/snapshot_io_diagnosis.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
