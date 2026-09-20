# LHM Data Check — Python SDK Data Validation Toolkit

Drives the entire data validation workflow through the Alibaba Cloud LHM (LakeHouse Migration) Python SDK, covering data consistency verification across 18+ heterogeneous data sources.

This toolkit supports two usage modes:

- **Mode A**: conversational driving inside AI coding assistants such as QoderWork (the AI automatically generates validation code based on SKILL.md)
- **Mode B**: run the Python scripts directly (edit the parameters in the config section, then execute in one step)

If this is your first time, we recommend reading [docs/operations-manual.md](docs/operations-manual.md) first to complete platform configuration and your first validation; for the 4 standard usage scenarios see [docs/scenarios.md](docs/scenarios.md); to embed it into an external scheduling system, see [docs/integration-guide.md](docs/integration-guide.md).

---

## Standard Usage Scenarios

| Scenario | When to use | Entry point |
|------|----------|------|
| Start a validation task from scratch | First-time or repeat validation of specified tables / a whole database | `scripts/01_count_per_table.py` / `02_count_batch.py` / `03_metric_per_table.py` |
| View historical tasks and rerun | You already have a `task_id` / `batch_id` and need to view results or rerun failed tables | `summarize_batch()` / `diagnose_failed()` / `rerun_failed()` |
| External workflow invocation | Non-interactive triggering from Airflow / DataWorks / an internal scheduling platform | `run_batch_check()` / `run_count_check()` / `run_metric_check()` |
| Trigger execution and download the report | You already have a batch and need the overview, diagnosis, and report download | `summarize_batch()` / `download_report()` |

For detailed instructions, prerequisites, and expected output, see [docs/scenarios.md](docs/scenarios.md).

---

## Environment Setup

### 1. Install dependencies

The network layer calls the LHM API through the aliyun CLI (aliyun-cli-lhm plugin):

```bash
# 1. Install the aliyun CLI (version >= 3.3.8): https://help.aliyun.com/cli/

# 2. Install the lhm plugin (one-step script: pre-checks + always installs the latest version online from the public plugin index)
bash scripts/install_lhm_plugin.sh
# The plugin has a single source — the public plugin index; offline-package installation and version pinning are not supported.
# The runtime environment must be able to reach the public index (https://aliyuncli.alicdn.com/plugins);
# if a qualifying version (>= 0.1.1) is already pre-installed in the image, the script keeps it and exits 0 when the online update fails.
# The exit code is the interruption contract: 0 = environment ready; 1 = prerequisites not met, the caller must interrupt immediately
# and must not continue any LHM call (see the root SKILL.md Step 2.1 Hard Stop Gate).
# You can also install online manually:
# aliyun plugin install --names lhm

# 3. Python dependencies (the request models are provided by the local scripts/lhm_models.py; no LHM SDK needs to be installed)
pip install pyyaml
```

### 2. Configure credentials

Set the environment variables (the AccessKey must have LHM service permissions):

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="your-access-key-id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your-access-key-secret"
```

You can also manage credentials centrally through `lhm-common`'s `data_validation_config.yaml` to avoid setting environment variables manually each time. `lhm-common` also provides a pre-flight check to verify environment connectivity before first use:

```bash
python atomic-skills/lhm-common/scripts/run.py check --profile data-validation --region hangzhou
```

### 3. Confirm data source information

You must register the source and target data sources in the LHM console in advance and obtain:

- `src_ds_id` / `dst_ds_id`: the data source IDs
- `src_ds_type` / `dst_ds_type`: the data source types (e.g. MySQL, Hive, MaxCompute)

---

## Mode A: AI Conversational Driving (QoderWork)

### Setup steps

1. Place this directory (`data-validation-skill/`) into your project
2. In QoderWork's project or Skill settings, mount `data-validation-skill/` as an available Skill, or reference `../../SKILL.md` in the workspace context

### Conversation examples

```
User: Help me validate the row counts of all tables between src_db and dst_db; the source is MySQL (ds-001) and the target is Hive (ds-002)

