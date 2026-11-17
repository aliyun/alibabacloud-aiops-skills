#!/usr/bin/env python3
"""
sts_token.py -- caller identity pre-check helper
================================================
SECURITY: Query-only identity check. Runs the plugin-mode command
`aliyun sts get-caller-identity` once through the shared CLI layer to verify
which account the default credential chain currently resolves to, and derives
the account UID for traceability. It performs NO explicit credential
handling: it never reads, prompts for, caches, prints or forwards any
AccessKey ID / Secret / STS token.

Usage:
  python3 scripts/areas/spec_change_purchase/sts_token.py
  python3 scripts/areas/spec_change_purchase/sts_token.py --json
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
    """Run the identity query; on failure print the remediation guidance and
    exit non-zero (the agent must relay it instead of continuing)."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as err:
        print(f"[ERROR] identity check failed (Code: "
              f"{getattr(err, 'code', '') or 'NoPermission'}): {err}",
              file=sys.stderr)
        print("[ERROR] remediation: the skill authenticates ONLY through the "
              "aliyun CLI default credential chain. Run `aliyun sts get-caller-identity` "
              "and retry. Do not pass credential values explicitly; if the "
              "failure reads NoPermission or ImplicitDeny, attach the "
              "minimal policy in references/ram-policies.md.", file=sys.stderr)
        sys.exit(1)


def derive_uid(identity):
    uid = _mask_pii(str(identity.get("AccountId") or "").strip())
    if not uid:
        print("[ERROR] the identity response carried no AccountId; cannot "
              "derive the account UID tag. Verify the credential belongs to "
              "the intended account.", file=sys.stderr)
        sys.exit(1)
    return uid


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI caller identity via the "
                    "plugin-mode command aliyun sts get-caller-identity "
                    "(query-only)",
    )
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    identity = get_caller_identity(profile=args.profile)
    uid = derive_uid(identity)
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    summary = (f"Caller identity verified: account UID {uid} "
               f"(identity type {identity_type}). All cloud readings this "
               f"skill returns cover this account only.")
    key_findings = [
        f"Account UID: {uid}",
        f"Identity type: {identity_type}",
        f"Credential ARN: {arn}" if arn else "Credential ARN not reported",
    ]
    suggestions = [
        "Confirm this UID is the account whose ECS instances are being "
        "assessed before continuing.",
        "Proceed to scripts/areas/spec_change_purchase/assess_spec_change.py with the instance id "
        "and/or the verbatim error string.",
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
        print("=" * 72)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 72)
        for line in key_findings:
            print(f"  {line}")
        print("\nSummary")
        print("-------")
        print(summary)
        print("Next step       : if this is the expected account, run "
              "scripts/areas/spec_change_purchase/assess_spec_change.py; if not, switch the CLI "
              "profile first.")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/areas/spec_change_purchase/assess_spec_change.py with the customer "
            "inputs; relay the mandatory notices with every change "
            "conclusion")


if __name__ == "__main__":
    main()
