#!/usr/bin/env python3
"""列出实例下已有的 M2M 应用（SsoType=oidc+oauth2/m2m，供「绑定已有应用」选择）。

用法: list_m2m_apps.py <region> <instance_id>
"""
import sys

from common import run_aliyun


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("用法: list_m2m_apps.py <region> <instance_id>")
    region, iid = sys.argv[1], sys.argv[2]

    d = run_aliyun(["eiam", "ListApplications", "--region", region,
                    "--InstanceId", iid, "--PageNumber", "1", "--PageSize", "100"])
    apps = d.get("Applications", [])
    total = d.get("TotalCount", len(apps))
    if total > len(apps):
        print(f"WARNING: 实例共 {total} 个应用，本页仅取 {len(apps)} 个，M2M 列表可能不全",
              file=sys.stderr)
    m2m = [a for a in apps if a.get("SsoType") == "oidc+oauth2/m2m"]
    print(f"M2M 应用 {len(m2m)} 个 (实例应用总数 {total}):")
    for a in m2m:
        feats = a.get("Features") or ""
        role = "client" if "m2m_client" in feats else ("server?" if "m2m" in feats else "?")
        print(f"{a['ApplicationId']} | {a.get('ApplicationName', '')} | M2M角色={role}")
    if not m2m:
        print("(无已有 M2M 应用，建议新建)")


if __name__ == "__main__":
    main()
