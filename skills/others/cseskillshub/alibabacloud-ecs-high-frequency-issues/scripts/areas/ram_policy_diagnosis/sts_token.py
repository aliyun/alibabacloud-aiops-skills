#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sts_token.py -- caller identity verification helper
===================================================
SECURITY: Non-mutating identity check. This script only calls STS
GetCallerIdentity to verify who the configured aliyun CLI credential belongs
to. It performs NO explicit credential handling: it never reads, prints,
caches or asks for any AccessKey / Secret / token -- authentication is
resolved exclusively by the aliyun CLI default credential chain. It confirms
the credential; when it fails, the guidance is always `aliyun sts get-caller-identity`,
never a request for key material.

Why this skill starts with identity: the first triage question of a RAM
permission case is WHICH identity the client actually presents (root
account / RAM user / assumed role). A grant attached to the wrong identity
place is a top real-ticket root cause.

Dual-audience output:
  - Default (human-readable): identity table + plain-language Summary.
  - --json (for Agents): machine fields + summary/key_findings/suggestions.

Usage:
  python3 sts_token.py
  python3 sts_token.py --json
  python3 sts_token.py --profile <name>
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
    """Run STS GetCallerIdentity through the shared CLI layer.

    Exits with a clear credential-chain guidance message when the call
    fails; never requests key material.
    """
    _cli.check_cli_available()
    try:
        return _cli.resolve_caller_identity(profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] get-caller-identity failed: {e}\n"
            "[ERROR] Next step: check that the aliyun CLI credential chain "
            "is available (verify with `aliyun sts get-caller-identity`); never pass key "
            "material manually.",
            file=sys.stderr,
        )
        sys.exit(1)


_IDENTITY_MEANING = {
    "Account": "the root (main) account itself -- denials under this identity "
               "are not RAM grant problems",
    "RAMUser": "a sub-account (RAM user) -- its grants live under Users -> "
               "the user's Permissions tab",
    "AssumedRole": "an assumed RAM role -- the ROLE's grants decide access, "
                   "not the caller's personal user grants",
    "FederatedUser": "a federated identity -- check the role/provider grants",
}


def interpret_identity(identity: dict) -> str:
    """One-line, evidence-only interpretation of the identity type."""
    return _IDENTITY_MEANING.get(
        identity.get("identity_type", ""), "identity type not reported")


# Boundary assertions on the pure interpreter (batch layer-1 rule).
assert interpret_identity({"identity_type": "RAMUser"}).startswith("a sub-account")
assert "not reported" in interpret_identity({})
assert "not reported" not in interpret_identity({"identity_type": "Account"})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the configured aliyun CLI caller identity via STS "
                    "GetCallerIdentity (non-mutating; no credential handling)",
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    meaning = interpret_identity(identity)

    summary = (
        f"Verified the identity behind the configured CLI credential: "
        f"account UID {identity.get('account_id') or 'n/a'}, identity type "
        f"{identity.get('identity_type')}. {meaning}."
    )
    key_findings = [
        f"Account UID: {identity.get('account_id') or 'n/a'}",
        f"Identity type: {identity.get('identity_type')}",
        f"ARN: {identity.get('arn') or 'n/a'}",
    ]
    suggestions = [
        "Confirm this is the account whose ECS resources you are diagnosing; "
        "all queries below run against this account only.",
        "If the complaining client is a DIFFERENT identity (the sub-account "
        "in the ticket), its grants -- not these credentials' -- are the "
        "diagnosis target; note the UID of the customer account before "
        "proceeding.",
        "Proceed with scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py (paste the customer "
        "error text with --error-text).",
    ]

    if args.json:
        print(json.dumps({
            **identity,
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
        }, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print(f"  AccountId (UID) : {identity.get('account_id') or 'n/a'}")
        print(f"  IdentityType    : {identity.get('identity_type')}")
        print(f"  Arn             : {identity.get('arn') or 'n/a'}")
        print("=" * 60)
        print("\nSummary")
        print("-------")
        print(summary)

    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py --error-text "
          "\"<customer error as received>\" for the triage report")


if __name__ == "__main__":
    main()
