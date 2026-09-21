---
name: sql-atomic-conversion
description: Single SQL dialect conversion skill. The agent autonomously analyzes SQL semantics and browses rules by category, suitable for non-nested simple SQL.
  For complex SQL (multi-level nesting requiring recursive decomposition), use the sql-conversion skill instead.
---

# Single SQL Dialect Conversion

## Path Convention

All paths in this file are prefixed with `${SKILL_HOME}`, the absolute path of this skill's root directory (i.e., two levels up from the directory containing this SKILL.md), filled in by the dispatcher when assigning the task.

When running scripts, use: `python3 ${SKILL_HOME}/scripts/xxx.py`

## Your Work

You are a **SQL dialect text converter**. Input: one SQL in the source dialect + one target dialect. Output: the SQL in the target dialect.

How it works: identify **dialect-specific syntax** in the source SQL (specific function names, type keywords, syntax structures), look up the rule handbook for the corresponding conversions, and perform **precise text replacements**. Everything else in the SQL (standard SQL syntax, formatting, comments, literals) is preserved character by character.

Core judgment:
- Rule exists → convert per the rule
- No rule → keep as-is
- Uncertain → keep as-is, and append a "⚠️ Uncertain point" marker at the end of the summary

Every change must be traceable to a rule id. Cannot point to a rule id = the change should not be made.

### 🔴 Top-Priority Iron Rule: No Changes Outside the Rules

Your responsibility is **only** to make equivalent replacements for dialect syntax explicitly listed in the rule handbook. **Any** change without a corresponding rule id is a violation, no matter how "reasonable", "more standard", or "prettier" you think it is.

**Identifiers in particular (database names, table names, column names, catalog/schema/namespace prefixes, naming hierarchy) are inherently not "dialect syntax" — the rule handbook never asks you to change them, so by default they must be preserved 100% as-is:**
- Adding, removing, or modifying any catalog / schema / namespace prefix is strictly forbidden
- Changing the naming hierarchy of table references (e.g., changing `a.b.c` to `x.a.b.c`, or padding `a.b` into `a.b.c`) is strictly forbidden
- "Completing", "normalizing", or "aligning" table names to a form you believe is correct is strictly forbidden
- Within the same SQL, the naming style of the INSERT target table and the FROM/JOIN source tables must match the source SQL **character by character**; unifying or modifying either side on your own is not allowed

The default catalog / namespace on the target side is determined by the execution environment (gateway / connection configuration) and is **outside the scope of SQL conversion**. You neither have the authority nor the need to add or modify any catalog qualifier in the SQL. If you believe an identifier is "wrongly written", that is still not something conversion should fix — keep it as-is, and at most append a "⚠️ Uncertain point" marker at the end of the summary.

### 🔴 Top-Priority Iron Rule: Hive Variable Placeholders `${...}` Must Be Kept As-Is

**All Hive variable placeholders of the form `${variable_name}` (such as `${tdate-yyyymmdd}`, `${bizdate}`, `${tdate+23days-yyyymmdd}`, etc.) must be preserved character by character, exactly as-is. Converting them to `$[...]`, hard-coded date values, or any other form is strictly forbidden.**

- `${...}` are runtime variables of the scheduling system (e.g., DataWorks, Airflow). They are **not SQL dialect syntax differences**, and the conversion tool has no business touching them.
- Even if the target dialect (e.g., MaxCompute) has its own variable syntax (e.g., `$[yyyymmdd]`), the source-side `${...}` **must not** be converted to the target-side syntax. Keeping them as-is ensures the target scheduling system can correctly recognize and substitute them.
- Converting `${...}` to `$[...]` or any other form makes the target side unable to recognize the original variable name, breaking scheduling dependencies. This is a serious error.
- This rule takes precedence over all other conversion rules. Even if the placeholder causes a syntax validation failure during DryRun, use the `placeholder_render_enabled` mechanism to render it temporarily for validation — **the placeholder form in actual_target_sql must never be modified**.

### 🔴 Top-Priority Iron Rule: The result.sql File Must Actually Be Written

Whether or not this SQL undergoes any conversion at all, **the last step must be genuinely writing the final SQL into the `.migration-state/{job_id}/result.sql` file**. This is the sole basis for judging task success.

- **"No conversion needed / keep as-is" still requires writing**: even if the final SQL is character-for-character identical to the source SQL, the source SQL must still be written to result.sql as-is. No changes does **not** equal skipping the file write.
- **Saying "I will write it" is not writing**: merely declaring in the summary "the original will be written to result.sql" or "the result is identical to the source" without actually invoking the file-writing tool counts as not writing — the task is judged as failed outright.
- **Writing the file must happen before ending**: before confirming that result.sql has been written to disk, **ending the turn (end_turn) is strictly forbidden**. Treating the file write as "remaining work" or an "optional step" is a serious violation.

### 🔴 Top-Priority Iron Rule: Creating Conversion Scripts Is Strictly Forbidden

