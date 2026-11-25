#!/usr/bin/env python3
"""Single entry point for the ECS site-migration guide skill.

Subcommands:
  plan      Route the request to a migration path and print the ordered human-executed steps.
  precheck  Gather the inspection-only cloud evidence needed before a move starts.
  cutover   Gather the post-move verification evidence and print the cutover checklist.
  guest-commands  Print or vet the in-guest inspection command allow-list.

Only the allow-listed Describe and Get actions in ``_constants.ALLOWED_ACTIONS`` are reachable.
The script never performs a mutating call and never asks for credentials.
"""

import argparse
import json
import re
import sys

import _cli
import _constants as C
import sts_token

MAX_STATUS_IDS = 50
COMMAND_SPLIT_PATTERN = re.compile(r"[\s;|&\n]+")
SOURCE_DISKS_NOTE = (
    "Disk sizes are not returned by the actions available to this build, so the capacity gate is a "
    "manual console check: the target system disk must be at least as large as the source system "
    "disk, otherwise the move cannot be applied to that target."
)
EXPIRY_NOTE = (
    "Billing type is returned by the instance listing; the expiry date is not. Read the expiry or "
    "release deadline shown in the console instance list or the expiry notice, and confirm the "
    "current retention window there rather than relying on any figure quoted elsewhere."
)


def _as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def _nested_list(obj, outer_key, inner_key):
    if not isinstance(obj, dict):
        return []
    block = obj.get(outer_key)
    if isinstance(block, dict):
        return _as_list(block.get(inner_key))
    return _as_list(block)


def _split_ids(raw):
    ids = []
    for piece in (raw or "").split(","):
        trimmed = piece.strip()
        if trimmed and trimmed not in ids:
            ids.append(trimmed)
    return ids


def _chunks(items, size):
    out = []
    for start in range(0, len(items), size):
        out.append(items[start:start + size])
    return out


def _pick_ip(block):
    if isinstance(block, dict):
        for key in ("IpAddress", "InternetAddress"):
            value = block.get(key)
            if isinstance(value, str) and value:
                return [value]
            if value:
                return _as_list(value)
        return []
    if isinstance(block, str) and block:
        return [block]
    return _as_list(block)


def summarise_instance(instance):
    """Project one instance record onto the fields a migration decision needs."""
    if not isinstance(instance, dict):
        return {}
    summary = {
        "instance_id": instance.get("InstanceId"),
        "instance_name": instance.get("InstanceName"),
        "status": instance.get("Status"),
        "region_id": instance.get("RegionId"),
        "zone_id": instance.get("ZoneId"),
        "instance_type": instance.get("InstanceType"),
        "charge_type": instance.get("InstanceChargeType"),
        "image_id": instance.get("ImageId"),
        "os_name": instance.get("OSName"),
        "os_type": instance.get("OSType"),
        "cpu": instance.get("Cpu"),
        "memory_mib": instance.get("Memory"),
        "network_type": instance.get("InstanceNetworkType"),
        "internet_max_bandwidth_out": instance.get("InternetMaxBandwidthOut"),
        "security_group_ids": _nested_list(instance, "SecurityGroupIds", "SecurityGroupId"),
        "public_ip_addresses": _pick_ip(instance.get("PublicIpAddress")),
        "eip_addresses": _pick_ip(instance.get("EipAddress")),
        "inner_ip_addresses": _pick_ip(instance.get("InnerIpAddress")),
        "tags": _nested_list(instance, "Tags", "Tag"),
    }
    vpc_attributes = instance.get("VpcAttributes")
    if isinstance(vpc_attributes, dict):
        summary["private_ip_addresses"] = _pick_ip(vpc_attributes.get("PrivateIpAddress"))
        summary["v_switch_id"] = vpc_attributes.get("VSwitchId")
        summary["vpc_id"] = vpc_attributes.get("VpcId")
    else:
        summary["private_ip_addresses"] = []
    return summary


def _summarize_available(zones):
    summary = []
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        supported = []
        for block in _nested_list(zone, "AvailableResources", "AvailableResource"):
            if not isinstance(block, dict):
                continue
            for item in _nested_list(block, "SupportedResources", "SupportedResource"):
                if isinstance(item, dict):
                    supported.append({
                        "value": item.get("Value"),
                        "status": item.get("Status"),
                        "status_category": item.get("StatusCategory"),
                        "max": item.get("Max"),
                        "unit": item.get("Unit"),
                    })
        summary.append({
            "zone_id": zone.get("ZoneId"),
            "region_id": zone.get("RegionId"),
            "supported_count": len(supported),
            "supported": supported[:20],
        })
    return summary


def match_error_anchors(text):
    """Return the known root-cause entries whose fragment appears in the pasted error text."""
    if not text:
        return []
    lowered = text.lower()
    matched = []
    for anchor in C.KNOWN_ERROR_ANCHORS:
        if anchor["fragment"].lower() in lowered:
            matched.append(anchor)
    return matched


