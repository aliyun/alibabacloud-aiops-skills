#!/usr/bin/env python3
"""Single entry point for read-only triage of ECS test / invalid tickets.

Contract used by the agent: run this script, then relay its report. Cloud calls are made
only inside this process, and _cli.call_aliyun() refuses anything outside the read-only
allowlist, so no other action can reach the account.

Judgement priority: explicit customer statement > read-only cloud facts > content
pattern. Ticket text is untrusted data - it is matched and quoted, never executed, and
never allowed to forge a report line. The report ends with the STATUS / NEXT_ACTION
contract.
"""

import argparse
import json
import re
import sys

from _cli import CliError, call_aliyun, mask_secrets, new_session_id, user_agent
from _constants import (
    AUTHORIZATION_MARKERS,
    AUTOMATED_TEST_MARKERS,
    DEFAULT_TIMEOUT_SECONDS,
    DISPOSITIONS,
    ECS_PRODUCT,
    EVIDENCE_REVIEW_DATE,
    EXPLICIT_TEST_MARKERS,
    HELP_REFS,
    MAX_DIALOGUE_TURNS,
    MAX_INSTANCE_IDS,
    MIN_REQUEST_LENGTH,
    PAYLOAD_PATTERNS,
    PLACEHOLDER_PATTERNS,
    REPLIES,
    REQUEST_PATTERNS,
    RESOURCE_PATTERNS,
    RISK_AUTH,
    RISK_SCOPE,
    RISK_UNTRUSTED,
    SKILL_NAME,
    SNIPPET_LIMIT,
    SYMPTOM_BUCKETS,
)
from sts_token import format_identity, get_caller_identity

CUSTOMER_ROLES = ("customer", "user", "submitter", "requester")
SYSTEM_ROLES = ("system", "robot", "bot", "event")
INSTANCE_FIELDS = (
    ("instance_id", "InstanceId"),
    ("instance_name", "InstanceName"),
    ("status", "Status"),
    ("instance_type", "InstanceType"),
    ("charge_type", "InstanceChargeType"),
    ("region_id", "RegionId"),
    ("zone_id", "ZoneId"),
    ("creation_time", "CreationTime"),
)
CATEGORY_MEANING = {
    "A": "explicit test or no-action declaration by the customer",
    "B": "automated, interface or security test payload",
    "C": "no identifiable request in the content",
    "D": "a real request inside a ticket that reads as a test - must not be judged invalid",
    "UNKNOWN": "insufficient evidence to judge",
}


# ---------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------

def _read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_ticket(args):
    """Merge an optional ticket JSON file with the command line overrides."""
    ticket = {"biz_id": args.biz_id or "", "title": args.title or "",
              "content": args.content or "", "dialogue": []}
    if args.ticket_file:
        data = _read_json(args.ticket_file)
        if not isinstance(data, dict):
            raise ValueError("--ticket-file must contain a JSON object")
        ticket["biz_id"] = ticket["biz_id"] or str(data.get("biz_id") or "")
        ticket["title"] = ticket["title"] or str(data.get("title") or "")
        ticket["content"] = (ticket["content"]
                             or str(data.get("content") or data.get("description") or ""))
        turns = data.get("dialogue") or data.get("messages") or []
        if isinstance(turns, list):
            ticket["dialogue"] = [turn for turn in turns if isinstance(turn, dict)]
    if args.dialogue_file:
        turns = _read_json(args.dialogue_file)
        if isinstance(turns, dict):
            turns = turns.get("dialogue") or turns.get("messages") or []
        if isinstance(turns, list):
            ticket["dialogue"] += [turn for turn in turns if isinstance(turn, dict)]
    if len(ticket["dialogue"]) > MAX_DIALOGUE_TURNS:
        ticket["dialogue"] = ticket["dialogue"][:MAX_DIALOGUE_TURNS]
    return ticket


def turn_role(turn):
    role = str(turn.get("role") or turn.get("sender") or "unknown").strip().lower()
    if role in CUSTOMER_ROLES:
        return "customer"
    if role in SYSTEM_ROLES:
        return "system"
    return "agent"


