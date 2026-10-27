#!/usr/bin/env bash
# fetch_vpn_logs.sh - Fetch VPN negotiation logs via Alibaba Cloud CLI
#
# Usage: bash fetch_vpn_logs.sh --vpn-connection-id <vco-xxx> --region <region> --time <YYYY-MM-DD HH:MM:SS> [OPTIONS]
#
# Options:
#   --vpn-connection-id  Required. VPN connection ID (vco-xxxxx)
#   --region             Required. Region (e.g. cn-hangzhou)
#   --time               Required. Time point, format "YYYY-MM-DD HH:MM:SS"
#   --window             Optional. Time window in minutes, default 60
#   --direction          Optional. both (default) | after | before
#   --tunnel-id          Optional. Tunnel ID (tun-xxxxx) for dual-tunnel
#   --page-size          Optional. Page size 1-50, default 50
#   --session-id         Optional. Diagnostic session UUID for observability

set -euo pipefail

SKILL_NAME="alibabacloud-ipsec-vpn-negotiation-doctor"

# ========== Security check ==========
validate_api_safety() {
    local action="$1"
    if [[ ! "$action" =~ ^[Dd]escribe ]]; then
        echo "[SECURITY ERROR] Blocked: only describe-type API calls are allowed. Blocked: $action" >&2
        exit 1
    fi
}

# ========== Defaults ==========
WINDOW_MINUTES=60
PAGE_SIZE=50
VPN_CONNECTION_ID=""
REGION=""
TIME_POINT=""
TUNNEL_ID=""
DIRECTION="both"
SESSION_ID=""

# ========== Argument parsing ==========
usage() {
    cat <<'EOF'
Usage: bash fetch_vpn_logs.sh --vpn-connection-id <ID> --region <REGION> --time <TIME> [OPTIONS]

Required:
  --vpn-connection-id   VPN connection ID (vco-xxxxx)
  --region              Region, e.g. cn-hangzhou
  --time                Time point, "YYYY-MM-DD HH:MM:SS"

Optional:
  --window              Time window in minutes, default 60
  --direction           both (default) | after | before
  --tunnel-id           Tunnel ID (tun-xxxxx) for dual-tunnel
  --page-size           Page size 1-50, default 50
  --session-id          Diagnostic session UUID for observability
  --help                Show help
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --vpn-connection-id) VPN_CONNECTION_ID="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --time) TIME_POINT="$2"; shift 2 ;;
        --window) WINDOW_MINUTES="$2"; shift 2 ;;
        --tunnel-id) TUNNEL_ID="$2"; shift 2 ;;
        --page-size) PAGE_SIZE="$2"; shift 2 ;;
        --direction) DIRECTION="$2"; shift 2 ;;
        --session-id) SESSION_ID="$2"; shift 2 ;;
        --help|-h) usage ;;
        *) echo "[ERROR] Unknown argument: $1" >&2; usage ;;
    esac
done

# ========== Validation ==========
errors=()
if [[ -z "$VPN_CONNECTION_ID" ]]; then
    errors+=("--vpn-connection-id is required")
elif [[ ! "$VPN_CONNECTION_ID" =~ ^vco-[a-zA-Z0-9]+$ ]]; then
    errors+=("--vpn-connection-id format error, expected vco-xxxxx, got: $VPN_CONNECTION_ID")
fi
if [[ -z "$REGION" ]]; then
    errors+=("--region is required")
fi
if [[ -z "$TIME_POINT" ]]; then
    errors+=("--time is required")
