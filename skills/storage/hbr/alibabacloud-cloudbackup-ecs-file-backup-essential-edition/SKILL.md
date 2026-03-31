---
name: alibabacloud-cloudbackup-ecs-file-backup-essential-edition
description: |
  Alibaba Cloud ECS File Backup Essential Edition (ECS文件备份基础版). One-click activation, daily automatic backup, 30-day file recovery, 100 GiB free quota.
  Trigger words: ECS file backup, HBR essential edition, Cloud Backup essential, file deletion recovery, free backup quota, ECS data protection, lightweight backup, affordable ECS backup
  Redirect words: ECS database backup, ECS full-machine backup, full-machine clone, cross-region backup, cross-account backup, KMS encrypted backup
---

# ECS File Backup Essential Edition - Operations & Viewing

## Scenario Description

ECS File Backup Essential Edition (ECS文件备份基础版) is a basic backup product launched by Alibaba Cloud's Cloud Backup service (HBR) for ECS file scenarios, featuring one-click activation and zero-configuration setup.

### Core Features

| Feature | Description |
|---------|-------------|
| Automatic Backup (自动备份) | Daily automatic backup with 30-day retention |
| File Recovery (文件恢复) | Files accidentally deleted within 30 days can be recovered; supports file-level restoration |
| Free Quota (免费额度) | 100 GiB permanent free block storage backup quota per account (shared across all regions) |
| Low Maintenance (低运维) | One-click activation, zero configuration required, backup client auto-installed |

### Recommended Use Cases

When user requirements match the following conditions, recommend ECS File Backup Essential Edition:

| Scenario | Description |
|----------|-------------|
| **ECS File Data Protection** | Need to protect/backup ECS file data and recover from accidental deletion |
| **Accept Daily Backup Policy** | Accept once-daily backup with 30-day retention |
| **Cost-Effective** | Affordable/free ECS data backup; 100 GiB permanent free quota per account (shared across all regions) |
| **Personal Websites/Blogs** | Quick recovery from accidental deletion of images or config files |
| **Dev/Test Environments** | Protection for code and configuration files |
| **Small Business Applications** | Basic data protection needs with low maintenance cost |

### Not-Recommended Scenarios & Alternatives

| Scenario | Reason | Alternative |
|----------|--------|-------------|
| **RDS or Self-Managed Database Backup** (数据库备份) | Database files are locked by the main process; backups may be inconsistent | For RDS, contact the RDS team; for MySQL/Oracle/SQL Server, use **Cloud Backup Database Backup** |
| **Cannot Install Backup Client** (不接受安装备份客户端) | Backup client consumes ECS CPU and memory resources | Use **ECS Snapshots** (note: no file-level recovery) |
| **ECS Spec < 1C512MB** | Specs too low, affecting backup performance | Use **ECS Snapshots**, or upgrade ECS specs first |
| **Full-Machine Clone/DR Failover** (整机克隆/异地拉起) | Essential Edition does not support full-machine recovery | Use **ECS Snapshots** |
| **Cross-Region/Cross-Account Backup** (跨地域/跨账号备份) | Essential Edition does not support cross-region or cross-account | Use **Cloud Backup ECS File Backup Standard Edition** (enterprise-grade) |
| **KMS-Encrypted Backup Data** (KMS加密备份) | Essential Edition does not support KMS encryption | Use **Cloud Backup ECS File Backup Standard Edition** |
| **Custom Backup Policy** (自定义备份策略) | Essential Edition is fixed at once-daily backup with 30-day retention | Use **Cloud Backup ECS File Backup Standard Edition** (customizable policy) |
| **Data Volume > 2 TB** | Backup may not complete within 24 hours | Contact Cloud Backup technical support, or use Standard Edition |

### Usage Limitations

| Limitation | Description |
|------------|-------------|
| Operating System | 32-bit operating systems not supported |
| Network Type | Classic network (经典网络) ECS not supported |
| Storage Type | Only block storage (块存储) supported; NAS/OSS and other network-mounted storage not supported |
| Dependent Service | Requires Cloud Assistant (云助手) service (ECS purchased before Dec 2017 requires manual installation of Cloud Assistant Agent) |
| ECS Spec | Recommended >= 1 vCPU, 512 MB memory for adequate backup performance |
| Data Volume | Low priority: < 600 GB; High priority: < 2 TB |

