#!/usr/bin/env python3
"""Read-only entry point for ECS system event and maintenance notice questions.

What it does:
  1. checks that the already-configured identity is reachable
  2. resolves the instances named by ID or by IP through one read action
  3. cross-checks the current running status through a second read action
  4. interprets the wording of the notice the customer received
  5. prints an evidence based report with the customer-performed next steps

What it never does: no change API, no command inside an instance, no ticket or
order submission. See SKILL.md for the read-only boundary.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from _cli import (
    CliError,
    build_user_agent,
    chunked,
    describe_failure_for_customer,
    flatten_instance_ids,
    new_session_id,
    redact,
    run_aliyun,
    warn,
)
from _constants import (
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_INSTANCE_STATUS,
    CLI_TIMEOUT_SECONDS,
    DOC_VERIFICATION_NOTE,
    ECS_API_VERSION,
    ECS_PRODUCT,
    LIMITATION_EVENT_RECORDS,
    LIMITATION_HOST_HEALTH,
    LIMITATION_NO_WRITE,
    MAX_INSTANCE_IDS,
    MAX_PAGES,
    NEXT_ACTION_DEFAULT,
    NEXT_ACTION_DEGRADED,
    NEXT_ACTION_NEEDS_INSTANCE,
    NOTICE_FAMILIES,
    PAGE_SIZE,
    SKILL_NAME,
    SKILL_TITLE,
    STATE_ENUMERATION_NOTE,
    STS_ACTION_NAME,
    STS_API_VERSION,
    STS_PRODUCT,
)
import sts_token

INSTANCE_FIELDS = (
    ("InstanceId", "instance id"),
    ("InstanceName", "instance name"),
    ("Status", "status from " + ACTION_DESCRIBE_INSTANCES),
    ("InstanceType", "instance type"),
    ("InstanceNetworkType", "network type"),
    ("InstanceChargeType", "billing type"),
    ("RegionId", "region"),
    ("ZoneId", "zone"),
    ("OsName", "operating system"),
    ("CreationTime", "created at"),
    ("LockReason", "lock reason"),
)

STATUS_FIELD_LABELS = (
    ("Status", "status from " + ACTION_DESCRIBE_INSTANCE_STATUS),
    ("HealthStatus", "health status"),
)


# ------------------------------------------------------------------ argparse
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecs_system_event_notice.py",
        description=(
            "Read-only helper for ECS system event and scheduled maintenance "
            "notice questions."
        ),
    )
    parser.add_argument(
        "--region-id",
        required=True,
        help="Region of the instance, for example cn-hangzhou.",
    )
    parser.add_argument(
        "--instance-id",
        dest="instance_ids",
        action="append",
        default=[],
        metavar="ID",
        help="Instance id. Repeat the flag or pass a comma separated list.",
    )
    parser.add_argument(
        "--private-ip",
        dest="private_ips",
        action="append",
        default=[],
        metavar="IP",
        help="Private IP shown in the notice; resolved to an instance id.",
    )
    parser.add_argument(
        "--public-ip",
        dest="public_ips",
        action="append",
        default=[],
        metavar="IP",
        help="Public IP shown in the notice; resolved to an instance id.",
    )
    parser.add_argument(
        "--notice-text",
        default="",
        metavar="TEXT",
        help=(
            "The wording of the notice, rendered into English so it can be "
            "matched against references/notification-playbook.md."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=CLI_TIMEOUT_SECONDS,
        help="Per-call timeout in seconds for every CLI invocation.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional CLI profile name; never a credential value.",
    )
    parser.add_argument(
        "--output",
        choices=("md", "json"),
        default="md",
        help="Report format.",
    )
    return parser


def _split_multi(values: Sequence[str]) -> List[str]:
    """Expand repeated flags and comma separated values into one clean list."""
    collected: List[str] = []
    for value in values:
        for part in str(value).split(","):
            item = part.strip()
            if item and item not in collected:
                collected.append(item)
    return collected


# -------------------------------------------------------------- read API work
def describe_instances(
    region_id: str,
    instance_ids: Sequence[str],
    private_ips: Sequence[str],
    public_ips: Sequence[str],
    session_id: str,
    timeout: int,
    profile: Optional[str],
) -> Tuple[List[Dict[str, Any]], List[str], Optional[CliError]]:
    """Page through DescribeInstances for one selector set."""
    instances: List[Dict[str, Any]] = []
    declared: List[str] = []
    selectors: List[Tuple[str, Sequence[str]]] = []
    if instance_ids:
        selectors.append(("InstanceIds", instance_ids))
    if private_ips:
        selectors.append(("PrivateIpAddresses", private_ips))
    if public_ips:
        selectors.append(("PublicIpAddresses", public_ips))

    for selector_name, selector_values in selectors:
        batches = chunked(list(selector_values), PAGE_SIZE) or [[]]
        for batch_index, batch in enumerate(batches, start=1):
            if len(batches) > 1:
                declared.append(
                    selector_name
                    + " batch "
                    + str(batch_index)
                    + " of "
                    + str(len(batches))
                    + " ("
                    + str(len(batch))
                    + " values)"
                )
            page_number = 1
            while page_number <= MAX_PAGES:
                params = {
                    "RegionId": region_id,
                    "PageSize": PAGE_SIZE,
                    "PageNumber": page_number,
                }
                if batch:
                    params[selector_name] = list(batch)
                try:
                    response = run_aliyun(
                        ECS_PRODUCT,
                        ACTION_DESCRIBE_INSTANCES,
                        params,
                        session_id=session_id,
                        timeout=timeout,
                        profile=profile,
                    )
                except CliError as exc:
                    return instances, declared, exc
                page = (response.get("Instances") or {}).get("Instance") or []
                if isinstance(page, dict):
                    page = [page]
                instances.extend(page)
                total = int(response.get("TotalCount") or 0)
                if not page or page_number * PAGE_SIZE >= total:
                    break
                page_number += 1
            else:
                declared.append(
                    "pagination stopped at MAX_PAGES=" + str(MAX_PAGES) + " for " + selector_name
                )
    return instances, declared, None


def describe_instance_status(
    region_id: str,
    instance_ids: Sequence[str],
    session_id: str,
    timeout: int,
    profile: Optional[str],
) -> Tuple[Dict[str, Dict[str, Any]], Optional[CliError]]:
    """Map instance id to its status record."""
    status_map: Dict[str, Dict[str, Any]] = {}
    if not instance_ids:
        return status_map, None
    for batch in chunked(list(instance_ids), PAGE_SIZE) or [[]]:
        params: Dict[str, Any] = {"RegionId": region_id, "PageSize": PAGE_SIZE}
        if batch:
            params.update(flatten_instance_ids(batch))
        try:
            response = run_aliyun(
                ECS_PRODUCT,
                ACTION_DESCRIBE_INSTANCE_STATUS,
                params,
                session_id=session_id,
                timeout=timeout,
                profile=profile,
            )
        except CliError as exc:
            warn(
                describe_failure_for_customer(exc, region_id)
                + " - continuing with the instance records already read."
            )
            return status_map, exc
        records = (response.get("InstanceStatuses") or {}).get("InstanceStatus") or []
        if isinstance(records, dict):
            records = [records]
        for record in records:
            if isinstance(record, dict) and record.get("InstanceId"):
                status_map[str(record["InstanceId"])] = record
    return status_map, None


# ------------------------------------------------------- notice interpretation
def classify_notice(notice_text: str) -> List[Dict[str, Any]]:
    """Rank the notice families whose wording appears in the notice."""
    haystack = (notice_text or "").lower()
    if not haystack.strip():
        return []
    matches: List[Dict[str, Any]] = []
    for family in NOTICE_FAMILIES:
        hits = [key for key in family["keys"] if str(key).lower() in haystack]
        if hits:
            entry = dict(family)
            entry["matched_keys"] = hits
            entry["score"] = len(hits)
            matches.append(entry)

    unplanned_seen = any(item["id"] == "unplanned-down-migration" for item in matches)
    if unplanned_seen:
        decisive = [
            item
            for item in matches
            if item["id"] != "scheduled-maintenance-reboot"
            or set(item["matched_keys"]) - set(item.get("generic_keys", ()))
        ]
        matches = decisive

    matches.sort(key=lambda item: (-item["score"], item["id"]))
    return matches


# ---------------------------------------------------------------- report parts
def _instance_view(
    instance: Dict[str, Any], status_record: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    view: Dict[str, Any] = {}
    for field, label in INSTANCE_FIELDS:
        value = instance.get(field)
        if isinstance(value, (list, dict)):
            value = json.dumps(value)
        view[label] = value if value not in (None, "", []) else "not returned"
    addresses = (instance.get("VpcAttributes") or {}).get("PrivateIpAddress") or {}
    public_addresses = instance.get("PublicIpAddress") or {}
    view["private ip"] = addresses.get("IpAddress") or "not returned"
    view["public ip"] = public_addresses.get("IpAddress") or "not returned"
    eip = instance.get("EipAddress") or {}
    if eip.get("IpAddress"):
        view["eip"] = eip.get("IpAddress")
    security_groups = (instance.get("SecurityGroupIds") or {}).get("SecurityGroupId")
    if security_groups:
        view["security groups"] = security_groups
    tags = (instance.get("Tags") or {}).get("Tag") or []
    if isinstance(tags, dict):
        tags = [tags]
    view["tags"] = [
        str(tag.get("TagKey")) + "=" + str(tag.get("TagValue"))
        for tag in tags
        if isinstance(tag, dict)
    ]
    if status_record:
        for field, label in STATUS_FIELD_LABELS:
            if status_record.get(field) is not None:
                view[label] = status_record.get(field)
    return view


def _addresses_of(instance: Dict[str, Any]) -> List[str]:
    """Every address a DescribeInstances record can expose."""
    found: List[str] = []
    nested = (instance.get("VpcAttributes") or {}).get("PrivateIpAddress") or {}
    public = instance.get("PublicIpAddress") or {}
    eip = instance.get("EipAddress") or {}
    for source in (nested.get("IpAddress"), public.get("IpAddress")):
        if isinstance(source, str):
            found.append(source)
        elif isinstance(source, list):
            found.extend(str(item) for item in source)
    if eip.get("IpAddress"):
        found.append(str(eip["IpAddress"]))
    legacy = instance.get("InnerIpAddress") or {}
    legacy_value = legacy.get("IpAddress") if isinstance(legacy, dict) else legacy
    if isinstance(legacy_value, list):
        found.extend(str(item) for item in legacy_value)
    elif legacy_value:
        found.append(str(legacy_value))
    return found


def _unresolved(
    wanted: Sequence[str],
    instances: Sequence[Dict[str, Any]],
    matched: Sequence[str],
) -> List[str]:
    """Requested selectors that produced no record, in the order given."""
    present = {str(instance.get("InstanceId") or "") for instance in instances}
    present.update(matched)
    return [item for item in wanted if item not in present]


def build_report(args: argparse.Namespace, session_id: str) -> Dict[str, Any]:
    region_id = args.region_id.strip()
    instance_ids = _split_multi(args.instance_ids)
    private_ips = _split_multi(args.private_ips)
    public_ips = _split_multi(args.public_ips)
    selector_given = bool(instance_ids or private_ips or public_ips)
    declared_parameters: List[str] = [
        "RegionId=" + region_id + " (given by the caller)",
        "PageSize=" + str(PAGE_SIZE) + " (skill default)",
        "session id " + session_id + " (generated for this run)",
        "user agent " + build_user_agent(session_id) + " (attached to every call)",
    ]
    if selector_given:
        declared_parameters.append(
            "selectors queried in region "
            + region_id
            + ": "
            + str(len(instance_ids))
            + " instance id, "
            + str(len(private_ips))
            + " private ip, "
            + str(len(public_ips))
            + " public ip"
        )
    warnings: List[str] = []
    errors: List[Dict[str, str]] = []
    status = "OK"

    if len(instance_ids) > MAX_INSTANCE_IDS:
        warnings.append(
            "Only the first " + str(MAX_INSTANCE_IDS) + " instance ids are queried; "
            + str(len(instance_ids) - MAX_INSTANCE_IDS) + " were skipped."
        )
        instance_ids = instance_ids[:MAX_INSTANCE_IDS]

    caller: Dict[str, str] = {}
    caller_error: Optional[CliError] = None
    if selector_given:
        caller, caller_error = sts_token.resolve_caller(
            session_id, timeout=args.timeout, profile=args.profile
        )
    else:
        declared_parameters.append(
            "identity check skipped: no selector given, so no cloud call is made"
        )
    if caller_error is not None:
        errors.append(
            {
                "step": "identity check",
                "detail": redact(str(caller_error)),
                "meaning": (
                    "The CLI could not resolve the caller. Credentials may be "
                    "missing or expired; configure them outside this skill with "
                    "`aliyun configure`. Instance queries below may also fail."
                ),
            }
        )
        status = "DEGRADED"

    instances: List[Dict[str, Any]] = []
    if selector_given:
        instances, paging_declared, instance_error = describe_instances(
            region_id, instance_ids, private_ips, public_ips, session_id, args.timeout, args.profile
        )
        declared_parameters.extend(paging_declared)
        if instance_error is not None:
            errors.append(
                {
                    "step": ACTION_DESCRIBE_INSTANCES,
                    "detail": describe_failure_for_customer(instance_error, region_id),
                    "meaning": (
                        "Instance facts could not be read. Check the region first: "
                        "an instance listed in another region always looks missing "
                        "here. Other documented causes are that the instance does "
                        "not exist, or that these credentials have no view on it "
                        "(another account, another resource group, or a missing "
                        "read action). The exact code and message are in the line "
                        "above."
                    ),
                }
            )
            status = "DEGRADED"

    matched_ids = [str(instance.get("InstanceId") or "") for instance in instances]
    matched_ids = [item for item in matched_ids if item]

    status_map: Dict[str, Dict[str, Any]] = {}
    if matched_ids:
        status_map, _ = describe_instance_status(
            region_id, matched_ids, session_id, args.timeout, args.profile
        )

    resolved_addresses = [
        address for instance in instances for address in _addresses_of(instance)
    ]
    unresolved_ids = _unresolved(instance_ids, instances, resolved_addresses)
    unresolved_ips = _unresolved(private_ips + public_ips, instances, resolved_addresses)
    unresolved = unresolved_ids + unresolved_ips
    if unresolved:
        warnings.append(
            "No instance record was returned for: "
            + ", ".join(unresolved)
            + " in region "
            + region_id
            + ". An unreadable instance is not evidence that it has no event: it "
            "may live in another region, belong to another account, or be "
            "invisible to these credentials."
        )

    matched_families = classify_notice(args.notice_text)
    if args.notice_text.strip() and not matched_families:
        warnings.append(
            "The notice wording did not match any documented family. Ask the "
            "customer for the exact wording, then re-run; do not guess the "
            "event type."
        )
    if not selector_given:
        declared_parameters.append("no instance selector given: facts section is empty by design")
    if not instances and not matched_families and status == "OK":
        status = "DEGRADED"

    return {
        "title": SKILL_TITLE,
        "skill": SKILL_NAME,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "session_id": session_id,
        "region_id": region_id,
        "caller": caller,
        "api_surface": [
            {"product": ECS_PRODUCT, "action": ACTION_DESCRIBE_INSTANCES, "version": ECS_API_VERSION},
            {
                "product": ECS_PRODUCT,
                "action": ACTION_DESCRIBE_INSTANCE_STATUS,
                "version": ECS_API_VERSION,
            },
            {"product": STS_PRODUCT, "action": STS_ACTION_NAME, "version": STS_API_VERSION},
        ],
        "declared_parameters": declared_parameters,
        "instances": [
            _instance_view(instance, status_map.get(str(instance.get("InstanceId") or "")))
            for instance in instances
        ],
        "unresolved": unresolved,
        "event_data_read": "not supported by this build: " + LIMITATION_EVENT_RECORDS,
        "notice_interpretation": matched_families,
        "warnings": warnings,
        "errors": errors,
        "limitations": [
            LIMITATION_EVENT_RECORDS,
            LIMITATION_HOST_HEALTH,
            LIMITATION_NO_WRITE,
            STATE_ENUMERATION_NOTE,
            DOC_VERIFICATION_NOTE,
        ],
        "status": status,
    }


def next_action_for(report: Dict[str, Any]) -> str:
    if not report["instances"]:
        return NEXT_ACTION_NEEDS_INSTANCE
    if report["status"] != "OK":
        return NEXT_ACTION_DEGRADED
    return NEXT_ACTION_DEFAULT


# ------------------------------------------------------------------- rendering
def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    add = lines.append
    add("# " + report["title"])
    add("")
    add(
        "- Generated: " + report["generated_at_utc"] + " - region `"
        + report["region_id"] + "` - session `" + report["session_id"] + "`"
    )
    add(
        "- Caller: account `" + report["caller"].get("account_masked", "unknown")
        + "`, principal `" + report["caller"].get("principal_masked", "unknown") + "`"
    )
    add("- Read actions used: " + ", ".join(
        item["product"] + ":" + item["action"] for item in report["api_surface"]
    ))
    add("")
    add("## 1. Instance facts")
    add("")
    if report["instances"]:
        for view in report["instances"]:
            add("### " + str(view.get("instance id", "unknown")))
            add("")
            for label, value in view.items():
                if label == "instance id":
                    continue
                add("- " + label + ": " + _render_value(value))
            add("")
    else:
        add("_No instance record was read._")
        add("")
    if report["unresolved"]:
        add("Not resolved in this region: " + ", ".join(report["unresolved"]))
        add("")
    add("## 2. Notice interpretation")
    add("")
    if report["notice_interpretation"]:
        for family in report["notice_interpretation"]:
            add("### " + family["title"])
            add("")
            add("- Matched wording: " + ", ".join(family["matched_keys"]))
            add("- Why the customer received it: " + family["why"])
            add("- State reading: " + family["state"])
            add("- Action required: " + family["action_required"])
            add("- Deadline rule: " + family["answer_deadline"])
            add("- Data impact: " + family["answer_data"])
            add("- IP impact: " + family["answer_ip"])
            add("- Customer options: " + "; ".join(family["options"]))
            add("- Source: " + "; ".join(family["refs"]) + " (" + family["basis"] + ")")
            if family.get("handoff"):
                add("- Handoff: see references/boundary-handoff.md (" + family["handoff"] + ")")
            add("")
    else:
        add("_No notice wording was supplied or nothing matched._")
        add("")
    add("## 3. Next steps for the customer (performed by the customer)")
    add("")
    add(
        "- To see whether an event exists and in which state: open the scheduled "
        "O&M events area of the ECS console for this region. This build cannot "
        "read event records through the API, so the console is the source."
    )
    for family in report["notice_interpretation"]:
        for option in family["options"]:
            add("- " + option)
    add("- Complete step lists: references/customer-selfcheck-steps.md")
    add("- Requests outside this boundary: references/boundary-handoff.md")
    add("")
    add("## 4. Declared parameters and assumptions")
    add("")
    for item in report["declared_parameters"]:
        add("- " + item)
    add("")
    add("## 5. Warnings")
    add("")
    if report["warnings"]:
        for item in report["warnings"]:
            add("- " + item)
    else:
        add("- none")
    add("")
    add("## 6. Read failures")
    add("")
    if report["errors"]:
        for item in report["errors"]:
            add("- " + item["step"] + ": " + item["detail"])
            add("  - what it means: " + item["meaning"])
    else:
        add("- none")
    add("")
    add("## 7. Fixed limitations of this skill")
    add("")
    for item in report["limitations"]:
        add("- " + item)
    add("")
    add("STATUS: " + report["status"])
    add("NEXT_ACTION: " + next_action_for(report))
    return "\n".join(lines) + "\n"


def _render_value(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "not returned"
        return ", ".join(str(item) for item in value[:20])
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


# ------------------------------------------------------------------------ main
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    session_id = new_session_id()
    try:
        report = build_report(args, session_id)
    except CliError as exc:  # pragma: no cover - defensive
        sys.stderr.write("[WARN] " + redact(str(exc)) + "\n")
        report = {
            "status": "FAIL",
            "session_id": session_id,
            "next_action": NEXT_ACTION_DEGRADED,
            "fatal_error": redact(str(exc)),
        }
        print(json.dumps(report, indent=2))
        return 2

    report["next_action"] = next_action_for(report)
    if args.output == "json":
        # ASCII-escaped on purpose: a non-UTF-8 stdout would otherwise raise
        # while printing fields such as a localised OsName.
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))
    if report["status"] == "FAIL":
        return 2
    if report["status"] == "DEGRADED":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
