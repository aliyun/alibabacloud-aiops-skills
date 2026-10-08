# Table

Use when users need individual records, sortable details, or numeric cells with
threshold colors, gauges, or sparklines. Rows and columns retain their query shape.

Start with the [three-row table dashboard](../../assets/dashboards/charts/tablepro.json)
for a complete example.

## Contents

- [Usage](#usage)
- [Configuration parameters](#configuration-parameters)
- [Cell modes](#cell-modes)
- [Examples](#examples)

## Usage

- No queryOptionMap is needed when showing all columns.
- Gauge cells require numeric values and a meaningful maximum. Sparkline cells require JSON numeric arrays.
- For threshold highlighting, choose a `cellMode` that supports colors and configure threshold rules and coloring.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.closedKeys` | string[] | No | [] | Hide these output columns in the selected query group. |
| `tableOptions.showMode` | string | No | — | pagination shows pages; equalHeight uses fixed-height rows with scrolling. |
| `tableOptions.adaptivedColumn` | boolean | No | false | Size columns from content unless a fixed width is supplied. |
| `tableOptions.defaultLines` | number | No | 3 | Visible text lines when adaptive column sizing is enabled. |
| `tableOptions.rowHeight` | number | No | 36 | Row height in pixels for equalHeight mode. |
| `tableOptions.pageSize` | number | No | 20 | Rows per page in pagination mode. |
| `tableOptions.sortField` | string | No | None | Initial sort column as <queryName>-<fieldName>; affects only that query group. |
| `tableOptions.sortMethod` | string | No | default | default preserves result order; asc or desc sorts whole rows by sortField. |
| `tableOptions.showHeader` | boolean | No | true | Show column headings. |
| `tableOptions.showTotal` | boolean | No | true | Show total row count for the current query group. |
| `tableOptions.showHoverPreview` | boolean | No | true | Allow a hover preview of overflowing cell text. |
| `tableOptions.transparentBackground` | boolean | No | false | Remove the table-content background. |
| `tableOptions.showGaugeTitle` | boolean | No | true | Show formatted values in gauge cells. |
| `columnOptions.columnMinWidth` | number | No | 100 | Minimum column width in pixels. |
| `columnOptions.columnWidth` | number | No | Automatic | Fixed column width in pixels. |
| `columnOptions.columnAlign` | string | No | left | left, center, or right. |
| `columnOptions.fontSize` | number | No | 12 | Cell font size in pixels. |
| `columnOptions.closeSort` | boolean | No | — | Disable interactive sorting for the column. |
| `columnOptions.closeSearch` | boolean | No | — | Disable column search/filter controls. |
| `columnOptions.searchMode` | string | No | — | search accepts text; filter selects column values. |
| `columnOptions.searchMultiple` | boolean | No | true | Allow multiple selected filter values. |
| `columnOptions.searchAccurate` | boolean | No | false | Match the complete search value. |
| `columnOptions.showAll` | boolean | No | false | Expand plain-text cells in non-adaptive pagination mode; a 10,000-character limit still applies. |
| `columnOptions.maxNumber` | number | No | Full result-column maximum | Gauge upper bound; independent of current page or selected rows. Gauge lower bound is 0. |
| `columnOptions.cellMode` | string | No | — | Cell presentation; see modes below. |
| `fieldOptions` | object[] | No | [] | Override options for individual query fields; see field overrides. |

## Cell modes

| Value | Effect and input |
| --- | --- |
| `none` | Formatted text. |
| `text` | Color text using field colors or thresholds. |
| `background` | Color the cell background. |
| `fullbackground` | Extend the cell's color across the row. |
| `basic_gauge` | Continuous gauge; numeric input. |
| `lcd_gauge` | Segmented gauge; numeric input. |
| `gradient_gauge` | Gradient gauge; numeric input. |
| `line` / `area` / `interval` | Line / area / bar sparkline from a JSON string containing a numeric array, such as "[3,5,4,8]". Array indices form X; timestamps and labels are not supported inside the array. |

Multiple queries remain separate, switchable tables; they are not joined.
Set `maxNumber` explicitly for fixed scales such as percentages. Apply cell modes
through [field overrides](../features/field-overrides.md) when only one column
should use them. Use query `ORDER BY` for stable TopN selection.

## Examples

Display fragments:

### Adaptive text table

```json
{
  "tableOptions": {
    "showMode": "pagination",
    "adaptivedColumn": true,
    "defaultLines": 3
  }
}
```

### Threshold highlight

```json
{
  "fieldOptions": [
    {
      "queryName": "A",
      "name": "numeric_value",
      "overrides": [
        {
          "optionKeys": [
            "columnOptions",
            "cellMode"
          ],
          "value": "background"
        },
        {
          "optionKeys": [
            "standardOption",
            "colorSchame"
          ],
          "value": {
            "schema": "threshold"
          }
        },
        {
          "optionKeys": [
            "thresholdOption",
            "thresholds"
          ],
          "value": [
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
      ]
    }
  ]
}
```

### Gauge cell

```json
{
  "fieldOptions": [
    {
      "queryName": "A",
      "name": "numeric_value",
      "overrides": [
        {
          "optionKeys": [
            "columnOptions",
            "cellMode"
          ],
          "value": "basic_gauge"
        },
        {
          "optionKeys": [
            "columnOptions",
            "maxNumber"
          ],
          "value": 100
        }
      ]
    }
  ]
}
```

### Sparkline cell

```json
{
  "fieldOptions": [
    {
      "queryName": "A",
      "name": "series",
      "overrides": [
        {
          "optionKeys": [
            "columnOptions",
            "cellMode"
          ],
          "value": "line"
        }
      ]
    }
  ]
}
```
