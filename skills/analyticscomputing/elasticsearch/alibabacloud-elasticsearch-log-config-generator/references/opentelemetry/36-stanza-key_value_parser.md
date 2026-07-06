# stanza key_value_parser operator

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/operators/key_value_parser.md
>
> Splits a string into key=value pairs and writes them as attributes. All values land as strings.

## Fields

| Field | Default | Notes |
|---|---|---|
| `id` | `key_value_parser` | Operator instance ID. |
| `type` | required | Must be `key_value_parser`. |
| `delimiter` | `=` | Char between key and value. |
| `pair_delimiter` | whitespace | Char between consecutive pairs. |
| `parse_from` | `body` | Source field. |
| `parse_to` | `attributes` | Destination field. |
| `on_error` | `send` | See `21-stanza-operators-overview.md`. |
| `if` | — | Per-entry guard. |
| `timestamp` | — | Embedded timestamp block (`25-stanza-timestamp.md`). |
| `severity` | — | Embedded severity block (`26-stanza-severity.md`). |

## Example — default `key=value` whitespace-separated

```yaml
operators:
  - type: key_value_parser
    parse_from: body
```

## Example — custom delimiters with embedded timestamp + severity

For input `name:stanza ! org:otel ! level:info ! seconds_since_epoch:1136214245`:

```yaml
operators:
  - type: key_value_parser
    parse_from: body
    delimiter: ":"
    pair_delimiter: "!"
    timestamp:
      parse_from: attributes.seconds_since_epoch
      layout_type: epoch
      layout: s
    severity:
      parse_from: attributes.level
```
