# Common Nginx Snippet to WASM Plugin Patterns

## Table of Contents
- [Header Manipulation](#header-manipulation)
- [Request Validation](#request-validation)
- [Request Modification](#request-modification)
- [Lua Script Conversion](#lua-script-conversion)
- [Response Modification](#response-modification)
- [Best Practices](#best-practices)

When migrating to APIG, incompatible nginx snippet annotations are stripped from the new Ingress and replaced with a `higress.io/wasmplugin` annotation pointing to a WasmPlugin that implements equivalent logic. Use the patterns below to create those replacement WasmPlugins.

> **Important**: All custom plugins must be validated for correct behavior in a test environment before deploying to production via the operations manual. Faulty plugin logic can cause requests to be incorrectly blocked or security controls to be bypassed.

## Header Manipulation

When converting `server-snippet` or `configuration-snippet` that contains multiple `add_header` directives, you MUST convert ALL of them — not just a subset. Count the `add_header` lines in the original snippet and verify the same count appears in your WasmPlugin config. Security headers are especially critical: `Strict-Transport-Security` (HSTS), `Content-Security-Policy` (CSP), `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, and `Referrer-Policy` are commonly used together — dropping any one of them weakens the security posture.

### Add Response Header

**Nginx snippet:**
```nginx
more_set_headers "X-Custom-Header: custom-value";
more_set_headers "X-Request-ID: $request_id";
```

**WASM plugin:**
```go
func onHttpResponseHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    proxywasm.AddHttpResponseHeader("X-Custom-Header", "custom-value")
    
    // For request ID, get from request context
    if reqId, err := proxywasm.GetHttpRequestHeader("x-request-id"); err == nil {
        proxywasm.AddHttpResponseHeader("X-Request-ID", reqId)
    }
    return types.HeaderContinue
}
```

**Deploy via Ingress annotation:**
```yaml
annotations:
  higress.io/wasmplugin: |
    {
      "apiVersion": "extensions.istio.io/v1alpha1",
      "kind": "WasmPlugin",
      "metadata": {"name": "<ingress-name>-apig-wasmplugin"},
      "spec": {
        "phase": "UNSPECIFIED_PHASE",
        "pluginConfig": {
          "_rules_": [
            {
              "headers": [
                {"name": "X-Custom-Header", "value": "custom-value"}
              ]
            }
          ]
        },
        "priority": 100,
        "url": "oci://<registry>/higress-wasm-custom-headers:v1"
      }
    }
```
Route matching is automatic — `_match_route_` is auto-filled from the Ingress path rules.

### Remove Headers

**Nginx snippet:**
```nginx
more_clear_headers "Server";
more_clear_headers "X-Powered-By";
```

**WASM plugin:**
```go
func onHttpResponseHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    proxywasm.RemoveHttpResponseHeader("Server")
    proxywasm.RemoveHttpResponseHeader("X-Powered-By")
    return types.HeaderContinue
}
```

### Conditional Header

**Nginx snippet:**
```nginx
if ($http_x_custom_flag = "enabled") {
    more_set_headers "X-Feature: active";
}
```

**WASM plugin:**
```go
func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    flag, _ := proxywasm.GetHttpRequestHeader("x-custom-flag")
    if flag == "enabled" {
        proxywasm.AddHttpRequestHeader("X-Feature", "active")
    }
    return types.HeaderContinue
}
```

## Request Validation

### Block by Path Pattern

**Nginx snippet:**
```nginx
if ($request_uri ~* "(\.php|\.asp|\.aspx)$") {
    return 403;
}
```

**WASM plugin:**
```go
import "regexp"

type MyConfig struct {
    BlockPattern *regexp.Regexp
}

func parseConfig(json gjson.Result, config *MyConfig) error {
    pattern := json.Get("blockPattern").String()
    if pattern == "" {
        pattern = `\.(php|asp|aspx)$`
    }
    config.BlockPattern = regexp.MustCompile(pattern)
    return nil
}

func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    path := ctx.Path()
    if config.BlockPattern.MatchString(path) {
        proxywasm.SendHttpResponse(403, nil, []byte("Forbidden"), -1)
        return types.HeaderStopAllIterationAndWatermark
    }
    return types.HeaderContinue
}
```

### Block by User Agent

**Nginx snippet:**
```nginx
if ($http_user_agent ~* "(bot|crawler|spider)") {
    return 403;
}
```

> **Built-in alternative:** Use `bot-detect` plugin instead of custom WASM. See the built-in plugins catalog (builtin-plugins.md, loaded separately from SKILL.md).

**WASM plugin (if custom logic needed):**
```go
func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    ua, _ := proxywasm.GetHttpRequestHeader("user-agent")
    ua = strings.ToLower(ua)
    
    blockedPatterns := []string{"bot", "crawler", "spider"}
    for _, pattern := range blockedPatterns {
        if strings.Contains(ua, pattern) {
            proxywasm.SendHttpResponse(403, nil, []byte("Blocked"), -1)
            return types.HeaderStopAllIterationAndWatermark
        }
    }
    return types.HeaderContinue
}
```

### Request Size Validation

**Nginx snippet:**
```nginx
if ($content_length > 10485760) {
    return 413;
}
```

**WASM plugin:**
```go
func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    clStr, _ := proxywasm.GetHttpRequestHeader("content-length")
    if cl, err := strconv.ParseInt(clStr, 10, 64); err == nil {
        if cl > 10*1024*1024 { // 10MB
            proxywasm.SendHttpResponse(413, nil, []byte("Request too large"), -1)
            return types.HeaderStopAllIterationAndWatermark
        }
    }
    return types.HeaderContinue
}
```

## Request Modification

### URL Rewrite with Logic

**Nginx snippet:**
```nginx
set $backend "default";
if ($http_x_version = "v2") {
    set $backend "v2";
}
rewrite ^/api/(.*)$ /api/$backend/$1 break;
```

**WASM plugin:**
```go
func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    version, _ := proxywasm.GetHttpRequestHeader("x-version")
    backend := "default"
    if version == "v2" {
        backend = "v2"
    }
    
    path := ctx.Path()
    if strings.HasPrefix(path, "/api/") {
        newPath := "/api/" + backend + path[4:]
        proxywasm.ReplaceHttpRequestHeader(":path", newPath)
    }
    return types.HeaderContinue
}
```

### Add Query Parameter

**Nginx snippet:**
```nginx
if ($args !~ "source=") {
    set $args "${args}&source=gateway";
}
```

**WASM plugin:**
```go
func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    path := ctx.Path()
    if !strings.Contains(path, "source=") {
        separator := "?"
        if strings.Contains(path, "?") {
            separator = "&"
        }
        newPath := path + separator + "source=gateway"
        proxywasm.ReplaceHttpRequestHeader(":path", newPath)
    }
    return types.HeaderContinue
}
```

## Lua Script Conversion

### Conversion Completeness Checklist

When converting a Lua `access_by_lua_block` or `content_by_lua_block` to a WasmPlugin, follow this process to avoid losing logic:

1. **Enumerate every code block** in the original Lua script — list each `if/else`, `ngx.exit()`, `ngx.req.set_header()`, `more_set_headers`, and variable assignment
2. **Create a mapping table** with columns: Original Lua line/block → WasmPlugin Go code location → Status (done/skipped/simplified)
3. **Preserve validation strictness** — if the Lua checks a regex pattern (e.g., JWT format `^Bearer [A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$`), the WasmPlugin must validate with equivalent strictness. A simple `strings.HasPrefix(auth, "Bearer ")` is NOT equivalent to a full JWT 3-part structure check
4. **Preserve error responses** — if the Lua returns specific JSON error bodies (e.g., `{"error":"invalid_token_format"}`), the WasmPlugin must return the same or equivalent error bodies, not generic messages
5. **Preserve all header injections** — if the Lua sets 3 upstream headers, the WasmPlugin must set all 3, not just 2

Common Lua → Go equivalences:
- `ngx.var.http_xxx` → `proxywasm.GetHttpRequestHeader("xxx")`
- `ngx.req.set_header("X-Foo", val)` → `proxywasm.AddHttpRequestHeader("X-Foo", val)`
- `more_set_headers "X-Foo: bar"` → `proxywasm.AddHttpResponseHeader("X-Foo", "bar")` (in response phase)
- `ngx.exit(401)` → `proxywasm.SendHttpResponse(401, ...)` + `return types.HeaderStopAllIterationAndWatermark`
- `ngx.say(json)` → include in `proxywasm.SendHttpResponse` body parameter
- `string:match("pattern")` → `regexp.MustCompile("pattern").MatchString(s)` or `strings.Contains` for simple cases
- `token:gmatch("[^%.]+")` (split by dot) → `strings.Split(token, ".")`

### Simple Lua Access Check

**Nginx Lua:**
```lua
access_by_lua_block {
    local token = ngx.var.http_authorization
    if not token or token == "" then
        ngx.exit(401)
    end
}
```

**WASM plugin:**
```go
func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    token, _ := proxywasm.GetHttpRequestHeader("authorization")
    if token == "" {
        proxywasm.SendHttpResponse(401, [][2]string{
            {"WWW-Authenticate", "Bearer"},
        }, []byte("Unauthorized"), -1)
        return types.HeaderStopAllIterationAndWatermark
    }
    return types.HeaderContinue
}
```

### Lua with Redis

**Nginx Lua:**
```lua
access_by_lua_block {
    local redis = require "resty.redis"
    local red = redis:new()
    red:connect("127.0.0.1", 6379)
    
    local ip = ngx.var.remote_addr
    local count = red:incr("rate:" .. ip)
    if count > 100 then
        ngx.exit(429)
    end
    red:expire("rate:" .. ip, 60)
}
```

> **Built-in alternative:** Use `key-rate-limit` or `cluster-key-rate-limit` plugin. See the built-in plugins catalog (builtin-plugins.md, loaded separately from SKILL.md).

**WASM plugin (if custom logic needed):**
```go
// Redis callback uses resp.Value — import: github.com/higress-group/proxy-wasm-go-sdk/proxywasm/resp
// See references/redis-client.md in higress-wasm-go-plugin skill for full API
func parseConfig(json gjson.Result, config *MyConfig) error {
    config.redis = wrapper.NewRedisClusterClient(wrapper.FQDNCluster{
        FQDN: json.Get("redisService").String(),
        Port: json.Get("redisPort").Int(),
    })
    return config.redis.Init("", json.Get("redisPassword").String(), 1000)
}

