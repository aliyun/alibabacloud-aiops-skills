---
title: PolarDB-X CREATE TABLE (Table Types, Partition Strategies, and Management)
---

# PolarDB-X CREATE TABLE

PolarDB-X Distributed Edition supports three table types: single tables, broadcast tables, and partitioned tables. Partitioned tables are the default type, where data is horizontally split across multiple storage nodes (DN) according to partition rules.

## Three Table Types

### Single Table (SINGLE)

Data is stored on a single DN, suitable for small tables that don't require distribution.

```sql
CREATE TABLE config_tbl (
  id BIGINT PRIMARY KEY,
  key_name VARCHAR(64),
  value TEXT
) SINGLE;
```

### Broadcast Table (BROADCAST)

Data is fully replicated to every DN, suitable for small dictionary tables that need frequent JOINs.

```sql
CREATE TABLE region_dict (
  region_id INT PRIMARY KEY,
  region_name VARCHAR(64)
) BROADCAST;
```

### Partitioned Table (Default)

Data is distributed across multiple DNs according to partition rules, suitable for large business tables.

## First-Level Partition Types

### KEY Partition

Similar to MySQL's KEY partition, routes based on column value hashing. The most commonly used partition type:

```sql
CREATE TABLE t_order (
  order_id BIGINT PRIMARY KEY,
  user_id BIGINT,
  amount DECIMAL(10,2)
) PARTITION BY KEY(order_id) PARTITIONS 16;
```

Vector partition key (multi-column routing):

```sql
CREATE TABLE t_item (
  order_id BIGINT,
  item_id BIGINT,
  product_name VARCHAR(128),
  PRIMARY KEY (order_id, item_id)
) PARTITION BY KEY(order_id, item_id) PARTITIONS 16;
```

### HASH Partition

Supports partition functions that can compute on column values before hashing:

```sql
-- Hash by year
CREATE TABLE t_event (
  id BIGINT PRIMARY KEY,
  event_date DATE
) PARTITION BY HASH(YEAR(event_date)) PARTITIONS 8;

-- Hash by day (using TO_DAYS)
CREATE TABLE t_log (
  id BIGINT PRIMARY KEY,
  created_at DATETIME
) PARTITION BY HASH(TO_DAYS(created_at)) PARTITIONS 16;
```

Note: Vector partition keys do not support partition functions; for timezone-sensitive time columns, use `UNIX_TIMESTAMP()`.

### CO_HASH Partition

A PolarDB-X-specific joint hash partition where multiple columns participate in routing. An equality condition on any single column can achieve partition pruning:

```sql
CREATE TABLE t_order (
  order_id BIGINT,
  buyer_id BIGINT,
  seller_id BIGINT,
  PRIMARY KEY (order_id)
) PARTITION BY CO_HASH(
  RIGHT(order_id, 4),
  RIGHT(buyer_id, 4)
) PARTITIONS 16;
```

### RANGE / RANGE COLUMNS Partition

Partitions by range, suitable for time series or continuous numeric data:

```sql
CREATE TABLE t_sales (
  id BIGINT PRIMARY KEY,
  sale_date DATE,
  amount DECIMAL(10,2)
) PARTITION BY RANGE COLUMNS(sale_date) (
  PARTITION p2023 VALUES LESS THAN ('2024-01-01'),
  PARTITION p2024 VALUES LESS THAN ('2025-01-01'),
  PARTITION p2025 VALUES LESS THAN ('2026-01-01'),
  PARTITION pmax  VALUES LESS THAN MAXVALUE
);
```

### LIST / LIST COLUMNS Partition

Partitions by discrete value lists, suitable for enumeration-type fields:

```sql
CREATE TABLE t_regional_order (
  id BIGINT PRIMARY KEY,
  region VARCHAR(20),
  amount DECIMAL(10,2)
) PARTITION BY LIST COLUMNS(region) (
  PARTITION p_east VALUES IN ('shanghai', 'hangzhou', 'nanjing'),
  PARTITION p_north VALUES IN ('beijing', 'tianjin'),
  PARTITION p_south VALUES IN ('guangzhou', 'shenzhen')
);
```

## Secondary Partitions (SUBPARTITION)

PolarDB-X supports secondary partitions, where first-level and second-level partitions can be freely combined (49 combinations).

### Templated Secondary Partitions

All first-level partitions use the same secondary partition definition:

```sql
CREATE TABLE t_order_detail (
  id BIGINT PRIMARY KEY,
  order_date DATE,
  user_id BIGINT,
  amount DECIMAL(10,2)
) PARTITION BY RANGE COLUMNS(order_date)
  SUBPARTITION BY KEY(user_id) SUBPARTITIONS 4
(
  PARTITION p2024 VALUES LESS THAN ('2025-01-01'),
  PARTITION p2025 VALUES LESS THAN ('2026-01-01'),
  PARTITION pmax  VALUES LESS THAN MAXVALUE
);
```

### Non-Templated Secondary Partitions

Each first-level partition can have a different number of secondary partitions:

```sql
CREATE TABLE t_sales_detail (
  id BIGINT PRIMARY KEY,
  region VARCHAR(20),
  user_id BIGINT
) PARTITION BY LIST COLUMNS(region)
  SUBPARTITION BY KEY(user_id)
(
  PARTITION p_east VALUES IN ('shanghai', 'hangzhou') SUBPARTITIONS 8,
  PARTITION p_north VALUES IN ('beijing', 'tianjin') SUBPARTITIONS 4
);
```

## Partition Management Operations

```sql
-- Add partition (applicable to RANGE/LIST)
ALTER TABLE t_sales ADD PARTITION (
  PARTITION p2026 VALUES LESS THAN ('2027-01-01')
);

-- Drop partition
ALTER TABLE t_sales DROP PARTITION p2023;

-- Split partition (split one partition into multiple)
ALTER TABLE t_order SPLIT PARTITION p0 INTO (
  PARTITION p0a,
  PARTITION p0b
);

-- Merge partitions
ALTER TABLE t_order MERGE PARTITIONS p0a, p0b TO p0;

-- Move partition to a specific DN
ALTER TABLE t_order MOVE PARTITIONS p0 TO 'dn-1';
```

## Partition Key Selection Principles

- Choose columns from the **most frequent query conditions** as partition keys to avoid full-shard scans.
- Choose columns with **even data distribution** to avoid hotspot partitions.
- If there are multiple high-frequency query dimensions, use `CO_HASH` or create Global Secondary Indexes (GSI).
- Each table supports a **maximum of 8192 partitions**.

## Limitations

- Partition keys do not support JSON type columns.
- Partition keys do not support GEOMETRY type columns.
- Single-column HASH partitions can use partition functions; vector partition keys cannot.
- Secondary partitioned tables do not support SPLIT/MERGE/ADD/DROP SUBPARTITION.