def iter_fields(ticket):
    """Yield (source, kind, text) where kind is customer / agent / system."""
    title = (ticket.get("title") or "").strip()
    if title:
        yield "title", "customer", title
    content = (ticket.get("content") or "").strip()
    if content:
        yield "content", "customer", content
    for index, turn in enumerate(ticket.get("dialogue") or [], start=1):
        text = str(turn.get("content") or turn.get("text") or "").strip()
        if text:
            yield "dialogue[%d]" % index, turn_role(turn), text


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------

def _snippet(text, start, end):
    left = max(0, start - 24)
    right = min(len(text), end + 24)
    fragment = re.sub(r"\s+", " ", text[left:right]).strip()
    # Strip control characters so quoted ticket text cannot forge a report line.
    fragment = "".join(char for char in fragment if char.isprintable())
    if len(fragment) > SNIPPET_LIMIT:
        fragment = fragment[:SNIPPET_LIMIT] + "..."
    return fragment


def match_phrases(text, phrases):
    """Bounded match for ASCII phrases, substring match for source-language phrases."""
    hits = []
    lowered = text.lower()
    for phrase in phrases:
        if phrase.isascii():
            match = re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(phrase.lower()),
                              lowered)
            if match:
                hits.append((phrase, _snippet(lowered, match.start(), match.end())))
        else:
            position = text.find(phrase)
            if position >= 0:
                hits.append((phrase, _snippet(text, position, position + len(phrase))))
    return hits


def match_patterns(text, patterns):
    """Return (matched text, pattern, snippet) for each pattern that hits."""
    hits = []
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            hits.append((match.group(0), pattern,
                         _snippet(text, match.start(), match.end())))
    return hits


def extract_resources(text):
    found = {}
    for name, pattern in RESOURCE_PATTERNS:
        values = sorted(set(re.findall(pattern, text, re.IGNORECASE)))
        if values:
            found[name] = values
    return found


def is_placeholder(text):
    stripped = (text or "").strip()
    if not stripped:
        return True
    return any(match_patterns(line, PLACEHOLDER_PATTERNS) for line in stripped.splitlines())


# ---------------------------------------------------------------------------
# judgement
# ---------------------------------------------------------------------------

def score_symptoms(customer_text):
    scored = []
    for name, description, target, phrases in SYMPTOM_BUCKETS:
        hits = match_phrases(customer_text, phrases)
        if hits:
            scored.append({
                "symptom": name,
                "description": description,
                "target": target,
                "evidence": [{"phrase": phrase, "quote": quote} for phrase, quote in hits],
            })
    scored.sort(key=lambda item: len(item["evidence"]), reverse=True)
    return scored


def downgrade(confidence):
    return {"high": "medium", "medium": "low", "low": "low"}[confidence]


