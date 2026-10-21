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
import hashlib
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


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            env=env,
            timeout=10,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("local CLI metadata inspection timed out after 10 seconds") from error
    except OSError as error:
        raise RuntimeError("local CLI metadata inspection could not be executed") from error
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


def read_help_payload(aliyun: str, product_code: str, version: str,
                      plugin_info: dict[str, str] | None = None) -> dict[str, Any]:
    # Pin plugin/kebab help, not the traditional PascalCase surface: those
    # spellings route through different CLI engines. Keep overrides local to
    # the metadata subprocess and request machine output explicitly.
    help_env = dict(os.environ)
    help_env["ALIBABA_CLOUD_ORIGINAL_PRODUCT_HELP"] = "false"
    help_env["ALIBABA_CLOUD_BASELINE_PRODUCT_HELP"] = "true"
    output = run_command([
        aliyun, product_code, "--api-version", version, "--help-all",
        "--cli-output", "json", "--cli-ai-mode",
    ], env=help_env)
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as error:
        if plugin_info and plugin_info.get("Type") == "go":
            return read_verified_text_payload(aliyun, product_code, version, plugin_info, output, help_env)
        raise RuntimeError(
            f"{product_code}/{version} help-all did not return JSON metadata; "
            "catalog was not replaced"
        ) from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{product_code}/{version} help-all metadata must be an object")
    product = payload.get("product") or {}
    if product.get("code") != product_code or product.get("selectedVersion") != version:
        raise RuntimeError(f"{product_code}/{version} help-all returned a different product/version")
    for api in payload.get("apis", []):
        name = api.get("name", "")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name):
            raise RuntimeError(
                f"{product_code}/{version} help-all did not return plugin command names; "
                "catalog was not replaced"
            )
    return payload


def read_verified_text_payload(aliyun: str, product_code: str, version: str,
                               plugin_info: dict[str, str], output: str,
                               help_env: dict[str, str]) -> dict[str, Any]:
    """Normalize old binary-plugin Help only after verifying every leaf contract."""
    versions = parse_supported_versions(plugin_info, product_code)
    if plugin_info.get("Product code") != product_code or version not in versions:
        raise RuntimeError("binary plugin product/version does not match the requested metadata")
    clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    if not re.search(rf"(?m)^\s*aliyun\s+{re.escape(product_code)}\s+\[parameters\]\s*$", clean):
        raise RuntimeError("binary plugin Help is not the requested product command listing")
    headers = list(re.finditer(r"(?m)^(?:Available Commands|可用命令):\s*$", clean))
    if len(headers) != 1:
        raise RuntimeError("binary plugin Help has no unambiguous command listing")
    apis = []
    for line in clean[headers[0].end():].splitlines():
        if not line.strip():
            if apis:
                break
            continue
        # Cobra guarantees a separator, not a two-space minimum: the longest
        # command can have just one space before its description.
        match = re.fullmatch(r"  ([a-z][a-z0-9]*(?:-[a-z0-9]+)*)(?: +(.*))?", line)
        if match:
            name, description = match.groups()
            if name in {"version", "list-api-versions", "help", "completion"}:
                continue
            apis.append({"name": name, "description": description or ""})
        elif line.startswith("    ") and apis:
            apis[-1]["description"] += "\n" + line.strip()
        else:
            raise RuntimeError("binary plugin Help contains an unsupported command-list row")
    if not apis or len({api["name"] for api in apis}) != len(apis):
        raise RuntimeError("binary plugin Help has empty or duplicate commands")
    for api in apis:
        name = api["name"]
        leaf = run_command([aliyun, product_code, name, "--api-version", version, "--help"], env=help_env)
        leaf = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", leaf)
        found_versions = re.findall(r"(?m)^(?:API [Vv]ersion|API 版本):\s*(\d{4}-\d{2}-\d{2})\s*$", leaf)
        usage = rf"(?m)^\s*aliyun\s+{re.escape(product_code)}\s+{re.escape(name)}\s+\[parameters\]\s*$"
        if found_versions != [version] or not re.search(usage, leaf):
            raise RuntimeError(f"{product_code}/{version}/{name} binary plugin Help contract could not be verified")
    return {
        "product": {"code": product_code, "selectedVersion": version, "supportedVersions": versions},
        "apis": apis, "result": {"total": len(apis), "truncated": False},
        "metadata_source": "cli_verified_text_help",
    }


