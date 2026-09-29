#!/usr/bin/env python3
"""Generate a deterministic command catalog from official WUYING product plugins."""

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
import tempfile
from typing import Any, Iterable


READ_PREFIXES = ("describe-", "list-", "get-", "query-")
DESTRUCTIVE_PREFIXES = ("delete-", "release-", "reset-", "rebuild-", "terminate-")


def classify_risk(command_name: str) -> str:
    name = command_name.lower()
    if name.startswith(DESTRUCTIVE_PREFIXES):
        return "destructive"
    if name.startswith(READ_PREFIXES):
        return "read"
    return "mutation"


def parse_key_value_output(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{detail}")
    return completed.stdout


def resolve_aliyun_binary(explicit: str | None) -> str:
    candidate = explicit or shutil.which("aliyun")
    if not candidate:
        raise RuntimeError("aliyun CLI was not found; pass --aliyun-bin or add it to PATH")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"aliyun CLI is not executable: {path}")
    return str(path)


def load_product_specs(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise RuntimeError(f"unsupported product configuration schema: {payload.get('schema_version')!r}")
    products = payload.get("products")
    if not isinstance(products, list) or not products:
        raise RuntimeError("product configuration must contain a non-empty products list")

    required_fields = {
        "code",
        "name",
        "plugin_package",
        "minimum_plugin_version",
        "required_api_versions",
    }
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for product in products:
        if not isinstance(product, dict):
            raise RuntimeError("each configured product must be an object")
        missing = sorted(required_fields - product.keys())
        if missing:
            raise RuntimeError(f"configured product is missing fields: {missing}")
        code = str(product["code"]).strip()
        if not code or code in seen:
            raise RuntimeError(f"invalid or duplicate product code: {code!r}")
        seen.add(code)
        normalized.append(product)
    return normalized


def parse_supported_versions(plugin_info: dict[str, str], product_code: str) -> list[str]:
    raw = plugin_info.get("API supported", "")
    versions = sorted({value.strip() for value in raw.split(",") if value.strip()})
    if not versions:
        raise RuntimeError(f"{product_code} plugin did not report any supported API versions")
    for version in versions:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", version):
            raise RuntimeError(f"unexpected {product_code} API version: {version}")
    return versions


def build_product_catalog(
    cli_version: str,
    product_spec: dict[str, Any],
    plugin_info: dict[str, str],
    payloads: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    product_code = str(product_spec["code"])
    commands: dict[str, dict[str, Any]] = {}
    version_counts: dict[str, int] = {}
    supported_versions: set[str] = set()

    for payload in payloads:
        product = payload.get("product") or {}
        payload_product_code = product.get("code")
        if payload_product_code != product_code:
            raise RuntimeError(
                f"help-all payload product mismatch: expected {product_code}, "
                f"received {payload_product_code!r}"
            )
        selected_version = product.get("selectedVersion")
        if not selected_version:
            raise RuntimeError(
                f"{product_code} help-all payload is missing product.selectedVersion"
            )
        apis = payload.get("apis")
        if not isinstance(apis, list):
            raise RuntimeError(
                f"{product_code} help-all payload for {selected_version} has no API list"
            )
        result = payload.get("result") or {}
        if result.get("truncated"):
            raise RuntimeError(
                f"{product_code} help-all payload for {selected_version} is truncated"
            )
        if result.get("total") != len(apis):
            raise RuntimeError(
                f"{product_code} help-all count mismatch for {selected_version}: "
                f"reported {result.get('total')}, received {len(apis)}"
            )

        supported_versions.update(product.get("supportedVersions") or [])
        version_counts[selected_version] = len(apis)
        seen_in_version: set[str] = set()
        for api in apis:
            name = str(api.get("name") or "").strip()
            description = str(api.get("description") or "").strip()
            if not name or name in seen_in_version:
                raise RuntimeError(
                    f"invalid or duplicate {product_code} command in "
                    f"{selected_version}: {name!r}"
                )
            seen_in_version.add(name)
            entry = commands.setdefault(
                name,
                {
                    "name": name,
                    "description": description,
                    "api_versions": [],
                    "risk": classify_risk(name),
                },
            )
            entry["api_versions"].append(selected_version)
            if not entry["description"] and description:
                entry["description"] = description

    for entry in commands.values():
        entry["api_versions"] = sorted(set(entry["api_versions"]))
        entry["preferred_api_version"] = entry["api_versions"][-1]

    declared_versions = parse_supported_versions(plugin_info, product_code)
    if sorted(supported_versions) != declared_versions:
        raise RuntimeError(
            f"{product_code} plugin metadata and help-all supported versions differ: "
            f"plugin={declared_versions}, help={sorted(supported_versions)}"
        )
    if sorted(version_counts) != declared_versions:
        raise RuntimeError(
            f"{product_code} catalog payload versions are incomplete: "
            f"expected {declared_versions}, "
            f"received {sorted(version_counts)}"
        )

    return {
        "product": product_code,
        "product_name": str(product_spec["name"]),
        "plugin_package": str(product_spec["plugin_package"]),
        "plugin_version": plugin_info.get("Version", "unknown"),
        "plugin_type": plugin_info.get("Type", "unknown"),
        "plugin_minimum_cli_version": plugin_info.get("Minimum CLI version", "unknown"),
        "default_api_version": plugin_info.get("API default", "unknown"),
        "supported_api_versions": declared_versions,
        "command_counts_by_version": dict(sorted(version_counts.items())),
        "unique_command_count": len(commands),
        "risk_note": (
            "Risk is a conservative name-based hint. Inspect live command help before execution; "
            "unknown and non-read patterns require confirmation."
        ),
        "commands": [commands[name] for name in sorted(commands)],
    }


def build_catalog(
    cli_version: str,
    product_catalogs: Iterable[dict[str, Any]],
    configured_products: Iterable[str] | None = None,
    missing_products: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    products = sorted(product_catalogs, key=lambda item: item["product"])
    if not products:
        raise RuntimeError("cannot build an empty command catalog")
    configured = sorted(set(configured_products or [item["product"] for item in products]))
    missing = sorted(
        list(missing_products or []),
        key=lambda item: str(item["product"]),
    )
    command_count = sum(int(product["unique_command_count"]) for product in products)
    return {
        "schema_version": 2,
        "source": "official aliyun CLI WUYING product plugins --help-all",
        "aliyun_cli_version": cli_version,
        "catalog_complete": not missing,
        "configured_product_count": len(configured),
        "configured_products": configured,
        "product_count": len(products),
        "command_count": command_count,
        "missing_products": missing,
        "risk_note": (
            "Risk is a conservative name-based hint. Inspect live command help before execution; "
            "unknown and non-read patterns require confirmation."
        ),
        "products": products,
    }


def write_json_atomic(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        delete=False,
    ) as temporary:
        temporary.write(rendered)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aliyun-bin", help="Path to the aliyun CLI binary")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "references" / "command-catalog.json",
        help="Catalog output path",
    )
    parser.add_argument(
        "--products",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "references" / "products.json",
        help="WUYING product configuration path",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "Generate a partial catalog from installed products and record unavailable "
            "configured products instead of failing."
        ),
    )
    args = parser.parse_args()

    aliyun = resolve_aliyun_binary(args.aliyun_bin)
    cli_version = run_command([aliyun, "version"]).strip()
    product_specs = load_product_specs(args.products.resolve())
    product_catalogs: list[dict[str, Any]] = []
    missing_products: list[dict[str, Any]] = []
    for product_spec in product_specs:
        product_code = str(product_spec["code"])
        try:
            plugin_output = run_command(
                [aliyun, "plugin", "show", "--name", product_code]
            )
        except RuntimeError as error:
            if not args.allow_missing:
                raise
            missing_products.append(
                {
                    "product": product_code,
                    "product_name": str(product_spec["name"]),
                    "plugin_package": str(product_spec["plugin_package"]),
                    "minimum_plugin_version": str(
                        product_spec["minimum_plugin_version"]
                    ),
                    "required_api_versions": sorted(
                        set(product_spec["required_api_versions"])
                    ),
                    "reason": str(error).splitlines()[-1],
                }
            )
            continue
        plugin_info = parse_key_value_output(plugin_output)
        if plugin_info.get("Product code") != product_code:
            raise RuntimeError(
                f"the installed plugin is not the official {product_code} product plugin"
            )

        versions = parse_supported_versions(plugin_info, product_code)
        payloads = []
        for version in versions:
            output = run_command(
                [aliyun, product_code, "--api-version", version, "--help-all"]
            )
            payloads.append(json.loads(output))
        product_catalogs.append(
            build_product_catalog(cli_version, product_spec, plugin_info, payloads)
        )

    catalog = build_catalog(
        cli_version,
        product_catalogs,
        configured_products=[str(item["code"]) for item in product_specs],
        missing_products=missing_products,
    )
    write_json_atomic(args.output.resolve(), catalog)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "cli_version": catalog["aliyun_cli_version"],
                "catalog_complete": catalog["catalog_complete"],
                "configured_product_count": catalog["configured_product_count"],
                "product_count": catalog["product_count"],
                "command_count": catalog["command_count"],
                "missing_products": catalog["missing_products"],
                "products": [
                    {
                        "product": product["product"],
                        "plugin_version": product["plugin_version"],
                        "versions": product["supported_api_versions"],
                        "unique_commands": product["unique_command_count"],
                        "counts_by_version": product["command_counts_by_version"],
                    }
                    for product in catalog["products"]
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
