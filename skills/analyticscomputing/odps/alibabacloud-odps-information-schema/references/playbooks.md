# Playbook Reference

> Related: [causal-templates.md](causal-templates.md), [verified-queries.md](verified-queries.md), [SKILL.md](../SKILL.md)

Diagnostic scenarios for common operational concerns. Each playbook provides: intent signals, required tables, preferred metrics/dimensions, and suggested queries.

## 1. Storage Pressure (storage_pressure)

**Intent signals:** "存储满了", "storage full", "space pressure", "磁盘不够", "storage trend", "storage growth"

**Required tables:** TABLES, PARTITIONS

**Key metrics:** total_storage_tb, storage_bytes, partition_count, zombie_table_count, stale_table_count

**MCP Quick Path:** `list_tables` -> browse by size -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for aggregate queries

**SQL Path / Check sequence:**
1. Total storage: `SELECT SUM(COALESCE(data_length, 0)) / 1024 / 1024 / 1024 / 1024 AS total_tb FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES;`
2. Top tables by size: Top 20 tables by data_length
3. Zombie tables: Tables not modified in 90+ days
4. Partition explosion risk: Tables with >500 partitions
5. Stale tables: Tables not modified in 30+ days

**Suggested prompt:** "Analyze storage usage. Show top tables by size, identify zombie tables, and check for partition explosion risks."

## 2. Cost Pressure (cost_pressure)

**Intent signals:** "费用太高", "cost too high", "compute cost", "CU消耗大", "扫描成本", "资源消耗"

**Required tables:** TASKS_HISTORY

**Key metrics:** cu_hour_consumed, task_cost_proxy, task_count, task_failure_rate

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` (async recommended for 7+ day ds range)

**SQL Path / Check sequence:**
1. Daily CU-hour trend: Group by ds
2. Top cost tasks: By cost_cpu descending
3. Cost breakdown by owner: GROUP BY owner_name
4. Cost breakdown by task type: GROUP BY task_type
5. Cost breakdown by project: GROUP BY task_catalog

**Suggested prompt:** "Analyze compute costs. Show daily CU-hour trend, top cost consumers, and breakdown by owner and task type."

## 3. Task Failure Spike (task_failure_spike)

**Intent signals:** "任务失败", "job failed", "error rate", "执行失败", "失败率升高", "作业异常"

**Required tables:** TASKS_HISTORY

**Key metrics:** failed_task_count, task_failure_rate, task_count

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` -> `check_access` to verify permissions

**SQL Path / Check sequence:**
1. Daily failure count and rate: `SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END)`
2. Failure breakdown by task_type
3. Failure breakdown by owner_name
4. Top failed tasks with error details (result field)

**Suggested prompt:** "Analyze task failures. Show failure rate trend, breakdown by type and owner, and list top failed tasks."

## 4. Permission Audit (permission_audit)

**Intent signals:** "权限审计", "who has access", "permission review", "安全审计", "高危授权", "越权风险"

**Required tables:** TABLE_PRIVILEGES, USERS, ROLES, USER_ROLES, COLUMNS, COLUMN_PRIVILEGES

**Key metrics:** grant_count, column_level_privilege_count, label_protected_table_count, admin_role_user_count

**MCP Quick Path:** `check_access` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for privilege details

**SQL Path / Check sequence:**
1. Total grant count
2. Permission exposure per table: COUNT(DISTINCT user_name) per table
3. Column-level privileges
4. Admin role users: USER_ROLES WHERE role_name IN ('super_administrator', 'admin')
5. Users without roles (orphan users)

**Suggested prompt:** "Audit permissions. Show grant distribution, column-level privileges, and identify users without roles."

## 5. Hot Table Analysis (hot_table_analysis)

**Intent signals:** "热表", "most accessed table", "频繁访问的表", "热点表"

**Required tables:** TASKS_HISTORY, TABLES, TABLE_ACCESS_INFO

**Key metrics:** table_access_count, table_hotness_score

**MCP Quick Path:** `list_tables` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for access pattern analysis (async recommended for 7+ day ds range)

