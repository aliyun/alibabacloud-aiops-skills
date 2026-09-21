# LHM Data Validation Operations Manual

This manual is intended for customer-side operations/development personnel who need to perform data consistency validation on the Alibaba Cloud LHM (LakeHouse Migration) platform. After reading it, you should be able to independently complete platform-side configuration, local environment preparation, launching validation tasks via the Skill, viewing results, and downloading reports.

> The core way to use this toolkit is **AI conversational driving (Skill)**: you only need to describe the validation requirement in natural language, and the AI will automatically select the correct functions, parameters, and call order based on `../../../SKILL.md`. Scripts and atomic Skills are mainly used for debugging, automation integration, or precise reproduction.

---

## 1. Platform-Side Configuration Checklist

Before running any validation task, confirm that the following 4 platform configurations are complete. For first-time use it is recommended to check each item; for subsequent reuse you only need to verify whether the data sources are still valid.

| Configuration item | Description | How to confirm |
|--------|------|----------|
| Alibaba Cloud AccessKey | Used to call the LHM OpenAPI; must have LHM service permissions | Create/view the AK/SK in RAM in the Alibaba Cloud console, and confirm that LHM-related policies are authorized |
| DataWorks exclusive data integration resource group | LHM data validation requires an exclusive resource group to execute SQL sampling and comparison | Purchase it in the DataWorks console and bind it to the current workspace |
| LHM data validation Agent | The validation execution component deployed on the resource group | In the LHM console "Agent Management", confirm the Agent status is "Online" |
| Source/target data sources | The database/data warehouse connections to be validated | Register them in the LHM console "Data Source Management" and record the `ds_id` and `ds_type` |

### 1.1 Data Source Registration Key Points

When registering a data source in the LHM console, record the following three elements:

- `ds_id`: The unique identifier of the data source in LHM; the core input parameter in scripts.
- `ds_name`: For display only; a Chinese name may be used and does not affect calls.
- `ds_type`: The data source type. Common values include `MySQL`, `Hive`, `MaxCompute`, `PostgreSQL`, `SQLServer`, `Oracle`, `Redshift`, `GaussDB`, `Hologres`, `ADBPG`, etc. See `references/enums.md` for the complete enumeration.

> Note: The source and target must be registered separately, and both data sources must be reachable by the LHM Agent.

### 1.2 Network and Whitelist

If the data source is in a VPC or private network, or has IP whitelisting enabled, ensure that:

- The elastic network interface IP or NAT egress IP of the DataWorks exclusive data integration resource group has been added to the data source whitelist.
- The LHM service domain (e.g. `lhm.cn-hangzhou.aliyuncs.com`) is accessible from the environment running the scripts.

---

## 2. Local Environment Preparation

### 2.1 Install Dependencies

The network layer is invoked through the aliyun CLI (aliyun-cli-lhm plugin), which must be installed first:

```bash
# Install the aliyun CLI (version >= 3.3.8): https://help.aliyun.com/cli/
# Install the lhm plugin (internal source)
aliyun plugin install --names lhm \
  --source-base https://cli.aliyun-inc.com/registry_id/2/env/pre/plugins

# Python dependencies (request models are provided by the built-in sdk/ directory)
pip install pyyaml
```

Python 3.9 or later is recommended.

### 2.2 Configure Credentials

It is recommended to configure the AccessKey via environment variables:

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="your-access-key-id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your-access-key-secret"
```

Credentials are resolved through the Alibaba Cloud default credential chain (environment variables / `~/.alibabacloud/credentials` / RAM Role). To switch between multiple accounts on the same machine, change the environment variables or the active CLI/RAM profile; the scripts never accept AK/SK as command-line arguments.

### 2.3 Pre-checks

`lhm-common check` does only two things:

1. **`check` subcommand**: Verifies whether the current credentials can connect to the LHM OpenAPI (by calling `GetDataCheckTaskList`), and reads the local onboarding state file.
2. **`confirm` subcommand**: Lets the user explicitly mark on the command line "I have confirmed certain prerequisites in the console", and records that confirmation to the local state file.

> Note: `confirm` does **not** actively call LHM to probe whether the resource group, Agent, or data sources actually exist; it only records your manual confirmation result. The real readiness check must be done manually in the Alibaba Cloud console.

Verify API connectivity:

```bash
python atomic-skills/lhm-common/scripts/run.py check --profile data-validation --region hangzhou
```

Expected output:

```json
{
  "ok": true,
  "state": {
    "resource_group_confirmed": false,
    "agent_confirmed": false,
    "data_sources_confirmed": false,
    "confirmed_at": null
  },
  "env_ready": true
}
```

Here `env_ready=true` only means the credentials and Region can connect to LHM; the three `confirmed` fields in `state` indicate whether you have manually confirmed the corresponding prerequisites.

After confirming in the Alibaba Cloud console that the resource group, Agent, and data sources are all ready, run:

```bash
python atomic-skills/lhm-common/scripts/run.py confirm --profile data-validation \
  --resource-group --agent --data-sources --region hangzhou
