#!/usr/bin/env python3
"""Single entry point of the read-only ECS stop-mode billing guide.

The agent must call only this script; it must not assemble cloud API calls by
hand. Every cloud call made here is a read-only ``Describe*`` query, and every
conclusion is printed together with the evidence it came from. The script never
stops, starts, reboots or removes an instance, and never runs a command inside
an instance: those are actions the customer performs in the console, after which
``verify-status`` can re-read the state.

Subcommands
    assess        pay-as-you-go eligibility plus the stop-mode billing matrix
    verify-status re-read the running or stopped state after the customer acted
    check-stock   read-only zone availability side-evidence for a failed restart
    report        the combined evidence report (name it explicitly)
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

NOT_RETURNED = "not returned by the API"

CHARGE_TYPE_LABELS = {
    "PrePaid": "subscription (prepaid)",
    "PostPaid": "pay-as-you-go (postpaid)",
}

ELIGIBILITY = {
    "PostPaid": ("eligible", "economical stop mode applies to pay-as-you-go instances"),
    "PrePaid": ("not eligible", "subscription instances cannot use economical stop mode; "
                               "a conversion to pay-as-you-go is a customer-executed change"),
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _kv(label, value):
    return "  {0:<28}: {1}".format(label, value)


def _unwrap(container, key, inner):
    """Return ``container[key][inner]`` as a list, tolerating either shape."""
    node = container.get(key) if isinstance(container, dict) else None
    if isinstance(node, dict):
        value = node.get(inner)
    else:
        value = node
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text(value):
    if value is None or value == "":
        return NOT_RETURNED
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "none"
    return str(value)


def _charge_label(charge_type):
    return CHARGE_TYPE_LABELS.get(charge_type, _text(charge_type))


def _split_ids(raw, limit=C.MAX_INSTANCE_IDS):
    if not raw:
        return [], False
    ids = [piece.strip() for piece in raw.replace(",", " ").split() if piece.strip()]
    truncated = len(ids) > limit
    return ids[:limit], truncated


# ---------------------------------------------------------------------------
# fact collection (read-only)
# ---------------------------------------------------------------------------
def summarize_instance(inst):
    """Pick only the fields this skill needs, and never invent a value."""
    public_ips = _text(_unwrap(inst, "PublicIpAddress", "IpAddress"))
    inner_ips = _text(_unwrap(inst, "InnerIpAddress", "IpAddress"))
    eip = inst.get("EipAddress") or {}
    eip_ip = eip.get("IpAddress") if isinstance(eip, dict) else None
    charge_type = inst.get("InstanceChargeType")
    spot = inst.get("SpotStrategy")
    summary = {
        "instance_id": inst.get("InstanceId"),
        "instance_name": inst.get("InstanceName"),
        "region_id": inst.get("RegionId"),
        "zone_id": inst.get("ZoneId"),
        "status": inst.get("Status"),
        "instance_type": inst.get("InstanceType"),
        "charge_type": charge_type,
        "charge_type_label": _charge_label(charge_type),
        "network_type": inst.get("InstanceNetworkType"),
        "internet_charge_type": inst.get("InternetChargeType"),
        "spot_strategy": spot,
        "public_ips": public_ips,
        "inner_ips": inner_ips,
        "eip": _text(eip_ip),
        "cpu": inst.get("Cpu"),
        "memory_mib": inst.get("Memory"),
    }
    return summary


def eligibility(summary):
    """Map the read charge type to an economical-stop eligibility verdict."""
    verdict = ELIGIBILITY.get(summary.get("charge_type"))
    if verdict:
        return verdict
    return ("unknown", "the charge type was not returned; ask the customer to confirm the "
                       "billing method on the instance details page")


def collect_instances(region_id, instance_ids, page_number, page_size, session_id, notes):
    params = [("RegionId", region_id), ("PageNumber", page_number), ("PageSize", page_size)]
    if instance_ids:
        params.append(("InstanceIds", json.dumps(instance_ids)))
    try:
        data = _cli.run_readonly("DescribeInstances", params, session_id)
    except _cli.CliError as exc:
        _cli.warn(exc)
        notes.append("DescribeInstances failed: {0}".format(exc))
        return [], None
    raw = _unwrap(data, "Instances", "Instance")
    total = data.get("TotalCount")
    return [summarize_instance(item) for item in raw if isinstance(item, dict)], total


def collect_status(region_id, instance_ids, session_id, notes):
    params = [("RegionId", region_id)]
    for index, instance_id in enumerate(instance_ids, start=1):
        params.append(("InstanceId.{0}".format(index), instance_id))
    try:
        data = _cli.run_readonly("DescribeInstanceStatus", params, session_id)
    except _cli.CliError as exc:
        _cli.warn(exc)
        notes.append("DescribeInstanceStatus failed: {0}".format(exc))
        return []
    return _unwrap(data, "InstanceStatuses", "InstanceStatus")


def collect_availability(region_id, zone_id, instance_type, charge_type, destination, session_id, notes):
    params = [("RegionId", region_id), ("DestinationResource", destination)]
    if zone_id:
        params.append(("ZoneId", zone_id))
    if instance_type:
        params.append(("InstanceType", instance_type))
    if charge_type:
        params.append(("InstanceChargeType", charge_type))
    try:
        data = _cli.run_readonly("DescribeAvailableResource", params, session_id)
    except _cli.CliError as exc:
        _cli.warn(exc)
        notes.append("DescribeAvailableResource failed: {0}".format(exc))
        return []
    rows = []
    for zone in _unwrap(data, "AvailableZones", "AvailableZone"):
        if not isinstance(zone, dict):
            continue
        rows.append({
            "zone_id": zone.get("ZoneId", "unknown"),
            "status": zone.get("Status", "unknown"),
            "status_category": zone.get("StatusCategory", "unknown"),
            "resources": _zone_resources(zone),
        })
    return rows


def _zone_resources(zone):
    resources = []
    for group in _unwrap(zone, "AvailableResources", "AvailableResource"):
        for item in _unwrap(group, "SupportedResources", "SupportedResource"):
            if not isinstance(item, dict):
                continue
            resources.append({
                "value": item.get("Value", "unknown"),
                "status": item.get("Status", "unknown"),
                "unit": item.get("Unit", ""),
                "max_amount": item.get("MaxAmount", ""),
            })
    return resources


def availability_verdict(rows, instance_type, notes):
    """Interpret the read-only availability rows without over-claiming."""
    if not rows:
        notes.append("no availability rows returned")
        return ("NO_DATA", "DescribeAvailableResource returned nothing usable; stock must be "
                           "confirmed by the customer retrying or by human support")
    sold_out_zones = [r["zone_id"] for r in rows if str(r["status"]).lower() == "soldout"
                      or str(r["status_category"]).lower() == "withoutstock"]
    available = []
    for row in rows:
        for res in row["resources"]:
            if str(res["status"]).lower() == "available":
                available.append((row["zone_id"], res["value"]))
    if instance_type:
        hits = [item for item in available if item[1] == instance_type]
        if hits:
            return ("AVAILABLE", "the queried instance type is reported available in {0}".format(
                ", ".join(sorted(set(z for z, _ in hits)))))
        if sold_out_zones:
            return ("SOLD_OUT", "zone(s) {0} are reported without stock for this credential".format(
                ", ".join(sorted(set(sold_out_zones)))))
        return ("NO_MATCH", "the queried instance type was not listed as available; it may be sold "
                            "out, unsupported in that zone, or outside what this account can see")
    if sold_out_zones:
        return ("SOLD_OUT", "zone(s) {0} are reported without stock for this credential".format(
            ", ".join(sorted(set(sold_out_zones)))))
    return ("AVAILABLE", "at least one zone reported stock for the queried destination resource")


# ---------------------------------------------------------------------------
# report sections
# ---------------------------------------------------------------------------
def section_header(title):
    return [
        "=" * 78,
        "ECS STOP MODE AND STOPPED-INSTANCE BILLING - {0} (READ-ONLY)".format(title.upper()),
        "=" * 78,
    ]


def session_lines(session_id):
    return [
        _kv("Skill", C.SKILL_NAME),
        _kv("Session id", session_id),
        _kv("User-Agent", _cli.user_agent_for(session_id)),
        _kv("Boundary", "read-only Describe* queries; no lifecycle action is performed"),
        "",
    ]


def declared_input_lines(args, instance_ids, truncated, destination=None, sts_probed=True):
    lines = ["DECLARED INPUTS (assumptions made by this script)"]
    lines.append(_kv("RegionId", args.region_id))
    if instance_ids:
        lines.append(_kv("InstanceIds", ", ".join(instance_ids)))
    else:
        lines.append(_kv("InstanceIds", "not supplied; the region listing was used"))
    if truncated:
        lines.append(_kv("Truncation", "more ids were given than the {0} supported; the first "
                                       "{0} were queried".format(C.MAX_INSTANCE_IDS)))
    lines.append(_kv("PageNumber / PageSize", "{0} / {1}".format(args.page_number, args.page_size)))
    if destination:
        lines.append(_kv("DestinationResource", "{0} (default; change it with "
                           "--destination-resource)".format(destination)))
    charge = getattr(args, "instance_charge_type", None)
    if charge:
        lines.append(_kv("InstanceChargeType filter", charge))
    if sts_probed and not getattr(args, "no_sts", False):
        lines.append(_kv("Credential probe", "sts get-caller-identity was called to prove the "
                                            "default credential chain"))
    return lines


def billing_matrix_lines():
    lines = ["", "BILLING MATRIX (rule knowledge; sources at the end of this report)"]
    row_format = "  {0:<38}{1:<22}{2:<34}{3}"
    lines.append(row_format.format("resource", "normal stop", "economical stop", "released"))
    for row in C.BILLING_MATRIX:
        lines.append(row_format.format(*row))
    lines.append("  Note: the public bandwidth row is deliberately unresolved in this package;")
    lines.append("  answer it only after checking the cited document online and record the date.")
    return lines


def tristate_lines():
    lines = ["", "THREE STATES THE CUSTOMER MIXES UP"]
    for name, meaning, consequence in C.STOP_MODE_TRISTATE:
        lines.append("  {0}".format(name))
        lines.append("      state kept    : {0}".format(meaning))
        lines.append("      consequence   : {0}".format(consequence))
    return lines


def instance_lines(summaries, total):
    lines = ["", "FACTS READ FROM DescribeInstances"]
    if not summaries:
        lines.append("  No instance was returned for this credential and region.")
        lines.append("  Do not conclude that the instance does not exist: it may live in another")
        lines.append("  region, another account, or be filtered out by the supplied ids.")
        return lines
    if total is not None:
        lines.append(_kv("TotalCount reported", total))
    for item in summaries:
        verdict, reason = eligibility(item)
        lines.append("  - {0} ({1})".format(_text(item["instance_id"]), _text(item["instance_name"])))
        lines.append("      {0}".format(_kv("region / zone",
                                            "{0} / {1}".format(_text(item["region_id"]),
                                                               _text(item["zone_id"])))))
        lines.append("      {0}".format(_kv("power state", _text(item["status"]))))
        lines.append("      {0}".format(_kv("charge type", _text(item["charge_type_label"]))))
        lines.append("      {0}".format(_kv("instance type", _text(item["instance_type"]))))
        lines.append("      {0}".format(_kv("network", "{0} / {1}".format(
            _text(item["network_type"]), _text(item["internet_charge_type"])))))
        lines.append("      {0}".format(_kv("public ip", _text(item["public_ips"]))))
        lines.append("      {0}".format(_kv("elastic ip", _text(item["eip"]))))
        lines.append("      {0}".format(_kv("spot strategy", _text(item["spot_strategy"]))))
        lines.append("      {0}".format(_kv("economical stop", "{0} - {1}".format(verdict, reason))))
        lines.append("      {0}".format(_kv("stop mode marker", "not verifiable read-only here; "
                                            "the customer confirms it on the instance page")))
    return lines


def status_lines(region_id, statuses):
    lines = ["", "POWER STATE READ FROM DescribeInstanceStatus ({0})".format(region_id)]
    if not statuses:
        lines.append("  Nothing returned; re-check the instance ids or run assess first.")
        return lines
    for item in statuses:
        if not isinstance(item, dict):
            continue
        lines.append("  {0} -> {1}".format(_text(item.get("InstanceId")), _text(item.get("Status"))))
    lines.append("  A state change proves the customer's action landed. It does not prove which")
    lines.append("  stop mode was chosen, so never report the mode as confirmed.")
    return lines


def stock_lines(rows, verdict_code, verdict_text, instance_type, zone_id):
    lines = ["", "ZONE AVAILABILITY READ FROM DescribeAvailableResource"]
    if instance_type or zone_id:
        lines.append(_kv("queried", "zone {0}, instance type {1}".format(
            _text(zone_id), _text(instance_type))))
    for row in rows:
        lines.append("  {0}: status={1} category={2}".format(
            row["zone_id"], row["status"], row["status_category"]))
        for res in row["resources"][:10]:
            lines.append("      {0} -> {1}{2}".format(
                res["value"], res["status"],
                " (max {0}{1})".format(res["max_amount"], res["unit"]) if res["max_amount"] != "" else ""))
        if len(row["resources"]) > 10:
            lines.append("      ... {0} more entries not listed".format(len(row["resources"]) - 10))
    lines.append("  Verdict: {0} - {1}".format(verdict_code, verdict_text))
    lines.append("  Stock is dynamic and limited to what this account can see; never promise a")
    lines.append("  restart succeeds based on this query alone.")
    return lines


def error_text_lines(raw_text):
    """Interpret the customer's own wording against the verified sentence and phrases."""
    lines = ["", "CUSTOMER ERROR TEXT"]
    text = (raw_text or "").strip()
    if not text:
        lines.append("  No error text supplied; ask the customer to paste the exact console or")
        lines.append("  API message. Do not guess a cause from a paraphrase.")
        return lines
    lines.append(_kv("quoted by customer", text[:300]))
    lowered = text.lower()
    matched = False
    if C.SOLD_OUT_ERROR_PATTERN in lowered:
        matched = True
        lines.append("  verified error sentence matched -> {0}".format(C.SOLD_OUT_READING))
        lines.append("  exact wording: {0}".format(C.SOLD_OUT_ERROR_TEXT))
    for phrase, reading in C.SYMPTOM_PHRASES:
        if phrase in lowered:
            matched = True
            lines.append("  symptom phrase matched (a paraphrase, not an official code): '{0}' -> {1}".format(
                phrase, reading))
    if not matched:
        lines.append("  Nothing verified matched this text; do not map it to a cause here.")
        lines.append("  Route the exact wording to human support if the rules below do not settle it.")
    lines.append("  A sold-out message is a stock problem, not a billing fault and not data loss.")
    return lines


