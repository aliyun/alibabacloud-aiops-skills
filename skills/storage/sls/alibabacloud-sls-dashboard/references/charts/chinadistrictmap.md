# China administrative map

Use when comparing measures across Chinese administrative regions.

## Usage

- Use where the map service is available for the account and region. Supply one query.
- Coordinate modes associate positions with regions; they do not draw point markers. Values from coordinates in the same region are summed. Combined coordinates use latitude,longitude.
- Unrecognized regions and regions outside the selected scope are ignored.
- Region colors scale relative to the current data maximum; regions without data are gray. Custom gradients, map projections, and point markers are not configurable.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.dataType` | number | Yes | — | 0 uses regions; 1 uses separate coordinates; 2 uses combined coordinates. |
| `queryOptionMap.<queryName>.showFieldKey` | string | For dataType=0 | None | Province/city name or code column. |
| `queryOptionMap.<queryName>.longitudeFieldKey` | string | For dataType=1 | None | Longitude column. |
| `queryOptionMap.<queryName>.latitudeFieldKey` | string | For dataType=1 | None | Latitude column. |
| `queryOptionMap.<queryName>.lnglatFieldKey` | string | For dataType=2 | None | Column containing latitude,longitude strings. |
| `queryOptionMap.<queryName>.numFieldKey` | string | Yes | None | Numeric column determining region color. |
| `queryOptionMap.<queryName>.adcode` | number or string | Yes | — | Geographic scope: 100000 for China, or a province code; does not enable interactive drilldown. |
| `queryOptionMap.<queryName>.extraInfo` | string[] | No | [] | Additional raw result columns shown in hover details; region mode only. |
| `mapOption.enableScrollWheel` | boolean | No | false | Allow mouse-wheel zoom. |
| `mapOption.enableDrag` | boolean | No | false | Allow map dragging. |

## Examples

### National region fill

Query `A` with full province names:

```sql
* | select province, value
from unnest(array['浙江省', '江苏省', '广东省'], array[40, 25, 15]) as t(province, value)
```

Alternatively, use administrative codes:

```sql
* | select province, value
from unnest(array['330000', '320000', '440000'], array[40, 25, 15]) as t(province, value)
```

Display fragment:

```json
{
  "queryOptionMap": {
    "A": {
      "dataType": 0,
      "adcode": 100000,
      "showFieldKey": "province",
      "numFieldKey": "value"
    }
  }
}
```

### Coordinates to regions

```json
{
  "queryOptionMap": {
    "A": {
      "dataType": 2,
      "adcode": 100000,
      "lnglatFieldKey": "geo",
      "numFieldKey": "value"
    }
  }
}
```
