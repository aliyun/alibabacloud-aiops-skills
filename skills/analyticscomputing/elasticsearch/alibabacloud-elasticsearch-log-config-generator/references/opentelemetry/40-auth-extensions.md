# Auth extensions — basicauth / bearertokenauth / headerssetter

> Companion to `15-configauth.md`. Sources:
> - https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/extension/basicauthextension/README.md
> - https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/extension/bearertokenauthextension/README.md
> - https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/extension/headerssetterextension/README.md
>
> Each extension exposes a single name (`basicauth`, `bearertokenauth`, `headers_setter`) and is wired via `auth.authenticator: <name>` on a receiver (server-side) or exporter (client-side). Always include the instance under `service.extensions:` or it won't load.

## basicauth

| Field | Notes |
|---|---|
| `htpasswd.file` | Path to a server-side htpasswd file. |
| `htpasswd.inline` | Inline htpasswd content; **takes precedence over `htpasswd.file`** when both set. |
| `client_auth.username` | Static username for client-side use. |
| `client_auth.username_file` | File holding the username (watched, supersedes `username`). |
| `client_auth.password` | Static password. |
| `client_auth.password_file` | File holding the password (watched, supersedes `password`). |

Server vs client mode are mutually exclusive on a single instance — define separate named instances (`basicauth/server`, `basicauth/client`) for both.

```yaml
extensions:
  basicauth/server:
    htpasswd:
      inline: |
        ${env:BASIC_AUTH_USERNAME}:${env:BASIC_AUTH_PASSWORD}
  basicauth/client:
    client_auth:
      username: ${env:UPSTREAM_USER}
      password: ${env:UPSTREAM_PASS}

receivers:
  otlp:
    protocols:
      http:
        auth:
          authenticator: basicauth/server

exporters:
  otlphttp:
    endpoint: https://upstream.example.com
    auth:
      authenticator: basicauth/client

service:
  extensions: [basicauth/server, basicauth/client]
```

> The Elasticsearch exporter uses native `user` / `password` / `api_key` fields and does **not** need this extension — only reach for `basicauth` when an upstream OTLP/HTTP destination requires Basic.

## bearertokenauth

| Field | Default | Notes |
|---|---|---|
| `header` | `Authorization` | Outgoing header name. |
| `scheme` | `Bearer` | Prefix prepended to the token. |
| `token` | — | Inline token; mutually exclusive with `tokens` and `filename`. |
| `tokens` | — | Multiple acceptable tokens (any matches). |
| `filename` | — | Path to a token file; first whitespace-delimited string per line is the token. **If both `token` and `filename` set, `token` is ignored.** |

Either `token` or `filename` is required. **TLS must be enabled on the exporter** ("requires transport layer security enabled on the exporter").

```yaml
extensions:
  bearertokenauth:
    scheme: Bearer
    filename: /etc/otel/upstream.token

exporters:
  otlp:
    endpoint: upstream.example.com:4317
    auth:
      authenticator: bearertokenauth
    tls:
      ca_file: /etc/ssl/ca.pem

service:
  extensions: [bearertokenauth]
```

## headers_setter

| Field | Notes |
|---|---|
| `additional_auth` | Optional ID of another auth extension to chain (applied first). |
| `headers[]` | List of header rules (below). |
| `headers[].key` | Header name. |
| `headers[].action` | `insert` (only if missing), `update` (only if exists), `upsert` (default), `delete`. |
| `headers[].value` | Static value. |
| `headers[].value_file` | Path to a file (watched — handy for rotated secrets). |
| `headers[].from_context` | Pull from request metadata key. |
| `headers[].from_attribute` | Pull from request auth data (e.g., `subject`). |
| `headers[].default_value` | Fallback when `from_context` / `from_attribute` is empty. |

`value`, `value_file`, `(from_context, default_value)`, `(from_attribute, default_value)` are mutually exclusive per header.

For `from_context` to work:
- Receivers must set `include_metadata: true`.
- If using `batch`, list the metadata key under `metadata_keys:` so it survives batching.

```yaml
extensions:
  headers_setter:
    headers:
      - action: insert
        key: X-Scope-OrgID
        from_context: tenant_id
        default_value: default-org
      - action: upsert
        key: X-Custom-Header
        value: my-static-value

receivers:
  otlp:
    protocols:
      http:
        include_metadata: true

processors:
  batch:
    metadata_keys: [tenant_id]

exporters:
  otlphttp:
    endpoint: https://api.example.com
    auth:
      authenticator: headers_setter

service:
  extensions: [headers_setter]
```

> `headers_setter` is alpha; available in `contrib` and `k8s` distributions.
