# Define alert triggering

Triggering determines whether query results warrant an alert, which severity
applies, and whether repeated qualifying executions are required. Configure
these settings inside the rule's `configuration`.

- [Conditions](#four-trigger-modes): choose which result
  rows or field values qualify; use optional `evalCondition` fields in each severity branch.
- [Severity](#severity-order-is-semantic): assign levels and order
  the entries in `severityConfigurations`.
- [Consecutive evaluations](#consecutive-evaluations):
  set `threshold` when firing requires repeated qualifying runs.
- [No-data behavior](#no-data-behavior): optionally alert
  when the query produces no data.

For an ordinary rule, use one severity branch, `threshold: 1`, and no-data
firing disabled. Use the [query result shape](../queries/define-alert-queries.md), not discarded raw
logs, to design conditions. Independent per-entity alerts additionally require
[group evaluation](../group-evaluation.md).

## Four trigger modes

Each severity branch contains numeric `severity`. `evalCondition` is optional;
when present, its `condition` and `countCondition` fields are optional strings.
Missing/null fields and an empty object are accepted. An empty count condition
uses `__count__ > 0`. For a new draft, the following explicit values make the
intended trigger clear:

| Desired trigger | `evalCondition.condition` | `evalCondition.countCondition` |
| --- | --- | --- |
| Any data | `""` | `""` |
| A specified number of rows | `""` | `"__count__ >= 5"` |
| Any data matching a field condition | `"errorCount > 0"` | `""` |
| A specified number of rows matching a field condition | `"latency > 100"` | `"__count__ >= 5"` |

For the fourth mode, SLS first keeps rows matching `condition`, then applies the
count predicate. `__count__` is the number of result rows at this evaluation
stage; it is not an SQL aggregate alias. If the query returns
`count(*) as errorCount`, compare `errorCount` in `condition` instead.

For new or changed expressions, check operators, field-name quoting, regex,
query prefixes, and escaping against [evaluation syntax](expressions.md).
Use representative [query results](../queries/verify-alert-query.md#validate-a-new-or-changed-query)
to check referenced fields, types, and the intended match.

## Severity order is semantic

One severity branch is enough for an ordinary alert. When the requirement maps
different conditions to different levels, SLS evaluates branches from top to
bottom and stops at the first match. Use this order whenever those levels are
present:

| Level | Numeric `severity` |
| --- | --- |
| Critical | `10` |
| High | `8` |
| Medium | `6` |
| Low | `4` |
| Report | `2` |

Larger values mean greater severity. This same scale applies to notification
policy conditions; it is not a 1-based priority ranking. See the
[official severity mapping](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-an-alert-monitoring-rule).

Include only the required levels, but never place a broader lower-severity
condition before a higher one. This configuration reports Critical for 100 or
more errors and High for 20 through 99:

```json
[
  {
    "severity": 10,
    "evalCondition": {
      "condition": "errorCount >= 100",
      "countCondition": ""
    }
  },
  {
    "severity": 8,
    "evalCondition": {
      "condition": "errorCount >= 20",
      "countCondition": ""
    }
  }
]
```

## Consecutive evaluations

`configuration.threshold` is the number of consecutive qualifying evaluations
required before firing. Use `1` by default, or a larger value for sustained
conditions. It is independent of the query window and result-row count;
row-count conditions belong in `evalCondition.countCondition`.

## No-data behavior

Set `configuration.noDataFire` only when missing data should trigger an alert;
it is `false` by default. Choose `noDataSeverity` from the [severity scale](#severity-order-is-semantic).
A query returning a zero-valued aggregate row has data and is not a no-data result.
