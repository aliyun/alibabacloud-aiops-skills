---
name: alibabacloud-polardbx-ops
description: |
  Manage Alibaba Cloud PolarDB-X instance lifecycle and routine operations via the Aliyun CLI.
  Use when the user asks to create, delete, restart, scale, modify, monitor, or inspect PolarDB-X instances.
  Triggers: "polardb-x", "polardbx", "create polardb-x", "delete polardb-x", "restart polardb-x",
  "scale polardb-x", "upgrade polardb-x", "describe polardb-x", "polardb-x instance",
  "polardb-x parameters", "polardb-x slow log", "polardb-x performance", "polardb-x binlog"
---

# PolarDB-X Instance Management

Manage Alibaba Cloud PolarDB-X instances through the `aliyun polardbx` CLI: instance lifecycle, scaling, parameter management, monitoring, and logs.

This skill uses **intent routing**: identify the user's intent, run pre-flight checks, then load the relevant module reference document fully before generating any CLI command.

---

## Architecture

```
Alibaba Cloud PolarDB-X Instance Management
├── Instance Lifecycle    --> references/instance-lifecycle.md
│   ├── CreateDBInstance
│   ├── DeleteDBInstance
│   ├── RestartDBInstance
│   ├── DescribeDBInstanceAttribute
│   ├── DescribeDBInstances
│   ├── DescribeDBInstanceTopology
│   ├── DescribeTasks
│   ├── ModifyDBInstanceDescription
│   ├── ModifyDBInstanceMaintainTime
│   └── UpgradeDBInstanceKernelVersion
├── Scaling               --> references/scaling.md
│   ├── UpdatePolarDBXInstanceNode
│   ├── ModifyDBInstanceClass
│   └── DescribeScaleOutMigrateTaskList
├── Parameters            --> references/parameters.md
│   ├── DescribeDBInstanceConfig
│   ├── ModifyDBInstanceConfig
│   ├── DescribeParameters
│   ├── ModifyParameter
│   └── DescribeParameterTemplates
├── Instance Specs        --> scripts/spec_lookup.sh (spec code <-> cores/memory)
│   ├── Enterprise CN (CnClass)
│   ├── Enterprise DN (DnClass)
│   ├── Standard DBNodeClass
│   └── Naming Rules
└── Monitoring & Logs     --> references/monitoring-logs.md
    ├── DescribeDBNodePerformance
    ├── DescribeSlowLogRecords
    └── DescribeBinaryLogList
```

### Extended Modules

The following modules cover the full PolarDB-X (2020-02-02) API surface. See each reference file for the complete API spec.

```
├── Account Management      --> references/account-management.md
├── Database Management     --> references/database-management.md
├── Backup & Restore        --> references/backup-restore.md
├── Security & Access        --> references/security-access.md
├── SQL Audit & Compliance   --> references/sql-audit-compliance.md
├── Operation Tasks & Events --> references/operation-tasks.md
├── HA & Migration           --> references/ha-migration.md
├── Connection & Endpoint    --> references/connection-endpoint.md
├── Tags & Resource Group    --> references/tags-resourcegroup.md
├── Metadata & Query         --> references/metadata-query.md
├── Cold Storage             --> references/cold-storage.md
├── Data Evaluate & Migration--> references/data-evaluate-migration.md
├── SQL Flashback            --> references/sql-flashback.md
├── CDC (Log Engine)         --> references/cdc.md
├── Columnar                 --> references/columnar.md
├── GDN                      --> references/gdn.md
└── Mem0                     --> references/mem0.md
```

---

## Requirement Analysis

Before routing, analyze the user request:

1. Identify intent: create / delete / restart / describe / list / scale / modify parameters / view monitoring / view logs.
2. Extract required parameters: `RegionId`, instance identifier (`DBInstanceName` or `DBInstanceId`), `EngineVersion`, `DBInstanceClass`, node counts, time ranges, etc.
3. If any required parameter is missing, ask the user. Do NOT guess values or APIs.
4. After intent and parameters are clear, load the matched reference document **fully**, then construct the CLI command.

---

## Pre-flight Checks

