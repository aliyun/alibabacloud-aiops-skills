# Radar chart

Use when comparing several series across a small set of dimensions with compatible scales.

Start with the [two-series comparison dashboard](../../assets/dashboards/charts/radarchart.json)
for a complete example.

## Usage

- Use one query: categories form axes, numeric columns form comparison series.
- Use non-negative measures with comparable scales, or normalize them. Limit series count and aim for 3–8 axes.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.showFieldKey` | string | Yes | None | Category column; each row defines one radar axis. |
| `queryOptionMap.<queryName>.numFieldKey` | string[] | Yes | None | Numeric columns; each column is a comparison series. |
| `typeOption.chartType` | string | No | PolygonsChart | PolygonsChart uses a polygon grid; CircleChart uses a circular grid. |
| `typeOption.showLabel` | boolean | No | true | Show category labels. |
| `radarOption.pointSize` | number | No | 5 | Vertex marker size in pixels. |
| `radarOption.lineWidth` | number | No | 1 | Series-outline width in pixels. |

All series share a scale derived from the maximum data value.

## Examples

Display fragments:

### Compare normalized entities

```json
{
  "queryOptionMap": {
    "A": {
      "showFieldKey": "dimension",
      "numFieldKey": [
        "entity_a_score",
        "entity_b_score"
      ]
    }
  },
  "legendOption": {
    "show": true,
    "position": "bottom"
  }
}
```

Nonnumeric values become zero and can distort the shape.
