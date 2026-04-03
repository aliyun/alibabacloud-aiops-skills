---
title: PolarDB-X and MySQL Compatibility Notes
---

# PolarDB-X and MySQL Compatibility Notes

PolarDB-X Distributed Edition (Enterprise Edition) is highly compatible with MySQL protocol and syntax, but due to distributed architecture differences, some features are unsupported or behave differently. Use this as a checklist when migrating MySQL SQL to PolarDB-X.

## Detecting PolarDB-X Version

```sql
SELECT VERSION();
```

Distinguish instance types by the return value:

| Return Value Example | Instance Type | MySQL Compatibility |
|-----------|---------|-------------|
| `5.7.25-TDDL-5.4.19-20251031` | **2.0 Enterprise Edition (Distributed Edition)** | Highly compatible, with differences listed in this document |
| `5.6.29-TDDL-5.4.12-16327949` | **DRDS 1.0** (version <= 5.4.12) | Legacy version, this document does not apply |
| `8.0.32-X-Cluster-8.4.20-20251017` | **2.0 Standard Edition** | 100% MySQL compatible, no need for this document |

- Contains `TDDL` with version > 5.4.12 -> 2.0 Enterprise Edition, version number is the part after `TDDL-` (e.g., `5.4.19`).
- Contains `TDDL` with version <= 5.4.12 -> DRDS 1.0, this skill does not apply.
- Contains `X-Cluster` -> 2.0 Standard Edition, handle with standard MySQL syntax.

## Unsupported MySQL Features (Do not generate by default)

- Stored Procedures and Stored Functions
- Triggers
- Event Scheduler (Events)
- User-Defined Functions (UDF)
- `SPATIAL` / `GEOMETRY` data types, spatial functions, and spatial indexes
- `LOAD XML`
- `HANDLER` statement
- `IMPORT TABLE`
- `INSERT DELAYED`
- `STRAIGHT_JOIN` (use standard JOIN instead)
- `NATURAL JOIN` (use explicit JOIN ON instead)
- `:=` assignment operator (move logic to application layer)
- XML functions
- GTID functions
- Full-text search functions (MySQL's FULLTEXT is not available)
- `ALTER EVENT` / `ALTER INSTANCE` / `ALTER SERVER`
- `CREATE EVENT` / `DROP EVENT`
- `CREATE SERVER` / `DROP SERVER`
- `CREATE SPATIAL REFERENCE SYSTEM`
- `LOCK INSTANCE FOR BACKUP` / `UNLOCK INSTANCE`
- Replication statements (`CHANGE MASTER TO`, `START/STOP SLAVE`, etc.)
- Group replication statements (`START/STOP GROUP_REPLICATION`)
- `INSTALL/UNINSTALL COMPONENT/PLUGIN`

## Partially Supported or Behavioral Differences

### Subquery Limitations

- Subqueries are **not supported in `HAVING` clauses**; rewrite as JOIN or CTE.
- Subqueries are **not supported in `JOIN ON` clauses**; extract subqueries as independent JOINs.
- Scalar subqueries with equality operators are supported normally.

### DML Differences

- `ON UPDATE CURRENT_TIMESTAMP` behavior is not fully consistent with MySQL; it's recommended to explicitly set update times in the application layer.
- Variable reference operations (`@c=1, @d=@c+1`) are not supported.

### SHOW Commands

- `SHOW WARNINGS` and `SHOW ERRORS` do not support `LIMIT` and `COUNT` combinations.
- `HELP` command is not supported.

### Keyword Limitations

- `MILLISECOND` and `MICROSECOND` keywords are not supported.

### Data Type Limitations

- `JSON` type cannot be used as a partition key.
- `GEOMETRY` / `LINESTRING` and other spatial types are not supported.

## DDL Limitations

- Secondary partitioned tables do not support Merge/Split/Add/Drop Subpartition.
- Index partitioned tables do not support Merge/Split/Add/Drop.
- Foreign keys are supported.
- Generated Columns are supported.
- `RENAME TABLE` is supported.

## Identifier Limitations

| Type | Maximum Character Length |
|------|------------|
| Database | 32 |
| Table | 64 |
| Column | 64 |
| Partition | 16 |
| Sequence | 128 |
| View | 64 |
| Constraint | 64 |

## Resource Limitations

| Resource | Limit |
|------|------|
| Tables per database | 8192 |
| Columns per table | 1017 |
| Partitions per table | 8192 |
| Global indexes per table | 32 |
| Sequences per database | 16384 |
| Views per database | 8192 |
| Users per database | 2048 |
| Databases | 32 |

## Character Sets and Collations

- Default character set: `utf8mb4`.
- It's recommended to explicitly specify collations to avoid relying on default behavior (PolarDB-X's default collation may differ from MySQL's).
- If case-insensitive comparison is needed, explicitly set `utf8mb4_general_ci` collation.

## Compatible MySQL Features (Safe to Use)

- Standard DML: SELECT / INSERT / UPDATE / DELETE / REPLACE
- Transactions: BEGIN / COMMIT / ROLLBACK / SAVEPOINT
- DDL: CREATE/ALTER/DROP TABLE / CREATE/DROP INDEX / CREATE/ALTER/DROP VIEW
- Account management: CREATE/ALTER/DROP USER / GRANT / REVOKE
- Prepared statements: PREPARE / EXECUTE / DEALLOCATE PREPARE
- LOAD DATA (disabled by default, needs manual enablement)
- LOCK TABLES
- SET TRANSACTION
- Most SHOW commands
