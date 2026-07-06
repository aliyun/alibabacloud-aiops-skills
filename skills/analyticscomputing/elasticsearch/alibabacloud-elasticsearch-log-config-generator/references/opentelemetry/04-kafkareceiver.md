# OpenTelemetry kafkareceiver

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/kafkareceiver/README.md

## Connection & Cluster

- `brokers` (default `localhost:9092`): list of Kafka brokers.
- `protocol_version` (default `2.1.0`): Kafka protocol version.
- `resolve_canonical_bootstrap_servers_only` (default `false`).
- `client_id` (default `otel-collector`).
- `rack_id` (default `""`).
- `conn_idle_timeout` (default `9m`).

## Per-Signal Settings (`logs`, `metrics`, `traces`, `profiles`)

- `topics` — list of topics. Defaults: `otlp_logs`, `otlp_metrics`, `otlp_spans`, `otlp_profiles`.
- `encoding` (default `otlp_proto`).
- `exclude_topics`: regex pattern for excluded topics when using regex topic patterns (prefix `^`).

## Consumer Group / Offsets

- `group_id` (default `otel-collector`).
- `group_instance_id`: when set, becomes static group member.
- `initial_offset` (default `latest`): `latest` or `earliest`, used only when no offset has been committed.
- `session_timeout` (default `10s`).
- `heartbeat_interval` (default `3s`).
- `group_rebalance_strategy` (default `cooperative-sticky`): `range`, `roundrobin`, `sticky`, `cooperative-sticky`.

## Fetch Tuning

- `min_fetch_size` (default `1`)
- `max_fetch_size` (default `1048576`)
- `max_fetch_wait` (default `250ms`)
- `max_partition_fetch_size` (default `1048576`).

## TLS

- `tls`: standard `configtls` options.

## Auth (`auth`)

- `sasl`:
  - `username`, `password`
  - `mechanism`: `SCRAM-SHA-256`, `SCRAM-SHA-512`, `AWS_MSK_IAM_OAUTHBEARER`, or `PLAIN`
  - `aws_msk.region` (with `AWS_MSK_IAM_OAUTHBEARER`)
- `kerberos`:
  - `service_name`, `realm`, `use_keytab`
  - `username`, `password`
  - `config_file` (e.g. `/etc/krb5.conf`)
  - `keytab_file`
  - `disable_fast_negotiation` (default `false`).

## Metadata / Autocommit

- `metadata.full` (default `true`)
- `metadata.refresh_interval` (default `10m`)
- `metadata.retry.max` (default `3`)
- `metadata.retry.backoff` (default `250ms`)
- `autocommit.enable` (default `true`)
- `autocommit.interval` (default `1s`)

## Message Marking

- `message_marking.after` (default `false`)
- `message_marking.on_error` (default `false`)
- `message_marking.on_permanent_error` (default = value of `on_error`)

## Header Extraction

- `header_extraction.extract_headers` (default `false`)
- `header_extraction.headers` (default `[]`): exact-match header names. Extracted headers attached as resource attributes prefixed with `kafka.header.`.

## Error Backoff

- `enabled` (default `false`)
- `initial_interval`, `max_interval`, `multiplier`, `randomization_factor`, `max_elapsed_time`.

## Built-in Encodings

- All signals: `otlp_proto`, `otlp_json`.
- Logs only: `raw`, `text` (or `text_<ENCODING>` such as `text_utf-8`), `json`.

## Request-Metadata Propagation

Attaches `kafka.topic`, `kafka.partition`, `kafka.offset` plus all Kafka message headers to request metadata.

## Sample YAML — Receive Logs From Kafka

```yaml
receivers:
  kafka:
    brokers:
      - kafka-1.example.com:9092
      - kafka-2.example.com:9092
    protocol_version: 2.8.0
    client_id: otel-logs-collector
    group_id: otel-logs-consumer
    initial_offset: earliest
    session_timeout: 10s
    heartbeat_interval: 3s
    group_rebalance_strategy: cooperative-sticky
    logs:
      topics: [app-logs, infra-logs]
      encoding: json
    tls:
      insecure: false
      ca_file: /etc/ssl/certs/kafka-ca.pem
    auth:
      sasl:
        username: otel-user
        password: ${env:KAFKA_PASSWORD}
        mechanism: SCRAM-SHA-512
    autocommit:
      enable: true
      interval: 1s

service:
  pipelines:
    logs:
      receivers: [kafka]
      exporters: [elasticsearch]
```

## Common pitfalls (must enforce when generating configs)

1. Always set `protocol_version` to match the Kafka cluster (mismatch causes silent failures).
2. Use `${env:KAFKA_PASSWORD}` for passwords, never inline.
3. Set `encoding` to `json` or `text` for log payloads from typical app pipelines (otlp_proto only when source is OTel-encoded).
4. For initial backfill set `initial_offset: earliest`; otherwise `latest`.
