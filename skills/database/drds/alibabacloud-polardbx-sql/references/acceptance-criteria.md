# Acceptance Criteria: alibabacloud-polardbx-sql

**Scenario**: PolarDB-X SQL writing, review, and adaptation
**Purpose**: Skill testing acceptance criteria

---

# Correct SQL Patterns

## 1. Version and Mode Verification

#### CORRECT
```sql
SELECT VERSION();
-- Expected output contains TDDL with version > 5.4.12, e.g., 5.7.25-TDDL-5.4.19-20251031

SHOW CREATE DATABASE db_name;
-- Expected output contains MODE = 'auto'
```

#### INCORRECT
```sql
-- Using PolarDB-X-specific syntax without verifying the version first
CREATE TABLE t1 (...) PARTITION BY KEY(id);
-- Error: Should first confirm the target instance is 2.0 Enterprise Edition + AUTO mode
```

## 2. CREATE TABLE Syntax — Table Type Selection

#### CORRECT
```sql
-- Broadcast table (small/dictionary tables)
CREATE TABLE dict_status (
  id INT PRIMARY KEY,
  name VARCHAR(50)
) BROADCAST;

-- Single table (no distribution needed)
CREATE TABLE config (
  id INT PRIMARY KEY,
  value TEXT
) SINGLE;

-- Partitioned table (default, KEY partition)
CREATE TABLE orders (
  id BIGINT AUTO_INCREMENT,
  user_id BIGINT,
  created_at DATETIME,
  PRIMARY KEY (id, user_id)
) PARTITION BY KEY(user_id) PARTITIONS 16;
```

#### INCORRECT
```sql
-- Error: Using broadcast table for a large table causes full data on every DN
CREATE TABLE huge_log_table (
  id BIGINT PRIMARY KEY,
  content TEXT
) BROADCAST;

```

## 3. Global Secondary Index GSI

#### CORRECT
```sql
-- Create GSI to solve non-partition-key queries
CREATE GLOBAL INDEX idx_order_status ON orders(order_status) PARTITION BY KEY(order_status);

-- Use Clustered GSI to cover more columns and avoid table lookback
CREATE CLUSTERED INDEX idx_order_user ON orders(user_id)
  PARTITION BY KEY(user_id) PARTITIONS 16;
```

#### INCORRECT
```sql
-- Error: Creating a regular index (LOCAL INDEX) cannot solve full-shard scans
CREATE INDEX idx_order_status ON orders(order_status);
-- When order_status is not the partition key, queries still scan all shards
```

## 4. Clustered Columnar Index CCI

#### CORRECT
```sql
-- Create CCI during table creation
CREATE TABLE analytics_data (
  id BIGINT AUTO_INCREMENT,
  event_time DATETIME,
  metric_value DECIMAL(10,2),
  PRIMARY KEY (id, event_time),
  CLUSTERED COLUMNAR INDEX cci_analytics(event_time)
) PARTITION BY KEY(id) PARTITIONS 16;
```

#### INCORRECT
```sql
-- Error: Creating CCI on a high-frequency single-row update OLTP table
-- CCI is designed for OLAP analytical queries, not high-frequency write scenarios
CREATE TABLE hot_write_table (
  id BIGINT PRIMARY KEY,
  counter INT,
  CLUSTERED COLUMNAR INDEX cci_counter(counter)
) PARTITION BY KEY(id);
```

## 5. Unsupported MySQL Features

#### CORRECT
```sql
-- Use standard JOIN instead of NATURAL JOIN
SELECT a.id, b.name
FROM table_a a
INNER JOIN table_b b ON a.id = b.a_id;

-- Rewrite HAVING subquery as JOIN
SELECT department, COUNT(*) as cnt
FROM employees e
JOIN (SELECT AVG(salary) as avg_sal FROM employees) t ON 1=1
GROUP BY department
HAVING cnt > t.avg_sal;
```

