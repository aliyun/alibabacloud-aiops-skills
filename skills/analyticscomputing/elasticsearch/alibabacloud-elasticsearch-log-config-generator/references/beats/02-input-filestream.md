# Filebeat filestream Input

> Source: https://www.elastic.co/docs/reference/beats/filebeat/filebeat-input-filestream

The recommended modern input for tailing log files. Replaces the legacy `log` input.

## Minimum Sample

```yaml
filebeat.inputs:
- type: filestream
  id: my-filestream-id
  paths:
    - /var/log/messages
    - /var/log/*.log
```

Each input requires a unique `id`. Omitting/changing it can cause data duplication.

## Core Options

| Option | Description |
|---|---|
| `id` | **required**, unique. Changing it triggers re-ingestion. |
| `paths` | List of glob paths. Supports Go glob. |
| `enabled` | default `true` |
| `tags` | Appended to `tags` field. |
| `fields` / `fields_under_root` | Custom fields; under root or nested. |
| `encoding` | `plain`, `utf-8`, `utf-16-bom`, `gbk`, `iso8859-1`, etc. |
| `buffer_size` | Per-harvester read buffer (bytes). Default `16384`. |
| `message_max_bytes` | Max bytes per message (extra dropped). Default 10MB. |
| `include_lines` / `exclude_lines` | Regex line filters. |
| `harvester_limit` | Cap parallel harvesters. Default `0` (unlimited). |
| `processors` | Inline processor list. |
| `pipeline` | Elasticsearch ingest pipeline ID. |
| `index` | Static index override. |

```yaml
include_lines: ['^ERR', '^WARN']
exclude_lines: ['^DBG']
```

## File Identity

Default since 9.0 is **`fingerprint`** (content hash) — recommended for network shares, cloud, and Windows.

```yaml
file_identity.fingerprint: ~       # default
# file_identity.native: ~          # inode+device (legacy)
# file_identity.path: ~            # path-based (NOT safe with rotation into same glob)
# file_identity.inode_marker.path: /logs/.filebeat-marker
```

Migration only supported from `native` or `path` → `fingerprint`.

## Prospector / Scanner

```yaml
prospector.scanner.check_interval: 10s          # avoid <1s
prospector.scanner.recursive_glob: true         # expand ** up to 8 levels
prospector.scanner.symlinks: false
prospector.scanner.exclude_files: ['\.gz$']
prospector.scanner.include_files: ['^/var/log/.*']
prospector.scanner.resend_on_touch: false
prospector.scanner.fingerprint:
  enabled: true
  offset: 0
  length: 1024                                  # min 64
```

Files smaller than `offset + length` are ignored until they grow.

## Close / Cleanup

| Option | Description | Default |
|---|---|---|
| `close.on_state_change.inactive` | Close handle after inactivity. | `5m` |
| `close.on_state_change.renamed` | Close on rename. | off |
| `close.on_state_change.removed` | Close on file removal. | on (Windows); off (other) |
| `close.reader.on_eof` | Close at EOF. | off |
| `close.reader.after_interval` | Close after fixed lifetime. | `0` (off) |

`clean_inactive` must satisfy `> ignore_older + prospector.scanner.check_interval`.

## Backoff

```yaml
backoff.init: 2s
backoff.max:  10s    # init <= max <= scanner.check_interval
```

## ignore_older / ignore_inactive

- `ignore_older` — skip files older than duration. Must be `> close.on_state_change.inactive`. Default `0`.
- `ignore_inactive` — `since_first_start` or `since_last_start`.

## take_over (state migration)

```yaml
take_over:
  enabled: true
  from_ids: [foo, bar]
```

Source inputs must be inactive.

## GZIP

```yaml
compression: auto   # "", "gzip", or "auto"
```

Requires `file_identity: fingerprint`. GZIP files are immutable — harvester closes at EOF.

## Delete after ingestion

```yaml
delete:
  enabled: true
  grace_period: 30m
```

Keep `clean_removed: true` when delete is enabled.

## Parsers (ordered list)

```yaml
parsers:
  - ndjson:
      target: ""
      message_key: msg
      add_error_key: true
      overwrite_keys: false
      expand_keys: false
  - multiline:
      type: pattern
      pattern: '^\['
      negate: true
      match: after
  - container:
      stream: stdout      # all | stdout | stderr
      format: auto        # auto | docker | cri
  - syslog:
      format: rfc3164     # rfc3164 | rfc5424 | auto
      timezone: Asia/Shanghai
  - include_message:
      patterns: ['^ERR', '^WARN']
```

## Log rotation

Built-in `create` and `rename` strategies need no extra config. For `copytruncate`:

```yaml
rotation.external.strategy.copytruncate:
  suffix_regex: \.\d$
```

## Common pitfalls

1. Always provide a unique `id`. Removing or changing it re-ingests data.
2. Don't combine GZIP with `copytruncate` rotation.
3. `paths` patterns must be absolute.
