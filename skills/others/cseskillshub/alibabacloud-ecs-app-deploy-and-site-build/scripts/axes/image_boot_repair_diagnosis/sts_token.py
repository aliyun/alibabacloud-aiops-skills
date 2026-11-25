#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: READ-ONLY identity check. Calls STS GetCallerIdentity (CLI plugin
mode, lowercase-hyphenated command) to verify who the current aliyun CLI
session is. Performs NO explicit credential handling: it never reads, writes,
caches or prints any AccessKey / Secret / token; authentication is resolved
exclusively by the aliyun CLI default credential chain.

The derived account UID is used ONLY as a traceability label (declared in
every report), never for access decisions.

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
    """Run the identity check through the shared CLI layer; on failure
    print guidance (configure the default chain -- never pass AK/SK here)
    and exit non-zero."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] identity check failed: {e}\n"
            "[ERROR] Next step: verify the aliyun CLI default credential "
            "chain (run `aliyun configure`); never pass credential values "
            "to this skill.",
            file=sys.stderr,
        )
        sys.exit(1)


def derive_uid(identity: dict) -> str:
    """Extract the AccountId (UID) label from the caller identity."""
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print(
            "[ERROR] the identity response carried no AccountId; the UID "
            "label cannot be derived.",
            file=sys.stderr,
        )
        sys.exit(1)
    return uid


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI caller identity via STS "
                    "GetCallerIdentity (read-only)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    uid = derive_uid(identity)
    arn = _cli._mask_credentials(str(identity.get("Arn") or ""))
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (
        f"Verified the account behind the configured CLI credential. UID "
        f"{uid} (type {identity_type}). Every read-only query issued by "
        f"this skill covers THIS account only; an empty result outside it "
        f"is an account-scope limit, not proof of absence."
    )
    payload = {
        "uid": uid,
        "arn": arn,
        "identity_type": identity_type,
        "session_id": _cli.session_id(),
        "user_agent": _cli.user_agent(),
        "summary": summary,
        "suggestions": [
            "Confirm this UID is the account owning the image / instance "
            "before running the diagnosis entry script.",
            "Proceed to scripts/image_boot_repair_diagnosis.py.",
        ],
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print(f"  AccountId (UID) : {uid}")
        print(f"  Arn             : {arn}")
        print(f"  IdentityType    : {identity_type}")
        print(f"  Session-Id      : {payload['session_id']}")
        print(f"  User-Agent      : {payload['user_agent']}")
        print("\nSummary\n-------")
        print(summary)
        for s in payload["suggestions"]:
            print(f"  - {s}")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/image_boot_repair_diagnosis.py triage "
          "for the target region (or analyze-log / analyze-report on the "
          "text the customer pasted)")


if __name__ == "__main__":
    main()
