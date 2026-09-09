---
name: alibabacloud-db-cost-diagnosis
description: |
  Read-only cost diagnostics and audits for Alibaba Cloud database products
  (RDS, Redis, MongoDB, PolarDB, DTS, DBS, CDT): explain a high or spiking
  DB bill with billing-item breakdowns and month-over-month anomaly
  attribution, and run proactive audits of renewal/expiry risk, idle
  instances, and optional paid features — never modifying any resource.
  Triggers: "why is my database bill so high", "DB cost spike",
  "database cost anomaly", "database bill surged",
  "unexpected database charges", "unexplained database charge",
  "don't know what feature is charging me", "RDS bill breakdown",
  "billing item breakdown", "charged after instance deleted",
  "released instance still billed", "monthly DB cost trend",
  "cost increase root cause", "CDT bill",
  "cost audit", "database cost audit", "idle database instance",
  "idle instance still charging", "renewal lock", "about to expire",
  "unexpected auto-renewal charge", "DMS charges", "DAS billing".
---

# DB Cost Diagnosis

Diagnose Alibaba Cloud database costs: "why is my database bill so high", "which billing item dominates this RDS instance's charge", "my DB cost jumped this month — what caused it", "I deleted the instance, why am I still being billed", "which instances are about to expire", "am I paying for idle databases", "what paid feature is charging me".

Core approach: confirm identity and billing scope, then either (1) drill into a single instance's bill detail with billing-item split to locate the dominant cost driver, (2) aggregate the account-level DB cost trend over recent months, detect anomalies, and attribute them to specific products and instances, or (3) run a proactive read-only audit — renewal/expiry risk and order anomalies, idle/low-load detection, or paid-feature attribution for unexplained charges. Conclude with evidence-based findings only; this skill never changes anything.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating API — e.g. `Modify*`, `Delete*`, `Create*`, `Restart*`, `Release*`, `Upgrade*`, `Downgrade*`, or any configuration/spec change on database resources. This includes commands "for the user to run manually". If the user asks to downgrade, release, or resize an instance to cut cost, only output the manual guidance and declare this skill is read-only.
2. **API WHITELIST:** The only permitted OpenAPI actions are the read-only BSS queries `DescribeInstanceBill`, `DescribeSplitItemBill`, `QueryOrders`, and `QueryAvailableInstances` (bssopenapi, endpoint `business.aliyuncs.com`, API version `2017-12-14`), the read-only CloudMonitor query `DescribeMetricList` (cms), plus `sts:GetCallerIdentity` for identity traceability. Any other action is forbidden.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. Credentials are resolved automatically by the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by the billing APIs. If a query fails or returns empty, record it and state the limitation — never invent cost numbers, instance names, or billing items.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <Code>: <Message>` to stderr and continue with the remaining queries — never silently skip or abort the whole diagnosis. The final report is still produced with the data at hand.
6. **SCOPE BOUNDARY:** This skill answers questions about issued or current bills and cost attribution (which product/instance/billing item produced a charge), and provides READ-ONLY audits of renewal status, order anomalies, idle capacity and paid features. It does NOT execute renewals, unsubscriptions, refunds, or any other mutation, does NOT handle pre-purchase price quotes or unlocking resources after overdue payment — for such requests, state the boundary and point the user to the console purchase/renewal pages.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. The Agent is forbidden from assembling its own `aliyun` CLI commands or bypassing the scripts to call billing APIs directly — the scripts embed pagination, retry, error degradation, and observability guarantees that ad-hoc commands lack. Read the script output, interpret it, and compose the report; do not re-implement the queries.

## Observability

All OpenAPI calls (invoked through the aliyun CLI by the scripts) include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id}`, where `{skill-name}` is `alibabacloud-db-cost-diagnosis`
- **session-id**: 32-character hex string (`uuid.uuid4().hex`) generated once per script run and attached to every CLI command of that run, so all calls of one diagnosis can be correlated.

The shared CLI layer implements this automatically: the session-id is generated lazily on the first call of each run, cached for the rest of the run, and concatenated into the `--user-agent` argument of every `aliyun` invocation.

## Prerequisites

