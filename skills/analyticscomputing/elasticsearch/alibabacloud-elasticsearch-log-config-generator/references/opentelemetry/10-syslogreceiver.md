# OpenTelemetry syslogreceiver

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/syslogreceiver/README.md
> Stability: beta (logs).

## Top-Level Fields

| Field | Default | Notes |
|-------|---------|-------|
| `tcp` | `nil` | TCP input operator block. |
| `udp` | `nil` | UDP input operator block. |
| `protocol` | required | `rfc3164` or `rfc5424`. |
| `location` | `UTC` | IANA timezone for RFC 3164. |
| `enable_octet_counting` | `false` | RFC 6587 octet counting; RFC 5424 + TCP only. |
| `max_octets` | `8192` | Max octets when octet counting is enabled. |
| `allow_skip_pri_header` | `false` | Allow records without PRI header. Requires `enable_octet_counting: false`. |
| `non_transparent_framing_trailer` | `nil` | `LF` or `NUL`; RFC 6587 non-transparent framing. |
| `attributes` / `resource` | `{}` | Static labels. |
| `operators` | `[]` | Pipeline of operators. |
| `on_error` | `send` | Behavior on parser error. |

### retry_on_failure

| Field | Default |
|-------|---------|
| `enabled` | `false` |
| `initial_interval` | `1s` |
| `max_interval` | `30s` |
| `max_elapsed_time` | `5m` (`0` to retry forever) |

## TCP Block

| Field | Default | Notes |
|-------|---------|-------|
| `listen_address` | required | `<ip>:<port>`. |
| `max_log_size` | `1MiB` | |
| `tls` | `nil` | Optional TLS config. |
| `add_attributes` | `false` | Adds `net.*` semconv attributes. |
| `multiline` | — | `line_start_pattern` or `line_end_pattern`. |
| `one_log_per_packet` | `false` | |
| `encoding` | `utf-8` | |

## UDP Block

Same as TCP minus `max_log_size` and `tls`, plus async block: `async.readers`, `async.processors`, `async.max_queue_length` (defaults 1/1/100).

## Sample: RFC 5424 over TCP

```yaml
receivers:
  syslog:
    tcp:
      listen_address: 0.0.0.0:54526
      add_attributes: true
    protocol: rfc5424
    on_error: send
    retry_on_failure:
      enabled: true

service:
  pipelines:
    logs:
      receivers: [syslog]
      exporters: [elasticsearch]
```

## Sample: RFC 3164 over UDP

```yaml
receivers:
  syslog:
    udp:
      listen_address: 0.0.0.0:54526
      add_attributes: true
      one_log_per_packet: true
    protocol: rfc3164
    location: Asia/Shanghai

service:
  pipelines:
    logs:
      receivers: [syslog]
      exporters: [elasticsearch]
```
