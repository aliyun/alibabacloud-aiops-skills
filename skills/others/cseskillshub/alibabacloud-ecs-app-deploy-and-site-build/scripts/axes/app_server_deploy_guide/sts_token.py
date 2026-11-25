#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
===================================================
SECURITY: evidence-class identity check. This script only calls STS
GetCallerIdentity to verify which account the configured aliyun CLI session
belongs to. It performs no explicit key handling, never reads or writes any
AccessKey material, and never writes a credential cache file. Authentication
is resolved exclusively by the aliyun CLI default credential chain.

Usage:
  python3 sts_token.py
  python3 sts_token.py --json
"""

from __future__ import annotations

import argparse
import json
import sys

import _cli
from _constants import (
    CODE_CLI_UNAVAILABLE,
    PRODUCT_STS,
    ACTION_GET_CALLER_IDENTITY,
)


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

def get_caller_identity(timeout=None):
    """Run STS GetCallerIdentity through the shared CLI layer and return the
    parsed response. Exits with clear guidance when the call fails."""
    body = None
    try:
        body = _cli.run_cli(PRODUCT_STS, ACTION_GET_CALLER_IDENTITY, {},
                            session_id=_cli.new_session_id(),
                            timeout=timeout or 30)
    except _cli.CliError as exc:
        if exc.code == CODE_CLI_UNAVAILABLE:
            print("[ERROR] %s" % exc.message, file=sys.stderr)
        else:
            print(
                "[ERROR] get-caller-identity failed: %s\n"
                "[ERROR] Next step: %s" % (exc.message,
                                           _cli.credential_remediation()),
                file=sys.stderr,
            )
        print("STATUS: FAIL")
        print("NEXT_ACTION: repair the aliyun CLI default credential chain "
              "with aliyun configure, then re-run this check")
        sys.exit(2)
    return body


def main():
    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI caller identity via STS "
                    "GetCallerIdentity (evidence class, mutates nothing)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the per-call timeout in seconds")
    args = parser.parse_args()

    identity = get_caller_identity(timeout=args.timeout)
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    arn = str(_cli.mask_secrets(identity.get("Arn") or ""))
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (
        "Verified the account behind the configured CLI credential. The "
        "account UID is %s (identity type: %s). Every query this skill runs "
        "covers this account only." % (uid or "not returned", identity_type)
    )
    if args.json:
        print(json.dumps({
            "uid": uid,
            "arn": arn,
            "identity_type": identity_type,
            "summary": summary,
        }, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print("  AccountId (UID) : %s" % (uid or "not returned"))
        print("  Arn             : %s" % (arn or "not returned"))
        print("  IdentityType    : %s" % identity_type)
        print("=" * 60)
        print("\nSummary")
        print("-------")
        print(summary)
        print("Next step       : if this is the account you expect, run "
              "scripts/app_server_deploy_guide.py with the target region and "
              "instance; if not, switch the credential profile first.")
    if not uid:
        print("\nSTATUS: DEGRADED")
        print("NEXT_ACTION: the identity call returned but carried no "
              "AccountId; re-check the credential profile before deploying "
              "anything against this account")
        sys.exit(1)
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/app_server_deploy_guide.py --region-id "
          "<region> --instance-id <i-...> for the deployment-preparation "
          "assessment")


if __name__ == "__main__":
    main()
