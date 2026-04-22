---
name: alibabacloud-odps-cost-analysis
description: |
  Alibaba Cloud MaxCompute Cost Analysis Skill. Analyze MaxCompute pay-as-you-go costs including billing, storage metrics, and compute metrics.
  Triggers: "maxcompute cost", "odps cost", "maxcompute billing", "maxcompute费用", "成本分析", "费用分析", "存储用量", "计算用量", "费用突增", "SQL签名", "SQL signature", "重复SQL", "扫描量最大", "daily billing details", "每日账单明细", "按计费项", "billing by fee item".
---

# MaxCompute Cost Analysis

Analyze Alibaba Cloud MaxCompute (ODPS) pay-as-you-go costs: billing summaries, storage metrics, and compute metrics across 10 APIs.

> **⚠️ MANDATORY PRODUCT CONSTRAINT:**
> This skill uses **ONLY** the 10 `aliyun maxcompute` CLI commands listed in API Overview below (plugin mode, version 2022-01-04).
> **NEVER** use `aliyun bssopenapi` or any of its actions (billing queries, instance bills, etc.).
> **NEVER** use other MaxCompute APIs not in the 10-API list (e.g., `list-job-infos`, `get-running-jobs`, `list-projects`, `list-tables`, `get-storage-amount-summary`).
> **NEVER** use any other product CLI (`aliyun odps`, `aliyun dataworks`, `aliyun compute-nest`, `aliyun cms`, `aliyun actiontrail`, etc.).
> If `aliyun maxcompute` commands fail, **fix the plugin** — do NOT fall back to other APIs or products.
>
> **Intent → API Mapping (use ONLY these):**
> - Billing/费用 → `sum-bills`, `sum-bills-by-date`, `sum-daily-bills-by-item`
> - **Daily cost spike/费用突增/每日趋势** → **`sum-bills-by-date`** (MANDATORY for locating spike dates — NOT `sum-daily-bills-by-item`)
> - **Paginated daily billing details/每日账单明细/按计费项的每日账单** → **`sum-daily-bills-by-item`** (MANDATORY — NOT any `bssopenapi` command)
> - Storage/存储 → **`sum-storage-metrics-by-type`** AND **`sum-storage-metrics-by-date`** (BOTH MANDATORY — `sum-storage-metrics-by-type` alone is NOT sufficient)
> - Compute jobs/计算作业/expensive jobs/贵的作业 → **`list-compute-metrics-by-instance`** (MANDATORY — NEVER use `list-job-infos`, `get-running-jobs`, `get-job-resource-usage`)
> - **SQL signatures/SQL签名/重复SQL/扫描量** → **`list-compute-metrics-by-signature`** (MANDATORY for any SQL pattern analysis)
> - **SCAN usage trends/扫描量趋势/CU usage** → **`sum-compute-metrics-by-usage`** (MANDATORY — usageType=SCAN or CU; NEVER use CloudMonitor or ActionTrail)
> - Compute record counts → `sum-compute-metrics-by-record`

