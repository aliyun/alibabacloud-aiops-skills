---
name: alibabacloud-migration-lhm-migrate-hive-to-paimon
description: "Hive 到阿里云 DLF Paimon 数据迁移工具，覆盖存量迁移与增量迁移全流程。存量迁移：Hive DDL 自动转换为 Paimon DDL 与 format-table 外表、rclone 同步 HDFS 到 OSS、Spark Thrift Server 执行 INSERT OVERWRITE，支持 orc/parquet/csv/json/text；提供 --auto-create-db、--force、--max-parallel 并行、--verify 行数校验、--direct-read 直读模式（OSS-HDFS/DLS 场景跳过 rclone）、迁移报告自动生成。增量迁移：三阶段流水线（DDL → rclone → INSERT）执行 hive-exploration 增量探查结果。内置独立 ddl_converter 支持 Hive DDL 快速转换为 DLF Paimon/FORMAT 外表 DDL。使用场景：用户提到\"存量迁移\"、\"增量迁移\"、\"增量同步\"、\"Hive Paimon 迁移\"、\"Paimon 建表\"、\"Hive 数据湖迁移\"、\"format-table\"、\"direct-read\"、\"hive-to-paimon\"、\"migration-lhm-migrate-hive-to-paimon\"、\"转换 Hive DDL\"、\"建 DLF 表\"、\"生成 Paimon/外表 DDL\"、\"表记录数统计SQL\"时调用此 skill。"
---

# Hive-to-Paimon Data Migration

> Verified agent platforms: Claude / Qoder / OpenCode / Codex. Other platforms are not compatibility-tested.
>
> ⚠️ **This skill performs production data writes and overwrites. Preview every write operation with `--dry-run` first, and execute only after human review. All output is for reference and must be verified by a human.**

## Safety Red Lines

1. **Overwrites are irreversible**: `INSERT OVERWRITE` clears all data in the target Paimon table; `--force` runs `DROP TABLE` then recreates. Before running, confirm the target table is empty, disposable, or already backed up.
2. **Never commit credentials**: OSS AK/SK, Spark password, and Metastore password in `config.ini` are highly sensitive. **Never** commit them to Git/SVN. Add `config.ini` to `.gitignore` and inject credentials via environment variables (see "Credential Security").
3. **No real-prefix placeholders**: Never write example AKs with real prefixes like `LTAI...`. Always use `<YOUR_AK>` / `<YOUR_SK>`.
4. **Large-cluster protection**: The default rclone concurrency of 64 may overwhelm the source HDFS or target OSS. On production clusters, evaluate with low concurrency first (e.g. `--max-parallel 2 --transfers 16`) before scaling up.
5. **DLS direct-read boundary**: `--direct-read` only applies to OSS-HDFS (DLS) sources. Enabling it on plain HDFS results in unreadable data.
6. **Writes require confirmation**: Before running `CREATE TABLE` / `DROP TABLE` / `INSERT OVERWRITE` / `rclone copy`, the agent must show the impact and obtain explicit confirmation (see [references/agent-rules.md](./references/agent-rules.md)).

## Tooling Overview

This skill depends on no external MCP tools; it is implemented via a Python CLI plus external services:

| Name | Type | Purpose |
|------|------|---------|
| `python main.py` | Local CLI | Full-migration orchestration (Step 1-5) |
| `python incremental_migrate.py` | Local CLI | Incremental three-phase pipeline |
| `python scripts/ddl_converter/cli.py` | Local CLI | Standalone Hive DDL → Paimon/external DDL conversion |
| `pyhive (Spark Thrift)` | Python lib | Execute DDL / INSERT via Spark Thrift Server |
| `rclone` | System CLI | HDFS → OSS data sync |
| `hive` / `hadoop` CLI | System CLI | Extract DDL from Hive Metastore in `-d`/`-t` modes |
| Hive Metastore DB (MySQL/PostgreSQL) | External DB | Metadata queries (only in `-d`/`-t` modes) |

## Scenario Detection and Tool Selection

Choose the execution path based on user input and environment:

