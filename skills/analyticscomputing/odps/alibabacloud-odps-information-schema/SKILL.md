---
name: alibabacloud-odps-information-schema
description: "Query MaxCompute (ODPS) Information Schema metadata views. Tenant-level (SYSTEM_CATALOG.INFORMATION_SCHEMA.*, recommended) or project-level (Information_Schema.*, deprecated). NL→SQL for IS views: tables, columns, partitions, tasks_history, tunnels_history, table_privileges, users, user_roles, quota_usage, etc. NOT for: DDL/DML, listing tables via MCP, running ad-hoc SQL, general MaxCompute questions."
license: Apache-2.0
compatibility: "Requires MaxCompute tenant-level Information Schema access. Execution channels: MCP preferred (maxcompute-catalog MCP server >= 0.1.0), odpscmd >= 0.35.0 as fallback."
metadata:
  domain: aiops
  owner: MaxCompute
  contact: jiexian.hc@alibaba-inc.com, zhipeng.gzp@alibaba-inc.com
  version: 27
  when_to_use: "User asks about metadata analysis using Information Schema views — e.g. table storage stats, query history, permission audit, cost tracking, governance diagnostics, zombie tables, who has access to table X, CU consumption trend, failed tasks analysis, table access patterns, tunnel audit. Do NOT use for: show me my tables (use list_tables), create a table (DDL), run this SQL (execution), general ODPS questions without IS context."
---

# ODPS Information Schema

**This skill is for Information Schema (IS) metadata queries ONLY.** If the user's question is about DDL/DML, listing tables, or general MaxCompute usage (not IS views), do NOT use this skill — use MCP tools (list_tables, get_table_schema) or odpscmd instead.

Query MaxCompute metadata through INFORMATION_SCHEMA views for storage, cost, permission, task, and governance analysis.

## Prerequisites <a name="prerequisites"></a>

> **MANDATORY: Every IS query MUST set namespace flag.** Without it, ALL queries fail with "Table not found".
> - **MCP**: `hints={"odps.namespace.schema":"true"}` in `execute_sql`
> - **odpscmd**: `SET odps.namespace.schema=true;` before each query
> - No exceptions. Applies to ALL `SYSTEM_CATALOG.INFORMATION_SCHEMA.*` queries.

> IS views require tenant-level permission. If you get access errors, the user needs tenant-level role — see [references/ram-policies.md](references/ram-policies.md) for Policy template.

> **Data freshness**: History views (TASKS_HISTORY, TUNNELS_HISTORY) have ~5 min delay, realtime views ~3 hours. For yesterday's data, query after 06:00 to ensure completeness.

