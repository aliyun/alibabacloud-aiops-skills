#!/usr/bin/env python3
"""Create an M2M client application (SsoType=oidc+oauth2/m2m) and ensure its M2M client capabilities are enabled.

Usage: create_m2m_client.py <region> <instance_id> <app_name> [description]
Output: Raw response, followed by APP_ID=app_xxx and M2M_STATUS=enabled.
"""
import json
import sys

from common import die, info, run_aliyun, validate_general_name


def main() -> None:
    if len(sys.argv) < 4:
        die_usage()
    region, iid, name = sys.argv[1:4]
    validate_general_name(name, "Application name")
    desc = sys.argv[4] if len(sys.argv) > 4 else "Created by skill idaas-ecs-m2m-federated-credential"

    d = run_aliyun([
        "eiam", "create-application", "--region", region,
        "--instance-id", iid,
        "--application-name", name,
        "--application-source-type", "urn:alibaba:idaas:app:source:standard",
        "--sso-type", "oidc+oauth2/m2m",
        "--description", desc,
    ])
    print(json.dumps(d, ensure_ascii=False))
    app_id = d.get("ApplicationId", "")
    if not app_id:
        sys.exit("ERROR: Application creation failed (name conflict? M2M application license quota exceeded? "
                 "Paid M2M feature not enabled on the instance?)")

    # Record the resource before post-creation calls, including on later failure.
    print(f"APP_ID={app_id}", flush=True)

    def get_status() -> str:
        g = run_aliyun(["eiam", "get-application", "--region", region,
                        "--instance-id", iid, "--application-id", app_id])
        return g.get("Application", g).get("M2MClientStatus", "")

    status = get_status()
    if status != "enabled":
        info(f"M2MClientStatus={status or 'unknown'}; attempting to enable...")
        run_aliyun(["eiam", "enable-application-m2m-client", "--region", region,
                    "--instance-id", iid, "--application-id", app_id])
        status = get_status()

    print(f"M2M_STATUS={status}")
    if status != "enabled":
        die("M2M client is not enabled; stop before creating dependent credentials. Check the console.")


def die_usage() -> None:
    sys.exit("Usage: create_m2m_client.py <region> <instance_id> <app_name> [description]")


if __name__ == "__main__":
    main()
