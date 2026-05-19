---
name: alibabacloud-odps-sql-generation
description: "Provides MaxCompute SQL intelligent generation capabilities for AI agents, covering text2sql conversion principles, dialect syntax differences (DQL/DDL/DML), common query pattern templates (Top N, PIVOT, window functions, etc.), and ODPS error code diagnostics. Use when generating, debugging, or migrating MaxCompute / ODPS SQL."
license: Apache-2.0
metadata:
  domain: coding
  owner: MaxCompute
  contact: jiexian.hc@alibaba-inc.com, zhipeng.gzp@alibaba-inc.com
  version: 1.0.0
---

# MaxCompute SQL Engine Syntax Skill

Provides MaxCompute SQL engine syntax guidance for text2sql scenarios. MaxCompute is based on Hive SQL extensions and has significant differences from ANSI standard SQL.

## Usage

Load corresponding reference files based on question type (can be combined). The `load` column indicates relative loading weight (heavy ≈ large, medium ≈ moderate), for budget estimation, not exact token counts. Each file's opening paragraph describes its own scope.

| Trigger condition | File | load |
|---|---|---|
| NL→SELECT generation / text2sql (determine intent, granularity, table-column mapping, output format first) | `references/text2sql_principles.md` | light |
| Generate MaxCompute SELECT queries (dialect rules, DQL default must-read) | `references/maxcompute_select_guide.md` | heavy |
| Match query pattern keywords: Top N / top-N per group / year-over-year / month-over-month / consecutive N days / retention / row-to-column / column-to-row / PIVOT / UNPIVOT / array expansion / LATERAL VIEW / EXPLODE / JSON extraction / GET_JSON_OBJECT / cumulative / running total / Range Join / GROUPING SETS / CUBE / ROLLUP / pagination / paging | `references/sql_query_patterns.md` | medium |
| SQL execution failure requiring diagnosis and recovery (including `ODPS-0xxx` error codes)| `references/sql_common_errors.md` | medium |

> Relationship: `text2sql_principles.md` provides engine-independent NL→SELECT generation principles; `maxcompute_select_guide.md` is the **single authoritative source** for MaxCompute DQL dialect rules (unsupported syntax/functions/partitioning/types/SET parameters). `sql_query_patterns.md` provides **query template snippets** only, without duplicating rules.

## Out of Scope

The following scenarios exceed this skill's scope:

- **MaxCompute non-SQL interfaces**: Tunnel / MapReduce / Graph / PyODPS DataFrame API, SDK invocation methods
- **Console and permission management**: Quota requests, IAM / RAM roles, project owner operations — use Aliyun console or support tickets
- **Execution plan-level deep tuning**: Only lists common SET parameters and hints; does not analyze specific plan nodes / Fuxi DAG / data skew formation paths
- **Cluster-side / platform-side failures**: Worker crashes, resource scheduling failures, MetaStore transaction conflicts, storage layer read/write errors — these are support ticket issues, not SQL issues
