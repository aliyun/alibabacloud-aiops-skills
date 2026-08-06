# Hive-to-Paimon Data Migration Tool - Overview

> Moved from the original README.md into references/, as an optional supplement to SKILL.md.
> Last Updated: 2026-05-14

Batch-migrate a Hive data warehouse to the Alibaba Cloud DLF Paimon lakehouse format, supporting full migration and incremental sync.

## Architecture Overview

```
                          Full migration (main.py)
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐  │
│  │  Step 1  │──▶│  Step 2  │──▶│  Step 3  │──▶│   Step 4   │  │
│  │ DDL conv │   │ ext-table│   │ Spark    │   │  rclone    │  │
│  │ Hive→    │   │ format-  │   │ create   │   │ HDFS→OSS   │  │
│  │ Paimon   │   │ table    │   │ tables   │   │  data sync │  │
│  └──────────┘   └──────────┘   └──────────┘   └─────┬──────┘  │
│                                                       │         │
│                                         ┌─────────────▼──────┐  │
│                                         │      Step 5        │  │
│                                         │ INSERT OVERWRITE   │  │
│                                         │ ext → internal load│  │
│                                         └────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                         Incremental migration (incremental_migrate.py)
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: DDL exec  ──▶  Phase 2: rclone sync  ──▶  Phase 3: INSERT │
└─────────────────────────────────────────────────────────────────┘
```

## Core Capabilities

| Capability | Description |
|------------|-------------|
| **Automatic DDL conversion** | Hive DDL → Paimon DDL, with automatic partition-column merging and storage-format mapping |
| **Multi-format support** | Five storage formats: ORC, Parquet, JSON, CSV, TextFile |
| **TextFile special handling** | Auto-generates `split()` + `CAST` INSERT statements, handling `\u0001` delimiters and `\N` nulls |
| **format-table external tables** | Reads raw Hive data files on OSS via Paimon format-table |
| **rclone parallel sync** | Multi-table parallel HDFS→OSS sync with background run, bandwidth limit, and resume-on-break |
| **DLS direct-read mode** | Copy-free for OSS-HDFS (DLS); external table points directly at the DLS source path |
| **Resumable runs** | Resume from any step, skipping completed steps |
| **Incremental migration** | Works with migration-lhm-inspect-hive-metastore incremental exploration to sync only changed tables |

## Two Data Paths

### Standard mode (HDFS → rclone → OSS)

```bash
python main.py -e /path/to/explore/ -c config.ini
```

### Direct-read mode (DLS copy-free)

```bash
python main.py -e /path/to/explore/ -c config.ini --direct-read
```

## Input Sources

| Source | Command | Prerequisites |
|--------|---------|---------------|
| migration-lhm-inspect-hive-metastore full-explore output | `-e <explore_dir>` | `summary_report.csv` + `ddl_files/` |
| Specify databases | `-d ads,dwd,dws` | Hive Metastore DB connection + hive CLI |
| Specify tables | `-t db.t1,db.t2` | Same as above |

## File Structure

```
migration-lhm-migrate-hive-to-paimon/
├── SKILL.md                         # main technical doc
├── config.ini                       # config file template
├── references/                      # detailed references
│   ├── overview.md                  # this file
│   ├── configuration.md             # full config.ini field reference
│   ├── agent-rules.md               # agent execution rules
│   ├── troubleshooting.md           # troubleshooting
│   └── serde-mapping.md             # SERDE → DLF FORMAT mapping
└── scripts/
    ├── main.py                      # full-migration orchestrator
    ├── step1_generate_paimon_ddl.py
    ├── step2_generate_ext_ddl.py
    ├── step3_execute_ddl.py
    ├── step4_rclone_sync.py
    ├── step5_insert_overwrite.py
    ├── incremental_migrate.py       # standalone incremental script
    ├── ddl_converter/               # standalone DDL converter
    └── common.py
```

## Collaboration with migration-lhm-inspect-hive-metastore

1. **inspect full explore** → outputs `summary_report.csv` + `ddl_files/`.
2. **migrate full migration** → consumes explore output, completes full migration.
3. **inspect incremental explore** → outputs `paimon_sync.sql` + `sync_commands.sh`.
4. **migrate incremental migration** → consumes incremental explore output, completes incremental sync.
