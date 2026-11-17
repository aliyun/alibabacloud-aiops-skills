---
name: alibabacloud-ecs-high-frequency-issues
area: punishment-appeal-guide
description: |
  Read-only triage and manual guidance for ECS violation punishments and unblock appeals: classify the disposal tier, corroborate it with read-only ECS Describe queries, then give the rectification checklist, appeal materials, submission channel and review timeliness.
  Use when the customer says (Triggers): "account frozen by risk control"; "ECS instance force stopped or locked"; "server shut down after violation notice"; "website blocked, how do I appeal"; "UnknownError when paying or renewing".
  Do NOT use for DDoS blackhole unblock (area:attack-blackhole-diagnosis), plain start/stop faults (area:instance-state-diagnosis), general ECS diagnosis (alibabacloud-ecs-diagnose), security-group-only reachability, 25-port email, ICP filing or refunds.
metadata:
  openclaw:
    requires:
      env: []
      bins: [aliyun, python3]
---

# Alibaba Cloud ECS Punishment and Appeal Guide

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Guidance for customers hit by a platform disposal on the violation /
risk-control area: the account is frozen by risk control, an instance was
force-stopped or locked, a website or URL was blocked for illegal content,
an order was intercepted at payment, or a "blocked" claim arrives with no
notice at all. The skill classifies the disposal tier, corroborates it with
read-only ECS queries, and then outputs the remediation checklist, the
appeal-material list, the submission-channel wording and the review
timeliness. It changes nothing, anywhere: appeals, unblocks and cleanups
are executed by platform specialists and by the customer, never by this
skill.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these phrases
(the same list the `description` advertises):

- "account frozen by risk control"
- "ECS instance force stopped or locked"
- "server shut down after violation notice"
- "website blocked, how do I appeal"
- "UnknownError when paying or renewing"

Customers state symptoms, not root causes: match the symptom sentence or
the error string, never assume a disposal type before the facts come back.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under NO circumstances
   may you generate, write or execute any mutating call — action families
   such as `Create*`, `Update*`, `Modify*`, `Delete*`, `Put*`, `Attach*`,
   `Detach*`, `Add*`, `Remove*`, `Reset*`, `Release*`, `Import*`,
   `Revoke*`, `Bind*`, `Unbind*`, `Start*`, `Stop*`, `Reboot*` and Cloud
   Assistant command-injection APIs — including "commands for the user to
   run manually" produced through this skill's scripts. This skill is
   read-only: mutating requests end as console guidance text, never as an
   executable action.
2. **API WHITELIST:** The only permitted OpenAPI actions are the four ECS
   reads `DescribeInstances`, `DescribeInstanceStatus`,
   `DescribeSecurityGroups`, `DescribeSecurityGroupAttribute` (product ecs,
   version 2014-05-26) plus the STS identity check
   (`aliyun sts get-caller-identity`, plugin mode). Nothing else may be
   called, in any error path.
3. **NO GUEST ACCESS, NO PROXIED ACTIONS:** This skill never executes
   commands inside the instance, never logs in for the customer, never
   submits an appeal for them and never files snapshots on their behalf.
   Customer-side remediation (delete pages, fix trojans, stop an instance,
   take a snapshot) is delivered as step guidance only, and every cleanup
   instruction MUST start with "create a manual snapshot or full backup
   first" — the customer performs it in the console.
4. **ABSOLUTE PROHIBITION (credential handling):** Never read, print,
   cache or pass AK/SK/STS tokens explicitly; never export credential
   variables or pass `--access-key-id` / `--access-key-secret` style flags
   (the scripts do not accept them). Credentials resolve only through the
   aliyun CLI default credential chain; on failure guide them to verify the default credential chain with `aliyun sts get-caller-identity`.