#### INCORRECT
```sql
-- Error: Using NATURAL JOIN (not supported by PolarDB-X)
SELECT * FROM table_a NATURAL JOIN table_b;

-- Error: Using STRAIGHT_JOIN (not supported by PolarDB-X)
SELECT STRAIGHT_JOIN * FROM t1 JOIN t2 ON t1.id = t2.id;

-- Error: Using := assignment operator (not supported by PolarDB-X)
SELECT @rownum := @rownum + 1 AS rank FROM t1;

-- Error: Subquery in HAVING (not supported by PolarDB-X)
SELECT department, COUNT(*) as cnt
FROM employees
GROUP BY department
HAVING cnt > (SELECT AVG(salary) FROM employees);

-- Error: Creating stored procedures (not supported by PolarDB-X)
CREATE PROCEDURE my_proc() BEGIN ... END;

-- Error: Creating triggers (not supported by PolarDB-X)
CREATE TRIGGER my_trigger BEFORE INSERT ON t1 FOR EACH ROW ...;
```

## 6. EXPLAIN Diagnostics

#### CORRECT
```sql
-- View logical execution plan
EXPLAIN SELECT * FROM orders WHERE user_id = 123;

-- Check for full-shard scans
EXPLAIN SHARDING SELECT * FROM orders WHERE order_status = 'pending';

-- View actual execution statistics
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123;

-- View physical execution plan pushed down to DN
EXPLAIN EXECUTE SELECT * FROM orders WHERE user_id = 123;
```

#### INCORRECT
```sql
-- Error: Using only EXPLAIN without EXPLAIN SHARDING cannot determine full-shard scans
-- EXPLAIN only shows the logical plan, not shard scan information
EXPLAIN SELECT * FROM orders WHERE order_status = 'pending';
-- Should use EXPLAIN SHARDING to check shard scan patterns
```

## 7. Sequence

#### CORRECT
```sql
-- Use NEW SEQUENCE (default type for 5.4.14+)
CREATE SEQUENCE my_seq START WITH 1 INCREMENT BY 1;

-- Use AUTO_INCREMENT during table creation (PolarDB-X automatically associates a Sequence)
CREATE TABLE t1 (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100)
) PARTITION BY KEY(id);
```

## 8. Distributed Transactions

#### CORRECT
```sql
-- PolarDB-X uses distributed transactions by default, no extra configuration needed
BEGIN;
UPDATE account SET balance = balance - 100 WHERE user_id = 1;
UPDATE account SET balance = balance + 100 WHERE user_id = 2;
COMMIT;

-- View current transaction policy
SHOW VARIABLES LIKE 'drds_transaction_policy';
```

#### INCORRECT
```sql
-- Error: Lowering transaction isolation level to READ UNCOMMITTED
-- PolarDB-X distributed transactions are based on TSO + MVCC; lowering isolation level is not recommended
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
```

## 9. Partition Design — Partition Key Selection

#### CORRECT
```sql
-- Correct: Select the primary key with high equality query ratio and high cardinality as partition key
-- account_id as the primary key has highest cardinality and no hotspots
ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 256;

-- Correct: Use SQL Insight data to analyze each field's query ratio, then select the best partition key
-- rather than relying on verbal descriptions from the business team
```

#### INCORRECT
```sql
-- Error: Selecting a field with low cardinality and obvious hotspots as partition key
-- base_account_id has only thousands of distinct values with obvious hotspots
ALTER TABLE account PARTITION BY HASH(base_account_id) PARTITIONS 256;

-- Error: Selecting a field with very few distinct values (e.g., gender, status) as partition key
ALTER TABLE user_info PARTITION BY HASH(gender) PARTITIONS 256;
```

## 10. Partition Design — GSI Selection

#### CORRECT
```sql
-- Correct: Create regular GSI for high-frequency non-partition-key fields with few returned rows
CREATE GLOBAL INDEX gsi_address ON account (address)
  PARTITION BY HASH(address) PARTITIONS 256;

-- Correct: Create Global Unique Index (UGSI) for unique key fields
CREATE GLOBAL UNIQUE INDEX ugsi_exchange_account_id
  ON account (exchange_account_id)
  PARTITION BY HASH(exchange_account_id) PARTITIONS 256;

-- Correct: One-to-many scenario (many records per value), use Clustered GSI to avoid table lookback
CREATE CLUSTERED INDEX cgsi_buyer ON t_order (buyer_id)
  PARTITION BY KEY(buyer_id) PARTITIONS 256;

-- Correct: Use INSPECT INDEX to check for redundant and unused GSIs
INSPECT INDEX;
```