func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    ip, _ := proxywasm.GetHttpRequestHeader("x-real-ip")
    if ip == "" {
        ip, _ = proxywasm.GetHttpRequestHeader("x-forwarded-for")
    }
    
    key := "rate:" + ip
    err := config.redis.Incr(key, func(response resp.Value) {
        if response.Error() != nil {
            proxywasm.LogErrorf("redis error: %v", response.Error())
            proxywasm.ResumeHttpRequest()
            return
        }
        
        count := response.Integer()
        ctx.SetContext("timeStamp", key)
        ctx.SetContext("callTimeLeft", strconv.Itoa(config.qpm - count))
        
        if count == 1 {
            // First request in this minute, set expiry
            config.redis.Expire(key, 60, func(response resp.Value) {
                if response.Error() != nil {
                    proxywasm.LogErrorf("expire error: %v", response.Error())
                }
                proxywasm.ResumeHttpRequest()
            })
        } else if count > config.qpm {
            proxywasm.SendHttpResponse(429, [][2]string{
                {"Retry-After", "60"},
            }, []byte("Rate limited\n"), -1)
        } else {
            proxywasm.ResumeHttpRequest()
        }
    })
    
    if err != nil {
        return types.HeaderContinue // Fallback on Redis error
    }
    return types.HeaderStopAllIterationAndWatermark
}
```

## Response Modification

### HMAC Signature Validation (Request Body)

**Nginx Lua:**
```lua
access_by_lua_block {
    ngx.req.read_body()
    local body = ngx.req.get_body_data() or ""
    local sig = ngx.var.http_x_hub_signature_256 or ""
    -- compute HMAC and compare...
    if sig ~= expected then
        ngx.exit(403)
    end
    ngx.req.set_header("X-Verified", "true")
}
```

**WASM plugin (request headers + body phases):**

When a plugin needs to read the request body (e.g., HMAC validation), it must use two phases:
1. `ProcessRequestHeaders` — check preconditions, call `ctx.BufferRequestBody()` to buffer the body
2. `ProcessRequestBody` — receive the buffered body, perform validation

```go
func init() {
    wrapper.SetCtx(
        "hmac-auth",
        wrapper.ParseConfig(parseConfig),
        wrapper.ProcessRequestHeaders(onHttpRequestHeaders),
        wrapper.ProcessRequestBody(onHttpRequestBody),
    )
}

