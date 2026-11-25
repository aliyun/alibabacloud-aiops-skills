#!/usr/bin/env python3
"""
clone_guidance.py -- offline clone-planning, triage, checklist and handoff
engine for the ECS instance clone guide skill.

SECURITY: this script performs NO network calls and NO subprocess calls at
all. It renders the deterministic guidance data embedded in _constants.py
(distilled from the confirmed tier dossier) and applies pure decision
functions. Nothing here can change a cloud resource or touch a credential.
Every console action it describes is executed BY THE CUSTOMER after an
explicit risk notice; high-risk steps (replace operating system wipes the
system disk; snapshot cleanup) additionally require the customer's explicit
acknowledgment in the conversation before the next guided step.

Modes (exactly one per run):
  --plan      choose the clone path and print step-by-step console guidance
  --triage    classify a slow/stuck clone or image task (relative thresholds
              only -- never a time promise) and emit the escalation packet
  --checklist print the post-clone verification checklist, including
              read-only commands the CUSTOMER runs inside their own OS
  --topic     print one embedded FAQ entry; --list-topics to enumerate
  --handoff   match a symptom sentence against the sibling-area handoff map
  --selftest  run the inline boundary assertions of the pure functions

Output contract: human-readable report by default; `--json` prints pure
JSON on stdout (in that mode the STATUS/NEXT_ACTION lines go to stderr).
Every run ends with `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION: ...`.

Usage examples:
  python3 clone_guidance.py --plan --account-relation cross \
      --region-relation cross --target new-purchase
  python3 clone_guidance.py --triage --progress 0 --baseline much-longer
  python3 clone_guidance.py --handoff "website unreachable after switching
      to the cloned security group"
  python3 clone_guidance.py --topic fake-failure
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

from _constants import (
    CLONE_PATHS,
    DATA_BOUNDARY_NOTES,
    DOC_LINKS,
    ESCALATION_TEMPLATE,
    FAQ_TOPICS,
    FEE_ITEMS,
    GOAL_HANDOFFS,
    GUEST_SELF_CHECK_COMMANDS,
    HANDOFF_MAP,
    LANDING_MODES,
    POST_CLONE_CHECKLIST,
    RISK_NOTICES,
    TRIAGE_BRANCHES,
    TRIAGE_COLLECT_FIRST,
)

GUIDANCE_DISCLAIMER = (
    "This skill is read-only guidance: the customer performs every console "
    "step listed here, and this skill never performs write operations or "
    "runs commands inside an instance."
)

PATH_KEYS = {
    ("same", "same"): "same-account-same-region",
    ("same", "cross"): "same-account-cross-region",
    ("cross", "same"): "cross-account-same-region",
    ("cross", "cross"): "cross-account-cross-region",
}

PLAN_DOC_KEYS = ["clone-instances", "create-custom-image", "copy-image",
                 "share-image", "replace-os", "create-snapshot",
                 "snapshot-billing", "delete-snapshot"]


# ---------------------------------------------------------------------------
# Pure decision functions (each guarded by inline boundary assertions below)
# ---------------------------------------------------------------------------

def select_path(account_relation: Optional[str],
                region_relation: Optional[str],
                goal: Optional[str]) -> dict[str, Any]:
    """Map the customer's account/region relation (and goal) onto either a
    clone path, an out-of-scope goal handoff, or a missing-information ask."""
    if goal == "export-offline":
        return {"mode": "handoff", "topic": "export-offline"}
    if goal == "batch-scale":
        return {"mode": "handoff", "topic": "batch-scale"}
    missing = []
    if account_relation not in ("same", "cross"):
        missing.append("account relation (same account or different account)")
    if region_relation not in ("same", "cross"):
        missing.append("region relation (same region or different region)")
    if missing:
        return {"mode": "ask", "missing": missing}
    key = PATH_KEYS[(account_relation, region_relation)]
    return {"mode": "path", "path_key": key}


assert select_path("cross", "cross", None) == {
    "mode": "path", "path_key": "cross-account-cross-region"}
assert select_path("same", "same", None)["path_key"] == \
    "same-account-same-region"
assert select_path(None, "cross", None)["mode"] == "ask"
assert select_path("same", None, None)["missing"] == [
    "region relation (same region or different region)"]
assert select_path(None, None, "export-offline") == {
    "mode": "handoff", "topic": "export-offline"}
assert all(v in CLONE_PATHS for v in PATH_KEYS.values())


def parse_progress(raw: Optional[str]) -> Optional[int]:
    """Parse the customer-reported progress percentage (0-100). Anything
    unparsable or out of range degrades to None -> insufficient facts."""
    if raw is None:
        return None
    try:
        value = int(float(str(raw).strip().rstrip("%")))
    except (TypeError, ValueError):
        return None
    if value < 0 or value > 100:
        return None
    return value


assert parse_progress("0") == 0
assert parse_progress("42%") == 42
assert parse_progress(" 100 ") == 100
assert parse_progress("101") is None
assert parse_progress("half") is None
assert parse_progress(None) is None


def triage_verdict(progress: Optional[int], baseline: str,
                   first_image: str) -> str:
    """Classify a slow/stuck task. Thresholds are RELATIVE to the
    customer's own normal completion time (no official duration standard
    exists in the source evidence). Returns a TRIAGE_BRANCHES key."""
    if progress is None:
        return "info-missing"
    if progress > 0:
        return "in-progress"
    if baseline == "much-longer":
        return "stuck-zero-long"
    if baseline == "normal":
        return "in-progress"
    # Progress is 0% with no baseline: the first full-snapshot image is the
    # only evidence-backed reason for a legitimate 0%, so a known-non-first
    # image cannot wait on that explanation.
    if first_image == "no":
        return "stuck-zero-not-first"
    return "stuck-zero-default"


assert triage_verdict(None, "unknown", "unknown") == "info-missing"
assert triage_verdict(30, "unknown", "unknown") == "in-progress"
assert triage_verdict(0, "much-longer", "unknown") == "stuck-zero-long"
assert triage_verdict(0, "unknown", "yes") == "stuck-zero-default"
assert triage_verdict(0, "unknown", "unknown") == "stuck-zero-default"
assert triage_verdict(0, "unknown", "no") == "stuck-zero-not-first"
assert triage_verdict(0, "normal", "no") == "in-progress"
assert all(k in TRIAGE_BRANCHES for k in (
    triage_verdict(0, "unknown", "no"),
    triage_verdict(0, "unknown", "yes"),
    triage_verdict(0, "much-longer", "no"),
    triage_verdict(None, "unknown", "no"),
    triage_verdict(5, "unknown", "no")))


def match_handoff(symptom_text: str) -> list[dict[str, Any]]:
    """Rank sibling-area topics by keyword hits in the customer's wording."""
    text = (symptom_text or "").lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in HANDOFF_MAP:
        hits = sum(1 for kw in entry["keywords"] if kw.lower() in text)
        if hits:
            scored.append((hits, entry))
    scored.sort(key=lambda pair: -pair[0])
    return [dict(entry, hits=hits) for hits, entry in scored]


