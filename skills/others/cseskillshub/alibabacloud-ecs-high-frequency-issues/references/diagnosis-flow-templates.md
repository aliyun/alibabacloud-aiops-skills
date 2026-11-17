# Diagnosis Flow Templates and the Answer Contract

This file is the contract between the three layers that produce a customer answer:

| layer | owner | what it decides |
| --- | --- | --- |
| flow class | this file, per `(area, scenario)` | which evidence the answer is allowed to rest on, and in what order the steps run |
| answer slots | the shared dispatcher plus the shared guardrail | which lines survive into the customer block, and in what order |
| narrative | the area's own script | the text that fills the slots |

Vocabulary: an **area** is one customer-symptom family, one entry in the Area Index of
`../SKILL.md`, one `--area <slug>` value. A **scenario** is one situation inside an area.
The dispatcher composes the answer, so a flow class binds to an area only
through its scenarios; a single area can carry scenarios of different classes. The Chinese
names for these two levels are recorded in the project decision log, not in this package.

## 1. Why the class binds to `(area, scenario)` and not to `area`

Measured offline against a PATH-shadowed CLI stub, counting every `aliyun stub called:`
line on the run log and accepting only a run that exits 0 with a non-trivial answer.
Eleven areas answer at least one scenario with **zero cloud reads at all** (the caller
identity pre-check included), and every one of them also contains sibling scenarios that
do read:

| area | scenario that reads nothing | answer size |
| --- | --- | --- |
| `web-service-runtime-config` | `knowledge` | 9661 B |
| `hbr-backup-diagnosis` | `billing-attribution` | 9460 B |
| `stop-mode-billing-guide` | `assess` / `report` / `check-stock` | 6296 / 6462 / 2152 B |
| `bt-panel-diagnosis` | `readback` / `handoff` | 5239 / 3172 B |
| `file-transfer-diagnosis` | `collect` / `guest-plan` | 3443 / 613 B |
| `cloud-assistant-diagnosis` | `invocations` / `snapshot-guard` / `check-env` | 2398 / 1818 / 374 B |
| `public-ip-guide` | `--intent consult` | 2148 B |
| `network-quality-bandwidth` | `judge` / `preflight` | 999 / 232 B |
| `instance-relocation-guide` | `doctor` / `stock` | 564 / 372 B |
| `sas-alert-vulnerability` | bare entry | 1483 B |
| `db-on-ecs-diagnosis` | `check-auth` | 664 B |

Two consequences this file is built around:

1. **Zero-read answering is a property of the path, never of the area.** Each of those
   eleven areas also contains a sibling scenario that reaches the cloud, and each of them
   names a read operation in its own code. The table is therefore a floor, not a ceiling:
   22 areas were probed and 33 were not, and an unprobed area may hold an unlisted
   zero-read path.
2. **A template that keys on `area` would mis-classify every row of that table.** Class
   lookup happens on the scenario actually executed, which the entry script knows and the
   dispatcher infers from the sub-command it was handed.

Demand points the same way: of 200 first customer messages sampled from September tickets,
164 (82%) name no resource identifier and 2 name a region. A first answer usually cannot
rest on a cloud read, because there is nothing to read yet.

## 2. Flow classes

Membership of A, B and D is machine-decidable from the area's own code, and the roster is
reproduced by the command at the end of this section. The predicates, in the order they are
tested:

| class | rule | areas | evidence the answer may rest on |
| --- | --- | --- | --- |
| **A** in-guest | the area's code names a guest dispatch (`run-command` / `invoke-command`, either spelling) | 28 | cloud facts **and** guest readings |
| **B** enumerated verdict | no guest dispatch, and the area defines at least three `VERDICT_*` tokens | 4 | cloud facts plus that verdict |
| **D** read-and-report | everything else: reads the control plane, no guest channel, no verdict set | 23 | cloud facts only |
| **C** knowledge-only | *not* an area class: the scenario actually executed performs no cloud read | overlay on all three (11 measured, floor) | published rules and the document leg only |

Two things that measurement settled, against expectations written earlier in this project:

- **No area is knowledge-only.** All 55 areas name at least one read operation in their own
  code, so **C** can only ever be inherited from a scenario, never declared by an area.