def read_indexed_payload(plugin_info: dict[str, str], product_code: str, version: str) -> dict[str, Any]:
    """Read the official installed metadata, without a Help rendering round-trip."""
    plugin_dir = Path(plugin_info["Path"]).expanduser().resolve()

    def package_file(name: str) -> Path:
        if not isinstance(name, str) or not name:
            raise RuntimeError("plugin metadata file name is missing")
        path = (plugin_dir / name).resolve()
        if path.parent != plugin_dir or not path.is_file():
            raise RuntimeError("plugin metadata file must exist inside the installed package")
        return path

    manifest = json.loads(package_file("manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("type") != "meta"
            or manifest.get("name") != f"aliyun-cli-{product_code}"
            or manifest.get("productCode") != product_code
            or manifest.get("version") != plugin_info.get("Version")):
        raise RuntimeError(f"{product_code} installed metadata manifest identity/version mismatch")
    metadata = manifest.get("metadata") or {}
    if (metadata.get("schema") != "aliyun-openapi-meta"
            or metadata.get("schemaVersion") != 1
            or metadata.get("layoutVersion") != 1
            or metadata.get("format") != "protobuf"):
        raise RuntimeError(f"{product_code} unsupported installed metadata layout")
    versions = parse_supported_versions(plugin_info, product_code)
    if sorted(manifest.get("apiVersions", {}).get("supported", [])) != versions or version not in versions:
        raise RuntimeError(f"{product_code} installed metadata API versions mismatch")
    index = json.loads(package_file(metadata.get("index")).read_text(encoding="utf-8"))
    if (index.get("schema") != "aliyun-openapi-meta"
            or index.get("schemaVersion") != 1 or index.get("layoutVersion") != 1):
        raise RuntimeError(f"{product_code} unsupported installed metadata index")
    if index.get("dataFile") != metadata.get("data"):
        raise RuntimeError(f"{product_code} installed metadata data file mismatch")
    data = package_file(index.get("dataFile")).read_bytes()
    if (len(data) != index.get("dataSize")
            or "sha256:" + hashlib.sha256(data).hexdigest() != index.get("dataSha256")):
        raise RuntimeError(f"{product_code} installed metadata integrity check failed")
    apis = index.get("apis")
    if not isinstance(apis, list) or not apis:
        raise RuntimeError(f"{product_code} installed metadata has no API index")
    selected = []
    for api in apis:
        name = api.get("commandName", "")
        if (not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name)
                or api.get("cmdFullName") != f"{product_code} {name}"
                or api.get("apiVersion") not in versions):
            raise RuntimeError(f"{product_code} invalid installed metadata command/version")
        if api["apiVersion"] == version:
            selected.append({"name": name, "description": api.get("descriptionEn") or api.get("descriptionZh") or ""})
    if not selected:
        raise RuntimeError(f"{product_code}/{version} installed metadata has no indexed commands")
    return {
        "product": {"code": product_code, "selectedVersion": version, "supportedVersions": versions},
        "apis": selected,
        "result": {"total": len(selected), "truncated": False},
        "metadata_source": "installed_plugin_index",
    }


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
        "oauth_api_versions",
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
        required_versions = sorted(set(product["required_api_versions"]))
        oauth_versions = sorted(set(product["oauth_api_versions"]))
        if not oauth_versions:
            raise RuntimeError(f"{code} must declare at least one OAuth API version")
        unsupported_oauth_versions = sorted(set(oauth_versions) - set(required_versions))
        if unsupported_oauth_versions:
            raise RuntimeError(
                f"{code} OAuth API versions are not required plugin versions: "
                f"{unsupported_oauth_versions}"
            )
        seen.add(code)
        normalized_product = dict(product)
        normalized_product["required_api_versions"] = required_versions
        normalized_product["oauth_api_versions"] = oauth_versions
        normalized.append(normalized_product)
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
    oauth_api_versions = set(product_spec["oauth_api_versions"])
    commands: dict[str, dict[str, Any]] = {}
    version_counts: dict[str, int] = {}
    metadata_sources: dict[str, str] = {}
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
        metadata_sources[selected_version] = payload.get("metadata_source", "cli_json_help")
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
            if selected_version not in oauth_api_versions:
                continue
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
    missing_oauth_versions = sorted(oauth_api_versions - set(declared_versions))
    if missing_oauth_versions:
        raise RuntimeError(
            f"{product_code} plugin is missing configured OAuth API versions: "
            f"{missing_oauth_versions}"
        )
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
        "authentication_mode": "OAuth",
        "oauth_api_versions": sorted(oauth_api_versions),
        "excluded_api_versions": sorted(set(declared_versions) - oauth_api_versions),
        "command_counts_by_version": dict(sorted(version_counts.items())),
        "metadata_sources_by_version": dict(sorted(metadata_sources.items())),
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
    configured = sorted(set(configured_products or [item["product"] for item in products]))
    missing = sorted(
        list(missing_products or []),
        key=lambda item: str(item["product"]),
    )
    if not products and (
        not configured or {str(item["product"]) for item in missing} != set(configured)
    ):
        raise RuntimeError("cannot build an empty command catalog without complete missing-product evidence")
    command_count = sum(int(product["unique_command_count"]) for product in products)
    return {
        "schema_version": 2,
        "source": "official installed WUYING plugin metadata or verified CLI help, filtered for OAuth",
        "authentication_mode": "OAuth",
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
                    "oauth_api_versions": sorted(
                        set(product_spec["oauth_api_versions"])
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
            if plugin_info.get("Type") == "meta":
                payloads.append(read_indexed_payload(plugin_info, product_code, version))
            else:
                payloads.append(read_help_payload(aliyun, product_code, version, plugin_info))
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
                        "oauth_versions": product["oauth_api_versions"],
                        "excluded_versions": product["excluded_api_versions"],
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
