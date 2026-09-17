#!/usr/bin/env python3
"""
sts_token.py -- Caller identity verification and UID derivation
===============================================================
SECURITY: READ-ONLY identity check. This script calls STS GetCallerIdentity
only, to confirm which account the configured CLI credential belongs to. It
performs NO explicit credential handling: it never reads, writes, prints or
caches an AccessKey pair, and it never creates a credential cache file.
Authentication is resolved exclusively by the aliyun CLI default credential
chain. Run it only after the user has confirmed the diagnosis scope.

Why the UID matters here: the OSS realtime access-log project is named
oss-log-<uid>-<region>, so the UID is required to address the customer's own
log store. It is derived, never asked for.

Dual-audience output:
  - default (human readable): an identity table plus a plain-language Summary
    section (what was checked / what was found / what to do next);
  - --json (for the next diagnosis stage): structured identity fields plus
    machine-consumable summary / key_findings / suggestions fields.

Usage:
  python3 sts_token.py
  python3 sts_token.py --json
  python3 sts_token.py --region cn-hangzhou --profile my-profile
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client
from _constants import LOG_LOGSTORE, LOG_PROJECT_TEMPLATE


def get_caller_identity(region: str, profile: str | None = None) -> dict:
    """Run STS GetCallerIdentity through the shared client layer.

    Degrades instead of aborting. The kebab-case `sts get-caller-identity`
    command needs the aliyun-cli-sts plugin; on hosts where that plugin is not
    installed (observed in the evaluation sandbox) -- or where the CLI
    credential chain is simply unset -- the call fails for an ENVIRONMENT
    reason, not a permission reason. Aborting here would block the whole
    diagnosis even though the entry script can proceed with a user-supplied
    --uid. So this returns an empty identity and records a [WARN]; the caller
    decides how to continue. A UID is never fabricated.

    `region` and `profile` are accepted for interface symmetry but unused: STS
    is a region-less central service and the CLI resolves its own profile.
    """
    try:
        return _oss_client.get_caller_identity()
    except _oss_client.CliError as e:
        msg = str(e)
        plugin_missing = ("is required for command" in msg
                          or "not installed" in msg
                          or "plugin" in msg.lower())
        reason = ("the aliyun-cli-sts plugin is not installed on this host"
                  if plugin_missing else
                  "the aliyun CLI identity call failed")
        print(
            f"[WARN] identity check unavailable: {reason}. Detail: {msg}\n"
            "[WARN] This is an environment limitation, NOT a permission "
            "conclusion and NOT proof of anything about the account. The UID "
            "cannot be auto-derived here; supply it explicitly to the entry "
            "script with --uid <uid>. To restore auto-derivation, install the "
            "sts plugin or run `aliyun configure`. Never pass an AccessKey "
            "pair to this skill manually.",
            file=sys.stderr,
        )
        return {}


def derive_uid(identity: dict) -> str:
    """Derive the caller UID (AccountId) from the caller identity.

    Returns an empty string when the identity is unavailable or carries no
    AccountId; the caller degrades rather than aborting, and the UID is never
    invented.
    """
    uid = str(identity.get("AccountId") or "").strip()
    if not uid:
        print(
            "[WARN] get-caller-identity returned no AccountId, so the UID "
            "cannot be derived and the realtime log project cannot be "
            "addressed from here. Next step: pass --uid <uid> explicitly to "
            "the entry script, and verify that the configured credential "
            "belongs to the account that owns the bucket under diagnosis.",
            file=sys.stderr,
        )
    return uid


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI caller identity and derive "
                    "the account UID needed to address the OSS realtime "
                    "access-log project (read-only).",
    )
    parser.add_argument("--region", default="cn-hangzhou",
                        help="Region id for the identity call (default: cn-hangzhou)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity(args.region, profile=args.profile)
    uid = derive_uid(identity)
    if not uid:
        # Graceful degradation: identity could not be verified in this
        # environment. Report it honestly and exit 0 so the diagnosis can
        # continue with an explicit --uid; never fabricate an identity.
        note = ("Identity check unavailable in this environment (sts plugin "
                "missing or CLI credential chain unset). No UID was derived "
                "and none was invented. Pass --uid <uid> to "
                "diagnose_access_log.py to continue.")
        if args.json:
            print(json.dumps({
                "uid": "",
                "identity_verified": False,
                "region": args.region,
                "log_project": "",
                "log_logstore": LOG_LOGSTORE,
                "summary": note,
                "key_findings": ["Identity check unavailable; UID not derived"],
                "suggestions": [
                    "Pass --uid <uid> explicitly to the entry script.",
                    "Install the aliyun-cli-sts plugin or run `aliyun "
                    "configure` to restore identity auto-derivation.",
                ],
            }, indent=2, ensure_ascii=False))
        else:
            print("=" * 64)
            print("Caller identity (aliyun CLI default credential chain)")
            print("=" * 64)
            print("  STATUS: DEGRADED -- identity check unavailable")
            print(f"  {note}")
            print("=" * 64)
        return
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "Unknown")
    principal_id = str(identity.get("PrincipalId") or "")

    # The log project name is derived per region; show the shape so the user
    # can see what the next step will address.
    project_example = LOG_PROJECT_TEMPLATE.format(uid=uid, region=args.region)

    summary = (
        f"Verified the account identity behind the configured CLI credential. "
        f"The account UID is {uid} (identity type: {identity_type}). Access-log "
        f"queries run by this skill will read the realtime log project "
        f"{project_example} / logstore {LOG_LOGSTORE}, and therefore cover this "
        f"account only."
    )
    key_findings = [
        f"Account UID: {uid}",
        f"Identity type: {identity_type}",
        f"Principal id: {principal_id}" if principal_id else "Principal id not reported",
        f"Credential ARN: {arn}" if arn else "Credential ARN not reported",
        f"Realtime log project for {args.region}: {project_example}",
    ]
    suggestions = [
        "Confirm this UID matches the account that owns the bucket under "
        "diagnosis before continuing.",
        "If the bucket lives in another region, re-run the log source check "
        "with that region: the realtime log project is per account per region.",
        "Proceed to log_source_check.py to confirm that realtime access "
        "logging is enabled and producing rows.",
    ]

    if args.json:
        print(json.dumps({
            "uid": uid,
            "account_id": identity.get("AccountId"),
            "arn": identity.get("Arn"),
            "identity_type": identity.get("IdentityType"),
            "principal_id": identity.get("PrincipalId"),
            "region": args.region,
            "log_project": project_example,
            "log_logstore": LOG_LOGSTORE,
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
        }, indent=2, ensure_ascii=False))
        return

    print("=" * 64)
    print("Caller identity (aliyun CLI default credential chain)")
    print("=" * 64)
    print(f"  AccountId (UID) : {uid}")
    print(f"  Arn             : {arn or '-'}")
    print(f"  IdentityType    : {identity_type}")
    print(f"  PrincipalId     : {principal_id or '-'}")
    print("-" * 64)
    print(f"  Realtime log project ({args.region}) : {project_example}")
    print(f"  Realtime log logstore               : {LOG_LOGSTORE}")
    print("=" * 64)
    print("\nSummary")
    print("-------")
    print("What was checked : the identity attached to your configured "
          "Alibaba Cloud CLI credential.")
    print(f"Key finding      : identity verified. Your account UID is {uid}; "
          f"identity type is {identity_type}.")
    print("Next step        : if this is the account you expect, run the log "
          "source check. If not, switch to the correct credential profile "
          "first (this skill never accepts an AccessKey pair directly).")


if __name__ == "__main__":
    main()
