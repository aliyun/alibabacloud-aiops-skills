#!/usr/bin/env python3
"""
ecs_service_escalation.py -- single entry point of the ECS Service
Escalation Guide (ticket follow-up / service complaint, READ-ONLY guide tier)
============================================================================
SECURITY: This skill is strictly READ-ONLY. The only cloud calls this script
can make are the two whitelisted ECS reads (`DescribeInstances`,
`DescribeInstanceStatus`) plus the STS identity pre-check, all routed through
`_cli.py`. It NEVER calls any ticket-system action: the support ticket state
is invisible to this skill, so every timeline fact it prints is labeled
customer-stated. No credential is ever read, printed or passed here; the
aliyun CLI default credential chain handles authentication.

Deterministic design (anti-hallucination layer L1): classification, promise
checking and package completeness are pure functions computed HERE, not by
the model. The agent maps customer wording onto these flags and relays the
result. The script ends with `STATUS: OK|DEGRADED|FAIL` + `NEXT_ACTION:`.

Exit codes (contract):
  0  a usable conclusion was produced (STATUS OK or DEGRADED)
  1  no usable conclusion (STATUS FAIL; NEXT_ACTION names what is missing)
  2  argparse usage error only (unknown option / bad value)

Modes (mutually exclusive):
  --screen  --text "<customer original wording>"
  --build-package --intent escalate|complaint [material flags]
  --collect-evidence --region-id <r> [--instance-ids i-a i-b ...]
Common: --json, --profile <name>
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
import time

import _cli
from _constants import (
    ADJACENT_ROUTES,
    COMPLAINT_TERMS,
    ESCALATION_TERMS,
    EVIDENCE_NOTE,
    GUIDANCE_STEPS,
    INSTANCE_ID_PATTERN,
    LIMITATIONS_BLOCK,
    MAX_IDS_PER_STATUS_CALL,
    PACKAGE_FIELDS,
    PROMISE_PATTERNS,
    TECHNICAL_ROUTES,
)

# Hard input caps (defensive; the APIs themselves bound what they accept).
MAX_IDS_IN_QUERY = 100


# ---------------------------------------------------------------------------
# Pure functions (import-time boundary assertions below)
# ---------------------------------------------------------------------------

def screen_request(text: str) -> dict:
    """Classify the customer wording into demand areas and handoff routes.

    Returns a dict with: areas (ordered), matched terms per area, handoff
    targets, a technical_open flag and a recommendation string. Detection
    only -- this skill never diagnoses technical areas nor handles commercial
    ones; it routes them (SKILL.md Absolute Rule 9).
    """
    norm = (text or "").lower()
    areas: list[str] = []
    matched: dict[str, list[str]] = {}
    handoffs: list[dict] = []

    hits = [term for term in ESCALATION_TERMS if term in norm]
    if hits:
        areas.append("escalation")
        matched["escalation"] = hits
    hits = [term for term in COMPLAINT_TERMS if term in norm]
    if hits:
        areas.append("complaint")
        matched["complaint"] = hits
    technical_found = False
    for area, terms, target, note in TECHNICAL_ROUTES:
        hits = [term for term in terms if term in norm]
        if hits:
            technical_found = True
            areas.append(area)
            matched[area] = hits
            handoffs.append({"area": area, "target": target, "note": note,
                             "kind": "technical"})
    for area, terms, target, note in ADJACENT_ROUTES:
        hits = [term for term in terms if term in norm]
        if hits:
            areas.append(area)
            matched[area] = hits
            handoffs.append({"area": area, "target": target, "note": note,
                             "kind": "adjacent"})

    if not areas:
        areas.append("unclear")
        recommendation = (
            "No ECS service-process signal found. Ask one brief clarifying "
            "question: is this about the progress of an existing ECS "
            "support ticket, a complaint about the support service, or a "
            "technical fault? Do not build a package on assumptions."
        )
    elif technical_found:
        if "escalation" in areas or "complaint" in areas:
            recommendation = (
                "An open technical area was detected next to a "
                "service-process demand. Handle the technical handoff(s) "
                "FIRST via the listed targets; a follow-up or complaint "
                "never substitutes for fault resolution. You may still "
                "build the service-process package afterwards so the "
                "materials stay attached to the ticket."
            )
        else:
            recommendation = (
                "Only technical areas were detected: this is a fault "
                "question, not a service-process demand. Hand off to the "
                "listed target(s); do NOT build a follow-up or complaint "
                "package."
            )
    elif "escalation" in areas and "complaint" in areas:
        recommendation = (
            "Both service areas present: build one complaint package "
            "(--intent complaint) that references the same timeline, and "
            "keep the follow-up wording on the original ticket."
        )
    elif "escalation" in areas:
        recommendation = (
            "Follow-up (escalation) area. Run --build-package --intent "
            "escalate with every material the customer already provided."
        )
    elif "complaint" in areas:
        recommendation = (
            "Complaint area. Run --build-package --intent complaint with "
            "the complaint subject, timeline and deliverable expectation."
        )
    else:
        recommendation = (
            "Adjacent process only: do NOT build a follow-up/complaint "
            "package; hand off per the listed targets, retaining the facts "
            "the customer already gave."
        )

    return {
        "areas": areas,
        "matched": matched,
        "handoffs": handoffs,
        "technical_open": technical_found,
        "recommendation": recommendation,
        "customer_ask": customer_ask(areas, technical_found),
    }


def customer_ask(areas, technical_open):
    """The one line the CUSTOMER reads; `recommendation` instructs the agent.

    Measured on the release package: this area's whole customer answer was the
    screening scaffold (`areas : unclear`, `technical_open : False`) plus an
    agent instruction, 461 characters with no step the customer could take.
    """
    if technical_open:
        return ("Have the customer paste the exact error text or screenshot and the "
                "instance id: the technical fault is diagnosed first, and a follow-up "
                "or complaint never replaces fixing it.")
    if "escalation" in areas and "complaint" in areas:
        return ("Have the customer give the original ticket number, the timeline of "
                "every reply so far, and what outcome they expect, so one complaint "
                "record can reference the same timeline as the follow-up.")
    if "escalation" in areas:
        return ("Have the customer give the ticket number and when it was submitted, "
                "then read its progress in Console > Tickets > My tickets: the "
                "engineer replies there asynchronously, not in real time.")
    if "complaint" in areas:
        return ("Have the customer state the complaint subject, the timeline with "
                "ticket or call references, and the outcome they expect, then submit "
                "it in Console > Tickets > My tickets so it stays on the record.")
    return ("Have the customer say which of these this is - the progress of an "
            "existing ECS support ticket, a complaint about the support service, or a "
            "technical fault - and paste the ticket number or the exact error text.")


def check_expectation(expectation: str) -> list[str]:
    """Flag promise-shaped / undeliverable wording in an expected outcome.

    Returns a list of rewording notes (empty when the demand is already
    deliverable-shaped). The skill must never carry an undeliverable
    commitment into a package (SKILL.md Absolute Rule 3).
    """
    notes: list[str] = []
    low = (expectation or "").lower()
    for pattern, advice in PROMISE_PATTERNS:
        if re.search(pattern, low):
            notes.append(advice)
    return notes


def validate_instance_ids(ids: list[str]) -> tuple[list[str], list[str]]:
    """Split instance ids into (valid, invalid) by shape.

    Invalid ids are never sent to the API; they are reported back so the
    customer can confirm them (they may belong to another region or be
    misspelled).
    """
    shape = re.compile(INSTANCE_ID_PATTERN)
    valid = [i for i in ids if shape.match(i)]
    invalid = [i for i in ids if not shape.match(i)]
    return valid, invalid


def build_package(intent: str, values: dict[str, str]) -> dict:
    """Assemble the structured material package for one intent.

    Every present value is echoed verbatim and labeled customer-stated;
    missing CORE fields are listed (the half package is still emitted --
    decision-tree step 4: never replace output by interrogation).
    """
    spec = PACKAGE_FIELDS[intent]
    fields: dict[str, str] = {}
    missing_core: list[str] = []
    missing_optional: list[str] = []
    for name, _flag, core, _hint in spec:
        value = (values.get(name) or "").strip()
        if value:
            fields[name] = value
        elif core:
            missing_core.append(name)
        else:
            missing_optional.append(name)

    expectation_flags = check_expectation(fields.get("expected_outcome", ""))
    status = "OK" if not missing_core else "DEGRADED"
    if missing_core:
        next_action = (
            "Ask the customer once for: "
            + ", ".join(missing_core)
            + " -- meanwhile the half package above stays usable."
        )
    elif expectation_flags:
        next_action = (
            "Reword the expected outcome per expectation_flags, then hand "
            "the package to the customer for their own submission through "
            "the official support entry."
        )
    else:
        next_action = (
            "Hand the package to the customer for their own submission on "
            "the original ticket thread; state the limitations block "
            "verbatim; do not promise any result."
        )

    return {
        "intent": intent,
        "fields": fields,
        "missing_core": missing_core,
        "missing_optional": missing_optional,
        "expectation_flags": expectation_flags,
        "guidance": list(GUIDANCE_STEPS),
        "limitations": list(LIMITATIONS_BLOCK),
        "status": status,
        "next_action": next_action,
    }


# ---------------------------------------------------------------------------
# Read-only evidence collection (optional corroboration step)
# ---------------------------------------------------------------------------

def _dig(container, key: str):
    """Safely read one wrapped member of an API response (never raises)."""
    if isinstance(container, dict):
        return container.get(key)
    return None


def _first(d: dict, *keys: str) -> str:
    for key in keys:
        value = d.get(key)
        if value not in (None, "", []):
            return str(value)
    return "n/a"


def collect_evidence(region_id: str, instance_ids: list[str],
                     profile: str | None) -> dict:
    """Run the two whitelisted read-only ECS queries and build the fact
    sheet. Failures degrade (never abort): the material package flow must
    continue without the attachment (SKILL.md Absolute Rule 8)."""
    errors: list[dict] = []
    valid_ids, invalid_ids = validate_instance_ids(instance_ids)
    query_ids = valid_ids[:MAX_IDS_IN_QUERY]
    if len(valid_ids) > MAX_IDS_IN_QUERY:
        errors.append({
            "call": "input", "code": "IdListTruncated",
            "message": f"{len(valid_ids)} ids supplied; the first "
                       f"{MAX_IDS_IN_QUERY} were queried",
        })

    account_uid = _cli.resolve_account_id(profile=profile)
    if account_uid:
        print(f"[_cli] caller account UID (label only): {account_uid}",
              file=sys.stderr)

    instances: list[dict] = []
    instances_ok = False
    params: dict = {"RegionId": region_id}
    if query_ids:
        params["InstanceIds"] = json.dumps(query_ids)
    try:
        raw = _cli.paginate_page_number(
            "ecs", "DescribeInstances", params,
            ["Instances", "Instance"], profile=profile)
        instances = [x for x in raw if isinstance(x, dict)]
        instances_ok = True
    except _cli.CliError as e:
        errors.append({"call": "DescribeInstances", "code": e.code,
                       "message": _cli._clean_stderr(str(e))})
        print(f"[WARN] DescribeInstances failed: {e.code}: "
              f"{_cli._clean_stderr(str(e))}", file=sys.stderr)

    found_ids = [str(x.get("InstanceId") or "") for x in instances]
    status_ids = (query_ids or found_ids)[:MAX_IDS_PER_STATUS_CALL]
    lifecycle: dict[str, str] = {}
    if instances and status_ids:
        status_params: dict = {"RegionId": region_id}
        for index, instance_id in enumerate(status_ids, 1):
            status_params[f"InstanceId.{index}"] = instance_id
        try:
            raw = _cli.paginate_page_number(
                "ecs", "DescribeInstanceStatus", status_params,
                ["InstanceStatuses", "InstanceStatus"], profile=profile)
            for item in raw:
                if isinstance(item, dict) and item.get("InstanceId"):
                    lifecycle[str(item["InstanceId"])] = str(
                        item.get("Status") or "unknown")
        except _cli.CliError as e:
            errors.append({"call": "DescribeInstanceStatus", "code": e.code,
                           "message": _cli._clean_stderr(str(e))})
            print(f"[WARN] DescribeInstanceStatus failed: {e.code}: "
                  f"{_cli._clean_stderr(str(e))}", file=sys.stderr)

    rows = []
    for inst in instances:
        sg_raw = _dig(inst.get("SecurityGroupIds"), "SecurityGroupId")
        vpc_raw = _dig(inst.get("VpcAttributes"), "VpcId")
        iid = str(inst.get("InstanceId") or "n/a")
        rows.append({
            "instance_id": iid,
            "instance_name": _first(inst, "InstanceName"),
            "zone_id": _first(inst, "ZoneId"),
            "instance_type": _first(inst, "InstanceType"),
            "os": _first(inst, "OSName", "OSNameEn"),
            "charge_type": _first(inst, "InstanceChargeType"),
            "console_status": _first(inst, "Status"),
            "api_lifecycle_status": lifecycle.get(iid, "n/a"),
            "vpc_id": str(vpc_raw) if vpc_raw else "n/a",
            "security_groups": (
                ",".join(str(s) for s in sg_raw)
                if isinstance(sg_raw, list)
                else str(sg_raw or "n/a")),
        })

    # "requested but not returned here" is only a sound conclusion when the
    # inventory query itself succeeded and was not truncated.
    if instances_ok and query_ids and len(query_ids) == len(valid_ids):
        not_found = [i for i in query_ids if i not in found_ids]
    else:
        not_found = []

    if instances_ok and not rows and not errors:
        note = (
            f"No ECS instances were returned for region '{region_id}' under "
            f"the current credential. This is a valid finding, not an error: "
            f"confirm the region id and the account before concluding "
            f"anything about the resources."
        )
    else:
        note = EVIDENCE_NOTE

    status = "OK" if not errors else "DEGRADED"
    if errors and not rows:
        next_action = (
            "Evidence unavailable: record 'no attached resource facts' in "
            "the package and continue the service-process guidance. Check "
            "the reported code (parameter, NoPermission / ImplicitDeny, "
            "transient) against references/ram-policies.md."
        )
    elif errors:
        next_action = (
            "Attach the partial fact sheet; list the failed query among the "
            "gaps. Do not retry beyond what this run already did."
        )
    else:
        next_action = (
            "Attach the resource fact sheet to the material package, "
            "labeled as a point-in-time read, and proceed to delivery."
        )

    return {
        "region_id": region_id,
        "account_uid_label": account_uid or "unavailable",
        "queried_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "instances": rows,
        "requested_ids": query_ids,
        "invalid_ids": invalid_ids,
        "not_found_in_region": not_found,
        "errors": errors,
        "note": note,
        "limitations": list(LIMITATIONS_BLOCK),
        "status": status,
        "next_action": next_action,
    }


# ---------------------------------------------------------------------------
# Rendering (human-readable; --json emits the same data as a dict)
# ---------------------------------------------------------------------------

def render_screen(result: dict) -> None:
    print("=" * 68)
    print("Demand-area screening (classification only, no diagnosis)")
    print("=" * 68)
    print(f"areas            : {', '.join(result['areas'])}")
    for area, terms in result["matched"].items():
        print(f"  matched[{area}]: {', '.join(sorted(set(terms)))}")
    for handoff in result["handoffs"]:
        print(f"  handoff         : {handoff['area']} -> {handoff['target']} "
              f"({handoff['note']})")
    print(f"technical_open  : {result['technical_open']}")
    print("recommendation  : " + result["recommendation"])
    print(result.get("customer_ask") or customer_ask(result["areas"],
                                                      result["technical_open"]))


def render_package(result: dict) -> None:
    print("=" * 68)
    print(f"Service-process material package ({result['intent']})")
    print("=" * 68)
    print("All timeline/progress values below are CUSTOMER-STATED and are")
    print("not verified against any ticket system by this skill.")
    print("-" * 68)
    if result["fields"]:
        for name, value in result["fields"].items():
            print(f"{name:>20}: {value}")
    else:
        print("(no material supplied yet -- the gaps list below shows what "
              "to collect)")
    print("-" * 68)
    print("MISSING INPUTS (core): "
          + (", ".join(result["missing_core"]) or "none"))
    if result["missing_optional"]:
        print("MISSING INPUTS (optional): "
              + ", ".join(result["missing_optional"]))
    if result["expectation_flags"]:
        print("EXPECTATION REWORDING REQUIRED:")
        for note in result["expectation_flags"]:
            print(f"  - {note}")
    print("-" * 68)
    print("NEXT STEPS (generic official-channel wording; entries must be")
    print("confirmed by the customer in their own console):")
    for step in result["guidance"]:
        print(f"  - {step}")
    print("-" * 68)
    for line in result["limitations"]:
        print(line)


def render_evidence(result: dict) -> None:
    print("=" * 68)
    print("Read-only resource corroboration (point-in-time ECS facts only)")
    print("=" * 68)
    print(f"region          : {result['region_id']}")
    print(f"queried at      : {result['queried_at_local']} (local time)")
    print(f"account label   : {result['account_uid_label']}")
    if result["invalid_ids"]:
        print(f"invalid ids     : {', '.join(result['invalid_ids'])} "
              f"(excluded from the query; ask the customer to confirm)")
    if result["not_found_in_region"]:
        print(f"not found here  : {', '.join(result['not_found_in_region'])} "
              f"(not returned in the queried region; the region may be "
              f"wrong -- never conclude the resource is gone)")
    if result["instances"]:
        for row in result["instances"]:
            print("-" * 68)
            for key in ("instance_id", "instance_name", "zone_id",
                        "instance_type", "os", "charge_type",
                        "console_status", "api_lifecycle_status",
                        "vpc_id", "security_groups"):
                print(f"  {key:>20}: {row[key]}")
    else:
        print("-" * 68)
        print("no instance facts returned")
    for err in result["errors"]:
        print(f"[gap] {err['call']}: {err['code']}: {err['message']}")
    print("-" * 68)
    print(result["note"])
    print("-" * 68)
    for line in result["limitations"]:
        print(line)


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecs_service_escalation.py",
        description=(
            "Read-only guide entry: screen the demand area, build the "
            "escalation/complaint material package, and (optionally) "
            "corroborate affected instances with whitelisted read-only ECS "
            "queries. Never touches the ticket system; never promises any "
            "deadline or outcome."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--screen", action="store_true",
                      help="classify customer wording into demand areas")
    mode.add_argument("--build-package", action="store_true",
                      help="assemble the material package for one intent")
    mode.add_argument("--collect-evidence", action="store_true",
                      help="run the optional read-only ECS fact queries")

    parser.add_argument("--text", default=None,
                        help="customer original wording (with --screen)")
    parser.add_argument("--intent", choices=("escalate", "complaint"),
                        default=None,
                        help="service area (with --build-package)")
    parser.add_argument("--ticket-id", dest="ticket_id", default="")
    parser.add_argument("--submitted", dest="submitted_at", default="")
    parser.add_argument("--waited", dest="waited_so_far", default="")
    parser.add_argument("--replies", dest="replies_so_far", default="")
    parser.add_argument("--impact", dest="business_impact", default="")
    parser.add_argument("--expectation", dest="expected_outcome", default="")
    parser.add_argument("--impact-resources", dest="affected_resources",
                        default="")
    parser.add_argument("--subject", dest="complaint_subject", default="",
                        help="complaint subject: timeliness / outcome / "
                             "attitude / other")
    parser.add_argument("--region-id", dest="region_id", default=None,
                        help="explicit region for --collect-evidence "
                             "(never guessed)")
    parser.add_argument("--instance-ids", dest="instance_ids", nargs="*",
                        default=[], help="optional instance-id filter")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")
    return parser


def fail(next_action: str) -> int:
    print("STATUS: FAIL")
    print(f"NEXT_ACTION: {next_action}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.screen:
        if not (args.text or "").strip():
            return fail("screening needs --text \"<customer original "
                        "wording>\"; without wording, no area can be "
                        "classified.")
        result = screen_request(args.text)
        if args.json:
            print(json.dumps({**result, "mode": "screen", "status": "OK",
                              "next_action": result["recommendation"]}))
        else:
            render_screen(result)
            print("\nSTATUS: OK")
            print(f"NEXT_ACTION: {result['recommendation']}")
        return 0

    if args.build_package:
        if not args.intent:
            return fail("--build-package needs --intent escalate|complaint "
                        "(run --screen first to determine the area).")
        # --submitted feeds both intents under different field names:
        # escalate calls it "submitted_at", complaint calls it "fact_timeline".
        values = {
            "ticket_id": args.ticket_id,
            "submitted_at": args.submitted_at,
            "fact_timeline": args.submitted_at,
            "waited_so_far": args.waited_so_far,
            "replies_so_far": args.replies_so_far,
            "business_impact": args.business_impact,
            "expected_outcome": args.expected_outcome,
            "affected_resources": args.affected_resources,
            "complaint_subject": args.complaint_subject,
        }
        result = build_package(args.intent, values)
        if args.json:
            print(json.dumps({**result, "mode": "build-package"}, indent=2))
        else:
            render_package(result)
            print(f"\nSTATUS: {result['status']}")
            print(f"NEXT_ACTION: {result['next_action']}")
        return 0

    # --collect-evidence
    if not (args.region_id or "").strip():
        return fail("--collect-evidence needs an explicit --region-id "
                    "(e.g. cn-hangzhou). Never guess the region: ask the "
                    "customer or read it from the ticket text they paste.")
    _cli.check_cli_available()
    result = collect_evidence(args.region_id.strip(),
                              list(args.instance_ids or []), args.profile)
    if args.json:
        print(json.dumps({**result, "mode": "collect-evidence"}, indent=2))
    else:
        render_evidence(result)
        print(f"\nSTATUS: {result['status']}")
        print(f"NEXT_ACTION: {result['next_action']}")
    return 0


# ---------------------------------------------------------------------------
# Import-time boundary assertions for the pure functions (deterministic
# judgement logic, guarded inside the script per the batch dev rules).
# ---------------------------------------------------------------------------

# screen_request: escalation + complaint + technical detection, ordering.
_s = screen_request("my ECS ticket gets no response and nobody is "
                    "following up; the disk is full again and the support "
                    "attitude is unacceptable")
assert _s["technical_open"] is True
assert "escalation" in _s["areas"] and "complaint" in _s["areas"]
assert "disk-capacity" in _s["areas"]
assert any(h["target"] == "area:disk-expand-diagnosis"
           for h in _s["handoffs"])
# screen_request: adjacent area routes out without disabling escalation.
_s2 = screen_request("my ECS ticket has no progress, I want a refund now")
assert "refund" in _s2["areas"] and "escalation" in _s2["areas"]
# screen_request: technical-only wording is a pure handoff, no package.
_s3 = screen_request("the disk is full and I cannot write anything")
assert _s3["technical_open"] is True and "escalation" not in _s3["areas"]
assert "do NOT build" in _s3["recommendation"]
# screen_request: empty/neutral input degrades to 'unclear', never crashes.
assert screen_request("")["areas"] == ["unclear"]
assert screen_request("hello")["areas"] == ["unclear"]
# check_expectation: promise shapes flagged; deliverable shape not flagged.
assert check_expectation("they must compensate me and guarantee a fix "
                         "within 24 hours")
assert check_expectation("guarantee a reply within 2 business days")
assert check_expectation("a progress update today and reassignment if the "
                         "engineer is unavailable") == []
assert check_expectation("") == []
# validate_instance_ids: shape gate.
_v, _x = validate_instance_ids(["i-bp1exampleb02e2051b3", "i-", "not-an-id",
                                "i-BP1UPPER"])
assert _v == ["i-bp1exampleb02e2051b3"]
assert sorted(_x) == sorted(["i-", "not-an-id", "i-BP1UPPER"])
assert validate_instance_ids([]) == ([], [])
# build_package: half package still emitted, core gaps listed, status drops.
_p = build_package("escalate", {"ticket_id": "0001ABCX",
                                "expected_outcome": "compensation please"})
assert _p["status"] == "DEGRADED"
assert "submitted_at" in _p["missing_core"]
assert _p["fields"]["ticket_id"] == "0001ABCX"
assert _p["expectation_flags"], "compensation wording must be flagged"
_p2 = build_package("complaint", {
    "complaint_subject": "timeliness", "fact_timeline": "2026-09-10",
    "expected_outcome": "a written review of the handling timeline"})
assert _p2["status"] == "OK" and _p2["missing_core"] == []
assert _p2["limitations"] == list(LIMITATIONS_BLOCK)
# stable JSON shape: both builds carry the same key set.
assert set(_p.keys()) == set(_p2.keys())

if __name__ == "__main__":
    sys.exit(main())
