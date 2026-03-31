#!/usr/bin/env bash
# List ALB listeners via aliyun CLI.
# Usage: bash list_listeners.sh --region cn-hangzhou --lb-id alb-xxx [--protocol HTTP]

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: list_listeners.sh --region REGION --lb-id LB_ID [--protocol PROTO] [--json] [--output FILE]

List listeners of an ALB instance.

Required:
  --region      Region ID (e.g. cn-hangzhou)
  --lb-id       Load Balancer ID (e.g. alb-xxx)

Optional:
  --protocol    Filter by protocol: HTTP, HTTPS, QUIC
  --json        Output raw JSON response
  --output      Write output to file
  -h, --help    Show this help
EOF
    exit 0
}

REGION=""
LB_ID=""
PROTOCOL=""
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)    REGION="$2"; shift 2 ;;
        --lb-id)     LB_ID="$2"; shift 2 ;;
        --protocol)  PROTOCOL="$2"; shift 2 ;;
        --json)      JSON_OUTPUT=true; shift ;;
        --output)    OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)   usage ;;
        *)           echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION"
require_arg "--lb-id" "$LB_ID"

# Build CLI command (plugin mode)
CMD=("${ALIYUN_CMD[@]}" alb list-listeners
    --region "$REGION"
    --load-balancer-ids "$LB_ID"
    --max-results 100)

if [[ -n "$PROTOCOL" ]]; then
    CMD+=(--listener-protocol "$PROTOCOL")
fi

if [[ "$JSON_OUTPUT" == true ]]; then
    RESULT=$(run_cli "Failed to list listeners." "${CMD[@]}")
else
    RESULT=$(paginate_collection "Listeners" "Failed to list listeners." "${CMD[@]}")
fi

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        if ! echo "$RESULT" | normalize_json_output | python3 -c "
import sys, json
d = json.load(sys.stdin)
listeners = d.get('Listeners', [])
if not listeners:
    print('No listeners found.')
    sys.exit(0)
print(f'Found {len(listeners)} listener(s):')
print()
for ls in listeners:
    lid = ls.get('ListenerId', 'N/A')
    proto = ls.get('ListenerProtocol', 'N/A')
    port = ls.get('ListenerPort', 'N/A')
    status = ls.get('ListenerStatus', 'N/A')
    desc = ls.get('ListenerDescription', '')
    # Check default actions
    actions = ls.get('DefaultActions', [])
    action_summary = ''
    for a in actions:
        atype = a.get('Type', '')
        if atype == 'Redirect':
            rc = a.get('RedirectConfig', {})
            action_summary = f\"Redirect -> {rc.get('Protocol', '?')}:{rc.get('Port', '?')} ({rc.get('HttpRedirectCode', '301')})\"
        elif atype == 'ForwardGroup':
            sgs = a.get('ForwardGroupConfig', {}).get('ServerGroupTuples', [])
            sg_ids = [s.get('ServerGroupId', '?') for s in sgs]
            action_summary = f\"Forward -> {', '.join(sg_ids)}\"
        elif atype == 'FixedResponse':
            fc = a.get('FixedResponseConfig', {})
            action_summary = f\"FixedResponse {fc.get('HttpCode', '?')}\"
        else:
            action_summary = atype
    print(f'  {lid}  {proto}:{port}  [{status}]')
    if desc:
        print(f'    Description: {desc}')
    if action_summary:
        print(f'    DefaultAction: {action_summary}')
    print()
 " 2>/dev/null
        then
            echo "Warning: Failed to parse listener list as JSON. Showing raw output instead." >&2
            echo "$RESULT"
        fi
    fi
}

write_output "$OUTPUT_FILE" output_result