Run these checks at the start of every skill invocation. Only load the referenced document if a check fails. If step 1/2/3/5 fails, read [references/cli-installation-guide.md](references/cli-installation-guide.md); if step 4 fails, read [references/ram-policies.md](references/ram-policies.md).

### 1. aliyun CLI version

```bash
aliyun --version
```

**Success:** Output contains `Alibaba Cloud Command Line Interface Version` and the version is >= `3.3.3`.

**Failure:** Read [references/cli-installation-guide.md](references/cli-installation-guide.md) section 1.

### 2. aliyun CLI plugin and configuration

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
aliyun configure list
```

**Success:** `aliyun configure list` shows at least one valid profile (AK, STS, or OAuth identity).

**Failure:** Read [references/cli-installation-guide.md](references/cli-installation-guide.md) sections 2 and 3.

### 3. Caller identity

```bash
aliyun sts get-caller-identity
```

**Success:** Returns JSON with `AccountId`, `UserId`, and `Arn`.

**Failure:** Read [references/cli-installation-guide.md](references/cli-installation-guide.md) section 4.

### 4. RAM permissions

```bash
aliyun polardbx describe-db-instances --biz-region-id <RegionId> --region <RegionId> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

**Success:** Returns an instance list or empty list without permission errors.

**Failure:** Read [references/ram-policies.md](references/ram-policies.md).

### 5. jq availability

```bash
jq --version
```

**Success:** Output contains a version string such as `jq-1.7.1`.

**Failure:** Read [references/cli-installation-guide.md](references/cli-installation-guide.md) section 5.

---

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun polardbx describe-db-instances --biz-region-id cn-hangzhou --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script / Terraform execution:** When running Python SDK scripts or Terraform commands or bash scripts, inject the session-id via inline environment variable so the code can read it at runtime:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} python3 scripts/deploy.py

