# Verified Queries Reference

> Related: [metrics.md](metrics.md), [views-reference.md](views-reference.md), [joins.md](joins.md), [SKILL.md](../SKILL.md)

## Query Index

**Storage** (Q1–Q4)
[Q1: Top 20 Tables by Storage](#q1-top-20-tables-by-storage) · [Q2: Storage Breakdown by Owner](#q2-storage-breakdown-by-owner) · [Q3: Zombie Tables (Not Accessed in 90 Days)](#q3-zombie-tables-not-accessed-in-90-days) · [Q4: Partition Explosion Risk](#q4-partition-explosion-risk)

**Cost** (Q5–Q8)
[Q5: Daily CU-Hour Trend](#q5-daily-cu-hour-trend) · [Q6: Cost by Task Owner](#q6-cost-by-task-owner) · [Q7: Cost by Task Type](#q7-cost-by-task-type) · [Q8: Top 20 Most Expensive Tasks](#q8-top-20-most-expensive-tasks)

**Failure** (Q9–Q11)
[Q9: Failed Tasks Yesterday](#q9-failed-tasks-yesterday) · [Q10: Daily Failure Rate](#q10-daily-failure-rate) · [Q11: Failure Breakdown by Type](#q11-failure-breakdown-by-type)

**Permission** (Q12–Q14)
[Q12: Permission Exposure](#q12-permission-exposure) · [Q13: Admin Role Users](#q13-admin-role-users) · [Q14: User-Role Matrix](#q14-user-role-matrix)

**Governance** (Q15–Q16)
[Q15: Table Comment Coverage](#q15-table-comment-coverage) · [Q16: Column Comment Coverage](#q16-column-comment-coverage)

**Tunnel** (Q17–Q18)
[Q17: Daily Tunnel Volume](#q17-daily-tunnel-volume) · [Q18: Top Tunnel Downloads](#q18-top-tunnel-downloads)

**Object Count** (Q19)
[Q19: Object Inventory](#q19-object-inventory)

**Performance** (Q20)
[Q20: Top 20 Slowest Tasks](#q20-top-20-slowest-tasks)

**Hot Table** (Q21–Q23)
[Q21: Top 20 Most Accessed Tables (Last 7 Days)](#q21-top-20-most-accessed-tables-last-7-days) · [Q22: Top Tables by Data Volume Read (Last 7 Days)](#q22-top-tables-by-data-volume-read-last-7-days) · [Q23: User Resource Consumption by Table](#q23-user-resource-consumption-by-table)

**Official Verified** (Q24–Q29)
[Q24: TOP Storage Tables with COALESCE](#q24-top-storage-tables-with-coalesce) · [Q25: Partition Explosion Risk (Simplified)](#q25-partition-explosion-risk-simplified) · [Q26: Daily Failure Trend](#q26-daily-failure-trend) · [Q27: CU-Hour by Project and Hour](#q27-cu-hour-by-project-and-hour) · [Q28: User Resource Consumption](#q28-user-resource-consumption) · [Q29: Project Configuration Audit](#q29-project-configuration-audit)

**Smoke Test** (Q30)
[Q30: Namespace Flag Verification](#q30-namespace-flag-verification)

Pre-validated SQL queries for common INFORMATION_SCHEMA analysis scenarios. All queries require `SET odps.namespace.schema=true;` prefix.

## Storage Queries

### Q1: Top 20 Tables by Storage

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT table_name, owner_name, data_length / 1024 / 1024 / 1024 AS size_gb,
       lifecycle, last_modified_time
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
WHERE table_type = 'MANAGED_TABLE'
  AND data_length IS NOT NULL
ORDER BY data_length DESC
LIMIT 20;
```

### Q2: Storage Breakdown by Owner

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT owner_name,
       COUNT(*) AS table_count,
       SUM(data_length) / 1024 / 1024 / 1024 / 1024 AS total_tb
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
WHERE table_type = 'MANAGED_TABLE'
  AND data_length IS NOT NULL
GROUP BY owner_name
ORDER BY total_tb DESC;
```

### Q3: Zombie Tables (Not Accessed in 90 Days)

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT table_name, owner_name, data_length / 1024 / 1024 / 1024 AS size_gb,
       last_modified_time, lifecycle
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
WHERE COALESCE(last_access_time, last_modified_time) < DATEADD(GETDATE(), -90, 'dd')
  AND table_type = 'MANAGED_TABLE'
  AND data_length IS NOT NULL
ORDER BY data_length DESC;
```

### Q4: Partition Explosion Risk

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT table_catalog, table_schema, table_name,
       COUNT(*) AS partition_count,
       SUM(data_length) / 1024 / 1024 / 1024 AS size_gb
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.PARTITIONS
GROUP BY table_catalog, table_schema, table_name
HAVING COUNT(*) > 1000
ORDER BY partition_count DESC
LIMIT 20;
```

## Cost Queries

### Q5: Daily CU-Hour Trend

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL
**Execution:** Sync OK for ds ≤3 days; MUST use `async=true` for ds >3 days

```sql
SELECT ds,
       COUNT(*) AS task_count,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -14, 'dd'), 'yyyymmdd')
GROUP BY ds
ORDER BY ds DESC
LIMIT 30;
```

### Q6: Cost by Task Owner

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT owner_name,
       COUNT(*) AS task_count,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours,
       SUM(cost_cpu) * 100.0 / SUM(SUM(cost_cpu)) OVER () AS cost_pct
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
GROUP BY owner_name
ORDER BY cu_hours DESC;
```

### Q7: Cost by Task Type

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT task_type,
       COUNT(*) AS task_count,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
GROUP BY task_type
ORDER BY cu_hours DESC;
```

### Q8: Top 20 Most Expensive Tasks

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT task_name, task_type, owner_name, start_time,
       cost_cpu / 100.0 / 3600 AS cu_hours,
       DATEDIFF(end_time, start_time, 'ss') AS run_seconds
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
ORDER BY cost_cpu DESC
LIMIT 20;
```

## Failure Queries

### Q9: Failed Tasks Yesterday

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT task_catalog, task_name, task_type, inst_id, owner_name, start_time, end_time,
       result,
       cost_cpu / 100.0 / 3600 AS cu_hours
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
  AND status = 'Failed'
ORDER BY start_time DESC;
```

### Q10: Daily Failure Rate

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL
**Execution:** Sync OK for ds ≤3 days; MUST use `async=true` for ds >3 days

```sql
SELECT ds,
       COUNT(*) AS total_tasks,
       SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) AS failed_tasks,
       SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS failure_rate
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -14, 'dd'), 'yyyymmdd')
GROUP BY ds
ORDER BY ds DESC
LIMIT 14;
```

### Q11: Failure Breakdown by Type

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT task_type,
       COUNT(*) AS total,
       SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS failure_rate
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
GROUP BY task_type
ORDER BY failed DESC;
```

## Permission Queries

### Q12: Permission Exposure

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT p.table_catalog, p.table_schema, p.table_name, p.user_name, p.privilege_type, t.owner_name
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLE_PRIVILEGES p
JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES t 
  ON p.table_catalog = t.table_catalog AND p.table_schema = t.table_schema AND p.table_name = t.table_name
WHERE p.user_name != t.owner_name
  AND (p.expired IS NULL OR p.expired > GETDATE())
ORDER BY p.table_name;
```

### Q13: Admin Role Users

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT u.user_name, u.user_id, r.role_name, ur.user_role_catalog
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.USERS u
JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.USER_ROLES ur ON u.user_id = ur.user_id AND (u.user_catalog = ur.user_role_catalog OR (u.user_catalog IS NULL AND ur.user_role_catalog IS NULL))
-- NOTE: user_role_catalog and role_catalog may be NULL for tenant-level roles;
-- the OR condition handles both project-level and tenant-level role matching.
JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.ROLES r ON ur.role_name = r.role_name AND (ur.user_role_catalog = r.role_catalog OR (ur.user_role_catalog IS NULL AND r.role_catalog IS NULL))
WHERE LOWER(r.role_name) IN ('super_administrator', 'admin')
ORDER BY u.user_name;
```

### Q14: User-Role Matrix

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT u.user_name, u.user_id, r.role_name, ur.user_role_catalog
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.USERS u
LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.USER_ROLES ur ON u.user_id = ur.user_id AND (u.user_catalog = ur.user_role_catalog OR (u.user_catalog IS NULL AND ur.user_role_catalog IS NULL))
LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.ROLES r ON ur.role_name = r.role_name AND (ur.user_role_catalog = r.role_catalog OR (ur.user_role_catalog IS NULL AND r.role_catalog IS NULL))
ORDER BY u.user_name, r.role_name;
```

## Governance Queries

### Q15: Table Comment Coverage

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT
    COUNT(CASE WHEN table_comment IS NOT NULL AND table_comment != '' THEN 1 END) AS commented,
    COUNT(*) AS total,
    COUNT(CASE WHEN table_comment IS NOT NULL AND table_comment != '' THEN 1 END) * 100.0 / COUNT(*) AS coverage_pct
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES;
```

### Q16: Column Comment Coverage

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT
    COUNT(CASE WHEN column_comment IS NOT NULL AND column_comment != '' THEN 1 END) AS commented,
    COUNT(*) AS total,
    COUNT(CASE WHEN column_comment IS NOT NULL AND column_comment != '' THEN 1 END) * 100.0 / COUNT(*) AS coverage_pct
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.COLUMNS;
```

## Tunnel Queries

### Q17: Daily Tunnel Volume

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL
**Execution:** Sync OK for ds =1 day; MUST use `async=true` for ds >1 day (TUNNELS_HISTORY volume >> TASKS_HISTORY)

```sql
SELECT ds,
       COUNT(*) AS tunnel_count,
       SUM(data_size) / 1024 / 1024 / 1024 AS volume_gb
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TUNNELS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
GROUP BY ds
ORDER BY ds DESC
LIMIT 7;
```

> **Tip:** For upload/download breakdown, add `operate_type` to SELECT and GROUP BY: `GROUP BY ds, operate_type`

### Q18: Top Tunnel Downloads

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT tunnel_catalog, object_name, operate_type,
       COUNT(*) AS tunnel_count,
       SUM(data_size) / 1024 / 1024 / 1024 AS volume_gb
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TUNNELS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
  AND operate_type IN ('DOWNLOADLOG', 'DOWNLOADINSTANCELOG')
GROUP BY tunnel_catalog, object_name, operate_type
ORDER BY volume_gb DESC
LIMIT 20;
```

## Object Count Queries

### Q19: Object Inventory

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT 'Tables' AS object_type, COUNT(*) AS cnt FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
UNION ALL
SELECT 'UDFs', COUNT(*) FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.UDFS
UNION ALL
SELECT 'Resources', COUNT(*) FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.RESOURCES
UNION ALL
SELECT 'Roles', COUNT(*) FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.ROLES
UNION ALL
SELECT 'Packages', COUNT(*) FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.INSTALLED_PACKAGES;
```

## Performance Queries

### Q20: Top 20 Slowest Tasks

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT task_catalog, task_name, task_type, owner_name, start_time,
       DATEDIFF(end_time, start_time, 'ss') AS run_seconds
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
  AND status = 'Terminated'
ORDER BY run_seconds DESC
LIMIT 20;
```

## Hot Table Queries

### Q21: Top 20 Most Accessed Tables (Last 7 Days)

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL
**Execution:** Sync may work for ds ≤3 days; MUST use `async=true` for ds >3 days (LATERAL VIEW EXPLODE causes row expansion)

```sql
SELECT table_name,
       COUNT(*) AS access_count,
       SUM(input_bytes) / 1024 / 1024 / 1024 AS total_read_gb
FROM (
    SELECT input_bytes,
           REGEXP_REPLACE(input_tables, '^\\[|\\]|"|\\s', '') AS table_list
    FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
    WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd')
      AND input_tables IS NOT NULL AND input_tables != ''
) t
LATERAL VIEW EXPLODE(SPLIT(table_list, ',')) tbl AS table_name
WHERE table_name != ''
GROUP BY table_name
ORDER BY access_count DESC
LIMIT 20;
```

### Q22: Top Tables by Data Volume Read (Last 7 Days)

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL
**Execution:** Sync may work for ds ≤3 days; MUST use `async=true` for ds >3 days (LATERAL VIEW EXPLODE causes row expansion)

```sql
SELECT table_name,
       COUNT(*) AS access_count,
       SUM(input_bytes) / 1024 / 1024 / 1024 AS total_read_gb
FROM (
    SELECT input_bytes,
           REGEXP_REPLACE(input_tables, '^\\[|\\]|"|\\s', '') AS table_list
    FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
    WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd')
      AND input_tables IS NOT NULL AND input_tables != ''
) t
LATERAL VIEW EXPLODE(SPLIT(table_list, ',')) tbl AS table_name
WHERE table_name != ''
GROUP BY table_name
ORDER BY total_read_gb DESC
LIMIT 20;
```

### Q23: User Resource Consumption by Table

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL
**Execution:** Sync may work for ds ≤3 days; MUST use `async=true` for ds >3 days (LATERAL VIEW EXPLODE causes row expansion)

```sql
SELECT owner_name, table_name,
       COUNT(*) AS access_count,
       SUM(input_bytes) / 1024 / 1024 / 1024 AS total_read_gb,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours
FROM (
    SELECT owner_name, input_bytes, cost_cpu,
           REGEXP_REPLACE(input_tables, '^\\[|\\]|"|\\s', '') AS table_list
    FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
    WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd')
      AND input_tables IS NOT NULL AND input_tables != ''
) t
LATERAL VIEW EXPLODE(SPLIT(table_list, ',')) tbl AS table_name
WHERE table_name != ''
GROUP BY owner_name, table_name
ORDER BY access_count DESC;
```

For column name pitfalls and corrections, see the [Critical Column Name Reference in SKILL.md](../SKILL.md#column-reference).

## Official Verified Queries (Q24-Q29)

These queries use COALESCE for robustness across schema variations.

### Q24: TOP Storage Tables with COALESCE

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
-- Cost warning: LEFT JOIN PARTITIONS may produce many rows for heavily partitioned tables.
-- Consider adding WHERE clause or using a subquery for partition_count instead.
SELECT
    t.table_catalog,
    t.table_schema,
    t.table_name,
    t.table_comment,
    COALESCE(t.data_length, 0) AS storage_bytes,
    CASE
        WHEN COALESCE(t.data_length, 0) >= 1099511627776
        THEN CONCAT(ROUND(COALESCE(t.data_length, 0) / 1099511627776.0, 2), ' TB')
        WHEN COALESCE(t.data_length, 0) >= 1073741824
        THEN CONCAT(ROUND(COALESCE(t.data_length, 0) / 1073741824.0, 2), ' GB')
        ELSE CONCAT(ROUND(COALESCE(t.data_length, 0) / 1048576.0, 2), ' MB')
    END AS storage_readable,
    t.owner_name,
    t.last_modified_time,
    COUNT(DISTINCT p.partition_name) AS partition_count
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES t
LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.PARTITIONS p
    ON t.table_catalog = p.table_catalog
    AND t.table_schema = p.table_schema
    AND t.table_name = p.table_name
GROUP BY t.table_catalog, t.table_schema, t.table_name,
         t.table_comment, t.data_length,
         t.owner_name, t.last_modified_time
ORDER BY storage_bytes DESC
LIMIT 20;
```

### Q25: Partition Explosion Risk (Simplified)

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT
    table_catalog,
    table_schema,
    table_name,
    COUNT(DISTINCT partition_name) AS partition_count,
    MIN(create_time) AS earliest_partition,
    MAX(create_time) AS latest_partition
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.PARTITIONS
GROUP BY table_catalog, table_schema, table_name
HAVING COUNT(DISTINCT partition_name) > 500
ORDER BY partition_count DESC;
```

### Q26: Daily Failure Trend

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL
**Execution:** Sync OK for ds ≤3 days; MUST use `async=true` for ds >3 days

```sql
SELECT
    ds AS stat_date,
    COUNT(*) AS task_count,
    SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) AS failed_count,
    ROUND(SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2) AS failure_rate_pct
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd')
GROUP BY ds
ORDER BY stat_date;
```

### Q27: CU-Hour by Project and Hour

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT task_catalog,
       DATEPART(end_time, 'hh') AS end_hour,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
GROUP BY task_catalog, DATEPART(end_time, 'hh')
ORDER BY cu_hours DESC;
```

> **Warning:** Do NOT use `TO_CHAR(end_time, 'hh')` (12-hour format, AM/PM collapse) or `TO_CHAR(end_time, 'hh24')` (not supported in MaxCompute, outputs literal "24"). Use `DATEPART(end_time, 'hh')` or `HOUR(end_time)` which return 0-23.

### Q28: User Resource Consumption

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL
**Execution:** Sync OK for ds ≤3 days; MUST use `async=true` for ds >3 days

```sql
SELECT owner_name,
       COUNT(*) AS query_count,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours,
       SUM(cost_mem) AS mem_mb_seconds,
       SUM(input_bytes) / 1024 / 1024 / 1024 AS input_gb,
       SUM(output_bytes) / 1024 / 1024 / 1024 AS output_gb
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd')
GROUP BY owner_name
ORDER BY cu_hours DESC
LIMIT 100;
```

### Q29: Project Configuration Audit

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT catalog_name, region, create_time,
       get_json_object(json_parse(settings), '$."odps.timemachine.retention.days"') AS backup_days,
       get_json_object(json_parse(settings), '$."odps.sql.metering.value.max"') AS sql_cost_limit
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.CATALOGS;
```

## Smoke Test

### Q30: Namespace Flag Verification

> **Purpose**: Minimal query to verify `odps.namespace.schema=true` is set correctly. Run this first if IS queries return "Table not found".

**MCP:** `execute_sql` hints=`{"odps.namespace.schema":"true"}` | **odpscmd:** `SET odps.namespace.schema=true;` + SQL

```sql
SELECT COUNT(*) AS table_count
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES;
```
