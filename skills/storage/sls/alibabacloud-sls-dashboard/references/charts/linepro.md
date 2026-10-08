# Line chart

Use when showing trends over time or comparing several numeric series. Native
metric series need no table-field bindings; tabular results use `queryOptionMap`.

Start with the [single-series trend dashboard](../../assets/dashboards/charts/linepro.json)
for a complete example.

## Contents

- [Usage](#usage)
- [Configuration parameters](#configuration-parameters)
- [Examples](#examples)

## Usage

- For a category X axis, use one query result.
- Multiple time-query results align by their X values; use matching X meanings and granularity across queries.
- For time/category/value rows, use [aggpro](aggpro.md) to split categories into lines, or reshape the query to a wide table. `linepro` does not support `aggField` grouping.
- Sort time results and align units and time windows. Fill gaps with zero only when missing observations mean zero.
- Missing timestamps and null samples can still be connected by line segments. Use `graphOptions.seriesStyle="points"`, `graphOptions.pointSize=5` and `dataOption.autoFill=false` to show only observed samples.
- Stacking changes only series layout; it does not calculate percentages. Calculate percentages in the query when needed.
- Use returned labels in `legendFormat`.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `isTimeSeries` | boolean | Yes | — | true for a time axis; false for categories. |
| `queryOptionMap.<queryName>.xAxisKey` | string | For table results | None | Time or category column. |
| `queryOptionMap.<queryName>.yAxisKeys` | string[] | For table results | None | Numeric columns; ["__all_numeric__"] selects every numeric column except X. |
| `dataOption.autoFill` | boolean | No | false | Insert values into missing time positions. |
| `dataOption.autoFillWindow` | number | No | Smallest adjacent time difference | Fill interval in seconds, with a minimum effective interval of 10 seconds; automatic inference needs at least two points. |
| `dataOption.autoFillNumber` | number | No | 0 | Value inserted at a missing time position. |
| `dataOption.maxCategoryCount` | number | No | — | Maximum series count displayed. |

See [line and axis options](../features/xy-options.md), [legend](../features/legend.md), and [tooltip](../features/tooltip.md).

## Examples

Display fragments:

### Single time series

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKeys": [
        "value"
      ]
    }
  },
  "graphOptions": {
    "seriesStyle": "lines",
    "lineInterpolation": "linear",
    "showPoint": "never",
    "fillOpacity": 0
  },
  "legendOption": {
    "show": false
  }
}
```

### Multi metric time series

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKeys": [
        "value_a",
        "value_b"
      ]
    }
  },
  "graphOptions": {
    "seriesStyle": "lines",
    "lineInterpolation": "linear",
    "showPoint": "never",
    "fillOpacity": 0
  },
  "legendOption": {
    "show": true
  }
}
```

### Stacked area components

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKeys": [
        "component_a",
        "component_b"
      ]
    }
  },
  "graphOptions": {
    "seriesStyle": "lines",
    "lineInterpolation": "linear",
    "showPoint": "never",
    "fillOpacity": 80
  },
  "yAxisOption": {
    "stackingMode": "normal"
  },
  "legendOption": {
    "show": true
  }
}
```

### Series boundary band

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKeys": [
        "value"
      ]
    }
  },
  "thresholdOption": {
    "thresholdsStyle": "series",
    "lowBoundary": "lower##$##A",
    "upBoundary": "upper##$##A",
    "fillOpacity": 30,
    "colorSchame": {
      "schema": "single",
      "color": "#f54d61"
    }
  }
}
```

### Category axis

For one query returning service and requests:

```json
{
  "isTimeSeries": false,
  "queryOptionMap": {"A": {"xAxisKey": "service", "yAxisKeys": ["requests"]}}
}
```
