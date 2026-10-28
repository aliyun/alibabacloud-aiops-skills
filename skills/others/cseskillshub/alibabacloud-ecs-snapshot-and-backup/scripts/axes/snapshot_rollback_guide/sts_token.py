#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
===================================================
SECURITY: Runs the single STS identity query (plugin-mode command
get-caller-identity) through the shared CLI layer to verify WHO the current
credential belongs to. Performs NO explicit credential handling: it never
reads, prompts for, prints, caches or forwards an AccessKey ID / SecretKey /
STS token. Authentication is resolved exclusively by the aliyun CLI default
credential chain (environment or ~/.aliyun/config.json).

The AccountId it returns is used ONLY as a local traceability label in the
report ("which account was queried"), never as an input to any other call.

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
# --- end hygiene

def get_caller_identity(profile: str | None = None) -> dict:
    """Return the caller identity; exit(1) with guidance when unavailable."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] identity check failed: {e}\n"
            "[ERROR] The default credential chain is not usable. Guide the "
            "user to run `aliyun configure`; never ask for or pass keys "
            "manually.",
            file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the active aliyun CLI identity via the STS "
                    "caller-identity query (no credentials are handled)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    uid = str(identity.get("AccountId") or "")
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")

    if args.json:
        print(json.dumps({
            "uid": uid,
            "arn": arn,
            "identity_type": identity_type,
            "summary": ("Identity verified through the default credential "
                        f"chain; account UID {uid}."),
        }, indent=2))
    else:
        print("=" * 64)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 64)
        print(f"  AccountId (UID) : {uid or '(not reported)'}")
        print(f"  Arn             : {arn or '(not reported)'}")
        print(f"  IdentityType    : {identity_type}")
        print("=" * 64)
        print("\nSummary")
        print("-------")
        print("What was checked : the identity attached to the configured "
              "Alibaba Cloud CLI credential.")
        print(f"Key finding      : account UID {uid or '(unavailable)'} "
              f"(type {identity_type}). All rollback-readiness queries run "
              "by this skill cover THIS account only.")
        print("Next step        : confirm this is the account owning the "
              "instance/disk in question, then run "
              "rollback_readiness.py assess.")

    if not uid:
        print("\nSTATUS: DEGRADED")
        print("NEXT_ACTION: report that the account UID is unavailable and "
              "proceed with explicit region/instance inputs only")
        sys.exit(0)
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run rollback_readiness.py assess for the target "
          "region and instance/disk")


if __name__ == "__main__":
    main()