def validate_guest_command(command):
    """Decide whether one proposed in-guest command may be offered at all.

    Deny markers are checked first, so a compound command that also deletes, redirects, restarts,
    or reformats is rejected even when it starts with an allow-listed command.
    """
    text = (command or "").strip()
    if not text:
        return False, "No command was supplied. Ask for one command at a time."
    lowered = text.lower()
    tokens = [token for token in COMMAND_SPLIT_PATTERN.split(lowered) if token]
    for marker in C.GUEST_COMMAND_DENY_MARKERS:
        key = marker.strip().lower()
        if not key:
            continue
        if " " in key:
            matched = key in lowered
        else:
            matched = any(token == key or token.startswith(key) for token in tokens)
        if matched:
            return False, (
                "Rejected: the command uses '%s', which is outside the inspection allow-list. "
                "Do not run it and do not offer it as a copy-paste command. Give the documented "
                "console procedure, state the risk, and require a snapshot first." % key
            )
    for entry in C.GUEST_COMMAND_ALLOWLIST:
        prefix = entry["command"].split(" <")[0].lower()
        if lowered == prefix or lowered.startswith(prefix + " ") or lowered.startswith(prefix + "\t"):
            return True, ("Allowed: matches '%s' - %s. Announce the command, its scope, and that it "
                          "has no side effects, get confirmation for this one command, then have "
                          "the customer paste the output."
                          % (entry["command"], entry["reads"]))
    return False, (
        "Rejected: not on the inspection allow-list. Offer an allow-listed command instead, or ask "
        "the customer or a human agent to run it and paste the output."
    )


class Report(object):
    """Collects evidence, warnings, checks, and guidance for one run."""

    def __init__(self, command, session_id):
        self.command = command
        self.session_id = session_id
        self.inputs = {}
        self.auto_filled = {}
        self.evidence = {}
        self.warnings = []
        self.limitations = []
        self.checks = []
        self.manual_steps = []
        self.open_questions = []
        self.handoffs = []
        self.degraded = False
        self.fatal_status = False
        self.next_action = ""

    def warn(self, source, error, detail):
        safe_detail = _cli.mask_credentials(detail)
        self.warnings.append({"source": source, "error": error, "detail": safe_detail})
        _cli.warn("%s failed: %s: %s" % (source, error, safe_detail))

    def check(self, name, state, finding, action_required):
        self.checks.append({
            "name": name,
            "state": state,
            "finding": finding,
            "action_required": action_required,
        })

    def status(self):
        if self.fatal_status:
            return C.STATUS_FAIL
        if self.warnings or self.degraded:
            return C.STATUS_DEGRADED
        return C.STATUS_OK

    def as_dict(self):
        return {
            "skill": C.SKILL_NAME,
            "command": self.command,
            "session_id": self.session_id,
            "user_agent": _cli.user_agent(self.session_id),
            "actions_used": api_scope(),
            "status": self.status(),
            "inputs": self.inputs,
            "auto_filled": self.auto_filled,
            "evidence": self.evidence,
            "checks": self.checks,
            "manual_steps": self.manual_steps,
            "open_questions": self.open_questions,
            "handoffs": self.handoffs,
            "limitations": self.limitations,
            "warnings": self.warnings,
            "next_action": self.next_action,
        }


def record_identity(report, session_id):
    """Best effort account UID label; a failure degrades the report but does not stop it."""
    try:
        identity = sts_token.get_caller_identity(session_id)
    except _cli.CliError as exc:
        report.warn("sts get-caller-identity", exc.code, exc.message)
        report.open_questions.append(
            "Account identity is unavailable, so cross-account ownership could not be confirmed. "
            "Configure the CLI credential chain with `aliyun configure`."
        )
        return None
    report.auto_filled["account_uid"] = identity.get("account_id")
    report.auto_filled["identity_arn"] = identity.get("arn")
    report.evidence["identity"] = identity
    return identity


def describe_instances(report, region_id, instance_ids, label, page_size=None):
    """Return instance summaries, or None when the call failed."""
    try:
        if instance_ids:
            params = {"RegionId": region_id, "InstanceIds": json.dumps(instance_ids)}
            data = _cli.call_api(C.ECS_PRODUCT, "DescribeInstances", params,
                                 session_id=report.session_id)
            raw = _cli.extract_items(data, "Instances", "Instance")
        else:
            raw = _cli.paginate(C.ECS_PRODUCT, "DescribeInstances", {"RegionId": region_id},
                                "Instances", "Instance", report.session_id, page_size=page_size)
    except _cli.CliError as exc:
        report.warn(label, exc.code, exc.message)
        return None
    return [summarise_instance(item) for item in raw if isinstance(item, dict)]


def describe_status(report, region_id, instance_ids, label):
    """Return ``{instance_id: status}`` from DescribeInstanceStatus."""
    statuses = {}
    if not instance_ids:
        return statuses
    try:
        for chunk in _chunks(instance_ids, MAX_STATUS_IDS):
            params = {"RegionId": region_id}
            for index, instance_id in enumerate(chunk, start=1):
                params["InstanceId.%d" % index] = instance_id
            data = _cli.call_api(C.ECS_PRODUCT, "DescribeInstanceStatus", params,
                                 session_id=report.session_id)
            for item in _cli.extract_items(data, "InstanceStatuses", "InstanceStatus"):
                if isinstance(item, dict) and item.get("InstanceId"):
                    statuses[str(item["InstanceId"])] = item.get("Status")
    except _cli.CliError as exc:
        report.warn(label, exc.code, exc.message)
    return statuses


