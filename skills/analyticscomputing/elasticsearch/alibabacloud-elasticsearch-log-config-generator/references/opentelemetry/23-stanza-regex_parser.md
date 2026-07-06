# stanza — `regex_parser`

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/operators/regex_parser.md

Parses a string field with a Go (RE2) regex; named capture groups become fields in `parse_to`.

## Fields

| Field | Default | Description |
|---|---|---|
| `id` | `regex_parser` | Unique identifier. |
| `type` | required | `regex_parser`. |
| `output` | next in pipeline | Downstream operator IDs. |
| `regex` | **required** | Go regex with named captures. |
| `parse_from` | `body` | Source field. |
| `parse_to` | `attributes` | Destination. |
| `on_error` | `send` | Standard error modes. |
| `if` | — | Per-entry expression to gate the parse. |
| `timestamp` | nil | Embedded timestamp block. |
| `severity` | nil | Embedded severity block. |
| `cache.size` | `0` (disabled) | FIFO cache for repeated values; replaces ≤10% per 5s. |

## Examples

Parse `body.message` into named fields:

```yaml
- type: regex_parser
  parse_from: body.message
  regex: '^Host=(?P<host>[^,]+), Type=(?P<type>.*)$'
```

With embedded timestamp:

```yaml
- type: regex_parser
  regex: '^Time=(?P<timestamp_field>\d{4}-\d{2}-\d{2}), Host=(?P<host>[^,]+), Type=(?P<type>.*)$'
  timestamp:
    parse_from: body.timestamp_field
    layout_type: strptime
    layout: '%Y-%m-%d'
```

Test patterns at regex101 (Go flavor) — Go uses RE2, so no lookarounds/backrefs.
