#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: READ-ONLY identity check. This script only calls STS
GetCallerIdentity (via `aliyun sts get-caller-identity`, plugin mode, CLI
default credential chain) to verify who the current session is. It performs
NO explicit credential handling, never reads or writes any AccessKey /
Secret, and never writes any credential cache file.

Dual-audience output:
  - Default (human-readable): an identity table plus a plain-language
    "Summary" section (what was checked / what was found / what to do next).
  - --json (for Agents): structured identity fields plus machine-consumable
    "summary" / "key_findings" / "suggestions" fields.

Usage:
  python3 sts_token.py
  python3 sts_token.py --json
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client


def get_caller_identity() -> dict:
    """Run STS GetCallerIdentity through the shared client layer and return
    the parsed response. Exits with a clear error when the call fails."""
    try:
        return _oss_client.get_caller_identity()
    except _oss_client.CliError as e:
        print(
            f"[ERROR] get-caller-identity failed: {e}\n"
            "[ERROR] Next step: check that the aliyun CLI credential chain "
            "is configured (run `aliyun configure`); never pass AK/SK "
            "manually.",
            file=sys.stderr,
        )
        sys.exit(1)


def derive_uid(identity: dict) -> str:
    """Derive the caller UID (AccountId) from the caller identity."""
    uid = str(identity.get("AccountId") or "").strip()
    if not uid:
        print(
            "[ERROR] get-caller-identity returned no AccountId; cannot "
            "derive UID. Next step: verify the configured credential belongs "
            "to the intended account.",
            file=sys.stderr,
        )
        sys.exit(1)
    return uid


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI caller identity via STS "
                    "GetCallerIdentity (read-only)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity()
    uid = derive_uid(identity)
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (
        f"Verified the account identity behind the configured CLI "
        f"credential. The account UID is {uid} "
        f"(identity type: {identity_type}). OSS cross-region replication "
        f"config checks run by this skill will cover this account only."
    )
    key_findings = [
        f"Account UID: {uid}",
        f"Identity type: {identity_type}",
        f"Credential ARN: {arn}" if arn else "Credential ARN not reported",
    ]
    suggestions = [
        "Confirm this UID matches the account that owns the OSS bucket "
        "before running the CRR config check script.",
        "Proceed to crr_config_check.py with --bucket (and optionally "
        "--endpoint / --region).",
    ]

    if args.json:
        print(json.dumps({
            "uid": uid,
            "account_id": identity.get("AccountId"),
            "arn": identity.get("Arn"),
            "identity_type": identity.get("IdentityType"),
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
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
        print(f"What was checked : the identity attached to your configured "
              f"Alibaba Cloud CLI credential.")
        print(f"Key finding     : identity verified. Your account number "
              f"(UID) is {uid}; identity type is {identity_type}.")
        print("Next step       : if this is the account you expect, proceed "
              "with crr_config_check.py. If not, switch to the correct "
              "credential profile first.")
    print("\nSTATUS: OK")
    print(f"NEXT_ACTION: run crr_config_check.py with --bucket (and "
          f"optionally --endpoint / --region) to check the replication "
          f"configuration")


if __name__ == "__main__":
    main()
