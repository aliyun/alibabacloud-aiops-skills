# stanza — operators overview

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/operators/README.md
>
> The `filelogreceiver` (and other file-style log receivers) build their parsing pipeline from stanza operators. An operator is "the most basic unit of log processing." Operators link via `output: <next-id>` until reaching the receiver's emitter.

## Operator catalog

**Inputs** — generally not needed when wrapping a receiver: `file_input`, `journald_input`, `stdin`, `syslog_input`, `tcp_input`, `udp_input`, `windows_eventlog_input`.

**Parsers** — turn raw text into structure:

- `json_parser` — JSON → map
- `regex_parser` — named-capture regex → map
- `csv_parser`
- `key_value_parser`
- `syslog_parser`
- `severity_parser` — body field → severity_number/text
- `time_parser` — body field → entry timestamp
- `trace_parser`
- `uri_parser`
- `scope_name_parser`
- `json_array_parser`
- `container` (k8s container log line parsing)

**Outputs** — only when running stanza standalone: `file_output`, `stdout`.

**General-purpose**:

- `add`, `remove`, `move`, `copy` — attribute manipulation
- `flatten` — nested map → flat keys
- `retain` — drop everything except listed fields
- `recombine` — merge multiple lines into one entry (multiline)
- `regex_replace` — regex replacement on a field
- `router` — fan out by `if` expression
- `filter` — drop entries by `if`
- `noop`
- `unquote`, `sanitize_utf8`
- `assign_keys`

## Common fields

Most operators share these:

| Field | Default | Description |
|---|---|---|
| `id` | operator's `type` | Unique name. |
| `type` | required | Operator kind. |
| `output` | next-in-list | ID of next operator. |
| `on_error` | `send` | One of `send`, `drop`, `send_quiet`, `drop_quiet`. |
| `parse_from` | `body` | Source field. |
| `parse_to` | `attributes` (parser) / depends | Destination. |
| `if` | none | Expression gating execution. |

## Detailed pages we pulled

- `22-stanza-json_parser.md`
- `23-stanza-regex_parser.md`
- `24-stanza-recombine.md`
- `25-stanza-time_parser.md`
- `26-stanza-severity_parser.md`

## Worked example A — JSON line with timestamp + severity

```yaml
operators:
  - type: json_parser
    parse_from: body
  - type: time_parser
    parse_from: attributes.ts
    layout_type: strptime
    layout: '%Y-%m-%dT%H:%M:%S.%L%z'
  - type: severity_parser
    parse_from: attributes.level
```

## Worked example B — Multi-line stack trace via recombine

```yaml
operators:
  - type: recombine
    combine_field: body
    is_first_entry: 'body matches "^\\d{4}-\\d{2}-\\d{2}"'
    source_identifier: attributes["log.file.path"]
  - type: regex_parser
    parse_from: body
    regex: '^(?P<ts>\S+ \S+)\s+(?P<level>\w+)\s+(?P<msg>[\s\S]+)$'
```
