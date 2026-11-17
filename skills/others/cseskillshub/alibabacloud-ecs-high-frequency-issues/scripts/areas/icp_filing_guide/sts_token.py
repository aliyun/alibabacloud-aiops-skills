#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: READ-ONLY identity check. This script only calls STS
GetCallerIdentity (aliyun CLI plugin mode: `aliyun sts get-caller-identity`)
to verify which account the configured credential belongs to. It performs NO
explicit credential handling: it never reads, writes, caches, prints or
prompts for an AccessKey / SecretKey / STS token. Authentication is resolved
exclusively by the aliyun CLI default credential chain.

Purpose in this skill
---------------------
The account UID is used only as a traceability label in the reports of
icp_filing_check.py, and the identity check doubles as a credential
pre-flight: if it fails, the CLI credential chain is not configured and the
user is guided to run `aliyun sts get-caller-identity` (never to hand over credentials).

Dual-audience output:
  - default: a human-readable identity table plus a Summary section;
  - --json: structured fields for agent consumption.

Every run ends with the STATUS / NEXT_ACTION contract.
"""

from __future__ import annotations

import argparse
import json
import sys

import _cli
from _constants import DEFAULT_TIMEOUT, SKILL_NAME, STATUS_FAIL, STATUS_OK


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

def get_caller_identity(profile: str | None, timeout: int) -> dict:
    """Run STS GetCallerIdentity through the shared read-only CLI layer."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile,
                         timeout=timeout)
    except _cli.CliError as err:
        rec = _cli.describe_error(err)
        print(
            f"[ERROR] get-caller-identity failed: "
            f"{rec['code'] or 'error'}: {rec['message']}\n"
            "[ERROR] Next step: check that the aliyun CLI default credential "
            "chain is available (verify with `aliyun sts get-caller-identity`); never pass or "
            "accept an AccessKey manually.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def derive_uid(identity: dict) -> str:
    """Derive the caller UID (AccountId) from the identity response."""
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print(
            "[ERROR] get-caller-identity returned no AccountId; the UID "
            "label cannot be derived. Next step: verify that the configured "
            "credential belongs to the intended account.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return uid


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sts_token.py",
        description=("Verify the current aliyun CLI caller identity via "
                     "sts get-caller-identity (read-only) and derive the "
                     "account UID traceability label."),
    )
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI credential profile name")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="per-call timeout in seconds (default 60)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    args = parser.parse_args()

    identity = get_caller_identity(args.profile, args.timeout)
    uid = derive_uid(identity)
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (
        f"Verified the account identity behind the configured CLI "
        f"credential (skill {SKILL_NAME}). The account UID is {uid} "
        f"(identity type: {identity_type}). Every read-only query run by "
        f"this skill covers this account only."
    )
    key_findings = [
        f"Account UID: {uid}",
        f"Identity type: {identity_type}",
        f"Credential ARN: {arn}" if arn else "Credential ARN not reported",
    ]
    suggestions = [
        "Confirm this UID matches the account whose ICP filing questions you "
        "are handling; results never cover another account.",
        "Proceed to icp_filing_check.py (eligibility / triage / knowledge).",
    ]

    if args.json:
        print(json.dumps({
            "mode": "identity",
            "read_only": True,
            "uid": uid,
            "account_id": identity.get("AccountId"),
            "arn": identity.get("Arn"),
            "identity_type": identity.get("IdentityType"),
            "session_id": _cli.session_id(),
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
            "STATUS": STATUS_OK,
            "NEXT_ACTION": ("Declare the UID as auto-derived in the final "
                            "report, then run icp_filing_check.py in the "
                            "mode the customer's question needs."),
        }, indent=2))
    else:
        print("=" * 62)
        print(" Caller identity (aliyun CLI default credential chain)")
        print("=" * 62)
        print(f"  AccountId (UID) : {uid}")
        print(f"  Arn             : {arn}")
        print(f"  IdentityType    : {identity_type}")
        print(f"  Session label   : {_cli.session_id()}")
        print()
        print("Summary")
        print("-------")
        print(f"What was checked : {summary}")
        for finding in key_findings:
            print(f"  - {finding}")
        print("Next steps:")
        for suggestion in suggestions:
            print(f"  - {suggestion}")
        print()
        print("READ-ONLY SKILL - NO CHANGES WERE MADE")
        print(f"\nSTATUS: {STATUS_OK}")
        print("NEXT_ACTION: declare the UID as auto-derived via sts "
              "get-caller-identity in the final report, then run "
              "icp_filing_check.py in the mode the request needs "
              f"({STATUS_FAIL} is returned by this script only through a "
              "non-zero exit when identity cannot be verified).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
