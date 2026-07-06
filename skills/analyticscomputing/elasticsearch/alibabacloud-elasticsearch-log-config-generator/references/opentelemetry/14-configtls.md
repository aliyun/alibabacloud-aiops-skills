# configtls — TLS settings (referenced by confighttp & configgrpc)

> Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/config/configtls/README.md
>
> All `tls:` blocks in receivers and exporters use this schema, regardless of whether they are layered on HTTP (`confighttp`) or gRPC (`configgrpc`).

## Common fields (client & server)

| Field | Default | Description |
|---|---|---|
| `insecure` | `false` | Disables transport security entirely. Cannot be combined with `insecure_skip_verify`. |
| `insecure_skip_verify` | `false` | Skip server certificate chain verification. |
| `ca_file` | — | Path to CA cert. Client: validates server cert; server: validates client certs. Empty = system roots. |
| `ca_pem` | — | Inline equivalent of `ca_file`. |
| `cert_file` | — | TLS cert path. Required on servers; on clients only for mTLS. |
| `cert_pem` | — | Inline equivalent of `cert_file`. |
| `key_file` | — | TLS key path; must accompany `cert_file`. |
| `key_pem` | — | Inline equivalent of `key_file`. |
| `include_system_ca_certs_pool` | `false` | Load system CAs alongside the configured CA. |
| `min_version` | `"1.2"` | One of `"1.0"`, `"1.1"`, `"1.2"`, `"1.3"`. TLS 1.0/1.1 are deprecated. |
| `max_version` | `""` (i.e., TLS 1.3) | Same enum as `min_version`. |
| `cipher_suites` | `[]` | Explicit cipher suite list; blank = safe defaults. |
| `curve_preferences` | `[]` | Allowed: `X25519`, `P521`, `P256`, `P384`. |
| `reload_interval` | unset | Duration string for periodic cert reload. |
| `tpm` | unset | TPM block (TSS2 keys only). |

## Client-only

Used by exporters under `tls:`.

| Field | Description |
|---|---|
| `server_name_override` | Overrides `:authority` / virtual host (mostly for testing). |

## Server-only

Used by receivers under `tls:`.

| Field | Default | Description |
|---|---|---|
| `client_ca_file` | — | Verifies client certs (sets `RequireAndVerifyClientCert`). Required for mTLS. |
| `client_ca_file_reload` | `false` | Reload client CA file on change. |

## TPM (`tls.tpm`)

| Field | Default | Description |
|---|---|---|
| `enabled` | `false` | Load `tls.key_file` from a TPM. |
| `path` | `""` | TPM device or socket (`/dev/tpm0`, `/dev/tpmrm0`). Not on Windows. |
| `owner_auth` | `""` | TPM owner authorization. |
| `auth` | `""` | Authorization to authenticate to the TPM. |

## Client YAML examples

```yaml
exporters:
  otlp_grpc:
    endpoint: myserver.local:55690
    tls:
      insecure: false
      ca_file: server.crt
      cert_file: client.crt
      key_file: client.key
      min_version: "1.2"
  otlp/insecure:
    endpoint: myserver.local:55690
    tls:
      insecure: true
  otlp/secure_no_verify:
    endpoint: myserver.local:55690
    tls:
      insecure: false
      insecure_skip_verify: true
```

Cipher suites:

```yaml
cipher_suites:
  - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
  - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
  - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
```

## Server YAML examples (incl. mTLS)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: mysite.local:55690
        tls:
          cert_file: server.crt
          key_file: server.key
  otlp/mtls:
    protocols:
      grpc:
        endpoint: mysite.local:55690
        tls:
          client_ca_file: client.pem
          cert_file: server.crt
          key_file: server.key
  otlp/notls:
    protocols:
      grpc:
        endpoint: mysite.local:55690
```

## Practical pairing with elasticsearchexporter

```yaml
exporters:
  elasticsearch:
    endpoints: [https://es.example.com:9200]
    api_key: ${env:ELASTIC_API_KEY}
    tls:
      ca_file: /etc/pki/elastic-ca.pem
      min_version: "1.2"
      # cert_file / key_file only when ES requires mTLS
```

## mTLS recap

- Client (exporter): `cert_file` + `key_file` (presented identity) + `ca_file` (trust anchor).
- Server (receiver): `cert_file` + `key_file` (server identity) + `client_ca_file` (verifies client). Optionally `client_ca_file_reload: true`.
