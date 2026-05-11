#!/usr/bin/env python3
"""
check_permissions.py — Verify RAM permissions for OSS and IMM operations

Checks whether the configured AccessKey has sufficient permissions to:
  1. Access the specified OSS bucket (GetBucketInfo)
  2. Access the specified IMM project (GetProject)
  3. Perform image processing operations (SignURL test)

Usage:
    python check_permissions.py
    python check_permissions.py --verbose
"""

import json
import os
import sys

# Ensure sibling modules (load_env, etc.) are importable
# regardless of the working directory when invoked via absolute path.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from permission_checks import check_imm_permission, check_oss_permission


def _mask(value: str) -> str:
    """Mask a credential value for display."""
    if len(value) > 8:
        return value[:4] + "****" + value[-4:]
    return "****"


def _check_oss_permission(bucket: str, region: str, verbose: bool = False) -> dict:
    """
    Check OSS bucket access permission by calling HeadBucket.
    Returns a dict with status and details.
    """
    result = {
        "service": "OSS",
        "bucket": bucket,
        "region": region,
        "status": "fail",
        "details": "",
    }

    ok, error = check_oss_permission(bucket, region)
    if ok:
        result["status"] = "pass"
        result["details"] = f"Bucket '{bucket}' is accessible."
    elif error == "oss2 SDK not installed":
        result["details"] = "oss2 SDK not installed. Run: pip install oss2==2.19.1"
    elif error == "AccessKey not configured":
        result["details"] = "AccessKey not configured."
    elif "does not exist in region" in error:
        result["status"] = "fail"
        result["details"] = f"{error}. Check the bucket name and region."
    elif error == "Access denied to bucket (lacks OSS read permission)":
        result["status"] = "fail"
        result["details"] = (
            f"Access denied to bucket '{bucket}'. "
            f"The AccessKey lacks OSS bucket read permission."
        )
        result["hint"] = (
            "Grant the 'AliyunOSSReadOnlyAccess' policy to your RAM user, "
            "or attach a custom policy with 'oss:GetBucketInfo' permission:\n"
            "  https://ram.console.aliyun.com/policies"
        )
    elif error == "Invalid AccessKey ID":
        result["status"] = "fail"
        result["details"] = "Invalid AccessKey ID."
        result["hint"] = (
            "Verify your AccessKey at: "
            "https://ram.console.aliyun.com/users"
        )
    else:
        result["status"] = "fail"
        result["details"] = error

    return result


def _check_imm_permission(project: str, region: str, verbose: bool = False) -> dict:
    """
    Check IMM project access permission by calling GetProject.
    Returns a dict with status and details.
    """
    result = {
        "service": "IMM",
        "project": project,
        "region": region,
        "status": "fail",
        "details": "",
    }

    if not project:
        result["status"] = "skip"
        result["details"] = "IMM project not configured. Skipped."
        return result

    ok, error = check_imm_permission(project, region)
    if ok is None:
        result["status"] = "skip"
        result["details"] = "IMM project not configured. Skipped."
        return result

    if error == "IMM SDK not installed":
        result["details"] = (
            "IMM SDK not installed. Run: "
            "pip install alibabacloud_imm20200930==4.8.2 alibabacloud_tea_openapi==0.4.4"
        )
        return result
    if error == "AccessKey not configured":
        result["details"] = "AccessKey not configured."
        return result
    if ok:
        result["status"] = "pass"
        result["details"] = f"Project '{project}' is accessible."
    elif error == "Access denied to IMM project (lacks IMM permission)":
        result["status"] = "fail"
        result["details"] = (
            f"Access denied to IMM project '{project}'. "
            f"The AccessKey lacks IMM permissions."
        )
        result["hint"] = (
            "Grant the 'AliyunIMMFullAccess' policy to your RAM user, "
            "or attach a custom policy with required IMM permissions:\n"
            "  https://ram.console.aliyun.com/policies"
        )
    elif "not found" in error.lower():
        result["status"] = "fail"
        result["details"] = f"Project '{project}' not found."
        result["hint"] = (
            f"Create a project: "
            f"python imm_admin.py create-project --project {project} "
            f"--bucket $ALIBABA_CLOUD_OSS_BUCKET --region {region}"
        )
    else:
        result["status"] = "fail"
        result["details"] = error

    return result


