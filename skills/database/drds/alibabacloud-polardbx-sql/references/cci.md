---
title: PolarDB-X Clustered Columnar Index (CCI)
---

# PolarDB-X Clustered Columnar Index (CCI)

The Clustered Columnar Index (CCI) is a row-column hybrid storage capability provided by PolarDB-X Enterprise Edition. CCI is essentially a columnar clustered index based on object storage that stores all columns from the primary table by default in columnar format, designed to accelerate OLAP analytical queries.

## Applicable Scenarios

- Wide table multi-column aggregation queries (SUM/COUNT/AVG, etc.).
- Complex reports and data analysis.
- Scenarios requiring both OLTP and OLAP on the same data (HTAP).
- Combined with TTL tables for hot/cold data separation.

## Creation Syntax

### Create during table creation

```sql
CREATE TABLE t_order (
  order_id BIGINT PRIMARY KEY,
  buyer_id BIGINT,
  seller_id BIGINT,
  amount DECIMAL(10,2),
  create_time DATETIME,
  CLUSTERED COLUMNAR INDEX cci_seller(seller_id)
    PARTITION BY KEY(seller_id) PARTITIONS 16
) PARTITION BY KEY(order_id) PARTITIONS 16;
```

### Add to an existing table

```sql
-- Using CREATE INDEX
CREATE CLUSTERED COLUMNAR INDEX cci_buyer
  ON t_order(buyer_id)
  PARTITION BY KEY(buyer_id) PARTITIONS 16;

-- Using ALTER TABLE
ALTER TABLE t_order ADD CLUSTERED COLUMNAR INDEX cci_buyer(buyer_id)
  PARTITION BY KEY(buyer_id) PARTITIONS 16;
```

## Query Usage

The PolarDB-X optimizer can automatically select CCI for analytical queries, or you can specify it manually:

```sql
-- Automatic selection (optimizer decides based on cost model)
SELECT seller_id, SUM(amount) FROM t_order
GROUP BY seller_id ORDER BY SUM(amount) DESC LIMIT 10;

-- Manually specify CCI
SELECT /*+TDDL:FORCE_INDEX(t_order, cci_seller)*/ seller_id, SUM(amount)
FROM t_order GROUP BY seller_id;

-- Using FORCE INDEX
SELECT seller_id, SUM(amount) FROM t_order FORCE INDEX(cci_seller)
GROUP BY seller_id;
```

## View CCI Information

```sql
SHOW COLUMNAR INDEX;
```

## Relationship with GSI

CCI is essentially the columnar version of Clustered GSI:
- **Clustered GSI**: Row-store format, suitable for point queries and small range scans.
- **CCI**: Columnar format, suitable for large range scans and aggregation analysis.

Both store all primary table columns by default, but differ in storage format and applicable query types.

## Combined with TTL Tables

CCI can be combined with TTL tables for hot/cold data separation: hot data resides in the row-store partitioned table, while cold data is archived to the columnar CCI (based on object storage), reducing storage costs while retaining analytical query capabilities.

## Limitations

- Only supported by PolarDB-X **Enterprise Edition (Distributed Edition)**.
- CCI data is stored on object storage; writes have some latency (eventually consistent).
- Creating CCI is an online operation that does not block DML.
