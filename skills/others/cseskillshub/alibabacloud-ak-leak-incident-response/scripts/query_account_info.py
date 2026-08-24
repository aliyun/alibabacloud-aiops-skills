#!/usr/bin/env python3
"""
query_account_info.py  (dual-backend edition)
=============================================
Query account-level information via the dual-backend layer in `_cli.py`
(aliyun CLI preferred, direct V3-signed HTTPS fallback; no Python product SDKs).
Provides a comprehensive account profile useful for incident response:
  - Account summary (RAM quota & usage)      -> IMS GetAccountSummary
  - AccessKeys (all live AKs)                 -> RAM ListAccessKeys
  - RAM users (active and recycled)           -> RAM ListUsers / IMS ListUsersInRecycleBin
  - Roles                                     -> RAM ListRoles
  - Security & password policy                -> RAM GetSecurityPreference / GetPasswordPolicy
  - Cloud SSO status                          -> CloudSSO GetServiceStatus

AUTHENTICATION:
    Handled by the active backend (see _cli.py). CLI backend uses the aliyun
    CLI profile (~/.aliyun/config.json); HTTP fallback uses env AK/SK or
    config.json. Use --profile to select a non-default profile.

Usage:
    python query_account_info.py --account <UID>
    python query_account_info.py --account <UID> --format json
    python query_account_info.py --account <UID> --section summary,accesskeys
    python query_account_info.py --account <UID> --profile myprofile
"""

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cli

SECTIONS = ["summary", "accesskeys", "users", "recycled_users", "roles",
            "security_policy", "cloud_sso"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Query account-level info for incident response via dual-backend"
    )
    p.add_argument("--account", "--uid", dest="uid", required=True, help="Alibaba Cloud Account UID")
    p.add_argument("--section", default="all",
                   help=f"Comma-separated sections: {','.join(SECTIONS)} (default: all)")
    p.add_argument("--region", default="cn-shanghai", help="Alibaba Cloud region (default: cn-shanghai)")
    p.add_argument("--profile", default=None, help="aliyun CLI profile name (optional)")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Query functions (all via the dual-backend layer)
# ---------------------------------------------------------------------------

def get_account_summary(region: str, profile: Any) -> dict:
    """IMS GetAccountSummary -> SummaryMap dict."""
    try:
        body = _cli.call("ims", "GetAccountSummary", region=region, profile=profile)
        return body.get("SummaryMap", {}) or {}
    except _cli.CliError as e:
        return {"error": str(e)}


def list_access_keys(region: str, profile: Any, user_name: str = "") -> list[dict]:
    """RAM ListAccessKeys -> normalized list."""
    try:
        params = {"UserName": user_name} if user_name else {}
        body = _cli.call("ram", "ListAccessKeys", params, region=region, profile=profile)
        aks = ((body.get("AccessKeys") or {}).get("AccessKey")) or []
        return [
            {
                "accessKeyId": a.get("AccessKeyId", ""),
                "status": a.get("Status", ""),
                "createDate": a.get("CreateDate", ""),
            }
            for a in aks
        ]
    except _cli.CliError as e:
        return [{"error": str(e)}]


def list_users(region: str, profile: Any) -> list[dict]:
    """RAM ListUsers (Marker pagination) -> normalized list."""
    try:
        users = _cli.paginate_marker(
            "ram", "ListUsers", {"MaxItems": 100},
            region=region, profile=profile, list_path=["Users", "User"],
        )
        return [
            {
                "userName": u.get("UserName", ""),
                "userId": u.get("UserId", ""),
                "displayName": u.get("DisplayName", ""),
                "createDate": u.get("CreateDate", ""),
                "comments": u.get("Comments", ""),
            }
            for u in users
        ]
    except _cli.CliError as e:
        return [{"error": str(e)}]


def list_users_in_recycle_bin(region: str, profile: Any) -> dict:
    """IMS ListUsersInRecycleBin (Marker pagination) -> normalized dict."""
    try:
        users = _cli.paginate_marker(
            "ims", "ListUsersInRecycleBin", {"MaxItems": 100},
            region=region, profile=profile, list_path=["Users", "User"],
        )
        out = [
            {
                "userName": u.get("UserPrincipalName") or u.get("UserName", ""),
                "userId": u.get("UserId", ""),
                "recycleTime": u.get("GmtDeleted") or u.get("RecycleTime", ""),
                "originCreateTime": u.get("GmtCreate") or u.get("OriginCreateTime", ""),
            }
            for u in users
        ]
        return {"recycledUserList": out, "totalCount": len(out)}
    except _cli.CliError as e:
        return {"error": str(e)}


