#!/usr/bin/env python3
"""DSC RPC transport using an explicit Alibaba Cloud CLI credential profile.

Python never loads, exports, or signs with cloud credentials. CLI owns signing
and supported refresh flows. Only the non-secret profile mode is inspected.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


DEFAULT_PROFILE = "dsc-oauth"
SUPPORTED_AUTH_MODES = frozenset({"OAuth", "AK", "StsToken", "RamRoleArn"})
MIN_CLI_VERSION = (3, 4, 10)
STS_COMPAT_CLI_VERSION = (3, 3, 23)
CLI_REQUIREMENT = "CLI >= 3.4.10 (or exactly 3.3.23 with StsToken)"
SKILL_NAME = "alibabacloud-dsc-column-encryption"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "references" / "manifest.json"
SESSION_ID_ENV = "ALIBABA_CLOUD_SKILL_SESSION_ID"
_PROCESS_SESSION_ID = uuid.uuid4().hex
WRITE_ACTIONS = frozenset({
    "CreateDataMaskingRule", "DeleteDataMaskingRule", "UpdateDataMaskingUsers",
    "UpdateDataMaskingEncryptionAlgorithm", "SyncDataAssets", "UpgradeKernelVersion",
})
REGION_RE = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
PROFILE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
ACTION_RE = re.compile(r"[A-Z][A-Za-z0-9]*\Z")
FIELD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.]*\Z")
SESSION_ID_RE = re.compile(r"[0-9a-f]{32}\Z")
SEMVER_RE = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z"
)


class CliError(RuntimeError):
    """An intentionally bounded error; never contains raw CLI output."""

    def __init__(self, message: str, *, http_status: Optional[int] = None,
                 error_code: Optional[str] = None,
                 definite_rejection: bool = False):
        super().__init__(message)
        self.http_status = http_status
        self.error_code = error_code
        self.definite_rejection = definite_rejection


@dataclass(frozen=True)
class CliProfile:
    name: str
    mode: str = "OAuth"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not PROFILE_RE.fullmatch(self.name):
            raise CliError("CLI profile name must contain letters, digits, dots, underscores or hyphens",
                           definite_rejection=True)
        if not isinstance(self.mode, str) or self.mode not in SUPPORTED_AUTH_MODES:
            raise CliError("Supported CLI profile modes are OAuth, AK, StsToken and RamRoleArn",
                           definite_rejection=True)


def skill_user_agent() -> str:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise CliError("Skill manifest is missing or invalid; restore references/manifest.json",
                       definite_rejection=True) from None
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if (not isinstance(manifest, dict) or manifest.get("name") != SKILL_NAME
            or not isinstance(version, str) or len(version) > 128
            or not SEMVER_RE.fullmatch(version)):
        raise CliError("Skill manifest must contain the canonical skill name and a valid semantic version",
                       definite_rejection=True)
    # A process shares its generated ID across all clients and API products.
    # Set this non-secret override before invoking separate script commands
    # when they belong to the same logical session.
    session_id = os.environ.get(SESSION_ID_ENV, _PROCESS_SESSION_ID)
    if not SESSION_ID_RE.fullmatch(session_id):
        raise CliError(f"{SESSION_ID_ENV} must contain exactly 32 lowercase hexadecimal characters",
                       definite_rejection=True)
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id} skill-version/{version}"


def cli_environment() -> dict[str, str]:
    # A previously exported AK, STS token, default profile, endpoint, or debug
    # switch must not override the selected profile. Preserve HOME/PATH
    # and normal proxy settings so CLI can reach its own config and endpoints.
    result = {name: value for name, value in os.environ.items()
              if not name.upper().startswith(("ALIBABA_CLOUD_", "ALIBABACLOUD_", "ALIYUN_", "ALICLOUD_"))
              and name.upper() not in {"ACCESS_KEY_ID", "ACCESS_KEY_SECRET", "SECURITY_TOKEN"}}
    # CLI's native Mock interceptor runs before RPC dispatch. Removing its
    # platform-provided controls silently turns an evaluation into a live call.
    # Preserve only these exact non-credential keys; never enable Mock ourselves
    # or forward arbitrary cloud-prefixed settings (identity/endpoint/debug).
    for name in ("ALIBABA_CLOUD_CLI_MOCK", "ALIBABA_CLOUD_CLI_MOCK_PATH"):
        if name in os.environ:
            result[name] = os.environ[name]
    # CLI has a throttling loop in addition to the underlying SDK retry count.
    result["ALIBABA_CLOUD_THROTTLING_RETRY_ENABLED"] = "false"
    return result


def _run(argv: Sequence[str], *, timeout: int = 75) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(list(argv), stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", check=False,
                              timeout=timeout, env=cli_environment())
    except subprocess.TimeoutExpired:
        raise CliError("Alibaba Cloud CLI timed out; the API outcome may be unknown. Do not retry a write") from None
    except OSError:
        raise CliError("Could not start Alibaba Cloud CLI; check its installation") from None


def _executable() -> str:
    executable = shutil.which("aliyun")
    if not executable:
        raise CliError(f"Alibaba Cloud {CLI_REQUIREMENT} is required; install it before online use")
    return executable


def check_version(executable: str) -> str:
    result = _run([executable, "version"], timeout=15)
    match = re.fullmatch(r"\s*(\d+)\.(\d+)\.(\d+)\s*", result.stdout)
    if result.returncode or not match:
        raise CliError(f"Could not verify Alibaba Cloud CLI version; {CLI_REQUIREMENT} is required")
    version = tuple(int(part) for part in match.groups())
    if version < MIN_CLI_VERSION and version != STS_COMPAT_CLI_VERSION:
        detected = ".".join(match.groups())
        raise CliError(
            f"Alibaba Cloud {CLI_REQUIREMENT} is required; detected {detected}; "
            "update the CLI in the execution sandbox before using this skill"
        )
    return ".".join(match.groups())


def read_profile_mode(executable: str, profile: CliProfile) -> str:
    result = _run([executable, "configure", "get", "mode", "--profile", profile.name], timeout=15)
    # Read exactly one non-secret property, not configure get/list output or
    # ~/.aliyun/config.json (which can contain cached OAuth refresh tokens).
    modes = {f"mode={mode}": mode for mode in SUPPORTED_AUTH_MODES}
    mode = modes.get(result.stdout.strip())
    if result.returncode or mode is None:
        raise CliError(
            f"Profile '{profile.name}' is missing or its mode is unsupported. "
            "Configure the selected OAuth, AK, StsToken or RamRoleArn profile outside this session; "
            "see references/runtime-constraints.md. Credential and profile fallback is disabled",
            definite_rejection=True,
        )
    return mode


def check_profile_mode(executable: str, profile: CliProfile) -> None:
    if read_profile_mode(executable, profile) != profile.mode:
        raise CliError(
            "The selected CLI profile mode changed during this workflow. "
            "Recheck targets and repeat preflight before executing; this API call was not submitted",
            definite_rejection=True,
        )


def resolve_profile(name: str = DEFAULT_PROFILE) -> CliProfile:
    profile = CliProfile(name)
    executable = _executable()
    version = check_version(executable)
    mode = read_profile_mode(executable, profile)
    # Only this exact old release and preconfigured temporary-credential mode
    # have been exercised with the forced-RPC transport. No identity fallback.
    if version == "3.3.23" and mode != "StsToken":
        raise CliError(
            f"CLI 3.3.23 compatibility supports StsToken only; selected mode is {mode}. "
            "Use CLI >= 3.4.10 for this profile; do not switch identity automatically",
            definite_rejection=True,
        )
    return CliProfile(name, mode)


def request_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def command_args(executable: str, profile: CliProfile, region: str, product: str,
                 version: str, action: str, params: Mapping[str, Any]) -> list[str]:
    if not REGION_RE.fullmatch(region):
        raise CliError("Invalid API region", definite_rejection=True)
    if (product, version) not in {("sddp", "2026-01-20"), ("kms", "2016-01-20")}:
        raise CliError("Only DSC 2026-01-20 and KMS 2016-01-20 RPC APIs are supported", definite_rejection=True)
    if not ACTION_RE.fullmatch(action):
        raise CliError("RPC Action must use its exact PascalCase name", definite_rejection=True)
    # CLI 3.4.10 rejects the new version for bundled "sddp" even with --force.
    # An unregistered dispatch token selects generic RPC; the real endpoint and
    # API version remain explicit below. KMS keeps its existing metadata route.
    cli_product = "sddp-2026" if product == "sddp" else product
    # PascalCase preserves legacy RPC dispatch, including APIs absent from the
    # bundled metadata. --force skips metadata checks, never authorization.
    # Do NOT add --mode: in CLI 3.4.10 that can suppress timeout/retry overrides.
    argv = [executable, cli_product, action, "--profile", profile.name,
            "--region", region, "--endpoint", f"{product}.{region}.aliyuncs.com",
            "--version", version, "--method", "POST", "--secure", "--force",
            "--auto-plugin-install", "false", "--retry-count", "0",
            "--connect-timeout", "10", "--read-timeout", "45",
            "--user-agent", skill_user_agent()]
    if action in WRITE_ACTIONS:
        # The caller's --execute path already verifies the approved plan token.
        argv.append("--yes")
    for name, value in params.items():
        if not isinstance(name, str) or not FIELD_RE.fullmatch(name) or not name[0].isupper():
            raise CliError("Invalid RPC parameter name", definite_rejection=True)
        if value is not None:
            argv.extend([f"--{name}", request_value(value)])
    return argv


def _api_error(action: str, output: str) -> CliError:
    # CLI diagnostics may contain signed URLs, token material, or full command
    # lines. Never include raw stdout/stderr, Messages, or Recommendation links.
    status_match = re.search(r"(?im)^\s*(?:HTTPStatus|HttpStatus|StatusCode|HTTP Status)[\s:=]+(\d{3})\s*$", output)
    status = int(status_match[1]) if status_match else None
    code_match = re.search(r"(?im)^\s*(?:ErrorCode|Code)[\s:=]+([A-Za-z][A-Za-z0-9_.-]{0,127})\s*$", output)
    code = code_match[1] if code_match else None
    suffix = f" (Code={code})" if code else ""
    return CliError(
        f"{action} failed in Alibaba Cloud CLI{suffix}. Check the selected profile credentials, RAM permissions and API parameters; "
        "raw CLI diagnostics are withheld. Do not retry a write before checking its state",
        http_status=status,
        error_code=code,
        definite_rejection=status is not None and 400 <= status < 500 and status != 408,
    )


def safe_error(exc: Exception) -> str:
    if isinstance(exc, (subprocess.SubprocessError, OSError)):
        return "CLI execution failed; raw process details are withheld. Verify state before retrying a write"
    return str(exc)


def safe_error_fields(exc: Exception) -> dict[str, Any]:
    """Expose only bounded CLI status/code, never raw diagnostics or guessed fields."""
    if not isinstance(exc, CliError):
        return {}
    result: dict[str, Any] = {}
    if type(exc.http_status) is int and 100 <= exc.http_status <= 599:
        result["HTTPStatus"] = exc.http_status
    if isinstance(exc.error_code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,127}", exc.error_code):
        result["ErrorCode"] = exc.error_code
    return result


def print_safe_error_diagnostics(exc: Exception, *, file: Any) -> None:
    """Render validated status/code as CLI-style lines, never raw output."""
    for name, value in safe_error_fields(exc).items():
        print(f"{name}: {value}", file=file, flush=True)


class AliyunCliClient:
    def __init__(self, profile: CliProfile, region: str):
        self.profile = profile
        self.region = region
        self.executable = _executable()

    def call(self, region: str, product: str, version: str, action: str,
             params: Mapping[str, Any]) -> dict[str, Any]:
        argv = command_args(self.executable, self.profile, region, product, version, action, params)
        check_profile_mode(self.executable, self.profile)
        result = _run(argv)
        if result.returncode:
            raise _api_error(action, result.stdout + "\n" + result.stderr)
        try:
            response = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise CliError(f"{action} returned invalid JSON; outcome may be unknown. Raw output is withheld") from None
        if not isinstance(response, dict):
            raise CliError(f"{action} returned a non-object response; outcome may be unknown")
        return response


def build_client(profile: CliProfile, region: str) -> AliyunCliClient:
    return AliyunCliClient(profile, region)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check the selected CLI profile mode without reading credentials or calling cloud APIs")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    args = parser.parse_args(argv)
    try:
        profile = resolve_profile(args.profile)
        result = {"Profile": profile.name, "Mode": profile.mode, "Configured": True,
                  "CloudAccessVerified": False,
                  "NextStep": "Run a read-only DSC query to verify login and permissions"}
        code = 0
    except CliError as exc:
        result = {"Configured": False, "Error": safe_error(exc)}
        code = 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
