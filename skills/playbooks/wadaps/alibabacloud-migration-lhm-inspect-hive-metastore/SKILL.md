---
name: alibabacloud-migration-lhm-inspect-hive-metastore
description: 执行 Hive 数据表探查任务，支持全量探查和增量探查，提供两种连接方式：DB 直连（通过 Metastore MySQL/PostgreSQL 数据库）和 Thrift 直连（通过 HMS Thrift API 端口 9083）。全量探查导出所有表的元数据、存储大小和 DDL；增量探查识别指定时间节点之后的表创建、结构变更、数据变更和分区变更。使用场景：用户提到"Hive 探查"、"全量探查"、"增量探查"、"Hive 元数据"、"hive_dive"、"metastore 变更"、"Thrift 探查"、"migration-lhm-inspect-hive-metastore"时调用此 skill。不适用于数据迁移执行、DDL 转换、数据写入等场景，这些功能由 migration-lhm-migrate-hive-to-paimon 等下游 skill 承担。
---

# Hive Metadata Exploration

> This skill targets AI agent platforms that support terminal command execution (e.g. Claude Code, Qoder).

## Safety Red Lines

- Database passwords in the config file must never be printed to the terminal or logs.
- Only read-only exploration operations are performed; Hive metadata is never modified.
- Exploration output files contain no sensitive credentials.
- Never echo the plaintext password from config.ini back to the user.

## Tooling Overview

> This skill depends on no MCP tools. It connects to the Hive Metastore directly via local Python/Bash scripts.

## Prerequisites

- Python >= 3.7
- `pip install PyMySQL>=1.0.0` — MySQL Metastore driver
- `pip install psycopg2-binary>=2.9` — PostgreSQL Metastore driver
- `pip install hmsclient>=0.1.1` — base dependency for Thrift mode
- `pip install thrift_sasl gssapi` — Kerberos authentication (optional)
- `hadoop` CLI — only needed in `size_source=hadoop` mode
- `hive` CLI — only needed for `hive_dive.sh` full exploration

## Required Permissions

### DB direct-connect mode
- MySQL/PostgreSQL read-only: `SELECT` on `TBLS`, `DBS`, `SDS`, `TABLE_PARAMS`, `PARTITIONS`, `PARTITION_KEYS`, `PARTITION_PARAMS`

### Thrift mode
- HMS Thrift API read access: `get_all_databases`, `get_all_tables`, `get_table`, `get_partitions`

### Storage size retrieval (optional)
- `hadoop fs -du -s` access (HDFS path read permission)

---

## Overview

| Mode | Connection | Script | Key output |
|------|------------|--------|------------|
| Full exploration | DB direct | `hive_dive.sh` | `summary_report.csv` + per-table DDL files |
| Full exploration | Thrift direct | `hive_dive_thrift.py` | `summary_report.csv` + per-table DDL files |
| Incremental | DB direct | `get_metastore_changes.py` | `metastore_delta.csv` |
| Incremental | Thrift direct | `get_metastore_changes_thrift.py` | `metastore_delta.csv` |

**Choosing a connection method:**
- **DB direct**: connects straight to the Metastore MySQL/PostgreSQL DB + hadoop/hive CLI; suitable when you have DB access.
- **Thrift direct**: uses the HMS Thrift API (port 9083); needs only Python, no hadoop/hive CLI; suitable for remote or container environments.

---

## Full Exploration (hive_dive.sh)

### How It Works

1. Connect to the Hive Metastore database (MySQL) and query `TBLS / DBS / SDS` to get all managed and external tables.
2. Run `hadoop fs -du -s <location>` per table to get storage size.
3. Run `hive -e "SHOW CREATE TABLE"` to export DDL into individual `.sql` files.
4. Aggregate into `summary_report.csv`.

### Configuration

Edit the variables at the top of the script:

```bash
MYSQL_HOST="localhost"
MYSQL_USER="root"
MYSQL_PASSWORD="your_password"
MYSQL_DATABASE="hive"   # Metastore database name
```

### Commands

```bash
# Explore all databases → output dir: hive_explore_all_dbs_YYYYMMDD/
bash hive_dive.sh

# Explore specific databases → output dir: hive_explore_batch_YYYYMMDD/
bash hive_dive.sh db1 db2 db3
```

### Output Layout

```
hive_explore_<all_dbs|batch>_YYYYMMDD/
├── summary_report.csv     # columns: db_name, tbl_name, tbl_location, total_size_bytes, total_size_human, ddl_file_path
├── ddl_files/
│   └── <db>.<table>.sql   # SHOW CREATE TABLE result per table
└── error.log              # hadoop/hive command error log
```

### Notes

