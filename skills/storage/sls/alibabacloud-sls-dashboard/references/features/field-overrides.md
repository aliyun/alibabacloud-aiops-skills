# Field overrides

Use `display.fieldOptions[]` to change settings for one query field. This format
differs from Grafana's matcher/properties structure.

Common settings, grouped by parent:

- Under `standardOption`: `displayName`, `colorSchame`, `unit`, and `decimals`.
- Under `graphOptions`: `lineWidth` and `fillOpacity`.
- `legendOption.show` and `columnOptions.columnWidth`.

Write each path as segments, for example `optionKeys: ["standardOption", "unit"]`.

Only settings supported by the chart take effect. Overrides change presentation
without renaming query output fields.

For field-level value mapping, use `optionKeys: ["valueMappingOption"]` with the
rule array.

## Configuration parameters

Parameters belong to `display.fieldOptions[]`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryName` | string | Yes | None | Query containing the target field. |
| `name` | string | Yes | None | Original output field name. |
| `overrides` | object[] | Yes | [] | Settings applied only to that field. |
| `overrides[].optionKeys` | string[] | Yes | None | Path segments, such as ["standardOption","decimals"]. |
| `overrides[].value` | any | Yes | None | Value required by the selected parameter's type. |

## Configuration examples

```json
{
  "display": {
    "fieldOptions": [
      {
        "queryName": "A",
        "name": "latency",
        "overrides": [
          {
            "optionKeys": ["standardOption", "displayName"],
            "value": "P95 Latency"
          }
        ]
      }
    ]
  }
}
```