```

At this point `state` will be updated to `true`, for subsequent `check` reads and auditing.

---

## 3. Enabling the Skill

Place `data-validation-skill/SKILL.md` into the context of a Qoder-series AI assistant to drive validation through conversation.

In QoderWork's Skill / project settings, mount the `data-validation-skill/` directory as an available Skill, or reference `../../../SKILL.md` in the workspace context. After configuration, the AI will automatically generate validation code based on your description.

---

## 4. Usage Overview

After completing the platform configuration, you can use this toolkit in the following three ways:

| Method | Applicable scenario | Description |
|------|----------|------|
| **AI conversational driving (Skill)** | Daily validation; describe the requirement to generate code | Directly describe what to validate; the AI automatically selects functions and parameters based on `../../../SKILL.md` (recommended) |
| **Atomic Skill** | Embedding into external scheduling systems, CI/CD, or when JSON output is needed | `atomic-skills/lhm-*/scripts/run.py`; all parameters are passed via the command line |
| **One-click script execution** | Local quick verification, debugging | `scripts/01_count_per_table.py` / `02_count_batch.py` / `03_metric_per_table.py` |

Regardless of the method, the core flow is the same: create task → configure tables/rules → save batch → trigger execution → poll status → view report.

---

## 5. Atomic Capabilities Quick Reference

When you need to embed validation capabilities into an external scheduling system or CI/CD, or need precise JSON output, you can directly call the atomic Skills under `atomic-skills/`. Each atomic Skill is a single-responsibility, command-line-driven executable script.

| Atomic Skill | Responsibility | Typical use case | Corresponding common.py function |
|-----------|------|-------------|---------------------|
| `lhm-common` | Build/verify the LHM client (aliyun CLI), prerequisite checks, and onboarding state management | Environment connectivity check, first-use confirmation checklist | `build_client()` + `check_env()` + state file |
| `lhm-count-check` | Create and trigger per-table row count validation | Row count comparison for specific tables + partitions | `run_count_check()` |
| `lhm-metric-check` | Create and trigger per-table metric validation | Compare aggregate metrics such as avg/max/min/sum | `run_metric_check()` |
| `lhm-batch-check` | Create and trigger batch-mode validation | Match an entire database or multiple tables by rule | `run_batch_check()` |
| `lhm-poll-status` | Query/poll execution status | External workflows waiting for task completion | `poll_exec_status()` |
| `lhm-report-summary` | Get the batch overview | View the number of passed/failed tables | `summarize_batch()` |
| `lhm-report-download` | Download the validation report | Download the Excel report after task completion | `download_report()` |
| `lhm-report-diagnose` | Diagnose failure reasons | Root cause analysis of failed tables | `diagnose_failed()` |
| `lhm-rerun-failed` | Rerun failed tasks | Generate a new batch for failed/non-passing tables | `rerun_failed()` |

These scripts all receive input via command-line parameters, output JSON to `stdout` on success, and output progress and errors to `stderr`, for easy parsing by external systems.

## 6. Best Practice Examples

The following examples use **Skill conversation** as the entry point and also provide the typical calls (atomic Skill commands) the AI might generate. You can copy and run the commands directly, or hand the prompts to the AI assistant to generate them automatically.

### 6.1 Example 1: Full-Database Row Count Validation (MySQL → Hive)

**Prompt for the AI:**

```text
Help me validate the full-database row count from MySQL data source ds-mysql-001 to Hive data source ds-hive-001.
The source database is src_db, the target database is dst_db, and the task name is MySQLToHive全库数据量校验.
```

**Typical call the AI will generate:**

```bash
python atomic-skills/lhm-batch-check/scripts/run.py \
  --task-name "MySQLToHive全库数据量校验" \
  --src-ds-id ds-mysql-001 \
  --src-ds-name "源端MySQL" \
  --src-ds-type MySQL \
  --dst-ds-id ds-hive-001 \
  --dst-ds-name "目标端Hive" \
  --dst-ds-type Hive \
  --check-type 0 \
  --match-rule "src_db|dst_db|*" \
  --region hangzhou
