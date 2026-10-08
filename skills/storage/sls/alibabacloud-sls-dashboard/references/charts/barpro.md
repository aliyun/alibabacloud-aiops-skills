# Bar chart

Use when ranking categories or comparing grouped or stacked values. Horizontal
bars suit long category names.

Start with the [vertical category bars dashboard](../../assets/dashboards/charts/barpro.json)
for a complete example.

## Contents

- [Usage](#usage)
- [Configuration parameters](#configuration-parameters)
- [Examples](#examples)

## Usage

- Only the first query result is used. Match its name to the `queryOptionMap` key.
- Prefer arrays for `yAxisKeys`.
- Aggregate, sort and limit top categories in the query.
- Stack only mutually exclusive, additive measures with the same unit. Show the legend when it distinguishes multiple series.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.xAxisKey` | string | Yes | None | Category column. |
| `queryOptionMap.<queryName>.xAxisConcatKeys` | string[] | No | [] | Append same-row field values to displayed category labels in the listed order; does not change grouping keys. |
| `queryOptionMap.<queryName>.yAxisKeys` | string[] or string | Yes | None | Numeric columns; ["__all_numeric__"] selects all numeric fields. Select exactly one when aggField is set. Values that cannot be converted to numbers are displayed as 0. |
| `queryOptionMap.<queryName>.aggField` | string | No | None | Split rows into series by category. |
| `barOptions.orientation` | string | No | vertical | vertical columns or horizontal bars. |
| `barOptions.groupWidth` | number | No | 0.7 | Fraction of category space occupied by a group; 0–1. |
| `barOptions.barWidth` | number | No | 0.9 | Fraction of each allocated bar slot occupied by the bar; 0–1. |
| `barOptions.labelRotate` | number | No | Automatic | Category-label angle in degrees, -90–90; vertical orientation only. |
| `barOptions.stackingMode` | string | No | none | none groups series; normal stacks them per category. Stacking does not calculate percentages; return percentages from the query when needed. |
| `barOptions.showValues` | string | No | auto | `auto`: show values when space permits; `always`: attempt to show them; `never`: hide values. |
| `barOptions.labelLocation` | string | No | — | xAxis places category labels on the axis; bar places them inside bars only with a single Y series, replacing numeric value labels with category labels. |
| `barOptions.valueSize` | number | No | 12 | Value or in-bar label font size; 8–30 pixels. |
| `barOptions.lineWidth` | number | No | 1 | Bar-border width; 0–10 pixels. |
| `barOptions.fillOpacity` | number | No | 85 | Bar fill opacity; 0–100. An explicit 0 also selects 85. |
| `barOptions.gradientMode` | string | No | none | none or opacity. |

See [axis options](../features/xy-options.md), [legend](../features/legend.md), and [tooltip](../features/tooltip.md).

## Examples

Display fragments:

### Top ranking

```json
{
  "queryOptionMap": {
    "A": {
      "xAxisKey": "category",
      "yAxisKeys": [
        "value"
      ]
    }
  },
  "barOptions": {
    "orientation": "horizontal",
    "stackingMode": "none"
  },
  "legendOption": {
    "show": false
  },
  "yAxisOption": {
    "softMin": 0
  }
}
```

### Grouped wide metrics

```json
{
  "queryOptionMap": {
    "A": {
      "xAxisKey": "category",
      "yAxisKeys": [
        "value_a",
        "value_b"
      ]
    }
  },
  "barOptions": {
    "orientation": "vertical",
    "stackingMode": "none"
  },
  "legendOption": {
    "show": true
  }
}
```

### Stacked long components

```json
{
  "queryOptionMap": {
    "A": {
      "xAxisKey": "category",
      "yAxisKeys": [
        "value"
      ],
      "aggField": "component"
    }
  },
  "barOptions": {
    "orientation": "vertical",
    "stackingMode": "normal"
  },
  "legendOption": {
    "show": true
  }
}
```
