# Index Search

## Purpose and features

Index search filters logs using indexed content and returns matching records. It can run on
its own or provide the input filter before SQL or SPL processing.

For searchable fields and matching rules, see
[index field coverage](../index/index-configuration.md#field-coverage) and
[text matching](../index/index-configuration.md#text-matching).

## Basic syntax

```text
index_search_statement
```

| Operation | Example |
| --- | --- |
| No additional filter | `*` |
| Full-text search (no field name) | `GET or POST` |
| Field search | `request_method:GET` |
| Field existence | `key:*` |
| Field absence | `not key:*` |
| Empty field value | `key:""` |
| JSON subfield | `payload.status:success` |
| Combined conditions | `(request_method:GET or request_method:POST) and status:200 not request_uri:"/health"` |
| Numeric comparison | `request_time > 100` |
| Numeric range | `request_time in [100 200)` |
| Field name containing spaces | `"request method":PUT` |

`key:*` checks existence, including an empty string. Use `key:""` to search for an empty value;
`not key:*` searches for a missing field.

For a numeric range, square brackets include a boundary and parentheses exclude it. Separate
the two bounds with a space. The `in` operator must be lowercase; other search operators are
case-insensitive. `and` and `not` take precedence over `or`; use parentheses to make Boolean grouping explicit.

Quote field names or values containing special characters or reserved words with double
quotes. Text matching depends on indexed tokens: double quotes do not make a tokenized field
comparison equivalent to whole-field equality.

## Specialized search

Prefer ordinary index searches using complete terms, field predicates, and numeric ranges
when they meet the request. Phrase and fuzzy search are lower-priority choices: use them
only when their specific matching behavior is needed and the limitations below are acceptable.

### Phrase search

Consider phrase search when ordinary keyword matching returns too much because it does not
enforce adjacency or order, for example an error-message fragment:
`body:#"connection timed out"`.

It is suited to inspecting matching raw logs. It cannot be
combined with wildcards, `not`, or SQL analysis; the histogram counts ordinary-search
candidates rather than final phrase matches. For substring filtering followed by aggregation,
consider SQL `LIKE` or regular expressions instead, with the required analysis indexes.
See [Phrase search](phrase-search.md) for matching semantics and retrieval limits.

### Fuzzy search

Consider fuzzy search for exploratory lookup when only part of an indexed term is known,
for example `host:api*`. Prefer a complete term when available.

Fuzzy search matches at most 100 terms, so matching logs may be omitted. For complete
results, accurate counts, or exhaustive exclusion, consider SQL `LIKE` or regular
expressions with the required analysis indexes; retain ordinary index predicates
before the pipe to narrow the input.

- `*` matches zero or more characters; `?` matches one character within a token. Matching does
  not cross token-delimiter boundaries.
- The documented search-term length limit is 64 characters. Wildcards can appear inside a
  term or at its end, but not at the beginning.
- Fuzzy search applies to text, not `long` or `double` indexes; use numeric ranges for numeric fields.
- The 100-term limit is not a limit of 100 logs. Short prefixes are more likely to exceed it.
- With `not`, terms outside those 100 matches may remain in the result even though they match
  the wildcard pattern. Do not rely on a broad fuzzy predicate for exhaustive exclusion.

See [fuzzy-query behavior](https://help.aliyun.com/zh/sls/how-do-i-query-logs-by-using-fuzzy-match)
and [query syntax](https://help.aliyun.com/zh/sls/query-syntax) for the matching process and limits.

## Pagination and log counts

For ordinary index search, use `--line` and `--offset`. Keep the search condition
and sort direction unchanged between pages.
`meta.count` is the number of records in the response, not the total number of matching logs.
Assess [result precision](query-execution.md#result-precision) before using the result.

Use `aliyun sls histogram`
with the same search condition and query time range to obtain the distribution of matching logs over
time. Specify either `--time-range` or both `--from` and `--to`. For an exact comparison with a
separate query, use the same absolute time bounds for both commands. Each interval has a `count`;
sum the interval counts to obtain the total. Check that the
histogram results are complete before using them as the full count.

## References

- [Index query behavior](../index/index-configuration.md#query-behavior)
- [Query syntax and examples](https://help.aliyun.com/zh/sls/query-syntax)
- [Indexed query behavior and limits](https://help.aliyun.com/zh/sls/query-and-analyze-logs-in-index-mode/)
