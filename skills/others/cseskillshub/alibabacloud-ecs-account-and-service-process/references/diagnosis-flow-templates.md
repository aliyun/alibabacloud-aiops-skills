# Diagnosis Flow Templates and the Answer Contract

> This file is generated from measured code facts of this package: the class
> membership in section 1 and the marker census in section 3 are reproducible with
> the commands quoted there. Do not edit those numbers by hand; re-measure.

This file is the contract between the three layers that produce a customer answer:

| layer | owner | what it decides |
| --- | --- | --- |
| flow class | this file, per `(axis, scenario)` | which evidence the answer is allowed to rest on, and in what order the steps run |
| answer slots | the dispatcher (`scripts/account-and-service-process.py`) plus the shared guardrail (`scripts/_guardrails.py`) | which lines survive into the customer block, and in what order |
| narrative | the axis entry script | the text that fills the slots |

Vocabulary: an **axis** is one customer-symptom family, one entry in the Axis Index
of `../SKILL.md`, one `--axis <slug>` value. A **scenario** is one situation inside
an axis - a sub-command or a path the axis takes. The dispatcher composes the answer,
so a flow class binds to an axis only through its scenarios; a single axis can carry
scenarios of different classes.

## 1. Why the class binds to `(axis, scenario)` and not to `axis`

The predicates below are machine-decidable from the axis code. Measured over the
5 axes of this package: **A** (in-guest) 1, **B** (enumerated verdict)
0, **D** (read-and-report) 4. Class **C** (knowledge-only) is
not an axis property: it is inherited by any *scenario* that performs no cloud read,
while every axis here also contains scenarios that do read - so C can never be
declared by an axis, only inherited from a scenario.

| class | rule (tested in this order) |
| --- | --- |
| **A** in-guest | the axis code names a guest dispatch (`run-command` / `invoke-command`, either spelling) |
| **B** enumerated verdict | no guest dispatch, and the axis defines at least three `VERDICT_*` tokens |
| **D** read-and-report | everything else: names control-plane reads, no guest channel, no verdict set |
| **C** knowledge-only | overlay: the scenario actually executed performs no cloud read |

Membership per axis, with the guest-activation flags the dispatcher recognizes and
the cloud operations the axis code names:

| axis | class | guest flags | verdict tokens | cloud operations named in code |
| --- | --- | --- | --- | --- |
| `account-transfer-guide` | A | - | 1 | DescribeAvailableResource, DescribeInstanceStatus, DescribeInstances |
| `business-contact-routing` | D | - | - | DescribeAvailableResource, DescribeInstanceStatus, DescribeInstances |
| `instance-tag-metadata-guide` | D | - | - | DescribeInstanceStatus, DescribeInstances, ListTagResources |
| `invalid-ticket-triage` | D | - | - | DescribeInstanceStatus, DescribeInstances |
| `swas-boundary-guide` | D | - | - | DescribeAvailableResource, DescribeInstanceStatus, DescribeInstances |

Reproduce the class column from the package root:

```
python3 - <<'PY'
import os, re
GUEST = re.compile(r'run-command|RunCommand|invoke-command|InvokeCommand', re.I)
VERD = re.compile(r'VERDICT_[A-Z][A-Z0-9_]{2,}')
out = {"A": [], "B": [], "D": []}
for d in sorted(os.listdir("scripts/axes")):
    p = os.path.join("scripts/axes", d)
    if not os.path.isdir(p):
        continue
    txt = "".join(open(os.path.join(r, f), encoding="utf-8", errors="ignore").read()
                  for r, _, fs in os.walk(p) for f in fs if f.endswith(".py"))
    k = "A" if GUEST.search(txt) else "B" if len(set(VERD.findall(txt))) >= 3 else "D"
    out[k].append(d.replace("_", "-"))
print(out)
PY
```

This package does not publish a measured zero-read path list yet. When a scenario
reads nothing (rule answers, boundary routing, plan-only first contact), the C rules
in section 2 govern it; treat the class table as a floor for what reads exist in
code, not as a claim that every path reads.

## 2. Class rules

**A - in-guest.** 1) resolve identity, then the target, and say which region and
account the answer covers; 2) read the control plane, stop and report if a refusal
leaves a layer undecided; 3) ask for guest evidence, or dispatch one approved
non-mutating command through the consent gate - a refused consent is a named state
(`CONSENT-REQUIRED:`), not a silent skip; 4) evaluate blockers in the documented
order; 5) conclude, then hand over the next action the customer can perform. An A
answer that never got guest evidence is degraded and must say its conclusions rest
on cloud facts alone.

**B - enumerated verdict.** Same skeleton minus the guest reading. The report selects
one token from the axis's closed `VERDICT_*` set and the answer must carry the
reading that produced it plus why the neighbouring verdicts do not apply;
`VERDICT_UNKNOWN` / `VERDICT_INSUFFICIENT` exist so that too little evidence says so
instead of choosing the nearest-sounding cause.

