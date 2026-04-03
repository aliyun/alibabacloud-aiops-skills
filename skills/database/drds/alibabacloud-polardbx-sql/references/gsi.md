---
title: PolarDB-X Global Secondary Index (GSI)
---

# PolarDB-X Global Secondary Index (GSI)

A Global Secondary Index (GSI) is a special partitioned table in PolarDB-X that stores redundant copies of selected columns from the primary table, distributed across storage nodes according to a specified partition scheme. The core purpose of GSI is to solve **full-shard scan issues caused by non-partition-key queries**.

## Three GSI Types

### Global Secondary Index (GSI)

Provides a different partition scheme from the primary table. The index table contains only the index columns, primary key columns, and the primary table's partition key:

```sql
CREATE TABLE t_order (
  order_id BIGINT PRIMARY KEY,
  buyer_id BIGINT,
  seller_id BIGINT,
  order_snapshot TEXT,
  GLOBAL INDEX g_i_buyer(buyer_id) PARTITION BY KEY(buyer_id) PARTITIONS 16
) PARTITION BY KEY(order_id) PARTITIONS 16;
```

### Global Unique Index (UGSI)

Adds a global uniqueness constraint on top of GSI, ensuring the index key is unique across the entire table:

```sql
CREATE TABLE t_user (
  user_id BIGINT PRIMARY KEY,
  phone VARCHAR(20),
  name VARCHAR(64),
  UNIQUE GLOBAL INDEX g_i_phone(phone) PARTITION BY KEY(phone) PARTITIONS 16
) PARTITION BY KEY(user_id) PARTITIONS 16;
```

### Clustered Global Index (Clustered GSI)

Stores all columns from the primary table by default, avoiding table lookback queries at the cost of storage space equal to the primary table:

```sql
CREATE TABLE t_order (
  order_id BIGINT PRIMARY KEY,
  buyer_id BIGINT,
  seller_id BIGINT,
  order_info TEXT,
  create_time DATETIME,
  CLUSTERED INDEX cg_i_buyer(buyer_id) PARTITION BY KEY(buyer_id) PARTITIONS 16
) PARTITION BY KEY(order_id) PARTITIONS 16;
```

## Creation Methods

### Inline creation during table creation (recommended)

See the examples above for each type.

### Add to an existing table

```sql
-- Add a regular GSI
ALTER TABLE t_order ADD GLOBAL INDEX g_i_seller(seller_id)
  PARTITION BY KEY(seller_id) PARTITIONS 16;

-- Add a Global Unique Index
ALTER TABLE t_order ADD UNIQUE GLOBAL INDEX g_i_order_no(order_no)
  PARTITION BY KEY(order_no) PARTITIONS 16;

-- Add a Clustered Global Index
ALTER TABLE t_order ADD CLUSTERED INDEX cg_i_seller(seller_id)
  PARTITION BY KEY(seller_id) PARTITIONS 16;
```

### Using CREATE INDEX syntax

```sql
CREATE GLOBAL INDEX g_i_seller ON t_order(seller_id)
  PARTITION BY KEY(seller_id) PARTITIONS 16;
```

## Covering Columns (COVERING)

Use `COVERING` to specify additional redundant columns, reducing table lookback overhead:

```sql
CREATE TABLE t_order (
  order_id BIGINT PRIMARY KEY,
  buyer_id BIGINT,
  seller_id BIGINT,
  amount DECIMAL(10,2),
  status INT,
  GLOBAL INDEX g_i_buyer(buyer_id) COVERING(amount, status)
    PARTITION BY KEY(buyer_id) PARTITIONS 16
) PARTITION BY KEY(order_id) PARTITIONS 16;
```

The index table automatically includes the primary key columns and the primary table's partition key columns; no need to repeat them in COVERING.

## Query Usage

The PolarDB-X optimizer can automatically select GSIs, or you can specify them manually:

```sql
-- Using FORCE INDEX
SELECT * FROM t_order FORCE INDEX(g_i_buyer)
WHERE buyer_id = 12345;

-- Using HINT
SELECT /*+TDDL:INDEX(t_order, g_i_buyer)*/ *
FROM t_order WHERE buyer_id = 12345;
```

## Limitations

- Each table supports a maximum of **32 global indexes**.
- GSI requires **XA/TSO distributed transaction** support.
- Direct DML (INSERT/UPDATE/DELETE) or DDL on GSI index tables is prohibited.
- `TRUNCATE` on tables with GSI is prohibited; use `DELETE` to clear data instead.
- Before dropping a column included in a GSI, the corresponding GSI must be dropped first.
- GSI write performance has additional overhead (index table data must be kept consistent).
- Creating and dropping GSIs are online operations that do not block DML.

## Design Recommendations

- Prioritize creating GSIs for the **most frequent non-partition-key query conditions**.
- If queries need to return many columns, use **Clustered GSI** to avoid table lookback.
- If only a few additional columns are needed, **COVERING** is more storage-efficient than Clustered GSI.
- If global uniqueness constraints are needed (e.g., phone numbers, order numbers), use **UGSI**.