1. **aliyun CLI 3.x** — required: all billing queries and the identity check are invoked via the `aliyun` CLI (built-in API metadata mode for `bssopenapi`; the identity check uses plugin mode for `sts get-caller-identity` and, when the STS plugin is not installed in the environment, automatically falls back to the built-in API metadata mode for the same identity action). No direct HTTP signing, no external Python SDK.
2. **Python 3.9+** — standard library only, no third-party dependencies.
3. **Alibaba Cloud credentials** — resolved automatically by the aliyun CLI default credential chain (environment variables or `~/.aliyun/config.json`). Do not read, print, or pass AK/SK/STS tokens explicitly.

## Authentication

Credentials are resolved automatically by the aliyun CLI default credential chain (environment or `~/.aliyun/config.json`). Do not read, print, or pass AK/SK/STS tokens explicitly.

```bash
cd $SKILL_DIR

# Verify caller identity (informational only; credentials always come from the CLI default chain)
python3 scripts/sts_token.py
```

**Identity Verification Failure**: If `sts get-caller-identity` fails, the default credential chain is not configured. Guide the user to run `aliyun configure` — never ask for AK/SK.

## Input Parameters

- **Billing cycle** (`--billing-cycle YYYY-MM`): the month to analyze. Default: current month. Auto-fill the current month when omitted and declare it.
- **Instance ID** (`--instance-id`): required for single-instance diagnosis; optional for account-level trend analysis, where instances are auto-discovered from the bill itself.
- **Product filter** (`--product`): optional; one of `rds|dds|kvstore|polardb|dts|cbs|cdt`. When an instance ID is given, the DB product is auto-inferred from its prefix (`rm-` RDS, `r-` Redis, `dds-` MongoDB, `pc-` PolarDB, etc.), so no extra question is needed; CDT is an account-level transfer product, so pass `--product cdt` explicitly when its charges are in question.
- **UID**: can always be omitted — it is derived via `aliyun sts get-caller-identity` and used only as a traceability label. Auto-fill first, ask second: never ask the user for UID when it can be derived.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (billing cycle, product, or UID), the Agent MUST explicitly declare this in the response or report metadata, e.g. "Billing cycle auto-defaulted to the current month (2026-08)" or "Product auto-inferred from instance prefix: ApsaraDB RDS".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Cost query orchestration | [references/module1_cost_query.md](references/module1_cost_query.md) | How to compose bill/trend queries: granularity choice, pagination, split-item semantics, anomaly drill-down sequencing |
| M2: DB cost FAQ | [references/module2_cost_faq.md](references/module2_cost_faq.md) | High-frequency database billing questions: billing items, charging modes, deleted-instance charges, common cost drivers |
| M3: Cost-audit orchestration | [references/module3_cost_audit.md](references/module3_cost_audit.md) | Renewal/order audit, idle detection and paid-feature audit: when to use which script, parameter and output interpretation, verdict/threshold semantics, EOS table |
| M4: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Scope

**EXECUTION RULE (MANDATORY FIRST STEP):** You MUST run `python3 scripts/sts_token.py` before any billing query, on every diagnosis, **even when the user already supplied a UID in the request**. A UID given by the user is only a label to cross-check against; the identity pre-check is what proves which account the returned bills belong to, so skipping it invalidates the whole diagnosis. Never treat a user-provided UID as a substitute for this call, and never drop this step to save queries — it does not count against any query budget.

Then determine which capability the user needs: A single-instance bill detail, B account-level trend & anomaly attribution, C renewal & order audit, D idle/low-load instance detection, or E paid-feature & unexplained-charge audit (see [references/module3_cost_audit.md](references/module3_cost_audit.md) for the audit selection guide). If genuinely ambiguous, ask one brief clarifying question.

### Step 2 (Capability A): Single-Instance Bill Detail & Billing-Item Split

```bash
cd $SKILL_DIR && python3 scripts/query_instance_bill.py \
    --instance-id <ID> --billing-cycle <YYYY-MM> [--split-item] \
    [--granularity MONTHLY|DAILY] [--billing-date <YYYY-MM-DD>] [--json]
```

The script calls the bssopenapi `DescribeInstanceBill` action (or `DescribeSplitItemBill` with `--split-item`) through the aliyun CLI built-in API metadata mode, with full NextToken pagination, then aggregates by billing item:

