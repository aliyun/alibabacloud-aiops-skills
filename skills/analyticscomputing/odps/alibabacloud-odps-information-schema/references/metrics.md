# Metrics Reference

> Related: [verified-queries.md](verified-queries.md), [views-reference.md](views-reference.md), [SKILL.md](../SKILL.md)

All metrics with SQL expressions. Query INFORMATION_SCHEMA views with `SET odps.namespace.schema=true;`.

## Storage Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `storage_bytes` | Storage Usage | bytes | TABLES | `SUM(COALESCE(data_length, 0))` |
| `total_storage_tb` | Total Storage | TB | TABLES | `SUM(COALESCE(data_length, 0)) / 1024 / 1024 / 1024 / 1024` |
| `partition_count` | Partition Count | count | PARTITIONS | `COUNT(DISTINCT partition_name)` |
| `avg_partition_count` | Avg Partitions per Table | count | PARTITIONS | `AVG(partition_count)` |
| `zombie_table_count` | Zombie Tables (>90d unmodified) | count | TABLES | `COUNT(CASE WHEN DATEDIFF(GETDATE(), COALESCE(last_access_time, last_modified_time), 'dd') > 90 THEN 1 END)` |
| `stale_table_count` | Stale Table Count (>30d unmodified) | count | TABLES | `COUNT(CASE WHEN DATEDIFF(GETDATE(), COALESCE(last_access_time, last_modified_time), 'dd') > 30 THEN 1 END)` |

## Cost Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `task_count` | Task Count | count | TASKS_HISTORY | `COUNT(*)` |
| `failed_task_count` | Failed Task Count | count | TASKS_HISTORY | `SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END)` |
| `task_failure_rate` | Task Failure Rate | percent | TASKS_HISTORY | `SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)` |
| `running_task_count` | Running Task Count | count | TASKS | `COUNT(*)` |
| `avg_task_duration` | Avg Task Duration | seconds | TASKS_HISTORY | `AVG(DATEDIFF(end_time, start_time, 'ss'))` |
| `p99_task_duration` | P99 Task Duration | seconds | TASKS_HISTORY | `PERCENTILE(DATEDIFF(end_time, start_time, 'ss'), 0.99)` |
| `task_cost_proxy` | Task Cost Proxy | bytes | TASKS_HISTORY | `SUM(COALESCE(input_bytes, 0))` |
| `cu_hour_consumed` | CU-Hour Consumed | CU*hour | TASKS_HISTORY | `SUM(cost_cpu) / 100.0 / 3600` |

**Important notes:**
- `cost_cpu` is DOUBLE type, unit = 100 * core * seconds. Convert to CU-hours: `SUM(cost_cpu) / 100.0 / 3600`
- `cost_mem` is DOUBLE type, unit = MB * seconds
- TASKS_HISTORY status values: `Terminated` (normal finish), `Failed`, `Cancelled`
- TABLES table_type values: `MANAGED_TABLE`, `VIRTUAL_VIEW`, `EXTERNAL_TABLE`, `MATERIALIZED_VIEW`, `METADATA_TABLE`, `OBJECT_TABLE`

## Permission Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `grant_count` | Grant Count | count | TABLE_PRIVILEGES | `COUNT(*)` |
| `label_protected_table_count` | Label-Protected Table Count | count | TABLE_LABELS | `COUNT(DISTINCT table_name)` |
| `column_level_privilege_count` | Column-Level Privilege Count | count | COLUMN_PRIVILEGES | `COUNT(*)` |
| `admin_role_user_count` | Admin Role User Count | count | USER_ROLES | `COUNT(DISTINCT user_name) WHERE role_name IN ('super_administrator', 'admin')` |

## Governance Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `column_comment_coverage` | Column Comment Coverage | percent | COLUMNS | `COUNT(CASE WHEN column_comment IS NOT NULL AND column_comment != '' THEN 1 END) * 100.0 / COUNT(*)` |
| `table_comment_coverage` | Table Comment Coverage | percent | TABLES | `COUNT(CASE WHEN table_comment IS NOT NULL AND table_comment != '' THEN 1 END) * 100.0 / COUNT(*)` |

**Note:** COLUMNS view has NO time field (`last_modified_time` exists in TABLES/PARTITIONS only). `column_comment_coverage` can only be computed as a static snapshot, not as a time-series metric.

## Hotness Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `table_hotness_score` | Table Hotness Score | score | TASKS_HISTORY | `COUNT(*)` appearances in input_tables/output_tables |
| `table_access_count` | Table Access Count | count | TABLE_ACCESS_INFO | `SUM(access_count)` |
| `partition_access_count` | Partition Access Count | count | PARTITION_ACCESS_INFO | `SUM(access_count)` |

