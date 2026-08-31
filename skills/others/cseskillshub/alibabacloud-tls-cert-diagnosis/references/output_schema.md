# Output JSON Schema

The helper script `scripts/check_tls.py` outputs JSON matching this schema.

```json
{
  "type": "object",
  "required": ["domain", "port", "ok", "dns_ok", "port_ok", "tls_ok", "summary"],
  "properties": {
    "domain": { "type": "string", "description": "Target domain or IP" },
    "port": { "type": "integer", "description": "Target port" },
    "ok": { "type": "boolean", "description": "Overall check passed" },
    "dns_ok": { "type": "boolean", "description": "DNS resolution succeeded" },
    "port_ok": { "type": "boolean", "description": "At least one resolved IP is reachable" },
    "tls_ok": { "type": "boolean", "description": "Certificate trusted, hostname matches, not expired" },
    "summary": { "type": "string", "description": "Human-readable result summary" },
    "dns_result": {
      "type": "object",
      "properties": {
        "success": { "type": "boolean" },
        "a_records": { "type": "array", "items": { "type": "string" } },
        "aaaa_records": { "type": "array", "items": { "type": "string" } },
        "resolved_ips": { "type": "array", "items": { "type": "string" } },
        "error": { "type": ["string", "null"] }
      }
    },
    "port_check": {
      "type": "object",
      "properties": {
        "tested": { "type": "boolean" },
        "success": { "type": "boolean" },
        "results": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "ip": { "type": "string" },
              "port": { "type": "integer" },
              "reachable": { "type": "boolean" },
              "latency_ms": { "type": ["number", "null"] },
              "error": { "type": ["string", "null"] }
            }
          }
        }
      }
    },
    "tls_result": {
      "type": "object",
      "properties": {
        "tested": { "type": "boolean" },
        "checked_ip": { "type": "string" },
        "handshake_success": { "type": "boolean" },
        "certificate_trusted": { "type": ["boolean", "null"] },
        "hostname_matches_certificate": { "type": ["boolean", "null"] },
        "certificate_expired": { "type": ["boolean", "null"] },
        "certificate_not_yet_valid": { "type": ["boolean", "null"] },
        "chain_complete": { "type": ["boolean", "null"] },
        "valid_from": { "type": ["string", "null"], "format": "date-time" },
        "valid_to": { "type": ["string", "null"], "format": "date-time" },
        "days_until_expiry": { "type": ["integer", "null"] },
        "subject": { "type": ["string", "null"] },
        "issuer": { "type": ["string", "null"] },
        "common_names": { "type": "array", "items": { "type": "string" } },
        "san_dns_names": { "type": "array", "items": { "type": "string" } },
        "serial_number": { "type": ["string", "null"] },
        "sha256_fingerprint": { "type": ["string", "null"] },
        "trust_error": { "type": ["string", "null"] },
        "error": { "type": ["string", "null"] }
      }
    }
  }
}
```
