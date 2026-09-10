# Trigger conditions

## Four trigger modes

Each severity branch contains numeric `severity` and an `evalCondition` with
two string fields:

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
to check referenced fields, types, and the intended match. The local rule
validator does not parse expression syntax.
