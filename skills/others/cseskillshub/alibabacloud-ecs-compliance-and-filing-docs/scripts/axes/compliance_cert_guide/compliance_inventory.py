#!/usr/bin/env python3
"""
compliance_inventory.py -- single entry point of the ECS compliance &
security-qualification evidence guide (strictly READ-ONLY)
===========================================================================
SECURITY: READ-ONLY. This script performs only the two whitelisted ECS read
queries (DescribeInstances / DescribeInstanceStatus, version 2014-05-26)
through the guarded shared layer in _cli.py. It never creates, changes,
deletes, or executes anything in the account or inside an instance, and it
performs NO explicit credential handling: the aliyun CLI default credential
chain resolves authentication on its own.

Modes
-----
* inventory (S3):   --regions cn-hangzhou[,cn-beijing ...]
                    [--instance-ids i-xxx,i-yyy] [--profile NAME] [--json]
  Cross-region read-only asset inventory + embedded manual checklist.
* knowledge (S1/S2/boundary):
                    --list-topics | --topic <key>
  Renders the embedded, evidence-bound knowledge blocks (no API calls).

Output contract (platform playbook):
  report body ...
  Summary section ...
  STATUS: OK | DEGRADED | FAIL
  NEXT_ACTION: <one concrete instruction for the agent>

Exit codes: 0 = OK/DEGRADED conclusion produced; 1 = FAIL (nothing usable);
2 = argparse usage error only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import _cli
from _constants import (
    ACCOUNT_SCOPE_NOTE,
    CHANNEL_PENDING_NOTE,
    CRYPTO_ASSESSMENT_TEXT,
    DOC_URLS,
    ECS_API_VERSION,
    HANDOFF_RULES,
    INSTANCE_PAGE_SIZE,
    MATERIAL_BUCKETS,
    MLPS_CONTROL_MAP,
    RESPONSIBILITY_SPLIT_TEXT,
    SELF_AUDIT_AREAS,
    SKILL_NAME,
    STATUS_PAGE_SIZE,
    TABLE_DIVIDER,
    TABLE_HEADER,
)

REGION_RE = re.compile(r"^[a-z][a-z0-9-]{2,24}$")
INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9]{6,40}$")

TOPICS = (
    "mlps-control-map",   # S1 control areas -> capability -> doc
    "material-scope",     # S2 buckets + pending-channel DEGRADED note
    "self-audit-checklist",  # S3 manual items behind the automated table
    "handoff-rules",      # boundary recognition + handoff sentences
)


def _die_usage(message: str) -> None:
    """Emit a FAIL conclusion (exit 1): a diagnosed condition, not usage."""
    print(f"[ERROR] {message}", file=sys.stderr)
    print("Summary")
    print("-------")
    print(f"What was checked : nothing - required input was missing or "
          f"invalid.")
    print(f"Key finding      : {message}")
    print("\nSTATUS: FAIL")
    print("NEXT_ACTION: collect the missing/invalid input from the customer "
          "and re-run this entry script; never guess values.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# S3 inventory
# ---------------------------------------------------------------------------

def summarize_instance(raw: dict, region: str) -> dict:
    """Project one DescribeInstances item onto the report fields.

    Only fields actually present in the API response are read; anything
    missing stays None (rendered as '(not reported)'), never inferred.
    """
    sg_ids = _cli_list(raw.get("SecurityGroupIds"))
    public_ips = _cli_list(raw.get("PublicIpAddress"))
    eip = raw.get("EipAddress") or {}
    eip_ip = ""
    if isinstance(eip, dict):
        eip_ip = str(eip.get("IpAddress") or "")
    vpc_attrs = raw.get("VpcAttributes") or {}
    vpc_id = ""
    if isinstance(vpc_attrs, dict):
        vpc_id = str(vpc_attrs.get("VpcId") or "")
    return {
        "region": region,
        "instance_id": str(raw.get("InstanceId") or "(not reported)"),
        "name": str(raw.get("InstanceName") or "(not reported)"),
        "status": str(raw.get("Status") or "(not reported)"),
        "zone": str(raw.get("ZoneId") or "(not reported)"),
        "instance_type": str(raw.get("InstanceType") or "(not reported)"),
        "os_type": str(raw.get("OSType") or "(not reported)"),
        "network": str(raw.get("InstanceNetworkType") or "(not reported)"),
        "vpc": vpc_id or "(not reported)",
        "security_groups": ", ".join(sg_ids) if sg_ids else "(none bound)",
        "public_ip": public_ips[0] if public_ips else "no",
        "eip": eip_ip if eip_ip else "no",
    }


def _cli_list(container) -> list[str]:
    """Unwrap the RPC list envelope shapes {Key: [..]} / [..] / scalar."""
    if isinstance(container, dict):
        for value in container.values():
            if isinstance(value, list):
                return [str(v) for v in value]
            if value:
                return [str(value)]
        return []
    if isinstance(container, list):
        return [str(v) for v in container]
    if container:
        return [str(container)]
    return []


def collect_region(region: str, instance_ids: list[str],
                   profile: str | None) -> tuple[list[dict], list[str]]:
    """One region: instances + statuses. Raises CliError to the caller."""
    params: dict = {}
    if instance_ids:
        params["InstanceIds"] = json.dumps(instance_ids)
    raw_instances = _cli.paginate_next_token(
        "DescribeInstances", params, region,
        items_path=["Instances", "Instance"],
        profile=profile, page_size=INSTANCE_PAGE_SIZE)
    rows = [summarize_instance(item, region)
            for item in raw_instances if isinstance(item, dict)]

    statuses = _cli.paginate_page_number(
        "DescribeInstanceStatus", {}, region,
        items_path=["InstanceStatuses", "InstanceStatus"],
        profile=profile, page_size=STATUS_PAGE_SIZE)
    status_map = {str(s.get("InstanceId")): str(s.get("Status"))
                  for s in statuses if isinstance(s, dict)}
    notes: list[str] = []
    for row in rows:
        cross = status_map.get(row["instance_id"])
        if cross and cross != row["status"]:
            notes.append(f"{row['instance_id']}: DescribeInstances says "
                         f"'{row['status']}', DescribeInstanceStatus says "
                         f"'{cross}' - re-check before compiling evidence")
    return rows, notes


def render_markdown(regions: list[str], inventory: dict[str, list[dict]],
                    errors: list[dict], notes: list[str]) -> str:
    out: list[str] = []
    out.append(f"# ECS compliance self-audit inventory ({SKILL_NAME})")
    out.append("")
    out.append(f"- Mode: strictly read-only; API surface: ecs / "
               f"{ECS_API_VERSION} (DescribeInstances, "
               f"DescribeInstanceStatus)")
    out.append(f"- Regions requested: {', '.join(regions)}")
    out.append("- Filters applied: none beyond the region list and the "
               "optional instance-ID filter shown above")
    out.append(f"- Observability: every call carried the per-run session-id "
               f"{_cli.session_id()} in its User-Agent")
    out.append("")
    for region in regions:
        rows = inventory.get(region)
        out.append(f"## Region {region}")
        out.append("")
        if rows is None:
            out.append("- RESULT UNAVAILABLE - this region failed (see the "
                       "Errors section); no data is assumed.")
            out.append("")
            continue
        if not rows:
            out.append("- No instances reported for this region under the "
                       "current credential (valid finding, not an error).")
            out.append("")
            continue
        out.append(TABLE_HEADER)
        out.append(TABLE_DIVIDER)
        for r in rows:
            out.append(
                f"| {r['instance_id']} | {r['name']} | {r['status']} | "
                f"{r['zone']} | {r['instance_type']} | {r['os_type']} | "
                f"{r['network']} | {r['vpc']} | {r['security_groups']} | "
                f"{r['public_ip']} | {r['eip']} |")
        out.append("")
    if notes:
        out.append("## Cross-check notes")
        out.append("")
        for note in notes:
            out.append(f"- {note}")
        out.append("")
    if errors:
        out.append("## Errors (degraded evidence)")
        out.append("")
        for err in errors:
            out.append(f"- region `{err['region']}` during `{err['action']}`:"
                       f" {err['code'] or 'unknown-code'}: {err['message']}")
            if err.get("permission_hint"):
                out.append(f"  - {err['permission_hint']}")
        out.append("")
    out.append("## Manual checklist (customer-side evidence)")
    out.append("")
    out.append("Automated facts above cover ONLY what the two whitelisted "
               "read queries return. These items stay manual (mirrors "
               "references/self-audit-checklist.md):")
    for area in SELF_AUDIT_AREAS:
        out.append(f"- **{area['area']}** (auto basis: {area['auto_basis']})")
        for item_id, check, where in area["items"]:
            out.append(f"  - [{item_id}] {check} -> verify: {where}")
    out.append("")
    out.append(f"- {ACCOUNT_SCOPE_NOTE}")
    out.append("- Security-group RULE detail, snapshot inventory and "
               "in-guest configuration are outside this skill's read "
               "whitelist: console review only.")
    return "\n".join(out)


def run_inventory(regions: list[str], instance_ids: list[str],
                  profile: str | None, as_json: bool) -> int:
    _cli.check_cli_available()
    inventory: dict[str, list[dict]] = {}
    errors: list[dict] = []
    notes: list[str] = []
    for region in regions:
        try:
            rows, region_notes = collect_region(region, instance_ids,
                                                profile)
            inventory[region] = rows
            notes.extend(region_notes)
        except _cli.CliError as err:
            print(f"[WARN] Describe inventory failed in {region}: "
                  f"{err.code or 'unknown'}: {str(err)[:300]}",
                  file=sys.stderr)
            hint = ""
            if err.is_permission:
                hint = ("permission gap: grant the missing action per the "
                        "minimal policy in references/ram-policies.md "
                        "(literals: NoPermission / ImplicitDeny)")
            errors.append({"region": region,
                           "action": "DescribeInstances + "
                                     "DescribeInstanceStatus",
                           "code": err.code, "message": str(err)[:300],
                           "permission_hint": hint})

    total_ok = sum(len(v) for v in inventory.values())
    if not inventory:  # every region failed
        print("Summary")
        print("-------")
        print("What was checked : the requested regions, one read-only "
              "query path each.")
        print("Key finding      : every region query failed; no usable "
              "evidence was collected.")
        for err in errors:
            print(f"  - {err['region']}: {err['code'] or 'unknown'}")
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: fix credentials (user runs `aliyun configure`) "
              "or grant the read actions per references/ram-policies.md, "
              "then re-run the same command.")
        return 1

    report = render_markdown(regions, inventory, errors, notes)
    status = "OK" if not errors else "DEGRADED"
    summary = (f"Queried {len(regions)} region(s) read-only; "
               f"{total_ok} instance(s) reported; "
               f"{len(errors)} region(s) degraded.")
    next_action = ("relay this report verbatim under the Final Answer "
                   "Contract; keep automated facts separate from manual "
                   "checklist items; for out-of-scope symptoms use "
                   "references/handoff-matrix.md")
    if errors:
        next_action = ("relay the report INCLUDING the Errors section; for "
                       "each permission hint, name the missing action and "
                       "point to references/ram-policies.md")

    if as_json:
        print(json.dumps({
            "skill": SKILL_NAME,
            "mode": "inventory",
            "status": status,
            "session_id": _cli.session_id(),
            "regions": regions,
            "instance_ids_filter": instance_ids or None,
            "inventory": inventory,
            "notes": notes,
            "errors": errors,
            "summary": summary,
            "next_action": next_action,
            "account_scope_note": ACCOUNT_SCOPE_NOTE,
        }, indent=2, ensure_ascii=True))
    else:
        print(report)
        print("")
        print("Summary")
        print("-------")
        print(f"What was checked : {', '.join(regions)} via the two "
              f"whitelisted read queries.")
        print(f"Key finding      : {summary}")
        print("Next step        : work the manual checklist with the "
              "customer's administrators; re-run before the assessment to "
              "refresh facts.")
        print(f"\nSTATUS: {status}")
        print(f"NEXT_ACTION: {next_action}")
    return 0


# ---------------------------------------------------------------------------
# Knowledge topics (S1 / S2 / S3 / boundary)
# ---------------------------------------------------------------------------

def topic_control_map() -> str:
    lines = ["# MLPS 2.0 (Dengbao) control-area map (S1)", ""]
    lines.append(RESPONSIBILITY_SPLIT_TEXT)
    lines.append("")
    for entry in MLPS_CONTROL_MAP:
        lines.append(f"## {entry['area']}")
        lines.append(f"- Customer wording: {entry['customer_wording']}")
        lines.append(f"- Platform capability: {entry['capability']}")
        lines.append(f"- Boundary: {entry['boundary']}")
        for doc_key in entry["docs"]:
            doc = DOC_URLS[doc_key]
            lines.append(f"- Official doc: {doc['title']} -> {doc['url']}")
        lines.append("")
    lines.append("## Cryptographic assessment note")
    lines.append(CRYPTO_ASSESSMENT_TEXT)
    lines.append("")
    lines.append("Expansion discipline: the documents above are the ONLY "
                 "citable links of this release; anything else is pending "
                 "human verification - say so verbatim.")
    return "\n".join(lines)


def topic_material_scope() -> str:
    lines = ["# Compliance / qualification materials: buckets (S2)", ""]
    lines.append(RESPONSIBILITY_SPLIT_TEXT)
    lines.append("")
    for bucket in MATERIAL_BUCKETS:
        lines.append(f"## {bucket['bucket']}")
        lines.append(f"- Examples: {bucket['examples']}")
        lines.append(f"- Issued/owned by: {bucket['owner']}")
        lines.append(f"- How obtained: {bucket['how']}")
        lines.append("")
    lines.append(CHANNEL_PENDING_NOTE)
    lines.append("")
    lines.append("Do not claim any specific file name, seal, or acceptance "
                 "outcome; bucket B always belongs to an accredited "
                 "assessment body and bucket C to the human commercial "
                 "channel.")
    return "\n".join(lines)


def topic_self_audit() -> str:
    lines = ["# Pre-assessment self-audit checklist (S3 companion)", ""]
    lines.append("Automated facts come from "
                 "`compliance_inventory.py --regions ...`; the items below "
                 "are manual customer actions. Never mark one as passed "
                 "from a console guess.")
    lines.append("")
    for area in SELF_AUDIT_AREAS:
        lines.append(f"## {area['area']}")
        lines.append(f"- Auto basis: {area['auto_basis']}")
        for item_id, check, where in area["items"]:
            lines.append(f"- [{item_id}] {check} -> verify: {where}")
        lines.append("")
    lines.append(ACCOUNT_SCOPE_NOTE)
    return "\n".join(lines)


def topic_handoff() -> str:
    lines = ["# Handoff rules (boundary, RO skill)", ""]
    for rule in HANDOFF_RULES:
        lines.append(f"- If you hear: {', '.join(rule['keywords'])}")
        lines.append(f"  Hand off to: {rule['target']}")
        lines.append(f"  Say: {rule['sentence']}")
        lines.append("")
    lines.append("Serve the compliance part of a mixed request; emit the "
                 "handoff line(s) for the rest; never execute anything.")
    return "\n".join(lines)


TOPIC_RENDERERS = {
    "mlps-control-map": topic_control_map,
    "material-scope": topic_material_scope,
    "self-audit-checklist": topic_self_audit,
    "handoff-rules": topic_handoff,
}


def run_knowledge(topic: str | None, list_topics: bool, as_json: bool) -> int:
    if list_topics:
        if as_json:
            print(json.dumps({"topics": list(TOPICS),
                              "status": "OK"}, indent=2))
        else:
            print("Available topics: " + ", ".join(TOPICS))
            print("\nSTATUS: OK")
            print("NEXT_ACTION: re-run with --topic <key> for one of the "
                  "topics above")
        return 0
    if topic not in TOPIC_RENDERERS:
        print(f"[ERROR] unknown topic '{topic}'", file=sys.stderr)
        print("Summary")
        print("-------")
        print("Key finding      : topic not found in the embedded set.")
        print("\nSTATUS: FAIL")
        print(f"NEXT_ACTION: run --list-topics; embedded topics are: "
              f"{', '.join(TOPICS)}")
        return 1
    body = TOPIC_RENDERERS[topic]()
    if as_json:
        print(json.dumps({"skill": SKILL_NAME, "mode": "knowledge",
                          "topic": topic, "text": body, "status": "OK",
                          "no_api_calls": True}, indent=2,
                         ensure_ascii=True))
    else:
        print(body)
        print("\nSTATUS: OK")
        if topic == "material-scope":
            print("NEXT_ACTION: deliver the pending-channel note verbatim "
                  "and mark the channel part as DEGRADED in your answer")
        else:
            print("NEXT_ACTION: relay this content with the cited URLs "
                  "only; anything beyond it is pending human verification")
    return 0


# ---------------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------------

def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def validate_inputs(regions: list[str], instance_ids: list[str]) -> None:
    bad_regions = [r for r in regions if not REGION_RE.match(r)]
    if bad_regions:
        _die_usage(f"invalid RegionId format: {', '.join(bad_regions)} "
                   f"(expected lowercase region ids like cn-hangzhou)")
    bad_ids = [i for i in instance_ids if not INSTANCE_ID_RE.match(i)]
    if bad_ids:
        _die_usage(f"invalid instance ID(s): {', '.join(bad_ids)} "
                   f"(expected i- prefixed ids)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only ECS compliance self-audit inventory and "
                    "embedded knowledge topics (no changes, no guest "
                    "commands)",
    )
    parser.add_argument("--regions", default="",
                        help="Comma-separated region IDs supplied by the "
                             "customer (inventory mode)")
    parser.add_argument("--instance-ids", default="",
                        help="Optional comma-separated i-* instance IDs to "
                             "narrow the inventory")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable output for the agent")
    parser.add_argument("--list-topics", action="store_true",
                        help="List the embedded knowledge topics and exit")
    parser.add_argument("--topic", default=None,
                        help=f"One of: {', '.join(TOPICS)}")
    args = parser.parse_args()

    if args.list_topics and args.topic:
        _die_usage("--list-topics and --topic cannot be combined")
    if args.topic:
        sys.exit(run_knowledge(args.topic, False, args.json))
    if args.list_topics:
        sys.exit(run_knowledge(None, True, args.json))

    regions = split_csv(args.regions)
    instance_ids = split_csv(args.instance_ids)
    if not regions:
        _die_usage("--regions is required for the inventory mode: ask the "
                   "customer which regions their assessed system lives in "
                   "(never scan unlisted regions)")
    validate_inputs(regions, instance_ids)
    sys.exit(run_inventory(regions, instance_ids, args.profile, args.json))


if __name__ == "__main__":
    main()
