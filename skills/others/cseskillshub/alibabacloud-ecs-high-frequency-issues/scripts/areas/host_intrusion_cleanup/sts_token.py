#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification helper
====================================================
SECURITY: This script only calls STS GetCallerIdentity to confirm who the
active aliyun CLI credential is. It performs no explicit credential
handling: it never reads, prints, caches or passes any AccessKey / Secret /
token, and authentication is resolved exclusively by the CLI default
credential chain. The AccountId it returns is used only as a traceability
label for reports.

Usage:
  python3 scripts/areas/host_intrusion_cleanup/sts_token.py            # human-readable
  python3 scripts/areas/host_intrusion_cleanup/sts_token.py --json     # machine-readable
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
    """Call STS GetCallerIdentity; exit with guidance when it fails."""
    _cli.check_cli_available()
    try:
        return _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        print("[ERROR] get-caller-identity failed: %s" % e, file=sys.stderr)
        print("[ERROR] The default credential chain is not usable. Next "
              "step: run `aliyun sts get-caller-identity` (or fix the injected profile); "
              "never pass credentials on any command line.", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: Fix CLI credentials via `aliyun sts get-caller-identity`, "
              "then re-run this pre-check. Do not ask the customer for "
              "AK/SK values.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the active aliyun CLI identity via STS "
                    "GetCallerIdentity (evidence pre-check)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(profile=args.profile)
    account_id = str(identity.get("AccountId") or "")
    arn = _cli.mask_credentials(str(identity.get("Arn") or ""))
    identity_type = str(identity.get("IdentityType") or "Unknown")

    status = "OK" if account_id else "DEGRADED"
    if status == "OK":
        summary = (
            "Verified the account behind the active CLI credential. Account "
            "UID %s (type %s). Every query and gated operation this skill "
            "runs is scoped to this account only; an empty result proves "
            "absence inside this account, not globally."
            % (account_id, identity_type)
        )
        next_action = ("Proceed with scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py "
                       "for the instance in question.")
    else:
        summary = ("STS GetCallerIdentity answered but carried no AccountId; "
                   "identity could not be confirmed.")
        next_action = ("Re-run with --profile <name> or repair the default "
                       "credential chain via `aliyun sts get-caller-identity`.")

    if args.json:
        print(json.dumps({
            "account_id": account_id,
            "identity_type": identity_type,
            "arn": arn,
            "summary": summary,
            "status": status,
            "next_action": next_action,
            "session_id": _cli.session_id(),
        }, indent=2, ensure_ascii=False))
    else:
        print("== Caller identity ==")
        print("  AccountId     : %s" % (account_id or "(missing)"))
        print("  Identity type : %s" % identity_type)
        print("  Arn           : %s" % arn)
        print()
        print("Summary:")
        print("  " + summary)
        print()
        print("STATUS: %s" % status)
        print("NEXT_ACTION: %s" % next_action)

    sys.exit(0 if status == "OK" else 1)


if __name__ == "__main__":
    main()