def list_roles(region: str, profile: Any) -> list[dict]:
    """RAM ListRoles (Marker pagination) -> normalized list."""
    try:
        roles = _cli.paginate_marker(
            "ram", "ListRoles", {"MaxItems": 100},
            region=region, profile=profile, list_path=["Roles", "Role"],
        )
        return [
            {
                "roleName": r.get("RoleName", ""),
                "roleId": r.get("RoleId", ""),
                "createDate": r.get("CreateDate", ""),
                "description": r.get("Description", ""),
            }
            for r in roles
        ]
    except _cli.CliError as e:
        return [{"error": str(e)}]


def get_password_policy(region: str, profile: Any) -> dict:
    """RAM GetPasswordPolicy -> normalized dict."""
    try:
        body = _cli.call("ram", "GetPasswordPolicy", region=region, profile=profile)
        pp = body.get("PasswordPolicy", {}) or {}
        return {
            "minimumPasswordLength": pp.get("MinimumPasswordLength", "N/A"),
            "requireLowercaseCharacters": pp.get("RequireLowercaseCharacters", False),
            "requireUppercaseCharacters": pp.get("RequireUppercaseCharacters", False),
            "requireNumbers": pp.get("RequireNumbers", False),
            "requireSymbols": pp.get("RequireSymbols", False),
            "maxPasswordAge": pp.get("MaxPasswordAge", 0),
            "passwordReusePrevention": pp.get("PasswordReusePrevention", 0),
            "maxLoginAttemps": pp.get("MaxLoginAttemps", 0),
        }
    except _cli.CliError as e:
        return {"error": str(e)}


def get_security_policy(region: str, profile: Any) -> dict:
    """RAM GetSecurityPreference -> normalized dict."""
    try:
        body = _cli.call("ram", "GetSecurityPreference", region=region, profile=profile)
        sp = body.get("SecurityPreference", {}) or {}
        ak_pref = sp.get("AccessKeyPreference", {}) or {}
        login_pref = sp.get("LoginProfilePreference", {}) or {}
        mfa_pref = sp.get("MFAPreference", {}) or {}
        return {
            "sessionDuration": login_pref.get("LoginSessionDuration", "N/A"),
            "allowUserToChangePassword": login_pref.get("AllowUserToChangePassword", True),
            "allowUserToManageAccessKeys": ak_pref.get("AllowUserToManageAccessKeys", True),
            "loginNetworkMasks": login_pref.get("LoginNetworkMasks", ""),
            "enforceMFAForLogin": mfa_pref.get("OperationForRiskLogin", "") == "EnforceVerify",
        }
    except _cli.CliError as e:
        return {"error": str(e)}


def get_cloud_sso_status(region: str, profile: Any) -> dict:
    """CloudSSO GetServiceStatus -> normalized dict."""
    try:
        body = _cli.call("cloudsso", "GetServiceStatus", region=region, profile=profile)
        status = (body.get("ServiceStatus") or {})
        st = status.get("Status", "N/A")
        return {"enabled": st == "Enabled", "configStatus": st}
    except _cli.CliError as e:
        msg = str(e)
        if "NotEnabled" in msg or "ServiceNotEnabled" in msg:
            return {"enabled": False, "configStatus": "NotEnabled"}
        return {"error": msg}