def describe_available_resource(report, region_id, zone_id, instance_type, charge_type, label):
    params = {"RegionId": region_id, "DestinationResource": "InstanceType"}
    if zone_id:
        params["ZoneId"] = zone_id
    if instance_type:
        params["InstanceType"] = instance_type
    if charge_type and charge_type != "unknown":
        params["InstanceChargeType"] = charge_type
    try:
        data = _cli.call_api(C.ECS_PRODUCT, "DescribeAvailableResource", params,
                             session_id=report.session_id)
    except _cli.CliError as exc:
        report.warn(label, exc.code, exc.message)
        return None
    zones = _cli.extract_items(data, "AvailableZones", "AvailableZone")
    return _summarize_available(zones)


def probe_cloud_assistant(report, region_id, instance_id):
    params = {
        "RegionId": region_id,
        "InstanceId": instance_id,
        "IncludeOutput": False,
        "PageSize": 5,
        "PageNumber": 1,
    }
    try:
        data = _cli.call_api(C.ECS_PRODUCT, "DescribeInvocations", params,
                             session_id=report.session_id)
    except _cli.CliError as exc:
        report.warn("ecs DescribeInvocations", exc.code, exc.message)
        return
    invocations = _cli.extract_items(data, "Invocations", "Invocation")
    records = []
    for item in invocations:
        if isinstance(item, dict):
            records.append({
                "invoke_id": item.get("InvokeId"),
                "command_id": item.get("CommandId"),
                "command_name": item.get("CommandName"),
                "invocation_status": item.get("InvocationStatus"),
            })
    report.evidence["cloud_assistant_invocations"] = {
        "instance_id": instance_id,
        "returned_records": len(records),
        "records": records[:5],
    }
    report.check(
        "in-guest history",
        "EVIDENCE" if records else "MANUAL",
        "DescribeInvocations returned %d recorded invocation(s) for %s." % (len(records), instance_id),
        "Recorded history only shows that commands were run before; it does not prove the agent is "
        "online now. For instance-level facts, have the customer run an allow-listed inspection "
        "command and paste the output.",
    )
    if not records:
        report.limitations.append(
            "No Cloud Assistant invocation history for %s; in-guest facts must come from the "
            "customer's own pasted command output." % instance_id
        )


def api_scope():
    """Render the versioned actions this skill is allowed to call."""
    items = []
    for product in sorted(C.ALLOWED_ACTIONS):
        version = C.API_VERSION_BY_PRODUCT.get(product, "unknown-version")
        for action in sorted(C.ALLOWED_ACTIONS[product]):
            items.append("%s %s (%s)" % (product, action, version))
    return ", ".join(items)


def render_text(report):
    lines = []
    lines.append("# %s" % report.command.title())
    lines.append("Skill: %s" % C.SKILL_NAME)
    lines.append("Session: %s" % report.session_id)
    lines.append("User-Agent: %s" % _cli.user_agent(report.session_id))
    lines.append("Actions used: %s" % api_scope())
    lines.append("")
    lines.append("## Inputs")
    for key in sorted(report.inputs):
        lines.append("- %s: %s" % (key, report.inputs[key]))
    if report.auto_filled:
        lines.append("## Auto-filled from the credential chain")
        for key in sorted(report.auto_filled):
            lines.append("- %s: %s" % (key, report.auto_filled[key]))
    if report.evidence:
        lines.append("## Evidence")
        lines.append(json.dumps(report.evidence, indent=2, sort_keys=True, default=str))
    if report.checks:
        lines.append("## Checks")
        for item in report.checks:
            lines.append("- [%s] %s: %s" % (item["state"], item["name"], item["finding"]))
            lines.append("  -> %s" % item["action_required"])
    if report.manual_steps:
        lines.append("## Manual steps (customer executes; no write call is made by this skill)")
        for index, step in enumerate(report.manual_steps, start=1):
            lines.append("%d. %s" % (index, step))
    if report.open_questions:
        lines.append("## Open questions")
        for item in report.open_questions:
            lines.append("- %s" % item)
    if report.handoffs:
        lines.append("## Hand off")
        for item in report.handoffs:
            lines.append("- %s" % item)
    if report.limitations:
        lines.append("## Limitations")
        for item in report.limitations:
            lines.append("- %s" % item)
    if report.warnings:
        lines.append("## Warnings")
        for item in report.warnings:
            lines.append("- %s: %s (%s)" % (item["source"], item["detail"], item["error"]))
    lines.append("")
    lines.append("STATUS: %s" % report.status())
    lines.append("NEXT_ACTION: %s" % (report.next_action or "review the checks above"))
    return "\n".join(lines)


def finish(report, args):
    if getattr(args, "output", "text") == "json":
        sys.stdout.write("%s\n" % json.dumps(report.as_dict(), indent=2, sort_keys=True,
                                             default=str))
    else:
        sys.stdout.write("%s\n" % render_text(report))
    return 0 if report.status() != C.STATUS_FAIL else 1