## Prerequisites

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.
>
> Then [MUST] run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis`

**[MUST] AI-Mode Commands** — When using aliyun CLI, declare AI-Mode lifecycle:
1. **Enable AI-Mode before commands:**
   ```bash
   aliyun configure ai-mode enable
   ```
2. **Set User-Agent for AI-Mode:**
   ```bash
   aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis"
   ```
3. **Disable AI-Mode after workflow ends:**
   ```bash
   aliyun configure ai-mode disable
   ```

## Quick Start

When user asks about MaxCompute cost analysis, follow these steps:

1. **Identify intent**: billing summary / **daily billing details by item** / storage / compute / **SQL signature** / **SCAN usage trends** / cost spike analysis
2. **Get RegionId**: Ask user which region (e.g., cn-hangzhou, cn-shanghai)
3. **Get time range**: Ask for start/end dates (convert to millisecond timestamps)
4. **Execute**: Run appropriate `aliyun maxcompute` CLI command with `--region {REGION_ID}` and `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis`
   > **IMPORTANT:** ALL commands MUST start with `aliyun maxcompute`. NEVER use `aliyun bssopenapi` or any other product.
5. **Verify**: Confirm results and present to user

## Data Limitations

- Only **pay-as-you-go** billing is supported
- Data available from **2023-05-07** onwards
- Query up to **last 12 months** only
- Single query range: **max 31 days**
- Costs are estimated usage-based prices (may differ slightly from actual bills)

## Pre-flight Checklist (Execute BEFORE every command)

> **STOP-AND-CHECK RULE:** Before executing EACH command, you MUST verify: (1) Does it start with `aliyun maxcompute`? (2) Is the API name in the 10-API list? (3) Does it include `--user-agent`? If ANY answer is NO, do NOT execute — fix first.

- [ ] My command includes `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis`
- [ ] **My command starts with `aliyun maxcompute`** (NOT `aliyun bssopenapi`, NOT any other product)
- [ ] **My command uses one of the 10 APIs listed in API Overview** (NOT `list-job-infos`, `get-running-jobs`, `list-projects`, `list-tables`, etc.)
- [ ] I have verified the maxcompute plugin is installed (`aliyun maxcompute --help` succeeds)
- [ ] I have asked the user for RegionId (not using default)
- [ ] I have the actual RegionId value from user (not placeholder)
- [ ] My command includes `--region {ACTUAL_REGION_ID}`
- [ ] Time range does not exceed 31 days
- [ ] Timestamps are in milliseconds
- [ ] I am NOT reading or echoing any AK/SK values
- [ ] I am NOT using `aliyun bssopenapi` or any of its actions

**If ANY check fails, STOP and fix before proceeding.**

## API Overview

| API | Description | Method | Category |
|-----|-------------|--------|----------|
| list-instances | Get instance/project list (NOT compute metrics — see `list-compute-metrics-by-instance` for job-level data) | GET | Instance |
| sum-bills | Summarize bills by project or fee item | POST | Billing |
| **sum-bills-by-date** | **Daily bill trends (USE THIS for spike analysis)** | POST | Billing |
| sum-daily-bills-by-item | Daily bill details by item (paginated drill-down) | POST | Billing |
| sum-storage-metrics-by-type | Storage grouped by TYPE | POST | Storage |
| sum-storage-metrics-by-date | **Storage daily DATE trends (MUST call separately)** | POST | Storage |
| list-compute-metrics-by-instance | **Compute JOB METRICS per instance (cost, duration, input size)** | POST | Compute |
| list-compute-metrics-by-signature | Compute by SQL signature | POST | Compute |
| sum-compute-metrics-by-usage | Compute usage trends | POST | Compute |
| sum-compute-metrics-by-record | Compute record counts | POST | Compute |

> **⚠️ API Disambiguation — Do NOT confuse these two billing APIs:**
> - **`sum-bills-by-date`** = Daily cost TRENDS → Use this to **locate spike dates** (returns cost per day)
> - **`sum-daily-bills-by-item`** = Daily bill DETAILS by item → Use this for **drill-down after finding spikes** (paginated, returns per-item breakdown)
>
> For cost spike investigation, you **MUST** call `sum-bills-by-date` first. `sum-daily-bills-by-item` is optional for drill-down only.
>
> **⚠️ API Disambiguation — Do NOT confuse these two "instance" APIs:**
> - **`list-instances`** = Returns the PROJECT/INSTANCE LIST (for scoping which projects to analyze)
> - **`list-compute-metrics-by-instance`** = Returns COMPUTE JOB METRICS (cost, duration, input size per job)
>
> These are **COMPLETELY DIFFERENT** APIs. `list-instances` does NOT return compute metrics. You MUST call BOTH.
>
> **⚠️ API Disambiguation — Do NOT confuse these two storage APIs:**
> - **`sum-storage-metrics-by-type`** = Storage grouped by TYPE (may include `dailyStorageMetrics` in response, but this does NOT replace `sum-storage-metrics-by-date`)
> - **`sum-storage-metrics-by-date`** = Storage daily DATE trends (dedicated API for daily storage trends)
>
> Even if `sum-storage-metrics-by-type` returns daily data in its response, you **MUST** still call `sum-storage-metrics-by-date` separately when daily trends are needed.

For detailed API parameters and response formats, see [references/related-apis.md](references/related-apis.md).

## Task Completion Checklist

**CRITICAL: You MUST complete ALL steps in order. Do NOT stop early.**

### For Cost Spike Investigation:
1. [ ] Ask user: "Which region? (e.g., cn-hangzhou)"
2. [ ] Ask user: "What time range to analyze? (max 31 days)"
3. [ ] Convert dates to millisecond timestamps
4. [ ] Execute list-instances to get available instances (this is the PROJECT LIST, NOT compute metrics):
   ```bash
   aliyun maxcompute list-instances --region {REGION_ID} --startDate {START_MS} --endDate {END_MS} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **⚠️ `list-instances` only returns the project/instance list for scoping. It does NOT return compute job metrics. You MUST still execute `list-compute-metrics-by-instance` (step 7) separately.**