- `set -e` is enabled; if the MySQL connection fails, the script exits immediately.
- When DDL export fails, the file content is `-- FAILED TO GET DDL for <db>.<table>`, without affecting the overall flow.
- Views are out of scope (the WHERE clause filters for `MANAGED_TABLE` / `EXTERNAL_TABLE`).

> Storage sizes in the exploration result are based on a Metastore metadata snapshot and may differ from the actual runtime state; cross-verify critical data.

---

## Incremental Exploration (get_metastore_changes.py)

### How It Works

Queries the Hive Metastore DB directly to detect changes after a given time point, with dedup priority:
`TABLE_CREATE > TABLE_MODIFIED > DATA_MODIFIED`. Partition changes of newly created tables are filtered automatically.

### Change Types

| type | Meaning |
|------|---------|
| `TABLE_CREATE` | New table |
| `TABLE_MODIFIED` | Schema change (existing table) |
| `DATA_MODIFIED` | Data change of a non-partitioned table (no schema change) |
| `PARTITION_CREATE` | New partition (not a new table) |
| `PARTITION_MODIFIED` | Partition data change (not a new partition) |

### Environment Setup

```bash
# MySQL Metastore
pip install PyMySQL

# PostgreSQL Metastore
pip install psycopg2-binary
```

### Config File (config.ini)

**Only the `[metastore_db]` section is needed** (incremental exploration does not involve rclone/paimon):

```ini
[metastore_db]
db_type = mysql          # or postgres
host = your_host
port = 3306
user = your_user
password = your_password
database = hivemeta      # Metastore database name
```

> **Security tip**: in production, reference the password via an environment variable, e.g. `password = ${HIVE_METASTORE_PWD}`, to avoid plaintext storage.

### Command

```bash
# Run incremental metadata query only (does not generate rclone/paimon statements)
python get_metastore_changes.py \
  -c config.ini \
  -s "2026-01-12 18:00:00" \
  -o metastore_delta.csv
```

### Output Format (metastore_delta.csv)

```
type,db_name,table_name,is_partitioned,partition_keys,partition_values,location,change_time
TABLE_CREATE,default,new_table,1,p_dt,,hdfs://.../new_table,2026-01-15 14:33:00
PARTITION_MODIFIED,default,orders,1,dt,2026-01-12,hdfs://.../orders/dt=2026-01-12,2026-01-15 15:00:00
```

Field notes:
- `is_partitioned`: 1 = partitioned table, 0 = non-partitioned.
- `partition_keys`: partition key names (comma-separated).
- `partition_values`: partition values (`/`-separated, key names removed).
- `location`: HDFS/OSS path.

---

## Troubleshooting

| Issue | Diagnostic direction |
|-------|----------------------|
| Full-exploration MySQL connection fails | Check `MYSQL_HOST/USER/PASSWORD/DATABASE` and network connectivity |
| `hadoop fs -du` errors | Check `error.log`; confirm HADOOP_HOME and cluster connectivity |
| `hive` DDL export fails | Check `error.log`; confirm the hive command works and table names have no special characters |
| Incremental query returns empty | Confirm `-s` time format is `YYYY-MM-DD HH:MM:SS`; confirm the timezone matches the Metastore |
| psycopg2 / PyMySQL not installed | Install the corresponding driver per the environment-setup steps |

---

## Unified Entry Point (hive_explore.py) — recommended

`hive_explore.py` is the recommended way to use this skill, integrating config management, connection preflight, automatic fallback, and profile saving.

### Subcommands

```
python hive_explore.py <subcommand> [options]

Subcommands:
  full      Full exploration (Thrift mode)
  incr      Incremental exploration (DB or Thrift)
  test      Connection test (connectivity check only)
  compare   Compare mode (run DB + Thrift together, produce a diff report)
```

### Common Examples

```bash
# connection test
python hive_explore.py test --host 10.0.1.100 --thrift-port 9083

# Thrift full exploration
python hive_explore.py full --host 10.0.1.100 --mode thrift db1 db2

# DB incremental exploration
python hive_explore.py incr --mode db --host 10.0.1.100 --user root --password xxx \
  -s "2026-01-12 18:00:00"

# Thrift incremental exploration (interactive config completion)
python hive_explore.py incr --mode thrift -s "2026-01-12 18:00:00"

# compare mode
python hive_explore.py compare --host 10.0.1.100 --user root --password xxx \
  -s "2026-01-12 18:00:00"

# use/save a profile
python hive_explore.py incr --profile prod -s "2026-01-12 18:00:00"
python hive_explore.py full --host 10.0.1.100 --save-profile prod
```

### Global Parameters