elif [[ ! "$TIME_POINT" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]; then
    errors+=("--time format error, expected 'YYYY-MM-DD HH:MM:SS', got: '$TIME_POINT'")
fi
if [[ ! "$WINDOW_MINUTES" =~ ^[0-9]+$ ]] || [[ "$WINDOW_MINUTES" -lt 1 ]]; then
    errors+=("--window must be a positive integer, got: $WINDOW_MINUTES")
fi
if [[ ! "$PAGE_SIZE" =~ ^[0-9]+$ ]] || [[ "$PAGE_SIZE" -lt 1 ]] || [[ "$PAGE_SIZE" -gt 50 ]]; then
    errors+=("--page-size must be 1-50, got: $PAGE_SIZE")
fi
if [[ -n "$TUNNEL_ID" ]] && [[ ! "$TUNNEL_ID" =~ ^tun-[a-zA-Z0-9]+$ ]]; then
    errors+=("--tunnel-id format error, expected tun-xxxxx, got: $TUNNEL_ID")
fi
if [[ "$DIRECTION" != "both" ]] && [[ "$DIRECTION" != "after" ]] && [[ "$DIRECTION" != "before" ]]; then
    errors+=("--direction must be both/after/before, got: $DIRECTION")
fi
if [[ ${#errors[@]} -gt 0 ]]; then
    echo "[ERROR] Validation failed:" >&2
    for err in "${errors[@]}"; do echo "  - $err" >&2; done
    echo "" >&2; usage
fi

# ========== Check aliyun CLI ==========
if ! command -v aliyun &>/dev/null; then
    echo "[ERROR] aliyun CLI not found. Please install and configure it." >&2
    exit 1
fi

# ========== Build user-agent ==========
# UA format: AlibabaCloud-Agent-Skills/alibabacloud-ipsec-vpn-negotiation-doctor/{session-id} skill-version/{skill-version}
readonly UA_PREFIX="AlibabaCloud-Agent-Skills/alibabacloud-ipsec-vpn-negotiation-doctor"
if [[ -z "$SESSION_ID" ]]; then
    SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || echo "no-session")
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_VERSION=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$SCRIPT_DIR/../references/manifest.json" 2>/dev/null || echo "unknown")
USER_AGENT="${UA_PREFIX}/${SESSION_ID} skill-version/${SKILL_VERSION}"

# ========== Calculate time window ==========
if [[ "$(uname)" == "Darwin" ]]; then
    EPOCH=$(date -j -f "%Y-%m-%d %H:%M:%S" "$TIME_POINT" "+%s" 2>/dev/null)
else
    EPOCH=$(date -d "$TIME_POINT" "+%s" 2>/dev/null)
fi
if [[ -z "$EPOCH" ]]; then
    echo "[ERROR] Failed to parse time: '$TIME_POINT'" >&2
    exit 1
fi

case "$DIRECTION" in
    both)
        HALF_WINDOW=$((WINDOW_MINUTES / 2))
        FROM_TS=$((EPOCH - HALF_WINDOW * 60))
        TO_TS=$((EPOCH + HALF_WINDOW * 60))
        DIRECTION_DESC="±${HALF_WINDOW}min around time point"
        ;;
    after)
        FROM_TS=$EPOCH
        TO_TS=$((EPOCH + WINDOW_MINUTES * 60))
        DIRECTION_DESC="${WINDOW_MINUTES}min after time point"
        ;;
    before)
        FROM_TS=$((EPOCH - WINDOW_MINUTES * 60))
        TO_TS=$EPOCH
        DIRECTION_DESC="${WINDOW_MINUTES}min before time point"
        ;;
esac

if [[ "$(uname)" == "Darwin" ]]; then
    START_TIME_DISPLAY=$(date -j -f "%s" "$FROM_TS" "+%Y-%m-%d %H:%M:%S")
    END_TIME_DISPLAY=$(date -j -f "%s" "$TO_TS" "+%Y-%m-%d %H:%M:%S")
else
    START_TIME_DISPLAY=$(date -d "@$FROM_TS" "+%Y-%m-%d %H:%M:%S")
    END_TIME_DISPLAY=$(date -d "@$TO_TS" "+%Y-%m-%d %H:%M:%S")
fi

# ========== Print query info ==========
echo "=========================================="
echo " VPN Log Query (DescribeVpnConnectionLogs)"
echo "=========================================="
echo " VPN Connection ID: $VPN_CONNECTION_ID"
echo " Region:            $REGION"
echo " Time Point:        $TIME_POINT"
echo " Direction:         $DIRECTION ($DIRECTION_DESC)"
echo " Query Range:       $START_TIME_DISPLAY ~ $END_TIME_DISPLAY"
if [[ -n "$TUNNEL_ID" ]]; then
    echo " Tunnel ID:         $TUNNEL_ID"
