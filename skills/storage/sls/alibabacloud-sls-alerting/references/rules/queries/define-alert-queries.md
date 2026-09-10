# Alert queries

`configuration.queryList` defines the data sources and result fields used by
trigger conditions. A query can read an authorized source outside the owning Project.

## One ordinary log query

Prefer one `queryList` entry when sufficient. Use multiple queries when needed
to produce the requested result; the user need not specify the implementation.

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

The text before `|` follows SLS search syntax. The text after `|` follows SLS SQL
analysis syntax. A statement without `|` can return matching log rows directly;
an SQL clause can aggregate or shape them. In the example, the next trigger
expression can refer to `errorCount`, for example `errorCount > 0`.

Use the `alibabacloud-sls-query` skill to generate, explain, validate, or
optimize nontrivial SLS search/SQL. Bring its final statement and result-field
names back into this `queryList`; this alerting skill remains responsible for
the rule's data source and time window. Do not invent field names without a log
sample or an existing query.
If the query skill is unavailable, use a supplied/previously verified statement
or construct it from a log sample and the official SLS query documentation.
Do not install another skill implicitly. [Query verification](verify-alert-query.md) provides a fallback for
execution; with no verified query or source fields, report the missing input.

## Result shape drives evaluation

Trigger conditions evaluate the rows and fields returned here, not raw logs that
the query discarded. For example, `select count(*) as errorCount` normally
returns one row even when the aggregate value is zero. That requires a field
condition such as `errorCount > 0`; “any data” would only test whether the result
row exists.

Keep the query window explicit and within the alert service's supported range.
Alert queries use SLS search/SQL semantics; do not substitute Scan/SPL syntax.
Phrase-query and result-size limitations can differ from an interactive console
query, so aggregate and limit deliberately. See the
[official rule-creation guide](https://help.aliyun.com/zh/sls/create-an-alert-monitoring-rule-for-logs)
for current alert-query constraints.

## Open deeper only when needed

- For two or three result sets, read
  [multiple queries and set operations](combine.md).
- To produce and evaluate a separate alert per field value, first shape that
  field in the result, then read
  [independent group evaluation](../group-evaluation.md).
- For cross-account access or a configured role's authorization failure, read
  [cross-account queries](cross-account.md).

Use these result fields in [trigger conditions](../triggering/define-alert-triggering.md).

Before embedding a new or changed query, follow [query verification](verify-alert-query.md).
