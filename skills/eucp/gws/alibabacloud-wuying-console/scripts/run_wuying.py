#!/usr/bin/env python3
"""Recheck OAuth/plugin readiness before delegating a WUYING request to Aliyun CLI."""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
AUTH_OVERRIDE_FLAGS = {
    "--profile", "--mode", "--access-key-id", "--access-key-secret",
    "--sts-token", "--security-token", "--bearer-token", "--credentials-uri",
    "--config-file",
}


def validate_request(
    command: list[str], specs: dict[str, Any], evidence: dict[str, Any]
) -> None:
    if len(command) < 4 or command[0] != "aliyun" or command[1].startswith("-") or command[2].startswith("-"):
        raise ValueError("usage: run_wuying.py -- aliyun <product> <command> --api-version <version> ...")
    products = {item["code"]: item for item in specs["products"]}
    product = command[1]
    if product not in products:
        raise ValueError("product is outside the configured WUYING scope")
    flags = command[3:]
    if any(arg.split("=", 1)[0] in AUTH_OVERRIDE_FLAGS for arg in flags):
        raise ValueError("authentication overrides are not allowed; use the checked active OAuth profile")
    versions = []
    for index, arg in enumerate(flags):
        if arg == "--api-version":
            if index + 1 >= len(flags) or flags[index + 1].startswith("--"):
                raise ValueError("--api-version requires a value")
            versions.append(flags[index + 1])
        elif arg.startswith("--api-version="):
            versions.append(arg.split("=", 1)[1])
    if len(versions) != 1 or versions[0] not in products[product]["oauth_api_versions"]:
        raise ValueError("exactly one explicit OAuth-compatible --api-version is required")
    checks = evidence.get("checks", {})
    if evidence.get("status") not in {"ready", "partial"}:
        raise ValueError("environment is not ready; no business request was sent")
    if checks.get("valid_oauth_profile") is not True:
        raise ValueError("the active profile must be valid OAuth; no business request was sent")
    if product not in checks.get("ready_products", []):
        raise ValueError("the requested official product plugin is not ready")


def main() -> int:
    command = sys.argv[1:]
    options: list[str] = []
    if "--" in command:
        separator = command.index("--")
        options, command = command[:separator], command[separator + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aliyun-bin", help="Use the same effective CLI as setup/preflight, without changing PATH")
    args = parser.parse_args(options)
    try:
        aliyun = args.aliyun_bin or shutil.which("aliyun")
        if not aliyun:
            raise ValueError("official Aliyun CLI is not installed")
        if args.aliyun_bin:
            binary = Path(aliyun).expanduser().resolve()
            if not binary.is_file() or not os.access(binary, os.X_OK):
                raise ValueError("the selected CLI binary is not executable")
            aliyun = str(binary)
        specs = json.loads((ROOT / "references" / "products.json").read_text(encoding="utf-8"))
        # The workflow already checks remote updates. This fresh execution gate
        # intentionally performs only local CLI/plugin/profile checks.
        checked = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_environment.py"),
             "--aliyun-bin", aliyun, "--skip-update-check"],
            capture_output=True, text=True, check=False, timeout=60,
        )
        if checked.returncode not in {0, 4}:
            raise ValueError("OAuth/plugin preflight failed; no business request was sent")
        evidence = json.loads(checked.stdout)
        validate_request(command, specs, evidence)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired) as error:
        # Do not echo raw CLI diagnostics, argv, profile contents or credentials.
        detail = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else "preflight evidence unavailable"
        print(json.dumps({"status": "blocked", "request_sent": False, "reason": detail,
                          "next_action": "stop_business_execution",
                          "credential_fallback_allowed": False,
                          "direct_cli_sdk_http_retry_allowed": False}, ensure_ascii=False))
        return 2
    return subprocess.run([aliyun, *command[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