| Trigger condition | Recommended tool | Key flags |
|-------------------|------------------|-----------|
| User already has an inspect output directory | `main.py -e <explore_dir>` | Recommended path |
| User only gives a database list (e.g. `ads,dwd`) | `main.py -d ads,dwd` | Needs `[metastore_db]` + hive CLI |
| User wants only a few specific tables | `main.py -t db1.t1,db2.t2` | Same as above |
| Source is OSS-HDFS / DLS (contains `oss-dls.aliyuncs.com`) | Add `--direct-read` | Skips rclone |
| Target database may not exist | Add `--auto-create-db` | Auto-creates DB (**needs confirmation**) |
| Target table exists but must be rebuilt | Add `--force` | DROP+CREATE (**per-table confirmation**) |
| User wants batched / resumable runs | `--start-step N` / `--skip-steps a,b` | Reuse the same `--output-dir` |
| Only DDL conversion, no execution | `scripts/ddl_converter/cli.py` | Connects to no external service |
| User already has an inspect incremental output | `incremental_migrate.py -i <incr_dir>` | Three-phase pipeline |

Decision flow:
1. Check the input source first (explore dir / DB list / table list).
2. Check the source storage type (plain HDFS / DLS) to decide whether to enable `--direct-read`.
3. Check whether same-name tables/DBs exist on the target to decide `--force` / `--auto-create-db`.
4. Preview any write operation with `--dry-run` before execution.

## Overview

### Full Migration (main.py)

| Step | Script | Key output |
|------|--------|------------|
| 1. Generate Paimon internal-table DDL | `step1_generate_paimon_ddl.py` | `paimon_ddl.sql` + `table_manifest.csv` |
| 2. Generate external-table DDL | `step2_generate_ext_ddl.py` | `paimon_ext_ddl.sql` + `text_tables_insert.sql` |
| 3. Execute table-creation DDL | `step3_execute_ddl.py` | `ddl_result.csv` |
| 4. rclone data sync | `step4_rclone_sync.py` | `rclone_result.csv` |
| 5. INSERT OVERWRITE | `step5_insert_overwrite.py` | `insert_result.csv` |

The orchestrator `main.py` chains Step 1-5, supporting `--start-step` for resumable runs and `--skip-steps` to skip specific steps.

### Incremental Migration (incremental_migrate.py)

| Phase | Content | Key output |
|-------|---------|------------|
| Phase 1 | Execute DDL (CREATE TABLE) | `incr_ddl_result.csv` |
| Phase 2 | rclone data sync | `incr_rclone_result.csv` |
| Phase 3 | INSERT OVERWRITE data load | `incr_insert_result.csv` |

The standalone `incremental_migrate.py` executes commands generated by the migration-lhm-inspect-hive-metastore incremental exploration, supporting parallel and background execution.

---

## Quick Start

1. Edit `config.ini` with the real connection info for your environment (Metastore DB, HDFS, OSS, Spark Thrift). Full field reference: [references/configuration.md](./references/configuration.md).
2. Run one of:

```bash
# Run a full migration using migration-lhm-inspect-hive-metastore output
python main.py -e /path/to/hive_explore_all_dbs_YYYYMMDD/ -c config.ini

# Or migrate specific databases
python main.py -d ads,dwd,dws -c config.ini

# dry-run preview (does not execute)
python main.py -e /path/to/explore/ -c config.ini --dry-run

# direct-read mode (OSS-HDFS/DLS; external table points at source path, skips rclone)
python main.py -e /path/to/explore/ -c config.ini --direct-read
```

> 🔐 All config examples use `<...>` placeholders. **In production, inject credentials via environment variables** and add `config.ini` to `.gitignore`.

---

## Input Sources

### Source A: migration-lhm-inspect-hive-metastore output (recommended)

```bash
python main.py -e /path/to/hive_explore_all_dbs_YYYYMMDD/ -c config.ini
```

The explore directory must contain `summary_report.csv` and a `ddl_files/` subdirectory. Use `--filter-db` and `--filter-tables` to further filter the explore results.

### Source B: specify databases or table names

```bash
python main.py -d ads,dwd -c config.ini              # by database
python main.py -t ads.ads_xxx,dwd.dwd_yyy -c config.ini   # by table
```

This mode requires the `[metastore_db]` config and a usable hive CLI on the ECS host.

---

## Step Details

### Step 1: Generate Paimon internal-table DDL

Converts Hive DDL into Paimon internal-table CREATE statements.

**Conversion rules:**
1. Remove Hive storage info: `ROW FORMAT` / `STORED AS` / `LOCATION` / `TBLPROPERTIES`.
2. Add `USING paimon`.
3. Merge partition columns into the column list (required by Paimon).
4. `PARTITIONED BY` keeps only column names, not types.
5. Add `IF NOT EXISTS`.

```bash
python step1_generate_paimon_ddl.py -e /path/to/explore/ -o output/
```

### Step 2: Generate external-table DDL

Generates Paimon format-table external-table DDL based on the storage format.

- **orc/parquet/json/csv**: standard external table, table-name suffix `_oss`.
- **text**: single-column `raw_line string` external table (suffix `_oss`), plus a split+CAST INSERT statement.

