# Grouped series chart

Use when a table contains time/category/value rows and each category should
become a series. Aggregate to one row per X/category pair in the query.

## Usage

- Dashboard JSON processes each query independently and combines the resulting series without joining queries. Each query must supply X, one numeric value, and one category field; the category field splits rows into series.
- Limit category count in the query; a row limit alone may not bound series count.
- Configure fill with `graphOptions` and stacking with `yAxisOption.stackingMode`. Stack only additive measures with the same unit.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `isTimeSeries` | boolean | Yes | — | true for time X; false for category X. |
| `queryOptionMap.<queryName>.xAxisKey` | string | No | First time field, otherwise first column | Time or row-category column. |
| `queryOptionMap.<queryName>.aggField` | string | No | First string field excluding X and Y, otherwise third column | Column whose distinct values become series. |
| `queryOptionMap.<queryName>.yAxisKey` | string | No | First numeric field excluding X | Single numeric value column. |
| `aggChartOption.chartType` | string | Yes | — | line: lines; area: lines with area fill configured through graphOptions.fillOpacity; interval: bars; crossover: pivot table. |
| `dataOption.maxClassifyGroupNum` | number | No | — | Maximum category series retained across the chart for line, area, or interval mode, after legend sorting. Does not limit query rows; define business Top N in the query. |

See [line and axis options](../features/xy-options.md), [legend](../features/legend.md), and [tooltip](../features/tooltip.md).

For `crossover`, see [table options](tablepro.md). `xAxisKey` supplies table rows and
`aggField` supplies columns; time mode and X/Y axis options do not apply.

## Examples

Display fragments:

### Long time series

```json
{
  "isTimeSeries": true,
  "xAxisOption": {
    "show": true
  },
  "yAxisOption": {
    "show": true,
    "position": 3
  },
  "aggChartOption": {
    "chartType": "line"
  },
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKey": "value",
      "aggField": "series"
    }
  },
  "legendOption": {
    "show": true
  }
}
```

### Stacked area

```json
{
  "isTimeSeries": true,
  "aggChartOption": {
    "chartType": "area"
  },
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKey": "value",
      "aggField": "component"
    }
  },
  "graphOptions": {
    "fillOpacity": 80,
    "gradientMode": "none",
    "lineWidth": 0,
    "showPoint": "never"
  },
  "xAxisOption": {
    "show": true
  },
  "yAxisOption": {
    "show": true,
    "position": 3,
    "stackingMode": "normal"
  },
  "legendOption": {
    "show": true
  }
}
```

For stacked bars, set `aggChartOption.chartType` to `interval` and
`graphOptions.barStyle` to `middle`, keeping the fill and stacking settings above.

### Pivot crossover

```json
{
  "aggChartOption": {
    "chartType": "crossover"
  },
  "queryOptionMap": {
    "A": {
      "xAxisKey": "row_key",
      "yAxisKey": "value",
      "aggField": "column_category"
    }
  }
}
```

## Plan configuration

The Plan requires exactly one query. In `queries[].fields`, declare exactly one
field with `type=time`, the value field with `type=number`, and the category field
with `type=string`. Place these bindings under `charts[].config`:

```json
{"agg":{"valueField":"requests","aggField":"service"}}
```

The Plan generates time trends; use complete Dashboard JSON for other grouped
chart configurations.
