# Datasource capabilities

## Sources supported by the bundled tools

| Dashboard type | Backing/mode | Build | Online discovery/query |
| --- | --- | --- | --- |
| logstore | Logstore SQL/Scan SQL/SPL | Yes | CLI index, metadata, GetLogsV2 |
| metricstore | Metricstore PromQL | Yes | CLI metrics, labels and queries |
| metricsql | Metricstore SQL | Yes | CLI SQL |
| logstore_storeview | Named log StoreView | Yes | View metadata/index; GetLogsV2 with the view name |
| metricstore_storeview | Metric StoreView PromQL | Yes | Documented SLS metric HTTP API |

Metricstore SQL is a query mode over a Metricstore, not another physical resource.
Views retain their own coordinates; do not substitute a member store.
Use existing named views; these tools do not assemble temporary multi-store queries.

See [Logstore](logstore.md), [Metricstore](metricstore.md), [StoreView](storeview.md),
and [SLS commands](api.md) for their query and discovery contracts.

## Other Dashboard JSON sources

| Datasource | Purpose | Reference |
| --- | --- | --- |
| builtin | Local simulated data for chart demonstrations and static image display | [Builtin](builtin.md) |
| prometheus | PromQL against an identified Prometheus instance | [Prometheus query entries](../queries/promql.md#prometheus-datasource) |
| metricsql_storeview | SQL-mode entries targeting a named metric view | [MetricsQL StoreView entries](storeview.md#metricsql-storeview-entries) |

Builtin Dashboard JSON can be validated and published. Plan builds automatically
add builtin data to imagePro charts with no queries; see [image configuration](../charts/imagepro.md).

For prometheus and metricsql_storeview, baseline-aware validation preserves an entirely unchanged chart as unchecked;
this is not validation of its datasource. Do not replace its datasource identifier
or resource coordinates to bypass a tool restriction.