def classify(ticket, extra_markers=()):
    """Return the judgement: category, confidence, evidence, risks, handoff, gaps."""
    fields = list(iter_fields(ticket))
    customer_text = "\n".join(text for _, kind, text in fields if kind == "customer")
    machine_text = "\n".join([text for _, kind, text in fields if kind != "agent"])
    test_markers = tuple(EXPLICIT_TEST_MARKERS) + tuple(extra_markers)

    evidence = {"request": [], "test_markers": [], "automated_markers": [], "payload": [],
                "authorization": [], "test_markers_in_agent_replies": []}
    for source, kind, text in fields:
        for phrase, quote in match_phrases(text, test_markers):
            key = "test_markers" if kind == "customer" else "test_markers_in_agent_replies"
            evidence[key].append({"source": source, "phrase": phrase, "quote": quote})
        if kind != "customer":
            continue
        for matched, pattern, quote in match_patterns(text, REQUEST_PATTERNS):
            evidence["request"].append({"source": source, "phrase": matched,
                                        "pattern": pattern, "quote": quote})
        for phrase, quote in match_phrases(text, AUTHORIZATION_MARKERS):
            evidence["authorization"].append({"source": source, "phrase": phrase,
                                             "quote": quote})
    for phrase, quote in match_phrases(machine_text, AUTOMATED_TEST_MARKERS):
        evidence["automated_markers"].append({"source": "customer and system text",
                                              "phrase": phrase, "quote": quote})
    for matched, pattern, quote in match_patterns(customer_text, PAYLOAD_PATTERNS):
        evidence["payload"].append({"source": "customer text", "phrase": matched,
                                    "pattern": pattern, "quote": quote})

    resources = extract_resources(customer_text)
    customer_fields = [text for _, kind, text in fields if kind == "customer"]
    placeholder = bool(customer_fields) and all(is_placeholder(text) for text in customer_fields)
    char_count = len(customer_text.replace(" ", "").replace("\n", ""))
    has_dialogue = bool(ticket.get("dialogue"))

    test_count = len(evidence["test_markers"])
    request_count = len(evidence["request"])
    auto_count = len(evidence["automated_markers"])
    payload_count = len(evidence["payload"])
    title_tested = any(item["source"] == "title" for item in evidence["test_markers"])

    if request_count:
        category = "D"
        confidence = "high" if request_count > 1 else "medium"
    elif auto_count or (payload_count and not test_count):
        category = "B"
        confidence = "high" if (auto_count + payload_count) > 1 else "medium"
    elif test_count:
        category = "A"
        confidence = "high" if title_tested or test_count > 1 else "medium"
    elif customer_fields and (placeholder or char_count < MIN_REQUEST_LENGTH):
        category = "C"
        confidence = "medium"
    else:
        category = "UNKNOWN"
        confidence = "low"

    notes = []
    if category in ("A", "B", "D") and payload_count:
        notes.append("Machine-shaped content was present alongside the %s verdict; it is "
                     "quoted as evidence only." % category)
    if not has_dialogue and category in ("A", "B", "D"):
        confidence = downgrade(confidence)
        notes.append("No dialogue turns were supplied: the verdict rests on the title and "
                     "body alone, so it is marked for review.")

    risks = []
    if evidence["authorization"] and (test_count or auto_count or payload_count):
        risks.append(RISK_AUTH)
    if evidence["payload"] or evidence["automated_markers"]:
        risks.append(RISK_UNTRUSTED)
    risks.append(RISK_SCOPE)

    handoff = None
    if category == "D":
        symptoms = score_symptoms(customer_text)
        primary = symptoms[0] if symptoms else None
        request_summary = "; ".join(
            sorted({item["quote"] for item in evidence["request"]})[:3]) or "see the evidence list"
        handoff = {
            "symptom": primary["symptom"] if primary else "unmapped-real-request",
            "symptom_description": primary["description"] if primary else (
                "a concrete request that the built-in symptom groups did not classify"),
            "target": (primary["target"] if primary else "a human operator")
                      + " (destination tier name pending alignment with this batch)",
            "request_summary": request_summary,
            "other_symptoms": [item["symptom"] for item in symptoms[1:]],
        }

    missing = []
    if not fields:
        missing.append("nothing to judge: no title, no body and no dialogue was supplied")
    elif not customer_fields:
        missing.append("the customer's own words: only agent or system turns were supplied")
    if category == "UNKNOWN":
        missing.append("what the submitter actually wants; the text carries no identifiable "
                       "request and no explicit test declaration")
    if category == "C":
        missing.append("a customer reply to the clarification draft before any invalid "
                       "verdict is recorded")
    if resources.get("masked_order_id"):
        missing.append("the complete order number: a masked one is present and this skill "
                       "has no order API")

    return {
        "category": category,
        "confidence": confidence,
        "evidence": evidence,
        "resources": resources,
        "placeholder_content": placeholder,
        "customer_char_count": char_count,
        "turn_count": len(ticket.get("dialogue") or []),
        "notes": notes,
        "risks": risks,
        "handoff": handoff,
        "missing_information": missing,
        "disposition": DISPOSITIONS[category],
    }


# ---------------------------------------------------------------------------
# read-only verification
# ---------------------------------------------------------------------------

