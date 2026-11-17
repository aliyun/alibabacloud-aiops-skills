#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: READ-ONLY identity check. This script only calls STS
GetCallerIdentity to verify who the current aliyun CLI session is. It performs
NO explicit credential handling, never reads or writes any AccessKey / Secret,
and never writes any credential cache file. Authentication is resolved
exclusively by the aliyun CLI default credential chain.

Dual-audience output:
  - Default (human-readable): an identity table plus a plain-language "Summary".
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

def get_caller_identity(profile=None):
    """Run STS GetCallerIdentity through the shared CLI layer and return the
    parsed response. Exits with a clear error when the call fails."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as exc:
        print(
            "[ERROR] get-caller-identity failed: " + str(exc) + "\n"
            "[ERROR] Next step: check that the aliyun CLI credential chain is "
            "configured (run `aliyun sts get-caller-identity`); never pass AK/SK manually.",
            file=sys.stderr,
        )
        sys.exit(1)


def derive_uid(identity):
    """Derive the caller UID (AccountId) from the caller identity."""
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print(
            "[ERROR] get-caller-identity returned no AccountId; cannot derive "
            "UID. Next step: verify the configured credential belongs to the "
            "intended account.",
            file=sys.stderr,
        )
        sys.exit(1)
    return uid


def main():
    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI caller identity via STS "
                    "GetCallerIdentity (read-only)",
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    uid = derive_uid(identity)
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (
        "Verified the account identity behind the configured CLI credential. "
        "The account UID is " + uid + " (identity type: " + identity_type +
        "). Read-only queries run by this skill will cover this account only."
    )
    key_findings = [
        "Account UID: " + uid,
        "Identity type: " + identity_type,
        ("Credential ARN: " + arn) if arn else "Credential ARN not reported",
    ]
    suggestions = [
        "Confirm this UID matches the account whose instances you want to "
        "inspect before running the entry script.",
        "Proceed to ddh_capacity_guide.py with --region-id and the target "
        "instance id(s) or instance type(s).",
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
        print("  AccountId (UID) : " + uid)
        print("  Arn             : " + arn)
        print("  IdentityType    : " + identity_type)
        print("=" * 60)
        print("\nSummary")
        print("-------")
        print("What was checked : the identity attached to your configured "
              "Alibaba Cloud CLI credential.")
        print("Key finding      : identity verified. Your account number (UID) "
              "is " + uid + "; identity type is " + identity_type + ".")
        print("Next step        : if this is the account you expect, proceed "
              "with the entry script. If not, switch to the correct credential "
              "profile first.")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run ddh_capacity_guide.py with --region-id and the "
          "target instance id(s) or instance type(s)")


if __name__ == "__main__":
    main()
