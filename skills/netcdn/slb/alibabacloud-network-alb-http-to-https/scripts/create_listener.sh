#!/usr/bin/env bash
# Create ALB listener (HTTP/HTTPS/QUIC) via aliyun CLI.
# DefaultAction is always ForwardGroup. Use create_rule.sh for Redirect/FixedResponse.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Shared shell helpers keep the wrappers small without hiding ALB-specific checks.
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: create_listener.sh --region REGION --lb-id LB_ID --protocol PROTO --port PORT
       --forward-sg SGP_ID [OPTIONS]

Create an HTTP, HTTPS, or QUIC listener on an ALB instance.
DefaultAction is ForwardGroup (forwarding to a server group).
To add Redirect or FixedResponse behavior, use create_rule.sh after creating the listener.

Required:
  --region          Region ID (e.g. cn-hangzhou)
  --lb-id           Load Balancer ID (e.g. alb-xxx)
  --protocol        Listener protocol: HTTP, HTTPS, QUIC
  --port            Listener port (1-65535)
  --forward-sg      Server group ID for default forwarding action

HTTPS/QUIC options:
  --cert-id         Certificate ID (required for HTTPS/QUIC)
  --security-policy TLS security policy ID
  --http2           Enable HTTP/2: true or false (HTTPS only, default: true)

General options:
  --description     Listener description
  --idle-timeout    Idle timeout in seconds (1-60)
  --request-timeout Request timeout in seconds (1-180)
  --dry-run         Only precheck, do not actually create
  --json            Output raw JSON response
  --output          Write output to file
  -h, --help        Show this help

Examples:
  # HTTP:80 forwarding to server group (then add redirect rules)
  bash create_listener.sh --region cn-hangzhou --lb-id alb-xxx \
      --protocol HTTP --port 80 --forward-sg sgp-xxx

  # HTTPS:443 with certificate
  bash create_listener.sh --region cn-hangzhou --lb-id alb-xxx \
      --protocol HTTPS --port 443 --forward-sg sgp-xxx --cert-id cert-xxx

  # HTTPS with custom TLS policy
  bash create_listener.sh --region cn-hangzhou --lb-id alb-xxx \
      --protocol HTTPS --port 443 --forward-sg sgp-xxx --cert-id cert-xxx \
      --security-policy tls_cipher_policy_1_2
EOF
    exit 0
}

REGION=""
LB_ID=""
PROTOCOL=""
PORT=""
FORWARD_SG=""
CERT_ID=""
SECURITY_POLICY=""
HTTP2=""
DESCRIPTION=""
IDLE_TIMEOUT=""
REQUEST_TIMEOUT=""
DRY_RUN=false
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)            REGION="$2"; shift 2 ;;
        --lb-id)             LB_ID="$2"; shift 2 ;;
        --protocol)          PROTOCOL="$2"; shift 2 ;;
        --port)              PORT="$2"; shift 2 ;;
        --forward-sg)        FORWARD_SG="$2"; shift 2 ;;
        --cert-id)           CERT_ID="$2"; shift 2 ;;
        --security-policy)   SECURITY_POLICY="$2"; shift 2 ;;
        --http2)             HTTP2="$2"; shift 2 ;;
        --description)       DESCRIPTION="$2"; shift 2 ;;
        --idle-timeout)      IDLE_TIMEOUT="$2"; shift 2 ;;
        --request-timeout)   REQUEST_TIMEOUT="$2"; shift 2 ;;
        --dry-run)           DRY_RUN=true; shift ;;
        --json)              JSON_OUTPUT=true; shift ;;
        --output)            OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)           usage ;;
        *)                   echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION"
require_arg "--lb-id" "$LB_ID"
require_arg "--protocol" "$PROTOCOL"
require_arg "--port" "$PORT"
require_arg "--forward-sg" "$FORWARD_SG"

require_prefix "--lb-id" "$LB_ID" "alb-"

if [[ "$PROTOCOL" != "HTTP" && "$PROTOCOL" != "HTTPS" && "$PROTOCOL" != "QUIC" ]]; then
    echo "Error: --protocol must be HTTP, HTTPS, or QUIC." >&2
    exit 1
fi

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [[ "$PORT" -lt 1 || "$PORT" -gt 65535 ]]; then
    echo "Error: --port must be between 1 and 65535." >&2
    exit 1
fi

if [[ "$PROTOCOL" == "HTTPS" || "$PROTOCOL" == "QUIC" ]] && [[ -z "$CERT_ID" ]]; then
    echo "Error: --cert-id is required for $PROTOCOL listener." >&2
    exit 1
fi

if [[ -n "$HTTP2" && "$PROTOCOL" != "HTTPS" ]]; then
    echo "Error: --http2 is only supported for HTTPS listeners." >&2
    exit 1
fi

if [[ -n "$HTTP2" && "$HTTP2" != "true" && "$HTTP2" != "false" ]]; then
    echo "Error: --http2 must be true or false." >&2
    exit 1
fi

if [[ "$PROTOCOL" == "HTTPS" && -z "$HTTP2" ]]; then
    HTTP2="true"
fi

[[ -z "$DESCRIPTION" ]] && DESCRIPTION="${PROTOCOL}_${PORT}_${FORWARD_SG}"

