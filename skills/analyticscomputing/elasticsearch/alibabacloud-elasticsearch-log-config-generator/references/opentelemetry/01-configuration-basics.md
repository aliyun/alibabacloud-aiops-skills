# OpenTelemetry Collector Configuration Reference

> Source: https://opentelemetry.io/docs/collector/configuration/

## Overview

The OpenTelemetry Collector is configured via a YAML file (default location: `/etc/<otel-directory>/config.yaml`, where `<otel-directory>` is typically `otelcol` or `otelcol-contrib`).

You can specify configuration with the `--config` flag, which accepts a file path or a URI in the form `<scheme>:<opaque_data>`.

### Supported config providers (schemes)

- **file** — reads from a file (e.g., `file:path/to/config.yaml`)
- **env** — reads from an environment variable (e.g., `env:MY_CONFIG_IN_AN_ENVVAR`)
- **yaml** — reads from a YAML string, with `::` separating nested keys (e.g., `yaml:exporters::debug::verbosity: detailed`)
- **http** — reads from an HTTP URI
- **https** — reads from an HTTPS URI

Multiple `--config` flags can be passed; the Collector merges them into a single in-memory configuration. If the merged result is incomplete, the Collector returns an error (no defaults are inserted).

Validate a config file with: `otelcol validate --config=customconfig.yaml`

> Tip: Use double colons (`::`) for nested keys to avoid confusion with namespaces that contain dots.

---

## Configuration Structure

A Collector config consists of these top-level sections:

1. **receivers** — collect telemetry from sources (pull or push)
2. **processors** — transform/filter telemetry between receivers and exporters (optional but some recommended)
3. **exporters** — send telemetry to backends/destinations
4. **connectors** — act as both exporter (end of one pipeline) and receiver (start of another)
5. **extensions** — optional capabilities not directly handling telemetry (health checks, auth, etc.)
6. **service** — enables and wires together the above components

**Critical rule:** Defining a component under `receivers`, `processors`, `exporters`, `connectors`, or `extensions` does **not** enable it. A component is only enabled when referenced inside the `service` section.

### Component identifiers

Components use the format `type[/name]`, e.g., `otlp` or `otlp/2`. You can declare multiple instances of the same type as long as each identifier is unique. Pipelines also follow this format (e.g., `traces`, `traces/2`).

---

## The `service` Section

The `service` section has three subsections:

### `service.extensions`

A list of extension IDs to enable:

```yaml
service:
  extensions: [health_check, pprof, zpages]
```

### `service.pipelines`

Pipelines come in three types:

- `traces` — collect and process trace data
- `metrics` — collect and process metric data
- `logs` — collect and process log data

A pipeline lists `receivers`, `processors`, and `exporters`. Rules:

- Components must be declared in their respective top-level section before being referenced in a pipeline.
- A receiver, processor, or exporter can appear in more than one pipeline.
- When a processor is used in multiple pipelines, **each pipeline gets its own instance** of that processor.
- The order of processors in a pipeline determines the order of operations.
- Use `type[/name]` (e.g., `traces/2`) to define additional pipelines of a given type.

### `service.telemetry`

Configures the Collector's own observability. Two subsections — `logs` and `metrics`.

| Field | Default | Notes |
|---|---|---|
| `logs.level` | `INFO` | `DEBUG` / `INFO` / `WARN` / `ERROR`. Bump to `debug` to trace processor decisions (filter drops, OTTL evaluations). |
| `logs.encoding` | `console` | Or `json`. |
| `logs.processors` | — | Optional list (e.g., `batch`) wrapping an `otlp` exporter to ship the Collector's own logs to a backend. |
| `metrics.level` | `normal` | `none` / `basic` / `normal` / `detailed`. |
| `metrics.readers` | — | List of `pull` (with a `prometheus` exporter — `host`/`port`) or `periodic` (with an `otlp` exporter) readers. |
| `metrics.address` | — | **Ignored as of Collector v0.123.0** — use a `pull` reader with `prometheus` instead. |

```yaml
service:
  telemetry:
    logs:
      level: debug
      encoding: console
    metrics:
      level: normal
      readers:
        - pull:
            exporter:
              prometheus:
                host: '0.0.0.0'
                port: 8888
```

> Connectors are wired by listing the same connector ID under one pipeline's `exporters:` AND another pipeline's `receivers:` (see `34-routingconnector.md` for a worked example).

---

## Minimal Example Configuration

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  otlp_grpc:
    endpoint: otelcol:4317
    sending_queue:
      batch:

extensions:
  health_check:
    endpoint: 0.0.0.0:13133

service:
  extensions: [health_check]
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [otlp_grpc]
```

> Security note: Examples bind to `0.0.0.0` for convenience, but binding to `localhost` is preferred when all clients are local.

---

## Example with Named Instances and Multiple Pipelines

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
  otlp/2:
    protocols:
      grpc:
        endpoint: 0.0.0.0:55690

exporters:
  otlp_grpc:
    endpoint: otelcol:4317
  otlp_grpc/2:
    endpoint: otelcol2:4317

service:
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [otlp_grpc]
    logs/2:
      receivers: [otlp/2]
      exporters: [otlp_grpc/2]
```

---

## Environment Variables

- Use `${env:VAR_NAME}` to substitute env vars in the config.
- Defaults: `${env:DB_KEY:-mydefault}`
- Use `$$` to represent a literal `$`.

```yaml
processors:
  attributes/example:
    actions:
      - key: ${env:DB_KEY:-mydefault}
        action: ${env:OPERATION:-}
```

---

## TLS / mTLS Configuration

### Common TLS settings

| Setting | Description |
|---|---|
| `ca_file` | Path to the CA certificate to verify the peer certificate |
| `cert_file` | Path to the TLS certificate |
| `key_file` | Path to the TLS private key |
| `client_ca_file` | Path to the CA certificate to verify client certificates |
| `insecure` | Disable TLS verification (not recommended for production) |
| `insecure_skip_verify` | Skip server certificate verification (not recommended) |
| `min_version` | Minimum TLS version (e.g., `1.2` or `1.3`) |
| `max_version` | Maximum TLS version |
| `reload_interval` | Duration after which the certificate is reloaded |

### Exporter TLS (client-side)

```yaml
exporters:
  otlp_grpc:
    endpoint: otelcol2:4317
    tls:
      ca_file: /path/to/ca.pem
      cert_file: /path/to/cert.pem
      key_file: /path/to/cert-key.pem
```

---

## Inspection Commands

- List components in a distribution: `otelcol components`
- Print resolved configuration: `otelcol print-config --config=file:examples/local/otel-config.yaml --feature-gates=otelcol.printInitialConfig`
- Show sensitive fields: add `--mode=unredacted`
- JSON output: add `--format=json`

---

## Referenced URLs

- Receiver README: https://github.com/open-telemetry/opentelemetry-collector/blob/main/receiver/README.md
- Processor README: https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/README.md
- Exporter README: https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/README.md
- Connector README: https://github.com/open-telemetry/opentelemetry-collector/blob/main/connector/README.md
- Extension README: https://github.com/open-telemetry/opentelemetry-collector/blob/main/extension/README.md
- Contrib processors list: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor
- Core processors list: https://github.com/open-telemetry/opentelemetry-collector/tree/main/processor
- TLS configuration reference (configtls): https://github.com/open-telemetry/opentelemetry-collector/blob/main/config/configtls/README.md
