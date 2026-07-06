# stanza syslog_parser operator

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/operators/syslog_parser.md
>
> Parses RFC 3164 (BSD) or RFC 5424 syslog out of a string field. Used inside `filelogreceiver`/`syslogreceiver` `operators:` blocks. For end-to-end syslog over TCP/UDP/Unix-socket, use `syslogreceiver` (`10-syslogreceiver.md`).

## Fields

| Field | Default | Notes |
|---|---|---|
| `id` | `syslog_parser` | Operator instance ID. |
| `type` | required | Must be `syslog_parser`. |
| `protocol` | required | `rfc3164` or `rfc5424`. |
| `parse_from` | `body` | Source field. |
| `parse_to` | `attributes` | Destination. |
| `on_error` | `send` | See operator overview (`21-stanza-operators-overview.md`). |
| `if` | — | Per-entry guard expression. |
| `location` | `UTC` | IANA timezone for RFC 3164 (no offset in the format). |
| `enable_octet_counting` | `false` | RFC 6587 octet counting (RFC 5424 only). |
| `allow_skip_pri_header` | `false` | Accept entries without `<PRI>`; severity/priority/facility omitted. Requires `enable_octet_counting: false`. |
| `non_transparent_framing_trailer` | — | RFC 6587 non-transparent framing trailer: `LF` or `NUL` (RFC 5424 only). |
| `timestamp` | — | Embedded timestamp block (`25-stanza-timestamp.md`). |
| `severity` | — | Embedded severity block (`26-stanza-severity.md`). |

Timestamp parsing happens automatically per spec; the embedded `timestamp:` block only applies if the spec doesn't carry one.

## RFC 5424 example

```yaml
operators:
  - type: syslog_parser
    protocol: rfc5424
    parse_from: body
    parse_to: attributes
    location: UTC
    enable_octet_counting: false
```

## RFC 3164 example (with explicit timezone)

```yaml
operators:
  - type: syslog_parser
    protocol: rfc3164
    location: America/New_York
    if: 'body matches "^<"'
```
