# OpenTelemetry filelogreceiver

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/filelogreceiver/README.md
> Stability: beta (logs). Distributions: contrib, k8s.

The File Log Receiver tails and parses logs from files.

## Configuration Options

### File selection

| Field | Default | Purpose |
|---|---|---|
| `include` | required | Glob patterns for files to read |
| `exclude` | `[]` | Glob patterns excluded from `include` matches |
| `exclude_older_than` | — | Skip files whose mtime exceeds the given age |
| `ordering_criteria.regex` | — | Regex with named capture groups used by `regex_key` |
| `ordering_criteria.group_by` | — | Pre-sort grouping regex with named capture groups |
| `ordering_criteria.top_n` | `1` | Number of files tracked after ordering |
| `ordering_criteria.sort_by.regex_key` | — | Capture-group name used for sorting |
| `ordering_criteria.sort_by.sort_type` | — | One of `numeric`, `alphabetical`, `timestamp`, `mtime` |
| `ordering_criteria.sort_by.location` | — | Timestamp location (when `sort_type: timestamp`) |
| `ordering_criteria.sort_by.format` | — | strptime format for timestamp sorting |
| `ordering_criteria.sort_by.ascending` | — | Direction of the sort |

### Reading behavior

| Field | Default | Purpose |
|---|---|---|
| `start_at` | `end` | `beginning` or `end` at startup |
| `multiline` | — | See multiline section |
| `force_flush_period` | `500ms` | Idle time before emitting a partial trailing log |
| `encoding` | `utf-8` | See supported encodings list |
| `preserve_leading_whitespaces` | `false` | Keep leading whitespace |
| `preserve_trailing_whitespaces` | `false` | Keep trailing whitespace |
| `poll_interval` | `200ms` | Filesystem polling cadence |
| `fingerprint_size` | `1000` | Bytes used to identify a file (min 16) |
| `initial_buffer_size` | `16KiB` | Starting buffer for headers/logs |
| `max_log_size` | `1MiB` | Per-entry size cap |
| `max_log_size_behavior` | `split` | `split` or `truncate` for oversized entries |
| `max_concurrent_files` | `1024` | Concurrent file cap (otherwise batched) |
| `max_batches` | `0` | Per-poll batch limit; `0` = unlimited |
| `delete_after_read` | `false` | Read then delete; needs `filelog.allowFileDeletion` gate; incompatible with `start_at: end` |
| `acquire_fs_lock` | `false` | Try to acquire an FS lock (Unix only) |
| `file_cache_advise` | `false` | Linux page-cache hint for sequential reads |
| `compression` | — | `""`, `gzip`, or `auto` |
| `polls_to_archive` | `0` | Poll cycles persisted to disk (experimental) |
| `on_truncate` | `ignore` | `ignore`, `read_whole_file`, or `read_new` |

### File attributes added to entries

| Field | Default | Attribute |
|---|---|---|
| `include_file_name` | `true` | `log.file.name` |
| `include_file_path` | `false` | `log.file.path` |
| `include_file_name_resolved` | `false` | `log.file.name_resolved` |
| `include_file_path_resolved` | `false` | `log.file.path_resolved` |
| `include_file_owner_name` | `false` | `log.file.owner.name` (not Windows) |
| `include_file_owner_group_name` | `false` | `log.file.owner.group.name` (not Windows) |
| `include_file_permissions` | `false` | `log.file.permissions` (3-digit octal; not Windows) |
| `include_file_record_number` | `false` | `log.file.record_number` |
| `include_file_record_offset` | `false` | `log.file.record_offset` |

### Pipeline / persistence / headers

| Field | Default | Purpose |
|---|---|---|
| `attributes` | `{}` | Static attribute map |
| `resource` | `{}` | Static resource map |
| `operators` | `[]` | Pipeline of stanza operators |
| `storage` | none | Storage extension ID for offset persistence |
| `header` | `nil` | Header parsing config; needs `filelog.allowHeaderMetadataParsing`; not allowed with `start_at: end` |
| `header.pattern` | required (if header used) | Regex matching every header line |
| `header.metadata_operators` | required (if header used) | Operators that build header metadata |

### Retry on failure

| Field | Default |
|---|---|
| `retry_on_failure.enabled` | `false` |
| `retry_on_failure.initial_interval` | `1s` |
| `retry_on_failure.max_interval` | `30s` |
| `retry_on_failure.max_elapsed_time` | `5m` (set to `0` to retry forever) |

