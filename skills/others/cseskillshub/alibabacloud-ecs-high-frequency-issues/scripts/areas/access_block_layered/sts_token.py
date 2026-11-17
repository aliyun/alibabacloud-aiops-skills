#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
===================================================
SECURITY: this script only calls STS GetCallerIdentity to confirm WHO the
configured CLI credential belongs to, so the diagnosis provably runs against
the customer's own account. It performs no explicit credential handling:
nothing here reads, prints, caches or passes AccessKeys or tokens; the aliyun
CLI default credential chain resolves authentication.

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
    """Run the identity check through the shared CLI layer or exit 1."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] identity check failed: {e}\n"
            "[ERROR] Next step: run `aliyun sts get-caller-identity` to set up the default "
            "credential chain. Never paste credentials into the chat and never "
            "pass them on a command line.",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the configured aliyun CLI caller identity and derive the account UID label",
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print(
            "[ERROR] the identity response carried no AccountId; cannot label "
            "the session. Next step: confirm the credential belongs to the "
            "intended account.",
            file=sys.stderr,
        )
        sys.exit(1)
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (
        f"Identity verified. The configured credential belongs to account "
        f"UID {uid} (type: {identity_type}). All layered checks run against "
        f"this account only."
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
        print(f"  AccountId (UID) : {uid}")
        print(f"  Arn             : {arn}")
        print(f"  IdentityType    : {identity_type}")
        print("=" * 60)
        print("\nSummary")
        print("-------")
        print(summary)
        print("Next step       : run diagnose_access_block.py for the target "
              "instance to start the layered check.")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/areas/access_block_layered/diagnose_access_block.py with the target instance")


if __name__ == "__main__":
    main()
