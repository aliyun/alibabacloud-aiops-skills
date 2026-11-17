# Cross-area hand-off and Chinese-question routing - measured basis

Maintainer evidence behind two MANDATORY rules in SKILL.md: the cross-area hand-off
(Execution Flow step 6) and selecting an area from a Chinese question (Area Index).
The binding rules live in SKILL.md; this file records why each row was admitted and how
the numbers are re-derived. Ticket counts and batch labels here are provenance and never
appear in a customer answer.

## Cross-area hand-off (Execution Flow step 6)

6. **Cross-area hand-off is decided by the table, not by improvisation (MANDATORY).**
   Measured over 37,750 real ECS tickets, 15,930 of the 27,615 tickets that name an
   area at all (57.7%) walk through more than one area before they are resolved, and
   this package used to document zero hand-offs between its own 55 areas. The
   dispatcher now reads `references/routing-table.json`, matches the customer's own
   words (passed with `--customer-question`, which is now also listed in `--help`),
   and appends a three-line `Handoff:` block naming the target area, what that area
   settles, and what happens next. The agent half of the hand-off - the exact switch,
   `--area <target>` plus its sub-command - is printed on the run log as
   `HANDOFF-SWITCH:` and must never be pasted into the customer answer, because a
   ticket customer cannot run this script. ABSOLUTE PROHIBITION: do not invent another hand-off
   target, another sub-command, or a skill name that is not in that table; do not
   re-state the block in your own words; and do not add a hand-off when the
   dispatcher withheld it (the run log says `HANDOFF: not evaluated (...)` with the
   reason - credential failure, missing toolchain, or a rejected argument shape).
   Every row was admitted only on words that were tested against tickets that never
   reached the target: a word is dropped when more than half of the tickets using it
   belong to a different area. `ecs-suite-v2/tools/check_routing_table.py` re-derives
   those numbers and fails the build if a row stops clearing them.

## Selecting an area from a Chinese question (Area Index)

The `Triggers:` on each area card are English. When the customer's first question is
Chinese, also match it against `references/trigger-lexicon.json`: per-area Chinese
trigger terms measured over the same 37,750-ticket corpus, each admitted only when it
fires in at least 20 first questions and at most half of those belong to other areas.
It covers the 41 areas whose Chinese vocabulary is discriminative; the other 14 share
words with sibling areas and must be chosen by meaning, using the cross-area table in
`references/routing-table.json`. The lexicon only helps pick `--area`; it never
authorises a dispatch or a write, and a lexical match is a hint, not a confirmed cause.

`python3 scripts/ticket-support.py --route-question "<customer question>"` prints a
`ROUTE-SUGGESTION:` block ranking candidate `--area` slugs from that lexicon. It is a
suggestion-only hint and NEVER dispatches; confirm the area by meaning, then run that
area normally with `--area`. With no lexical signal it prints `no lexical signal`
(exit 1) and you choose by meaning plus the cross-area table. Do not paste the
suggestion block into a customer answer.