| Parameter | Description |
|-----------|-------------|
| `-c, --config` | Config file path (default: config.ini) |
| `--profile NAME` | Load a saved profile |
| `--save-profile NAME` | Save the current config as a profile |
| `--mode {db,thrift,both}` | Connection mode (default: thrift) |
| `--host` | Host address (shared by DB and Thrift) |
| `--thrift-host` | Thrift-specific host |
| `--port` | DB port |
| `--thrift-port` | Thrift port |
| `--user` / `--password` | DB authentication |
| `--database` | Metastore database name (auto-detected if empty) |
| `--db-type {mysql,postgres}` | DB type |
| `--auth {NOSASL,KERBEROS}` | Thrift authentication method |
| `--fallback-host` | Fallback host |
| `--no-interactive` | Disable interactive prompts |

### Features

- **Connection preflight**: checks port connectivity before running to surface network issues fast.
- **Automatic fallback**: prompts to switch to Thrift when the DB is unreachable.
- **Database-name auto-detection**: auto-detects when `--database` is omitted in DB mode.
- **Fallback host**: configure internal/external dual addresses via `--fallback-host`.
- **Automatic retry**: retries on network jitter (exponential backoff, up to 3 times).
- **Config profiles**: save/load common environment configs to avoid repeated input.
- **Friendly error messages**: classifies errors and gives specific diagnostic suggestions.

---

## Thrift Direct-Connect Mode

### When to Use

- Cannot access the Hive Metastore MySQL/PostgreSQL database directly.
- No `hadoop` / `hive` CLI in the environment (e.g. a remote host or container).
- Can only reach the HMS Thrift Service over the network (port 9083).

### Environment Setup

```bash
# base dependency (unauthenticated NOSASL mode)
pip install hmsclient

# for Kerberos authentication
pip install hmsclient thrift_sasl gssapi
```

### Config File (config.ini)

Fill in the `[general]` and `[thrift]` sections:

```ini
[general]
connection_mode = thrift    # 'db' or 'thrift'

[thrift]
host = your_hms_host        # HMS Thrift service address
port = 9083                 # Thrift port
auth = NOSASL               # NOSASL or KERBEROS
kerberos_principal = hive/_HOST@YOUR.REALM  # only for KERBEROS mode
timeout = 60                # connection timeout (seconds)
size_source = params        # table-size source: params / hadoop / skip
```

**`size_source` explained:**

| Value | Behavior | Requirement |
|-------|----------|-------------|
| `params` | Read from the Hive table parameter `totalSize` (requires prior `ANALYZE TABLE`) | No external dependency |
| `hadoop` | Get actual size via `hadoop fs -du -s` | Requires hadoop CLI |
| `skip` | Always show N/A | None |

**Kerberos authentication**: obtain a ticket before running the script:

```bash
# using a password
kinit user@YOUR.REALM

# using a keytab
kinit -kt /path/to/keytab principal@YOUR.REALM
```

### Full Exploration (hive_dive_thrift.py)

#### How It Works

1. Connect to HMS via the Thrift API, calling `get_all_databases()` / `get_all_tables()` / `get_table()` for metadata.
2. Get storage size from table parameters or the hadoop command.
3. Rebuild DDL from the Thrift Table object (via `ddl_builder.py`).
4. Aggregate into `summary_report.csv`.

#### Commands

```bash
# explore all databases
python hive_dive_thrift.py -c config.ini

# explore specific databases
python hive_dive_thrift.py -c config.ini db1 db2 db3
```

#### Output Layout

Identical to `hive_dive.sh`:

```
hive_explore_<all_dbs|batch>_YYYYMMDD/
├── summary_report.csv     # columns: db_name, tbl_name, tbl_location, total_size_bytes, total_size_human, ddl_file_path
├── ddl_files/
│   └── <db>.<table>.sql   # DDL rebuilt from Thrift metadata
└── error.log              # error log
```

#### Notes

- DDL is rebuilt from Thrift metadata and may differ in formatting from `SHOW CREATE TABLE` output (property ordering, whitespace), but is semantically equivalent.
- With `size_source = params`, size may show N/A if the table has never run `ANALYZE TABLE`.
- Downstream tools `generate_rclone_script.py` / `generate_paimon_statements.py` can consume the output directly.

### Incremental Exploration (get_metastore_changes_thrift.py)

#### How It Works

Iterates all tables and partitions via the Thrift API, checking timestamp parameters, implementing the same five-stage dedup logic as the DB-direct version:
`TABLE_CREATE > TABLE_MODIFIED > DATA_MODIFIED > PARTITION_CREATE > PARTITION_MODIFIED`

#### Commands

```bash
# scan all databases
python get_metastore_changes_thrift.py \
  -c config.ini \
  -s "2026-01-12 18:00:00" \
  -o metastore_delta.csv

# limit scan scope (improves performance on large clusters)
python get_metastore_changes_thrift.py \
  -c config.ini \
  -s "2026-01-12 18:00:00" \
  -o metastore_delta.csv \
  --databases db1 db2
```

#### Output Format

Identical to `get_metastore_changes.py`:

