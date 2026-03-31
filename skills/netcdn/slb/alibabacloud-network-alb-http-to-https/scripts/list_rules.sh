#!/usr/bin/env bash
# List ALB forwarding rules via aliyun CLI.
# Usage: bash list_rules.sh --region cn-hangzhou --listener-id lsn-xxx

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: list_rules.sh --region REGION (--listener-id LSN_ID | --lb-id LB_ID | --rule-id RULE_ID) [--json] [--output FILE]

List forwarding rules, or query a single rule by ID.

Required (at least one):
  --region        Region ID (e.g. cn-hangzhou)
  --listener-id   Listener ID (query rules for this listener)
  --lb-id         Load Balancer ID (query rules for all listeners)
  --rule-id       Rule ID (query a single rule's details)

Optional:
  --json          Output raw JSON response
  --output        Write output to file
  -h, --help      Show this help
EOF
    exit 0
}

REGION=""
LISTENER_ID=""
LB_ID=""
RULE_ID=""
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)        REGION="$2"; shift 2 ;;
        --listener-id)   LISTENER_ID="$2"; shift 2 ;;
        --lb-id)         LB_ID="$2"; shift 2 ;;
        --rule-id)       RULE_ID="$2"; shift 2 ;;
        --json)          JSON_OUTPUT=true; shift ;;
        --output)        OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)       usage ;;
        *)               echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION"

if [[ -z "$LISTENER_ID" && -z "$LB_ID" && -z "$RULE_ID" ]]; then
    echo "Error: --listener-id, --lb-id, or --rule-id is required." >&2
    exit 1
fi

# Build CLI command (plugin mode)
CMD=("${ALIYUN_CMD[@]}" alb list-rules
    --region "$REGION"
    --max-results 100)

if [[ -n "$LISTENER_ID" ]]; then
    CMD+=(--listener-ids "$LISTENER_ID")
fi

if [[ -n "$LB_ID" ]]; then
    CMD+=(--load-balancer-ids "$LB_ID")
fi

if [[ -n "$RULE_ID" ]]; then
    CMD+=(--rule-ids "$RULE_ID")
fi

if [[ "$JSON_OUTPUT" == true ]]; then
    RESULT=$(run_cli "Failed to list rules." "${CMD[@]}")
else
    RESULT=$(paginate_collection "Rules" "Failed to list rules." "${CMD[@]}")
fi

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        if ! echo "$RESULT" | normalize_json_output | python3 -c "
import sys, json
d = json.load(sys.stdin)
rules = d.get('Rules', [])
if not rules:
    print('No forwarding rules found.')
    sys.exit(0)
print(f'Found {len(rules)} rule(s):')
print()
for r in rules:
    rid = r.get('RuleId', 'N/A')
    name = r.get('RuleName', 'N/A')
    priority = r.get('Priority', 'N/A')
    status = r.get('RuleStatus', 'N/A')
    lid = r.get('ListenerId', 'N/A')

    # Summarize conditions
    conditions = r.get('RuleConditions', [])
    cond_parts = []
    for c in conditions:
        ctype = c.get('Type', '')
        if ctype == 'Host':
            hosts = c.get('HostConfig', {}).get('Values', [])
            cond_parts.append(f\"Host({', '.join(hosts)})\")
        elif ctype == 'Path':
            paths = c.get('PathConfig', {}).get('Values', [])
            cond_parts.append(f\"Path({', '.join(paths)})\")
        elif ctype == 'Method':
            methods = c.get('MethodConfig', {}).get('Values', [])
            cond_parts.append(f\"Method({', '.join(methods)})\")
        else:
            cond_parts.append(ctype)
    cond_str = ' AND '.join(cond_parts) if cond_parts else 'ALL'

    # Summarize actions
    actions = r.get('RuleActions', [])
    action_parts = []
    for a in sorted(actions, key=lambda x: x.get('Order', 0)):
        atype = a.get('Type', '')
        if atype == 'Redirect':
            rc = a.get('RedirectConfig', {})
            action_parts.append(f\"Redirect -> {rc.get('Protocol', '?')}:{rc.get('Port', '?')}\")
        elif atype == 'ForwardGroup':
            sgs = a.get('ForwardGroupConfig', {}).get('ServerGroupTuples', [])
            sg_ids = [s.get('ServerGroupId', '?') for s in sgs]
            action_parts.append(f\"Forward -> {', '.join(sg_ids)}\")
        elif atype == 'FixedResponse':
            fc = a.get('FixedResponseConfig', {})
            action_parts.append(f\"FixedResponse {fc.get('HttpCode', '?')}\")
        else:
            action_parts.append(atype)
    action_str = '; '.join(action_parts) if action_parts else 'N/A'

    print(f'  [{priority:>5}] {rid}  \"{name}\"  [{status}]')
    print(f'         Listener: {lid}')
    print(f'         Match:    {cond_str}')
    print(f'         Action:   {action_str}')
    print()
 " 2>/dev/null
        then
            echo "Warning: Failed to parse rule list as JSON. Showing raw output instead." >&2
            echo "$RESULT"
        fi
    fi
}

write_output "$OUTPUT_FILE" output_result