assert match_handoff("the website is unreachable after switching security "
                     "group rules")[0]["topic"] == "security-group-behavior"
assert match_handoff("refund my balance please")[0]["topic"] == \
    "commercial-billing"
assert match_handoff("totally unrelated sentence") == []


# ---------------------------------------------------------------------------
# Mode builders (pure payload) + human renderers
# ---------------------------------------------------------------------------

def _doc_lines(keys: list[str]) -> list[str]:
    lines = []
    for key in keys:
        doc = DOC_LINKS.get(key)
        if doc:
            lines.append(f"  - {doc['title']}: {doc['url']}")
    return lines


def build_plan_payload(account_relation: Optional[str],
                       region_relation: Optional[str],
                       goal: Optional[str],
                       target: Optional[str]) -> dict[str, Any]:
    plan = select_path(account_relation, region_relation, goal)
    payload: dict[str, Any] = {"plan": plan}

    if plan["mode"] == "ask":
        payload["status"] = "FAIL"
        payload["next_action"] = (
            "ask the customer the missing questions in one short message, "
            "then rerun --plan; do NOT guess an account/region relation")
        return payload

    if plan["mode"] == "handoff":
        entry = GOAL_HANDOFFS[plan["topic"]]
        payload["label"] = entry["label"]
        payload["wording"] = entry["wording"]
        payload["status"] = "DEGRADED"
        payload["next_action"] = (
            "deliver the handoff wording and the evidence list from "
            "references/handoff-map.md; do not plan a clone chain for "
            "this goal")
        return payload

    path = CLONE_PATHS[plan["path_key"]]
    payload["label"] = path["label"]
    payload["summary"] = path["summary"]
    payload["steps"] = path["steps"]
    payload["landing_mode"] = (
        LANDING_MODES[target]["wording"] if target in LANDING_MODES else
        "ask whether the target is an existing instance (replace-operating-"
        "system landing, wipe warning mandatory) or a new purchase from "
        "the image")
    payload["risk_notices"] = [RISK_NOTICES[k]
                               for k in path.get("risk_notices", [])]
    payload["fees"] = FEE_ITEMS
    payload["docs"] = _doc_lines(PLAN_DOC_KEYS)
    payload["disclaimer"] = GUIDANCE_DISCLAIMER
    payload["status"] = "OK"
    payload["next_action"] = (
        "guide the customer step by step in the console (risk notice + "
        "customer acknowledgment before every high-risk step); after they "
        "finish, verify with scripts/clone_readiness_check.py and "
        "--checklist")
    return payload


