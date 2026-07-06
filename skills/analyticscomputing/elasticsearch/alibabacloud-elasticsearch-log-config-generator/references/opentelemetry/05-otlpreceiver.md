# OpenTelemetry otlpreceiver

> Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/receiver/otlpreceiver/README.md

The OTLP receiver accepts data over gRPC or HTTP using the OTLP format.

## Configuration Options

### Protocol endpoints

- `protocols.grpc.endpoint` — default `localhost:4317`
- `protocols.http.endpoint` — default `localhost:4318`

A protocol is disabled by omitting it.

### HTTP signal URL paths (defaults)

- `traces_url_path` → `/v1/traces`
- `metrics_url_path` → `/v1/metrics`
- `logs_url_path` → `/v1/logs`
- `profiles_url_path` → `/v1/profiles`

### CORS (HTTP only)

- `cors.allowed_origins`
- `cors.allowed_headers`
- `cors.max_age`

### gRPC settings (from `configgrpc`)

Highlights:

- `max_recv_msg_size_mib`
- `max_concurrent_streams`
- `transport` (e.g., `tcp`)
- `keepalive.server_parameters.{max_connection_idle, max_connection_age, max_connection_age_grace, time, timeout}`

Full reference: `16-configgrpc.md`. HTTP-side knobs (CORS, max body size, response headers, compression algorithms accepted) come from `13-confighttp.md`.

### TLS / mTLS

Standard `configtls` options: `cert_file`, `key_file`, `client_ca_file`, `ca_file`, `insecure`, `insecure_skip_verify`. Full reference: `14-configtls.md`.

### Auth

- `auth.authenticator`: reference to an authenticator extension (oidc, basicauth, bearertokenauth, headerssetter, etc.). See `15-configauth.md`.
- `include_metadata`: forward request metadata to downstream components.

## Sample YAML — Logs over gRPC + HTTP

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        transport: tcp
        max_recv_msg_size_mib: 16
        max_concurrent_streams: 100
        include_metadata: true
        keepalive:
          server_parameters:
            max_connection_idle: 11s
            max_connection_age: 12s
            time: 30s
            timeout: 5s
        tls:
          cert_file: /etc/otel/server.crt
          key_file: /etc/otel/server.key
          client_ca_file: /etc/otel/ca.crt
      http:
        endpoint: 0.0.0.0:4318
        logs_url_path: /v1/logs
        include_metadata: true
        tls:
          cert_file: /etc/otel/server.crt
          key_file: /etc/otel/server.key
        cors:
          allowed_origins: [https://*.example.com]
          allowed_headers: [Authorization]
          max_age: 7200

service:
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [elasticsearch]
```

## Common pitfalls

1. The default endpoints bind to `localhost`. To accept remote traffic, set `0.0.0.0:4317` / `0.0.0.0:4318` (warn user about exposure).
2. To send logs via OTLP/HTTP+JSON, the payload must be OTLP-JSON, not arbitrary JSON.
3. To disable HTTP entirely, omit the `http:` block under `protocols:`.