1. **Billing-item breakdown**: original / discount / payment / cash amount per billing item, plus a cost-share ranking of items contributing more than 5%.
2. **Split-item drill-down**: add `--split-item` when the user needs per-split-item (e.g. per-shard / per-storage-segment) granularity.
3. **DAILY granularity**: `--granularity DAILY` MUST be paired with `--billing-date YYYY-MM-DD` (BSS mandates `BillingDate` for daily bills, and it must fall inside the billing cycle); the script exits with code 2 when it is missing.
4. **Deleted-instance branch**: if the user says the instance was released/deleted but still appears on the bill, query the cycle in which the instance existed and the following cycle(s); bill entries for released instances are expected for usage accrued before release (and for retained billable components, e.g. backups or disks not released with the instance). Judge in order: first identify the exact billing item from the returned bill data (e.g. `backup_storage`), then cite the matching FAQ entry in `references/module2_cost_faq.md` — state which items carry the residual charge, using the actual returned data only.

**Dual-audience output**: every script ends its human-readable report with a plain-language `Summary` section (what was queried / key findings in plain words / suggested next steps) aimed at non-technical users; with `--json` the same conclusion is exposed as machine-consumable `summary` / `key_findings` / `suggestions` fields alongside the detail fields, for the next diagnosis stage. Empty or failed queries still populate these fields (with reasons and actionable next steps), so downstream consumers can rely on them unconditionally.

Internally: endpoint `business.aliyuncs.com`, API version `2017-12-14`.

### Step 3 (Capability B): Account-Level DB Cost Trend & Anomaly Attribution

```bash
cd $SKILL_DIR && python3 scripts/query_cost_trend.py [--months 6] [--product rds|dds|kvstore|polardb|dts|cbs|cdt] [--granularity MONTHLY|DAILY] [--billing-date <YYYY-MM-DD>] [--json]
```

The script aggregates `DescribeInstanceBill` per ProductCode over the last N billing cycles (default 6) and computes:

1. **Monthly cost trend** per DB product (RDS, Redis, MongoDB, PolarDB, DTS, DBS, CDT) plus a monthly total.
2. **Anomaly detection**: a month-over-month increase is flagged when relative growth > 20% **OR** absolute growth > 100 CNY. When the baseline month is non-positive (refund / bill adjustment), the percentage is not computed and the change is judged by the absolute threshold only (annotated "baseline non-positive").
3. **Drill-down attribution**: for every flagged month, the top-3 instances driving the increase are listed with their previous vs. current cost. If finer resolution is needed, re-run with `--granularity DAILY --billing-date <YYYY-MM-DD>` to drill into a single day of that month — DAILY is a one-day drill-down (single query loop) and always requires `--billing-date`; it never iterates day by day.

The same dual-audience contract as Step 2 applies: the readable report ends with a plain-language `Summary` section, and `--json` carries `summary` / `key_findings` / `suggestions` (populated even for empty or failed queries) for downstream stages.

### Step 5 (Capability C): Renewal & Order Audit

```bash
cd $SKILL_DIR && python3 scripts/audit_renewal_orders.py [--months <N>] [--json]
```

MANDATORY single-command entry for any renewal/expiry/order/EOS question. The script queries `QueryAvailableInstances` (the server-side ProductCode filter is unreliable, so RDS rows are re-filtered client-side) and grades each instance's `EndTime` into the 90/30/7-day expiry windows with a high/medium/low risk label derived from `RenewStatus`; it then pulls the order history via `QueryOrders` with a MANDATORY explicit time window (default 6 months; without an explicit window the API silently narrows to ~1 hour) to detect auto-renewal charge sequences, adjacent renewal price jumps (> 3x), and refund/cancelled anomalies; finally it matches best-effort engine versions against the embedded EOS table. When no engine version can be extracted, report the EOS table and ask the user to confirm the versions in the console — never fabricate a version. Same dual-audience output contract as Step 2.

### Step 6 (Capability D): Idle & Low-Load Instance Audit

```bash
cd $SKILL_DIR && python3 scripts/audit_idle_instances.py [--billing-cycle <YYYY-MM>] [--json]
```

