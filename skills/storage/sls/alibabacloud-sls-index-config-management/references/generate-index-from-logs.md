# Generate Index Configuration from Log Samples

Use this reference when the user provides multiple structured log samples and wants an SLS field
index config inferred from them.

For direct index config operations and CLI examples, see
[manage-index-config.md](manage-index-config.md). For workload/cost/throughput tuning on an
existing index, see [optimize-index-config.md](optimize-index-config.md).

## Workflow

1. Run `get-index` and save the current index config as a backup if an index exists. If `IndexConfigNotExist` is returned, skip the backup and plan to use `create-index`.
2. Analyze the user-provided samples and infer each field's SLS index type.
3. Generate the complete final index config.
4. Output the final index config and the matching `create-index` or `update-index` CLI command.

## Generation Rules

Use user-provided structured log samples. The expected shape is a single-level key/value map:
`{ "field": value, ... }`.

Generate `keys` only by default. Do not generate a full-text `line` index unless the user asks for
full-text keyword search.

For each top-level field:

1. Inspect all non-empty sample values for that field.
2. Infer the narrowest compatible SLS type.
3. Add one `keys.<field>` entry.
4. Set `doc_value: false` unless the user explicitly says the field is needed for SQL analytics
   (`SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, aggregations).

Do not make assumptions from field names alone. For example, do not set `doc_value: true` just
because a field is named `status`, `request_time`, or `user_id`.

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
  "doc_value": false,
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
  "doc_value": false,
  "caseSensitive": false,
  "chn": false,
  "token": [",", " ", ":", "-", "\n", "\t", "\r"],
  "json_keys": {
    "trace_id": {
      "type": "text",
      "doc_value": false,
      "caseSensitive": false,
      "chn": false
    },
    "region": {
      "type": "text",
      "doc_value": false,
      "caseSensitive": false,
      "chn": false
    },
    "cost": {
      "type": "double",
      "doc_value": false
    }
  }
}
```

## Output

Return a concise field inference summary, the complete generated index config, and the matching
`create-index` or `update-index` command from [manage-index-config.md](manage-index-config.md).

## Example Output

Example `keys` config (three representative field types):

```json
{
  "request_uri": {
    "type": "text",
    "doc_value": false,
    "caseSensitive": false,
    "chn": false,
    "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", "?", "&", "/", ":", "\n", "\t", "\r"]
  },
  "status": {
    "type": "long",
    "doc_value": false
  },
  "extra": {
    "type": "json",
    "doc_value": false,
    "caseSensitive": false,
    "chn": false,
    "token": [",", " ", ":", "-", "\n", "\t", "\r"],
    "json_keys": {
      "trace_id": { "type": "text", "doc_value": false, "caseSensitive": false, "chn": false },
      "cost": { "type": "double", "doc_value": false }
    }
  }
}
```
