# Generate Index Configuration from Log Samples

Use this reference when the user provides multiple structured log samples and wants an SLS field
index config inferred from them.

For direct index config operations and CLI examples, see
[manage-index-config.md](manage-index-config.md). For workload/cost/throughput tuning on an
existing index, see [optimize-index-config.md](optimize-index-config.md).

## Workflow

1. Analyze the user-provided samples and infer each field's SLS index type.
2. Generate the index config without accessing cloud resources.

If the user also asks to apply the config, follow [manage-index-config.md](manage-index-config.md)
for the cloud operation.

## Generation Rules

Use user-provided structured log samples. The expected shape is a single-level key/value map:
`{ "field": value, ... }`.

For a new index, generate `keys` only by default. Add `line` only when the user requests full-text
keyword search or automatic index discovery. For automatic index discovery and updates to existing
configs, follow the [shared rules](manage-index-config.md#automatic-index-discovery); do not
regenerate `line.auto_text_keys` from samples.

For each top-level field:

1. Inspect all non-empty sample values for that field.
2. Infer the narrowest compatible SLS type.
3. Add one `keys.<field>` entry.
4. Enable analytics (`doc_value: true`) by default unless the user requests otherwise.

For text/JSON indexes, default to case-insensitive matching (`caseSensitive: false`) and no
Chinese tokenization (`chn: false`). Enabling Chinese tokenization substantially reduces
tokenization and write throughput. Honor explicit user settings.

## Type Inference

| Observation                                                           | SLS type | Notes                                                         |
| --------------------------------------------------------------------- | -------- | ------------------------------------------------------------- |
| Every non-empty value is an integer and fits int64                    | `long`   | Numeric strings are allowed if all values are integer-shaped. |
| Every non-empty value is numeric and at least one value has a decimal | `double` | Use only when all values are numeric.                         |
| Every non-empty value parses as a JSON object string                  | `json`   | Configure only one explicit JSON level by default.            |
| Anything else                                                         | `text`   | Safe fallback for mixed values, booleans, IDs, and free text. |

Text defaults:

```json
{
  "type": "text",
  "doc_value": true,
  "caseSensitive": false,
  "chn": false,
  "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", "?", "&", "/", ":", "\n", "\t", "\r"]
}
```

## JSON Fields

For an SLS `json` field, do not use `index_all` by default. Parse the JSON object strings and
configure only first-level scalar keys under `json_keys`.

Rules:

- Infer `json_keys.<key>.type` from that first-level key's sample values.
- Use only `text`, `long`, or `double` inside `json_keys`.
- Do not configure `token` inside `json_keys`; text subkeys use the parent `json` field's
  tokenizer.
- Do not recurse into nested objects/arrays unless the user explicitly asks.

Example for field `extra`:

```json
{
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
    "region": {
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
```

## Example Output

Example `keys` config (three representative field types):

```json
{
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
      "trace_id": { "type": "text", "doc_value": true, "caseSensitive": false, "chn": false },
      "cost": { "type": "double", "doc_value": true }
    }
  }
}
```
