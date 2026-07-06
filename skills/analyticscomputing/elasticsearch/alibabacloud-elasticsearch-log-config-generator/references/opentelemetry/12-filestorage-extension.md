# OpenTelemetry filestorage extension

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/extension/storage/filestorage/README.md

Provides on-disk persistence (e.g., for filelogreceiver offsets, exporter persistent queues).

## Top-level Options

- **`directory`** — path to data directory. Must exist unless `create_directory: true`.
  - Default on Windows: `%ProgramData%\Otelcol\FileStorage`
  - Default elsewhere: `/var/lib/otelcol/file_storage`
- **`timeout`** (default `1s`)
- **`fsync`** (default `false`) — flush after every write; safer but slower.
- **`create_directory`** — auto-create the storage dir.
- **`recreate`** — rename corrupted bbolt DB to `.backup` and start fresh.

### Compaction

- `compaction.on_start` (default `false`)
- `compaction.on_rebound` (default `false`)
- `compaction.directory`
- `compaction.max_transaction_size` (default `65536`)
- `compaction.rebound_needed_threshold_mib` (default `100`)
- `compaction.rebound_trigger_threshold_mib` (default `10`)
- `compaction.check_interval` (default `5s`)

## Sample — persistent offsets for filelog

```yaml
extensions:
  file_storage:
    directory: /var/lib/otelcol/file_storage
    create_directory: true

receivers:
  filelog:
    include: [/var/log/myapp/*.log]
    start_at: beginning
    storage: file_storage

exporters:
  elasticsearch:
    endpoint: https://elasticsearch:9200
    api_key: ${env:ELASTIC_API_KEY}

service:
  extensions: [file_storage]
  pipelines:
    logs:
      receivers: [filelog]
      exporters: [elasticsearch]
```
