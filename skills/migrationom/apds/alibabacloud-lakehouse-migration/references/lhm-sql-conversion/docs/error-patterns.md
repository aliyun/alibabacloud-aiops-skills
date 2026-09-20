# DryRun Errors → Conversion Strategy

## Usage
Get the error text from `status.json.dryrun_error`, match it against the patterns below,
and guide the Agent's conversion according to the "Next-round strategy". If the same error appears ≥ 2 times, annotate at the beginning of the conversion:
**"⚠️ This error has appeared N times and must be fixed first."**

---

## MaxCompute Errors

| Error signature | Root cause | Next-round strategy |
|---------|------|----------|
| `column xxx cannot be resolved` | The column name does not exist or is misspelled | Check tableSchema to confirm the actual column name; check whether it is a Redshift system column (e.g. `$path`) that needs to be removed |
| `ambiguous column reference "xxx"` | Column name ambiguity in a multi-table JOIN | Add table alias prefixes to all non-aggregated SELECT columns; expand `SELECT *` into explicit column names |
| `Table xxx is not found` | The table does not exist or the schema prefix is wrong | Check the schema prefix; if it truly does not exist, annotate "environment issue, not a syntax issue" |
| `Unsupported function: xxx` | MC does not support this function | Use lookup_rules.py to find an equivalent; if no rule exists, rewrite with CASE WHEN |
| `UNNEST is not supported` | UNNEST was used | Change to `LATERAL VIEW EXPLODE(arr) tmp AS elem` |
| `syntax error` (abnormal parenthesis/keyword position) | A comment truncated the SQL | Check for the `-- xxx end AS TYPE)` pattern, and move the comment outside or remove it |
| Reserved word conflict (the column name is an MC keyword) | The column name is a reserved word | Wrap it in backticks: `` `order` `` |

## Hologres Errors

| Error signature | Root cause | Next-round strategy |
|---------|------|----------|
| `syntax error at or near "GLOBAL"` | GLOBAL JOIN | Remove the GLOBAL keyword |
| `syntax error at or near "QUALIFY"` | QUALIFY is not supported | Rewrite as a subquery + WHERE |
| `syntax error at or near "GROUP/ORDER"` | The preceding expression is incomplete | Check for comment truncation issues |
| `column reference "xxx" is ambiguous` | Column name ambiguity | Handle the same way as MC ambiguous |
| `operator does not exist: integer = text` | Type mismatch on both sides of the JOIN | Add `CAST(int_col AS TEXT)` |

## MySQL Errors

| Error signature | Root cause | Next-round strategy |
|---------|------|----------|
| `Unknown column 'xxx' in 'field list'` | The column name does not exist or is misspelled | Check tableSchema to confirm the actual column name |
| `Table 'xxx' doesn't exist` | The table does not exist or the schema prefix is wrong | Check the schema/database prefix |
| `FUNCTION xxx does not exist` | MySQL does not support this function | Use lookup_rules.py to find an equivalent |
| `You have an error in your SQL syntax` | Syntax error | Check for reserved word conflicts (wrap in backticks) and keyword spelling |
| `Incorrect parameter count` | Wrong number of function parameters | Check the parameter list of target_syntax in the rule |
| Reserved word conflict (the column name is a MySQL keyword) | The column name is a reserved word | Wrap it in backticks: `` `order` `` |

## SQL Server Errors

| Error signature | Root cause | Next-round strategy |
|---------|------|----------|
| `Invalid column name 'xxx'` | The column name does not exist or is misspelled | Check tableSchema to confirm the actual column name |
| `Invalid object name 'xxx'` | The table does not exist or the schema prefix is wrong | Check the schema prefix (dbo.xxx) |
| `'xxx' is not a recognized function name` | SQL Server does not support this function | Use lookup_rules.py to find an equivalent |
| `Incorrect syntax near 'xxx'` | Syntax error | Check T-SQL specific syntax (e.g. TOP vs LIMIT) |

## Distance Validation Failure Strategy

| distance_error description | Next-round strategy |
|--------------------|----------|
| The number of SELECT columns decreased | Strictly preserve all SELECT columns; only change functions/types, do not drop columns |
| The number of FROM/JOIN changed | Keep table references and the JOIN structure exactly unchanged |
| Subquery depth changed | Keep the subquery nesting unchanged; do not merge or split |
| WHERE/GROUP BY disappeared | Keep the original clauses; only change the syntax inside the clauses |

**General principle after a distance failure: fall back to `sqlt_output.sql` and fix the DryRun error with minimal changes.**
