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
LOCAL_CHECK_TIMEOUT_SECONDS = 5


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


def has_valid_oauth_profile(output: str) -> bool:
    for line in output.splitlines():
        columns = [column.strip() for column in line.split("|")]
        if len(columns) < 3:
            continue
        # An unused OAuth profile must not validate the active AK/STS profile.
        if "*" not in columns[0].split():
            continue
        credential, validity = columns[1:3]
        if credential.startswith("OAuth:") and validity.lower() == "valid":
            return True
    return False


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
    timeout: int | None = LOCAL_CHECK_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        timeout=timeout,
    )


def local_probe(command: list[str]) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    """Bound local inspection and return value-free failure evidence."""
    try:
        process = run(command)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except OSError:
        return None, "execution_error"
    return process, None if process.returncode == 0 else "command_failed"


def resolve_binary(explicit: str | None) -> str | None:
    candidate = explicit or shutil.which("aliyun")
    if not candidate:
        return None
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        return None
    return str(path)


def dependency_setup_plan(
    checks: dict[str, Any],
    product_specs: list[dict[str, Any]],
    required_products: list[str] | None = None,
) -> dict[str, Any]:
    """Plan only dependency repairs; never install, authenticate or call APIs."""
    configured = [str(product["code"]) for product in product_specs]
    required = configured if required_products is None else required_products
    if set(required) - set(configured):
        raise ValueError("required products must be in the configured WUYING scope")
    required = [code for code in configured if code in required]
    cli_ready = checks.get("aliyun_cli_compatible") is True
    if checks.get("cli_inspection_failed"):
        cli_action = "inspect"
    elif cli_ready:
        cli_action = "none"
    else:
        cli_action = "upgrade" if checks.get("aliyun_binary") else "install"
    commands: list[list[str]] = []
    optional_updates: list[str] = []
    missing: list[str] = []
    updates: list[str] = []
    if cli_ready:
        for code in required:
            info = checks.get("plugins", {}).get(code)
            if info is None:
                continue  # No observed plugin state is not an installation fact.
            if info.get("installed") is False:
                missing.append(code)
            elif info.get("installed") is True and info.get("ready") is False:
                updates.append(code)
            elif info.get("ready") is True and info.get("update_available") is True:
                optional_updates.append(code)
        binary = str(checks["aliyun_binary"])
        if missing:
            commands.append([binary, "plugin", "install", "--names", *missing])
        commands.extend([binary, "plugin", "update", "--name", code] for code in updates)
    return {
        "read_only_plan": True,
        "guide": "references/setup.md",
        "required_products": required,
        "cli_action": cli_action,
        "recheck_after_cli_action": not cli_ready,
        "plugin_commands": commands,
        "optional_plugin_updates": optional_updates,
        "authentication_changes_allowed": False,
        "cloud_mutation_approval_granted": False,
        "honor_explicit_no_install": True,
    }


