#!/usr/bin/env python3
"""Single entry point for the read-only ECS business / human contact routing skill.

The agent runs only this script. It classifies the routing intent in the customer
wording, optionally assembles a read-only resource context pack through the
allowlisted Describe/Get actions, and always emits the hand-off guidance even when
a query fails.

Subcommands: run, classify, context, channels, doctor.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from _cli import CliError, failure_record, run_cli, run_help, session_id, user_agent
from _constants import (
    BUSINESS_TERMS,
    CHANNEL_DIRECTORY_STATUS,
    CLARIFYING_QUESTION,
    COMMERCIAL_ACTION_TERMS,
    CONFIDENCE_THRESHOLD,
    CONSOLE_SERVICE_ENTRY,
    ECS_PRODUCT,
    HANDOFF_TERMS,
    HUMAN_PHONE_TERMS,
    INTENT_BUSINESS,
    INTENT_COMMERCIAL_ACTION,
    INTENT_HUMAN_PHONE,
    INTENT_LABELS,
    INTENT_UNCLASSIFIED,
    MAX_INSTANCE_IDS,
    PAGE_NUMBER,
    PAGE_SIZE,
    READ_ONLY_ALLOWLIST,
    SUPPLEMENTARY_NOTIFICATION_CHANNEL,
)
from sts_token import get_caller_identity

LEXICON: Dict[str, Tuple[str, ...]] = {
    INTENT_BUSINESS: BUSINESS_TERMS,
    INTENT_HUMAN_PHONE: HUMAN_PHONE_TERMS,
    INTENT_COMMERCIAL_ACTION: COMMERCIAL_ACTION_TERMS,
}

AUTO_FILLED_PAGINATION = {"PageNumber": PAGE_NUMBER, "PageSize": PAGE_SIZE}


def _assert_allowed(product: str, action: str) -> None:
    if (product, action) not in READ_ONLY_ALLOWLIST:
        raise CliError("AllowlistViolation",
                       f"{product} {action} is not on the read-only allowlist", action)


def _hits(text: str, terms: Sequence[str]) -> List[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def detect_handoffs(text: str) -> List[Dict[str, Any]]:
    """Technical symptoms are transfer cues here, never triggers owned by this skill."""
    signals = []
    for topic, skill, terms in HANDOFF_TERMS:
        matched = _hits(text, terms)
        if matched:
            signals.append({"topic": topic, "target_skill": skill, "matched_terms": matched})
    return signals


def classify_text(text: str) -> Dict[str, Any]:
    """Deterministic routing-intent classification over the customer wording."""
    matched = {intent: _hits(text, terms) for intent, terms in LEXICON.items()}
    scores = {intent: len(hits) for intent, hits in matched.items()}
    total = sum(scores.values())

    if total == 0:
        intent, confidence = INTENT_UNCLASSIFIED, 0.0
    else:
        intent = max(scores, key=lambda key: (scores[key], key))
        confidence = scores[intent] / total

    return {
        "intent": intent,
        "label": INTENT_LABELS[intent],
        "confidence": round(confidence, 2),
        "term_counts": scores,
        "matched_terms": matched,
        "clarify_needed": confidence < CONFIDENCE_THRESHOLD,
        "handoff_signals": detect_handoffs(text),
    }


def _query(product: str, action: str, params: Dict[str, Any],
           summariser: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    record: Dict[str, Any] = {"action": f"{product} {action}", "params_declared": params}
    try:
        _assert_allowed(product, action)
        body = run_cli(product, action, params)
    except CliError as error:
        failure = failure_record(error, action)
        record.update({"status": "failed", "code": failure["code"],
                       "message": failure["message"], "kind": failure["kind"]})
        return record
    record.update({"status": "ok", "summary": summariser(body)})
    return record


def _summarise_instances(body: Dict[str, Any]) -> Dict[str, Any]:
    items = _dig(body, "Instances", "Instance")
    return {
        "returned": len(items),
        "total_count": body.get("TotalCount", "unknown"),
        "instances": [
            {
                "instance_id": item.get("InstanceId", "unknown"),
                "status": item.get("Status", "unknown"),
                "instance_type": item.get("InstanceType", "unknown"),
                "zone_id": item.get("ZoneId", "unknown"),
                "charge_type": item.get("InstanceChargeType", "unknown"),
            }
            for item in items if isinstance(item, dict)
        ],
    }


def _summarise_status(body: Dict[str, Any]) -> Dict[str, Any]:
    items = _dig(body, "InstanceStatuses", "InstanceStatus")
    return {
        "returned": len(items),
        "total_count": body.get("TotalCount", "unknown"),
        "statuses": [{"instance_id": item.get("InstanceId", "unknown"),
                      "status": item.get("Status", "unknown")}
                     for item in items if isinstance(item, dict)],
    }


def _summarise_available(body: Dict[str, Any]) -> Dict[str, Any]:
    zones = _dig(body, "AvailableZones", "AvailableZone")
    if not zones:
        return {"returned": 0,
                "note": "response carried no AvailableZones list; top-level keys: "
                        + ", ".join(sorted(body))}
    return {
        "returned": len(zones),
        "zones": [{"zone_id": zone.get("ZoneId", "unknown"),
                   "status": zone.get("Status", "unknown"),
                   "status_category": zone.get("StatusCategory", "unknown")}
                  for zone in zones if isinstance(zone, dict)],
    }


def _dig(mapping: Any, *keys: str) -> List[Any]:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return current if isinstance(current, list) else []


def gather_context(region_id: str, instance_ids: Optional[Sequence[str]] = None,
                   destination_resource: Optional[str] = None,
                   instance_type: Optional[str] = None, zone_id: Optional[str] = None,
                   include_identity: bool = True) -> Dict[str, Any]:
    """Assemble the read-only material pack. Never raises: failures become degraded records."""
    ids = [i for i in (instance_ids or []) if i][:MAX_INSTANCE_IDS]
    calls: List[Dict[str, Any]] = []

    if include_identity:
        identity = get_caller_identity()
        calls.append({"action": "sts get-caller-identity", "params_declared": {},
                      "status": "ok" if identity.get("status") == "ok" else "failed",
                      "code": identity.get("code", "unknown"),
                      "message": identity.get("message", ""),
                      "result": identity})

    instance_params: Dict[str, Any] = {"RegionId": region_id}
    if ids:
        instance_params["InstanceIds"] = ids
    instance_params.update(AUTO_FILLED_PAGINATION)
    calls.append(_query(ECS_PRODUCT, "DescribeInstances", instance_params, _summarise_instances))

    status_params: Dict[str, Any] = {"RegionId": region_id}
    for position, instance_id in enumerate(ids, start=1):
        status_params[f"InstanceId.{position}"] = instance_id
    status_params.update(AUTO_FILLED_PAGINATION)
    calls.append(_query(ECS_PRODUCT, "DescribeInstanceStatus", status_params, _summarise_status))

    if destination_resource:
        available_params: Dict[str, Any] = {"RegionId": region_id,
                                           "DestinationResource": destination_resource}
        if instance_type:
            available_params["InstanceType"] = instance_type
        if zone_id:
            available_params["ZoneId"] = zone_id
        calls.append(_query(ECS_PRODUCT, "DescribeAvailableResource", available_params,
                            _summarise_available))

    degraded = [call for call in calls if call["status"] != "ok"]
    return {
        "region_id": region_id,
        "instance_ids": ids,
        "calls": calls,
        "degraded_items": [f"{c['action']} ({c.get('code', 'unknown')})" for c in degraded],
        "status": "ok" if not degraded else "degraded",
    }


def build_channels(decision: Dict[str, Any]) -> Dict[str, Any]:
    """Core deliverable, independent of every cloud query above."""
    guidance = {
        INTENT_BUSINESS: [
            "Commercial terms (quotation, discount, contract, bulk purchase) are handled by a "
            "business contact, never by this skill: pass the material pack to the human owner.",
            CONSOLE_SERVICE_ENTRY,
        ],
        INTENT_HUMAN_PHONE: [
            "Human handling was requested: use the ticket entry and ask for a human agent, and "
            "restate the resource context already collected so nothing has to be asked twice.",
            CONSOLE_SERVICE_ENTRY,
        ],
        INTENT_COMMERCIAL_ACTION: [
            "Refund, unsubscribe, downgrade, invoice and account-entity changes are never "
            "performed here; they need manual acceptance by the billing or business owner, and "
            "this skill only supplies the read-only material pack.",
            CONSOLE_SERVICE_ENTRY,
        ],
        INTENT_UNCLASSIFIED: [
            f"Routing intent is ambiguous; ask once: {CLARIFYING_QUESTION}",
            CONSOLE_SERVICE_ENTRY,
        ],
    }[decision["intent"]]

    handoffs = [
        f"Symptom '{signal['topic']}' is owned by {signal['target_skill']}, not by this skill: "
        "transfer the technical part there and keep only the contact-routing part here."
        for signal in decision["handoff_signals"]
    ]

    return {
        "channel_directory_status": CHANNEL_DIRECTORY_STATUS,
        "guidance": guidance + handoffs,
        "supplementary_self_service": SUPPLEMENTARY_NOTIFICATION_CHANNEL,
        "not_covered": [
            "Cannot verify or record which business owner the account already has.",
            "Cannot place a call, book a call-back or promise any response window.",
            "Cannot judge policy eligibility, amounts or refund feasibility.",
            "No emotional de-escalation advantage over a human agent; stated as a known limit.",
        ],
    }


def _status_line(decision: Dict[str, Any], context: Optional[Dict[str, Any]]) -> str:
    if context and context["status"] != "ok":
        return "DEGRADED"
    if decision["confidence"] < CONFIDENCE_THRESHOLD:
        return "DEGRADED"
    return "OK"


def _next_action(decision: Dict[str, Any], context: Optional[Dict[str, Any]]) -> str:
    steps = ["Hand the guidance block to the human or business owner through the console "
             "ticket entry; a human confirms the official contact channel."]
    if decision["handoff_signals"]:
        steps.append("Transfer technical symptoms to "
                     + ", ".join(s["target_skill"] for s in decision["handoff_signals"]))
    if context and context["degraded_items"]:
        steps.append("Re-run the failed read-only queries after fixing credentials, region or "
                     "instance id: " + "; ".join(context["degraded_items"]))
    if decision["clarify_needed"]:
        steps.append("Ask the single clarifying question before any further look-up.")
    return " ".join(steps)


def render_report(decision: Dict[str, Any], context: Optional[Dict[str, Any]],
                  channels: Dict[str, Any]) -> str:
    lines: List[str] = [f"# ECS contact-routing report (session {session_id()})", ""]
    lines.append("## Routing intent")
    lines.append(f"- intent: {decision['intent']} ({decision['label']})")
    lines.append(f"- confidence: {decision['confidence']}")
    for intent, hits in decision["matched_terms"].items():
        if hits:
            lines.append(f"- matched {intent}: {', '.join(hits)}")
    for signal in decision["handoff_signals"]:
        lines.append(f"- hand-off signal: {signal['topic']} -> {signal['target_skill']}")

    lines.extend(["", "## Read-only material pack"])
    if context is None:
        lines.append("- not collected: no region supplied, so the guidance below stands alone")
    else:
        lines.append(f"- region: {context['region_id']} | instance ids: "
                     f"{', '.join(context['instance_ids']) or 'none supplied'}")
        for call in context["calls"]:
            declared = json.dumps(call["params_declared"], ensure_ascii=False)
            lines.append(f"- {call['action']} -> {call['status']} (declared params: {declared})")
            payload = call.get("summary") or call.get("result")
            if call["status"] == "ok":
                lines.append(f"  {json.dumps(payload, ensure_ascii=False)}")
            else:
                lines.append(f"  {call.get('code', 'unknown')}: {call.get('message', payload)}")
        if context["degraded_items"]:
            lines.append("- degraded items: " + "; ".join(context["degraded_items"]))

    lines.extend(["", "## Hand-off guidance"])
    lines.append(f"- channel directory: {channels['channel_directory_status']}")
    for item in channels["guidance"]:
        lines.append(f"- {item}")
    supplement = channels["supplementary_self_service"]
    lines.append(f"- supplementary self-service: {supplement['name']} "
                 f"(`{supplement['doc']}`; {supplement['evidence']})")

    lines.extend(["", "## What this skill cannot do"])
    lines.extend(f"- {limit}" for limit in channels["not_covered"])

    lines.extend(["", f"STATUS: {_status_line(decision, context)}",
                  f"NEXT_ACTION: {_next_action(decision, context)}"])
    return "\n".join(lines)


def preflight_notice(include_context: bool, check_availability: bool) -> None:
    if not include_context:
        print("[NOTICE] No cloud query will be run; guidance only.", file=sys.stderr)
        return
    planned = ["sts get-caller-identity", f"{ECS_PRODUCT} DescribeInstances",
               f"{ECS_PRODUCT} DescribeInstanceStatus"]
    if check_availability:
        planned.append(f"{ECS_PRODUCT} DescribeAvailableResource")
    print("[NOTICE] Read-only queries about to run, no resource is changed: "
          + "; ".join(planned)
          + ". Pagination is auto-filled where the action supports it.", file=sys.stderr)


def _add_text_argument(target: argparse.ArgumentParser) -> None:
    target.add_argument("--text", required=True,
                        help="Customer request wording, in Chinese or English.")


def _add_context_arguments(target: argparse.ArgumentParser, region_required: bool) -> None:
    target.add_argument("--region-id", dest="region_id", required=region_required,
                        help="Required by every allowlisted action; omit in `run` to skip "
                             "all cloud queries and return guidance only.")
    target.add_argument("--instance-id", dest="instance_ids", action="append", default=[],
                        help="Repeatable; narrows the material pack to these instances.")
    target.add_argument("--destination-resource", dest="destination_resource",
                        help="Availability branch only; pass the exact console value.")
    target.add_argument("--instance-type", dest="instance_type")
    target.add_argument("--zone-id", dest="zone_id")
    target.add_argument("--skip-identity", action="store_true",
                        help="Do not resolve the current account.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="routing.py",
        description="Read-only ECS business / human contact routing and material pack.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Classify, collect context, emit guidance.")
    _add_text_argument(run_parser)
    _add_context_arguments(run_parser, region_required=False)
    run_parser.add_argument("--json", action="store_true", help="Structured output.")

    classify_parser = sub.add_parser("classify", help="Classify the routing intent only.")
    _add_text_argument(classify_parser)

    context_parser = sub.add_parser("context", help="Collect the read-only material pack only.")
    _add_context_arguments(context_parser, region_required=True)

    channels_parser = sub.add_parser("channels", help="Emit guidance for a known intent.")
    channels_parser.add_argument("--intent", required=True, choices=sorted(INTENT_LABELS))
    channels_parser.add_argument("--json", action="store_true")

    sub.add_parser("doctor", help="Check that the CLI resolves each allowlisted action.")
    return parser


def _run_context(args: argparse.Namespace) -> int:
    preflight_notice(True, bool(args.destination_resource))
    context = gather_context(args.region_id, args.instance_ids, args.destination_resource,
                             args.instance_type, args.zone_id,
                             include_identity=not args.skip_identity)
    print(json.dumps(context, ensure_ascii=False, indent=2))
    print(f"STATUS: {'OK' if context['status'] == 'ok' else 'DEGRADED'}", file=sys.stderr)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "doctor":
        for product, action in READ_ONLY_ALLOWLIST:
            verified, output = run_help(product, action)
            print(f"{product} {action}: {'VERIFIED' if verified else 'NOT VERIFIED'}")
            if not verified:
                print(f"  {output.splitlines()[0] if output else 'no output'}")
        print(f"user-agent: {user_agent()}")
        return 0

    if args.command == "channels":
        decision = {"intent": args.intent, "confidence": 1.0, "clarify_needed": False,
                    "handoff_signals": []}
        channels = build_channels(decision)
        if args.json:
            print(json.dumps(channels, ensure_ascii=False, indent=2))
        else:
            print("\n".join(f"- {item}" for item in channels["guidance"]))
            print(f"- {channels['channel_directory_status']}")
        print("STATUS: OK")
        return 0

    if args.command == "context":
        return _run_context(args)

    if args.command == "classify":
        print(json.dumps(classify_text(args.text), ensure_ascii=False, indent=2))
        return 0

    decision = classify_text(args.text)
    context = None
    if args.region_id:
        preflight_notice(True, bool(args.destination_resource))
        context = gather_context(args.region_id, args.instance_ids, args.destination_resource,
                                 args.instance_type, args.zone_id,
                                 include_identity=not args.skip_identity)
    else:
        preflight_notice(False, False)

    channels = build_channels(decision)
    if args.json:
        print(json.dumps({"decision": decision, "context": context, "channels": channels,
                          "status": _status_line(decision, context),
                          "next_action": _next_action(decision, context)},
                         ensure_ascii=False, indent=2))
    else:
        print(render_report(decision, context, channels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
