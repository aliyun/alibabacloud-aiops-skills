# Funnel

Use when comparing successive stages whose intended order follows decreasing values.

## Usage

- Stages are displayed in descending value order, regardless of query order. There is no stage-order setting; legend sorting changes only the legend.
- Overall shares use the largest stage value; preceding-stage shares use the preceding stage in that display order.
- Use comparable non-negative values. Choose another chart if the process order differs from descending value order.
- Duplicate stage names are summed within each query, not across queries. All queries feed one globally sorted funnel; aggregate into one query first if matching stages must be combined.

## Configuration parameters

Paths are relative to `display`. Include `funnelGrapOptions`, even if empty.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.xAxis` | string | Yes | None | Stage-name column. |
| `queryOptionMap.<queryName>.yAxis` | string | Yes | None | Stage-value column. |
| `funnelGrapOptions.isCurved` | boolean | No | false | Use curved edges and gradient blocks; false uses straight edges. |
| `funnelGrapOptions.dynamicWidth` | boolean | No | false | Shrink width by adjacent-stage ratios when true or isCurved=true; a fixed slope requires both to be false. |
| `funnelGrapOptions.dynamicHeight` | boolean | No | false | Size heights by value divided by the largest value; false gives equal heights. |
| `funnelGrapOptions.minHeight` | number | No | 20 | Pixels reserved per stage before proportional height allocation when dynamicHeight=true. If these minimum heights exceed panel height, stages overflow; reduce minHeight or the stage count. |
| `funnelGrapOptions.bottomPinch` | number | No | 1 | Number of final stages with equal width, forming the neck; less than stage count. |
| `funnelGrapOptions.showMode` | string | No | — | percent, type_percent, or type_num_percent: percentages alone, with stage name, or with name and value. |

## Examples

Display fragments:

### Conversion funnel

```json
{
  "queryOptionMap": {
    "A": {
      "xAxis": "stage",
      "yAxis": "value"
    }
  },
  "funnelGrapOptions": {
    "dynamicWidth": true,
    "showMode": "type_num_percent"
  }
}
```
