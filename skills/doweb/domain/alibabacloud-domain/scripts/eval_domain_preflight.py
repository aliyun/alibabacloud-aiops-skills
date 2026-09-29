#!/usr/bin/env python3
"""Check read-only prerequisites before DomainCLI functional evaluations.

Dependencies: Python >= 3.10, standard library only; an already installed,
caller-approved Alibaba Cloud CLI >= 3.5.1 with DomainCLI >= 0.9.8. This script does not
install, log in, retry, read credential files, convert credentials, or write cloud
resources. Only --check-cloud authorizes whoami and exact-target fixture reads.
CLI response data stays in memory; stdout contains only a sanitized JSON report.
--fixture-file validates an already delivered non-secret read-fixtures.json;
it does not provision resources or authorize cloud reads. Functional runners must
use --check-cloud --require-ready and consume status/boolean readiness, not just
the default local-only exit code.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence


LOCAL_TIMEOUT = 20
CLOUD_TIMEOUT = 60
TOTAL_TIMEOUT = 120
MAX_RESPONSE_CHARS = 2_000_000
MAX_FIXTURE_BYTES = 4096
MAX_TEMPLATE_ID = (1 << 63) - 1
MANIFEST = Path(__file__).resolve().parents[1] / "references" / "manifest.json"
MIN_PARENT_VERSION = (3, 5, 1)
MIN_DOMAIN_VERSION = (0, 9, 8)
DNS_RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV", "CAA", "PTR", "REDIRECT_URL", "FORWARD_URL")
DOMAIN_FIXTURE_KEYS = ("asset_domain", "verification_failed_domain", "transfer_in_domain", "transfer_out_domain", "renewable_domain", "redemption_domain", "lock_domain", "server_lock_domain")
ID_FIXTURE_KEYS = ("verification_failed_template_id", "task_id")


class CheckFailure(Exception):
    """Carry only fixed, safe classifications, never CLI or input text."""

    def __init__(self, error_class: str, status: str = "blocked_runtime") -> None:
        self.error_class = error_class
        self.status = status
        super().__init__()


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's default message may quote unknown secret-bearing arguments.
        raise CheckFailure("invalid_arguments", "invalid_input")


def parser() -> argparse.ArgumentParser:
    result = SafeArgumentParser(
        description="Read-only DomainCLI eval prerequisites; defaults to local version checks.",
        epilog="No login, installation, retry, writes, credential inspection or raw API fallback. "
        "Exit codes: 0 local checks passed or requested fixtures ready; 1 prerequisite blocked; "
        "2 invalid input. Local success is not cloud/fixture readiness.",
    )
    result.add_argument("--cli", help="Exact approved installed aliyun executable; default resolves aliyun on PATH once.")
    result.add_argument("--profile", help="Preserve this exact parent CLI profile selector; not a credential value.")
    result.add_argument("--config-path", help="Preserve this exact parent CLI configuration-store selector; file is not read here.")
    result.add_argument("--check-cloud", action="store_true", help="Explicitly allow read-only cloud identity and supplied exact-target checks.")
    result.add_argument("--fixture-file", help="Already delivered absolute single-link read-fixtures.json; only the fixed non-secret locator registry is allowed. Reject symlinks/hardlinks, non-regular files, foreign owners and group/world-writable files. Does not create the file or authorize cloud access.")
    result.add_argument("--domain-key", choices=DOMAIN_FIXTURE_KEYS, help="Explicitly select this domain locator field; with an explicit --domain the default comparison key is asset_domain. No registrar check is inferred merely from other fields in the file.")
    result.add_argument("--dns-zone-from-fixture", action="store_true", help="Explicitly select dns_zone from --fixture-file. DNS-only checks do not request registrar ownership reads for unrelated asset_domain locators.")
    result.add_argument("--require-ready", action="store_true", help="Functional runner gate: exit 0 only for status=ready with verified cloud identity and every requested exact-target fixture ready. Without --check-cloud, local checks remain local_only and exit 1.")
    result.add_argument("--domain", help="Exact managed account domain fixture, as an ASCII FQDN (punycode for IDNs).")
    result.add_argument("--dns-zone", help="Exact hosted DNS-zone fixture, independent of registrar ownership; ASCII FQDN.")
    result.add_argument("--require-record", action="store_true", help="With --check-cloud --dns-zone, require an existing usable DNS record for record-dependent functional evals.")
    result.add_argument("--record-type", choices=DNS_RECORD_TYPES, help="With --require-record, filter DNS reads by the verified leaf --type option and require this exact returned type (for example A); other types cannot substitute. The checker flag name is not forwarded.")
    return result


def normalize_fqdn(value: str) -> str:
    """Permit only unambiguous DNS names; do not discover or replace a target."""
    if not isinstance(value, str) or not value or not value.isascii():
        raise CheckFailure("unsafe_target", "invalid_input")
    normalized = value.lower().removesuffix(".")
    if len(normalized) > 253 or len(normalized.split(".")) < 2:
        raise CheckFailure("unsafe_target", "invalid_input")
    labels = normalized.split(".")
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
        raise CheckFailure("unsafe_target", "invalid_input")
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        pass
    else:
        raise CheckFailure("unsafe_target", "invalid_input")
    if labels[-1].isdigit():
        raise CheckFailure("unsafe_target", "invalid_input")
    return normalized


def validate_selector(value: str | None) -> None:
    if value is not None and (
        not value or len(value) > 4096 or value.startswith("-")
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise CheckFailure("invalid_selector", "invalid_input")


def load_attribution(manifest: Path = MANIFEST) -> dict[str, str]:
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise CheckFailure("invalid_manifest") from None
    if not isinstance(data, dict) or data.get("name") != "alibabacloud-domain" or not isinstance(data.get("version"), str):
        raise CheckFailure("invalid_manifest")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", data["version"]):
        raise CheckFailure("invalid_manifest")
    session_id = secrets.token_hex(16)
    return {
        "name": data["name"], "version": data["version"], "session_id": session_id,
        "user_agent": f"AlibabaCloud-Agent-Skills/{data['name']}/{session_id} skill-version/{data['version']}",
    }


def resolve_cli(selected: str | None) -> str:
    # A caller-selected executable never falls back to another installation.
    if selected is None:
        selected = shutil.which("aliyun")
    if not selected:
        raise CheckFailure("cli_unavailable")
    path = Path(selected).absolute()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise CheckFailure("cli_unavailable")
    return str(path)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def load_fixture_file(selected: str) -> dict[str, str]:
    """Read only the caller-designated, bounded non-secret locator contract.

    Open each path component relative to a pinned directory descriptor so a
    symlink swap cannot redirect the read to a credential or personal-data file.
    No directory scanning, path resolving, or secure-input content inspection.
    """
    validate_selector(selected)
    path = Path(selected)
    if (not path.is_absolute() or path.name != "read-fixtures.json"
            or any(part in (".", "..") for part in selected.split("/"))):
        raise CheckFailure("unsafe_fixture_path", "invalid_input")
    descriptors: list[int] = []
    try:
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        directory = os.open("/", flags | os.O_DIRECTORY)
        descriptors.append(directory)
        for part in path.parts[1:-1]:
            directory = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            descriptors.append(directory)
        fixture = os.open(path.name, flags | os.O_NONBLOCK, dir_fd=directory)
        descriptors.append(fixture)
        info = os.fstat(fixture)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                or info.st_mode & 0o022):
            raise CheckFailure("unsafe_fixture_file", "invalid_input")
        if info.st_size > MAX_FIXTURE_BYTES:
            raise CheckFailure("invalid_fixture_file", "invalid_input")
        raw = os.read(fixture, MAX_FIXTURE_BYTES + 1)
        if len(raw) > MAX_FIXTURE_BYTES:
            raise CheckFailure("invalid_fixture_file", "invalid_input")
    except FileNotFoundError:
        raise CheckFailure("fixture_file_missing", "blocked_fixture") from None
    except (OSError, ValueError):
        raise CheckFailure("unsafe_fixture_file", "invalid_input") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (ValueError, UnicodeError, RecursionError):
        raise CheckFailure("invalid_fixture_file", "invalid_input") from None
    if (not isinstance(data, dict) or not data
            or set(data) - set(DOMAIN_FIXTURE_KEYS + ID_FIXTURE_KEYS + ("dns_zone",))):
        raise CheckFailure("invalid_fixture_fields", "invalid_input")
    validated: dict[str, str] = {}
    for key, value in data.items():
        if key == "verification_failed_template_id":
            # template-failure --template-id is an integer, unlike the opaque
            # string consumed by task show --task-id. Keep IDs canonical and
            # positive, with a portable signed-64-bit upper bound.
            if (not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,18}", value)
                    or int(value) > MAX_TEMPLATE_ID):
                raise CheckFailure("invalid_fixture_identifier", "invalid_input")
            validated[key] = value
        elif key == "task_id":
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
                raise CheckFailure("invalid_fixture_identifier", "invalid_input")
            validated[key] = value
        else:
            validated[key] = normalize_fqdn(value)
    return validated


def merge_fixture_target(explicit: str | None, loaded: str | None) -> str | None:
    normalized = normalize_fqdn(explicit) if explicit is not None else None
    if normalized is not None and loaded is not None and normalized != loaded:
        raise CheckFailure("fixture_target_conflict", "invalid_input")
    return normalized if normalized is not None else loaded


def structured_response(stdout: str) -> dict[str, Any]:
    try:
        data = json.loads(stdout, object_pairs_hook=_reject_duplicate_keys)
    except (ValueError, TypeError, RecursionError):
        raise CheckFailure("unknown_response", "blocked_fixture") from None
    if not isinstance(data, dict) or not data:
        raise CheckFailure("unknown_response", "blocked_fixture")
    return data


def response_error(data: dict[str, Any]) -> str | None:
    if isinstance(data.get("data"), dict):
        nested_error = response_error(data["data"])
        if nested_error:
            return nested_error
    code = data.get("code", data.get("Code"))
    error = data.get("error")
    if isinstance(error, dict):
        code = error.get("code", error.get("Code", code))
    status = data.get("status")
    failed = data.get("ok") is False or data.get("success") is False or data.get("Success") is False or bool(error)
    failed = failed or status in ("error", "failed", "failure", "unauthenticated", "authorization_required")
    if isinstance(code, str) and code.upper() not in ("", "SUCCESS", "OK", "200"):
        failed = True
    if not failed:
        return None
    if isinstance(code, str):
        lowered = code.lower()
        # This is a failed server-response transformation, not missing user
        # input or evidence that the supplied domain is absent from the account.
        message = error.get("message") if isinstance(error, dict) else None
        if (lowered == "internal" and isinstance(message, str)
                and "failed to transform" in message.lower()):
            return "response_schema_mismatch"
        if lowered == "internal":
            return "internal_response"
        if any(fragment in lowered for fragment in ("authorization_required", "unauth", "invalidaccesskey", "invalidsecuritytoken", "credential", "oauth", "tokenexpired")):
            return "authentication_unavailable"
        if any(fragment in lowered for fragment in ("forbidden", "denied", "nopermission")):
            return "permission_denied"
        if any(fragment in lowered for fragment in ("notfound", "not_found", "nodomain")):
            return "fixture_missing"
    return "cloud_read_failed"


class Checker:
    def __init__(self, cli: str, attribution: dict[str, str], args: argparse.Namespace,
                 runner: Callable[..., Any], clock: Callable[[], float]) -> None:
        self.cli = cli
        self.attribution = attribution
        self.args = args
        self.runner = runner
        self.clock = clock
        self.started = clock()

    def invoke(self, *arguments: str, cloud: bool = False) -> str:
        remaining = TOTAL_TIMEOUT - (self.clock() - self.started)
        if remaining <= 0:
            raise CheckFailure("total_timeout", "blocked_timeout")
        timeout = min(CLOUD_TIMEOUT if cloud else LOCAL_TIMEOUT, remaining)
        argv = [self.cli, *arguments]
        if self.args.profile is not None:
            argv.extend(["--profile", self.args.profile])
        if self.args.config_path is not None:
            argv.extend(["--config-path", self.args.config_path])
        if arguments[0] == "domain":
            argv.extend(["--user-agent", self.attribution["user_agent"], "--cli-ai-mode"])
        try:
            completed = self.runner(argv, shell=False, stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise CheckFailure("cloud_timeout" if cloud else "local_timeout", "blocked_timeout") from None
        except (OSError, ValueError, UnicodeError):
            raise CheckFailure("cli_execution_failed") from None
        stdout = completed.stdout
        if not isinstance(stdout, str) or len(stdout) > MAX_RESPONSE_CHARS:
            raise CheckFailure("unknown_response", "blocked_fixture" if cloud else "blocked_runtime")
        if cloud:
            data = structured_response(stdout)
            error_class = response_error(data)
            if error_class:
                status = ("blocked_authentication" if error_class == "authentication_unavailable"
                          else "blocked_runtime" if error_class in ("response_schema_mismatch", "internal_response")
                          else "blocked_fixture")
                raise CheckFailure(error_class, status)
        if completed.returncode != 0:
            raise CheckFailure("cloud_read_failed" if cloud else "local_version_failed", "blocked_fixture" if cloud else "blocked_runtime")
        return stdout


def check_version(stdout: str, minimum: tuple[int, int, int]) -> str:
    match = re.search(r"(?<![a-zA-Z0-9])v?([0-9]{1,6})\.([0-9]{1,6})\.([0-9]{1,6})\b", stdout)
    if not match:
        raise CheckFailure("unknown_version")
    version = tuple(int(value) for value in match.groups())
    if version < minimum:
        raise CheckFailure("unsupported_version")
    return ".".join(str(value) for value in version)


def check_identity(data: dict[str, Any]) -> None:
    # DomainCLI 0.9.4 auth_status contract: verified STS identity is top-level,
    # not a nested local-profile object. Readiness is independent of auth mode.
    if (data.get("ok") is not True or data.get("action") != "auth_status"
            or data.get("status") != "authenticated" or data.get("identity_verified") is not True
            or data.get("identity_scope") != "cloud_account"):
        raise CheckFailure("cloud_identity_unverified", "blocked_authentication")
    account = data.get("account_id")
    principal = data.get("principal_id") or data.get("user_id")
    if not isinstance(account, str) or not re.fullmatch(r"[0-9]{1,32}", account):
        raise CheckFailure("cloud_identity_unverified", "blocked_authentication")
    if not isinstance(principal, str) or not principal.strip():
        raise CheckFailure("cloud_identity_unverified", "blocked_authentication")


def check_domain(data: dict[str, Any], target: str) -> None:
    name = data.get("domain")
    if not isinstance(name, str):
        raise CheckFailure("unknown_response", "blocked_fixture")
    try:
        actual = normalize_fqdn(name)
    except CheckFailure:
        raise CheckFailure("target_mismatch", "blocked_fixture") from None
    if actual != target:
        raise CheckFailure("target_mismatch", "blocked_fixture")
    if not any(isinstance(data.get(key), str) and data[key].strip() for key in ("status", "instance_id")):
        raise CheckFailure("unknown_response", "blocked_fixture")


def check_dns(data: dict[str, Any], target: str, record_type: str | None = None) -> tuple[int, bool]:
    # The 0.9.4 dns_list contract counts returned records, not total records.
    # Do not turn historical API-shaped total_count/rr objects into readiness.
    if (data.get("action") != "dns_list" or data.get("status") != "completed"
            or data.get("product") != "alidns"):
        raise CheckFailure("unknown_response", "blocked_fixture")
    name = data.get("domain")
    if not isinstance(name, str):
        raise CheckFailure("unknown_response", "blocked_fixture")
    try:
        actual = normalize_fqdn(name)
    except CheckFailure:
        raise CheckFailure("target_mismatch", "blocked_fixture") from None
    if actual != target:
        raise CheckFailure("target_mismatch", "blocked_fixture")
    records = data.get("records")
    count = data.get("count")
    if not isinstance(records, list) or isinstance(count, bool) or not isinstance(count, int) or count != len(records):
        raise CheckFailure("unknown_response", "blocked_fixture")
    for record in records:
        if not isinstance(record, dict) or not record:
            raise CheckFailure("unknown_response", "blocked_fixture")
        if not isinstance(record.get("record_id"), str) or not record["record_id"]:
            raise CheckFailure("unknown_response", "blocked_fixture")
        if record.get("type") not in DNS_RECORD_TYPES:
            raise CheckFailure("unknown_response", "blocked_fixture")
        if record_type is not None and record["type"] != record_type:
            raise CheckFailure("record_type_mismatch", "blocked_fixture")
        if record_type == "A":
            if not isinstance(record.get("value"), str):
                raise CheckFailure("dns_record_value_invalid", "blocked_fixture")
            try:
                ipaddress.IPv4Address(record.get("value"))
            except (ValueError, TypeError):
                raise CheckFailure("dns_record_value_invalid", "blocked_fixture") from None
        if not isinstance(record.get("host"), str) or not record["host"]:
            raise CheckFailure("unknown_response", "blocked_fixture")
        try:
            record_domain = normalize_fqdn(record.get("domain"))
        except CheckFailure:
            raise CheckFailure("unknown_response", "blocked_fixture") from None
        if record_domain != target:
            raise CheckFailure("target_mismatch", "blocked_fixture")
    return count, any(record_type is None or record["type"] == record_type for record in records)


def report_template() -> dict[str, Any]:
    return {
        "schema_version": 1, "status": "not_checked", "error_class": None,
        "local_ready": False, "cloud_checked": False, "cloud_identity_verified": False,
        "fixture_ready": False, "domain_fixture_ready": False, "dns_fixture_ready": False,
        "fixture_file_checked": False,
        "dns_zone_accessible": False, "dns_record_fixture_ready": False,
        "checks": {}, "metadata": {"script": "eval_domain_preflight", "read_only": True,
                                   "timeout_seconds": {"local": LOCAL_TIMEOUT, "cloud": CLOUD_TIMEOUT, "total": TOTAL_TIMEOUT}},
    }


def evaluate(argv: Sequence[str] | None = None, *, runner: Callable[..., Any] | None = None,
             clock: Callable[[], float] | None = None, manifest: Path = MANIFEST) -> tuple[dict[str, Any], int]:
    report = report_template()
    try:
        args = parser().parse_args(argv)
        for selector in (args.profile, args.config_path, args.cli):
            validate_selector(selector)
        loaded = load_fixture_file(args.fixture_file) if args.fixture_file is not None else {}
        report["fixture_file_checked"] = args.fixture_file is not None
        report["metadata"]["fixture_source"] = "locator_file" if args.fixture_file is not None else "arguments"
        if args.domain_key is not None and args.fixture_file is None:
            raise CheckFailure("missing_fixture_file", "invalid_input")
        if args.domain_key is not None and args.domain_key not in loaded:
            raise CheckFailure("fixture_identifier_missing", "blocked_fixture")
        domain_key = args.domain_key or "asset_domain"
        if args.domain_key is not None or args.domain is not None:
            args.domain = merge_fixture_target(args.domain, loaded.get(domain_key))
        if args.dns_zone_from_fixture:
            if args.fixture_file is None:
                raise CheckFailure("missing_fixture_file", "invalid_input")
            if "dns_zone" not in loaded:
                raise CheckFailure("fixture_identifier_missing", "blocked_fixture")
        if args.dns_zone_from_fixture or args.dns_zone is not None:
            args.dns_zone = merge_fixture_target(args.dns_zone, loaded.get("dns_zone"))
        if args.check_cloud and not (args.domain or args.dns_zone):
            raise CheckFailure("missing_fixture_identifier", "invalid_input")
        if args.require_record and not (args.check_cloud and args.dns_zone):
            raise CheckFailure("missing_dns_record_scope", "invalid_input")
        if args.record_type is not None and not args.require_record:
            raise CheckFailure("missing_dns_record_requirement", "invalid_input")
        domain = normalize_fqdn(args.domain) if args.domain is not None else None
        dns_zone = normalize_fqdn(args.dns_zone) if args.dns_zone is not None else None
        report["metadata"]["cli_selection"] = "explicit" if args.cli is not None else "PATH"
        report["metadata"]["requested_fixtures"] = {"domain": domain is not None, "dns_zone": dns_zone is not None}
        report["metadata"]["fixture_readiness_scope"] = "selected_targets_only"
        report["metadata"]["domain_eligibility_checked"] = False
        if args.record_type is not None:
            report["metadata"]["required_dns_record_type"] = args.record_type
        attribution = load_attribution(manifest)
        # Activation attribution stays in transport memory, never a report or
        # artifact field that a runner might persist as an execution log.
        report["metadata"]["skill"] = {key: attribution[key] for key in ("name", "version")}
        cli = resolve_cli(args.cli)
        checker = Checker(cli, attribution, args, runner or subprocess.run, clock or time.monotonic)
        report["metadata"]["parent_cli_version"] = check_version(checker.invoke("version"), MIN_PARENT_VERSION)
        report["checks"]["parent_version"] = "passed"
        report["metadata"]["domain_cli_version"] = check_version(checker.invoke("domain", "version"), MIN_DOMAIN_VERSION)
        report["checks"]["domain_version"] = "passed"
        report["local_ready"] = True
        if not args.check_cloud:
            report["status"] = "local_only"
            if args.require_ready:
                report["error_class"] = "cloud_check_required"
                return report, 1
            return report, 0
        report["cloud_checked"] = True
        check_identity(structured_response(checker.invoke("domain", "whoami", cloud=True)))
        report["cloud_identity_verified"] = True
        report["checks"]["cloud_identity"] = "passed"
        # Keep registrar and DNS fixture checks separate. A registrar miss cannot
        # suppress the independent exact hosted-zone read.
        failures: list[CheckFailure] = []
        for fixture, target in (("domain", domain), ("dns", dns_zone)):
            if target is None:
                continue
            try:
                if fixture == "domain":
                    check_domain(structured_response(checker.invoke("domain", "detail", "--domain", target, "--view", "summary", cloud=True)), target)
                    report["domain_fixture_ready"] = True
                else:
                    dns_arguments = ["domain", "dns", "list", "--domain", target]
                    if args.record_type is not None:
                        dns_arguments.extend(["--type", args.record_type])
                    report["metadata"]["dns_record_search_scope"] = "returned_page_only"
                    count, record_ready = check_dns(structured_response(checker.invoke(*dns_arguments, cloud=True)), target, args.record_type)
                    report["dns_zone_accessible"] = True
                    report["dns_record_fixture_ready"] = record_ready
                    report["metadata"]["dns_returned_record_count"] = count
                    if args.require_record and not record_ready:
                        raise CheckFailure("dns_record_fixture_missing", "blocked_fixture")
                    report["dns_fixture_ready"] = True
                report["checks"][fixture + "_fixture"] = "passed"
            except CheckFailure as failure:
                report["checks"][fixture + "_fixture"] = {"status": failure.status, "error_class": failure.error_class}
                failures.append(failure)
                if failure.status in ("blocked_authentication", "blocked_timeout"):
                    break
        if failures:
            raise failures[0]
        report["fixture_ready"] = True
        report["status"] = "ready"
        return report, 0
    except CheckFailure as failure:
        report["status"] = failure.status
        report["error_class"] = failure.error_class
        return report, 2 if failure.status == "invalid_input" else 1
    except Exception:
        # Unexpected exceptions must not expose argv, credential/PII payloads,
        # filesystem locations, or the subprocess exception's raw output.
        report["status"] = "blocked_runtime"
        report["error_class"] = "internal_error"
        return report, 1


def main(argv: Sequence[str] | None = None) -> int:
    report, code = evaluate(argv)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
