#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_with_aliyun_creds.py — auto-inject credentials from the aliyun CLI current
profile into the subprocess environment, then exec the subcommand.

================================================================================
Purpose
================================================================================
Helper for the §1.alt external-network fallback path of the Skill
`alibabacloud-vms-smart-call-by-tts`.
It encapsulates the full pipeline:
    "read ~/.aliyun/config.json -> pick the current profile -> validate mode ->
     inject ALIBABA_CLOUD_ACCESS_KEY_ID / _SECRET / _SECURITY_TOKEN env ->
     exec the subcommand"
so that no agent has to roll an ad-hoc script (which commonly mis-reads
profiles[0], forgets the STS token, or echoes credentials into logs).

Design goal: provide agents with a one-line standard entrypoint that completes
credential injection, lowering usage friction and avoiding the common errors
introduced when each agent rolls its own implementation:

    python3 scripts/run_with_aliyun_creds.py -- \\
        python3 scripts/dyvmsapi_rpc.py SubmitIntent -P UserMessage="..."

================================================================================
Behavior
================================================================================
1. Read ~/.aliyun/config.json
2. Pick the profile referenced by the `current` field (NEVER hardcode
   profiles[0]); --profile overrides
3. Validate profile.mode in {AK, StsToken}
     - other modes (RamRoleArn / EcsRamRole / OAuth / External / ...) -> exit 3
4. Inject env:
     - all modes: ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
     - StsToken: also inject ALIBABA_CLOUD_SECURITY_TOKEN
5. Print one transparency line to stderr (no credential values):
     [run_with_aliyun_creds] using profile=<name> mode=<mode> region=<region>
6. exec the subcommand; the child's exit code is propagated as-is

[FORBIDDEN] Hard rules:
- NEVER print AK / SK / SecurityToken values to stdout / stderr / log files
- NEVER pass these values as subprocess arguments (env only)
- NEVER fall back to profiles[0] (do not read a profile not referenced by
  `current`)

================================================================================
Usage
================================================================================

# Most common: run SubmitIntent with the current profile
python3 scripts/run_with_aliyun_creds.py -- \\
    python3 scripts/dyvmsapi_rpc.py SubmitIntent -P UserMessage="Remind Mom not to wait up for dinner"

# Use a specific profile (overrides current)
python3 scripts/run_with_aliyun_creds.py --profile my-other-profile -- \\
    python3 scripts/dyvmsapi_rpc.py SubmitIntent -P UserMessage="..."

# Show which profile would be used (dry-run; does not exec the subcommand)
python3 scripts/run_with_aliyun_creds.py --print-profile

# Check whether the profile is eligible for auto-injection (mode in {AK, StsToken})
python3 scripts/run_with_aliyun_creds.py --check

================================================================================
Exit codes
================================================================================
    0      Subcommand succeeded (or --check passed / --print-profile printed OK)
    1      ~/.aliyun/config.json missing or unparsable JSON
    2      Profile not found (the name in `current` is not in `profiles`)
    3      profile.mode is outside the supported set {AK, StsToken}
    4      Profile is missing required fields
           (access_key_id / access_key_secret / sts_token)
    5      Argument error (e.g. no subcommand)
    other  Subprocess exit code (passed through)
