# stanza — `json_parser`

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/operators/json_parser.md

Parses a string-typed field as JSON.

## Fields

| Field | Default | Description |
|---|---|---|
| `id` | `json_parser` | Unique identifier. |
| `type` | required | `json_parser`. |
| `output` | next in pipeline | Downstream operator IDs. |
| `parse_from` | `body` | Source field. |
| `parse_to` | `attributes` | Destination. |
| `on_error` | `send` | `send` / `drop` / `send_quiet` / `drop_quiet`. |
| `if` | — | Per-entry expression to gate the parse. |
| `timestamp` | nil | Embedded timestamp block (see `25-stanza-timestamp.md`). |
| `severity` | nil | Embedded severity block (see `26-stanza-severity.md`). |
| `parse_ints` | `false` | When true, integers stay integers; otherwise all numbers become `float64`. |

## Examples

Parse `body.message` as JSON:

```yaml
- type: json_parser
  parse_from: body.message
```

Parse JSON and extract an epoch timestamp:

```yaml
- type: json_parser
  parse_from: body.message
  timestamp:
    parse_from: body.seconds_since_epoch
    layout_type: epoch
    layout: s
```

Conditional parse only when body looks like JSON:

```yaml
- type: json_parser
  if: 'body matches "^{.*}$"'
```
