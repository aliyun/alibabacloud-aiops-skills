# M2: Escalation / Complaint Package (fields, discipline, template)

Companion of `scripts/areas/service_escalation_guide/ecs_service_escalation.py --build-package`. The script
owns the deterministic parts (field collection, core-gap computation,
expectation flagging, limitations text); this module explains the fields and
the wording discipline around them.

## Iron rule (tier-level, from the confirmed requirements)

Commercial/service process demands **must run through the human flow**. The
skill's job is policy-neutral explanation, material structuring and
self-service routing. **Any promise of a result, deadline or compensation
outcome is a design violation.** The package must be handable to a human
intake without needing to be corrected.

## Fact sources (label each value with its source)

| Source label | Meaning | Trust level |
|---|---|---|
| customer-stated | Timeline/progress/impact the customer typed | unverifiable by this skill -- always label |
| customer-pasted | Ticket number or console text pasted verbatim | pass-through; never claim it was checked |
| read-only query | Instance facts from the two whitelisted ECS reads | verified, point-in-time, region-scoped |
| embedded guidance | Generic steps in this skill's references | process advice only, not official policy |

Anything else (entries, button paths, hotline numbers, service-plan terms,
deadline figures) has **no admissible source** here and must not appear.

## Field spec

### Intent: escalate (ticket follow-up)

| Field | Flag | Core? | Guidance |
|---|---|---|---|
| ticket_id | `--ticket-id` | yes | Number exactly as pasted. The skill cannot query it |
| submitted_at | `--submitted` | yes | First submission time as stated by the customer |
| waited_so_far | `--waited` | yes | Elapsed wait as stated (not computed by the skill) |
| replies_so_far | `--replies` | no | One line; "none" is a valid answer |
| business_impact | `--impact` | yes | Concrete impact: service down, users blocked, revenue risk -- facts, not adjectives |
| expected_outcome | `--expectation` | yes | Must be deliverable-shaped (see below) |
| affected_resources | `--impact-resources` | no | Instance ids / region as stated; corroborated only via `--collect-evidence` |

### Intent: complaint

| Field | Flag | Core? | Guidance |
|---|---|---|---|
| complaint_subject | `--subject` | yes | One of: timeliness / outcome / attitude / other |
| ticket_id | `--ticket-id` | no | Related ticket if any (pass-through) |
| fact_timeline | `--submitted` | yes | Key dates of the service history, customer-stated |
| replies_so_far | `--replies` | no | Communication attempts so far |
| business_impact | `--impact` | no | Impact of the service experience |
| expected_outcome | `--expectation` | yes | Deliverable request: a review, a callback window the customer can state, a written response -- never a verdict |

## Expectation discipline (deliverable vs. undeliverable)

The script flags promise-shaped wording; reword before delivery:

| Undeliverable shape (flagged) | Reword toward (deliverable) |
|---|---|
| "guarantee a fix within 24 hours" | "a first progress update today" |
| "compensate me / refund" | removed from the package; belongs to the refund area (handoff-matrix.md) |
| "punish the engineer" | "a review of the handling timeline and communication" |
| "promise an escalation now" | "request escalation of the ticket through official channels" |
| "you must reply by X date" | "confirm the next checkpoint with the handling team" |

## Half-package rule

Never interrogate before producing output: emit the package with what the
customer already said plus the `MISSING INPUTS (core)` list (decision-tree
step 4). The customer decides what to add.

## Optional evidence attachment

`--collect-evidence` output is attached only as a labeled fact sheet:
region, query time (local), instance id/name/zone/type/state lines, and any
requested ids "not found in the queried region". Attach the script's note
that these are resource facts, never ticket facts. If the run degraded
(`STATUS: DEGRADED`), attach the gap line instead; the package ships anyway.

## Final delivery skeleton (order is mandatory)

1. Area statement (from `--screen`).
2. Package fields (verbatim; source labels kept).
3. Evidence fact sheet or its gap note (only if collected).
4. `MISSING INPUTS` list (core first).
5. Generic next steps (support-process-guidance.md) or handoff wording
   (handoff-matrix.md).
6. Limitations block (verbatim from the script).
7. `STATUS` / `NEXT_ACTION` relayed from the script.
