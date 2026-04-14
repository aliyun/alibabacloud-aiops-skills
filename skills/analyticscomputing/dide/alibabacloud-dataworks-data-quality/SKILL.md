---
name: alibabacloud-dataworks-data-quality
description: |
  DataWorks Data Quality (Read-Only): Query rule templates, data quality monitors (scans), alert rules, and scan run records/logs.
  Uses aliyun CLI to call dataworks-public OpenAPI (2024-05-18). All operations are read-only — no create, update, or delete.
  Trigger keywords: DataWorks data quality, quality rule, quality template, quality monitor, quality scan, scan run,
  quality check result, quality alert rule, quality run log, DQ monitor, data quality execution, quality pass/fail,
  list quality scans, get quality scan, query quality result, quality monitoring detail, quality run history.
  Not triggered: creating/updating/deleting quality rules or monitors, data source management, compute resource management,
  resource group management, workspace member management, data development tasks, scheduling configuration.
---

# DataWorks Data Quality (Read-Only)

Query and investigate **Rule Templates**, **Data Quality Monitors**, **Alert Rules**, and **Scan Run Records** in Alibaba Cloud DataWorks.

> **Coverage**: All Get/List read-only OpenAPIs under DataWorks Data Quality, totaling 9:
> ListDataQualityTemplates / GetDataQualityTemplate · ListDataQualityScans / GetDataQualityScan ·
> ListDataQualityAlertRules / GetDataQualityAlertRule · ListDataQualityScanRuns / GetDataQualityScanRun / GetDataQualityScanRunLog
> **Excludes** write operations: Create / Update / Delete / CreateDataQualityScanRun.

> **Read-Only Skill**: This skill supports query operations only. Any write operation request **must be blocked immediately** — direct the user to the DataWorks console.

## Architecture

```
DataWorks Data Quality
├── Rule Templates ─── Reusable metric logic definitions (built-in & custom)
│
├── Data Quality Monitors (Scans) ─── Monitor tasks bound to tables, with rules and trigger config
│   └── Alert Rules ─── Notification rules tied to a monitor (channels, recipients, conditions)
│
└── Scan Runs ─── Execution records each time a monitor runs
    └── Scan Run Logs ─── Detailed execution logs for a run
```

---

## Global Rules

### Prerequisites

1. **Aliyun CLI >= 3.3.1**: `aliyun version` (Installation: see [references/cli-installation-guide.md](references/cli-installation-guide.md))
2. **First-time use**: `aliyun configure set --auto-plugin-install true`
3. **jq** (recommended for output formatting): `which jq`
4. **Credential status**: `aliyun configure list`, verify valid credentials exist

> **Security Rules**: **DO NOT** read/print/echo AK/SK values. **ONLY** use `aliyun configure list` to check credential status.

### Command Formatting