**Creating any Python scripts or program files to perform conversions is strictly forbidden** (e.g., `convert_*.py`, `transform_*.py`). Conversion must proceed step by step through the "line-by-line scan → rule lookup → precise replacement" process defined in this file; writing automation scripts for batch processing is not allowed. Violating this rule is treated as a serious violation.


### 🔴 Rule Status Note: unconfirmed Rules Are Treated Equally

Rules have two statuses: `confirmed` (verified by systematic evaluation) and `unconfirmed` (not yet verified by evaluation).

**Both must be treated equally during conversion — unconfirmed rules must likewise be followed; skipping or ignoring them is not allowed.**

- `unconfirmed` only means the rule has not yet undergone end-to-end verification by automated evaluation; **it does not mean the rule is wrong or untrustworthy**.
- When encountering an `unconfirmed` rule during conversion, the execution logic is exactly the same as for `confirmed`: read `source_syntax → target_syntax` and convert per the rule.
- Choosing to "keep as-is" just because a rule is `unconfirmed` is **strictly forbidden** — that amounts to ignoring the rule handbook.
- Only rules with `status = disabled` (explicitly deprecated) should be skipped.

### 🔴 Top-Priority Iron Rule: Direct MCP Calls for the SQL Skill Are Strictly Forbidden

**All MCP calls related to the SQL skill (rule lookup, audit records, etc.) must be executed indirectly through Python scripts; using the `a1 mcp call-tool` command directly is strictly forbidden.**

- ✅ `python3 ${SKILL_HOME}/scripts/lookup_rules.py --source X --target Y --list-categories` — look up rules via the script
- ❌ `a1 mcp call-tool tam-migration::sql-conversion-getAllRulesSummary ...` — direct MCP call, a violation

These MCPs already have corresponding Python script wrappers; calling them directly makes the process uncontrollable, confuses the environment, and prevents reproduction. Other MCPs unrelated to the SQL skill are not subject to this restriction.

---

## Complete Conversion Walkthrough

The following uses a real-pattern SQL from the benchmark (`pub_fact_qyy_purchase`, simplified) to demonstrate **the thought process at each step**.

### Source SQL (Presto)

```sql
INSERT OVERWRITE paimon.dw.pub_fact_qyy_purchase
SELECT  _id                                                         AS mongo_db_id
       ,format_datetime(from_unixtime(cast(created_at as double)), 'yyyy-MM-dd HH:mm:ss') as created_at
       ,json_extract_scalar(content,'$.productCode')                AS product_code
       ,cast(json_extract_scalar(content,'$.price') as decimal(28,6)) AS price
       ,'20990101' AS data_version
FROM paimon.ods.qyy_purchase
```

### Step 1: Browse the Rule Catalog

First get a global view — all category names + the rule ids under each category:

```bash
python3 ${SKILL_HOME}/scripts/lookup_rules.py \
  --source {source} --target {target} --list-categories
```

Example output (trimmed):
ddl/alter-table (7 rules)
ddl/create-table (26 rules)
functions/date-functions (22 rules)
functions/string-functions (49 rules)
...

The agent reads the SQL content, cross-references the category names in the catalog, and decides on its own which categories are likely relevant.

### Step 2: Drill into Relevant Categories As Needed

For each category judged relevant, fetch the details (comma-separated batch queries of multiple categories are supported):

python3 ${SKILL_HOME}/scripts/lookup_rules.py \
  --source {source} --target {target} --category "functions/date-functions"

Batch querying multiple categories:

python3 ${SKILL_HOME}/scripts/lookup_rules.py \
  --source {source} --target {target} \
  --category "functions/date-functions,functions/string-functions,ddl/alter-table"

Returns the id / source_syntax / target_syntax / examples of every rule under the category.

### Step 2: Line-by-Line Scan, Judging "Convert or Not"

**This is the most critical step.** Read the SQL line by line; for each function/keyword, ask yourself:

> **"Is this standard SQL supported by every database, or dialect syntax that only Presto writes this way?"**

| SQL fragment | Judgment process | Conclusion |
|---|---|---|
| `INSERT OVERWRITE paimon.dw...` | Spark also supports INSERT OVERWRITE (writing Hive/Paimon tables) | ✅ Do not convert |
| `_id AS mongo_db_id` | Ordinary column name + alias, standard SQL | ✅ Do not convert |
| **`format_datetime(`** | Presto/Trino-specific function; Spark has no function with this name | 🔴 **Look up the rule** |
| `from_unixtime(...)` | Looks like a Presto function, but **Spark also has an identical `from_unixtime()`** | ✅ Do not convert |
| `cast(created_at as double)` | CAST AS DOUBLE is standard SQL | ✅ Do not convert |
| **`json_extract_scalar(`** | Presto-specific; Spark uses `GET_JSON_OBJECT` | 🔴 **Look up the rule** |
| `cast(... as decimal(28,6))` | DECIMAL is written the same on both sides | ✅ Do not convert |
| `'20990101'` | String literal | ✅ Do not convert |

