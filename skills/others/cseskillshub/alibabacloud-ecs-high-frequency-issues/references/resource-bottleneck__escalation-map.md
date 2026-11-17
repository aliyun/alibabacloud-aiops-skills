# Escalation and handoff map

The symptoms in this tier are entangled, and the ticket corpus shows the real root
cause frequently living **outside** this skill's scope: behind a "CPU is at 100%"
report there may be a disk throughput ceiling, a public-bandwidth limit, a
cross-border link, malicious traffic, an ICP filing block, or a console
front-end defect. Triage that ends in a correct handoff is a successful outcome,
not a failure — and a handoff is only legitimate when the readings that justify
it are in the report.

The machine-readable copy is `ESCALATION_MAP` in `scripts/areas/resource_bottleneck/_constants.py`.

## Handoff table

| Detected area / evidence | Handoff target | Status of that name |
| --- | --- | --- |
| Disk IO slow, throughput/IOPS at the provisioned ceiling, per-disk BPS attribution, requests to confirm backend storage operations (migration, replica rebuild) | `area:resource-bottleneck` | name in this batch's skill list |
| Capacity / inode usage, expansion that did not take effect, partition not applied | `area:disk-expand-diagnosis` | name in this batch's skill list |
| Instance will not boot, start/stop stuck in an intermediate state, system unbootable | `area:instance-state-diagnosis` | name in this batch's skill list |
| Public bandwidth saturated, EIP / NAT path bottleneck, cross-border latency, DNS resolution, unfiled domain blocked, TLS reset | network-tier skill | **name pending** — do not invent one; see below |
| Attack traffic, malicious process, WAF rule, IP blocking action | security-tier skill | **name pending** — do not invent one; see below |
| Spec change, downgrade/refund fee rules, promotional price continuation, discount | billing / commercial (human, plus account manager) | not a skill |
| Concrete implementation of nginx / MySQL / PHP / SpringBoot tuning | human engineer | skill gives evidence and a parameterized direction only |
| Console front-end defect (e.g. a delete button that does nothing) | front-end / backend specialist ticket | not a resource question |

## How a handoff must be stated

1. Name the reading that triggered it, with its value, caliber and window
   (rule R7), and the rule id (R1-R9) that produced the finding.
2. State explicitly what this skill **can no longer answer**, so the customer does
   not re-ask here.
3. For disk ceilings specifically: report the observed rate and the co-peak
   timestamp, and **escalate the ceiling question** — this skill does not compute
   provisioned BPS/IOPS per disk category (ticket T-CC0FA37F, rule R4).

## The two "name pending" rows

The requirements document lists the network and security handoff targets as
pending alignment with this batch's skill list (section 8, item 14). Until that
alignment lands, the output must say `network-tier skill (name pending)` /
`security-tier skill (name pending)` verbatim, which is exactly what
`ESCALATION_MAP` contains. Guessing a plausible skill name would send the customer
to a package that may not exist — the same class of error as referencing a
resource that was not returned (rule R8, ticket T-50C39C59).

## Weakly-related evidence that is *not* this skill's question

Recorded so an operator does not re-derive it:

| Topic | Why it stays out of scope |
| --- | --- |
| Preemptible/spot instance interruption events | belongs to the instance-state area; relevant only when a "suddenly slow/stopped" report turns out to be an interruption event |
| eRDMA monitoring | only relevant for GPU/HPC families; no ticket in this tier reached it |
| EBS `CreateDiagnoseReport` / `DescribeDiagnoseReport` | listed in the requirements doc as an *optional* diagnosis-report source, flagged for hallucination risk and held pending section 8 confirmation; **not called by this package** and therefore absent from `related_apis.yaml` and `references/ram-policies.md` |
| Application log analysis beyond resource shape (e.g. which URL was requested) | exceeds CloudMonitor's capability; it is an application question |

## When no handoff applies

If every evidenced area is calm, rule R5 permits the negative conclusion "not the
resources" — and it must still carry a direction: which unevidenced question
remains open (R6 gap list), and whether the next step is in-guest historical
replay (`atop -r`), an application review, or an event-log check.