```bash
python step2_generate_ext_ddl.py -m output/table_manifest.csv -c config.ini -o output/
# direct-read mode (external-table path points at the source path)
python step2_generate_ext_ddl.py -m output/table_manifest.csv -c config.ini -o output/ --direct-read
```

### Step 3: Execute table-creation DDL

Creates internal and external tables via Spark Thrift Server (pyhive).

```bash
python step3_execute_ddl.py -c config.ini --inner-ddl output/paimon_ddl.sql --ext-ddl output/paimon_ext_ddl.sql
```

### Step 4: rclone data sync

Runs rclone to sync HDFS data to OSS. Supports multi-table parallel sync; the OSS path stays identical to the HDFS path.

```bash
python step4_rclone_sync.py -m output/table_manifest.csv -c config.ini --max-parallel 4
```

### Step 5: INSERT OVERWRITE

Generates and runs INSERT OVERWRITE to load external-table data into the Paimon internal tables. TextFile tables use the special INSERT statement generated in Step 2.

```bash
python step5_insert_overwrite.py -m output/table_manifest.csv -c config.ini --text-insert output/text_tables_insert.sql
```

---

## TextFile Format Special Handling

Paimon format-table cannot read multi-column TextFile data directly. Solution:

1. **External table**: create a single-column `raw_line string` external table (suffix `_oss`) with `file.format = 'text'`.
2. **INSERT**: use `split(raw_line, '\u0001')` to split fields, `CAST` to convert types, and `CASE WHEN ... = '\\N' THEN NULL` for nulls.

This is handled automatically in Step 2; no manual intervention needed.

---

## Direct-Read Mode (OSS-HDFS/DLS)

When source data is on OSS-HDFS (DLS), rclone cannot access the DLS data layer via the S3 API (DLS and plain OSS are different storage layers). Use `--direct-read` mode:

- The Step 2 external-table DDL uses the source DLS path directly (e.g. `oss://bucket.cn-hangzhou.oss-dls.aliyuncs.com/...`).
- Step 4 (rclone) is skipped automatically.
- Spark EMR has a built-in DLS driver and can read DLS paths directly.

```bash
python main.py -e /path/to/explore/ -c config.ini --direct-read
```

**Applicable when:**
- The source is Alibaba Cloud OSS-HDFS (DLS) and the Spark cluster can access DLS paths directly.
- No need to copy data to another OSS bucket; the external table reads the source location directly.
- `[rclone_source_hdfs]` and `[rclone_target_s3]` can be omitted (only `[spark_thrift]` is needed).

---

## Orchestrator (main.py)

```bash
python main.py \
  (-e <explore_dir> | -d <db_list> | -t <table_list>) \
  -c config.ini \
  [--output-dir output/xxx]     # output directory
  [--start-step N]              # start from step N
  [--skip-steps 3,4]            # skip specific steps
  [--dry-run]                   # dry-run all steps
  [--direct-read]               # direct-read mode, skip rclone
  [--filter-db ads,dwd]         # filter databases
  [--filter-tables db.t1,db.t2] # filter tables
```

**Resumable-run example** (Step 1-2 done, continue from Step 3):
```bash
python main.py -e /path/to/explore -c config.ini --start-step 3 --output-dir output/20260413
```

---

## Output Layout

```
output/YYYYMMDDHHMMSS/
├── paimon_ddl.sql              # Step 1: Paimon internal-table DDL
├── table_manifest.csv          # Step 1: table manifest (bridge between steps)
├── paimon_ext_ddl.sql          # Step 2: Paimon external-table DDL
├── text_tables_insert.sql      # Step 2: TextFile-table INSERT statements
├── insert_overwrite_all.sql    # Step 5: all INSERT statements combined
├── rclone_result.csv           # Step 4: rclone sync results
├── insert_result.csv           # Step 5: INSERT execution results
└── logs/                       # per-step error logs
```

---

## Environment Setup

```bash
# Python dependencies
pip install pyhive thrift thrift_sasl

# Only for -d/-t input modes (connect to Metastore DB)
pip install PyMySQL           # MySQL Metastore
pip install psycopg2-binary   # PostgreSQL Metastore

# rclone (data sync tool) — the script auto-detects and tries to install it
#   CentOS/RHEL: yum install -y epel-release && yum install -y rclone
#   Debian/Ubuntu: apt-get install -y rclone
#   Generic: curl https://rclone.org/install.sh | bash
```

---

## Troubleshooting

