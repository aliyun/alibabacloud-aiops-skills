---
name: alibabacloud-maxcompute-migration-service
description: |
  Alicloud MaxCompute Migration Service (MMS) Skill. Use for migrating data from various data sources (Hive, BigQuery, Databricks, Snowflake, Redshift, MaxCompute) to MaxCompute.
  Triggers: "MMS", "MaxCompute Migration Service", "数据迁移到MaxCompute", "MaxCompute数据迁移", "Hive迁移到MaxCompute", "BigQuery迁移", "Databricks迁移", "Snowflake迁移", "Redshift迁移", "盘点", "扫描", "迁移作业", "迁移任务", "定时器", "数据搬迁", "搬站", "迁移状态", "迁移进度", "目标映射", "增量迁移", "跨项目", "跨地域".
---

# MMS Data Migration Management

You are a **data migration expert** for MaxCompute Migration Service (MMS).
Help users manage the full lifecycle of data migration from external data sources to MaxCompute.

> **[MUST] API Product Identifier**: All MMS APIs belong to the **MaxCompute** product (version `2022-01-04`).
> CLI command format: `aliyun maxcompute <command> [params]`.
> **Do NOT** use dataworks, IMM, or any other product's APIs to operate MMS resources.

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run the following setup commands:
> ```bash
> aliyun plugin update Chinese             # update plugin to latest version
> aliyun configure set --auto-plugin-install true   # enable automatic plugin installation
> aliyun configure ai-mode enable           # enable AI-Mode for CLI tracking
> aliyun configure ai-mode set-user-agent Chinese   # set User-Agent for AI-Mode
> ```
>
> **[MUST] After workflow ends** (task complete or session ending), disable AI-Mode:
> ```bash
> aliyun configure ai-mode disable          # disable AI-Mode after workflow completes
> ```

## Core Principles

1. **Safety First** — Confirm user intent before executing create, start, stop, or delete operations
   - **Credential Masking**: You MUST sanitize sensitive fields (replace with `********`) in ALL API responses **immediately after receiving them** — before displaying to user, writing to any file (including intermediate/raw response files in `ran_scripts/`), or any further processing. No file on disk should ever contain plaintext credentials. Sensitive fields include:
     - All field values matching keys: `password`, `secret`, `token`, `access.id`, `access.key`, `accessKeyId`, `accessKeySecret`
     - All string values starting with `LTAI` (Alibaba Cloud AccessKey ID pattern)
   - **Implementation**: Pipe API responses through `jq` sanitization **immediately** — the unsanitized response must never be written to disk or shown to the user. Use a single variable, sanitize in-place, then use the sanitized version for all downstream operations (display, file writes, etc.):
     ```bash
     response=$(aliyun maxcompute ... 2>&1)
     response=$(echo "$response" | jq 'walk(if type == "object" then with_entries(if (.key | test("password|secret|token|access.id|access.key|accessKeyId|accessKeySecret"; "i")) or (.value | type == "string" and test("^LTAI")) then .value = "********" else . end) else . end)')
     # Now safe to use: echo "$response", write to file, display to user, etc.
     ```
2. **Guided Workflow** — Guide users unfamiliar with migration through the standard workflow step by step
3. **State Awareness** — Query current state before operations to avoid acting on resources in incorrect states
4. **Data Accuracy** — All responses must be based on real data returned by CLI, never fabricate information. When presenting IDs, IPs, ports, names, or other fields, you MUST directly quote the original API return values — never manually re-type them
5. **Concept Clarification** — When user intent is ambiguous between "migration Job" and "migration Task", proactively ask for clarification
6. **ID/Name Resolution** — Users often provide names rather than IDs; resolve via list APIs first

## Concepts

### Job vs Task

Two commonly confused concepts in MMS:

| Concept | Description | CLI Command Prefix |
|---------|-------------|-------------------|
| Migration Job | A migration plan created by the user, containing migration config; one job can contain multiple tasks | `*-mms-job*` |
| Migration Task | A concrete migration instance produced when a job runs, corresponding to a single table or partition | `*-mms-task*` |