def limitation_lines(notes, has_instances):
    lines = ["", "LIMITATIONS (stated plainly, not glossed over)"]
    lines.append("  1. Actual billed amounts are not available here: there is no billing API in")
    lines.append("     this skill. The customer checks the bill detail page (link below).")
    lines.append("  2. Whether the economical stop mode marker is set cannot be read back through")
    lines.append("     a verified read-only field; the customer confirms it in the console.")
    lines.append("  3. Only instances of the current credential and the queried region are visible.")
    lines.append("  4. Refunds, coupons, arrears, IP recovery and ICP filing changes are out of")
    lines.append("     scope and go to human support.")
    if not has_instances:
        lines.append("  5. No instance fact was established in this run, so every downstream")
        lines.append("     conclusion below is rule knowledge only, not a diagnosis.")
    for note in notes:
        lines.append("  - {0}".format(note))
    return lines


def clarification_lines():
    lines = ["", "STANDING CLARIFICATIONS FOR THE RECURRING MISREADINGS"]
    for item in C.MISCONCEPTION_CLARIFICATIONS:
        lines.append("  - {0}".format(item))
    return lines


def handoff_lines():
    lines = ["", "BOUNDARY AND HANDOFF"]
    for topic, action in C.HANDOFF_TOPICS:
        lines.append("  - {0}: {1}".format(topic, action))
    return lines