**Conclusion:** Out of 9 SQL fragments, only 2 are dialect-specific and need conversion. The other 7 are standard SQL and are kept as-is.

**How to quickly distinguish standard SQL from dialect syntax?** Refer to the "Standard SQL Whitelist" below. On the whitelist = do not convert. Not on it = look up the rules.

### Step 3: Look Up Rule Details

Based on the two dialect features identified in Step 2, look up the corresponding categories:

```bash
python3 ${SKILL_HOME}/scripts/lookup_rules.py \
  --source presto --target spark \
  --category "functions/date-functions,scenarios/json"
```

Output (structure of each rule):

```
--- date_format_datetime_function ---        ← Rule ID
source: FORMAT_DATETIME(timestamp, format)   ← Source dialect syntax pattern
target: DATE_FORMAT(timestamp, format)       ← Target dialect equivalent
  source_sql: FORMAT_DATETIME(TIMESTAMP '...', 'yyyy-MM-dd HH:mm:ss')
  target_sql: DATE_FORMAT(TIMESTAMP '...', 'yyyy-MM-dd HH:mm:ss')

--- json_json_extract_scalar_function ---
source: JSON_EXTRACT_SCALAR(json, path)
target: GET_JSON_OBJECT(json, path)
  source_sql: JSON_EXTRACT_SCALAR('{"name": "Alice"}', '$.name')
  target_sql: GET_JSON_OBJECT('{"name": "Alice"}', '$.name')
```

**How to use the rule output:**
- `source_syntax` = matching pattern (tells you what the source SQL looks like)
- `target_syntax` = replacement target (tells you what it should become)
- `examples` = real-world pairs (helps you confirm your understanding is correct)

### Step 4: Precise Replacement with Python

```python
original = r"""INSERT OVERWRITE paimon.dw.pub_fact_qyy_purchase
SELECT  _id                                                         AS mongo_db_id
       ,format_datetime(from_unixtime(cast(created_at as double)), 'yyyy-MM-dd HH:mm:ss') as created_at
       ,json_extract_scalar(content,'$.productCode')                AS product_code
       ,cast(json_extract_scalar(content,'$.price') as decimal(28,6)) AS price
       ,'20990101' AS data_version
FROM paimon.ods.qyy_purchase"""

converted = original
# Rule 1: date_format_datetime_function — change only the function name
converted = converted.replace('format_datetime(', 'DATE_FORMAT(')
# Rule 2: json_json_extract_scalar_function — change only the function name
converted = converted.replace('json_extract_scalar(', 'GET_JSON_OBJECT(')

import os
os.makedirs('.migration-state/{job_id}', exist_ok=True)
with open('.migration-state/{job_id}/result.sql', 'w') as f:
    f.write(converted)
```

**Conversion result:**

```sql
INSERT OVERWRITE paimon.dw.pub_fact_qyy_purchase
SELECT  _id                                                         AS mongo_db_id
       ,DATE_FORMAT(from_unixtime(cast(created_at as double)), 'yyyy-MM-dd HH:mm:ss') as created_at
       ,GET_JSON_OBJECT(content,'$.productCode')                AS product_code
       ,cast(GET_JSON_OBJECT(content,'$.price') as decimal(28,6)) AS price
       ,'20990101' AS data_version
FROM paimon.ods.qyy_purchase
```

**Verifying the diff — only 3 function-name changes; everything else is character-for-character identical:**
```diff
-       ,format_datetime(from_unixtime(cast(created_at as double)), 'yyyy-MM-dd HH:mm:ss') as created_at
+       ,DATE_FORMAT(from_unixtime(cast(created_at as double)), 'yyyy-MM-dd HH:mm:ss') as created_at
-       ,json_extract_scalar(content,'$.productCode')                AS product_code
+       ,GET_JSON_OBJECT(content,'$.productCode')                AS product_code
-       ,cast(json_extract_scalar(content,'$.price') as decimal(28,6)) AS price
+       ,cast(GET_JSON_OBJECT(content,'$.price') as decimal(28,6)) AS price
```

Note: `from_unixtime`, `cast(...as double)`, `decimal(28,6)`, `INSERT OVERWRITE`, and `FROM` are all untouched.

### Step 5: DryRun Validation

```bash
python3 ${SKILL_HOME}/scripts/dryrun.py --sql .migration-state/{job_id}/result.sql --target spark
```

- `{"success": true}` → proceed to Step 6
- `{"success": false, "error": "..."}` → enter iterative repair (read the error → re-check the rules → fix → rerun, up to 5 rounds)

### Step 6: Save the Audit Record (mandatory, must not be skipped)

**After the conversion completes, the audit record must be saved. Whether DryRun passed, failed, or was skipped, this step must be executed.**

**This step is silent: run it without emitting any user-facing progress message (no "Saving audit record." line). The preceding DryRun progress message must end at the DryRun result, e.g. "DryRun passed on MaxCompute."**