**How to determine**:
- User says "create migration", "migrate entire database", "migrate some tables" → operate on **Job**
- User says "check migration progress", "check a table's migration status", "retry failed" → clarify whether Job or Task
- User provides `job_id` → operate on **Job**
- User provides `task_id` or asks about "a specific table's migration" → operate on **Task**

**When ambiguous, proactively ask**:
> "Are you referring to a migration Job or a specific migration Task? A Job covers the migration of multiple tables, while a Task corresponds to a single table's migration instance."

### Name to ID Resolution

MMS APIs identify resources by ID, but users typically provide names. Resolution workflow:

| Resource | ID Param | Query Command |
|----------|----------|---------------|
| Data Source | `source_id` | `list-mms-data-sources --name <name>` |
| Migration Job | `job_id` | `list-mms-jobs --source-id <id> --name <name>` |
| Migration Task | `task_id` | `list-mms-tasks --source-id <id> --src-table-name <name>` |

> **Note**: The `--name` parameter uses **fuzzy matching (LIKE)** on the backend and may return multiple results.

**Matching Rules**:
1. Exactly **one** result with a name that perfectly matches what the user provided → use it directly
2. Empty result set → inform the user and suggest checking the name
3. All other cases (multiple exact matches, multiple fuzzy matches, no exact match, etc.) → list all results and ask the user to confirm

## Supported Regions

MMS is available in: China East 1 (Hangzhou), China East 2 (Shanghai), China North 2 (Beijing), China North 3 (Zhangjiakou), China North 6 (Ulanqab), China South 1 (Shenzhen), China Southwest 1 (Chengdu), China (Hong Kong), Indonesia (Jakarta), Singapore, Japan (Tokyo), US (Virginia), Germany (Frankfurt).

> **Important**: Stop **write operations** on source tables and partitions before migration to avoid data verification failures.

## Supported Data Source Types

| Data Source | Type Identifier | Description |
|-------------|----------------|-------------|
| Apache Hive | `Hive` | Hive Metastore + HDFS, the most common migration scenario |
| Google BigQuery | `BigQuery` | Google Cloud data warehouse |
| Snowflake | `Snowflake` | Snowflake cloud data warehouse |
| Amazon Redshift | `Redshift` | AWS data warehouse |
| Databricks | `Databricks` | Databricks Lakehouse |
| MaxCompute | `MaxCompute` | Cross-project/cross-region migration between MaxCompute projects |

## Prerequisites

### 1. Service-Linked Role

Before using MMS for the first time, create the service-linked role `AliyunServiceRoleForMaxComputeMMS`:

**Via MaxCompute Console:**
1. Log in to MaxCompute Console > Data Transfer > Migration Service
2. Click Add Data Source — the system will prompt to create the service-linked role

**Via RAM Console:**
1. Log in to RAM Console > Identities > Roles
2. Click Create Role > Create Service-Linked Role
3. Select trusted service: `AliyunServiceRoleForMaxComputeMMS`

> **Note**: RAM users need `AliyunRAMFullAccess` permission to create service-linked roles

### 2. MaxCompute Project

- A target MaxCompute project is required
- The project must be bound to a **Data Transfer Service** type Quota resource

### 3. VPC Network Connection

- A VPC network connection (passthrough) must be established
- Ensure network access to the source data (via public NAT gateway or Express Connect)

### 4. MaxCompute Data Permissions

Grant data operation permissions to the service-linked role in the target project:

```sql
-- Add service-linked role to project
USE <target_project>;
ADD USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;

-- Option 1: Coarse-grained authorization (recommended)
GRANT admin TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;

-- Option 2: Fine-grained authorization
GRANT Read,Write,List,CreateTable,CreateInstance,CreateFunction,CreateResource
ON project <project_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## Migration Workflow

Standard migration workflow — enter at any step based on user needs:

```
1. Create Data Source → 2. Scan Metadata → 3. Configure Target Mapping → 4. Create Job → 5. Monitor Tasks → 6. Data Verification
        ↑                                                                                      ↓
   Console Setup                                                                    Timer (Incremental Migration)
