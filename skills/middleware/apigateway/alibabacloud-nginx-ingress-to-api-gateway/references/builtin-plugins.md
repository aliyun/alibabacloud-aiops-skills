# APIG Built-in Platform Plugins

Before writing custom WASM plugins, check if APIG has a built-in platform plugin that meets your needs.

**Official docs**: https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/platform-plug-ins/

## Authentication & Authorization

| Plugin | Description | Replaces nginx feature | Docs |
|--------|-------------|----------------------|------|
| `key-auth` | API Key authentication from URL params or headers | Custom auth headers | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/key-auth-plug-ins) |
| `basic-auth` | HTTP Basic Auth (RFC 7617) | `auth_basic` directive | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/basic-auth-plug-ins) |
| `hmac-auth` | HMAC signature-based authentication | Signature validation scripts | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/hmac-auth-plug-ins) |
| `jwt-auth` | JWT validation from URL params, headers, or cookies; supports per-caller credentials | JWT Lua scripts, `auth_request` for JWT | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/jwt-auth-plug-ins) |
| `oauth` | OAuth 2.0 Access Token issuance based on JWT (RFC 9068) | OAuth Lua scripts | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/oauth-plugin) |
| `jwt-logout` | JWT logout & unique-login control via Redis; supports session kick-off across devices | Custom session invalidation logic | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/jwt-logout-plug-ins) |

## Traffic Control

| Plugin | Description | Replaces nginx feature | Docs |
|--------|-------------|----------------------|------|
| `key-rate-limit` | Rate limiting by key (URL param or header) | `limit_req` directive | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/key-rate-limit-plugin) |
| `cluster-key-rate-limit` | Distributed rate limiting via Redis across gateway instances | `limit_req` with shared state | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/throttle-based-on-cluster-keys) |
| `http-real-ip` | WASM implementation of nginx `ngx_http_realip_module`; extracts real client IP from trusted proxies | `set_real_ip_from`, `real_ip_header` directives | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/http-real-ip-plug-ins) |
| `hsts` | Adds `Strict-Transport-Security` header to HTTPS responses; browser-side 307 redirect to HTTPS | `add_header Strict-Transport-Security` | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/hsts-plug-in) |
| `canary-header` | Adds headers by configurable weight for proportional grayscale routing without client-side changes | Custom canary routing scripts | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/canary-header-plugin) |
| `traffic-tag` | Tags/colors traffic by weight or request content via request headers | Custom headers for routing | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/the-traffic-tag-plugin) |

## Transmission Protocol

| Plugin | Description | Replaces nginx feature | Docs |
|--------|-------------|----------------------|------|
| `custom-response` | Custom HTTP response (status code, headers, body); can be used for mocking or custom error pages | `return` directive, `error_page` | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/custom-response-plugin) |
| `de-graphql` | Maps URIs to GraphQL queries, converting GraphQL upstream to REST-like access | GraphQL handling | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/degraphql-plugin) |
| `frontend-gray` | Frontend A/B testing and grayscale release by user ID, cookie, weight, or localStorage | Frontend deployment scripts | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/front-end-grayscale-plug-in) |
| `cache-control` | Adds `Expires` and `Cache-Control` headers by URL file suffix (e.g. jpg, png) | `expires`, `add_header Cache-Control` | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/browser-cache-control) |
| `geo-ip` | Resolves client IP to geographic location; passes results via request headers and attributes | `geoip` module | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/geographic-location-of-ip) |

## Security Protection

| Plugin | Description | Replaces nginx feature | Docs |
|--------|-------------|----------------------|------|
| `request-block` | Blocks HTTP requests by URL, header, or other patterns | `if` + `return 403` | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/request-block-plugin) |
| `bot-detect` | Identifies and blocks web crawlers/bots | Bot detection Lua scripts | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/bot-detect-plug-ins) |
| `waf` | Web Application Firewall based on ModSecurity; supports OWASP CRS | ModSecurity module | [doc](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/waf-plugin) |

## Open-source Higress Plugins NOT Confirmed in APIG

The following plugins exist in open-source Higress but are **NOT listed** in the APIG platform plugin documentation. They may still work if you push the WASM image to a private registry, but they are not officially supported as platform plugins. The agent should **not** assume these are available as built-in; if equivalent functionality is needed, generate a custom WasmPlugin instead.

| Plugin | Description | Status |
|--------|-------------|--------|
| `transformer` | Request/response header/body transformation | Not in APIG docs |
| `cors` | CORS header injection | Not in APIG docs (CORS is handled via native annotations `enable-cors` etc.) |
| `ip-restriction` | IP whitelist/blacklist | Not in APIG docs (use `request-block` or native annotation `whitelist-source-range`) |
| `ext-auth` | External authorization service | Not in APIG docs |
| `oidc` | OpenID Connect | Not in APIG docs |
| `opa` | Open Policy Agent | Not in APIG docs |
| `request-validation` | Request parameter validation | Not in APIG docs |

## Using Built-in Plugins

### Via Ingress Annotation (Recommended for Migration)

For APIG migration, bind built-in plugins directly to Ingress resources via the `higress.io/wasmplugin` annotation:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-apig
  namespace: production
  annotations:
    higress.io/wasmplugin: |
      {
        "apiVersion": "extensions.istio.io/v1alpha1",
        "kind": "WasmPlugin",
        "metadata": {"name": "my-app-rate-limit"},
        "spec": {
          "phase": "UNSPECIFIED_PHASE",
          "pluginConfig": {
            "_rules_": [
              {
                "limit_by_per_ip": 10
              }
            ]
          },
          "priority": 200,
          "url": "oci://apiginner-registry-vpc.cn-shanghai.cr.aliyuncs.com/platform_wasm/key-rate-limit:1.0.0"
        }
      }
spec:
  ingressClassName: apig
  # ... rules ...
```

Key points:
- **Route matching is automatic** — `_match_route_` is auto-filled by the controller from the Ingress path rules
- **One Ingress = one plugin annotation** — if multiple behaviors are needed, combine into one plugin or use native annotations for standard features
- **Self-contained** — deleting the Ingress removes the plugin binding automatically

### Via Higress Console

1. Navigate to **Plugins** → **Plugin Market**
2. Find the desired plugin
3. Click **Enable** and configure
4. Under **Scope**, select specific routes/domains

## OCI Image Registry

Platform built-in plugin images are hosted in a **region-specific VPC registry**. To construct the correct OCI URL for a built-in plugin, consult platform-oci-registry.md (loaded separately from SKILL.md) for:
- Auto-detection command (via kubectl node labels)
- Full region ID → `PLATFORM_OCI_BASE` lookup table
- OCI URL construction formula: `oci://${PLATFORM_OCI_BASE}/<plugin-name>:<version>`

> **Custom plugins** use the user's own OCI registry (e.g. `oci://registry.cn-hangzhou.aliyuncs.com/my-plugins/higress-wasm-foo:v1`). The user must ensure VPC connectivity from the gateway to their registry.

## Plugin Configuration Reference

Each plugin has its own configuration schema. For detailed configuration, refer to the official Alibaba Cloud documentation:
https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/platform-plug-ins/

Or check the open-source plugin specs:
https://github.com/higress-group/higress-console/tree/main/backend/sdk/src/main/resources/plugins/<plugin-name>/spec.yaml
