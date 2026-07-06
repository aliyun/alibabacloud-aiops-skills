# Filebeat Elasticsearch Output

> Source: https://www.elastic.co/docs/reference/beats/filebeat/elasticsearch-output

## Connection / Routing

- **`hosts`**: list of ES nodes (URL or `IP:PORT`, default port `9200`). All hosts must be in the same cluster. Events distributed round-robin.
- **`protocol`**: `http` or `https`. Defaults to `http`. Overridden by URL scheme in `hosts`.
- **`path`**: HTTP path prefix.
- **`parameters`**: query params appended to index ops.
- **`headers`**: custom HTTP headers.
- **`proxy_url`**: HTTP proxy URL. Falls back to `HTTP_PROXY`/`HTTPS_PROXY` env vars.

## Authentication

- **`username`** / **`password`**: Basic auth.
- **`api_key`**: `id:api_key` format. Mutually exclusive with username/password.
- **`ssl`**: TLS settings (`certificate_authorities`, `certificate`, `key`, `verification_mode`).

## Indexing targets

- **`index`**: target index/alias/data stream. Default: `filebeat-%{[agent.version]}-%{+yyyy.MM.dd}`. Supports format strings. **When ILM is enabled, custom `index` is ignored.**
- **`indices`**: ordered selector rules (`index`, `when` conditions). First match wins; defining `indices` disables ILM.
- **`ilm`**: Index Lifecycle Management settings.
- **`pipeline`**: ES ingest pipeline name. Supports format strings.
- **`pipelines`**: list of conditional ingest pipelines.

## Performance / Reliability

| Option | Default | Notes |
|---|---|---|
| `preset` | `custom` | `balanced` / `throughput` / `scale` / `latency` / `custom`. Bundles overrides toward a goal; **applied last, overrides matching user fields**. See "Presets" below. |
| `bulk_max_size` | `1600` | events per `_bulk` request |
| `worker` (alias `workers`) | `1` | connections per host |
| `loadbalance` | `true` | parallel sends across all hosts |
| `compression_level` | `1` | gzip 0–9 |
| `escape_html` | `false` | |
| `timeout` | `90` | HTTP timeout (seconds) |
| `idle_connection_timeout` | `3s` | idle connection lifetime |
| `max_retries` | n/a | ignored — retries indefinitely |
| `backoff.init` | `1s` | initial reconnect wait |
| `backoff.max` | `60s` | reconnect backoff cap |
| `queue` | — | mem or disk queue (set in only one place). Full options in `12-internal-queue.md`. |
| `non_indexable_policy` | `drop` | What to do when ES rejects a doc: `drop` discards. `dead_letter_index` reroutes to a named index — **deprecated 9.5.0+, beta 9.0–9.4**; the recommended path is the data stream failure store. |
| `allow_older_versions` | `true` | When `false`, refuse to connect to ES older than this Filebeat. Useful but can prevent reconnection after upgrading the Beat past the stack. |
| `proxy_disable` | `false` | Ignore all proxy env vars. |
| `proxy_headers` | — | Extra headers on `CONNECT`. |

### Presets

| Preset | Goal | Example overrides |
|---|---|---|
| `balanced` | General efficiency | sane defaults — good starting point. |
| `throughput` | High data volumes (more CPU/RAM) | e.g., `worker: 4`, `queue.mem.events: 12800`, `queue.mem.flush.timeout: 5s`, `idle_connection_timeout: 15s`. |
| `scale` | Low ambient load on large fleets | trims per-instance worker counts and queue sizes. |
| `latency` | Minimise time to visibility | shrinks batch sizes / flush timeouts. |
| `custom` | No overrides (default) | use only your explicit fields. |

A preset replaces matching settings; anything you don't set falls back to user values then defaults.

## Sample — Minimal

```yaml
output.elasticsearch:
  hosts: ["http://localhost:9200"]
```

## Sample — HTTPS + API Key

```yaml
output.elasticsearch:
  hosts: ["https://myEShost:9200"]
  protocol: https
  api_key: "${ELASTIC_API_KEY}"
  index: "filebeat-%{[agent.version]}-%{+yyyy.MM.dd}"
  ssl:
    certificate_authorities: ["/etc/pki/root/ca.pem"]
    verification_mode: full
  worker: 2
  bulk_max_size: 1600
  backoff.init: 1s
  backoff.max: 60s
```

## Sample — Conditional indices (data stream / index per severity)

```yaml
output.elasticsearch:
  hosts: ["https://es:9200"]
  username: "${ELASTIC_USER}"
  password: "${ELASTIC_PASSWORD}"
  ssl.verification_mode: full
  index: "filebeat-default-%{+yyyy.MM.dd}"
  indices:
    - index: "warning-%{+yyyy.MM.dd}"
      when.contains:
        message: WARN
    - index: "error-%{+yyyy.MM.dd}"
      when.contains:
        message: ERR
```

## Sample — `preset: throughput` (modern tuning)

```yaml
output.elasticsearch:
  hosts: ["https://myEShost:9200"]
  api_key: "${ELASTIC_API_KEY}"
  preset: throughput
  allow_older_versions: false
  non_indexable_policy.drop: ~
```

## Sample — Conditional `pipelines:` with default fallback

```yaml
output.elasticsearch:
  hosts: ["https://myEShost:9200"]
  api_key: "${ELASTIC_API_KEY}"
  preset: balanced

  # First-match-wins routing rules
  pipelines:
    - pipeline: "warning_pipeline"
      when.contains:
        message: "WARN"
    - pipeline: "error_pipeline"
      when.contains:
        message: "ERR"
    - pipeline: "%{[fields.log_type]}"
      mappings:
        critical: "sev1_pipeline"
        normal:   "sev2_pipeline"
      default:    "sev3_pipeline"

  # Fallback if no rule above matches
  pipeline: "default_ingest_pipeline"
```

`pipelines:` rules support `pipeline`, `mappings` (`<lookup>: <pipeline>`), `default`, and `when:`. `pipeline` (singular) acts as the no-match fallback. The pipeline name **is always lowercased** by Filebeat.

## Common pitfalls

1. Choose ONE auth method (username/password OR api_key).
2. When ILM is enabled (default in newer versions), the `index` field is ignored. Set `setup.ilm.enabled: false` and configure `index` explicitly only if you do NOT want ILM.
3. Defining `indices:` disables ILM.
4. Use env vars (`${VAR}`) for secrets.
