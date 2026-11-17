---
name: alibabacloud-ecs-high-frequency-issues
area: billing-attribution-bill-check
description: |
  Read-only ECS cost attribution and bill check: traces every charge to
  product, billing item, region, resource ID, usage, price and
  payable/deducted amounts; explains charges after shutdown, undeducted
  packages and mismatched bill totals. Use when the customer asks where
  the ECS bill money went.
  Triggers: "why was I charged and I cannot tell what for", "charged after shutting down the instance", "savings stop mode still deducting", "public traffic fee is abnormally high", "resource package or savings plan not deducted", "coupon not applied to my bill", "bill total does not match the amount I owe", "where can I export monthly bill details".
  Do NOT use: snapshot create/delete or auto-snapshot policy operations ->
  alibabacloud-ebs-disk-snapshot-management; refunds, fee waivers, coupon
  issuance and renewal-price negotiation -> human commercial handling.
metadata:
  openclaw:
    requires:
      # No environment variable is required: the skill runs on the aliyun CLI
      # configuration file alone.
      env: []
      # Both binaries evidenced in the shipped code must be installed.
      bins: [aliyun, python3]
---

# ECS Billing Attribution & Bill Check

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Answer the four money questions this skill owns, in English or by mapping
Chinese customer symptoms onto them: (1) "what exactly is this charge" —
amount -> product -> billing item -> region -> resource -> usage -> price
-> payable/deducted; (2) "why does it still bill while stopped/idle" —
post-paid settlement timing, stop semantics, disks/snapshots that bill
regardless; (3) "why did my package / savings plan / coupon not deduct" —
deterministic deduction rules; (4) "is the bill number right and where do
I see it" — multi-layer reconciliation, usage-vs-monitor cross-checks and
exact console entries.

## Data Flows and External Calls

- **Alibaba Cloud BSS billing OpenAPI — `business.aliyuncs.com`, HTTPS,
  API version `2017-12-14`.** The scripts never build HTTP requests or
  credentials themselves; they invoke the `aliyun` CLI as a subprocess
  (`aliyun bssopenapi <Action> --endpoint business.aliyuncs.com`) for five
  read-only actions: `QueryBillOverview`, `QueryBill`,
  `QueryInstanceBill`, `DescribeInstanceBill`, `QuerySettleBill`. Per call
  only the action name plus query parameters (billing cycle, product
  filter, page token) and the per-run `--user-agent` observability label
  are sent.
- **CloudMonitor — `metrics.<region>.aliyuncs.com`, read-only
  `DescribeMetricList`** (namespace + metric + instance dimensions + time
  window) for the bill-vs-monitor usage cross-check.
- **ECS — `ecs.<region>.aliyuncs.com`, read-only `DescribeInstances`**
  for instance charge type, stop mode and bandwidth billing mode.
- **STS — `sts.aliyuncs.com`, one read-only
  `aliyun sts get-caller-identity`** per run as the identity pre-check.
- Authentication is attached by the aliyun CLI from its own default
  credential chain. The scripts never read, print, store or forward any
  AccessKey, SecretKey or STS token; credential material appearing in CLI
  error text is masked before any output (see Observability).

## ABSOLUTE RULES (top-priority constraints)

1. **READ-ONLY (ABSOLUTE PROHIBITION)**: never generate, write or execute
   ANY cloud-mutating API or command — every verb family of
   `Modify*` / `Create*` / `Delete*` / `Release*` / `Reset*` / `Attach*` /
   `Detach*` / `Reboot*` / `Start*` / `Stop*` and any other change —
   against any Alibaba Cloud product, including "for the user to run
   manually" commands, and including commands inside a guest OS (this
   skill performs no guest execution at all).
2. **API WHITELIST**: the ONLY permitted API operations in the entire
   session are `bssopenapi QueryBillOverview`, `bssopenapi QueryBill`,
   `bssopenapi QueryInstanceBill`, `bssopenapi DescribeInstanceBill`,
   `bssopenapi QuerySettleBill`, `cms DescribeMetricList`, `ecs
   DescribeInstances`, `sts GetCallerIdentity`. If a diagnosis seems to
   need any other operation, it is OUT OF SCOPE: say so and route per
   `references/billing-attribution-bill-check__handoff-map.md`.
3. **CREDENTIALS (SA-2.12)**: rely on the default credential chain only;
   never handle keys explicitly, never ask the user for them.
4. **NO FABRICATION**: every amount, usage, resource ID and date in the
   answer MUST trace to script output or the embedded `references/`
   knowledge; never invent or mentally re-compute numbers. State the
   timing caliber with any figure.