def source_lines():
    lines = ["", "SOURCES (verify online before quoting; write the check date into the answer)"]
    for key in sorted(C.DOC_SOURCES):
        lines.append("  - {0}: {1}".format(key.replace("_", " "), C.DOC_SOURCES[key]))
    lines.append("  - Document check date: {fill-at-answer-time}")
    return lines


def next_action_lines(command, has_instances, sold_out):
    lines = ["", "NEXT_ACTION (manual guidance only; this skill changes nothing)"]
    if command == "check-stock":
        if sold_out:
            lines.append("  - Customer retries the start with another instance type, or another zone or")
            lines.append("    region; disk data is preserved and can also be backed up by snapshot first.")
        else:
            lines.append("  - Customer retries the start in the console; the availability read above is")
            lines.append("    side-evidence only, and stock changes minute to minute.")
        return lines
    if not has_instances:
        lines.append("  - Customer confirms the region, the account and the instance ids, then re-runs")
        lines.append("    'report'; nothing was verified about the instance yet.")
        return lines
    lines.append("  - Customer performs any stop, start or release in the console themselves; this")
    lines.append("    skill hands over the steps in references/stop-mode-billing-guide__enable-steps-and-prerequisites.md.")
    lines.append("  - After the customer acts, re-run 'verify-status' to read the power state back.")
    lines.append("  - For an amount question, the customer opens the bill detail page listed in")
    lines.append("    references/stop-mode-billing-guide__stop-mode-billing-rules.md; disputes go to human support.")
    return lines


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def _credential_context(args, session_id, notes):
    if args.no_sts:
        return {"skipped": True}
    try:
        caller = sts_token.get_caller_identity(session_id)
        return {"skipped": False, "account_tag": sts_token.account_tag(caller),
                "identity_type": caller.get("IdentityType") or "unknown"}
    except _cli.CliError as exc:
        _cli.warn(exc)
        notes.append("credential probe failed: {0}".format(exc))
        notes.extend(sts_token.credential_guidance(exc))
        return {"skipped": True, "error": str(exc)}


