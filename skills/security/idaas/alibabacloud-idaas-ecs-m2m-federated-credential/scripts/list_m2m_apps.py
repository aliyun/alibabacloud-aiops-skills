#!/usr/bin/env python3
"""List existing M2M applications (SsoType=oidc+oauth2/m2m) for the user to select.

Usage: list_m2m_apps.py <region> <instance_id>
"""
import sys

from common import list_all_pages


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("Usage: list_m2m_apps.py <region> <instance_id>")
    region, iid = sys.argv[1], sys.argv[2]

    apps = list_all_pages(["eiam", "list-applications", "--region", region,
                           "--instance-id", iid], "Applications", "ApplicationId")
    total = len(apps)
    m2m = [a for a in apps if a.get("SsoType") == "oidc+oauth2/m2m"]
    print(f"M2M applications: {len(m2m)} (total applications in instance: {total}):")
    for a in m2m:
        feats = a.get("Features") or ""
        role = "client" if "m2m_client" in feats else ("server?" if "m2m" in feats else "?")
        print(f"{a['ApplicationId']} | {a.get('ApplicationName', '')} | M2M role={role}")
    if not m2m:
        print("(No existing M2M applications; creating one is recommended)")


if __name__ == "__main__":
    main()
