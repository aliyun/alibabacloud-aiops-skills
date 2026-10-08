# Data heatmap

Use when comparing one reduced value per field or metric series as colored tiles.

## Usage

- Each numeric field or metric series becomes one tile after reduction. A time column should be identified as time to avoid an extra tile.
- Use lastNotNull for current state or max for peak values. Hide values when there are many tiles.
- Set `min` and `max` for a known range, with `max > min`. No `queryOptionMap` is needed.
- Only finite numeric reduction results produce tiles. A time field appears in the tooltip, not in tile positioning or reduction.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `hotmapOption.max` | number | No | Largest reduced value | Shared color-scale upper bound. |
| `hotmapOption.min` | number | No | Smallest reduced value | Shared color-scale lower bound. |
| `hotmapOption.calculationType` | string | No | firstNotNull | Reduce each numeric field or metric series to one tile value. |
| `hotmapOption.showValue` | boolean | No | false | Show formatted values inside tiles. |

See [reducers](../features/reducers.md).

The shared color scale divides `[min, max]` into four equal bands: green, yellow,
orange, then red. Bounds affect colors, not the reduced values; values are not
clipped. Color-bar filtering changes visible tiles; the selection is not saved in
Dashboard JSON.

With `showValue=true`, tile labels use the first numeric field's
[formatting](../features/standard-options.md), while tooltips use each field's own
formatting. Use the same units and comparable ranges across tiles; split
incompatible measures into separate charts.

## Examples

Display fragments:

### Current status tiles

```json
{
  "hotmapOption": {
    "min": 0,
    "calculationType": "lastNotNull",
    "showValue": true
  }
}
```

### Peak overview

```json
{
  "hotmapOption": {
    "min": 0,
    "calculationType": "max",
    "showValue": false
  }
}
```