def _resolve_targets(args, notes):
    instance_ids, truncated = _split_ids(args.instance_ids)
    return instance_ids, truncated


def cmd_assess(args, session_id):
    notes = []
    credential = _credential_context(args, session_id, notes)
    instance_ids, truncated = _resolve_targets(args, notes)
    summaries, total = collect_instances(args.region_id, instance_ids, args.page_number,
                                         args.page_size, session_id, notes)
    payload = {
        "command": "assess",
        "region_id": args.region_id,
        "session_id": session_id,
        "credential": credential,
        "declared_inputs": {
            "instance_ids": instance_ids or None,
            "page_number": args.page_number,
            "page_size": args.page_size,
            "truncated": truncated,
        },
        "instances": summaries,
        "eligibility": dict(
            (item["instance_id"] or "unknown", eligibility(item)[0]) for item in summaries
        ),
        "billing_matrix": [list(row) for row in C.BILLING_MATRIX],
        "notes": notes,
    }
    degraded = bool(notes) or not summaries
    payload["status"] = "DEGRADED" if degraded else "OK"
    payload["next_action"] = ("confirm region, account and instance ids with the customer"
                              if not summaries else
                              "customer follows the console steps; re-run verify-status afterwards")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    out = section_header("assess") + session_lines(session_id)
    out += declared_input_lines(args, instance_ids, truncated)
    if not credential.get("skipped"):
        out += ["", _kv("account tag", credential["account_tag"]),
                _kv("identity type", credential["identity_type"])]
    out += instance_lines(summaries, total)
    out += billing_matrix_lines()
    out += tristate_lines()
    out += clarification_lines()
    out += limitation_lines(notes, bool(summaries))
    out += handoff_lines()
    out += source_lines()
    out += next_action_lines("assess", bool(summaries), False)
    out.append("")
    out.append("STATUS: {0}".format(payload["status"]))
    out.append("NEXT_ACTION: {0}".format(payload["next_action"]))
    print("\n".join(out))
    return 0