5. **EXECUTION RULE FOR ERRORS**: API errors are final for that step —
   the scripts log `[WARN]`, degrade, and continue; never re-issue a
   failed call manually or invent a workaround.
6. **SCOPE BOUNDARY**: this skill attributes money and reconciles bills;
   it does not promise fee cancellation/waivers/refunds (fixed wording:
   accrued fees cannot be cancelled through support), never performs
   purchases or mode switches, and hands off traffic-destination
   forensics (historical traffic is not traceable cloud-side), snapshot
   operations, operation-provenance questions and other products'
   internal billing rules per `references/billing-attribution-bill-check__handoff-map.md`.

## Trigger Conditions

- "why was I charged and I cannot tell what for" / "an unknown amount hit
  my balance"
- "charged after shutting down the instance" / "savings stop mode still
  deducting"
- "public traffic fee is abnormally high" / month-over-month bill surge
- "resource package or savings plan not deducted" / "coupon not applied
  to my bill"
- "bill total does not match the amount I owe" / export vs console gap
- "where can I export monthly bill details" / "the detail page is empty"

## Execution Principle

The agent MUST run all cloud queries through the single entry script
`scripts/areas/billing_attribution_bill_check/query_ecs_bill.py`; it MUST NOT assemble `aliyun` commands by
itself. The script prints a human report by default and machine JSON with
`--json`, and ends every run with `STATUS: OK|DEGRADED|FAIL` and
`NEXT_ACTION: ...`. Those two lines are the machine channel: report their meaning
faithfully to the customer, and keep the tokens themselves out of the reply
(`SKILL.md` 3h). Identity
pre-check alone may also run via `scripts/areas/billing_attribution_bill_check/sts_token.py`.

## Observability

Each script run generates one random **32-hex session-id** (lowercase,
`uuid4().hex`) and attaches it to **every** cloud API call of that run as
a User-Agent template:

```
AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
```

implemented as the CLI argument `--user-agent` in the shared layer
(`scripts/areas/billing_attribution_bill_check/_cli.py`). The session-id is a run identifier, not an account
identifier. All CLI error text is credential-masked (AccessKey / token /
signature values replaced by `***`) before it can surface in any
`[WARN]` line or report field.

## Prerequisites and Authentication

1. The `aliyun` CLI installed, with credentials available through its default chain, and
   the read-only actions of `references/ram-policies.md` granted to the
   credential (bill queries need the `bss:` / `bssapi:` billing read
   actions; see the RAM mapping there).
2. `python3` (standard library only; see `scripts/requirements.txt`).
3. Optional credential profile name passed to the scripts with
   `--profile <name>`.

## User Confirmation

This skill performs only cloud reads and needs no per-call confirmation.
Confirmation discipline applies at the SCOPE BOUNDARY: requests to
convert billing modes, buy/unsubscribe packages, release/delete resources
or settle/waive fees MUST NOT be executed or drafted as commands — answer
with the manual guidance in `references/billing-attribution-bill-check__stop-billing-guide.md` /
`references/billing-attribution-bill-check__handoff-map.md` plus the irreversibility warning (data is
unrecoverable; back up before any deletion or release).

## Input Parameters

| Parameter | Required | Notes |
|---|---|---|
| `--billing-cycle YYYY-MM` | yes (auto-derivable) | the settlement cycle; a deduction at the start of month N maps to cycle N-1 |
| `--charge-date YYYY-MM-DD` | no | balance-deduction day; auto-maps to the previous cycle and declares the mapping |
| `--months N` | no (1..12) | consecutive cycles for month-over-month surge detection |
| `--instance-id` / `--instance-ids` | sometimes | instance / disk / snapshot resource ids as they appear in the bill |
| `--region` | for ecs/cms reads | instance region; default declared in output when auto-filled |
| `--product-code` | no | BSS product filter (e.g. `ecs`, `snapshot`) |
| `--topic` / `--list-topics` | no | embedded FAQ knowledge, no cloud call |
| `--json` | no | machine output incl. raw rows and `evidence_pack` when generated |

Every auto-filled parameter (billing cycle, region, UID) is declared in
the script output and MUST be declared to the user in the answer.

## Orchestration and Modules

Follow the Diagnostic Flow; load a module only when the flow reaches it.
Modules and their owners:

