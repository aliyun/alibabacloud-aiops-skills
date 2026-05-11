#!/usr/bin/env python3
"""
load_env.py — Alibaba Cloud OSS Media Processing Skill environment variable loader

Purpose:
  Scan platform-specific configuration files or storage for environment
  variables and load them into os.environ (without overwriting existing values).

  Unix-like systems scan these files (first file containing any target var is loaded):
    /etc/environment
    /etc/profile
    ~/.bashrc
    ~/.profile
    ~/.bash_profile
    ~/.zshrc
    ~/.env

  Windows systems scan these files:
    %USERPROFILE%\\.env
    %USERPROFILE%\\alibaba.env

  Target variables (a file is loaded if it contains any of these):
    ALIBABA_CLOUD_OSS_BUCKET
    ALIBABA_CLOUD_OSS_REGION

Usage (call from other scripts):
    from load_env import ensure_env_loaded
    ensure_env_loaded()

Standalone (diagnostic mode):
    python load_env.py              # Load and check
    python load_env.py --check-only # Check current state only
    python load_env.py --verbose    # Show detailed load log
    python load_env.py --verify-imm # Verify IMM project and bucket binding
"""

import json
import importlib.metadata
import os
import platform
import re
import sys
from typing import Tuple

# Ensure sibling modules (check_permissions, etc.) are importable
# regardless of the working directory when invoked via absolute path.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from permission_checks import check_imm_permission, check_oss_permission

# Target variables to look for
_TARGET_VARS = {
    "ALIBABA_CLOUD_OSS_BUCKET",
    "ALIBABA_CLOUD_OSS_REGION",
}

# Platform-specific configuration files
_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    _ENV_FILES = [
        os.path.join(os.environ.get("USERPROFILE", ""), ".env"),
        os.path.join(os.environ.get("USERPROFILE", ""), "alibaba.env"),
    ]
else:
    _ENV_FILES = [
        "/etc/environment",
        "/etc/profile",
        os.path.expanduser("~/.bashrc"),
        os.path.expanduser("~/.profile"),
        os.path.expanduser("~/.bash_profile"),
        os.path.expanduser("~/.zshrc"),
        os.path.expanduser("~/.env"),
    ]

# KEY=VALUE line pattern (supports quoted values, optional "export" prefix)
_KV_RE = re.compile(
    r"""^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(['"]?)(.*?)\2\s*$"""
)


# Pattern to match $VAR or ${VAR} references in values
_VAR_REF_RE = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)')
_REQUIREMENT_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)\s*$")
_REQUIREMENTS_FILE = os.path.join(_SCRIPT_DIR, "requirements.txt")


def _safe_display(key, value):
    """Return a safe display of a value."""
    _ = key
    return value