def cmd_verify_status(args, session_id):
    notes = []
    instance_ids, truncated = _resolve_targets(args, notes)
    if not instance_ids:
        sys.stderr.write("[WARN] verify-status needs --instance-ids\n")
        print("STATUS: FAIL")
        print("NEXT_ACTION: re-run verify-status with --instance-ids i-xxx,i-yyy")
        return 2
    statuses = collect_status(args.region_id, instance_ids, session_id, notes)
    if args.json:
        print(json.dumps({
            "command": "verify-status", "region_id": args.region_id, "session_id": session_id,
            "instance_ids": instance_ids, "statuses": statuses, "notes": notes,
            "status": "OK" if statuses and not notes else "DEGRADED",
            "next_action": "report the read state; the stop mode marker is not confirmed",
        }, indent=2, sort_keys=True))
        return 0
    out = section_header("verify-status") + session_lines(session_id)
    out += declared_input_lines(args, instance_ids, truncated, sts_probed=False)
    out += status_lines(args.region_id, statuses)
    out += limitation_lines(notes, bool(statuses))
    out.append("")
    out.append("STATUS: {0}".format("OK" if statuses and not notes else "DEGRADED"))
    out.append("NEXT_ACTION: report the state that was read back; a state change never confirms "
               "which stop mode was chosen")
    print("\n".join(out))
    return 0


def cmd_check_stock(args, session_id):
    notes = []
    instance_ids, truncated = _resolve_targets(args, notes)
    zone_id = args.zone_id
    instance_type = args.instance_type
    if not zone_id and instance_ids:
        summaries, _ = collect_instances(args.region_id, instance_ids, args.page_number,
                                         args.page_size, session_id, notes)
        zones = sorted(set(item["zone_id"] for item in summaries if item.get("zone_id")))
        types = sorted(set(item["instance_type"] for item in summaries if item.get("instance_type")))
        if zones:
            zone_id = zones[0]
            notes.append("ZoneId auto-filled from the queried instance: {0}".format(zone_id))
        if types and not instance_type:
            instance_type = types[0]
            notes.append("InstanceType auto-filled from the queried instance: {0}".format(instance_type))
    rows = collect_availability(args.region_id, zone_id, instance_type,
                                args.instance_charge_type or "PostPaid",
                                args.destination_resource, session_id, notes)
    code, text = availability_verdict(rows, instance_type, notes)
    if args.json:
        print(json.dumps({
            "command": "check-stock", "region_id": args.region_id, "session_id": session_id,
            "zone_id": zone_id, "instance_type": instance_type,
            "destination_resource": args.destination_resource, "availability": rows,
            "verdict": {"code": code, "text": text}, "notes": notes,
            "status": "OK" if rows else "DEGRADED",
            "next_action": "customer retries the start with another type, zone or region",
        }, indent=2, sort_keys=True))
        return 0
    out = section_header("check-stock") + session_lines(session_id)
    out += declared_input_lines(args, instance_ids, truncated, destination=args.destination_resource,
                                sts_probed=False)
    out += stock_lines(rows, code, text, instance_type, zone_id)
    out += error_text_lines(getattr(args, "error_text", ""))
    out += limitation_lines(notes, bool(rows))
    out.append("")
    out.append("STATUS: {0}".format("OK" if rows else "DEGRADED"))
    out.append("NEXT_ACTION: the customer retries the start with another instance type, zone or region")
    print("\n".join(out))
    return 0


