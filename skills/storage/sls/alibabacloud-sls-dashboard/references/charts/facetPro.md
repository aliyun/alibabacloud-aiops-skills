# Time-series facets

Use when exploring SLS decomposition, clustering, similarity, or root-cause results as related subplots.

## Usage

Use one supported algorithm query. Preserve result field names, order and
structure; do not add ordinary line-chart bindings or reshape the output.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `innerTokenOption` | object[] | No | [] | Static chart-local selectors; see [local variables](../features/local-variables.md). |

## Query and display

Use `ts_decompose` for decomposition; `ts_density_cluster`,
`ts_hierarchical_cluster` or `ts_similar_instance` for related series; and
`rca_kpi_search` for root-cause groups.

Use this display configuration as a starting point for `ts_decompose`:

```json
{
  "version": 2,
  "basicOptions": {
    "displayName": "Time-series decomposition",
    "showTitle": true,
    "showBackground": true,
    "showBorder": true,
    "showTime": false
  },
  "xPos": 0,
  "yPos": 0,
  "width": 12,
  "height": 8,
  "isTimeSeries": true,
  "legendOption": {
    "show": true,
    "position": "right"
  },
  "xAxisOption": {
    "show": true,
    "timeRangeMode": "dataTime"
  },
  "yAxisOption": {
    "show": true,
    "position": 3
  },
  "graphOptions": {
    "seriesStyle": "lines",
    "showPoint": "never",
    "lineInterpolation": "linear",
    "fillOpacity": 20
  }
}
```

Omitting the legend and axis configuration objects can cause rendering to fail
even when the algorithm query succeeds. See [legend settings](../features/legend.md)
and [axes and graph settings](../features/xy-options.md) for the fields used here.

## Result markers

The server supplies `marker` as query-response metadata, not a Dashboard JSON
option. Do not add it to chart, query, or `display` configuration.

| Marker | Required result and display |
| --- | --- |
| `ts_decompose` | The first result column is time. Subsequent numeric columns such as `src`, `trend`, `season`, and `residual` become separate subplots. |
| `ts_density_cluster`, `ts_hierarchical_cluster`, `ts_similar_instance` | Keep `cluster_id`, `time_series`, `data_series`, `instance_names`, and `rate` values encoded as JSON-array strings; do not rename or expand them. One subplot per cluster. |
| `rca_kpi_search` | The first row's first column must be a JSON string containing `rcSets` for the dedicated RCA view. |
