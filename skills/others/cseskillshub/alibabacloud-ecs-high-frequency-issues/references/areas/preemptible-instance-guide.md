---
name: alibabacloud-ecs-high-frequency-issues
area: preemptible-instance-guide
description: |
  Read-only Alibaba Cloud ECS guide for preemptible (spot) instances that were reclaimed or interrupted. Checks instance existence, status and spot billing type, queries spot inventory, and answers with official rule statements plus evidence.
  Use when customers say: spot instance disappeared on its own | preemptible instance reclaimed, data lost | spot instance stopped with no operation record | will enter the stopped state due to inventory changes | cannot buy spot instances in this zone | 5 minute spot interruption notice | recover a released preemptible instance | spot queries fail with NoPermission
  Do NOT use for non-spot stop causes, subscription expiry, snapshot rollback, billing amount reconciliation, Auto Scaling architecture, or resource changes.
---

# ECS Preemptible (Spot) Instance Reclamation Guide

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

A **read-only** question-answering and evidence-gathering guide for one symptom area:
an Alibaba Cloud ECS **preemptible (spot) instance was interrupted, stopped by the
system, or reclaimed**, and the customer wants to know why, whether the data is
recoverable, whether spot capacity is available, and how the charges are composed.

The pipeline is always: **gather read-only facts -> apply documented rules -> output an
evidence-based report plus the next step for the CUSTOMER to take**. There is no repair
step, because nothing in this flow is a repair.

## When to use

- A spot instance vanished, stopped itself, or was reclaimed and the customer asks why.
- The customer received (or did not receive) the pre-interruption notice and wants the
  reclamation rules explained.
- The customer asks whether the environment or data on a reclaimed spot instance can be
  recovered, or how to keep data before the next reclamation.
- The customer asks which interruption mode (`StopCharging` / direct release) applies, what
  it keeps, or why the instance cannot be restarted after a stop-charging interruption.
- The customer asks about the guaranteed usage duration: what the 1-hour setting protects,
  and whether it can be changed after creation.
- The customer cannot buy a spot instance in a given region/zone/type and asks whether
  and when stock returns.
- The customer asks why a spot instance costs more than the spot price, or why a disk is
  still charged while the instance is stopped.
- The customer asks whether their workload is fit for spot at all.

## Do NOT use

| Ask | Hand off to |
|---|---|
| A non-spot instance stopped, or a spot-labelled instance whose billing type is not spot | Instance stop / forced-stop and billing tiers |
| Stop-mode rules of a pay-as-you-go **non-spot** instance (how to turn stop-charging on, what it saves) | Pay-as-you-go stop-mode tier — but do answer the spot case here: the interruption mode of a spot instance, and the fact that retained disks / EIP / snapshots keep billing |
| Actually taking, rolling back or pricing snapshots and images | Snapshot and image tiers |
| Reconciling specific amounts, refunds, invoices, vouchers, coupons | Billing and commerce tier |
| Subscription (prepaid) expiry, renewal, mistaken deletion and recovery lifecycle | Expiry, release and retention lifecycle tier |
| Designing an Auto Scaling / multi-instance high-availability architecture | Solution and architecture tier |
| Changing the billing type of a running spot instance, or swapping its public IP | Not answered here: no bundled evidence; state that and route to a support ticket |

If a request mixes both (for example "my instance stopped and I was overcharged"),
answer only the spot-reclamation part with evidence and route the rest.

## Permission model: strictly read-only

This skill resolves facts through **read-only** OpenAPI queries only.

**ABSOLUTE PROHIBITION — the agent MUST NOT, under any phrasing of the request:**

1. Call, generate, or suggest any action that is not read-only. The only permitted action
   names are those starting with `Describe`, `Get`, or `List`; any action whose name
   creates, changes, removes, attaches, detaches, restarts, powers, or otherwise mutates
   state is outside the whitelist and MUST NOT be invoked here **or** handed to the
   customer as a command line to run.
2. Run any command inside a customer instance — read-only commands included. This skill
   has no guest access, no Cloud Assistant execution and no Workbench session.
3. Submit, change, or prepare any cloud configuration on the customer's behalf:
   snapshots, image creation, disk attributes, billing-type change, notification
   recipients, message-center settings.
4. Query or estimate bill amounts. No billing API is whitelisted.
5. Claim that anything was fixed, cleaned up, restored, or changed. The only outcomes
   this skill can report are: a fact read back, a rule stated, a limitation, a next step
   for the customer.

**Customer-executed guidance (RO+G).** Where the resolution requires the customer to act
in the console, this skill provides the path, the option names, the material list and the
impact warning — and stops there. Before any such step the report MUST state the
irreversibility that applies, for example: *after the instance is gone the data on disks
released together with it cannot be recovered, and the retention settings below only
protect instances that are still running.* Re-verification afterwards uses the same
read-only queries only.