def add_common(parser):
    parser.add_argument("--output", choices=["text", "json"], default="text",
                        help="report format")
    parser.add_argument("--page-size", type=int, default=C.DEFAULT_PAGE_SIZE,
                        help="listing page size, capped at %d" % C.MAX_PAGE_SIZE)


def guest_report(report, args):
    allowed, reason = (None, "")
    if args.check:
        allowed, reason = validate_guest_command(args.check)
        report.inputs = {"proposed_command": args.check}
    else:
        report.inputs = {"proposed_command": "none, listing the allow-list"}
    report.evidence = {
        "allow_list": C.GUEST_COMMAND_ALLOWLIST,
        "manual_only": C.GUEST_COMMAND_MANUAL_ONLY,
    }
    report.manual_steps = [
        "Announce the command, what it reads, its scope, and that it has no side effect, then get "
        "an explicit confirmation. One command per confirmation.",
        "Have the customer or their technician run it and paste the raw output back; do not "
        "paraphrase numbers.",
        "Windows volumes have no inode equivalent, so a size estimate from Get-Volume or "
        "Get-PSDrive is lower confidence than a Linux df and du pair; say so in the report.",
        "If the fact is not obtainable this way, continue with cloud evidence only and end the "
        "report with STATUS: DEGRADED naming the missing fact.",
    ]
    if allowed is None:
        report.check(
            "allow-list", "EVIDENCE",
            "%d inspection command(s) are allowed; %d command(s) stay manual this build."
            % (len(C.GUEST_COMMAND_ALLOWLIST), len(C.GUEST_COMMAND_MANUAL_ONLY)),
            "Run again with --check \"<command>\" before offering anything inside the instance.")
        report.next_action = "Pick one allow-listed command that answers the missing fact, announce " \
                             "it, get confirmation, and collect the pasted output."
    elif allowed:
        report.check("command policy", "EVIDENCE", reason,
                     "Announce and confirm before the customer runs it.")
        report.next_action = "Collect the pasted output and record it as customer-provided evidence."
    else:
        report.check("command policy", "MANUAL", reason,
                     "Refuse the automation request and give the documented console procedure with "
                     "its risk and the snapshot-first gate.")
        report.next_action = "State the boundary, then provide the manual procedure instead of a " \
                             "command to run."
    return report


def build_parser():
    parser = argparse.ArgumentParser(
        prog="site_migration.py",
        description="Plan, pre-check, and verify an ECS whole-site or server-to-server move. "
                    "Inspection-only: this tool never mutates cloud resources.",
    )
    sub = parser.add_subparsers(dest="command")

    plan = sub.add_parser("plan", help="route the request and print human-executed steps")
    plan.add_argument("--source-kind", required=True,
                      choices=["ecs", "ecs-expired", "virtual-host", "other-cloud", "idc"],
                      help="what is being moved")
    plan.add_argument("--account-relation", default="unknown", choices=["same", "cross", "unknown"])
    plan.add_argument("--region-relation", default="unknown", choices=["same", "cross", "unknown"])
    plan.add_argument("--target-state", default="unknown",
                      choices=["purchased", "not-purchased", "unknown"],
                      help="whether the destination instance already exists")
    plan.add_argument("--charge-type", default="unknown",
                      choices=["PREPAID", "POSTPAID", "unknown"])
    plan.add_argument("--guest-os", default="unknown", choices=["linux", "windows", "unknown"])
    plan.add_argument("--symptom", default="", help="verbatim customer wording, used to detect "
                                                   "out-of-scope axes and known error strings")
    add_common(plan)

    pre = sub.add_parser("precheck", help="gather pre-migration cloud evidence")
    pre.add_argument("--region-id", required=True, help="region of the source instances")
    pre.add_argument("--source-instance-ids", default="", help="comma-separated instance ids")
    pre.add_argument("--target-region-id", default="", help="region of the destination")
    pre.add_argument("--target-instance-ids", default="", help="comma-separated destination ids")
    pre.add_argument("--target-zone-id", default="")
    pre.add_argument("--instance-type", default="", help="destination instance type to check")
    pre.add_argument("--charge-type", default="unknown", choices=["PREPAID", "POSTPAID", "unknown"])
    pre.add_argument("--error-text", default="", help="pasted error text to identify")
    pre.add_argument("--check-cloud-assistant", action="store_true",
                     help="also read Cloud Assistant invocation history for the first source id")
    add_common(pre)

    cut = sub.add_parser("cutover", help="gather post-migration verification evidence")
    cut.add_argument("--region-id", required=True, help="region of the destination instances")
    cut.add_argument("--target-instance-ids", required=True, help="comma-separated destination ids")
    cut.add_argument("--source-instance-ids", default="", help="optional source ids for compare")
    cut.add_argument("--source-region-id", default="", help="region of the source ids")
    cut.add_argument("--domains", default="", help="comma-separated domain names to re-point")
    cut.add_argument("--error-text", default="", help="pasted error text to identify")
    add_common(cut)

    guest = sub.add_parser("guest-commands",
                           help="print or vet the in-guest inspection command allow-list")
    guest.add_argument("--check", default="",
                       help="a proposed in-guest command to allow or reject")
    add_common(guest)
    return parser


