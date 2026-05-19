# MCP Tools Reference

> Related: [SKILL.md](../SKILL.md)

Complete reference for maxcompute-catalog MCP tools used by odps_is skill. This document supplements SKILL.md with detailed MCP execution guidance.

## MCP Availability Detection

If `mcp__maxcompute-catalog__*` tools are available in your tool list, use MCP as the primary channel. If an MCP tool call returns a connection error or auth failure, fall back to odpscmd for all subsequent queries.

Degradation rules:
1. Connection/auth error → mark MCP unavailable, use odpscmd for all subsequent queries
2. SQL execution error (syntax, permission) → do NOT degrade, this is a business-level error
3. Result truncation (exactly 1000 rows) → warn user, suggest odpscmd for complete data

## Tool Overview

| Tool Name | Category | Purpose | IS Query Applicable |
|---|---|---|---|
| list_projects | Metadata Exploration | List accessible projects | No (use CATALOGS SQL) |
| get_project | Metadata Exploration | Project details, schemaEnabled detection | No (use CATALOGS SQL) |
| list_schemas | Metadata Exploration | List schemas under project | No (use SCHEMAS SQL) |
| get_schema | Metadata Exploration | Schema details | No |
| list_tables | Metadata Exploration | List tables/views, namingModel | Yes (for table listing) |
| get_table_schema | Metadata Exploration | Column details, sqlTableRef | Yes (for column info) |
| get_partition_info | Metadata Exploration | Partition list with sizes | Yes (for partition info) |
| execute_sql | SQL Execution | Run DQL queries | Yes (primary IS query path) |
| cost_sql | SQL Execution | Estimate query cost | Yes (supports IS views, verified 2026-04) |
| get_instance_status | SQL Execution | Poll async job status | Yes (for async queries) |
| get_instance | SQL Execution | Get async query results | Yes (for async queries) |
| search_meta_data | Search | Cross-project table search | No (for table discovery) |
| check_access | Security | Verify identity and permissions | No (for auth check) |
| create_table | Table Design | Create tables via SDK API | No |
| insert_values | Table Design | Insert data rows | No |

## Metadata Exploration

### list_projects / get_project

- `list_projects`: Lists all accessible project IDs (paginated via `pageSize` + `token`)
- `get_project`: Returns project details including `schemaEnabled` (critical for determining 2-level vs 3-level naming model)
- **Fallback**: `SELECT * FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.CATALOGS`

### list_schemas / get_schema

- `list_schemas`: Lists schemas under a project (returns synthetic "default" for 2-level projects)
- `get_schema`: Returns schema details and metadata
- **Fallback**: `SELECT * FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.SCHEMAS`

### list_tables

- Lists tables/views in a project
- Returns `namingModel` ("3-level" or "2-level") to guide SQL table references
- Supports `filter` parameter for table name prefix matching
- **Fallback**: odpscmd SQL

### get_table_schema

- Returns column names, types, partition keys
- **Critical**: Returns `sqlTableRef` (exact table reference for SQL) and `sqlExample`
- Always call this before writing SQL to ensure correct table reference format
- **Fallback**: odpscmd SQL

### get_partition_info

- Lists partitions with data size, create_time, last_modified_time
- Paginated (`pageSize` + `token`)
- **Fallback**: odpscmd SQL

## SQL Execution

### execute_sql

Execute SQL queries. Key parameters:

| Parameter | Description | Default |
|---|---|---|
| `sql` | The SQL statement | (required) |
| `project` | Billing project (for IS queries, use defaultProject from config) | defaultProject |
| `hints` | Runtime parameters merged with default `{"odps.sql.submit.mode":"script"}` | {} |
| `async` | Async execution mode | true |
| `maxCU` | Resource limit (cost check before execution) | - |
| `timeout` | Sync mode timeout in seconds | 30 |

**Namespace Flag (verified)**:
Two working methods (choose one):
1. Via hints: `hints={"odps.namespace.schema":"true"}` (recommended)
2. Via SQL prefix: `SET odps.namespace.schema=true; SELECT ...` (also works, MCP uses script mode)

**DQL Whitelist**: SELECT, WITH, SHOW, DESC, DESCRIBE, EXPLAIN, VALUES, SET

**DML Blacklist**: INSERT, UPDATE, DELETE, MERGE, UPSERT, TRUNCATE, CREATE, DROP, ALTER, RENAME, GRANT, REVOKE, CALL, EXEC, EXECUTE, LOAD, UNLOAD, COPY, MSCK, REPAIR

