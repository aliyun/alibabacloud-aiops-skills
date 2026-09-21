# sql-conversion-skill-release

The external release version of the SQL dialect conversion skill. It provides two modes: single-SQL conversion and batch directory conversion. All conversions are strictly executed through the `sql-atomic-conversion` sub-skill.

## 🔴 Self-Containment Statement

**This repository is self-contained — it does not depend on any file, configuration, or tool outside this directory.**

- All utility scripts are located in `${SKILL_HOME}/scripts/`
- The atomic conversion skill instructions are located in `${SKILL_HOME}/skills/sql-atomic-conversion/SKILL.md`
- Reference documents are located in `${SKILL_HOME}/docs/` and `${SKILL_HOME}/sql-dialects/`

When using this skill, **there is no need to reference or depend on any external project files**. Copy this directory to any location and it will run independently.

## Directory Structure

```
${SKILL_HOME}/
├── SKILL.md                              # Main dispatch skill (entry point)
├── README.md                             # This file
├── scripts/                              # Utility scripts
│   ├── check_env.py                     # Environment pre-check (verifies DryRun configuration readiness)
│   ├── lookup_rules.py                   # Browse/query conversion rules (fetches data via MCP Tool internally)
│   ├── dryrun.py                         # DryRun syntax validation
│   ├── get_table_schema.py               # Query the table schema of the target side
│   ├── client.py                         # Low-level connection module (depended on by the scripts above)
│   ├── config_template.json              # Configuration template
├── skills/
│   └── sql-atomic-conversion/
│       └── SKILL.md                      # Atomic conversion sub-skill
├── docs/
│   ├── error-patterns.md                 # DryRun error pattern reference
│   └── dev-pitfalls.md                   # Development pitfalls record
└── sql-dialects/
    └── dialects/                         # Syntax reference documents for each dialect
```

## Quick Start

### 1. Configure the Database Connection

DryRun validation requires connection configuration for the target database. Choose either of the two methods:

**Method A: Configuration file**

All configuration is managed through a single unified JSON file: `~/.lhm/credentials.json`.

This file contains configuration for all LHM skills, including:
- Alibaba Cloud credentials (AK/SK)
- LHM service configuration (endpoint, region_id)
- SQL conversion database connection settings (maxcompute, hologres, clickhouse, etc.)
- Schedule migration data source names

```bash
# Create the config directory
mkdir -p ~/.lhm

# Copy the unified config template
cp ${SKILL_HOME}/scripts/config_template.json ~/.lhm/credentials.json

# Edit ~/.lhm/credentials.json and fill in the real credentials
```

**Method B: Environment variables**

Set environment variables according to the target side; see the environment variable reference table in `../../SKILL.md` for details.

### 2. Install Python Dependencies

Install the corresponding SDK according to the target side you use:

```bash
# Core dependencies (rule browsing does not require extra installation)
# Note: JSON is used for configuration, no pyyaml required

# Install per target side as needed
pip install pyodps          # MaxCompute
pip install psycopg2-binary # Hologres / Redshift (Postgres protocol)
pip install prestodb        # Presto / Trino
pip install clickhouse-connect  # ClickHouse
pip install pyhive          # Spark (Kyuubi)
pip install pymysql         # MySQL / StarRocks
pip install pymssql         # SQL Server
pip install google-cloud-bigquery  # BigQuery
pip install boto3           # Redshift (Data API)
```

### 3. Use the Skill

Load this directory as a skill into your AI platform (Claude Code, Qoder, or any other platform that supports the SKILL.md specification), then:

- **Single conversion**: provide the SQL text + source dialect + target dialect directly
- **Batch conversion**: provide a directory path containing .sql files + source dialect + target dialect

See `../../SKILL.md` for detailed usage.

## Core Design

### Single Conversion Entry Point

All SQL dialect conversions **must** be executed through the six-step process defined in `${SKILL_HOME}/skills/sql-atomic-conversion/SKILL.md`. Bypassing this process to convert by any other means is strictly prohibited.

### Platform Agnostic

This skill does not presuppose a runtime platform. How subagents are created is determined by the native mechanism of the current platform; this skill only describes the task content that the subagents should execute.

### Tool Dependency Graph

```
check_env.py         → client.py (_load_json)
    │
lookup_rules.py     (fetches rule data via MCP Tool through a1 mcp call-tool)
    │
dryrun.py           → client.py
    │
get_table_schema.py → client.py
    │
client.py           (core dependency, conditionally imports each target-side SDK)
    └── local_config.json (optional, credential configuration)
```

## License

Internal use.