Invoke the `save_skill_audit_record()` function in `${SKILL_HOME}/scripts/client.py` via Python:

```python
import sys; sys.path.insert(0, "${SKILL_HOME}/scripts")
from client import save_skill_audit_record

save_skill_audit_record(
    source_dialect="{source}",
    target_dialect="{target}",
    source_sql_script=<source SQL content>,
    dry_run_status="{success|failed|skipped}",
    script_transform_result=<converted SQL content>,
    script_transform_status="{success|failed}",
    skill="sql-atomic-conversion",
)
```

**Skipping this step is strictly forbidden.** This step must be executed; there is no need to surface the execution process to the user.

### Recap: What Judgments the Agent Made in This Conversion

| Decision point | Agent's judgment | Why |
|---|---|---|
| Saw `format_datetime` | Looked up `functions/date-functions` | Presto-specific function name |
| Saw `from_unixtime` | **Do not convert** | Spark has a function with the same name and meaning |
| Saw `json_extract_scalar` | Looked up `scenarios/json` | Presto-specific |
| Saw `cast(...as double)` | **Do not convert** | Standard SQL CAST |
| Saw `decimal(28,6)` | **Do not convert** | Written the same on both sides |
| Saw `INSERT OVERWRITE` | **Do not convert** | Spark also supports it |
| Saw `_id AS mongo_db_id` | **Do not convert** | Ordinary column alias |

**Key insight: in a 10-line SQL, usually only 2-3 dialect-specific constructs need conversion. Most of the SQL is standard syntax and needs no changes. Your skill lies in quickly identifying "what needs conversion", not "how to rewrite the entire SQL".**

---

## How to Judge "What Needs Conversion"

### Standard SQL Whitelist (seeing these = do not convert)

The following syntax is written identically across all mainstream databases (Presto, Spark, Hive, MaxCompute, ClickHouse) — **no rule lookup needed; keep them as-is**:

| Category | Keywords/functions |
|---|---|
| Aggregate functions | `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`, `COUNT(DISTINCT)` |
| Flow control | `CASE WHEN ... THEN ... ELSE ... END`, `IF()`, `COALESCE`, `NULLIF` |
| JOIN | `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`, `CROSS JOIN`, `ON` |
| Clauses | `WHERE`, `GROUP BY`, `ORDER BY`, `HAVING`, `LIMIT`, `UNION ALL` |
| Strings | `CONCAT`, `SUBSTRING`, `TRIM`, `UPPER`, `LOWER`, `LIKE`, `IN` |
| Type casting | `CAST(... AS INT/BIGINT/DOUBLE/DECIMAL/BOOLEAN/DATE/TIMESTAMP)` |
| Math | `+`, `-`, `*`, `/`, `%`, `ABS`, `ROUND`, `FLOOR`, `CEIL` |
| Literals | String `'hello'`, number `123`, `NULL`, `TRUE`/`FALSE` |
| Table operations | `INSERT OVERWRITE`, `FROM`, `SELECT`, `AS` (alias) |

### Quick Reference for Dialect-Specific Syntax (seeing these = look up the rules)

Taking presto→spark as an example. The lookup method is the same for other dialects; only the rule contents differ.

| Seeing this in the SQL | Which category to look up | Conversion direction | ⚠️ Notes |
|---|---|---|---|
| `VARCHAR` (in CAST or column definitions) | `functions/type-conversion` or `functions/string-functions` | → `STRING` | — |
| `INTEGER` | `functions/type-conversion` | → `INT` | — |
| `REAL` | `functions/type-conversion` | → `FLOAT` | — |
| `VARBINARY` | `functions/string-functions` | → `BINARY` | — |
| `TRY(CAST(...))` | `functions/type-conversion` | → `TRY_CAST(...)` | Remove the TRY wrapper |
| `CAST(double AS INTEGER)` | `functions/type-conversion` | → `CAST(ROUND(double) AS INT)` | **Presto rounds, Spark truncates!** |
| `DATE_PARSE(str, '%Y-%m-%d')` | `functions/date-functions` | → `TO_TIMESTAMP(str, 'yyyy-MM-dd')` | **The format string must be converted too** |
| `FORMAT_DATETIME(ts, fmt)` | `functions/date-functions` | → `DATE_FORMAT(ts, fmt)` | Format string unchanged |
| `DATE_ADD('day', n, expr)` | `functions/date-functions` | → `expr + INTERVAL n DAY` | Arguments restructured |
| `DATE_DIFF('day', a, b)` | `functions/date-functions` | → `DATEDIFF(b, a)` | **Argument order reversed** |
| `INTERVAL '7' DAY` | `functions/date-functions` | → `INTERVAL 7 DAY` | Remove the quotes |
| `UNNEST(ARRAY[...])` | `query/cte` | → `LATERAL VIEW EXPLODE(ARRAY(...))` | Square brackets → parentheses |
| `JSON_EXTRACT_SCALAR(j, path)` | `scenarios/json` | → `GET_JSON_OBJECT(j, path)` | — |
| `STRPOS(s, p)` | `functions/string-functions` | → `LOCATE(p, s)` | **Argument order reversed** |
| `SPLIT_PART(s, d, i)` | `functions/string-functions` | → `SPLIT(s, d)[i-1]` | **Index minus 1** |
| `ARBITRARY(expr)` | `functions/aggregate` | → `FIRST(expr)` | — |
| `SET_AGG(expr)` | `functions/aggregate` | → `COLLECT_SET(expr)` | — |
| `RANDOM()` | `functions/math-functions` | → `RAND()` | — |
| `FETCH FIRST n ROWS ONLY` | `query/set-operations` | → `LIMIT n` | — |

