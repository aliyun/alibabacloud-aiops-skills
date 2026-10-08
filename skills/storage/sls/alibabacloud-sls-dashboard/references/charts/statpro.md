# Statistic

Use when showing a current KPI, a reduced statistic, or a bounded set of labeled
values. Comparison values must be calculated in the query.

## Usage

- Use `calculate` with `first` for one aggregated row, or `lastNotNull` for a series' current value. `allValues` creates one card per selected field per row without reduction; limit the card count.
- Each query produces cards independently; rows from different queries are not joined or paired.
- Sort samples in the query for chronological sparklines; a time field is optional.
- compareField contains a prepared signed difference or rate of change, not the original baseline value.
- Preserve requested or existing thresholds. Use `percent_decimal` for fractions and `percent` for values on a 0–100 scale.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `statValueOption.showMode` | string | No | calculate when statValueOption is omitted | calculate reduces each field; allValues displays rows. Set explicitly when supplying statValueOption. |
| `statValueOption.calculationType` | string | For calculate | first when statValueOption is omitted | Reduction function; see reducers. |
| `statValueOption.limitCount` | number | For bounded allValues | 25 when statValueOption is omitted | Maximum cards across all queries and selected fields. |
| `statValueOption.layoutOrientation` | string | No | auto when statValueOption is omitted | auto, vertical, or horizontal. |
| `statValueOption.minItemHeight` | number | No | 50 when statValueOption is omitted | Minimum card height in pixels for vertical layout. |
| `statValueOption.minItemWidth` | number | No | 50 when statValueOption is omitted | Minimum card width in pixels for horizontal layout. |
| `queryOptionMap.<queryName>.showField` | string[] | For table bindings | Numeric fields when queryOptionMap is omitted | Main value columns. |
| `queryOptionMap.<queryName>.associatedField` | string | No | Field name for row titles | Row title in allValues; point labels in calculate with graphMode=area. Does not change sample order or spacing. |
| `queryOptionMap.<queryName>.compareField` | string | No | None | Prepared comparison column, reduced using the main calculationType; calculate only. |
| `queryOptionMap.<queryName>.compareValueDescription` | string | No | None | Text beside the comparison. |
| `queryOptionMap.<queryName>.compareThreshold` | number | No | 0 | Above this value shows an upward indicator; below shows downward; equality shows no arrow. |
| `queryOptionMap.<queryName>.descriptionFormat` | string | No | — | Comparison format; see standard options. |
| `queryOptionMap.<queryName>.compareUnit` | string or object | No | — | Comparison unit suffix. |
| `queryOptionMap.<queryName>.descriptionDecimals` | number | No | — | Comparison decimal places. |
| `queryOptionMap.<queryName>.descriptionFontSize` | number or `""` | No | Automatic | Comparison font size in pixels. Omit it or use the empty string for automatic sizing; other strings are invalid. |
| `statStyleOptions.textMode` | string | No | auto when statStyleOptions is omitted | auto, value, value_and_name, name, or none. |
| `statStyleOptions.titleFontSize` | number | No | Automatic | Card title font size in pixels. |
| `statStyleOptions.textFontSize` | number | No | Automatic | Main value font size in pixels. |
| `statStyleOptions.colorMode` | string | No | value when statStyleOptions is omitted | none disables value-driven color; value colors text; background colors the card. |
| `statStyleOptions.customValueColor` | string | No | — | Text color in background mode. |
| `statStyleOptions.customBackgroundColor` | object | No | — | Background color configuration in value mode. |
| `statStyleOptions.customBackgroundColor.mode` | string | No | — | builtin leaves the background transparent; fixed uses color; thresholds reuses the value text color. To follow thresholds, set standardOption.colorSchame.schema=threshold and thresholdOption.thresholds. |
| `statStyleOptions.customBackgroundColor.color` | string | For fixed mode | None | Fixed background color. |
| `statStyleOptions.graphMode` | string | No | none when statStyleOptions is omitted | none hides the sparkline; area plots at least two raw samples, equally spaced by sample index. The main value remains the reduced result. |
| `statStyleOptions.textAlignment` | string | No | auto when statStyleOptions is omitted | auto or center. |

See [reducers](../features/reducers.md) and [standard options](../features/standard-options.md).

## Examples

Display fragments:

### Single KPI

```json
{
  "queryOptionMap": {
    "A": {
      "showField": [
        "value"
      ]
    }
  },
  "statValueOption": {
    "showMode": "calculate",
    "calculationType": "first"
  },
  "statStyleOptions": {
    "textMode": "value",
    "graphMode": "none",
    "colorMode": "none"
  }
}
```

### Current value with sparkline

```json
{
  "queryOptionMap": {
    "A": {
      "showField": [
        "value"
      ],
      "associatedField": "time"
    }
  },
  "statValueOption": {
    "showMode": "calculate",
    "calculationType": "lastNotNull"
  },
  "statStyleOptions": {
    "textMode": "value",
    "graphMode": "area",
    "colorMode": "value"
  }
}
```

### Explicit comparison

```json
{
  "queryOptionMap": {
    "A": {
      "showField": [
        "value"
      ],
      "compareField": "delta_percent",
      "compareValueDescription": "Compared with baseline",
      "descriptionFormat": "percent",
      "descriptionDecimals": 2
    }
  },
  "statValueOption": {
    "showMode": "calculate",
    "calculationType": "first"
  },
  "statStyleOptions": {
    "textMode": "value",
    "graphMode": "none",
    "colorMode": "value"
  }
}
```

### Threshold background

```json
{
  "queryOptionMap": {
    "A": {
      "showField": [
        "value"
      ]
    }
  },
  "statValueOption": {
    "showMode": "calculate",
    "calculationType": "first"
  },
  "statStyleOptions": {
    "textMode": "value",
    "graphMode": "none",
    "colorMode": "background"
  },
  "standardOption": {
    "colorSchame": {
      "schema": "threshold"
    }
  },
  "thresholdOption": {
    "thresholdMode": "absolute",
    "thresholds": [
      {
        "rule": ">",
        "value": 0,
        "color": "rgb(115, 191, 105)"
      },
      {
        "rule": ">=",
        "value": 80,
        "color": "rgb(208, 74, 90)"
      }
    ]
  }
}
```

## Plan configuration

Set `charts[].config.stat`. For table results:

```json
{"stat":{"mode":"calculate","valueFields":["requests"],"reducer":"first"}}
```

For labeled rows use `mode="allValues"`, exactly one valueFields entry, labelField
and a positive limit, omitting reducer. For native metric series use only
`{"stat":{"reducer":"lastNotNull"}}`. Declare table fields in queries[].fields.