- **User-Agent (mandatory)**: All `aliyun` CLI commands **must** include `--user-agent AlibabaCloud-Agent-Skills`.
- **Timeout (mandatory)**: All `aliyun` CLI commands **must** include `--connect-timeout 5 --read-timeout 10`. These match the CLI built-in defaults and make the timeout policy explicit.
- **Single-line commands**: Construct as a **single-line string**; do not use `\` for line breaks.
- **jq step-by-step**: First execute the `aliyun` command to get JSON, then pipe to `jq` for formatting.
- **Endpoint mandatory**: When specifying `--region`, you **must** also add `--endpoint dataworks.<REGION_ID>.aliyuncs.com`.

### Parameter Confirmation

**Must be explicitly provided by user — do not assume or use defaults**:
- `ProjectId`: Core parameter for every query — must be confirmed
- `Id`-type resource identifiers: template ID, monitor ID, alert rule ID, scan run ID
- `region`: Affects endpoint — must be confirmed

**Can use default values directly — no user confirmation needed**:
- `PageNumber`: default `1`
- `PageSize`: default `10`
- `SortBy`: default `ModifyTime Desc` or `CreateTime Desc`

**Ask contextually — only collect when the user has a specific need**:
- `Name`, `Table`: fuzzy search keywords
- Time range: `CreateTimeFrom` / `CreateTimeTo`
- `Status`: collect only when the user explicitly wants to filter by a specific status

> If the user has already provided `ProjectId`, `Id`, or `region` in the conversation, reuse them directly without re-confirmation.

### Time Parameter Conversion

When the user describes time in natural language, convert it to millisecond timestamps automatically. Do **not** ask the user to provide raw timestamps.

- `"yesterday"` → yesterday `00:00:00` to `23:59:59`
- `"today"` → today `00:00:00` to current time
- `"last N days"` → current time minus `N × 24` hours through current time
- If the time phrase is ambiguous, ask a clarification question and offer a suggested range

### Query Result Presentation

After every query, present the result in a decision-friendly way:

- **List queries**: use a Markdown table for key fields such as ID, name, status, and time; do **not** dump raw JSON
- **Detail queries**: present a short summary first, then expand full `Spec` only if the user asks
- **Abnormal status**: highlight `Fail` / `Error` / `Warn`, and proactively recommend the next diagnostic step
- **Empty result**: explain likely causes such as wrong `ProjectId`, wrong `region`, or filters that are too strict

### Pagination

- First query uses the default `PageSize` of `10`
- If the number of returned rows equals `PageSize`, proactively offer next page or a larger `PageSize`
- Do not fetch more than `100` records in a single request

### ⚠️ Read-Only Execution Gate

> **MANDATORY**: Before responding to ANY request, check whether it involves a write operation.
> If YES: **BLOCK immediately**. Do NOT call any API. Respond with:
> "This skill supports query operations only and cannot perform create/update/delete. Please go to the [DataWorks Console](https://dataworks.console.aliyun.com) for configuration."

**Quick Reference — All Blocked Operations**：

| Operation Type | Blocked APIs |
|----------------|-------------|
| Create | CreateDataQualityTemplate, CreateDataQualityScan, CreateDataQualityScanRun, CreateDataQualityAlertRule |
| Update | UpdateDataQualityTemplate, UpdateDataQualityScan, UpdateDataQualityAlertRule |
| Delete | DeleteDataQualityTemplate, DeleteDataQualityScan, DeleteDataQualityAlertRule |
| Trigger | CreateDataQualityScanRun (manual execution trigger) |

### RAM Permissions

All operations require `dataworks:<APIAction>` permissions on the target workspace.
> Full permission matrix: [references/ram-policies.md](references/ram-policies.md)

---

## Quick Start: Data Quality Investigation

When the user request is vague, use the following default path:

1. **Environment check** — Confirm CLI and credentials per Prerequisites. After completion, proactively suggest the workspace confirmation step.
2. **Confirm workspace** — Confirm `ProjectId` and `region`. If either is missing, use Module 0. After completion, proactively suggest listing monitors.
3. **List monitors** — Call `ListDataQualityScans`, present a table, and let the user choose a monitor. After completion, proactively suggest monitor detail.
4. **Check monitor detail** — Call `GetDataQualityScan`, summarize rules, monitored object, and trigger mode. After completion, proactively suggest recent runs.
5. **Check run history** — Call `ListDataQualityScanRuns`, default to the most recent 10 rows, and highlight abnormal status. After completion, proactively suggest drilling into one run.
6. **Drill into failed or warned runs** — For `Fail` / `Error` / `Warn`, call `GetDataQualityScanRun` and summarize per-rule results. After completion, proactively suggest log inspection.
7. **Fetch execution logs** — If `Results` shows failed rules or runtime errors, call `GetDataQualityScanRunLog` to locate root cause. After completion, proactively suggest whether further analysis is needed.

---

## Next Step Guidance

| Completed Operation | Recommended Next Step |
|---------------------|----------------------|
| ListDataQualityTemplates | "Would you like to view the full configuration of a specific template? (GetDataQualityTemplate)" |
| GetDataQualityTemplate | "Would you like to view monitors that use this template? (ListDataQualityScans)" |
| ListDataQualityScans | "Select a monitor to view its full configuration? (GetDataQualityScan)" |
| GetDataQualityScan | "View associated alert rules (ListDataQualityAlertRules) or recent run history (ListDataQualityScanRuns)?" |
| ListDataQualityAlertRules | "View details for a specific alert rule? (GetDataQualityAlertRule)" |
| GetDataQualityAlertRule | "Return to view run history for the associated monitor? (ListDataQualityScanRuns)" |
| ListDataQualityScanRuns | "View detailed results for a specific run? (GetDataQualityScanRun)" |
| GetDataQualityScanRun (Pass) | "This run passed. Would you like to view other run records or alert configuration?" |
| GetDataQualityScanRun (Fail/Error/Warn) | "Anomaly detected — recommend viewing execution logs to locate the root cause. (GetDataQualityScanRunLog)" |
| GetDataQualityScanRunLog (NextOffset=-1) | "Log retrieval complete. Is further analysis needed?" |
| GetDataQualityScanRunLog (NextOffset≠-1) | "Log not fully retrieved — continue fetching the next segment. (Retry with Offset)" |

---

## Trigger Rules

**Trigger scenarios**: Query data quality monitors/rules/templates/alerts/scan runs/logs, diagnose data quality check failures, view quality alert notification configuration, `list/get quality scan/rule/template/alert/run`

**Not triggered**:
- Creating/updating/deleting data quality configuration → Use DataWorks Console
- Data source/compute resource/resource group management → `alibabacloud-dataworks-infra-manage`
- Workspace query/member management → `alibabacloud-dataworks-workspace-manage`
- Data development node/scheduling configuration → `alibabacloud-dataworks-datastudio-develop`

---

## Interaction Flow

**Identify query intent → Environment check → Module 0 (if ProjectId/region missing) → Collect parameters → Execute command → Present results → Guide next step**

Common aliases: DW = DataWorks, DQ = Data Quality, scan = monitor, scan run = execution record

---

# Module 0: Workspace / ProjectId / Region Query

> If the `alibabacloud-dataworks-workspace-manage` skill is available, prefer using it for workspace lookup. The following is only a fallback.

```bash
aliyun dataworks-public ListProjects --user-agent AlibabaCloud-Agent-Skills --Status Available --PageSize 100
```

Rules:

- If the user provides only a workspace name, list candidate workspaces and ask the user to confirm the `ProjectId`
- If `ProjectId` is unknown, ask for it explicitly and never guess
- If `region` is unknown, offer common regions for confirmation: `cn-hangzhou`, `cn-shanghai`, `cn-beijing`, `cn-shenzhen`
- Once `ProjectId` and `region` are confirmed in the conversation, reuse them in later steps

Intent guidance:

- `"there's a data quality issue"` → ask whether the user wants monitor configuration, run records, or alert settings
- `"show me this table"` → start with `ListDataQualityScans --Table <TABLE_NAME>`
- If the intent is still unclear, ask the user to choose one of four modules: rule templates, monitors, alert rules, or scan runs

---

# Module 1: Rule Templates

Rule templates define reusable metric logic such as null rate, duplicate rate, row count, and custom SQL checks. Use this module when the user wants to know what a template checks, whether it is built-in or workspace-specific, and how its threshold logic is defined.

## Task 1.1: List Rule Templates (ListDataQualityTemplates)

```bash
aliyun dataworks-public ListDataQualityTemplates --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] [--ProjectId <PROJECT_ID>] [--Name <FUZZY_NAME>] [--Catalog <CATALOG_PATH>] [--PageNumber 1] [--PageSize 10]
```

How to interpret the result:

- `PageInfo.DataQualityTemplates[]` is the working set for user selection
- Show `Id`, a concise template name if present in `Spec`, owner, and modification time in a table
- If `ProjectId` is omitted, explain that the result is the system built-in template set
- Use `Catalog` and template naming patterns to tell the user what class of checks is available

## Task 1.2: Get Rule Template Details (GetDataQualityTemplate)

```bash
aliyun dataworks-public GetDataQualityTemplate --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --Id <TEMPLATE_ID>
```

How to interpret the result:

- Focus on `Spec`: summarize the metric logic, parameter definitions, and threshold expression
- Tell the user what this template checks and how pass/fail is decided
- Mention whether the template belongs to a workspace (`ProjectId` present) or is reused as a generic template
- Expand full `Spec` only when the user explicitly asks for raw detail

---

# Module 2: Data Quality Monitors

A data quality monitor (scan) is a concrete monitoring task bound to a table or field. Use this module to locate monitors, explain what they check, and understand how they are triggered.

## Task 2.1: List Data Quality Monitors (ListDataQualityScans)

```bash
aliyun dataworks-public ListDataQualityScans --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --ProjectId <PROJECT_ID> --PageNumber 1 --PageSize 10 [--Name <FUZZY_NAME>] [--Table <FUZZY_TABLE_NAME>] [--SortBy "ModifyTime Desc"]
```

How to interpret the result:

- `PageInfo.DataQualityScans[]` is the candidate monitor list; show `Id`, `Name`, `Description`, owner, and latest update time
- When `--Table` is used, explicitly tell the user these monitors are the likely matches for that table
- Use the table to help the user choose one target monitor before moving to detail query
- When the list is empty, suggest checking `ProjectId`, `region`, or relaxing `Name` / `Table`

## Task 2.2: Get Monitor Details (GetDataQualityScan)

```bash
aliyun dataworks-public GetDataQualityScan --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --Id <SCAN_ID>
```

How to interpret the result:

- `Spec`: summarize monitored object, rule count, core metrics, and threshold settings
- `Trigger`: explain whether the monitor is `ByManual` or `BySchedule`
- `ComputeResource` and `RuntimeResource`: mention them only when they help explain execution behavior
- `Parameters` and `Hooks`: summarize only if they affect how the run is triggered or analyzed
- Present a concise monitor summary first, then suggest alert-rule or run-history follow-up

---

# Module 3: Alert Rules

Alert rules define when notifications are sent and to whom. Use this module when the user asks who gets notified, through which channel, and under what condition.

**Receiver Type Quick Reference**

| ReceiverType | Description |
|-------------|-------------|
| AliUid | Specific Alibaba Cloud account UID |
| DataQualityScanOwner | Owner of the data quality monitor task |
| TaskOwner | Owner of the associated scheduling task |
| DingdingUrl | DingTalk custom robot Webhook |
| FeishuUrl | Feishu custom robot Webhook |
| WeixinUrl | WeCom Webhook |
| WebhookUrl | Generic Webhook URL |
| ShiftSchedule | On-call schedule (notify by shift) |

## Task 3.1: List Alert Rules (ListDataQualityAlertRules)

```bash
aliyun dataworks-public ListDataQualityAlertRules --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --ProjectId <PROJECT_ID> --PageNumber 1 --PageSize 10 [--DataQualityScanId <SCAN_ID>] [--SortBy "CreateTime Desc"]
```

How to interpret the result:

- `PageInfo.DataQualityAlertRules[]` should be summarized as: rule ID, condition, channels, receivers, and associated monitor IDs
- Translate `Notification.Channels` into user-friendly channel names such as DingTalk, email, Feishu, SMS, or Webhook
- Summarize `Notification.Receivers` by receiver type instead of showing nested raw JSON
- If `DataQualityScanId` is provided, explicitly state these are the alert rules attached to that monitor

## Task 3.2: Get Alert Rule Details (GetDataQualityAlertRule)

```bash
aliyun dataworks-public GetDataQualityAlertRule --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --Id <ALERT_RULE_ID>
```

How to interpret the result:

- Explain the alert condition in plain language
- Summarize notification channels and recipients with emphasis on who will be notified and how
- Call out whether the rule targets one monitor or multiple monitors
- If the user is diagnosing missing alerts, suggest returning to recent run history for the associated monitor

---

# Module 4: Scan Runs

A scan run is created every time a monitor executes. Use this module to inspect run history, diagnose failed checks, and read execution logs.

**Status Quick Reference**

| Status | Meaning | Recommended Path |
|--------|---------|-----------------|
| Pass | All rules passed | No action needed |
| Fail | At least one rule failed to meet the threshold | GetDataQualityScanRun → Results → GetDataQualityScanRunLog |
| Error | Execution error (engine error, insufficient resources) | GetDataQualityScanRunLog to view error details |
| Warn | Warning triggered but did not reach the blocking threshold | GetDataQualityScanRun → Results to view metric values |
| Running | Execution in progress | Wait for completion before querying |

## Task 4.1: List Scan Runs (ListDataQualityScanRuns)

```bash
aliyun dataworks-public ListDataQualityScanRuns --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --ProjectId <PROJECT_ID> [--DataQualityScanId <SCAN_ID>] [--Status <Pass|Running|Error|Fail|Warn>] [--CreateTimeFrom <TIMESTAMP_MS>] [--CreateTimeTo <TIMESTAMP_MS>] [--Filter '{"TaskInstanceId":"<INSTANCE_ID>"}'] [--SortBy "CreateTime Desc"] [--PageNumber 1] [--PageSize 20]
```

Filter quick reference:

| Scenario | Filter JSON Example |
|----------|---------------------|
| Filter by scheduling instance | `{"TaskInstanceId":"123456"}` |
| Filter by run number | `{"RunNumber":"2"}` |

How to interpret the result:

- `PageInfo.DataQualityScanRuns[]` should be shown as a table with `Id`, `Status`, `CreateTime`, `FinishTime`, and key runtime parameters
- Sort by recent time first so phrases like "most recent" map naturally to the first row
- Highlight `Fail`, `Error`, and `Warn`, then recommend drilling into `GetDataQualityScanRun`
- If the user asks for recent failures, combine `Status=Fail` with a converted time range instead of asking for timestamps

## Task 4.2: Get Scan Run Details (GetDataQualityScanRun)

```bash
aliyun dataworks-public GetDataQualityScanRun --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --Id <SCAN_RUN_ID>
```

How to interpret the result:

- `Status`: state clearly whether the run passed, failed, warned, errored, or is still running
- `Results`: extract each rule's status, actual metric value, threshold, and whether it caused the overall failure; present this as a table instead of raw JSON
- `Scan`: use it as configuration snapshot context only when it helps explain the failure
- `Parameters`: mention runtime parameters when they may have influenced the result
- If any rule is abnormal, proactively suggest `GetDataQualityScanRunLog`

## Task 4.3: Get Scan Run Log (GetDataQualityScanRunLog)

```bash
aliyun dataworks-public GetDataQualityScanRunLog --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --Id <SCAN_RUN_ID> [--Offset <BYTE_OFFSET>]
```

How to interpret the result:

- `Log` is the raw execution trace; summarize the root cause first, then provide key excerpts if needed
- `NextOffset = -1` means log retrieval is complete
- If `NextOffset != -1`, continue querying with the returned offset until completion when the user asks for the full log
- When logs are long, explain the main error path instead of pasting everything by default

---

## Best Practices

1. **List before detail** — Do not guess IDs. Use list queries first, then drill into a selected resource.
2. **Diagnose failures in order** — For `Fail`, check `GetDataQualityScanRun` results first, then read `GetDataQualityScanRunLog`.
3. **Separate built-in vs workspace templates** — Omit `ProjectId` for built-in templates; include it for workspace custom templates.
4. **Use a bounded time window** — For run-history queries, default to recent 24 hours or recent 10 rows to avoid oversized result sets.
5. **Proactively guide the next step** — After every query, suggest the most likely follow-up instead of waiting for the user to ask.
6. **Expand `Spec` on demand** — `Spec` is often verbose. Summarize first, expand only on request.

## Query Result Guidance

- **Empty list result**: Explain likely causes including wrong `ProjectId`, wrong `region`, or overly strict filters — suggest confirming parameters or relaxing filter conditions.
- **Spec field handling**: First extract monitored object, rule count, key thresholds, and trigger mode; expand full JSON only when the user requests it.
- **Abnormal status handling**: When encountering `Fail` / `Error` / `Warn`, do not just display the status — proactively provide the next diagnostic path.
- **Results field handling**: Present status, actual value, threshold, and conclusion per rule in a table — do not dump the raw array.

## Common Errors

| Error Code | Solution |
|------------|----------|
| Forbidden.Access / PermissionDenied | Check RAM permissions, see [references/ram-policies.md](references/ram-policies.md) |
| InvalidParameter | Verify parameter names, JSON shape, and required fields |
| EntityNotExists | Check whether the ID, `ProjectId`, and `region` match the target resource |
| InvalidPageSize | `PageSize` must be within the API-supported range, usually `1-100` |

## Region and Endpoint

Common: `cn-hangzhou`, `cn-shanghai`, `cn-beijing`, `cn-shenzhen`.
Endpoint format: `dataworks.<REGION_ID>.aliyuncs.com`

> Full region and endpoint list: [references/related-apis.md](references/related-apis.md)

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission configuration and policy examples |
| [references/related-apis.md](references/related-apis.md) | API parameter details and Region Endpoints |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