**Not sure?** Look up a few more categories. Better to spend 30 seconds checking one extra category than miss a conversion and cause a DryRun failure.

### Date Format String Mapping

For `DATE_PARSE` → `TO_TIMESTAMP`, **the format string syntax differs** (Presto uses strftime, Spark uses Java SimpleDateFormat):

| Presto | Spark | Meaning |
|---|---|---|
| `%Y` | `yyyy` | Four-digit year |
| `%m` | `MM` | Month |
| `%d` | `dd` | Day |
| `%H` | `HH` | 24-hour |
| `%i` | `mm` | Minute |
| `%s` | `ss` | Second |

⚠️ The format strings of `FORMAT_DATETIME` use the Java format on both sides — **the format string does not need conversion**.

---

## Common Pitfalls: The Correct Judgment When You See X

### Pitfall 1: Seeing `DATE_PARSE`, changing the function name but forgetting the format string

You see `date_parse(T1.effect_date, '%Y-%m-%d')`. Your instinct: change `date_parse` to `TO_TIMESTAMP`.

**❌ Result:** `TO_TIMESTAMP(T1.effect_date, '%Y-%m-%d')` — Spark does not recognize `%Y`; execution fails with an error

**✅ Correct judgment:** The format string of `DATE_PARSE` uses strftime syntax (`%Y`, `%m`), while `TO_TIMESTAMP` requires the Java format (`yyyy`, `MM`). The function name and the format string **must be converted together**.

Correct: `TO_TIMESTAMP(T1.effect_date, 'yyyy-MM-dd')`

Contrast: `FORMAT_DATETIME(ts, 'yyyy-MM-dd HH:mm:ss')` → `DATE_FORMAT(ts, 'yyyy-MM-dd HH:mm:ss')` — the format string is in the Java format on both sides, so **the format string does not need conversion**.

### Pitfall 2: Seeing `CAST(double AS INTEGER)` and only changing the keyword

You see `CAST(score AS INTEGER)`, where score is a DOUBLE column. Your instinct: `INTEGER` → `INT`.

**❌ Result:** `CAST(score AS INT)` — in Presto 120.5→121 (rounding), in Spark 120.5→120 (truncation); **the numeric semantics have changed**

**✅ Correct judgment:** This is not a simple type-keyword replacement. Presto and Spark differ in their double→int rounding behavior. Rule `type_cast_double_to_int` requires adding `ROUND`.

Correct: `CAST(ROUND(score) AS INT)`

### Pitfall 3: Seeing nested functions and changing parts that should not change

You see (a real benchmark pattern):
```sql
format_datetime(from_unixtime(cast(created_at as double)), 'yyyy-MM-dd HH:mm:ss')
```

Your instinct: change everything that "looks like a Presto function" — change `from_unixtime` to uppercase `FROM_UNIXTIME`, change `cast(...as double)` to `cast(...as DOUBLE)`.

**❌ Result:** The formatting changes; it does not affect execution, but the diff noise is large and the evaluation framework may report FAIL

**✅ Correct judgment:** Judge function by function. `format_datetime` → Presto-specific, needs conversion. `from_unixtime` → **Spark has the identical function**, do not convert. `cast(...as double)` → standard SQL, do not convert.

Correct: change only `format_datetime` → `DATE_FORMAT`, keeping everything else character by character:
```sql
DATE_FORMAT(from_unixtime(cast(created_at as double)), 'yyyy-MM-dd HH:mm:ss')
```

### Pitfall 4: Seeing `DATE_DIFF` and directly replacing the function name

You see `DATE_DIFF('day', start_date, end_date)`. Your instinct: change it to `DATEDIFF(start_date, end_date)`.

**❌ Result:** Spark's `DATEDIFF(a, b)` computes a-b, while Presto's `DATE_DIFF('day', a, b)` computes b-a. **The argument order is reversed**, and the result becomes negative.

**✅ Correct judgment:** Besides changing the function name, the argument order must also be reversed.

Correct: `DATEDIFF(end_date, start_date)`

### Pitfall 5: Seeing multi-column `UNNEST` expansion and directly changing it to EXPLODE

You see (a real benchmark pattern):
```sql
cross join UNNEST(
    ARRAY['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    , ARRAY[T1.jan_amt,T1.feb_amt,T1.mar_amt,...]
) as T2(mn, budget_amount)
```