"""
import argparse
import json
import os
import sys
from pathlib import Path

SUPPORTED_MODES = ("AK", "StsToken")
CONFIG_PATH = Path.home() / ".aliyun" / "config.json"


def load_profile(profile_name=None):
    """Read config.json and return (profile_dict, current_name)."""
    if not CONFIG_PATH.is_file():
        print(
            f"[run_with_aliyun_creds] ERROR: {CONFIG_PATH} does not exist. "
            "Please run `aliyun configure` in a terminal first to set up credentials.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(
            f"[run_with_aliyun_creds] ERROR: failed to parse {CONFIG_PATH}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    profiles = cfg.get("profiles", [])
    if not profiles:
        print(
            "[run_with_aliyun_creds] ERROR: the `profiles` array in config.json is empty.",
            file=sys.stderr,
        )
        sys.exit(2)

    name = profile_name or cfg.get("current", "default")
    prof = next((p for p in profiles if p.get("name") == name), None)
    if prof is None:
        avail = ", ".join(p.get("name", "?") for p in profiles)
        print(
            f"[run_with_aliyun_creds] ERROR: profile '{name}' not found. "
            f"Available profiles: [{avail}]. To use a different profile, pass --profile.",
            file=sys.stderr,
        )
        sys.exit(2)

    return prof, name


def validate_mode(prof, name):
    """Check that mode is in the supported set; otherwise exit 3 with guidance."""
    mode = prof.get("mode", "")
    if mode in SUPPORTED_MODES:
        return mode

    print(
        f"[run_with_aliyun_creds] ERROR: mode='{mode}' on profile '{name}' "
        f"is not in the auto-injection supported set {SUPPORTED_MODES}.\n"
        "  - Modes such as RamRoleArn / EcsRamRole / OAuth / External / "
        "CredentialsURI require obtaining temporary AK/SK/STS via STS / the "
        "metadata service / an external command before they can be used.\n"
        "  - Options:\n"
        "    a) Use the primary path (the aliyun CLI natively supports all modes), or\n"
        "    b) Run `aliyun configure --profile <name> --mode AK` to create a new "
        "AK profile and pass `--profile <name>`, or\n"
        "    c) Perform AssumeRole yourself, then manually export "
        "ALIBABA_CLOUD_ACCESS_KEY_ID / _SECRET / _SECURITY_TOKEN and invoke the "
        "script directly.",
        file=sys.stderr,
    )
    sys.exit(3)


def build_env(prof, name, mode, base_env):
    """Build the env dict with credentials injected."""
    ak = prof.get("access_key_id", "")
    sk = prof.get("access_key_secret", "")
    if not ak or not sk:
        print(
            f"[run_with_aliyun_creds] ERROR: profile '{name}' is missing "
            "access_key_id or access_key_secret. Please re-run "
            f"`aliyun configure --profile {name}`.",
            file=sys.stderr,
        )
        sys.exit(4)

    env = dict(base_env)
    env["ALIBABA_CLOUD_ACCESS_KEY_ID"] = ak
    env["ALIBABA_CLOUD_ACCESS_KEY_SECRET"] = sk

    if mode == "StsToken":
        sts = prof.get("sts_token", "")
        if not sts:
            print(
                f"[run_with_aliyun_creds] ERROR: profile '{name}' mode=StsToken "
                "but the `sts_token` field is empty / expired. Re-issue temporary "
                f"credentials, then re-run `aliyun configure --profile {name}`.",
                file=sys.stderr,
            )
            sys.exit(4)
        env["ALIBABA_CLOUD_SECURITY_TOKEN"] = sts
    else:
        # AK mode: clear any leftover STS token in the environment so the
        # downstream script does not pick it up by mistake.
        env.pop("ALIBABA_CLOUD_SECURITY_TOKEN", None)
        env.pop("ALIBABACLOUD_SECURITY_TOKEN", None)
        env.pop("ALIYUN_SECURITY_TOKEN", None)

    return env


def announce(prof, name, mode):
    """Print a single transparency line to stderr; no credential values."""
    region = prof.get("region_id", "<unset>")
    print(
        f"[run_with_aliyun_creds] using profile={name} mode={mode} region={region}",
        file=sys.stderr,
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Auto-inject credentials from the aliyun CLI current profile into "
            "the env, then exec the subcommand. Credentials are env-only and "
            "are NEVER printed."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Name of the profile to use (default: the `current` field in config.json)",
    )
    parser.add_argument(
        "--print-profile",
        action="store_true",
        help="Print the profile name / mode / region that would be used; do not exec a subcommand",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the current profile is eligible for auto-injection "
             "(mode in {AK,StsToken} and required fields present)",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="The subcommand to run (must be separated by `--`). "
             "Example: -- python3 scripts/dyvmsapi_rpc.py SubmitIntent -P UserMessage=...",
    )

    args = parser.parse_args()

    prof, name = load_profile(args.profile)

    if args.print_profile:
        mode = prof.get("mode", "<unset>")
        region = prof.get("region_id", "<unset>")
        # Print to stdout (not via announce(), which writes to stderr) so the
        # output can be piped.
        print(f"profile={name} mode={mode} region={region}")
        sys.exit(0)

    mode = validate_mode(prof, name)

    if args.check:
        # Run all validations but do not actually exec.
        build_env(prof, name, mode, os.environ)
        print(f"OK profile={name} mode={mode} ready for auto-injection")
        sys.exit(0)

    # Take the real subcommand after `--`.
    cmd = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print(
            "[run_with_aliyun_creds] ERROR: no subcommand specified.\n"
            "Usage: python3 scripts/run_with_aliyun_creds.py -- <subcommand> [<args>...]",
            file=sys.stderr,
        )
        sys.exit(5)

    env = build_env(prof, name, mode, os.environ)
    announce(prof, name, mode)

    # Use os.execvpe to replace the current process; the child's exit code is
    # propagated naturally.
    try:
        os.execvpe(cmd[0], cmd, env)
    except FileNotFoundError:
        print(
            f"[run_with_aliyun_creds] ERROR: executable not found: {cmd[0]}",
            file=sys.stderr,
        )
        sys.exit(127)


if __name__ == "__main__":
    main()
