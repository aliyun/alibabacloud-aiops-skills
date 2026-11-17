#!/usr/bin/env python3
"""
billing_mode_advisor.py -- SINGLE ENTRY POINT of the ECS billing-mode skill
===========================================================================
SECURITY / OPERATION MODEL (RO_GUIDE):
  * This script is strictly READ-ONLY. It only calls the allow-listed
    Describe*-class ECS APIs below, via the shared `_cli` layer, plus the
    STS identity query. It never invokes a mutating API and never runs
    anything inside a customer instance.
  * All remediation (billing-method conversion, top-up, snapshot,
    unsubscription, release) is performed BY THE CUSTOMER in the console;
    this script emits step-by-step manual guidance, risk notices, and
    read-only re-verification.
  * Credentials are resolved exclusively by the aliyun CLI default
    credential chain; this script never reads, prints or passes AK/SK.

Allowed OpenAPI actions (ABSOLUTE allow-list, anything else is rejected):
    ecs DescribeInstances          -- instance inventory + billing facts
    ecs DescribeInstanceStatus     -- run-state re-verification
    ecs DescribeAvailableResource  -- selection-time availability check
    sts GetCallerIdentity          -- identity trace label (optional)

Contract:
  Every run ends with machine-readable lines:
      STATUS: OK | DEGRADED | FAIL
      NEXT_ACTION: <what the agent must do / ask next>
  Exit codes: 0 = OK or DEGRADED (a usable advisory was produced),
  1 = FAIL (nothing usable; NEXT_ACTION names the missing input),
  2 = argparse usage error.

Usage examples:
  python3 scripts/areas/billing_mode_selection/billing_mode_advisor.py --region-id cn-hangzhou
  python3 scripts/areas/billing_mode_selection/billing_mode_advisor.py --region-id cn-hangzhou \
      --instance-ids i-bp1abcdef12345 --intent subscription_to_payg
  python3 scripts/areas/billing_mode_selection/billing_mode_advisor.py \
      --question "I released the server last week but I am still being charged"
  python3 scripts/areas/billing_mode_selection/billing_mode_advisor.py --list-topics
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import _cli
import _knowledge
from _constants import (
    ARREARS_LOCK_REASONS,
    CHARGE_TYPE_LABELS,
    INSTANCE_ID_PATTERN,
    INSTANCE_TYPE_PATTERN,
    MAX_RESULTS,
    PAGE_SIZE,
    REGION_ID_PATTERN,
    ZONE_ID_PATTERN,
)

VALID_INTENTS = (
    "auto",
    "payg_to_subscription",
    "subscription_to_payg",
    "residual_billing",
    "expiry_handling",
    "selection",
    "overview",
)


# ---------------------------------------------------------------------------
# Input validation (strict; unvalidated text never reaches a CLI argument)
# ---------------------------------------------------------------------------

def validate_region_id(value: str) -> str:
    """Return the region id when it matches the documented shape."""
    if not re.fullmatch(REGION_ID_PATTERN, value or ""):
        raise ValueError(f"invalid --region-id {value!r} (expected e.g. cn-hangzhou)")
    return value


def parse_instance_ids(value: str | None) -> list[str]:
    """Parse a comma-separated instance-id list; reject malformed entries."""
    if not value:
        return []
    ids = [t.strip() for t in value.split(",") if t.strip()]
    for one in ids:
        if not re.fullmatch(INSTANCE_ID_PATTERN, one):
            raise ValueError(f"invalid instance id {one!r} (expected i-<alnum>)")
    return ids


def classify_intent(question: str | None) -> tuple[str | None, list[str]]:
    """Pure intent classifier: scores embedded phrase patterns per intent."""
    if not question:
        return None, []
    low = question.lower()
    best_intent: str | None = None
    best_score = 0
    matched: list[str] = []
    for intent, phrases in _knowledge.INTENT_PATTERNS.items():
        hits = [p for p in phrases if p in low]
        if len(hits) > best_score:
            best_intent, best_score, matched = intent, len(hits), hits
    return best_intent, matched


def days_until(iso_ts: str | None, now: datetime) -> int | None:
    """Whole days from `now` until an ISO8601 timestamp; None when unusable."""
    if not iso_ts:
        return None
    try:
        text = iso_ts.replace("Z", "+00:00")
        ts = datetime.fromisoformat(text)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (ts.date() - now.astimezone(timezone.utc).date()).days
    except ValueError:
        return None


# inline boundary assertions for the pure functions (normal/boundary/invalid)
assert validate_region_id("cn-hangzhou") == "cn-hangzhou"
try:
    validate_region_id("CN_HANGZHOU; rm -rf")  # invalid: must be rejected
    raise AssertionError("region validation failed to reject bad input")
except ValueError:
    pass
assert parse_instance_ids("i-bp1abcdef12345,i-bp1abcdef12346") == [
    "i-bp1abcdef12345", "i-bp1abcdef12346"]
assert parse_instance_ids(None) == []
try:
    parse_instance_ids("i-x")  # invalid: too short
    raise AssertionError("instance-id validation failed to reject bad input")
except ValueError:
    pass
assert classify_intent("I released the server but I am STILL CHARGED")[0] == "residual_billing"
assert classify_intent("no billing words here at all")[0] is None
_UTC = datetime(2026, 9, 1, tzinfo=timezone.utc)
assert days_until("2026-09-03T15:59Z", _UTC) == 2
assert days_until(None, _UTC) is None
assert days_until("garbage", _UTC) is None


# ---------------------------------------------------------------------------
# Evidence collection (read-only, degradable)
# ---------------------------------------------------------------------------

def _flatten_ips(row: dict) -> str:
    """Human-readable IP summary from one DescribeInstances row."""
    parts: list[str] = []
    pub = row.get("PublicIpAddress")
    if isinstance(pub, dict) and isinstance(pub.get("IpAddress"), list):
        parts.extend(str(x) for x in pub["IpAddress"])
    eip = row.get("EipAddress")
    if isinstance(eip, dict) and eip.get("PublicIpAddress"):
        parts.append(str(eip["PublicIpAddress"]))
    inner = row.get("InnerIpAddress")
    if isinstance(inner, dict) and isinstance(inner.get("IpAddress"), list):
        parts.extend(f"{x} (classic-internal)" for x in inner["IpAddress"])
    return ", ".join(parts) if parts else "none"


def _lock_reasons(row: dict) -> list[str]:
    """Extract OperationLocks lock reasons defensively."""
    locks = row.get("OperationLocks")
    if isinstance(locks, dict):
        items = locks.get("LockReason") or []
    elif isinstance(locks, list):
        items = locks
    else:
        items = []
    reasons: list[str] = []
    for item in items:
        if isinstance(item, dict):
            reasons.append(str(item.get("LockReason", "")))
        elif item:
            reasons.append(str(item))
    return [r for r in reasons if r]


def collect_instances(region: str, instance_ids: list[str],
                      profile: str | None, errors: list[dict]) -> list[dict]:
    """DescribeInstances (allow-listed, read-only) with pagination."""
    params: dict = {}
    if instance_ids:
        params["InstanceIds"] = json.dumps(instance_ids)
    try:
        rows = _cli.paginate_next_token(
            "ecs", "DescribeInstances", params,
            items_path=["Instances"], wrapped_key="Instance",
            region=region, profile=profile, max_results=MAX_RESULTS,
        )
    except _cli.CliError as e:
        print(f"[WARN] DescribeInstances failed: {e}", file=sys.stderr)
        errors.append({"api": "DescribeInstances", "code": e.code or "Unknown",
                       "message": str(e)[:300]})
        return []
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append({
            "instance_id": str(row.get("InstanceId", "") or "N/A"),
            "name": str(row.get("InstanceName", "") or "N/A"),
            "status": str(row.get("Status", "") or "N/A"),
            "charge_type": str(row.get("InstanceChargeType", "") or "N/A"),
            "expired_time": str(row.get("ExpiredTime", "") or ""),
            "creation_time": str(row.get("CreationTime", "") or ""),
            "instance_type": str(row.get("InstanceType", "") or "N/A"),
            "public_ips": _flatten_ips(row),
            "lock_reasons": _lock_reasons(row),
        })
    return out


def collect_statuses(region: str, profile: str | None,
                     errors: list[dict]) -> dict[str, str]:
    """DescribeInstanceStatus (allow-listed, read-only, supplementary).

    A permission failure here (e.g. NoPermission) is non-fatal: the runtime
    status already arrives from DescribeInstances; this call only sharpens
    the re-verification path."""
    try:
        rows = _cli.paginate_page_number(
            "ecs", "DescribeInstanceStatus", {},
            items_path=["InstanceStatuses"], wrapped_key="InstanceStatus",
            region=region, profile=profile, page_size=PAGE_SIZE,
        )
    except _cli.CliError as e:
        print(f"[WARN] DescribeInstanceStatus failed (non-fatal, degrading): {e}",
              file=sys.stderr)
        errors.append({"api": "DescribeInstanceStatus", "code": e.code or "Unknown",
                       "message": str(e)[:300]})
        return {}
    mapping: dict[str, str] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("InstanceId"):
            mapping[str(row["InstanceId"])] = str(row.get("Status", "N/A"))
    return mapping


def check_availability(region: str, instance_type: str, zone_id: str | None,
                       charge_type: str, profile: str | None,
                       errors: list[dict]) -> list[dict]:
    """DescribeAvailableResource (allow-listed) for selection consulting."""
    params = {
        "DestinationResource": "InstanceType",
        "InstanceChargeType": charge_type,
        "InstanceType": instance_type,
        "ZoneId": zone_id,
    }
    try:
        body = _cli.call("ecs", "DescribeAvailableResource", params,
                         region=region, profile=profile)
    except _cli.CliError as e:
        print(f"[WARN] DescribeAvailableResource failed: {e}", file=sys.stderr)
        errors.append({"api": "DescribeAvailableResource", "code": e.code or "Unknown",
                       "message": str(e)[:300]})
        return []
    zones = body.get("AvailableZones")
    rows = zones.get("AvailableZone") if isinstance(zones, dict) else None
    out: list[dict] = []
    for z in rows or []:
        if not isinstance(z, dict):
            continue
        verdict = "unknown"
        available = z.get("AvailableResources")
        res_list = available.get("AvailableResource", []) if isinstance(available, dict) else []
        for res in res_list or []:
            supported = res.get("SupportedResources") if isinstance(res, dict) else None
            sup_list = supported.get("SupportedResource", []) if isinstance(supported, dict) else []
            for sup in sup_list or []:
                if isinstance(sup, dict) and str(sup.get("Value", "")) == instance_type:
                    verdict = f"{sup.get('Status', '?')}/{sup.get('StatusCategory', '?')}"
        out.append({"zone_id": str(z.get("ZoneId", "N/A")),
                    "status": str(z.get("Status", "N/A")),
                    "instance_type_verdict": verdict})
    return out


# ---------------------------------------------------------------------------
# Fact summaries (pure)
# ---------------------------------------------------------------------------

def summarize(instances: list[dict], now: datetime) -> dict:
    """Aggregate observable billing facts across the collected instances."""
    by_charge: dict[str, int] = {}
    arrears_locked: list[str] = []
    expiring: list[dict] = []
    expired: list[dict] = []
    for row in instances:
        by_charge[row["charge_type"]] = by_charge.get(row["charge_type"], 0) + 1
        if ARREARS_LOCK_REASONS & set(row["lock_reasons"]):
            arrears_locked.append(row["instance_id"])
        days = days_until(row["expired_time"], now)
        if row["charge_type"] == "PrePaid" and days is not None:
            entry = {"instance_id": row["instance_id"], "expired_time": row["expired_time"], "days": days}
            if days < 0:
                expired.append(entry)
            elif days <= 15:
                expiring.append(entry)
    return {
        "count": len(instances),
        "by_charge_type": by_charge,
        "arrears_locked_ids": arrears_locked,
        "expiring_within_15d": expiring,
        "expired_not_released": expired,
    }


# inline boundary assertions for summarize()
_fake_now = datetime(2026, 9, 1, tzinfo=timezone.utc)
_fake_rows = [
    {"instance_id": "i-a", "charge_type": "PrePaid", "expired_time": "2026-09-05T00:00Z",
     "lock_reasons": [], "status": "N/A", "name": "N/A", "creation_time": "", "instance_type": "N/A", "public_ips": "none"},
    {"instance_id": "i-b", "charge_type": "PostPaid", "expired_time": "",
     "lock_reasons": ["financial"], "status": "N/A", "name": "N/A", "creation_time": "", "instance_type": "N/A", "public_ips": "none"},
]
_fake_sum = summarize(_fake_rows, _fake_now)
assert _fake_sum["by_charge_type"] == {"PrePaid": 1, "PostPaid": 1}
assert _fake_sum["arrears_locked_ids"] == ["i-b"]
assert [e["instance_id"] for e in _fake_sum["expiring_within_15d"]] == ["i-a"]
assert summarize([], _fake_now)["count"] == 0


# ---------------------------------------------------------------------------
# Advisory assembly
# ---------------------------------------------------------------------------

def resolve_intent(args: argparse.Namespace) -> tuple[str, str]:
    """Return (intent, provenance). Explicit flag wins over question text."""
    if args.intent and args.intent != "auto":
        return args.intent, "explicit --intent flag"
    detected, matched = classify_intent(args.question)
    if detected:
        return detected, f"keyword match from --question ({len(matched)} phrase(s))"
    if args.intent == "overview":
        return "overview", "explicit --intent overview"
    return "overview", "no intent signal; emitting inventory + triage menu"


def build_sections(intent: str, instances: list[dict], summary: dict,
                   statuses: dict[str, str], availability: list[dict],
                   args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    """Assemble the advisory sections in fixed order. Pure formatting of
    embedded knowledge + real evidence; invents nothing."""
    sections: list[tuple[str, list[str]]] = []

    # --- inventory evidence -------------------------------------------------
    if instances:
        lines = [f"{len(instances)} instance(s) visible in this region to the current credential "
                 f"(visibility is per-account and PER-REGION; other regions need their own run):"]
        for row in instances:
            charge = CHARGE_TYPE_LABELS.get(row["charge_type"], row["charge_type"])
            lines.append(
                f"  - {row['instance_id']}  name={row['name']}  status={row['status']}"
                + (f"  status(api)={statuses[row['instance_id']]}" if row["instance_id"] in statuses else "")
                + f"  billing={charge}"
                + (f"  expires={row['expired_time']}" if row["expired_time"] else "")
                + f"  ips={row['public_ips']}"
                + (f"  LOCKS={','.join(row['lock_reasons'])}" if row["lock_reasons"] else "")
            )
        bt = ", ".join(f"{k}={v}" for k, v in sorted(summary["by_charge_type"].items()))
        lines.append(f"Billing-type census: {bt}")
        if summary["arrears_locked_ids"]:
            lines.append("Financial-locked instances (arrears suspected): "
                         + ", ".join(summary["arrears_locked_ids"])
                         + " -- conversion entries may be hidden until the customer tops up (Billing Center, customer action).")
        for e in summary["expiring_within_15d"]:
            lines.append(f"{e['instance_id']} expires in {e['days']} day(s) at {e['expired_time']}"
                         " -- see the expiry-handling rules.")
        for e in summary["expired_not_released"]:
            lines.append(f"{e['instance_id']} expiry timestamp {e['expired_time']} is in the past"
                         " -- manual release is available from 00:00 the next day; auto-delete ~15 days after expiry.")
        sections.append(("Instance evidence (read-only queries)", lines))
    elif args.region_id:
        sections.append(("Instance evidence (read-only queries)", [
            "No instance data available in this run (query failed or the region holds no instances for "
            "this credential). Degrade to guidance-only: ask the customer which instance id / name the "
            "console shows and continue with the knowledge sections below.",
        ]))

    # --- pre-checks ----------------------------------------------------------
    if intent in ("payg_to_subscription", "subscription_to_payg"):
        pre = list(_knowledge.PRECHECKS_COMMON)
        pre += (_knowledge.PRECHECKS_PAYG_TO_SUB if intent == "payg_to_subscription"
                else _knowledge.PRECHECKS_SUB_TO_PAYG)
        sections.append(("Pre-checks the customer must clear BEFORE console steps", pre))

    if intent == "subscription_to_payg":
        sections.append(("Risk acknowledgement (mandatory gate)",
                         list(_knowledge.RISK_ACK_SUB_TO_PAYG)))

    # --- direction-specific guidance ----------------------------------------
    if intent in _knowledge.CONVERSION_GUIDES:
        guide = _knowledge.CONVERSION_GUIDES[intent]
        lines = list(guide["steps"])  # type: ignore[index]
        lines.append("")
        lines.append("Re-verification: " + str(guide["reverify"]))  # type: ignore[str-util]
        # Cross-check the requested direction against observed charge types.
        prepaid = [r["instance_id"] for r in instances if r["charge_type"] == "PrePaid"]
        postpaid = [r["instance_id"] for r in instances if r["charge_type"] == "PostPaid"]
        if intent == "payg_to_subscription" and prepaid:
            lines.append(f"Direction cross-check: {', '.join(prepaid)} already subscription; "
                         "the pay-as-you-go conversion targets are: "
                         + (", ".join(postpaid) if postpaid else "(none found in this region)"))
        if intent == "subscription_to_payg" and postpaid:
            lines.append(f"Direction cross-check: {', '.join(postpaid)} already pay-as-you-go; "
                         "the subscription conversion targets are: "
                         + (", ".join(prepaid) if prepaid else "(none found in this region)"))
        sections.append((str(guide["heading"]), lines))  # type: ignore[arg-type]

    # --- residual billing ----------------------------------------------------
    if intent == "residual_billing":
        lines = []
        for item in _knowledge.RESIDUAL_CHECKLIST:
            lines.append(f"* {item['item']} -- {item['why']}")
            lines.append(f"    Customer self-check path: {item['where']} {item['source']}")
        lines.append("")
        lines.append("This skill cannot read bill line items through the ECS read-only surface; ask the customer "
                     "for the Billing Center bill-detail screenshot and interpret the pasted data instead of guessing.")
        sections.append(("Residual-billing checklist (after conversion / release)", lines))

    # --- lifecycle / expiry --------------------------------------------------
    if intent == "expiry_handling":
        sections.append(("Expiry / unsubscription / release rules",
                         list(_knowledge.LIFECYCLE_RULES)))

    # --- selection -----------------------------------------------------------
    if intent == "selection":
        model = _knowledge.SELECTION_MODEL
        lines = [str(x) for x in model["comparison"]]  # type: ignore[union-attr]
        lines.append("")
        lines.append(str(model["decision_rule"]))  # type: ignore[call-overload]
        lines.append(str(model["price_policy"]))  # type: ignore[call-overload]
        sections.append(("Billing-model selection consulting", lines))
        if availability:
            av = [f"  zone={z['zone_id']} zone-status={z['status']} {args.instance_type}: {z['instance_type_verdict']}"
                  for z in availability]
            av.insert(0, f"DescribeAvailableResource for {args.instance_type} (charge={args.target_charge_type}) in {args.region_id}:")
            sections.append(("Target-resource availability (read-only check)", av))

    # --- availability standalone (also shown when intent differs) ------------
    if availability and intent != "selection":
        av = [f"  zone={z['zone_id']} zone-status={z['status']} {args.instance_type}: {z['instance_type_verdict']}"
              for z in availability]
        av.insert(0, f"DescribeAvailableResource for {args.instance_type} (charge={args.target_charge_type}) in {args.region_id}:")
        sections.append(("Target-resource availability (read-only check)", av))

    # --- data the cloud cannot show ------------------------------------------
    if intent in ("payg_to_subscription", "subscription_to_payg", "residual_billing",
                  "selection", "expiry_handling"):
        sections.append(("Not visible through read-only APIs -- customer self-check required",
                         list(_knowledge.SELF_CHECK_ITEMS)))

    # --- triage menu for overview runs ---------------------------------------
    if intent == "overview":
        menu = [
            "Detected billing-type census above; choose the matching guidance and re-run with --intent:",
            "  --intent payg_to_subscription   conversion steps + arrears/promo pre-checks",
            "  --intent subscription_to_payg   refund rules + auto-release risk gate",
            "  --intent residual_billing       which items keep charging after conversion/release",
            "  --intent expiry_handling        expiry timeline, early refund, manual release",
            "  --intent selection              model comparison + decision rule + availability check",
        ]
        sections.append(("Triage menu", menu))

    # --- handoffs (always) ----------------------------------------------------
    ho = []
    for key, item in _knowledge.HANDOFFS.items():
        ref = ""
        if item["ref"]:
            doc = _knowledge.DOC_LINKS.get(item["ref"])
            if doc:
                ref = f" Reference: {doc['title']} {doc['url']}"
        ho.append(f"* {item['symptom']} -> {item['script']}{ref}")
    sections.append(("Neighbor-symptom handoff (identify, do not diagnose here)", ho))

    return sections


def next_action_for(intent: str, summary: dict, have_evidence: bool) -> str:
    """Deterministic NEXT_ACTION line."""
    if not have_evidence:
        return ("Guidance-only mode: present the knowledge sections to the customer, ask for the "
                "instance id + region shown in their console (and a Billing Center screenshot for "
                "any money question), then re-run with --region-id to attach evidence.")
    if intent == "subscription_to_payg":
        return ("Read the risk acknowledgement to the customer and obtain an explicit acknowledgement "
                "BEFORE presenting the console steps; after the customer converts, re-run this script "
                "to verify InstanceChargeType and then walk the residual-billing checklist.")
    if intent == "payg_to_subscription":
        if summary["arrears_locked_ids"]:
            return ("Guide the customer to clear the overdue balance in the Billing Center first "
                    "(console entry is hidden while locked); after top-up re-run this script, then "
                    "present the conversion steps.")
        return ("Present the step-by-step console guidance; the customer performs every step and the "
                "price shown on the order page is the only price authority; re-run this script to "
                "verify the new InstanceChargeType / ExpiredTime.")
    if intent == "residual_billing":
        return ("Have the customer work through the checklist against their Billing Center detail "
                "(ask for a screenshot if a row is unclear); items outside ECS scope hand off to "
                "their own product consoles.")
    if intent == "expiry_handling":
        return ("Apply the expiry timeline to the concrete ExpiredTime above (never to a guessed "
                "date); unsubscription amounts are read from the refund page by the customer.")
    if intent == "selection":
        return ("Deliver the comparison + decision rule without any price promise; for historical "
                "traffic ask the customer to export usage from CloudMonitor / Billing Center; "
                "campaign pricing hands off to a sales manager.")
    return ("Pick the matching --intent from the triage menu once the customer's direction is clear.")


# ---------------------------------------------------------------------------
# Inline boundary assertions for the advisory assembly (pure functions only)
# ---------------------------------------------------------------------------

# _lock_reasons: every OperationLocks shape the API has shipped must reduce to
# a flat, non-empty list of reason strings (dict-wrapped, bare list, string
# entries, missing/None must not raise nor leak blanks).
assert _lock_reasons({"OperationLocks": {"LockReason": [
    {"LockReason": "financial"}, {"LockReason": "security"}]}}) == ["financial", "security"]
assert _lock_reasons({"OperationLocks": [{"LockReason": "debt"}]}) == ["debt"]
assert _lock_reasons({"OperationLocks": ["a", ""]}) == ["a"]   # blanks dropped
# a dict item carrying an empty LockReason must also be dropped (this is the
# case the trailing filter exists for -- the dict branch appends unconditionally)
assert _lock_reasons({"OperationLocks": [{"LockReason": ""},
                                         {"LockReason": "debt"}]}) == ["debt"]
assert _lock_reasons({}) == [] and _lock_reasons({"OperationLocks": None}) == []

# resolve_intent: precedence explicit flag > keyword match > overview.
_ri = argparse.Namespace(intent="selection", question="I released the server but STILL CHARGED")
assert resolve_intent(_ri) == ("selection", "explicit --intent flag")
_kw = argparse.Namespace(intent="auto", question="I released the server but STILL CHARGED")
assert resolve_intent(_kw)[0] == "residual_billing" and "keyword match" in resolve_intent(_kw)[1]
_none = argparse.Namespace(intent="auto", question="what billing options exist")
assert resolve_intent(_none)[0] == "overview"

# next_action_for: each intent maps to its own guidance; no-evidence and the
# arrears-locked variant must take priority over the generic payg->sub path.
_sum = {"count": 1, "by_charge_type": {}, "arrears_locked_ids": ["i-b"],
        "expiring_within_15d": [], "expired_not_released": []}
_sum_clear = dict(_sum, arrears_locked_ids=[])
assert "Guidance-only mode" in next_action_for("overview", _sum, False)
assert "risk acknowledgement" in next_action_for("subscription_to_payg", _sum, True)
assert "overdue balance" in next_action_for("payg_to_subscription", _sum, True)
assert "step-by-step" in next_action_for("payg_to_subscription", _sum_clear, True)
assert "Billing Center detail" in next_action_for("residual_billing", _sum, True)
assert "matching --intent" in next_action_for("unexpected", _sum, True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="billing_mode_advisor.py",
        description=(
            "READ-ONLY ECS billing-mode advisory: instance evidence via Describe* APIs + "
            "customer-performed console guidance for billing-mode selection and conversion."
        ),
    )
    parser.add_argument("--region-id", default=None,
                        help="Required for any evidence query (ECS APIs are regional)")
    parser.add_argument("--instance-ids", default=None,
                        help="Optional comma-separated i-... ids to focus the advisory")
    parser.add_argument("--intent", choices=VALID_INTENTS, default="auto",
                        help="Explicit intent, or auto-classify from --question")
    parser.add_argument("--question", default=None,
                        help="Customer original wording (drives intent classification)")
    parser.add_argument("--check-availability", action="store_true",
                        help="Selection-time DescribeAvailableResource check (needs --region-id and --instance-type)")
    parser.add_argument("--instance-type", default=None,
                        help="Target instance type for --check-availability, e.g. ecs.g6.large")
    parser.add_argument("--zone-id", default=None,
                        help="Optional zone restriction for --check-availability")
    parser.add_argument("--target-charge-type", choices=("PrePaid", "PostPaid"), default="PrePaid",
                        help="Charge type to test availability for (default PrePaid)")
    parser.add_argument("--list-topics", action="store_true",
                        help="List embedded FAQ topics (no API call)")
    parser.add_argument("--topic", default=None,
                        help="Print one embedded FAQ topic (no API call)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    # ---- FAQ-only paths (pure knowledge, zero API) --------------------------
    if args.list_topics:
        payload = {k: {"q": v["q"], "source": v["source"]} for k, v in _knowledge.FAQ_TOPICS.items()}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else
              "\n".join(f"{k}: {v['q']}" for k, v in payload.items()))
        print("STATUS: OK")
        print("NEXT_ACTION: Answer the matching question with --topic <key>, relayed verbatim.")
        return

    if args.topic:
        topic = _knowledge.FAQ_TOPICS.get(args.topic)
        if not topic:
            print(f"[ERROR] unknown --topic {args.topic!r}; run --list-topics for the catalogue.",
                  file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: Re-run with one of the listed topic keys.")
            sys.exit(1)
        if args.json:
            print(json.dumps({"topic": args.topic, **topic, "status": "OK",
                              "next_action": "Relay the answer verbatim; route numbers to customer self-check."},
                             ensure_ascii=False, indent=2))
        else:
            print(f"Q: {topic['q']}\nA: {topic['a']}\nSource: {topic['source']}")
            print("STATUS: OK")
            print("NEXT_ACTION: Relay the answer verbatim; route numbers to customer self-check.")
        return

    # ---- validate inputs -----------------------------------------------------
    try:
        if args.region_id:
            args.region_id = validate_region_id(args.region_id)
        ids = parse_instance_ids(args.instance_ids)
        if args.check_availability:
            if not (args.region_id and args.instance_type):
                raise ValueError("--check-availability needs --region-id and --instance-type")
            if not re.fullmatch(INSTANCE_TYPE_PATTERN, args.instance_type):
                raise ValueError(f"invalid --instance-type {args.instance_type!r}")
            if args.zone_id and not re.fullmatch(ZONE_ID_PATTERN, args.zone_id):
                raise ValueError(f"invalid --zone-id {args.zone_id!r}")
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: Fix the named parameter (region id like cn-hangzhou; instance ids like "
              "i-bp1abc1234; type like ecs.g6.large) and re-run. Never guess identifiers.")
        sys.exit(1)

    errors: list[dict] = []
    uid = ""
    instances: list[dict] = []
    statuses: dict[str, str] = {}
    availability: list[dict] = []
    now = datetime.now(timezone.utc)

    if args.region_id:
        # Identity is best-effort: it only labels the report (traceability).
        try:
            _cli.check_cli_available()
            uid = _cli.resolve_account_id(profile=args.profile)
            if not uid:
                errors.append({"api": "GetCallerIdentity", "code": "NoIdentity",
                               "message": "identity unavailable; advisory continues per guidance-only"})
        except _cli.CliError as e:
            print(f"[WARN] identity check failed (degrading to guidance-only): {e}", file=sys.stderr)
            errors.append({"api": "GetCallerIdentity", "code": e.code or "CredentialChain",
                           "message": str(e)[:300]})
        instances = collect_instances(args.region_id, ids, args.profile, errors)
        if instances:
            statuses = collect_statuses(args.region_id, args.profile, errors)
        if args.check_availability:
            availability = check_availability(
                args.region_id, args.instance_type, args.zone_id,
                args.target_charge_type, args.profile, errors)
    else:
        print("[WARN] no --region-id supplied: running guidance-only (no cloud evidence attached)",
              file=sys.stderr)

    intent, intent_src = resolve_intent(args)
    summary = summarize(instances, now)
    sections = build_sections(intent, instances, summary, statuses, availability, args)

    have_evidence = bool(instances)
    if have_evidence and not errors:
        status = "OK"
    elif sections:
        status = "DEGRADED"
    else:
        status = "FAIL"

    summary_block = [
        "Advisory produced from the read-only evidence and embedded guidance above.",
        f"Intent: {intent} ({intent_src}).",
        f"Evidence: {summary['count']} instance(s) in {args.region_id or '(no region queried)'}"
        + (f"; UID auto-derived via sts get-caller-identity: {uid}" if uid else "; UID not derived"),
        "Remediation is customer-performed in the console; this skill applied no change.",
    ]

    if args.json:
        print(json.dumps({
            "skill": "area:billing-mode-selection",
            "session_id": _cli.session_id(),
            "uid": uid or None,
            "region": args.region_id,
            "intent": intent,
            "intent_source": intent_src,
            "instance_summary": summary,
            "sections": [{"heading": h, "lines": b} for h, b in sections],
            "errors": errors,
            "summary": summary_block,
            "status": status.lower(),
            "next_action": next_action_for(intent, summary, have_evidence),
        }, ensure_ascii=False, indent=2))
    else:
        print("=" * 74)
        print(" ECS BILLING-MODE ADVISORY  (read-only evidence + manual guidance only)")
        print("=" * 74)
        print(f" Region queried : {args.region_id or '(none -- guidance-only)'}")
        print(f" Caller UID     : {uid or 'N/A (auto-derive failed; trace label only)'}")
        if instances:
            print(f" Instances      : {summary['count']}")
        for heading, body in sections:
            print(f"\n## {heading}")
            for line in body:
                print(line)
        print("\nSummary:")
        for line in summary_block:
            print(f"  {line}")
        if errors:
            print("\n## Graceful Degradation Log")
            for err in errors:
                print(f"  [DEGRADED] {err['api']}: {err['code']} -- {err['message']}")
        print(f"\nSTATUS: {status}")
        print(f"NEXT_ACTION: {next_action_for(intent, summary, have_evidence)}")

    sys.exit(0 if status in ("OK", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