## Tunnel Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `daily_tunnel_volume` | Daily Tunnel Volume | bytes | TUNNELS_HISTORY | `SUM(data_size)` grouped by ds |

## Quota Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `quota_cpu_usage_ratio` | Elastic CPU Usage Ratio | percent | QUOTA_USAGE | `cpu_elastic_quota_used * 100.0 / NULLIF(cpu_elastic_quota_max, 0)` |
| `quota_mem_usage_ratio` | Elastic Memory Usage Ratio | percent | QUOTA_USAGE | `mem_elastic_quota_used * 100.0 / NULLIF(mem_elastic_quota_max, 0)` |
| `quota_reserved_cpu_usage_ratio` | Reserved CPU Usage Ratio | percent | QUOTA_USAGE | `cpu_quota_used * 100.0 / NULLIF(cpu_quota_max, 0)` |
| `quota_reserved_mem_usage_ratio` | Reserved Memory Usage Ratio | percent | QUOTA_USAGE | `mem_quota_used * 100.0 / NULLIF(mem_quota_max, 0)` |
| `quota_count` | Quota Group Count | count | QUOTA_USAGE | `COUNT(DISTINCT name)` |

## Object Count Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `catalog_count` | Project Count | count | CATALOGS | `COUNT(DISTINCT catalog_name)` |
| `schema_count` | Schema Count | count | SCHEMAS | `COUNT(DISTINCT schema_name)` |
| `package_count` | Installed Package Count | count | INSTALLED_PACKAGES | `COUNT(DISTINCT package_name)` |
| `udf_count` | UDF Count | count | UDFS | `COUNT(DISTINCT udf_name)` |
| `resource_count` | Resource Count | count | RESOURCES | `COUNT(DISTINCT resource_name)` |

## Advanced Task Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `input_records_total` | Total Input Records | count | TASKS_HISTORY | `SUM(COALESCE(input_records, 0))` |
| `output_records_total` | Total Output Records | count | TASKS_HISTORY | `SUM(COALESCE(output_records, 0))` |
| `io_ratio` | I/O Record Ratio | ratio | TASKS_HISTORY | `SUM(output_records) * 1.0 / NULLIF(SUM(input_records), 0)` |
| `sql_complexity_avg` | Avg SQL Complexity | score | TASKS_HISTORY | `AVG(complexity)` |
| `task_count_by_type` | Task Count by Type | count | TASKS_HISTORY | `COUNT(*)` GROUP BY task_type |
| `cost_by_task_type` | Cost by Task Type | CU*hour | TASKS_HISTORY | `SUM(cost_cpu) / 100.0 / 3600` GROUP BY task_type |

## Storage Tier Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `standard_storage_bytes` | Standard Storage Bytes | bytes | TABLES | `SUM(COALESCE(data_length, 0)) WHERE storage_tier = 'standard'` |
| `lowfreq_storage_bytes` | Low-Frequency Storage Bytes | bytes | TABLES | `SUM(COALESCE(data_length, 0)) WHERE storage_tier = 'lowfrequency'` |
| `longterm_storage_bytes` | Long-Term Storage Bytes | bytes | TABLES | `SUM(COALESCE(data_length, 0)) WHERE storage_tier = 'longterm'` |
| `storage_tier_distribution` | Storage Tier Distribution | bytes | TABLES | `storage_tier, COUNT(*), SUM(data_length)` GROUP BY storage_tier |
| `extreme_storage_bytes` | Extreme Storage Bytes | bytes | TABLES | `SUM(COALESCE(data_length, 0)) WHERE table_exstore_type IS NOT NULL` |

## Cluster Table Metrics

| Metric ID | Metric Name | Unit | Data Source | SQL Expression |
|---|---|---|---|---|
| `cluster_table_count` | Cluster Table Count | count | TABLES | `COUNT(*) WHERE cluster_type IS NOT NULL` |
| `hash_cluster_count` | Hash Cluster Table Count | count | TABLES | `COUNT(*) WHERE cluster_type = 'HASH'` |
| `range_cluster_count` | Range Cluster Table Count | count | TABLES | `COUNT(*) WHERE cluster_type = 'RANGE'` |

## Alert Thresholds

| Metric | Warning | Critical | Description |
|---|---|---|---|
| `zombie_table_count` | >100 | >500 | Tables unaccessed for 90+ days |
| `task_failure_rate` | >10% | >25% | Daily task failure rate |
| `daily_cu_hours` | >1000 | >5000 | Daily CU-hour consumption |