# Terraform
SKILL_SESSION_ID={session-id} terraform apply
```

Scripts and Terraform configs should read `SKILL_SESSION_ID` from the environment (default to empty string if absent). See `references/how-to-implement-by-common-sdk.md` for SDK patterns.

---

## Intent Routing

Match the user request to the first matching row, then load the listed reference file and follow its API spec.

| If the user wants to ... | Module | Required reading | Key APIs |
|---|---|---|---|
| Create / delete / restart / describe / list instances, modify description / maintain time, upgrade kernel, query topology or tasks | Instance Lifecycle | [references/instance-lifecycle.md](references/instance-lifecycle.md) | CreateDBInstance, DeleteDBInstance, RestartDBInstance, DescribeDBInstanceAttribute, DescribeDBInstances, DescribeDBInstanceTopology, DescribeTasks, ModifyDBInstanceDescription, ModifyDBInstanceMaintainTime, UpgradeDBInstanceKernelVersion |
| Scale nodes / change instance class / view scale-out migration progress | Scaling | [references/scaling.md](references/scaling.md) | UpdatePolarDBXInstanceNode, ModifyDBInstanceClass, DescribeScaleOutMigrateTaskList |
| View / modify instance config or parameters | Parameters | [references/parameters.md](references/parameters.md) | DescribeDBInstanceConfig, ModifyDBInstanceConfig, DescribeParameters, ModifyParameter, DescribeParameterTemplates |
| Look up CN / DN / DBNodeClass spec codes, or convert between a spec code and its cores/memory | Instance Specs | [scripts/spec_lookup.sh](scripts/spec_lookup.sh) for spec-code <-> hardware mapping (`--code` / `--cores`+`--memory`; `--list` to enumerate all specs) | spec_lookup.sh --code / --cores/--memory |
| View performance data / slow logs / binlog list | Monitoring & Logs | [references/monitoring-logs.md](references/monitoring-logs.md) | DescribeDBNodePerformance, DescribeSlowLogRecords, DescribeBinaryLogList |
| Manage database accounts (create/delete/list/reset password/privilege) | Account Management | [references/account-management.md](references/account-management.md) | CreateAccount, DeleteAccount, DescribeAccountList, CreateSuperAccount, ResetAccountPassword, ResetAccountPasswordRestrict, ModifyAccountDescription, ModifyAccountPrivilege |
| Manage databases and tables | Database Management | [references/database-management.md](references/database-management.md) | CreateDB, DeleteDB, DescribeDbList, DescribeDistributeTableList, DescribeArchiveTableList, ModifyDatabaseDescription |
| Backup / restore / clone instance | Backup & Restore | [references/backup-restore.md](references/backup-restore.md) | CreateBackup, DescribeBackupPolicy, UpdateBackupPolicy, DescribeBackupSet, DescribeBackupSetList, DescribeOpenBackupSet, RestoreDBInstance |
| Manage IP whitelist / SSL / TDE / KMS authorization | Security & Access | [references/security-access.md](references/security-access.md) | DescribeSecurityIps, ModifySecurityIps, DescribeDBInstanceSSL, UpdateDBInstanceSSL, DescribeDBInstanceTDE, UpdateDBInstanceTDE, DescribeUserEncryptionKeyList, CheckCloudResourceAuthorized |
| SQL audit / rights separation | SQL Audit & Compliance | [references/sql-audit-compliance.md](references/sql-audit-compliance.md) | EnableSqlAudit, DisableSqlAudit, DescribeSqlAuditInfo, CheckSqlAuditSlsStatus, EnableRightsSeparation, DisableRightsSeparation |
| View / manage O&M events, maintenance conf, history events, health | Operation Tasks & Events | [references/operation-tasks.md](references/operation-tasks.md) | DescribeActiveOperationTasks, DescribeActiveOperationTaskCount, DescribeActiveOperationMaintainConf, ModifyActiveOperationMaintainConf, ModifyActiveOperationTasks, CancelActiveOperationTasks, DescribeEvents, SkipCurrentStep, CheckHealth, DescribeComponentPropeties |
| HA switch / zone migration | HA & Migration | [references/ha-migration.md](references/ha-migration.md) | DescribeDBInstanceHA, SwitchDBInstanceHA, MigrateDBInstance, AlignStoragePrimaryAzone, ConfirmNoConnection, StartSwitchDatabase, DescribeTransformStatus (standard-to-enterprise upgrade not supported) |
| Manage connection strings / VIP / custom endpoints | Connection & Endpoint | [references/connection-endpoint.md](references/connection-endpoint.md) | DescribeDBInstanceEndpoint, ModifyDBInstanceConnectionString, ModifyDBInstanceVip, CreateCustomEndpoint, DeleteCustomEndpoint, ModifyCustomEndpoint, ModifyCustomEndpointNet, DescribeCustomEndpointList, DescribeDBInstanceViaEndpoint, CreateSubCNInstance, DeleteSubCNInstance |
| Manage tags / resource group | Tags & Resource Group | [references/tags-resourcegroup.md](references/tags-resourcegroup.md) | TagResources, UntagResources, ListTagResources, DescribeTags, ChangeResourceGroup, UpdateCustinsParam |
| Query regions / VPC / VSwitch / character set / data nodes / parameter groups | Metadata & Query | [references/metadata-query.md](references/metadata-query.md) | DescribeRegions, DescribeAvailableCrossRegions, DescribeEnabledCrossRegions, DescribeRdsVpcs, DescribeRdsVswitches, DescribeCharacterSet, DescribePolarxDataNodes, DescribeParameterGroups |
| Manage cold-data volume / storage pool / storage usage | Cold Storage | [references/cold-storage.md](references/cold-storage.md) | AllocateColdDataVolume, ReleaseColdDataVolume, DescribeColdDataBasicInfo, CreateStoragePool, DescribeStoragePoolInfo, DescribeShowStorageInfo |
| SQL evaluation / evaluate-import tasks / replication inspection / engine migration | Data Evaluate & Migration | [references/data-evaluate-migration.md](references/data-evaluate-migration.md) | CreateSQLEvaluateTask, DescribeEvaluateAndImportTask, DescribeEvaluateAndImportTasks, DeleteEvaluateAndImportTask, CreateRplInspectionTask, DescribeRplInspectionTask, CloseEngineMigration, ModifyEngineMigration |
| SQL flashback (row-level recovery) | SQL Flashback | [references/sql-flashback.md](references/sql-flashback.md) | DescribeSqlFlashbackTaskList, PreCheckSqlFlashbackTask, SubmitSqlFlashbackTask |
| CDC / log engine info, spec, version | CDC (Log Engine) | [references/cdc.md](references/cdc.md) | DescribeCdcInfo, DescribeCdcClassList, DescribeCdcVersionList, ModifyCdcClass, UpgradeCDCVersion |
| Columnar (column store) info, spec, version | Columnar | [references/columnar.md](references/columnar.md) | AttachColumnarInstance, DescribeColumnarInfo, DescribeColumnarClassList, DescribeColumnarVersionList, ModifyColumnarClass, UpgradeColumnarVersion |
| GDN (Global Database Network) management | GDN | [references/gdn.md](references/gdn.md) | CreateGdnInstance, DeleteGdnInstance, DescribeGdnInstances, CreateGdnStandbyMember, SwitchGdnMemberRole |
| Mem0 (memory engine) management | Mem0 | [references/mem0.md](references/mem0.md) | CreateMem0, DeleteMem0, DescribeMem0Info, DescribeMem0SecurityIps, ModifyMem0SecurityIps, ResetMem0AccountPassword, CreateGatewayConsumerForPolarDBX |

> If multiple intents are present, handle them sequentially: route -> execute -> verify -> next route.
> If the intent does not match any row, ask the user to clarify; do NOT guess an API.

---

## Global Conventions

These conventions apply to every `aliyun polardbx` CLI command produced by this skill.

### Command format

```bash
aliyun polardbx <action-name> --biz-region-id <RegionId> --region <RegionId> [other parameters]
```

**[MUST] Always pass BOTH `--biz-region-id <RegionId>` AND the global flag `--region <RegionId>` with the same value.** `--biz-region-id` is only a business-level parameter; the CLI resolves the API endpoint from the profile default region or the global `--region` flag. Without `--region`, every request is sent to the profile's default-region endpoint (e.g. `polardbx.cn-hangzhou.aliyuncs.com`), so instances/VPCs in other regions return `InvalidDBInstance.NotFound` / `InvalidParameter.VpcId.VSwitchId`.

- The `aliyun` CLI returns JSON by default. Do NOT add `--output` unless the user explicitly asks for table format.
- Read operations append `--connect-timeout 3 --read-timeout 10`.
- Write operations append `--connect-timeout 3 --read-timeout 30 --client-token <token>`.

### Command style: plugin mode

This skill uses the `aliyun` CLI **plugin mode** for PolarDB-X:

| Example | Parameter naming | Region parameters |
|---|---|---|
| `aliyun polardbx create-db-instance` | `--biz-region-id`, `--vpc-id`, `--vswitch-id` | `--biz-region-id` + `--region` (global, same value) |

- All action names are lowercase words connected with hyphens (`describe-db-instances`).
- All parameter flags are kebab-case (`--db-instance-name`, `--client-token`).
- Do NOT mix plugin mode with the legacy PascalCase API style within a single command.
- If a parameter is rejected, fall back to `aliyun polardbx <action-name> --help` to verify the exact parameter name.

### CN spec naming

PolarDB-X CN node specs follow the pattern `polarx.xN.<size>.<suffix>`. The `<size>` field determines the core multiplier:

| Suffix | Cores | Memory | Example (`x4`) |
|---|---|---|---|
| `large` | N (1x) | 4N GB | `polarx.x4.large.2e` = 4C16G |
| `xlarge` | 2N (2x) | 8N GB | `polarx.x4.xlarge.2e` = 8C32G |

- `large` is NOT a small size; it is the **base** (1x) multiplier.
- `xlarge` **doubles** the core count and memory.
- When the user says "4-core 16G", select `large`; do NOT select `xlarge`.
- For full spec list, run `aliyun polardbx create-db-instance --help`.

### Output parsing

- Pipe the default JSON output to `jq` and extract only the fields the user needs.
- Avoid dumping large raw JSON blocks; prefer concise `jq` filters.
- Example:

```bash
aliyun polardbx describe-db-instances \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id} \
  | jq '.DBInstances[] | {DBInstanceName, Status, Description}'
