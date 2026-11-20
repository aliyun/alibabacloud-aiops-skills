# Convert types and time

Use these objects in `chart.search.transformers[]`. See the [common fields](../transformations.md#common-fields).

- [convertFieldType](#convertfieldtype)
- [parseTimestamp](#parsetimestamp)
- [convertTimestamp](#converttimestamp)

## convertFieldType

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `conversions[].targetField` | string | Yes | None | Original field name; matches across all results. |
| `conversions[].destinationType` | string | Yes | None | number, string, boolean, or time. |
| `conversions[].dateFormat` | string | For non-ISO time text | None | Input date format, such as YYYY-MM-DD HH:mm:ss. |

Invalid numbers become null; empty strings and null convert to 0. Non-empty strings,
including "false" and "0", convert to boolean true. Time output uses milliseconds;
text dates without a timezone use browser local time. Invalid dates become null.

### Example: Convert field types

```json
{
  "name": "TA",
  "type": "convertFieldType",
  "conversions": [
    { "targetField": "count", "destinationType": "number" },
    { "targetField": "enabled", "destinationType": "boolean" },
    {
      "targetField": "event_time",
      "destinationType": "time",
      "dateFormat": "YYYY-MM-DD HH:mm:ss"
    }
  ]
}
```

## parseTimestamp

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `datasource` | string | Yes | None | Exact result name to process. |
| `fieldName` | string | Yes | None | Exact original name of the text-time field. |
| `format` | string | Yes | None | Input format, such as YYYY-MM-DD HH:mm:ss; supply explicitly in Dashboard JSON. |

Unmatched result or field names leave data unchanged. Output is Unix seconds;
invalid values become null. Text without a timezone uses browser local time.
This changes values but does not mark the field as time-typed; use
`convertFieldType` when both the type and millisecond values are needed.

### Example: Parse text timestamps

```json
{
  "name": "TA",
  "type": "parseTimestamp",
  "datasource": "A",
  "fieldName": "event_time",
  "format": "YYYY-MM-DD HH:mm:ss"
}
```

## convertTimestamp

No parameters. Convert 13-digit millisecond timestamps in time-typed fields to
seconds. Ten-digit seconds remain unchanged; date strings are not parsed.

### Example: Convert timestamp units

```json
{
  "name": "TA",
  "type": "convertTimestamp"
}
```