### API whitelist

| Product | Action | Purpose here |
|---|---|---|
| ecs | `DescribeInstances` | Existence, status, zone, billing type and spot bidding mode of the instance |
| ecs | `DescribeInstanceStatus` | Batch status sweep for many instance IDs |
| ecs | `DescribeAvailableResource` | Whether a region/zone/instance-type is sellable, including spot |
| sts | `GetCallerIdentity` | Confirm which account the read-only queries can see (traceability label only) |

Anything not in this table is out of scope and MUST NOT be called. The whitelist is also
enforced in code (`scripts/areas/preemptible_instance_guide/spot_instance_check.py`, which rejects any action not starting
with `Describe`/`Get`/`List`).

See `references/ram-policies.md` for the exact actions and the minimal policy snippet.

## Prerequisites

- Alibaba Cloud CLI installed and configured through its **default credential chain**
  (profile or platform-injected credentials). Never ask for, accept, echo, store or pass
  an AccessKey pair or a security token; this skill has no code path that takes
  credentials as arguments.
- The credential must hold the read-only actions in
  `references/ram-policies.md`, for the region being queried.
- Queries only ever see resources of **the account behind the active credential**, within
  **the region passed in**. Cross-account instances, resources in other regions, history
  of already-released instances, bill amounts, and notification delivery records are not
  visible here. When a lookup comes back empty, say so; do not infer customer error.

## How to run

Single entry point; the agent runs this script and must not assemble API calls by hand.

```bash
# 0. Optional: confirm which account is in scope
python3 scripts/areas/preemptible_instance_guide/sts_token.py

# 1. Why did it stop / is it still there? (accepts several IDs)
python3 scripts/areas/preemptible_instance_guide/spot_instance_check.py --region <RegionId> \
    --instance-id <instance-id> [--instance-id <instance-id> ...]
python3 scripts/areas/preemptible_instance_guide/spot_instance_check.py --region <RegionId> --name <instance-name>

# 2. Sweep the region for spot instances (batch identification)
python3 scripts/areas/preemptible_instance_guide/spot_instance_check.py --region <RegionId> --all-spot

# 3. Can this spot capacity be bought right now?
python3 scripts/areas/preemptible_instance_guide/spot_instance_check.py --region <RegionId> --inventory \
    --instance-type <instance-type> [--zone-id <zone-id>] \
    [--spot-strategy SpotWithPriceLimit|SpotAsPriceGo]

# 4. Rules only, no cloud call (mechanism, retention, inventory, billing scope)
python3 scripts/areas/preemptible_instance_guide/spot_instance_check.py --explain

# Machine-readable output for any mode
python3 scripts/areas/preemptible_instance_guide/spot_instance_check.py ... --json
```

`--region` is required for every cloud-querying mode and is never guessed. Only
`InstanceChargeType=PostPaid` and the pagination parameters are auto-filled, and the
report declares them under `ASSUMPTIONS`.

## Interpretation flow

```
Ask arrives
|-- "why did my spot instance stop / disappear"
|   DescribeInstances + DescribeInstanceStatus
|   |-- not visible in this region/account -> report "not found" (consistent with a
|   |   reclamation, NOT proof of one) -> mechanism rules -> retention branch -> stability
|   |   option (customer-executed billing-type change guidance)
|   |-- Stopped / stopping
|   |   |-- bidding mode present (SpotWithPriceLimit / SpotAsPriceGo)
|   |   |      -> spot reclamation rules + interruption-event self-check path
|   |   |-- NoSpot -> NOT this tier: route to the stop-cause / expiry / billing tier
|   |   |-- lock reason says recycling -> strongest available in-API signal
|   |-- Running -> no reclamation happened; report status and the risk rules
|-- "can the data come back / how do I keep it"      -> references/preemptible-instance-guide__ref-data-retention.md
|   FIRST ask/read the interruption mode: direct release = disks released with the
|   instance; StopCharging (stop-charging) = disks, EIP and snapshots retained and
|   still billed, and a later restart may fail on inventory or price
|-- "what does the 1-hour setting protect"           -> guaranteed usage duration, fixed at
|   creation and not modifiable; after it is exceeded the notice gives about 5 minutes
|-- "cannot buy, sold out, when is stock back"       -> DescribeAvailableResource ->
|   references/preemptible-instance-guide__ref-inventory-advisor.md
|-- "why does it cost this much / disk still billed" -> references/preemptible-instance-guide__ref-billing-scope.md
|-- "is my workload fit for spot"                    -> suitability rules + handoff
|-- anything needing an amount, a delivery record, or a cause the APIs do not expose
    -> state the limitation, give the self-check path, route to a support ticket
```

