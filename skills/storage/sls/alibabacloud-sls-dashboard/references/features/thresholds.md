# Thresholds and boundary bands

Configure `display.thresholdOption`, or use a field override.

The first `thresholds[]` entry supplies the fallback color and is not drawn as a
line. Subsequent rules are evaluated in array order; the last matching rule wins.

`absolute` compares values directly: for CPU values on a 0–100 scale,
80 is an 80% threshold. `percentage` uses a chart-specific relative scale,
regardless of the measure's unit; see the chart table below.

Eligible XY charts use `thresholdsStyle` for numeric threshold lines and areas.
String rules affect colors, not numeric threshold lines or areas. Stat, table and
gauge charts use threshold colors rather than XY boundary lines.

Series boundary bands require two time-aligned boundary series, rather than
fixed numeric thresholds. Set `upBoundary`, `lowBoundary`, `colorSchame` and
`fillOpacity`; see the example below.

## Configuration parameters

Parameters belong to `display.thresholdOption`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `thresholdMode` | string | No | — | absolute tests values directly; percentage uses the chart-specific scale described below. |
| `thresholds` | object[] | No | [] | Ordered color rules; the first entry supplies the base color. |
| `thresholds[].value` | number or string | For a rule | None | Compared value. |
| `thresholds[].rule` | string | For a rule | None | Numeric: `>`, `<`, `=`, `>=`, `<=`. String: `=` or `equal` matches exact text, `include` matches a substring, and `regex` matches a regular expression. |
| `thresholds[].color` | string | Yes for each entry | None | Color for the rule or base entry. |
| `thresholdsStyle` | string | No | — | off, line, dashed, area, line+area, dashed+area, or series; supported axis charts only. `off` hides threshold lines and areas, not threshold-based value or series colors. |
| `upBoundary / lowBoundary` | string | For series bands | None | Upper/lower field identity as fieldName##$##queryName. |
| `colorSchame` | object | For band color | — | Band fill color configuration; use a fixed color or built-in palette, not threshold coloring. |
| `fillOpacity` | number | For explicit band opacity | — | Band fill opacity; 0–100. |

`area` uses numeric ranges; equality rules do not partition areas. Invalid regex
rules are ignored. Field-level thresholds override chart-level thresholds.

| Chart | Color behavior |
| --- | --- |
| Stat | Requires threshold color scheme and `colorMode=value` or `background`. In `background` mode, the matched threshold color determines the gradient background; `customValueColor` controls title and value text. |
| Table | Uses the column's cellMode: text, cell background, row background, or gauge. When a value mapping supplies a color, it takes precedence over threshold colors. |
| Gauge | Percentage thresholds set outer arc boundaries at `min + (max-min) × threshold / 100`. Current-value coloring compares the current value directly against configured thresholds. |
| TreeMap / Funnel | With threshold coloring and `thresholdMode="percentage"`, compare `100 × category value / largest category value` against thresholds, not the category's share of the sum. |
| Bar gauge | Percentage thresholds use (maxRange-minRange) × threshold / 100; use absolute thresholds for an unambiguous nonzero minimum. LCD colors segments; gradient mode creates a color band. |
| Polystat | Uses thresholdOptions.thresholds, with a plural options name. |
| State timeline | Threshold colors compare mapped state text when value mapping is configured; see [mapped state colors](../charts/timelinepro.md#mapped-state-colors). |

Use `thresholdMode` and `colorSchame` for new configuration; preserve legacy
`thresholdsMode` or `colorScheme` only when maintaining existing configurations.

## Configuration examples

```json
{
  "display": {
    "standardOption": {
      "colorSchame": {
        "schema": "threshold",
        "seriesBy": "last"
      }
    },
    "thresholdOption": {
      "thresholdMode": "absolute",
      "thresholdsStyle": "off",
      "thresholds": [
        { "value": 0, "color": "rgb(115, 191, 105)", "rule": ">" },
        { "value": 80, "color": "#faad14", "rule": ">=" },
        { "value": 95, "color": "#f5222d", "rule": ">=" }
      ]
    }
  }
}
```

```json
{
  "thresholdOption": {
    "thresholdsStyle": "series",
    "upBoundary": "upper_field##$##A",
    "lowBoundary": "lower_field##$##A",
    "colorSchame": {
      "schema": "single",
      "color": "#0070cc"
    },
    "fillOpacity": 40
  }
}
```
