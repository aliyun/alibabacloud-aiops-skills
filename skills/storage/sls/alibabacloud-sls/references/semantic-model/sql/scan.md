# Scan Analysis (SCAN)

See [query mode selection](../../query/entry.md#2-choose-a-query-mode) and
[SQL SCAN](../../query/sql/sql-scan.md) for mode selection, syntax and scan-specific limits.

You can scan raw logs when a required field has no index or a field needed for SQL analysis does not have SQL analysis enabled.

```sql
<search-prefix> | set session mode=scan; <SQL-statement>
```

- If the search prefix references unindexed fields, rewrite the relevant filters into SQL `WHERE`, preserving the original condition combinations and matching semantics. Tokenized searches cannot be replaced directly with whole-field equality.
- All fields are treated as `varchar`, including fields configured with numeric indexes. Cast types explicitly for numeric calculations.
- Select output fields or expressions explicitly; `SELECT *` is unsupported.
- Preserve effective index-based prefilters where query semantics remain unchanged, to reduce the amount of data scanned.
- SCAN is billed by the amount of data scanned and has scan-volume limits. Exceeding those limits returns partial, inexact results.
