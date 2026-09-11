> Loaded on demand — ODPS-XXXXXXX error codes mapped to recovery actions. Skip unless `aliyun maxc query --json` returned `status=failure` with a non-self-explanatory `error.code`.

# MaxCompute SQL error recovery handbook

Decision reference after a SQL execution fails. When `aliyun maxc query --json` returns `status=failure`, this file maps the `error.code` (e.g. `ODPS-0130071`) to recovery actions. Self-explanatory errors that need no agent action are not expanded here.

## Retry policy

Use the JSON Envelope as the control plane:

1. Confirm `status=failure`; then inspect `error.code`, `error.suggestion`, warnings, and any job or instance identifier.
2. Retry only when the returned state identifies a transient failure or when a deterministic SQL correction addresses the reported error. Do not use a fixed retry count independent of state.
3. Before retrying an asynchronous query, inspect its job state with the returned job identifier. Do not submit a duplicate while the original job may still be running or may have succeeded.
4. Stop when the state is unknown, the same corrective action did not change the failure, recovery requires broader permissions, or a different execution mode or write is proposed. Report the error code, a sanitized message, and the request or job identifier, then ask the user.

Never auto-retry or rewrite DDL/DML. Execute `INSERT OVERWRITE`, `INSERT INTO`, `MERGE`, `UPDATE`, `DELETE`, and other SQL mutations only when the user explicitly authorizes the exact statement, target, and effect; use `--force` one statement at a time.

## How to match entries

The error-code prefix indicates the broad category: `0130xxx` compile / `0123xxx` runtime / `0140xxx` Sandbox / `1850xxx` MCQA.

`ODPS-0130071` and `ODPS-0010000` are **wrappers** (one code covers many subscenarios) — split them by message keyword, see below.

## Dedicated semantic error codes