def cmd_report(args, session_id):
    notes = []
    credential = _credential_context(args, session_id, notes)
    instance_ids, truncated = _resolve_targets(args, notes)
    summaries, total = collect_instances(args.region_id, instance_ids, args.page_number,
                                         args.page_size, session_id, notes)
    statuses = collect_status(args.region_id, instance_ids, session_id, notes) if instance_ids else []
    zone_id = args.zone_id
    instance_type = args.instance_type
    if not zone_id and summaries:
        zones = sorted(set(item["zone_id"] for item in summaries if item.get("zone_id")))
        if zones:
            zone_id = zones[0]
            notes.append("ZoneId auto-filled from the queried instance: {0}".format(zone_id))
    rows = []
    code, text = "SKIPPED", "no zone or instance type was queried; nothing to corroborate"
    if args.with_stock and (zone_id or instance_type):
        rows = collect_availability(args.region_id, zone_id, instance_type,
                                    args.instance_charge_type or "PostPaid",
                                    args.destination_resource, session_id, notes)
        code, text = availability_verdict(rows, instance_type, notes)
    sold_out = code == "SOLD_OUT"
    if args.json:
        print(json.dumps({
            "command": "report", "region_id": args.region_id, "session_id": session_id,
            "credential": credential, "instances": summaries, "statuses": statuses,
            "availability": rows, "verdict": {"code": code, "text": text},
            "customer_error_text": args.error_text,
            "declared_inputs": {"instance_ids": instance_ids or None, "zone_id": zone_id,
                                "instance_type": instance_type,
                                "destination_resource": args.destination_resource},
            "notes": notes,
            "status": "OK" if summaries and not notes else "DEGRADED",
            "next_action": "customer executes the console steps; this skill re-reads state only",
        }, indent=2, sort_keys=True))
        return 0
    out = section_header("report") + session_lines(session_id)
    out += declared_input_lines(args, instance_ids, truncated,
                                destination=args.destination_resource if args.with_stock else None)
    if not credential.get("skipped"):
        out += ["", _kv("account tag", credential["account_tag"]),
                _kv("identity type", credential["identity_type"])]
    out += instance_lines(summaries, total)
    if statuses:
        out += status_lines(args.region_id, statuses)
    if rows or args.with_stock:
        out += stock_lines(rows, code, text, instance_type, zone_id)
    out += error_text_lines(args.error_text)
    out += billing_matrix_lines()
    out += tristate_lines()
    out += clarification_lines()
    out += limitation_lines(notes, bool(summaries))
    out += handoff_lines()
    out += source_lines()
    out += next_action_lines("report", bool(summaries), sold_out)
    out.append("")
    out.append("STATUS: {0}".format("OK" if summaries and not notes else "DEGRADED"))
    out.append("NEXT_ACTION: {0}".format(
        "hand the customer the console steps and the bill self-check entry; re-run verify-status "
        "after the customer acts" if summaries else
        "confirm region, account and instance ids with the customer before answering"))
    print("\n".join(out))
    return 0


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="ecs_stop_mode_billing_guide.py",
        description="Read-only assessment of ECS stop modes, economical-stop eligibility and "
                    "restart stock. This tool never changes a cloud resource.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--region-id", required=True, dest="region_id",
                        help="required region of the instance, for example cn-hangzhou")
    common.add_argument("--instance-ids", default="", dest="instance_ids",
                        help="comma separated instance ids (up to {0})".format(C.MAX_INSTANCE_IDS))
    common.add_argument("--page-number", type=int, default=1, dest="page_number")
    common.add_argument("--page-size", type=int, default=C.DEFAULT_PAGE_SIZE, dest="page_size")
    common.add_argument("--instance-charge-type", default="", dest="instance_charge_type",
                        help="optional PostPaid or PrePaid narrowing")
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--no-sts", action="store_true", dest="no_sts",
                        help="skip the credential probe (not recommended)")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("assess", parents=[common], help="eligibility plus the billing matrix")
    sub.add_parser("verify-status", parents=[common], help="re-read the power state only")
    stock = sub.add_parser("check-stock", parents=[common], help="read-only zone availability")
    stock.add_argument("--zone-id", default="", dest="zone_id")
    stock.add_argument("--instance-type", default="", dest="instance_type")
    stock.add_argument("--error-text", default="", dest="error_text",
                       help="verbatim error text the customer saw, matched against known wording")
    stock.add_argument("--destination-resource", default="InstanceType", dest="destination_resource",
                       help="DestinationResource value for DescribeAvailableResource")
    report = sub.add_parser("report", parents=[common], help="combined evidence report")
    report.add_argument("--zone-id", default="", dest="zone_id")
    report.add_argument("--instance-type", default="", dest="instance_type")
    report.add_argument("--error-text", default="", dest="error_text",
                       help="verbatim error text the customer saw, matched against known wording")
    report.add_argument("--destination-resource", default="InstanceType", dest="destination_resource")
    report.add_argument("--with-stock", action="store_true", dest="with_stock",
                        help="also query zone availability for the restart-failure path")

    return parser