```
type,db_name,table_name,is_partitioned,partition_keys,partition_values,location,change_time
TABLE_CREATE,default,new_table,1,p_dt,,hdfs://.../new_table,2026-01-15 14:33:00
PARTITION_MODIFIED,default,orders,1,dt,2026-01-12,hdfs://.../orders/dt=2026-01-12,2026-01-15 15:00:00
```

#### Performance Notes

Thrift incremental exploration iterates all tables and partitions to check timestamps, which can be slow on large clusters. Limit the scan scope with `--databases`.

### Orchestrator Integration

`main_metastore_changes.py` supports Thrift mode and switches automatically via `connection_mode` in `config.ini`:

```bash
# after setting connection_mode = thrift in config.ini
python main_metastore_changes.py -c config.ini -s "2026-01-12 18:00:00"
```

---

## Thrift Mode Troubleshooting

| Issue | Diagnostic direction |
|-------|----------------------|
| Thrift connection timeout | Check whether the HMS service is running, port 9083 is reachable, and firewall rules |
| Kerberos authentication fails | Confirm `kinit` was run, check ticket validity with `klist`, verify the principal config |
| `ImportError: hmsclient` | Run `pip install hmsclient` |
| `ImportError: thrift_sasl` | Kerberos mode requires: `pip install thrift_sasl gssapi` |
| DDL rebuild incomplete | A few special tables may lack a StorageDescriptor; check error.log |
| Table size shows N/A | With `size_source = params`, run `ANALYZE TABLE` first; or switch to `hadoop` mode |
| Incremental scan too slow | Limit scan scope with `--databases` |

---

## Known Limitations

- Thrift incremental exploration must iterate all tables/partitions; performance is slow on large clusters (>10000 tables). Limit scope with `--databases`.
- `size_source=params` depends on the table having run `ANALYZE TABLE`; otherwise size shows N/A.
- DDL is rebuilt from Thrift metadata and may differ in formatting from `SHOW CREATE TABLE` (property ordering, whitespace), but is semantically equivalent.
- Hive view exploration is not supported (`VIRTUAL_VIEW` / `MATERIALIZED_VIEW` are filtered).
- DB direct mode depends on the MySQL/PostgreSQL client library; Thrift mode depends on `hmsclient`.

---

## File Structure

```
scripts/
├── hive_explore.py                    # unified entry point (recommended)
├── connection_utils.py                # connection utils (preflight/retry/fallback/error classification)
├── config_manager.py                  # config management (profile/interactive completion)
├── hive_dive.sh                       # full exploration (DB direct, Bash)
├── hive_dive_thrift.py                # full exploration (Thrift direct)
├── get_metastore_changes.py           # incremental exploration (DB direct)
├── get_metastore_changes_thrift.py    # incremental exploration (Thrift direct)
├── thrift_client.py                   # Thrift connection factory (NOSASL/Kerberos)
├── ddl_builder.py                     # DDL rebuild engine
├── main_metastore_changes.py          # full-pipeline orchestrator
├── generate_rclone_script.py          # rclone migration-script generation
└── generate_paimon_statements.py      # Paimon sync-SQL generation

config.ini                             # unified config file (skill root)
```

---

## Suite Relationship

This skill is part of the **lakehouse migration suite**; its exploration output can be used directly as input to downstream tools (`-e <explore_dir>`).

Related tools:
- **migration-lhm-migrate-hive-to-paimon**: uses this skill's exploration result to run an end-to-end Hive → Paimon migration.
- **migration-lhm-migrate-hive-to-maxcompute**: uses this skill's exploration result to run an end-to-end Hive → MaxCompute migration.
- **migration-lhm-migrate-sqlserver-to-maxcompute-ddl**: SQL Server → MaxCompute DDL migration.
- **migration-lhm-manage-maxcompute-mms**: MaxCompute MMS migration-service monitoring and management.

Downstream toolchain:
1. **rclone data migration** (`generate_rclone_script.py`): generates HDFS → S3 rclone copy scripts.
2. **Paimon sync** (`generate_paimon_statements.py`): generates Paimon external-table creation and data-sync SQL.
3. **Full-pipeline orchestration** (`main_metastore_changes.py`): chains incremental query → rclone script → Paimon SQL.

The output format is identical for both connection methods, so downstream tools need not distinguish the data source.

---

## Termination and Summary

After exploration completes, the agent should report to the user:

1. **Output directory path** and key file locations (`summary_report.csv` or `metastore_delta.csv`).
2. **Exploration stats**: number of databases and tables explored (full), or number of change records (incremental).
3. **Error notice**: if any errors occurred, guide the user to check `error.log`.
4. **Next-step suggestion**: note that the exploration result can be passed to downstream migration tools.

> Exploration results are based on a Metastore metadata snapshot; actual storage sizes may differ from the runtime state. Cross-verify critical data.