| Module | File | Owner | Purpose |
|---|---|---|---|
| M1 Billing items | `references/billing-attribution-bill-check__billing-items.md` | script output reader | item dictionary, amount-field calibers, subscription-vs-postpaid nuances |
| M2 Console paths | `references/billing-attribution-bill-check__bill-console-paths.md` | "where do I look" answers | exact entries, filters and page traps |
| M3 Timing & caliber | `references/billing-attribution-bill-check__billing-timing-and-caliber.md` | every number statement | finalization time, 24h/48h lags, amount-caliber taxonomy |
| M4 Deduction matrix | `references/billing-attribution-bill-check__deduction-matrix.md` | package/coupon questions | deduction rules R1..R8 and the degraded-confidence protocol |
| M5 Stop-billing guide | `references/billing-attribution-bill-check__stop-billing-guide.md` | "how do I stop this" | manual steps + irreversible-data warnings per item |
| M6 Handoff map | `references/billing-attribution-bill-check__handoff-map.md` | boundary cases | out-of-scope routing + evidence-pack contents + fixed wordings |
| M7 RAM policy | `references/ram-policies.md` | permission failures | minimal read-only action mapping (API name != RAM name) |

## Diagnostic Flow

### Step 1: Identity pre-check + cycle pinning (C3)

```bash
cd $SKILL_DIR && python3 scripts/areas/billing_attribution_bill_check/sts_token.py
```

