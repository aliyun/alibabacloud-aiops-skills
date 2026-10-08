# Trajectory

Use when showing movement paths from time-ordered locations for identified objects.

## Usage

- Use one query with one point per row, ordered within each object by time.
- For `lnglat`, return object ID, coordinates and Unix-second time. For `poi`, return object ID, place text and Unix-second `__time__`.
- In `lnglat` mode, a point is dropped if either coordinate is zero or integer-valued, including `10.0`, even when the location is valid.
- In `poi` mode, locations that cannot be geocoded are dropped.
- Path width, color, and direction arrows are not configurable.
- Limit object and point counts, validate locations and use a region where the map service is available.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `trajectoryOptions.lineType` | string | Yes | — | lnglat uses coordinate columns; poi uses location text. |
| `trajectoryOptions.id` | string | Yes | None | Object ID column; rows with the same ID form one path. |
| `trajectoryOptions.longitude` | string | For lnglat | None | Longitude column. |
| `trajectoryOptions.latitude` | string | For lnglat | None | Latitude column. |
| `trajectoryOptions.poiKey` | string | For poi | None | Location-text column to geocode. |
| `trajectoryOptions.info` | string[] | No | [] | Additional columns displayed when clicking a point. |
| `trajectoryOptions.timeKey` | string | No | __time__ | Unix-second time column for coordinate-mode ordering and time interaction. Ignored in `poi` mode, which always uses `__time__`. |

## Examples

Display fragments:

### Lnglat tracks

```json
{
  "trajectoryOptions": {
    "lineType": "lnglat",
    "id": "object_id",
    "longitude": "longitude",
    "latitude": "latitude",
    "timeKey": "event_time",
    "info": []
  }
}
```

### Poi tracks

```json
{
  "trajectoryOptions": {
    "lineType": "poi",
    "id": "object_id",
    "poiKey": "poi",
    "info": []
  }
}
```