#### INCORRECT
```sql
-- Error: Creating GSI on a very low cardinality field (e.g., gender, province with very few values)
CREATE GLOBAL INDEX gsi_gender ON user_info (gender)
  PARTITION BY HASH(gender) PARTITIONS 256;

-- Error: Creating GSI on time/date fields (local indexes usually suffice)
CREATE GLOBAL INDEX gsi_gmt_modified ON account (gmt_modified)
  PARTITION BY HASH(gmt_modified) PARTITIONS 256;

-- Error: Creating standalone GSI for a field that always appears combined with others, never alone
-- base_account_id always appears with kw_location or address in high-frequency SQL
CREATE GLOBAL INDEX gsi_base_account ON account (base_account_id)
  PARTITION BY HASH(base_account_id) PARTITIONS 256;

-- Error: Creating GSI for low-ratio SQL (e.g., only dozens of times per hour)
-- Don't obsess over "every query must hit the partition key or GSI"
CREATE GLOBAL INDEX gsi_account_type ON account (account_type)
  PARTITION BY HASH(account_type) PARTITIONS 256;
```

## 11. Single Table to Partitioned Table — Migration Workflow

> **Key principle**: The three-step method is only needed when the table has unique indexes on non-partition-key columns.
> If the partition key is the primary key and there are no other unique constraints, direct migration is safe.

### Case 1: No unique indexes on non-partition-key columns — Direct migration

When the partition key equals the primary key and there are no other unique indexes (e.g., order table partitioned by order_id),
uniqueness is naturally preserved. Direct migration is the correct approach.

#### CORRECT
```sql
-- Correct: Partition key = primary key, no other unique indexes → direct migration
-- buyer_id and seller_id are not unique, only need regular GSI
ALTER TABLE t_order PARTITION BY KEY(order_id) PARTITIONS 256;

CREATE CLUSTERED INDEX cg_i_buyer ON t_order (buyer_id)
  PARTITION BY KEY(buyer_id) PARTITIONS 256;
CREATE GLOBAL INDEX g_i_seller ON t_order (seller_id)
  PARTITION BY KEY(seller_id) PARTITIONS 256;
```

#### INCORRECT
```sql
-- Error: Unnecessarily using three-step method when there are no non-partition-key unique indexes
-- order_id is both the primary key and partition key, no uniqueness risk exists
ALTER TABLE t_order PARTITION BY KEY(order_id) PARTITIONS 1;  -- unnecessary intermediate step
CREATE CLUSTERED INDEX cg_i_buyer ON t_order (buyer_id)
  PARTITION BY KEY(buyer_id) PARTITIONS 256;
ALTER TABLE t_order PARTITION BY KEY(order_id) PARTITIONS 256;
-- The three-step method adds complexity without benefit here
```

### Case 2: Has unique indexes on non-partition-key columns — Three-step method required

When the table has unique indexes on columns other than the partition key (e.g., account table partitioned by account_id
but with a unique constraint on exchange_account_id), the three-step method is required to prevent uniqueness degradation.

#### CORRECT
```sql
-- Correct: Three-step method ensuring uniqueness constraints are never lost
-- account has a unique index on exchange_account_id which is NOT the partition key

-- Step 1: Convert to a partitioned table with 1 partition (unique keys remain globally unique)
ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 1;

-- Step 2: Create required global indexes and global unique indexes
CREATE GLOBAL UNIQUE INDEX ugsi_exchange_account_id
  ON account (exchange_account_id)
  PARTITION BY HASH(exchange_account_id) PARTITIONS 256;
CREATE GLOBAL INDEX gsi_address
  ON account (address)
  PARTITION BY HASH(address) PARTITIONS 256;

-- Step 3: Change to target partition count
ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 256;
```

#### INCORRECT
```sql
-- Error: Directly changing to target partition count then creating UGSI
-- During the interval between ALTER PARTITION and CREATE UGSI, uniqueness cannot be guaranteed
ALTER TABLE account PARTITION BY HASH(account_id) PARTITIONS 256;
-- At this point exchange_account_id's unique key has degraded to Local, duplicate data may be written!
CREATE GLOBAL UNIQUE INDEX ugsi_exchange_account_id
  ON account (exchange_account_id)
  PARTITION BY HASH(exchange_account_id) PARTITIONS 256;
-- If duplicate data was written during the interval, this statement will fail

-- Error: Creating a global index on a single table (single tables don't support GSI)
CREATE GLOBAL INDEX gsi_address ON account_single_table (address)
  PARTITION BY HASH(address) PARTITIONS 256;
-- ERROR: Single tables cannot create global indexes
```