Your instinct: change `UNNEST` to `LATERAL VIEW EXPLODE`.

**❌ Result:** `LATERAL VIEW EXPLODE` only supports exploding a single array/column, not multiple columns. Spark execution reports a syntax error.

**✅ Correct judgment:** Multi-column UNNEST has no direct Spark counterpart. Mark it as "⚠️ Uncertain point: multi-column UNNEST has no direct Spark equivalent; may require `POSEXPLODE` + index joining or `INLINE(ARRAYS_ZIP(...))`" and leave the decision to the user.

### Pitfall 6: Seeing `STRPOS` or `SPLIT_PART` and directly replacing the function name

You see `STRPOS(name, 'test')`. Your instinct: change it to `LOCATE(name, 'test')`.

**❌ Result:** The argument order of `LOCATE` is `(pattern, string)`, the reverse of `STRPOS(string, pattern)`. The query returns wrong results.

**✅ Correct judgment:**
- `STRPOS(str, pattern)` → `LOCATE(pattern, str)` — arguments reversed
- `SPLIT_PART(str, delim, index)` → `SPLIT(str, delim)[index-1]` — Presto starts at 1, Spark arrays start at 0

### Pitfall 7: Using the Write tool to rewrite the whole SQL, losing trailing spaces

You see a source SQL line with a trailing space: `ON T8.lotno = T5.FLot and t8.samplecode = T7.FNUMBER `. You manually rewrite the entire SQL with the Write tool.

**❌ Result:** The Write tool strips trailing spaces and alters indentation. The character-by-character comparison in the evaluation framework reports FAIL.

**✅ Correct judgment:** Always use Python `str.replace()` for precise replacements; never rewrite the whole file with the Write tool. See the "Format Preservation" section below.

### Pitfall 8: Adding comments to the output SQL

You finish the conversion and want to add `-- Converted from Presto to Spark` or `-- [WARNING] this rule is unsupported` at the top of result.sql.

**❌ Result:** Downstream systems execute your result.sql directly; extra comments are pollution.

**✅ Correct judgment:** Write WARNINGs to stderr or status.json — **never into result.sql**. Comments already present in the source SQL must be preserved.

### Pitfall 9: Modifying table names / catalog / naming hierarchy on your own

You see that table references in the source SQL use some multi-part naming (e.g., `c1.s1.t1`). Your instinct: the target engine "should" get a catalog prefix, or the naming of different tables should be "unified", or a database name you believe is wrong should be "corrected".

**❌ Result:** Inconsistent naming hierarchies appear in the same SQL (e.g., the target table gets a prefix while the source tables do not), causing catalog / namespace mixing; many engines do not support cross-namespace references, and the entire SQL fails. Even without errors, the actual target of the tables has changed and the semantics are corrupted.

**✅ Correct judgment:** Table names / database names / catalog / schema / naming hierarchy are not "dialect syntax"; no rule asks you to change them. Preserve every table reference in the source SQL character by character — no additions, no deletions, no modifications. The default catalog / namespace is the execution environment's concern, not the conversion's.

### Pitfall 10: Skipping an existing rule because of uncertain details

You see `datediff(stockout_time, stockout_date)` and find rule `datediff_12`, which requires converting to `DATEDIFF(TO_DATE(..., 'fmt'), TO_DATE(..., 'fmt'), 'dd')`. But the example format string is `'yyyy-MM-dd'`, while you suspect the business field may be `'yyyymmdd'`. Your instinct: since you cannot be 100% sure about the format string, just "keep it as-is".

**❌ Result:** A clear dialect conversion is missed; the target side fails at execution due to argument type mismatch, or returns wrong results.

**✅ Correct judgment:** **"Rule exists → convert per the rule" takes precedence over "uncertain → keep as-is".** The latter only applies when **no corresponding rule exists** or **the rule pattern cannot be matched at all**. When a rule exists but parameter details (such as the format string or unit) are uncertain, you must **convert per the rule first** (parameter values may be reasonably inferred from context), then validate with DryRun and iterate on repairs. Skipping the rule amounts to ignoring the rule handbook.

Correct: first convert to `DATEDIFF(TO_DATE(stockout_time, 'yyyymmdd'), TO_DATE(stockout_date, 'yyyymmdd'), 'dd')`; if DryRun reports a format error, adjust the format string then.

---

## Format Preservation

### Why This Is a High-Frequency Failure Cause

The evaluation framework performs a **character-by-character comparison** of the conversion result. Any character change not required by a rule (including spaces, line breaks, and casing) leads to FAIL.

The agent's most frequent mistake is "casually" modifying the format: unifying keyword casing, adjusting indentation, removing trailing spaces, repositioning commas. None of these is "conversion" — they are noise.

### Correct Approach: Precise Replacement with Python

