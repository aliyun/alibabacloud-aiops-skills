# routing connector (note: connector, not processor)

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/connector/routingconnector/README.md
>
> Sits between pipelines as both an exporter (in the source pipeline) and a receiver (in each downstream pipeline). Dispatches data based on OTTL conditions. Use this when the older `routingprocessor` would have applied — it has been replaced by this connector.

## Why a connector instead of a processor

- Processors operate within one pipeline.
- Routing changes which pipeline (and therefore which exporters) data flows into. That's a connector's job.
- The wiring pattern: `routing` appears as an **exporter** on the source pipeline and a **receiver** on each downstream pipeline.

## Supported telemetry

Alpha for traces, metrics, logs. Both exporter and receiver roles are supported per signal.

## Top-level fields

| Field | Default | Description |
|---|---|---|
| `table` | required | Routing table; see entry fields below. |
| `default_pipelines` | — | Pipelines for records matching no entry. |
| `error_mode` | `propagate` | `propagate` / `ignore` / `silent`. With ignore/silent, errored records go to `default_pipelines`; silent suppresses logging. |

> `match_once` was deprecated in v0.116.0 and **removed** in v0.120.0. Migration: split into parallel routers, enumerate combined conditions, or layer routers.

## Table entry

| Field | Default | Description |
|---|---|---|
| `context` | `resource` | OTTL context: `resource`, `span`, `metric`, `datapoint`, `log`, or `request`. |
| `statement` | — | OTTL statement form. Required if `condition` not set. Not allowed for `request` context. |
| `condition` | — | OTTL condition form. Required if `statement` not set. **Required** for `request` context. |
| `action` | `move` | `move` (matched data exits further evaluation) or `copy` (continues through later routes). |
| `pipelines` | required | Target pipelines on match. |

`request` context grammar is restricted to `request["key"] == "value"` / `request["key"] != "value"`.

## Example 1 — Route by tenant header (request context)

```yaml
connectors:
  routing:
    default_pipelines: [logs/other]
    table:
      - context: request
        condition: request["X-Tenant"] == "acme"
        pipelines: [logs/acme]
      - context: request
        condition: request["X-Tenant"] == "ecorp"
        pipelines: [logs/ecorp]

exporters:
  elasticsearch/acme:
    endpoints: [https://es-acme.example.com:9200]
    api_key: ${env:ES_KEY_ACME}
    mapping: {mode: otel}
  elasticsearch/ecorp:
    endpoints: [https://es-ecorp.example.com:9200]
    api_key: ${env:ES_KEY_ECORP}
    mapping: {mode: otel}
  elasticsearch/other:
    endpoints: [https://es-default.example.com:9200]
    api_key: ${env:ES_KEY_DEFAULT}
    mapping: {mode: otel}

service:
  pipelines:
    logs/in:
      receivers: [otlp]
      exporters: [routing]
    logs/acme:
      receivers: [routing]
      exporters: [elasticsearch/acme]
    logs/ecorp:
      receivers: [routing]
      exporters: [elasticsearch/ecorp]
    logs/other:
      receivers: [routing]
      exporters: [elasticsearch/other]
```

## Example 2 — Tier by severity + service.name

```yaml
connectors:
  routing:
    table:
      - context: log
        condition: severity_number < SEVERITY_NUMBER_ERROR
        pipelines: [logs/cheap]
      - context: resource
        condition: attributes["service.name"] == "service1"
        pipelines: [logs/service1]
      - context: resource
        condition: attributes["service.name"] == "service2"
        pipelines: [logs/service2]
```

## Multiple instances

Run side-by-side via name aliasing (`routing/env`, `routing/region`) and list both as exporters on the source pipeline — each receives an independent copy of the data.

## Supported OTTL functions

Standard converter functions, plus `delete_key` and `delete_matching_keys`.
