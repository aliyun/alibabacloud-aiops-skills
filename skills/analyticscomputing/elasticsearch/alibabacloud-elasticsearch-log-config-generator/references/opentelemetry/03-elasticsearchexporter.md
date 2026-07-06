# OpenTelemetry elasticsearchexporter

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/exporter/elasticsearchexporter/README.md
> Distribution: contrib

## Connection Options (one of three is required)

- **`endpoint`**: target Elasticsearch URL, e.g. `https://elasticsearch:9200`.
- **`endpoints`**: list of Elasticsearch URLs, attempted in round-robin order.
- **`cloudid`**: Elastic Cloud ID for the target cluster.

If none are set, `endpoints` falls back to comma-separated `ELASTICSEARCH_URL` env var.

## Authentication

- **`user`** + **`password`**: HTTP Basic Auth.
- **`api_key`**: Elasticsearch API Key in encoded form.
- **`auth.authenticator`**: reference to an authenticator extension (e.g., `basicauth`). See `15-configauth.md`.
- Standard `configauth` settings supported — see `15-configauth.md`.

## HTTP Settings (from `confighttp`)

Full options live in `13-confighttp.md`. ES-relevant highlights:

- **`timeout`**: defaults to **90s** (overrides exporterhelper's 5s).
- **`compression`**: gzip enabled by default; disable with `compression: none`.
  - Other accepted algorithms: `zstd`, `snappy`, `zlib`, `deflate`, `lz4`, `none`.
  - Tune with `compression_params.level` (e.g., gzip/zlib/deflate `1`–`9` or `-1`; zstd `1`/`3`/`6`/`11`; snappy/lz4 don't support levels).
  - Default compression level is `1` (gzip.BestSpeed).
- TLS via `configtls` — see `14-configtls.md` for `ca_file`, `cert_file`, `key_file`, `min_version`, `insecure_skip_verify`, mTLS, etc.
- Other knobs available: `headers`, `proxy_url`, `max_idle_conns`, `idle_conn_timeout`, `read_buffer_size`, `write_buffer_size` — all documented in `13-confighttp.md`.
- Queue / retry / batch behavior is inherited from exporterhelper — see `17-exporterhelper.md`.

## Index / Data Stream Routing

- **`logs_index`**: target index/data stream for logs (and span events in OTel mode).
- **`metrics_index`**: target for metrics (in development).
- **`traces_index`**: target for traces.
- `*_dynamic_index.enabled` are DEPRECATED no-ops.

Routing precedence (first match wins):
1. Static (`logs_index` / `metrics_index` / `traces_index` if non-empty).
2. Dynamic via `elasticsearch.index` attribute (record > scope > resource).
3. Dynamic data stream via `${data_stream.type}-${data_stream.dataset}-${data_stream.namespace}`.

In `bodymap` mode, `data_stream.type` may be set dynamically from attributes (valid: `logs`, `metrics`).

Fallbacks: `data_stream.dataset` → `generic`, `data_stream.namespace` → `default`. In OTel mode, `data_stream.dataset` is suffixed with `.otel`.

### Logstash format

- **`logstash_format.enabled`** (default `false`).
- **`logstash_format.prefix_separator`** (default `-`).
- **`logstash_format.date_format`** (default `%Y.%m.%d`).

### Dynamic Document IDs

- **`logs_dynamic_id.enabled`** (default `false`): uses `elasticsearch.document_id` attribute when present.
- **`traces_dynamic_id.enabled`** (default `false`): same for spans.

## Mapping

- **`mapping.mode`** is being deprecated in favor of the `X-Elastic-Mapping-Mode` client metadata header or `elastic.mapping.mode` scope attribute, but config-file `mapping.mode` still works in current builds. Default is `otel`.
- **`mapping.allowed_modes`**: list restricting which modes may be requested (defaults to all).

Valid mapping modes:

| Mode | Behavior |
|------|----------|
| `otel` | Default; OTel-native schema, `data_stream.*` lifted to root, span events as separate docs |
| `ecs` | Maps OTel SemConv to Elastic Common Schema (under change) |
| `none` | Original OTLP field names; attributes prefixed with `Attributes.`, span events with `Events.` |
| `raw` | Same as `none` but without the `Attributes.`/`Events.` prefixes |
| `bodymap` | Logs only; uses log record body verbatim as document |

Signal support:

| Mode | Logs | Traces | Metrics | Profiles |
|------|------|--------|---------|----------|
| otel | ✅ | ✅ | ✅ | ✅ |
| ecs | ✅ | ✅ | ✅ | 🚫 |
| none | ✅ | ✅ | 🚫 | 🚫 |
| raw | ✅ | ✅ | 🚫 | 🚫 |
| bodymap | ✅ | 🚫 | 🚫 | 🚫 |

Notes: `otel`/`ecs` need Elasticsearch 8.12+; `otel` works best with 8.16+.

## Ingest Pipelines

- **`pipeline`**: default Elasticsearch ingest pipeline ID.
- **`logs_dynamic_pipeline.enabled`** (default `false`): uses `elasticsearch.ingest_pipeline` log record attribute if non-empty.

## Bulk Indexing

- **`retry`**:
  - `enabled` (default `true`)
  - `max_retries` (default `2`)
  - `initial_interval` (default `100ms`)
  - `max_interval` (default `1m`)
  - `retry_on_status` (default `[429]`)
- **`include_source_on_error`**: `true` / `false` / `null`. Requires ES 8.18+.

## Sending Queue / Batching

```yaml
sending_queue:
  enabled: true
  sizer: requests
  num_consumers: 10
  queue_size: 10
  batch:
    flush_timeout: 10s
    min_size: 1e+6   # 1MB
    max_size: 5e+6   # 5MB
    sizer: bytes
```

> Keep `max_size` well under Elasticsearch's `http.max_content_length` (recommended under 5MB).

Additional fields: `wait_for_result` (default `false`), `block_on_overflow` (default `false`).

## Node Discovery

- **`discover.on_start`**: query for cluster nodes on startup.
- **`discover.interval`**: refresh interval; `0` disables.

## Telemetry (experimental)

- **`telemetry.log_request_body`** (default `false`)
- **`telemetry.log_response_body`** (default `false`)
- **`telemetry.log_failed_docs_input`** (default `false`)
- **`telemetry.log_failed_docs_input_rate_limit`** (default `1s`)

All require `service::telemetry::logs::level: debug`.

## Sample Configurations

### Basic logs to ES with basic auth (via authenticator extension)

```yaml
exporters:
  elasticsearch:
    endpoint: https://elastic.example.com:9200
    auth:
      authenticator: basicauth

extensions:
  basicauth:
    client_auth:
      username: elastic
      password: changeme

service:
  extensions: [basicauth]
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [elasticsearch]
```

### Inline basic auth

```yaml
exporters:
  elasticsearch:
    endpoints: [https://es-node-1:9200, https://es-node-2:9200]
    user: elastic
    password: ${env:ELASTIC_PASSWORD}
    tls:
      ca_file: /etc/ssl/certs/elasticsearch-ca.pem
```

### API key auth + cloud ID

```yaml
exporters:
  elasticsearch:
    cloudid: my-cluster:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvOjQ0MyR...
    api_key: ${env:ELASTIC_API_KEY}
```

### Static logs index (vs data stream)

```yaml
exporters:
  elasticsearch:
    endpoint: https://elasticsearch:9200
    api_key: ${env:ELASTIC_API_KEY}
    logs_index: my-logs-index
    mapping:
      mode: ecs
```

### Data stream routing (default)

```yaml
exporters:
  elasticsearch:
    endpoint: https://elasticsearch:9200
    api_key: ${env:ELASTIC_API_KEY}
    mapping:
      mode: otel
```

The data stream name uses `data_stream.type-data_stream.dataset-data_stream.namespace`. With OTel mode, dataset gets suffixed with `.otel` (e.g., `logs-myapp.otel-default`).

### Setting mapping mode via scope attribute (recommended new way)

```yaml
processors:
  transform:
    log_statements:
      - context: scope
        statements:
          - set(attributes["elastic.mapping.mode"], "otel")

exporters:
  elasticsearch:
    endpoint: https://elasticsearch:9200

service:
  pipelines:
    logs:
      receivers: [otlp]
      processors: [transform]
      exporters: [elasticsearch]
```

## Common pitfalls (must enforce when generating configs)

1. Provide exactly ONE of `endpoint`, `endpoints`, or `cloudid`.
2. Choose mapping mode based on ES version: `otel` (8.16+ ideal, 8.12+ minimum), `ecs` for ECS-style fields, `none`/`raw` for raw OTLP-shaped docs.
3. When using `logs_index` (a static index), data-stream routing is bypassed — confirm with user whether they want a data stream (default) or a classic index.
4. Authentication: do NOT inline secrets — always use `${env:...}` substitution.
5. For HTTPS without proper certs, use `tls.insecure_skip_verify: true` only as a last resort and warn the user.