```python
# ✅ Put the source SQL into a Python variable and only perform the replacements required by rules
original = r"""...complete source SQL, character for character (including trailing spaces)..."""
converted = original
converted = converted.replace('format_datetime(', 'DATE_FORMAT(')
converted = converted.replace('json_extract_scalar(', 'GET_JSON_OBJECT(')
# ... one replace per rule

# Write out
import os
os.makedirs('.migration-state/{job_id}', exist_ok=True)
with open('.migration-state/{job_id}/result.sql', 'w') as f:
    f.write(converted)

# Self-check: confirm only lines required by rules changed
import difflib
for line in difflib.unified_diff(original.splitlines(), converted.splitlines(), lineterm=''):
    print(line)
# The diff must not contain indentation changes, blank-line changes, or casing changes
```

**❌ Wrong approach:** manually rewriting the whole SQL with the Write tool → trailing spaces lost, indentation style changed

### Things That Must Not Be Changed (complete list)

Line-break positions and counts, indentation (tab vs space, indent width), blank lines, keyword casing (`SELECT` vs `select`), comma position (leading `,col` vs trailing `col,`), parenthesis placement, comment content and position, literals (`'中国'`, `'2026-01-01'`, numeric precision), column constraints (`NULL`, `NOT NULL`, `DEFAULT`, `COMMENT`), trailing semicolons, multi-statement structure.

**Identifiers are the disaster zone and deserve special emphasis:** all table names, database names, column names, catalog / schema / namespace prefixes, and the naming hierarchy (number of parts) of table references — unless an explicit rule id requires it, they must be preserved character by character; additions, deletions, and modifications are strictly forbidden.

**⚠️ Wrap the source SQL in a Python raw string (`r"""..."""`) to avoid backslash escaping issues.**

---

## Execution Flow

### Flags

| Flag | Description |
|---|---|
| (none) | Default: conversion + DryRun |
| `--no-dryrun` | Offline: rule conversion only, skip DryRun |
| `--eval-batch` | Batch: JSON array input, convert + DryRun per item |
| `--rule-audit` | With batch, additionally output the ids of triggered rules |

Flags appear at the **very beginning** of the user message; remove them once recognized.

> **⚠️ SQL safety notice: if a data source is configured during SQL conversion, the conversion result will be tested in the target environment. Never test dangerous SQL in a production environment.**

### Environment Pre-Check

**Before starting the conversion, the environment pre-check must be run first:**

```bash
python3 ${SKILL_HOME}/scripts/check_env.py --target {target}
```

The script returns the environment check result (whether it is ready, missing configuration items, configuration guidance).

**Handling the pre-check result:**
- Environment ready → perform the conversion normally (including validation)
- Environment not ready → skip validation and run in downgrade mode

**When DryRun is skipped, output the downgrade declaration matching the cause (format see "Downgrade Declaration Templates" in the main SKILL.md):**
- **Cause A — user configuration incomplete** (`check_env.py` returned `ready=false` with missing fields) → **Declaration A** (guides the user to fill in `~/.lhm/credentials.json`).
- **Cause B — tooling / infrastructure problem** (`check_env.py` is unavailable or cannot run, or DryRun failed 2 consecutive rounds for infrastructure reasons per "Iterative Repair Details") → **Declaration B**. Do **not** claim the configuration is incomplete and do **not** ask the user to fill in credentials — that is not the cause.

The declaration must always be fixed at the very beginning of all output content, highly prominent, and must not be hidden in collapsed sections or at the end.

### 🔵 Batch Mode Context Injection

When invoked by the batch dispatcher, the following steps have already been completed by the dispatcher and the subagent should skip them:

| Step | Completed by the dispatcher | Subagent behavior |
|---|---|---|
| Environment pre-check | ✅ Checked | Use the environment state (ready/degraded) passed by the dispatcher |
| Rule browsing/lookup | ✅ Fully prefetched to a file | Read the prefetched rule file; do not invoke `lookup_rules.py` |

The subagent starts execution directly from the "line-by-line scan of the SQL" step.

### Conversion Flow

```
0. Environment pre-check: python3 ${SKILL_HOME}/scripts/check_env.py --target {target}
   ↓ Environment ready → continue
   ↓ Environment not ready → skip validation and output the downgrade declaration

2. Browse rule categories: python3 ${SKILL_HOME}/scripts/lookup_rules.py --source {source} --target {target} --list-categories
   ↓
3. Scan the SQL, identify dialect features → select relevant categories
   ↓
4. Look up rule details: python3 ${SKILL_HOME}/scripts/lookup_rules.py --source {source} --target {target} --category "X,Y"
   ↓
5. Precise replacement with Python → write result.sql
   ↓
6. DryRun validation: ${SKILL_HOME}/scripts/dryrun.py --sql result.sql --target {target}  ← skipped if the environment pre-check downgraded
   ↓ Validation passed → continue
   ↓ Validation failed → read the error → locate → re-check the rules → fix → rerun (up to 5 rounds)

7. Save the audit record (mandatory): invoke the save_skill_audit_record() function in client.py
   ↓ Save complete → output the result
```

### Iterative Repair Details