## 12. Partition Algorithm and Partition Count Selection

#### CORRECT
```sql
-- Correct: Vast majority of workloads use single-level HASH/KEY + 256 partitions
CREATE TABLE orders (
  order_id BIGINT PRIMARY KEY,
  user_id BIGINT
) PARTITION BY KEY(order_id) PARTITIONS 256;

-- Correct: Order-type multi-dimensional queries use CO_HASH (alternative when high write volume makes GSI impractical)
CREATE TABLE t_order (
  order_id BIGINT PRIMARY KEY,
  buyer_id BIGINT,
  seller_id BIGINT
) PARTITION BY CO_HASH(
  RIGHT(order_id, 4),
  RIGHT(buyer_id, 4)
) PARTITIONS 256;

-- Correct: Use HASH + RANGE secondary partition for time-based data cleanup
CREATE TABLE t_log (
  id BIGINT PRIMARY KEY,
  user_id BIGINT,
  created_at DATE
) PARTITION BY HASH(user_id)
  SUBPARTITION BY RANGE COLUMNS(created_at)
  SUBPARTITIONS 4
(
  PARTITION p1 VALUES LESS THAN ('2025-01-01'),
  PARTITION p2 VALUES LESS THAN ('2026-01-01'),
  PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

#### INCORRECT
```sql
-- Error: Too few partitions, prone to data skew and may require repartition when scaling
CREATE TABLE orders (
  order_id BIGINT PRIMARY KEY,
  user_id BIGINT
) PARTITION BY KEY(order_id) PARTITIONS 4;

-- Error: Unnecessarily using multiple fields as HASH partition keys (pick the one with highest cardinality)
CREATE TABLE orders (
  order_id BIGINT,
  user_id BIGINT,
  PRIMARY KEY (order_id)
) PARTITION BY HASH(order_id, user_id) PARTITIONS 256;
```

## 13. Efficient Pagination Queries

#### CORRECT
```sql
-- Correct: Use Keyset pagination with auto-increment PK (AUTO mode, New Sequence)
-- First batch
SELECT * FROM t1 ORDER BY id LIMIT 1000;
-- Subsequent batches (last_id is the id of the last row from previous batch)
SELECT * FROM t1 WHERE id > 12345 ORDER BY id LIMIT 1000;

-- Correct: When sort columns may have duplicates, use tuple comparison (recommended)
SELECT * FROM t1
WHERE (gmt_create, id) > ('2025-01-01 00:00:00', 12345)
ORDER BY gmt_create, id
LIMIT 1000;

-- Correct: Equivalent expansion of tuple comparison
SELECT * FROM t1
WHERE gmt_create >= '2025-01-01 00:00:00'
  AND (gmt_create > '2025-01-01 00:00:00' OR id > 12345)
ORDER BY gmt_create, id
LIMIT 1000;

-- Correct: Create appropriate composite index for pagination queries
ALTER TABLE t1 ADD INDEX idx_page (gmt_create, id);

-- Correct: Pagination with filter conditions, index includes filter column
ALTER TABLE t1 ADD INDEX idx_page_c1 (c1, gmt_create, id);
SELECT * FROM t1
WHERE c1 = 'value' AND (gmt_create, id) > (?, ?)
ORDER BY gmt_create, id
LIMIT 1000;

-- Correct: Pagination queries must explicitly specify ORDER BY
SELECT * FROM t1 WHERE id > 12345 ORDER BY id LIMIT 1000;
```

#### INCORRECT
```sql
-- Error: Using LIMIT OFFSET for deep pagination, cost O(M+N), gets slower as you go deeper
SELECT * FROM t1 ORDER BY gmt_create LIMIT 1000000, 1000;
-- Must scan 1,001,000 records to return 1,000 rows

-- Error: When sort columns may have duplicates, using only > will lose data
SELECT * FROM t1
WHERE gmt_create > '2025-01-01 00:00:00'
ORDER BY gmt_create
LIMIT 1000;
-- If multiple records have gmt_create = '2025-01-01 00:00:00', some will be skipped

-- Error: When sort columns may have duplicates, using only >= will have duplicate data
SELECT * FROM t1
WHERE gmt_create >= '2025-01-01 00:00:00'
ORDER BY gmt_create
LIMIT 1000;
-- Records already returned in the previous batch will be returned again

