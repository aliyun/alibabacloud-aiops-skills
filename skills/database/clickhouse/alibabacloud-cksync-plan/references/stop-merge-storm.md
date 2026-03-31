# How To Stop Merge Storm

After cksync completes synchronization, all pending merges will start simultaneously. This guide explains how to identify large tables and configure merge settings to control the merge storm.

## Step 1: Analyze Part Details Per Table

Run the following SQL to observe part size distribution for each table:

```sql
WITH (
    SELECT sum(data_compressed_bytes) AS total_cmp_size
    FROM system.parts
    WHERE (active = 1) AND (database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA'))
) AS total_cmp_size
SELECT
    database,
    table,
    count() AS part_cnt,
    countDistinct(partition_id) AS partition_cnt,
    arrayMap(x -> round(x), quantiles(0.05, 0.1, 0.3, 0.5, 0.99)((data_uncompressed_bytes / 1024) / 1024)) AS p05_10_30_50_99_uncmp_part_mb,
    sum(data_uncompressed_bytes) AS uncmp_total_bytes,
    formatReadableSize(uncmp_total_bytes) AS uncmp_total_size,
    arrayMap(x -> round(x), quantiles(0.05, 0.1, 0.3, 0.5, 0.99)((data_compressed_bytes / 1024) / 1024)) AS p05_10_30_50_99_cmp_part_mb,
    formatReadableSize(sum(data_compressed_bytes)) AS cmp_total_size,
    (sum(data_compressed_bytes) / total_cmp_size) * 100 AS cmp_size_percent
FROM system.parts
WHERE (active = 1) AND (database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA'))
GROUP BY
    database,
    table
ORDER BY uncmp_total_bytes DESC
LIMIT 10;
```

**Output Columns Explained:**
| Column | Description |
|--------|-------------|
| `part_cnt` | Total number of active parts |
| `partition_cnt` | Number of distinct partitions |
| `p05_10_30_50_99_uncmp_part_mb` | Percentile distribution (5th, 10th, 30th, 50th, 99th) of uncompressed part sizes in MB |
| `uncmp_total_size` | Total uncompressed data size |
| `p05_10_30_50_99_cmp_part_mb` | Percentile distribution of compressed part sizes in MB |
| `cmp_total_size` | Total compressed data size |
| `cmp_size_percent` | Percentage of total cluster storage |

## Step 2: Identify Target Tables and Calculate Merge Memory

**Identify Target Tables:**
- Focus on tables with highest `cmp_size_percent` values
- Typically, top 5 tables account for ~95% of total storage
- Controlling these tables effectively stops most merge activity

**Calculate Required Merge Memory:**
- Check the `p05_10_30_50_99_uncmp_part_mb` column (10th percentile - p10)
- If p10 uncompressed part size is ≥500MB, most parts (>90%) exceed 500MB when uncompressed
- Merging two parts requires memory ≥ sum of both parts' uncompressed sizes
- **Rule of thumb:** Set merge memory limit to `2 × p10 uncompressed part size`

**Example:**
- If p10 = 500MB, set merge memory limit to ~1GB (1,073,741,824 bytes)
- This prevents old/large parts from merging while allowing small new parts to merge

## Step 3: Configure Merge Memory Settings

**SQL to limit merge memory per table:**

```sql
-- Replace $DATABASE, $TABLE, and $MERGE_MAX_BYTES with actual values
ALTER TABLE `$DATABASE`.`$TABLE` ON CLUSTER default 
MODIFY SETTING 
    max_bytes_to_merge_at_max_space_in_pool = $MERGE_MAX_BYTES,
    max_bytes_to_merge_at_min_space_in_pool = 1048576;
```

**Parameters:**
| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| `max_bytes_to_merge_at_max_space_in_pool` | Maximum bytes to merge when memory pool is full | `2 × p10 uncompressed part size` (e.g., 1073741824 for 1GB) |
| `max_bytes_to_merge_at_min_space_in_pool` | Minimum bytes allowed for merge | 1048576 (1MB) - allows tiny parts to still merge |

**Example with actual values:**

```sql
-- For a table where p10 uncompressed = 500MB, set limit to 1GB
ALTER TABLE `default`.`large_table` ON CLUSTER default 
MODIFY SETTING 
    max_bytes_to_merge_at_max_space_in_pool = 1073741824,
    max_bytes_to_merge_at_min_space_in_pool = 1048576;
```

## Step 4: Gradually Restore Merge Settings (After Stabilization)

After the post-sync merge storm subsides and system resources stabilize, **gradually increase** the merge limit instead of immediately restoring to a large value.

**Recommended Approach:**
1. Start by doubling the current limit
2. Monitor CPU, memory, and I/O for 1-2 hours
3. If stable, double again
4. Repeat until reaching target value

**Target Values:**
| Business Type | Recommended Final Value | Bytes |
|---------------|------------------------|-------|
| General business | ≤ 10 GB | 10,737,418,240 |
| Very large data volume (rare) | ≤ 30 GB | 32,212,254,720 |

> **Note:** Most businesses do NOT need values larger than 10GB. Only consider 30GB for exceptionally large datasets.

**Example: Gradual Restoration**

```sql
-- Step 1: Current limit is 1GB, double to 2GB
ALTER TABLE `$DATABASE`.`$TABLE` ON CLUSTER default 
MODIFY SETTING max_bytes_to_merge_at_max_space_in_pool = 2147483648;

-- Step 2: After 1-2 hours if stable, increase to 4GB
ALTER TABLE `$DATABASE`.`$TABLE` ON CLUSTER default 
MODIFY SETTING max_bytes_to_merge_at_max_space_in_pool = 4294967296;

-- Step 3: Continue doubling until reaching target (e.g., 10GB)
ALTER TABLE `$DATABASE`.`$TABLE` ON CLUSTER default 
MODIFY SETTING max_bytes_to_merge_at_max_space_in_pool = 10737418240;
```

## Common Merge Memory Values

| Uncompressed p10 Size | Recommended `max_bytes_to_merge_at_max_space_in_pool` |
|-----------------------|-------------------------------------------------------|
| 256 MB | 536870912 (512 MB) |
| 500 MB | 1073741824 (1 GB) |
| 1 GB | 2147483648 (2 GB) |
| 2 GB | 4294967296 (4 GB) |

## Notes

- Apply settings to **all nodes** in the cluster using `ON CLUSTER default`
- For Enterprise Edition, `ON CLUSTER` is not needed
- Monitor CPU, memory, and I/O after applying settings to verify effectiveness
- These settings only affect new merge operations; running merges will continue until completion