AI assistant: Sure, I'll create a batch count-check task...
        [automatically generates code and executes it]
```

```
User: The last validation had batch_id=20001; help me see which tables did not pass and diagnose the cause

AI assistant: I'll query the report and analyze the failure causes...
        [invokes the diagnose_failed flow]
```

The AI assistant automatically selects the correct API call order based on the conventions in SKILL.md, avoiding common mistakes.

---

## Mode B: Run the Python Scripts Directly

### Available scripts

| Script | Scenario | Description |
|------|------|------|
| `scripts/01_count_per_table.py` | Per-table fine-grained | Specify concrete table names + partitions; suitable for validating key core tables |
| `scripts/02_count_batch.py` | Batch matching | Match a whole database with regex/wildcard rules; suitable for full validation |
| `scripts/03_metric_per_table.py` | Metric check | Compare aggregate metrics such as avg/max/min/sum |

### Usage steps

1. Open the script file and edit the parameters in the **[Config section]** at the top
2. Run the script:

```bash
cd data-validation-skill
python scripts/01_count_per_table.py
```

### Config section example (01_count_per_table.py)

```python
# Data sources: (id, name, type)
SRC_DS = ('ds-src-001', 'source MySQL', 'MySQL')
DST_DS = ('ds-dst-001', 'target Hive', 'Hive')

# Tables to validate: [(source_table, target_table, source_partition, target_partition)]
TABLES = [
    ('src_db.orders', 'dst_db.orders', 'dt=20240305', 'dt=20240305'),
    ('src_db.users',  'dst_db.users',  '',            ''),
]

# Validation parameters
TOTAL_COUNT_THRESHOLD = 0.0   # 0.0 = exact match
CONCURRENCY = 2
```

### Shared module common.py

Provides reusable workflow functions that can be imported directly:

```python
from common import build_client, run_count_check, run_batch_check, run_metric_check
from common import poll_exec_status, download_report, diagnose_failed, summarize_batch
from report_formatter import format_batch_summary, format_diagnosis_report

client = build_client()
# You can also load credentials from data_validation_config.yaml:
# from common import build_client_from_config
# client = build_client_from_config(config_path='data_validation_config.yaml', profile='data-validation')
task_id, batch_id = run_batch_check(client, task_name='FullDbCheck', ...)
poll_exec_status(client, task_id, batch_id)

# Overview table
summary = summarize_batch(client, batch_id)
print(format_batch_summary(summary))

# Failure diagnosis table
diagnosis = diagnose_failed(client, batch_id)
print(format_diagnosis_report(diagnosis))

url = download_report(client, batch_id)
```

> Note: the progress logs in `common.py` are uniformly written to `stderr`; `stdout` keeps only the final result or JSON, so external workflows can parse it easily.

### Report output example

`scripts/report_formatter.py` converts the raw objects returned by the SDK into Markdown tables:

```markdown
| Item                | Value             |
|---------------------|-------------------|
| Task name           | Per-table count check |
| Validation template | -                 |
| Total tables        | 2                 |
| Passed tables       | 1                 |
| Failed tables       | 1                 |
| Skipped tables      | 0                 |
| Table pass rate     | 50.00%            |
| Column consistency  | -                 |
| Difference rate     | -                 |
| Execution status    | 4(FINISHED)       |
| Validation result   | 2(FAILED)         |
```

---

## Core Concepts

### Check types

| check_type | Meaning | When to use |
|-----------|------|---------|
| 0 | Count comparison | Quickly verify whether row counts match |
| 1 | Metric comparison | Verify aggregate values such as avg/max/min/sum |

### Task modes

| task_mode | Meaning | Description |
|-----------|------|------|
| 0 | Per-table fine-grained | Specify the configuration of each table one by one |
| 1 | Batch matching | Match in bulk with rules (see references/batch_match_rules.md for the format) |

### ID passing relationships

```
Create task (add_data_check_task)
  └→ task_id  ← used for: configuring tables, saving the batch, querying, deleting

Save batch (exec_data_check_save_task)
  └→ batch_id ← used for: executing, stopping, rerunning, reporting, downloading

