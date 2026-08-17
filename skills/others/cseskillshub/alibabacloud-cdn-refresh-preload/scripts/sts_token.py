#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sts_token.py — Caller identity verification helper

Confirms who the current aliyun CLI session is (account / RAM user / assumed
role) via the public STS API `GetCallerIdentity`, invoked through the aliyun
CLI in plugin mode. All authentication is resolved by the CLI itself via its
default chain (CLI config or platform-injected environment); this script
performs no explicit auth handling and never reads or writes any secrets.

Capabilities:
  - Print the caller identity (AccountId / Arn / IdentityType)
  - Auto-derive the caller UID (AccountId) for downstream tooling
  - Detect whether the caller already holds a session of the target diagnosis
    role (evaluation sandboxes pre-inject such a session); in that case no
    further role-related action is needed — the CLI session is already usable.

Usage:
  python3 sts_token.py
  python3 sts_token.py --json
  python3 sts_token.py --role-name cseesadiagnosticrole --json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from typing import Dict, Any

# Per-run session id for platform-level tracing (Observability)
_SESSION_ID = uuid.uuid4().hex
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-cdn-refresh-preload/{_SESSION_ID}"

DEFAULT_ROLE_NAME = "cseesadiagnosticrole"

# Region env aliases (platform-injected sandboxes may set any of these).
_REGION_ENV_KEYS = (
    "ALIBABA_CLOUD_REGION_ID",
    "ALIBABACLOUD_REGION_ID",
    "ALICLOUD_REGION",
    "REGION_ID",
)
DEFAULT_REGION = "cn-hangzhou"


def _resolve_region() -> str:
    """Resolve the region for the STS call.

    Chain: env aliases -> aliyun CLI config (current profile) -> cn-hangzhou
    fallback. Evaluation sandboxes may have no config.json and only
    env-injected credentials; passing --region avoids 'region can't be empty'.
    """
    for key in _REGION_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return value

    config_path = os.path.join(os.path.expanduser("~"), ".aliyun", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
        current = config.get("current") or ""
        for profile in config.get("profiles") or []:
            if profile.get("name") == current:
                region = str(profile.get("region_id") or "").strip()
                if region:
                    return region
    except (OSError, ValueError):
        pass

    return DEFAULT_REGION


def get_caller_identity() -> Dict[str, Any]:
    """Run `aliyun sts get-caller-identity` (plugin mode) and return the parsed
    response. Exits with a clear error when the call fails."""
    if shutil.which('aliyun') is None:
        print("Error: aliyun CLI not found on PATH. Install it and run 'aliyun configure'.", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "aliyun", "sts", "get-caller-identity",
        "--user-agent", _USER_AGENT,
        # Defensive: keeps env-only credential sandboxes (no config.json)
        # working; harmless when the CLI resolves the region itself.
        "--region", _resolve_region(),
    ]
    try:
        # stdin=DEVNULL: never hang on interactive CLI prompts (e.g. plugin
        # auto-install questions); fail fast with a timeout/error instead.
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        print("Error: get-caller-identity timed out after 60s. Retry or check network.", file=sys.stderr)
        sys.exit(1)

    data: Dict[str, Any] = {}
    for chunk in (proc.stdout, proc.stderr):
        text = (chunk or "").strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                data = parsed
                break
        except json.JSONDecodeError:
            continue

    if proc.returncode != 0:
        msg = data.get("Message") or (proc.stderr or proc.stdout or "").strip()[:500]
        print(
            f"Error: get-caller-identity failed (exit={proc.returncode}): {msg}\n"
            "Check that the aliyun CLI default chain is configured.",
            file=sys.stderr,
        )
        sys.exit(1)

    return data


def derive_uid_from_caller_identity() -> str:
    """Derive the caller UID (AccountId) from the caller identity."""
    data = get_caller_identity()
    uid = str(data.get("AccountId") or "").strip()
    if not uid:
        print(
            "Error: get-caller-identity returned no AccountId; cannot derive UID.",
            file=sys.stderr,
        )
        sys.exit(1)
    return uid


def already_assumed_target_role(identity: Dict[str, Any], role_name: str) -> bool:
    """True when the caller is already a session of the target role.

    Evaluation sandboxes pre-inject a session that has already assumed the
    diagnosis role; the CLI session is then directly usable for queries.
    Arn shape: acs:sts::<uid>:assumed-role/<role-name>/<session-name>
    RAM role names are case-sensitive, so the match is exact (no lower()).
    """
    arn = str(identity.get("Arn") or "")
    return f":assumed-role/{role_name}/" in arn


def main():
    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI caller identity via STS GetCallerIdentity",
    )
    parser.add_argument("--role-name", default=DEFAULT_ROLE_NAME,
                        help="Diagnosis role name used for the nested-session check "
                             "(default: cseesadiagnosticrole)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    identity = get_caller_identity()
    assumed = already_assumed_target_role(identity, args.role_name)
    if assumed:
        print(
            f"[INFO] caller already assumed role {args.role_name}; "
            "the current CLI session is directly reusable, no further role action needed",
            file=sys.stderr,
        )

    if args.json:
        print(json.dumps({
            "account_id": identity.get("AccountId"),
            "arn": identity.get("Arn"),
            "identity_type": identity.get("IdentityType"),
            "assumed_target_role": assumed,
            "role_name": args.role_name,
        }, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default chain)")
        print("=" * 60)
        print(f"  AccountId    : {identity.get('AccountId')}")
        print(f"  Arn          : {identity.get('Arn')}")
        print(f"  IdentityType : {identity.get('IdentityType')}")
        print(f"  Assumed target role ({args.role_name}): {'yes' if assumed else 'no'}")
        print("=" * 60)


if __name__ == "__main__":
    main()
