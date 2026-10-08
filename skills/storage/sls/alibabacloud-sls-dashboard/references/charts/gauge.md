# Semicircular gauge

Use when showing a value against a configured range as a semicircular dial.
Use [bar gauge](burgauge.md) for progress bars or LCD segments.

Start with the [percentage dial dashboard](../../assets/dashboards/charts/gauge.json)
for a complete example.

## Usage

- Set `max > min` and match the bounds to the data scale: 0–1 for fractions or 0–100 for percentages.
- `calculate` produces one gauge per selected field or native metric series; `allValues` produces one per selected field per row without reduction. For rows, use `associatedField` and limit the gauge count.
- Each query produces gauges independently; rows from different queries are not joined or paired.
- Arc length uses (value - min) / (max - min), clipped to [0, 1]. This changes the position, not the displayed source value.
- Gauges use automatic layout with a minimum size of 50 × 50 pixels per gauge; there is no orientation setting.
- With standardOption.colorSchame.schema=threshold and a nonempty thresholdOption.thresholds list, numeric threshold rules divide the outer arc into colored segments. The current-value arc separately uses the color matched by the value; see [thresholds](../features/thresholds.md).

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `valueOption.showMode` | string | No | calculate when valueOption is omitted | calculate reduces fields; allValues creates gauges from rows. Set explicitly when supplying valueOption. |
| `valueOption.calculationType` | string | For calculate | first when valueOption is omitted | Reduction function; see reducers. |
| `valueOption.limitCount` | number | For bounded allValues | 25 when valueOption is omitted | Maximum gauges across all queries and fields. |
| `queryOptionMap.<queryName>.showField` | string[] | For table bindings | Numeric fields when queryOptionMap is omitted | Main numeric columns. |
| `queryOptionMap.<queryName>.associatedField` | string | No | Field name | Same-row gauge title in allValues mode. |
| `queryOptionMap.<queryName>.useQuery` | boolean | No | false | Use a query column to determine the shared maximum. |
| `queryOptionMap.<queryName>.queryField` | string | When useQuery=true | None | Column whose full-result maximum overrides standardOption.max for every gauge. |
| `standardOption.min` | number | No | 0 | Scale lower bound. |
| `standardOption.max` | number | No | 100 | Scale upper bound unless replaced by queryField maximum. |
| `styleOption.showTitle` | boolean | No | false when styleOption is omitted | Show the field or row title. |

See [reducers](../features/reducers.md).

## Examples

Display fragments:

### Current percentage

```json
{
  "queryOptionMap": {
    "A": {
      "showField": [
        "usage_percent"
      ]
    }
  },
  "valueOption": {
    "showMode": "calculate",
    "calculationType": "lastNotNull"
  },
  "standardOption": {
    "format": "percent",
    "min": 0,
    "max": 100
  },
  "styleOption": {
    "showTitle": false
  }
}
```

### Labeled percentages

```json
{
  "queryOptionMap": {
    "A": {
      "showField": [
        "usage_percent"
      ],
      "associatedField": "label"
    }
  },
  "valueOption": {
    "showMode": "allValues",
    "limitCount": 10
  },
  "standardOption": {
    "format": "percent",
    "min": 0,
    "max": 100
  },
  "styleOption": {
    "showTitle": true
  }
}
```
