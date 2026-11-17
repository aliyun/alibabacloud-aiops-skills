---
name: alibabacloud-ecs-high-frequency-issues
area: spec-change-purchase
description: |
  Query-only feasibility check for ECS spec change and purchase: selectable target specs, stock by zone, quota and stock error triage, estimated change cost, and effectiveness conditions. Changes are executed by the customer in the console.
  Use when an ECS spec change or purchase fails, is blocked, or does not apply. Triggers: "upgrade instance type", "downgrade instance spec", "change not taking effect after restart", "cannot purchase or create instance", "OperationDenied.NoStock", "config sold out, insufficient stock", "vCPU quota limit exceeded", "StoragePerformanceReachLimit".
  Do NOT use: slow or crashing server root cause -> alibabacloud-ecs-diagnose; disk resized but unseen in OS -> area:disk-expand-diagnosis; disk IOPS slow -> area:resource-bottleneck; instance stuck start/stop -> area:instance-state-diagnosis.
metadata:
  openclaw:
    requires:
      env: []
      bins: [aliyun, python3]
---

# ECS Spec Change & Purchase Feasibility

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Answers five questions for Alibaba Cloud ECS instance changes and purchases,
from live cloud readings plus the rule tables in `references/`:

1. **Which target specs are actually selectable** for this instance (the
   change set, which is NOT the same list as the buy page)?
