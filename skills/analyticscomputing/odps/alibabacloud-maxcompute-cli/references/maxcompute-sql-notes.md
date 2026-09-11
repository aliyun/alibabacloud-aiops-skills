> Loaded on demand — CLI-side SQL behaviors: SET injection, client-side write gate, result fetching, upload semantics. Skip unless the agent needs to know how `aliyun maxc` wraps SQL execution.

# MaxCompute SQL with `aliyun maxc`

Read this file for `aliyun maxc`-specific SQL behaviors: how `aliyun maxc query` injects SET options, how the client-side write gate works, how result fetching behaves, and how `aliyun maxc data upload` maps to `INSERT INTO` / `INSERT OVERWRITE` semantics.

For SQL dialect rules (NULL handling, date functions, types, JOIN semantics, window frames, SET parameter semantics), see [maxcompute-select-guide.md](maxcompute-select-guide.md). For ODPS error code recovery, see [sql-common-errors.md](sql-common-errors.md). For NL→SQL planning, see [text2sql-principles.md](text2sql-principles.md). For partition discovery, see [partition-guide.md](partition-guide.md).

## `SET` options

`aliyun maxc` supports inline `SET` statements before SQL. The SET values are passed to MaxCompute as execution hints:

```bash
aliyun maxc query "SET odps.sql.type.system.odps2=true; SELECT CAST(id AS INT) FROM schema.table LIMIT 10" --json
```

Multiple SET statements can be chained:

```bash
aliyun maxc query "SET odps.sql.type.system.odps2=true; SET odps.sql.hive.compatible=true; SELECT ..." --json
```

For the meaning of each SET option (which switches enable which types / dialect features), see [maxcompute-select-guide.md](maxcompute-select-guide.md) §12.

A leading `SET` is execution context, not authorization. Project-security,
access-control, and masking parameters are blocked even for `SELECT`. For a
forced DDL/DML statement, the CLI additionally accepts only audited
statement-local SQL/runtime hints; an unknown hint fails closed. Never use a
`SET` hint to weaken permissions, project protection, label security, or data
masking.

Audited write examples include `odps.sql.bigquery.compatible=true` for
BigQuery-compatible DDL identifiers and
`odps.sql.insert.acidtable.deduplicate.enable=true` for the explicitly requested
Delta-table INSERT deduplication behavior. Their use still belongs to the same
one-statement authorization; the hint is not separate permission to write.

## SQL write gate

The client checks every executable operation, including operations nested in
script control flow. Without `--force`, only SQL shapes proven read-only are
submitted. With `--force`, the client still accepts exactly one executable
statement; audited leading `SET` hints may configure that statement. Treat the
gate as a safety aid, not an authorization boundary.

For read-only work, submit only verified `SET` statements followed by one
`SELECT`. Do not send an additional statement. For DDL/DML, require the user's
explicit request, verify the exact statement, project, schema, target, and
effect, then send one statement at a time with `--force`. Never combine an
authorized write with an unrelated statement or infer it from a read request.

The `--force` path uses a positive data-plane allowlist. It accepts recognized
DML and DDL for tables, views, functions, and schemas plus documented table
maintenance or transfer statements. Permission, account, project, system,
resource, package, tenant, cluster, quota, and unknown administrative shapes
remain blocked; route those through a dedicated approved workflow.

`aliyun maxc data upload` writes through the Tunnel API and does not use the SQL
gate. Confirm its project, table, complete partition specification, source file,
and append or overwrite mode separately before each upload.

## Result fetching

- Default `--max-rows` is 100. Use `--max-rows N` to retrieve up to N rows.
- The backend can use Instance Tunnel internally for a large requested page,
  but the response is still bounded by `--max-rows` or `--page-size`.
- Query `--output` writes only the current envelope page; it does not lift the
  row bound or collect later pages. Check `data.pagination.has_more` and
  `next_cursor`. Prefer `data download` for a complete table or partition export
  within its limits; otherwise paginate and combine outputs without overwriting
  earlier pages.
- `LIMIT` without `ORDER BY` returns **non-deterministic** rows — the same query may return different rows each run. See [maxcompute-select-guide.md](maxcompute-select-guide.md) §1 for the dialect rule on `ORDER BY`+`LIMIT` pairing.

## Upload semantics

Choose append or overwrite from the user's requested write semantics:

| SQL statement | Effect | `aliyun maxc data upload` equivalent |
|---|---|---|
| `INSERT INTO` | Append rows to the table/partition | `aliyun maxc data upload <table> --file path.csv [--partition ...]` (default append) |
| `INSERT OVERWRITE` | Replace all data in the target table/partition | `aliyun maxc data upload <table> --file path.csv [--partition ...] --overwrite` |

Duplicate rows, partial partitions, or missing recent partitions do not establish
how the data was written. Verify job history, table documentation, and the
relevant pipeline evidence before attributing a cause.

`aliyun maxc data upload` goes through Tunnel, supports primitive types only (no
array/map/struct), is fail-fast on bad rows, and requires the target table to
already exist. A missing partition is rejected unless the caller explicitly
adds `--create-partition`; that metadata mutation requires separate
authorization. `--dry-run` validates the complete local file and mapping without
opening an upload session, creating the partition, or writing rows. If the
requested transfer exceeds these capabilities, explain the limitation and ask
the user to choose a supported transfer workflow.
