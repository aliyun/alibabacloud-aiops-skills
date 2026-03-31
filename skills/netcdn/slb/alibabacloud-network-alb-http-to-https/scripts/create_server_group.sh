#!/usr/bin/env bash
# Create an empty ALB server group for HTTP listener placeholder via aliyun CLI.
# Usage: bash create_server_group.sh --region cn-hangzhou --name http-placeholder --vpc-id vpc-xxx

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: create_server_group.sh --region REGION --name NAME --vpc-id VPC_ID [OPTIONS]

Create an empty server group. Used as a placeholder DefaultAction target for
HTTP listeners that only serve redirect rules.

Required:
  --region      Region ID (e.g. cn-hangzhou)
  --name        Server group name (2-128 chars)
  --vpc-id      VPC ID (must match the ALB instance's VPC)

Optional:
  --dry-run     Only precheck
  --json        Output raw JSON response
  --output      Write output to file
  -h, --help    Show this help

Examples:
  bash create_server_group.sh --region cn-hangzhou --name http-placeholder --vpc-id vpc-xxx
EOF
    exit 0
}

REGION=""
NAME=""
VPC_ID=""
DRY_RUN=false
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)    REGION="$2"; shift 2 ;;
        --name)      NAME="$2"; shift 2 ;;
        --vpc-id)    VPC_ID="$2"; shift 2 ;;
        --dry-run)   DRY_RUN=true; shift ;;
        --json)      JSON_OUTPUT=true; shift ;;
        --output)    OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)   usage ;;
        *)           echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION"
require_arg "--name" "$NAME"
require_arg "--vpc-id" "$VPC_ID"
require_prefix "--vpc-id" "$VPC_ID" "vpc-"

HEALTH_CHECK_CONFIG='{"HealthCheckEnabled":false}'
STICKY_SESSION_CONFIG='{"StickySessionEnabled":false}'

CMD=("${ALIYUN_CMD[@]}" alb create-server-group
    --region "$REGION"
    --server-group-name "$NAME"
    --vpc-id "$VPC_ID"
    --protocol HTTP
    --health-check-config "$HEALTH_CHECK_CONFIG"
    --sticky-session-config "$STICKY_SESSION_CONFIG")

if [[ "$DRY_RUN" == true ]]; then
    echo "Dry run - would create server group:"
    echo "  Name:  $NAME"
    echo "  VpcId: $VPC_ID"
    if DRYRUN_OUTPUT=$(run_api_dry_run "${CMD[@]}" --dry-run true); then
        echo "$DRYRUN_OUTPUT"
        echo "API precheck passed."
    else
        echo "$DRYRUN_OUTPUT"
        echo "API precheck failed (see above)."
    fi
    exit 0
fi

echo "Creating server group '$NAME' ..." >&2

RESULT=$("${CMD[@]}" 2>&1) || {
    echo "Error: Failed to create server group." >&2
    echo "$RESULT" >&2
    exit 1
}

SG_ID=$(printf '%s' "$RESULT" | json_get_field "ServerGroupId" "")

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        echo "Server group created successfully."
        echo "  ServerGroupId: $SG_ID"
        echo "  Name:          $NAME"
    fi
}

write_output "$OUTPUT_FILE" output_result