def format_text_output(uid: str, results: dict) -> str:
    """Format all sections for human-readable output."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  Account Profile: {uid}")
    lines.append("=" * 60)

    # Summary
    summary = results.get("summary", {})
    if summary and not summary.get("error"):
        lines.append("")
        lines.append("--- Account Summary ---")
        keys_of_interest = [
            ("Users", "RAM Users"),
            ("Roles", "Roles"),
            ("Policies", "Custom Policies"),
            ("Groups", "Groups"),
            ("MFADevices", "MFA Devices"),
            ("MFADevicesInUse", "MFA Devices In Use"),
            ("AccessKeys", "Active AccessKeys"),
        ]
        for key, label in keys_of_interest:
            val = summary.get(key, "N/A")
            lines.append(f"  {label}: {val}")

        mfa_in_use = summary.get("MFADevicesInUse", 0)
        if mfa_in_use == 0 or mfa_in_use == "0":
            lines.append("")
            lines.append("  WARNING: No MFA devices in use -- account has no 2FA protection!")

    # AccessKeys
    accesskeys = results.get("accesskeys", [])
    if accesskeys:
        lines.append("")
        lines.append(f"--- AccessKeys ({len(accesskeys)}) ---")
        for ak in accesskeys:
            if "error" in ak:
                lines.append(f"  Error: {ak['error']}")
                continue
            status_flag = " [ACTIVE]" if ak.get("status") == "Active" else ""
            lines.append(
                f"  {ak.get('accessKeyId', '?')} | {ak.get('status', '?')}{status_flag} | "
                f"created={ak.get('createDate', '?')}"
            )

    # Users
    users_list = results.get("users", [])
    if users_list is not None:
        lines.append("")
        lines.append(f"--- Active RAM Users ({len(users_list)}) ---")
        if users_list:
            for u in users_list:
                if "error" in u:
                    lines.append(f"  Error: {u['error']}")
                    continue
                lines.append(
                    f"  {u.get('userName', '?')} | id={u.get('userId', '?')} | "
                    f"created={u.get('createDate', '?')}"
                )
        else:
            lines.append("  (no active RAM users)")

    # Recycled Users
    recycled = results.get("recycled_users", {})
    if recycled and not recycled.get("error"):
        recycled_list = recycled.get("recycledUserList", [])
        total = recycled.get("totalCount", 0)
        lines.append("")
        lines.append(f"--- Recycled/Deleted Users ({total}) ---")
        if recycled_list:
            for u in recycled_list:
                lines.append(f"  {u.get('userName', '?')}")
                lines.append(f"    Originally created: {u.get('originCreateTime', '?')}")
                lines.append(f"    Deleted (recycled): {u.get('recycleTime', '?')}")
        else:
            lines.append("  (none)")

    # Security Policy
    sec_policy = results.get("security_policy", {})
    if sec_policy and not sec_policy.get("error"):
        lines.append("")
        lines.append("--- Security Policy ---")
        lines.append(f"  Session duration: {sec_policy.get('sessionDuration', 'N/A')}")
        lines.append(f"  Users can manage AKs: {sec_policy.get('allowUserToManageAccessKeys', 'N/A')}")
        lines.append(f"  Login network masks: {sec_policy.get('loginNetworkMasks', '') or '(none)'}")
        lines.append(f"  MFA enforced for login: {sec_policy.get('enforceMFAForLogin', False)}")

    # Password Policy
    pw_policy = results.get("password_policy", {})
    if pw_policy and not pw_policy.get("error"):
        lines.append("")
        lines.append("--- Password Policy ---")
        lines.append(f"  Minimum length: {pw_policy.get('minimumPasswordLength', 'N/A')}")
        lines.append(f"  Max password age: {pw_policy.get('maxPasswordAge', 'N/A')} days")
        lines.append(f"  Password reuse prevention: {pw_policy.get('passwordReusePrevention', 'N/A')}")
        lines.append(f"  Max login attempts: {pw_policy.get('maxLoginAttemps', 'N/A')}")

    # Cloud SSO
    cloud_sso = results.get("cloud_sso", {})
    if cloud_sso and not cloud_sso.get("error"):
        lines.append("")
        lines.append("--- Cloud SSO ---")
        lines.append(f"  Enabled: {cloud_sso.get('enabled', 'N/A')}")
        lines.append(f"  Config Status: {cloud_sso.get('configStatus', 'N/A')}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    _cli.check_cli_available()

    if args.section == "all":
        sections = SECTIONS
    else:
        sections = [s.strip() for s in args.section.split(",") if s.strip() in SECTIONS]
        if not sections:
            print(f"Error: invalid --section. Choose from: {', '.join(SECTIONS)}", file=sys.stderr)
            return 1

    region, profile = args.region, args.profile
    results = {}
    if "summary" in sections:
        print("[query] Account summary...", file=sys.stderr)
        results["summary"] = get_account_summary(region, profile)
    if "accesskeys" in sections:
        print("[query] AccessKeys...", file=sys.stderr)
        results["accesskeys"] = list_access_keys(region, profile)
    if "users" in sections:
        print("[query] Active RAM users...", file=sys.stderr)
        results["users"] = list_users(region, profile)
    if "recycled_users" in sections:
        print("[query] Recycled/deleted users...", file=sys.stderr)
        results["recycled_users"] = list_users_in_recycle_bin(region, profile)
    if "roles" in sections:
        print("[query] Roles...", file=sys.stderr)
        results["roles"] = list_roles(region, profile)
    if "security_policy" in sections:
        print("[query] Security & password policy...", file=sys.stderr)
        results["security_policy"] = get_security_policy(region, profile)
        results["password_policy"] = get_password_policy(region, profile)
    if "cloud_sso" in sections:
        print("[query] Cloud SSO status...", file=sys.stderr)
        results["cloud_sso"] = get_cloud_sso_status(region, profile)

    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_text_output(args.uid, results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
