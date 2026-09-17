# Flink SQL Reference Index

Read one or a few topics appropriate to the current lifecycle stage; do not load every file at once:

- First job or end-to-end example: [quickstart.md](quickstart.md)
- Event time, state, Checkpoints, Savepoints, and job resources: [concepts.md](concepts.md)
- DDL/DML, windows, Joins, aggregations, deduplication, Watermarks, and tuning: [sql-development.md](sql-development.md)
- Source/Sink options for Kafka, MySQL CDC, Hologres, Paimon, and others: [connectors.md](connectors.md)
- Mapping between VVR and Apache Flink versions: [engine-versions.md](engine-versions.md)

## Required Checks When Generating SQL

1. Provide complete Source DDL, Sink DDL, and DML.
2. Do not define a Watermark on a Sink table. Event time and Watermarks belong to input-side time semantics.
3. Declare primary keys according to the Connector's update semantics, usually as `PRIMARY KEY (...) NOT ENFORCED` in Flink SQL.
4. Bound all state. Do not invent inline `STATE ttl INTERVAL` syntax in DDL. Use an SQL Hint, `SET`, or a table/job option only when documentation for the target VVR version explicitly supports it.
5. `allowNonRestoredState` is a Job restore parameter, not an SQL `SET` option. When restoring after operator changes, distinguish stateless operators from stateful operators; old state may not map to the latter.
6. Connector options, enum values, and defaults vary by version. For current support, consult official Alibaba Cloud documentation and use `validate_sql` when a workspace is available.

## Expressing Evidence

- Actual platform results supplied by the user take precedence over offline guidance.
- Label general Apache Flink behavior as a community-wide principle; label VVR console paths, Connector options, and version restrictions as Alibaba Cloud/VVR behavior.
- For thresholds, defaults, and support scope without online or API evidence, write “requires verification against the target version” instead of inventing exact values.
