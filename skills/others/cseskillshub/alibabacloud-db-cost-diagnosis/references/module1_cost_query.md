# Module 1: Bill & Cost Trend Query Orchestration

Orchestration guide for querying database instance bills and account-level DB
cost trends. Every command and API reference in this document matches the
scripts under `scripts/` exactly.

## Scope

This module covers three read-only workflows:

1. **Caller identity verification** -- confirm who the current credential
   session is and derive the account UID.
2. **Single-instance bill query** -- per-billing-item cost breakdown of one
   database instance for one billing cycle.
3. **Account-level cost trend** -- monthly cost per DB product over N months,
   with automatic anomaly detection.

## API contract

The full API surface of this skill is exactly three read-only APIs. Nothing
else is called, and no wildcard actions are used anywhere.

| RAM Action | API Version | Endpoint | Used by |
|---|---|---|---|
| `sts:GetCallerIdentity` | 2015-04-01 | `sts.aliyuncs.com` | `scripts/sts_token.py` |
| `bssopenapi:DescribeInstanceBill` | 2017-12-14 | `business.aliyuncs.com` | `query_instance_bill.py`, `query_cost_trend.py` |
| `bssopenapi:DescribeSplitItemBill` | 2017-12-14 | `business.aliyuncs.com` | `query_instance_bill.py` (with `--split-item`) |

All BSS billing APIs are region-less and served by the central endpoint
`business.aliyuncs.com`. STS uses the central endpoint `sts.aliyuncs.com`.

## Prerequisites

- `aliyun` CLI installed and authenticated. Credentials are resolved
  exclusively by the aliyun CLI default credential chain (`aliyun configure`).
  The scripts never accept, read, or write any AccessKey / Secret.
- Python 3.7+.
- A credential with the minimal read-only policy documented in the RAM policy
  reference listed in the SKILL.md Module Index. If a call returns
  `NoPermission` / `AccessDenied`, ask the account owner to attach that policy;
  do not attempt any privilege escalation.

All scripts accept an optional `--profile <name>` flag to select a named
aliyun CLI credential profile.

## Step 1: Verify caller identity (always run first)

```bash
python3 scripts/sts_token.py            # human-readable
python3 scripts/sts_token.py --json     # structured output
```

Behavior:

- Calls STS `GetCallerIdentity` through the shared CLI layer.
- Derives the caller UID from the `AccountId` field; fails with a clear error
  if `AccountId` is missing.
- JSON output fields: `uid`, `account_id`, `arn`, `identity_type`.

Use the derived UID to confirm you are querying the intended account before
running any bill query.

## Step 2: Input validation and normalization

Before running any query, normalize the inputs:

1. **Billing cycle** (required for instance bill):
   - The scripts expect `YYYY-MM` (e.g. `2026-08`), not `YYYYMM`. Convert any
     user-provided format first.
   - Vague expressions ("last month", "recently") must be converted to a
     concrete `YYYY-MM` value before the query.
   - If the user provides no time range at all, default to the **current
     month**.
2. **Instance ID** (required for instance bill):
   - Accept any ID; product detection is done from the prefix (see below).
   - If the user gives no instance ID, run the account-level trend query
     first (Step 4) to discover which products/instances carry cost, then ask
     the user which instance to drill into.
3. **Months window** (required for trend):
   - `--months` must be at least 2 (the script rejects smaller values),
     because trend comparison needs at least two cycles. Default: 6.
4. **Granularity**: see Step 3.

## Step 3: Granularity selection (MONTHLY vs DAILY)

Both bill scripts accept `--granularity MONTHLY|DAILY` (default `MONTHLY`).

| Granularity | When to use | Cost of query |
|---|---|---|
| `MONTHLY` (default) | Almost every scenario: bill summary, multi-month trend, anomaly month detection | Fast, one row per billing item per month |
| `DAILY` | Only to drill down ONE month that already showed an anomaly at monthly level, or when the user explicitly asks for per-day figures. MUST be paired with `--billing-date YYYY-MM-DD` (BSS mandates `BillingDate` for daily bills, inside the billing cycle) | Heavy: one row per billing item per day; the trend script drills a single day, never the whole window |

Decision rule: if MONTHLY answers the question, never escalate to DAILY. When
MONTHLY reveals an anomaly but cannot localize it, re-run with DAILY plus
`--billing-date` scoped to the single anomalous day.

## Step 4: Query paths

### Path A: Single-instance bill detail

```bash
python3 scripts/query_instance_bill.py \
  --instance-id <ID> --billing-cycle <YYYY-MM> \
  [--split-item] [--granularity MONTHLY|DAILY] [--billing-date <YYYY-MM-DD>] \
  [--json] [--profile <name>]
```

API selection:

- Default: `bssopenapi:DescribeInstanceBill` with parameters `BillingCycle`,
  `InstanceID`, `Granularity`.
- With `--split-item`: `bssopenapi:DescribeSplitItemBill` (same parameters),
  which breaks the cost down per split item / billing item (instance fee vs
  storage fee vs backup fee, etc.). Use `--split-item` whenever the question is
  "which component of the cost grew".
- With `--granularity DAILY`: `--billing-date YYYY-MM-DD` becomes mandatory;
  it is passed as the API parameter `BillingDate` and must fall inside
  `--billing-cycle` (same month). The script exits with code 2 when missing.

Pagination: every `NextToken` page is fetched automatically (page size 300,
hard guardrail of 20 pages per query loop). Never base a conclusion on
first-page-only results.

Output:

- Table mode (default): instance header (product inferred from prefix,
  subscription type, item count), per-billing-item table with Original /
  Discount / Payment / Cash columns, a TOTAL row, and a cost-share analysis
  listing every billing item contributing more than 5% of the original amount.
