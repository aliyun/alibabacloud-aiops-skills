#!/usr/bin/env bash
# Create ALB forwarding rule via aliyun CLI.
# Supports Redirect, ForwardGroup, and FixedResponse actions.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: create_rule.sh --region REGION --listener-id LSN_ID --name NAME
       --priority N --action-type TYPE [OPTIONS]

Create a forwarding rule on an ALB listener.

Required:
  --region        Region ID (e.g. cn-hangzhou)
  --listener-id   Listener ID (e.g. lsn-xxx)
  --name          Rule name (2-128 chars, letters/digits/._-)
  --priority      Rule priority (1-10000, smaller = higher priority)
  --action-type   Action type: Redirect, ForwardGroup, FixedResponse

Condition options (combine for AND logic, omit all for match-all /*):
  --host          Match hostname (e.g. "api.example.com")
  --path          Match path pattern (e.g. "/login" or "/api/*")
  --method        Match HTTP method (e.g. GET, POST, DELETE)

Redirect options (--action-type Redirect):
  --redirect-proto  Target protocol: HTTPS or HTTP (default: HTTPS)
  --redirect-port   Target port (default: 443)
  --redirect-code   HTTP code: 301 or 302 (default: 301)

ForwardGroup options (--action-type ForwardGroup):
  --forward-sg    Server group ID

FixedResponse options (--action-type FixedResponse):
  --fixed-code    HTTP status code (default: 405)
  --fixed-content Response body
  --fixed-type    Content type (default: text/plain)

General options:
  --dry-run       Only precheck
  --json          Output raw JSON response
  --output        Write output to file
  -h, --help      Show this help

Examples:
  # Redirect all traffic to HTTPS:443
  # First inspect existing priorities:
  #   bash scripts/list_rules.sh --region cn-hangzhou --listener-id lsn-xxx
  bash create_rule.sh --region cn-hangzhou --listener-id lsn-xxx \
      --name "force-https" --priority <AVAILABLE_PRIORITY> --action-type Redirect

  # Redirect specific domain
  bash create_rule.sh --region cn-hangzhou --listener-id lsn-xxx \
      --name "force-https-api" --priority <AVAILABLE_PRIORITY> --action-type Redirect \
      --host "api.example.com"

  # Host-based routing to server group
  bash create_rule.sh --region cn-hangzhou --listener-id lsn-xxx \
      --name "api-route" --priority 20 --action-type ForwardGroup \
      --host "api.example.com" --forward-sg sgp-xxx

  # Block DELETE method
  bash create_rule.sh --region cn-hangzhou --listener-id lsn-xxx \
      --name "block-delete" --priority 5 --action-type FixedResponse \
      --method DELETE --fixed-code 405 --fixed-content "Method Not Allowed"
EOF
    exit 0
}

REGION=""
LISTENER_ID=""
RULE_NAME=""
PRIORITY=""
ACTION_TYPE=""
HOST=""
PATH_PATTERN=""
METHOD=""
REDIRECT_PROTO="HTTPS"
REDIRECT_PORT="443"
REDIRECT_CODE="301"
FORWARD_SG=""
FIXED_CODE="405"
FIXED_CONTENT=""
FIXED_TYPE="text/plain"
DRY_RUN=false
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)          REGION="$2"; shift 2 ;;
        --listener-id)     LISTENER_ID="$2"; shift 2 ;;
        --name)            RULE_NAME="$2"; shift 2 ;;
        --priority)        PRIORITY="$2"; shift 2 ;;
        --action-type)     ACTION_TYPE="$2"; shift 2 ;;
        --host)            HOST="$2"; shift 2 ;;
        --path)            PATH_PATTERN="$2"; shift 2 ;;
        --method)          METHOD="$2"; shift 2 ;;
        --redirect-proto)  REDIRECT_PROTO="$2"; shift 2 ;;
        --redirect-port)   REDIRECT_PORT="$2"; shift 2 ;;
        --redirect-code)   REDIRECT_CODE="$2"; shift 2 ;;
        --forward-sg)      FORWARD_SG="$2"; shift 2 ;;
        --fixed-code)      FIXED_CODE="$2"; shift 2 ;;
        --fixed-content)   FIXED_CONTENT="$2"; shift 2 ;;
        --fixed-type)      FIXED_TYPE="$2"; shift 2 ;;
        --dry-run)         DRY_RUN=true; shift ;;
        --json)            JSON_OUTPUT=true; shift ;;
        --output)          OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)         usage ;;
        *)                 echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION"
require_arg "--listener-id" "$LISTENER_ID"
require_arg "--name" "$RULE_NAME"
require_arg "--priority" "$PRIORITY"
require_arg "--action-type" "$ACTION_TYPE"

if ! [[ "$PRIORITY" =~ ^[0-9]+$ ]] || [[ "$PRIORITY" -lt 1 || "$PRIORITY" -gt 10000 ]]; then
    echo "Error: --priority must be between 1 and 10000." >&2
    exit 1
fi

# --- Pre-check: listener exists and redirect is attached to HTTP listener ---
LISTENER_RESULT=$(run_cli "Failed to query listener $LISTENER_ID." \
    "${ALIYUN_CMD[@]}" alb get-listener-attribute \
    --region "$REGION" \
    --listener-id "$LISTENER_ID")

LISTENER_PROTOCOL=$(printf '%s' "$LISTENER_RESULT" | json_get_field "ListenerProtocol" "")
if [[ "$ACTION_TYPE" == "Redirect" && "$LISTENER_PROTOCOL" != "HTTP" ]]; then
    echo "Error: Redirect rules for HTTP -> HTTPS must be created on an HTTP listener." >&2
    echo "       Listener $LISTENER_ID protocol is: ${LISTENER_PROTOCOL:-unknown}" >&2
    exit 1
fi

# --- Pre-check: priority is available on this listener ---
RULES_RESULT=$(paginate_collection "Rules" "Failed to query existing rules on listener $LISTENER_ID." \
    "${ALIYUN_CMD[@]}" alb list-rules \
    --region "$REGION" \
    --listener-ids "$LISTENER_ID" \
    --max-results 100)

PRIORITY_CONFLICT=$(printf '%s' "$RULES_RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print('parse-error')
    raise SystemExit(0)
for rule in data.get('Rules', []):
    if str(rule.get('Priority', '')) == '$PRIORITY':
        print(f\"{rule.get('RuleId', '?')}::{rule.get('RuleName', '?')}\")
        break
" 2>/dev/null || true)

if [[ "$PRIORITY_CONFLICT" == "parse-error" ]]; then
    echo "Error: Failed to parse existing rules on listener $LISTENER_ID." >&2
    exit 1
fi

if [[ -n "$PRIORITY_CONFLICT" ]]; then
    CONFLICT_RULE_ID="${PRIORITY_CONFLICT%%::*}"
    CONFLICT_RULE_NAME="${PRIORITY_CONFLICT#*::}"
    echo "Error: Priority $PRIORITY is already in use on listener $LISTENER_ID." >&2
    echo "       Existing rule: $CONFLICT_RULE_ID ($CONFLICT_RULE_NAME)" >&2
    echo "       Run: bash scripts/list_rules.sh --region $REGION --listener-id $LISTENER_ID" >&2
    exit 1
fi

# --- Build conditions (plugin list payload) ---
MATCH_DESC_PARTS=()
RULE_CONDITIONS_JSON=$(python3 -c '
import json
import sys

conditions = []
host = sys.argv[1]
path = sys.argv[2]
method = sys.argv[3]

if host:
    conditions.append({
        "Type": "Host",
        "HostConfig": {"Values": [host]},
    })

if path:
    conditions.append({
        "Type": "Path",
        "PathConfig": {"Values": [path]},
    })

if method:
    conditions.append({
        "Type": "Method",
        "MethodConfig": {"Values": [method]},
    })

if not conditions:
    conditions.append({
        "Type": "Path",
        "PathConfig": {"Values": ["/*"]},
    })

print(json.dumps(conditions))
' "$HOST" "$PATH_PATTERN" "$METHOD")

if [[ -n "$HOST" ]]; then
    MATCH_DESC_PARTS+=("Host($HOST)")
fi

if [[ -n "$PATH_PATTERN" ]]; then
    MATCH_DESC_PARTS+=("Path($PATH_PATTERN)")
fi

if [[ -n "$METHOD" ]]; then
    MATCH_DESC_PARTS+=("Method($METHOD)")
fi

# If no conditions specified, match all with path /*
if [[ -z "$HOST" && -z "$PATH_PATTERN" && -z "$METHOD" ]]; then
    MATCH_DESC_PARTS+=("ALL (/*)")
fi

MATCH_DESC=$(IFS=' AND '; echo "${MATCH_DESC_PARTS[*]}")

# --- Build action (plugin list payload) ---
ACTION_DESC=""
RULE_ACTIONS_JSON=""

case "$ACTION_TYPE" in
    Redirect)
        RULE_ACTIONS_JSON=$(python3 -c '
import json
import sys
print(json.dumps([{
    "Type": "Redirect",
    "Order": 1,
    "RedirectConfig": {
        "Protocol": sys.argv[1],
        "Port": sys.argv[2],
        "HttpCode": sys.argv[3],
    }
}]))
' "$REDIRECT_PROTO" "$REDIRECT_PORT" "$REDIRECT_CODE")
        ACTION_DESC="Redirect -> $REDIRECT_PROTO:$REDIRECT_PORT ($REDIRECT_CODE)"
        ;;
    ForwardGroup)
        if [[ -z "$FORWARD_SG" ]]; then
            echo "Error: --forward-sg is required for ForwardGroup action." >&2
            exit 1
        fi
        RULE_ACTIONS_JSON=$(python3 -c '
import json
import sys
print(json.dumps([{
    "Type": "ForwardGroup",
    "Order": 1,
    "ForwardGroupConfig": {
        "ServerGroupTuples": [
            {"ServerGroupId": sys.argv[1]}
        ]
    }
}]))
' "$FORWARD_SG")
        ACTION_DESC="Forward -> $FORWARD_SG"
        ;;
    FixedResponse)
        RULE_ACTIONS_JSON=$(python3 -c '
import json
import sys
print(json.dumps([{
    "Type": "FixedResponse",
    "Order": 1,
    "FixedResponseConfig": {
        "HttpCode": sys.argv[1],
        "Content": sys.argv[2],
        "ContentType": sys.argv[3],
    }
}]))
' "$FIXED_CODE" "$FIXED_CONTENT" "$FIXED_TYPE")
        ACTION_DESC="FixedResponse $FIXED_CODE"
        ;;
    *)
        echo "Error: --action-type must be Redirect, ForwardGroup, or FixedResponse." >&2
        exit 1
        ;;
esac

# --- Build full command ---
CMD=("${ALIYUN_CMD[@]}" alb create-rule
    --region "$REGION"
    --listener-id "$LISTENER_ID"
    --rule-name "$RULE_NAME"
    --priority "$PRIORITY"
    --rule-conditions "$RULE_CONDITIONS_JSON"
    --rule-actions "$RULE_ACTIONS_JSON")

# --- Dry run ---
if [[ "$DRY_RUN" == true ]]; then
    echo "Dry run - would create rule:"
    echo "  Listener: $LISTENER_ID"
    echo "  Name:     $RULE_NAME"
    echo "  Priority: $PRIORITY"
    echo "  Match:    $MATCH_DESC"
    echo "  Action:   $ACTION_DESC"

    if DRYRUN_OUTPUT=$(run_api_dry_run "${CMD[@]}" --dry-run true); then
        echo "$DRYRUN_OUTPUT"
        echo "API precheck passed."
    else
        echo "$DRYRUN_OUTPUT"
        echo "API precheck failed (see above)."
    fi
    exit 0
fi

# --- Create rule ---
echo "Creating rule: $MATCH_DESC -> $ACTION_DESC ..." >&2

RESULT=$("${CMD[@]}" 2>&1) || {
    echo "Error: Failed to create rule." >&2
    echo "$RESULT" >&2
    exit 1
}

RULE_ID=$(printf '%s' "$RESULT" | json_get_field "RuleId" "")

# --- Wait for rule to become Available via polling ---
if [[ -n "$RULE_ID" ]]; then
    echo "Waiting for rule $RULE_ID to become Available ..." >&2
    if ! WAITER_OUTPUT=$(wait_for_json_field \
        "Rule $RULE_ID" \
        "Rules.0.RuleStatus" \
        "Available" \
        40 \
        3 \
        "Failed to query rule $RULE_ID during wait." \
        "${ALIYUN_CMD[@]}" alb list-rules \
        --region "$REGION" \
        --rule-ids "$RULE_ID"); then
        exit 1
    fi
fi

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        echo "Rule created successfully."
        echo "  RuleId:   $RULE_ID"
        echo "  Name:     $RULE_NAME"
        echo "  Priority: $PRIORITY"
        echo "  Match:    $MATCH_DESC"
        echo "  Action:   $ACTION_DESC"
    fi
}

write_output "$OUTPUT_FILE" output_result