**SQL Path / Check sequence:**
1. Tables by access frequency from TABLE_ACCESS_INFO
2. Top 10 most accessed tables from TASKS_HISTORY input_tables
3. Hot tables with storage sizes (join TABLES)
4. Zombie tables (not accessed in 90+ days)

**Suggested prompt:** "Find the most accessed tables. Show top 10 by query frequency and their storage sizes."

## 6. Metadata Governance Gap (metadata_governance_gap)

**Intent signals:** "注释覆盖率", "comment coverage", "governance gap", "元数据治理"

**Required tables:** TABLES, COLUMNS

**Key metrics:** table_comment_coverage, column_comment_coverage

**MCP Quick Path:** `list_tables` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for coverage metrics

**SQL Path / Check sequence:**
1. Table comment coverage percentage
2. Column comment coverage percentage
3. Tables missing comments
4. Columns missing comments

**Suggested prompt:** "Check metadata governance. Show table and column comment coverage, list tables/columns missing comments."

## 7. Task Performance (task_performance)

**Intent signals:** "任务慢", "slow query", "performance", "执行时间长"

**Required tables:** TASKS_HISTORY

**Key metrics:** avg_task_duration, p99_task_duration, task_count

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` (async recommended for large ds range)

**SQL Path / Check sequence:**
1. Top 20 longest running tasks: ORDER BY DATEDIFF(end_time, start_time, 'ss') DESC
2. P99 duration by task type
3. Tasks with high cost_cpu but low input_bytes (inefficient)

**Suggested prompt:** "Analyze task performance. Show top 20 slowest tasks, P99 duration by type, and identify inefficient queries."

## 8. Data Transfer Audit (data_transfer_audit)

**Intent signals:** "下载审计", "tunnel audit", "data export", "数据传输", "公网下载"

**Required tables:** TUNNELS_HISTORY

**Key metrics:** daily_tunnel_volume (SUM(data_size))

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` -> async recommended for tunnel history queries

**SQL Path / Check sequence:**
1. Daily tunnel volume trend: SUM(data_size) GROUP BY ds
2. Top downloads by data_size: ORDER BY data_size DESC
3. Public IP download tracing: GROUP BY client_ip for DOWNLOAD operations
4. Failed tunnel transfers

**Suggested prompt:** "Audit data transfers. Show daily tunnel volume trend, top downloads, and trace public IP access."

## 9. User Role Audit (user_role_audit)

**Intent signals:** "用户角色", "user roles", "role matrix", "角色分配"

**Required tables:** USERS, ROLES, USER_ROLES

**Key metrics:** admin_role_user_count

**MCP Quick Path:** `check_access` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for role matrix

**SQL Path / Check sequence:**
1. User-role matrix: JOIN USER_ROLES with ROLES
2. Users with multiple roles
3. Roles with no users (orphan roles)
4. Admin/super_administrator users

**Suggested prompt:** "Show user-role matrix. Identify users with excessive roles and orphan roles."

## 10. Partition Lifecycle (partition_lifecycle)

**Intent signals:** "分区太多", "partition explosion", "分区治理"

**Required tables:** PARTITIONS, TABLES

**Key metrics:** partition_count, avg_partition_count

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for partition queries -> `list_tables` for context

**SQL Path / Check sequence:**
1. Tables with most partitions: GROUP BY table_name HAVING COUNT > 500
2. Partition count by storage_tier
3. Small partitions (<1MB)
4. Partitions with lifecycle_enabled = false

**Suggested prompt:** "Analyze partition usage. Show tables with most partitions, identify small partitions, and check lifecycle settings."

## 11. Quota Resource Monitoring (quota_resource_monitoring)

**Intent signals:** "quota 使用", "资源使用率", "CPU利用率", "内存使用", "配额监控"

**Required tables:** QUOTA_USAGE

**Key metrics:** quota_cpu_usage_ratio, quota_mem_usage_ratio, quota_reserved_cpu_usage_ratio

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for quota usage queries

