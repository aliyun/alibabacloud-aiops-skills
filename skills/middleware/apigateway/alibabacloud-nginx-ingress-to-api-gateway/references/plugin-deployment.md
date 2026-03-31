# WASM Plugin Build and Deployment

## Table of Contents
- [Plugin Project Structure](#plugin-project-structure)
- [Build Process](#build-process)
- [Deployment: Ingress Annotation Binding](#deployment-ingress-annotation-binding)
- [OCI Image Registry (Region-Specific)](#oci-image-registry-region-specific)
- [Verify Deployment](#verify-deployment)
- [Troubleshooting](#troubleshooting)

> **Safety notice**: Custom plugin images are only pushed to the user-specified registry path and never overwrite existing images. Always use new image names (e.g., `higress-wasm-<name>:v1`).

## Plugin Project Structure

```
my-plugin/
├── main.go          # Plugin entry point
├── go.mod           # Go module
├── go.sum           # Dependencies
├── Dockerfile       # OCI image build
├── build.sh         # Compile script
└── push.sh          # Build & push OCI image
```

## Build Process

### 1. Initialize Project

```bash
mkdir my-plugin && cd my-plugin
go mod init my-plugin

# Set proxy (only needed in China mainland due to network restrictions)
# Skip this step if you're outside China or have direct access to GitHub
go env -w GOPROXY=https://proxy.golang.com.cn,direct

# Get dependencies (pinned versions for reproducible builds)
go get github.com/higress-group/proxy-wasm-go-sdk@go-1.24
go get github.com/higress-group/wasm-go@main
go get github.com/tidwall/gjson
```

### 2. Write Plugin Code

See the higress-wasm-go-plugin skill for detailed API reference. Basic template:

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
    // Config fields parsed from pluginConfig._rules_[]
}

func parseConfig(json gjson.Result, config *MyConfig) error {
    // Parse YAML config (converted to JSON)
    return nil
}

func onHttpRequestHeaders(ctx wrapper.HttpContext, config MyConfig) types.Action {
    // Process request
    return types.HeaderContinue
}
```

### 3. Compile to WASM

```bash
go mod tidy
GOOS=wasip1 GOARCH=wasm go build -buildmode=c-shared -o main.wasm ./
```

### 4. Create Dockerfile

```dockerfile
FROM scratch
COPY main.wasm /plugin.wasm
```

### 5. Login and Push OCI Image

Standard `docker push` to ACR produces an **OCI-compliant image**. APIG gateway uses the `oci://` protocol to pull the image and extract the WASM binary from the image layer. No special OCI tooling is needed.

```bash
# User provides registry (must be VPC-accessible from the APIG gateway)
REGISTRY=your-registry.com/higress-plugins

# Login to registry first
docker login $(echo ${REGISTRY} | cut -d'/' -f1)

# Build OCI image (FROM scratch + .wasm = minimal OCI image with only the WASM binary)
docker build -t ${REGISTRY}/my-plugin:v1 .

# Push
docker push ${REGISTRY}/my-plugin:v1
```

## Deployment: Ingress Annotation Binding

APIG supports binding WasmPlugin **directly to an Ingress resource** via annotation. This is the recommended approach for migration because:

- **No separate WasmPlugin CRD** — the plugin config is embedded in the Ingress annotation
- **Automatic route matching** — the controller auto-fills `_match_route_` from the Ingress path rules
- **Self-contained** — each migrated Ingress carries its own plugin config
- **Easy rollback** — deleting the Ingress removes the plugin binding automatically

### Supported Annotation Keys

Any one of these annotation keys can be used (they are equivalent):

| Annotation Key | Notes |
|----------------|-------|
| `higress.io/wasmplugin` | Recommended |
| `higress.ingress.kubernetes.io/wasmplugin` | Alternative |
| `mse.ingress.kubernetes.io/wasmplugin` | MSE compatible |

### Annotation Value Format

The annotation value is a **JSON string** with the following structure:

```json
{
  "apiVersion": "extensions.istio.io/v1alpha1",
  "kind": "WasmPlugin",
  "metadata": {
    "name": "<plugin-name>"
  },
  "spec": {
    "imagePullPolicy": "Always",
    "phase": "<AUTHN|AUTHZ|STATS|UNSPECIFIED_PHASE>",
    "pluginConfig": {
      "_rules_": [
        {
          "config_key": "config_value"
        }
      ]
    },
    "priority": 100,
    "url": "oci://<registry>/<image>:<tag>"
  }
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `metadata.name` | Optional | Plugin name. Auto-generates as `{ingress-name}-wasmplugin` if omitted |
| `spec.url` | **Yes** | OCI image URL of the WASM plugin |
| `spec.phase` | Optional | Execution phase: `AUTHN`, `AUTHZ`, `STATS`, or `UNSPECIFIED_PHASE` |
| `spec.priority` | Optional | Execution order within same phase (higher = earlier). Default: 0 |
| `spec.imagePullPolicy` | Optional | `Always`, `IfNotPresent`, or `Never`. Default: `IfNotPresent` |
| `spec.pluginConfig._rules_` | **Yes** | Array of config objects for route matching |

### Understanding `_rules_` Structure

The `_rules_` field is an array where each element is the plugin's config object. The controller auto-matches routes from the Ingress path rules — you never need to specify route matching yourself.

```json
"pluginConfig": {
  "_rules_": [
    {
      "key1": "value1",
      "key2": "value2"
    }
  ]
}
```

In most migration cases, `_rules_` contains a single element — the config for all routes in that Ingress. The config schema is defined by the plugin's `parseConfig` function: whatever fields you read via `json.Get("xxx")` in `parseConfig`, those are the fields you put in `_rules_[0]`.

For example, if your plugin does `config.AuthURL = json.Get("auth_url").String()`, then the config is:
```json
"_rules_": [{ "auth_url": "http://auth-service/verify" }]
```

For array configs, use JSON arrays:
```json
"_rules_": [{
  "headers": [
    {"name": "X-Frame-Options", "value": "DENY"},
    {"name": "X-XSS-Protection", "value": "1; mode=block"}
  ]
}]
```

### Key Behaviors

1. **`_match_route_` is auto-populated** — The controller automatically fills `_match_route_` based on the Ingress path rules. Do NOT manually specify it; any value you provide will be overridden.

2. **One Ingress = one WasmPlugin** — Each Ingress can only have one `wasmplugin` annotation. If multiple plugin behaviors are needed, combine them into a single plugin image.

3. **Route scoping is automatic** — The plugin only applies to routes defined in the Ingress that carries the annotation.

### Complete Example

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-apig
  namespace: production
  labels:
    migration.higress.io/source: nginx
    migration.higress.io/original-name: my-app
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/use-regex: "true"
    higress.io/wasmplugin: |
      {
        "apiVersion": "extensions.istio.io/v1alpha1",
        "kind": "WasmPlugin",
        "metadata": {
          "name": "my-app-apig-wasmplugin"
        },
        "spec": {
          "imagePullPolicy": "Always",
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
          "url": "oci://your-registry.com/higress-wasm-custom-headers:v1"
        }
      }
spec:
  ingressClassName: apig
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /api(/|$)(.*)
        pathType: ImplementationSpecific
        backend:
          service:
            name: backend
            port:
              number: 8080
```

### Using Built-in Plugins via Annotation

For built-in plugins, use the official OCI registry URL directly:

```yaml
annotations:
  higress.io/wasmplugin: |
    {
      "apiVersion": "extensions.istio.io/v1alpha1",
      "kind": "WasmPlugin",
      "metadata": {"name": "rate-limit"},
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
```

## OCI Image Registry (Region-Specific)

Platform built-in plugin images are in a **region-specific VPC registry**. To determine the correct `PLATFORM_OCI_BASE` for the target cluster, see platform-oci-registry.md (loaded separately from SKILL.md).

**Custom plugins** use the user's own registry and must be VPC-accessible from the gateway.

## Verify Deployment

```bash
# Check plugin annotation on the Ingress
kubectl get ingress <name>-apig -o jsonpath='{.metadata.annotations.higress\.io/wasmplugin}' | jq .

# Test endpoint (user must provide the gateway VPC address)
curl -v -H "Host: example.com" http://<gateway-address>/test-path
```

> The APIG gateway runs outside the ACK cluster. For gateway-side logs (plugin loading, errors), ask the user to check the **Alibaba Cloud APIG console**.

## Troubleshooting

### Plugin Not Loading

1. Verify the OCI image URL uses the correct region and `platform_wasm` path for built-in plugins
2. For custom plugins, verify VPC connectivity from the gateway to the user's OCI registry
3. Check gateway logs in the **Alibaba Cloud APIG console** for image pull or WASM loading errors

### Plugin Errors

1. Verify the annotation JSON is well-formed: `kubectl get ingress <name>-apig -o jsonpath='{.metadata.annotations.higress\.io/wasmplugin}' | jq .`
2. Check the `pluginConfig` matches the plugin's expected schema
3. Check gateway logs in the **Alibaba Cloud APIG console** for runtime errors

### Multiple Plugins Needed for One Ingress

Since one Ingress can only carry one `wasmplugin` annotation, if you need multiple plugin behaviors:

1. **Combine into one plugin** — create a single WASM plugin that implements all needed logic
2. **Use built-in for common features** — some features (CORS, rate limiting) may be handled via native annotations without a WasmPlugin
3. **Split the Ingress** — if the paths are independent, split into multiple Ingress resources, each with its own plugin annotation
