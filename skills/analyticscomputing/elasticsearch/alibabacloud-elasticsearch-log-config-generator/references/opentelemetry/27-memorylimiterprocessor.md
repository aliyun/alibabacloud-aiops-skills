# memory_limiter processor

> Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/memorylimiterprocessor/README.md
>
> **Place this first in every pipeline**. It guards against OOM by refusing new data when memory crosses a soft limit and forces GC at the hard limit.

## Fields

| Field | Default | Description |
|---|---|---|
| `check_interval` | `0s` | Sampling interval; `1s` is the recommended floor. Lower it (or raise `spike_limit_mib`) for spiky traffic. |
| `limit_mib` | `0` | Hard limit on Go heap (MiB). Total RSS is typically ~50 MiB above this. |
| `spike_limit_mib` | 20% of `limit_mib` | Max spike between checks. Must be < `limit_mib`. Soft limit = `limit_mib − spike_limit_mib`. |
| `limit_percentage` | `0` | Hard limit as % of available memory (cgroups; container-friendly). |
| `spike_limit_percentage` | 20% of `limit_percentage` | Spike % when using percentage limit. |

One of `limit_mib` or `limit_percentage` must be set. `limit_mib` wins if both are.

## Behavior

- **Soft limit crossed** → refuse new data with a non-permanent error; receivers retry / apply backpressure.
- **Hard limit crossed** → refuse + force GC.
- **Drop back below soft** → resume normal operation.

Caveat: data already buffered upstream of the processor may still consume memory before being rejected. Size accordingly, especially with non-OTLP receivers.

If a receiver doesn't honor backpressure, refused data is permanently lost — that receiver is considered incorrectly implemented.

## Best practices

- Always **first** processor in the pipeline.
- Set `GOMEMLIMIT` env var to ~80% of the hard limit.
- Default `spike_limit_mib` of ~20% of hard limit; bump for spiky traffic or longer `check_interval`.
- `limit_percentage` for K8s/containers; `limit_mib` for VMs/bare metal.

## Examples

Fixed MiB:

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 4000
    spike_limit_mib: 800
    # hard 4000 / soft 3200
```

Container percentage:

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 15
    # on a 1000 MiB pod: hard 800 / soft 650
```

Wire it first:

```yaml
service:
  pipelines:
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [elasticsearch]
```