```

**Expected output:**

```json
{"ok": true, "task_id": 12345, "batch_id": 20001}
```

### 6.2 Example 2: MaxCompute Partitioned Table Batch Validation

**Prompt for the AI:**

```text
Do a batch row count validation on MaxCompute partitioned tables:
- Both the source and target data sources are MaxCompute, with ds_id ds-mc-src-001 and ds-mc-dst-001 respectively
- Source table lhm_test_count_src, target table lhm_test_count_tgt
- The database name is source_db for both
- Partition dt='2026-01-01'
The task name is MC分区表批量校验.
```

**Typical call the AI will generate:**

```bash
python atomic-skills/lhm-batch-check/scripts/run.py \
  --task-name "MC分区表批量校验" \
  --src-ds-id ds-mc-src-001 \
  --src-ds-name "源端MaxCompute" \
  --src-ds-type MaxCompute \
  --dst-ds-id ds-mc-dst-001 \
  --dst-ds-name "目标端MaxCompute" \
  --dst-ds-type MaxCompute \
  --check-type 0 \
  --match-rule "source_db|source_db|lhm_test_count_src|lhm_test_count_tgt|dt='2026-01-01';dt='2026-01-01'" \
  --source-global-params "odps.sql.allow.fullscan=true" \
  --target-global-params "odps.sql.allow.fullscan=true" \
  --region hangzhou
```

**Key points:**

- Both `source_global_params` and `target_global_params` must be set.
- The partition field of the match rule must be written for both source and target, separated by a semicolon: `dt='2026-01-01';dt='2026-01-01'`.
- The table name field of a batch rule is parsed as a regex; to match all tables starting with `lhm_`, write `lhm_.*`, not `lhm_*`.

### 6.3 Example 3: Per-Table Metric Validation

**Prompt for the AI:**

```text
Do a metric validation on MySQL's src_db.orders and Hive's dst_db.orders by dt=20240305.
The data source ds_id are ds-mysql-001 and ds-hive-001 respectively, and the task name is 订单表指标校验.
```

**Typical call the AI will generate:**

```bash
python atomic-skills/lhm-metric-check/scripts/run.py \
  --task-name "订单表指标校验" \
  --src-ds-id ds-mysql-001 \
  --src-ds-name "源端MySQL" \
  --src-ds-type MySQL \
  --dst-ds-id ds-hive-001 \
  --dst-ds-name "目标端Hive" \
  --dst-ds-type Hive \
  --tables-json '[
    ["src_db.orders", "dst_db.orders", "dt=20240305", "dt=20240305"]
  ]' \
  --check-template-id 1001 \
  --region hangzhou
```

> The `threshold` for metric validation is not passed by default; the system uses the default threshold. Never pass `0.0`, otherwise all metrics will be judged PASSED.

### 6.4 Example 4: Viewing and Downloading the Report

**Prompt for the AI:**

```text
The task with batch_id=20001 has finished; help me check the results and download the report.
```

**The AI will execute in sequence:**

Query the overview:

```bash
python atomic-skills/lhm-report-summary/scripts/run.py \
  --batch-id 20001 \
  --region hangzhou
```

If there are failed tables, diagnose them:

```bash
python atomic-skills/lhm-report-diagnose/scripts/run.py \
  --batch-id 20001 \
  --region hangzhou
```

Download the full Excel report:

```bash
python atomic-skills/lhm-report-download/scripts/run.py \
  --batch-id 20001 \
  --region hangzhou
