#!/bin/bash
# Generate WASM plugin scaffold for nginx snippet migration

set -e

# ── Execution timeout (120 seconds) ──────────────────────────────────────────
SCRIPT_TIMEOUT=${SCRIPT_TIMEOUT:-120}
if [[ "${_TIMEOUT_GUARD:-}" != "1" ]]; then
    export _TIMEOUT_GUARD=1
    if command -v timeout &>/dev/null; then
        timeout "$SCRIPT_TIMEOUT" bash "$0" "$@"
        exit $?
    elif command -v gtimeout &>/dev/null; then
        gtimeout "$SCRIPT_TIMEOUT" bash "$0" "$@"
        exit $?
    fi
fi

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 <plugin-name> [output-dir] [--type <auth|response-headers|rewrite|full>]"
    echo ""
    echo "Generate a WASM plugin scaffold for nginx snippet migration."
    echo ""
    echo "Arguments:"
    echo "  <plugin-name>    Name of the plugin to generate"
    echo "  [output-dir]     Directory to create plugin in (default: current dir)"
    echo "  --type <type>    Plugin type (determines which phases are registered):"
    echo "                     auth              Request headers only"
    echo "                     response-headers  Response headers only"
    echo "                     rewrite           Response headers + body"
    echo "                     full              All 4 phases (default)"
    echo ""
    echo "Example: $0 custom-headers ./plugins --type response-headers"
    exit 0
fi

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <plugin-name> [output-dir] [--type <auth|response-headers|rewrite|full>]"
    echo ""
    echo "Plugin types (determines which phases are registered):"
    echo "  auth              Request headers only (auth checks, header injection)"
    echo "  response-headers  Response headers only (add/modify response headers)"
    echo "  rewrite           Response headers + body (cookie/redirect rewriting)"
    echo "  full              All 4 phases (default — remove unused phases after implementing)"
    echo ""
    echo "Example: $0 custom-headers ./plugins --type response-headers"
    exit 1
fi

PLUGIN_NAME="$1"
OUTPUT_DIR="${2:-.}"
PLUGIN_TYPE="full"

# ── Input validation ──────────────────────────────────────────────────────────
# Validate PLUGIN_NAME: only allow alphanumeric, hyphens, and underscores
if [[ ! "$PLUGIN_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Error: Invalid plugin name '${PLUGIN_NAME}'." >&2
    echo "  Plugin name must contain only letters, digits, hyphens, and underscores ([a-zA-Z0-9_-])." >&2
    exit 1
fi

# Validate OUTPUT_DIR: reject path traversal patterns
if [[ "$OUTPUT_DIR" == *".."* ]]; then
    echo "Error: Invalid output directory '${OUTPUT_DIR}'." >&2
    echo "  Path must not contain '..' (path traversal is not allowed)." >&2
    exit 1
fi

# Parse --type flag
shift 2 2>/dev/null || shift $# 2>/dev/null
while [[ $# -gt 0 ]]; do
    case "$1" in
        --type) PLUGIN_TYPE="$2"; shift 2 ;;
        *) shift ;;
    esac
done
PLUGIN_DIR="${OUTPUT_DIR}/${PLUGIN_NAME}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Generating WASM plugin scaffold: ${PLUGIN_NAME}${NC}"

# Create directory
mkdir -p "$PLUGIN_DIR"

# Generate go.mod
cat > "${PLUGIN_DIR}/go.mod" << EOF
module ${PLUGIN_NAME}

go 1.24.1

require (
	github.com/higress-group/proxy-wasm-go-sdk v0.0.0-20251103120604-77e9cce339d2
	github.com/higress-group/wasm-go v1.1.2-0.20260216154005-c425a9111a36
	github.com/tidwall/gjson v1.18.0
)

require (
	github.com/google/uuid v1.6.0 // indirect
	github.com/tidwall/match v1.1.1 // indirect
	github.com/tidwall/pretty v1.2.1 // indirect
	github.com/tidwall/resp v0.1.1 // indirect
	github.com/tidwall/sjson v1.2.5 // indirect
)
EOF

# Generate main.go based on plugin type
case "$PLUGIN_TYPE" in
    auth)
cat > "${PLUGIN_DIR}/main.go" << 'EOF'
package main

import (
	"github.com/higress-group/proxy-wasm-go-sdk/proxywasm"
	"github.com/higress-group/proxy-wasm-go-sdk/proxywasm/types"
	"github.com/higress-group/wasm-go/pkg/wrapper"
	"github.com/tidwall/gjson"
)

func main() {}

func init() {
	wrapper.SetCtx(
		"PLUGIN_NAME_PLACEHOLDER",
		wrapper.ParseConfig(parseConfig),
		wrapper.ProcessRequestHeaders(onHttpRequestHeaders),
	)
}

// PluginConfig holds the plugin configuration
type PluginConfig struct {
	// TODO: Add configuration fields
	Enabled bool
}

// parseConfig parses the plugin configuration from YAML (converted to JSON)
func parseConfig(json gjson.Result, config *PluginConfig) error {
	config.Enabled = json.Get("enabled").Bool()
	proxywasm.LogInfof("Plugin config loaded: enabled=%v", config.Enabled)
	return nil
}

// onHttpRequestHeaders is called when request headers are received
func onHttpRequestHeaders(ctx wrapper.HttpContext, config PluginConfig) types.Action {
	if !config.Enabled {
		return types.HeaderContinue
	}

	// TODO: Implement auth logic
	// Example: Check authorization header
	// auth, _ := proxywasm.GetHttpRequestHeader("authorization")
	// if auth == "" {
	//     proxywasm.SendHttpResponse(401, [][2]string{
	//         {"Content-Type", "application/json"},
	//     }, []byte(`{"error":"unauthorized"}`), -1)
	//     return types.HeaderStopAllIterationAndWatermark
	// }

	return types.HeaderContinue
}
EOF
    ;;
    response-headers)