**SQL Path / Check sequence:**
1. Current elastic CPU and memory usage: cpu_elastic_quota_used / cpu_elastic_quota_max
2. Reserved CPU and memory usage: cpu_quota_used / cpu_quota_max
3. Quotas approaching limits (>80%)
4. Usage trend over time by region

**Suggested prompt:** "Monitor quota usage. Show current CPU and memory utilization by quota group."

## 12. Package Management (package_management)

**Intent signals:** "package 审计", "package audit", "包管理", "共享包"

**Required tables:** INSTALLED_PACKAGES, PACKAGE_OBJECTS, PACKAGE_PRIVILEGES

**Key metrics:** package_count

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for package inventory and privileges

**SQL Path / Check sequence:**
1. Installed packages by project
2. Package object types distribution
3. Package privilege audit

**Suggested prompt:** "Audit installed packages. Show package distribution by project and their permissions."

## 13. UDF Management (udf_management)

**Intent signals:** "UDF 审计", "UDF audit", "自定义函数", "函数管理"

**Required tables:** UDFS, UDF_RESOURCES, UDF_PRIVILEGES

**Key metrics:** udf_count

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for UDF inventory and dependencies

**SQL Path / Check sequence:**
1. UDF list by project
2. UDF resource dependencies
3. UDF privilege audit

**Suggested prompt:** "Audit UDFs. Show UDF list, resource dependencies, and permissions."

## 14. Resource Audit (resource_audit)

**Intent signals:** "资源审计", "resource audit", "资源管理"

**Required tables:** RESOURCES, RESOURCE_PRIVILEGES

**Key metrics:** resource_count

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for resource inventory and privileges

**SQL Path / Check sequence:**
1. Resource list by type (jar, archive, table, py)
2. Resource privilege audit
3. Temporary resources

**Suggested prompt:** "Audit resources. Show resource distribution by type and their permissions."

## 15. Catalog & Schema Overview (catalog_schema_overview)

**Intent signals:** "项目概览", "project overview", "schema 结构", "组织"

**Required tables:** CATALOGS, SCHEMAS

**Key metrics:** catalog_count, schema_count

**MCP Quick Path:** `list_projects` -> `list_schemas` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for settings audit

**SQL Path / Check sequence:**
1. Project list with status and region
2. Schema organization per project
3. Project settings audit (backup, IP whitelist, cost limits)

**Suggested prompt:** "Show project and schema overview. Include project settings and status."

## 16. Data Security LABEL (data_security_label)

**Intent signals:** "安全标签", "label audit", "LABEL 管理", "数据安全"

**Required tables:** TABLE_LABELS, COLUMN_LABELS, TABLE_LABEL_GRANTS, COLUMN_LABEL_GRANTS

**Key metrics:** label_protected_table_count

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for LABEL inventory and grant queries

**SQL Path / Check sequence:**
1. Tables with LABEL protection
2. Columns with LABEL protection
3. LABEL grant distribution
4. Expired LABEL grants

**Suggested prompt:** "Audit LABEL security. Show protected tables/columns and grant distribution."

## 17. Access Pattern Analysis (access_pattern_analysis)

**Intent signals:** "访问模式", "access pattern", "访问频率", "热点分析"

**Required tables:** TABLE_ACCESS_INFO, PARTITION_ACCESS_INFO, TASKS_HISTORY

**Key metrics:** table_access_count, partition_access_count

**MCP Quick Path:** `list_tables` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for access frequency analysis (async recommended for 7+ day ds range)

**SQL Path / Check sequence:**
1. Table access frequency by project
2. Partition access hotspots
3. Access pattern by time (daily trend)

**Suggested prompt:** "Analyze access patterns. Show table access frequency and partition hotspots."

## 18. Real-time Task Monitoring (realtime_task_monitoring)

**Intent signals:** "实时任务", "running tasks", "当前任务", "监控"

**Required tables:** TASKS (live view, Preview)

**Key metrics:** running_task_count

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for live task queries (TASKS view)

**SQL Path / Check sequence:**
1. Currently running tasks with CPU/memory usage
2. Tasks waiting in queue
3. Resource usage by quota