def plan_report(report, args):
    links = C.HELP_LINKS
    steps = report.manual_steps
    steps.append("Confirm in the console that the destination system disk is at least as large as "
                 "the source system disk, and list the data disks that must travel with the site. "
                 "%s" % SOURCE_DISKS_NOTE)

    if args.source_kind in ("ecs", "ecs-expired"):
        if args.account_relation == "unknown":
            report.degraded = True
            report.open_questions.append(
                "Are source and destination in the same Alibaba Cloud account? Cross-account moves "
                "differ: promotions stay with the purchasing account, and prefix lists and port "
                "range lists cannot be carried across accounts.")
        if args.region_relation == "unknown":
            report.degraded = True
            report.open_questions.append(
                "Are source and destination in the same region? A cross-region move needs an image "
                "copy step and changes the public IP.")
        if args.source_kind == "ecs-expired":
            steps.append("Expired or stopped instance: data is still on the disk while the "
                         "instance is retained. Renew briefly, or ask a human agent about a "
                         "short-term extension; an extension is a manual decision and must not be "
                         "promised. %s" % EXPIRY_NOTE)
            steps.append("Take a snapshot of the system disk and every data disk before touching "
                         "anything: %s (billing: %s)"
                         % (links["create_snapshot"], links["snapshot_billing"]))
        if args.account_relation == "cross":
            steps.append("Cross-account, keep billing and configuration: use the instance transfer "
                         "(change of ownership) procedure for the account pair. Official entry "
                         "point for the transfer procedure needs manual confirmation; confirm "
                         "eligibility with a human agent first. Note that account-bound promotions "
                         "do not follow the instance.")
        steps.append("Step 1 - create a custom image from the source instance (the source keeps "
                     "running and is unaffected): %s"
                     % links["create_custom_image_from_instance"])
        if args.region_relation == "cross":
            steps.append("Step 2 - copy that image to the destination region: %s"
                         % links["copy_image_cross_region"])
        if args.account_relation == "cross":
            steps.append("Step 3 - share the image with the destination account. Official entry "
                         "point for image sharing needs manual confirmation.")
        if args.target_state == "purchased":
            steps.append("Apply the image on the existing destination instance by replacing its "
                         "operating system. Official entry point for replacing the operating "
                         "system needs manual confirmation; the console form for lightweight "
                         "servers is %s. RISK: replacing the system disk releases the old system "
                         "disk and its data - snapshot first." % links["reset_simple_application_server"])
        else:
            steps.append("Final step - purchase the destination instance from that image: %s"
                         % links["create_instance_from_custom_image"])
        steps.append("Before buying a new instance type, verify it is sellable in the destination "
                     "region and zone, then validate the image on a pay-as-you-go instance first: "
                     "image and instance-type compatibility cannot be predicted, and some newer "
                     "instance families need an extra driver that has to be installed on the source "
                     "before the image will boot there.")
        if args.charge_type == "PREPAID":
            steps.append("Remaining subscription value and the remaining term cannot be moved to "
                         "another region or another instance. The options are an unsubscription for "
                         "a partial refund, or a compensation decision by a human or the commercial "
                         "owner; this skill only states the rule and never quotes an amount. "
                         "Rules: %s and %s"
                         % (links["unsubscription_rules"], links["refund_rules"]))
    else:
        steps.append("Changing DNS does not move data. The site only works once the web program, "
                     "the database, and the application configuration exist and run on the new "
                     "server; multiple sites can share port 80 through name-based virtual hosts.")
        if args.guest_os == "windows":
            steps.append("Packaging on the source: built-in Windows compression can stall for hours "
                         "on a deep tree of many small files. Archive per directory in batches, or "
                         "use a faster archiver, and verify the archive size before transferring.")
        steps.append("Move the files and a database dump with the customer's own transfer method, "
                     "then deploy the target environment: %s and %s"
                     % (links["deploy_lnmp"], links["build_a_website"]))
        steps.append("Update the application configuration on the destination so it points at the "
                     "new database host, user, password, and name. Editing configuration files is a "
                     "write inside the instance and is executed by the customer, never by this skill.")
        if args.source_kind == "other-cloud":
            steps.append("If a migration-agent import is used instead of a file-level move: an "
                         "unrecognised source distribution is imported as OthersLinux_64, and the "
                         "console cannot reset the root password for that image type. Use the "
                         "console connection or attach an SSH key pair instead: %s. Check whether "
                         "automatic snapshots were attached to the system disk or only to a data "
                         "disk before relying on them."
                         % links["instance_login_credentials"])
        steps.append("Take a snapshot of the destination disks before overwriting an existing "
                     "system: %s (billing: %s)"
                     % (links["create_snapshot"], links["snapshot_billing"]))

    if args.guest_os == "unknown":
        report.open_questions.append(
            "Is the source Linux or Windows? Windows needs the PowerShell inspection commands and "
            "has no inode equivalent, so a volume estimate carries lower confidence.")
    steps.append("Then run the cutover checks: python3 scripts/site_migration.py cutover "
                 "--region-id <destination region> --target-instance-ids <id> --domains <domain list>")
    steps.append("Finally review leftover billing: post-paid and unattached data disks, outbound "
                 "traffic, and side services such as file storage. Bill item detail: %s. NAS "
                 "pricing: %s. Deletion and release are customer actions in the console."
                 % (links["billing_item_detail"], links["nas_pricing"]))

    if args.symptom:
        for anchor in match_error_anchors(args.symptom):
            steps.append("Recognised error - %s: %s Next action: %s"
                         % (anchor["fragment"], anchor["meaning"], anchor["next_action"]))
    report.limitations.append(
        "Every step above is executed by the customer in the console. The image, transfer, "
        "purchase, operating-system replacement, snapshot, security-group, and DNS actions are not "
        "reachable from this skill.")
    report.limitations.append("Documentation entry points still pending confirmation: %s"
                              % "; ".join(C.HELP_LINKS_PENDING))
    report.next_action = "Run precheck with --region-id and the source instance ids to attach " \
                         "cloud evidence to this plan, then execute the steps in order."
    return report