---

## Scenario Eligibility Check (Mandatory First Step)

> **CRITICAL - Hard Gate**: This is the **first step** before all operations, taking priority over installation checks, credential verification, and any workflow.
> The agent **MUST** complete this check before executing any other step.

**Decision Flow:**
```
User requests ECS backup/restore
|
+-> Check each item in "Not-Recommended Scenarios & Alternatives"
|   +-> Matches any not-recommended scenario -> Execute [HALT Flow]
|   +-> No match -> Pass, continue to "Installation Requirements"
|
+-> Not-recommended scenario keywords:
    - Database: MySQL/Oracle/SQL Server/PostgreSQL/MongoDB/Redis/database data directory
    - Full-machine: full-machine recovery/DR failover/clone instance
    - Cross-region/cross-account: remote backup/cross-account replication
    - Custom policy: hourly backup/custom retention period
    - Large data volume: data exceeds 2 TB
```

**[HALT Flow] - Must execute when a not-recommended scenario is matched:**
1. **Stop immediately** - Do NOT execute installation checks, credential verification, parameter confirmation, or any CLI command
2. **Output warning to user** - Explain why the current scenario is not suitable for ECS File Backup Essential Edition (cite the reason from "Not-Recommended Scenarios & Alternatives")
3. **Recommend alternatives** - Provide specific alternative products/features
4. **End current task** - After outputting the warning and alternatives, the agent **MUST stop** and **NOT continue with any subsequent steps of this Skill**

> **Sole recovery condition**: Only when the user, after receiving the warning, **proactively and explicitly** states "I understand the risks and still want to use ECS File Backup Essential Edition" (or semantically equivalent explicit confirmation), may the agent continue with subsequent steps.
> The following are **NOT** considered valid confirmations; the agent must remain stopped:
> - User does not reply
> - User only replies with vague confirmations like "OK", "Continue", "Help me backup" without mentioning "ECS File Backup Essential Edition"
> - User changes the topic
> - User asks for details about alternatives (indicates user is considering alternatives; do not force continuation)

---

## Installation Requirements (Mandatory Pre-check)

> **CRITICAL**: The agent **MUST** complete the following pre-checks before executing any core workflow.

### Pre-check: Aliyun CLI >= 3.3.1 required

