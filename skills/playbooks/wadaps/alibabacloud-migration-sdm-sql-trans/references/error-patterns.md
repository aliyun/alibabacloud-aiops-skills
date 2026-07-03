# DryRun Errors → Conversion Repair Strategies

## How to Use

When validation (Step 4) finds residual syntax or execution errors, match the pattern below and follow the "Repair Strategy" column to guide the next conversion round.
If the same error appears ≥ 2 times and remains unresolved, annotate: **"⚠️ This error has appeared N times; must be fixed with highest priority."**

---

## Hologres (PostgreSQL) Common Errors

| Error Signature | Root Cause | Repair Strategy |
|-----------------|------------|-----------------|
| `syntax error at or near "["` | T-SQL square brackets not removed | All `[identifier]` → `identifier` (lowercase) or `"Identifier"` (mixed case) |
| `column "xxx" does not exist` | Column name case mismatch | Hologres folds to lowercase by default; if tables were created with `""`, queries must also use `""` |
| `function xxx(type) does not exist` | Function not converted or parameter type wrong | Check function mapping table in reference.md; verify whether parameters need CAST |
| `operator does not exist: integer = text` | Type mismatch on both sides of JOIN/WHERE | Add `CAST(int_col AS TEXT)` or `int_col = text_col::INT` |
| `syntax error at or near "TOP"` | TOP N not converted to LIMIT | `SELECT TOP n ...` → `SELECT ... LIMIT n` (move to end) |
| `syntax error at or near "NOLOCK"` | Query hint not removed | Delete `WITH (NOLOCK)` / `OPTION(...)` |
| `type "nvarchar" does not exist` | Data type not converted | `NVARCHAR(n)` → `VARCHAR(n)` or `TEXT`; `DATETIME2` → `TIMESTAMP` |
| `syntax error at or near "ISNULL"` | Function not converted | `ISNULL(a,b)` → `COALESCE(a,b)` |
| `syntax error at or near "#"` | Temp table syntax not converted | `#temp` → `CREATE TEMPORARY TABLE temp` or use CTE instead |
| `syntax error at or near "@"` | Table variable / variable not converted | In PL/pgSQL: `@var` → `var`; in non-procedural context: use CTE instead |
| `relation "dbo.xxx" does not exist` | Schema prefix not mapped | `dbo.table` → `public.table` (or the actual target schema) |
| `IDENTITY is not supported` | IDENTITY syntax residual | `IDENTITY(1,1)` → `BIGSERIAL` or `GENERATED ALWAYS AS IDENTITY` |
| `syntax error at or near "APPLY"` | APPLY not converted | `CROSS APPLY` → `CROSS JOIN LATERAL`; `OUTER APPLY` → `LEFT JOIN LATERAL ... ON TRUE` |
| `syntax error at or near "IIF"` | Conditional function not converted | `IIF(cond,t,f)` → `CASE WHEN cond THEN t ELSE f END` |
| `invalid input syntax for type timestamp` | Date functions not correctly converted | Review `DATEDIFF`/`DATEADD` conversions; use interval arithmetic, not function calls |

## MaxCompute (ODPS-SQL) Common Errors

| Error Signature | Root Cause | Repair Strategy |
|-----------------|------------|-----------------|
| `ODPS-0130071: Semantic analysis exception - column xxx cannot be resolved` | Column name missing or misspelled | Verify actual column names; check whether system columns need to be removed |
| `Ambiguous column reference "xxx"` | Multi-table JOIN column name ambiguity | Prefix all non-aggregated columns with table aliases; expand `SELECT *` |
| `Table xxx is not found` | Table name missing schema/project prefix | Verify `project.schema.table` format |
| `Unsupported function: xxx` | Function not supported in MC | Check rule mapping table; if no rule, rewrite using CASE WHEN |
| `UNNEST is not supported` | UNNEST used | Replace with `LATERAL VIEW EXPLODE(arr) tmp AS elem` |
| Reserved-word conflict | Column name is an MC keyword | Wrap in backticks: `` `order` `` |
| `Syntax error - unexpected LIMIT` | LIMIT in wrong position | MC LIMIT not supported in certain contexts; wrap in a subquery |

---

## Distance Validation Failure Repair Strategies

| Failure Description | Repair Strategy |
|---------------------|-----------------|
| SELECT column count reduced | Preserve all SELECT columns strictly; only change functions/types, never drop columns |
| FROM/JOIN count changed | Keep table references and JOIN structure completely unchanged |
| Subquery depth changed | Preserve subquery nesting levels; do not merge or split |
| WHERE/GROUP BY disappeared | Preserve original clauses; only change the syntax inside them |

**General principle after distance failure: fall back to the original SQL and apply only the minimum changes needed to fix syntax differences.**

---

## General Repair Principles

| Principle | Description |
|-----------|-------------|
| Minimum change | Fix only the error point; no extra "optimization" |
| Rules first | Consult mapping rules in references files first |
| No guessing | If not covered by rules, keep original and annotate `-- TODO: verify` |
| NULL safety | Conversion must not introduce extra NULL risk (use `COALESCE`, not `\|\|`) |
| Structure unchanged | Do not merge/split subqueries, drop columns, or remove clauses |

---

## Extending This File

When adding a new engine pair, append a "<target-engine> Common Errors" table to this file. Format:
- **Error Signature**: key fragment of the error message
- **Root Cause**: the true underlying cause
- **Repair Strategy**: specific remediation approach (with examples preferred)
