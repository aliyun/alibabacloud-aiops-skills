# Define alert triggering

Triggering determines whether query results warrant an alert, which severity
applies, and whether repeated qualifying executions are required. Configure
these settings inside the rule's `configuration`.

- [Conditions](trigger-conditions.md): choose which result
  rows or field values qualify; each severity branch has an `evalCondition`.
- [Severity](severity.md): assign levels and order
  the entries in `severityConfigurations`.
- [Consecutive evaluations](#consecutive-evaluations):
  set `threshold` when firing requires repeated qualifying runs.
- [No-data behavior](#no-data-behavior): optionally alert
  when the query produces no data.

For an ordinary rule, use one severity branch, `threshold: 1`, and no-data
firing disabled. Use the [query result shape](../queries/define-alert-queries.md), not discarded raw
logs, to design conditions. Independent per-entity alerts additionally require
[group evaluation](../group-evaluation.md).

## Consecutive evaluations

`configuration.threshold` is the number of consecutive qualifying evaluations
required before firing. Use `1` by default, or a larger value for sustained
conditions. It is independent of the query window and result-row count;
row-count conditions belong in `evalCondition.countCondition`.

## No-data behavior

Set `configuration.noDataFire` only when missing data should trigger an alert;
it is `false` by default. Choose `noDataSeverity` from the [severity scale](severity.md).
A query returning a zero-valued aggregate row has data and is not a no-data result.