def verify_instances(region_id, instance_ids, session_id, timeout):
    """Confirm visibility and running state of instance ids; changes nothing."""
    facts, limitations = [], []
    ids = [str(item).strip() for item in instance_ids if str(item).strip()]
    if len(ids) > MAX_INSTANCE_IDS:
        limitations.append("only the first %s of %s ids were checked"
                           % (MAX_INSTANCE_IDS, len(ids)))
        ids = ids[:MAX_INSTANCE_IDS]
    if not ids:
        limitations.append("no instance id appeared in the ticket and none was passed with "
                           "--instance-id, so there was nothing to verify")
        return facts, limitations, ids
    if not region_id:
        limitations.append("DescribeInstances requires RegionId and none was given, so no "
                           "cloud call was made for: %s" % ", ".join(ids))
        return facts, limitations, ids

    try:
        body = call_aliyun(ECS_PRODUCT, "DescribeInstances",
                           {"RegionId": region_id, "InstanceIds": json.dumps(ids),
                            "PageSize": max(len(ids), 1)},
                           session_id=session_id, timeout=timeout)
    except CliError as exc:
        hint = (" - the identity behind these credentials lacks ecs:DescribeInstances; "
                "see references/ram-policies.md for the minimal policy"
                if exc.is_permission_error else "")
        limitations.append("the read-only instance check did not complete: %s%s"
                           % (mask_secrets(exc), hint))
        return facts, limitations, ids

    listed = (body.get("Instances") or {}).get("Instance") or []
    if isinstance(listed, dict):
        listed = [listed]
    for item in listed:
        fact = {"checked_by": "ecs:DescribeInstances (read-only)"}
        for key, field in INSTANCE_FIELDS:
            value = item.get(field)
            fact[key] = value if value not in (None, "") else "not returned"
        facts.append(fact)

    visible = {str(item.get("InstanceId") or "") for item in listed}
    invisible = [item for item in ids if item and item not in visible]
    if invisible:
        limitations.append(
            "%s has no record visible to these credentials in region %s. That means 'not "
            "visible here', not 'the id is invalid': an instance in another account (the "
            "usual situation for automated probes), in another region, or already released "
            "all look identical from this call." % (", ".join(invisible), region_id))

    if facts and not invisible:
        params = {"RegionId": region_id, "PageSize": max(len(ids), 1)}
        for index, item in enumerate(ids, start=1):
            params["InstanceId.%d" % index] = item
        try:
            status_body = call_aliyun(ECS_PRODUCT, "DescribeInstanceStatus", params,
                                      session_id=session_id, timeout=timeout)
        except CliError as exc:
            limitations.append("optional DescribeInstanceStatus corroboration was skipped: %s"
                               % mask_secrets(exc))
        else:
            statuses = ((status_body.get("InstanceStatuses") or {}).get("InstanceStatus")) or []
            if isinstance(statuses, dict):
                statuses = [statuses]
            by_id = {str(item.get("InstanceId") or ""): item.get("Status")
                     for item in statuses}
            for fact in facts:
                state = by_id.get(str(fact.get("instance_id")))
                if state:
                    fact["status"] = state
                    fact["status_confirmed_by"] = "ecs:DescribeInstanceStatus (read-only)"
    return facts, limitations, ids


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def build_reply(verdict, facts):
    category = verdict["category"]
    template = REPLIES[category]
    if category != "D":
        return template
    handoff = verdict["handoff"] or {}
    confirmed = ", ".join([str(fact.get("instance_id")) for fact in facts]) or "none"
    return template.format(request=handoff.get("request_summary", "see the evidence list"),
                           target=handoff.get("target", "a human operator"),
                           facts="instance ids confirmed visible to the read-only check: %s"
                                 % confirmed)


def _format_hits(lines, title, hits, label_key):
    lines.append(title)
    if not hits:
        lines.append("    none")
        return
    for item in hits:
        lines.append("    - [%s] %s | quoted: %s"
                     % (item.get("source", "?"), item.get(label_key, ""),
                        json.dumps(item.get("quote", ""), ensure_ascii=False)))


