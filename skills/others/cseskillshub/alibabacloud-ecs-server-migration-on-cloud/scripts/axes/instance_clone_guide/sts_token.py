#!/usr/bin/env python3
"""
sts_token.py -- caller identity verification helper (READ-ONLY)

SECURITY: performs one read-only identity query (sts get-caller-identity via
the aliyun CLI) to verify the credential works and to derive the account UID
as a traceability label. NO explicit credential handling: no AccessKey /
SecretKey / token is read, printed, cached or written anywhere by this
script. Authentication is resolved exclusively by the aliyun CLI default
credential chain. No credential cache file is created.

Data-boundary meaning of this check: every read-only query issued by this
skill can only see THIS account and the region passed to the scripts. Facts
about resources in other accounts are always customer self-check items.

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
# --- end hygiene

def get_caller_identity(profile: str | None = None) -> dict:
    """Run the identity check through the shared CLI layer.

    Exits with guidance (never a credential prompt) when it fails.
    """
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] identity check failed: {e}\n"
            "[ERROR] Next step: configure the aliyun CLI default credential "
            "chain (run `aliyun configure`); never pass credentials on the "
            "command line and never share them with the agent.",
            file=sys.stderr,
        )
        sys.exit(1)


def derive_uid(identity: dict) -> str:
    """Derive the caller UID (AccountId) from the identity response."""
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print(
            "[ERROR] identity response carried no AccountId; cannot derive "
            "the UID label. Next step: verify the configured credential "
            "belongs to the intended account.",
            file=sys.stderr,
        )
        sys.exit(1)
    return uid


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the aliyun CLI caller identity via a read-only "
                    "STS query and print the account UID traceability label.",
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    uid = derive_uid(identity)
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    boundary = (
        "All read-only queries made by this skill see ONLY this account "
        f"(UID {uid}) and the single region passed to each script. Another "
        "account's instances, and image/snapshot task queues, are not "
        "visible to it; those stay customer self-check items."
    )
    summary = (
        "Verified the identity behind the configured CLI credential. "
        f"Account UID: {uid}; identity type: {identity_type}. This account "
        "owns every instance that the clone readiness check can read."
    )
    key_findings = [
        f"Account UID: {uid}",
        f"Identity type: {identity_type}",
        f"Credential ARN: {arn}" if arn else "Credential ARN not reported",
        boundary,
    ]
    suggestions = [
        "Confirm this UID is the account that owns the source/target "
        "instances of the clone before running the readiness check.",
        "For the other account in a cross-account clone, switch the CLI "
        "profile and rerun, or treat that account's facts as customer "
        "self-check items.",
        "Continue with scripts/clone_readiness_check.py (facts) and "
        "scripts/clone_guidance.py (path plan, triage, checklist).",
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
            "status": "OK",
            "next_action": "run scripts/clone_readiness_check.py for the "
                           "target region to collect instance facts",
        }, indent=2))
        # Keep stdout pure JSON: the contract lines go to stderr in --json mode.
        print("STATUS: OK", file=sys.stderr)
        print("NEXT_ACTION: run scripts/clone_readiness_check.py for the "
              "target region to collect instance facts before clone guidance",
              file=sys.stderr)
    else:
        print("=" * 62)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 62)
        print(f"  AccountId (UID) : {uid}")
        print(f"  Arn             : {arn}")
        print(f"  IdentityType    : {identity_type}")
        print("=" * 62)
        print("\nSummary")
        print("-------")
        print(summary)
        print(f"Data boundary   : {boundary}")
        print("Next step       : if this is the expected account, run "
              "clone_readiness_check.py and/or clone_guidance.py.")
        print("\nSTATUS: OK")
        print("NEXT_ACTION: run scripts/clone_readiness_check.py for the "
              "target region to collect instance facts before clone guidance")


if __name__ == "__main__":
    main()
