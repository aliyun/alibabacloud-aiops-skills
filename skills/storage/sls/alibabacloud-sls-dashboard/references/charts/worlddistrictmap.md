# World administrative map

Use when comparing numeric measures across countries or regions.

## Usage

- Use one query with country names or codes and a numeric value. Aggregate to one row per country.
- For coordinate-only input, first obtain a reliable country field.
- Unrecognized countries are ignored. Country colors scale relative to the current data maximum; countries without data are gray. Custom gradients and map projections are not configurable.
- Legend values start in descending order; legendOption.sortOrder can select ascending or descending order. none does not restore query order.
- Keep full geographic coverage unless a TopN subset is requested. Use where the map service is available.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.dataType` | number | Yes | — | Use 0 for country/region input. |
| `queryOptionMap.<queryName>.showFieldKey` | string | Yes | None | Column containing supported country names in the current interface language or supported two-letter country codes. |
| `queryOptionMap.<queryName>.numFieldKey` | string | Yes | None | Numeric column determining country color. |
| `queryOptionMap.<queryName>.extraInfo` | string[] | No | [] | Additional raw result columns shown in hover details. |
| `mapOption.enableScrollWheel` | boolean | No | false | Allow mouse-wheel zoom. |
| `mapOption.enableDrag` | boolean | No | false | Allow map dragging. |

## Examples

Display fragments:

### Country region fill

```json
{
  "queryOptionMap": {
    "A": {
      "dataType": 0,
      "showFieldKey": "country",
      "numFieldKey": "value"
    }
  }
}
```