fi
echo " Page Size:         $PAGE_SIZE"
echo " Session ID:        $SESSION_ID"
echo "=========================================="
echo ""

# ========== Security check ==========
validate_api_safety "DescribeVpnConnectionLogs"

# ========== Fetch logs in segments ==========
echo "[INFO] Fetching VPN negotiation logs..."

SEGMENT_SECONDS=600
ALL_LOGS=()
SEGMENT_COUNT=0
SEGMENT_FAIL=0
CURRENT_FROM=$FROM_TS

while [[ $CURRENT_FROM -lt $TO_TS ]]; do
    SEGMENT_COUNT=$((SEGMENT_COUNT + 1))
    CURRENT_TO=$((CURRENT_FROM + SEGMENT_SECONDS))
    if [[ $CURRENT_TO -gt $TO_TS ]]; then
        CURRENT_TO=$TO_TS
    fi

    if [[ "$(uname)" == "Darwin" ]]; then
        SEG_FROM_DISP=$(date -j -f "%s" "$CURRENT_FROM" "+%H:%M:%S")
        SEG_TO_DISP=$(date -j -f "%s" "$CURRENT_TO" "+%H:%M:%S")
    else
        SEG_FROM_DISP=$(date -d "@$CURRENT_FROM" "+%H:%M:%S")
        SEG_TO_DISP=$(date -d "@$CURRENT_TO" "+%H:%M:%S")
    fi
    echo "[INFO] Segment ${SEGMENT_COUNT}: ${SEG_FROM_DISP} ~ ${SEG_TO_DISP} ..."

    CLI_ARGS=(
        vpc describe-vpn-connection-logs
        --biz-region-id "$REGION"
        --vpn-connection-id "$VPN_CONNECTION_ID"
        --from "$CURRENT_FROM"
        --to "$CURRENT_TO"
        --page-number 1
        --page-size "$PAGE_SIZE"
        --region "$REGION"
        --read-timeout 30
        --connect-timeout 10
        --user-agent "$USER_AGENT"
    )

    if [[ -n "$TUNNEL_ID" ]]; then
        CLI_ARGS+=(--tunnel-id "$TUNNEL_ID")
    fi

    RESPONSE=$(aliyun "${CLI_ARGS[@]}" 2>&1) || {
        if echo "$RESPONSE" | grep -q "NotFound"; then
            echo ""
            echo "[NOT FOUND] VPN connection not found: $VPN_CONNECTION_ID in $REGION"
            echo "  Possible causes:"
            echo "    1. Incorrect VPN connection ID"
            echo "    2. Incorrect region — try other regions"
            echo "    3. Incorrect Alibaba Cloud account"
            exit 0
        fi
        echo "[WARN] Segment ${SEGMENT_COUNT} failed, skipping: $(echo "$RESPONSE" | head -c 200)" >&2
        SEGMENT_FAIL=$((SEGMENT_FAIL + 1))
        CURRENT_FROM=$CURRENT_TO
        continue
    }

    PARSE_RESULT=$(echo "$RESPONSE" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f'PARSE_ERROR: {e}', file=sys.stderr)
    sys.exit(1)

if 'Code' in data and data['Code'] != '':
    code = data.get('Code', '')
    msg  = data.get('Message', 'Unknown error')
    if code == 'InvalidVpnConnectionInstanceId.NotFound':
        print(f'NOT_FOUND:{msg}')
        sys.exit(0)
    print(f'API_ERROR: {code}: {msg}', file=sys.stderr)
    sys.exit(1)

logs = data.get('Data', {}).get('Logs', [])
count = data.get('Count', 0)
page_size = data.get('PageSize', $PAGE_SIZE)

for log_line in logs:
    if log_line and log_line.strip():
        print(f'LOG:{log_line}')