# --- Pre-check: ALB Active ---
echo "Checking ALB instance $LB_ID ..." >&2
ALB_RESULT=$(run_cli "Failed to query ALB instance $LB_ID." \
    "${ALIYUN_CMD[@]}" alb get-load-balancer-attribute \
    --region "$REGION" \
    --load-balancer-id "$LB_ID")

LB_STATE=$(printf '%s' "$ALB_RESULT" | json_get_field "LoadBalancerStatus" "")
if [[ "$LB_STATE" != "Active" ]]; then
    echo "Error: ALB $LB_ID is not Active (current: $LB_STATE)." >&2
    exit 1
fi

# --- Pre-check: port conflict ---
echo "Checking for existing listener on port $PORT ..." >&2
EXISTING=$(paginate_collection "Listeners" "Failed to query existing listeners on ALB $LB_ID." \
    "${ALIYUN_CMD[@]}" alb list-listeners \
    --region "$REGION" \
    --load-balancer-ids "$LB_ID" \
    --max-results 100)

CONFLICT=$(printf '%s' "$EXISTING" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for ls in d.get('Listeners', []):
        if ls.get('ListenerPort') == $PORT:
            print(f\"{ls.get('ListenerId','?')} ({ls.get('ListenerProtocol','?')}:{ls.get('ListenerPort','?')})\")
            break
except Exception:
    print('parse-error')
" 2>/dev/null || true)

if [[ "$CONFLICT" == "parse-error" ]]; then
    echo "Error: Failed to parse existing listeners on ALB $LB_ID." >&2
    exit 1
fi

if [[ -n "$CONFLICT" ]]; then
    echo "Error: Listener already exists on port $PORT: $CONFLICT" >&2
    exit 1
fi

# --- Build CLI command (plugin mode) ---
DEFAULT_ACTIONS=$(python3 -c '
import json
import sys

print(json.dumps([{
    "Type": "ForwardGroup",
    "ForwardGroupConfig": {
        "ServerGroupTuples": [
            {"ServerGroupId": sys.argv[1]}
        ]
    }
}]))
' "$FORWARD_SG")

CMD=("${ALIYUN_CMD[@]}" alb create-listener
    --region "$REGION"
    --load-balancer-id "$LB_ID"
    --listener-protocol "$PROTOCOL"
    --listener-port "$PORT"
    --default-actions "$DEFAULT_ACTIONS"
    --listener-description "$DESCRIPTION")

if [[ -n "$CERT_ID" ]]; then
    CMD+=(--certificates "CertificateId=$CERT_ID")
fi
[[ -n "$SECURITY_POLICY" ]] && CMD+=(--security-policy-id "$SECURITY_POLICY")
[[ -n "$HTTP2" ]] && CMD+=(--http2-enabled "$HTTP2")
[[ -n "$IDLE_TIMEOUT" ]] && CMD+=(--idle-timeout "$IDLE_TIMEOUT")
[[ -n "$REQUEST_TIMEOUT" ]] && CMD+=(--request-timeout "$REQUEST_TIMEOUT")

# --- Dry run ---
if [[ "$DRY_RUN" == true ]]; then
    echo "Dry run - would create listener:"
    echo "  LB:         $LB_ID"
    echo "  Protocol:   $PROTOCOL"
    echo "  Port:       $PORT"
    echo "  ForwardTo:  $FORWARD_SG"
    [[ -n "$CERT_ID" ]] && echo "  Cert:       $CERT_ID"
    [[ -n "$SECURITY_POLICY" ]] && echo "  TLS:        $SECURITY_POLICY"

    if DRYRUN_OUTPUT=$(run_api_dry_run "${CMD[@]}" --dry-run true); then
        echo "$DRYRUN_OUTPUT"
        echo "API precheck passed."
    else
        echo "$DRYRUN_OUTPUT"
        echo "API precheck failed (see above)."
    fi
    exit 0
fi

# --- Create ---
echo "Creating $PROTOCOL:$PORT listener (Forward -> $FORWARD_SG) ..." >&2

RESULT=$("${CMD[@]}" 2>&1) || {
    echo "Error: Failed to create listener." >&2
    echo "$RESULT" >&2
    exit 1
}

LISTENER_ID=$(printf '%s' "$RESULT" | json_get_field "ListenerId" "")

# --- Wait for Running via polling ---
if [[ -n "$LISTENER_ID" ]]; then
    echo "Waiting for listener $LISTENER_ID to become Running ..." >&2
    if ! WAITER_OUTPUT=$(wait_for_json_field \
        "Listener $LISTENER_ID" \
        "ListenerStatus" \
        "Running" \
        40 \
        3 \
        "Failed to query listener $LISTENER_ID during wait." \
        "${ALIYUN_CMD[@]}" alb get-listener-attribute \
        --region "$REGION" \
        --listener-id "$LISTENER_ID"); then
        exit 1
    fi
fi

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        echo "Listener created successfully."
        echo "  ListenerId: $LISTENER_ID"
        echo "  Protocol:   $PROTOCOL"
        echo "  Port:       $PORT"
        echo "  ForwardTo:  $FORWARD_SG"
    fi
}

write_output "$OUTPUT_FILE" output_result