**Suggested prompt:** "Show currently running tasks. Include CPU and memory usage."

## 19. Data Lineage Tracking (data_lineage_tracking) **[NEW]**

**Intent signals:** "数据血缘", "lineage", "上下游依赖", "影响面", "表依赖"

**Required tables:** TASKS_HISTORY

**Key metrics:** table_hotness_score (based on input_tables/output_tables)

**MCP Quick Path:** `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for lineage queries on input_tables/output_tables (async recommended for large ds range)

**SQL Path / Check sequence:**
1. Upstream tables for a given table (appearing in input_tables)
2. Downstream tables for a given table (appearing in output_tables)
3. Full dependency chain for critical tables
4. Tables with most dependencies

**Suggested prompt:** "Trace data lineage for table X. Show upstream and downstream dependencies."

## 20. Storage Tier Analysis (storage_tier_analysis) **[NEW]**

**Intent signals:** "存储分层", "storage tier", "低频存储", "长期存储", "极限存储"

**Required tables:** TABLES, PARTITIONS

**Key metrics:** storage_bytes by storage_tier

**MCP Quick Path:** `list_tables` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for storage tier distribution

**SQL Path / Check sequence:**
1. Data distribution by storage_tier (standard/lowfrequency/longterm)
2. Tables eligible for tier migration
3. Extreme storage tables (table_exstore_type)
4. Cost savings from tier optimization

**Suggested prompt:** "Analyze storage tier distribution. Show data by tier and migration opportunities."

## 21. Project Configuration Audit (project_config_audit) **[NEW]**

**Intent signals:** "项目配置", "project settings", "备份配置", "IP白名单", "安全配置"

**Required tables:** CATALOGS

**Key metrics:** catalog_count with settings

**MCP Quick Path:** `list_projects` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for CATALOGS settings audit

**SQL Path / Check sequence:**
1. Backup retention: `get_json_object(json_parse(settings), '$."odps.timemachine.retention.days"')`
2. IP whitelist audit: `get_json_object(json_parse(settings), '$."odps.security.ip.whitelist"')`
3. SQL cost limits: `get_json_object(json_parse(settings), '$."odps.sql.metering.value.max"')`
4. Projects missing backup configuration

**Suggested prompt:** "Audit project configurations. Check backup settings, IP whitelists, and cost limits."

## 22. Extreme Storage Analysis (extreme_storage_analysis)

**Intent signals:** "极限存储", "extreme storage", "exstore", "极限存储表", "存储压缩"

**Required tables:** TABLES

**Key metrics:** extreme_storage_bytes, storage_bytes

**MCP Quick Path:** `list_tables` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for EXSTORE table analysis

**SQL Path / Check sequence:**
1. Tables with extreme storage: `WHERE table_exstore_type IN ('EXSTORE_TABLE_VIRTUAL', 'EXSTORE_TABLE_PHYSICAL')`
2. Virtual vs physical table ratio
3. Storage savings from extreme storage compression
4. Projects using extreme storage

**Suggested prompt:** "Analyze extreme storage usage. Show tables using EXSTORE and their storage savings."

## 23. Cluster Table Analysis (cluster_table_analysis)

**Intent signals:** "聚簇表", "cluster table", "HASH聚簇", "RANGE聚簇", "分桶表", "bucket"

**Required tables:** TABLES, PARTITIONS

**Key metrics:** cluster_table_count, hash_cluster_count, range_cluster_count

**MCP Quick Path:** `list_tables` -> `execute_sql` + hints=`{"odps.namespace.schema":"true"}` for cluster type distribution and bucket analysis

**SQL Path / Check sequence:**
1. Cluster type distribution: GROUP BY cluster_type (HASH/RANGE)
2. Tables with optimal bucket count: `WHERE number_buckets > 0`
3. Large tables without clustering: `WHERE cluster_type IS NULL AND data_length > threshold`
4. Bucket count distribution by cluster_type

**Suggested prompt:** "Analyze cluster table distribution. Show HASH vs RANGE clustering and identify large tables missing cluster optimization."