```

### Table output

If the user explicitly requests table format, use `--output` with `cols` and `rows`:

```bash
aliyun polardbx describe-db-instances \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --output cols=DBInstanceName,Status,Description,rows=DBInstances \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

> In `zsh`, quote the `--output` value to prevent glob expansion: `--output 'cols=DBInstanceName,Status,Description,rows=DBInstances'`.

### Required user input

- `RegionId`: MUST be explicitly provided by the user. NEVER guess. NEVER use a default region.
- Instance identifier: `DBInstanceName` or `DBInstanceId` depending on the API. MUST be explicitly provided.

### Idempotency

For write APIs (`CreateDBInstance`, `RestartDBInstance`, `UpdatePolarDBXInstanceNode`, `ModifyDBInstanceClass`, `ModifyDBInstanceMaintainTime`, `ModifyDBInstanceConfig`, `ModifyParameter`, `UpgradeDBInstanceKernelVersion`), use `--client-token`.

> `DeleteDBInstance` does NOT support `--client-token`; do not append it.

```bash
CLIENT_TOKEN=$(uuidgen)   # reuse on retry
```

On timeout / failure, retry with **the same** `ClientToken`.

### Pagination

For all paginated read operations (`DescribeDBInstances`, `DescribeTasks`, `DescribeSlowLogRecords`, `DescribeBinaryLogList`, etc.), use `--page-size 100` unless the user explicitly requests a different size.

