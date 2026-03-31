#!/bin/bash
# Offline analysis of nginx Ingress YAML files — no kubectl required.
# Classifies annotations into Compatible / Ignorable / Unsupported.
#
# Usage:
#   bash analyze-ingress-offline.sh <ingress.yaml>
#   bash analyze-ingress-offline.sh <ingress.yaml> --json-only
#   bash analyze-ingress-offline.sh --help
#
# Input:  A YAML file containing one or more Kubernetes Ingress resources
# Output: Colored terminal report (stderr) + JSON classification (stdout)
#
# Dependencies: jq (>= 1.6), bash (>= 4.0)
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
    # If neither timeout nor gtimeout is available, continue without timeout
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/annotation-sets.sh"

# ── Help ──────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $(basename "$0") <ingress.yaml> [--json-only]"
    echo ""
    echo "Analyze nginx Ingress YAML files offline and classify annotations."
    echo ""
    echo "Arguments:"
    echo "  <ingress.yaml>   Path to YAML file containing Ingress resources"
    echo "  --json-only      Output only JSON to stdout (suppress terminal report)"
    echo ""
    echo "Output:"
    echo "  stderr: Colored terminal report with per-Ingress classification"
    echo "  stdout: JSON array with structured classification results"
    echo ""
    echo "Dependencies: jq, bash"
    echo "Note: Does NOT require kubectl or cluster access."
    exit 0
fi

# ── Args ──────────────────────────────────────────────────────────────────────
YAML_FILE="${1:-}"
JSON_ONLY=false
if [[ "${2:-}" == "--json-only" ]]; then
    JSON_ONLY=true
fi

if [[ -z "$YAML_FILE" ]]; then
    echo "Error: No YAML file specified." >&2
    echo "  Usage: $(basename "$0") <ingress.yaml>" >&2
    echo "  Expected: Path to a YAML file containing Kubernetes Ingress resources." >&2
    exit 1
fi

if [[ ! -f "$YAML_FILE" ]]; then
    echo "Error: File not found: $YAML_FILE" >&2
    echo "  Expected: A valid file path to a YAML file." >&2
    exit 1
fi

# ── YAML content safety validation ────────────────────────────────────────────
# Reject files that are too large (>10MB) to prevent resource exhaustion
MAX_FILE_SIZE=$((10 * 1024 * 1024))
FILE_SIZE=$(wc -c < "$YAML_FILE" | tr -d ' ')
if [[ "$FILE_SIZE" -gt "$MAX_FILE_SIZE" ]]; then
    echo "Error: File too large (${FILE_SIZE} bytes, max ${MAX_FILE_SIZE} bytes): $YAML_FILE" >&2
    exit 1
fi

# Reject binary files (YAML must be text)
if file "$YAML_FILE" | grep -qv 'text'; then
    echo "Error: File does not appear to be a text file: $YAML_FILE" >&2
    echo "  Expected: A valid YAML text file." >&2
    exit 1
fi

# Reject YAML files containing dangerous patterns (e.g., shell injection via anchors/aliases abuse)
if grep -qE '!!python/|!!ruby/|!!js/|!!perl/' "$YAML_FILE" 2>/dev/null; then
    echo "Error: YAML file contains potentially unsafe language-specific type tags: $YAML_FILE" >&2
    echo "  Only standard Kubernetes YAML is accepted." >&2
    exit 1
fi

if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed." >&2
    echo "  Install: brew install jq (macOS) or apt install jq (Linux)" >&2
    exit 1
fi

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ── Parse YAML ────────────────────────────────────────────────────────────────
INGRESS_JSON=$(convert_yaml_to_json "$YAML_FILE")
ITEM_COUNT=$(echo "$INGRESS_JSON" | jq '.items | length')

if [[ "$ITEM_COUNT" -eq 0 ]]; then
    echo "Error: No Ingress resources found in $YAML_FILE" >&2
    echo "  Expected: YAML file containing resources with kind: Ingress" >&2
    exit 0
