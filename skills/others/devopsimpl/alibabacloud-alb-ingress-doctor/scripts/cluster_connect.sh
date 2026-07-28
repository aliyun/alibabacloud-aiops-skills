#!/usr/bin/env bash
# ACK Multi-Cluster Connection Verification Script
# Usage: bash cluster_connect.sh [--profile <name>] [--private]
#
# One-click completion: Fetch all clusters → Fetch kubeconfig one by one → Verify connectivity → Output summary

set -euo pipefail

# ============================================================
# Global Configuration
# ============================================================
KUBE_DIR="$HOME/.kube"
KUBECONFIG_PREFIX="ack-"
TEMP_DURATION=4320  # kubeconfig validity (minutes), 3 days
SESSION_ID="$(openssl rand -hex 16)"

# Runtime Variables
PROFILE=""
PRIVATE_IP=false

# ============================================================
# Argument Parsing
# ============================================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            --private)
                PRIVATE_IP=true
                shift
                ;;
            -h|--help)
                echo "ACK Multi-Cluster Connection Verification Tool"
                echo ""
                echo "Usage: bash cluster_connect.sh [options]"
                echo ""
                echo "Options:"
                echo "  --profile <name>  Specify aliyun CLI profile (default to current active profile)"
                echo "  --private         Get intranet apiserver config (default public network)"
                echo "  -h, --help        Show help"
                exit 0
                ;;
            *)
                echo "Unknown argument: $1"
                echo "Run 'bash cluster_connect.sh --help' for help"
                exit 1
                ;;
        esac
    done
}

# ============================================================
# Helper Functions
# ============================================================