def render_plan_human(payload: dict[str, Any]) -> None:
    plan = payload["plan"]
    print("=" * 74)
    if plan["mode"] == "ask":
        print(" Clone path selection - information needed")
        print("=" * 74)
        for item in plan["missing"]:
            print(f"  ? {item}")
        print("  ? what is the goal: clone inside Alibaba Cloud, copy to "
              "an on-premises server, or batch scaling?")
        return
    if plan["mode"] == "handoff":
        print(f" Goal outside clone guidance scope: {payload['label']}")
        print("=" * 74)
        print(f"  {payload['wording']}")
        return
    print(f" Clone path: {payload['label']}")
    print("=" * 74)
    print(f" Summary: {payload['summary']}\n")
    for idx, step in enumerate(payload["steps"], 1):
        print(f" Step {idx} [{step['entry']}]")
        print(f"   action : {step['action']}")
        print(f"   expect : {step['expect']}")
        print(f"   if-not : {step['fallback']}\n")
    print(f" Landing mode: {payload['landing_mode']}\n")
    print(" Mandatory risk notices to deliver BEFORE the customer acts:")
    for notice in payload["risk_notices"]:
        print(f"   ! {notice}")
    print("\n Fee composition to state up front:")
    for item in payload["fees"]:
        print(f"   $ {item}")
    print(f"\n Reminder: {payload['disclaimer']}")
    print("\n Official guides (verify each link against the help center "
          "before quoting; captured from tier research/ticket evidence):")
    for line in payload["docs"]:
        print(line)


def build_triage_payload(progress_raw: Optional[str], baseline: str,
                         first_image: str) -> dict[str, Any]:
    progress = parse_progress(progress_raw)
    branch_key = triage_verdict(progress, baseline, first_image)
    branch = TRIAGE_BRANCHES[branch_key]
    escalate = branch_key in ("stuck-zero-long", "stuck-zero-not-first",
                              "info-missing")
    return {
        "branch": branch_key,
        "verdict": branch["verdict"],
        "wording": branch["wording"],
        "collect_first": TRIAGE_COLLECT_FIRST,
        "escalation_template": ESCALATION_TEMPLATE if escalate else None,
        "first_image_context": first_image,
        "status": "OK" if branch_key != "info-missing" else "DEGRADED",
        "next_action": branch["next"],
    }


def render_triage_human(payload: dict[str, Any]) -> None:
    print("=" * 74)
    print(f" Clone progress triage - branch: {payload['branch']}")
    print("=" * 74)
    print(f" Verdict: {payload['verdict']}")
    print(f" {payload['wording']}")
    print("\n Collect from the customer first (whatever is missing):")
    for item in payload["collect_first"]:
        print(f"   - {item}")
    if payload["escalation_template"]:
        print("\n Escalation packet (platform-side task queues are invisible "
              "to both this skill and a live support session):")
        print(f"   {payload['escalation_template']}")