See [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

```bash
aliyun version
```

Enable automatic plugin installation:
```bash
aliyun configure set --auto-plugin-install true
```

### Pre-check: aliyun-cli-hbr plugin >= 0.1.3 required

```bash
aliyun plugin list 2>/dev/null | grep aliyun-cli-hbr
```

If the plugin is not installed or the version is below 0.1.3, install/update:
```bash
aliyun plugin install --names aliyun-cli-hbr
```

> After plugin installation, HBR commands and parameter names use kebab-case naming convention (e.g., `describe-backup-plans` instead of `DescribeBackupPlans`).

---

## Credential Verification

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** print, echo, or output AK/SK values in any form (including partial fragments or masked forms)
> - **NEVER** expose any credential content in command-line arguments, logs, conversation output, or code comments
> - **NEVER** enter AK/SK directly in the command line
> - **ONLY USE** `aliyun configure list` to check credential status; **NEVER echo the output of this command to the user** (output may contain credential-related information); the agent should only use the output internally to determine whether credentials are valid
>
> ```bash
> aliyun configure list
> ```
>
> Confirm the output shows a valid profile (AK, STS, or OAuth identity).
>
> **If no valid credentials exist, configure first:**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Run `aliyun configure` in the terminal to configure credentials
> 3. Re-run `aliyun configure list` to confirm successful configuration

---

## Parameter Confirmation & Validation

> **IMPORTANT: Parameter Confirmation** - Before executing any command, all customizable parameters must be confirmed with the user.
> Do not assume default values; explicit user confirmation is required.
> **If the user refuses to confirm or does not respond to the confirmation request, the agent MUST abort the current operation and NOT continue with subsequent steps.**

> **CRITICAL - Security Gate**: Before embedding any parameter into a CLI command, the agent **MUST** validate all user-provided parameters against the validation regex in the table below.
> On validation failure, the agent **MUST refuse to execute the command**, inform the user which parameter is invalid and what format is expected, and wait for the user to provide a valid value before re-validating.

| Parameter | Required/Optional | Description | Validation Regex | Example |
|-----------|-------------------|-------------|------------------|---------|
| `REGION_ID` | Required | Region of the ECS instance (ECS实例所在地域) | `^[a-zA-Z0-9-]+$` | `cn-hangzhou` |
| `INSTANCE_ID` | Required | ECS Instance ID (ECS实例ID) | `^[a-zA-Z0-9-]+$` | `i-bp1abc123def456` |
| `PLAN_ID` | Required for some ops | Backup Plan ID (备份计划ID); needed for pause/resume/cancel | `^[a-zA-Z0-9-]+$` | `plan-abc123` |
| `VAULT_ID` | Required for restore | Backup Vault ID (备份仓库ID); obtained via `search-historical-snapshots` | `^[a-zA-Z0-9-]+$` | `v-0001xjb123` |
| `SNAPSHOT_ID` | Required for restore | Snapshot ID (备份版本ID); obtained via `search-historical-snapshots` | `^[a-zA-Z0-9-]+$` | `s-0001abc123` |
| `SNAPSHOT_HASH` | Required for restore | Snapshot Hash (备份版本哈希值); obtained via `search-historical-snapshots` | `^[a-zA-Z0-9-]+$` | `sh-abc123` |
| `performanceLevel` | Optional | Backup priority (备份优先级): `L0` (default, data < 600 GB) or `L1` (data 600 GB~2 TB) | `^(L0\|L1)$` | `L0` |
| `ConflictPolicy` | Required for restore | File conflict policy (文件冲突策略): `SKIP_THE_FILE` (skip) or `OVERWRITE_EXISTING` (overwrite) | `^(SKIP_THE_FILE\|OVERWRITE_EXISTING)$` | `SKIP_THE_FILE` |
| `CLIENT_TOKEN` | Required for restore | Idempotency token (幂等令牌); agent-generated UUID, reuse on timeout retry | `^[a-zA-Z0-9-]{1,64}$` | `550e8400-e29b-41d4-a716-446655440000` |
| `keep-latest-snapshots` | Optional | Keep last backup version (保留最后一个备份版本): `1` (keep) or `0` (don't keep) | `^(0\|1)$` | `1` |
| `SOURCE_PATH` | Optional for restore | Source file path to restore (要恢复的源文件路径) | `^[a-zA-Z0-9/_.-]+$` | `/home/data/file.txt` |
| `TARGET_PATH` | Required for restore | Restore target directory (恢复目标目录); must already exist | `^[a-zA-Z0-9/_.-]+$` | `/tmp/restore` |

## RAM Permissions

This Skill requires the permissions detailed in [references/ram-policies.md](references/ram-policies.md).

Recommended system policy: `AliyunHBRFullAccess`

---

## Core Workflows

> **CRITICAL**: Before executing any of the following workflows, the agent **MUST** complete all steps in "Scenario Eligibility Check" and "Installation Requirements (Mandatory Pre-check)".
> If Aliyun CLI or the aliyun-cli-hbr plugin is not installed or does not meet version requirements, it **MUST be installed/updated first** before proceeding.

### 1. Activate Backup

Activate ECS File Backup Essential Edition for a specified ECS instance.

**Step 1: Enable Cloud Backup Service (first-time use)**
```bash
aliyun hbr open-hbr-service \
  --endpoint hbr.aliyuncs.com \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> Idempotent operation; safe to run repeatedly.

**Step 2: Activate ECS Instance Backup**
```bash
aliyun hbr create-backup-plan \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --instance-id <INSTANCE_ID> \
  --keep-latest-snapshots 1 \
  --options '{"performanceLevel":"<LEVEL>"}' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> Idempotent operation; repeated calls for the same instance will not create duplicate backup plans. Safe to retry on timeout.

**Step 3: Verify Activation Status**

> Activation and client installation are asynchronous operations; they typically take a few minutes to become ready.

Use the status determination logic from "5. View ECS Backup Status" to verify. Expected state progression: `Preparing` -> `Ready` -> `Backing Up`

---

### 2. Pause Backup (Suspend)

Pause the backup plan (备份计划) while retaining existing backup data; can be resumed later.

**Step 1: Get Backup Plan ID**
```bash
aliyun hbr describe-backup-plans \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"instanceId","Values":["<INSTANCE_ID>"]}]' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> Extract `PlanId` from the response.

**Step 2: Pause Backup**
```bash
aliyun hbr disable-backup-plan \
  --region <REGION_ID> \
  --plan-id <PLAN_ID> \
  --edition BASIC \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> Idempotent operation; safe to call repeatedly.

---

### 3. Resume Backup

Resume a previously paused backup plan.

```bash
aliyun hbr enable-backup-plan \
  --region <REGION_ID> \
  --plan-id <PLAN_ID> \
  --edition BASIC \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> Idempotent operation; safe to call repeatedly.

---

### 4. Cancel Backup (Delete)

> **WARNING**: This operation will permanently delete all backup data and is irreversible! User intent must be confirmed before execution.
> **If the user has not explicitly confirmed deletion, the agent MUST abort the operation and NOT continue.**

**Step 1: Get Backup Plan ID**
```bash
aliyun hbr describe-backup-plans \
  --region <REGION_ID> \
  --source-type ECS_FILE \
  --edition BASIC \
  --filters '[{"Key":"instanceId","Values":["<INSTANCE_ID>"]}]' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Step 2: Delete Backup Plan**
```bash
aliyun hbr delete-backup-plan \
  --region <REGION_ID> \
  --plan-id <PLAN_ID> \
  --edition BASIC \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> After cancellation, the instance stops incurring charges; deleted backup data cannot be recovered.
> Idempotent operation; safe to call repeatedly on an already-deleted plan.

---

### 5. View ECS Backup Status

**Step 1: Query Backup Plan**
```bash
aliyun hbr describe-backup-plans \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"instanceId","Values":["<INSTANCE_ID>"]}]' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Step 2: Query Latest Backup Job**
```bash
aliyun hbr describe-backup-jobs-2 \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"instanceId","Values":["<INSTANCE_ID>"]}]' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> `describe-backup-jobs-2` returns backup jobs sorted by creation time in descending order; the first record is the latest execution result.

**Status Determination Logic**
```
describe-backup-plans finds no plan -> Not Activated (未激活)
describe-backup-plans finds a plan
+-> Disabled = true -> Paused (已暂停)
+-> Query describe-backup-jobs-2 for latest backup job
    +-> No backup jobs -> Preparing (准备中)
    +-> Has backup jobs (first record = latest result)
        +-> COMPLETE/PARTIAL_COMPLETE -> Backup Normal (备份正常)
        +-> RUNNING/QUEUED/CREATED -> Backing Up (备份中)
        +-> CANCELED -> Canceled (已取消)
        +-> FAILED/EXPIRED -> Backup Abnormal (备份异常); troubleshoot via describe-backup-clients