# Call aliyun cs API
aliyun_cs() {
    local method="$1"
    local path="$2"
    shift 2

    local cmd=(aliyun cs "$method" "$path" --header "Content-Type=application/json"
        --read-timeout 30 --connect-timeout 10 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-alb-ingress-doctor/${SESSION_ID}")
    if [[ -n "$PROFILE" ]]; then
        cmd+=(--profile "$PROFILE")
    fi
    cmd+=("$@")

    "${cmd[@]}" 2>&1
}

# ============================================================
# Step 1: Check Prerequisites
# ============================================================
check_prerequisites() {
    echo "=== Check Prerequisites ==="
    local has_error=false

    # aliyun CLI
    if command -v aliyun &>/dev/null; then
        local ver
        ver=$(aliyun version 2>/dev/null || echo "unknown")
        echo "[OK] aliyun CLI: ${ver}"
    else
        echo "[FAIL] aliyun CLI not installed"
        echo "  Install: brew install aliyun-cli"
        has_error=true
    fi

    # kubectl
    if command -v kubectl &>/dev/null; then
        local ver
        ver=$(kubectl version --client -o json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('clientVersion',{}).get('gitVersion','unknown'))" 2>/dev/null || echo "unknown")
        echo "[OK] kubectl: ${ver}"
    else
        echo "[FAIL] kubectl not installed"
        has_error=true
    fi

    # python3
    if command -v python3 &>/dev/null; then
        echo "[OK] python3 available"
    else
        echo "[FAIL] python3 not installed"
        has_error=true
    fi

    if [[ "$has_error" == "true" ]]; then
        echo ""
        echo "Please install missing dependencies first"
        exit 1
    fi

    mkdir -p "$KUBE_DIR"
    echo ""
}

# ============================================================
# Step 2: Fetch Cluster List
# ============================================================
fetch_clusters() {
    echo "=== Fetch Cluster List ==="

    local response
    response=$(aliyun_cs GET /api/v1/clusters)

    # Check if API error
    if echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, dict) and 'Code' in data:
        print(f\"API Error: {data.get('Code')} - {data.get('Message','')}\", file=sys.stderr)
        sys.exit(1)
except (json.JSONDecodeError, ValueError):
    print('Response is not valid JSON', file=sys.stderr)
    sys.exit(1)
" 2>&1; then
        : # JSON parsed successfully with no error code
    else
        echo "[FAIL] Failed to fetch cluster list"
        echo "$response" | head -5
        exit 1
    fi

    # Parse cluster info, output list and generate temp file for subsequent use
    CLUSTER_DATA=$(echo "$response" | python3 -c "
import sys, json

data = json.load(sys.stdin)
clusters = data if isinstance(data, list) else data.get('clusters', [])

running = [c for c in clusters if c.get('state') == 'running']

if not running:
    print('No running clusters found', file=sys.stderr)
    sys.exit(1)

print(f'Found {len(running)} running cluster(s):')
for c in running:
    cid = c.get('cluster_id', 'N/A')
    name = c.get('name', 'N/A')
    region = c.get('region_id', 'N/A')
    version = c.get('current_version', 'N/A')
    print(f'  {cid}  {name}  {region}  {version}')

# Output separator followed by machine-readable data
print('---CLUSTER_IDS---')
for c in running:
    print(f\"{c['cluster_id']}|{c.get('name','N/A')}|{c.get('region_id','N/A')}\")
" 2>&1)

    if [[ $? -ne 0 ]]; then
        echo "[FAIL] Failed to parse cluster data"
        echo "$CLUSTER_DATA"
        exit 1
    fi

    # Display human-readable part (macOS head does not support -n -1, use sed to remove the last line)
    echo "$CLUSTER_DATA" | sed -n '1,/^---CLUSTER_IDS---$/p' | sed '$d'
    echo ""
}

# ============================================================
# Step 3 & 4: Fetch kubeconfig and verify connection one by one
# ============================================================
connect_and_verify() {
    echo "=== Fetch kubeconfig and verify connection ==="

    # Extract cluster ID list
    local cluster_lines
    cluster_lines=$(echo "$CLUSTER_DATA" | sed -n '/^---CLUSTER_IDS---$/,$ p' | tail -n +2)

    local total
    total=$(echo "$cluster_lines" | wc -l | tr -d ' ')
    local idx=0
    local success=0
    local failed=0

    # Array for summary
    SUMMARY_LINES=()

    while IFS='|' read -r cluster_id cluster_name cluster_region; do
        idx=$((idx + 1))
        echo "[${idx}/${total}] ${cluster_id} (${cluster_name})"

        local kubeconfig_file="${KUBE_DIR}/${KUBECONFIG_PREFIX}${cluster_id}.yaml"

        # Fetch kubeconfig
        local private_flag="false"
        [[ "$PRIVATE_IP" == "true" ]] && private_flag="true"

        local config_response
        config_response=$(aliyun_cs GET "/k8s/${cluster_id}/user_config" \
            --PrivateIpAddress "$private_flag" --TemporaryDurationMinutes "$TEMP_DURATION")

        # Extract config field from JSON
        local config_content
        config_content=$(echo "$config_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'Code' in data:
        print(f\"ERROR:{data.get('Code')}:{data.get('Message','')}\")
    elif 'config' in data:
        print(data['config'])
    else:
        print('ERROR:UNKNOWN:No config field in response')
except (json.JSONDecodeError, ValueError):
    print('ERROR:PARSE:JSON parse failed')
" 2>&1)

        # Check if error response
        if [[ "$config_content" == ERROR:* ]]; then
            local err_msg="${config_content#ERROR:}"
            echo "  kubeconfig fetch failed: ${err_msg}"
            SUMMARY_LINES+=("${cluster_id}|${cluster_name}|${cluster_region}|${kubeconfig_file}|failed: ${err_msg}")
            failed=$((failed + 1))
            sleep 1
            continue
        fi

        # Save kubeconfig
        echo "$config_content" > "$kubeconfig_file"
        chmod 600 "$kubeconfig_file"
        echo "  kubeconfig saved: ${kubeconfig_file}"

        # Verify connection
        if kubectl --kubeconfig "$kubeconfig_file" cluster-info &>/dev/null; then
            echo "  Connection verification: OK"
            SUMMARY_LINES+=("${cluster_id}|${cluster_name}|${cluster_region}|${kubeconfig_file}|connected")
            success=$((success + 1))
        else
            echo "  Connection verification: FAILED"
            SUMMARY_LINES+=("${cluster_id}|${cluster_name}|${cluster_region}|${kubeconfig_file}|failed: Connection timeout or refused")
            failed=$((failed + 1))
        fi

        echo ""
        sleep 1

    done <<< "$cluster_lines"

    TOTAL_COUNT=$total
    SUCCESS_COUNT=$success
    FAILED_COUNT=$failed
}

# ============================================================
# Step 5: Output Summary
# ============================================================
print_summary() {
    echo "=== Summary ==="
    echo "Total: ${TOTAL_COUNT} cluster(s), ${SUCCESS_COUNT} connected successfully, ${FAILED_COUNT} failed"
    echo ""

    if [[ ${#SUMMARY_LINES[@]} -gt 0 ]]; then
        echo "Switch cluster:"
        for line in "${SUMMARY_LINES[@]}"; do
            IFS='|' read -r cid cname cregion cfile cstatus <<< "$line"
            if [[ "$cstatus" == "connected" ]]; then
                echo "  export KUBECONFIG=${cfile}  # ${cname} (${cregion})"
            fi
        done
    fi
}

# ============================================================
# Main Flow
# ============================================================
main() {
    parse_args "$@"
    check_prerequisites
    fetch_clusters
    connect_and_verify
    print_summary
}

main "$@"
