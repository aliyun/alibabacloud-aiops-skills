# Higress WASM Go Plugin SDK Reference

## Table of Contents
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
- [Common Patterns](#common-patterns)
- [Best Practices](#best-practices)

> Consolidated from the `higress-wasm-go-plugin` skill. Additional reference files (HTTP client, Redis client, advanced patterns, local testing) are linked from SKILL.md Step 3b.

> ⚠️ **Safety Notice**: Plugin code should be thoroughly validated in a test environment before deploying to production. Plugins run in the gateway data plane — a faulty implementation can affect all traffic passing through the gateway.

## Quick Start

### Project Setup

```bash
mkdir my-plugin && cd my-plugin
go mod init my-plugin

# Set proxy (China mainland — skip if you have direct GitHub access)
go env -w GOPROXY=https://proxy.golang.com.cn,direct

# Download dependencies (use pinned versions for reproducible builds)
go get github.com/higress-group/proxy-wasm-go-sdk@go-1.24
go get github.com/higress-group/wasm-go@main
go get github.com/tidwall/gjson
```

> If `go mod tidy` fails with "unknown revision", run `go get github.com/higress-group/proxy-wasm-go-sdk@go-1.24` and `go get github.com/higress-group/wasm-go@main` to resolve correct versions.

### Minimal Plugin Template

```go
package main

import (
    "github.com/higress-group/wasm-go/pkg/wrapper"
    "github.com/higress-group/proxy-wasm-go-sdk/proxywasm"
    "github.com/higress-group/proxy-wasm-go-sdk/proxywasm/types"
    "github.com/tidwall/gjson"
)

func main() {}

func init() {
    wrapper.SetCtx(
        "my-plugin",
        wrapper.ParseConfig(parseConfig),
        wrapper.ProcessRequestHeaders(onHttpRequestHeaders),
    )
}

type MyConfig struct {
    Enabled bool
}

func parseConfig(json gjson.Result, config *MyConfig) error {
    config.Enabled = json.Get("enabled").Bool()
    return nil
}

func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    if config.Enabled {
        proxywasm.AddHttpRequestHeader("x-my-header", "hello")
    }
    return types.HeaderContinue
}
```

### Compile

```bash
go mod tidy
GOOS=wasip1 GOARCH=wasm go build -buildmode=c-shared -o main.wasm ./
```

## Core Concepts

### Plugin Lifecycle

1. **init()** — Register plugin with `wrapper.SetCtx()`
2. **parseConfig** — Parse YAML config (auto-converted to JSON via gjson)
3. **HTTP processing phases** — Handle requests/responses

### HTTP Processing Phases

Register only the phases you need — unused phases add overhead.

| Phase | Trigger | Handler | When to use |
|-------|---------|---------|-------------|
| Request Headers | Gateway receives client request headers | `ProcessRequestHeaders` | Auth checks, header manipulation, routing decisions |
| Request Body | Gateway receives client request body | `ProcessRequestBody` | Body validation, transformation (buffers entire body) |
| Response Headers | Gateway receives backend response headers | `ProcessResponseHeaders` | Add/modify response headers, set cookies |
| Response Body | Gateway receives backend response body | `ProcessResponseBody` | Body transformation (buffers entire body) |
| Stream Done | HTTP stream completes | `ProcessStreamDone` | Cleanup, logging |

### Action Return Values

| Action | Behavior | When to use |
|--------|----------|-------------|
| `types.HeaderContinue` | Continue to next filter | Default — processing complete, pass through |
| `types.HeaderStopIteration` | Stop header processing, wait for body | When you need the body but don't need async calls |
| `types.HeaderStopAllIterationAndWatermark` | Stop all processing, buffer data | **Required for async external calls** — call `proxywasm.ResumeHttpRequest/Response()` in callback to resume |

### Body Action Return Values

| Action | Behavior |
|--------|----------|
| `types.ActionContinue` | Continue processing (used in body phase handlers) |

## API Reference

### HttpContext Methods

```go
ctx.Scheme()   // :scheme
ctx.Host()     // :authority
ctx.Path()     // :path
ctx.Method()   // :method

ctx.HasRequestBody()        // Check if request has body
ctx.HasResponseBody()       // Check if response has body
ctx.DontReadRequestBody()   // Skip reading request body
ctx.DontReadResponseBody()  // Skip reading response body
ctx.BufferRequestBody()     // Buffer instead of stream
ctx.BufferResponseBody()    // Buffer instead of stream

ctx.IsWebsocket()           // Check WebSocket upgrade
ctx.IsBinaryRequestBody()   // Check binary content
ctx.IsBinaryResponseBody()  // Check binary content

ctx.SetContext(key, value)
ctx.GetContext(key)
ctx.GetStringContext(key, defaultValue)
ctx.GetBoolContext(key, defaultValue)

ctx.SetUserAttribute(key, value)
ctx.WriteUserAttributeToLog()
```

### Header/Body Operations (proxywasm)

```go
// Request headers
proxywasm.GetHttpRequestHeader(name)
proxywasm.AddHttpRequestHeader(name, value)
proxywasm.ReplaceHttpRequestHeader(name, value)
proxywasm.RemoveHttpRequestHeader(name)
proxywasm.GetHttpRequestHeaders()
proxywasm.ReplaceHttpRequestHeaders(headers)

// Response headers
proxywasm.GetHttpResponseHeader(name)
proxywasm.AddHttpResponseHeader(name, value)
proxywasm.ReplaceHttpResponseHeader(name, value)
proxywasm.RemoveHttpResponseHeader(name)
proxywasm.GetHttpResponseHeaders()
proxywasm.ReplaceHttpResponseHeaders(headers)

// Request body (only in body phase)
proxywasm.GetHttpRequestBody(start, size)
proxywasm.ReplaceHttpRequestBody(body)
proxywasm.AppendHttpRequestBody(data)
proxywasm.PrependHttpRequestBody(data)

// Response body (only in body phase)
proxywasm.GetHttpResponseBody(start, size)
proxywasm.ReplaceHttpResponseBody(body)
proxywasm.AppendHttpResponseBody(data)
proxywasm.PrependHttpResponseBody(data)

// Direct response (blocks request, auto-resumes — do NOT call ResumeHttpRequest after this)
proxywasm.SendHttpResponse(statusCode, headers, body, grpcStatus)

// Flow control
proxywasm.ResumeHttpRequest()   // Resume paused request (after async call completes)
proxywasm.ResumeHttpResponse()  // Resume paused response
```

### Logging (proxywasm)

```go
proxywasm.LogInfo(msg)
proxywasm.LogInfof(format, args...)
proxywasm.LogWarn(msg)
proxywasm.LogWarnf(format, args...)
proxywasm.LogError(msg)
proxywasm.LogErrorf(format, args...)
proxywasm.LogDebug(msg)
proxywasm.LogDebugf(format, args...)
```

## Common Patterns

### External HTTP Call (Async)

The async call pattern is the most important pattern in WASM plugin development — pause the request, make an async HTTP call, then resume or reject in the callback.

```go
import "net/http" // Only for http.Header type in callback — do NOT use http.Client

type MyConfig struct {
    client wrapper.HttpClient
}

func parseConfig(json gjson.Result, config *MyConfig) error {
    config.client = wrapper.NewClusterClient(wrapper.FQDNCluster{
        FQDN: json.Get("serviceName").String(),
        Port: json.Get("servicePort").Int(),
    })
    return nil
}

func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    var headers [][2]string
    if auth, err := proxywasm.GetHttpRequestHeader("authorization"); err == nil && auth != "" {
        headers = append(headers, [2]string{"Authorization", auth})
    }
    
    err := config.client.Get("/api/check", headers,
        func(statusCode int, responseHeaders http.Header, responseBody []byte) {
            if statusCode != 200 {
                proxywasm.SendHttpResponse(403, [][2]string{
                    {"Content-Type", "application/json"},
                }, []byte(`{"error":"forbidden"}`), -1)
                return
            }
            proxywasm.ResumeHttpRequest()
        }, 3000)
    
    if err != nil {
        proxywasm.LogWarnf("http call dispatch failed: %v", err)
        return types.HeaderContinue
    }
    return types.HeaderStopAllIterationAndWatermark
}
```

### Redis Integration

```go
func parseConfig(json gjson.Result, config *MyConfig) error {
    config.redis = wrapper.NewRedisClusterClient(wrapper.FQDNCluster{
        FQDN: json.Get("redisService").String(),
        Port: json.Get("redisPort").Int(),
    })
    return config.redis.Init(
        json.Get("username").String(),
        json.Get("password").String(),
        json.Get("timeout").Int(),
    )
}
```

### Phase Registration Patterns

```go
// Auth-only plugin (most common for migration): request headers only
wrapper.SetCtx("my-auth",
    wrapper.ParseConfig(parseConfig),
    wrapper.ProcessRequestHeaders(onHttpRequestHeaders),
)

// Response header injection: response headers only
wrapper.SetCtx("add-headers",
    wrapper.ParseConfig(parseConfig),
    wrapper.ProcessResponseHeaders(onHttpResponseHeaders),
)

// Cookie/redirect rewriting: needs both response headers and body
wrapper.SetCtx("rewrite",
    wrapper.ParseConfig(parseConfig),
    wrapper.ProcessResponseHeaders(onHttpResponseHeaders),
    wrapper.ProcessResponseBody(onHttpResponseBody),
)

// Body validation: request headers + body
wrapper.SetCtx("validate",
    wrapper.ParseConfig(parseConfig),
    wrapper.ProcessRequestHeaders(onHttpRequestHeaders),
    wrapper.ProcessRequestBody(onHttpRequestBody),
)
```

### Config Parsing with `gjson.ForEach`

```go
// Array iteration
json.Get("headers").ForEach(func(_, item gjson.Result) bool {
    name := item.Get("name").String()
    value := item.Get("value").String()
    if name != "" {
        config.Headers = append(config.Headers, Header{Name: name, Value: value})
    }
    return true // return true to continue, false to stop
})

// Map/object iteration
config.InjectHeaders = make(map[string]string)
json.Get("inject_headers").ForEach(func(key, value gjson.Result) bool {
    config.InjectHeaders[key.String()] = value.String()
    return true
})
```

### Multi-level Config

Plugin configuration supports multiple levels in the console: global, domain-level, and route-level. The control plane automatically handles config priority and matching logic — the config received by `parseConfig` is the one that matched the current request.

## Best Practices

1. **Never call Resume after SendHttpResponse** — `SendHttpResponse` auto-resumes the filter chain
2. **Always return `HeaderStopAllIterationAndWatermark` for async calls** — Using `HeaderStopIteration` instead will cause the request to proceed before the callback fires
3. **Check HasRequestBody() before returning HeaderStopIteration** — If there's no body, the body phase handler will never fire, blocking the request forever
4. **Use cached ctx methods** — `ctx.Path()`, `ctx.Host()`, `ctx.Method()` work in any phase; `GetHttpRequestHeader(":path")` only works in the request header phase
5. **Handle external call failures gracefully** — Return `HeaderContinue` on dispatch error to avoid blocking the request
6. **Set appropriate timeouts** — Default HTTP call timeout is 500ms, which is too short for most auth services. Use 3000-5000ms
7. **Cannot use `net/http` for outbound calls** — Use `wrapper.NewClusterClient` exclusively. `net/http` is only imported for the `http.Header` type in callback signatures
8. **Register only needed phases** — Each registered phase adds processing overhead
9. **Cache regex patterns in config** — Compile `regexp.Regexp` in `parseConfig`, not in request handlers
10. **`GetHttpRequestHeader` returns `(string, error)`** — Check both: `if auth, err := proxywasm.GetHttpRequestHeader("authorization"); err == nil && auth != ""`