```

**Auxiliary Query Commands**

View backup client status:
```bash
aliyun hbr describe-backup-clients \
  --region <REGION_ID> \
  --client-type ECS_CLIENT \
  --instance-ids '["<INSTANCE_ID>"]' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

View backup history (Snapshot list):
```bash
aliyun hbr search-historical-snapshots \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --query '[{"field":"instanceId","value":"<INSTANCE_ID>","operation":"MATCH_TERM"}]' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 6. View Free Quota & Capacity

```bash
aliyun hbr get-basic-statistics \
  --source-type ECS_FILE \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key field**: `GlobalStatistics.ProtectedDataSize` is the total block storage capacity of backed-up ECS instances (in bytes).

**Free quota rules**: 100 GiB per account (permanent, shared across all regions). Usage beyond the quota is billed on a pay-as-you-go basis; billing is based on the total block storage capacity mounted on backed-up ECS instances.

---

### 7. File Restore

```bash
aliyun hbr create-restore-job \
  --region <REGION_ID> \
  --restore-type ECS_FILE \
  --edition BASIC \
  --source-type ECS_FILE \
  --vault-id <VAULT_ID> \
  --snapshot-id <SNAPSHOT_ID> \
  --snapshot-hash <SNAPSHOT_HASH> \
  --include '["<SOURCE_PATH>"]' \
  --target-instance-id <INSTANCE_ID> \
  --target-path <TARGET_PATH> \
  --options '{"ConflictPolicy":"<CONFLICT_POLICY>"}' \
  --client-token <UUID> \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

> `VaultId`, `SnapshotId`, and `SnapshotHash` can be obtained via `search-historical-snapshots`.
> Omitting `--include` restores all files in the snapshot.
> `TargetPath` must be an existing directory on the target ECS instance; otherwise the restore job will report a `TARGET_NOT_EXIST` error.
> Using the `OVERWRITE_EXISTING` policy will overwrite files with the same name at the target path; explicit user confirmation is required before execution. If the user has not confirmed, the agent MUST abort the restore operation.
> Use `--client-token` to ensure idempotency; the agent should generate a UUID as the ClientToken and reuse the same token on timeout retries to prevent duplicate restore jobs.

**View Restore Progress**
```bash
aliyun hbr describe-restore-jobs-2 \
  --region <REGION_ID> \
  --edition BASIC \
  --restore-type ECS_FILE \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 8. Modify Scheduled Backup Time