2. **Is there stock** for a type, zone or region right now?
3. **What does the error or quota wording really mean** (inventory vs
   refund-vCPU quota vs overdue balance vs the customer's own program)?
4. **What will it approximately cost / refund** (estimate only - the exact
   account-discounted number is not computable by any query)?
5. **What makes a change take effect** (restart needed for specs; bandwidth
   changes are immediate; per-order effective times).

**This skill changes nothing.** It runs query-only cloud calls
(`Describe*` / `Get*`) and then guides. The customer personally performs
every change in the ECS console; submissions, approvals, refunds and
on-machine work go to a human (`references/spec-change-purchase__handoff-map.md`). This matches
the reviewed support practice: agents explain and point, the customer
clicks.

## Trigger Conditions

Trigger phrasing lives in the frontmatter `description` (symptom wording
from customer tickets translated to English, plus the two registered
customer-visible codes `OperationDenied.NoStock` and
`StoragePerformanceReachLimit`). Typical openings:

- "I want to downgrade my server from 16G to 8G memory" / "upgrade to 4
  cores" / "change the instance spec"
- "the target spec shows sold out on the change page" / "cannot buy, it
  says OperationDenied.NoStock"
- "I paid for the upgrade but it still shows the old CPU and memory"
- "it says my quota is insufficient but I never bought anything"
- "bandwidth change - does it need a restart?"

## What This Skill Never Does

- Never calls a mutating or executing API, never runs anything inside an
  instance, never submits orders / quota applications / refunds.
- Never diagnoses "why is it slow / crashing / under attack": it answers
  the change-feasibility half and routes the root-cause half to
  `alibabacloud-ecs-diagnose` (see `references/spec-change-purchase__handoff-map.md`).
- Never inspects disk capacity inside the guest (`area:disk-expand-diagnosis`
  covers that), disk IO performance (`area:resource-bottleneck`), or instance
  start/stop state machines (`area:instance-state-diagnosis`).
- Never states an exact refund, a quota value it did not read, an approval
  time, or a moment when stock returns. Order-side questions (paid but not
  applied, auto refund) are registered and handed to a human - this tier
  has no order-query API.

**Routing is decided before any lookup.** When the opening signal belongs to
another capability (slow disk IO -> `area:resource-bottleneck`; a
resized disk the OS cannot see -> `area:disk-expand-diagnosis`; an instance
stuck starting/stopping -> `area:instance-state-diagnosis`; general slowness or
crashing -> `alibabacloud-ecs-diagnose`), state the handoff and stop there. Do
not list regions, hunt for an instance id the customer never gave, or query
stock/orders first: a boundary answer needs no cloud read, and wandering for a
locator burns the turn budget without adding evidence.

## Data Flows and External Calls

The shipped code contacts ONLY the Alibaba Cloud OpenAPI endpoints that the
`aliyun` CLI resolves for the four declared products (see
`related_apis.yaml`): `ecs` (regional endpoints via `--region`),
`bssopenapi` via `business.aliyuncs.com`, and `sts` via `sts.aliyuncs.com`,
all HTTPS. Each outbound request is one whitelisted query action with an
explicit parameter list (never built from a shell string), carries the
observability user-agent
`AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/{session-id} skill-version/<skill-version>`
(session-id = a random 32-char hex, generated once per run) and a hard
60-second timeout. Only API request parameters and default-chain
credentials reach the network; nothing else is uploaded. Every CLI failure
text passes through credential masking before it can appear in a report
line. There is no HTTP fallback path: if the `aliyun` CLI is missing, the
scripts stop and ask the user to install it.

## Execution Principle (entry-script only)

All cloud access MUST go through `python3 scripts/areas/spec_change_purchase/assess_spec_change.py`
(and `scripts/areas/spec_change_purchase/sts_token.py` for a bare identity check). Do NOT hand-assemble
`aliyun` CLI commands, do NOT call any API outside the whitelist below, do
NOT write helper scripts. If the entry script fails, report its error and
`STATUS` honestly - never fake a reading or substitute a guess.

## API Whitelist (hard constraint)

The scripts may invoke ONLY these eight query actions, exactly as declared
in `related_apis.yaml` and `references/ram-policies.md`:

`ecs: DescribeInstances, DescribeInstanceAttribute, DescribeResourcesModification, DescribeAvailableResource, DescribeInstanceTypes`
`bssopenapi: DescribePricingModule, GetSubscriptionPrice`
`sts: GetCallerIdentity`

`DescribeResourcesModification` is invoked with query semantics only: it
returns what COULD be changed and the stock states; it changes nothing.
`GetSubscriptionPrice` is an inquiry; its RAM action name is
`bss:DescribePrice` (API name and RAM name deliberately differ).

**ABSOLUTE PROHIBITION** (no exceptions, even if the customer asks): never
call or generate any mutating API (any `Create*` / `Modify*` / `Delete*` /
`Release*` / `Reset*` / `Replace*` / `Attach*` / `Detach*` / `Start*` /
`Stop*` / `Reboot*` action, and no snapshot-creation call), never execute
anything on the customer's instance, and never emit a mutating command line
for the customer to run - change steps are CONSOLE CLICK GUIDANCE only,
delivered together with the mandatory notices below.

## Credentials and Authentication

Default credential chain only (environment or `~/.aliyun/config.json`,
managed with `aliyun sts get-caller-identity`). The scripts never ask for, read, print,
cache or forward AccessKey / SecretKey / token values, and never write a
credential cache. On `NoPermission` / `ImplicitDeny`: name the missing
action from `references/ram-policies.md`, give the minimal policy snippet,
stop that line, and keep the rest of the report.

## User Confirmation (inform-first gate for customer-executed actions)

- Before the first cloud query, restate the scope in one sentence (which
  instance / region, which five-question line) and proceed; queries run
  without per-call confirmation because none of them can change anything.
- Before ANY guidance for a customer-executed change, the reply MUST
  first output the mandatory notice bundle (five change notices, the three
  effectiveness statements, the snapshot advice - `references/spec-change-purchase__change-rules.md`)
  and, when applicable, the matching irreversibility notice (stop-required
  downgrade; restart data-loss window; cross-zone move changes the private
  IP; bandwidth-to-pay-by-traffic plus IP-to-EIP conversion can never be
  reversed). Then state plainly: "you execute this in the console
  yourself; this assistant will not perform it" - and wait for the
  customer to act.
- Price and refund figures are relayed ONLY together with the estimate
  disclaimer (console page value at order time is authoritative; read the
  expected refund without confirming the order).
- Any unverified numeric (caps, fees) is deferred to "the value shown on
  the console page / official doc" - the reviewed agent-quoted numbers are
  pending documentation verification and must not be restated as facts.

## Prerequisites

- Python 3.9+ (standard library only, see `scripts/requirements.txt`).
- Alibaba Cloud CLI 3.x (`aliyun`) installed and configured; commands use
  plugin mode where applicable (`aliyun sts get-caller-identity`).
- The RAM actions in `references/ram-policies.md` attached to the active
  credential.

## Observability

Each run generates one 32-char lowercase hex session-id (`uuid4().hex`) at
first use and appends it to the User-Agent of EVERY CLI call. UA template:
`AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, instantiated for this
skill as:

`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/{session-id} skill-version/<skill-version>`

The session-id is printed once to stderr; reports carry the per-run label
only - never account credentials.

## Orchestration and Decision Flow

Entry script `scripts/areas/spec_change_purchase/assess_spec_change.py`; the scenario lines are NOT
mutually exclusive - one ticket often crosses two lines (e.g. a paid
downgrade that did not apply AND changed bandwidth).

```text
S0 intake      -> split the change object (spec vs bandwidth vs billing
                  conversion vs disk), keep any verbatim error text
C1 identity    -> scripts/areas/spec_change_purchase/sts_token.py logic (GetCallerIdentity) first
S2 locate      -> DescribeInstances + DescribeInstanceAttribute:
                  current spec, status, billing type, region/zone,
                  public IP type, bandwidth (an ecs.* answer to "which
                  instance?" is corrected automatically)
S3 routing     -> spec -> S4; bandwidth -> immediate-effect rules;
                  disk capacity -> handoff; other product -> boundary
S4 change set  -> DescribeResourcesModification: target in set? state?
                  not in set -> explain change-set vs buy-page, offer
                  substitutes; if customer prefers new purchase ->
                  IP-change warning first
S5 inventory   -> DescribeAvailableResource per zone (+ DescribeInstanceTypes
                  same-tier substitutes); every substitution PROVEN by a
                  reading; stock is instantaneous, release unpredictable
S6 estimate    -> DescribePricingModule + GetSubscriptionPrice -> ESTIMATE
                  + five notices + snapshot advice; exact refund is guided
                  to the console page, never stated
S7 purchase    -> error text -> references/spec-change-purchase__error-codes.md table ->
                  inventory line / quota line / billing-first check /
                  risk-control handoff
S8 effectiveness-> inventory spec vs claimed target: applied-awaiting-
                  restart vs not-applied vs order-side (human handoff);
                  guest-OS symptoms -> handoff after stating the spec
S9 quota       -> references/spec-change-purchase__quota-triage.md order: source attribution ->
                  balance check -> quota item parsing -> application
                  material -> human for submission/approval
```

## Execution Flow

1. Map the customer's message to a line above; collect what is missing
   (instance id, region, target spec, verbatim error text) - ask once.
2. If any error text exists, run the triage with it FIRST (offline).
3. Run ONE entry command combining the needed flags; relay findings.
4. Always append the mandatory notice bundle when a change is discussed,
   plus the matching irreversibility notice.
5. Close per the Final Answer Contract: `STATUS` (`OK` / `DEGRADED` /
   `FAIL`), every auto-filled parameter declared (e.g. a defaulted
   region), named gaps instead of invented values, and the console entry
   the customer uses to act.

Quick start (one command):

```bash
python3 scripts/areas/spec_change_purchase/assess_spec_change.py --region-id cn-hangzhou \
  --instance-id i-bp1f0xxxxxx --target-type ecs.u1-c1m2.xlarge \
  --direction downgrade --list-targets --estimate
```

## Available Scripts

| Script | Purpose |
|---|---|
| `scripts/areas/spec_change_purchase/assess_spec_change.py` | Single entry: identity gate, instance facts, change set + per-target stock, region inventory + substitutes, estimate line, effectiveness check, error triage, guidance bundle |
| `scripts/areas/spec_change_purchase/sts_token.py` | Standalone identity pre-check (query-only) |
| `scripts/areas/spec_change_purchase/_cli.py` | Shared CLI layer: whitelist-only invocation, UA/session-id, timeout, retry on transient errors, credential masking |
| `scripts/areas/spec_change_purchase/_constants.py` | Endpoints, limits, and the embedded notice / triage rule data (mirrors `references/`) |
| `scripts/requirements.txt` | Runtime dependencies (standard library only) |

## Input Parameters

| Flag | When required | Notes |
|---|---|---|
| `--instance-id` | any change / effectiveness line | `i-...`; a `ecs.*` value is corrected as a spec name, not an instance id |
| `--region-id` | instance line optional (defaults are DECLARED), inventory line needed | read from the instance response when possible |
| `--target-type` | target named by the customer | `ecs.*`; membership is judged against the change set, not memory |
| `--direction` | when upgrade vs downgrade is known | drives the change-set filter and the stop-required notice |
| `--charge-type` `--zone-id` `--cores` `--memory` | purchase / substitute scan | narrow the inventory evidence |
| `--error-string` | any failure wording | ALWAYS the verbatim text from the customer |
| `--change-object` | guidance-only routes | spec / bandwidth / billing-conversion / disk / other-product |
| `--list-targets` `--check-inventory` `--verify-effective` `--estimate` `--json` | line switches | combine freely |

## Error Handling

| Situation (Code) | Skill behavior |
|---|---|
| `NoPermission` / `ImplicitDeny` on a query action | name the action, show the minimal snippet from `references/ram-policies.md`, mark the report `DEGRADED` |
| `InvalidParameter` | fix the single flagged parameter, re-issue once; repeated failure = record and degrade |
| `Throttling` | handled inside `_cli.py` (linear backoff, 3 attempts max) |
| CLI timeout / connection error | 3 attempts max (each call hard-capped at 60 s), then `DEGRADED` with the console self-check fallback |
| Customer cannot provide error text | do NOT wait for a screenshot: run the query lines first and report the readings (`T-27532B97` pattern) |
| Unknown error string | keep it verbatim, collect region / zone / ids, route per `references/spec-change-purchase__error-codes.md` red lines |

## Important Notes

- Two registered customer-visible codes only (`OperationDenied.NoStock`,
  `StoragePerformanceReachLimit`); every other text stays a ticket-observed
  string. `StoragePerformanceReachLimit` has no verified scenario in this
  tier's evidence - do not improvise its explanation; disk-IO symptoms
  route out.
- "Auto-refunded change order = stock shortage" is an UNVERIFIED human
  guess in the evidence; phrase it as a hypothesis only.
- Quota values and application states are NOT queryable from this tier's
  contract - work from verbatim errors plus console screenshots the
  customer provides.
- The snapshot step is advice plus a billing reminder; the skill never
  creates it.
- CloudMonitor-based utilization pre-checks are not an automated capability
  of this skill; ask the customer to eyeball CPU/memory watermarks before
  paying for a change (the reviewed case `T-D35ABA20` proved the "needs
  upgrade" assumption wrong).

## Examples

Prompt: "I paid to downgrade to 8G but my instance still shows 16G."

```bash
python3 scripts/areas/spec_change_purchase/assess_spec_change.py --region-id cn-hangzhou --instance-id i-bp1f0xxxxxx --target-type ecs.u1-c1m2.xlarge --verify-effective
```

Relay the verdict, the three effectiveness statements, the restart data-loss
risk, the snapshot advice; if the platform spec differs from the paid order,
record the order number and hand off.

Prompt: "ECS quota insufficient: Your available quota is insufficient.
I never bought a server before."

```bash
python3 scripts/areas/spec_change_purchase/assess_spec_change.py --error-string "Your available quota is insufficient."
```

Relay the billing-first order (overdue balance check in the Billing
Management console), then the quota self-application material - the skill
never submits anything.

Prompt: "Downgrade page shows my target sold out, buy page has it."

```bash
python3 scripts/areas/spec_change_purchase/assess_spec_change.py --region-id cn-hangzhou --instance-id i-bp1f0xxxxxx --target-type ecs.u1-c1m2.xlarge --list-targets --check-inventory --cores 4 --memory 8
```

Show change-set membership + per-zone stock + proven same-tier substitutes,
state the stock caveat verbatim, and reserve / business coordination goes
to a human.

## Final Answer Contract

1. Relay the script's findings and its `STATUS` / `NEXT_ACTION` verbatim
   where possible; quote only real returned values (specs, states,
   bracketed quota numbers, estimate fields).
2. Declare every auto-filled parameter (defaulted region, merged
   attributes) and every degraded line (which action, which missing RAM
   point if `NoPermission` / `ImplicitDeny`).
3. Wherever a change or purchase is discussed, the reply MUST include the
   mandatory notice bundle, the snapshot advice, and for prices the
   estimate disclaimer - no omitted notices, no restated agent-quoted
   numbers, no help links beyond `references/spec-change-purchase__help-docs.md`.
4. Close with what the CUSTOMER does next in the console, or the named
   handoff from `references/spec-change-purchase__handoff-map.md`; never claim anything was
   changed, submitted, reserved or approved.

## Module Index

| File | Content |
|---|---|
| `references/ram-policies.md` | exact query actions to grant; API-name vs RAM-name divergence; `NoPermission` / `ImplicitDeny` remediation |
| `references/spec-change-purchase__error-codes.md` | two-level code/string table with verbatim texts, ticket IDs, red lines |
| `references/spec-change-purchase__change-rules.md` | five notices, effectiveness statements, snapshot advice, irreversibility texts, price wording |
| `references/spec-change-purchase__quota-triage.md` | source attribution, billing-first order, refund-vCPU parsing, application material |
| `references/spec-change-purchase__inventory-fallback.md` | stock ladder (re-check, substitute, zone/region, wait), reservation boundary |
| `references/spec-change-purchase__handoff-map.md` | human-only list, sibling-skill routing, out-of-product false positives |
| `references/spec-change-purchase__help-docs.md` | official-document clues pending verification; console entry points safe to output |