def build_checklist_payload() -> dict[str, Any]:
    return {
        "checklist": POST_CLONE_CHECKLIST,
        "guest_self_check_commands": GUEST_SELF_CHECK_COMMANDS,
        "guest_note": (
            "These commands are run BY THE CUSTOMER inside their own "
            "operating system and pasted back; they are read-only disk / "
            "identity listings. This skill never executes anything inside "
            "an instance; in-guest remediation belongs to the remote-"
            "connection / Cloud Assistant sibling area."),
        "data_boundary_notes": DATA_BOUNDARY_NOTES,
        "status": "OK",
        "next_action": (
            "for each failing line follow the owner column: read-only "
            "re-check via clone_readiness_check.py, customer console "
            "self-check, or the sibling-area handoff wording from "
            "--handoff"),
    }


def render_checklist_human(payload: dict[str, Any]) -> None:
    print("=" * 74)
    print(" Post-clone verification checklist")
    print("=" * 74)
    for idx, item in enumerate(payload["checklist"], 1):
        print(f" [ ] {idx}. {item['item']}  (owner: {item['owner']})")
        print(f"         {item['detail']}")
    print("\n Guest-side read-only self-check commands (customer runs them "
          "in their own OS and pastes the output back):")
    for entry in payload["guest_self_check_commands"]:
        print(f"   {entry['cmd']}   # {entry['purpose']}")
    print(f"\n {payload['guest_note']}")


def build_topics_payload() -> dict[str, Any]:
    listing = [{"key": key, "question": topic["question"]}
               for key, topic in sorted(FAQ_TOPICS.items())]
    return {"topics": listing, "status": "OK",
            "next_action": "rerun with --topic <key> for the full answer"}


def render_topics_human(payload: dict[str, Any]) -> None:
    print("=" * 74)
    print(" Embedded FAQ topics")
    print("=" * 74)
    for row in payload["topics"]:
        print(f"  {row['key']:<28} {row['question']}")


def build_topic_payload(key: str) -> Optional[dict[str, Any]]:
    topic = FAQ_TOPICS.get(key)
    if topic is None:
        return None
    payload = dict(topic)
    payload["key"] = key
    payload["status"] = "OK"
    payload["next_action"] = topic.get("guidance",
                                       "relay the answer to the customer")
    return payload


def render_topic_human(payload: dict[str, Any]) -> None:
    print("=" * 74)
    print(f" FAQ topic: {payload['key']}")
    print("=" * 74)
    print(f" Q: {payload['question']}")
    print(f" A: {payload['answer']}")
    if payload.get("guidance"):
        print(f" Guidance: {payload['guidance']}")


def build_handoff_payload(text: str) -> dict[str, Any]:
    matches = match_handoff(text)
    if not matches:
        return {
            "matches": [],
            "known_topics": [entry["topic"] for entry in HANDOFF_MAP],
            "status": "DEGRADED",
            "next_action": (
                "no sibling-area keyword matched; keep the request inside "
                "the clone scope or ask one clarifying question about what "
                "the customer wants to achieve"),
        }
    return {
        "matches": [{"topic": m["topic"], "route": m["route"],
                     "hits": m["hits"], "wording": m["wording"]}
                    for m in matches],
        "status": "OK",
        "next_action": (
            "deliver the top wording, attach the evidence list from "
            "references/handoff-map.md, and stop here - the sibling area "
            "owns the rest"),
    }


def render_handoff_human(payload: dict[str, Any]) -> None:
    print("=" * 74)
    if not payload["matches"]:
        print(" Sibling-area handoff match - nothing recognized")
        print("=" * 74)
        print(" Known sibling areas: " + ", ".join(payload["known_topics"]))
        return
    print(" Sibling-area handoff match")
    print("=" * 74)
    for match in payload["matches"]:
        print(f"  topic: {match['topic']}  (route: {match['route']}, "
              f"keyword hits: {match['hits']})")
        print(f"    {match['wording']}")


