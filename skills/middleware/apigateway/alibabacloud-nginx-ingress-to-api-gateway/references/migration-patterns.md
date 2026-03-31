# Migration Patterns and Decision Tree

## Table of Contents
- [Annotation Resolution Decision Tree](#annotation-resolution-decision-tree)
- [Higress Native Annotation Mappings](#higress-native-annotation-mappings)
- [Safe-to-Drop Annotations](#safe-to-drop-annotations)
- [Special Annotation Handling](#special-annotation-handling)
- [Snippet Conversion Completeness](#snippet-conversion-completeness)
- [Handling satisfy Annotation](#handling-satisfy-annotation)
- [Common Plugin Patterns by Annotation Type](#common-plugin-patterns-by-annotation-type)

## Annotation Resolution Decision Tree

For each Ingress with unsupported annotations, follow this order:

```
1. Higress native annotation?  → Use native equivalent (no WasmPlugin)
2. Safe to drop?               → Remove without replacement
3. Built-in platform plugin?   → Use built-in OCI image
4. None of the above?          → Develop custom WasmPlugin
```

If an Ingress's only unsupported annotations are all safe-to-drop or have native equivalents, classify it as "cleaned" (no WasmPlugin needed).

## Higress Native Annotation Mappings

| nginx annotation | Higress equivalent | Notes |
|-----------------|-------------------|-------|
| `denylist-source-range` | `higress.io/blacklist-source-range` | Direct mapping |
| `mirror-target` | `higress.io/mirror-target-service` + `higress.io/mirror-percentage` | Extract service FQDN from URL; set percentage to `100` or user-specified |
| `mirror-request-body` | (drop) | Higress mirrors the full request by default |
| `mirror-host` | (drop) | Higress uses the target service's host; if custom Host header is needed, implement via WasmPlugin |
| `ssl-ciphers` | `ssl-cipher` (compatible annotation, singular form) | Rename only — no WasmPlugin needed |

## Safe-to-Drop Annotations

These unsupported annotations can be removed without any replacement:

| Annotation | Why safe to drop |
|-----------|-----------------|
| `service-upstream` | Envoy routes via Service ClusterIP by default (equivalent to `service-upstream: "true"`), safe regardless of value |
| `enable-access-log` | Configure at gateway level in APIG console |
| `proxy-request-buffering: off` | Envoy streams by default |
| `connection-proxy-header` | Envoy manages connection headers |
| `proxy-busy-buffers-size` | Not applicable in Envoy architecture |
| `auth-tls-error-page` | APIG returns its own TLS error responses; if custom error pages are critical, implement redirect in WasmPlugin, but usually safe to drop |
| `enable-global-auth: false` | Only meaningful with a global auth-url at the nginx-ingress controller level; APIG doesn't have a global external auth concept |

## Special Annotation Handling

### ssl-ciphers → ssl-cipher

APIG uses the singular form `ssl-cipher`. During migration, rename the annotation key (drop the trailing 's'). The value stays the same.

### load-balance: ewma

APIG doesn't support EWMA. Change to `round_robin` or `least_conn`. Call out the old and new values explicitly in the report — the user needs to verify the change doesn't break traffic routing.

### affinity-mode: persistent

APIG only supports `balanced`. Change the value and note it in the report.

### server-snippet / configuration-snippet

Analyze each directive individually:
- Directives with APIG-native equivalents (e.g., `gzip`, `limit_req`, `proxy_cache`) → drop and note in report
- `add_header` directives → use a response-headers type WasmPlugin; count all `add_header` lines and verify the same count in the plugin config
- Lua blocks (`access_by_lua_block`, `content_by_lua_block`) → convert to WasmPlugin
- `set` + `if` variable logic → convert to WasmPlugin header manipulation
- If a snippet mixes multiple concerns (e.g., compression + auth + headers), split into: native features (drop) + WasmPlugin (convert)

### Value Change Tracking

When a compatible annotation is kept but its value changes, the migration report must include an "Annotation Value Changes" table with: Ingress name, annotation, old value, new value, and reason.

## Snippet Conversion Completeness

When converting `configuration-snippet`, `server-snippet`, or `auth-snippet` to a WasmPlugin, follow this process to avoid losing logic:

1. Enumerate every directive/statement in the original snippet
2. Produce a 1:1 mapping table: Original directive → WasmPlugin code location → Status
3. After implementation, verify the table has no gaps

### Common Pitfalls

- **Dropping `add_header` directives** — e.g., a security header snippet with 6 headers but the WasmPlugin only adds 4. The missing 2 weaken the security posture
- **Simplifying multi-step validation** — e.g., a Lua script that performs both format validation AND structural validation. The WasmPlugin needs all checks, because skipping any one may open a security gap
- **Losing error response bodies** — e.g., original returns `{"error":"specific_reason"}` but WasmPlugin returns a generic message. Downstream clients may depend on the error format
- **Confusing `more_set_headers` context** — in `configuration-snippet` (location block), `more_set_headers` sets response headers; but `ngx.req.set_header()` in Lua sets request headers to upstream. Map each header operation to the correct WasmPlugin phase
- **Ignoring APIG-native directives** — `gzip on/off`, `gzip_types`, `limit_req`, `proxy_cache` etc. should be dropped or mapped to APIG-native features, not converted to WasmPlugin code
- **Missing conditional branches** — if the original snippet has multiple `if` blocks, the WasmPlugin must handle all branches including the implicit "else" (fall-through) case

## Handling satisfy Annotation

The `satisfy` annotation controls how multiple auth mechanisms combine:
- `satisfy: all` (default) — ALL auth checks must pass (AND logic)
- `satisfy: any` — ANY auth check passing is sufficient (OR logic)

### Migrating satisfy: any

1. Identify all auth mechanisms on the Ingress (e.g., IP whitelist via `whitelist-source-range`, Basic Auth via `auth-type`, HMAC via `auth-snippet`, external auth via `auth-url`, mTLS via `auth-tls-secret`)
2. In the WasmPlugin, check each mechanism in order — if any one passes, allow immediately
3. Only reject if ALL mechanisms fail

```go
// Generic satisfy:any pattern in onHttpRequestHeaders:
if firstAuthPasses(ctx, config) {
    return types.HeaderContinue
}
if secondAuthPasses(ctx, config) {
    return types.HeaderContinue
}
// All failed — reject
proxywasm.SendHttpResponse(401, headers, body, -1)
return types.HeaderStopAllIterationAndWatermark
```

### satisfy: any with whitelist-source-range

When combined with `whitelist-source-range` (a compatible annotation handled natively by APIG), the IP whitelist check happens at the gateway level before the WasmPlugin runs. The WasmPlugin only needs to handle non-IP auth mechanisms. For explicit/self-contained OR logic (e.g., testing or portability), you can replicate the IP check in the plugin.

### satisfy: all

Each auth mechanism should be a separate check that must all pass — this is the default behavior when multiple auth annotations are present.

## Common Plugin Patterns by Annotation Type

| Nginx annotation | Plugin pattern | Key SDK APIs |
|-----------------|---------------|-------------|
| `configuration-snippet` / `server-snippet` | Parse directives → implement in Go | `proxywasm.GetHttpRequestHeader`, `proxywasm.SendHttpResponse` |
| `auth-url` (external auth) | HTTP callout to auth service | `wrapper.NewClusterClient` + `client.Get` with async callback |
| `custom-headers` | Add response headers | `proxywasm.AddHttpResponseHeader` in `ProcessResponseHeaders` |
| `proxy-cookie-domain/path` | Rewrite Set-Cookie | `proxywasm.GetHttpResponseHeader("set-cookie")` + string replace |
| `modsecurity-*` | Use built-in `waf` plugin | N/A (built-in) |
| `denylist-source-range` | Use `higress.io/blacklist-source-range` or built-in `request-block` | N/A |
| `auth-snippet` + `satisfy: any` | Multi-auth OR logic | `ctx.BufferRequestBody()`, `proxywasm.GetHttpRequestHeader`, `proxywasm.SendHttpResponse` |
| `mirror-target` | Use Higress native annotations | `higress.io/mirror-target-service` + `higress.io/mirror-percentage` |