def precheck_report(report, args):
    source_ids = _split_ids(args.source_instance_ids)
    target_ids = _split_ids(args.target_instance_ids)
    target_region = (args.target_region_id or "").strip() or args.region_id
    report.inputs = {
        "source_region_id": args.region_id,
        "source_instance_ids": source_ids or "all instances in the region",
        "target_region_id": target_region,
        "target_instance_ids": target_ids,
        "target_zone_id": args.target_zone_id or "not supplied",
        "target_instance_type": args.instance_type or "not supplied",
    }
    record_identity(report, report.session_id)

    sources = describe_instances(report, args.region_id, source_ids,
                                 "ecs DescribeInstances(source)", page_size=args.page_size)
    if sources is None:
        report.fatal_status = True
        report.next_action = "Fix the failing inspection action (see references/ram-policies.md), " \
                             "then re-run precheck."
        return report
    report.evidence["source_instances"] = sources
    if not sources:
        report.degraded = True
        report.limitations.append("The source listing returned no instance in %s; verify the "
                                  "region and the instance ids." % args.region_id)

    source_instance_ids = [s["instance_id"] for s in sources if s.get("instance_id")]
    statuses = describe_status(report, args.region_id, source_instance_ids,
                               "ecs DescribeInstanceStatus(source)")
    if statuses:
        report.evidence["source_instance_status"] = statuses

    targets = None
    if target_ids:
        targets = describe_instances(report, target_region, target_ids,
                                     "ecs DescribeInstances(target)", page_size=args.page_size)
        if targets is not None:
            report.evidence["target_instances"] = targets
            target_status = describe_status(report, target_region, target_ids,
                                           "ecs DescribeInstanceStatus(target)")
            if target_status:
                report.evidence["target_instance_status"] = target_status

    available = describe_available_resource(report, target_region, args.target_zone_id,
                                            args.instance_type, args.charge_type,
                                            "ecs DescribeAvailableResource")
    if available is not None:
        report.evidence["available_resources"] = available
        if not available:
            report.degraded = True
            report.limitations.append(
                "DescribeAvailableResource returned no sellable entry for the supplied region, "
                "zone, and instance type. Either the parameters are too narrow or the specification "
                "is not sold there; confirm in the console before purchasing.")

    if args.error_text:
        for anchor in match_error_anchors(args.error_text):
            report.check("error anchor", "EVIDENCE", "Pasted error contains: %s" % anchor["fragment"],
                         "%s Next action: %s" % (anchor["meaning"], anchor["next_action"]))

    if args.check_cloud_assistant and source_instance_ids:
        probe_cloud_assistant(report, args.region_id, source_instance_ids[0])

    source_types = sorted({s.get("instance_type") for s in sources if s.get("instance_type")})
    report.check(
        "charge type and expiry", "MANUAL",
        "Billing type per source instance is in the evidence above (%s)." % ", ".join(
            sorted({str(s.get("charge_type")) for s in sources})),
        EXPIRY_NOTE)
    report.check(
        "capacity gate", "MANUAL", SOURCE_DISKS_NOTE,
        "Read the system and data disk sizes in the console for every source and target instance; "
        "an image or snapshot cannot be applied to a smaller system disk.")
    report.check(
        "source specification", "EVIDENCE" if source_types else "MANUAL",
        "Source instance types: %s." % (", ".join(source_types) or "not returned"),
        "Match or exceed the source specification in the destination region, then verify the image "
        "boots on a pay-as-you-go instance before replacing the production server.")
    report.check(
        "security group binding", "EVIDENCE" if sources else "MANUAL",
        "Bound security group ids per instance are in the evidence above.",
        "The destination must allow the ports the site needs (22 or 3389 for login, 80, 443, and "
        "the application or panel port). Rule changes are done by the customer in the console.")
    report.check(
        "in-guest sizing", "MANUAL",
        "The volume of the site and its database is not visible to cloud APIs.",
        "Have the customer run one allow-listed inspection command at a time, announced and "
        "confirmed first, and paste the output: see "
        "references/guest-inspection-and-errors.md.")
    report.limitations.append(
        "This build reads instances, their status, sellable resources, and Cloud Assistant history "
        "only. Disk inventory, image operations, transfers, and DNS are manual console steps.")
    report.next_action = "Resolve the MANUAL checks, take snapshots, then execute the migration " \
                         "steps from `plan` in the console; re-run with `cutover` afterwards."
    return report