**Result Format**:
- Sync mode (open_reader path): `{"success":true, "columns":[...], "data":[...], "rowCount":N}` — max 1000 rows
- Sync mode (no open_reader): `{"success":true, "data":["line1","line2"], "rawOutput":"...", "rowCount":N}` — for SHOW/DESC
- 1000-row truncation: if rowCount === 1000, warn user that results may be incomplete

### cost_sql

- Estimates CU cost, input bytes, complexity without executing
- **Supports both user tables and IS views** (verified 2026-04): Returns real estimates including `estimatedCU`, `inputBytes`, `complexity`, `udfCount`
- Recommended before executing multi-day TASKS_HISTORY or TUNNELS_HISTORY queries to avoid unexpected costs

### get_instance_status

- Poll async job: status, CU usage, progress, logView URL
- Returns: `instanceId`, `status` (RUNNING/TERMINATED/FAILED), `isTerminated`, `isSuccessful`

### get_instance

- Retrieve completed async query results
- **No row limit** (unlike sync execute_sql)
- **Result format varies**:
  - Has open_reader → structured JSON: `{"columns":[...], "data":[...]}`
  - No open_reader → CSV string: `"col1","col2"\n"val1","val2"`
- Agent should handle both formats

## Async Execution Pattern

**When to use async=true** (meet ANY condition):
1. Query involves TASKS_HISTORY/TUNNELS_HISTORY with `ds` range >= 7 days
2. Expected result rows > 500
3. Multi-table JOIN involving large tables (TABLES/PARTITIONS full scan)
4. Sync mode timeout (instanceId returned after timeout)

**Pattern**:
1. Submit: `execute_sql(async=true, hints={"odps.namespace.schema":"true"})` → get `instanceId`
2. Poll: `get_instance_status(instanceId)` → check `isTerminated`
3. Retrieve: `get_instance(instanceId)` → get results

## Search

### search_meta_data

- Cross-project search for tables/resources/schemas
- **Requires namespace_id** configuration (config.json or `MAXCOMPUTE_NAMESPACE_ID` env var)
- Query syntax: `name:foo,type=TABLE` or `description:bar,type=TABLE,project=proj`
- Type is mandatory: TABLE, RESOURCE, or SCHEMA
- **Fallback when unavailable**: SQL LIKE query on IS views

## Security

### check_access

- Returns identity info (account type, masked AK, default project)
- Optional: `include_grants=true` to run SHOW GRANTS
- Use to verify MCP connection and permissions before complex operations

## Table Design

### create_table

- Creates tables using pyodps SDK `compute.create_table()` (NOT execute_sql)
- Supports `columns`, `partitionColumns`, `lifecycle`, `comment`
- **Fallback**: odpscmd DDL

### insert_values

- Inserts rows via `compute.run_sql()` with SQL injection protection
- Backtick-escaped identifiers, quoted values
- Supports partitioned tables (groups by partition key)
- **Fallback**: odpscmd DML

## IS Query Patterns via MCP

### Pattern 1: Simple IS Query (sync)

```
execute_sql(
  sql="SELECT table_name, data_length FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES LIMIT 20",
  hints={"odps.namespace.schema":"true"},
  async=false
)
```

### Pattern 2: Historical IS Query (async)

```
execute_sql(
  sql="SELECT ds, COUNT(*) AS task_count FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd') GROUP BY ds ORDER BY ds DESC",
  hints={"odps.namespace.schema":"true"},
  async=true
)
→ get_instance_status(instanceId) until isTerminated
→ get_instance(instanceId)
```

### Pattern 3: Metadata First, Then SQL

```
1. list_tables(filter="my_table") → confirm table exists
2. get_table_schema(table="my_table") → get sqlTableRef
3. execute_sql(sql="SELECT ... FROM <sqlTableRef> ...", hints={"odps.namespace.schema":"true"})
```

## Routing Decision Matrix