def run_selftest() -> None:
    """Exercise the pure functions once more and report."""
    assert select_path("same", "cross", None)["path_key"] == \
        "same-account-cross-region"
    assert triage_verdict(parse_progress("0"), "unknown", "unknown") == \
        "stuck-zero-default"
    assert match_handoff("keep the same ip after cloning")[0]["topic"] == \
        "ip-retention"
    assert match_handoff("batch create many instances with host name "
                         "rules")[0]["topic"] == "batch-orchestration"
    assert FAQ_TOPICS["data-disk-included"]["question"].startswith("Does")
    assert build_plan_payload("same", "same", "clone",
                              None)["status"] == "OK"
    assert build_triage_payload("0", "much-longer", "unknown")["status"] == \
        "OK"
    print("selftest: all inline boundary assertions passed")
    print("STATUS: OK")
    print("NEXT_ACTION: use the modes as documented in the module docstring")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def finish(payload: dict[str, Any], json_mode: bool,
           human_renderer) -> None:
    """Deliver one payload under the two-mode output contract."""
    if json_mode:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"STATUS: {payload['status']}", file=sys.stderr)
        print(f"NEXT_ACTION: {payload['next_action']}", file=sys.stderr)
    else:
        if human_renderer is not None:
            human_renderer(payload)
        print(f"\nSTATUS: {payload['status']}")
        print(f"NEXT_ACTION: {payload['next_action']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline clone guidance engine: solution matrix, "
                    "progress triage, post-clone checklist, embedded FAQ "
                    "and sibling-area handoff matching. No network calls.",
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan", action="store_true",
                       help="choose the clone path and print step-by-step "
                            "customer guidance")
    modes.add_argument("--triage", action="store_true",
                       help="classify a slow/stuck clone or image task")
    modes.add_argument("--checklist", action="store_true",
                       help="print the post-clone verification checklist")
    modes.add_argument("--topic", metavar="KEY",
                       help="print one embedded FAQ topic")
    modes.add_argument("--list-topics", action="store_true",
                       help="enumerate FAQ topics")
    modes.add_argument("--handoff", metavar="SYMPTOM",
                       help="match a customer symptom sentence against the "
                            "sibling-area handoff map")
    modes.add_argument("--selftest", action="store_true",
                       help="run the pure-function boundary assertions")
    parser.add_argument("--json", action="store_true", help="JSON output")

    parser.add_argument("--account-relation", choices=("same", "cross"),
                        help="is the target instance in the SAME account "
                             "or a CROSS account")
    parser.add_argument("--region-relation", choices=("same", "cross"),
                        help="is the target in the SAME region as the "
                             "source or a CROSS region")
    parser.add_argument("--target", choices=("existing-instance",
                                             "new-purchase"),
                        help="landing carrier for the clone")
    parser.add_argument("--goal", choices=("clone", "export-offline",
                                           "batch-scale", "unknown"),
                        help="what the customer ultimately wants")
    parser.add_argument("--progress", default=None,
                        help="customer-reported progress percent, e.g. 0 "
                             "or 45 (for --triage)")
    parser.add_argument("--baseline", choices=("normal", "much-longer",
                                               "unknown"), default="unknown",
                        help="elapsed time versus THIS account's normal "
                             "completion time (for --triage)")
    parser.add_argument("--first-image", choices=("yes", "no", "unknown"),
                        default="unknown",
                        help="is this the first custom image for the "
                             "account/region (for --triage)")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if args.plan:
        payload = build_plan_payload(args.account_relation,
                                     args.region_relation,
                                     args.goal or "clone", args.target)
        finish(payload, args.json, render_plan_human)
    elif args.triage:
        payload = build_triage_payload(args.progress, args.baseline,
                                       args.first_image)
        finish(payload, args.json, render_triage_human)
    elif args.checklist:
        payload = build_checklist_payload()
        finish(payload, args.json, render_checklist_human)
    elif args.list_topics:
        payload = build_topics_payload()
        finish(payload, args.json, render_topics_human)
    elif args.topic:
        payload = build_topic_payload(args.topic)
        if payload is None:
            print(f"[ERROR] unknown topic '{args.topic}'.", file=sys.stderr)
            if args.json:
                print(json.dumps({"status": "FAIL", "key": args.topic,
                                  "error": "unknown topic",
                                  "next_action": "enumerate with "
                                                 "--list-topics"},
                                 indent=2))
                print("STATUS: FAIL", file=sys.stderr)
            else:
                print("STATUS: FAIL")
                print("NEXT_ACTION: list the available topics with "
                      "--list-topics and pick the closest one")
            sys.exit(1)
        finish(payload, args.json, render_topic_human)
    elif args.handoff:
        payload = build_handoff_payload(args.handoff)
        finish(payload, args.json, render_handoff_human)
    else:  # argparse mutually-exclusive-required makes this unreachable
        parser.error("exactly one mode is required")


if __name__ == "__main__":
    main()