cat > "${PLUGIN_DIR}/main.go" << 'EOF'
package main

import (
	"github.com/higress-group/proxy-wasm-go-sdk/proxywasm"
	"github.com/higress-group/proxy-wasm-go-sdk/proxywasm/types"
	"github.com/higress-group/wasm-go/pkg/wrapper"
	"github.com/tidwall/gjson"
)

func main() {}

func init() {
	wrapper.SetCtx(
		"PLUGIN_NAME_PLACEHOLDER",
		wrapper.ParseConfig(parseConfig),
		wrapper.ProcessResponseHeaders(onHttpResponseHeaders),
	)
}

type Header struct {
	Name  string
	Value string
}

// PluginConfig holds the plugin configuration
type PluginConfig struct {
	Headers []Header
}

// parseConfig parses the plugin configuration from YAML (converted to JSON)
func parseConfig(json gjson.Result, config *PluginConfig) error {
	json.Get("headers").ForEach(func(_, item gjson.Result) bool {
		name := item.Get("name").String()
		value := item.Get("value").String()
		if name != "" {
			config.Headers = append(config.Headers, Header{Name: name, Value: value})
		}
		return true
	})
	proxywasm.LogInfof("Plugin config loaded: %d headers", len(config.Headers))
	return nil
}

// onHttpResponseHeaders is called when response headers are received
func onHttpResponseHeaders(ctx wrapper.HttpContext, config PluginConfig) types.Action {
	for _, h := range config.Headers {
		proxywasm.AddHttpResponseHeader(h.Name, h.Value)
	}
	return types.HeaderContinue
}
EOF
    ;;
    rewrite)
cat > "${PLUGIN_DIR}/main.go" << 'EOF'
package main

import (
	"github.com/higress-group/proxy-wasm-go-sdk/proxywasm"
	"github.com/higress-group/proxy-wasm-go-sdk/proxywasm/types"
	"github.com/higress-group/wasm-go/pkg/wrapper"
	"github.com/tidwall/gjson"
)

func main() {}

func init() {
	wrapper.SetCtx(
		"PLUGIN_NAME_PLACEHOLDER",
		wrapper.ParseConfig(parseConfig),
		wrapper.ProcessResponseHeaders(onHttpResponseHeaders),
		wrapper.ProcessResponseBody(onHttpResponseBody),
	)
}

// PluginConfig holds the plugin configuration
type PluginConfig struct {
	// TODO: Add rewrite rules
	Enabled bool
}