- PolarDB-X APIs typically enforce a maximum `PageSize` of 100.
- Use `--page-number` to iterate through pages when more than 100 results exist.

### Security constraints

- NEVER expose the instance to the public internet.
- NEVER recommend `AllocateInstancePublicConnection` or any public-network command.
- NEVER ask users to provide AK/SK directly in the conversation.
- NEVER echo credential values.

---

## Error & Timeout Handling

When a CLI command fails, handle it according to the following rules.

### Network timeout / connect-timeout / read-timeout

- Retry up to 3 times with exponential backoff: 5s / 10s / 20s.
- For idempotent write operations, reuse the same `--client-token` on retry.
- If all retries fail, prompt the user to check local network and Region availability.

### API business errors (Code/Message)

| Error code | Handling |
|---|---|
| `InvalidDBInstanceId.NotFound` / `InvalidDBInstance.NotFound` | Verify `DBInstanceName` / `DBInstanceId` and `RegionId` |
| `Forbidden.RAM` / `NoPermission` | Read [references/ram-policies.md](references/ram-policies.md) |
| `Throttling` | Back off exponentially, then retry; reduce call frequency |
| `InternalError` | Retry up to 3 times; if still failing, suggest opening a support ticket |
| `MissingParameter` / `InvalidParameter` | Re-read the relevant reference file and confirm all required parameters |

### Asynchronous tasks

For operations that return a `TaskId` or order ID (create / delete / restart / scale / upgrade / class change):

1. Poll task status with `DescribeTasks`.
2. Poll interval: 10 seconds.
3. Timeout: 30 minutes (configurable).
4. On task failure, output `TaskErrorCode` and `TaskErrorMessage`.

**Preferred: Use the bundled polling script:**

```bash
./scripts/poll_task.sh \
  --region <RegionId> \
  --instance-id <DBInstanceId> \
  --start-time <StartDate> \
  --end-time <EndDate> \
  --session-id {session-id}
```

**Manual alternative:**

```bash
aliyun polardbx describe-tasks \
  --biz-region-id <RegionId> \
  --region <RegionId> \
  --db-instance-id <DBInstanceId> \
  --start-time <StartTime> \
  --end-time <EndTime> \
  --page-number 1 \
  --page-size 100 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id} \
  | jq '.Items[] | {TaskId, Status, TaskAction, TaskErrorCode, TaskErrorMessage}'
```

> `DescribeTasks` returns the task list in `.Items[]` (NOT `.Tasks[]`). Each item has `Status` (e.g. `"8"` finished, `RUNNING`/`FAILED`), `TaskAction`, `TaskId`, `BeginTime`, `FinishTime`, and optional `TaskErrorCode`/`TaskErrorMessage`. A task with a non-empty `FinishTime` has ended; check `Status` for success or failure.

### Unexpected output

