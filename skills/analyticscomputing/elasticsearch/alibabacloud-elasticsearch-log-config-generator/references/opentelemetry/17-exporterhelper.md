# exporterhelper — sending_queue / retry_on_failure / timeout / batcher

> Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md
>
> The Elasticsearch exporter (and most OTel exporters) inherit these knobs. This is where queue/batch/retry semantics actually live.

## `sending_queue`

| Option | Default | Description |
|---|---|---|
| `enabled` | `true` | Toggle the sending queue. |
| `num_consumers` | `10` | Concurrent dequeue workers (ignored when disabled). |
| `queue_size` | `1000` | Capacity, measured per `sizer`. |
| `wait_for_result` | `false` | Caller blocks until processing completes. |
| `block_on_overflow` | `false` | Block instead of drop when full. |
| `sizer` | `requests` | One of `requests`, `items`, or `bytes`. |
| `storage` | unset | Storage extension name; if set, queue is **persistent** (no in-memory queue). |

Overflow drops by default; enqueue failures are reported via `otelcol_exporter_enqueue_failed_*` metrics and skip retry logic.

## `sending_queue.batch`

Off by default; supply `batch: {}` to enable defaults.

| Option | Default | Description |
|---|---|---|
| `flush_timeout` | `200ms` | Flush deadline regardless of size; must be non-zero. |
| `min_size` | `8192` | Minimum batch size; usually ≤ `queue_size` when sizers match. |
| `max_size` | `0` | Max batch size; `0` disables splitting. |
| `sizer` | inherits parent (else `items`) | One of `items`, `bytes`. |
| `partition.metadata_keys` | empty | `client.Metadata` keys; one batcher per distinct value combination (case-insensitive; duplicates fail). |

## `retry_on_failure`

| Option | Default | Description |
|---|---|---|
| `enabled` | `true` | Toggle retries. |
| `initial_interval` | `5s` | Wait before first retry. |
| `max_interval` | `30s` | Backoff upper bound. |
| `max_elapsed_time` | `300s` | Total retry budget; `0` = unlimited. |
| `multiplier` | `1.5` | Backoff multiplier per attempt. |

## `timeout`

- Default: `5s`. Per-attempt send timeout. (ES exporter overrides default to `90s`.)

Duration units: `ns`, `us`/`µs`, `ms`, `s`, `m`, `h`.

## Persistent queue notes

- Backed by a storage extension (commonly `file_storage`).
- Survives restarts: items resume after collector restart.
- Client metadata + span context are preserved across persistence; **auth-injected context is NOT** — no auth/authz info is available after replay.

## Sample YAML — OTLP-style with persistent queue

```yaml
exporters:
  otlp:
    endpoint: otel-backend.example.com:4317
    timeout: 5s
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
      multiplier: 1.5
    sending_queue:
      enabled: true
      num_consumers: 10
      queue_size: 1000
      sizer: requests
      block_on_overflow: false
      storage: file_storage/otc
      batch:
        flush_timeout: 200ms
        min_size: 8192
        max_size: 0
        sizer: items

extensions:
  file_storage/otc:
    directory: /var/lib/storage/otc
    timeout: 10s

service:
  extensions: [file_storage/otc]
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [otlp]
```

## Sample YAML — Elasticsearch-style (bytes-based queue + batch)

```yaml
exporters:
  elasticsearch:
    endpoints: [https://es.example.com:9200]
    api_key: ${env:ELASTIC_API_KEY}
    timeout: 90s          # ES exporter default
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
      multiplier: 1.5
    sending_queue:
      enabled: true
      num_consumers: 10
      sizer: bytes
      queue_size: 33554432   # 32 MiB
      storage: file_storage/es
      batch:
        flush_timeout: 200ms
        sizer: bytes
        min_size: 1048576    # 1 MiB
        max_size: 5242880    # 5 MiB
```

## ES exporter override (cross-reference)

The ES exporter's own README documents:

- `timeout` default overridden to `90s`.
- The exporter wraps **its own** batcher inside the queue; check `exporter/elasticsearchexporter/README.md` for any extra knobs.
