# Causal Analysis Templates

> Related: [playbooks.md](playbooks.md), [verified-queries.md](verified-queries.md), [SKILL.md](../SKILL.md)

Root-cause investigation patterns. Each template defines: trigger condition, hypothesis dimensions with weights, verification queries, and recommendations.

**MCP Tip:** Before running causal analysis queries, use `check_access` to verify permissions and `get_project` to check project configuration. Use `list_tables` to confirm the existence of relevant IS views.

## Placeholder Filling Rules

These rules apply to all templates below:

- **Date placeholders**: Always use `DATEADD` expressions, not literal date strings (format may be wrong, and TASKS_HISTORY has ~5 min delay):
  - `<yesterday>` → `TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')`
  - `<today>` → Avoid using (data may be incomplete due to delay); if required, use `TO_CHAR(GETDATE(), 'yyyymmdd')`
  - `<baseline_period>` → `TO_CHAR(DATEADD(GETDATE(), -8, 'dd'), 'yyyymmdd')` through `TO_CHAR(DATEADD(GETDATE(), -2, 'dd'), 'yyyymmdd')`
- **`{{primary_dimension}}`**: Select the dimension with the highest `(weight × percentage_change)`. Example: if `owner_name` (weight 0.45) changed 40% and `task_type` (weight 0.30) changed 20%, pick `owner_name` because 0.45 × 40 = 18 > 0.30 × 20 = 6.
- **`ds` filter**: Every TASKS_HISTORY/TUNNELS_HISTORY query MUST include a `ds` filter.

## 1. Cost Spike Analysis (cost_spike)

**Trigger:** CU-hour consumption increased by 20%+ compared to baseline.

**Hypothesis Dimensions:**
- `owner_name` (weight: 0.45) -- Which user submitted the most additional tasks?
- `task_type` (weight: 0.30) -- Is a specific task type driving the increase?
- `task_catalog` (weight: 0.25) -- Is the increase concentrated in one project?

**Verification Queries:**

```sql
-- By owner_name
SELECT owner_name, COUNT(*) AS task_count,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds IN (TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd'), TO_CHAR(GETDATE(), 'yyyymmdd'))
GROUP BY owner_name
ORDER BY cu_hours DESC
LIMIT 10;

-- By task_type
SELECT task_type, COUNT(*) AS task_count,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds IN (TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd'), TO_CHAR(GETDATE(), 'yyyymmdd'))
GROUP BY task_type
ORDER BY cu_hours DESC;

-- By task_catalog
SELECT task_catalog, COUNT(*) AS task_count,
       SUM(cost_cpu) / 100.0 / 3600 AS cu_hours
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds IN (TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd'), TO_CHAR(GETDATE(), 'yyyymmdd'))
GROUP BY task_catalog
ORDER BY cu_hours DESC
LIMIT 10;
```

**Judgment Rules:**
- **Support hypothesis:** If cost proportion change for a specific dimension value exceeds 20%
- **Refute hypothesis:** If all dimension values show stable cost distribution (change < 5%)

**Recommended Actions:**
- Check {{primary_dimension}} task queue for abnormal tasks
- Consider setting cost alert thresholds for {{primary_dimension}}

## 2. Storage Spike Analysis (storage_spike)

**Trigger:** Total storage increased by 30%+ compared to baseline.

**Hypothesis Dimensions:**
- `table_name` (weight: 0.50) -- Which table grew the most?
- `owner_name` (weight: 0.35) -- Which owner's tables grew?
- `table_catalog` (weight: 0.15) -- Is the growth in one project?

**Verification Queries:**

```sql
-- Top growing tables
SELECT table_name, owner_name, COALESCE(data_length, 0) / 1024 / 1024 / 1024 AS size_gb,
       lifecycle
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
WHERE table_type = 'MANAGED_TABLE'
ORDER BY COALESCE(data_length, 0) DESC
LIMIT 20;

-- Storage by owner
SELECT owner_name,
       COUNT(*) AS table_count,
       SUM(COALESCE(data_length, 0)) / 1024 / 1024 / 1024 AS total_tb
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLES
GROUP BY owner_name
ORDER BY total_tb DESC;
```

**Judgment Rules:**
- **Support hypothesis:** If storage proportion change for a specific dimension value exceeds 30%
- **Refute hypothesis:** If all dimension values show stable storage distribution

**Recommended Actions:**
- Check {{primary_dimension}} data import task frequency
- Consider setting lifecycle policies to clean up expired data

## 3. Job Failure Spike Analysis (job_failure_spike)

**Trigger:** Task failure rate increased by 15%+ compared to baseline.

**Hypothesis Dimensions:**
- `task_catalog` (weight: 0.40) -- Is failure concentrated in one project?
- `task_type` (weight: 0.35) -- Is a specific task type failing?
- `owner_name` (weight: 0.25) -- Is one user's jobs failing?

**Verification Queries:**

```sql
-- Failure rate by project
SELECT task_catalog,
       COUNT(*) AS total,
       SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) AS failed,
       SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS failure_rate
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
GROUP BY task_catalog
ORDER BY failed DESC;

-- Failure details
SELECT task_name, task_type, owner_name, start_time, result
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TASKS_HISTORY
WHERE ds = TO_CHAR(DATEADD(GETDATE(), -1, 'dd'), 'yyyymmdd')
  AND status = 'Failed'
ORDER BY start_time DESC;
```

**Recommended Actions:**
- Check {{primary_dimension}} resource configuration for adequacy
- Consider increasing {{primary_dimension}} compute resource quota

## 4. Partition Growth Analysis (partition_growth)

**Trigger:** Partition count increased by 50%+ on a table.

**Hypothesis Dimensions:**
- `table_name` -- Which tables have the most partitions?
- `partition_pattern` -- Are partitions following expected naming patterns?

**Verification Queries:**

```sql
-- Tables with most partitions
SELECT table_name,
       COUNT(*) AS partition_count,
       SUM(data_length) / 1024 / 1024 AS size_mb,
       MIN(partition_name) AS oldest_partition,
       MAX(partition_name) AS newest_partition
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.PARTITIONS
GROUP BY table_name
HAVING COUNT(*) > 5000
ORDER BY partition_count DESC;
```

**Recommendation Template:**
- Set lifecycle on partitioned tables to auto-expire old partitions
- Consider partition-level merges for small partitions
- Review partition creation scripts for unintended patterns

## 5. Permission Change Analysis (permission_change)

**Trigger:** Grant count changed by 25%+ compared to baseline.

**Hypothesis Dimensions:**
- `user_name` -- Who received new permissions?
- `privilege_type` -- What type of permissions changed?
- `table_name` -- Which tables had permission changes?

**Verification Queries:**

```sql
-- Permission distribution (active grants only)
SELECT user_name, privilege_type, COUNT(*) AS grant_count
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLE_PRIVILEGES
WHERE expired IS NULL OR expired > GETDATE()
GROUP BY user_name, privilege_type
ORDER BY grant_count DESC;

-- Tables with most grantees (active grants only)
SELECT table_name, COUNT(DISTINCT user_name) AS grantee_count
FROM SYSTEM_CATALOG.INFORMATION_SCHEMA.TABLE_PRIVILEGES
WHERE expired IS NULL OR expired > GETDATE()
GROUP BY table_name
ORDER BY grantee_count DESC
LIMIT 20;
```

**Recommendation Template:**
- Review recent grant activities for unexpected changes
- Ensure least-privilege principle is maintained
- Check for orphan users (users with permissions but no active roles)
