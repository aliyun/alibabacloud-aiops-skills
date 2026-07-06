# Filebeat syslog Input

> Source: https://www.elastic.co/docs/reference/beats/filebeat/filebeat-input-syslog
> Note: deprecated since 8.14 — Elastic recommends the `syslog` processor on a `tcp`/`udp` input.

Receives RFC 3164 / RFC 5424 events over TCP, UDP, or Unix socket.

## Top-level

- `format`: `rfc3164`, `rfc5424`, `auto`. Default `rfc3164`.
- `timezone`: IANA zone, fixed offset, or `Local`. Default `Local`.

## protocol.udp

| Option | Default |
|---|---|
| `host` | required |
| `max_message_size` | `10KiB` |
| `network` | `udp` |
| `read_buffer` | OS default |
| `timeout` | `5m` |

## protocol.tcp

| Option | Default |
|---|---|
| `host` | required |
| `max_message_size` | `20MiB` |
| `network` | `tcp` |
| `framing` | `delimiter` (or `rfc6587` for octet counting / non-transparent framing) |
| `line_delimiter` | `\n` |
| `max_connections` | unset |
| `timeout` | `300s` |
| `ssl` | TLS config |

## protocol.unix

| Option | Default |
|---|---|
| `path` | required |
| `socket_type` | `stream` |
| `max_message_size` | `20MiB` |
| `mode` | system |

## Sample — TCP / RFC 5424 with TLS

```yaml
filebeat.inputs:
  - type: syslog
    format: rfc5424
    protocol.tcp:
      host: "0.0.0.0:9000"
      framing: rfc6587
      line_delimiter: "\n"
      max_connections: 512
      max_message_size: 20MiB
      timeout: 300s
      ssl:
        enabled: true
        certificate: /etc/filebeat/certs/server.crt
        key: /etc/filebeat/certs/server.key
        certificate_authorities: [/etc/filebeat/certs/ca.crt]
    timezone: Asia/Shanghai
    tags: [syslog]
```

## Sample — UDP / RFC 3164

```yaml
filebeat.inputs:
  - type: syslog
    format: rfc3164
    protocol.udp:
      host: "0.0.0.0:514"
      max_message_size: 10KiB
    timezone: Asia/Shanghai
```

## Recommended migration (newer Filebeat)

```yaml
filebeat.inputs:
  - type: tcp
    host: "0.0.0.0:9000"
    parsers:
      - syslog:
          format: rfc5424
          timezone: Asia/Shanghai
```
