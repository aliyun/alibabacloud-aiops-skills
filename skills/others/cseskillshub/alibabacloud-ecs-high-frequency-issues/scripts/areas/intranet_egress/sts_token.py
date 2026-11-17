#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
===================================================
SECURITY: Non-mutating identity check only. This script calls STS
GetCallerIdentity through the shared aliyun CLI layer in _cli.py to find out
WHO the configured credential belongs to, and derives the account UID used as
a traceability label and as the asset-ownership baseline for the diagnosis.
It performs no explicit credential handling: it never reads, prints, caches,
accepts as arguments or writes out any access key, secret or session token.
Authentication is resolved exclusively by the aliyun CLI default credential
chain.

Why this exists (evidence: real support tickets): a large share of
"connectivity" tickets are mis-routed -- the target server belongs to a
DIFFERENT Alibaba Cloud account, or is not an Alibaba Cloud asset at all.
Confirming the account behind the credential first turns that check into one
query instead of a support round trip.

Output contract:
  - default: human identity table + Summary + STATUS / NEXT_ACTION lines
  - --json : machine-readable identity fields

Usage:
  python3 scripts/areas/intranet_egress/sts_token.py
  python3 scripts/areas/intranet_egress/sts_token.py --json
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

def get_caller_identity(region: str = "cn-hangzhou") -> dict:
    """Run STS GetCallerIdentity through the shared CLI layer.

    Exits with code 2 and clear guidance when the credential chain is not
    usable: the caller must repair `aliyun sts get-caller-identity`, never hand key
    material to this skill.
    """
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, region=region)
    except _cli.CliError as e:
        print(
            f"[ERROR] get-caller-identity failed: {e}\n"
            "[ERROR] Next step: repair the aliyun CLI default credential "
            "chain (`aliyun sts get-caller-identity`). This skill never accepts account "
            "credentials as parameters, and never asks the customer for a "
            "password, panel login or private key.",
            file=sys.stderr,
        )
        sys.exit(2)


def derive_uid(identity: dict) -> str:
    """Return the caller account UID, or exit 2 when it cannot be resolved."""
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print(
            "[ERROR] get-caller-identity returned no AccountId; the account "
            "baseline for the ownership check is unavailable.",
            file=sys.stderr,
        )
        sys.exit(2)
    return uid


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sts_token.py",
        description=(
            "Verify the current aliyun CLI caller identity via STS "
            "GetCallerIdentity (non-mutating; account-ownership baseline)"
        ),
    )
    parser.add_argument("--region-id", default="cn-hangzhou",
                        help="region used only for CLI endpoint resolution "
                             "of the central STS service")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(args.region_id)
    uid = derive_uid(identity)
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (
        f"Verified the account behind the configured CLI credential. Account "
        f"UID: {uid} (identity type: {identity_type}). Every connectivity "
        f"query run by this skill covers THIS account only; resources owned "
        f"by another account legitimately show up as 'not found'."
    )
    key_findings = [
        f"Account UID: {uid}",
        f"Identity type: {identity_type}",
        f"Caller ARN: {arn}" if arn else "Caller ARN not reported",
    ]
    suggestions = [
        "Confirm this UID is the account that OWNS the instance being "
        "diagnosed before continuing; cross-account resources cannot be "
        "read from here.",
        "Proceed to scripts/areas/intranet_egress/ecs_connectivity_diagnose.py with --region-id "
        "plus the instance locator.",
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
        print("=" * 62)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 62)
        print(f"  AccountId (UID) : {uid}")
        print(f"  Arn             : {arn}")
        print(f"  IdentityType    : {identity_type}")
        print("=" * 62)
        print("\nSummary")
        print("-------")
        print("What was checked : the identity attached to the configured "
              "Alibaba Cloud CLI credential.")
        print(f"Key finding      : account UID is {uid}; type "
              f"{identity_type}.")
        print("Next step        : if this is the account owning the target "
              "instance, run the entry script; otherwise select the right "
              "CLI profile first.")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/areas/intranet_egress/ecs_connectivity_diagnose.py with "
          "--region-id and --instance-id (or an IP locator) for the "
          "connectivity diagnosis")


if __name__ == "__main__":
    main()