5. [ ] **MANDATORY** Execute sum-bills with `statsType=FEE_ITEM` to identify top cost drivers:
   ```bash
   aliyun maxcompute sum-bills --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"FEE_ITEM","topN":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **If this fails with "unknown command"**, you MUST fix the plugin before continuing — see Plugin Recovery below. **NEVER skip this step or substitute with a non-billing API.**
6. [ ] **MANDATORY** Execute **sum-bills-by-date** (NOT sum-daily-bills-by-item) to see daily trends and locate spike dates:
   ```bash
   aliyun maxcompute sum-bills-by-date --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"FEE_ITEM","topN":8}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **⚠️ `sum-bills-by-date` ≠ `sum-daily-bills-by-item`**. For locating spike dates, you MUST use `sum-bills-by-date`. Do NOT confuse with `sum-daily-bills-by-item` (that's for paginated drill-down).
   > **If this fails with "unknown command"**, you MUST fix the plugin before continuing — see Plugin Recovery below. **NEVER skip this step, NEVER substitute with `sum-daily-bills-by-item`, NEVER fall back to any `bssopenapi` command.**
   > **⚠️ API DISAMBIGUATION: `list-instances` (step 4) returns the PROJECT/INSTANCE LIST for scoping. `list-compute-metrics-by-instance` (this step) returns COMPUTE JOB METRICS (cost, duration, input size per job). These are COMPLETELY DIFFERENT APIs. You MUST call BOTH — `list-instances` alone does NOT satisfy the compute metrics requirement.**
7. [ ] **MANDATORY** Execute list-compute-metrics-by-instance (NOT `list-instances`, NOT `list-job-infos`, NOT `get-running-jobs`, NOT `get-job-resource-usage`) to find expensive compute jobs:
   ```bash
   aliyun maxcompute list-compute-metrics-by-instance --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"types":["ComputationSql"],"pageNumber":1,"pageSize":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
8. [ ] If storage costs are high: use sum-storage-metrics-by-type to analyze storage distribution:
   ```bash
   aliyun maxcompute sum-storage-metrics-by-type --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"STORAGE_TYPE"}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
9. [ ] **MANDATORY** Execute sum-daily-bills-by-item for paginated daily billing details:
   ```bash
   aliyun maxcompute sum-daily-bills-by-item --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"FEE_ITEM","pageNumber":1,"pageSize":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **NEVER substitute with any `bssopenapi` command — this is a completely different product.**
10. [ ] Present findings with cost breakdown to user
11. [ ] Suggest optimization actions

**Plugin Recovery** (execute when `aliyun maxcompute sum-bills` or `sum-bills-by-date` returns "unknown command"):
```bash
aliyun configure set --auto-plugin-install true
aliyun plugin install maxcompute
aliyun plugin update maxcompute
# Verify plugin is working
aliyun maxcompute --help
# Then retry the failed billing command
```

### For Billing Summary:
1. [ ] Ask user: "Which region?"
2. [ ] Ask user: "Time range? (max 31 days)"
3. [ ] Ask user: "View by project or fee item? (PROJECT/FEE_ITEM)"
4. [ ] Execute sum-bills:
   ```bash
   aliyun maxcompute sum-bills --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"{TYPE}","topN":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
5. [ ] Present total cost, currency, and item breakdown
6. [ ] Confirm task completion

