#!/usr/bin/env python3
"""
sts_token.py -- caller identity verification helper
===================================================
SECURITY: READ-ONLY. This script performs exactly one thing: it asks STS
GetCallerIdentity who the current aliyun CLI session is, and derives the
account UID used as a traceability label. It performs NO explicit credential
handling -- it never reads, prints, caches or asks for an access key, a secret
or a session token, and it writes no credential file. Authentication is
resolved exclusively by the aliyun CLI default credential chain.

Why this skill needs it
-----------------------
Every fact this skill reports is scoped to the account behind the current
credential and to the regions actually queried. The identity check makes that
scope explicit in the report instead of letting the reader assume a fleet-wide
answer, and it produces a clean failure with `aliyun configure` guidance when
no credential chain exists at all.

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
from _constants import SKILL_NAME


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
    """Return the STS GetCallerIdentity response, or exit with guidance."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as err:
        print(
            f"[ERROR] {err.code or 'CredentialUnavailable'}: "
            f"could not verify the caller identity.\n"
            "[ERROR] Next step: run `aliyun configure` (or check the "
            "platform-injected credential environment) so the default "
            "credential chain resolves. Never pass an access key or secret "
            "to this script.",
            file=sys.stderr,
        )
        sys.exit(1)


def derive_uid(identity: dict) -> str:
    """Account UID (AccountId) of the caller; "" when the field is missing."""
    return str(identity.get("AccountId") or "").strip()


def build_result(identity: dict) -> dict:
    """Normalize the identity response into the skill's result contract."""
    uid = derive_uid(identity)
    return {
        "skill": SKILL_NAME,
        "account_id": uid,
        "identity_type": str(identity.get("IdentityType") or ""),
        "principal_arn": str(identity.get("Arn") or ""),
        "principal_id": str(identity.get("PrincipalId") or ""),
        "session_id": _cli.session_id(),
        "user_agent": _cli.user_agent(),
    }


def summarize(result: dict) -> tuple[str, list[str], list[str]]:
    """(summary, key findings, suggestions) -- dual-audience text."""
    uid = result["account_id"] or "unknown"
    summary = (
        f"Verified the identity behind the configured aliyun CLI credential: "
        f"account UID {uid} (identity type "
        f"{result['identity_type'] or 'unknown'}). Every instance fact this "
        f"skill reports is limited to this account and to the regions you "
        f"query."
    )
    findings = [
        f"Account UID: {uid}",
        f"Identity type: {result['identity_type'] or 'not reported'}",
        f"Principal ARN: {result['principal_arn'] or 'not reported'}",
    ]
    suggestions = [
        "If this is not the account you meant, switch the CLI profile "
        "(--profile <name>) and re-run; this skill never accepts a credential "
        "from you directly.",
        "Continue with scripts/ecs_instance_tag_metadata_check.py to read "
        "instance resource-group, tag and metadata-option facts.",
    ]
    return summary, findings, suggestions


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the aliyun CLI caller identity via sts get-caller-identity "
            "(read-only; no credential handling)"
        ),
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of the table")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    result = build_result(identity)
    summary, findings, suggestions = summarize(result)

    if args.json:
        print(json.dumps({
            **result,
            "summary": summary,
            "key_findings": findings,
            "suggestions": suggestions,
            "status": "OK" if result["account_id"] else "DEGRADED",
        }, indent=2))
    else:
        print("=" * 72)
        print(" Caller identity (aliyun CLI default credential chain)")
        print("=" * 72)
        print(f"  AccountId (UID)  : {result['account_id'] or 'not reported'}")
        print(f"  IdentityType     : {result['identity_type'] or 'not reported'}")
        print(f"  Principal ARN    : {result['principal_arn'] or 'not reported'}")
        print(f"  session-id (UA)  : {result['session_id']}")
        print("=" * 72)
        print("\nSummary")
        print(summary)
        print("\nKey findings")
        for line in findings:
            print(f"  - {line}")
        print("\nNext steps")
        for line in suggestions:
            print(f"  - {line}")

    print("\nSTATUS: " + ("OK" if result["account_id"] else "DEGRADED"))
    print("NEXT_ACTION: run scripts/ecs_instance_tag_metadata_check.py with "
          "--instance-id / --resource-group-id / --tag-key to read the "
          "ownership facts, or --question for the rule answers")


if __name__ == "__main__":
    main()