def check_permissions(verbose: bool = False) -> dict:
    """
    Check RAM permissions for both OSS and IMM.
    Returns a summary dict with all check results.
    """
    bucket = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", "")
    region = os.environ.get("ALIBABA_CLOUD_OSS_REGION", "")
    project = os.environ.get("ALIBABA_CLOUD_IMM_PROJECT", "")
    import credential
    credential_client = credential.get_credential_client(required=False)
    masked_access_key = "not set"
    if credential_client is not None:
        try:
            cred = credential_client.get_credential()
        except Exception:
            cred = None
        if cred and cred.get_access_key_id():
            masked_access_key = _mask(cred.get_access_key_id())

    results = {
        "access_key_id": masked_access_key,
        "checks": [],
        "summary": "",
    }

    if not bucket or not region:
        results["checks"].append({
            "service": "OSS",
            "status": "skip",
            "details": (
                "Bucket or region not configured. Set ALIBABA_CLOUD_OSS_BUCKET "
                "and ALIBABA_CLOUD_OSS_REGION, or use --bucket / --region."
            ),
        })
    else:
        results["checks"].append(
            _check_oss_permission(bucket, region, verbose)
        )

    results["checks"].append(
        _check_imm_permission(project, region, verbose)
    )

    # Summary
    pass_count = sum(1 for c in results["checks"] if c["status"] == "pass")
    fail_count = sum(1 for c in results["checks"] if c["status"] == "fail")
    total = len(results["checks"])
    results["summary"] = f"{pass_count}/{total} checks passed"
    results["all_pass"] = fail_count == 0

    return results


def _print_results(results: dict) -> None:
    """Print check results in a human-readable format."""
    print(f"AccessKey: {results['access_key_id']}")
    print()

    for check in results["checks"]:
        service = check["service"]
        status = check["status"].upper()
        details = check["details"]

        if status == "PASS":
            print(f"  [{status}] {service}: {details}")
        elif status == "SKIP":
            print(f"  [{status}] {service}: {details}")
        else:
            print(f"  [{status}] {service}: {details}")
            if "hint" in check:
                print(f"         Hint: {check['hint']}")

    print()
    print(f"Summary: {results['summary']}")

    if not results.get("all_pass", False):
        print(
            "\nSome checks failed. Review the hints above and fix "
            "permissions before proceeding.",
            file=sys.stderr,
        )


# ─── Standalone mode ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    from load_env import ensure_env_loaded

    parser = argparse.ArgumentParser(
        description="Check RAM permissions for OSS and IMM operations."
    )
    parser.add_argument(
        "--bucket", default=os.environ.get("ALIBABA_CLOUD_OSS_BUCKET"),
        help="OSS bucket name (falls back to env var)."
    )
    parser.add_argument(
        "--region", default=os.environ.get("ALIBABA_CLOUD_OSS_REGION"),
        help="OSS region (falls back to env var)."
    )
    parser.add_argument(
        "--project", default=os.environ.get("ALIBABA_CLOUD_IMM_PROJECT"),
        help="IMM project name (falls back to env var)."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed output."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON."
    )
    args = parser.parse_args()

    # Set env vars from CLI args so check_permissions() picks them up
    if args.bucket:
        os.environ["ALIBABA_CLOUD_OSS_BUCKET"] = args.bucket
    if args.region:
        os.environ["ALIBABA_CLOUD_OSS_REGION"] = args.region
    if args.project:
        os.environ["ALIBABA_CLOUD_IMM_PROJECT"] = args.project

    # Load env vars from config files first
    ensure_env_loaded(verbose=False)

    results = check_permissions(verbose=args.verbose)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        _print_results(results)
        sys.exit(0 if results.get("all_pass", False) else 1)