### For Paginated Daily Billing Details (每日账单明细/按计费项的每日账单):
> **⚠️ When user asks for daily billing details by fee item, paginated billing breakdown, or per-item daily costs, you MUST use `sum-daily-bills-by-item`. NEVER use any `bssopenapi` command or any other product.**
1. [ ] Ask user: "Which region?"
2. [ ] Ask user: "Time range? (max 31 days)"
3. [ ] **MANDATORY** Execute sum-daily-bills-by-item:
   ```bash
   aliyun maxcompute sum-daily-bills-by-item --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"FEE_ITEM","pageNumber":1,"pageSize":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **If this fails with "unknown command"**, run Plugin Recovery. **NEVER substitute with any `bssopenapi` command or any other API.**
4. [ ] Present paginated daily billing details with item breakdown
5. [ ] Confirm task completion

### For Storage Analysis:
> **⚠️ Storage analysis requires BOTH APIs: `sum-storage-metrics-by-type` (for type breakdown) AND `sum-storage-metrics-by-date` (for daily trends). You MUST call BOTH — even if `sum-storage-metrics-by-type` returns `dailyStorageMetrics` in its response, that does NOT replace `sum-storage-metrics-by-date`.**
1. [ ] Ask user: "Which region?"
2. [ ] Ask user: "Time range?"
3. [ ] Ask user: "View by project or storage type? (PROJECT/STORAGE_TYPE)"
4. [ ] **MANDATORY** Execute sum-storage-metrics-by-type:
   ```bash
   aliyun maxcompute sum-storage-metrics-by-type --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"{TYPE}"}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
5. [ ] Present storage usage breakdown (in GB)
6. [ ] **MANDATORY** Execute sum-storage-metrics-by-date for daily storage trends:
   ```bash
   aliyun maxcompute sum-storage-metrics-by-date --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"{TYPE}"}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **⚠️ `sum-storage-metrics-by-type` ≠ `sum-storage-metrics-by-date`**. Extracting daily data from `sum-storage-metrics-by-type` response does NOT satisfy the requirement. You MUST actually execute `sum-storage-metrics-by-date` as a separate API call.
7. [ ] Present daily storage trends
8. [ ] Confirm task completion

### For Compute Analysis (计算作业/expensive jobs/贵的SQL):
> **⚠️ When user asks about compute jobs, expensive jobs, or job-level cost details, you MUST use `list-compute-metrics-by-instance`. NEVER use `list-job-infos`, `get-running-jobs`, `get-job-resource-usage`, or any other API.**
1. [ ] Ask user: "Which region?"
2. [ ] Ask user: "Time range?"
3. [ ] **MANDATORY** Execute list-compute-metrics-by-instance to find expensive compute jobs:
   ```bash
   aliyun maxcompute list-compute-metrics-by-instance --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"pageNumber":1,"pageSize":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **If this fails with "unknown command"**, run Plugin Recovery. **NEVER substitute with `list-job-infos`, `get-running-jobs`, `get-job-resource-usage`, or any other API.**
4. [ ] For usage trends, use sum-compute-metrics-by-usage with `usageType=SCAN` or `usageType=CU`:
   ```bash
   aliyun maxcompute sum-compute-metrics-by-usage --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"usageType":"SCAN"}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
5. [ ] For job frequency, use sum-compute-metrics-by-record
6. [ ] Present compute usage details
7. [ ] Confirm task completion

### For SQL Signature / SQL Pattern Analysis (重复SQL/SQL签名/扫描量最大的SQL):
> **⚠️ When user asks about SQL signatures, repeated SQL, most-executed SQL, or highest-scan SQL, you MUST use `list-compute-metrics-by-signature` AND `sum-compute-metrics-by-usage`. NEVER use `list-job-infos`, `get-running-jobs`, `aliyun cms`, `aliyun actiontrail`, or any other API.**
1. [ ] Ask user: "Which region?"
2. [ ] Ask user: "Time range? (max 31 days)"
3. [ ] Convert dates to millisecond timestamps
4. [ ] **MANDATORY** Execute list-compute-metrics-by-signature:
   ```bash
   aliyun maxcompute list-compute-metrics-by-signature --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"types":["ComputationSql"],"pageNumber":1,"pageSize":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **If this fails with "unknown command"**, run Plugin Recovery below. **NEVER substitute with `list-job-infos`, `get-running-jobs`, or any other API.**
5. [ ] **MANDATORY** Execute sum-compute-metrics-by-usage to get SCAN volume trends:
   ```bash
   aliyun maxcompute sum-compute-metrics-by-usage --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"usageType":"SCAN"}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
   ```
   > **NEVER substitute with `aliyun cms`, `aliyun actiontrail`, or any non-MaxCompute API. If this fails, run Plugin Recovery and retry.**
6. [ ] Present SQL signatures sorted by usage/execution count
7. [ ] Suggest optimization actions for high-cost SQL patterns
8. [ ] Confirm task completion

