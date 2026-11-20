# Generate Index Configuration from Log Samples

Structured log samples can be used to infer field indexes and generate a complete writable
object such as `{"keys": {...}}` offline. For applying it, see
[index operations](manage-index-config.md#changes).

## Generation Rules

Use user-provided structured log samples. The expected shape is a single-level key/value map:
`{ "field": value, ... }`.

For a new index, generate `keys` only by default. Add `line` when the user requests keyword search
across log fields or automatic index discovery. For automatic index discovery and updates to existing
configs, follow the [shared rules](index-configuration.md#automatic-index-discovery); do not
regenerate `line.auto_text_keys` from samples.

Use query time bounds for `__time__`. Once indexing is enabled, `__source__` and
`__topic__` have built-in text indexes. For `__tag__:` fields, use a `text` field
index when SQL analytics is needed.

Each top-level user field becomes a `keys.<field>` entry. Its purpose and non-empty
sample values guide type selection. Analytics (`doc_value: true`) is enabled by default
unless the user requests otherwise.

For text/JSON indexes, default to case-insensitive matching (`caseSensitive: false`) and no
Chinese tokenization (`chn: false`). Honor explicit user settings.

## Type Inference

Consider field purpose before value shape. Identifiers such as user IDs, order numbers, and
codes default to `text`, even when all samples contain only digits. For fields representing
numeric quantities, choose `long` or `double` from the sample values. Honor an explicitly
requested type.

| Field purpose and sample values | SLS type | Notes |
| --- | --- | --- |
| Identifier or code | `text` | Preserve its textual form, including leading zeros. |
| Numeric quantity; all non-empty values are integers within int64 | `long` | Numeric strings can qualify when the field has numeric meaning. |
| Numeric quantity; all non-empty values are numeric and some are fractional | `double` | Use for non-integer numeric quantities. |
| Every non-empty value parses as a JSON object string | `json` | Configure only one explicit JSON level by default. |
| Anything else | `text` | Fallback for mixed values, booleans, free text, or uncertain numeric meaning. |

## JSON Fields

For an SLS `json` field, do not use `index_all` by default. Parse the JSON object strings and
configure only first-level scalar keys under `json_keys`.

Rules:

- Infer `json_keys.<key>.type` from that first-level key's sample values.
- Use only `text`, `long`, or `double` inside `json_keys`.
- Keep generated token settings at the parent by default. Preserve explicit JSON leaf `token`
  arrays when updating an existing configuration.
- Do not recurse into nested objects/arrays unless the user explicitly asks.

## Example Output

Complete `index.json` with representative field types:

```json
{
  "keys": {
    "request_uri": {
      "type": "text",
      "doc_value": true,
      "caseSensitive": false,
      "chn": false,
      "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", "?", "&", "/", ":", "\n", "\t", "\r"]
    },
    "status": {
      "type": "long",
      "doc_value": true
    },
    "extra": {
      "type": "json",
      "doc_value": true,
      "caseSensitive": false,
      "chn": false,
      "token": [",", " ", ":", "-", "\n", "\t", "\r"],
      "json_keys": {
        "trace_id": {
          "type": "text",
          "doc_value": true,
          "caseSensitive": false,
          "chn": false
        },
        "cost": {
          "type": "double",
          "doc_value": true
        }
      }
    }
  }
}
```