- The in-guest population is **28**, not the 31 or 48 quoted from two earlier static passes.
  Those two passes disagreed because they used different, unreproducible criteria (one
  resolved only direct call sites, the other counted any mention of an in-guest step in the
  area's spec). The rule in the table above is the one now in force, and it is reproducible:

```
python3 - <<'PY'
import os, re
GUEST = re.compile(r'run-command|RunCommand|invoke-command|InvokeCommand', re.I)
VERD = re.compile(r'VERDICT_[A-Z][A-Z0-9_]{2,}')
READ = re.compile(r'"((?:Describe|List|Get)[A-Za-z0-9]+)"')
out = {'A': [], 'B': [], 'D': []}
no_read = []
for d in sorted(os.listdir('scripts/areas')):
    p = os.path.join('scripts/areas', d)
    if not os.path.isdir(p):
        continue
    txt = ''.join(open(os.path.join(r, f), encoding='utf-8', errors='ignore').read()
                  for r, _, fs in os.walk(p) for f in fs if f.endswith('.py'))
    k = 'A' if GUEST.search(txt) else 'B' if len(set(VERD.findall(txt))) >= 3 else 'D'
    out[k].append(d.replace('_', '-'))
    if not READ.search(txt):
        no_read.append(d.replace('_', '-'))
print({k: len(v) for k, v in out.items()})       # {'A': 28, 'B': 4, 'D': 23}
print('areas naming no read at all:', len(no_read))   # 0, which is what makes C an overlay
PY
```

**C overrides the class of the area it runs inside.** An A, B or D area follows its own class
for scenarios that read, and follows the C rules below for a scenario that reads nothing.
That is why the table has 55 areas across three rows while section 1's zero-read measurement
spans eleven areas.

A per-layer HIT / EXCLUDED walk is **not** a class of its own: it is how one class-A area
(`access-block-layered`) reaches its answer, and it is governed by the ranking law in
`../SKILL.md` rather than by anything here.

### A. In-guest diagnosis (28 areas)

1. Resolve identity, then the target, and say which region and account the answer covers.
2. Read the control plane; stop and report if a refusal leaves a layer undecided.
3. Ask for guest evidence, or dispatch one approved non-mutating command through the
   consent gate. A refused consent is a named state, not a silent skip.
4. Evaluate blockers in the documented order for the area.
5. Conclude, then hand over the next action that the customer can actually perform.

An A answer that never got guest evidence is `DEGRADED` and must say its conclusions rest
on cloud facts alone.

### B. Enumerated verdict (4 areas)

Same skeleton as A, minus the guest reading. The report selects one token from the area's closed
`VERDICT_*` set, and the customer answer must carry the reading that produced it plus the
reason the neighbouring verdicts do not apply - `VERDICT_UNKNOWN` and
`VERDICT_INSUFFICIENT` exist precisely so that a run with too little evidence says so
instead of choosing the nearest sounding cause.

### C. Knowledge-only

1. Restate the question in customer words and name the rule that answers it.
2. Answer from the published rule; cite at most three adjudicated documents.
3. Name what would change the answer, in the form of a readable attribute
   ("if the disk is already attached to a running instance, ...").
4. Ask for exactly the identifiers needed to move to A or D, or hand off.

Hard rules for C:

- The answer must not read as if it were about the customer's resources. No `PRIMARY-CAUSE`
  line may claim a verified cause, and no line may assert a state of an instance, disk or
  bill that was never read. The shared guardrail keeps the lead honest: an unverified
  lead is printed as unverified.
- Zero cloud reads is a documented outcome, not a failure. Never emit a `not read:` tail
  listing reads that were never planned, and never pad the answer with an empty evidence
  section.
- A C answer is complete for the question asked. Do not append "run a diagnosis" when the
  diagnosis would not change the rule.

### D. Read-and-report (23 areas)

1 through 3 as in A, then: report what the reads returned including an empty result that
is a real answer, then state the limit of the reading (one region, one account, one
time window) in the customer's own words.

## 3. Answer slots

The template is a selection contract: lines the area printed are kept or folded, never
rewritten. Slots, in print order, with the 8-line / 600-character body ceiling already
enforced by the shared guardrail.

`today` is what the 55 areas produce now, on two instruments, and the two are separated
because they answer different questions. **Answers**: 110 runs - every area, two offline
stub modes, call shapes derived from each area's own `--help` and its intake errors, so all
55 areas reached a diagnosis rather than an argument error. **Code**: the same strings
searched in `scripts/areas/*/`, which is what an area is *capable* of printing even in a
run this corpus did not create (a consent gate, a denied read, a real in-guest reply).

| # | slot | source | when it is dropped | today (answers / code) |
| --- | --- | --- | --- | --- |
| 1 | verdict line | `report_lead`, printed by the area | never | 55/55 |
| 2 | read trace: which operation, how many rows | the area's call log | class C, where there is nothing to trace | **0/55 - not produced**; 1/55 areas print such a line anywhere |
| 3 | the finding in customer words | the area's `[FINDING]` / verdict body | when no layer hit | verdict carries it 55/55; `[FINDING]` 0/55 answers, 1/55 areas |
| 4 | the next customer action | `[HUMAN STEP]`, `[HANDOFF]` | never | an action-ranked line 13/55; a hand-off register named in the answer the customer receives **23/55 areas** (55 of 165 cells); bracket marker 1/55 areas |
| 5 | what stays undecided | `[RISK]`, the not-read tail, `not collected` | when the run read everything the class plans | tail 54/55 - the exception is `public-ip-guide`, a rule answer that planned no read; `not collected` 0/55 answers, 2/55 areas |
| 6 | authorization or consent gap | `authorization_gap_short`, `CONSENT-REQUIRED` | only when that is what happened | the gap block is dispatcher-side, so no area code is needed to emit it - yet under the `no-permission` stub it **fires in 5 of 55 areas**; why the other 50 do not (no read attempted, or a denial in the area's own words that the `action: <product>:<Name>` extractor does not recognise) is not settled here and is open as a routing-batch item. consent 0/55 answers, 1/55 areas |
| 7 | escalated hand-off with console entry | `[HANDOFF]` | when the answer is closed | 2 marker spellings in the package, parsed by nothing |
| 8 | cited documents | the document leg, at most three | when the leg found nothing relevant | 60 anchor records owned by 6 areas, 19 areas reachable through `also_covered_by` |
| 9 | re-verification after the fix | the area's own recheck path | when nothing was applied | recheck wording 1/55 answers; **2/55 areas have a recheck sub-command** |

The code column is reproducible from the package alone:

```
python3 - <<'PY'
import json, os, re
HAND = re.compile(r'(?i)\b(console|submit a (?:ticket|request|work order)|work order|'
                  r'ticket|escalat\w*|human|support engineer|after-?sales|'
                  r'contact alibaba|hand ?-?off|manual review)\b')
RECHECK = re.compile(r'(?i)^(?:re-?check|re-?verify|verify-?status|verify-?fix|'
                     r'readback|retest|post-?check|re-?run)$')
ROWS = re.compile(r'(?i)(?:Describe|List|Get|Lookup)[A-Za-z]+'
                  r'[^\n]{0,60}?\b\d+\s+(?:row|record|item|instance|disk|event)s?\b')
code, hand, recheck, rows = {}, [], {}, []
for d in sorted(os.listdir('scripts/areas')):
    p = os.path.join('scripts/areas', d)
    if not os.path.isdir(p):
        continue
    slug = d.replace('_', '-')
    code[slug] = ''.join(open(os.path.join(p, f), encoding='utf-8', errors='ignore').read()
                         for f in sorted(os.listdir(p)) if f.endswith('.py'))
for needle in ('[FINDING]', '[HUMAN STEP]', '[HANDOFF]', 'CONSENT-REQUIRED',
               'not collected'):
    print('%-18s %d/55' % (needle, sum(needle in t for t in code.values())))
print('op+row-count     %d/55' % sum(bool(ROWS.search(t)) for t in code.values()))
for slug, t in code.items():
    names = set(re.findall(r'add_parser\(\s*["\']([a-z0-9][a-z0-9_-]{2,})["\']', t))
    hit = sorted(n for n in names if RECHECK.match(n))
    if hit:
        recheck[slug] = hit
    # a hand-off register is NOT measurable from code alone: requiring the word on
    # the same line as `print(` finds 11/55 (most areas build the block first and
    # print the list later), accepting any line finds 55/55 (comments count). The
    # operative number is the answer-side one in the table above, 23/55.
    if any(HAND.search(l) for l in t.splitlines() if 'print(' in l):
        hand.append(slug)
print('recheck sub-cmd  %d/55  %s' % (len(recheck), recheck))
print('hand-off wording %d/55' % len(hand))
anchors = json.load(open('references/doc-anchors.json'))['anchors']
owners = sorted({a['area'] for a in anchors} - {'_shared'})
reach = set(owners)
for a in anchors:
    reach.update(a.get('also_covered_by') or [])
print('anchors %d records | owners %d | reachable %d' % (len(anchors), len(owners), len(reach)))
PY
```

Two honest consequences of that column:

- **Slot 2 cannot be filled by the dispatcher.** No area prints which operation it
  called and how many rows came back; the only read information that reaches the
  answer is a *count of failed reads* in the verdict tail, and that count now
  requires a failure word rather than any `[WARN]` line (see the measured
  before/after in §3.1). Synthesising a trace would be inventing it, so slot 2 is an
  area-side development item, not a composer feature.
- **Slot 9 is a display rule for now**: an answer that says the customer applied a
  fix may not claim the pressure eased without a second run. Wiring the second run
  is area work, and only 2 of 55 areas even expose a sub-command that means "check
  again after the change" (`bt-panel-diagnosis readback`, `stop-mode-billing-guide
  verify-status`).

`EVIDENCE_SOURCES` in the shared guardrail names the six source forms
(`cloud-read`, `platform-rule`, `in-guest`, `not-collected`, `refused-read`,
`unverified`) so the gap above is countable. The footer it produces,
`What this answer rests on: …`, appears **only** under `ECS_ANSWER_DETAIL=investigation`
and **only** with a source the run itself named: either in the area's own output, or in
the verdict line and denial code the dispatcher observed. The short answer gets no
restatement of its own lead.

Coverage, measured over 165 investigation runs (all 55 areas, three stub modes):

| source | runs naming it |
| --- | --- |
| `unverified` | 165/165 |
| `in-guest` | 27/165 |
| `refused-read` | 6/165 |
| `platform-rule` | 3/165 |
| `cloud-read` | 0/165 |
| `not-collected` | 0/165 |

The two zeros are the row this table exists for. `cloud-read` is 0 because the offline
stub answers every read with an error body or an empty set, so no `live read HIT` line
ever exists here - it needs a real resource, which is batch-4 work, not a wording gap.
`not-collected` is 0 because only 2 of 55 areas use those words at all, and neither of
those paths ran in this corpus. Both stay honest precisely because the footer cannot
invent them.

A remedy block the customer has to act on is never truncated to fit: the credential
fail-closed block is kept whole and the authorization gap is compressed to its two
decision lines instead. Everything folded out of the body is named in the closing note,
and `ECS_ANSWER_DETAIL=investigation` restores the per-call detail at the cost of a
16-line / 1400-character ceiling.

### 3.1 Counts that were wrong before the corpus was

Three numbers in this section were measured on a corpus the harness had half-blindled,
and all three were re-measured once the shapes were fixed. The instrument, not the
product, was at fault: the first shape discovery read every `{a,b,c}` block in `--help`
as a sub-command, so for 29 of 55 areas it passed an optional flag's value
(`--scope {all,...}`, `--guest-command {auth-failure-history,...}`) where argparse
expects no positional. Those 29 areas answered an intake error, and their answers then
counted as "this area produces no finding line" - which is not what happened: the area
was never run. The current instrument derives the shape from the usage line's bracket
depth and from the error each run prints about itself, and reports the outcome it
actually got: **55 of 55 areas reach a diagnosis** (0 usage-rejected cells).

What that changed in the numbers:

| claim | on the half-blind corpus | on the fixed corpus |
| --- | --- | --- |
| answers asserting failed/degraded reads, before the failure-word rule | 24 of 110 | **87 of 110** |
| the same assertion after the rule | 14 of 110, "all legitimate" | **85 of 110** |
| those assertions on runs that exited 0 | 12 → 4 | **22 → 20** |
| areas with a hand-off register in their code | 43 areas / 12 shapes | not a usable instrument (11/55 strict, 55/55 loose); the answer-side value is 23/55 |
| areas with a recheck sub-command | 1/55 | **2/55** |
| per-claim `[FINDING]` text | 4/55 | **1/55** |
| the earlier `slot 2` failed-read story | "the rule removed 10 false claims" | **it removed 2 of 87** |

The last row is the one worth keeping. The rule is still right - a count of failed reads
must come from a line that says a read failed - but its measured effect is two cells,
not ten, and the remaining claims are substantiated: of the 41 answers that assert
failed or degraded reads under the `identity` stub, **0** have no error body anywhere in
their run log; 51 of the matched lines are the area's own `STATUS: FAIL`, 33 are
`STATUS: DEGRADED`, and 8 are explicit `[WARN]` read failures. That leaves a smaller,
real question this file now records instead: areas print `STATUS: DEGRADED` when a read
*succeeded and returned nothing*, and the stub returns empty sets for everything. Under a
real account that wording would call a valid empty answer a degradation, which is an
area-side wording item, not a composer item.

## 4. What this file does not promise

- It does not apply to a script run directly from `scripts/areas/<area>/`. That path keeps
  its own report shape and is the developer channel; only the dispatcher output is bound
  by slots.
- It does not apply to the 14 extension packages, which still carry the previous directory
  spelling and will be brought to this vocabulary in their own change.
- It does not make class C cheaper or class A safer. It states which answer a run may give,
  so that a missing read shows up as an undeclared gap rather than as a confident sentence.

## 5. Enforcement

`enforced by` is stated because three of these rows were, before this table existed,
promises that nothing checked - the same shape of defect as a permission-denied answer
that promised a grant path the code never produced.

| rule | where it is checked | enforced by |
| --- | --- | --- |
| every customer answer goes through the dispatcher | `../SKILL.md`, mandatory entry script clause | **discipline** (nothing detects a hand-written report) |
| body ceiling and slot order | the composer and its `t*` self-tests in the shared dispatcher | code |
| unverified lead never reads as verified | `report_lead`, self-tested by the `rl_*` checks | code |
| a failed-read count needs a failure word | `rl_call_log_is_not_a_failed_read` and neighbours | code |
| verbatim tokens survive the identifier scrub | `t25`-`t27` (`CREDENTIAL-FAIL-CLOSED`, `UNVERIFIED`) | code |
| the failure class is one of six named classes | `failure_class`, self-tested by `k14`-`k18` | code |
| citations come only from the adjudicated anchor file | the document-leg module, checked by the build-time anchor gate | code |
| no claim that a fix worked without a second run | this file, section 3 slot 9 | **discipline** - and only 2/55 areas expose a sub-command that *is* that second run, so today the rule binds the agent's wording, not the tool's output |
| class C answer asserts no resource state | area scripts own their lead | **discipline** (0 checks; the per-claim `[FINDING]` source exists in 1/55 areas) |
| a hand-off names a real target area | nothing | **not enforced**. 23/55 areas name a hand-off in the answer they actually deliver (measured over 165 investigation runs); 1/55 marks it with a bracket the dispatcher could parse. A code-side census is not usable here: requiring the word on the same line as `print(` finds 11/55, accepting any line finds 55/55 because comments count. |

## 6. The cross-area hand-off (added after this file's slot table was measured)

Slot 4 and slot 7 above were measured on a package that could only hand off in prose.
That is no longer the whole story, so the contract is stated here rather than by
editing the measured column.

Measured demand (37,750 September ECS tickets, each turn attributed to an area by
`routing-measure`):

| quantity | value |
| --- | --- |
| tickets attributed to at least one area | 27,615 of 37,750 (73.2%; the other 10,135 carry no attributable turn - phone-channel tickets included) |
| of those, tickets that walk more than one area | 15,930 (57.7%); 42.2% of all tickets |
| distinct ordered area-to-area transitions seen | 2,288 |
| transitions seen in at least 50 tickets | 114, carrying 9,960 transition events |
| transitions the package documented before this batch | 3 of those 114, 1.0% of the weight |
| hand-off targets in package text that resolve to nothing locally | 65 hits over 16 distinct names, on the scan range this table was built with. The 2026-11-11 re-scan over the full customer text (SKILL.md + `references/**` + `scripts/**`, 165,723 lines) found 84: the old glob skipped `references/areas/` and the constants that assemble the sentence. All 84 are closed in 6.1. |

The shipped answer is `references/routing-table.json`: 104 rows over 33 source areas,
covering 9,319 of the 9,960 events at that threshold (93.6%). How a row earns its
place, in order:

1. the edge was seen in at least 50 real tickets;
2. each trigger word appears in at least 20 customer first questions;
3. fewer than half of those questions belong to tickets whose trajectory never
   reached the target area. This is the test that rejected the four highest-volume
   near-miss words - the generic ones a Chinese customer uses for "charges" (467 of
   its 808 questions did not reach the target), "released" (326 of 489), "alert"
   (92 of 136) and "risk" (99 of 123) - plus 145 further words. They describe the
   product, not the problem. The words themselves are Chinese and are kept out of
   this file by the English-content rule; the exact strings and their numbers are in
   the corpus-side artifact `routing-batch3/edge_terms_heldout.json`.
4. the sub-command needed to switch is one the target area really accepts, read from
   that area's own `--help` (33 of 55 areas expose machine-level scenario values; for
   the other 22 the switch names the area only, instead of inventing a name). The
   customer is never told to run anything: measured on 25 real tickets, five customer
   blocks ended with a switch instruction a customer cannot execute.

Runtime contract, in the customer's block:

```
Continue with: the part of this question still open belongs to the <target> check.
  - What that check settles: <the target area's own heading>
  - Next: we run that check on this same request and report what it finds.
```

The agent half travels on the run log as `HANDOFF-SWITCH: --area <target>
[<sub-command>]`, next to the `HANDOFF:` line that already names the edge and the
words that fired it.

Three lines, at most one per run, and withheld entirely when the run failed on
credentials, on a missing toolchain, or on a rejected argument shape - a run that
read nothing has no standing to redirect anyone. The run log always says which of
those it was, including the case where the agent supplied no customer text at all,
because that is the one the operator can fix.

What is still not true, stated so it does not read as true:

- **Sub-scenario routing is measured only weakly.** Area-level attribution cannot see a
  switch of scenario inside one area, and 22 of 55 areas expose no machine-level
  scenario value at all. The 30-ticket test ran on 2026-11-11 and its numbers are in
  6.1 below; they are a lexical match against the engineer's own turns, which is a
  review aid, not a verdict.
- **The hand-off target names are now adjudicated, one by one, against the published
  catalogue** (6.1). What remains unproven is not the names but the direction: in the
  30 real first questions the block fired 6 times and agreed with the labelled second
  area once, and the label itself comes from a lexical attributor.

### 6.1 Measured after both blocks shipped (2026-11-11, batch 3)

The slot-4 and slot-7 columns above were written while neither block could fire. The
post-launch numbers come from two instruments: 30 real first questions run under an
assumed-role credential, and the 55-area offline corpus driven through the aliyun stub.

| quantity | measured | how to re-run |
| --- | --- | --- |
| hand-off target names that resolve to nothing | 0, down from 84 | `check_routing_table.py` full run, check `t6` (baseline column now 0) |
| how the 84 closed | 50 published in the skill catalogue and kept (HTTP 200 with a `name:` frontmatter equal to the requested name); 33 were mistyped targets this suite already ships and were repointed; 1 has no owner anywhere in the suite and is now a named human path (console finance flow, otherwise a ticket) | commit `e8c5798` |
| hand-off block on a real question | fires 6/30; `no route matched for these words` 12/30; withheld for want of standing 12/30 (all argument errors) | `routing-batch3/run30.py`, field `handoff_line` |
| hand-off target vs the labelled second area | 1 of the 6. The label comes from a lexical attributor, so this is a lead to review, not an accuracy rate | field `handoff_matches_gold_second` |
| slot 7's concrete shape - the instance the customer named cannot be read | the block is present in 23/55 areas on the not-found yardstick, reaches a real candidate list in 18/55 on the listing-answers yardstick, and appeared in 1/30 real tickets | `invalid_id_offer.py` with mode `invalid-id` / `absent-with-list` / `pinned` |
| candidate-list discipline | at most three rows, each carrying id, status, name and region; rows left out are counted, not silenced; an empty read is described as this credential and region, never as "you have no instances"; an unreadable list offers nothing; no id is ever generated | the 13 `b2_*` checks in the dispatcher selftest |
| sub-scenario landing | of 22 tickets entered at an area with machine-acceptable scenario values: 2 hit the value the engineer used, 6 miss, 14 sit at tickets where the engineer's own turns named none. The remaining 8 tickets are at the 22 areas without machine values: capability gap, not a miss | `run30.jsonl`, field `subscenario_verdict` |
| alignment with the engineer's steps | mean aligned prefix 0.40 of 8 steps; 24 of 30 align on zero steps | field `alignment.aligned_prefix`, with `answers30/` kept for a human to overrule |
| what stays undecided (slot 5) | `SOURCES: unverified` 25/30, `in-guest` 4/30, `not-collected` 1/30 | field `sources` |

Two consequences, and they are different in kind:

1. The template keeps earning its place as the **shape** contract. The block added in this
   batch is code, but its customer-visible form - state the absence, offer choices without
   rewriting the customer's own identifier, never upgrade "this credential read nothing"
   into "you have nothing" - is the slot table's rule applied to a case the slot table
   already named. Nothing in the answer's shape had to be invented to ship it.
2. It is still not a routing oracle and must not be cited as one. On 30 tickets the
   cross-area block agreed with the trajectory's second area once out of six firings, and
   the agreement was measured against a label this package produced itself. Promoting the
   template into routing state - one shape per class, chosen in code - would put that
   unmeasured claim inside the executor.