def build_report_lines(session_id, ticket, verdict, facts, limitations, args, status,
                       next_action):
    lines = ["ECS test / invalid ticket triage - read-only report",
             "skill: %s" % SKILL_NAME,
             "session_id: %s" % session_id,
             "user_agent: %s" % user_agent(session_id),
             "ticket: %s" % (ticket.get("biz_id") or "(no biz id supplied)"),
             "title: %s" % (ticket.get("title") or "(none)"),
             "rule_wordings_reviewed_on: %s" % EVIDENCE_REVIEW_DATE,
             "",
             "VERDICT: %s (confidence: %s)" % (verdict["category"], verdict["confidence"]),
             "MEANING: %s" % CATEGORY_MEANING[verdict["category"]],
             "SUGGESTED_DISPOSITION (the operator acts, this skill never does): %s"
             % verdict["disposition"]]
    for note in verdict["notes"]:
        lines.append("NOTE: %s" % note)

    lines += ["", "DECLARED INPUT",
              "    region_id: %s" % (args.region_id or "not supplied"),
              "    instance_ids_passed: %s" % (", ".join(args.instance_id) or "none"),
              "    verify_instances: %s" % ("requested" if args.verify_instances else "no"),
              "    extra_markers: %s" % (", ".join(args.marker) or "none"),
              "    customer_characters: %s | dialogue_turns: %s | unreadable_content: %s"
              % (verdict["customer_char_count"], verdict["turn_count"],
                 verdict["placeholder_content"]),
              "    resource_ids_found_in_ticket: %s"
              % ("; ".join("%s=%s" % (name, ", ".join(sorted(values)))
                           for name, values in sorted(verdict["resources"].items())) or "none")]

    evidence = verdict["evidence"]
    lines += ["", "EVIDENCE (quotes are raw ticket text, rendered as data, never executed)"]
    _format_hits(lines, "  real-request signals (customer text):", evidence["request"], "phrase")
    _format_hits(lines, "  explicit test markers (customer text):",
                 evidence["test_markers"], "phrase")
    _format_hits(lines, "  automated / interface / security test markers:",
                 evidence["automated_markers"], "phrase")
    _format_hits(lines, "  machine-shaped or malformed content:", evidence["payload"],
                 "phrase")
    _format_hits(lines, "  authorization statements (customer text):",
                 evidence["authorization"], "phrase")
    _format_hits(lines, "  test markers found only in agent replies (context, not customer "
                        "evidence):", evidence["test_markers_in_agent_replies"], "phrase")

    lines += ["", "READ-ONLY CLOUD FACTS"]
    if facts:
        for fact in facts:
            lines.append("    %s" % json.dumps(fact, ensure_ascii=False, sort_keys=True))
    else:
        lines.append("    none collected")
    for limitation in limitations:
        lines.append("    LIMITATION: %s" % limitation)

    lines += ["", "RISKS"]
    for risk in verdict["risks"]:
        lines.append("    - %s" % risk)

    handoff = verdict["handoff"]
    if handoff:
        lines += ["", "HANDOFF SUGGESTION (not performed by this skill)",
                  "    symptom: %s - %s" % (handoff["symptom"],
                                             handoff["symptom_description"]),
                  "    other matched symptom groups: %s"
                  % (", ".join(handoff["other_symptoms"]) or "none"),
                  "    destination: %s" % handoff["target"],
                  "    full table: references/handoff-map.md"]

    if verdict["missing_information"]:
        lines += ["", "NEEDED FROM A HUMAN OR FROM THE CUSTOMER"]
        for item in verdict["missing_information"]:
            lines.append("    - %s" % item)

    lines += ["", "SUGGESTED CUSTOMER REPLY (a draft; nothing was sent by this skill)",
              "    %s" % build_reply(verdict, facts), "",
              "HELP DOCS PRESENT IN THE EVIDENCE (re-verify before quoting to a customer)"]
    for description, url in HELP_REFS:
        lines.append("    %s: %s" % (description, url))
    lines += ["", "STATUS: %s" % status, "NEXT_ACTION: %s" % next_action]
    return lines