5. **NO FABRICATION:** Every conclusion cites a notice field the customer
   provided or a field actually returned by the four whitelisted queries.
   Punishment records, violating-content detail, appeal progress and
   supervisory blocks are NOT queryable here — say so. The only
   evidence-backed error string for this tier is `ErrorCode: UnknownError`
   (transaction interception); do not invent other codes, and do not quote
   the appeal-form URL until its official confirmation (use the link inside
   the customer's own notice, or a support ticket).
6. **SCOPE BOUNDARY:** Requests outside the punishment/rectification/appeal
   area are recognized and handed off per
   [references/punishment-appeal-guide__handoff-map.md](references/punishment-appeal-guide__handoff-map.md) — blackhole/DDoS,
   plain start/stop faults, security-group-only reachability, disk
   expand/IO/capacity, host cleanup, 25-port email, ICP filing, guest
   login repair, lightweight-server products, refunds.

## Execution Principle (script-only, no fallback)

All evidence operations MUST be performed by running the bundled script
under `scripts/`. The agent MUST NOT assemble its own `aliyun` CLI commands
or bypass the entry script — the scripts embed the whitelist, pagination,
retry, timeout, credential masking and observability guarantees that
ad-hoc commands lack. If a script fails or degrades, relay its report and
follow its `NEXT_ACTION` line; NEVER fall back to manual CLI queries.
Knowledge answers (tiers, materials, timeliness, talks) come from the
embedded `references/` modules and the script's built-in knowledge, never
from model memory.

## User Confirmation (required before any API call)

1. Restate the scope to the user: the region, the target identifiers
   (instance IDs / public IP), and that only read-only Describe queries
   from the whitelist will run against the current account.
2. Obtain confirmation to proceed. An explicit request naming the target
   resource already authorizes the read-only run: restate and proceed. If
   region or target is ambiguous, ask once and wait.
3. For every customer-side action the guidance suggests (cleanup edits,
   stopping an instance to cut cost, submitting materials), state what it
   does, its blast radius and reversibility, and leave the execution — and
   its confirmation — entirely to the customer.

## Observability

All OpenAPI calls (issued through the aliyun CLI by the scripts) carry:

- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`,
  where `{skill-name}` is `area:punishment-appeal-guide`.
- **session-id**: a 32-character hex string (`uuid.uuid4().hex`) generated
  once per script run and attached to every CLI invocation of that run, so
  all calls of one diagnosis correlate. It is a random label, not an
  account identifier.

The shared layer in `scripts/areas/punishment_appeal_guide/_cli.py` implements this automatically: the
session-id is created lazily on first call and concatenated into the
`--user-agent` argument of every `aliyun` invocation.

## Prerequisites

1. **aliyun CLI 3.x** on PATH (built-in metadata mode for the ecs product,
   plugin mode for `aliyun sts get-caller-identity`).
2. **Python 3.9+**, standard library only — no third-party packages.
3. **Alibaba Cloud credentials** configured in the CLI default chain; the
   RAM identity needs exactly the actions in
   [references/ram-policies.md](references/ram-policies.md).

## Input Parameters

| Parameter | Flag | Required | Notes |
|-----------|------|----------|-------|
| RegionId | `--region-id` | Yes | every whitelisted query is region-scoped |
| Instance ids | `--instance-ids` | No | comma-separated ECS instance IDs |
| Public IP | `--public-ip` | No | alternative locator for the claimed asset |
| Security group | `--security-group-id` | No | force-inspect one group |
| Symptom hint | `--symptom` | No | account / instance / url / port / transaction / judicial / unverified; `auto` (default, auto-filled and declared) classifies from notice + facts |
| Notice keyword | `--notice-keyword` | No | key wording copied from the customer's notice |
| Port check | `--check-port` + `--check-protocol` | No | does an ingress allow rule explain the outage |

**Auto-fill declaration**: whenever `--symptom` is defaulted to `auto`, or
the account label is derived via the STS identity check, the final answer
MUST declare this explicitly (for example: "symptom hint auto-defaulted to
auto-classification; account label auto-derived from the credential").
Never ask the customer for their UID when the identity check can derive the
label: auto-fill first, ask second.

## Module Index

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Classification | [references/punishment-appeal-guide__penalty-type-classification.md](references/punishment-appeal-guide__penalty-type-classification.md) | 7-tier disposal model, decision tree, evidence-to-conclusion rules, verified query matrix |
| M2: Remediation | [references/punishment-appeal-guide__remediation-checklist.md](references/punishment-appeal-guide__remediation-checklist.md) | backup-first cleanup checklists per violation type |
| M3: Appeals | [references/punishment-appeal-guide__appeal-materials-and-channels.md](references/punishment-appeal-guide__appeal-materials-and-channels.md) | principal-authorization branch, material lists, channels, timeliness, fixed talks |
| M4: Handoff | [references/punishment-appeal-guide__handoff-map.md](references/punishment-appeal-guide__handoff-map.md) | neighbor-area recognition and boundary sentences |
| M5: RAM | [references/ram-policies.md](references/ram-policies.md) | minimal read-only policy for the exact four actions |

## Workflow

### Step 1: Intake and scope confirmation

Collect: the ORIGINAL notice text (console message / SMS / email), the
punished object (account / instance / URL / order), instance IDs or public
IP, region, domain/URL if involved. Confirm read-only scope per User
Confirmation. If no notice exists and the claim is only "blocked", still
proceed — Step 2 is exactly what disproves or corroborates such claims.

### Step 2: Run the entry script

```bash
cd $SKILL_DIR && python3 scripts/areas/punishment_appeal_guide/punishment_appeal_guide.py \
  --region-id <region> [--instance-ids <ids> | --public-ip <ip>] \
  [--symptom <hint>] [--notice-keyword "<notice wording>"] \
  [--check-port <n> --check-protocol <proto>] [--json]
```

The script runs Step 1's identity check plus the four whitelisted reads,
classifies the tier deterministically, and emits the triage report. Per
query failures degrade to `[WARN]` lines and a `STATUS: DEGRADED` closing;
the report is still produced.

### Step 3: Interpret the classification relay

Read the report's Classification section: tier label and every rationale
line (each names its source: notice cue vs API field). If the evidence is
`no instance matched`, first suspect region/account ownership — punishment
records are account-scoped; ask which account the resource lives in before
drawing any conclusion.

### Step 4: Deliver guidance (materials, channel, timeliness)

Relay the script's Guidance block: remediation checklist pointer (snapshot
first, always), the material checklist for the tier, the principal-
authorization precondition, the channel wording (entry from the notice, or
manual ticket when no self-service path exists or the link is broken), the
timeliness (typically same day, within 3 calendar days; automatic release
timestamps cannot be advanced; no expedite guarantee), and the tier's
fixed talks verbatim. For judicial / law-enforcement requests deliver the
fixed talk only — run no queries for disclosure demands.

### Step 5: Closing verification

After the platform confirms an unblock, re-run the script with the same
identifiers and show the status back at Running as closing evidence. A
case is closed only with that verification or an explicit customer
decision (for example choosing to keep the shutdown).

### Step 6: Out-of-scope closure

Anything matching the handoff map gets the boundary sentence plus the
target area, with no further expansion here. Refunds, legal cooperation
and expedite demands end in the fixed human-channel sentences.

## Output Contract

The final answer MUST:

1. Start with the script's classification and evidence relay (real
   statuses, real lock reasons, real rule counts — nothing inferred).
2. Declare every auto-filled parameter (symptom hint, account label,
   region defaults) explicitly.
3. State the boundary verbatim: punishment records, content detail and
   appeal progress are not visible to this skill.
4. End with the script's `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION`
   lines, faithfully transcribed. On `DEGRADED` always carry the fallback:
   original notice text from the customer plus manual ticket.
5. Keep every suggestion as manual guidance; never emit an executable
   change command.

## Error Handling

| Condition | Report behavior | Agent behavior |
|-----------|-----------------|----------------|
| `NoPermission` / `ImplicitDeny` from a query | `[WARN]` + degraded list | name the missing action, point to [references/ram-policies.md](references/ram-policies.md), never broaden to other APIs |
| Credential chain unavailable | identity degraded / `STATUS: FAIL` | guide the customer through `aliyun sts get-caller-identity`; never request AK/SK values |
| `InvalidRegionId` / no matching instance | degraded, ownership rationale | ask for the correct region / owning account (cross-account confusion is the documented ticket pattern) |
| `Throttling` / 5xx / timeout | retried inside `_cli.py`, then `[WARN]` | relay the degradation; do not re-issue manual CLI calls |
| Notice-only tiers (transaction / account / judicial) | cloud facts reported as "normal/not visible" side-evidence | run the guidance path; never promise review outcomes |

## Examples

**Example 1 — instance shut down after a notice**

> User: "My server was shut down after a violation notice, players cannot
> get in. How do I appeal?"

```bash
python3 scripts/areas/punishment_appeal_guide/punishment_appeal_guide.py --region-id cn-hangzhou \
  --instance-ids i-bp10exampleid0001 \
  --notice-keyword "illegal content, security management policy"
```

Relay the tier (instance or URL, per lock/status facts), the tampered-
content checklist with the snapshot-first rule, the content-appeal material
list with the principal-authorization precondition, and the same-day-to-3-
days timeliness with the no-expedite-guarantee talk.

**Example 2 — account frozen, pay-as-you-go still billing**

> User: "My account is frozen by risk control, I cannot open the console,
> and my pay-as-you-go ECS keeps charging."

```bash
python3 scripts/areas/punishment_appeal_guide/punishment_appeal_guide.py --region-id cn-hangzhou \
  --symptom account --notice-keyword "account frozen by risk control"
```

Deliver: release timestamp comes from the notice and cannot be advanced;
cost-reduction guidance (remote login then stop the instance, billing
caveat, official stop-an-instance document); manual appeal channel with the
account material list — all as customer-executed steps.

**Example 3 — "my IP is blocked" with no notice**

> User: "47.236.134.120 is blocked, everyone in the mainland says it is
> unreachable. Wait for the unblock or refund?"

```bash
python3 scripts/areas/punishment_appeal_guide/punishment_appeal_guide.py --region-id ap-southeast-1 \
  --public-ip 47.236.134.120
```

The script checks existence / Running / locks / SG rules; on all-normal it
classifies unverified and asks the fixed judgement-basis question; it does
not endorse the claim and does not touch refund (commercial handoff).

## Important Notes

- **What this skill cannot see, it says**: penalty records, violating
  content detail (privacy-restricted), appeal progress, account risk
  verdicts, supervisory blocks. The notice text is the anchor; when it is
  missing, the claim is unverified — not false.
- **URL blocked is not server closed**: the Running + no-lock combination
  is the classic ticket confusion; classify before alarming anyone.
- **Some things are not self-service**: account restrictions and several
  unblock types require manual verification with the full material set; a
  broken appeal link is itself a documented failure mode — fall back to a
  support ticket carrying the notice.
- **No outcome prediction, no expedite promise**: reviews decide; the skill
  prepares complete, correctly-authorized submissions only.
- **Read-only guarantee**: the shipped code only calls the whitelisted
  Describe* and identity queries; guest execution, snapshots and all other
  writes are excluded by design, so no write permission is declared
  anywhere in this package.
