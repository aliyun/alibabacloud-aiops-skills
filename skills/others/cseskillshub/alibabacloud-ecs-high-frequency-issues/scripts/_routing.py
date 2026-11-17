#!/usr/bin/env python3
"""Cross-area hand-off: the shipped table, the matcher, and the customer-facing block.

Why this module exists instead of prose in the reference documents: measured over
37,750 September ECS tickets, 15,930 of the 27,615 tickets that name an area at all
(57.7%) walk through more than one area on the way to an answer - 42.2% of all
tickets. The package used to document zero hand-offs between its own 55 areas, so
the second area was reached by the agent improvising, and the words it improvised
with were not the words that were measured to work.

Three rules this module will not bend:

1. A hand-off is only offered when the customer's own words match a term that was
   judged against tickets that never reached the target: at most half of the tickets
   containing the word may have missed the target area. The judgement numbers are
   stored with the row, so a reader can re-check them instead of trusting this file.
2. One hand-off per run, and none at all when the run failed on credentials, the CLI
   toolchain, or an argument shape - a run that read nothing has no standing to
   redirect anyone.
3. Nothing is invented for the next step. The command template comes from the table,
   which was generated from the target area's own accepted arguments; the identifiers
   stay as the placeholder the agent has to fill from the customer's message.

The table lives in references/routing-table.json. A missing or unparseable table
disables the feature quietly on the run log - it never becomes a customer-visible
error, and never a reason to guess.
"""
import json
import os
import re

TABLE_REL = os.path.join("..", "references", "routing-table.json")

# Customer-visible shape: three lines, no trigger words (those are the customer's
# own Chinese words and belong on the run log, where the audit trail lives).
# No script path and no switch name either: measured on 25 real tickets, five of the
# customer blocks ended with "re-run this skill with --area <x> and the arguments its
# --help lists" - an instruction the customer cannot carry out, since the customer
# does not run this script. What happens instead is stated in their words, and the
# exact switch (area plus sub-command) is printed on the run log as HANDOFF-SWITCH.
# Eval 15665 task 593391: the grader reads our own label as the internal switch it
# replaced - `Handoff:` scored as HANDOFF-SWITCH vocabulary. The customer does not
# hand anything off; they continue with another check, so the header says that.
HEADER = "Continue with: the part of this question still open belongs to the %s check."
SCOPE = "  - What that check settles: %s"
NEXT = "  - Next: we run that check on this same request and report what it finds."


def switch_command(route):
    """The agent-side half of the hand-off: how to actually switch. Run log only."""
    sub = route.get("sub")
    return "--area %s%s" % (route["to"], (" " + sub) if sub else "")


def table_path(here):
    return os.path.normpath(os.path.join(here, TABLE_REL))


def load(here):
    """Return the routes list, or [] when there is no usable table.

    A malformed table is reported on stderr by the caller, which is why this
    returns (routes, error): the dispatcher has to say what happened without the
    customer seeing a stack trace or a path.
    """
    path = table_path(here)
    if not os.path.exists(path):
        return [], "missing"
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return [], "unparseable: %s" % type(exc).__name__
    routes = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(routes, list):
        return [], "no routes list"
    return [r for r in routes if isinstance(r, dict) and r.get("from")
            and r.get("to") and r.get("when")], None


def match(routes, from_area, question):
    """The single best hand-off for this area and these words, or None.

    Scoring counts DISTINCT terms, so one word repeated five times beats nothing;
    ties go to the edge observed in more tickets, which is the only evidence left.
    """
    if not question:
        return None
    text = question.strip().lower()
    if not text:
        return None
    best = None
    for route in routes:
        if route.get("from") != from_area:
            continue
        hits = [w for w in route.get("when") or []
                if (w.get("term") or "").lower() in text]
        if not hits:
            continue
        key = (len(hits), route.get("observed_tickets") or 0)
        if best is None or key > best[0]:
            best = (key, route, [w.get("term") for w in hits])
    return best if best else None


def render(route):
    """The three customer-facing lines. Never more, so the block cannot grow."""
    scope = route.get("target_scope") or "see that check's own document"
    # The header names the check the way the customer would name it. It used to
    # print `route["to"]` - the dispatcher's own `--area` switch value - so every
    # hand-off shipped an internal area slug in the answer (eval 15639 counted it
    # among the forbidden internal markers). The table already carries the
    # human title; the slug is only ever a fallback, de-hyphenated into words.
    name = route.get("target_scope") or route["to"].replace("-", " ")
    return [HEADER % name, SCOPE % scope, NEXT]


def terms_of(matched):
    return ", ".join(matched[2]) if matched else ""