def result(status: str, checks: dict[str, Any], remediation: list[str],
           product_specs: list[dict[str, Any]] | None = None,
           required_products: list[str] | None = None) -> dict[str, Any]:
    allowed = bool(status in {"ready", "partial"}
                   and checks.get("aliyun_cli_compatible") is True
                   and checks.get("valid_oauth_profile") is True
                   and checks.get("ready_products"))
    payload = {
        "status": status,
        "checks": checks,
        "execution_gate": {
            "business_requests_allowed": allowed,
            "required_authentication": "active_valid_OAuth",
            "required_entrypoint": "scripts/run_wuying.py",
            "on_denial": "stop_business_execution_do_not_fallback_to_STS_AK_or_direct_calls",
            "grants_installation_authorization": False,
        },
        "remediation": remediation,
        "credential_values_exposed": False,
    }
    if product_specs is not None:
        payload["dependency_setup_plan"] = dependency_setup_plan(
            checks, product_specs, required_products
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aliyun-bin", help="Path to the aliyun CLI binary")
    parser.add_argument("--skip-profile", action="store_true", help="Skip profile validity detection")
    parser.add_argument(
        "--required-products", nargs="+",
        help="Scope the read-only dependency repair plan to these configured products",
    )
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
    product_specs = load_product_specs(args.products.resolve())
    if args.required_products and set(args.required_products) - {p["code"] for p in product_specs}:
        parser.error("--required-products must contain only configured WUYING products")
    required_codes = set(args.required_products or [p["code"] for p in product_specs])

    checks: dict[str, Any] = {"local_check_errors": {}}
    remediation: list[str] = []
    aliyun = resolve_binary(args.aliyun_bin)
    if not aliyun:
        remediation.append(
            "Prepare the official Aliyun CLI using references/setup.md and its official "
            "source fallbacks, unless installation was explicitly prohibited; then recheck."
        )
        print(json.dumps(result("blocked", checks, remediation, product_specs, args.required_products), ensure_ascii=False, indent=2))
        return 2
    checks["aliyun_binary"] = aliyun

    version_process, version_error = local_probe([aliyun, "version"])
    cli_version = version_process.stdout.strip() if version_process else ""
    checks["aliyun_cli_version"] = cli_version or "unknown"
    try:
        cli_compatible = bool(
            version_process is not None and version_process.returncode == 0
            and version_at_least(cli_version, MINIMUM_CLI_VERSION)
        )
    except ValueError:
        cli_compatible = False
        version_error = "unrecognized_version"
    checks["aliyun_cli_compatible"] = cli_compatible
    checks["cli_inspection_failed"] = version_error is not None
    if version_error:
        checks["local_check_errors"]["cli_version"] = version_error
        remediation.append(
            "CLI inspection failed; retry this local check once. "
            "Do not infer an old CLI or reinstall from a failed probe."
        )
    elif not cli_compatible:
        remediation.append(
            "Prepare Aliyun CLI >=3.5.0 using references/setup.md; preserve the package "
            "manager and respect explicit no-upgrade restrictions, then recheck."
        )

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
        except (subprocess.TimeoutExpired, OSError) as error:
            checks["plugin_update_check"] = {
                "status": "unavailable",
                "source": "aliyun plugin list-remote",
                "error": (
                    f"official remote plugin index check timed out after {REMOTE_UPDATE_TIMEOUT_SECONDS} seconds"
                    if isinstance(error, subprocess.TimeoutExpired)
                    else "official remote plugin index could not be executed"
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
        oauth_api_versions = set(product["oauth_api_versions"])
        plugin_process, plugin_error = local_probe([aliyun, "plugin", "show", "--name", code])
        plugin_info = parse_key_value_output(plugin_process.stdout) if plugin_process else {}
        plugin_version = plugin_info.get("Version", "unknown")
        installed = None
        if plugin_process is not None:
            if plugin_process.returncode == 0 and plugin_info.get("Product code") == code:
                installed = True
            elif plugin_process.returncode != 0 and any(
                marker in (plugin_process.stdout + plugin_process.stderr).lower()
                for marker in ("not installed", "not found in local manifest")
            ):
                installed = False
                plugin_error = None
            elif plugin_error is None:
                plugin_error = "unrecognized_plugin_identity"
        if plugin_error:
            checks["local_check_errors"][f"plugin:{code}"] = plugin_error
        try:
            compatible = installed is True and version_at_least(
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
            "oauth_api_versions": sorted(oauth_api_versions),
            "required_api_versions_available": required_versions_available,
            "ready": ready,
        }
        if code not in required_codes:
            continue  # Observe all products, but never recommend unrelated repairs.
        if installed is None:
            remediation.append(
                f"The {code} plugin state is unknown; retry its local inspection once, "
                "without assuming it is missing or reinstalling it."
            )
        elif not installed:
            remediation.append(
                "If required for this task and installation is not prohibited, prepare with: "
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
                f"({plugin_version} -> {latest_version}). Optional only; after an explicit update request, "
                f"update it with: aliyun plugin update --name {package}"
            )
    checks["plugins"] = plugin_checks
    checks["ready_products"] = ready_products
    checks["unavailable_products"] = unavailable_products
    checks["updates_available"] = updates_available

    # Authentication evidence must not disappear merely because a plugin or CLI
    # upgrade is also needed. Do not encourage remediation before revealing the
    # independent OAuth blocker.
    checks["authentication_mode"] = "OAuth"
    if args.skip_profile:
        checks["valid_profile"] = "not_checked"
        checks["valid_oauth_profile"] = "not_checked"
    else:
        profiles, profile_error = local_probe([aliyun, "configure", "list"])
        valid_oauth_profile = (
            profiles is not None and profiles.returncode == 0
            and has_valid_oauth_profile(profiles.stdout)
        )
        checks["valid_profile"] = valid_oauth_profile
        checks["valid_oauth_profile"] = valid_oauth_profile
        if profile_error:
            checks["local_check_errors"]["oauth_profile"] = profile_error
            remediation.append(
                "OAuth profile inspection failed; retry the local check once. "
                "Do not infer expiration or start login/change profiles from a failed probe."
            )
        elif not valid_oauth_profile:
            remediation.append(
                "Stop all business requests. Follow references/authentication.md; reuse existing "
                "authorization for the exact login/profile change without asking again, "
                "otherwise obtain it once. Then "
                "configure an active OAuth profile without overwriting existing credentials; "
                "never use STS/AK or direct calls as a fallback."
            )

    technical_ready = bool(checks["aliyun_cli_compatible"] and ready_products)
    if not technical_ready or "oauth_profile" in checks["local_check_errors"]:
        print(json.dumps(result("blocked", checks, remediation, product_specs, args.required_products), ensure_ascii=False, indent=2))
        return 2
    if not args.skip_profile and not valid_oauth_profile:
        print(json.dumps(result("needs_auth", checks, remediation, product_specs, args.required_products), ensure_ascii=False, indent=2))
        return 3

    status = "partial" if unavailable_products else "ready"
    print(json.dumps(result(status, checks, remediation, product_specs, args.required_products), ensure_ascii=False, indent=2))
    return 4 if unavailable_products else 0


if __name__ == "__main__":
    raise SystemExit(main())
