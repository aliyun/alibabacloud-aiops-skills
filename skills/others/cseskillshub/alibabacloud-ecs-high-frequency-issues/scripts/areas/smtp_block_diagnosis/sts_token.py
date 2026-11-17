#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: this script performs no state change of any kind. It only calls
STS GetCallerIdentity (via the shared _cli layer) to verify WHO the current
aliyun CLI session is, so the diagnosis can (a) fail fast when the default
credential chain is broken and (b) label every report with the account it
ran against, and (c) surface the classic sub-account permission-gap case of
port-25 unblock applications (a RAM user that cannot view or submit them --
see references/smtp-block-diagnosis__unblock-application-path.md).

It performs NO explicit credential handling: no AccessKey ID / Secret /
token is ever read, written, cached, or printed here; authentication is
resolved exclusively by the aliyun CLI default credential chain.

Dual-audience output:
  - default: an identity table + plain-language Summary;
  - --json:  structured fields (uid / account_id / arn / identity_type /
             permission_hint / summary / next_action).

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
    """Return the raw GetCallerIdentity response; exit(1) with guidance on
    failure (missing/broken default credential chain)."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] get-caller-identity failed: {e}\n"
            "[ERROR] Next step: configure the aliyun CLI default credential "
            "chain (`aliyun sts get-caller-identity`); never pass keys or tokens to this "
            "script.",
            file=sys.stderr,
        )
        sys.exit(1)


def permission_hint(identity_type: str) -> str:
    """Ticket-evidence-based hint: RAM sub-accounts frequently cannot view
    the port-25 block state or submit unblock applications."""
    if identity_type == "SubUser":
        return ("Sub-account in use. If console views or the port-25 "
                "unblock application are denied for this principal, the "
                "gap is RAM authorization, not the mail path: hand off to "
                "the RAM policy diagnosis flow (references/"
                "handoff-boundaries.md).")
    if identity_type == "AssumedRole":
        return ("Assumed role in use: results reflect only this role's "
                "grants and its account scope; an empty finding is not "
                "proof of 'nothing wrong' across the whole account.")
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Verify the current aliyun CLI caller identity via STS "
                     "GetCallerIdentity (no state change)"),
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")
    hint = permission_hint(identity_type)

    if not uid:
        print("[ERROR] get-caller-identity returned no AccountId; cannot "
              "label the diagnosis with an account. Verify the configured "
              "credential belongs to the intended account.", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: switch to the correct credential profile, then "
              "re-run")
        sys.exit(1)

    summary = (
        f"Verified the account behind the configured CLI credential. The "
        f"account UID is {uid} (identity type: {identity_type}). All "
        f"queries this skill runs cover THIS account only."
    )
    next_action = (
        "proceed with scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py once the user has "
        "confirmed the diagnostic scope (instance id + region)"
    )

    if args.json:
        print(json.dumps({
            "uid": uid,
            "account_id": uid,
            "arn": arn,
            "identity_type": identity_type,
            "permission_hint": hint,
            "summary": summary,
            "next_action": next_action,
            "status": "OK",
        }, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print(f"  AccountId (UID) : {uid}")
        print(f"  Arn             : {arn}")
        print(f"  IdentityType    : {identity_type}")
        if hint:
            print(f"  Hint            : {hint}")
        print("=" * 60)
        print("\nSummary")
        print("-------")
        print(f"What was checked : {summary}")
        print("Next step        : " + next_action)
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py for the "
            "target instance after user confirmation of scope")


if __name__ == "__main__":
    main()