-- Error: Pagination query without ORDER BY, return order is undefined
SELECT * FROM t1 WHERE id > 12345 LIMIT 1000;
-- In distributed databases, data return order from different shards is random, results are unreliable

-- Error: No index on pagination sort columns, each query requires full table scan and sort
SELECT * FROM t1
WHERE (gmt_create, id) > (?, ?)
ORDER BY gmt_create, id
LIMIT 1000;
-- Without a (gmt_create, id) composite index, performance is poor
```

## 14. Range Partition Auto-Add Partitions

#### CORRECT
```sql
-- Correct: Configure auto-add partitions for time-type Range partition table (add-only)
ALTER TABLE t_order
MODIFY TTL SET
  TTL_ENABLE = 'ON',
  TTL_CLEANUP = 'OFF',
  TTL_EXPR = `gmt_created`,
  TTL_PART_INTERVAL = INTERVAL(1, MONTH),
  ARCHIVE_TYPE = 'PARTITION',
  ARCHIVE_TABLE_PRE_ALLOCATE = 2;

-- Correct: Immediately trigger pre-creation after configuration, WITH TTL_CLEANUP='OFF' forces add-only
ALTER TABLE t_order CLEANUP EXPIRED DATA WITH TTL_CLEANUP = 'OFF';

-- Correct: Second-level Range subpartitions use ARCHIVE_TYPE = 'SUBPARTITION'
ALTER TABLE t_event
MODIFY TTL SET
  TTL_ENABLE = 'ON',
  TTL_CLEANUP = 'OFF',
  TTL_EXPR = `created_at`,
  TTL_PART_INTERVAL = INTERVAL(1, MONTH),
  ARCHIVE_TYPE = 'SUBPARTITION',
  ARCHIVE_TABLE_PRE_ALLOCATE = 2;

-- Correct: Range partition table primary key includes partition column
CREATE TABLE t_order (
  id BIGINT AUTO_INCREMENT,
  gmt_created DATETIME NOT NULL,
  PRIMARY KEY (id, gmt_created)
) PARTITION BY RANGE COLUMNS(`gmt_created`) (
  PARTITION p20250401 VALUES LESS THAN ('2025-04-01'),
  PARTITION p20250501 VALUES LESS THAN ('2025-05-01')
);
```

#### INCORRECT
```sql
-- Error: Not triggering pre-creation immediately after configuring auto-add, must wait for next day's scheduled task
ALTER TABLE t_order
MODIFY TTL SET
  TTL_ENABLE = 'ON',
  TTL_CLEANUP = 'OFF',
  TTL_EXPR = `gmt_created`,
  TTL_PART_INTERVAL = INTERVAL(1, MONTH),
  ARCHIVE_TYPE = 'PARTITION',
  ARCHIVE_TABLE_PRE_ALLOCATE = 2;
-- Missing: ALTER TABLE t_order CLEANUP EXPIRED DATA WITH TTL_CLEANUP = 'OFF';
-- Customer's table may only have initial partitions; without triggering, must wait until 02:00 next day

-- Error: Manual trigger without WITH TTL_CLEANUP='OFF', may accidentally drop old partitions
ALTER TABLE t_order CLEANUP EXPIRED DATA;
-- If the table's TTL_CLEANUP = 'ON', expired partitions will be dropped simultaneously
-- Should use: ALTER TABLE t_order CLEANUP EXPIRED DATA WITH TTL_CLEANUP = 'OFF';

-- Error: Using auto-add partitions with integer-type partition column (not supported)
ALTER TABLE t_int_range
MODIFY TTL SET
  TTL_ENABLE = 'ON',
  TTL_EXPR = `int_col`,
  ARCHIVE_TYPE = 'PARTITION';
-- Auto-add partitions only supports DATE/DATETIME/TIMESTAMP type partition columns

-- Error: Second-level Range subpartitions using ARCHIVE_TYPE = 'PARTITION'
ALTER TABLE t_event
MODIFY TTL SET
  TTL_ENABLE = 'ON',
  TTL_EXPR = `created_at`,
  ARCHIVE_TYPE = 'PARTITION';
-- Second-level subpartitions should use ARCHIVE_TYPE = 'SUBPARTITION'
```
