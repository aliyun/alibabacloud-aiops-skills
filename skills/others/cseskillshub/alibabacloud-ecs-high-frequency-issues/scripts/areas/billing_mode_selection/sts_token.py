#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: READ-ONLY identity check. This script only calls STS
GetCallerIdentity (via `aliyun sts get-caller-identity`, plugin mode) to
verify who the current aliyun CLI session is. It performs NO explicit
credential handling, never reads or writes any AccessKey / Secret, and never
writes any credential cache file. Authentication is resolved exclusively by
the aliyun CLI default credential chain.

Dual-audience output:
  - Default (human-readable): an identity table plus a plain-language
    "Summary" section (what was checked / what was found / what to do next).
  - --json (for Agents): structured identity fields plus machine-consumable
    "summary" / "status" / "next_action" fields.

Usage:
  python3 sts_token.py
  python3 sts_token.py --json
  python3 sts_token.py --profile <name> --json
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
    """Run STS GetCallerIdentity through the shared CLI layer and return the
    parsed response. Exits with guidance when the call fails."""
    try:
        _cli.check_cli_available()
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] get-caller-identity failed: {e}\n"
            "[ERROR] Next step: configure the aliyun CLI default credential "
            "chain (run `aliyun sts get-caller-identity`); credentials are always resolved "
            "by the chain itself -- never pass them to this script.",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the current aliyun CLI caller identity via STS "
            "GetCallerIdentity (read-only identity check)"
        ),
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    if not uid:
        print(
            "[ERROR] get-caller-identity returned no AccountId. Next step: "
            "verify the configured credential belongs to the intended account.",
            file=sys.stderr,
        )
        print("STATUS: FAIL")
        print("NEXT_ACTION: Re-check the CLI credential configuration; "
              "then re-run this script.")
        sys.exit(1)

    summary = (
        "Verified the account identity behind the configured CLI credential. "
        f"The account UID is {uid} (identity type: {identity_type}). All ECS "
        "read-only queries run by this skill will cover this account only, "
        "and per-region -- instances outside the queried region are not "
        "visible in a single run."
    )

    if args.json:
        print(json.dumps({
            "uid": uid,
            "arn": arn,
            "identity_type": identity_type,
            "session_id": _cli.session_id(),
            "summary": summary,
            "status": "OK",
            "next_action": "Proceed with scripts/areas/billing_mode_selection/billing_mode_advisor.py.",
        }, ensure_ascii=False, indent=2))
    else:
        print("=" * 70)
        print(" Caller identity (read-only check)")
        print("=" * 70)
        print(f"  Account UID : {uid}")
        print(f"  Identity    : {identity_type}")
        print(f"  ARN         : {arn}")
        print(f"  Session-id  : {_cli.session_id()}")
        print("\nSummary:")
        print(f"  {summary}")
        print("\nSTATUS: OK")
        print("NEXT_ACTION: Proceed with scripts/areas/billing_mode_selection/billing_mode_advisor.py.")


if __name__ == "__main__":
    main()