def cutover_report(report, args):
    target_ids = _split_ids(args.target_instance_ids)
    source_ids = _split_ids(args.source_instance_ids)
    domains = _split_ids(args.domains)
    report.inputs = {
        "target_region_id": args.region_id,
        "target_instance_ids": target_ids,
        "source_region_id": args.source_region_id or "not supplied",
        "source_instance_ids": source_ids,
        "domains": domains,
    }
    record_identity(report, report.session_id)

    targets = describe_instances(report, args.region_id, target_ids,
                                 "ecs DescribeInstances(target)", page_size=args.page_size)
    if targets is None:
        report.fatal_status = True
        report.next_action = "Grant the ecs:DescribeInstances inspection action from " \
                             "references/ram-policies.md, then re-run cutover."
        return report
    report.evidence["target_instances"] = targets
    statuses = describe_status(report, args.region_id, target_ids, "ecs DescribeInstanceStatus(target)")
    report.evidence["target_instance_status"] = statuses

    if source_ids and args.source_region_id:
        sources = describe_instances(report, args.source_region_id, source_ids,
                                     "ecs DescribeInstances(source)", page_size=args.page_size)
        if sources is not None:
            report.evidence["source_instances"] = sources
    elif source_ids:
        report.degraded = True
        report.limitations.append("Source ids were supplied without --source-region-id, so the "
                                  "source baseline was not read.")

    running = [i for i in target_ids if statuses.get(i) == "Running"]
    not_running = [i for i in target_ids if statuses.get(i) != "Running"]
    report.check(
        "1. destination running", "EVIDENCE" if statuses else "MANUAL",
        "Running: %s. Not confirmed running: %s." % (", ".join(running) or "none",
                                                     ", ".join(not_running) or "none"),
        "If a destination instance is not Running, that is an instance-state question, not a "
        "migration question: hand off to %s." % C.ADJACENT_SKILLS["instance-state"])

    security_groups = []
    for instance in targets:
        for group in instance.get("security_group_ids") or []:
            if group not in security_groups:
                security_groups.append(str(group))
    report.check(
        "2. security group ports", "EVIDENCE" if security_groups else "MANUAL",
        "Bound security groups: %s." % (", ".join(security_groups) or "none returned"),
        "Add inbound rules for the ports the site needs (%s). Rule editing is a customer console "
        "action; logins failing with no route means the port is not allowed, not that the move "
        "lost data." % ", ".join("%s (%s)" % (p["port"], p["use"]) for p in C.CUTOVER_PORTS_HINT))

    public_ips = []
    for instance in targets:
        for ip in (instance.get("public_ip_addresses") or []) + (instance.get("eip_addresses") or []):
            if ip and ip not in public_ips:
                public_ips.append(str(ip))
    if domains:
        report.check(
            "3. DNS re-pointed", "MANUAL",
            "Domains to check: %s. Destination public addresses from the cloud side: %s."
            % (", ".join(domains), ", ".join(public_ips) or "none returned"),
            "Each authoritative record value must equal the new public address; the old server keeps "
            "serving traffic until it does. Verify with the customer's own resolver, and clear the "
            "local DNS cache before concluding that the change failed.")
    else:
        report.check(
            "3. DNS re-pointed", "MANUAL", "No domain names were supplied.",
            "Provide --domains so the expected record value can be compared against %s."
            % (", ".join(public_ips) or "the destination public address"))

    private_ips = []
    for instance in targets:
        for ip in instance.get("private_ip_addresses") or []:
            private_ips.append(str(ip))
    report.check(
        "4. disks, files, and services", "MANUAL",
        "Destination private addresses: %s. Image-based moves copy the disk contents, so a size "
        "that looks smaller than purchased is an expansion question, not a migration failure."
        % (", ".join(private_ips) or "none returned"),
        "Compare disk count and size against the pre-check baseline in the console, then have the "
        "customer confirm with one allow-listed inspection command and paste the output. If the "
        "destination kept the old static private address from the image, fix the network interface "
        "setting; if the service did not start, starting it is the customer's action.")

    if args.error_text:
        for anchor in match_error_anchors(args.error_text):
            report.check("error anchor", "EVIDENCE",
                         "Pasted error contains: %s" % anchor["fragment"],
                         "%s Next action: %s" % (anchor["meaning"], anchor["next_action"]))
    else:
        report.open_questions.append(
            "Paste the exact error text if the site still fails after these checks; a database "
            "connection error, an OthersLinux image type, and a missing service PID file each point "
            "to a different cause.")

    report.check(
        "5. leftover billing", "MANUAL",
        "Stopped or released source-side resources can still bill for post-paid disks and outbound "
        "traffic.",
        "Review the bill item detail (%s) and release or delete what is no longer needed in the "
        "console; refunds and compensation go to a human or the commercial owner. This skill never "
        "quotes an amount." % C.HELP_LINKS["billing_item_detail"])

    report.handoffs.append("Disk size unchanged after an expansion is not a migration failure: "
                           "use %s." % C.ADJACENT_SKILLS["disk-expand"])
    report.handoffs.append("Building an image-based backup or recovery design is out of scope: use "
                           "%s." % C.ADJACENT_SKILLS["backup-image"])
    report.limitations.append("Application-layer fixes (web server configuration, database "
                              "parameters, service start-up) are documented guidance only.")
    report.next_action = "Close the MANUAL checks in order 1 to 5, then re-check the site over " \
                         "HTTPS from outside the customer's own network."
    return report


