# SQL Reference

## Query Settings

For cluster information gathering queries, use these SETTINGS to ensure safe, optimized execution:
```sql
SETTINGS readonly = 1, max_execution_time = 300, max_threads = 1
```
- `readonly = 1`: Prevents accidental writes
- `max_execution_time = 300`: 5-minute timeout
- `max_threads = 1`: Reduces cluster load during information gathering

## 1. Cluster Information Queries

### 1.1 Database Information
```sql
SELECT
    name AS database_name,
    engine
FROM system.databases
WHERE name NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
FORMAT TabSeparatedWithNames
SETTINGS readonly = 1, max_execution_time = 300, max_threads = 1;
```

### 1.2 Table Information (Comprehensive)
```sql
SELECT
    table_name,
    engine,
    engine_full,
    if(engine IN ('Log', 'TinyLog', 'StripeLog', 'Join'), 'UNKNOWN', toString(part_count)) AS part_count,
    if(engine IN ('Log', 'TinyLog', 'StripeLog', 'Join'), 'UNKNOWN', toString(data_bytes)) AS data_bytes,
    if(engine IN ('Log', 'TinyLog', 'StripeLog', 'Join'), 'UNKNOWN', toString(write_speed_bytes_per_sec)) AS write_speed_bytes_per_sec
FROM
(
    SELECT
        c.table_name,
        c.engine,
        c.engine_full,
        c.part_count_of_one_shard AS part_count,
        c.byte_size_of_one_shard AS data_bytes,
        d.byte_size_3_day / 259200 AS write_speed_bytes_per_sec
    FROM
    (
        SELECT
            a.table_name,
            a.engine,
            a.engine_full,
            b.part_count AS part_count_of_one_shard,
            b.byte_size AS byte_size_of_one_shard
        FROM
        (
            SELECT
                concat('`', database, '`.`', name, '`') AS table_name,
                engine,
                engine_full
            FROM system.tables
            WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
        ) AS a
        LEFT JOIN
        (
            SELECT
                concat('`', database, '`.`', table, '`') AS table_name,
                count(1) AS part_count,
                sum(bytes_on_disk) AS byte_size
            FROM system.parts
            WHERE (database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')) AND (active = 1)
            GROUP BY table_name
        ) AS b ON a.table_name = b.table_name
    ) AS c
    LEFT JOIN
    (
        SELECT
            concat('`', database, '`.`', table, '`') AS table_name,
            sum(size_in_bytes) AS byte_size_3_day
        FROM system.part_log
        WHERE (database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')) AND (event_date >= today() - 3) AND (event_time > (now() - toIntervalDay(3))) AND (event_type = 'NewPart')
        GROUP BY table_name
    ) AS d ON c.table_name = d.table_name
) AS e
ORDER BY engine, table_name
FORMAT TabSeparatedWithNames
SETTINGS readonly = 1, max_execution_time = 300, max_threads = 1;
```

**Note:** `part_count`, `data_bytes`, and `write_speed_bytes_per_sec` show 'UNKNOWN' for Join and Log family engines (Log, TinyLog, StripeLog) since `system.parts` doesn't track their data. Use `SELECT count(*) FROM table` to get row counts for these engines.

---

## 2. INSERT FROM REMOTE Migration SQL

### 2.1 Schema Migration

```sql
-- List databases
SHOW databases;

-- Show database definition
SHOW CREATE DATABASE <DATABASE>; 

-- List tables in database
SHOW tables from <DATABASE>;

-- Get table definitions
SELECT concat(create_table_query, ';') 
FROM system.tables 
WHERE database='<DATABASE>';
```

### 2.2 Partition-Based Migration
Best for: Large tables with time-based partitioning

```sql
-- Pull from old cluster (new cluster version ≤23.8)
INSERT INTO <new_database>.<new_table> 
SELECT * 
FROM remote('<old_endpoint>', <old_database>.<old_table>, '<username>', '<password>') 
WHERE _partition_id = '<partition_id>'
SETTINGS max_execution_time = 0, max_bytes_to_read = 0, log_query_threads = 0, max_result_rows = 0;

-- Push to new cluster (all versions)
INSERT INTO FUNCTION remote('<new_endpoint>', '<DATABASE>', '<TABLE>', '<USERNAME>', '<PASSWORD>')
SELECT * FROM <DATABASE>.<TABLE>
WHERE _partition_id = '<partition_id>'
SETTINGS max_execution_time = 0, max_bytes_to_read = 0, log_query_threads = 0, max_result_rows = 0;

-- Clean up partition (if migration failed, retry)
ALTER TABLE <DATABASE>.<TABLE> DROP PARTITION '<PARTITION>';
```

### 2.3 Full Table Migration
Best for: Small tables (<20GB)

