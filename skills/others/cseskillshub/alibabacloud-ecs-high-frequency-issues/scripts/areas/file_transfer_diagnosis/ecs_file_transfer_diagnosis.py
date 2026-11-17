#!/usr/bin/env python3
"""Single entry point for ECS file transfer and upload/download diagnosis.

Subcommands
-----------
classify    Route a customer symptom and error string to a branch, likely root
            cause and next action. No cloud call, nothing changes.
collect     Gather instance, health and Cloud Assistant evidence with bounded
            queries, then classify it. Queries only.
invocation  Fetch the result of a previously sent inspection command.
guest-plan  Print the in-guest inspection plan, or send one approved command.

Every run ends with ``STATUS: OK|DEGRADED|FAIL`` and ``NEXT_ACTION:`` so the
answering agent quotes the outcome instead of inventing one.

Usage examples
--------------
    python scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py classify \
        --symptom "ftp uploads report permission denied"
    python scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py collect \
        --region-id cn-hangzhou --instance-id i-abc123
    python scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py guest-plan \
        --region-id cn-hangzhou --instance-id i-abc123 \
        --command "stat /www/wwwroot" --confirm
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import sys

import _cli
import _constants as C
import sts_token

MAX_PLAN_TARGETS = 3


# ---------------------------------------------------------------------------
# Local classification: symptom and error text in, branch and next action out
# ---------------------------------------------------------------------------
def classify(symptom, error_text=""):
    """Return the ordered candidate matches for the reported problem.

    Error strings rank above symptom keywords because they are the harder
    evidence. Both are shown so the customer can see what was matched.
    """
    haystack = "{0} {1}".format(symptom or "", error_text or "").lower()
    matches = []

    for signature in C.ERROR_SIGNATURES:
        if signature["pattern"] in haystack:
            matches.append({
                "kind": "error-signature",
                "matched": signature["pattern"],
                "branch": signature["branch"],
                "root_cause": signature["root_cause"],
                "confidence": signature["confidence"],
                "next_action": signature["next_action"],
            })

    for branch, keywords, root_cause, next_action in C.SYMPTOM_ROUTES:
        hit = next((word for word in keywords if word in haystack), None)
        if hit:
            matches.append({
                "kind": "symptom-keyword",
                "matched": hit,
                "branch": branch,
                "root_cause": root_cause,
                "confidence": "supporting" if matches else "medium",
                "next_action": next_action,
            })

    if not matches:
        matches.append({
            "kind": "no-match",
            "matched": "",
            "branch": "B1",
            "root_cause": "the report carries no known transfer signature, so "
                          "the transfer path itself is still unknown",
            "confidence": "low",
            "next_action": "Ask the intake questions in references/"
                           "symptom-taxonomy.md (who transfers what to where, "
                           "which client and protocol, the exact error text, "
                           "file size and count), then re-run classify.",
        })
    return matches


def render_classification(matches):
    lines = []
    for index, match in enumerate(matches, start=1):
        branch = match["branch"]
        lines.append("  {0}. [{1}] {2}".format(index, branch,
                                               C.BRANCHES.get(branch, "")))
        lines.append("     matched: {0} ({1})".format(
            match["matched"] or "none", match["kind"]))
        lines.append("     likely cause: {0}".format(match["root_cause"]))
        lines.append("     confidence: {0}".format(match["confidence"]))
        lines.append("     next: {0}".format(match["next_action"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cloud evidence
# ---------------------------------------------------------------------------
def collect_evidence(region_id, instance_id, session_id, note=""):
    """Run the bounded query set; return ``(evidence, gaps)``."""
    gaps = []
    evidence = {
        "region": region_id,
        "instanceRequested": instance_id,
        "accountNote": note,
        "autoFilled": {"RegionId": region_id, "InstanceId": instance_id},
        "instances": [],
        "fullStatus": [],
        "cloudAssistant": [],
        "recentInvocations": [],
    }

    evidence["instances"] = _describe(
        "ecs:DescribeInstances",
        {"RegionId": region_id, "InstanceIds": json.dumps([instance_id])},
        "Instances.Instance", session_id, gaps)

    if not evidence["instances"]:
        gaps.append("No instance matched {0} in {1}; every conclusion below "
                    "stays unconfirmed until the id and region are "
                    "right.".format(instance_id, region_id))
        return evidence, gaps

    instance = _as_dict(evidence["instances"][0])
    evidence["instanceId"] = instance.get("InstanceId")
    evidence["instanceRegion"] = instance.get("RegionId", "")
    evidence["status"] = instance.get("Status", "")
    evidence["osType"] = _first(instance, "OSName", "OSType")
    evidence["publicIp"] = _public_ip(instance)
    evidence["internalIp"] = _internal_ip(instance)
    evidence["bandwidthConfig"] = _bandwidth_config(instance)
    evidence["securityGroupIds"] = _security_group_ids(instance)
    evidence["chargeType"] = instance.get("InstanceChargeType", "")

    actual_region = evidence["instanceRegion"]
    if actual_region and actual_region != region_id:
        gaps.append("--region-id said {0} but the response places the instance "
                    "in {1}; trust the response field and re-check which region "
                    "owns this instance.".format(region_id, actual_region))
        region_id = actual_region

    evidence["fullStatus"] = _describe(
        "ecs:DescribeInstancesFullStatus",
        {"RegionId": region_id, "InstanceId.1": instance.get("InstanceId")},
        "InstanceFullStatusSet.InstanceFullStatusType", session_id, gaps)

    evidence["cloudAssistant"] = _describe(
        "ecs:DescribeCloudAssistantStatus",
        {"RegionId": region_id, "InstanceId.1": instance.get("InstanceId")},
        "InstanceCloudAssistantStatusSet.InstanceCloudAssistantStatus",
        session_id, gaps)
    if not evidence["cloudAssistant"]:
        gaps.append("Cloud Assistant status is unknown, so in-guest inspection "
                    "must be treated as unavailable for this instance.")

    evidence["recentInvocations"] = _describe(
        "ecs:DescribeInvocations",
        {"RegionId": region_id, "InstanceId": instance.get("InstanceId")},
        "Invocations.Invocation", session_id, gaps)

    return evidence, gaps


def _describe(action, params, list_path, session_id, gaps):
    """Paged query that degrades to an empty list and records why."""
    query = dict(params)
    query.setdefault("PageSize", C.PAGE_SIZE)
    query.setdefault("PageNumber", 1)
    try:
        return _cli.collect_paged(action, query, list_path,
                                  session_id=session_id)
    except _cli.CliError as error:
        if _cli.is_arrears(str(error)):
            gaps.append(
                "{0} was refused because the account balance stopped the "
                "resource. That is an account and billing matter, not a "
                "transfer fault: route it to the billing support channel "
                "before continuing."
                .format(action.split(":", 1)[1]))
        else:
            gaps.append("{0} unavailable ({1}).".format(
                action.split(":", 1)[1], error))
        return []


def _first(mapping, *keys):
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", []):
            return value
    return ""


def _public_ip(instance):
    pool = ((instance.get("PublicIpAddresses") or {}).get(
        "PublicIpAddress") or [])
    if pool:
        return list(pool)
    eip = instance.get("EipAddress") or {}
    return [eip["IpAddress"]] if eip.get("IpAddress") else []


def _internal_ip(instance):
    vpc = instance.get("VpcAttributes") or {}
    pool = ((vpc.get("PrivateIpAddresses") or {}).get("PrivateIpAddress") or [])
    if pool:
        return list(pool)
    return list((instance.get("InnerIpAddress") or {}).get(
        "InnerIpAddress") or [])


def _bandwidth_config(instance):
    return {
        "internetMaxBandwidthIn": instance.get("InternetMaxBandwidthIn", ""),
        "internetMaxBandwidthOut": instance.get("InternetMaxBandwidthOut", ""),
        "instanceNetworkType": instance.get("InstanceNetworkType", ""),
        "chargeType": instance.get("InternetChargeType", ""),
    }


def _security_group_ids(instance):
    return list(((instance.get("SecurityGroupIds") or {}).get(
        "SecurityGroupId")) or [])


# ---------------------------------------------------------------------------
# In-guest inspection gate
# ---------------------------------------------------------------------------
class GuestPlanError(ValueError):
    """Raised when a command is outside the inspection whitelist."""


def validate_guest_command(command):
    """Accept only whitelisted inspection commands, one command line at a time.

    The check is structural: no shell composition characters, a known program,
    only listed flags, and bounded paths. Anything rejected becomes manual
    guidance instead of an executed call.
    """
    text = (command or "").strip()
    if not text:
        raise GuestPlanError("no command supplied")
    if len(text) > C.MAX_COMMAND_LENGTH:
        raise GuestPlanError("the command line exceeds {0} characters".format(
            C.MAX_COMMAND_LENGTH))
    bad = sorted(ch for ch in set(text) if ch in C.DISALLOWED_COMMAND_CHARS)
    if bad:
        raise GuestPlanError("shell composition characters are rejected: "
                             "{0}".format(" ".join(bad)))

    words = text.split()
    program = words[0].rsplit("/", 1)[-1]
    allowed_flags = C.GUEST_COMMAND_WHITELIST.get(program)
    if allowed_flags is None:
        raise GuestPlanError("'{0}' is outside the inspection whitelist".format(
            program))

    arguments = words[1:]
    for index, word in enumerate(arguments):
        if word.startswith("-"):
            flag = word.split("=", 1)[0]
            if flag not in allowed_flags and word not in allowed_flags:
                raise GuestPlanError("the flag {0} is not allowed with "
                                     "{1}".format(word, program))
            if word in C.GUEST_VALUE_FLAGS and "=" not in word:
                if index + 1 >= len(arguments) or arguments[index + 1].startswith("-"):
                    raise GuestPlanError("{0} needs a value".format(word))
        elif len(word) > C.MAX_PATH_LENGTH:
            raise GuestPlanError("a path argument exceeds {0} characters".format(
                C.MAX_PATH_LENGTH))
    return words


def build_inspection_plan(paths=None):
    """The default upload-target plan used by branch B4."""
    targets = (paths or [])[:MAX_PLAN_TARGETS]
    if not targets:
        return ["df -h", "df -i"]
    plan = []
    for target in targets:
        plan.extend(["ls -l {0}".format(target), "stat {0}".format(target),
                     "du -x --max-depth=1 {0}".format(target)])
    return plan


def send_inspection_command(region_id, instance_id, command, session_id):
    """Send one already-validated inspection command through Cloud Assistant.

    Calling this at all is the confirmation step: ``run_guest_plan`` only
    reaches it after ``--confirm`` was passed for this one command.
    """
    words = validate_guest_command(command)
    params = {
        "RegionId": region_id,
        "Type": "RunShellScript",
        "CommandContent": " ".join(words),
        "InstanceId.1": instance_id,
        "Name": "ecs-file-transfer-inspection",
        "Description": "Non-mutating inspection command sent by "
                       "{0}".format(C.SKILL_NAME),
        "Timeout": 60,
    }
    return _cli.call("ecs:run-command", params, session_id=session_id,
                     write=True)


def manual_guidance(command, reason):
    """Turn a refused command into a customer-run step."""
    return (
        "Automatic execution is not available for `{0}` ({1}).\n"
        "Run it on the instance yourself and paste the full output:\n"
        "    {0}\n"
        "It only inspects state, so it is safe to re-run."
    ).format(command, reason)


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------
def render_report(evidence, matches, gaps, guidance):
    lines = ["# ECS file transfer diagnosis report", ""]
    lines.append("Session scope: region {0}, instance {1}".format(
        evidence.get("region"), evidence.get("instanceRequested")))
    if evidence.get("accountNote"):
        lines.append("Account note: {0}".format(evidence["accountNote"]))
    lines.append("Automatically filled parameters: {0}".format(
        ", ".join("{0}={1}".format(key, value) for key, value
                  in (evidence.get("autoFilled") or {}).items())))

    lines.extend(["", "## Evidence collected", format_evidence(evidence)])

    lines.extend(["", "## Symptom classification"])
    lines.append(render_classification(matches))

    lines.extend(["", "## Actions"])
    lines.extend("- {0}".format(item) for item in guidance)

    lines.extend(["", "## Risk and backup notes"])
    lines.append("- Take a manual snapshot of each disk before changing "
                 "anything inside the instance: {0} (billing: {1}).".format(
                     C.DOC_LINKS["snapshot-console"],
                     C.DOC_LINKS["snapshot-billing"]))
    lines.append("- This skill sends inspection commands only. Permission, "
                 "ownership, service, firewall and configuration changes are "
                 "handed over as steps for you to review and run yourself.")

    lines.extend(["", "## Gaps"])
    for gap in list(C.KNOWN_GAPS) + list(gaps):
        lines.append("- {0}".format(gap))
    return "\n".join(lines)


def format_evidence(evidence):
    lines = [
        "- Instance status: {0}".format(evidence.get("status") or "unknown"),
        "- Operating system: {0}".format(evidence.get("osType") or "unknown"),
        "- Public address: {0}".format(
            ", ".join(evidence.get("publicIp") or []) or "none bound"),
        "- Internal address: {0}".format(
            ", ".join(evidence.get("internalIp") or []) or "unknown"),
        "- Security groups attached: {0}".format(
            ", ".join(evidence.get("securityGroupIds") or []) or "none"),
        "- Charge type: {0}".format(evidence.get("chargeType") or "unknown"),
    ]
    band = evidence.get("bandwidthConfig") or {}
    lines.append(
        "- Declared bandwidth: inbound {0} Mbit/s, outbound {1} Mbit/s. The "
        "declared figure is a peak, not a guaranteed rate; charge mode is "
        "{2}.".format(band.get("internetMaxBandwidthIn") or "unknown",
                      band.get("internetMaxBandwidthOut") or "unknown",
                      band.get("chargeType") or "unknown"))
    lines.append("- Health and scheduled events: {0}".format(
        format_full_status(evidence.get("fullStatus") or [])))
    lines.append("- Cloud Assistant agent: {0}".format(
        format_assistant_status(evidence.get("cloudAssistant") or [])))
    lines.append("- Recent command executions: {0}".format(
        format_invocations(evidence.get("recentInvocations") or [])))
    return "\n".join(lines)


def format_full_status(items):
    if not items:
        return "none returned, treat as unverified"
    parts = []
    for raw_item in items:
        item = _as_dict(raw_item)
        status = _first(_as_dict(item.get("Status")), "Name", "Code")
        health = _first(_as_dict(item.get("HealthStatus")), "Name", "Code")
        events = _as_dict(item.get("ScheduledSystemEventSet")).get(
            "ScheduledSystemEventType") or []
        detail = "instance {0}, health {1}".format(status or "unknown",
                                                  health or "unknown")
        if events:
            names = sorted({_first(_as_dict(_as_dict(event).get("EventType")),
                                   "Name", "Code") or "unspecified"
                            for event in events})
            detail += ", scheduled events: {0}".format(", ".join(names))
        parts.append(detail)
    return "; ".join(parts)


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def format_assistant_status(items):
    if not items:
        return "unknown (nothing returned)"
    parts = []
    for raw_item in items:
        item = _as_dict(raw_item)
        raw = _first(item, "CloudAssistantStatus", "Running")
        normalized = str(raw).strip().lower()
        if normalized in ("true", "running"):
            state = "online"
        elif normalized in ("false", "stopped", ""):
            state = "offline or not installed"
        else:
            state = normalized
        version = _first(item, "CloudAssistantVersion", "Version")
        parts.append("{0}{1}".format(state,
                                     ", version " + version if version else ""))
    return "; ".join(parts)


def format_invocations(items):
    if not items:
        return "none recorded"
    shown = []
    for raw_item in items[:5]:
        item = _as_dict(raw_item)
        shown.append("{0} ({1}, {2})".format(
            _first(item, "CommandName", "Name") or "unnamed",
            _first(item, "InvocationStatus", "Status") or "unknown state",
            _first(item, "InvokeId") or "no id"))
    return "{0} total: {1}".format(len(items), "; ".join(shown))


def region_guidance(evidence):
    region = (evidence.get("instanceRegion") or evidence.get("region") or "")
    notes = []
    if any(marker in region for marker in
           C.RESTRICTED_REMOTE_ASSISTANCE_KEYWORDS):
        notes.append(
            "Region {0} sits outside mainland China and remote assistance on "
            "the instance is restricted there, so in-guest inspection is "
            "customer-run by default: expect to work from pasted output rather "
            "than executed commands.".format(region))
    elif region and not region.startswith("cn-"):
        notes.append(
            "Region {0} is not a mainland China region. When the customer "
            "workstation is in mainland China, cross-border routing and "
            "international congestion dominate the transfer speed: compare a "
            "mainland endpoint with an endpoint in the instance region, then "
            "route the link-quality part to "
            "alibabacloud-mtr-network-diagnosis-customer.".format(region))
    if region:
        notes.append(
            "For large files, relay through object storage in the instance's "
            "own region so the payload never crosses the public path twice; "
            "see references/file-transfer-diagnosis__transfer-methods.md.")
    return notes


def manual_steps(evidence, paths):
    steps = []
    for target in (paths or [])[:MAX_PLAN_TARGETS]:
        steps.append("Confirm the upload landed where the application reads: "
                     "`ls -l {0}` and `stat {0}`, through the guest-plan "
                     "subcommand or pasted back by the customer.".format(target))
    steps.append(
        "Ask the customer to test the transfer port from their own network and "
        "again on a phone hotspot; a one-sided failure points at the local "
        "egress path rather than the instance "
        "(references/file-transfer-diagnosis__customer-commands.md).")
    steps.append(
        "Have the customer paste the listening sockets, firewall state and any "
        "panel status from inside the instance. Those commands are outside the "
        "execution whitelist of this skill and stay manual.")
    groups = evidence.get("securityGroupIds") or []
    if groups:
        steps.append(
            "Open the attached security group {0} in the console and compare "
            "its inbound rules with the port matrix in "
            "references/file-transfer-diagnosis__transfer-methods.md; range separators use an English "
            "slash, for example 39000/40000.".format(", ".join(groups)))
    return steps


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def run_classify(args, session_id):
    matches = classify(args.symptom, args.error_text)
    if args.as_json:
        print(json.dumps({"matches": matches}, ensure_ascii=False, indent=2))
    else:
        print(render_classification(matches))
    print("")
    print(C.STATUS_OK)
    print("NEXT_ACTION: {0}".format(matches[0]["next_action"]))
    return 0


def run_collect(args, session_id):
    gaps = []
    note = args.account_note
    try:
        identity = sts_token.resolve_identity(session_id=session_id)
        if not note:
            note = identity.get("UidTag", "")
    except _cli.CliError as error:
        gaps.append("Caller identity unverified ({0}); the report cannot state "
                    "which account the evidence came from.".format(error))

    evidence, evidence_gaps = collect_evidence(args.region_id, args.instance_id,
                                               session_id, note)
    gaps.extend(evidence_gaps)

    matches = classify(args.symptom, args.error_text)
    guidance = []
    guidance.extend(region_guidance(evidence))
    guidance.append("Minimal allow list for the protocol in use: see the port "
                    "matrix in references/file-transfer-diagnosis__transfer-methods.md.")
    guidance.extend(manual_steps(evidence, args.paths))

    if args.as_json:
        payload = {k: v for k, v in evidence.items() if k != "instances"}
        payload.update({"matches": matches, "guidance": guidance,
                        "gaps": list(C.KNOWN_GAPS) + gaps})
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(render_report(evidence, matches, gaps, guidance))

    print("")
    if evidence.get("instances"):
        print(C.STATUS_OK)
        print("NEXT_ACTION: {0}".format(matches[0]["next_action"]))
        return 0
    print(C.STATUS_DEGRADED)
    print("NEXT_ACTION: Confirm the instance id and region with the customer "
          "and re-run collect; until then answer only with the guidance in "
          "references/, and do not claim any reading was taken.")
    return 0


def run_invocation(args, session_id):
    params = {"RegionId": args.region_id, "InvokeId": args.invoke_id,
              "IncludeOutput": "true"}
    if args.instance_id:
        params["InstanceId"] = args.instance_id
    gaps = []
    items = _describe("ecs:DescribeInvocations", params,
                      "Invocations.Invocation", session_id, gaps)
    if gaps:
        print(" ".join(gaps))
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: Re-check the region and invoke id, or ask the "
              "customer to paste the output shown on the Cloud Assistant task "
              "page.")
        return 0
    print(json.dumps(items, ensure_ascii=False, indent=2, default=str))
    if not items:
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: Nothing matched this invoke id; the command was "
              "most likely sent in another region.")
        return 0
    print(C.STATUS_OK)
    print("NEXT_ACTION: Quote the returned output verbatim in the report "
          "instead of paraphrasing it.")
    return 0


def run_guest_plan(args, session_id):
    if not args.command:
        plan = build_inspection_plan(args.paths)
        print(C.GUEST_COMMAND_PREAMBLE)
        print("Proposed inspection plan for {0} in {1}:".format(
            args.instance_id, args.region_id))
        for command in plan:
            print("    {0}".format(command))
        print("")
        print("Nothing has been sent. Each command needs its own approval, so "
              "send them one at a time.")
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: Tell the customer what the command does, that it "
              "changes nothing, and that the approval covers this run only; "
              "then re-run with --command <one command> --confirm once they "
              "agree.")
        return 0

    try:
        validate_guest_command(args.command)
    except GuestPlanError as error:
        print(manual_guidance(args.command, str(error)))
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: Have the customer run the command above and paste "
              "the output; do not route it through another channel.")
        return 0

    if not args.confirm:
        print(C.GUEST_COMMAND_PREAMBLE)
        print("Ready to send exactly one command to {0} in {1}:".format(
            args.instance_id, args.region_id))
        print("    {0}".format(args.command))
        print("Scope: this instance only. Effect: reads state, writes nothing, "
              "so no rollback is needed. The approval covers this run only.")
        print("")
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: Ask the customer to approve this exact command; if "
              "they agree, re-run with --confirm, otherwise ask them to run it "
              "and paste the output.")
        return 0

    try:
        payload = send_inspection_command(args.region_id, args.instance_id,
                                          args.command, session_id)
    except _cli.CliError as error:
        print("Command was not sent: {0}".format(error))
        if _cli.is_permission_error(str(error)):
            print("The calling identity is missing ecs:run-command "
                  "(NoPermission / ImplicitDeny). Attach the policy in "
                  "references/ram-policies.md.")
        print(manual_guidance(args.command, str(error)))
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: Fall back to customer-run output, or install and "
              "start Cloud Assistant before any in-guest inspection.")
        return 0

    print("Sent: {0}".format(args.command))
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    invoke_id = _first(_as_dict(payload), "InvokeId") or "<InvokeId>"
    print(C.STATUS_OK)
    print("NEXT_ACTION: Fetch the output with `python "
          "scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py invocation --region-id {0} "
          "--invoke-id {1}`.".format(args.region_id, invoke_id))
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="ecs_file_transfer_diagnosis.py",
        description="Diagnose ECS file transfer and upload/download failures "
                    "from verified evidence.")
    sub = parser.add_subparsers(dest="mode")
    sub.required = True

    classify_p = sub.add_parser("classify", help="route a symptom with no "
                                                 "cloud call")
    classify_p.add_argument("--symptom", required=True,
                            help="what the customer reports, in their words")
    classify_p.add_argument("--error-text", default="",
                            help="exact error text shown by the client")
    _add_json_flag(classify_p)

    collect_p = sub.add_parser("collect", help="gather cloud evidence")
    _add_target_args(collect_p)
    collect_p.add_argument("--symptom", default="",
                           help="what the customer reports, in their words")
    collect_p.add_argument("--error-text", default="")
    collect_p.add_argument("--paths", nargs="*", default=None,
                           help="upload target paths to reason about")
    collect_p.add_argument("--account-note", default="",
                           help="text recorded in the report when the account "
                                "cannot be resolved")
    _add_json_flag(collect_p)

    invocation_p = sub.add_parser("invocation",
                                  help="fetch a past inspection result")
    invocation_p.add_argument("--region-id", required=True)
    invocation_p.add_argument("--invoke-id", required=True)
    invocation_p.add_argument("--instance-id", default="")

    guest_p = sub.add_parser("guest-plan", help="plan or send one inspection "
                                                "command")
    _add_target_args(guest_p)
    guest_p.add_argument("--command", default="",
                         help="one command line to validate and send")
    guest_p.add_argument("--paths", nargs="*", default=None,
                         help="paths used to build the default plan")
    guest_p.add_argument("--confirm", action="store_true",
                         help="the customer approved this exact command for "
                              "this run")
    return parser


def _add_target_args(parser):
    parser.add_argument("--region-id", required=True,
                        help="region the instance lives in")
    parser.add_argument("--instance-id", required=True,
                        help="ECS instance id, for example i-abc123")


def _add_json_flag(parser):
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine readable output")


HANDLERS = {
    "classify": run_classify,
    "collect": run_collect,
    "invocation": run_invocation,
    "guest-plan": run_guest_plan,
}


def _run_selftest():
    """Offline boundary locks for the command gate, symptom routing and plan.

    ``validate_guest_command`` is a fail-closed structural gate guarding a
    command that is actually dispatched to the instance through Cloud
    Assistant RunCommand (write), so a wrongly-accepted composition character,
    non-whitelisted program, unknown flag or value-less flag is a real
    side-effect risk. ``classify`` ranks hard error signatures above soft
    symptom keywords and must always return a branch; ``build_inspection_plan``
    feeds the B4 plan. Pure logic only - no cloud, no credentials, no subprocess.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        if cond:
            print("PASS {0}".format(name))
        else:
            print("FAIL {0}".format(name))
            rc = 1

    def accepted(cmd):
        try:
            validate_guest_command(cmd)
            return True
        except GuestPlanError:
            return False

    def rejected(cmd):
        try:
            validate_guest_command(cmd)
            return False
        except GuestPlanError:
            return True

    # --- validate_guest_command accepts well-formed whitelist readings
    expect("vgc_df_h", accepted("df -h"))
    expect("vgc_basename_path", accepted("/usr/bin/df -h"))
    expect("vgc_value_flag_with_arg", accepted("findmnt -t ext4"))
    expect("vgc_value_flag_equals", accepted("df --output=SIZE"))
    expect("vgc_stat_no_flag", accepted("stat"))
    expect("vgc_plus_option", accepted("lsof +L1"))
    expect("vgc_ls_with_path", accepted("ls -la /data"))
    # --- and rejects every composition / non-whitelist / malformed shape
    expect("vgc_reject_semicolon", rejected("df -h ; rm"))
    expect("vgc_reject_pipe", rejected("df -h | sh"))
    expect("vgc_reject_redirect", rejected("df -h > /tmp/x"))
    expect("vgc_reject_non_whitelist_program", rejected("rm -rf /"))
    expect("vgc_reject_unknown_flag", rejected("df -Z"))
    expect("vgc_reject_value_flag_missing_value", rejected("findmnt -t"))
    expect("vgc_reject_value_flag_next_is_flag", rejected("df --output -h"))
    expect("vgc_reject_empty", rejected(""))
    expect("vgc_reject_backtick", rejected("df -h `id`"))
    # universal invariant: every whitelist program bare-form must self-accept
    expect("vgc_all_programs_self_accept",
           all(accepted(prog) for prog in C.GUEST_COMMAND_WHITELIST))

    # --- classify: error signature ranks first, symptom is 'supporting'
    both = classify("connect issue", "permission denied")
    expect("cls_error_ranks_first", both[0]["kind"] == "error-signature")
    one = classify("x", "permission denied")
    expect("cls_error_branch", one[0]["branch"] == "B4" and one[0]["confidence"] == "high")
    soft = classify("connect", "")
    expect("cls_symptom_medium_when_alone", soft[0]["kind"] == "symptom-keyword"
           and soft[0]["confidence"] == "medium")
    none = classify("totally unknown zzz")
    expect("cls_no_match_defaults_b1", none[0]["kind"] == "no-match" and none[0]["branch"] == "B1")
    expect("cls_empty_still_returns_branch", classify("")[0]["branch"] == "B1")

    # --- build_inspection_plan: default pair, one target -> three bounded steps
    expect("plan_default_pair", build_inspection_plan([]) == ["df -h", "df -i"])
    p = build_inspection_plan(["/data/up"])
    expect("plan_three_per_target", len(p) == 3 and p[0].startswith("ls -l "))

    print("SELFTEST: {0}".format("PASS" if rc == 0 else "FAIL"))
    return rc


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    args = build_parser().parse_args(argv)
    session_id = _cli.new_session_id()
    print("session id: {0}".format(session_id))
    print("user-agent: {0}".format(_cli.user_agent(session_id)))

    if args.mode != "classify" and not _cli.cli_available():
        print("The Alibaba Cloud CLI executable was not found on PATH, so no "
              "evidence can be collected or sent.")
        print(C.STATUS_FAIL)
        print("NEXT_ACTION: Install the CLI and configure a profile with "
              "`aliyun sts get-caller-identity`; `classify` still works without "
              "credentials.")
        return 1

    return HANDLERS[args.mode](args, session_id)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
