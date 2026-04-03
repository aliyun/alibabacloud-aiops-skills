---
title: PolarDB-X Primary Keys and Unique Keys (AUTO Mode)
---

# Primary Keys and Unique Keys

In PolarDB-X Distributed Edition AUTO mode, primary keys and unique keys are classified as **Global** (globally unique) or **Local** (unique within partition) based on their relationship with partition columns. Understanding this distinction is critical for correct table design and avoiding data consistency issues.

## Primary Key Classification

### Global Primary Key

Guarantees global uniqueness. Primary keys in the following scenarios are Global:

- **Single tables and broadcast tables**: Primary keys are always globally unique.
- **Manual partitioned tables**: When the primary key columns **include all partition columns**, it is a Global primary key.

```sql
-- Single table: Global primary key
CREATE TABLE single_tbl(
  id bigint NOT NULL AUTO_INCREMENT,
  name varchar(30),
  PRIMARY KEY(id)
) SINGLE;

-- Broadcast table: Global primary key
CREATE TABLE brd_tbl(
  id bigint NOT NULL AUTO_INCREMENT,
  name varchar(30),
  PRIMARY KEY(id)
) BROADCAST;

-- Manual partitioned table: PK (id, name, addr) includes all partition columns (id, addr) -> Global PK
CREATE TABLE key_tbl(
  id bigint,
  name varchar(10),
  addr varchar(30),
  PRIMARY KEY(id, name, addr)
) PARTITION BY KEY(id, addr);
```

### Local Primary Key

Only guarantees uniqueness within a partition, **cannot guarantee global uniqueness**. Occurs in manual partitioned tables where the primary key columns **do not include all partition columns**.

```sql
-- Manual partitioned table: PK (order_id) does not include partition column (city) -> Local PK
CREATE TABLE list_tbl(
  order_id bigint,
  city varchar(50),
  name text,
  PRIMARY KEY(order_id)
) PARTITION BY LIST(city)
(
  PARTITION p1 VALUES IN ("Beijing"),
  PARTITION p2 VALUES IN ("Shanghai"),
  PARTITION p3 VALUES IN ("Guangzhou"),
  PARTITION p4 VALUES IN ("Shenzhen"),
  PARTITION p5 VALUES IN(DEFAULT)
);
```

**Local primary key risks**: Different partitions can have the same primary key value.

```sql
-- Insert into p1 partition (Beijing)
INSERT INTO list_tbl(order_id, city, name) VALUES (10001, "Beijing", "phone");
-- Query OK

-- Same order_id, same partition -> Primary key conflict (within-partition uniqueness works)
INSERT INTO list_tbl(order_id, city, name) VALUES (10001, "Beijing", "book");
-- ERROR: Duplicate entry '10001' for key 'PRIMARY'

-- Same order_id, different partition (Shenzhen) -> Succeeds, global primary key duplication!
INSERT INTO list_tbl(order_id, city, name) VALUES (10001, "Shenzhen", "camera");
-- Query OK

SELECT * FROM list_tbl;
-- order_id=10001 appears in two records, in Beijing and Shenzhen partitions respectively
```

**Local primary key DDL issues**: When executing partition strategy changes that cause duplicate primary key data to fall into the same partition, the DDL will fail.

```sql
ALTER TABLE list_tbl
PARTITION BY LIST (city)
(
  PARTITION p1 VALUES IN ("Beijing", "Shenzhen"),  -- Two order_id=10001 rows merged into same partition
  PARTITION p2 VALUES IN ("Shanghai"),
  PARTITION p3 VALUES IN ("Guangzhou"),
  PARTITION p5 VALUES IN(DEFAULT)
);
-- ERROR: Duplicated entry '10001' for key 'PRIMARY'
```

## Unique Key Classification

### Global Unique Key

Guarantees global uniqueness. Unique keys in the following scenarios are Global:

- **Single tables and broadcast tables**: Unique keys are always globally unique.
- **Manual partitioned tables**: When the unique key columns **include all partition columns**, it is a Global unique key.
- **UNIQUE GLOBAL INDEX**: Achieves global uniqueness via a Global Secondary Index.

```sql
-- Manual partitioned table: UK (inner_id, type_id) includes partition column (type_id) -> Global UK
CREATE TABLE hash_tbl(
  type_id int,
  inner_id int,
  UNIQUE KEY(inner_id, type_id)
) PARTITION BY HASH(type_id);

-- Manual partitioned table: Achieves Global UK via UNIQUE GLOBAL INDEX
CREATE TABLE key_tbl(
  type_id int,
  serial_id int,
  UNIQUE GLOBAL INDEX u_sid(serial_id) PARTITION BY HASH(serial_id)
) PARTITION BY HASH(type_id);
```

### Local Unique Key

Only guarantees uniqueness within a partition, **cannot guarantee global uniqueness**. Occurs in manual partitioned tables where the unique key columns **do not include all partition columns**.

```sql
-- Manual partitioned table: UK (serial_id) does not include partition column (order_time) -> Local UK
CREATE TABLE range_tbl(
  id int primary key auto_increment,
  serial_id int,
  order_time datetime NOT NULL,
  UNIQUE KEY(serial_id)
) PARTITION BY RANGE(order_time)
(
  PARTITION p1 VALUES LESS THAN ('2022-12-31'),
  PARTITION p2 VALUES LESS THAN ('2023-12-31'),
  PARTITION p3 VALUES LESS THAN (MAXVALUE)
);
```

**Local unique key risks**: Similar to Local primary keys, different partitions can have the same unique key value.

```sql
INSERT INTO range_tbl(serial_id, order_time) VALUES (20001, '2022-01-01');
-- Query OK (p1 partition)

INSERT INTO range_tbl(serial_id, order_time) VALUES (20001, '2022-01-02');
-- ERROR: Duplicate entry '20001' for key 'serial_id' (within-partition uniqueness works)

INSERT INTO range_tbl(serial_id, order_time) VALUES (20001, '2024-01-01');
-- Query OK (p3 partition, different partition -> global unique key duplication!)
```

**Local unique key DDL issues**: When converting a manual partitioned table to a single table, redistribution will fail if duplicate unique key values exist.

```sql
ALTER TABLE range_tbl SINGLE;
-- ERROR: Duplicated entry for key 'PRIMARY'
```

## Quick Reference for Classification Rules

| Table Type | PK/UK Includes All Partition Columns | Classification |
| ------------ | ----------------------------- | ------------------- |
| Single table | - | Global |
| Broadcast table | - | Global |
| Manual partitioned table | Yes | Global |
| Manual partitioned table | No | Local (unique within partition) |
| UNIQUE GLOBAL INDEX | - | Global |

## Recommendations and Considerations

1. **Prefer Global primary/unique keys**: Ensure primary and unique keys include all partition columns when designing tables.
2. **Local primary key scenarios**: If the business genuinely requires a Local primary key, use `AUTO_INCREMENT` or Sequence for system-generated primary key values to avoid manually specifying primary key values from the business side.
3. **Local unique key scenarios**: The business side should take measures to ensure global uniqueness of unique key values.
4. **Data synchronization note**: If a table has duplicate primary key values due to Local primary keys, when syncing to downstream systems (e.g., AnalyticDB MySQL), set the downstream primary key to the full set of "PolarDB-X table's primary key columns + partition columns" to avoid conflicts.
5. **Converting Local PK to globally unique**: Use Sequence to generate unique values as primary key values; see `sequence.md`.
6. **No special syntax needed for Global PK/UK**: Use the same syntax as MySQL; just ensure the classification conditions above are met.