print(f'META:count={count}|page_size={page_size}|log_count={len(logs)}')
" 2>&1)

    PARSE_EXIT=$?
    if [[ $PARSE_EXIT -ne 0 ]]; then
        echo "[WARN] Segment ${SEGMENT_COUNT} parse failed, skipping" >&2
        SEGMENT_FAIL=$((SEGMENT_FAIL + 1))
        CURRENT_FROM=$CURRENT_TO
        continue
    fi

    # Check for NOT_FOUND — stop all segments immediately
    if echo "$PARSE_RESULT" | grep -q "^NOT_FOUND:"; then
        NOT_FOUND_MSG=$(echo "$PARSE_RESULT" | grep "^NOT_FOUND:" | head -1 | sed 's/^NOT_FOUND://')
        echo ""
        echo "[NOT FOUND] VPN connection not found: ${NOT_FOUND_MSG}"
        echo "  Possible causes:"
        echo "    1. Incorrect VPN connection ID"
        echo "    2. Incorrect region — try other regions"
        echo "    3. Incorrect Alibaba Cloud account"
        echo ""
        echo "=========================================="
        echo " Query complete (resource not found)"
        echo "=========================================="
        exit 0
    fi

    SEG_LOG_COUNT=0
    while IFS= read -r line; do
        if [[ "$line" == LOG:* ]]; then
            entry="${line#LOG:}"
            SEG_LOG_COUNT=$((SEG_LOG_COUNT + 1))
            # De-duplicate lines returned by overlapping segments
            dup=0
            for existing in "${ALL_LOGS[@]+"${ALL_LOGS[@]}"}"; do
                if [[ "$existing" == "$entry" ]]; then dup=1; break; fi
            done
            if [[ $dup -eq 0 ]]; then ALL_LOGS+=("$entry"); fi
        fi
    done <<< "$PARSE_RESULT"

    if [[ "$SEG_LOG_COUNT" -ge "$PAGE_SIZE" ]]; then
        echo "[WARN] Segment ${SEGMENT_COUNT} returned ${SEG_LOG_COUNT} lines (hit PageSize limit), may be truncated" >&2
    fi

    CURRENT_FROM=$CURRENT_TO
done

# ========== Output results ==========
TOTAL_LOGS=${#ALL_LOGS[@]}

echo ""
echo "[SUCCESS] Log query complete"
echo ""
echo "--- Summary ---"
echo "  Total log lines:  $TOTAL_LOGS"
echo "  Segments queried: ${SEGMENT_COUNT} (each ~10min)"
if [[ "$SEGMENT_FAIL" -gt 0 ]]; then
    echo "  Failed segments:  ${SEGMENT_FAIL}"
fi
echo "  Time range:       $START_TIME_DISPLAY ~ $END_TIME_DISPLAY"
echo ""

if [[ "$TOTAL_LOGS" -eq 0 ]]; then
    echo "--- No logs returned ---"
    echo ""
    echo "[Hint] Possible reasons:"
    echo "  1. No negotiation activity in this time range"
    echo "  2. Incorrect region"
    echo "  3. For dual-tunnel connections, try adding --tunnel-id"
    echo "  4. Try expanding the time window with --window"
else
    echo "--- Log Content ---"
    echo ""
    for log_line in "${ALL_LOGS[@]}"; do
        echo "$log_line"
    done

    echo ""
    echo "--- Analysis Hints ---"
    ERROR_COUNT=0
    WARN_COUNT=0
    for log_line in "${ALL_LOGS[@]}"; do
        if echo "$log_line" | grep -qiE "ERR|error|failed|mismatch|rejected|AUTHENTICATION_FAILED"; then
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
        if echo "$log_line" | grep -qiE "WARN|warning|timeout|retransmit"; then
            WARN_COUNT=$((WARN_COUNT + 1))
        fi
    done
    echo "  Error-keyword lines:   $ERROR_COUNT"
    echo "  Warning-keyword lines: $WARN_COUNT"
    echo ""

    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        echo "--- Error Log Sample (first 20) ---"
        SAMPLE_COUNT=0
        for log_line in "${ALL_LOGS[@]}"; do
            if echo "$log_line" | grep -qiE "ERR|error|failed|mismatch|rejected|AUTHENTICATION_FAILED"; then
                echo "  $log_line"
                SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
                if [[ "$SAMPLE_COUNT" -ge 20 ]]; then
                    echo "  ... (more error lines exist)"
                    break
                fi
            fi
        done
    fi
fi

echo ""
echo "=========================================="
echo " Query complete"
echo "=========================================="
