# Scan analysis (SCAN)

When required fields are not indexed, or fields required for SQL analysis do not have statistical analysis enabled, you can query by scanning the raw logs.

```sql
<search-prefix> | set session mode=scan; <SQL-analysis-statement>
```

- When the search prefix references unindexed fields, rewrite the relevant filters into SQL `WHERE`, preserving the original condition combinations and matching semantics. Tokenized search cannot be replaced directly by complete field equality.
- All fields are treated as `varchar`, including fields with numeric indexes. Cast types explicitly for numeric calculations.
- Select output fields or expressions explicitly; `SELECT *` is unsupported.
- Retain effective index prefilters to reduce scan volume without changing query semantics.
- SCAN is billed by data scanned and has a scan-volume limit. Exceeding it returns partial, inaccurate results.
