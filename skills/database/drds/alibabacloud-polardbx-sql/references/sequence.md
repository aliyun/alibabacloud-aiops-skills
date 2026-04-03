---
title: PolarDB-X Sequence
---

# PolarDB-X Sequence

Sequences in PolarDB-X generate globally unique numeric sequences, primarily used for primary key or unique index columns. In distributed scenarios, Sequences replace MySQL's AUTO_INCREMENT to provide global uniqueness guarantees.

## Sequence Types

### NEW SEQUENCE (Default, Recommended)

Introduced in version 5.4.14, this is the current **default Sequence type**. Key characteristics:

- **Sequential auto-increment**: Values generated within a single connection are strictly consecutive and increasing. Across connections, values also tend to increase (unlike GROUP SEQUENCE's batch segment allocation, there are no large gaps).
- **Globally unique**: Guarantees global uniqueness in distributed environments.
- **Persistence-based**: Value allocation is based on underlying storage nodes. After instance restart, allocation continues from the last position without loss or duplication.
- **High performance**: Internal caching mechanism ensures allocation efficiency, approaching GROUP SEQUENCE performance levels.
- **Customizable**: Supports START WITH, INCREMENT BY, MAXVALUE, CYCLE parameters (customization features require 5.4.17+).

```sql
-- Default creation (equivalent to CREATE NEW SEQUENCE)
CREATE SEQUENCE order_seq;

-- With parameters
CREATE NEW SEQUENCE order_seq
  START WITH 1
  INCREMENT BY 1
  MAXVALUE 9999999999
  NOCYCLE;
```

### GROUP SEQUENCE (Legacy Default Type)

Fetches ID segments in batch from the database and caches them in memory for allocation. High performance. Each node independently caches an ID segment, so **values allocated across nodes are not continuous** (e.g., Node A allocates 1-10000, Node B allocates 10001-20000). Starting value is 100001.

```sql
CREATE GROUP SEQUENCE user_id_seq;

-- With starting value
CREATE GROUP SEQUENCE user_id_seq START WITH 200001;
```

For unit-based deployment using UNIT COUNT / INDEX:

```sql
CREATE GROUP SEQUENCE user_id_seq
  START WITH 100001
  UNIT COUNT 3 INDEX 0;
```

### SIMPLE SEQUENCE

Supports custom step, maximum value, and cycling. Functionality has been superseded by NEW SEQUENCE; not recommended for new use cases:

```sql
CREATE SIMPLE SEQUENCE legacy_seq
  START WITH 1000
  INCREMENT BY 2
  MAXVALUE 99999999
  CYCLE;
```

### TIME SEQUENCE

Generates unique IDs based on timestamps. The column type must be BIGINT:

```sql
CREATE TIME SEQUENCE ts_seq;
```

## Explicit Sequence Usage

### Get Values

```sql
-- Get a single value
SELECT order_seq.NEXTVAL FROM DUAL;

-- Get 10 values in batch
SELECT order_seq.NEXTVAL FROM DUAL WHERE COUNT = 10;
```

### Use in INSERT

```sql
INSERT INTO t_order (order_id, buyer_id, amount)
VALUES (order_seq.NEXTVAL, 12345, 99.90);
```

### View All Sequences

```sql
SHOW SEQUENCES;
```

## Implicit Sequence

When a table column is defined with `AUTO_INCREMENT`, PolarDB-X automatically associates an implicit Sequence. Users don't need to create or manage it manually.

```sql
CREATE TABLE t_user (
  user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64)
) PARTITION BY KEY(user_id) PARTITIONS 16;
```

Note: The implicit Sequence type depends on the instance version. Version 5.4.14+ defaults to NEW SEQUENCE, where AUTO_INCREMENT is strictly consecutive within a single connection and tends to increase across connections. Versions before 5.4.14 default to GROUP SEQUENCE, where values allocated across nodes are not continuous.

## Modify and Drop Sequences

```sql
-- Modify parameters
ALTER SEQUENCE order_seq START WITH 500000 INCREMENT BY 5;

-- Change type (START WITH must be specified)
ALTER SEQUENCE order_seq CHANGE TO SIMPLE START WITH 1000000;

-- Drop
DROP SEQUENCE order_seq;
```

## Limitations

- Maximum **16384 Sequences** per database.
- NEW SEQUENCE requires version 5.4.14+; customization features require 5.4.17+.
- GROUP SEQUENCE starts at 100001; cannot start from 1.
- TIME SEQUENCE columns must be BIGINT type.
- Unit-based GROUP SEQUENCE does not support type conversion.
