# Filebeat SSL / TLS Configuration

> Source: https://www.elastic.co/docs/reference/beats/filebeat/configuration-ssl

## Options

| Option | Default | Notes |
|---|---|---|
| `enabled` | `true` | Disable with `false` or omit `ssl` section. |
| `supported_protocols` | `[TLSv1.2, TLSv1.3]` | Allowed TLS versions. |
| `cipher_suites` | Go defaults | TLS 1.3 suites always added unless TLS 1.3 disabled. |
| `curve_types` | system | `P-256`, `P-384`, `P-521`, `X25519`. |
| `certificate_authorities` | — | List of trusted CA paths or inline PEM. |
| `certificate` / `key` | — | Required when presenting a cert. |
| `key_passphrase` | — | For encrypted private keys. |
| `verification_mode` | `full` | `full`, `strict`, `certificate`, `none`. |
| `ca_sha256` | — | Base64 SHA-256 cert pin. |
| `ca_trusted_fingerprint` | — | Hex SHA-256 of CA (client only). |
| `renegotiation` | `never` | `never`, `once`, `freely` (server). |
| `client_authentication` | `required` if CAs set, else `none` | `none`, `optional`, `required`. |
| `restart_on_cert_change.enabled` | `false` | Not on Windows. |

## Verification modes

- **full** — CA chain + hostname/IP. **Recommended for production.**
- **strict** — Like full, but rejects empty SAN.
- **certificate** — CA chain only.
- **none** — No verification (strongly discouraged in production).

## Client (output) sample

```yaml
output.elasticsearch:
  hosts: ["https://es:9200"]
  ssl:
    enabled: true
    certificate_authorities: ["/etc/pki/ca.pem"]
    certificate: "/etc/pki/cert.pem"
    key: "/etc/pki/cert.key"
    verification_mode: full
    supported_protocols: [TLSv1.2, TLSv1.3]
```

## Server (input) sample

```yaml
filebeat.inputs:
  - type: tcp
    host: "0.0.0.0:9000"
    ssl:
      enabled: true
      certificate_authorities: ["/etc/server/ca.pem"]
      certificate: "/etc/server/cert.pem"
      key: "/etc/server/cert.key"
      client_authentication: required
      verification_mode: full
```
