#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: READ-ONLY identity check for the
alibabacloud-ecs-snapshot-consistency-group skill. This script only calls STS
GetCallerIdentity (plugin mode: `aliyun sts get-caller-identity`) to verify
who the current CLI session is and to derive the account UID as a
traceability label. It performs NO explicit credential handling, never reads
or writes any AccessKey material, and never writes any credential cache file.
Authentication is resolved exclusively by the aliyun CLI default credential
chain; never pass AK/SK to this script.

Dual-audience output:
  - Default (human-readable): an identity table plus a plain-language
    "Summary" section (what was checked / what was found / what to do next).
  - --json (for Agents): structured identity fields plus machine-consumable
    "summary" / "key_findings" / "suggestions" / "status" / "next_action".

Usage:
  python3 sts_token.py
  python3 sts_token.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

import _cli
from _constants import DEFAULT_TIMEOUT, SKILL_NAME


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

def get_caller_identity(profile: Optional[str] = None,
                        timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run STS GetCallerIdentity through the shared CLI layer and return the
    parsed response. Exits with a clear error when the call fails."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile,
                         timeout=timeout)
    except _cli.CliError as e:
        print(
            f"[ERROR] get-caller-identity failed ({e.code or 'unknown'}): {e}\n"
            "[ERROR] Next step: check that the aliyun CLI default credential "
            "chain is configured (run `aliyun configure`); never pass AK/SK "
            "manually. If the credential is configured but the call is "
            "denied, report the authorization failure as NoPermission or "
            "ImplicitDeny with the missing action.",
            file=sys.stderr,
        )
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: configure the aliyun CLI credential chain "
              "(aliyun configure), then re-run sts_token.py")
        sys.exit(1)


def derive_uid(identity: dict) -> str:
    """Derive the caller UID (AccountId) from the caller identity."""
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print(
            "[ERROR] get-caller-identity returned no AccountId; cannot "
            "derive the UID. Next step: verify the configured credential "
            "belongs to the intended account.",
            file=sys.stderr,
        )
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: verify the configured credential belongs to the "
              "intended account, then re-run sts_token.py")
        sys.exit(1)
    return uid


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Verify the current aliyun CLI caller identity via STS "
                     "get-caller-identity (read-only)"),
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Per-call timeout in seconds (default 60)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile, timeout=args.timeout)
    uid = derive_uid(identity)
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")
    session = _cli.session_id()

    summary = (
        f"Verified the account identity behind the configured CLI "
        f"credential. The account UID is {uid} (identity type: "
        f"{identity_type}). Read-only queries run by this skill cover this "
        f"account only; snapshot and disk facts are additionally isolated "
        f"per region."
    )
    key_findings = [
        f"Account UID: {uid}",
        f"Identity type: {identity_type}",
        f"Credential ARN: {arn}" if arn else "Credential ARN not reported",
        f"Session id (observability): {session}",
    ]
    suggestions = [
        "Confirm this UID matches the account whose snapshot consistency "
        "groups you want to check before running the entry script.",
        "Proceed to snapshot_group_check.py (--mode precheck before a "
        "manual group creation, --mode verify afterwards, --mode rules for "
        "capability-boundary questions).",
    ]
    next_action = ("run snapshot_group_check.py with the customer's RegionId "
                   "and the target InstanceId or DiskIds")

    if args.json:
        print(json.dumps({
            "skill": SKILL_NAME,
            "uid": uid,
            "account_id": identity.get("AccountId"),
            "arn": identity.get("Arn"),
            "identity_type": identity.get("IdentityType"),
            "session_id": session,
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
            "errors": [],
            "status": "OK",
            "next_action": next_action,
        }, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print(f"  AccountId (UID) : {uid}")
        print(f"  Arn             : {arn}")
        print(f"  IdentityType    : {identity_type}")
        print(f"  Session id      : {session}")
        print("=" * 60)
        print("\nSummary")
        print("-------")
        print("What was checked : the identity attached to your configured "
              "Alibaba Cloud CLI credential.")
        print(f"Key finding      : identity verified. Your account number "
              f"(UID) is {uid}; identity type is {identity_type}.")
        print("Next step        : if this is the account you expect, proceed "
              "with the entry script. If not, switch to the correct "
              "credential profile first.")
    print("\nSTATUS: OK")
    print(f"NEXT_ACTION: {next_action}")


if __name__ == "__main__":
    main()