def _run_selftest():
    """Offline regression locks for the pure migration-decision cores: the
    DescribeInstances projection (summarise_instance) and its IP/nested-list
    helpers, id splitting/chunking, error-anchor matching and the guest-command
    whitelist. A dropped or mis-nested field feeds a wrong migration plan, so the
    exact live DescribeInstances nesting is pinned here with no cloud call.
    Expected values were read off the live functions first. Returns 0 if all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # summarise_instance against the real nested shape {"Group": {"IpAddress": [...]}}:
    # public + vpc-private present, blank eip/inner collapse to [], sgs/tags/vswitch read.
    inst = {"InstanceId": "i-1", "Status": "Running", "RegionId": "cn-hangzhou",
            "InstanceType": "ecs.g6.large",
            "PublicIpAddress": {"IpAddress": ["47.1.1.1"]},
            "EipAddress": {"IpAddress": ""},
            "InnerIpAddress": {"IpAddress": []},
            "VpcAttributes": {"PrivateIpAddress": {"IpAddress": ["172.16.0.9"]},
                              "VSwitchId": "vsw-1", "VpcId": "vpc-1"},
            "SecurityGroupIds": {"SecurityGroupId": ["sg-a", "sg-b"]},
            "Tags": {"Tag": [{"TagKey": "env", "TagValue": "prod"}]}}
    s = summarise_instance(inst)
    expect("summarise_instance: extracts public/vpc-private ips and sg/vswitch",
           s["public_ip_addresses"] == ["47.1.1.1"]
           and s["private_ip_addresses"] == ["172.16.0.9"]
           and s["security_group_ids"] == ["sg-a", "sg-b"] and s["v_switch_id"] == "vsw-1")
    expect("summarise_instance: blank eip/inner lists collapse to [] and tags kept",
           s["eip_addresses"] == [] and s["inner_ip_addresses"] == []
           and s["tags"] == [{"TagKey": "env", "TagValue": "prod"}])
    expect("summarise_instance: non-dict input -> {} (never raises)",
           summarise_instance("junk") == {} and summarise_instance(None) == {})

    # _pick_ip: IpAddress / InternetAddress / bare string / None; _nested_list wrap.
    expect("pick_ip: str, IpAddress list, InternetAddress and None-safe",
           _pick_ip("8.8.8.8") == ["8.8.8.8"]
           and _pick_ip({"IpAddress": ["47.1.1.1"]}) == ["47.1.1.1"]
           and _pick_ip({"InternetAddress": "9.9.9.9"}) == ["9.9.9.9"]
           and _pick_ip(None) == [])
    expect("nested_list: dict wraps to list, absent container -> []",
           _nested_list({"A": {"B": {"x": 1}}}, "A", "B") == [{"x": 1}]
           and _nested_list({}, "A", "B") == [])

    # id handling: strip, de-duplicate, drop empties; chunking for API batching.
    expect("split_ids: strip, dedup, skip empty", _split_ids("i-1, i-2 ,i-1,,i-3") == ["i-1", "i-2", "i-3"])
    expect("chunks: partitions preserving order", _chunks([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]])

    # error anchors: a known fragment is found (case-insensitive), no-match/empty -> [].
    frag = C.KNOWN_ERROR_ANCHORS[0]["fragment"]
    expect("match_error_anchors: known fragment matches; junk/empty do not",
           len(match_error_anchors("prefix " + frag + " suffix")) >= 1
           and match_error_anchors("zzz nothing matches here qqq") == []
           and match_error_anchors("") == [])

    # guest whitelist: inspection-only allowed, mutating/unknown/empty refused.
    expect("guest gate: inspection reading allowed, mutating/unknown/empty refused",
           validate_guest_command("df -h")[0] is True
           and validate_guest_command("rm -rf /")[0] is False
           and validate_guest_command("notarealtool")[0] is False
           and validate_guest_command("")[0] is False)
    return rc


def main(argv=None):
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        sys.stderr.write("[WARN] a subcommand is required: plan, precheck, cutover, or "
                         "guest-commands\n")
        return 2

    session_id = _cli.new_session_id()
    report = Report(args.command, session_id)
    if args.command == "plan":
        plan_report(report, args)
    elif args.command == "precheck":
        precheck_report(report, args)
    elif args.command == "cutover":
        cutover_report(report, args)
    else:
        guest_report(report, args)
    return finish(report, args)


if __name__ == "__main__":
    sys.exit(main())
