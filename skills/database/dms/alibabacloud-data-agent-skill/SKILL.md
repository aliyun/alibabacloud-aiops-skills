---
name: alibabacloud-data-agent-skill
description: |
  Invoke Alibaba Cloud Apsara Data Agent for Analytics via CLI to perform natural language-driven data analysis on enterprise databases.
  Data Agent for Analytics is an intelligent data analysis agent developed by Alibaba Cloud Database team for enterprise users. It automatically completes requirement analysis, data understanding, analysis insights, and report generation based on natural language descriptions.
  This tool supports: discovering data resources (instances/databases/tables) managed in DMS, initiating query or deep analysis sessions, real-time progress tracking, and retrieving analysis conclusions and generated reports.
  Use this Skill when users need to query databases, analyze data trends, generate data reports, ask questions in natural language, or mention "Data Agent", "data analysis", "database query", "SQL analysis", "data insights".
compatibility: |
  Requires valid Alibaba Cloud credentials (default credential chain or API_KEY);
  Requires dependencies in requirements.txt to be installed;
  Data sources must be managed in Alibaba Cloud Apsara Database or DMS.
domain: AIOps
---
metadata:
  author: DataAgent Team
  version: "1.7.2"
---

# Changelog
- **v1.7.2**: Use Alibaba Cloud default credential chain instead of explicit AK/SK, add User-Agent header, fix RAM policy wildcard issues
- **v1.7.1**: Fix CLI `ls` command API response parsing (support case-insensitive field names), optimize SKILL documentation structure, separate ANALYSIS mode specification document
- **v1.7.0**: API_KEY authentication support, native async execution mode, session isolation, enhanced attach mode, optimized log output

---

---

# Installation


## Configure Credentials

This Skill uses Alibaba Cloud default credential chain (recommended) or API_KEY authentication.

### Option 1: Default Credential Chain (Recommended)

The Skill uses Alibaba Cloud SDK's default credential chain to automatically obtain credentials, supporting environment variables, configuration files, instance roles, etc.

See [Alibaba Cloud Credential Chain Documentation](https://help.aliyun.com/document_detail/378659.html)

### Option 2: API_KEY Authentication (File Analysis Only)

```bash
export DATA_AGENT_API_KEY=your-api-key
export DATA_AGENT_REGION=cn-hangzhou
```

Get API_KEY: [Data Agent Console](https://agent.dms.aliyun.com/cn-hangzhou/api-key)

### Permission Requirements

RAM users need `AliyunDMSFullAccess` or `AliyunDMSDataAgentFullAccess` permissions.
See [RAM-POLICIES.md](references/RAM-POLICIES.md) for detailed permission information.

## Debug Mode

```bash
DATA_AGENT_DEBUG_API=1 python3 scripts/data_agent_cli.py file example.csv -q "analyze"
```

## 💡 Getting Started Tips

- Use the built-in demo database `internal_data_employees` (DataAgent's built-in test database containing employee, department, and salary data) for first-time experience
- Or use local file `assets/example_game_data.csv` for file analysis experience


# Data Agent CLI — Unified Command-Line Data Analysis Tool

## Overview

`scripts/data_agent_cli.py` helps users complete the full workflow from **discover data → initiate analysis → track progress → get results**.

### Core Concepts

> **⚠️ Key Prerequisite**: Data Agent can only analyze databases that have been **imported into Data Agent Data Center**.
>
> - **Data Center**: Data Agent's data center, only databases here can be analyzed
> - **DMS**: Alibaba Cloud Data Management Service, stores metadata of all databases
> - **Relationship**: Databases registered in DMS ≠ Databases in Data Center
>
> **Usage Flow**:
> 1. First use `ls` to check if the target database exists in Data Center
> 2. If **not found**, use `dms` subcommand to search for database info, then use `import` subcommand to import it
> 3. After successful import, you can use `db` subcommand for analysis

---

## Analysis Modes

- **ASK_DATA** (default): Synchronous execution, sub-second response, suitable for quick Q&A
- **ANALYSIS**: Deep analysis, takes 5-40 minutes, requires spawning a sub-agent for async execution or using --async-run parameter

> See [ANALYSIS_MODE.md](references/ANALYSIS_MODE.md) for details

---

## Session Reuse

Use `db`/`file` to create a session for initial analysis, then use `attach --session-id <ID>` to reuse the session for follow-up questions.

> See [COMMANDS.md](references/COMMANDS.md) and [WORKFLOWS.md](references/WORKFLOWS.md) for details

---

## Quick Start

```bash
# 1. List available databases
python3 scripts/data_agent_cli.py ls

# 2. Query analysis (synchronous response)
python3 scripts/data_agent_cli.py db \
    --dms-instance-id <ID> --dms-db-id <ID> \
    --instance-name <NAME> --db-name <DB> \
    --tables "employees,departments" -q "Which department has the highest average salary"

# 3. Follow-up question (reuse session)
python3 scripts/data_agent_cli.py attach --session-id <ID> -q "Break down by month"
```

> 📖 See [WORKFLOWS.md](references/WORKFLOWS.md) and [COMMANDS.md](references/COMMANDS.md) for complete workflows, command reference, and best practices

---

## Project Structure

```
                          # Skill root directory
├── SKILL.md              # This document
├── scripts/              # Source code
│   ├── data_agent/       # SDK module
│   ├── cli/              # CLI module
│   ├── data_agent_cli.py # CLI entry point
│   └── requirements.txt  # Dependencies
├── sessions/             # Session data
└── references/           # Reference documents
```