// parseConfig parses the plugin configuration from YAML (converted to JSON)
func parseConfig(json gjson.Result, config *PluginConfig) error {
	config.Enabled = json.Get("enabled").Bool()
	proxywasm.LogInfof("Plugin config loaded: enabled=%v", config.Enabled)
	return nil
}

// onHttpResponseHeaders is called when response headers are received
func onHttpResponseHeaders(ctx wrapper.HttpContext, config PluginConfig) types.Action {
	if !config.Enabled {
		return types.HeaderContinue
	}

	// TODO: Implement header rewriting (e.g., Set-Cookie domain/path, Location header)
	// Example: Rewrite Set-Cookie domain
	// cookie, _ := proxywasm.GetHttpResponseHeader("set-cookie")
	// if cookie != "" {
	//     newCookie := strings.Replace(cookie, ".internal.example.com", ".example.com", -1)
	//     proxywasm.ReplaceHttpResponseHeader("set-cookie", newCookie)
	// }

	return types.HeaderContinue
}

// onHttpResponseBody is called when response body is received
func onHttpResponseBody(ctx wrapper.HttpContext, config PluginConfig, body []byte) types.Action {
	if !config.Enabled {
		return types.ActionContinue
	}

	// TODO: Implement body rewriting if needed
	return types.ActionContinue
}
EOF
    ;;
    *)
# full — all 4 phases (original behavior)
cat > "${PLUGIN_DIR}/main.go" << 'EOF'
package main

import (
	"github.com/higress-group/proxy-wasm-go-sdk/proxywasm"
	"github.com/higress-group/proxy-wasm-go-sdk/proxywasm/types"
	"github.com/higress-group/wasm-go/pkg/wrapper"
	"github.com/tidwall/gjson"
)

func main() {}

func init() {
	wrapper.SetCtx(
		"PLUGIN_NAME_PLACEHOLDER",
		wrapper.ParseConfig(parseConfig),
		wrapper.ProcessRequestHeaders(onHttpRequestHeaders),
		wrapper.ProcessRequestBody(onHttpRequestBody),
		wrapper.ProcessResponseHeaders(onHttpResponseHeaders),
		wrapper.ProcessResponseBody(onHttpResponseBody),
	)
}

// PluginConfig holds the plugin configuration
type PluginConfig struct {
	// TODO: Add configuration fields
	Enabled bool
}

// parseConfig parses the plugin configuration from YAML (converted to JSON)
func parseConfig(json gjson.Result, config *PluginConfig) error {
	config.Enabled = json.Get("enabled").Bool()
	proxywasm.LogInfof("Plugin config loaded: enabled=%v", config.Enabled)
	return nil
}

// onHttpRequestHeaders is called when request headers are received
func onHttpRequestHeaders(ctx wrapper.HttpContext, config PluginConfig) types.Action {
	if !config.Enabled {
		return types.HeaderContinue
	}

	// TODO: Implement request header processing
	return types.HeaderContinue
}

// onHttpRequestBody is called when request body is received
// Remove this function from init() if not needed
func onHttpRequestBody(ctx wrapper.HttpContext, config PluginConfig, body []byte) types.Action {
	if !config.Enabled {
		return types.ActionContinue
	}

	// TODO: Implement request body processing
	return types.ActionContinue
}

// onHttpResponseHeaders is called when response headers are received
func onHttpResponseHeaders(ctx wrapper.HttpContext, config PluginConfig) types.Action {
	if !config.Enabled {
		return types.HeaderContinue
	}

	// TODO: Implement response header processing
	return types.HeaderContinue
}

// onHttpResponseBody is called when response body is received
// Remove this function from init() if not needed
func onHttpResponseBody(ctx wrapper.HttpContext, config PluginConfig, body []byte) types.Action {
	if !config.Enabled {
		return types.ActionContinue
	}

	// TODO: Implement response body processing
	return types.ActionContinue
}
EOF
    ;;
esac

# Replace plugin name placeholder (PLUGIN_NAME is validated to [a-zA-Z0-9_-] above)
sed -i '' "s|PLUGIN_NAME_PLACEHOLDER|${PLUGIN_NAME}|g" "${PLUGIN_DIR}/main.go" 2>/dev/null || \
sed -i "s|PLUGIN_NAME_PLACEHOLDER|${PLUGIN_NAME}|g" "${PLUGIN_DIR}/main.go"

