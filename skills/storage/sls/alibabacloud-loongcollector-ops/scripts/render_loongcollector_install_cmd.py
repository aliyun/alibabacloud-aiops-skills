#!/usr/bin/env python3
"""render_loongcollector_install_cmd.py — render official Linux install/upgrade commands.

Does not download or execute. stdout = one JSON object; exit 0 ok, 2 usage.

Usage:
  python3 scripts/render_loongcollector_install_cmd.py \\
    --environment ecs|self_host --region cn-shanghai \\
    [--network intranet|internet|acceleration] \\
    [--account-relation same|cross] [--user-id <aliuid>] \\
    [--action install|upgrade] [--user-defined-id <id>]
"""
import argparse
import json
import os
import sys

VALID_ENV = {"ecs", "self_host"}
VALID_NET = {"intranet", "internet", "acceleration"}
VALID_REL = {"same", "cross"}
VALID_ACT = {"install", "upgrade"}


def die(msg, code=2):
    sys.stderr.write("[render_loongcollector_install_cmd] %s\n" % msg)
    sys.exit(code)


def download_url(region, network):
    endpoint = "oss-%s.aliyuncs.com" % region
    if network == "intranet":
        endpoint = "oss-%s-internal.aliyuncs.com" % region
    return (
        "https://aliyun-observability-release-%s.%s"
        "/loongcollector/linux64/latest/loongcollector.sh"
        % (region, endpoint)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--environment", required=True, choices=sorted(VALID_ENV))
    ap.add_argument("--region", required=True)
    ap.add_argument("--network", choices=sorted(VALID_NET), default="intranet")
    ap.add_argument("--account-relation", choices=sorted(VALID_REL), default="same")
    ap.add_argument("--user-id", default="")
    ap.add_argument("--action", choices=sorted(VALID_ACT), default="install")
    ap.add_argument("--user-defined-id", default="")
    args = ap.parse_args()

    region = args.region.strip()
    if not region or "/" in region or " " in region:
        die("region must be a simple id such as cn-shanghai")

    if args.account_relation == "cross" and not args.user_id:
        die("cross-account install requires --user-id (primary account ALIUID)")

    suffix = ""
    if args.action == "install":
        if args.network == "internet":
            suffix = "-internet"
        elif args.network == "acceleration":
            suffix = "-acceleration"

    url = download_url(region, args.network)
    download = (
        "wget --timeout=30 --tries=3 %s -O loongcollector.sh && chmod 755 loongcollector.sh" % url
    )
    if args.action == "upgrade":
        run = "./loongcollector.sh upgrade"
    else:
        run = "./loongcollector.sh install %s%s" % (region, suffix)

    identity = []
    if args.user_id:
        identity.append("sudo mkdir -p /etc/ilogtail/users && sudo touch /etc/ilogtail/users/%s" % args.user_id)
    if args.user_defined_id:
        identity.append(
            "printf '%s\\n' | sudo tee /etc/ilogtail/user_defined_id >/dev/null"
            % args.user_defined_id.replace("'", "")
        )

    status = "sudo /etc/init.d/loongcollectord status"
    remote = " && ".join([download, run] + identity + [status])

    out = {
        "tool": "render_loongcollector_install_cmd",
        "session_id": os.environ.get("SKILL_SESSION_ID", ""),
        "status": "ok",
        "environment": args.environment,
        "region": region,
        "network": args.network,
        "account_relation": args.account_relation,
        "action": args.action,
        "download_url": url,
        "download_cmd": download,
        "install_cmd": run,
        "identity_cmds": identity,
        "status_cmd": status,
        "remote_command": remote,
        "runcommand_hint": "aliyun ecs run-command --biz-region-id <region> --type RunShellScript --timeout 600 --command-content %s --instance-id <ecs_instance_id>" % json.dumps(remote),
        "ssh_hint": "ssh <alias> -- %s" % json.dumps(remote),
        "notes": [
            "upgrade must use ./loongcollector.sh upgrade, never install overwrite",
            "do not print AK/SK; do not StrictHostKeyChecking=no",
            "ECS: execute remote_command via aliyun ecs run-command + aliyun ecs describe-invocation-results, not workbench/OOS",
            "accept when status prints: loongcollector is running (or ilogtail is running)",
        ],
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
