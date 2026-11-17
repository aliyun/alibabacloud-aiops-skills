#!/usr/bin/env python3
"""
sts_token.py -- Caller identity pre-check for the ECS remote-connection
entry triage skill.

SECURITY: READ-ONLY. This script only runs the STS GetCallerIdentity query
(plugin-mode command `aliyun sts get-caller-identity` via the shared CLI
layer) to verify WHO the current credential belongs to. It performs no
explicit credential handling: no reading, printing, caching or passing of
any AK/SK/session token. The credential chain is resolved automatically by
the aliyun CLI (environment or local CLI config profile). On failure it
guides `aliyun sts get-caller-identity` -- it never asks the user for secret values.

Purpose in this skill: confirm the operator is acting on the intended
account before any ECS evidence query, and derive the UID traceability
label (auto-fill first, ask second -- always declare the derivation).

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

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the aliyun CLI caller identity via the read-only STS "
            "GetCallerIdentity query and derive the UID traceability label."
        ),
    )
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    _cli.check_cli_available()
    try:
        identity = _cli.get_caller_identity(profile=args.profile)
    except _cli.CliError as e:
        print(
            f"[ERROR] caller identity check failed: {e}\n"
            "[ERROR] Next step: ensure the aliyun CLI default credential "
            "chain is configured (`aliyun sts get-caller-identity`); never pass secret "
            "values on the command line or through this skill.",
            file=sys.stderr,
        )
        print("STATUS: FAIL")
        print("NEXT_ACTION: configure the CLI default credential chain, "
              "then re-run this identity pre-check")
        sys.exit(1)

    uid = identity["uid"]
    if not uid:
        print("[ERROR] identity response carried no account id; cannot "
              "label the account.", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: verify the credential belongs to the intended "
              "account before running the triage entry script")
        sys.exit(1)

    summary = (
        f"Verified the account behind the configured CLI credential. "
        f"Account UID (auto-derived traceability label): {uid}; identity "
        f"type: {identity['identity_type']}. All ECS evidence queries run "
        f"by this skill cover THIS account and the given region only."
    )
    next_action = (
        "run ecs_remote_connection_triage.py with the customer's instance "
        "id or public IP and region"
    )

    if args.json:
        print(json.dumps({
            "uid": uid,
            "arn": identity["arn"],
            "identity_type": identity["identity_type"],
            "summary": summary,
            "status": "OK",
            "next_action": next_action,
        }, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print(f"  AccountId (UID) : {uid}")
        print(f"  Arn             : {identity['arn'] or 'not reported'}")
        print(f"  IdentityType    : {identity['identity_type']}")
        print("-" * 60)
        print("Summary")
        print("-------")
        print(summary)
    print("\nSTATUS: OK")
    print(f"NEXT_ACTION: {next_action}")


if __name__ == "__main__":
    main()