Confirm the UID matches the account in question. Then pin the cycle:
customer-stated `YYYY-MM`, else `--charge-date` mapping (deduction on the
1st-3rd = previous cycle's post-paid settlement), else the script's
auto-default (previous cycle, declared as auto-filled). A renewal payment
is an ORDER, not a bill row — order lookups go to the order-list entry
(M2).

### Step 2: Full attribution (C1/C2/C9)

```bash
cd $SKILL_DIR && python3 scripts/areas/billing_attribution_bill_check/query_ecs_bill.py --billing-cycle <YYYY-MM> [--months 2] [--json]
```

Relay the product -> item -> region -> resource tree with amounts. Apply
M1 reading rules: read the BILLING ITEM, not just the product label;
flag Subscription-with-post-paid-traffic rows; run the printed
usage x price recomputation before asserting consistency.

### Step 3: Stop / idle questions (C4/C6)

When the customer says "it was stopped": run
`--instance-info --instance-id <i-...> --region <r>` and combine
`InstanceChargeType` / `StoppedMode` / `InternetChargeType` with the Step 2
rows still in fee for that period; answer with the savings-stop boundary
list and, if asked how to stop billing, M5 guidance (manual only).

### Step 4: Traffic surge drill-down (C5/C6)

```bash
cd $SKILL_DIR && python3 scripts/areas/billing_attribution_bill_check/query_ecs_bill.py --daily --billing-cycle <YYYY-MM> --days 7 --instance-id <i-...>
cd $SKILL_DIR && python3 scripts/areas/billing_attribution_bill_check/query_ecs_bill.py --traffic-check --billing-cycle <YYYY-MM> --instance-id <i-...> --region <r>
```

Present the bill amount, the usage x price math, the monitor cross-check
and the 24h/48h timing statement together. Traffic-destination questions
route to M6 immediately — this skill does not trace destinations.

### Step 5: Deduction disputes (C7/C8, degraded mode)

```bash
cd $SKILL_DIR && python3 scripts/areas/billing_attribution_bill_check/query_ecs_bill.py --deduction-report --billing-cycle <YYYY-MM>
```

Pair the zero-deduction rows with the customer-stated package facts and
quote the matching M4 reason (R1..R8) with explicit degraded confidence.
"Correctly associated yet still billed" -> evidence pack, ticket, done.

### Step 6: Multi-layer reconciliation (C9)

```bash
cd $SKILL_DIR && python3 scripts/areas/billing_attribution_bill_check/query_ecs_bill.py --reconcile --billing-cycle <YYYY-MM>
```

Relay L1 overview vs L2 bill vs L3 settlement with the M3 caliber table.
Explain each remaining delta with the caliber + timing statements; never
declare the bill "wrong" or "right" beyond what the layers show.

### Step 7: Output and handoffs (C10/C11)

Compose the answer per Final Answer Contract: amounts, flags, console
entries (M2), stop-billing guidance if relevant (M5), and an explicit
handoff list for anything beyond the boundary (M6).

## Important Notes

- **Timing is part of every number**: final bill at 12:00 on the 3rd of
  the next month; detail lags ~24h; instance fields lag ~48h; current
  month is provisional and not a reconciliation basis.
- Pay-as-you-go settles monthly against the balance at the start of the
  following month; align charge days with cycles before calling anything
  "unknown".
- Stopping never equals free: normal stop keeps the spec fee; savings
  stop keeps disks/snapshots/EIP/traffic items; only (manual) removal ends
  the chain — always attach the data-loss warning.
- A Subscription instance legitimately carries post-paid rows (traffic,
  snapshots, extra disks); a product label on the bill is coarser than
  the billing item (SurplusCredit lives under the ECS product name).
- Deduction inventory (packages/coupons) has no read API in this skill:
  say which facts are inferred (bill triple) and which are customer
  statements; confidence degraded, medium at best.
- Never promise fee cancellation, waivers or discounts; route commercial
  asks to a human manager.
- For "I want to see/export it myself", give M2 entries with exact filter
  parameters instead of re-running queries.

## Examples

**Example 1 — unknown charge**

User: "On August 1st my balance dropped about 165 yuan and I cannot tell
what it was for."

Actions: Step 1 with `--charge-date 2026-08-01` (maps to cycle 2026-07,
declared), Step 2
`python3 scripts/areas/billing_attribution_bill_check/query_ecs_bill.py --billing-cycle 2026-07 --json`, then
present the July item tree, the monthly-settlement statement, and the
order-vs-bill check for a renewal charge in the order list (M2).

**Example 2 — traffic bill surge**

User: "My July ECS bill jumped to 1300 yuan although my site traffic did
not change; instance i-2zeexamplee60da4174c, cn-beijing."

Actions: Step 2 attribution (dominant row = outbound traffic), Step 4
`--daily` then `--traffic-check --instance-id i-2zeexamplee60da4174c
--region cn-beijing`; relay usage x 0.8-per-GB math from the row fields,
the monitor curve summary and the timing caliber; offer fixed-bandwidth /
traffic-plan options as manual paths (M5); route "who accessed me" to M6.

**Example 3 — package not deducting**

User: "I bought a 389 yuan compute plan, the instance is associated, yet
the instance / traffic / system-disk fees are still being paid in cash."

Actions: Step 5 deduction report for the cycle; match bill triple
(payable>0, deductions=0) against R6 (entry-created + no reconfiguration)
with the customer-stated facts; if the customer insists the association
is correct, stop, generate the evidence pack (`--json` output) and hand
off per M6 — do not concede or deny a system fault.

## Available Scripts

| Script | Purpose | Usage |
|---|---|---|
| `scripts/areas/billing_attribution_bill_check/query_ecs_bill.py` | single entry: attribution / overview / monthly-total / settlement / reconcile / daily / traffic-check / deduction-report / instance-info / FAQ / timing (read-only) | `python3 scripts/areas/billing_attribution_bill_check/query_ecs_bill.py --billing-cycle 2026-07 [--overview|--settlement|--reconcile|--traffic-check] [filters] [--json]` |
| `scripts/areas/billing_attribution_bill_check/sts_token.py` | identity pre-check + UID derivation | `python3 scripts/areas/billing_attribution_bill_check/sts_token.py` |
| `scripts/areas/billing_attribution_bill_check/_cli.py` | shared CLI layer (UA session-id, retries, masking, pagination) — internal | imported only |
| `scripts/areas/billing_attribution_bill_check/_constants.py` | embedded knowledge (items, rules, timings, console paths, FAQ) | imported only |

## Error Handling

| Symptom | Cause | Action |
|---|---|---|
| `NoPermission` / `ImplicitDeny` from a bill action | missing RAM action in `references/ram-policies.md` | report WHICH action + minimal policy snippet; degrade, do not retry other credentials |
| STS identity call fails | credential chain not configured | guide them to verify the default credential chain with `aliyun sts get-caller-identity`; never ask for keys |
| `InvalidParameter` / cycle rejected | wrong `YYYY-MM` or out-of-range history | relay the format rule, ask the customer for the cycle; do not guess years |
| empty result for a cycle | zero usage -> no bill rows exist | state it as a valid finding, then check the cycle mapping |
| monitor returns no datapoints | wrong/renamed metric or retention shorter than the cycle | keep the bill-side conclusion; state degraded for the cross-check; suggest the console metric list |
| `Throttling.User` | rate limit | already retried inside the script; if still failing, slow down and rerun |

## Final Answer Contract

The final answer MUST:
1. relay the script `Summary` and findings faithfully, and carry the meaning of
   `STATUS` (`OK` / `DEGRADED` / `FAIL`) and `NEXT_ACTION` into the wording - the two
   tokens stay on the machine channel;
2. quote real numbers and billing-item names from script output only
   (full decimals preserved);
3. declare every auto-filled parameter (cycle, charge-date mapping,
   region, UID);
4. state the timing caliber alongside any provisional figure;
5. present stop-billing / console guidance as manual steps with
   data-loss warnings, and deduction verdicts with their degraded
   confidence;
6. end out-of-boundary requests with the M6 handoff sentence and evidence
   pack reference instead of an action.
