---
title: PolarDB-X Distributed Transactions
---

# PolarDB-X Distributed Transactions

PolarDB-X Distributed Edition implements distributed transactions based on TSO (Timestamp Oracle) global clock + MVCC (Multi-Version Concurrency Control) + 2PC (Two-Phase Commit), guaranteeing ACID properties for cross-shard transactions.

## Transaction Model

- **TSO Global Clock**: A central timestamp node provides globally monotonically increasing timestamps to ensure distributed consistent reads.
- **MVCC**: Multi-version concurrency control where read operations are based on snapshot timestamps and never read intermediate states.
- **2PC**: Write operations spanning multiple DNs use two-phase commit to guarantee atomicity.

## Isolation Levels

PolarDB-X supports the following isolation levels:

- **READ COMMITTED (RC)**: Default isolation level. Each statement reads the latest committed data.
- **REPEATABLE READ (RR)**: A snapshot is taken at transaction start; reads are consistent throughout the transaction.

```sql
-- View current isolation level
SELECT @@transaction_isolation;

-- Set isolation level
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
```

## Transaction Syntax

```sql
-- Start transaction
BEGIN;
-- or
START TRANSACTION;

-- Commit
COMMIT;

-- Rollback
ROLLBACK;

-- SAVEPOINT
SAVEPOINT sp1;
ROLLBACK TO SAVEPOINT sp1;
RELEASE SAVEPOINT sp1;
```

## Single-Shard Transaction Optimization

When all operations in a transaction fall on the **same shard**, PolarDB-X automatically optimizes it to a local transaction (1PC), avoiding the overhead of 2PC. When designing partitioned tables, try to keep operations within the same transaction on the same shard to significantly improve performance.

## Relationship with GSI

Write operations on Global Secondary Indexes (GSI) need to update both the primary table and the index table (which may be on different shards), so correct GSI operation depends on distributed transaction support (XA/TSO).

## Considerations

- **Avoid long transactions**: Long transactions hold locks for extended periods, affecting concurrent performance and blocking MVCC version cleanup.
- **Cross-shard transaction overhead**: Cross-shard transactions require 2PC coordination and perform worse than single-shard transactions. Design to keep high-frequency transaction operations within the same shard.
- **Large transaction limits**: Modifying too much data in a single transaction may trigger memory limits. Batch data operations should be committed in batches.
