#!/usr/bin/env python3
"""Single entry point for the alibabacloud-ecs-server-migration-on-cloud: forced-migration-guide skill.

READ-ONLY guide (RO_GUIDE): this script queries instance facts with exactly one
read-only action (ecs DescribeInstances) and prints human-followable self-service
guidance plus console entry points. It never changes cloud resources, never runs
commands inside a customer instance, and never submits billing or compensation
requests. The agent must only run THIS script; it must not assemble aliyun calls
by hand or call any other action.

Usage examples:
  python3 scripts/forced_migration_guide.py --region-id cn-hangzhou --intent triage
  python3 scripts/forced_migration_guide.py --region-id cn-hangzhou \
      --instance-ids i-bp1xxxx,i-bp1yyyy --intent migration
  python3 scripts/forced_migration_guide.py --region-id cn-shanghai --intent exposure
"""

import argparse
import json
import sys

import sts_token
from _cli import SESSION_ID, CliError, call_readonly, mask_credentials
from _constants import (
    BOUNDARY_STATEMENT,
    ECS_API_VERSION,
    GUIDE_BY_INTENT,
    MAX_INSTANCE_IDS,
    NEXT_ACTION_BY_STATUS,
    SKILL_NAME,
)


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="forced_migration_guide.py",
        description="Read-only ECS guide for decommission/forced migration, platform "
                    "reboots, and related impact or fee disputes.",
    )
    parser.add_argument("--region-id", required=True,
                        help="Alibaba Cloud region id, e.g. cn-hangzhou (only instances in "
                             "this region are visible to the read-only query).")
    parser.add_argument("--instance-ids", default="",
                        help="Optional comma-separated instance ids to scope the read-only "
                             "query (at most %d)." % MAX_INSTANCE_IDS)
    parser.add_argument("--intent",
                        choices=["triage", "migration", "incident", "billing", "exposure"],
                        default="triage",
                        help="Which guided playbook to print after the facts.")
    parser.add_argument("--skip-credential-check", action="store_true",
                        help="Do not probe caller identity (still read-only).")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Emit the raw read-only instance facts as JSON only.")
    return parser.parse_args(argv)


def _id_list(raw):
    ids = [x.strip() for x in (raw or "").split(",") if x.strip()]
    return ids[:MAX_INSTANCE_IDS]


def _query_instances(region_id, ids):
    params = {"RegionId": region_id}
    if ids:
        params["InstanceIds"] = json.dumps(ids)
    return call_readonly("DescribeInstances", params)


def _summarize(instances):
    rows = []
    for inst in instances:
        sg = (inst.get("SecurityGroupIds") or {}).get("SecurityGroupId") or []
        public_ips = inst.get("PublicIpAddress", {}).get("IpAddress", []) if isinstance(
            inst.get("PublicIpAddress"), dict) else []
        eip = (inst.get("EipAddress") or {}).get("IpAddress", "")
        rows.append({
            "InstanceId": inst.get("InstanceId", ""),
            "Status": inst.get("Status", ""),
            "RegionId": inst.get("RegionId", ""),
            "ZoneId": inst.get("ZoneId", ""),
            "InstanceType": inst.get("InstanceType", ""),
            "InstanceChargeType": inst.get("InstanceChargeType", ""),
            "OSName": inst.get("OSName", ""),
            "SecurityGroupIds": sg,
            "PublicIpAddresses": public_ips,
            "EipAddress": eip,
            "NetworkType": inst.get("InstanceNetworkType", ""),
        })
    return rows


def _print_facts(rows, out):
    out("Bound security groups are the anchor for the exposure self-check; the console is "
        "where you open and review them, not this script.")
    for i, r in enumerate(rows, 1):
        out("  [%d] %s" % (i, r["InstanceId"]))
        out("      status=%s  region=%s  zone=%s  type=%s  charge=%s"
            % (r["Status"], r["RegionId"], r["ZoneId"], r["InstanceType"],
               r["InstanceChargeType"]))
        out("      security groups=%s" % (", ".join(r["SecurityGroupIds"]) or "(none reported)"))
        net_ips = list(r["PublicIpAddresses"]) + ([r["EipAddress"]] if r["EipAddress"] else [])
        out("      public ip(s)=%s" % (", ".join([x for x in net_ips if x]) or "(none reported)"))


def main(argv=None):
    args = _parse_args(argv)
    out = lambda s="": sys.stdout.write(str(s) + "\n")  # noqa: E731

    out("=" * 72)
    out("%s :: read-only guided report" % SKILL_NAME)
    out("session-id: %s   api-version: %s" % (SESSION_ID, ECS_API_VERSION))
    out("region-id:  %s   intent: %s" % (args.region_id, args.intent))
    out("=" * 72)

    degraded = False
    status = "OK"

    # Best-effort, read-only caller identity probe (informational, never blocking).
    if not args.skip_credential_check and not args.as_json:
        try:
            identity = sts_token.get_caller_identity()
            out("account (default credential chain): %s" % sts_token.account_label(identity))
        except CliError as err:
            degraded = True
            out("[WARN] caller identity probe failed: %s" % mask_credentials(str(err)))
            out("       %s" % sts_token.configure_hint())

    # Single read-only query.
    ids = _id_list(args.instance_ids)
    try:
        raw = _query_instances(args.region_id, ids)
        instances = (raw.get("Instances") or {}).get("Instance") or []
    except CliError as err:
        if args.as_json:
            sys.stderr.write(json.dumps({"error": mask_credentials(str(err))}) + "\n")
        out("STATUS: FAIL")
        out("NEXT_ACTION: %s" % NEXT_ACTION_BY_STATUS["FAIL"])
        out("Detail: %s" % mask_credentials(str(err)))
        if "NoPermission" in str(err.code) or "ImplicitDeny" in str(err.code) \
                or "Unauthorized" in str(err.code):
            out("Missing read action: ecs:DescribeInstances. Grant only this single read-only "
                "action to the caller; see references/ram-policies.md. Re-run after granting it.")
        return 1

    if args.as_json:
        out(json.dumps({"instances": _summarize(instances)}, ensure_ascii=False, indent=2))
        out("STATUS: %s" % ("DEGRADED" if not instances else "OK"))
        return 0

    rows = _summarize(instances)
    out("")
    out("READ-ONLY FACTS (DescribeInstances, region %s):" % args.region_id)
    if not rows:
        degraded = True
        status = "DEGRADED"
        out("  No matching instance was returned in this region for the current account.")
        out("  Verify the RegionId and the account that owns the instance; do not assume it exists.")
    else:
        _print_facts(rows, out)

    out("")
    if args.intent == "triage":
        out("TRIAGE: choose the playbook that matches the customer's symptom and re-run with "
            "--intent <name>:")
        out("  migration  region / data-center decommission, forced or host migration")
        out("  incident   unplanned reboot / planned maintenance reboot, availability impact")
        out("  billing    fee or refund dispute tied to a platform action or a rule")
        out("  exposure   suspected breach / traffic / blame dispute with no platform fault")
    else:
        out(GUIDE_BY_INTENT[args.intent])

    out("")
    out(BOUNDARY_STATEMENT)

    if degraded and status == "OK":
        status = "DEGRADED"

    out("")
    out("STATUS: %s" % status)
    out("NEXT_ACTION: %s" % NEXT_ACTION_BY_STATUS[status])
    return 0


if __name__ == "__main__":
    sys.exit(main())
