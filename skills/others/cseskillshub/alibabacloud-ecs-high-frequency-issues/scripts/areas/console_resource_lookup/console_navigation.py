#!/usr/bin/env python3
"""
console_navigation.py -- pure-knowledge console navigation entry (read-only)
============================================================================
SECURITY: This script makes NO cloud API call and NO subprocess invocation at
all; it answers from knowledge tables embedded in _constants.py (every row is
sourced from a real, verified support ticket). It never proposes any change:
its output is entry paths, concept corrections, gating explanations, error
cards, and handoff sentences.

Usage:
    python3 scripts/areas/console_resource_lookup/console_navigation.py --list-topics
    python3 scripts/areas/console_resource_lookup/console_navigation.py --topic region-scoped-views
    python3 scripts/areas/console_resource_lookup/console_navigation.py --question "instance list is empty
        but the server is still running"
    python3 scripts/areas/console_resource_lookup/console_navigation.py --entry ram-console
    python3 scripts/areas/console_resource_lookup/console_navigation.py --gate detach
    python3 scripts/areas/console_resource_lookup/console_navigation.py --error "NoPermission.RAM"
    python3 scripts/areas/console_resource_lookup/console_navigation.py --route "disk expanded, OS still
        sees the old size"

Contract: text (or --json) + `STATUS:` / `NEXT_ACTION:` lines; exit 0 when a
match was found, 1 when nothing matched (the caller then falls back to the
intake questions).
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

from _constants import (
    CONCEPT_MAP,
    ENTRY_MAP,
    ERROR_CARDS,
    GATE_RULES,
    HANDOFF_ROUTES,
    INTAKE_QUESTIONS,
    NAV_TOPICS,
    OFFICIAL_DOCS,
)

_STOPWORDS = {
    "the", "a", "an", "is", "are", "to", "of", "in", "on", "for", "and",
    "or", "my", "i", "it", "but", "and", "how", "do", "does", "can", "not",
    "where", "why", "what", "this", "that", "with", "when", "you", "your",
}


def _tokens(text):
    low = (text or "").lower()
    words = re.findall(r"[a-z0-9][a-z0-9._-]*", low)
    toks = {w for w in words if w not in _STOPWORDS and len(w) > 2}
    for run in re.findall(r"[\u4e00-\u9fff]+", low):
        if len(run) == 1:
            toks.add(run)
        else:
            toks.update(run[i:i + 2] for i in range(len(run) - 1))
    return toks


def _score(needles, haystack):
    hay = _tokens(haystack)
    if not hay or not needles:
        return 0
    overlap = len(needles & hay)
    return overlap * 2 + (1 if any(n in haystack.lower() for n in needles)
                          else 0)


def _rank(question, limit=4):
    """Rank knowledge candidates against a free-text customer question."""
    needles = _tokens(question)
    scored = []
    for key, topic in NAV_TOPICS.items():
        s = _score(needles, topic["question"] + " " + topic["answer"])
        scored.append((s, "topic", key))
    for key, entry in ENTRY_MAP.items():
        s = _score(needles, entry["title"] + " " + entry["say"])
        scored.append((s, "entry", key))
    for card_key, card in ERROR_CARDS.items():
        s = _score(needles, card["signal"] + " " + card["meaning"] + " "
                   + card["steps"])
        scored.append((s, "error", card_key))
    for index, rule in enumerate(GATE_RULES):
        s = _score(needles, rule["symptom"] + " " + rule["gate"] + " "
                   + rule["unlock"])
        scored.append((s, "gate", str(index)))
    for index, row in enumerate(CONCEPT_MAP):
        s = _score(needles, " ".join(row))
        scored.append((s, "concept", str(index)))
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return scored[:limit]


def _print_topic(key):
    topic = NAV_TOPICS[key]
    print(f"Topic: {key}")
    print(f"Q: {topic['question']}")
    print(f"A: {topic['answer']}")


def _print_entry(key):
    entry = ENTRY_MAP[key]
    print(f"Entry: {entry['title']}")
    print(f"Path guidance: {entry['say']}")
    print(f"Verified console link: {entry['url']}")
    print(f"Ticket-verified usage: {', '.join(entry['tickets'])}")


def _print_error(key):
    card = ERROR_CARDS[key]
    print(f"Error signal: {card['signal']}")
    print(f"What it means: {card['meaning']}")
    print(f"What to do: {card['steps']}")
    print(f"Evidence source: {card['source']}")


def _print_gate(index):
    rule = GATE_RULES[int(index)]
    print(f"Symptom: {rule['symptom']}")
    print(f"Why the entry is gated: {rule['gate']}")
    print(f"Unlock path (manual): {rule['unlock']}")
    for doc_key in rule["docs"]:
        print(f"Official doc: {OFFICIAL_DOCS.get(doc_key, doc_key)}")
    print(f"Ticket-verified: {rule['source']}")


def _print_concept(index):
    term, reality, action = CONCEPT_MAP[int(index)]
    print(f"Customer wording: {term}")
    print(f"Product reality: {reality}")
    print(f"Where it is actually done: {action}")


def _print_route(symptom):
    needles = _tokens(symptom)
    printed = 0
    for route in HANDOFF_ROUTES:
        if _score(needles, route["pattern"]) > 0:
            print(f"Route: {route['pattern']}")
            print(f"  Target: {route['target']}")
            print(f"  Keep while handing off: {route['extra']}")
            printed += 1
    return printed


def main():
    parser = argparse.ArgumentParser(
        description="Console entry navigation, concept corrections, gating "
                    "rules, error cards and handoff routes (knowledge only, "
                    "no API calls).")
    parser.add_argument("--list-topics", action="store_true",
                        help="list all knowledge topic keys")
    parser.add_argument("--topic", default="", help="print one topic by key")
    parser.add_argument("--entry", default="", help="print one console entry")
    parser.add_argument("--error", default="",
                        help="print one error-signal card by key")
    parser.add_argument("--gate", default="",
                        help="index (or keyword) into the gating rules")
    parser.add_argument("--route", default="",
                        help="symptom text -> handoff route lookup")
    parser.add_argument("--question", default="",
                        help="customer wording, matched across all tables")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list_topics:
        payload = {"topics": sorted(NAV_TOPICS),
                   "entries": sorted(ENTRY_MAP),
                   "errors": sorted(ERROR_CARDS)}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("Topics:\n  " + "\n  ".join(payload["topics"]))
            print("Console entries:\n  " + "\n  ".join(payload["entries"]))
            print("Error cards:\n  " + "\n  ".join(payload["errors"]))
        print("STATUS: OK")
        print("NEXT_ACTION: pick the matching key and relay it verbatim; "
              "combine with lookup_console_resource.py output when the "
              "question involves a specific resource")
        return 0

    found = False
    out = {}
    if args.topic and args.topic in NAV_TOPICS:
        found = True
        _print_topic(args.topic)
    elif args.entry and args.entry in ENTRY_MAP:
        found = True
        _print_entry(args.entry)
    elif args.error and args.error in ERROR_CARDS:
        found = True
        _print_error(args.error)
    elif args.gate and str(args.gate).isdigit() and int(args.gate) < len(
            GATE_RULES):
        found = True
        _print_gate(args.gate)
    elif args.gate:
        for index, rule in enumerate(GATE_RULES):
            if _tokens(args.gate) & _tokens(rule["symptom"] + rule["gate"]):
                found = True
                _print_gate(index)
                break
    elif args.route:
        found = bool(_print_route(args.route))
        if not found:
            print("No handoff route matched; the symptom may still be in "
                  "scope -- answer from topics/entries instead.")
    elif args.question:
        ranked = _rank(args.question)
        if ranked:
            found = True
            print(f"Best knowledge matches for: {args.question!r}")
            for score, kind, key in ranked:
                print(f"--- {kind} [{key}] (score {score})")
                if kind == "topic":
                    _print_topic(key)
                elif kind == "entry":
                    _print_entry(key)
                elif kind == "error":
                    _print_error(key)
                elif kind == "gate":
                    _print_gate(key)
                else:
                    _print_concept(key)
        out = {"ranked": ranked if ranked else []}

    if not found and not (args.topic or args.entry or args.error
                          or args.gate or args.route or args.question):
        print("Nothing asked: use --list-topics, or pass --question \"<the "
              "customer's own wording>\".")
    if not found:
        print("\nNo confident match. Ask the intake questions:")
        for q in INTAKE_QUESTIONS:
            print(f"  - {q}")
        print("STATUS: FAIL")
        print("NEXT_ACTION: put the intake question card to the customer "
              "(which resource, which identifier, which region shown, which "
              "account, which exact button/error), then re-run")
        return 1

    if args.json and out:
        print(json.dumps(out, indent=2, default=str))
    print("STATUS: OK")
    print("NEXT_ACTION: relay the matched guidance verbatim; never invent "
            "console paths or doc URLs outside these tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
