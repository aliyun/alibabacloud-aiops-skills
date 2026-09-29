#!/usr/bin/env python3
"""Check whether the local Aliyun CLI environment can operate configured WUYING products."""

#
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
#
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any


MINIMUM_CLI_VERSION = (3, 5, 0)
REMOTE_UPDATE_TIMEOUT_SECONDS = 15


def version_tuple(raw: str) -> tuple[int, ...]:
    match = re.search(r"\d+(?:\.\d+)+", raw)
    if not match:
        raise ValueError(f"version not found in {raw!r}")
    return tuple(int(part) for part in match.group(0).split("."))


def version_at_least(raw: str, minimum: tuple[int, ...]) -> bool:
    current = version_tuple(raw)
    width = max(len(current), len(minimum))
    return current + (0,) * (width - len(current)) >= minimum + (0,) * (width - len(minimum))


def version_is_newer(candidate: str, current: str) -> bool:
    candidate_version = version_tuple(candidate)
    current_version = version_tuple(current)
    width = max(len(candidate_version), len(current_version))
    candidate_padded = candidate_version + (0,) * (width - len(candidate_version))
    current_padded = current_version + (0,) * (width - len(current_version))
    return candidate_padded > current_padded


def parse_key_value_output(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def parse_remote_plugins(output: str) -> dict[str, dict[str, str]]:
    plugins: dict[str, dict[str, str]] = {}
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("aliyun-cli-"):
            continue
        columns = re.split(r"\s{2,}", stripped, maxsplit=5)
        if len(columns) < 5:
            continue
        package, latest_version, preview, status, local_version = columns[:5]
        plugins[package] = {
            "latest_version": latest_version,
            "preview": preview,
            "status": status,
            "local_version": local_version,
            "description": columns[5] if len(columns) > 5 else "",
        }
    return plugins


def load_product_specs(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise RuntimeError(f"unsupported product configuration schema: {payload.get('schema_version')!r}")
    products = payload.get("products")
    if not isinstance(products, list) or not products:
        raise RuntimeError("product configuration must contain a non-empty products list")
    return products


def run(
    command: list[str],
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )


def resolve_binary(explicit: str | None) -> str | None:
    candidate = explicit or shutil.which("aliyun")
    if not candidate:
        return None
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        return None
    return str(path)


def result(status: str, checks: dict[str, Any], remediation: list[str]) -> dict[str, Any]:
    return {
        "status": status,
        "checks": checks,
        "remediation": remediation,
        "credential_values_exposed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aliyun-bin", help="Path to the aliyun CLI binary")
    parser.add_argument("--skip-profile", action="store_true", help="Skip profile validity detection")
    parser.add_argument(
        "--skip-update-check",
        action="store_true",
        help="Skip the official remote plugin index update check",
    )
    parser.add_argument(
        "--products",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "references" / "products.json",
        help="WUYING product configuration path",
    )
    args = parser.parse_args()

    checks: dict[str, Any] = {}
    remediation: list[str] = []
    aliyun = resolve_binary(args.aliyun_bin)
    if not aliyun:
        remediation.append("Install the official Aliyun CLI, then rerun this check.")
        print(json.dumps(result("blocked", checks, remediation), ensure_ascii=False, indent=2))
        return 2
    checks["aliyun_binary"] = aliyun

    version_process = run([aliyun, "version"])
    cli_version = version_process.stdout.strip()
    checks["aliyun_cli_version"] = cli_version or "unknown"
    try:
        cli_compatible = version_process.returncode == 0 and version_at_least(cli_version, MINIMUM_CLI_VERSION)
    except ValueError:
        cli_compatible = False
    checks["aliyun_cli_compatible"] = cli_compatible
    if not cli_compatible:
        remediation.append("Upgrade the official Aliyun CLI to version 3.5.0 or later.")

    product_specs = load_product_specs(args.products.resolve())
    remote_plugins: dict[str, dict[str, str]] = {}
    if args.skip_update_check:
        checks["plugin_update_check"] = {
            "status": "skipped",
            "source": "aliyun plugin list-remote",
        }
    else:
        try:
            remote_process = run(
                [aliyun, "plugin", "list-remote"],
                timeout=REMOTE_UPDATE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            checks["plugin_update_check"] = {
                "status": "unavailable",
                "source": "aliyun plugin list-remote",
                "error": (
                    "official remote plugin index check timed out after "
                    f"{REMOTE_UPDATE_TIMEOUT_SECONDS} seconds"
                ),
            }
        else:
            if remote_process.returncode == 0:
                remote_plugins = parse_remote_plugins(remote_process.stdout)
                checks["plugin_update_check"] = {
                    "status": "ok",
                    "source": "aliyun plugin list-remote",
                    "remote_plugin_count": len(remote_plugins),
                }
            else:
                detail = remote_process.stderr.strip() or remote_process.stdout.strip()
                checks["plugin_update_check"] = {
                    "status": "unavailable",
                    "source": "aliyun plugin list-remote",
                    "error": (
                        detail or f"command exited with status {remote_process.returncode}"
                    ),
                }

    plugin_checks: dict[str, Any] = {}
    ready_products: list[str] = []
    unavailable_products: list[str] = []
    updates_available: list[str] = []
    for product in product_specs:
        code = str(product["code"])
        package = str(product["plugin_package"])
        minimum_version = str(product["minimum_plugin_version"])
        required_api_versions = set(product["required_api_versions"])
        plugin_process = run([aliyun, "plugin", "show", "--name", code])
        plugin_info = parse_key_value_output(plugin_process.stdout)
        plugin_version = plugin_info.get("Version", "unknown")
        installed = plugin_process.returncode == 0 and plugin_info.get("Product code") == code
        try:
            compatible = installed and version_at_least(
                plugin_version, version_tuple(minimum_version)
            )
        except ValueError:
            compatible = False
        supported_versions = {
            value.strip()
            for value in plugin_info.get("API supported", "").split(",")
            if value.strip()
        }
        required_versions_available = required_api_versions.issubset(supported_versions)
        ready = bool(installed and compatible and required_versions_available)
        remote_plugin = remote_plugins.get(package)
        latest_version = (
            remote_plugin.get("latest_version") if remote_plugin is not None else None
        )
        try:
            update_available = bool(
                installed
                and latest_version
                and version_is_newer(latest_version, plugin_version)
            )
        except ValueError:
            update_available = False
        if ready:
            ready_products.append(code)
        else:
            unavailable_products.append(code)
        if update_available:
            updates_available.append(code)
        plugin_checks[code] = {
            "package": package,
            "installed": installed,
            "version": plugin_version,
            "latest_stable_version": latest_version,
            "update_available": update_available,
            "remote_index_found": remote_plugin is not None,
            "minimum_version": minimum_version,
            "compatible": compatible,
            "supported_api_versions": sorted(supported_versions),
            "required_api_versions": sorted(required_api_versions),
            "required_api_versions_available": required_versions_available,
            "ready": ready,
        }
        if not installed:
            remediation.append(
                "After user authorization, install it with: "
                f"aliyun plugin install --name {package}"
            )
        elif not compatible:
            remediation.append(
                f"Upgrade the official {code} plugin to version "
                f"{minimum_version} or later."
            )
        elif not required_versions_available:
            remediation.append(
                f"Upgrade the {code} plugin; its API version set is missing "
                f"{sorted(required_api_versions - supported_versions)}."
            )
        elif update_available:
            remediation.append(
                f"A newer stable {code} plugin is available "
                f"({plugin_version} -> {latest_version}). After user authorization, "
                f"update it with: aliyun plugin update --name {package}"
            )
    checks["plugins"] = plugin_checks
    checks["ready_products"] = ready_products
    checks["unavailable_products"] = unavailable_products
    checks["updates_available"] = updates_available

    technical_ready = bool(checks["aliyun_cli_compatible"] and ready_products)
    if not technical_ready:
        print(json.dumps(result("blocked", checks, remediation), ensure_ascii=False, indent=2))
        return 2

    if args.skip_profile:
        checks["valid_profile"] = "not_checked"
        status = "partial" if unavailable_products else "ready"
        print(json.dumps(result(status, checks, remediation), ensure_ascii=False, indent=2))
        return 4 if unavailable_products else 0

    profiles = run([aliyun, "configure", "list"])
    valid_profile = profiles.returncode == 0 and any(
        re.search(r"\bValid\b", line, re.IGNORECASE) for line in profiles.stdout.splitlines()
    )
    checks["valid_profile"] = valid_profile
    if not valid_profile:
        remediation.append(
            "After user authorization, configure a standard profile, preferably: "
            "aliyun configure --mode OAuth --profile default"
        )
        print(json.dumps(result("needs_auth", checks, remediation), ensure_ascii=False, indent=2))
        return 3

    status = "partial" if unavailable_products else "ready"
    print(json.dumps(result(status, checks, remediation), ensure_ascii=False, indent=2))
    return 4 if unavailable_products else 0


if __name__ == "__main__":
    raise SystemExit(main())