**D - read-and-report.** Steps 1-3 as in A (without step 3's guest leg), then report
what the reads returned - an empty result is a real answer - and state the limit of
the reading (one region, one account, one time window) in the customer's own words.

**C - knowledge-only overlay.** Restate the question in customer words and name the
rule that answers it; answer from published rules, no more than three cited pages;
name what would change the answer as a readable attribute; ask for exactly the
identifiers needed to move to A or D, or hand off. Hard rules: the answer must not
read as if it were about resources that were never read; zero cloud reads is a
documented outcome, not a failure - never emit a tail listing reads that were never
planned; a C answer is complete for the question asked, do not append "run a
diagnosis" when the diagnosis would not change the rule.

## 3. Answer slots of this package

The template is a selection contract: lines the axis printed are kept, folded, or
sanitized - never rewritten into claims the run did not make. The dispatcher
composes the customer block in this order:

1. the axis report body, as printed by the axis entry script;
2. a `CONSENT-REQUIRED:` notice whenever guest flags were stripped before the run;
3. a credential fail-closed block (`CREDENTIAL-FAIL-CLOSED:`, exit 3) listing the
   checks the customer can run, when a credential-class error was seen;
4. an instance-offer block when the target instance was not readable or was never
   given: at most 3 candidates (`INSTANCE_OFFER_LIMIT`) taken from a listing that
   reads up to `OFFER_MAX_PAGES` pages of `OFFER_PAGE_SIZE` and, past that bound,
   says how many it counted rather than pretending the list ended - under the
   invariant that the id the customer named is never rewritten into one of them and
   no id is invented, and that a record naming some other instance is never read as
   evidence about the one asked for. An empty list describes this credential and
   this region, never "you have no instances". When an id was named, a bounded
   existence check walks the built-in `SWEEP_REGIONS` list (29 regions, one filtered
   read per region, inside `SIGHTING_BUDGET_S`) and reports exactly one of three
   states: readable in region X, with the re-run spelled out and no automatic
   switch of the diagnosis target; not readable in the N of 29 the sweep completed
   when the identity was refused or the budget ran out, where regions never reached
   are named as not checked and not as empty; or not readable in any of the 29,
   which also says the regions outside that list were not covered;
5. one final pass through `customer_view`: internal banners, request ids, raw uids,
   session ids and invoke ids are stripped or masked, script paths become
   "the skill entry point", and the agent-facing `STATUS:` / `NEXT_ACTION:` contract
   lines stay on the run log for the agent.

Marker census, from the axis code of this package (not from a run): `STATUS:` in
5/5 axes, `NEXT_ACTION:` in 5/5, the degraded wording in
5/5, "not collected" in 1/5. Every axis names at least one read op, so no axis is knowledge-only by construction.

## 4. What this file does not promise

- It does not apply to a script run directly from `scripts/axes/<axis>/`. That path
  keeps its own report shape and is the developer channel; only the dispatcher
  output is bound by slots.
- It adds no call, no gate and no parameter of its own. Every mechanism it names
  already exists in the dispatcher, the guardrail, or the axis code.
- Cross-package routing is prose, not a table: the boundary sentences in
  `../SKILL.md` (the "do not claim core first-contact symptoms" round) are what
  hand a symptom to the core package or to a sibling skill. This package ships no
  routing table and no machine hand-off block; do not simulate one.
- The core package's slot vocabulary (routing-table.json, the three-line `Handoff:`
  block, the adjudicated document leg) does not exist here. The honesty rules above
  bind instead: no claim about a resource that was not read.

## 5. Enforcement

| rule | where it is checked | enforced by |
| --- | --- | --- |
| every customer answer goes through the dispatcher | `../SKILL.md` entry-script clauses | **discipline** (nothing detects a hand-written report) |
| consent gate strips guest flags before the axis runs, and names the strip | dispatcher + `_guardrails.py`, covered by `--selftest` | code (the 44-check selftest) |
| credential-class failure ends fail-closed with customer-executable checks | dispatcher + `_guardrails.py`, covered by `--selftest` | code |
| the instance-offer block never invents an id and never rewrites the customer's | `_guardrails.instance_offer_block`, covered by `--selftest` | code |
| a stopped region sweep reports the regions it never reached as not checked, and a filtered read naming another instance is dropped rather than diagnosed | `instance_sightings` + the axis fetch layer, exercised offline against a stub CLI (`ext-release` stub regression, 20 scenarios) | code |
| internal markers, identifiers and paths stay out of the customer block | `_guardrails.customer_view`, covered by `--selftest` | code |
| class C answers assert no resource state | the axis scripts own their lead | **discipline** - the rule binds the agent's wording, not the tool's output |
