# Treemap

Use when comparing category sizes as rectangles. The chart supports one level of categories, not nested hierarchies.

## Usage

Use one query with category and non-negative size. For readability, aim for
5–20 categories.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.xAxis` | string | Yes | None | Category column; each category becomes one rectangle. |
| `queryOptionMap.<queryName>.yAxis` | string | Yes | None | Non-negative value column determining area. |

Duplicate categories are combined by summing convertible numeric fields. Aggregate
explicitly in the query. Rectangles are arranged by descending value, not query
order; labels shrink, truncate, or disappear in small rectangles.

## Examples

Display fragments:

### Category size

```json
{
  "queryOptionMap": {
    "A": {
      "xAxis": "category",
      "yAxis": "value"
    }
  }
}
```
