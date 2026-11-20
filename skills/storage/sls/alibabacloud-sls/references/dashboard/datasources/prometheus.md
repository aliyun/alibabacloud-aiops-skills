# Prometheus datasource

Saved queries with `datasource="prometheus"` identify a Prometheus instance, not an
SLS Metricstore. Edit these entries directly in Dashboard JSON, preserving the
instance identity.

Paths are relative to `chart.search.chartQueries[]`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | None | Query ID used by chart bindings. |
| `datasource` | string | Yes | None | prometheus. |
| `regionId` | string | For an explicit instance | None | Instance region. |
| `clusterId` | string | For an explicit instance | None | Prometheus instance ID, not an SLS Logstore name. |
| `expr / tokenQuery / query` | string | Yes | None | PromQL expression; non-empty expr takes precedence over tokenQuery, then query. |
| `range` | boolean | No | true | true returns range samples; false evaluates at one time. |
| `instant` | boolean | No | false | true overrides range and forces an instant query; use range for new entries. |
| `format` | string | No | time_series | time_series returns numeric series fields; table exposes labels as columns. |
| `interval` | string | No | Automatic | Range evaluation step, such as 60s or 1m. |
| `legendFormat` | string | No | Metric name and labels | Series-name template using {{label}}. Missing labels leave empty text; a wholly empty name uses the default. Applies to time_series, not table. |

With `time_series`, the result has `time` and one numeric field per series. Unlike
Metricstore, the formatted series name is also that field's name: bind the
returned name, not an assumed `value` field. Retain labels that distinguish series.

With `table`, each sample is a row with `Time`, label columns and `Value`.
Multiple table queries use value columns such as `Value #A` and `Value #B`.
`range=false` gives one sample per series; it does not combine multiple series.

Example query entry; replace the instance ID and use metric and label names from
that instance:

```json
{
  "name": "A",
  "datasource": "prometheus",
  "regionId": "cn-hangzhou",
  "clusterId": "<prometheus-instance-id>",
  "expr": "sum by (service) (rate(http_requests_total[5m]))",
  "range": true,
  "format": "time_series",
  "interval": "60s",
  "legendFormat": "{{service}}"
}
```