| Intent Category | NL Trigger Examples | MCP Tool | SQL Method | Fallback |
|---|---|---|---|---|
| List projects | "有哪些项目"、"project列表" | list_projects | - | IS SQL: SELECT * FROM CATALOGS |
| Project details | "项目配置"、"schemaEnabled" | get_project | - | IS SQL: SELECT * FROM CATALOGS WHERE ... |
| List schemas | "有哪些schema"、"数据库列表" | list_schemas | - | IS SQL: SELECT * FROM SCHEMAS |
| List tables | "有哪些表"、"表列表"、"xxx开头的表" | list_tables | - | odpscmd SQL |
| Table schema | "表结构"、"有哪些列"、"字段类型" | get_table_schema | - | odpscmd SQL |
| Partition info | "分区列表"、"有多少分区" | get_partition_info | - | odpscmd SQL |
| Search tables | "搜索表"、"找表"、"哪个项目有xxx表" | search_meta_data | - | IS SQL: LIKE query |
| Permission check | "我有什么权限"、"SHOW GRANTS" | check_access | - | odpscmd: SHOW GRANTS |
| Create table | "建表"、"创建表" | create_table | - | odpscmd DDL |
| Insert data | "插入数据"、"INSERT" | insert_values | - | odpscmd DML |
| IS metadata query | "存储最大的表"、"注释覆盖率"、"权限分布" | - | MCP execute_sql | odpscmd |
| Large result set (>500 rows) | "列出所有权限"、"全量用户列表" | - | MCP async or odpscmd | odpscmd |
| Complex computation | "P99时长"、"多表JOIN分析" | - | MCP execute_sql | odpscmd |
| DDL/DML | "ALTER TABLE"、"DROP"、"UPDATE" | - | odpscmd | - |
| SHOW/DESC | "SHOW TABLES"、"DESC table" | - | MCP execute_sql | odpscmd |
| Cost estimation (user tables & IS views) | "查询费用预估"、"这个SQL多少钱" | cost_sql | - | - |

## MCP Setup

1. Install maxcompute-catalog-mcp Python package
2. Create config file (e.g., `config.json`):

```json
{
  "maxcompute": {
    "catalogapi_endpoint": "catalogapi.cn-hangzhou.maxcompute.aliyun.com",
    "maxcompute_endpoint": "http://service.odps.aliyun.com/api",
    "accessKeyId": "YOUR_AK",
    "accessKeySecret": "YOUR_SK",
    "defaultProject": "YOUR_PROJECT",
    "namespaceId": "YOUR_NAMESPACE_ID"
  }
}
```

> **Security warning:** Never commit real credentials to source control. Use environment variables or a secrets manager. Add `config.json` to `.gitignore`.

**Important**: `catalogapi_endpoint` must NOT include `https://` prefix.

3. Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "maxcompute-catalog": {
      "command": "/path/to/python3",
      "args": ["-m", "maxcompute_catalog_mcp", "--config", "/path/to/config.json"]
    }
  }
}
```

### Configuration Keys

| Key | Required | Description |
|---|---|---|
| `catalogapi_endpoint` | Yes | Catalog API endpoint (domain only, no https://) |
| `maxcompute_endpoint` | Yes | MaxCompute service endpoint |
| `accessKeyId` | Yes | Alibaba Cloud AccessKey ID |
| `accessKeySecret` | Yes | Alibaba Cloud AccessKey Secret |
| `defaultProject` | Yes | Default project for SQL execution and billing |
| `namespaceId` | For search | Namespace ID for search_meta_data (also supports env var `MAXCOMPUTE_NAMESPACE_ID`) |

### Verification

After configuration, verify MCP works:
1. `check_access` → Should return identity info
2. `list_tables` → Should return table list with namingModel
3. `execute_sql` with hints={"odps.namespace.schema":"true"} → Should return IS query results

## Installation

### QoderWork Skills Directory

```bash
cp -r odps_is ~/.qoderwork/skills/
```

Or place `odps_is` in your project's `skills/` directory.

### odpscmd Configuration

Edit `scripts/odps_is_query.sh` line 5 to set `ODPS_CMD`, or use environment variable:

```bash
export ODPS_CMD="/path/to/your/odpscmd"
```

### CLI Usage

```bash
ODPS_CMD=/path/to/odpscmd ./scripts/odps_is_query.sh top-storage
ODPS_CMD=/path/to/odpscmd ./scripts/odps_is_query.sh failed-tasks -d 20240101
ODPS_CMD=/path/to/odpscmd ./scripts/odps_is_query.sh custom 'SELECT ...'
```

Supported types: tables, top-storage, columns, partitions, failed-tasks, cu-hours, cost-by-owner, cost-by-type, quota-usage, permissions, permission-audit, user-roles, comment-coverage, tunnel-daily, zombie-tables, smoke-test, custom.

## MCP vs odpscmd Feature Matrix

| Feature | MCP | odpscmd |
|---|---|---|
| IS metadata query | execute_sql + hints | SET flag + SQL |
| Table listing | list_tables (structured) | SQL query |
| Table schema | get_table_schema (with sqlTableRef) | DESC command |
| Partition info | get_partition_info | SQL query |
| Cross-project search | search_meta_data | Not available |
| Cost estimation | cost_sql (user tables & IS views) | Not available |
| DDL/DML | create_table/insert_values (limited) | Full support |
| Result format | JSON (sync) or JSON/CSV (async) | Plain text |
| Result limit | 1000 rows (sync), unlimited (async) | Unlimited |
| Async execution | Supported | Not supported |