> Important caveat: by default, no logs are read from a file that isn't actively being written, because `start_at` defaults to `end`. For initial backfill use `start_at: beginning`.

## Operators

- Every operator has a `type`.
- `id` defaults to `type`; you must set `id` if a type appears more than once.
- Operators flow to the next in the list; the final one emits from the receiver. An explicit `output` can redirect to another operator's `id`.
- Common operators: `json_parser`, `regex_parser`, `csv_parser`, `syslog_parser`, `time_parser`, `severity_parser`, `add`, `move`, `copy`, `remove`, `filter`, `router`, `recombine` (multiline join).
- Full local references:
  - `21-stanza-operators-overview.md` — catalog and common fields (`id`, `type`, `output`, `on_error`, `parse_from`, `parse_to`, `if`).
  - `22-stanza-json_parser.md`, `23-stanza-regex_parser.md`, `24-stanza-recombine.md`.
  - `25-stanza-timestamp.md` (strptime/gotime/epoch layouts), `26-stanza-severity.md` (token list, mapping syntax).

## Multiline

The `multiline` block must specify exactly one of `line_start_pattern` or `line_end_pattern` (regex). `omit_pattern` strips the matched delimiter from each emitted entry.

## Supported encodings

| Key | Notes |
|---|---|
| `nop` | Treats input as raw bytes; no validation |
| `utf-8` | Default UTF-8 |
| `utf-8-raw` | UTF-8 without invalid-byte replacement |
| `utf-16le` | UTF-16 little-endian |
| `utf-16be` | UTF-16 big-endian |
| `ascii` | ASCII |
| `big5` | Big5 Chinese |

Other IANA encodings work on a best-effort basis.

## Time parameters

All durations require explicit units, e.g. `200ms`, `1s`, `1m`.

## Log rotation

Both **move/create** and **copy/truncate** rotation strategies are supported. Files are tracked by inode plus content fingerprint, so reads continue even when the new filename no longer matches `include`.

### Copytruncate handling (`on_truncate`)

- `ignore` (default): keep the saved offset; wait for the file to grow past it.
- `read_whole_file`: reset offset to 0 and re-read everything.
- `read_new`: jump the offset to the current size; only new writes are read.

## Examples

### Tail a JSON file

```yaml
receivers:
  filelog:
    include: [ /var/log/myservice/*.json ]
    start_at: beginning
    operators:
      - type: json_parser
        timestamp:
          parse_from: attributes.time
          layout: '%Y-%m-%d %H:%M:%S'
```

### Tail plaintext with regex parsing

```yaml
receivers:
  filelog:
    include: [ /simple.log ]
    operators:
      - type: regex_parser
        regex: '^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<sev>[A-Z]*) (?P<msg>.*)$'
        timestamp:
          parse_from: attributes.time
          layout: '%Y-%m-%d %H:%M:%S'
        severity:
          parse_from: attributes.sev
```

### Multiline (Java stack trace)

```yaml
receivers:
  filelog:
    include: [ /var/log/example/multiline.log ]
    multiline:
      line_start_pattern: ^Exception
```

### Compressed (gzip) input

```yaml
receivers:
  filelog:
    include: [ /var/log/example/compressed.log.gz ]
    compression: gzip
```

### Persistent offsets (storage extension)

```yaml
extensions:
  file_storage:
    directory: /var/lib/otelcol/file_storage

receivers:
  filelog:
    include: [ /var/log/myapp/*.log ]
    start_at: beginning
    storage: file_storage

service:
  extensions: [file_storage]
  pipelines:
    logs:
      receivers: [filelog]
      exporters: [...]
```

## Troubleshooting

- **Symlinked targets**: set `poll_interval` shorter than the symlink's update frequency.
- **Telemetry**: when Collector internal metrics are enabled, watch `otelcol_fileconsumer_open_files` and `otelcol_fileconsumer_reading_files`.

## Common pitfalls (must enforce when generating configs)

1. Without `start_at: beginning`, existing log files won't be read — only newly written lines after collector start. Confirm intent with the user.
2. Include patterns must be absolute glob paths.
3. For high-volume rotated logs, prefer `include: [/var/log/app/*.log*]` and configure `on_truncate` correctly.
4. To survive collector restarts without re-reading, configure `storage:` with a `file_storage` extension.
