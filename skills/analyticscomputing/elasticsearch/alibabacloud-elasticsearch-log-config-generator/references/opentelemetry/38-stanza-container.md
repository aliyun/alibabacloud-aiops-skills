# stanza container operator

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/operators/container.md
>
> Parses container runtime log lines (Docker JSON / containerd CRI / CRI-O) and lifts standard fields. Recombines partial CRI lines (P-tagged) into a full record.

## Fields

| Field | Default | Notes |
|---|---|---|
| `format` | `""` (auto-detect) | One of `docker`, `crio`, `containerd`. Auto-detection inspects the line. |
| `add_metadata_from_filepath` | `true` | Pulls K8s identifiers from the log path. Requires `log.file.path` (set `include_file_path: true` on the receiver). |
| `max_log_size` | `1MiB` | Cap for partial-log recombination buffer. `0` disables the limit. |

## Format detection

| Runtime | Line shape | Extracted |
|---|---|---|
| Docker (JSON) | `{"log":"...","stream":"stdout","time":"..."}` | body = `log`, `log.iostream` = `stream`, timestamp = `time`. |
| containerd (CRI) | `2023-06-22T10:27:25.813Z stdout F line` | timestamp, `log.iostream`, `logtag` (`F` final / `P` partial), body. |
| CRI-O | `2024-04-13T07:59:37.505201169-05:00 stdout F line` | same as containerd; offset preserved on `time`, entry timestamp normalized to UTC. |

For CRI variants, `P`-tagged partials are merged into the next `F`-tagged record.

## K8s metadata from filepath

When `add_metadata_from_filepath: true` and the path is `/var/log/pods/<ns>_<pod>_<uid>/<container>/<restart>.log`, the operator emits resource attributes:

- `k8s.namespace.name`
- `k8s.pod.name`
- `k8s.pod.uid`
- `k8s.container.name`
- `k8s.container.restart_count`

## Minimal example

```yaml
receivers:
  filelog:
    include: [/var/log/pods/*/*/*.log]
    include_file_path: true
    operators:
      - type: container
```

## Pinning a runtime (skip auto-detect)

```yaml
operators:
  - type: container
    format: containerd
```
