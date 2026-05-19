# Join Paths Reference

> Related: [views-reference.md](views-reference.md), [verified-queries.md](verified-queries.md), [SKILL.md](../SKILL.md)

Trusted join relationships between INFORMATION_SCHEMA views. All views are in `SYSTEM_CATALOG.INFORMATION_SCHEMA`.

**Important:** Always include `table_catalog` in join conditions for robustness, especially for non-3-tier model projects where `table_schema` may be NULL.

**MCP Tip:** Before constructing multi-table JOINs, use `list_tables` to confirm tables exist and `get_table_schema` to verify column names. This prevents errors from misspelled table/column names in complex queries.

## Join Paths

| # | Left Table | Right Table | Join Condition | Purpose |
|---|---|---|---|---|
| 1 | TABLES | COLUMNS | `t.table_catalog = c.table_catalog AND t.table_schema = c.table_schema AND t.table_name = c.table_name` | Table + column metadata |
| 2 | TABLES | PARTITIONS | `t.table_catalog = p.table_catalog AND t.table_schema = p.table_schema AND t.table_name = p.table_name` | Table + partition details |
| 3 | TABLES | TABLE_PRIVILEGES | `t.table_catalog = p.table_catalog AND t.table_schema = p.table_schema AND t.table_name = p.table_name` | Table + permissions |
| 4 | TABLES | TABLE_ACCESS_INFO | `t.table_catalog = a.table_catalog AND t.table_schema = a.table_schema AND t.table_name = a.table_name` | Table + access statistics |
| 5 | TABLES | TABLE_LABELS | `t.table_catalog = l.table_catalog AND t.table_schema = l.table_schema AND t.table_name = l.table_name` | Table + security labels |
| 6 | PARTITIONS | PARTITION_ACCESS_INFO | `p.table_catalog = a.table_catalog AND p.table_schema = a.table_schema AND p.table_name = a.table_name AND p.partition_name = a.partition_name` | Partition + access statistics |
| 7 | CATALOGS | SCHEMAS | `c.catalog_name = s.schema_catalog` | Project + schema hierarchy |
| 8 | USERS | USER_ROLES | `u.user_id = ur.user_id` | User + role assignments |
| 9 | USER_ROLES | ROLES | `ur.role_name = r.role_name AND ur.user_role_catalog = r.role_catalog` | Role assignments + role details |
| 10 | COLUMNS | COLUMN_LABELS | `c.table_catalog = l.table_catalog AND c.table_schema = l.table_schema AND c.table_name = l.table_name AND c.column_name = l.column_name` | Column + security labels |
| 11 | COLUMNS | COLUMN_PRIVILEGES | `c.table_catalog = p.table_catalog AND c.table_schema = p.table_schema AND c.table_name = p.table_name AND c.column_name = p.column_name` | Column + permissions |
| 12 | UDFS | UDF_RESOURCES | `u.udf_catalog = r.udf_catalog AND u.udf_schema = r.udf_schema AND u.udf_name = r.udf_name` | UDF + resource dependencies |
| 13 | UDFS | UDF_PRIVILEGES | `u.udf_catalog = p.udf_catalog AND u.udf_schema = p.udf_schema AND u.udf_name = p.udf_name` | UDF + permissions |
| 14 | INSTALLED_PACKAGES | PACKAGE_OBJECTS | `p.package_catalog = o.package_catalog AND p.package_name = o.package_name` | Package + contained objects |
| 15 | INSTALLED_PACKAGES | PACKAGE_PRIVILEGES | `p.package_catalog = pp.package_catalog AND p.package_name = pp.package_name` | Package + permissions |
| 16 | RESOURCES | RESOURCE_PRIVILEGES | `r.resource_catalog = p.resource_catalog AND r.resource_schema = p.resource_schema AND r.resource_name = p.resource_name` | Resource + permissions |

## Common Multi-Table Queries

### Table + Column + Privilege

```sql
SELECT t.table_catalog, t.table_name, t.owner_name, t.data_length,
       c.column_name, c.data_type, c.column_comment,
       p.user_name, p.privilege_type
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES t
LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.COLUMNS c
  ON t.table_catalog = c.table_catalog AND t.table_name = c.table_name
LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLE_PRIVILEGES p
  ON t.table_catalog = p.table_catalog AND t.table_name = p.table_name
WHERE t.table_name = 'my_table';
```

### Table + Partition Count

```sql
SELECT t.table_catalog, t.table_name, t.owner_name, t.data_length,
       COUNT(DISTINCT p.partition_name) AS partition_count
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES t
LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.PARTITIONS p
  ON t.table_catalog = p.table_catalog AND t.table_name = p.table_name
WHERE t.table_type = 'MANAGED_TABLE'
GROUP BY t.table_catalog, t.table_name, t.owner_name, t.data_length
ORDER BY t.data_length DESC
LIMIT 20;
```

### User + Role + Permission Chain

```sql
SELECT ur.user_role_catalog, ur.user_name, ur.user_id,
       r.role_name, r.role_label
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.USER_ROLES ur
LEFT JOIN SYSTEM_CATALOG.INFORMATION_SCHEMA.ROLES r
  ON ur.role_name = r.role_name AND ur.user_role_catalog = r.role_catalog
ORDER BY ur.user_role_catalog, ur.user_name;
```

### Admin Role Users

```sql
SELECT user_role_catalog, role_name, user_name, user_id
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.USER_ROLES
WHERE role_name IN ('super_administrator', 'admin')
ORDER BY user_role_catalog, role_name;
```

### Data Lineage: Upstream Tables

```sql
SELECT task_catalog, task_name, inst_id, input_tables, output_tables
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd')
  AND input_tables LIKE '%my_project.my_table%'
ORDER BY end_time DESC
LIMIT 50;
```

### Data Lineage: Downstream Tables

```sql
SELECT task_catalog, task_name, inst_id, output_tables
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds >= TO_CHAR(DATEADD(GETDATE(), -7, 'dd'), 'yyyymmdd')
  AND output_tables LIKE '%my_project.my_table%'
ORDER BY end_time DESC
LIMIT 50;
```

### Project Settings Audit

```sql
SELECT catalog_name, region, status,
       get_json_object(json_parse(settings), '$."odps.timemachine.retention.days"') AS backup_days,
       get_json_object(json_parse(settings), '$."odps.security.ip.whitelist"') AS ip_whitelist,
       get_json_object(json_parse(settings), '$."odps.sql.metering.value.max"') AS sql_cost_limit
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.CATALOGS;
```

### Storage Tier Distribution

```sql
SELECT storage_tier,
       COUNT(*) AS table_count,
       SUM(COALESCE(data_length, 0)) / 1024 / 1024 / 1024 AS storage_gb
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
WHERE table_type = 'MANAGED_TABLE'
GROUP BY storage_tier
ORDER BY storage_gb DESC;
```

### Permission Exposure Analysis

```sql
SELECT table_catalog, table_schema, table_name,
       COUNT(DISTINCT user_name) AS user_count,
       COLLECT_SET(privilege_type) AS privilege_types
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLE_PRIVILEGES
GROUP BY table_catalog, table_schema, table_name
ORDER BY user_count DESC
LIMIT 50;
```