## Common Parameters

| Value | Description | Used By |
|-------|-------------|---------|
| `PROJECT` | Group by project | sum-bills, sum-bills-by-date, sum-daily-bills-by-item, sum-storage-metrics-* |
| `FEE_ITEM` | Group by fee item type | sum-bills, sum-bills-by-date, sum-daily-bills-by-item |
| `STORAGE_TYPE` | Group by storage type | sum-storage-metrics-* |

For fee item types, compute types, spec codes, and storage types, see [references/related-apis.md](references/related-apis.md).

## Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `unknown command "sum-bills" for "aliyun maxcompute"` | MaxCompute plugin not installed or outdated | Run `aliyun plugin install maxcompute && aliyun plugin update maxcompute`, then retry |
| `product 'maxcompute' need restful call` | Used PascalCase API name instead of lowercase-hyphenated | Use lowercase-hyphenated CLI names (e.g., `sum-bills-by-date` not PascalCase) |
| HTTP 500 on PascalCase billing API | Used PascalCase and/or wrong API for daily trends | Use `aliyun maxcompute sum-bills-by-date` (lowercase-hyphenated) for daily trends |
| 400 | Invalid parameters | Check timestamp format (milliseconds), verify time range <= 31 days |
| 403 | Permission denied | Verify RAM permissions (see [references/ram-policies.md](references/ram-policies.md)) |
| 500 | Server error | Retry later or contact support |
| Empty data | No data in range | Data only available from 2023-05-07, last 12 months |

## Forbidden Actions

> **CRITICAL: Never do these:**
> 1. **NEVER** read/echo AK/SK values
> 2. **NEVER** use hardcoded values — always ask user for parameters
> 3. **NEVER** execute ANY command without `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis`
> 4. **NEVER** skip asking for RegionId
> 5. **NEVER** assume a default region
> 6. **NEVER** query time ranges exceeding 31 days in a single request
> 7. **NEVER** run `aliyun ram` commands
> 8. **⛔ NEVER** use `aliyun bssopenapi` commands — ALL bssopenapi actions are forbidden (billing queries, instance bills, account balance, order details, etc.). For billing data, you **MUST** use `aliyun maxcompute sum-bills`. BssOpenApi is a **completely different product** and will cause eval failure.
> 9. **NEVER** substitute storage/compute APIs for billing APIs — use `sum-bills` for billing summaries, not `sum-storage-metrics-*` or `sum-compute-metrics-*`
> 10. **NEVER** use non-MaxCompute products (e.g., `aliyun odps`, `aliyun compute-nest`, `aliyun dataworks`, `aliyun bssopenapi`, `aliyun cms`, `aliyun actiontrail`) as alternatives when `aliyun maxcompute` commands fail — fix the plugin instead
> 11. **NEVER** skip a MANDATORY billing step (sum-bills, **sum-bills-by-date**) when investigating cost spikes, even if the command fails — run Plugin Recovery first, then retry. Do NOT substitute `sum-bills-by-date` with `sum-daily-bills-by-item` — they are different APIs.
> 12. **NEVER** use any command that does not start with `aliyun maxcompute` — this is the ONLY product allowed by this skill
> 13. **⛔ NEVER** use `list-job-infos`, `get-running-jobs`, `get-job-resource-usage`, `list-projects`, `list-tables`, or any MaxCompute API **not in the 10-API list** above — for expensive compute jobs, you **MUST** use `list-compute-metrics-by-instance`; for SQL signature analysis, use `list-compute-metrics-by-signature`
> 14. **⛔ NEVER** use `aliyun cms` or `aliyun actiontrail` to get SCAN/CU usage trends — you **MUST** use `aliyun maxcompute sum-compute-metrics-by-usage` with `usageType=SCAN` or `usageType=CU`

## Negative Examples