See [references/troubleshooting.md](./references/troubleshooting.md), covering 14 common error classes (preflight, Spark connection, DDL execution, rclone sync, TextFile INSERT, DLS access, EMR Gateway 401, AK/SK leaks, etc.) and how to diagnose them.

## Agent Execution Rules

See [references/agent-rules.md](./references/agent-rules.md), which covers direct-read auto-detection, the rclone parameter-confirmation flow (with AK/SK masking), and the write-operation confirmation mechanism.

---

## Incremental Migration (incremental_migrate.py)

### Prerequisites

First generate an output directory via the incremental exploration of the migration-lhm-inspect-hive-metastore skill, containing:
- `sync_commands.sh` — rclone data-sync commands.
- `paimon_sync.sql` — Paimon table-creation and data-load SQL.
- `metastore_delta.csv` — change manifest (optional, correlates table names).
- `schema_changes.txt` — schema-change list (optional, warning only).

### Usage

```bash
python incremental_migrate.py -i /path/to/incr_output/ -c config.ini              # run
python incremental_migrate.py -i /path/to/incr_output/ -c config.ini --dry-run    # preview
python incremental_migrate.py -i /path/to/incr_output/ -c config.ini --background # background
python incremental_migrate.py -i /path/to/incr_output/ -c config.ini --skip-phase 2    # only DDL+INSERT
python incremental_migrate.py -i /path/to/incr_output/ -c config.ini --skip-phase 1,3  # only rclone
```

### Three-Phase Pipeline

1. **Phase 1 — DDL execution**: extract CREATE TABLE statements from `paimon_sync.sql` and create external + internal tables via Spark Thrift Server.
2. **Phase 2 — rclone sync**: extract rclone copy commands from `sync_commands.sh` and sync data in parallel (HDFS → OSS).
3. **Phase 3 — INSERT OVERWRITE**: extract INSERT OVERWRITE statements from `paimon_sync.sql` and load data.

The order is fixed as DDL → rclone → DML, ensuring table creation precedes sync, and sync precedes data load.

### Output Layout

```
<incr_output>/migrate_result/
├── incr_ddl_result.csv         # Phase 1 result
├── incr_rclone_result.csv      # Phase 2 result
├── incr_insert_result.csv      # Phase 3 result
├── incr_summary.txt            # full-pipeline summary report
└── logs/                       # per-phase execution logs
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `-i, --incr-dir` | Incremental explore output directory (required) |
| `-c, --config` | Config file path |
| `-o, --output-dir` | Result output dir (default `<incr-dir>/migrate_result/`) |
| `--max-parallel` | rclone max parallelism |
| `--skip-phase` | Skip phases, comma-separated (e.g. `1,2` or `2`) |
| `--dry-run` | Print only, do not execute |
| `--background` | Background run, detached from terminal session |

---

## Standalone DDL Converter (ddl_converter)

A lightweight built-in Hive DDL → DLF DDL converter that supports stdin/stdout piping and needs no database connection.

```bash
# Paimon internal-table mode
cat hive_ddl.sql | python scripts/ddl_converter/cli.py --mode paimon

# FORMAT external-table mode (or --mode both to output both)
cat hive_ddl.sql | python scripts/ddl_converter/cli.py --mode ext \
  --source-hdfs-nameservice mycluster \
  --oss-bucket my-bucket \
  --oss-prefix data/warehouse
