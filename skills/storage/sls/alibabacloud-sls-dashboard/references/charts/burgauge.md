# Bar gauge

Use when showing capacity, utilization, or progress as bars, LCD segments, or dials.

## Usage

- `calculate` produces one gauge per selected numeric field; `allValues` produces one per selected field per row without reduction. For rows, use a label field and limit the gauge count.
- Each query produces gauges independently; rows from different queries are not joined or paired.
- Progress uses (value - minRange) / (maxRange - minRange), with positions clipped to the gauge range. With gaugeLabelMode=value, labels retain the formatted source value even outside that range.
- Threshold colors require `standardOption.colorSchame.schema=threshold` and `thresholdOption.thresholds`.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `burGaugeValueOption.showMode` | string | No | calculate when the value option object is omitted | calculate reduces fields; allValues expands rows. Set explicitly when supplying the object. |
| `burGaugeValueOption.calculationType` | string | For calculate | mean when the value option object is omitted | Reduction function; see reducers. |
| `burGaugeValueOption.limitCount` | number | For bounded allValues | 25 when the value option object is omitted | Maximum gauges across queries and fields. |
| `burGaugeValueOption.layoutOrientation` | string | No | vertical when the value option object is omitted | auto, vertical, horizontal; dial always uses auto. |
| `burGaugeValueOption.minRows` | number | No | — | Minimum rows for vertical layout. |
| `burGaugeValueOption.minItemHeight` | number | No | 50 when the value option object is omitted | Minimum height in pixels for vertical layout. |
| `burGaugeValueOption.minItemWidth` | number | No | 50 when the value option object is omitted | Minimum width in pixels for horizontal layout. |
| `burGaugeValueOption.showGaugeTitle` | boolean | No | false when the value option object is omitted | Show the value beside a non-dial gauge. |
| `burGaugeValueOption.gaugeLabelMode` | string | No | percent | percent shows position within the range; value shows the formatted source value. |
| `burGaugeValueOption.gaugeUnit` | string | No | — | Suffix for percent labels in gradient/basic modes. |
| `burGaugeValueOption.showDialTitle` | boolean | No | true when the value option object is omitted | Show field/row titles in both dial and non-dial modes. |
| `queryOptionMap.<queryName>.showField` | string[] | For table bindings | Numeric fields when queryOptionMap is omitted | Main value columns. |
| `queryOptionMap.<queryName>.associatedField` | string | No | Field name | Same-row title in allValues mode. |
| `queryOptionMap.<queryName>.useQuery` | boolean | No | false | Use a query column for the shared upper bound. |
| `queryOptionMap.<queryName>.queryField` | string | When useQuery=true | None | Full-column maximum becomes every gauge's upper bound. |
| `queryOptionMap.<queryName>.compareField` | string | No | None | Comparison column reduced independently with the same reducer as the main value; calculate + dial only. No difference is calculated automatically; return the desired comparison in the query. |
| `queryOptionMap.<queryName>.compareValueDescription` | string | No | None | Comparison label. |
| `queryOptionMap.<queryName>.descriptionFormat` | string | No | — | Comparison number format. |
| `queryOptionMap.<queryName>.compareUnit` | string or object | No | — | Comparison unit suffix. |
| `queryOptionMap.<queryName>.descriptionDecimals` | number | No | — | Comparison decimal places. |
| `queryOptionMap.<queryName>.descriptionFontSize` | number or `""` | No | Automatic | Comparison font size in pixels. Omit it or use the empty string for automatic sizing; other strings are invalid. |
| `burGaugeStylesOption.displayMode` | string | No | gradient when the styles object is omitted | gradient: continuous color fill; lcd: segments; basic: solid fill; dial: semicircular gauge. |
| `burGaugeStylesOption.minRange` | number | No | 0 | Range lower bound. |
| `burGaugeStylesOption.maxRange` | number | No | 100 | Range upper bound unless supplied by queryField. The effective upper bound must be greater than minRange. |
| `burGaugeStylesOption.textFontSize` | number | No | Automatic | Value font size; dial or non-dial with showGaugeTitle. |
| `burGaugeStylesOption.textFontColor` | string | No | — | Value text color in gradient/basic modes. |
| `burGaugeStylesOption.titleFontSize` | number | No | — | Non-dial title font size. |
| `burGaugeStylesOption.titlePosition` | string | No | — | left or top; vertical non-dial layout only. |
| `burGaugeStylesOption.strokeLinecap` | string | No | — | square or round ends; gradient/basic only. |
| `burGaugeStylesOption.thickness` | number | No | — | Bar thickness as a fraction of the available size, 0.1–1; gradient/basic only. |
| `burGaugeStylesOption.thicknessRange` | number[] | No | — | [minimum, maximum] thickness in pixels; clamps the pixel size derived from relative thickness; gradient/basic/lcd. |
| `burGaugeStylesOption.showUnfilledArea` | boolean | No | true when the styles object is omitted | Show unused range in gradient/basic modes. |
| `burGaugeStylesOption.lineBgColor` | string | No | — | Unused-range color when showUnfilledArea is true. |
| `burGaugeStylesOption.showGradient` | boolean | No | false when the styles object is omitted | Gradient on the dial scale; dial only. |

See [reducers](../features/reducers.md), [standard options](../features/standard-options.md), and [thresholds](../features/thresholds.md).

## Examples

Display fragments:

### Single ratio

```json
{
  "queryOptionMap": {
    "A": {
      "showField": [
        "usage"
      ]
    }
  },
  "burGaugeValueOption": {
    "showMode": "calculate",
    "calculationType": "lastNotNull",
    "showGaugeTitle": true,
    "gaugeLabelMode": "percent"
  },
  "burGaugeStylesOption": {
    "displayMode": "gradient",
    "minRange": 0,
    "maxRange": 100
  }
}
```

### Labeled all values

```json
{
  "queryOptionMap": {
    "A": {
      "showField": [
        "value"
      ],
      "associatedField": "label",
      "useQuery": true,
      "queryField": "max_value"
    }
  },
  "burGaugeValueOption": {
    "showMode": "allValues",
    "limitCount": 10,
    "layoutOrientation": "vertical"
  },
  "burGaugeStylesOption": {
    "displayMode": "basic",
    "minRange": 0
  }
}
```

## Plan configuration

Place these fragments under `charts[].config`. Declare the selected
result fields in the query. Table modes use one query.

For a numeric table field with a known 0–100 range:

```json
{
  "gauge": {
    "data": {"mode": "calculate", "valueFields": ["usage"], "reducer": "lastNotNull"},
    "range": {"mode": "fixed", "min": 0, "max": 100},
    "labelMode": "value"
  }
}
```

For table rows, replace data with
`{"mode":"allValues","valueFields":["usage"],"labelField":"service","limit":10}`.
This Plan mode requires exactly one numeric value field, one label field, and a
positive limit. Sort and limit query rows to select the top values.
Use `labelMode="percent"` to show position within the range. A query-based range
uses `{"mode":"queryField","min":0,"maxField":"capacity"}`; capacity must be a
numeric field whose maximum is a valid shared upper bound.

For native metric series:

```json
{
  "gauge": {
    "data": {"reducer": "lastNotNull"},
    "range": {"mode": "fixed", "min": 0, "max": 100}
  }
}
```

The metric configuration accepts a reducer and fixed range, without table fields
or labelMode. Set the range to match the data; 0–100 is an example.