func onHttpRequestHeaders(ctx wrapper.HttpContext, config PluginConfig) types.Action {
    sig, _ := proxywasm.GetHttpRequestHeader("x-hub-signature-256")
    if sig == "" {
        proxywasm.SendHttpResponse(401, [][2]string{
            {"Content-Type", "application/json"},
        }, []byte(`{"error":"missing_signature"}`), -1)
        return types.HeaderStopAllIterationAndWatermark
    }
    // Store signature for body phase, then buffer the body
    ctx.SetContext("signature", sig)
    ctx.BufferRequestBody()
    return types.HeaderContinue
}

func onHttpRequestBody(ctx wrapper.HttpContext, config PluginConfig, body []byte) types.Action {
    sig := ctx.GetStringContext("signature", "")
    // Compute HMAC over body and compare with sig...
    if !valid {
        proxywasm.SendHttpResponse(403, [][2]string{
            {"Content-Type", "application/json"},
        }, []byte(`{"error":"invalid_signature"}`), -1)
        // After SendHttpResponse in body phase, return ActionContinue
        // (NOT HeaderStopAllIterationAndWatermark — that's only for header phase)
        return types.ActionContinue
    }
    // Inject verification headers
    proxywasm.AddHttpRequestHeader("X-Verified", "true")
    return types.ActionContinue
}
```

**Key rules for body-phase handlers:**
- Return `types.ActionContinue` (not `types.HeaderContinue` or `types.HeaderStopAllIterationAndWatermark`) — body phase uses `ActionContinue` exclusively
- After `proxywasm.SendHttpResponse()` in body phase, still return `types.ActionContinue` — the response auto-resumes
- Call `ctx.BufferRequestBody()` in the header phase to ensure the body is available in the body phase

### Inject Script/Content

**Nginx snippet:**
```nginx
sub_filter '</head>' '<script src="/tracking.js"></script></head>';
sub_filter_once on;
```

**WASM plugin:**
```go
func init() {
    wrapper.SetCtx(
        "inject-script",
        wrapper.ParseConfig(parseConfig),
        wrapper.ProcessResponseHeaders(onHttpResponseHeaders),
        wrapper.ProcessResponseBody(onHttpResponseBody),
    )
}

func onHttpResponseHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    contentType, _ := proxywasm.GetHttpResponseHeader("content-type")
    if strings.Contains(contentType, "text/html") {
        ctx.BufferResponseBody()
        proxywasm.RemoveHttpResponseHeader("content-length")
    }
    return types.HeaderContinue
}

func onHttpResponseBody(ctx wrapper.HttpContext, config MyConfig, body []byte) types.Action {
    bodyStr := string(body)
    injection := `<script src="/tracking.js"></script></head>`
    newBody := strings.Replace(bodyStr, "</head>", injection, 1)
    proxywasm.ReplaceHttpResponseBody([]byte(newBody))
    return types.ActionContinue
}
```

## Best Practices

1. **Error Handling**: Always handle external call failures gracefully
2. **Performance**: Cache regex patterns in config, avoid recompiling
3. **Timeout**: Set appropriate timeouts for external calls (default 500ms)
4. **Logging**: Use `proxywasm.LogInfo/Warn/Error` for debugging
5. **Testing**: Test locally with Docker Compose before deploying
6. **Always check built-in plugins first** — avoid custom WASM when a built-in plugin exists
7. **Use annotation binding**: Embed WasmPlugin via `higress.io/wasmplugin` annotation, route matching is automatic
8. **Validate JSON**: Always validate the annotation JSON with `jq` before applying
