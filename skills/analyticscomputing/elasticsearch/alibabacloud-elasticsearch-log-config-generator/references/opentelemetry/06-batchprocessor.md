# OpenTelemetry batchprocessor

> Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/batchprocessor/README.md

The batch processor groups logs/metrics/traces into batches to improve compression efficiency and reduce outbound connections.

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `send_batch_size` | `8192` | Item-count threshold that triggers a batch send before timeout elapses. Trigger only — does not cap batch size. |
| `timeout` | `200ms` | Maximum wait before flushing a batch. `0` disables time trigger. |
| `send_batch_max_size` | `0` | Hard upper bound on batch size; oversized batches split. `0` disables cap. Must be ≥ `send_batch_size`. |
| `metadata_keys` | empty | Per unique `client.Metadata` value combination, create a separate batcher. |
| `metadata_cardinality_limit` | `1000` | Caps distinct metadata combinations when `metadata_keys` is set. |

## Sample

```yaml
processors:
  batch:
    send_batch_size: 8192
    send_batch_max_size: 10000
    timeout: 5s

service:
  pipelines:
    logs:
      receivers: [filelog]
      processors: [batch]
      exporters: [elasticsearch]
```

## Notes

- Position batch processor **after** `memory_limiter` and any sampling processors.
- For `metadata_keys` to work, receivers must enable `include_metadata: true`.
- Batching by metadata raises memory usage; each combination keeps a pending batch.
