# Box plot

Use when comparing distributions from minimum, quartiles, median, and maximum.

## Usage

- Use one query with a category or time field and five numeric fields: minimum, Q1, median, Q3 and maximum. Raw observations are unsupported.
- Ensure `min <= Q1 <= median <= Q3 <= max`. Outliers are not calculated or displayed separately.
- Categories follow query row order. For time positions, return numeric timestamps in ascending order; X values are not parsed or sorted. Legends are unsupported.
- Box color comes from the first valid numeric field's color configuration. Use [field overrides](../features/field-overrides.md) to override boxOptions.lineWidth and boxOptions.fillOpacity for statistical fields.

## Configuration parameters

Paths are relative to `display`. See [shared result bindings](../model/result-shapes.md#table-result-bindings).

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.yAxisKeys` | string[] | Yes | None | Five columns in minimum, Q1, median, Q3, maximum order. Values that cannot be converted to numbers become null. |
| `boxOptions.barWidth` | number | No | 0.7 | Box width as a fraction of category space; 0–1. |
| `boxOptions.lineWidth` | number | No | 1 | Box, median, and whisker width; 0–10 pixels. |
| `boxOptions.fillOpacity` | number | No | 85 | Box fill opacity; 0–100. |

## Examples

Display fragments; “Changes to” examples keep unshown fields from the named example:

### Category distribution

```json
{
  "isTimeSeries": false,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "category",
      "yAxisKeys": [
        "minimum",
        "q1",
        "median",
        "q3",
        "maximum"
      ]
    }
  }
}
```

### Time bucket distribution

Changes to **Category distribution**:

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time"
    }
  }
}
```