View report (list_data_check_report)
  └→ job_id   ← used for: column details, step details
```

### Execution status

| exec_status | Meaning | Next action |
|------------|------|---------|
| 0 | Waiting | Wait |
| 1 | Running | Can run stop |
| 2 | Terminated | Can rerun/run_failed |
| 3 | Failed | View err_message |
| 4 | Finished | View the report |

---

## FAQ

| Problem | Cause | Solution |
|------|------|------|
| Calling run/stop/rerun with task_id | These APIs require batch_id | Get batch_id via save first |
| Report download returns empty | The report has not been generated | Call generate_report first → wait for status=2 → then download |
| Batch mode matches 0 tables | The match-rule field is parsed as a regex and wildcards are commonly misused; or a MaxCompute partitioned table has no two-sided partition condition | Check the rule format (see batch_match_rules.md): to match all tables starting with `lhm_`, write `lhm_.*` instead of `lhm_*`; for MaxCompute partitioned tables, specify both the source and target partition conditions in the rule, e.g. `dt='2026-01-01';dt='2026-01-01'` |
| Task name error `E500R103` | `task_name` only allows letters (Chinese/English) and digits; it cannot contain spaces, underscores, or other special characters | Change it to `'DailyFullDbCheck'`, `'HiveToMaxComputeCount'`, etc. |
| MaxCompute partitioned-table batch check reports `full scan with all partitions` or inconsistent results | In batch mode you must enable full-table scan and explicitly specify the two-sided partition condition | Set `source_global_params='odps.sql.allow.fullscan=true'` and `target_global_params='odps.sql.allow.fullscan=true'`, and specify the source and target partition conditions in the match rule (e.g. `dt='2026-01-01';dt='2026-01-01'`) |
| SDK call reports InvalidAccessKey | Credential error | Check whether the environment variables are set correctly |

---

## Directory structure

```
data-validation-skill/
├── README.md                  ← this file (user manual)
├── SKILL.md                   ← AI Skill definition (QoderWork)
├── docs/
│   ├── operations-manual.md   ← customer operations manual (platform config + best practices)
│   ├── scenarios.md           ← standard usage scenarios
│   ├── integration-guide.md   ← external workflow integration guide
│   ├── error-patterns.md      ← error quick reference
│   └── user-pitfalls.md       ← common customer pitfalls
├── knowledge/
│   └── patterns/              ← knowledge base for complex scenarios
│       ├── validation-strategies.md
│       ├── difference-patterns.md
│       ├── fix-strategies.md
│       ├── custom-check-sql.md
│       └── complex-type-sql.md
├── references/
│   ├── api-integration.md     ← complete API reference
│   ├── batch_match_rules.md   ← batch match rule syntax
│   ├── enums.md               ← enum quick reference
│   ├── examples.md            ← complete scenario code examples
│   ├── metric_check.md        ← metric check details
│   └── troubleshooting.md     ← troubleshooting decision tree
└── scripts/
    ├── common.py              ← shared utility module
    ├── report_formatter.py    ← report Markdown formatting
    ├── 01_count_per_table.py  ← per-table count check
    ├── 02_count_batch.py      ← batch count check
    └── 03_metric_per_table.py ← per-table metric check
```

---

## Reference documents

- [Operations manual](docs/operations-manual.md) — platform configuration, first use, and best-practice examples
- [Standard usage scenarios](docs/scenarios.md) — complete instructions for the 4 core scenarios
- [External workflow integration](docs/integration-guide.md) — guide for embedding into Airflow / DataWorks / internal scheduling platforms
- [API quick reference](references/api-integration.md) — inputs/responses/examples for all SDK methods
- [Batch match rules](references/batch_match_rules.md) — match syntax for task_mode=1
- [Enum quick reference](references/enums.md) — checkType, execStatus, jobStatus, etc.
- [Complete scenario examples](references/examples.md) — end-to-end code from creation to report download
- [Troubleshooting guide](references/troubleshooting.md) — common errors and solutions
- [Common customer pitfalls](docs/user-pitfalls.md) — recommended reading before and after use
