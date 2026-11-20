# Status block chart

Use when comparing discrete status values across times or categories and groups.

## Usage

- Supply one query with X, value and a grouping field.
- Return one row per X/group pair, order by X and limit category counts.

## Configuration parameters

Paths are relative to `display`. See [shared result bindings](../model/result-shapes.md#table-result-bindings).

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.xAxisKey` | string | Yes | None | Time or category position. |
| `queryOptionMap.<queryName>.yAxisKey` | string | Yes | None | Status/value used for the text and color. |
| `queryOptionMap.<queryName>.sizeKey` | string | For grouped rows | None | Row-group column; does not determine block size. |
| `colorBlockGraphOptions.isExpend` | boolean | No | false | true gives each sizeKey value its own row; false leaves groups unexpanded. |
| `colorBlockGraphOptions.cellGap` | number | No | 0 | Gap between blocks in pixels; larger gaps reduce block and label space. |

Continuous values share a color scale based on the minimum and maximum across all
`yAxisKey` values, not separate scales per row. For nonnumeric or discrete statuses,
configure [threshold rules](../features/thresholds.md) that assign colors to the status values.
Dragging the color-range control hides blocks outside the selected range; it does
not change query data.

## Examples

Display fragments; “Changes to” examples keep unshown fields from the named example:

### Time value matrix

```json
{
  "isTimeSeries": true,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "time",
      "yAxisKey": "value",
      "sizeKey": "entity"
    }
  },
  "colorBlockGraphOptions": {
    "isExpend": true,
    "cellGap": 2
  }
}
```

### Category value matrix

Changes to **Time value matrix**:

```json
{
  "isTimeSeries": false,
  "queryOptionMap": {
    "A": {
      "xAxisKey": "category",
      "sizeKey": "group"
    }
  }
}
```
