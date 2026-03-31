# Nginx Ingress Annotation → APIG Compatibility

## Table of Contents
- [Classification Rule](#classification-rule)
- [1. Compatible Annotations (50)](#1-compatible-annotations-50)
- [2. Ignorable Annotations (16)](#2-ignorable-annotations-16)
- [3. Unsupported Annotations (51)](#3-unsupported-annotations-51)
- [Migration Processing Summary](#migration-processing-summary)
- [Quick Reference: Annotation → Category Lookup](#quick-reference-annotation--category-lookup)
- [Analysis Script](#analysis-script)

> Authority source: `annotations/compatible_annotations.go` (`CompatibleAnnotations` / `IgnoreAnnotations`)
> Cross-referenced with: [Nginx Ingress Annotations](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#annotations) and [APIG Supported Annotations](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/annotations-supported-by-higress-ingress-gateways)

## Classification Rule

Every `nginx.ingress.kubernetes.io/*` annotation falls into exactly one of three categories:

| Category | Source | Count | Migration Action |
|----------|--------|-------|-----------------|
| Compatible | `CompatibleAnnotations` | 50 | **Keep** annotation in new Ingress |
| Ignorable | `IgnoreAnnotations` | 16 | **Strip** annotation (no replacement needed) |
| Unsupported | Not in either set | 51 | **Strip** annotation → **replace** with `higress.io/wasmplugin` annotation |

---

## 1. Compatible Annotations (50)

Source: `CompatibleAnnotations` set in `annotations/compatible_annotations.go`

These annotations are natively supported by APIG. **Keep them as-is** in the migrated Ingress.

### Canary / Grayscale (7)

| # | Annotation | Notes |
|---|-----------|-------|
| 1 | `canary` | Enable/disable canary |
| 2 | `canary-by-header` | Traffic split by header key |
| 3 | `canary-by-header-value` | Traffic split by header value (exact) |
| 4 | `canary-by-header-pattern` | Traffic split by header value (regex) |
| 5 | `canary-by-cookie` | Traffic split by cookie key |
| 6 | `canary-weight` | Weight-based traffic split |
| 7 | `canary-weight-total` | Weight total |

### CORS (7)

| # | Annotation | Notes |
|---|-----------|-------|
| 8 | `enable-cors` | Enable/disable CORS |
| 9 | `cors-allow-origin` | Allowed origins |
| 10 | `cors-allow-methods` | Allowed methods |
| 11 | `cors-allow-headers` | Allowed headers |
| 12 | `cors-expose-headers` | Exposed headers |
| 13 | `cors-allow-credentials` | Allow credentials |
| 14 | `cors-max-age` | Preflight cache duration |

### Redirect (6)

| # | Annotation | Notes |
|---|-----------|-------|
| 15 | `app-root` | Redirect `/` to specified path |
| 16 | `temporal-redirect` | Temporary redirect (302) |
| 17 | `permanent-redirect` | Permanent redirect (301) |
| 18 | `permanent-redirect-code` | Custom permanent redirect code |
| 19 | `ssl-redirect` | HTTP → HTTPS |
| 20 | `force-ssl-redirect` | Force HTTP → HTTPS |

### Rewrite (3)

| # | Annotation | Notes |
|---|-----------|-------|
| 21 | `rewrite-target` | Path rewrite, supports group capture |
| 22 | `use-regex` | Enable regex path matching (RE2) |
| 23 | `upstream-vhost` | Override Host header to upstream |

### Retry (3)

| # | Annotation | Notes |
|---|-----------|-------|
| 24 | `proxy-next-upstream-tries` | Max retry attempts (default: 3) |
| 25 | `proxy-next-upstream-timeout` | Retry timeout in seconds |
| 26 | `proxy-next-upstream` | Retry conditions |

### Fallback (2)

| # | Annotation | Notes |
|---|-----------|-------|
| 27 | `default-backend` | Fallback service when primary has no endpoints |
| 28 | `custom-http-errors` | Forward to default-backend on specified HTTP codes |

### Downstream TLS (2)

| # | Annotation | Notes |
|---|-----------|-------|
| 29 | `auth-tls-secret` | CA cert for client mTLS (format: `{domain-cert-secret}-cacert`) |
| 30 | `ssl-cipher` | TLS cipher suites. ⚠️ Nginx uses `ssl-ciphers` (with 's'); APIG uses `ssl-cipher` (without 's') |

### Upstream TLS (5)

| # | Annotation | Notes |
|---|-----------|-------|
| 31 | `backend-protocol` | HTTP/HTTP2/HTTPS/gRPC/gRPCS (⚠️ no AJP/FCGI) |
| 32 | `proxy-ssl-secret` | Client certificate for upstream mTLS |
| 33 | `proxy-ssl-verify` | Enable/disable upstream cert verification |
| 34 | `proxy-ssl-name` | SNI for upstream TLS |
| 35 | `proxy-ssl-server-name` | Enable/disable SNI |

### Load Balancing & Session Affinity (9)

| # | Annotation | Notes |
|---|-----------|-------|
| 36 | `load-balance` | round_robin/least_conn/random (⚠️ no EWMA). If the original Ingress uses `ewma`, change to `round_robin` or `least_conn` in the migrated copy |
| 37 | `upstream-hash-by` | Consistent hash key (⚠️ no variable combinations) |
| 38 | `affinity` | Affinity type (cookie only) |
| 39 | `affinity-mode` | ⚠️ Balanced only (persistent not supported) |
| 40 | `affinity-canary-behavior` | sticky/legacy for canary affinity |
| 41 | `session-cookie-name` | Cookie name as hash key |
| 42 | `session-cookie-path` | Cookie path (default: /) |
| 43 | `session-cookie-max-age` | Cookie max age in seconds |
| 44 | `session-cookie-expires` | Cookie expiry in seconds |

### IP Access Control (1)

| # | Annotation | Notes |
|---|-----------|-------|
| 45 | `whitelist-source-range` | IP whitelist (IP/CIDR) |

### Authentication (4)

| # | Annotation | Notes |
|---|-----------|-------|
| 46 | `auth-type` | ⚠️ Basic only (digest not supported) |
| 47 | `auth-realm` | Protection realm |
| 48 | `auth-secret` | Secret name (namespace/name format) |
| 49 | `auth-secret-type` | auth-file or auth-map |

### Domain Alias (1)

| # | Annotation | Notes |
|---|-----------|-------|
| 50 | `server-alias` | ⚠️ Exact/wildcard only (gateway ≥1.2.30) |

---

## 2. Ignorable Annotations (16)

Source: `IgnoreAnnotations` set in `annotations/compatible_annotations.go`

These annotations have no meaningful effect in Envoy-based APIG. During migration, **strip** them from the new Ingress — no replacement needed.

| # | Annotation | Why ignored |
|---|-----------|------------|
| 1 | `client-body-buffer-size` | Envoy has own buffer management |
| 2 | `proxy-buffering` | Envoy has own buffer management |
| 3 | `proxy-buffers-number` | Envoy has own buffer management |
| 4 | `proxy-buffer-size` | Envoy has own buffer management |
| 5 | `proxy-max-temp-file-size` | Envoy has own buffer management |
| 6 | `proxy-read-timeout` | Envoy uses unified route timeout (`higress.io/timeout`) |
| 7 | `proxy-send-timeout` | Same as above |
| 8 | `proxy-connect-timeout` | Same as above |
| 9 | `proxy-http-version` | Envoy auto-manages upstream HTTP version |
| 10 | `ssl-prefer-server-ciphers` | Envoy has own cipher preference |
| 11 | `proxy-ssl-protocols` | Envoy has own TLS protocol management |
| 12 | `preserve-trailing-slash` | Envoy preserves trailing slashes by default |
| 13 | `http2-push-preload` | HTTP/2 Push deprecated by major browsers |
| 14 | `proxy-ssl-ciphers` | Envoy has own upstream cipher management |
| 15 | `enable-rewrite-log` | Nginx-specific rewrite debug logging |
| 16 | `proxy-body-size` | APIG uses chunked streaming; no preset body size limit |

---

## 3. Unsupported Annotations (51)

These annotations exist in [Nginx Ingress](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/) but are **NOT** in `CompatibleAnnotations` or `IgnoreAnnotations`. During migration, **strip** the unsupported annotation from the new Ingress, then **add a `higress.io/wasmplugin` annotation** to the same Ingress to replicate the logic via a WasmPlugin (built-in or custom). The Ingress itself is always migrated.

### Snippets (5)

These inject raw Nginx/Lua/ModSecurity code and require full WasmPlugin conversion:

| # | Annotation | Nginx Functionality | WasmPlugin Approach |
|---|-----------|-------------------|-------------------|
| 1 | `configuration-snippet` | Location-level Nginx config injection | Parse directives → implement equivalent logic in Go WASM |
| 2 | `server-snippet` | Server-level Nginx config injection | Same as above |
| 3 | `stream-snippet` | TCP/UDP stream config | Envoy TCP filter via WASM if applicable |
| 4 | `modsecurity-snippet` | Custom ModSecurity rules | Use built-in `waf` plugin or custom WAF WASM |
| 5 | `auth-snippet` | Custom auth config block | Implement auth logic in WASM |

### External Authentication (10)

These implement external auth (subrequest-based) — requires a single WasmPlugin:

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 6 | `auth-url` | URL for external auth service |
| 7 | `auth-cache-key` | Cache key for auth responses |
| 8 | `auth-cache-duration` | Cache TTL for auth responses |
| 9 | `auth-keepalive` | Max keepalive connections to auth service |
| 10 | `auth-keepalive-share-vars` | Share Nginx vars with auth request |
| 11 | `auth-keepalive-requests` | Max requests per keepalive connection |
| 12 | `auth-keepalive-timeout` | Keepalive timeout to auth service |
| 13 | `auth-proxy-set-headers` | ConfigMap of headers to send to auth service |
| 14 | `enable-global-auth` | Toggle global external auth |

> **WasmPlugin approach**: Implement HTTP callout to external auth service using `proxy_http_call` in proxy-wasm-go SDK.

### Client Certificate / mTLS Extended (5)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 15 | `auth-tls-verify-depth` | Client cert chain verification depth |
| 16 | `auth-tls-verify-client` | Client cert verification mode (on/off/optional) |
| 17 | `auth-tls-error-page` | Redirect URL on cert auth failure |
| 18 | `auth-tls-pass-certificate-to-upstream` | Pass client cert to upstream via header |
| 19 | `auth-tls-match-cn` | Match CN of client cert (regex) |

> **WasmPlugin approach**: Read client cert from connection properties, validate CN, set headers.

### Rate Limiting (2)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 20 | `limit-connections` | Max concurrent connections per IP |
| 21 | `limit-rps` | Max requests per second per IP |

> **WasmPlugin approach**: Use built-in `key-rate-limit` plugin, or implement custom counter logic in WASM.

### ModSecurity / WAF (3)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 22 | `enable-modsecurity` | Enable ModSecurity WAF |
| 23 | `enable-owasp-core-rules` | Enable OWASP CRS ruleset |
| 24 | `modsecurity-transaction-id` | Set ModSecurity transaction ID |

> **WasmPlugin approach**: Use built-in `waf` plugin (`oci://apiginner-registry-vpc.<REGION>.cr.aliyuncs.com/platform_wasm/waf:1.0.0` — replace `<REGION>` with cluster region).

### Traffic Mirroring (3)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 25 | `mirror-target` | Mirror traffic to specified URI |
| 26 | `mirror-request-body` | Whether to include body in mirrored request |
| 27 | `mirror-host` | Override Host header for mirrored request |

> **WasmPlugin approach**: Use Higress annotation `higress.io/mirror-target-service` (mirrors to K8s Service instead of URI), or implement custom mirror logic in WASM.

### Custom Headers (1)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 28 | `custom-headers` | Add response headers via ConfigMap reference |

> **WasmPlugin approach**: Generate a custom WasmPlugin to add/modify response headers, or use Higress annotations `higress.io/response-header-control-add` if available.

### Proxy Settings (6)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 29 | `proxy-cookie-domain` | Rewrite Set-Cookie domain attribute |
| 30 | `proxy-cookie-path` | Rewrite Set-Cookie path attribute |
| 31 | `proxy-request-buffering` | Enable/disable request body buffering |

> Envoy streams request bodies by default (equivalent to `proxy_request_buffering off`). This annotation can usually be safely dropped. If the original value was `on` and the backend requires buffered requests, this may need investigation.
| 32 | `proxy-redirect-from` | Rewrite Location/Refresh header (source) |
| 33 | `proxy-redirect-to` | Rewrite Location/Refresh header (target) |
| 34 | `proxy-ssl-verify-depth` | Upstream cert chain verification depth |

> **WasmPlugin approach**: For cookie/redirect rewriting, implement header manipulation in WASM using `on_http_response_headers`.

### Proxy Buffer Extended (1)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 35 | `proxy-busy-buffers-size` | Limit busy buffer size during response streaming |

> Not applicable in Envoy architecture. Can be safely removed in most cases.

### Session Cookie Extended (5)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 36 | `session-cookie-change-on-failure` | Regenerate cookie on upstream failure |
| 37 | `session-cookie-conditional-samesite-none` | Browser-compat SameSite=None handling |
| 38 | `session-cookie-domain` | Set cookie Domain attribute |
| 39 | `session-cookie-samesite` | Set cookie SameSite attribute |
| 40 | `session-cookie-secure` | Set cookie Secure flag |

> **WasmPlugin approach**: Implement cookie attribute manipulation in WASM using `on_http_response_headers`.

### TLS / SSL (2)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 41 | `ssl-ciphers` | Downstream cipher suites (⚠️ APIG uses `ssl-cipher` without 's') |
| 42 | `ssl-passthrough` | TLS passthrough to backend (layer 4) |

> **Note**: For `ssl-ciphers`, the compatible annotation is `ssl-cipher` (without 's'). Migration should rename it. For `ssl-passthrough`, Envoy does not natively support layer-4 TLS passthrough via Ingress.

### Redirect Extended (2)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 43 | `from-to-www-redirect` | Redirect between www and non-www |
| 44 | `temporal-redirect-code` | Custom temporal redirect status code |

> **WasmPlugin approach**: Implement redirect logic checking Host header in WASM.

### IP Access Control (1)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 45 | `denylist-source-range` | IP blacklist (CIDR) |

> **Note**: APIG officially supports this via `higress.io/blacklist-source-range`. Migration should use the Higress annotation.

### Observability (3)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 46 | `enable-access-log` | Enable/disable access logging per Ingress |
| 47 | `enable-opentelemetry` | Enable/disable OpenTelemetry tracing |
| 48 | `opentelemetry-trust-incoming-span` | Trust incoming trace spans |

> Envoy has its own observability stack. These are typically configured at gateway level, not per-Ingress. `enable-access-log` can be safely dropped — configure access logging in the APIG console instead.

### Miscellaneous (3)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| 49 | `satisfy` | Auth combination logic (any/all) |
| 50 | `service-upstream` | Route to ClusterIP instead of Pod IPs |
| 51 | `connection-proxy-header` | Override Connection header (e.g., keep-alive) |

> **WasmPlugin approach**: `satisfy` can be implemented as multi-auth logic in WASM. `connection-proxy-header` is safe to drop as Envoy manages connection headers.
>
> **⚠️ `service-upstream` is safe to drop**: Envoy routes via Service ClusterIP by default (equivalent to `service-upstream: "true"`), so this annotation can be safely removed regardless of whether its value is `"true"` or `"false"` — no WasmPlugin replacement is needed. During Step 3 analysis, if an Ingress's only unsupported annotation is `service-upstream`, it does not actually need a WasmPlugin and should be classified as "cleaned" (strip the annotation only).

### Additional: `x-forwarded-prefix` (documented in nginx but not in annotation table)

| # | Annotation | Nginx Functionality |
|---|-----------|-------------------|
| — | `x-forwarded-prefix` | Add X-Forwarded-Prefix header |

> Envoy automatically handles X-Forwarded headers. Typically no replacement needed.

---

## Migration Processing Summary

When the AI agent processes each Ingress:

1. **Compatible (50)** → **Preserve** in the new `apig` Ingress copy
2. **Ignorable (16)** → **Strip** annotation from new Ingress — no replacement needed
3. **Unsupported (51)** → **Strip** annotation from new Ingress → develop/select WasmPlugin → **add `higress.io/wasmplugin` annotation** to the same Ingress

## Quick Reference: Annotation → Category Lookup

All annotations use prefix `nginx.ingress.kubernetes.io/`. Sorted alphabetically:

| Annotation | Category |
|-----------|----------|
| `affinity` | ✅ Compatible |
| `affinity-canary-behavior` | ✅ Compatible |
| `affinity-mode` | ✅ Compatible |
| `app-root` | ✅ Compatible |
| `auth-cache-duration` | ❌ Unsupported |
| `auth-cache-key` | ❌ Unsupported |
| `auth-keepalive` | ❌ Unsupported |
| `auth-keepalive-requests` | ❌ Unsupported |
| `auth-keepalive-share-vars` | ❌ Unsupported |
| `auth-keepalive-timeout` | ❌ Unsupported |
| `auth-proxy-set-headers` | ❌ Unsupported |
| `auth-realm` | ✅ Compatible |
| `auth-secret` | ✅ Compatible |
| `auth-secret-type` | ✅ Compatible |
| `auth-snippet` | ❌ Unsupported |
| `auth-tls-error-page` | ❌ Unsupported |
| `auth-tls-match-cn` | ❌ Unsupported |
| `auth-tls-pass-certificate-to-upstream` | ❌ Unsupported |
| `auth-tls-secret` | ✅ Compatible |
| `auth-tls-verify-client` | ❌ Unsupported |
| `auth-tls-verify-depth` | ❌ Unsupported |
| `auth-type` | ✅ Compatible |
| `auth-url` | ❌ Unsupported |
| `backend-protocol` | ✅ Compatible |
| `canary` | ✅ Compatible |
| `canary-by-cookie` | ✅ Compatible |
| `canary-by-header` | ✅ Compatible |
| `canary-by-header-pattern` | ✅ Compatible |
| `canary-by-header-value` | ✅ Compatible |
| `canary-weight` | ✅ Compatible |
| `canary-weight-total` | ✅ Compatible |
| `client-body-buffer-size` | ⚪ Ignorable |
| `configuration-snippet` | ❌ Unsupported |
| `connection-proxy-header` | ❌ Unsupported |
| `cors-allow-credentials` | ✅ Compatible |
| `cors-allow-headers` | ✅ Compatible |
| `cors-allow-methods` | ✅ Compatible |
| `cors-allow-origin` | ✅ Compatible |
| `cors-expose-headers` | ✅ Compatible |
| `cors-max-age` | ✅ Compatible |
| `custom-headers` | ❌ Unsupported |
| `custom-http-errors` | ✅ Compatible |
| `default-backend` | ✅ Compatible |
| `denylist-source-range` | ❌ Unsupported |
| `enable-access-log` | ❌ Unsupported |
| `enable-cors` | ✅ Compatible |
| `enable-global-auth` | ❌ Unsupported |
| `enable-modsecurity` | ❌ Unsupported |
| `enable-opentelemetry` | ❌ Unsupported |
| `enable-owasp-core-rules` | ❌ Unsupported |
| `enable-rewrite-log` | ⚪ Ignorable |
| `force-ssl-redirect` | ✅ Compatible |
| `from-to-www-redirect` | ❌ Unsupported |
| `http2-push-preload` | ⚪ Ignorable |
| `limit-connections` | ❌ Unsupported |
| `limit-rps` | ❌ Unsupported |
| `load-balance` | ✅ Compatible |
| `mirror-host` | ❌ Unsupported |
| `mirror-request-body` | ❌ Unsupported |
| `mirror-target` | ❌ Unsupported |
| `modsecurity-snippet` | ❌ Unsupported |
| `modsecurity-transaction-id` | ❌ Unsupported |
| `permanent-redirect` | ✅ Compatible |
| `permanent-redirect-code` | ✅ Compatible |
| `preserve-trailing-slash` | ⚪ Ignorable |
| `proxy-body-size` | ⚪ Ignorable |
| `proxy-buffer-size` | ⚪ Ignorable |
| `proxy-buffering` | ⚪ Ignorable |
| `proxy-buffers-number` | ⚪ Ignorable |
| `proxy-busy-buffers-size` | ❌ Unsupported |
| `proxy-connect-timeout` | ⚪ Ignorable |
| `proxy-cookie-domain` | ❌ Unsupported |
| `proxy-cookie-path` | ❌ Unsupported |
| `proxy-http-version` | ⚪ Ignorable |
| `proxy-max-temp-file-size` | ⚪ Ignorable |
| `proxy-next-upstream` | ✅ Compatible |
| `proxy-next-upstream-timeout` | ✅ Compatible |
| `proxy-next-upstream-tries` | ✅ Compatible |
| `proxy-read-timeout` | ⚪ Ignorable |
| `proxy-redirect-from` | ❌ Unsupported |
| `proxy-redirect-to` | ❌ Unsupported |
| `proxy-request-buffering` | ❌ Unsupported |
| `proxy-send-timeout` | ⚪ Ignorable |
| `proxy-ssl-ciphers` | ⚪ Ignorable |
| `proxy-ssl-name` | ✅ Compatible |
| `proxy-ssl-protocols` | ⚪ Ignorable |
| `proxy-ssl-secret` | ✅ Compatible |
| `proxy-ssl-server-name` | ✅ Compatible |
| `proxy-ssl-verify` | ✅ Compatible |
| `proxy-ssl-verify-depth` | ❌ Unsupported |
| `rewrite-target` | ✅ Compatible |
| `satisfy` | ❌ Unsupported |
| `server-alias` | ✅ Compatible |
| `server-snippet` | ❌ Unsupported |
| `service-upstream` | ❌ Unsupported |
| `session-cookie-change-on-failure` | ❌ Unsupported |
| `session-cookie-conditional-samesite-none` | ❌ Unsupported |
| `session-cookie-domain` | ❌ Unsupported |
| `session-cookie-expires` | ✅ Compatible |
| `session-cookie-max-age` | ✅ Compatible |
| `session-cookie-name` | ✅ Compatible |
| `session-cookie-path` | ✅ Compatible |
| `session-cookie-samesite` | ❌ Unsupported |
| `session-cookie-secure` | ❌ Unsupported |
| `ssl-ciphers` | ❌ Unsupported |
| `ssl-cipher` | ✅ Compatible |
| `ssl-passthrough` | ❌ Unsupported |
| `ssl-prefer-server-ciphers` | ⚪ Ignorable |
| `ssl-redirect` | ✅ Compatible |
| `stream-snippet` | ❌ Unsupported |
| `temporal-redirect` | ✅ Compatible |
| `temporal-redirect-code` | ❌ Unsupported |
| `upstream-hash-by` | ✅ Compatible |
| `upstream-vhost` | ✅ Compatible |
| `use-regex` | ✅ Compatible |
| `whitelist-source-range` | ✅ Compatible |

## Analysis Script

```bash
./scripts/analyze-ingress.sh [namespace]
```