NEXT_ACTIONS = {
    "A": "archive the ticket as a test submission and keep this report as the basis",
    "B": "archive as a controlled test and pass the payload excerpt to the security owner",
    "C": "send the one-round clarification draft, then suggest closing as invalid if no "
         "request arrives",
    "D": "route the ticket to the destination named in the handoff suggestion; this skill "
         "performs no handoff itself",
    "UNKNOWN": "have a human read the ticket and supply the missing information before any "
               "verdict is recorded",
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only triage of Alibaba Cloud ECS test / invalid tickets.")
    parser.add_argument("--biz-id", help="ticket business id, for the report header")
    parser.add_argument("--title", help="ticket title")
    parser.add_argument("--content", help="ticket body as submitted by the customer")
    parser.add_argument("--ticket-file",
                        help="path to a JSON object with biz_id, title, content, dialogue")
    parser.add_argument("--dialogue-file",
                        help="path to a JSON list of {role, content, timestamp} turns")
    parser.add_argument("--marker", action="append", default=[],
                        help="extra trigger phrase, repeatable; use it for vocabulary the "
                             "built-in table does not carry")
    parser.add_argument("--verify-instances", action="store_true",
                        help="run the read-only instance check over ids from --instance-id "
                             "or found in the ticket")
    parser.add_argument("--instance-id", action="append", default=[],
                        help="instance id to verify, repeatable")
    parser.add_argument("--region-id", help="RegionId used by the read-only check")
    parser.add_argument("--show-caller", action="store_true",
                        help="also label the report with the account the credentials belong to")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help="per-call timeout in seconds (default %(default)s)")
    parser.add_argument("--json", action="store_true", help="emit the same report as JSON")
    args = parser.parse_args(argv)

    session_id = new_session_id()

    try:
        ticket = load_ticket(args)
    except (OSError, ValueError) as exc:
        message = mask_secrets(exc)
        if args.json:
            print(json.dumps({"session_id": session_id, "status": "FAIL", "error": message,
                              "next_action_suggestion": "pass --title and --content, or fix "
                                                        "the --ticket-file JSON"},
                             ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print("\n".join([
                "ECS test / invalid ticket triage - read-only report",
                "session_id: %s" % session_id,
                "    ERROR: the ticket input could not be read: %s" % message,
                "STATUS: FAIL",
                "NEXT_ACTION: pass --title and --content, or fix the --ticket-file JSON",
            ]))
        return 1

    verdict = classify(ticket, extra_markers=args.marker)
    facts, limitations = [], []
    checked_ids = []
    if args.verify_instances:
        ids = list(args.instance_id) or list(verdict["resources"].get("instance_id") or [])
        facts, limitations, checked_ids = verify_instances(args.region_id, ids, session_id,
                                                           args.timeout)
    if not args.verify_instances and args.instance_id:
        limitations.append("instance ids were supplied but --verify-instances was not set, so "
                           "no read-only check ran; the ids stay unverified")

    if args.show_caller:
        caller = get_caller_identity(session_id=session_id, timeout=args.timeout)
        if caller:
            verdict["notes"].append("read-only calls were made as account %s"
                                    % format_identity(caller))
        else:
            limitations.append("caller identity is unavailable, so the account scope of any "
                               "read result cannot be stated")

    if not list(iter_fields(ticket)):
        status = "FAIL"
        next_action = "supply at least a title and a body (or a --ticket-file) to judge"
    else:
        status = "DEGRADED" if (limitations or verdict["category"] == "UNKNOWN") else "OK"
        if verdict["category"] == "D":
            next_action = "%s: %s" % (NEXT_ACTIONS["D"], verdict["handoff"]["target"])
        else:
            next_action = NEXT_ACTIONS[verdict["category"]]

    if args.json:
        report = {
            "session_id": session_id,
            "biz_id": ticket.get("biz_id") or "",
            "title": ticket.get("title") or "",
            "verdict": verdict["category"],
            "verdict_meaning": CATEGORY_MEANING[verdict["category"]],
            "confidence": verdict["confidence"],
            "disposition_suggestion": verdict["disposition"],
            "declared_input": {
                "region_id": args.region_id or "",
                "instance_ids_passed": args.instance_id,
                "instance_ids_checked": checked_ids,
                "verify_instances": bool(args.verify_instances),
                "extra_markers": args.marker,
            },
            "metrics": {
                "customer_characters": verdict["customer_char_count"],
                "dialogue_turns": verdict["turn_count"],
                "unreadable_content": verdict["placeholder_content"],
            },
            "resources_found": verdict["resources"],
            "evidence": verdict["evidence"],
            "notes": verdict["notes"],
            "read_only_facts": facts,
            "limitations": limitations,
            "risks": verdict["risks"],
            "handoff_suggestion": verdict["handoff"],
            "missing_information": verdict["missing_information"],
            "suggested_customer_reply": build_reply(verdict, facts),
            "help_doc_references": [{"description": item, "url": url}
                                    for item, url in HELP_REFS],
            "rule_wordings_reviewed_on": EVIDENCE_REVIEW_DATE,
            "status": status,
            "next_action_suggestion": next_action,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("\n".join(build_report_lines(session_id, ticket, verdict, facts, limitations,
                                           args, status, next_action)))
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