MANDATORY single-command entry for idle / "paying for a database nobody uses" questions. The script first discovers billed RDS instances from `DescribeInstanceBill` (an empty result is a valid "no billed RDS instance" outcome, exit 0), then samples CloudMonitor `DescribeMetricList` (namespace `acs_rds_dashboard`: CpuUsage / ConnectionUsage / IOPSUsage / DiskUsage; 7-day window, 3600 s period, at most 50 instances per batch) and renders an idle / low_load / active verdict per instance. Instances without complete metric data (no datapoints at all, or only one of the CPU/connection dimensions sampled) stay **inconclusive** and are NEVER judged idle; a total CloudMonitor failure degrades to the billing-side listing without aborting. Same dual-audience output contract as Step 2.

### Step 7 (Capability E): Paid-Feature & Unexplained-Charge Audit

```bash
cd $SKILL_DIR && python3 scripts/audit_paid_features.py [--billing-cycle <YYYY-MM>] [--product rds|dds|kvstore|polardb|dts|cbs|cdt] [--json]
```

MANDATORY single-command entry for "what am I paying for" / unexplained-charge questions. The script queries `DescribeInstanceBill(ProductCode)` for the cycle, drills `DescribeSplitItemBill` into the top 10 costliest instances (guardrail; the rest stay at instance level), and attributes every billing item via the paid-feature map (SQL Audit / Performance Insight / cross-region backup / proxy / read-only / auto scaling / DAS Pro). Items matching neither a paid feature nor a known base charge are listed as unidentified charge candidates. Same dual-audience output contract as Step 2.

### Step 8: Conclusion and Suggestions

Summarize: which billing item / instance / month explains the cost, or which audit verdicts / expiry risks / paid features were found, with the actual numbers from the script outputs. Base the conclusion on the script's own `Summary` section (readable mode) or `summary` / `key_findings` / `suggestions` JSON fields rather than re-deriving it.

**Final Answer Contract**: every number, verdict, and date in the final answer MUST be quoted verbatim from the script's `Summary` section or its JSON output (`summary` / `key_findings` / `suggestions`) — never recompute, round differently, or estimate. Suggestions must be evidence-based and stated as manual guidance only (this skill never applies any change).

**Fallback**: when the billing APIs cannot answer the question (no data, permission gap, or a pricing-policy question), search the official Alibaba Cloud help documentation for the relevant billing rules; if the question still cannot be resolved, suggest the user submit a support ticket with the diagnosis details attached.

## Important Notes

- **Data latency**: split-item bill data (DescribeSplitItemBill) has an approximately **48-hour delay**; very recent usage may be missing. State this when the queried window includes the last two days.
- **Granularity discipline**: `DAILY` granularity is heavier and is reserved for drilling down into a month that the MONTHLY trend already flagged as anomalous. Default to `MONTHLY`. `--granularity DAILY` MUST be paired with `--billing-date YYYY-MM-DD` (BSS mandates `BillingDate` for daily bills); the trend script treats DAILY as a single-day drill-down, never a per-day loop.
- **Authoritative source**: all figures come from the Billing Management (expense center) APIs; the official bill in the console is the final authority for any dispute.
- **QueryOrders time window**: the renewal audit ALWAYS sends an explicit `CreateTimeStart`/`CreateTimeEnd` window — without one, QueryOrders silently narrows to roughly 1 hour and returns nothing (known pitfall).
- **CloudMonitor degradation**: no datapoints (or a missing CPU/connection dimension) for an instance means `inconclusive`, never "idle"; a total CMS failure degrades to the billing-side listing and does not abort the audit.
- **EOS table is static knowledge**: embedded snapshot dated 2026-08-26 from the official Alibaba Cloud lifecycle announcements; when in doubt or the user disputes a date, the official announcements prevail.
- **Read-only operations**: only the whitelisted read-only BSS / CloudMonitor queries and `sts:GetCallerIdentity`; never modifies, releases, renews, or resizes anything.

## Examples

**Example 1 — single-instance bill breakdown**

> User: "Why did my RDS instance rm-bp1xxxx cost 800 CNY last month?"

```bash
python3 scripts/query_instance_bill.py --instance-id rm-bp1xxxx --billing-cycle 2026-07 --split-item
```