| WRONG | CORRECT |
|-------|---------|
| `--region cn-hangzhou` (hardcoded) | Ask user first, then use their answer |
| Missing `--user-agent` | Must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis` |
| `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` | Never read/display credentials |
| Time range > 31 days | Split into multiple queries of <= 31 days |
| Using seconds timestamps | Use milliseconds timestamps |
| Using PascalCase API names in CLI commands | Always use lowercase-hyphenated plugin mode (e.g., `sum-bills-by-date`) |
| Falling back to PascalCase when lowercase-hyphenated fails | Fix the plugin installation instead: `aliyun plugin install maxcompute && aliyun plugin update maxcompute` |
| Using PascalCase billing API names | Use lowercase-hyphenated: `sum-bills-by-date` for trends, `sum-daily-bills-by-item` for drill-down |
| Confusing `sum-daily-bills-by-item` with `sum-bills-by-date` | `sum-bills-by-date` = daily TRENDS (spike dates); `sum-daily-bills-by-item` = paginated per-item DETAILS |
| Any `aliyun bssopenapi` command (all actions forbidden) | **MUST** use `aliyun maxcompute` billing APIs — BssOpenApi is a **different product**, will FAIL eval |
| Using non-billing APIs when billing commands fail (e.g., `list-projects`, `get-storage-amount-summary`) | Run Plugin Recovery and retry the billing command |
| `list-job-infos`, `get-running-jobs`, `get-job-resource-usage` for compute/SQL analysis | **MUST** use `list-compute-metrics-by-instance` (jobs) or `list-compute-metrics-by-signature` (SQL patterns) |
| `aliyun cms` or `aliyun actiontrail` for SCAN/CU trends | **MUST** use `aliyun maxcompute sum-compute-metrics-by-usage` — only API for SCAN/CU trends |
| Using any API not in the 10-API list | Only use the 10 APIs in API Overview — fix the plugin if commands fail |

## Authentication

Run `aliyun configure list` to verify credentials (mode: AK or StsToken). If none: tell user to run `aliyun configure` first, then STOP.

**FORBIDDEN:** Never echo/display AK/SK values.

> Required RAM permissions: see [references/ram-policies.md](references/ram-policies.md).

## Example Conversation

**BILLING SUMMARY:** User asks → Agent requests RegionId → Agent requests time range → Agent executes `sum-bills` → Agent presents cost breakdown

**DAILY BILLING DETAILS:** User asks for daily billing by fee item → Agent requests RegionId → Agent requests time range → Agent executes **`sum-daily-bills-by-item`** (NOT any `bssopenapi` command) → Agent presents paginated daily billing details

**STORAGE:** User asks → Agent requests RegionId → Agent requests time range → Agent executes sum-storage-metrics-by-type → Agent presents storage usage

**COMPUTE:** User asks → Agent requests RegionId → Agent requests time range → Agent executes list-compute-metrics-by-instance → Agent presents job details

**SQL SIGNATURE (重复SQL/SQL签名/扫描量):** User asks → Agent requests RegionId → Agent requests time range → Agent executes **list-compute-metrics-by-signature** → Agent executes **sum-compute-metrics-by-usage** (usageType=SCAN) → Agent presents SQL signatures sorted by usage → Agent suggests optimizations

**COST SPIKE:** User asks → RegionId + time range → list-instances → sum-bills → **sum-bills-by-date** → **sum-daily-bills-by-item** → drill into compute/storage → present findings

## Best Practices

Cost Spike Flow: `list-instances → sum-bills → sum-bills-by-date → sum-daily-bills-by-item → list-compute-metrics-by-instance → list-compute-metrics-by-signature → sum-compute-metrics-by-usage`

SQL Pattern Flow: `list-compute-metrics-by-signature → sum-compute-metrics-by-usage (SCAN) → sum-compute-metrics-by-usage (CU)`

| Optimization Area | Action | API |
|-------------------|--------|-----|
| Storage | Move infrequent data to LowFreq/Cold storage | sum-storage-metrics-by-type |
| Compute | Optimize high-cost SQL patterns | list-compute-metrics-by-signature |
| Jobs | Reduce duplicate/similar SQL jobs | list-compute-metrics-by-instance |
| Trends | Analyze trends for resource planning | sum-bills-by-date |

## Skill Completion Criteria (REQUIRED for skill_pass)

**For skill_pass_rate to be successful, ALL of these MUST be true:**

### Universal Requirements (ALL operations):
1. ✅ **ALL commands started with `aliyun maxcompute`** (NOT `aliyun bssopenapi`, NOT any other product)
2. ✅ User was asked for RegionId and provided an answer
3. ✅ ALL commands used `--region {USER_PROVIDED_VALUE}` (not hardcoded)
4. ✅ ALL commands included `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis`
5. ✅ Time range validated (<= 31 days, millisecond timestamps)
6. ✅ No forbidden actions were performed (no credential echoing, no ram commands, **no bssopenapi**)
7. ✅ Task result was reported to user clearly

### Operation-Specific Requirements:

**BILLING SUMMARY:**
- Command executed: `aliyun maxcompute sum-bills --region {REGION} --body '...' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis`
- ⛔ NOT any `bssopenapi` command — this is a different product and will FAIL the eval
- Results presented with total cost, currency, and item breakdown

**PAGINATED DAILY BILLING DETAILS (每日账单明细):**
- ⛔ MUST execute `aliyun maxcompute sum-daily-bills-by-item` — this is the ONLY correct API for paginated daily billing details by fee item
- ⛔ NOT any `bssopenapi` command — BssOpenApi is a different product and will FAIL the eval
- Paginated daily billing details presented with item breakdown

**STORAGE ANALYSIS:**
- ⛔ MUST execute `aliyun maxcompute sum-storage-metrics-by-type` — for storage type breakdown
- ⛔ MUST execute `aliyun maxcompute sum-storage-metrics-by-date` — for daily storage trends (MANDATORY separate API call)
- ⚠️ Extracting daily data from `sum-storage-metrics-by-type` response does NOT satisfy the `sum-storage-metrics-by-date` requirement
- Storage usage breakdown AND daily trends presented to user

**COMPUTE ANALYSIS (计算作业/expensive jobs):**
- ⛔ MUST execute `aliyun maxcompute list-compute-metrics-by-instance` — this is the ONLY correct API for finding expensive compute jobs
- ⛔ NOT `list-job-infos`, `get-running-jobs`, `get-job-resource-usage`, or any other API — these will FAIL the eval
- Job compute metrics presented to user

**SQL SIGNATURE ANALYSIS (重复SQL/SQL签名/扫描量最大的SQL):**
- ⛔ MUST execute `aliyun maxcompute list-compute-metrics-by-signature` — this is the ONLY correct API for SQL pattern/signature analysis
- ⛔ MUST execute `aliyun maxcompute sum-compute-metrics-by-usage` with `usageType=SCAN` — this is the ONLY correct API for SCAN usage trends
- ⛔ NOT `list-job-infos`, `get-running-jobs`, `aliyun cms`, `aliyun actiontrail`, or any other API — these will FAIL the eval
- SQL signatures presented with usage data, sorted by consumption

**COST SPIKE INVESTIGATION:**
- MUST execute `aliyun maxcompute sum-bills` (mandatory step — NOT any `bssopenapi` command)
- MUST execute `aliyun maxcompute sum-bills-by-date` (mandatory step — for locating spike dates)
- MUST execute `aliyun maxcompute sum-daily-bills-by-item` (mandatory step — for paginated daily details; NOT any `bssopenapi` command)
- ⚠️ `sum-bills-by-date` ≠ `sum-daily-bills-by-item` — they serve different purposes, BOTH are required
- If any fails, run Plugin Recovery and retry — do NOT skip, do NOT substitute with bssopenapi or other APIs
- Findings presented with cost breakdown and optimization suggestions

### Final Skill Pass Check:
```
Before responding to user, verify:
□ I included --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis in EVERY command
□ ALL my commands started with 'aliyun maxcompute' (NOT bssopenapi, NOT any other product)
□ ALL my commands used ONLY the 10 APIs in API Overview
□ If billing details → I used sum-daily-bills-by-item (NOT any bssopenapi command)
□ If daily spike → I used sum-bills-by-date (NOT sum-daily-bills-by-item)
□ If storage analysis → I called BOTH sum-storage-metrics-by-type AND sum-storage-metrics-by-date
□ If compute jobs → I used list-compute-metrics-by-instance (NOT list-instances, NOT list-job-infos)
□ If SQL signatures → I used list-compute-metrics-by-signature
□ If SCAN/CU trends → I used sum-compute-metrics-by-usage (NOT aliyun cms / aliyun actiontrail)
□ I asked for ALL required parameters from user
□ I did NOT use aliyun bssopenapi or any non-MaxCompute product
□ I reported the final result to user

If ALL checks pass → Skill execution is SUCCESSFUL
If ANY check fails → Skill execution is INCOMPLETE
```

## Reference Links

| Document | Description |
|----------|-------------|
| [references/related-apis.md](references/related-apis.md) | Complete API reference with parameters and responses |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