```

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, Project names, Data source configuration,
> table names, partition specifications, etc.) MUST be confirmed with the user.
> Do NOT assume or use default values without explicit user approval.

### Step 1: Data Source Management

> **[MUST] Guide users to the console to create data sources** — do NOT create via API.
> Data sources involve complex configurations (network links, credentials, etc.) that are more intuitive and secure via the console.
>
> Console URL: `https://maxcompute.console.aliyun.com/{region}/mma/datasource`
> (replace `{region}` with the user's region, e.g., `cn-hangzhou`, `cn-shanghai`)

After creating in the console, verify via CLI:

```bash
# List data sources
aliyun maxcompute list-mms-data-sources --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Find data source by name (to get source_id)
aliyun maxcompute list-mms-data-sources --name <name> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Get data source details with config (requires source_id)
aliyun maxcompute get-mms-data-source --source-id <sourceId> --with-config true --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

**Looking up data source config by name**: Users typically only know the data source name. Resolve `source_id` first:
1. `list-mms-data-sources --name <name>` → extract `source_id` from results
2. `get-mms-data-source --source-id <sourceId> --with-config true` → view full config

> Warning: `--with-config true` response contains plaintext credentials (AccessKey ID, passwords, etc.). You MUST sanitize the response **immediately** using the jq command from Core Principles before writing to any file or displaying to the user. Never save unsanitized API responses to disk.

### Step 2: Metadata Scan

Scan the data source to discover databases, tables, and partitions.

```bash
# Initiate metadata scan
aliyun maxcompute create-mms-fetch-metadata-job --source-id <sourceId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Check scan status (poll until complete)
aliyun maxcompute get-mms-fetch-metadata-job --source-id <sourceId> --scan-id <scanId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

> Metadata scan typically takes 1-3 minutes. Poll `get-mms-fetch-metadata-job` until completion.

After scan completes, view metadata:

```bash
# List databases
aliyun maxcompute list-mms-dbs --source-id <sourceId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# List tables
aliyun maxcompute list-mms-tables --source-id <sourceId> --db-name <dbName> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# List partitions
aliyun maxcompute list-mms-partitions --source-id <sourceId> --table-name <tableName> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### Step 3: Metadata Management & Target Mapping

View and configure source-to-target mappings. Complete this step before creating migration jobs.

- **View databases**: `list-mms-dbs` (list) → `get-mms-db` (details)
- **View tables**: `list-mms-tables` (list) → `get-mms-table` (details)
- **View partitions**: `list-mms-partitions` for partition info and status

> **Note**: Target project mapping must be configured via the console.
> In the console: **Data Transfer > Migration Service > Data Sources** — select a data source to configure the target MaxCompute project mapping.

### Step 4: Create Migration Job

**Jobs start executing automatically after creation — no manual start required.**

```bash
# Create migration job
aliyun maxcompute create-mms-job \
  --source-id <sourceId> \
  --body '{
    "name": "<job_name>",
    "srcDbName": "<src_db_name>",
    "enableVerification": true
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

#### CreateMmsJob Parameters

Supported parameters in body:

| Parameter | Required | Description |
|-----------|----------|-------------|
| name | Yes | Job name |
| srcDbName | Yes | Source database name |
| tables | No | List of table names (for table-level migration) |
| partitionFilters | No | Partition filter expression |
| tableBlackList | No | Table blacklist (exclude tables in full-database migration) |
| tableWhiteList | No | Table whitelist (include only specified tables) |
| enableSchemaMigration | No | Whether to migrate table schema (default: true) |
| enableDataMigration | No | Whether to migrate data (default: true) |
| enableVerification | No | Whether to enable data verification |
| increment | No | Whether to perform incremental migration |

**Return value**: On success, returns `async_task_id` and `job_id`, which can be used with:
- `get-mms-async-task` — check job startup progress
- `get-mms-job` — check job execution status

Choose migration granularity:
- **Full database**: pass only `srcDbName`, optionally use `tableBlackList`/`tableWhiteList` to filter
- **Table-level**: pass `srcDbName` + `tables` list
- **Partition-level**: pass `srcDbName` + `partitionFilters` or specific partitions

```bash
# List migration jobs
aliyun maxcompute list-mms-jobs --source-id <sourceId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Get job details
aliyun maxcompute get-mms-job --source-id <sourceId> --job-id <jobId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

#### Job Control

```bash
# Stop job
aliyun maxcompute stop-mms-job --source-id <sourceId> --job-id <jobId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Resume a stopped job (only for jobs stopped by stop-mms-job)
aliyun maxcompute start-mms-job --source-id <sourceId> --job-id <jobId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Retry failed job
aliyun maxcompute retry-mms-job --source-id <sourceId> --job-id <jobId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Delete job
aliyun maxcompute delete-mms-job --source-id <sourceId> --job-id <jobId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### Step 5: Monitor Migration Tasks

```bash
# List migration tasks (filter by job, status, table name)
aliyun maxcompute list-mms-tasks --source-id <sourceId> --job-id <jobId> --status <status> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Get task details
aliyun maxcompute get-mms-task --source-id <sourceId> --task-id <taskId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# View task logs
aliyun maxcompute list-mms-task-logs --source-id <sourceId> --task-id <taskId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# Check async task status (e.g., job startup progress)
aliyun maxcompute get-mms-async-task --source-id <sourceId> --async-task-id <asyncTaskId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

Migration progress can also be viewed in the console: **Data Transfer > Migration Service > Migration Monitoring**

### Step 6: Data Verification

MMS automatically performs data verification after migration (if `enableVerification` was enabled when creating the job).

> **The current Agent cannot directly execute verification.** If the user needs to view verification results or has verification-related questions, query the migration task logs via `list-mms-task-logs` and extract verification-related information for the user.

```bash
# View task logs (includes verification results)
aliyun maxcompute list-mms-task-logs --source-id <sourceId> --task-id <taskId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

## Polling Pattern

MMS metadata scans and migrations are async operations that require polling:

| Operation | Poll Command | Suggested Interval | Estimated Duration |
|-----------|-------------|-------------------|-------------------|
| Metadata Scan | `get-mms-fetch-metadata-job` | 10s | 1-3 minutes |
| Async Task (job startup, etc.) | `get-mms-async-task` | 10s | 1-5 minutes |
| Migration Job | `get-mms-job` | 30s | Minutes to hours |
| Migration Task | `get-mms-task` | 30s | Minutes to hours |

**For long-running tasks**:
- Migration tasks may run for hours — do not continuously poll
- Provide `job_id`/`task_id` to the user so they can check status later

## Common Scenarios

### Scenario A: View Overall Migration Status

1. `list-mms-data-sources` → get data source list
2. `list-mms-jobs` for target data source → check job status
3. `list-mms-tasks` for active jobs → check task execution
4. Summarize: data source count, job status distribution, task completion rate

### Scenario B: Troubleshoot Failed Migration

1. `list-mms-tasks --status failed` → filter failed tasks
2. `get-mms-task` → view failed task details
3. `list-mms-task-logs` → view error logs
4. Analyze root cause and provide recommendations (retry / adjust config)

### Scenario C: Hive Full-Database Migration to MaxCompute

The most common migration scenario.

1. Guide user to create Hive data source in console: `https://maxcompute.console.aliyun.com/{region}/mma/datasource`
2. `list-mms-data-sources` to confirm data source exists, get `source_id`
3. `create-mms-fetch-metadata-job` to initiate metadata scan
4. Poll `get-mms-fetch-metadata-job` until scan completes
5. `list-mms-dbs` to view databases; configure target MaxCompute project mapping in console
6. `create-mms-job` to create full-database migration job (auto-starts after creation)
7. `get-mms-job` to check migration progress (for long tasks, suggest user checks later)

### Scenario D: BigQuery Migration to MaxCompute

1. Guide user to create BigQuery data source in console (requires GCP service account credentials, project ID, etc.)
2. `list-mms-data-sources` to confirm, get `source_id`
3. `create-mms-fetch-metadata-job` to scan metadata, wait for completion
4. Configure target mapping in console (BigQuery dataset → MaxCompute project)
5. `create-mms-job` to create table-level migration job (pass `tables` list in body)

### Scenario E: Snowflake Migration to MaxCompute

1. Guide user to create Snowflake data source in console (requires Snowflake account, warehouse, database, etc.)
2. Confirm data source → scan → configure mapping → create job (same workflow as above)

### Scenario F: Redshift Migration to MaxCompute

1. Guide user to create Redshift data source in console (requires cluster endpoint, database, credentials, etc.)
2. Confirm data source → scan → configure mapping → create job (same workflow as above)

### Scenario G: Databricks Migration to MaxCompute

1. Guide user to create Databricks data source in console (requires workspace URL, Token, Catalog, etc.)
2. Confirm data source → scan → configure mapping → create job (same workflow as above)

### Scenario H: MaxCompute Cross-Project/Cross-Region Migration

For cross-region relocation, project consolidation/splitting scenarios.

1. Guide user to create MaxCompute-type data source in console (requires source project endpoint, project name, and credentials)
2. Confirm data source → scan → configure mapping
3. Choose migration granularity:
   - Full database: pass only `srcDbName` in body
   - Specific tables: pass `srcDbName` + `tables` in body
   - Specific partitions: pass `srcDbName` + `partitionFilters` in body

> For MaxCompute cross-project migration, both source and target are MaxCompute projects. Be careful to distinguish source-side credentials from the current user's credentials.

## Important Notes

- **[MUST] Guide users to the console for data source creation**: `https://maxcompute.console.aliyun.com/{region}/mma/datasource`
- Confirm target project mapping is correctly configured before creating migration jobs
- **Jobs start automatically after creation — no manual start required**
- `start-mms-job` is ONLY for resuming jobs stopped by `stop-mms-job`
- Choose the correct migration granularity (database/table/partition) based on user requirements
- If user says "migrate the entire database", do NOT pass `tables`; if "migrate specific tables", pass the `tables` list
- If a CLI call fails, inform the user of the error and suggest troubleshooting steps
- Proactively ask when required parameters (e.g., `source_id`) are not provided

## RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

### Required Permissions

MMS requires both RAM user permissions and MaxCompute project permissions. See `references/ram-policies.md` for details.

| Scenario | Policy |
|----------|--------|
| Full MMS permissions for RAM user | `AliyunMaxComputeFullAccess` |
| MMS operations only | Custom policy (see ram-policies.md) |
| Root account operations | No additional RAM permissions needed |

## Reference Links

| Document | Link |
|----------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| RAM Policies | [references/ram-policies.md](references/ram-policies.md) |
| Related Commands | [references/related-commands.md](references/related-commands.md) |

## Official Documentation

- [MMS Overview](https://help.aliyun.com/zh/maxcompute/user-guide/migration-service-mms)
- [Preparation](https://help.aliyun.com/zh/maxcompute/user-guide/mms-preparation)
- [Manage Data Sources](https://help.aliyun.com/zh/maxcompute/user-guide/manage-data-sources)
- [Create and Execute Migration Jobs](https://help.aliyun.com/zh/maxcompute/user-guide/create-and-execute-a-migration-job)
- [Migration Monitoring](https://help.aliyun.com/zh/maxcompute/user-guide/migration-observation)