# Generate Dockerfile
cat > "${PLUGIN_DIR}/Dockerfile" << 'EOF'
FROM scratch
COPY main.wasm /plugin.wasm
EOF

# Generate build script
cat > "${PLUGIN_DIR}/build.sh" << 'EOF'
#!/bin/bash
set -e

echo "Downloading dependencies..."
go mod tidy

echo "Building WASM plugin..."
GOOS=wasip1 GOARCH=wasm go build -buildmode=c-shared -o main.wasm ./

echo "Build complete: main.wasm"
ls -lh main.wasm
EOF
chmod +x "${PLUGIN_DIR}/build.sh"

# Generate push script
cat > "${PLUGIN_DIR}/push.sh" << 'EOF'
#!/bin/bash
set -e

REGISTRY="${1:-}"
PLUGIN_NAME=$(basename "$(pwd)")

if [ -z "$REGISTRY" ]; then
    echo "Usage: $0 <registry-url>"
    echo ""
    echo "Example:"
    echo "  $0 registry.cn-hangzhou.aliyuncs.com/my-plugins"
    echo ""
    echo "Note: You must login to the registry first:"
    echo "  docker login registry.cn-hangzhou.aliyuncs.com"
    exit 1
fi

# Extract registry host for login check
REGISTRY_HOST=$(echo "${REGISTRY}" | cut -d'/' -f1)

# Verify docker login (non-interactive — exit with clear message if not logged in)
if ! docker info 2>/dev/null | grep -q "${REGISTRY_HOST}"; then
    echo "Warning: You may need to login to the registry first:" >&2
    echo "  docker login ${REGISTRY_HOST}" >&2
fi

IMAGE="${REGISTRY}/higress-wasm-${PLUGIN_NAME}:v1"

echo "Building OCI image: ${IMAGE}"
echo "  (FROM scratch + main.wasm → OCI-compliant image for APIG gateway)"
docker build -t "${IMAGE}" .

echo "Pushing to registry..."
docker push "${IMAGE}"

echo ""
echo "✓ Image pushed: ${IMAGE}"
echo ""
echo "Use this OCI URL in your Ingress wasmplugin annotation:"
echo "  \"url\": \"oci://${IMAGE}\""
echo ""
echo "Note: The APIG gateway pulls images via VPC. Ensure this registry"
echo "is accessible from the gateway's VPC network."
EOF
chmod +x "${PLUGIN_DIR}/push.sh"

# Generate annotation template JSON
cat > "${PLUGIN_DIR}/wasmplugin-annotation.json" << EOF
{
  "apiVersion": "extensions.istio.io/v1alpha1",
  "kind": "WasmPlugin",
  "metadata": {
    "name": "INGRESS_NAME-wasmplugin"
  },
  "spec": {
    "imagePullPolicy": "Always",
    "phase": "UNSPECIFIED_PHASE",
    "pluginConfig": {
      "_rules_": [
        {
          "TODO": "Replace with your plugin config"
        }
      ]
    },
    "priority": 100,
    "url": "oci://YOUR_REGISTRY/higress-wasm-${PLUGIN_NAME}:v1"
  }
}
EOF

echo -e "\n${GREEN}✓ Plugin scaffold generated at: ${PLUGIN_DIR} (type: ${PLUGIN_TYPE})${NC}"
echo ""
echo "Files created:"
echo "  - ${PLUGIN_DIR}/main.go                      (plugin source)"
echo "  - ${PLUGIN_DIR}/go.mod                       (Go module)"
echo "  - ${PLUGIN_DIR}/Dockerfile                   (OCI image)"
echo "  - ${PLUGIN_DIR}/build.sh                     (build script)"
echo "  - ${PLUGIN_DIR}/push.sh                      (push to registry)"
echo "  - ${PLUGIN_DIR}/wasmplugin-annotation.json   (Ingress annotation template)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. cd ${PLUGIN_DIR}"
echo "2. Edit main.go to implement your logic"
echo "3. Run: ./build.sh"
echo "4. Run: ./push.sh <your-registry-url>"
echo "5. Copy wasmplugin-annotation.json content into your Ingress annotation"
echo "6. Deploy: kubectl apply -f migrated-ingress.yaml"
