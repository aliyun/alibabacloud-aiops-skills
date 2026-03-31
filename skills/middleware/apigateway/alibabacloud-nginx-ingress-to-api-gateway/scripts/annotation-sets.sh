#!/bin/bash
# Shared annotation classification sets.
# Source this file from other scripts to avoid maintaining duplicate lists.
#
# Dependencies: python3 (>= 3.8, with PyYAML >= 5.0) or yq (>= 4.0) for YAML parsing
# Usage: source annotation-sets.sh (library — not meant to be run directly)
if [[ "${1:-}" == "--help" ]]; then
  echo "annotation-sets.sh — shared annotation arrays (COMPATIBLE/IGNORE)."
  echo "Source this file from other scripts: source annotation-sets.sh"
  echo "Provides: COMPATIBLE_ANNOTATIONS[], IGNORE_ANNOTATIONS[], annotation_in_set()"
  exit 0
fi
#
# Source: annotations/compatible_annotations.go (CompatibleAnnotations / IgnoreAnnotations)

COMPATIBLE_ANNOTATIONS=(
    "canary" "canary-by-header" "canary-by-header-value" "canary-by-header-pattern"
    "canary-by-cookie" "canary-weight" "canary-weight-total"
    "enable-cors" "cors-allow-origin" "cors-allow-methods" "cors-allow-headers"
    "cors-expose-headers" "cors-allow-credentials" "cors-max-age"
    "app-root" "temporal-redirect" "permanent-redirect" "permanent-redirect-code"
    "ssl-redirect" "force-ssl-redirect"
    "rewrite-target" "use-regex" "upstream-vhost"
    "proxy-next-upstream-tries" "proxy-next-upstream-timeout" "proxy-next-upstream"
    "default-backend" "custom-http-errors"
    "auth-tls-secret" "ssl-cipher"
    "backend-protocol" "proxy-ssl-secret" "proxy-ssl-verify" "proxy-ssl-name" "proxy-ssl-server-name"
    "load-balance" "upstream-hash-by"
    "affinity" "affinity-mode" "affinity-canary-behavior"
    "session-cookie-name" "session-cookie-path" "session-cookie-max-age" "session-cookie-expires"
    "whitelist-source-range"
    "auth-type" "auth-realm" "auth-secret" "auth-secret-type"
    "server-alias"
)

IGNORE_ANNOTATIONS=(
    "client-body-buffer-size" "proxy-buffering" "proxy-buffers-number" "proxy-buffer-size"
    "proxy-max-temp-file-size" "proxy-read-timeout" "proxy-send-timeout" "proxy-connect-timeout"
    "proxy-http-version" "ssl-prefer-server-ciphers" "proxy-ssl-protocols"
    "preserve-trailing-slash" "http2-push-preload" "proxy-ssl-ciphers"
    "enable-rewrite-log" "proxy-body-size"
)

# Helper: check if annotation is in a given array
# Usage: annotation_in_set "canary" "${COMPATIBLE_ANNOTATIONS[@]}"
annotation_in_set() {
    local needle="$1"
    shift
    for item in "$@"; do
        if [[ "$needle" == "$item" ]]; then
            return 0
        fi
    done
    return 1
}

# Helper: convert multi-doc YAML to JSON (Ingress resources only)
convert_yaml_to_json() {
    local file="$1"
    if command -v python3 &>/dev/null; then
        python3 -c '
import sys, json, yaml

docs = []
with open(sys.argv[1], "r") as f:
    for doc in yaml.safe_load_all(f):
        if doc and isinstance(doc, dict):
            kind = doc.get("kind", "")
            if kind == "Ingress":
                docs.append(doc)
            elif kind == "List" and "items" in doc:
                for item in doc["items"]:
                    if isinstance(item, dict) and item.get("kind") == "Ingress":
                        docs.append(item)

print(json.dumps({"items": docs}))
' "$file" 2>/dev/null && return 0
    fi

    if command -v yq &>/dev/null; then
        yq eval -o=json '[.]' "$file" 2>/dev/null | jq '{items: [.[] | select(.kind == "Ingress")]}' && return 0
    fi

    echo "Error: Cannot parse YAML. Install python3 with PyYAML: pip3 install pyyaml" >&2
    exit 1
}
