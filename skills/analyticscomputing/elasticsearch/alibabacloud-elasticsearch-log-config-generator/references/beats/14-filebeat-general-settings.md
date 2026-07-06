# Filebeat general settings

> Source: https://www.elastic.co/docs/reference/beats/filebeat/configuration-general-options
>
> Top-level options shared by all Beats — declared at the root of `filebeat.yml`, separate from `filebeat.inputs`, `output.*`, `processors`, `setup.*`, etc.

## Options

| Field | Type | Default | What it does |
|---|---|---|---|
| `name` | string | server hostname | Identifies the Beat. Surfaces as `agent.name` on every event; useful for grouping shipments from one host. |
| `tags` | []string | — | Labels added to the `tags` field of every event (group hosts by tier/role/service). |
| `fields` | map | — | Static metadata attached to every event. Nests under `fields.*` by default. |
| `fields_under_root` | bool | `false` | When `true`, `fields` keys land at the event root. **Custom keys overwrite existing top-level keys on collision** — name them carefully. |
| `processors` | []processor | — | Global processor pipeline (see `06-processors.md` and `13-filebeat-processors-detail.md`). |
| `max_procs` | int | logical CPU count | Caps how many CPUs Filebeat may use concurrently (Go `GOMAXPROCS`). |
| `timestamp.precision` | enum | `millisecond` | One of `millisecond` / `microsecond` / `nanosecond`. Applies to all event timestamps. |

## Minimal example

```yaml
name: edge-shipper-prod-01
tags: [prod, edge]
fields:
  service: payments
  region: ap-southeast-1
fields_under_root: true
max_procs: 4
timestamp.precision: millisecond
```

## When to use which

| Goal | Pick |
|---|---|
| Same label on every event from this Beat | `tags` (array) or `fields` (k=v) |
| Make ECS-style top-level fields (e.g., `service.name`) | `fields` + `fields_under_root: true` |
| Identify which shipper produced an event | `name` (lands in `agent.name`) |
| Higher-resolution timestamps for ES Index lifecycle / ordering | `timestamp.precision: nanosecond` |
| Cap CPU on a noisy node | `max_procs: <n>` |

## Note on path settings

Filesystem paths (`path.home`, `path.config`, `path.data`, `path.logs`) live in their own `configuration-path` section of the docs. They're typically set via CLI flags (`-path.home …`), env vars (`HOMEPATH`, `CONFIGPATH`, `DATAPATH`, `LOGPATH`), or the package defaults — not commonly inlined into `filebeat.yml`. Pull `configuration-path` separately if a deployment customises them.