| Code | Meaning | Fix |
|---|---|---|
| `ODPS-0130131` | Table not found | Check spelling, project/schema prefix, querier ACL |
| `ODPS-0130121` | Invalid argument type | Compare to function signature, `CAST` input to the correct type |
| `ODPS-0130141` | Illegal implicit type cast | Explicit `CAST(col AS ...)` (**note**: `Partition not found` is **not** this code, it's `0130071`) |
| `ODPS-0130241` | Illegal union operation | Make UNION column count and types match; explicit `CAST` each branch to a unified type (implicit promotion often fails: BIGINT vs DECIMAL, STRING vs BIGINT) |
| `ODPS-0130252` | Cartesian product is not allowed | Add the intended `ON` condition. Use MAPJOIN or allow Cartesian execution only after verifying the requested semantics, bounded inputs, and current project guidance. |
| `ODPS-0140081` | Unsupported join type | MAPJOIN does not support that OUTER configuration; switch JOIN type or drop the MAPJOIN hint |
| `ODPS-0130013` | Authorization exception / Access Denied | Insufficient table/column ACL; ask the owner to grant |
| `ODPS-0130161` | Syntax error, **or** SQL too large (message contains `DFA count`) | Fix syntax; for size, see "SQL size limit" below |

### `ODPS-0130071` is a generic semantic-exception wrapper (covers many subscenarios)

**Do not try to enumerate `0130071` subscenarios** — it is MaxCompute's catch-all semantic error code; any semantic exception without a dedicated code lands here.

Correct flow:
1. First compare against the "Dedicated semantic error codes" table above → match → fix per that row.
2. If the code is genuinely `0130071`, look up the message keyword in the "High-frequency subscenarios" section below.

---

## Compile-time errors

### SQL size limit (three same-root error codes)

Different stages, same fix direction:

| Code | Message signature | Trigger stage |
|---|---|---|
| `ODPS-0130161` | `Parse fail ... DFA count` | Parse |
| `ODPS-0130071` | `compile fail ... AST node count` | Semantic |
| `ODPS-0010000` | `The Size of Plan is too large` | Plan generation (>1MB rejected) |

**Fix**:
- Reduce nested expressions, repeated CTE expansion, JOIN levels, and scanned partitions.
- Split the read into smaller SELECT queries when the requested result allows it.
- If intermediate materialization is genuinely required, stop and ask for explicit authorization, the exact destination, and overwrite semantics before proposing any write.
- `UNION ALL` supports up to 256 tables. See [MaxCompute SQL limits](https://www.alibabacloud.com/help/en/maxcompute/user-guide/maxcompute-sql-limits).

### `ODPS-0010000` wrapper: plan-too-large vs. worker OOM (split by message)

Code `0010000` covers two opposite scenarios; you must classify by message text:

| Message keyword | Subscenario | Fix direction |
|---|---|---|
| `The Size of Plan is too large` | **Compile-time** plan rejected (>1MB) | Split SQL, see "SQL size limit" above |
| `worker out of memory` / `sigkill(oom)` (no `sqltask` keyword) | **Runtime** worker process OOM | Identify the failing task and operator, inspect skew and input size, then use environment-specific guidance before changing memory settings. |
| `sqltask` + OOM | Compile / planning SQL-task process OOM | Reduce partition scan, split SQL, reduce metadata queries. **Not an operator memory issue** — tuning stage memory has no effect. |

**Diagnostic order for worker OOM**:
1. Read logview / instance summary, identify the failed task type and the specific operator (HashJoin / SortMerge / WindowAgg / UDF).
2. Check skew: `DistinctValueCounts`, JOIN-key distribution, whether single-task input bytes are far above average.
3. If skewed, address confirmed hot keys with a verified semantics-preserving
   plan such as an applicable `SKEWJOIN` hint or a hot-key split. Key salting is
   valid only when both JOIN sides are transformed consistently and any
   required small-side rows are replicated so matches are preserved; otherwise
   it changes the result. Then consider memory only if evidence still supports
   it.
4. If none of the above work **and the data volume itself is genuinely large** → bump the corresponding stage memory or split SQL.
5. **Easy misdiagnosis**: when you see `Size of Plan` in the message, do **not** tune stage memory (root cause is compile-time plan size). HashJoin / window-operator blowup sometimes is not solved purely by adding memory — fix skew first.

### `ODPS-0130071` high-frequency subscenarios

| Message keyword | Scenario | Fix |
|---|---|---|
| `compile fail ... AST node count` | SQL size limit (semantic stage) | Reduce or split the SELECT; do not introduce intermediate writes without authorization |
| `recursive-cte ... exceed max iterate number %d` | Recursive CTE iteration limit | Confirm the required depth and termination condition before raising the setting; the documented default is 10 and maximum is 100. See [Common table expressions](https://www.alibabacloud.com/help/en/maxcompute/user-guide/common-table-expressions-1) |
| `partition not found:<spec>` | Partition does not exist | Check the partition value format (`'YYYYMMDD'` vs `'YYYY-MM-DD'`); confirm with `SHOW PARTITIONS <table>` or `aliyun maxc meta latest-partition` |
| `column %s cannot be resolved` | Column name resolution failed | MaxCompute SQL column names are [case-insensitive](https://www.alibabacloud.com/help/en/maxcompute/user-guide/maxcompute-sql-limits). Confirm spelling, qualification, and schema with `DESC <table>` or `aliyun maxc meta describe`; use any compiler suggestion only as a candidate. |
| `expect equality expression for join condition` | Non-equi JOIN without a supported plan | Prefer an equivalent equi-JOIN or another semantic rewrite. Use `/*+ MAPJOIN(small_table) */` only after verifying a bounded broadcast side and the requested non-equi semantics. |
| `function sum cannot match any overloaded functions with (BOOLEAN)` | `SUM(boolean expression)` | Rewrite as `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` or `COUNT_IF(...)` |
| `expression is not in GROUP BY` | Non-aggregate column missing from `GROUP BY` | Add the column to `GROUP BY` when it belongs to the requested granularity, or use a deterministic aggregate (`MAX` / `MIN` / `SUM`) that matches the metric. Use `ANY_VALUE(col)` only when any representative value is acceptable. |
| `INSERT INTO HASH CLUSTERED table` | Hash-clustered table does not support `INSERT INTO` | Report that the requested write mode is unsupported; do not switch to overwrite without explicit authorization for the exact target |
| `invalid partition value` | Dynamic partition value violates a documented constraint | Validate the value against the current error detail and [table creation documentation](https://www.alibabacloud.com/help/en/maxcompute/user-guide/table-creation-and-deletion); do not infer a valid format from another table. |
| `function date_format is not supported in current mode` | `DATE_FORMAT` type / mode restriction | For TIMESTAMP input, use `SET odps.sql.type.system.odps2=true;`; for other documented inputs, use `SET odps.sql.hive.compatible=true;`. Use `TO_CHAR` when it preserves the intended format semantics without a compatibility switch. |
| `function or view '<name>' cannot be resolved` | Function / view name wrong (e.g. `IFNULL`) | Check spelling. `IFNULL` does not exist — use `NVL` or `COALESCE`. |
| `Result of a union cannot be a map table` | UNION + MAPJOIN combination restriction | Rewrite SQL to avoid MAPJOIN inside UNION |
| `DDL does not support explain` | `EXPLAIN` followed by a DDL statement | Drop `EXPLAIN` |
| Other `Semantic analysis exception` | Hundreds of fine-grained scenarios | Decide based on message text + context |

### `ODPS-0130252` Cartesian product not allowed

A few well-known rewrite patterns:

| Scenario | Rewrite strategy |
|---|---|
| `CROSS JOIN + AVG/SUM` subquery | Replace with window function `AVG(x) OVER()` |
| `FROM a, b` with no `ON` | Explicit `JOIN ... ON` |
| Non-equi JOIN (the business genuinely needs CROSS-like semantics) | Use `/*+ MAPJOIN(small_table) */` only with a verified bounded broadcast side |
| Full cross-tagging (**use with care**) | Dummy key: each side `SELECT *, 1 AS jk`, JOIN `ON jk=jk` |

> Dummy-key full cross is an **N×M Cartesian product** — result size explodes. **Use only when all of these hold**: (1) the business genuinely needs a full cross, (2) both sides have small bounded cardinality, (3) the user accepts the storage / compute cost, (4) combined with `/*+ MAPJOIN(small) */` to broadcast the small side. Otherwise use a window function / grouped aggregate / semi-Cartesian (JOIN with a filter condition) instead.

Fallback: `SET odps.sql.allow.cartesian=true;` only when the requested semantics
require the Cartesian result, both inputs have verified bounded cardinality,
and the user accepts the compute and result-size cost.

### `ODPS-0123091` Dirty value CAST failure

Adding a `CAST()` does **not** help — the `CAST` itself is the failure point. The data contains dirty values.

**Fix (in priority order)**:
1. Pre-filter: `WHERE col RLIKE '^-?[0-9]+$'` then `CAST` — explicitly control how dirty values are handled (drop / mark / route to a separate table).
2. Return diagnostic counts or sample invalid values through a bounded SELECT. Do not create or write an audit table unless the user explicitly authorizes that target and write.
3. Fallback: use the strict-mode parameter named by the current error or verified environment documentation. Disabling strict mode does **not** drop the row: an invalid `CAST` becomes `NULL` while the other columns continue. Confirm that the downstream workflow can distinguish a business `NULL` from a cast-failure `NULL` before using this behavior.

---

## Runtime errors

### `ODPS-0123065` Join exception

Two trigger paths; the error text does not directly distinguish them:

| Path | How to identify | Fix |
|---|---|---|
| User-explicit `/*+ MAPJOIN(...) */` exceeds threshold | Hint visible in the SQL | Drop the hint, let the CBO decide |
| CBO auto-MAPJOIN (no hint) | Error text contains `small table exceeds when auto map join applied` | Inspect current project settings and table statistics; choose a plan change based on that evidence |

Do not assume a universal MAPJOIN threshold or memory value. Check whether the JOIN key is skewed and follow the error Envelope or current official guidance before changing optimizer or memory settings.

### `ODPS-0123131` User-defined function exception

The UDF threw an exception, or input data caused the UDF to fail.

**Fix**:
- Compare against the UDF signature and check input column types.
- Add safe upstream filtering when it preserves the requested result.
- If the failure requires UDF implementation changes, report the evidence and
  hand it to the UDF owner. Change UDF code only when the user explicitly asks
  for that code work and supplies the relevant source.

### `ODPS-0123144` UDF timeout

Error text contains `kInstanceMonitorTimeout` + `usually caused by bad udf performance`. Root cause: UDF operation is too slow (infinite loop / complex algorithm / external call).

**Recovery order**:
1. **Localize the slow point first**: read logview UDF profiling. Identify whether it is an infinite loop, a complex algorithm, an external call, or one bad row stuck.
2. Add upstream `WHERE` pre-filtering of abnormal inputs (bad data is a common root cause; faster to catch than tuning timeout).
3. If implementation work is required, report the slow point to the UDF owner.
   Change the UDF only when the user explicitly requests that code work and
   supplies the relevant source.
4. Change batch or timeout settings only when `error.suggestion` or verified environment documentation recommends it and the user accepts the runtime tradeoff.

### `ODPS-1850001` MCQA query-acceleration mode restriction

| Scenario | Action |
|---|---|
| Error explicitly identifies an MCQA-incompatible SELECT feature | Explain the batch-mode tradeoff and fall back only after the user accepts it |
| DML or DDL | Do not change execution mode automatically; execute only the exact user-authorized write with `--force` after rechecking its target and effect |
| Other failure | Do not infer an MCQA restriction; follow the specific error and recovery state |

### `ODPS-0140171` Sandbox violation / archive load failure

Three different errors share this code; **do not handle uniformly**:

| Message keyword | Nature | Fix |
|---|---|---|
| `permission denied to read archive resource` / `not allow symlink in archive files` | Hive Bridge sandbox **Java archive load restriction** (protects third-party Java code loading — not data ACL) | Only when the scenario is external table + TextFile + LazySimpleSerDe, try `SET odps.ext.hive.lazy.simple.serde.native=true;` to switch to the native reader and bypass the Hive Bridge. Other formats not applicable. |
| `PanguPermission` / `permission denied for volume` | **Volume data access permission** (data ACL) | Must go through authorization (`GRANT Read ON VOLUME ...`) — **cannot be bypassed via SET** |
| Non-external-table `Access Denied` | Table / column ACL | Ask the owner to grant access |

**Important**: `odps.ext.hive.lazy.simple.serde.native=true` is **not** an ACL bypass flag — it only switches the read code path. The sandbox protects Java-code-load safety; it has no effect on "data-level permission denied".

### UDF registration / invocation issues

Split by root cause:

**(A) Registration-side issues (jar / annotation / class signature / environment) — report them to the UDF owner; do not change the calling SQL**

| Error keyword | Fix direction |
|---|---|
| `cannot be loaded from any resources` | Check whether `CREATE FUNCTION ... USING '<jar>'` resource is uploaded |
| `does not match annotation` | Make the UDF class's `@Resolve` annotation match the actual signature |
| `UnsatisfiedLinkError` | Java version / native library mismatch |
| `Invalid function class ... static evaluate method` | UDF class signature wrong (missing `evaluate` method or wrong parameter types) |

**(B) Invocation-side issues (parameter type mismatch) — change the input type in SQL**

| Error keyword | Fix direction |
|---|---|
| `Wrong arguments UDTF ... initialize returned failed` | UDTF input parameter type mismatch; `CAST(col AS <expected>)` explicitly in the calling SQL |
| `cannot match any overloaded functions with (...)` | Invocation type does not match any UDF overload; `CAST` inputs per the signature |