```

### Output Modes

| Mode | Engine declaration | Use case |
|------|--------------------|----------|
| `paimon` | `USING paimon` | DLF Paimon internal table |
| `ext` | `USING ORC/CSV/PARQUET + OPTIONS` | Spark SQL external table |
| `both` | outputs both | Full migration preview |

### Automatic Format Detection

Maps output format automatically from the Hive table's SERDE/INPUTFORMAT: OrcSerde → ORC, LazySimpleSerDe → CSV, ParquetHiveSerDe → PARQUET, AvroSerDe → AVRO, JsonSerDe → JSON. See [references/serde-mapping.md](./references/serde-mapping.md) for detailed mapping rules.

---

## COUNT Verification SQL Generation

Provide a partition-info CSV via `--partition-info` to auto-generate partition-aware COUNT verification SQL after migration:

```bash
python scripts/main.py -e /path/to/explore/ -c config.ini --partition-info partitions.csv
```

Partition-info CSV format:
```
db.table_name,partition_col1,partition_col2
ads.ads_user_stats,dt
dwd.dwd_event_log,dt,platform
```

---

## Suite Relationship

This skill is part of the **lakehouse migration suite**. Using the exploration output of `migration-lhm-inspect-hive-metastore` as input is recommended.

- **migration-lhm-inspect-hive-metastore**: Hive metadata exploration; output can be used directly as this skill's input (`-e <explore_dir>`).
- **migration-lhm-migrate-sqlserver-to-maxcompute-ddl**: SQL Server → MaxCompute DDL migration.
- **migration-lhm-manage-maxcompute-mms**: MaxCompute MMS migration-service monitoring and management.

See [references/overview.md](./references/overview.md) for an architecture overview.

---

## Prerequisites

### Runtime

- **Python 3.7+**
- **rclone** ≥ 1.60 (required in standard mode, optional in DLS direct-read mode)
- **Spark EMR cluster** with a configured Paimon Catalog (DLF Catalog or self-managed); Spark ≥ 3.5.2 (required for TextFile format)
- Optional: `hadoop` / `hive` CLI (only for `-d`/`-t` input modes)

### Python Dependencies

```bash
pip install "pyhive[hive]>=0.7,<0.8" thrift thrift_sasl   # required
pip install "PyMySQL>=1.0"            # MySQL Metastore (only -d/-t modes)
pip install "psycopg2-binary>=2.9"    # PostgreSQL Metastore (only -d/-t modes)
```

### Credential Security (env vars recommended)

config.ini supports `${VAR}` environment-variable interpolation. Inject credentials via the variables below to avoid plaintext storage:

| Environment variable | Purpose |
|----------------------|---------|
| `METASTORE_PASSWORD` | Hive Metastore DB password |
| `OSS_AK` / `OSS_SK` | Target OSS AK/SK |
| `SRC_OSS_AK` / `SRC_OSS_SK` | Source S3/OSS AK/SK |
| `SPARK_PASSWORD` | Spark Thrift Server password |

Additional requirements:
- `config.ini` must be added to `.gitignore`.
- AK/SK must never be printed in plaintext in logs, stdout, or report CSVs (scripts already mask them; keep masking when customizing).
- Prefer Alibaba Cloud STS temporary credentials over long-lived AK/SK.

---

## Required Permissions

Minimum permissions by operation type. **All write permissions require user confirmation after the agent prompt.**

### Read permissions (exploration, DDL extraction)

| Resource | Permission | Purpose |
|----------|------------|---------|
| Hive Metastore DB | `SELECT ON hivemeta.*` | Query TBLS/DBS/SDS/PARTITIONS |
| HDFS source path | `READ` | rclone standard-mode reads |
| OSS-HDFS (DLS) source path | `oss:GetObject` / `oss:ListObjects` | DLS direct-read mode |
| Spark Catalog | `SELECT` on target tables | `--verify` row-count check |

### Write permissions (migration execution, requires confirmation)

| Resource | Permission | Purpose |
|----------|------------|---------|
| OSS target bucket | `oss:PutObject` / `oss:DeleteObject` / `oss:ListObjects` | rclone writes to target bucket |
| Spark Catalog (Paimon) | `CREATE DATABASE` (only `--auto-create-db`) | auto-create DB |
| Spark Catalog (Paimon) | `CREATE TABLE` / `DROP TABLE` (only `--force`) / `INSERT OVERWRITE` | create tables and overwrite data |

Recommendation: use a dedicated migration RAM user/role with a custom least-privilege policy and console login disabled.

---

## Termination and Summary

After a migration task ends (success, failure, or partial failure), the agent must output a structured summary containing at least:

1. **Execution mode**: standard / direct-read / incremental; the step range covered.
2. **Scope stats**: number of DBs / tables / total data volume (from `table_manifest.csv`).
3. **Result stats**: succeeded / failed / skipped tables, broken down per step (DDL/rclone/INSERT).
4. **Report paths**: the `output/YYYYMMDDHHMMSS/` directory and key CSV/log locations.
5. **Top 3 failure causes**: aggregated from `*_errors.log` and `*_result.csv`.
6. **Next-step suggestions**: retry failures (`--start-step N`) / row-count check (`--verify`) / manual review.
7. **Disclaimer**: > This output is based on automated migration-script results. **Whether the source Hive tables can be decommissioned must be decided after human review and business-side validation.**

Output example:
```
[Migration complete] Mode: standard | Scope: 3 DBs / 27 tables
  ✅ Success: 25  ❌ Failed: 2  ⏭ Skipped: 0
  Report: output/20260514_103045/
  Top failures: ① TextFile INSERT error (1)  ② OSS auth failure (1)
  Suggestion: python main.py ... --start-step 5 --filter-tables ads.t1,dwd.t2
  ⚠️ Please review row counts and sample data manually before decommissioning source Hive tables.
```
