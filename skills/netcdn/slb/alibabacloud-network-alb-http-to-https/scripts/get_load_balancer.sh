#!/usr/bin/env bash
# Query ALB instance details via aliyun CLI.
# Usage: bash get_load_balancer.sh --region cn-hangzhou --lb-id alb-xxx [--json]

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: get_load_balancer.sh --region REGION (--lb-id LB_ID | --lb-name LB_NAME) [--json] [--output FILE]

Query ALB (Application Load Balancer) instance details.

Required:
  --region    Region ID (e.g. cn-hangzhou)
  --lb-id     Load Balancer ID (e.g. alb-xxx)
  --lb-name   Load Balancer name; resolved to ID before querying

Optional:
  --json      Output raw JSON response
  --output    Write output to file
  -h, --help  Show this help
EOF
    exit 0
}

REGION=""
LB_ID=""
LB_NAME=""
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)    REGION="$2"; shift 2 ;;
        --lb-id)     LB_ID="$2"; shift 2 ;;
        --lb-name)   LB_NAME="$2"; shift 2 ;;
        --json)      JSON_OUTPUT=true; shift ;;
        --output)    OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)   usage ;;
        *)           echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION" "--region cn-hangzhou"

if [[ -z "$LB_ID" && -z "$LB_NAME" ]]; then
    echo "Error: --lb-id or --lb-name is required." >&2
    echo "       Example: --lb-id alb-bp1a2b3c4d5e6f" >&2
    echo "       Example: --lb-name my-alb" >&2
    exit 1
fi

resolve_lb_id_by_name() {
    local query_name="$1"
    local lookup_output=""

    lookup_output=$(run_cli "Failed to query ALB instances by name." \
        "${ALIYUN_CMD[@]}" alb list-load-balancers \
        --region "$REGION" \
        --load-balancer-names "$query_name" \
        --max-results 10) || return 1

    printf '%s' "$lookup_output" | python3 -c '
import json
import sys

query_name = sys.argv[1]
data = json.load(sys.stdin)
lbs = data.get("LoadBalancers", [])
exact = [lb for lb in lbs if lb.get("LoadBalancerName") == query_name]

if len(exact) == 1:
    print(exact[0].get("LoadBalancerId", ""))
    sys.exit(0)

if len(exact) > 1:
    print(
        f"Error: Multiple ALB instances matched name \"{query_name}\". Please rerun with --lb-id.",
        file=sys.stderr,
    )
    for lb in exact:
        print(
            f"  {lb.get('LoadBalancerId', 'N/A')} \"{lb.get('LoadBalancerName', 'N/A')}\"",
            file=sys.stderr,
        )
    sys.exit(2)

print("", end="")
' "$query_name"
}

if [[ -n "$LB_NAME" ]]; then
    LB_ID=$(resolve_lb_id_by_name "$LB_NAME") || exit 1
    if [[ -z "$LB_ID" ]]; then
        echo "Error: No ALB instance found with name \"$LB_NAME\" in region \"$REGION\"." >&2
        exit 1
    fi
    echo "Resolved ALB name \"$LB_NAME\" to ID \"$LB_ID\"." >&2
fi

if [[ -n "$LB_ID" && ! "$LB_ID" =~ ^alb- ]]; then
    RESOLVED_FROM_NAME=$(resolve_lb_id_by_name "$LB_ID") || exit 1
    if [[ -n "$RESOLVED_FROM_NAME" ]]; then
        echo "Warning: \"$LB_ID\" does not look like a LoadBalancerId. It matched an ALB name, so the script is using resolved ID \"$RESOLVED_FROM_NAME\"." >&2
        LB_ID="$RESOLVED_FROM_NAME"
    else
        echo "Error: --lb-id usually expects a value like alb-xxxx. \"$LB_ID\" was not found as an ALB name either." >&2
        echo "Hint: use --lb-name if the user gives you an ALB name." >&2
        exit 1
    fi
fi

query_load_balancer() {
    local output=""
    output=$("${ALIYUN_CMD[@]}" alb get-load-balancer-attribute \
        --region "$REGION" \
        --load-balancer-id "$LB_ID" 2>&1) || {
        printf '%s' "$output"
        return 1
    }
    printf '%s' "$output"
}

if ! RESULT=$(query_load_balancer); then
    if [[ -n "$LB_ID" ]]; then
        RESOLVED_FROM_NAME=$(resolve_lb_id_by_name "$LB_ID") || exit 1
        if [[ -n "$RESOLVED_FROM_NAME" ]]; then
            echo "Warning: \"$LB_ID\" was not found as a load balancer ID. It matched an ALB name, so the script is retrying with resolved ID \"$RESOLVED_FROM_NAME\"." >&2
            LB_ID="$RESOLVED_FROM_NAME"
            if ! RESULT=$(query_load_balancer); then
                echo "Error: Failed to query ALB instance." >&2
                echo "$RESULT" >&2
                exit 1
            fi
        else
            echo "Error: Failed to query ALB instance." >&2
            echo "$RESULT" >&2
            echo "Hint: if the user gave you an ALB name instead of a LoadBalancerId, resolve it first with:" >&2
            echo "      bash scripts/list_load_balancers.sh --region $REGION --lb-names \"$LB_ID\"" >&2
            exit 1
        fi
    else
        echo "Error: Failed to query ALB instance." >&2
        echo "$RESULT" >&2
        exit 1
    fi
fi

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        # Extract key fields for human-readable output
        if ! echo "$RESULT" | normalize_json_output | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('=== ALB Instance Details ===')
print(f\"  LoadBalancerId:   {d.get('LoadBalancerId', 'N/A')}\")
print(f\"  Name:             {d.get('LoadBalancerName', 'N/A')}\")
print(f\"  Status:           {d.get('LoadBalancerStatus', 'N/A')}\")
print(f\"  AddressType:      {d.get('AddressType', 'N/A')}\")
print(f\"  DNSName:          {d.get('DNSName', 'N/A')}\")
print(f\"  VpcId:            {d.get('VpcId', 'N/A')}\")
print(f\"  Edition:          {d.get('LoadBalancerEdition', 'N/A')}\")
print(f\"  CreateTime:       {d.get('CreateTime', 'N/A')}\")
zones = d.get('ZoneMappings', [])
if zones:
    print(f\"  Zones:\")
    for z in zones:
        print(f\"    - {z.get('ZoneId', 'N/A')} (vsw: {z.get('VSwitchId', 'N/A')})\")
dp = d.get('DeletionProtectionConfig', {})
if dp:
    print(f\"  DeletionProtection: {dp.get('Enabled', 'N/A')}\")
 " 2>/dev/null
        then
            echo "Warning: Failed to parse ALB details as JSON. Showing raw output instead." >&2
            echo "$RESULT"
        fi
    fi
}

write_output "$OUTPUT_FILE" output_result