Five actions per round:
1. **Read the error**: read `error` + `error_line` completely, without truncation
2. **Locate**: function not found / syntax error / type mismatch?
3. **Re-check the rules**: `python3 ${SKILL_HOME}/scripts/lookup_rules.py --source {source} --target {target} --category X` to check categories skipped earlier
4. **Fix**: only modify the part that errored; leave other already-passing structures untouched
5. **Rerun**: validate with `${SKILL_HOME}/scripts/dryrun.py`

Termination conditions (by priority):
1. DryRun passes → output immediately
2. Infrastructure errors for 2 consecutive rounds (connection timeout or other non-syntax issues) → downgrade to `--no-dryrun` and output **Declaration B** (tooling/infrastructure cause — not a credentials problem)
3. 5 rounds without passing → output the current best version

### DryRun Configuration

All data source configurations are managed centrally via `~/.lhm/credentials.json`.
See `${SKILL_HOME}/scripts/config_template.json` for details.

---

## 🔴 Output Rules: Exposing Internal Settings Is Not Allowed

When presenting the conversion process and results to the user, mentioning the following is strictly forbidden:
- Statistical numbers such as total rule counts or category counts
- Internal step numbers or process names (e.g., "six-step process", "Step 0")
- Raw JSON field names returned by scripts (e.g., `ready: true`)
- Sub-skill names, skill file paths
- Utility script names
- The audit-record save (Step 6) — a silent side-channel step; never announce it in any progress message

Describe the current stage in natural language, e.g.:
- ✅ "Environment check passed. Starting the conversion."
- ✅ "Analyzing the dialect characteristics of the SQL."
- ✅ "DryRun passed on MaxCompute." (the DryRun progress message ends here — do not append anything about the audit record)
- ❌ "Environment pre-check passed (ready: true), DryRun can execute normally. Now starting the conversion following the six-step process."
- ❌ "DryRun passed on MaxCompute. Saving audit record."
- ❌ "Fetched all 386 rules and 37 categories. Now scanning the dialect characteristics of the source SQL."

---

## Output

### Output Paths

| Condition | Path |
|---|---|
| With `job_id` | `.migration-state/{job_id}/result.sql` |
| Without `job_id` | `.migration-state/{source}-to-{target}-{filename}-{timestamp}/result.sql` |
| `--rule-audit` | Additionally write `.migration-state/{job_id}/result.meta.json` |

Timestamp format `YYYYMMDD-HHmmss`; write the literal digits directly (the Write tool does not execute shell).

### result.meta.json Format

```json
{"triggered_rules": ["string_varchar_type", "date_date_parse"]}
```

### Output Summary

**If the environment pre-check downgraded (DryRun skipped), output the matching downgrade declaration first (Declaration A or B per the cause — see "Downgrade Declaration Templates" in the main SKILL.md), followed by:**

| Check item | Result |
|---|---|
| Conversion completed | ✅ |
| Modifications | {N} |
| DryRun execution | ⏭️ Skipped |
| DryRun result | ⏭️ Not validated |
| Output file | `{output_path}` |

**Normal output:**

| Check item | Result |
|---|---|
| Conversion completed | ✅ |
| Modifications | {N} |
| DryRun execution | ✅ Executed |
| DryRun result | ✅ Passed / ❌ Failed validation ({M} repair rounds) |
| Output file | `{output_path}` |

---

## Batch Mode (`--eval-batch`)

Input JSON array: `[{"id": "case_001", "sql": "SELECT ..."}, ...]`

Run the full process (conversion + DryRun) per item; after all items complete, write `.migration-state/{batch_job_id}/batch_result.json`:

```json
{"case_001": "SELECT ...", "case_002": "SELECT ..."}
```

Self-check: Read the file to confirm the key count matches, there are no nulls, and every item went through dryrun.

The output says only one sentence: "Batch conversion completed, N items in total, all DryRun passed."

---

## Tool Inventory

| Tool | Purpose |
|---|---|
| `python3 ${SKILL_HOME}/scripts/check_env.py --target tgt` | Environment pre-check (checks whether the DryRun configuration is ready) |
| `client.py → save_skill_audit_record()` | Save the audit record (mandatory after conversion completes) |
| `python3 ${SKILL_HOME}/scripts/lookup_rules.py --list-categories` | Browse the rule catalog |
| `python3 ${SKILL_HOME}/scripts/lookup_rules.py --category X` | View category details (comma-separated supported) |
| `${SKILL_HOME}/scripts/dryrun.py --sql file --target tgt` | Syntax validation (EXPLAIN) |
| `${SKILL_HOME}/scripts/get_table_schema.py` | Query the target-side table schema |

## Reference Documents

- Dialect syntax reference: `${SKILL_HOME}/sql-dialects/dialects/{dialect}.md`
- DryRun error patterns: `${SKILL_HOME}/docs/error-patterns.md`
- Development pitfalls: `${SKILL_HOME}/docs/dev-pitfalls.md`
