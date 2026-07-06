# Filebeat http_endpoint Input

> Source: https://www.elastic.co/docs/reference/beats/filebeat/filebeat-input-http_endpoint

Starts an HTTP server that accepts POST/PUT/PATCH requests with JSON bodies (object or array). Useful for webhooks. Gzip request bodies are supported via `Content-Encoding: gzip`.

## Listener Options

| Option | Default |
|---|---|
| `listen_address` | `127.0.0.1` |
| `listen_port` | `8000` |
| `url` | `/` |
| `method` | `POST` (also `PUT`/`PATCH` treated as POST) |

## Body / Document Shaping

| Option | Description |
|---|---|
| `content_type` | Expected Content-Type. Default `application/json`. Empty disables check. |
| `prefix` | Doc prefix where payload is mapped. `.` maps to root. |
| `program` | CEL program (`obj`) for transforming the body. |
| `max_body_bytes` | Max request body size. |
| `preserve_original_event` | Store request JSON in `event.original`. |
| `include_headers` | List of headers to copy into the document. |

## Authentication

### Basic Auth
- `basic_auth: true`
- `username`, `password`

### Shared-secret header
- `secret.header`, `secret.value`

### HMAC signature
- `hmac.header` (e.g., `X-Hub-Signature-256`)
- `hmac.key`
- `hmac.type` (`sha256` or `sha1`)
- `hmac.prefix` (e.g., `sha256=`)

### CRC
- `crc.provider`, `crc.secret`

## TLS

```yaml
ssl.enabled: true
ssl.certificate: /etc/ssl/cert.pem
ssl.key: /etc/ssl/key.pem
ssl.certificate_authority: /etc/ssl/ca.pem
ssl.verification_mode: full
```

## Response Options

- `response_code`, `response_body`
- `options_headers`, `options_response_code` (default `200`)

End-to-end ACK: clients can pass `?wait_for_completion_timeout=1m`.

## Sample — webhook receiver

```yaml
filebeat.inputs:
  - type: http_endpoint
    enabled: true
    listen_address: 0.0.0.0
    listen_port: 8080
    url: /webhook
    method: POST
    content_type: application/json
    prefix: json
    response_code: 200
    response_body: '{"message": "success"}'
    secret.header: X-Webhook-Token
    secret.value: ${WEBHOOK_SECRET}
    include_headers: [X-Request-Id]
    tags: [webhook]
```

## Sample — HMAC-validated (GitHub-style)

```yaml
filebeat.inputs:
  - type: http_endpoint
    enabled: true
    listen_port: 8080
    url: /github
    hmac.header: X-Hub-Signature-256
    hmac.key: ${GITHUB_WEBHOOK_SECRET}
    hmac.type: sha256
    hmac.prefix: sha256=
```
