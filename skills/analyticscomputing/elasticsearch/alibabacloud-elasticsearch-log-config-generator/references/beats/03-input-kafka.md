# Filebeat kafka Input

> Source: https://www.elastic.co/docs/reference/beats/filebeat/filebeat-input-kafka

## Core options

| Option | Description |
|---|---|
| `hosts` | Bootstrap brokers list. |
| `topics` | List of topics. |
| `group_id` | Consumer group ID. |
| `client_id` | Optional client ID. |
| `version` | Kafka protocol version, default `"2.1.0"`. With Kafka 4.0+ must be ≥ `"2.1.0"`. |
| `initial_offset` | `oldest` (default) or `newest`. |
| `isolation_level` | `read_uncommitted` (default) or `read_committed`. |

## Fetch / timing

| Option | Default |
|---|---|
| `fetch.min` | `1` |
| `fetch.default` | `1MB` |
| `fetch.max` | `0` (unlimited) |
| `max_wait_time` | `250ms` |
| `connect_backoff` | `30s` |
| `consume_backoff` | `2s` |

## Authentication

- `sasl.mechanism`: `PLAIN`, `SCRAM-SHA-256`, `SCRAM-SHA-512`.
- `username` / `password`.
- `ssl.enabled` + `ssl.*` for TLS (e.g., Azure Event Hubs Kafka endpoint, port 9093).

## Payload handling

- `expand_event_list_from_field`: JSON field whose array elements each become a separate event.
- `parsers`: list of `ndjson` / `multiline` parsers.

## Compatibility

Works with Kafka versions 0.11 to 4.1.0.

## Sample

```yaml
filebeat.inputs:
  - type: kafka
    enabled: true
    hosts: [kafka-1:9092, kafka-2:9092]
    topics: [app-logs]
    group_id: filebeat
    version: "2.8.0"
    initial_offset: oldest
    username: ${KAFKA_USER}
    password: ${KAFKA_PASSWORD}
    sasl.mechanism: SCRAM-SHA-512
    ssl.enabled: true
    parsers:
      - ndjson:
          target: ""
          message_key: log
          add_error_key: true
```
