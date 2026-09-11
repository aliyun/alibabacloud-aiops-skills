#!/usr/bin/env python3
"""Mute or unmute an SLS rule via GetAlert/UpdateAlert, then verify the change.

Usage:
  python3 scripts/mute_alert.py --project PROJECT --alert-name ID --mute-until UNIX_SECONDS --user-agent UA
  python3 scripts/mute_alert.py --project PROJECT --alert-name ID --unmute --user-agent UA
Optional: --region REGION --endpoint ENDPOINT --profile PROFILE
"""

import argparse
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def call_cli(args, action, body=None):
    command = [
        "aliyun", "sls", action,
        "--project", args.project, "--alertName", args.alert_name,
        "--user-agent", args.user_agent,
    ]
    for option in ("region", "endpoint", "profile"):
        value = getattr(args, option)
        if value:
            command.extend(["--" + option, value])
    if body is not None:
        command.extend(["--body", json.dumps(body, ensure_ascii=False)])
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        # Do not print the command, which contains the complete rule body.
        raise RuntimeError("{} failed (exit {}): {}".format(
            action, result.returncode, result.stderr.strip()))
    if action == "GetAlert":
        try:
            rule = json.loads(result.stdout)
        except ValueError as exc:
            raise RuntimeError("GetAlert returned invalid JSON") from exc
        if not isinstance(rule, dict) or not isinstance(rule.get("configuration"), dict):
            raise RuntimeError("GetAlert must return a rule with a configuration object")
        if rule.get("name") != args.alert_name:
            raise RuntimeError("GetAlert returned a different rule ID")
        if not isinstance(rule.get("schedule"), dict) or not isinstance(rule.get("displayName"), str):
            raise RuntimeError("GetAlert response is missing schedule or displayName")
        return rule


def update_mute(args):
    before = call_cli(args, "GetAlert")
    # Only send UpdateAlert body fields; identity/status/timestamps are read-only.
    body = {key: copy.deepcopy(before[key]) for key in
            ("displayName", "description", "schedule", "configuration") if key in before}
    configuration = body["configuration"]
    if args.unmute:
        if "muteUntil" not in configuration:
            return {"changed": False, "muted": False, "verified": True}
        del configuration["muteUntil"]
    else:
        if args.mute_until <= time.time():
            raise RuntimeError("mute end time has passed; resolve a new end time before updating")
        configuration["muteUntil"] = args.mute_until

    call_cli(args, "UpdateAlert", body)
    try:
        after = call_cli(args, "GetAlert")
    except (OSError, RuntimeError) as exc:
        raise RuntimeError("UpdateAlert succeeded but read-back failed: {}".format(exc)) from exc
    mismatches = [key for key, value in body.items() if after.get(key) != value]
    mismatches.extend(key for key in ("name", "status") if after.get(key) != before.get(key))
    if mismatches:
        raise RuntimeError("UpdateAlert succeeded but read-back differs: " + ", ".join(mismatches))
    result = {"changed": True, "muted": not args.unmute, "verified": True}
    if not args.unmute:
        result["muteUntil"] = args.mute_until
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True)
    parser.add_argument("--alert-name", required=True, help="Stable rule ID")
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--mute-until", type=int, help="Future Unix timestamp in seconds")
    operation.add_argument("--unmute", action="store_true", help="Remove configuration.muteUntil")
    parser.add_argument("--user-agent", required=True, help="Resolved skill User-Agent from SKILL.md")
    for option in ("region", "endpoint", "profile"):
        parser.add_argument("--" + option, help="Optional Aliyun CLI override")
    args = parser.parse_args(argv)
    # A timestamp beyond year 9999 is invalid and usually indicates milliseconds.
    if args.mute_until is not None and not time.time() < args.mute_until <= 253402300799:
        parser.error("--mute-until must be a future Unix timestamp in seconds, not milliseconds")
    try:
        manifest = Path(__file__).resolve().parent.parent / "references" / "manifest.json"
        metadata = json.loads(manifest.read_text())
        version = metadata.get("version") if isinstance(metadata, dict) else None
        if not isinstance(version, str) or not version.strip():
            raise ValueError("manifest must contain a non-empty string version")
        pattern = (r"AlibabaCloud-Agent-Skills/alibabacloud-sls-alerting/[0-9a-f]{32} "
                   r"skill-version/" + re.escape(version))
        if not re.fullmatch(pattern, args.user_agent):
            raise ValueError("--user-agent must contain this skill's session ID and manifest version")
        result = update_mute(args)
        result.update(project=args.project, alertName=args.alert_name)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
