# Filebeat — internal queue (queue.mem / queue.disk)

> Source: https://www.elastic.co/guide/en/beats/filebeat/current/configuring-internal-queue.html
>
> Sits between inputs and `output.elasticsearch`. Only one queue type can be configured at a time. Settings may be top-level (`queue:`) or nested under an output's `queue:`.

## queue.mem (default)

In-memory buffer.

| Option | Default | Description |
|---|---|---|
| `events` | `3200` | Capacity in events. |
| `flush.min_events` | `1600` | Caps batch size when >1; `0`/`1` falls back to half the queue size in synchronous mode. Legacy — prefer the output's `bulk_max_size`. |
| `flush.timeout` | `10s` | Max wait before returning a partial batch; `0s` = synchronous. |

```yaml
queue.mem:
  events: 4096
  flush.min_events: 512
  flush.timeout: 5s
```

## queue.disk

Persistent disk-backed buffer; survives restarts at the cost of throughput.

| Option | Default | Description |
|---|---|---|
| `path` | `${path.data}/diskqueue` | Auto-created on start. |
| `max_size` (**required**) | `10GB` | Disk cap. `0` disables the cap — only safe on a dedicated partition. |
| `segment_size` | `max_size / 10` | Per-file segment size. |
| `read_ahead` | `512` | Events pre-read into memory; raise for slow outputs. |
| `write_ahead` | `2048` | Events buffered before disk write; raise to absorb input bursts. |
| `retry_interval` | `1s` | Backoff start on disk errors. |
| `max_retry_interval` | `30s` | Backoff cap. |

```yaml
queue.disk:
  max_size: 10GB
```

## Notes

- Disk queue is the right choice if Elasticsearch outages are common and event loss on Filebeat restart is unacceptable.
- For high-throughput pure-memory operation, raise `queue.mem.events` instead of switching queues.
- Only one queue may be active globally.
