# Multiple queries and set operations

Use multiple queries when the requested result requires combining independent
result sets, enriching data from another source, or adding query data to a
template. Infer this need from the business requirement; prefer one query when
it can express the requirement clearly.

## Structural rules

- `configuration.queryList` supports at most three entries.
- With one query, omit or use an empty `joinConfigurations` array.
- With two or three queries, `joinConfigurations` is required and its length
  must equal `queryList.length - 1`.
- With three queries, SLS combines queries 0 and 1 first, then combines that
  result with query 2. Order therefore changes the result.
- Omit `roleArn` by default. For entries reading another account's data, see
  [cross-account queries](cross-account.md).

Each join object has `type` and, for conditional joins, `condition`:

| `type` | Operation | Is `condition` required? |
| --- | --- | --- |
| `no_join` | Do not merge; the first set remains the evaluation result | No |
| `cross_join` | Cartesian product | No |
| `concat` | Append rows and align fields | No |
| `inner_join` | Inner join | Yes |
| `left_join` | Left join | Yes |
| `right_join` | Right join | Yes |
| `full_join` | Full join | Yes |
| `left_exclude` | Remove left rows found on the right | Yes |
| `right_exclude` | Remove right rows found on the left | Yes |

Example shape for two queries:

```json
{
  "queryList": [
    {"project": "app-project", "store": "access-log", "query": "* | select host, count(*) as errors group by host"},
    {"project": "inventory-project", "store": "hosts", "query": "* | select host, owner"}
  ],
  "joinConfigurations": [
    {"type": "left_join", "condition": "$0.host == $1.host"}
  ]
}
```

This fragment illustrates join structure only; each `queryList` entry still
needs the complete fields documented in
[query and statistics](define-alert-queries.md).
Use `$0`, `$1`, and `$2` prefixes when an expression must identify the source
query or disambiguate duplicate field names. Trigger evaluation uses the final
combined set; `no_join` keeps later query data available to templates without
making it the evaluation result.

Check join expressions against [evaluation syntax](../triggering/expressions.md)
and verify that the combined result contains the fields used by the trigger.

## Result bounds

SLS normally takes only the first 1000 rows of query/analysis results into set
operations. When there are three queries and no `no_join` operation, it takes
only the first 100 rows from each query. Add deterministic filtering, ordering,
aggregation, and `LIMIT` choices rather than assuming all rows participate.
Template result arrays have additional bounds; see [template data](../../notifications/templates/variables.md).

The error `join configurations and query count should be equal` or
`join config length is invalid` means the join count does not equal the query
count minus one. See the [official rule schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-an-alert-monitoring-rule)
and [set-operation guide](https://help.aliyun.com/zh/sls/set-query-statistics-statement).