fi

# ── Analysis ──────────────────────────────────────────────────────────────────
if [[ "$JSON_ONLY" == false ]]; then
    echo -e "${BLUE}========================================${NC}" >&2
    echo -e "${BLUE}Nginx → APIG Offline Migration Analysis${NC}" >&2
    echo -e "${BLUE}Input file: ${YAML_FILE}${NC}" >&2
    echo -e "${BLUE}========================================${NC}" >&2
    echo "" >&2
    echo -e "${YELLOW}Found ${ITEM_COUNT} Ingress resource(s)${NC}" >&2
    echo "" >&2
fi

COMPATIBLE_COUNT=0
IGNORABLE_COUNT=0
UNSUPPORTED_COUNT=0
JSON_RESULTS="[]"

for i in $(seq 0 $((ITEM_COUNT - 1))); do
    ingress=$(echo "$INGRESS_JSON" | jq -c ".items[$i]")
    NAME=$(echo "$ingress" | jq -r '.metadata.name // "unknown"')
    NS=$(echo "$ingress" | jq -r '.metadata.namespace // "default"')
    INGRESS_CLASS=$(echo "$ingress" | jq -r '.spec.ingressClassName // .metadata.annotations["kubernetes.io/ingress.class"] // "unknown"')

    # Skip already-migrated -apig Ingress
    if [[ "$NAME" == *-apig ]]; then
        continue
    fi

    if [[ "$JSON_ONLY" == false ]]; then
        echo -e "${BLUE}-------------------------------------------${NC}" >&2
        echo -e "${BLUE}Ingress: ${NS}/${NAME}${NC}" >&2
        echo -e "  IngressClass: ${INGRESS_CLASS} → apig" >&2
        echo -e "  New name: ${NAME}-apig" >&2
    fi

    HAS_UNSUPPORTED=false
    HAS_IGNORABLE=false
    KEPT_ANNOS="[]"
    IGNORED_ANNOS="[]"
    UNSUPPORTED_ANNOS="[]"

    while IFS= read -r key; do
        if [[ "$key" == nginx.ingress.kubernetes.io/* ]]; then
            ANNO_NAME="${key#nginx.ingress.kubernetes.io/}"
            VALUE=$(echo "$ingress" | jq -r --arg k "$key" '.metadata.annotations[$k] // ""')

            if annotation_in_set "$ANNO_NAME" "${COMPATIBLE_ANNOTATIONS[@]}"; then
                if [[ "$JSON_ONLY" == false ]]; then
                    echo -e "  ${GREEN}✓ Keep:         $ANNO_NAME${NC} = $VALUE" >&2
                fi
                KEPT_ANNOS=$(echo "$KEPT_ANNOS" | jq --arg n "$ANNO_NAME" --arg v "$VALUE" '. + [{"name": $n, "value": $v}]')
            elif annotation_in_set "$ANNO_NAME" "${IGNORE_ANNOTATIONS[@]}"; then
                HAS_IGNORABLE=true
                if [[ "$JSON_ONLY" == false ]]; then
                    echo -e "  ${YELLOW}○ Ignore:       $ANNO_NAME${NC} = $VALUE (not needed in Envoy)" >&2
                fi
                IGNORED_ANNOS=$(echo "$IGNORED_ANNOS" | jq --arg n "$ANNO_NAME" --arg v "$VALUE" '. + [{"name": $n, "value": $v}]')
            else
                HAS_UNSUPPORTED=true
                if [[ "$JSON_ONLY" == false ]]; then
                    echo -e "  ${RED}✗ Unsupported:  $ANNO_NAME${NC} = $VALUE (needs WasmPlugin)" >&2
                fi
                UNSUPPORTED_ANNOS=$(echo "$UNSUPPORTED_ANNOS" | jq --arg n "$ANNO_NAME" --arg v "$VALUE" '. + [{"name": $n, "value": $v}]')
            fi
        fi
    done < <(echo "$ingress" | jq -r '.metadata.annotations // {} | keys[]')

    # Determine status
    if [[ "$HAS_UNSUPPORTED" == true ]]; then
        STATUS="unsupported"
        UNSUPPORTED_COUNT=$((UNSUPPORTED_COUNT + 1))
        if [[ "$JSON_ONLY" == false ]]; then
            echo -e "\n  ${RED}Status: Has unsupported annotations — needs WasmPlugin${NC}" >&2
        fi
    elif [[ "$HAS_IGNORABLE" == true ]]; then
        STATUS="ignorable"
        IGNORABLE_COUNT=$((IGNORABLE_COUNT + 1))
        if [[ "$JSON_ONLY" == false ]]; then
            echo -e "\n  ${YELLOW}Status: Has ignorable annotations — safe to remove, no replacement needed${NC}" >&2
        fi
    else
        STATUS="compatible"
        COMPATIBLE_COUNT=$((COMPATIBLE_COUNT + 1))
        if [[ "$JSON_ONLY" == false ]]; then
            echo -e "\n  ${GREEN}Status: Fully compatible — direct copy${NC}" >&2
        fi
    fi

    if [[ "$JSON_ONLY" == false ]]; then
        echo "" >&2
    fi

    INGRESS_RESULT=$(jq -n \
        --arg name "$NAME" \
        --arg ns "$NS" \
        --arg class "$INGRESS_CLASS" \
        --arg status "$STATUS" \
        --argjson kept "$KEPT_ANNOS" \
        --argjson ignored "$IGNORED_ANNOS" \
        --argjson unsupported "$UNSUPPORTED_ANNOS" \
        '{name: $name, namespace: $ns, ingressClass: $class, status: $status, kept: $kept, ignored: $ignored, unsupported: $unsupported}')
    JSON_RESULTS=$(echo "$JSON_RESULTS" | jq --argjson item "$INGRESS_RESULT" '. + [$item]')
done

# ── Summary ───────────────────────────────────────────────────────────────────
if [[ "$JSON_ONLY" == false ]]; then
    echo -e "${BLUE}========================================${NC}" >&2
    echo -e "${BLUE}Summary${NC}" >&2
    echo -e "${BLUE}========================================${NC}" >&2
    echo -e "Total Ingress count: ${ITEM_COUNT}" >&2
    echo -e "  ${GREEN}Fully compatible:${NC}  ${COMPATIBLE_COUNT}" >&2
    echo -e "  ${YELLOW}Has ignorable:${NC}     ${IGNORABLE_COUNT}" >&2
    echo -e "  ${RED}Needs WasmPlugin:${NC}  ${UNSUPPORTED_COUNT}" >&2
    echo "" >&2
    echo -e "Classification (based on annotations/compatible_annotations.go):" >&2
    echo -e "  ${GREEN}✓ Keep${NC}          Compatible (50) — keep in new Ingress" >&2
    echo -e "  ${YELLOW}○ Ignore${NC}        Ignorable (16) — remove annotation, no replacement needed" >&2
    echo -e "  ${RED}✗ Unsupported${NC}   Unsupported (51) — remove annotation, replace with WasmPlugin" >&2
fi

# ── JSON output to stdout ─────────────────────────────────────────────────────
SUMMARY=$(jq -n \
    --argjson total "$ITEM_COUNT" \
    --argjson compatible "$COMPATIBLE_COUNT" \
    --argjson ignorable "$IGNORABLE_COUNT" \
    --argjson unsupported "$UNSUPPORTED_COUNT" \
    '{total: $total, compatible: $compatible, ignorable: $ignorable, unsupported: $unsupported}')

jq -n --argjson summary "$SUMMARY" --argjson ingresses "$JSON_RESULTS" \
    '{summary: $summary, ingresses: $ingresses}'
