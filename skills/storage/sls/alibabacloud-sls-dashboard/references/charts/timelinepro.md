# State timeline

Use when showing how states change over time or occupy explicit start/end intervals.

## Contents

- [Usage](#usage)
- [Configuration parameters](#configuration-parameters)
- [Mapped state colors](#mapped-state-colors)
- [Examples](#examples)

## Usage

- Choose wide time/state columns, time/category/state rows, or explicit start/end intervals.
- For ordinary states use yAxisKeys arrays. With aggField select a single Y field.
- For explicit intervals use isChangeChart=true, xAxisKey, xAxisEnd and a single string yAxisKeys naming the interval category. Do not also set aggField.
- Preserve gaps unless missing state means continuation.
- Return change points in ascending time order. Each state extends to the next valid state boundary; the final state extends to the chart end time.
- In explicit intervals, category values supply both row identity and interval content; there is no separate state-value binding. Use change points if a separate state field is needed.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `isTimeSeries` | boolean | No | false | false uses only the first query; true merges all queries by their time fields, retaining timestamps from every query. No cross-query matching on other fields. |
| `queryOptionMap.<queryName>.isChangeChart` | boolean | Yes | — | false uses change points; true uses explicit start/end intervals. |
| `queryOptionMap.<queryName>.xAxisKey` | string | Yes | None | Time column or interval start, in Unix seconds. |
| `queryOptionMap.<queryName>.yAxisKeys` | string[] or string | Yes | None | State fields as an array; explicit intervals use one category field as a string. |
| `queryOptionMap.<queryName>.aggField` | string | No | None | Split change-point rows by category; use one Y field. Do not combine with explicit intervals. |
| `queryOptionMap.<queryName>.xAxisEnd` | string | For explicit intervals | None | Interval end column, in Unix seconds. |
| `timelineOptions.mergeValues` | boolean | No | false | Merge adjacent equal states; false keeps each point as a segment. |
| `timelineOptions.connectNullValues` | string | No | never | For null gaps: never preserves gaps; always extends the preceding state across gaps; threshold connects only gaps within connectNullThreshold. In ungrouped change-point data, missing aligned samples do not interrupt the preceding state. |
| `timelineOptions.connectNullThreshold` | number | For threshold mode | 3600 | Maximum connected gap in seconds. |
| `timelineOptions.showValues` | string | No | always | auto shows values if space permits; always attempts to show them; never hides them. |
| `timelineOptions.textAlign` | string | Yes | — | left, center, or right inside state segments. |
| `timelineOptions.valueSize` | number | No | 12 | Label font size in pixels. |
| `timelineOptions.lineWidth` | number | No | 1 | Segment-outline width in pixels. |
| `timelineOptions.rowHeight` | number | Yes | — | Fraction of available row height; 0.1–1. |
| `timelineOptions.fillOpacity` | number | No | 100 | Segment fill opacity; 0–100. |

## Mapped state colors

With [threshold coloring](../features/thresholds.md) and text
[value mapping](../features/value-mapping.md), state colors are matched against
the mapped text. `valueMappingOption[].color` does not set the segment fill color.
When mapping numeric states to names, use text equality thresholds for those labels; numeric
thresholds no longer match them, leaving the first threshold's color.

This display fragment maps states 0, 1 and 2 to Healthy, Degraded and Failed,
with green, orange and red segment colors:

```json
{
  "standardOption": {
    "colorSchame": {"schema": "threshold"}
  },
  "valueMappingOption": [
    {"matchType": "value", "matchValue": "0", "replaceType": "text", "replaceText": "Healthy"},
    {"matchType": "value", "matchValue": "1", "replaceType": "text", "replaceText": "Degraded"},
    {"matchType": "value", "matchValue": "2", "replaceType": "text", "replaceText": "Failed"}
  ],
  "thresholdOption": {
    "thresholdMode": "absolute",
    "thresholdsStyle": "off",
    "thresholds": [
      {"rule": "=", "value": "Healthy", "color": "#36A269"},
      {"rule": "=", "value": "Degraded", "color": "#E9A23B"},
      {"rule": "=", "value": "Failed", "color": "#DA5C5C"}
    ]
  }
}
```

## Examples

Display fragments:

### Point state wide

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "isChangeChart": false,
      "xAxisKey": "time",
      "yAxisKeys": [
        "health",
        "phase"
      ]
    }
  },
  "timelineOptions": {
    "mergeValues": true,
    "connectNullValues": "never",
    "showValues": "auto",
    "rowHeight": 0.8
  }
}
```

### State by category

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "isChangeChart": false,
      "xAxisKey": "time",
      "yAxisKeys": [
        "state"
      ],
      "aggField": "instance"
    }
  },
  "timelineOptions": {
    "mergeValues": true,
    "connectNullValues": "never",
    "showValues": "auto",
    "rowHeight": 0.8
  }
}
```

### Explicit intervals

```json
{
  "isTimeSeries": false,
  "queryOptionMap": {
    "A": {
      "isChangeChart": true,
      "xAxisKey": "start_time",
      "xAxisEnd": "end_time",
      "yAxisKeys": "operation"
    }
  },
  "timelineOptions": {
    "mergeValues": false,
    "connectNullValues": "never",
    "showValues": "auto",
    "rowHeight": 0.8
  }
}
```
