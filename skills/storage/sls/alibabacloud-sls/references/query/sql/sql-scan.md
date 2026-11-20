# SQL SCAN (scan analysis)

## Purpose and features

SQL SCAN reads raw fields and analyzes them with SQL, without requiring indexes on those
analysis fields. It uses SQL syntax and functions, subject to the scan-specific limits below.
For indexed SQL analysis, see [SQL analysis](README.md).

The search before the first pipe can use indexes. The SQL stage extracts fields by scanning;
existing field indexes do not take effect within that analysis stage.

## Basic syntax

```sql
index_search_statement | set session mode=scan; sql_analysis_statement
```

`set session mode=scan;` is part of the query statement, immediately before the SQL analysis.
Use `*` for the search expression when no indexed filter is needed.

Count requests by API, first filtering on indexed `status`:

```sql
status:200 | set session mode=scan;
SELECT api, count(*) AS pv
GROUP BY api
```

Here, `status` needs an index for the search condition. The analysis field `api` does not.

## Field types

SQL SCAN treats fields as `varchar`, even if a field has a numeric index. Use `cast`
when another type is needed:

```sql
status:200 | set session mode=scan;
SELECT api, avg(cast(latency AS bigint)) AS average_latency
GROUP BY api
```

For indexed filters such as `status:200`, placing the condition before `|` reduces the input
that must be scanned. A predicate inside the SQL statement does not use that field index.

## Comparison with SQL analysis

| Aspect | SQL analysis (indexed analysis) | SQL SCAN |
| --- | --- | --- |
| Syntax | `index_search_statement \| sql_analysis_statement` | `index_search_statement \| set session mode=scan; sql_analysis_statement` |
| Index requirements | Analysis fields need field indexes with analytics enabled. | Analysis fields do not need indexes; the search before `\|` still relies on indexes. |
| SQL support | Supports SLS SQL syntax and functions. | Supports the same SQL syntax and functions, subject to the scan-specific restrictions below. |
| Analysis capacity | Supports datasets at the scale of hundreds of millions of records; Dedicated SQL provides greater capacity. | Lower capacity, suited to datasets at the scale of millions of records. Use indexed prefilters to reduce larger inputs. |

Source: [Official comparison of scan and indexed analysis](https://help.aliyun.com/zh/sls/scan-based-analysis-syntax#title-nb0-05h-oah).

## Limits

- The documented input limits are 500,000 logs per Shard and 10,000,000 logs in total, after
  any preceding search filtering. Exceeding these limits returns calculations over partial
  input and marks the result inaccurate.
- `* | SELECT *` is not supported in SQL SCAN.
- When joining multiple Logstores, qualify field names as `LogstoreName.key`.

To reduce the scanned input, use indexed prefilters or a smaller query time range. For large
structured datasets, the official documentation recommends indexed analysis with field indexes
and analytics enabled.

SQL syntax, functions, and final-result `LIMIT` behavior are covered in [SQL analysis](README.md).

## References

- [Official scan-analysis syntax and limits](https://help.aliyun.com/zh/sls/scan-based-analysis-syntax).
