# Pie, donut and polar area

Use when comparing non-negative parts of a meaningful whole as a pie, donut, or polar-area chart.

Start with the [category pie dashboard](../../assets/dashboards/charts/piepro.json)
for a complete example.

## Contents

- [Usage](#usage)
- [Configuration parameters](#configuration-parameters)
- [Examples](#examples)
- [Plan configuration](#plan-configuration)

## Usage

- Limit slice count to keep labels readable.
- Aggregate repeated categories in the query. In Dashboard JSON, slices from separate queries are not joined by category.
- PieChart and DountChart show shares; PolarAreaChart uses equal angles and logarithmic radii.
- PieChart and DountChart sort slices by descending value. All-zero slice values produce only a placeholder shape.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `pieDataMode` | string | Yes | — | queryOptionMap uses category/value rows; dataOption reduces fields or expands values. Do not combine the modes. |
| `queryOptionMap.<queryName>.showFieldKey` | string | For category/value mode | None | Column providing each slice name. |
| `queryOptionMap.<queryName>.xAxisConcatKeys` | string[] | No | [] | Append same-row values to slice names in the listed order. |
| `queryOptionMap.<queryName>.numFieldKey` | string | For category/value mode | None | Numeric column determining slice size. |
| `queryOptionMap.<queryName>.name` | string | No | — | Query name; match the outer queryOptionMap key. |
| `dataOption.showMode` | string | For dataOption mode | — | calculate reduces each field; allValues expands valid numeric values field-first, then row-by-row within each field. |
| `dataOption.calculationType` | string | For calculate | — | Reduction function; see reducers. |
| `dataOption.limitCount` | number | For bounded allValues | — | Maximum slices per query result, not across the chart. |
| `dataOption.labelField` | string | No | First field not selected as a value field | Same-row slice label in allValues. An unmatched field uses the default field. Missing, empty, null, false, or numeric 0 values use the numeric field's display name. |
| `dataOption.fields` | string | For dataOption mode | — | A field name; one space selects numeric fields; .* selects all fields, skipping non-numeric values. |
| `pieOption.chartType` | string | No | — | PieChart: proportional angles; DountChart: ring with total; PolarAreaChart: equal angles and relative log(value+1) radii. |
| `pieOption.labelType` | string | No | — | value, percent, type_percent, or type_num_percent: value; percentage; category:percentage; category:value (percentage). |
| `pieOption.showLabel` | boolean | No | — | Show outer slice labels. |
| `legendOption.calcs` | string[] | No | [] | value and percent show slice values and percentages in the legend. |

Hiding slices changes the visible slice proportions, but displayed percentages
and the donut center total remain based on the values before hiding.
See [reducers](../features/reducers.md) and [legend](../features/legend.md).

## Examples

Display fragments:

### Category value pie

```json
{
  "pieDataMode": "queryOptionMap",
  "queryOptionMap": {
    "A": {
      "showFieldKey": "category",
      "numFieldKey": "value"
    }
  },
  "pieOption": {
    "chartType": "DountChart",
    "labelType": "type_num_percent",
    "showLabel": true
  },
  "legendOption": {
    "show": true,
    "position": "bottom"
  }
}
```

### Reduce numeric series

```json
{
  "pieDataMode": "dataOption",
  "dataOption": {
    "showMode": "calculate",
    "calculationType": "lastNotNull",
    "fields": " "
  },
  "pieOption": {
    "chartType": "PieChart",
    "labelType": "type_num_percent",
    "showLabel": true
  },
  "legendOption": {
    "show": true
  }
}
```

## Plan configuration

Set `charts[].config.pie`. For category/value rows from one query:

```json
{"pie":{"mode":"categoryValue","categoryField":"service","valueField":"requests"}}
```

Optional concatFields adds category fields from the same query. Declare selected
fields in queries[].fields. To reduce table fields, use mode=dataCalculation with
`calculation={"mode":"calculate","valueFields":["requests"],"reducer":"total"}`.
When selecting multiple fields in that mode, include the complete set of numeric
result fields. For native metric series use only `{"pie":{"reducer":"lastNotNull"}}`
with exactly one query.