def _run_selftest():
    """Offline regression lock: pure core + stubbed CLI integration."""
    results = {"pass": 0, "fail": 0}

    def check(name, got, want):
        if got == want:
            results["pass"] += 1
        else:
            results["fail"] += 1
            print("FAIL {0}: got {1!r} want {2!r}".format(name, got, want))

    # --- _unwrap ---
    check("unwrap_dict", _unwrap({"Instances": {"Instance": [{"a": 1}]}}, "Instances", "Instance"),
          [{"a": 1}])
    check("unwrap_single_dict", _unwrap({"Instances": {"Instance": {"a": 1}}}, "Instances", "Instance"),
          [{"a": 1}])
    check("unwrap_flat_list", _unwrap({"Instances": [{"a": 1}]}, "Instances", "Instance"),
          [{"a": 1}])
    check("unwrap_missing", _unwrap({}, "Instances", "Instance"), [])
    check("unwrap_none", _unwrap({"Instances": None}, "Instances", "Instance"), [])
    check("unwrap_nondict_container", _unwrap("str", "a", "b"), [])

    # --- _text ---
    check("text_none", _text(None), NOT_RETURNED)
    check("text_empty", _text(""), NOT_RETURNED)
    check("text_list", _text(["a", "b"]), "a, b")
    check("text_empty_list", _text([]), "none")
    check("text_int", _text(42), "42")

    # --- _charge_label ---
    check("charge_postpaid", _charge_label("PostPaid"), "pay-as-you-go (postpaid)")
    check("charge_prepaid", _charge_label("PrePaid"), "subscription (prepaid)")
    check("charge_unknown", _charge_label("Spot"), "Spot")
    check("charge_none", _charge_label(None), NOT_RETURNED)

    # --- _split_ids ---
    ids, trunc = _split_ids("i-a,i-b,i-c", limit=2)
    check("split_ids_truncated", (ids, trunc), (["i-a", "i-b"], True))
    ids, trunc = _split_ids("i-a i-b", limit=10)
    check("split_ids_space", (ids, trunc), (["i-a", "i-b"], False))
    ids, trunc = _split_ids("", limit=10)
    check("split_ids_empty", (ids, trunc), ([], False))
    ids, trunc = _split_ids(None, limit=10)
    check("split_ids_none", (ids, trunc), ([], False))

    # --- summarize_instance ---
    raw = {"InstanceId": "i-x", "InstanceName": "web", "RegionId": "cn-hangzhou",
           "ZoneId": "cn-hangzhou-k", "Status": "Running", "InstanceType": "ecs.g6.large",
           "InstanceChargeType": "PostPaid", "InstanceNetworkType": "vpc",
           "InternetChargeType": "PayByTraffic", "SpotStrategy": "NoSpot",
           "PublicIpAddress": {"IpAddress": ["1.2.3.4"]},
           "InnerIpAddress": {"IpAddress": []},
           "EipAddress": {"IpAddress": ""}, "Cpu": 2, "Memory": 4096}
    s = summarize_instance(raw)
    check("sum_id", s["instance_id"], "i-x")
    check("sum_public", s["public_ips"], "1.2.3.4")
    check("sum_eip", s["eip"], NOT_RETURNED)
    check("sum_charge_label", s["charge_type_label"], "pay-as-you-go (postpaid)")

    # --- eligibility ---
    check("elig_postpaid", eligibility(s)[0], "eligible")
    check("elig_prepaid", eligibility({"charge_type": "PrePaid"})[0], "not eligible")
    check("elig_unknown", eligibility({"charge_type": None})[0], "unknown")

    # --- availability_verdict ---
    notes = []
    code, text = availability_verdict([], "ecs.g6.large", notes)
    check("av_empty", code, "NO_DATA")
    check("av_empty_note", "no availability rows" in notes[-1], True)

    rows = [{"zone_id": "cn-hangzhou-k", "status": "Available", "status_category": "WithStock",
             "resources": [{"value": "ecs.g6.large", "status": "Available", "unit": "",
                            "max_amount": ""}]},
            {"zone_id": "cn-hangzhou-j", "status": "SoldOut", "status_category": "WithoutStock",
             "resources": []}]
    notes = []
    code, text = availability_verdict(rows, "ecs.g6.large", notes)
    check("av_hit", code, "AVAILABLE")
    check("av_hit_zone", "cn-hangzhou-k" in text, True)
    code, text = availability_verdict(rows, "ecs.c5.large", notes)
    check("av_miss_soldout", code, "SOLD_OUT")
    code, text = availability_verdict(
        [{"zone_id": "z1", "status": "Available", "status_category": "WithStock",
          "resources": [{"value": "other", "status": "Available", "unit": "", "max_amount": ""}]}],
        "ecs.g6.large", [])
    check("av_nomatch_no_soldout", code, "NO_MATCH")
    code, _ = availability_verdict(rows, "", [])
    check("av_no_type_soldout", code, "SOLD_OUT")
    # Only status says SoldOut (status_category is normal): .lower() is load-bearing
    status_only_soldout = [
        {"zone_id": "z-so", "status": "SoldOut", "status_category": "WithStock", "resources": []}]
    code, _ = availability_verdict(status_only_soldout, "", [])
    check("av_soldout_via_status_field", code, "SOLD_OUT")
    code, _ = availability_verdict(
        [{"zone_id": "z", "status": "Available", "status_category": "WithStock",
          "resources": [{"value": "x", "status": "Available", "unit": "", "max_amount": ""}]}],
        "", [])
    check("av_no_type_available", code, "AVAILABLE")

    # --- _zone_resources ---
    zone = {"AvailableResources": {"AvailableResource": [
        {"SupportedResources": {"SupportedResource": [
            {"Value": "ecs.g6", "Status": "Available", "Unit": "Instance", "MaxAmount": 10},
            {"Value": "ecs.c5", "Status": "SoldOut"},
        ]}}]}}
    res = _zone_resources(zone)
    check("zr_count", len(res), 2)
    check("zr_first", res[0]["value"], "ecs.g6")
    check("zr_second_status", res[1]["status"], "SoldOut")

    # --- error_text_lines ---
    lines = error_text_lines("The requested resource is sold out in the specified zone")
    joined = "\n".join(lines)
    check("et_soldout_match", "verified error sentence matched" in joined, True)
    lines = error_text_lines("my ip changed after restart")
    check("et_symptom_match", "ip changed" in "\n".join(lines), True)
    lines = error_text_lines("hello world")
    check("et_no_match", "Nothing verified matched" in "\n".join(lines), True)
    lines = error_text_lines("")
    check("et_empty", "No error text supplied" in "\n".join(lines), True)

    # --- _cli helpers ---
    check("mask_akid", _cli.mask_secrets("AccessKeyId=LTAI5tXXX foo"),
          "AccessKeyId=*** foo")
    check("mask_st", _cli.mask_secrets("SecurityToken=abc123"), "SecurityToken=***")
    check("transient_yes", _cli.is_transient("Throttling.User"), True)
    check("transient_timeout", _cli.is_transient("call timed out after 30s"), True)
    check("transient_no", _cli.is_transient("NoPermission"), False)
    code, msg = _cli._split_error("ERROR: SDK.ServerError\nErrorCode: InvalidAccessKeyId\nMessage: bad")
    check("se_code", code, "InvalidAccessKeyId")
    check("se_msg", "bad" in msg, True)
    code, msg = _cli._split_error("")
    check("se_empty", code, "CliFailed")

    # --- assert_read_only ---
    check("aro_ok", _cli.assert_read_only("DescribeInstances"), True)
    try:
        _cli.assert_read_only("StopInstance")
        check("aro_deny", False, True)
    except _cli.CliError as e:
        check("aro_deny", "ReadOnlyWhitelist" in str(e), True)
    try:
        _cli.assert_read_only("SomethingRandom")
        check("aro_not_whitelisted", False, True)
    except _cli.CliError as e:
        check("aro_not_whitelisted", "ReadOnlyWhitelist" in str(e), True)

    # --- _backoff ---
    check("backoff_0", _cli._backoff(0), C.RETRY_BACKOFF_BASE_SECONDS)
    check("backoff_1", _cli._backoff(1), C.RETRY_BACKOFF_BASE_SECONDS * 2)
    check("backoff_cap", _cli._backoff(10) <= C.RETRY_BACKOFF_CAP_SECONDS, True)

    # --- sts_uses_rpc_form (contract guard) ---
    import _constants as _c
    check("sts_rpc_form", _c.ALLOWED_STS_ACTIONS, ("GetCallerIdentity",))

    # --- exit code propagated ---
    src = open(__file__, encoding="utf-8").read()
    check("exit_propagated", "sys.exit(main())" in src and "\n    main()\n" not in src, True)

    print("selftest: {0} passed, {1} failed".format(results["pass"], results["fail"]))
    return 1 if results["fail"] else 0


