#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: READ-ONLY identity check. This script only invokes the aliyun CLI's
STS identity command (plugin mode: aliyun sts get-caller-identity) to verify
who the current CLI session is. It performs no explicit credential handling:
it never reads, prints, caches or forwards any AccessKey / Secret / token
value, and it writes no credential file. Authentication is resolved
exclusively by the aliyun CLI default credential chain.

The AccountId it returns is used only as a local traceability label so the
report can state WHICH account the read-only evidence was collected from
(matters in this tier: punishment records are account-scoped, and real
tickets show diagnosis going wrong when the resource lives in a different
account or region than the credential in use).

Usage:
  python3 sts_token.py
  python3 sts_token.py --json
"""

from __future__ import annotations

import argparse
import json
import sys

import _cli


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

def get_caller_identity(profile: str | None = None) -> dict:
    """Run the STS identity command through the shared CLI layer.

    Exits with guidance (never a credential request) when the call fails.
    """
    _cli.check_cli_available()
    try:
        return _cli.call(_cli.STS_PRODUCT, "GetCallerIdentity", {},
                         profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] caller identity check failed: {e}\n"
            "[ERROR] Next step: configure the aliyun CLI default credential "
            "chain (run `aliyun sts get-caller-identity`); do not pass credentials to "
            "this script.",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI caller identity "
                    "(read-only, default credential chain only)",
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    account_id = str(identity.get("AccountId") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")
    arn = str(identity.get("Arn") or "")

    if not account_id:
        print(
            "[ERROR] the identity response carried no AccountId; verify the "
            "configured credential belongs to the intended account.",
            file=sys.stderr,
        )
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: re-check the CLI credential profile before running the guide script")
        sys.exit(1)

    summary = (
        f"Verified the account behind the configured CLI credential "
        f"(account ending {account_id[-4:] if len(account_id) > 4 else account_id}, "
        f"identity type {identity_type}). All read-only queries of this "
        f"skill cover THIS account only."
    )

    if args.json:
        print(json.dumps({
            "account_id": account_id,
            "arn": arn,
            "identity_type": identity_type,
            "summary": summary,
        }, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print(f"  AccountId ending : {account_id[-4:] if len(account_id) > 4 else account_id}")
        print(f"  IdentityType     : {identity_type}")
        print(f"  Arn              : {arn}")
        print("=" * 60)
        print("\nSummary")
        print("-------")
        print(summary)
        print("Next step       : confirm this is the account that received "
              "the violation notice; punishment records are account-scoped. "
              "Then run punishment_appeal_guide.py.")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run punishment_appeal_guide.py --region-id <region> "
          "to collect the read-only evidence")


if __name__ == "__main__":
    main()
