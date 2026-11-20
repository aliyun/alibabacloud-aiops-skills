# Datasource capabilities

## Plan sources

| Dashboard type | Query mode | Discovery |
| --- | --- | --- |
| logstore | Logstore SQL/Scan SQL/SPL | Metadata, indexes and sample rows |
| metricstore | Metricstore PromQL | Metrics and labels |
| metricsql | Metricstore SQL | Metricstore metadata |
| logstore_storeview | Named log StoreView queries | View metadata, member indexes and sample rows |
| metricstore_storeview | Metric StoreView PromQL | Metrics and label series |

Metricstore SQL is a query mode over a Metricstore, not another physical resource.
Views retain their own coordinates; do not substitute a member store.
Use existing named views.

See [Logstore](logstore.md), [Metricstore](metricstore.md), [StoreView](storeview.md),
and [CLI commands](../related-apis.md) for their query and discovery contracts.

## Other Dashboard JSON sources

| Datasource | Purpose | Reference |
| --- | --- | --- |
| builtin | Local simulated data for chart demonstrations and static image display | [Builtin](builtin.md) |
| prometheus | PromQL against an identified Prometheus instance | [Prometheus query entries](prometheus.md#prometheus-datasource) |
| metricsql_storeview | SQL-mode entries targeting a named metric view | [MetricsQL StoreView entries](storeview.md#metricsql-storeview-entries) |

Builtin Dashboard JSON can be validated and published. Plan builds automatically
add builtin data to imagePro charts with no queries; see [image configuration](../charts/imagepro.md).

Edit `prometheus` and `metricsql_storeview` entries directly in Dashboard JSON,
retaining their datasource identifiers and resource coordinates. Review reported
unknown values through [update validation](../validation/checks.md#update-validation).
