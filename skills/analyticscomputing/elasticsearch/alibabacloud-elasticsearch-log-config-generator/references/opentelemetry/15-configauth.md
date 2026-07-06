# configauth — auth extension wiring

> Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/config/configauth/README.md
>
> Both confighttp and configgrpc accept an `auth.authenticator` field that points to an extension. This module documents that wiring.

## Two flavors

- **Server authenticator** — validates incoming requests on a receiver.
- **Client authenticator** — adds credentials to outgoing requests from an exporter.

## How wiring works

1. Declare the auth extension in `extensions:` (with its own config).
2. Reference the extension's name from `auth.authenticator` inside the receiver or exporter.
3. Add the extension to `service.extensions: [...]`.

## Common extensions

**Server-side (receivers):**
- `basicauthextension`
- `bearertokenauthextension`
- `oidcauthextension`

**Client-side (exporters):**
- `asapauthextension`
- `basicauthextension`
- `bearertokenauthextension`
- `oauth2clientauthextension`
- `sigv4authextension`

## Sample YAML

```yaml
extensions:
  oidc:
    issuer_url: http://localhost:8080/auth/realms/opentelemetry
    audience: account

  oauth2client:
    client_id: someclientid
    client_secret: someclientsecret
    token_url: https://example.com/oauth2/default/v1/token
    scopes: ["api.metrics"]
    tls:
      insecure: true
      ca_file: /var/lib/mycert.pem
      cert_file: xxxxx
      key_file: xxxxx
    timeout: 2s

receivers:
  otlp/with_auth:
    protocols:
      grpc:
        endpoint: localhost:4318
        tls:
          cert_file: /tmp/certs/cert.pem
          key_file: /tmp/certs/cert-key.pem
        auth:
          authenticator: oidc      # server authenticator name

exporters:
  otlphttp/withauth:
    endpoint: http://localhost:9000
    auth:
      authenticator: oauth2client  # client authenticator name

service:
  extensions: [oidc, oauth2client]
  pipelines:
    logs:
      receivers: [otlp/with_auth]
      exporters: [otlphttp/withauth]
```

## Notes

- `auth` is independent of `tls`; both can coexist on the same receiver/exporter.
- Custom authenticators are extensions implementing `configauth.ServerAuthenticator` or `configauth.ClientAuthenticator`; ship them via the OpenTelemetry Collector Builder.
