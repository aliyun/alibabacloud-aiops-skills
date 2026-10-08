# Geographic point map

Use when displaying individual geographic points and their associated values.

## Usage

- Use where the map service is available. Supply one query with coordinates and a numeric value.
- Each valid row creates an independent point; there is no grouping, deduplication, or summation. The initial map center is the average of all valid coordinates.
- Clicking a point shows its numeric measure. The measure does not determine marker size or color. Use a geographic heat layer for intensity.
- Remove invalid coordinates and limit point count.
- Custom center, initial zoom level, aggregation, thresholds, legend, and click actions are not configurable.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.longlat` | string | Yes | None | Column containing latitude,longitude strings. |
| `queryOptionMap.<queryName>.numFieldKey` | string | Yes | None | Numeric value column. |
| `mapOption.enableScrollWheel` | boolean | No | false | Allow mouse-wheel zoom. |
| `mapOption.enableDrag` | boolean | No | false | Allow map dragging. |

## Examples

Display fragments:

### Location markers

```json
{
  "queryOptionMap": {
    "A": {
      "longlat": "geo",
      "numFieldKey": "value"
    }
  }
}
```
