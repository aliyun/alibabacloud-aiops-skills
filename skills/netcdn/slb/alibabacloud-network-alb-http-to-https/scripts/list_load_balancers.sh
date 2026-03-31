#!/usr/bin/env bash
# List ALB instances via aliyun CLI.
# Usage: bash list_load_balancers.sh --region cn-hangzhou [--vpc-id vpc-xxx]

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: list_load_balancers.sh --region REGION [OPTIONS]

List ALB (Application Load Balancer) instances in the specified region.

Required:
  --region          Region ID (e.g. cn-hangzhou)

Optional:
  --vpc-id          Filter by VPC ID
  --address-type    Filter by network type: Internet or Intranet
  --status          Filter by status: Active, Provisioning, Configuring, Inactive, CreateFailed
  --lb-ids          Filter by specific ALB IDs (space-separated)
  --lb-names        Filter by ALB names (space-separated)
  --json            Output raw JSON response
  --output          Write output to file
  -h, --help        Show this help

Examples:
  # List all ALB instances in a region
  bash list_load_balancers.sh --region cn-hangzhou

  # Filter by VPC
  bash list_load_balancers.sh --region cn-hangzhou --vpc-id vpc-xxx

  # Filter by network type and status
  bash list_load_balancers.sh --region cn-hangzhou --address-type Internet --status Active

  # Query specific instances
  bash list_load_balancers.sh --region cn-hangzhou --lb-ids alb-aaa alb-bbb

  # Resolve by ALB name
  bash list_load_balancers.sh --region cn-hangzhou --lb-names my-alb
EOF
    exit 0
}

REGION=""
VPC_ID=""
ADDRESS_TYPE=""
STATUS=""
LB_IDS=()
LB_NAMES=()
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)        REGION="$2"; shift 2 ;;
        --vpc-id)        VPC_ID="$2"; shift 2 ;;
        --address-type)  ADDRESS_TYPE="$2"; shift 2 ;;
        --status)        STATUS="$2"; shift 2 ;;
        --lb-ids)        shift; while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do LB_IDS+=("$1"); shift; done ;;
        --lb-names)      shift; while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do LB_NAMES+=("$1"); shift; done ;;
        --json)          JSON_OUTPUT=true; shift ;;
        --output)        OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)       usage ;;
        *)               echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION" "--region cn-hangzhou"

# Build CLI command (plugin mode)
CMD=("${ALIYUN_CMD[@]}" alb list-load-balancers
    --region "$REGION"
    --max-results 100)

if [[ -n "$VPC_ID" ]]; then
    CMD+=(--vpc-ids "$VPC_ID")
fi

if [[ -n "$ADDRESS_TYPE" ]]; then
    CMD+=(--address-type "$ADDRESS_TYPE")
fi

if [[ -n "$STATUS" ]]; then
    CMD+=(--load-balancer-status "$STATUS")
fi

if [[ ${#LB_IDS[@]} -gt 0 ]]; then
    CMD+=(--load-balancer-ids "${LB_IDS[@]}")
fi

if [[ ${#LB_NAMES[@]} -gt 0 ]]; then
    CMD+=(--load-balancer-names "${LB_NAMES[@]}")
fi

if [[ "$JSON_OUTPUT" == true ]]; then
    RESULT=$(run_cli "Failed to list ALB instances." "${CMD[@]}")
else
    RESULT=$(paginate_collection "LoadBalancers" "Failed to list ALB instances." "${CMD[@]}")
fi

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        if ! echo "$RESULT" | normalize_json_output | python3 -c "
import sys, json
d = json.load(sys.stdin)
lbs = d.get('LoadBalancers', [])
if not lbs:
    print('No ALB instances found.')
    sys.exit(0)
print(f'Found {len(lbs)} ALB instance(s):')
print()
for lb in lbs:
    lbid = lb.get('LoadBalancerId', 'N/A')
    name = lb.get('LoadBalancerName', 'N/A')
    status = lb.get('LoadBalancerStatus', 'N/A')
    addr_type = lb.get('AddressType', 'N/A')
    dns = lb.get('DNSName', 'N/A')
    vpc = lb.get('VpcId', 'N/A')
    edition = lb.get('LoadBalancerEdition', 'N/A')
    print(f'  {lbid}  \"{name}\"  [{status}]')
    print(f'    AddressType: {addr_type}    Edition: {edition}')
    print(f'    VpcId:       {vpc}')
    print(f'    DNSName:     {dns}')
    print()
 " 2>/dev/null
        then
            echo "Warning: Failed to parse ALB list as JSON. Showing raw output instead." >&2
            echo "$RESULT"
        fi
    fi
}

write_output "$OUTPUT_FILE" output_result