**Step 1: Get Backup Plan ID**
```bash
aliyun hbr describe-backup-plans \
  --region <REGION_ID> \
  --edition BASIC \
  --source-type ECS_FILE \
  --filters '[{"Key":"instanceId","Values":["<INSTANCE_ID>"]}]' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Step 2: Update Backup Schedule**
```bash
aliyun hbr update-backup-plan \
  --region <REGION_ID> \
  --plan-id <PLAN_ID> \
  --edition BASIC \
  --schedule 'I|<TIMESTAMP>|P1D' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> Schedule format: `I|<start_timestamp>|P1D`, where start_timestamp is a Unix timestamp in seconds, and `P1D` means once per day (fixed for Essential Edition).
> Idempotent operation; safe to call repeatedly.

---

### 9. Toggle Keep-Last-Snapshot

When enabled, even if all backup versions exceed the retention period, the system will retain the last version without deleting it.

```bash
aliyun hbr update-backup-plan \
  --region <REGION_ID> \
  --plan-id <PLAN_ID> \
  --edition BASIC \
  --keep-latest-snapshots <0_OR_1> \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> `1` = keep the last backup version (recommended); `0` = do not keep; all backup points older than 30 days will be automatically deleted.
> Idempotent operation; safe to call repeatedly.

---

### 10. Adjust Backup Execution Priority

```bash
aliyun hbr update-backup-plan \
  --region <REGION_ID> \
  --plan-id <PLAN_ID> \
  --edition BASIC \
  --options '{"performanceLevel":"<LEVEL>"}' \
  --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills
```
> See `performanceLevel` in the Parameter Confirmation table for valid values; detailed use cases are described in [references/related-apis.md](references/related-apis.md).
> Idempotent operation; safe to call repeatedly.

---

## Verification

See [references/verification-method.md](references/verification-method.md) for details.

---

## References

| Document | Link |
|----------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| API & CLI Command Reference | [references/related-apis.md](references/related-apis.md) |
| RAM Permission Policies | [references/ram-policies.md](references/ram-policies.md) |
| Verification Methods | [references/verification-method.md](references/verification-method.md) |
| Official User Guide | [ECS File Backup Essential Edition](https://help.aliyun.com/zh/cloud-backup/user-guide/ecs-file-backup-essential-edition) |
| Cloud Backup API Docs | [HBR API Reference](https://help.aliyun.com/zh/cloud-backup/developer-reference/api-hbr-2017-09-08-overview) |