def _read_pinned_requirements() -> list[tuple[str, str]]:
    """Read pinned requirements from scripts/requirements.txt."""
    requirements = []
    try:
        with open(_REQUIREMENTS_FILE, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                match = _REQUIREMENT_RE.match(line)
                if match:
                    requirements.append((match.group(1), match.group(2)))
    except OSError:
        pass
    return requirements


def _check_required_python_packages() -> Tuple[bool, str]:
    """Verify that pinned requirements are installed at the expected versions."""
    requirements = _read_pinned_requirements()
    if not requirements:
        return False, (
            "Could not read pinned Python requirements from "
            f"{_REQUIREMENTS_FILE}."
        )

    missing_or_mismatched = []
    for package_name, expected_version in requirements:
        try:
            installed_version = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            missing_or_mismatched.append(
                f"{package_name}=={expected_version} (not installed)"
            )
            continue

        if installed_version != expected_version:
            missing_or_mismatched.append(
                f"{package_name}=={expected_version} "
                f"(installed: {installed_version})"
            )

    if missing_or_mismatched:
        return False, (
            "Python package requirements are not satisfied: "
            + ", ".join(missing_or_mismatched)
            + ". Install with: pip install -r scripts/requirements.txt"
        )

    return True, ""


def _expand_vars(value: str, local_vars: dict) -> str:
    """
    Expand $VAR and ${VAR} references in a value string.
    Resolution order: local_vars (same file) → os.environ.
    Returns the original reference unexpanded if the variable is not found.
    """
    def _replace(m):
        var_name = m.group(1) or m.group(2)
        # Look up in local file variables first, then os.environ
        if var_name in local_vars:
            return local_vars[var_name]
        env_val = os.environ.get(var_name, "")
        if env_val:
            return env_val
        # Variable not found anywhere — return empty string
        return ""
    return _VAR_REF_RE.sub(_replace, value)


def _parse_env_file(filepath: str) -> dict:
    """
    Parse a shell-style environment file, returning {key: value}.
    Supports:
      KEY=value
      export KEY=value
      KEY="value with spaces"
      KEY='value'
      KEY=$OTHER_VAR  (variable expansion from same file or os.environ)
      # comment lines (ignored)
    """
    result = {}
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n\r")
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                m = _KV_RE.match(line)
                if m:
                    key = m.group(1)
                    raw_value = m.group(3)
                    quote_char = m.group(2)
                    # Only expand variables in unquoted or double-quoted values
                    # Single-quoted values are literal (shell convention)
                    if quote_char != "'" and _VAR_REF_RE.search(raw_value):
                        value = _expand_vars(raw_value, result)
                    else:
                        value = raw_value
                    result[key] = value
    except (OSError, IOError):
        pass
    return result


def _file_contains_target(parsed: dict) -> bool:
    """Return True if parsed dict contains at least one target variable."""
    return bool(_TARGET_VARS & set(parsed.keys()))


def load_env_files(verbose: bool = False) -> dict:
    """
    Scan platform-specific configuration files and load target variables
    into os.environ. Existing variables are not overwritten (setdefault semantics).

    Returns: dict of newly loaded variables {key: value}.
    """
    newly_loaded = {}

    # Scan configuration files
    for filepath in _ENV_FILES:
        if not os.path.isfile(filepath):
            if verbose:
                print(
                    f"[load_env] Skipped (not found): {filepath}",
                    file=sys.stderr,
                )
            continue

        parsed = _parse_env_file(filepath)

        if not _file_contains_target(parsed):
            if verbose:
                print(
                    f"[load_env] Skipped (no target vars): {filepath}",
                    file=sys.stderr,
                )
            continue

        if verbose:
            print(f"[load_env] Loading file: {filepath}", file=sys.stderr)

        for key, value in parsed.items():
            # Only load target variables
            if key not in _TARGET_VARS:
                continue
            if key not in os.environ:
                os.environ[key] = value
                newly_loaded[key] = value
                if verbose:
                    print(
                        f"[load_env]   Set {key}={_safe_display(key, value)}",
                        file=sys.stderr,
                    )
            elif verbose:
                print(
                    f"[load_env]   Skipped (already set): {key}",
                    file=sys.stderr,
                )

    return newly_loaded


def check_required_vars(required: list = None) -> list:
    """
    Check whether required environment variables are set.
    Returns a list of missing variable names (empty means all are set).
    """
    if required is None:
        required = [
            "ALIBABA_CLOUD_OSS_BUCKET",
            "ALIBABA_CLOUD_OSS_REGION",
        ]
    return [k for k in required if not os.environ.get(k)]


_VAR_DESCRIPTIONS = {
    "ALIBABA_CLOUD_OSS_BUCKET": "your OSS bucket name",
    "ALIBABA_CLOUD_OSS_REGION": "bucket region, e.g. cn-hangzhou",
}


def _print_setup_hint(missing_vars: list) -> None:
    """Print detailed setup guidance when environment variables are missing."""
    missing_str = "\n".join(
        f"    {k}=<{_VAR_DESCRIPTIONS.get(k, 'your_value')}>"
        for k in missing_vars
    )

    if _IS_WINDOWS:
        config_example = (
            "  Example (set in System Properties → Environment Variables, or "
            "add to %USERPROFILE%\\.env):\n"
            "    ALIBABA_CLOUD_OSS_BUCKET=<your bucket name>\n"
            "    ALIBABA_CLOUD_OSS_REGION=<your bucket region, e.g. cn-hangzhou>\n"
        )
        imm_note = (
            "  Note: IMM project is auto-detected from bucket binding.\n"
            "  Run: python scripts/imm_admin.py auto-setup\n"
        )
        config_files_hint = (
            f"    - %USERPROFILE%\\.env\n"
            f"    - %USERPROFILE%\\alibaba.env\n"
            "  Or set via System Properties → Environment Variables (user-level).\n"
        )
    else:
        config_example = (
            "  Example (using ~/.profile):\n"
            "    export ALIBABA_CLOUD_OSS_BUCKET=<your bucket name>\n"
            "    export ALIBABA_CLOUD_OSS_REGION=<your bucket region, e.g. cn-hangzhou>\n"
        )
        imm_note = (
            "  Note: IMM project is auto-detected from bucket binding.\n"
            "  Run: python scripts/imm_admin.py auto-setup\n"
        )
        config_files_hint = "\n".join(f"    - {f}" for f in _ENV_FILES) + "\n"

    hint = f"""
============================================================
  Alibaba Cloud OSS Media Processing — Environment Variables Not Configured
============================================================

The following environment variables are missing:
{missing_str}

【Obtain Credentials】
  Use Aliyun CLI to configure credentials:
    aliyun configure
  This stores credentials in ~/.aliyun/config.json and is automatically
  discovered by the alibabacloud-credentials SDK.

【Obtain Bucket and Region】
  OSS Console: https://oss.console.aliyun.com/bucket
  Bucket name and region (e.g., cn-hangzhou) are shown in the console.

【Activate IMM Service】
  (Required for image-intelligent operations: blind watermark, face/body/car
   detection, QR code recognition, image labeling, quality scoring.)
  IMM Console: https://imm.console.aliyun.com
  Create a Project and bind it to your OSS bucket before use.

【Pricing】
  Basic image processing: https://help.aliyun.com/zh/oss/data-processing-fees
  Image-intelligent (IMM): https://help.aliyun.com/zh/imm/product-overview/billable-items

【Configuration】Add the variables above to one of these files, then retry:
{config_files_hint}
{config_example}
{imm_note}  Security note: Configure credentials via secure channels (e.g., editing
  config files directly). Do not commit secrets to code repositories or
  share them with others.

After configuration, please retry.
"""
    print(hint, file=sys.stderr)


def ensure_env_loaded(
    required: list = None,
    verbose: bool = False,
) -> bool:
    """
    Ensure required environment variables are loaded.

    Flow:
      1. Check if required variables are already in os.environ.
      2. If missing, scan platform-specific sources and load them.
      3. Re-check; return True if all required variables are present.

    Args:
      required  — list of required variable names (default: AK/SK/bucket/region).
      verbose   — whether to print load logs to stderr.

    Returns: True if all required variables are present, False otherwise.
    """
    if required is None:
        required = [
            "ALIBABA_CLOUD_OSS_BUCKET",
            "ALIBABA_CLOUD_OSS_REGION",
        ]

    missing_before = check_required_vars(required)
    if not missing_before:
        return True

    if verbose:
        print(
            f"[load_env] Missing variables detected: {missing_before}, "
            f"scanning environment sources...",
            file=sys.stderr,
        )

    load_env_files(verbose=verbose)

    missing_after = check_required_vars(required)
    if missing_after:
        return False

    if verbose:
        print("[load_env] All required variables loaded.", file=sys.stderr)
    return True


def verify_imm() -> bool:
    """
    Verify IMM setup: auto-detect project from bucket binding via IMM API.
    Returns True if bucket is bound to an IMM project, False otherwise.
    Requires: ALIBABA_CLOUD_OSS_REGION, ALIBABA_CLOUD_OSS_BUCKET
    """
    bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    region = os.environ.get("ALIBABA_CLOUD_OSS_REGION", "")

    missing = []
    if not bucket:
        missing.append("ALIBABA_CLOUD_OSS_BUCKET")
    if not region:
        missing.append("ALIBABA_CLOUD_OSS_REGION")

    if missing:
        print(
            f"[verify-imm] Missing required variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        return False

    try:
        from alibabacloud_imm20200930.client import Client
        from alibabacloud_imm20200930 import models
        from alibabacloud_tea_openapi.models import Config
    except ImportError:
        print(
            "[verify-imm] IMM SDK not installed. Install with:\n"
            "  pip install alibabacloud_imm20200930==4.8.2 alibabacloud_tea_openapi==0.4.4",
            file=sys.stderr,
        )
        return False

    import credential
    credential_client = credential.get_credential_client(required=False)
    if credential_client is None:
        print("[verify-imm] AccessKey not configured.", file=sys.stderr)
        return False

    imm_region = region.replace("oss-", "")

    config = Config(
        credential=credential_client,
        endpoint=f"imm.{imm_region}.aliyuncs.com",
        region_id=imm_region,
        user_agent=credential.USER_AGENT,
    )
    client = Client(config)

    print(f"[verify-imm] Checking IMM binding for bucket '{bucket}'...")

    all_pass = True

    # Query bucket binding (auto-detect project)
    try:
        attach_req = models.GetOSSBucketAttachmentRequest()
        attach_req.ossbucket = bucket
        resp = client.get_ossbucket_attachment(attach_req)
        bound_project = None
        if resp.body:
            body_map = resp.body.to_map() if hasattr(resp.body, "to_map") else {}
            bound_project = (
                body_map.get("ProjectName")
                or body_map.get("project_name")
            )
        if bound_project:
            print(f"  [PASS] Bucket '{bucket}' is bound to IMM project '{bound_project}'.")
        else:
            print(f"  [FAIL] Bucket '{bucket}' is not bound to any IMM project.")
            all_pass = False
    except Exception as exc:
        print(f"  [FAIL] Bucket binding check failed: {exc}")
        all_pass = False

    if all_pass:
        print("[verify-imm] All checks passed.")
    else:
        print("[verify-imm] Some checks failed. Review the output above.")
    return all_pass


def _check_oss_permission(bucket: str, region: str) -> tuple:
    """Compatibility wrapper around the shared OSS permission check."""
    return check_oss_permission(bucket, region)


def _check_imm_permission(project: str, region: str) -> tuple:
    """Compatibility wrapper around the shared IMM permission check."""
    ok, error = check_imm_permission(project, region)
    if ok is None:
        return True, ""
    return ok, error


def _check_python_credentials() -> Tuple[bool, str]:
    """Verify that the Python SDK default credential chain is usable."""
    import credential

    if credential.ensure_credentials(required=False):
        return True, ""

    details = [
        "Python SDK could not load Alibaba Cloud credentials from the default chain.",
        "Confirm that the current process can access the same Aliyun CLI profile shown by `aliyun configure list`.",
    ]

    has_env_ak = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    has_env_sk = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    has_env_token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN")
    if (has_env_ak or has_env_sk) and not has_env_token:
        details.append(
            "If you are using STS environment variables, you must also set "
            "ALIBABA_CLOUD_SECURITY_TOKEN."
        )

    return False, " ".join(details)


def _generate_policy(bucket: str, include_imm: bool = False) -> dict:
    """Generate a ready-to-use RAM policy JSON with bucket-scoped Resource.
    When include_imm is True, IMM actions are appended."""
    oss_actions = [
        "oss:GetObject",
        "oss:PutObject",
        "oss:ProcessObject",
        "oss:DeleteObject",
        "oss:SignUrl",
        "oss:GetBucketInfo",
    ]
    statements = [
        {
            "Effect": "Allow",
            "Action": oss_actions,
            "Resource": [
                f"acs:oss:*:*:{bucket}",
                f"acs:oss:*:*:{bucket}/*",
            ],
        }
    ]
    if include_imm:
        statements.append({
            "Effect": "Allow",
            "Action": [
                "imm:CreateDecodeBlindWatermarkTask",
                "imm:GetTask",
                "imm:GetDecodeBlindWatermarkResult",
                "imm:GetProject",
            ],
            "Resource": "*",
        })
    return {"Version": "1", "Statement": statements}


# ─── Standalone: diagnostic mode ────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan environment sources and load Alibaba Cloud OSS "
                    "Media Processing variables (diagnostic mode)."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed load log."
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Only check current environment variable state, do not load."
    )
    parser.add_argument(
        "--verify-imm", action="store_true",
        help="Verify IMM project existence and bucket binding via IMM API."
    )
    parser.add_argument(
        "--check-permissions", action="store_true",
        help="Check RAM permissions for OSS and IMM operations."
    )
    args = parser.parse_args()

    if args.check_permissions:
        ensure_env_loaded(verbose=False)
        from check_permissions import check_permissions, _print_results
        results = check_permissions(verbose=args.verbose)
        _print_results(results)
        sys.exit(0 if results.get("all_pass", False) else 1)

    if args.verify_imm:
        # Load env vars first, then verify IMM
        ensure_env_loaded(verbose=False)
        ok = verify_imm()
        sys.exit(0 if ok else 1)

    if args.check_only:
        # Load from config files first (needed in non-interactive shells
        # where ~/.bashrc is not sourced automatically)
        newly = load_env_files(verbose=False)
        print("=== Current Environment Variable State ===")
        for var in sorted(_TARGET_VARS):
            val = os.environ.get(var, "")
            if val:
                source = " (loaded from config file)" if var in newly else ""
                status = f"[OK] Set ({_safe_display(var, val)}){source}"
            else:
                status = "[MISSING] Not set"
            print(f"  {var}: {status}")
        missing = check_required_vars()
        if missing:
            _print_setup_hint(missing)
            sys.exit(1)
        sys.exit(0)

    print("=== Checking Required Python Packages ===")
    deps_pass, deps_err = _check_required_python_packages()
    if deps_pass:
        print("  [PASS] Pinned Python package requirements are installed.")
    else:
        print(f"  [FAIL] {deps_err}")
        sys.exit(1)

    print("\n=== Scanning Environment Sources ===", flush=True)
    newly = load_env_files(verbose=True)
    sys.stderr.flush()

    print("\n=== Load Results ===")
    for var in sorted(_TARGET_VARS):
        val = os.environ.get(var, "")
        if val:
            status = f"[OK] Set ({_safe_display(var, val)})"
        else:
            status = "[MISSING] Not set"
        print(f"  {var}: {status}")

    if newly:
        print(f"\nNewly loaded {len(newly)} variables: {list(newly.keys())}")

    print("\n=== Checking Python SDK Credentials ===")
    cred_pass, cred_err = _check_python_credentials()
    if cred_pass:
        print("  [PASS] Python SDK default credential chain is usable.")
    else:
        print(f"  [FAIL] {cred_err}")

    # Check required variables; print setup hint if missing.
    required = [
        "ALIBABA_CLOUD_OSS_BUCKET",
        "ALIBABA_CLOUD_OSS_REGION",
    ]
    missing = check_required_vars(required)
    if missing:
        _print_setup_hint(missing)
        sys.exit(1)

    if not cred_pass:
        sys.exit(1)

    # Environment variables are configured, check RAM permissions.
    bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    region = os.environ.get("ALIBABA_CLOUD_OSS_REGION", "")

    print("\n=== Checking RAM Permissions ===")
    oss_pass, oss_err = _check_oss_permission(bucket, region)
    if oss_pass:
        print(f"  [PASS] OSS: Bucket '{bucket}' is accessible.")
    else:
        print(f"  [FAIL] OSS: {oss_err}")

    if not oss_pass:
        print(
            "\nCopy and attach this policy to your RAM user at "
            "https://ram.console.aliyun.com/policies :"
        )
        print(json.dumps(
            _generate_policy(bucket, include_imm=True),
            indent=2,
        ))
        sys.exit(1)
    else:
        print("\nAll permission checks passed.")
        print(
            f"\nTo verify IMM binding: python {sys.argv[0]} --verify-imm"
        )
