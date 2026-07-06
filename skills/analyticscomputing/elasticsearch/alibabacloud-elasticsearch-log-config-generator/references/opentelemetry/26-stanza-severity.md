# stanza — severity parsing (`severity_parser` & embedded `severity:` blocks)

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/types/severity.md

## Fields

| Field | Default | Description |
|---|---|---|
| `parse_from` | required | Source field for the raw severity. |
| `preset` | `default` | Built-in baseline mapping; set to `none` to start empty. |
| `mapping` | — | Custom rules merged on top of the preset. |
| `overwrite_text` | `false` | If true, replaces text with the standard alias. |

By default severity_text is set to the original input value.

## Severity tokens

Numbers ↔ aliases mirror the OpenTelemetry Logs Data Model:

- 0 → `default`
- 1–4 → `trace`, `trace2`, `trace3`, `trace4`
- 5–8 → `debug`, `debug2`, `debug3`, `debug4`
- 9–12 → `info`, `info2`, `info3`, `info4`
- 13–16 → `warn`, `warn2`, `warn3`, `warn4`
- 17–20 → `error`, `error2`, `error3`, `error4`
- 21–24 → `fatal`, `fatal2`, `fatal3`, `fatal4`

## Mapping syntax

Each alias maps to a single value, a list, a numeric range, or HTTP class shorthand (`2xx`, `3xx`, `4xx`, `5xx`).

```yaml
mapping:
  error: oops
  warn:
    - hey!
    - YSK
  info:
    - min: 300
      max: 399
  debug: 2xx
  fatal:
    - really serious
    - min: 9001
      max: 9050
    - 5xx
```

`Nxx` expands to `min: N00, max: N99`.

## Examples

Standalone:

```yaml
- type: severity_parser
  parse_from: body.severity_field
  mapping:
    warn: 5xx
    error: 4xx
    info: 3xx
    debug: 2xx
```

Embedded in a parser (runs after parsing, before forwarding):

```yaml
- type: regex_parser
  regexp: '^StatusCode=(?P<severity_field>\d{3}), Host=(?P<host>[^,]+)'
  severity:
    parse_from: body.severity_field
    mapping:
      warn: 5xx
      error: 4xx
      info: 3xx
      debug: 2xx
```

`preset: none` means only your explicit `mapping` applies; otherwise the preset already covers `info: info`, `error: error`, etc.
