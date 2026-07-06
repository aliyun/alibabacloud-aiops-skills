# confighttp — HTTP client/server common settings

> Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/config/confighttp/README.md
>
> This file is referenced indirectly from the elasticsearchexporter README ("HTTP Configuration Settings") and from the otlpreceiver README ("HTTP settings"). All HTTP-side knobs (compression, headers, timeouts, keep-alive, CORS, max body size) live here.

## HTTP Client (used by exporters, e.g. elasticsearchexporter)

### All client options

| Option | Description |
|---|---|
| `endpoint` | Target `address:port`. |
| `proxy_url` | HTTP proxy URL. |
| `tls` | Delegated to configtls. |
| `headers` | Map of name/value pairs added to outgoing requests. |
| `read_buffer_size` | Read buffer for `http.Transport`. |
| `write_buffer_size` | Write buffer for `http.Transport`. |
| `timeout` | Per-client request timeout. |
| `compression` | Outbound payload compression algorithm. |
| `compression_params` | Advanced compression options (e.g., `level`). |
| `max_idle_conns` | Idle (keep-alive) connection cap across hosts. |
| `max_idle_conns_per_host` | Idle conns per host. |
| `max_conns_per_host` | Total conns per host. |
| `idle_conn_timeout` | Idle keep-alive lifetime. |
| `auth` | configauth reference. |
| `disable_keep_alives` | Disable HTTP keep-alive. |
| `force_attempt_http2` | Always attempt HTTP/2. |
| `http2_read_idle_timeout` | Idle interval before HTTP/2 ping. |
| `http2_ping_timeout` | HTTP/2 ping response timeout. |
| `cookies` | `{ enabled: bool }`. |
| `middlewares` | Middleware extensions. |

### Header notes

- `Content-Length`, `Connection` are managed by the runtime; user-supplied values may be ignored.
- `Host` is normally derived from `endpoint`; setting `Host` in `headers` overrides it.

### Client compression

`compression` accepts:

- `gzip`
- `zstd`
- `snappy`
- `zlib`
- `deflate`
- `lz4`
- `none` (treated as uncompressed)
- `x-snappy-framed` (only when feature gate `confighttp.framedSnappy` is enabled)

Unknown values produce an error. The receiver side must support the chosen algorithm.

### Compression levels (`compression_params.level`)

| Algorithm | Valid level values |
|---|---|
| `gzip` | BestSpeed `1`, BestCompression `9`, DefaultCompression `-1` |
| `zlib` | BestSpeed `1`, BestCompression `9`, DefaultCompression `-1` |
| `deflate` | BestSpeed `1`, BestCompression `9`, DefaultCompression `-1` |
| `zstd` | SpeedFastest `1`, SpeedDefault `3`, SpeedBetterCompression `6`, SpeedBestCompression `11` |
| `snappy` | No levels supported. |
| `x-snappy-framed` | No levels supported (requires `confighttp.framedSnappy` gate). |
| `lz4` | No levels documented. |

### Client YAML example

```yaml
exporter:
  otlphttp:
    endpoint: otelcol2:55690
    auth:
      authenticator: some-authenticator-extension
    tls:
      ca_file: ca.pem
      cert_file: cert.pem
      key_file: key.pem
    headers:
      test1: "value1"
    compression: zstd
    compression_params:
      level: 6        # SpeedBetterCompression
    cookies:
      enabled: true
```

### Practical pairing with elasticsearchexporter

The ES exporter inherits these settings. Common configurations:

```yaml
exporters:
  elasticsearch:
    endpoints: [https://es:9200]
    api_key: ${env:ELASTIC_API_KEY}
    timeout: 90s              # ES exporter overrides default to 90s
    compression: gzip         # default already; explicit for clarity
    compression_params:
      level: 1                # BestSpeed; default for gzip in this exporter
    headers:
      X-Tenant-Id: tenant-a
    proxy_url: http://corp-proxy:3128
    max_idle_conns: 100
    idle_conn_timeout: 90s
```

To **disable** compression entirely:

```yaml
exporters:
  elasticsearch:
    endpoints: [https://es:9200]
    compression: none
```

To trade CPU for bandwidth (better compression):

```yaml
exporters:
  elasticsearch:
    endpoints: [https://es:9200]
    compression: zstd
    compression_params:
      level: 6
```

---

## HTTP Server (used by receivers, e.g. otlpreceiver/http, prometheus_http, etc.)

### All server options

| Option | Default | Description |
|---|---|---|
| `endpoint` | — | Listen address. |
| `transport` | `tcp` | Transport protocol. |
| `cors` | — | CORS settings; null/blank = disabled. |
| `max_request_body_size` | `20971520` (20 MiB) | Cap on request body bytes. |
| `include_metadata` | `false` | Forward client metadata downstream. |
| `response_headers` | — | Extra headers on every response. |
| `compression_algorithms` | `["", "gzip", "zstd", "zlib", "snappy", "deflate", "lz4"]` | Accepted inbound compression list. Empty string = uncompressed. |
| `read_timeout` | `0` (none) | Whole-request read deadline. |
| `read_header_timeout` | `1m` | Header read deadline (falls back to `read_timeout` if zero). |
| `write_timeout` | `30s` | Response write deadline. |
| `idle_timeout` | `1m` | Keep-alive idle deadline. |
| `keep_alives_enabled` | `true` | Toggle HTTP keep-alives. |
| `tls` | — | configtls. |
| `auth` | — | configauth + `request_params`. |
| `middlewares` | — | Middleware extensions. |

### CORS sub-options

- `allowed_origins`: supports wildcards like `https://*.example.com`. Avoid `["*"]` because responses include `Access-Control-Allow-Credentials: true`, which browsers reject with that origin. Use `["https://*", "http://*"]` to accept any origin.
- `allowed_headers`: defaults include the safelist + `X-Requested-With`. Use `["*"]` to allow all.
- `max_age`: seconds for `Access-Control-Max-Age`. Browsers default to 5s when unset.

### auth sub-options

- `authenticator`: name of the authenticator extension.
- `request_params`: query parameter names included in the auth context.

### Server YAML example

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
        include_metadata: true
        max_request_body_size: 20971520
        compression_algorithms: ["", "gzip", "zstd"]
        cors:
          allowed_origins: [https://*.example.com]
          allowed_headers: [Authorization]
          max_age: 7200
        auth:
          authenticator: bearertokenauth
          request_params: [token]
```

---

## Compression cheat sheet

- **Client** (exporter): pick one with `compression`, tune via `compression_params.level`. Use `compression: none` to disable.
- **Server** (receiver): advertise allow-list via `compression_algorithms`. Include `""` to keep accepting uncompressed payloads.
- **Feature gates**:
  - `confighttp.framedSnappy` → enables `x-snappy-framed` for clients.
  - `confighttp.snappyFramed` → enables `x-snappy-framed` for servers.