- `--json`: structured result with `totals`, `by_billing_item`, and raw
  `items` (fields: `billing_item`, `split_item_name`, `billing_date`,
  `subscription_type`, `pretax_amount`, `deducted_by_cash_coupons`,
  `payment_amount`).

Amount semantics: `original` = `PretaxAmount`, `discount` =
`DeductedByCashCoupons`, `payment` = `PaymentAmount`, `cash` = original minus
discount.

### Path B: Account-level cost trend with anomaly detection

```bash
python3 scripts/query_cost_trend.py \
  --months <N> [--product <code>] [--granularity MONTHLY|DAILY] \
  [--billing-date <YYYY-MM-DD>] [--json] [--profile <name>]
```

Behavior:

- Billing cycles are computed by exact calendar-month arithmetic (N months
  back from the current month); there is no day-count drift.
- Each cycle is queried per DB product code via
  `bssopenapi:DescribeInstanceBill` with parameters `BillingCycle`,
  `ProductCode`, `Granularity`; full NextToken pagination applies.
- With `--granularity DAILY`: `--billing-date YYYY-MM-DD` is mandatory
  (passed as the API parameter `BillingDate`). DAILY semantics are a
  single-day drill-down: ONE query loop for that day's billing cycle, no
  per-day iteration and no multi-month trend.
- Supported `--product` values: `rds`, `dds`, `kvstore`, `polardb`, `dts`,
  `cbs`. Omit the flag to cover all DB products.
- BSS may report DBS under product code `cbs` or `dbs`; both are normalized to
  `cbs` so DBS is never double-counted.

Anomaly rule (built-in): a month-over-month increase is flagged when the
relative growth exceeds **20%** OR the absolute growth exceeds **100 CNY**.
When the previous month's cost is non-positive (refund / bill adjustment),
the percentage is not computed (`pct_change` null, annotated "baseline
non-positive") and the change is judged by the absolute threshold only.

Output:

- Table mode: per-product monthly trend matrix with a Total column, followed by
  an anomaly list. For each flagged month, the top 3 instances driving the
  increase are printed with their previous/current cost.
- `--json`: `cycles`, `monthly_data`, `anomalies`, and the effective
  `thresholds`.

### Product identification from instance-ID prefix

Longer prefixes are matched before shorter ones, so `rm-` wins over `r-`:

| Prefix | Product |
|---|---|
| `rm-` | RDS |
| `rr-` | RDS (read-only instance) |
| `pgm-` | RDS PostgreSQL |
| `dds-` | MongoDB |
| `pc-` | PolarDB |
| `pxc-` | PolarDB-X |
| `dts-` | DTS |
| `r-` | Tair (Redis) -- checked last, must not shadow `rm-`/`rr-` |

An unrecognized prefix yields "Unknown product"; the bill query still runs,
because BSS data does not depend on prefix detection.

## Step 5: Anomaly attribution cascade

When the trend query flags an anomaly, drill down in this fixed order:

1. **Identify the product** with the largest growth (from the anomaly list).
2. **Locate the instance**: the same anomaly output ranks the top instances of
   that product/month by cost increase.
3. **Split the billing items**: run Path A with `--split-item` for that
   instance and month to see which component (storage, backup, proxy, etc.)
   grew.
4. **Localize the day (optional)**: re-run Path A with `--granularity DAILY
   --billing-date <YYYY-MM-DD>` for a specific day of the anomalous month.
5. **State the conclusion** in one sentence: which instance, which billing
   item, which month/day, and by how much. Then give optimization advice from
   the DB cost FAQ module listed in the SKILL.md Module Index.

## Special branch: deleted instance still billed

Trigger phrases: "deleted/released instance still charged", "I released it but
the bill continues". Handle this directly; do not run the full trend flow.

1. Query the released instance ID with Path A for the billed month.
   - Records exist: residual billable components remain (e.g. backup storage).
   - **No records (most common)**: the cost usually comes from retained
     backups billed under DBS; continue at step 2.
2. Query DBS cost: run Path B with `--product cbs` to confirm DBS is the
   source in that month.
3. Confirm the root cause in the console: RDS console -> Backups ->
   **Deleted Instance Backups** (select the correct region; widen the time
   range; check all three tabs: data backup / log backup / cross-region
   backup). If the retention policy is "keep last backup" or "keep all", the
   retained backups keep billing.
4. Advise the user to change the policy to "keep none"; billing stops the next
   day. Warn explicitly that deleted backups are unrecoverable.
5. Check the same page for other deleted instances with retained backups and
   report them together.

See the DB cost FAQ module listed in the SKILL.md Module Index (section
"Deleted instance still billed") for the customer-facing explanation.

## Error handling

- The scripts exit non-zero with a `[ERROR]` line on stderr when the aliyun
  CLI is missing or a BSS/STS call fails. Surface that message verbatim.
- `NoPermission` / `AccessDenied`: the credential lacks one of the actions
  required by the RAM policy reference listed in the SKILL.md Module Index;
  ask the account owner to grant it. Never retry with different credentials
  or elevated privileges.
- "No bill data found": the instance genuinely has no bill in that cycle;
  verify the cycle format (`YYYY-MM`) and the instance ID before concluding.

## Safety guardrails

1. Read-only: only `GetCallerIdentity`, `DescribeInstanceBill`, and
   `DescribeSplitItemBill` are ever invoked. No Create/Modify/Delete/Renew
   calls exist in this skill.
2. No credential handling: never pass AK/SK to the scripts; never echo, log,
   or persist credentials.
3. Pagination is capped (MAX_PAGES = 20) to bound query cost.
4. DAILY granularity requires `--billing-date YYYY-MM-DD` and is scoped to
   that single day.
