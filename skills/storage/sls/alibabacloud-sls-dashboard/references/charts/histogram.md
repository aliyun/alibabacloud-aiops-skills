# Histogram

Use when comparing a distribution in numeric or time buckets. Each selected Y field supplies weights summed within buckets.

Start with the [numeric distribution dashboard](../../assets/dashboards/charts/histogram.json)
for a complete example.

## Usage

- Use one query. X contains observations or time to bucket; selected Y fields contain weights or frequencies to sum. To count raw observations, return a constant 1 in a Y column for every row; rows are not counted automatically.
- X values are sorted ascending and rebucketed into left-closed, right-open intervals [start, end). Existing query bucket boundaries are not preserved.
- Values of X or Y that cannot be converted to numbers are treated as 0; validate numeric fields before charting.
- For numeric buckets, values outside explicit `startPosition/endPosition` bounds are excluded from visible buckets.
- For fixed time granularity, set `isTimeSeries=true` and `timeSelect`.
- Time bucketing uses the first and last returned X values; empty buckets are not added between the query start time and the first data point.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.xAxisKey` | string | Yes | None | Observation or time column used for bucketing. |
| `queryOptionMap.<queryName>.yAxisKeys` | string[] | Yes | None | Weight columns summed within each bucket. |
| `isTimeSeries` | boolean | Yes | false | true for time buckets; false for numeric buckets. |
| `histogramOptions.bucketSize` | number | No | Derived from bucketCount | Numeric bucket width; takes precedence over bucketCount. |
| `histogramOptions.startPosition` | number | No | Minimum X | First numeric bucket boundary. |
| `histogramOptions.endPosition` | number | No | Maximum X | End of numeric bucketing range. |
| `histogramOptions.bucketCount` | number | No | — | Bucket count used to derive width when no fixed width is selected. |
| `histogramOptions.timeType` | string | For time buckets | relativeTime | relativeTime starts from the first data time; absoluteTime aligns to interval boundaries. |
| `histogramOptions.timeSelect` | number or string | For time buckets | 0 | Bucket seconds: 10, 60, 300, 900, 1800, 3600; 0 derives width from bucketCount; custom uses custom. |
| `histogramOptions.custom` | number | For custom timeSelect | None | Bucket width in seconds. |
| `histogramOptions.combineMode` | string | No | no | no keeps separate series; yes sums series within each bucket; normal stacks them. |
| `histogramOptions.orientation` | string | No | vertical | vertical or horizontal. |
| `histogramOptions.labelRotate` | number | No | Automatic | Vertical category-label angle in degrees. |
| `histogramOptions.lineWidth` | number | No | 1 | Bar-border width; 0–10 pixels. |
| `histogramOptions.fillOpacity` | number | No | 85 | Fill opacity; 0–100. |
| `histogramOptions.gradientMode` | string | No | none | none or opacity. |

See [legend](../features/legend.md) and [tooltip](../features/tooltip.md).

## Examples

Display fragments:

### Numeric distribution

```json
{
  "isTimeSeries": false,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "value",
      "yAxisKeys": [
        "samples"
      ]
    }
  },
  "histogramOptions": {
    "orientation": "vertical",
    "bucketCount": 20,
    "combineMode": "no"
  },
  "legendOption": {
    "show": false
  }
}
```

### Time distribution

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKeys": [
        "samples"
      ]
    }
  },
  "histogramOptions": {
    "orientation": "vertical",
    "timeType": "relativeTime",
    "timeSelect": 60,
    "combineMode": "no"
  },
  "legendOption": {
    "show": false
  }
}
```
