#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
===================================================
SECURITY: READ-ONLY identity check. This script only calls STS
GetCallerIdentity (via the aliyun CLI plugin-mode command
`aliyun sts get-caller-identity`) to verify who the current CLI session is.
It performs NO explicit credential handling, never reads or writes any
AccessKey, Secret, or token, and never writes any credential cache file.
Authentication is resolved exclusively by the aliyun CLI default credential
chain.

Purpose in this skill: confirm the credential works and derive the account
UID used ONLY as a traceability label in the advisory report. If it fails,
this script guides the user to `aliyun configure`; it never asks for an AK
or Secret value.

Usage:
  python3 scripts/sts_token.py
  python3 scripts/sts_token.py --json
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
# --- end hygiene

def get_caller_identity(profile: str | None = None) -> dict:
    """Run STS GetCallerIdentity through the shared CLI layer and return the
    parsed response. Exits with a clear error when the call fails."""
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] get-caller-identity failed: {e}\n"
            "[ERROR] Next step: check that the aliyun CLI credential chain "
            "is configured (run `aliyun configure`); never pass credential "
            "values manually.",
            file=sys.stderr,
        )
        sys.exit(1)


def derive_uid(identity: dict) -> str:
    """Derive the caller UID (AccountId) from the caller identity."""
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print(
            "[ERROR] get-caller-identity returned no AccountId; cannot "
            "derive the UID label. Next step: verify the configured "
            "credential belongs to the intended account.",
            file=sys.stderr,
        )
        sys.exit(1)
    return uid


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the current aliyun CLI caller identity via STS "
            "GetCallerIdentity (read-only)"
        ),
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    uid = derive_uid(identity)
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (
        f"Verified the account identity behind the configured CLI "
        f"credential. The account UID is {uid} (identity type: "
        f"{identity_type}). Read-only queries run by this skill cover this "
        f"account, and only the region each query names."
    )
    key_findings = [
        f"Account UID: {uid}",
        f"Identity type: {identity_type}",
    ]
    suggestions = [
        "Confirm this UID matches the account whose ECS instances you want "
        "backup advice for before running the advisor script.",
        "Proceed to scripts/backup_strategy_advisor.py with the backup "
        "design question.",
    ]

    if args.json:
        print(json.dumps({
            "uid": uid,
            "identity_type": identity_type,
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
        }, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print(f"  AccountId (UID) : {uid}")
        print(f"  IdentityType    : {identity_type}")
        print("=" * 60)
        print("\nSummary")
        print("-------")
        print("What was checked : the identity attached to your configured "
              "Alibaba Cloud CLI credential.")
        print(f"Key finding      : identity verified; account UID label is "
              f"{uid}.")
        print("Next step        : if this is the account you expect, run "
              "scripts/backup_strategy_advisor.py for the backup design "
              "question. If not, switch to the correct credential profile "
              "first.")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/backup_strategy_advisor.py with the "
          "backup design inputs (region, target objects, sizes, retention)")


if __name__ == "__main__":
    main()