> **Tenant-level vs Project-level IS**: MaxCompute has two IS levels. **Tenant-level** (`SYSTEM_CATALOG.INFORMATION_SCHEMA.*`) is the default — it covers all projects under the same metadata center and is **recommended**. **Project-level** (`Information_Schema.*`) is per-project only, requires `install package Information_Schema.systables`, and is **being deprecated** (since 2024-03 new projects no longer auto-install). Key differences: (1) project-level has fewer views (no CATALOGS, VOLUMES, FOREIGN_SERVERS, SCHEMAS, PARTITION_ACCESS_INFO, TABLE_ACCESS_INFO, QUOTA_USAGE; has SCHEMA_PRIVILEGES which tenant lacks); (2) project-level TASKS_HISTORY has `task_schema` while tenant-level does NOT; (3) project-level `table_catalog` is always `odps` while tenant-level is the actual project name. See [Project-level IS Adaptation](#project-level-adaptation) for transformation rules.

For MCP configuration, see [references/mcp-tools-reference.md](references/mcp-tools-reference.md).

## Execution Channels <a name="channels"></a>

**MCP preferred** when `mcp__maxcompute-catalog__*` tools are available. Fall back to odpscmd on connection/auth errors.

| Channel | Use For | Key Detail |
|---|---|---|
| **MCP (tenant-level)** | DQL, metadata, search | `execute_sql` + `hints={"odps.namespace.schema":"true"}`; sync limit 1000 rows; `cost_sql` supports IS views (verified 2026-04) |
| **MCP (project-level)** | DQL, metadata, search | `execute_sql` + `hints={}` (no namespace flag); view prefix: `Information_Schema.*` |
| **odpscmd (tenant-level)** | DDL/DML, large results, MCP unavailable | `SET odps.namespace.schema=true;` prefix required |
| **odpscmd (project-level)** | DDL/DML, large results, MCP unavailable | No namespace flag; view prefix: `Information_Schema.*` |

See [references/mcp-tools-reference.md](references/mcp-tools-reference.md) for 15 MCP tools with routing guide.

## Important Rules <a name="rules"></a>

1. **Always set namespace flag** — every tenant-level IS query, no exceptions. Project-level IS queries do NOT need this flag
2. **Filter by `ds`** — TASKS_HISTORY / TUNNELS_HISTORY are partitioned; always add `ds` filter to avoid full scan
3. **No SELECT \*** — use explicit column names
4. **Cross-metadata-center NOT supported** — each region is independent
5. **last_access_time is NULL for partitioned tables** — use `COALESCE(last_access_time, last_modified_time)` or check PARTITIONS view. Also: not collected for ALGO jobs or Hologres direct reads; up to 24h delay from actual access.
6. **status values** — TASKS_HISTORY: `Terminated` (normal), `Failed`, `Cancelled` (rare). Never count Terminated as failure.
7. **operate_type values** — TUNNELS_HISTORY: `UPLOADLOG`, `DOWNLOADLOG`, `DOWNLOADINSTANCELOG`, `STORAGEAPIREAD`, `STORAGEAPIWRITE`
8. **Views without time fields** — COLUMNS has no time column. TABLE_PRIVILEGES/COLUMN_PRIVILEGES have no time column, only `expired`. These views support static snapshot only, not time-series.
9. **cost_cpu / cost_mem are DOUBLE** — unit: 100×core×seconds / MB×seconds. Convert to CU-hours: `cost_cpu / 100 / 3600`
10. **Duration** — use `DATEDIFF(end_time, start_time, 'ss')` (seconds). No `duration_ms` column exists.
11. **Non-existent fields trap** — see Critical Column Reference below
12. **JOIN IS views requires 3-field key** — when joining any two IS views, the ON condition MUST include `table_catalog`, `table_schema`, AND `table_name`. Missing any one causes incorrect results in multi-catalog environments

## Project-level IS Adaptation <a name="project-level-adaptation"></a>

All SQL templates in this skill default to **tenant-level** syntax (`SYSTEM_CATALOG.INFORMATION_SCHEMA.*` + namespace flag). If the environment only supports **project-level** IS, apply these mechanical transformations to every generated SQL:

| Transform | Tenant-level (default) | Project-level |
|-----------|----------------------|---------------|
| View prefix | `SYSTEM_CATALOG.INFORMATION_SCHEMA.` | `Information_Schema.` |
| Namespace flag (MCP) | `hints={"odps.namespace.schema":"true"}` | `hints={}` (remove flag) |
| Namespace flag (odpscmd) | `SET odps.namespace.schema=true;` | Remove entirely |
| Scope | All projects in metadata center | Current project only |
| Views unavailable | — | CATALOGS, VOLUMES, FOREIGN_SERVERS, SCHEMAS, PARTITION_ACCESS_INFO, TABLE_ACCESS_INFO, QUOTA_USAGE |
| View exclusive to this level | — | SCHEMA_PRIVILEGES |
| TASKS_HISTORY extra column | — | `task_schema` (project name; tenant-level lacks this) |
| `table_catalog` value | Actual project name | Fixed `odps` |

**Example transformation:**
```
-- Tenant-level (default):
SET odps.namespace.schema=true;
SELECT table_name, data_length FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES WHERE ...

-- Project-level (after transformation):
SELECT table_name, data_length FROM Information_Schema.tables WHERE ...
```

**When to switch**: If a tenant-level query fails with `Table not found` (and namespace flag is correctly set), or if the user explicitly says they only have project-level IS, apply the transformation rules above to all subsequent queries.

## Critical Column Name Reference <a name="column-reference"></a>

| Concept | Correct | Wrong |
|---|---|---|
| Table size | `data_length` | ~~size_bytes~~, ~~size~~ |
| Task instance | `inst_id` | ~~task_id~~ |
| Task submitter | `owner_name` | ~~task_owner~~ |
| Task project | `task_catalog` (tenant-level) | ~~project_name~~, ~~task_schema~~ (project-level IS only) |
| Task error | `result` | ~~error_message~~ |
| Task duration | `DATEDIFF(end_time, start_time, 'ss')` | ~~duration_ms~~ |
| Task status | `status` | ~~task_status~~ |
| Task input size | `input_bytes` | ~~scan_bytes~~, ~~processed_bytes~~ |
| Table comment | `table_comment` | ~~comment~~ |
| Column comment | `column_comment` | ~~comment~~ |
| Privilege grantee | `user_name`, `user_id` | ~~grantee~~ |
| Privilege time | `expired` | ~~grant_time~~ |
| Resource size | `size` | ~~size_bytes~~ |
| Tunnel session | `session_id` | ~~tunnel_id~~ |
| Tunnel data size | `data_size` | ~~size_bytes~~ |
| User identity | `identity_provider` | — |
| Timestamp type | `DATETIME` | ~~TIMESTAMP~~ |
| Table modified | `last_modified_time` | ~~last_ddl_time~~ |
| cost_cpu type | `DOUBLE` | ~~BIGINT~~ |

> For verified query examples using these columns, see [references/verified-queries.md](references/verified-queries.md).

## Routing Index <a name="routing"></a>

SKILL.md contains critical column names and namespace rules. Load sub-files only when needed:

- **If multiple rows match, load ALL matched files.** E.g., a non-English term causal query needs both terminology.md and playbooks+causal-templates.
- **If SKILL.md inline info (tables below) is sufficient, do NOT load extra files.**
- **NOT about IS views?** → This skill is not applicable. Use MCP tools (list_tables, get_table_schema, execute_sql) or odpscmd for DDL/DML/general queries.

| Query Type | When | Load Extra File |
|---|---|---|
| **NOT an IS query** | DDL/DML, list tables, run SQL, general ODPS | None — use MCP tools or odpscmd instead |
| **Single-view query** | One IS view, no JOIN | None — SKILL.md only |
| **Live monitoring** | TASKS / QUOTA_USAGE | None — SKILL.md only |
| **2+ IS view JOIN** | Combining views | [references/joins.md](references/joins.md) |
| **Named metric/template** | "comment coverage", "CU trend", "zombie table detection" | [references/verified-queries.md](references/verified-queries.md) + [references/metrics.md](references/metrics.md) |
| **Multi-step diagnosis** | "Why did CU spike?", root-cause analysis | [references/playbooks.md](references/playbooks.md) + [references/causal-templates.md](references/causal-templates.md) |
| **Non-English synonyms** | "cpu时间", "作业时长", "存储占用", or any CJK/localized terms | [references/terminology.md](references/terminology.md) (or use inline mapping below) |
| **Schema/field lookup** | "What columns does X have?" | [references/views-reference.md](references/views-reference.md) |
| **Access denied error** | Permission denied on IS view | [references/ram-policies.md](references/ram-policies.md) |
| **Troubleshooting** | Table not found, timeout, etc. | [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) |

### Anti-pattern: Do NOT load extra files for these

| User says | Looks like | Actually is | Load |
|---|---|---|---|
| "storage pressure, list top 20 tables" | Diagnostics | Single-view | SKILL.md only |
| "permission audit, who has SELECT on X" | Playbook | Single-view | SKILL.md only |
| "cost attribution by owner" | Causal | Single-view | SKILL.md only |

<!-- SYNC: derived from references/joins.md paths #1 #2 #3 #4 #5 #8 #10 -->
### Inline Join Conditions (for 2+ view JOINs)

When joining IS views, you MUST include `table_catalog`, `table_schema`, AND `table_name` in join conditions. Common join paths:

| Left | Right | Join Condition |
|---|---|---|
| TABLES | COLUMNS | `t.table_catalog = c.table_catalog AND t.table_schema = c.table_schema AND t.table_name = c.table_name` |
| TABLES | PARTITIONS | `t.table_catalog = p.table_catalog AND t.table_schema = p.table_schema AND t.table_name = p.table_name` |
| TABLES | TABLE_PRIVILEGES | `t.table_catalog = p.table_catalog AND t.table_schema = p.table_schema AND t.table_name = p.table_name` |
| TABLES | TABLE_ACCESS_INFO | `t.table_catalog = a.table_catalog AND t.table_schema = a.table_schema AND t.table_name = a.table_name` |
| TABLES | TABLE_LABELS | `t.table_catalog = l.table_catalog AND t.table_schema = l.table_schema AND t.table_name = l.table_name` |
| USERS | USER_ROLES | `u.user_id = ur.user_id` |
| COLUMNS | COLUMN_LABELS | `c.table_catalog = l.table_catalog AND c.table_schema = l.table_schema AND c.table_name = l.table_name AND c.column_name = l.column_name` |

For all 16 join paths, see [references/joins.md](references/joins.md). The 7 most common paths are inlined below.

<!-- SYNC: derived from references/terminology.md — metric terms: storage usage, task CPU consumption, task execution duration, CU-hours, queue wait; dimension terms: zombie tables; metric: task failure rate -->
### Inline Terminology Mapping (common non-English terms)

| Non-English term | English equivalent | Correct column/source | Common mistake |
|---|---|---|---|
| cpu时间 / CPU消耗 | CPU time / CPU consumption | `cost_cpu` (DOUBLE), ÷100÷3600 = CU·hour | ~~cpu_time~~ |
| 作业时长 / 任务耗时 | Task duration / task elapsed time | `DATEDIFF(end_time, start_time, 'ss')` | ~~duration_ms~~ |
| 存储占用 / 表大小 | Storage usage / table size | `data_length` (÷1073741824 = GB) | ~~size_bytes~~ |
| 僵尸表 | Zombie table | TABLES + TABLE_ACCESS_INFO | — |
| 排队时间 | Queue wait time | NOT available in IS views | — |
| CU时 / CU消耗 | CU-hours / CU consumption | `SUM(cost_cpu) / 100.0 / 3600` | — |
| 任务失败率 | Task failure rate | `status='Failed'` ratio in TASKS_HISTORY | — |

For all 59 terms, see [references/terminology.md](references/terminology.md).

## Error Recovery <a name="error-recovery"></a>

| Error Signal | Root Cause | Fix |
|---|---|---|
| `Table not found` on IS view | Missing namespace flag | Add `SET odps.namespace.schema=true;` / `hints={"odps.namespace.schema":"true"}`. Verify with [Q30 smoke test](references/verified-queries.md#q30-namespace-flag-verification) |
| `Access denied` / `Permission denied` on IS view | Missing tenant-level role | Verify access with `check_access(include_grants=true)`. User needs tenant-level role — load [references/ram-policies.md](references/ram-policies.md) for Policy template |
| `Table not found` on `SYSTEM_CATALOG.INFORMATION_SCHEMA.*` (namespace flag correctly set) | Environment only supports project-level IS | Apply [Project-level IS Adaptation](#project-level-adaptation) transformation rules to all subsequent queries: switch prefix to `Information_Schema.*`, remove namespace flag |
| `Information_Schema not found` / `Package not installed` | Project-level IS not installed in this project | User must run `install package Information_Schema.systables` as project owner or Super_Administrator. After install, query as `Information_Schema.view_name` (no namespace flag). Note: project-level IS is being deprecated — prefer tenant-level |
| `Object 'Information_Schema' not found` on new project | New projects (since 2024-03) don't auto-install project-level IS | Switch to tenant-level IS (`SYSTEM_CATALOG.INFORMATION_SCHEMA.*`) or manually install package |
| TASKS_HISTORY query slow/expensive | No `ds` filter | Add `WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -14, 'dd'), 'yyyymmdd')` |
| MCP returns exactly 1000 rows | Sync limit truncation | Re-run with `async=true`, or add tighter WHERE/LIMIT |
| `Column not found` | Used non-existent column | Check Critical Column Reference above — common: `size_bytes`→`data_length`, `task_status`→`status` |
| TUNNELS_HISTORY sync timeout (>30s) | Tunnel record volume much larger than TASKS_HISTORY | Use `async=true` + `get_instance`, or reduce ds to 1 day |
| Async timeout (>30s) | Large scan | Use `cost_sql` first; add `ds` filter; split query |
| IS view shows no recent data | ~5 min delay for history views | Query yesterday's data after 06:00 |
| odpscmd query hangs | Large result set or full-table scan | Use `odps_is_query.sh -t <seconds>` to set timeout (default 300s); add `ds` filter |
| Namespace flag set but still `Table not found` | Other causes (wrong project, typo, schema issue) | Load [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) for T1–T7 scenarios |

## Core Views <a name="core-views"></a>

| View | Purpose | Key Columns |
|---|---|---|
| `TABLES` | Table metadata | table_name, owner_name, data_length, table_type, lifecycle, last_modified_time |
| `COLUMNS` | Column metadata | column_name, data_type, column_comment, is_partition_key |
| `PARTITIONS` | Partition metadata | partition_name, data_length, create_time, last_modified_time |
| `TASKS` | Running jobs (live, seconds delay) | inst_id, task_name, owner_name, status, cpu_usage (core×100), mem_usage (MB) |
| `TASKS_HISTORY` | Query history | inst_id, task_name, owner_name, status, task_type, start_time, end_time, result, cost_cpu, input_bytes, ds |
| `TUNNELS_HISTORY` | Tunnel history | session_id, object_name, operate_type, data_size, owner_name, ds |
| `TABLE_PRIVILEGES` | Table permissions | table_name, user_name, privilege_type, expired |
| `TABLE_ACCESS_INFO` ⚠️ | Table access stats | table_name, access_count, access_bytes, last_access_time |
| `QUOTA_USAGE` | Subscription quota monitoring | name, cpu_elastic_quota_max, cpu_elastic_quota_used, mem_elastic_quota_max, mem_elastic_quota_used |
| `USERS` | Project users | user_name, user_id, identity_provider |
| `USER_ROLES` | User-role mapping | user_name, role_name, user_role_catalog |
| `CATALOGS` ⚠️ | Project list | catalog_name, status, owner_name, region |

For all 31 views with complete field definitions, see [references/views-reference.md](references/views-reference.md). Views marked ⚠️ are **tenant-level only** (not available in project-level IS).

## Additional Resources <a name="resources"></a>

- [references/views-reference.md](references/views-reference.md) — Complete field definitions for all 31 IS views
- [references/verified-queries.md](references/verified-queries.md) — 30 pre-validated SQL query templates (including smoke test)
- [references/entities.md](references/entities.md) — Entity-to-table mapping
- [references/metrics.md](references/metrics.md) — Metric definitions with SQL expressions
- [references/joins.md](references/joins.md) — Join paths between views
- [references/playbooks.md](references/playbooks.md) — 23 diagnostic scenario playbooks
- [references/causal-templates.md](references/causal-templates.md) — Root-cause analysis templates
- [references/terminology.md](references/terminology.md) — 59-term synonym dictionary for NL2SQL
- [references/ram-policies.md](references/ram-policies.md) — Tenant permission setup and Policy template
- [references/mcp-tools-reference.md](references/mcp-tools-reference.md) — 15 MCP tools with routing guide + MCP setup + installation
- [scripts/odps_is_query.sh](scripts/odps_is_query.sh) — CLI query tool (16 query types + custom, including smoke-test). Supports `-t <seconds>` for timeout (default 300s), `-d YYYYMMDD` for date, `-p` for project. Custom mode only allows SELECT (DDL/DML rejected).
- [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) — 7 error scenarios with fix templates (T1–T7)

## Official Documentation <a name="docs"></a>

- [MaxCompute Tenant-level Information Schema](https://help.aliyun.com/zh/maxcompute/user-guide/tenant-level-information-schema)