Report the per-billing-item table (e.g. instance spec vs. storage vs. backup), the cost-share ranking, and the script's closing `Summary` section (plain-language findings + next steps), and declare: "Billing cycle auto-filled to 2026-07 based on 'last month'." When the report feeds a follow-up stage instead of a human, use `--json` and consume its `summary` / `key_findings` / `suggestions` fields.

**Example 2 — account-level trend & anomaly attribution**

> User: "My database bill suddenly jumped, help me find the cause."

```bash
python3 scripts/query_cost_trend.py --months 6
```

Report the 6-month trend table, list flagged month-over-month jumps (with the > 20% / > 100 CNY rule), cite the top instances driving each jump, and relay the script's closing `Summary` section. If a month needs finer detail, drill down with `--granularity DAILY --billing-date <YYYY-MM-DD>` for one specific day of that month.

**Example 3 — released instance still billed**

> User: "I deleted instance r-bp1yyyy weeks ago, why am I still paying for it?"

```bash
python3 scripts/query_instance_bill.py --instance-id r-bp1yyyy --billing-cycle 2026-08 --split-item
```

Query the deletion month and the current month; identify which billing items still carry charges (e.g. usage accrued before release, or components not released with the instance), and explain strictly from the returned items — noting the ~48h split-item delay if the window is recent.

## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/query_instance_bill.py` | Single-instance bill detail: billing-item aggregation, cost-share ranking, split-item drill-down |
| `scripts/query_cost_trend.py` | Account-level DB cost trend per product over N months, anomaly detection, top-instance attribution |
| `scripts/audit_renewal_orders.py` | Renewal & order audit: expiry windows (90/30/7d), renewal price spikes, refund anomalies, EOS check |
| `scripts/audit_idle_instances.py` | Idle & low-load audit: billed RDS instances cross-checked against 7-day CloudMonitor load |
| `scripts/audit_paid_features.py` | Paid-feature audit: attributes split-item charges to optional add-ons; lists unidentified charges |

CLI options for `query_instance_bill.py`: `--instance-id <ID>` (required), `--billing-cycle <YYYY-MM>` (required), `--split-item` (DescribeSplitItemBill), `--granularity MONTHLY|DAILY` (default MONTHLY), `--billing-date <YYYY-MM-DD>` (required when `--granularity DAILY`, must fall inside the billing cycle), `--json`, `--profile`.

CLI options for `query_cost_trend.py`: `--months <N>` (default 6, minimum 2), `--product <rds|dds|kvstore|polardb|dts|cbs|cdt>` (optional filter), `--granularity MONTHLY|DAILY` (default MONTHLY; DAILY is a single-day drill-down), `--billing-date <YYYY-MM-DD>` (required when `--granularity DAILY`), `--json`, `--profile`.

CLI options for `audit_renewal_orders.py`: `--months <N>` (default 6, range 1-24), `--json`, `--profile`.

CLI options for `audit_idle_instances.py`: `--billing-cycle <YYYY-MM>` (default: current month), `--json`, `--profile`.

CLI options for `audit_paid_features.py`: `--billing-cycle <YYYY-MM>` (default: current month), `--product <rds|dds|kvstore|polardb|dts|cbs|cdt>` (default rds), `--json`, `--profile`.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Default credential chain not configured | Run `aliyun configure`; never ask the user for AK/SK |
| `NoPermission` / `AccessDenied` | RAM policy missing a BSS read permission | Record the missing action, continue with remaining queries, point to [references/ram-policies.md](references/ram-policies.md) |
| `InvalidParameter` / invalid billing cycle | Wrong cycle format or out-of-range month | Log `[WARN]`, verify `YYYY-MM` format, continue |
| `Throttling.User` | Request rate limited | Retried automatically with backoff (up to 3 attempts); then log `[WARN]` and continue |
| `InternalError` / `ServiceUnavailable` | Transient service-side failure | Retried automatically; log `[WARN]` and continue; do not conclude "no cost" from a single failed call |
| Empty bill data | No charge in the cycle, wrong instance ID, or 48h split-item delay | Report "no data" honestly; verify instance ID and cycle, mention the data latency when the window is recent |

All errors follow the `Code: Message` format raised as `CliError` inside the shared CLI layer; transient errors are retried, persistent ones are degraded with `[WARN]` on stderr, and the report is always emitted with whatever data succeeded.