- If the output is empty or fields are missing, first run the command without `| jq ...` to check whether the default JSON output is valid.
- If `jq` fails, verify the filter against the raw JSON output.
- Use `--cli-query` carefully; verify the JMESPath expression against the raw JSON output.
- All fields shown to the user SHOULD be extracted via `jq` filters.

---

## Reference Links

| Reference | Description |
|---|---|
| [references/instance-lifecycle.md](references/instance-lifecycle.md) | Instance lifecycle APIs |
| [references/scaling.md](references/scaling.md) | Scaling and class-change APIs |
| [references/parameters.md](references/parameters.md) | Config and parameter APIs |
| [references/monitoring-logs.md](references/monitoring-logs.md) | Performance, slow log, and binlog APIs |
| [references/account-management.md](references/account-management.md) | Database account management APIs |
| [references/database-management.md](references/database-management.md) | Database and table management APIs |
| [references/backup-restore.md](references/backup-restore.md) | Backup policy, backup set, and restore APIs |
| [references/security-access.md](references/security-access.md) | IP whitelist, SSL, TDE, KMS authorization APIs |
| [references/sql-audit-compliance.md](references/sql-audit-compliance.md) | SQL audit and rights-separation APIs |
| [references/operation-tasks.md](references/operation-tasks.md) | O&M events, maintenance config, history events APIs |
| [references/ha-migration.md](references/ha-migration.md) | HA switch, zone migration, transform APIs |
| [references/connection-endpoint.md](references/connection-endpoint.md) | Connection string, VIP, custom endpoint APIs |
| [references/tags-resourcegroup.md](references/tags-resourcegroup.md) | Tag and resource-group APIs |
| [references/metadata-query.md](references/metadata-query.md) | Region, VPC/VSwitch, character set, data node APIs |
| [references/cold-storage.md](references/cold-storage.md) | Cold-data volume and storage pool APIs |
| [references/data-evaluate-migration.md](references/data-evaluate-migration.md) | SQL evaluation and engine migration APIs |
| [references/sql-flashback.md](references/sql-flashback.md) | SQL flashback (row-level recovery) APIs |
| [references/cdc.md](references/cdc.md) | CDC / log engine APIs |
| [references/columnar.md](references/columnar.md) | Columnar (column store) APIs |
| [references/gdn.md](references/gdn.md) | Global Database Network (GDN) APIs |
| [references/mem0.md](references/mem0.md) | Mem0 memory engine APIs |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation, plugin, credential, and identity checks |
| [references/ram-policies.md](references/ram-policies.md) | RAM permissions and troubleshooting |
| [references/index.md](references/index.md) | Reference overview and routing index |
| [Official API Reference](https://api.aliyun.com/document/polardbx/2020-02-02/overview) | PolarDB-X OpenAPI documentation |

---

## Scripts

| Script | Description |
|---|---|
| [scripts/poll_task.sh](scripts/poll_task.sh) | Poll async task status with timeout and exponential backoff |
| [scripts/spec_lookup.sh](scripts/spec_lookup.sh) | Convert between a PolarDB-X spec code and its hardware config (cores/memory), in both directions; supports `--category`/`--disk`/`--type` filters and `--json` |

Runtime dependencies (bash >= 4.0, aliyun CLI >= 3.3.3, jq >= 1.6) are declared in each script's header comments. `spec_lookup.sh` only needs bash + awk (no CLI/jq).

### Spec code <-> hardware lookup

To resolve a spec code to cores/memory, or to find spec codes for a target hardware size, call `scripts/spec_lookup.sh`:

```bash
# Spec code -> hardware
./scripts/spec_lookup.sh --code polarx.x4.large.2e

# Hardware -> matching spec code(s) (filter by module / disk / type as needed)
./scripts/spec_lookup.sh --cores 8 --memory 32 --category cn --disk local

# Machine-readable output for the agent
./scripts/spec_lookup.sh --code mysql.n4.medium.25 --json
```

- `--category`: `cn` (enterprise compute) / `dn` (enterprise storage) / `standard`.
- `--disk`: `local` (custom_local_ssd) / `cloud` (cloud_auto).
- `--type`: `general` / `dedicated`.
- Exit codes: `0` found, `3` invalid args, `4` no match.
