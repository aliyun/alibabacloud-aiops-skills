# Alert queries

`configuration.queryList` defines the data sources and result fields used by
trigger conditions. A query can read an authorized source outside the owning Project.

## One ordinary log query

Prefer one `queryList` entry when sufficient. Use multiple queries when needed
to produce the requested result.

| Field | Meaning / usual value |
| --- | --- |
| `storeType` | `log` for a Logstore. |
| `region` | Region containing the data source. |
| `project` | Project containing the data source; it is not necessarily the rule's owning Project. |
| `store` | Logstore name. |
| `query` | SLS search and optional SQL analysis returning the fields used by the trigger. |
| `timeSpanType` | `Relative` for a rolling time window. |
| `start`, `end` | Window boundaries such as `-5m` and `now`. |
| `powerSqlMode` | `auto`, `enable`, or `disable`; prefer `auto` unless the requirement establishes another value. |
| `roleArn` | Omit by default; configure for [cross-account queries](cross-account.md). Preserve existing values on unrelated updates. |

Example: search for error logs, then return one aggregate field named
`errorCount`.

```json
{
  "storeType": "log",
  "region": "cn-hangzhou",
  "project": "example-project",
  "store": "example-logstore",
  "query": "level:ERROR | select count(*) as errorCount",
  "timeSpanType": "Relative",
  "start": "-5m",
  "end": "now",
  "powerSqlMode": "auto"
}
```

The text before `|` follows [SLS search syntax](../../../query/index-search.md#basic-syntax);
the text after it follows [SQL syntax](../../../query/sql/README.md#basic-syntax).
A statement without `|` can return matching log rows directly;
an SQL clause can aggregate or shape them. In the example, the next trigger
expression can refer to `errorCount`, for example `errorCount > 0`.

Existing queries and log samples can inform the statement. Returned aliases and types
determine which fields the trigger expression can use.

## Metric and resource queries

`storeType: metric` selects a Metricstore query. Provide its `store`, query,
and time window, and verify the corresponding metric expression and result
shape before using its fields or [automatic label grouping](../group-evaluation.md).

`storeType: meta` selects resource data: `store` is the resource name and the
optional `query` supplies its Tag filter. It does not require or evaluate a time
window. Verify that the resource is registered and the filter returns the
intended records. `maxRows` is an optional integer.

## Result shape drives evaluation

Trigger conditions evaluate the rows and fields returned here, not raw logs that
the query discarded. For example, `select count(*) as errorCount` normally
returns one row even when the aggregate value is zero. That requires a field
condition such as `errorCount > 0`; “any data” would only test whether the result
row exists.

Keep the query window explicit and within the alert service's supported range.
Log queries use alert-compatible SLS search/SQL syntax.
A raw-log query returns up to 100 logs by default. See the
[official rule-creation guide](https://help.aliyun.com/zh/sls/create-an-alert-monitoring-rule-for-logs)
for current alert-query constraints.

## Related query settings

- For two or three result sets, read
  [multiple queries and set operations](combine.md).
- To produce and evaluate a separate alert per field value, first shape that
  field in the result, then read
  [independent group evaluation](../group-evaluation.md).
- For cross-account access or a configured role's authorization failure, read
  [cross-account queries](cross-account.md).

Use these result fields in [trigger conditions](../triggering/define-alert-triggering.md).

For ways to inspect the inputs to a trigger, see [query results](verify-alert-query.md).