```

The output will include an OSS download link.

---

## 7. Prompt Suggestions for Collaborating with the AI

To help the Skill generate correct validation code faster, it is recommended to include the following information when describing requirements:

- **Data sources**: The `ds_id` and `ds_type` of the source and target.
- **Validation scope**: Specific table names, database names, or full-database/batch rules.
- **Partition conditions** (if any): e.g. `dt='2026-01-01'`.
- **Validation type**: Row count or metric.
- **Task name**: Only Chinese/English characters + digits; avoid spaces and underscores.

**Good prompt example:**

```text
Do a row count validation on tables lhm_test_count_src / lhm_test_count_tgt from MaxCompute data source ds-mc-src-001 to ds-mc-dst-001,
database name source_db, partition dt='2026-01-01', task name MCPartitionCheck.
```

**Poor prompt example:**

```text
Help me run a validation.
```

The latter lacks key information such as data sources, tables, and partitions, so the AI cannot directly generate executable code.

---

## 8. Core Parameter Description

This section lists the most commonly used parameters in validation tasks. When using the Skill, the AI handles these parameters automatically; when calling atomic Skills or scripts directly, you need to fill them in manually.

### 8.1 The Three Data Source Elements

```python
src_ds = ('ds-src-001', '源端MySQL', 'MySQL')
dst_ds = ('ds-dst-001', '目标端Hive', 'Hive')
```

- `ds_id`: The core SDK input parameter; must actually exist in the LHM console.
- `ds_name` / `ds_type`: For display and logging only; do not affect calls.

### 8.2 Task Name Rules

`task_name` only allows Chinese/English characters and digits; it cannot contain spaces, underscores, hyphens, or other special characters. Valid examples:

- `'每日全库校验'`
- `'HiveToMaxComputeCount'`
- `'订单表指标校验2024'`

Invalid examples: `daily_full_db_check`, `mysql-to-hive-count`, `全库 校验`.

### 8.3 Batch Match Rules

The rule format is:

```text
source_db|target_db|source_table|target_table|partition|mapping
```

Common patterns:

| Pattern | Meaning |
|------|------|
| `src_db|dst_db|*` | Full-database validation; source and target table names are identical |
| `src_db|dst_db|lhm_.*` | Validate all tables starting with `lhm_` |
| `src_db|dst_db|orders|orders|dt='2024-03-05';dt='2024-03-05'` | Batch validation of a single partitioned table |

See `references/batch_match_rules.md` for the complete syntax.

### 8.4 threshold and global_params

| Parameter | Meaning | Recommendation |
|------|------|------|
| `threshold` | Consistency rate threshold | Row count validation defaults to exact matching; it is recommended not to pass it or to pass `None`; passing `0.0` makes all validations pass |
| `source_global_params` / `target_global_params` | Source/target global parameters | MaxCompute partitioned tables need `odps.sql.allow.fullscan=true`; separate multiple parameters with semicolons |

---

## 9. Interpreting Results

### 9.1 Execution Status exec_status

| Status value | Meaning | Recommended action |
|--------|------|----------|
| 0 | Waiting | Wait |
| 1 | Running | You can call stop to terminate |
| 2 | Terminated | You can call rerun to rerun |
| 3 | Failed | Check err_message to diagnose |
| 4 | Completed | View the report |

### 9.2 Consistency Determination

- `is_consistent`: Whether the data is consistent; `1` means consistent, `0` means inconsistent.
- `check_result`: The validation result enum, such as `PASSED`, `FAILED`, `NO_RECORD`.

When determining whether the data is consistent, `is_consistent` should be the authority.

### 9.3 Report Download

`download_report()` automatically triggers generation and polls until `report_status=2`, then returns the OSS link. If the batch is not complete, it throws an exception.

---

## 10. Common Issues Quick Reference

| Symptom | Possible cause | Solution |
|------|----------|------|
| Task name error `E500R103` | Contains spaces, underscores, or other special characters | Rename using only Chinese/English characters + digits |
| Batch mode matched 0 tables | Misused wildcard, or MaxCompute partitioned table missing two-sided partition conditions | Check the regex; partition conditions must include both source and target |
| MaxCompute partitioned table reports `full scan with all partitions` | Full table scan not enabled or partition conditions missing | Set both `source_global_params` / `target_global_params` to `odps.sql.allow.fullscan=true` and add two-sided partition conditions |
| All metric validations PASSED | `threshold=0.0` | Remove the `threshold` parameter and use the system default |
| Calling run/stop/rerun with `task_id` fails | These interfaces require `batch_id` | Use the `batch_id` returned after saving the batch |
| Report download is empty | The report has not been generated | Wait until `exec_status=4` before downloading, or call `download_report()` to poll automatically |

See `references/troubleshooting.md` for a more detailed troubleshooting guide, and `docs/user-pitfalls.md` for common misconceptions.

---

## 11. First-Use Checklist

- [ ] Created an Alibaba Cloud AccessKey with LHM permissions and configured it in environment variables.
- [ ] Purchased a DataWorks exclusive data integration resource group and bound it to the workspace.
- [ ] Completed Agent onboarding in the LHM console.
- [ ] Registered the source and target data sources in the LHM console and recorded `ds_id` / `ds_type`.
- [ ] Confirmed in the Alibaba Cloud console that the DataWorks resource group is bound, the LHM Agent is online, and the data sources are registered.
- [ ] Ran `lhm-common check --profile data-validation` to confirm `env_ready=true` (API connectivity), then ran `confirm` to record the manual confirmation state.
- [ ] Configured `data-validation-skill/SKILL.md` into the AI assistant context.
- [ ] Read the common misconceptions about threshold, task_name, wildcards, etc. in `docs/user-pitfalls.md`.
- [ ] Completed a simple full-database row count validation to confirm the end-to-end pipeline works.