```sql
-- Pull from old cluster (new cluster version ≤23.8)
INSERT INTO <new_database>.<new_table> 
SELECT * 
FROM remote('<old_endpoint>', <old_database>.<old_table>, '<username>', '<password>') 
SETTINGS max_execution_time = 0, max_bytes_to_read = 0, log_query_threads = 0, max_result_rows = 0;

-- Push to new cluster (all versions)
INSERT INTO FUNCTION remote('<new_endpoint>', '<DATABASE>', '<TABLE>', '<USERNAME>', '<PASSWORD>')
SELECT * FROM <DATABASE>.<TABLE>
SETTINGS max_execution_time = 0, max_bytes_to_read = 0, log_query_threads = 0, max_result_rows = 0;

-- Clean up table (if migration failed, retry)
TRUNCATE TABLE <DATABASE>.<TABLE>;
```

---

## 3. Data Verification SQL

### 3.1 Table-Level Row Count
Use when:
- Engine is MergeTree or ReplicatedMergeTree (NOT Replacing/Aggregating/Collapsing variants)
- No DROP PARTITION, TRUNCATE, DELETE operations executed
- No TTL data cleanup

```sql
SELECT `database`, `table`, sum(rows) 
FROM cluster(`default`, `system`, `parts`) 
WHERE (`database` != 'system') AND (active = 1) 
GROUP BY (`database`, `table`) 
ORDER BY (`database`, `table`) ASC;
```

### 3.2 Partition-Level Row Count
Use when table-level count may not match due to data operations.

```sql
SELECT
    partition_id,
    sum(rows) AS rows
FROM cluster(<CLUSTER>, system, parts)
WHERE (active = 1) AND (database = '<DATABASE>') AND (`table` = '<TABLE>')
GROUP BY partition_id
ORDER BY partition_id ASC;
```

### 3.3 Accurate Count with FINAL
Use when above methods don't work (merging engines, data operations, TTL).

```sql
SELECT
    _partition_id,
    count(1) AS cnt
FROM <DATABASE>.<TABLE>
FINAL
WHERE (_partition_id >= '<MIN_PARTITION>') AND (_partition_id <= '<MAX_PARTITION>')
GROUP BY _partition_id;
```

### 3.4 Query Result Verification
Run on both old and new clusters; results should match.

```sql
WITH result AS (<YOUR_QUERY>) SELECT sum(cityHash64(*)) FROM result;
```

---

## 4. DDL Change Detection SQL

Check if there were DDL changes in the past 7 days (affects migration).

### Version ≥20.8
```sql
SELECT count(*) 
FROM clusterAllReplicas(default, system.query_log) 
WHERE `event_time` >= now() - interval 10080 minute 
    AND (type = 'QueryFinish' and is_initial_query = 1) 
    AND (
        (query_kind = 'Alter' and lower(query) not like '% update %' and lower(query) not like '% delete %') 
        OR (query_kind in ('Grant', 'Revoke')) 
        OR (query_kind in ('Create', 'Drop', 'Rename'))
    );
```

### Version >20.3 and <20.8
```sql
SELECT count(*) 
FROM clusterAllReplicas(default, system.query_log) 
WHERE `event_time` >= now() - interval 10080 minute 
    AND (type = 'QueryFinish' and is_initial_query = 1) 
    AND (
        (ProfileEvents.Values[indexOf(ProfileEvents.Names, 'SelectQuery')] != 1 
         and ProfileEvents.Values[indexOf(ProfileEvents.Names, 'InsertQuery')] != 1) 
        and (lower(query) not like '%grant %' and lower(query) not like '%revoke %') 
        and (lower(query) like '%alter %' and lower(query) not like '% update %' and lower(query) not like '% delete %')
    )
    OR (/* Grant/Revoke and Create/Drop patterns - see full SQL in source */);
```

### Version ≤20.3
Use similar pattern to >20.3 version (see source documentation for full SQL).

---

## 5. HTTP Access to ClickHouse

Use HTTP protocol when direct SQL client access is not available.

### Connection Parameters
- `HOST_NAME`: Cluster endpoint (e.g., `cc-xxx.clickhouse.rds.aliyuncs.com`)
- `HTTP_PORT`: HTTP port (default: `8123`)
- `USER_NAME`: Database username
- `PASSWORD`: Database password

### Credential Security Guidelines

⚠️ **IMPORTANT**: Never expose passwords directly in command line arguments. Use one of these secure methods:

**Method 1: Environment Variables (Recommended)**
```bash
# Set credentials as environment variables (add to ~/.bashrc or export in session)
export CLICKHOUSE_HOST="cc-xxx.clickhouse.rds.aliyuncs.com"
export CLICKHOUSE_PORT="8123"
export CLICKHOUSE_USER="your_username"
export CLICKHOUSE_PASSWORD="your_password"
```

