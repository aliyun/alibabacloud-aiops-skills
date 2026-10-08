# Builtin simulated data

Use `builtin` to demonstrate charts and test field bindings, colors, thresholds,
and layout without querying a datastore. Preset data does not validate source
connectivity, indexes, permissions, or business metrics.

## Query parameters

Paths are relative to `chart.search.chartQueries[]`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | None | Query ID used by field bindings, such as A. |
| `datasource` | string | Yes | None | Set to builtin. |
| `type` | string | No | random_time_line | Select random_time_line, bar_data, or china_district. |

Builtin queries need no Project, Logstore, Region, SQL, or PromQL. They use the
presets below, not user-supplied rows or custom series definitions.

## Preset results

| Preset | Result fields | Use |
| --- | --- | --- |
| `random_time_line` | `__time__`: time; `count`: number | Random series over the effective chart time window. |
| `bar_data` | `Group`: string; `pv`, `uv`, `rate`: number | Five fixed categories for tables and bars; uv contains negative values. |
| `china_district` | `Province`: string; `count`: number | Five fixed Chinese provinces and numeric values for a regional map. |

Bind the result field names exactly, including capitalization. For the province
preset, use `Province` and `count`, not its displayed aliases `Group` and `pv`.

## Example: category bars

Dashboard chart fragment:

```json
{
  "title": "simulated-bars",
  "type": "barpro",
  "search": {
    "chartQueries": [
      {"name": "A", "datasource": "builtin", "type": "bar_data"}
    ]
  },
  "display": {
    "basicOptions": {"displayName": "Simulated category values"},
    "queryOptionMap": {
      "A": {"xAxisKey": "Group", "yAxisKeys": ["pv", "uv"]}
    },
    "barOptions": {"orientation": "vertical", "stackingMode": "none"}
  }
}
```

## Tool support

Dashboard JSON containing builtin queries can be validated and published with the
bundled commands. The console generates the simulated results locally.

For an `imagePro` Plan with no queries, the builder adds a builtin
`random_time_line` query automatically so the image displays. See
[image configuration](../charts/imagepro.md). Other preset configurations can be
supplied in complete Dashboard JSON. See [datasource capabilities](overview.md).
