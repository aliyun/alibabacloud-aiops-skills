# Filebeat — setup.kibana / logging / monitoring / http endpoint

> Sources:
> - https://www.elastic.co/docs/reference/beats/filebeat/setup-kibana-endpoint
> - https://www.elastic.co/docs/reference/beats/filebeat/configuration-logging
> - https://www.elastic.co/docs/reference/beats/filebeat/monitoring-internal-collection
> - https://www.elastic.co/docs/reference/beats/filebeat/http-endpoint
>
> These are the non-input/non-output top-level sections most often touched in real configs.

## setup.kibana

Used by `filebeat setup` to push dashboards / ILM templates to Kibana. Not needed if you provision artefacts out-of-band.

| Field | Default | Notes |
|---|---|---|
| `host` | `127.0.0.1:5601` | URL or `IP:PORT`. Port `5601` if omitted. |
| `protocol` | `http` | Or `https`. Overridden if scheme is in `host`. |
| `username` | falls back to ES output's `username` | Basic auth. |
| `password` | falls back to ES output's `password` | Basic auth. |
| `path` | — | URL prefix for reverse-proxy setups. |
| `space.id` | default space | Kibana space ID. |
| `headers` | — | Custom request headers. |
| `ssl.enabled` | `true` over HTTPS | Plus the standard `ssl.*` block from `07-ssl.md`. |

```yaml
setup.kibana:
  host: "https://kibana.example.com:5601"
  username: "${KIBANA_USER}"
  password: "${KIBANA_PASS}"
  space.id: "logs"
  ssl:
    certificate_authorities: ["/etc/ssl/ca.pem"]
```

## logging

Filebeat's own log output. The `logging.to_*` outputs are mutually exclusive.

| Field | Default | Notes |
|---|---|---|
| `level` | `info` | `debug` / `info` / `warning` / `error`. |
| `selectors` | — | Debug selector tags (e.g., `[harvester, input]`); `*` enables all (only meaningful at `level: debug`). |
| `to_stderr` | — | Equivalent to `-e`. |
| `to_syslog` | — | Not on Windows. |
| `to_eventlog` | — | Windows only. |
| `to_files` | — | Rotated files. |
| `metrics.enabled` | `true` | Periodic stats line in the log. |
| `metrics.period` | `30s` | How often to emit. |
| `metrics.namespaces` | `[stats]` | Stat groups to emit. |

`logging.files.*` (when `to_files: true`):

| Field | Default | Notes |
|---|---|---|
| `path` | logs path | Directory. |
| `name` | `filebeat` | File name stem. |
| `rotateeverybytes` | `10485760` (10 MB) | Size-based rotation. |
| `keepfiles` | `7` | Range 2–1024. |
| `permissions` | `0600` | Max permissive `0640`. Linux/macOS only. |
| `interval` | disabled | Time-based rotation, e.g. `24h`. |
| `rotateonstartup` | `true` | Rotate on boot. |
| `redirect_stderr` | `false` | Preview — sends Go runtime diagnostics to the log file. |

```yaml
logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  rotateeverybytes: 10485760
  keepfiles: 7
  permissions: 0640
  interval: 24h
logging.metrics.enabled: true
logging.metrics.period: 30s
```

> systemd note: Linux + systemd defaults Filebeat to `-e` (stderr to journald) and disables other outputs. Override via the unit file if you want file logging.

## monitoring (internal collection)

Ships Filebeat's own metrics to a monitoring cluster. Skip when using Metricbeat-based monitoring.

| Field | Notes |
|---|---|
| `monitoring.enabled` | Boolean toggle. |
| `monitoring.cluster_uuid` | UUID of the production cluster being monitored — needed when output and monitoring destinations differ. |
| `monitoring.elasticsearch.hosts` | Monitoring cluster endpoints. |
| `monitoring.elasticsearch.username` | Auth user (e.g., `beats_system`). Set to `""` for PKI. |
| `monitoring.elasticsearch.password` | — |
| `monitoring.elasticsearch.api_key` | `id:api_key`. Alternative to user/pass. |
| `monitoring.elasticsearch.ssl.{certificate_authorities,certificate,key}` | TLS / PKI. |

```yaml
monitoring:
  enabled: true
  elasticsearch:
    hosts: ["https://monitor-es:9200"]
    api_key: "${MONITORING_API_KEY}"
    ssl:
      certificate_authorities: ["/etc/ssl/ca.pem"]
```

When the production cluster (`output.elasticsearch.hosts`) is the same as the monitoring cluster, omit `hosts` + `cluster_uuid`.

## http (stats endpoint)

Local HTTP endpoint exposing runtime stats (`/stats`, `/dataset`, `/inputs/`). Technical preview.

| Field | Default | Notes |
|---|---|---|
| `http.enabled` | `false` | — |
| `http.host` | `localhost` | Hostname / IP / unix socket (`unix:///var/run/filebeat.sock`) / Windows named pipe (`npipe:///filebeat`). Stick to `localhost` per docs. |
| `http.port` | `5066` | — |
| `http.named_pipe.user` | current user | Windows only. |
| `http.named_pipe.security_descriptor` | RW for current user | Windows only — SDDL. |

```yaml
http.enabled: true
http.host: localhost
http.port: 5066
```

Query: `curl -XGET 'localhost:5066/stats?pretty'`.
