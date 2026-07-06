# configgrpc — gRPC client/server common settings

> Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/config/configgrpc/README.md
>
> Indirectly referenced by otlpreceiver (`protocols.grpc:`) and any gRPC-based exporter. ES exporter is HTTP-only, so this is mostly relevant for the OTLP receiver side of an OTel pipeline.

## Client config (exporters)

| Field | Description |
|---|---|
| `endpoint` | gRPC target (per gRPC naming spec). |
| `compression` | `gzip`, `snappy`, `zstd`, or `none`. |
| `balancer_name` | gRPC client load-balancing policy. |
| `tls` | TLS block (configtls). |
| `headers` | Per-RPC metadata pairs added to each call. |
| `keepalive.permit_without_stream` | Allow pings with no streams. |
| `keepalive.time` | Keepalive interval. |
| `keepalive.timeout` | Keepalive ping timeout. |
| `read_buffer_size` / `write_buffer_size` | gRPC buffer sizes. |
| `auth` | Authenticator extension reference (configauth). |
| `middlewares` | Middleware extensions. |

`balancer_name` default: `round_robin` (was `pick_first` before v0.103.0).

`per_rpc_auth` is now provided through extensions (e.g., bearertokenauthextension), not as a static `headers` entry.

### Client YAML

```yaml
exporters:
  otlp_grpc:
    endpoint: otelcol2:55690
    auth:
      authenticator: some-authenticator-extension
    tls:
      ca_file: ca.pem
      cert_file: cert.pem
      key_file: key.pem
    headers:
      test1: "value1"
      "test 2": "value 2"
```

## Server config (receivers)

| Field | Description |
|---|---|
| `endpoint` | Listen address. |
| `transport` | `tcp` (default) or other (via confignet). |
| `keepalive.enforcement_policy.min_time` | Min ping interval allowed from clients. |
| `keepalive.enforcement_policy.permit_without_stream` | Allow pings without active streams. |
| `keepalive.server_parameters.max_connection_age` | Cap connection lifetime. |
| `keepalive.server_parameters.max_connection_age_grace` | Grace period after max age. |
| `keepalive.server_parameters.max_connection_idle` | Max idle time. |
| `keepalive.server_parameters.time` | Server keepalive ping interval. |
| `keepalive.server_parameters.timeout` | Keepalive ping timeout. |
| `max_concurrent_streams` | gRPC concurrent stream cap. |
| `max_recv_msg_size_mib` | Max receive message size in MiB. |
| `read_buffer_size` / `write_buffer_size` | gRPC buffer sizes. |
| `tls` | TLS block (configtls). |
| `auth` | Authenticator extension reference. |
| `middlewares` | Middleware extensions. |

### Server YAML (otlpreceiver gRPC slice)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        max_recv_msg_size_mib: 16
        keepalive:
          server_parameters:
            time: 30s
            timeout: 5s
        tls:
          cert_file: server.crt
          key_file: server.key
        auth:
          authenticator: bearertokenauth
```

## Compression notes

`gzip`, `snappy`, `zstd`, or `none`:

- `gzip` — required by all OTLP servers; reasonable default with strong ratios on large payloads.
- `snappy` — fastest CPU/throughput; weaker ratios; can be negative on very small payloads.
- `zstd` — best ratios with throughput between gzip and snappy.
- `none` — default; lowest CPU.

Pick `gzip` when the network is the bottleneck, `snappy` when the CPU is, `none` when both are cheap.
