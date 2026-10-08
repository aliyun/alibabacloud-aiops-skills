# Pivot table

Use when turning row dimensions, a category, and a numeric measure into a pivot table.

## Usage

Return row dimensions, one numeric value and one column category. Limit column
categories in the query.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.xAxisKeys` | string[] | Yes | None | Row dimensions; their combined values identify each output row. |
| `queryOptionMap.<queryName>.yAxisKey` | string | Yes | None | One numeric column providing cell values. |
| `queryOptionMap.<queryName>.aggField` | string | Yes | None | Category column whose values become output columns. |

The chart pivots without aggregating. Aggregate duplicate dimension/category
combinations in the query; missing combinations produce empty cells.
Each query produces a separate switchable table. See [table options](tablepro.md).

For example, `(api, 2xx, 120)` and `(api, 5xx, 3)` become one `api` row with
`2xx=120` and `5xx=3` columns.

## Examples

Display fragments:

### Basic pivot

```json
{
  "queryOptionMap": {
    "A": {
      "xAxisKeys": [
        "row_dimension"
      ],
      "aggField": "column_category",
      "yAxisKey": "value"
    }
  }
}
```

### Hierarchical rows

```json
{
  "queryOptionMap": {
    "A": {
      "xAxisKeys": [
        "row_level_1",
        "row_level_2"
      ],
      "aggField": "column_category",
      "yAxisKey": "value"
    }
  }
}
```