def main(argv=None):
    if argv is None and "--selftest" in sys.argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "assess": cmd_assess,
        "verify-status": cmd_verify_status,
        "check-stock": cmd_check_stock,
        "report": cmd_report,
    }
    if not args.command or args.command not in handlers:
        parser.print_help(sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: choose one of assess, verify-status, check-stock, report")
        return 2
    if args.page_size < 1 or args.page_size > C.MAX_PAGE_SIZE:
        sys.stderr.write("[WARN] PageSize outside 1..{0}; using {1}\n".format(
            C.MAX_PAGE_SIZE, C.DEFAULT_PAGE_SIZE))
        args.page_size = C.DEFAULT_PAGE_SIZE
    session_id = _cli.new_session_id()
    try:
        return handlers[args.command](args, session_id)
    except _cli.CliError as exc:
        _cli.warn(exc)
        print("STATUS: FAIL")
        if exc.is_auth_failure:
            print("NEXT_ACTION: grant the read-only actions in references/ram-policies.md "
                  "(NoPermission or ImplicitDeny was returned), then re-run")
            print("MISSING_ACTION_SCOPE: {0}".format(", ".join(C.RAM_READ_ONLY_ACTIONS)))
            print("MINIMAL_POLICY:")
            print(C.MINIMAL_RAM_POLICY.rstrip())
        else:
            print("NEXT_ACTION: fix the reported error, then re-run; do not retry a change-making "
                  "call, this skill has none")
        return 2
    except KeyboardInterrupt:
        sys.stderr.write("[WARN] interrupted\n")
        print("STATUS: FAIL")
        print("NEXT_ACTION: re-run the same read-only command")
        return 130


if __name__ == "__main__":
    sys.exit(main())
