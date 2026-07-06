# stanza csv_parser operator

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/operators/csv_parser.md
>
> Parses a delimited line into named fields. Either `header` (static) or `header_attribute` (dynamic, read from another attribute) is required.

## Fields

| Field | Default | Notes |
|---|---|---|
| `header` | required when `header_attribute` not set | Delimited string of field names, e.g. `id,severity,message`. |
| `header_attribute` | required when `header` not set | Name of an attribute holding the header for that entry (dynamic schema). |
| `header_delimiter` | value of `delimiter` | Char to split `header`. `\r`/`\n` not allowed. |
| `delimiter` | `,` | Char to split values. `\r`/`\n` not allowed. |
| `lazy_quotes` | `false` | Allow non-canonical quoting. Mutually exclusive with `ignore_quotes`. |
| `ignore_quotes` | `false` | Treat quote chars literally; pure delimiter split. Mutually exclusive with `lazy_quotes`. |
| `parse_from` | `body` | Source field. |
| `parse_to` | `attributes` | Destination. |
| `on_error` | `send` | — |
| `if` | — | Per-entry guard. |

## Example — static schema

```yaml
operators:
  - type: csv_parser
    parse_from: body
    header: id,severity,message
```

## Example — dynamic header per entry

```yaml
operators:
  - type: csv_parser
    parse_from: body
    header_attribute: csv_header
    delimiter: "|"
    lazy_quotes: true
```