**Method 2: Using netrc file**
```bash
# Create ~/.netrc file with restricted permissions
echo "machine ${CLICKHOUSE_HOST} login ${CLICKHOUSE_USER} password ${CLICKHOUSE_PASSWORD}" >> ~/.netrc
chmod 600 ~/.netrc
# Then use: curl --netrc ...
```

### Timeout Settings
Always use timeout settings to prevent hanging connections:
- `--connect-timeout 30`: Maximum time to wait for connection (30 seconds)
- `--max-time 300`: Maximum time for entire operation (300 seconds for queries, 60 seconds for ping)

### Connectivity Test
```bash
# Using environment variables (secure)
curl --connect-timeout 30 --max-time 60 \
  -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/ping"
```

### Get Database Information
```bash
echo "SELECT name AS database_name, engine FROM system.databases WHERE name NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA') FORMAT TabSeparatedWithNames SETTINGS readonly = 1, max_execution_time = 300, max_threads = 1;" | \
curl --connect-timeout 30 --max-time 300 \
  -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/" -d @-
```

### Get Table Information
```bash
cat << 'EOF' | curl --connect-timeout 30 --max-time 300 \
  -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/" -d @-
SELECT
    table_name,
    engine,
    engine_full,
    if(engine IN ('Log', 'TinyLog', 'StripeLog', 'Join'), 'UNKNOWN', toString(part_count)) AS part_count,
    if(engine IN ('Log', 'TinyLog', 'StripeLog', 'Join'), 'UNKNOWN', toString(data_bytes)) AS data_bytes,
    if(engine IN ('Log', 'TinyLog', 'StripeLog', 'Join'), 'UNKNOWN', toString(write_speed_bytes_per_sec)) AS write_speed_bytes_per_sec
FROM (
    SELECT 
        c.table_name, c.engine, c.engine_full,
        c.part_count_of_one_shard AS part_count,
        c.byte_size_of_one_shard AS data_bytes,
        d.byte_size_3_day / 259200 AS write_speed_bytes_per_sec
    FROM (
        SELECT a.table_name, a.engine, a.engine_full,
            b.part_count AS part_count_of_one_shard,
            b.byte_size AS byte_size_of_one_shard
        FROM (
            SELECT concat(database, '.', name) AS table_name, engine, engine_full
            FROM system.tables
            WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
        ) AS a
        LEFT JOIN (
            SELECT concat(database, '.', table) AS table_name, 
                count(1) AS part_count, sum(bytes_on_disk) AS byte_size
            FROM system.parts
            WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA') AND active = 1
            GROUP BY table_name
        ) AS b ON a.table_name = b.table_name
    ) AS c
    LEFT JOIN (
        SELECT concat(database, '.', table) AS table_name, 
            sum(size_in_bytes) AS byte_size_3_day
        FROM system.part_log
        WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA') 
            AND event_date >= today() - 3 AND event_time > now() - INTERVAL 3 DAY AND event_type = 'NewPart'
        GROUP BY table_name
    ) AS d ON c.table_name = d.table_name
) AS e
ORDER BY engine, table_name
FORMAT TabSeparatedWithNames
SETTINGS readonly = 1, max_execution_time = 300, max_threads = 1;
EOF
```

### Execute Any Query via HTTP
```bash
echo '<YOUR_SQL_QUERY>' | curl --connect-timeout 30 --max-time 300 \
  -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/" -d @-
```

---

## 6. Documentation Links

### Console Migration
- Community → Enterprise: https://help.aliyun.com/zh/clickhouse/user-guide/migrate-from-self-built-clickhouse-to-enterprise-edition
- Community → Community: https://help.aliyun.com/zh/clickhouse/user-guide/migrate-data-between-apsaradb-for-clickhouse-clusters
- Self-built → Community: https://help.aliyun.com/zh/clickhouse/user-guide/migrate-table-data-from-a-self-managed-clickhouse-cluster-to-an-apsaradb-for-clickhouse-cluster
- Self-built → Enterprise: https://help.aliyun.com/zh/clickhouse/user-guide/migrate-from-self-built-clickhouse-to-enterprise-edition
- Horizontal Scaling: https://help.aliyun.com/zh/clickhouse/user-guide/modify-the-configurations-of-an-apsaradb-for-clickhouse-cluster
- Disk Downgrade: https://help.aliyun.com/zh/clickhouse/user-guide/disk-downgrade
- AZ Switch: https://help.aliyun.com/zh/clickhouse/user-guide/modify-the-configurations-of-an-apsaradb-for-clickhouse-clusters

### Compatibility Verification
- https://help.aliyun.com/zh/clickhouse/user-guide/analysis-and-solution-of-cloud-compatibility-and-performance-bottleneck-of-self-built-clickhouse
