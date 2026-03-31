#!/bin/bash
# Offline generation of migrated Ingress data from YAML files — no kubectl required.
# Reads Ingress YAML, classifies annotations, outputs JSON for Agent to generate final YAML.
#
# Usage:
#   bash generate-migrated-ingress-offline.sh <ingress.yaml>
#   bash generate-migrated-ingress-offline.sh --help
#
# Input:  A YAML file containing one or more Kubernetes Ingress resources
# Output: JSON to stdout (one object per Ingress with classified annotations)
#         Progress/status to stderr
#
# Dependencies: jq (>= 1.6), python3 (>= 3.8, with PyYAML >= 5.0) or yq (>= 4.0), bash (>= 4.0)
# Note: This script does NOT require kubectl or cluster access.

set -e

# ── Execution timeout (300 seconds) ──────────────────────────────────────────
SCRIPT_TIMEOUT=${SCRIPT_TIMEOUT:-300}
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/annotation-sets.sh"

# ── Help ──────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $(basename "$0") <ingress.yaml>"
    echo ""
    echo "Generate migrated Ingress data from YAML files (offline)."
    echo ""
    echo "Arguments:"
    echo "  <ingress.yaml>   Path to YAML file containing Ingress resources"
    echo ""
    echo "Output:"
    echo "  stdout: JSON array — each element contains the Ingress spec with"
    echo "          classified annotations (kept/ignored/unsupported)"
    echo "  stderr: Progress messages"
    echo ""
    echo "The Agent uses this JSON output to write final YAML files,"
    echo "injecting higress.io/wasmplugin annotations as needed."
    exit 0
fi

YAML_FILE="${1:-}"

if [[ -z "$YAML_FILE" ]]; then
    echo "Error: No YAML file specified." >&2
    echo "  Usage: $(basename "$0") <ingress.yaml>" >&2
    exit 1
fi

if [[ ! -f "$YAML_FILE" ]]; then
    echo "Error: File not found: $YAML_FILE" >&2
    exit 1
fi

# ── YAML content safety validation ────────────────────────────────────────────
MAX_FILE_SIZE=$((10 * 1024 * 1024))
FILE_SIZE=$(wc -c < "$YAML_FILE" | tr -d ' ')
if [[ "$FILE_SIZE" -gt "$MAX_FILE_SIZE" ]]; then
    echo "Error: File too large (${FILE_SIZE} bytes, max ${MAX_FILE_SIZE} bytes): $YAML_FILE" >&2
    exit 1
fi

if file "$YAML_FILE" | grep -qv 'text'; then
    echo "Error: File does not appear to be a text file: $YAML_FILE" >&2
    exit 1
fi

if grep -qE '!!python/|!!ruby/|!!js/|!!perl/' "$YAML_FILE" 2>/dev/null; then
    echo "Error: YAML file contains potentially unsafe language-specific type tags: $YAML_FILE" >&2
    exit 1
fi

if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed." >&2
    echo "  Install: brew install jq (macOS) or apt install jq (Linux)" >&2
    exit 1
fi

# ── Parse YAML ────────────────────────────────────────────────────────────────
INGRESS_JSON=$(convert_yaml_to_json "$YAML_FILE")
ITEM_COUNT=$(echo "$INGRESS_JSON" | jq '.items | length')

if [[ "$ITEM_COUNT" -eq 0 ]]; then
    echo "Error: No Ingress resources found in $YAML_FILE" >&2
    exit 0
fi

echo "Processing ${ITEM_COUNT} Ingress resources..." >&2

# ── Process each Ingress ──────────────────────────────────────────────────────
RESULTS="[]"

for i in $(seq 0 $((ITEM_COUNT - 1))); do
    ingress=$(echo "$INGRESS_JSON" | jq -c ".items[$i]")
    NAME=$(echo "$ingress" | jq -r '.metadata.name // "unknown"')
    NS=$(echo "$ingress" | jq -r '.metadata.namespace // "default"')

    # Skip already-migrated
    if [[ "$NAME" == *-apig ]]; then
        continue
    fi

    echo "  Processing: ${NS}/${NAME}" >&2

    NEW_ANNOS="{}"
    KEPT="[]"
    STRIPPED="[]"
    UNSUPPORTED_LIST="[]"

    while IFS= read -r key; do
        VALUE=$(echo "$ingress" | jq -r --arg k "$key" '.metadata.annotations[$k] // ""')

        if [[ "$key" == nginx.ingress.kubernetes.io/* ]]; then
            ANNO_NAME="${key#nginx.ingress.kubernetes.io/}"

            if annotation_in_set "$ANNO_NAME" "${COMPATIBLE_ANNOTATIONS[@]}"; then
                NEW_ANNOS=$(echo "$NEW_ANNOS" | jq --arg k "$key" --arg v "$VALUE" '. + {($k): $v}')
                KEPT=$(echo "$KEPT" | jq --arg n "$ANNO_NAME" --arg v "$VALUE" '. + [{"name": $n, "value": $v}]')
            elif annotation_in_set "$ANNO_NAME" "${IGNORE_ANNOTATIONS[@]}"; then
                STRIPPED=$(echo "$STRIPPED" | jq --arg n "$ANNO_NAME" --arg v "$VALUE" --arg r "ignorable" '. + [{"name": $n, "value": $v, "reason": $r}]')
            else
                STRIPPED=$(echo "$STRIPPED" | jq --arg n "$ANNO_NAME" --arg v "$VALUE" --arg r "unsupported" '. + [{"name": $n, "value": $v, "reason": $r}]')
                UNSUPPORTED_LIST=$(echo "$UNSUPPORTED_LIST" | jq --arg n "$ANNO_NAME" --arg v "$VALUE" '. + [{"name": $n, "value": $v}]')
            fi
        else
            # Non-nginx annotations: keep as-is
            NEW_ANNOS=$(echo "$NEW_ANNOS" | jq --arg k "$key" --arg v "$VALUE" '. + {($k): $v}')
        fi
    done < <(echo "$ingress" | jq -r '.metadata.annotations // {} | keys[]')

    TLS=$(echo "$ingress" | jq '.spec.tls // []')
    RULES=$(echo "$ingress" | jq '.spec.rules // []')

    RESULT=$(jq -n \
        --arg name "$NAME" \
        --arg ns "$NS" \
        --arg newName "${NAME}-apig" \
        --argjson annotations "$NEW_ANNOS" \
        --argjson kept "$KEPT" \
        --argjson stripped "$STRIPPED" \
        --argjson unsupported "$UNSUPPORTED_LIST" \
        --argjson tls "$TLS" \
        --argjson rules "$RULES" \
        '{
            originalName: $name,
            namespace: $ns,
            newName: $newName,
            annotations: $annotations,
            kept: $kept,
            stripped: $stripped,
            unsupported: $unsupported,
            tls: $tls,
            rules: $rules
        }')

    RESULTS=$(echo "$RESULTS" | jq --argjson item "$RESULT" '. + [$item]')
done

echo "Done. Processed $ITEM_COUNT Ingress resources." >&2

# Output JSON
echo "$RESULTS" | jq '.'
