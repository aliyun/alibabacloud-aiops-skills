# Grafana Dashboard Rules

## Metric Metadata Query

**Before generating panels**, query metric metadata via `aliyun cms2 meta metrics --meta-format PROM_BASIC`:

- **metric type → PromQL pattern**:
  - `counter` → `rate()` / `increase()`
  - `gauge` → raw value or aggregation
- **dimensions → template variables**: label keys become Grafana variables (`$instance_id`, etc.) and `legendFormat`

## Alibaba Cloud Dashboard Conventions

### Data Source Placeholder

Data source `uid` must use placeholder `"${DS_PROMETHEUS}"` — never hardcode a concrete uid.

Declare `DS_PROMETHEUS` in the top-level `__inputs`:

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "type": "datasource",
      "pluginId": "prometheus",
      "pluginName": "Prometheus"
    }
  ]
}
```

### Panel Data Source Reference

Every panel must reference the data source via the placeholder:

```json
{
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      }
    }
  ]
}
```

### PromQL Best Practices

- Prefer `$__rate_interval` over fixed ranges (e.g. `[5m]`) for `rate()` and `increase()` functions
- Use Grafana template variables (`$region`, `$instance_id`, etc.) derived from metric label keys for dynamic filtering
- Set `legendFormat` using label variables to provide meaningful series names (e.g. `{{instance_id}} - {{dimension}}`)

### Prometheus Instance Discovery

To find the Prometheus instance ID for a given integration policy:

```bash
aliyun cms2 integration storage list \
  --policy-id <policyId> \
  --storage-type Prometheus
```

Read `status.instanceId` from the result and use it as `--prometheus-id` for subsequent PromQL queries.

### Label and Series Inspection

Before authoring panels, inspect available labels and series:

```bash
# List available label keys
aliyun cms2 metric promql labels --prometheus-id <id>

# Get values for a specific label
aliyun cms2 metric promql label-values --prometheus-id <id> --label <labelKey>

# Inspect time series matching a selector
aliyun cms2 metric promql series --prometheus-id <id> --match '{__name__="<metricName>"}'
```

Use discovered labels to define Grafana dashboard variables and panel queries.
