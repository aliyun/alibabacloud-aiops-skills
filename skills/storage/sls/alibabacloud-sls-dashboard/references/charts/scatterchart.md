# Scatter or bubble plot

Use when comparing points or bubbles across time or categories.

## Usage

- Bind X and numeric Y fields; add a non-negative size measure for bubbles.
- Category spacing represents distinct labels, not numeric distance, even when the labels are numbers.
- Each query independently adds points to the same chart; queries are not joined. All fields for a point must come from the same query row.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.xAxisKey` | string | Yes | None | Time or category column. |
| `queryOptionMap.<queryName>.yAxisKeys` | string[] | Yes | None | Numeric columns; select one when aggField is used. |
| `queryOptionMap.<queryName>.aggField` | string | No | None | Split rows into series by distinct values. |
| `queryOptionMap.<queryName>.sizeKey` | string | No | Fixed pointSize | Non-negative numeric column controlling relative bubble area, with a shared scale across all series; values are not pixel sizes. |
| `isTimeSeries` | boolean | Yes | — | true for a time X axis; false for a non-time X axis. |
| `scatterGraphOptions.lineWidth` | number | No | 1 | Point-outline width; 0–10 pixels. |
| `scatterGraphOptions.fillOpacity` | number | No | 20 | Point fill opacity; 0–100. |
| `scatterGraphOptions.pointSize` | number | No | 5 | Fixed point diameter without sizeKey; 0–60 pixels. |
| `scatterGraphOptions.shape` | string | No | circle | circle, square, or triangle. |
| `scatterGraphOptions.isExpend` | boolean | No | false | true assigns one fixed horizontal lane per string aggField value when isTimeSeries=false; numeric Y no longer determines vertical position. |

See [axis options](../features/xy-options.md) when configuring axis visibility and scales.

## Examples

Display fragments:

### Time bubble by category

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
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKeys": [
        "value"
      ],
      "sizeKey": "size",
      "aggField": "category"
    }
  },
  "legendOption": {
    "show": true,
    "position": "right"
  }
}
```

### Categorical points

```json
{
  "isTimeSeries": false,
  "xAxisOption": {
    "show": true
  },
  "yAxisOption": {
    "show": true,
    "position": 3
  },
  "queryOptionMap": {
    "A": {
      "xAxisKey": "category",
      "yAxisKeys": [
        "value_a",
        "value_b"
      ]
    }
  },
  "legendOption": {
    "show": true,
    "position": "right"
  }
}
```
