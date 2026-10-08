# Geographic heat layer

Use when displaying geographic density or intensity from weighted coordinates.

## Usage

- Use one query with valid latitude,longitude strings and numeric intensity.
- Rows with duplicate coordinates remain separate weighted points; there is no deduplication or preaggregation.
- Prefer comparable weights in the 0–100 range; larger values saturate the heat scale.
- Radius, opacity, gradient, and maximum intensity are not configurable.
- Use where the map service is available.

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

### Weighted location density

```json
{
  "queryOptionMap": {
    "A": {
      "longlat": "geo",
      "numFieldKey": "weight"
    }
  }
}
```
