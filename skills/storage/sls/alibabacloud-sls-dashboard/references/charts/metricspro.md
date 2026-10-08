# Native metric chart

Use when viewing native Metricstore trends with interactive historical comparisons. For ordinary trends, use [line chart](linepro.md).

## Usage

- Use `queryType=range`, `interval` and `limit`, with `legendFormat` that distinguishes series. No table-style `queryOptionMap` is needed.
- Configure the current query; historical comparison selections handle the comparison windows.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `isTimeSeries` | boolean | Yes | true | Keep enabled for native range series. |

Use [line/axis options](../features/xy-options.md),
[data filling](linepro.md#configuration-parameters), [legend](../features/legend.md),
[tooltip](../features/tooltip.md), and [field overrides](../features/field-overrides.md).
Historical comparison choices are temporary viewing selections; do not persist a
comparison duration as a chart parameter.

## Examples

Display fragments:

### Metric range series

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
  "graphOptions": {
    "seriesStyle": "lines",
    "lineInterpolation": "linear",
    "showPoint": "never",
    "fillOpacity": 0
  }
}
```

### Metric range by label

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
  "legendOption": {
    "show": true
  }
}
```