**Attribution discipline (the most important rule in this skill).** "The instance is
gone" is provable; "it was reclaimed" is provable from the spot billing type plus the
status and lock fields; **"whether the market price or the inventory caused this
particular interruption" is NOT readable from the whitelisted queries**. Never pick one
cause. Report both triggers, point at the interruption-event self-check path in
`references/preemptible-instance-guide__ref-spot-mechanism.md`, ask for the customer's bidding mode to explain the
mechanics, and route platform-side evidence requests to a support ticket.

## Output contract

Every run ends with the machine-consumable contract, and the agent's answer mirrors it:

```
STATUS: OK          # all planned queries returned
STATUS: DEGRADED    # at least one query failed or was skipped; limitations listed
STATUS: FAIL        # nothing could be read; guidance and handoff still given
NEXT_ACTION: <the single next step, customer-executed or "await customer input">
```

Reporting rules:

- Quote only values actually returned, plus rule statements traced to
  `references/preemptible-instance-guide__ref-*.md`. Restate the script's `Summary`, `FINDINGS`, `LIMITATIONS`,
  `STATUS` and `NEXT_ACTION`.
- Cite the source document for every rule, and carry the bundled caveat that the help
  links were recorded from the tier evidence bundle and not re-fetched while packaging,
  so version-sensitive values (the 5-minute notice, retention limits) must be checked
  against the live official document before being quoted as current.
- Confidence by fact class: mechanism rules that depend only on billing type and cloud
  rules are OS-independent (high); Windows-specific interruption behaviour has no
  bundled evidence (low, unverified — do not assert it).
- Placeholder resource identifiers only in examples (`i-bp1xxxxxxxxxxxx`), never a real
  customer resource ID.
- Authentication failures are reported with the literal provider codes
  `NoPermission` or `ImplicitDeny`, naming the missing action and pointing at
  `references/ram-policies.md`. Failed API calls are echoed with their `Code`, `Message`
  and `RequestId` verbatim (credential material is masked by the shared layer).

## Known limitations (state them, do not work around them)

| Cannot | Nearest available |
|---|---|
| Read the interruption mode (direct release vs `StopCharging`) or the guaranteed usage duration from the read-only queries | Neither `DescribeInstances` nor `DescribeInstanceStatus` returns them: ask the customer to read the setting on the instance, then apply the matching rule row |
| Tell price-trigger vs inventory-trigger for one interruption | Both triggers explained + self-check path + ticket |
| Read SMS / notification delivery records or the recipient list | Message Center guidance, customer-executed |
| Read bill amounts or daily charges | Cost-composition rules + self-check paths |
| Show which disks/snapshots the customer kept | Ask the customer, or route to the disk/snapshot tier |
| Prove the release time | Only what `DescribeInstances` still returns |
| Restore a released instance or its data | No exit; say it plainly and give the prevention list |
| Answer "convert a spot instance to subscription" or "swap the public IP" | No bundled evidence; route to a support ticket |

## Observability

Every API invocation of one script run carries a per-run session id and a User-Agent
built from `AlibabaCloud-Agent-Skills/{skill_name}/{session_id} skill-version/{skill-version}`, where `{session_id}` is
a 32-character hex string from `uuid.uuid4().hex` and `{skill_name}` is
`area:preemptible-instance-guide`.

- The session id is generated once per run in `scripts/areas/preemptible_instance_guide/_cli.py` (`session_id()`) and
  reused by every call, so all calls of one diagnosis correlate.
- It is attached to every call as the CLI flag `--user-agent` (`user_agent()` ->
  `UA_TEMPLATE` in `scripts/areas/preemptible_instance_guide/_constants.py`), including the identity call.
- Per-attempt timeouts (`DEFAULT_TIMEOUT`, 60 s), bounded retry with backoff for
  throttling / 5xx / timeouts, and a page-count guardrail keep runs observable and
  finite.

## References

| File | Contents |
|---|---|
| `references/ram-policies.md` | Exact read-only actions, minimal policy snippet, auth-failure handling |
| `references/preemptible-instance-guide__ref-spot-mechanism.md` | Reclamation mechanism, notice and protection period, bidding modes, attribution limits, distinguishing other stop causes |
| `references/preemptible-instance-guide__ref-data-retention.md` | What survives a reclamation, retention options and their limits, customer-executed protection steps |
| `references/preemptible-instance-guide__ref-inventory-advisor.md` | Inventory querying, sold-out semantics, suitability judgement, spot advisor entries |
| `references/preemptible-instance-guide__ref-billing-scope.md` | Cost composition, stop-state and release-day charging, self-check paths, amount boundary |
| `references/preemptible-instance-guide__ref-handoff.md` | Neighbour-tier identification, handoff wording, open questions that must not be answered |
