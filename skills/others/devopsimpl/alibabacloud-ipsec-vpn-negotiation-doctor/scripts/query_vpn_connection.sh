#!/usr/bin/env bash
# query_vpn_connection.sh - Query VPN tunnel status and config via Alibaba Cloud CLI
#
# Usage: bash query_vpn_connection.sh --vpn-connection-id <vco-xxx> --region <region> [--session-id <uuid>]

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
VPN_CONNECTION_ID=""
REGION=""
SESSION_ID=""

# ========== Argument parsing ==========
usage() {
    cat <<'EOF'
Usage: bash query_vpn_connection.sh --vpn-connection-id <ID> --region <REGION> [--session-id <UUID>]

Required:
  --vpn-connection-id   VPN connection ID (vco-xxxxx)
  --region              Region, e.g. cn-hangzhou

Optional:
  --session-id          Diagnostic session UUID for observability
  --help                Show help
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --vpn-connection-id) VPN_CONNECTION_ID="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
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

# ========== Security check ==========
validate_api_safety "DescribeVpnConnection"

# ========== Execute ==========
echo "=========================================="
echo " VPN Connection Query (DescribeVpnConnection)"
echo "=========================================="
echo " VPN Connection ID: $VPN_CONNECTION_ID"
echo " Region:            $REGION"
echo " Session ID:        $SESSION_ID"
echo "=========================================="
echo ""
echo "[INFO] Querying VPN connection status and config..."

RESPONSE=$(aliyun vpc describe-vpn-connection \
    --biz-region-id "$REGION" \
    --vpn-connection-id "$VPN_CONNECTION_ID" \
    --region "$REGION" \
    --read-timeout 30 \
    --connect-timeout 10 \
    --user-agent "$USER_AGENT" 2>&1) || {
    if echo "$RESPONSE" | grep -q "NotFound"; then
        echo "[NOT FOUND] VPN connection not found: $VPN_CONNECTION_ID in $REGION"
        echo "  Possible causes:"
        echo "    1. Incorrect VPN connection ID"
        echo "    2. Incorrect region — try other regions"
        echo "    3. Incorrect Alibaba Cloud account"
        exit 0
    fi
    echo "[ERROR] aliyun CLI call failed:" >&2
    echo "$RESPONSE" >&2
    exit 1
}

# ========== Parse and format output ==========
echo "$RESPONSE" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f'[ERROR] JSON parse failed: {e}', file=sys.stderr)
    sys.exit(1)

if 'Code' in data and data.get('Code', '') != '':
    code = data.get('Code', '')
    msg  = data.get('Message', 'Unknown error')
    if code == 'InvalidVpnConnectionInstanceId.NotFound':
        print(f'[NOT FOUND] VPN connection not found: {msg}')
        print('  Possible causes:')
        print('    1. Incorrect VPN connection ID')
        print('    2. Incorrect region — try other regions')
        print('    3. Incorrect Alibaba Cloud account')
        sys.exit(0)
    print(f'[ERROR] API error ({code}): {msg}', file=sys.stderr)
    sys.exit(1)

print('[SUCCESS] VPN connection query complete')
print()

print('--- Basic Info ---')
print(f'  VPN Connection ID: {data.get(\"VpnConnectionId\", \"N/A\")}')
print(f'  Name:              {data.get(\"Name\", \"N/A\")}')
print(f'  State:             {data.get(\"State\", \"N/A\")}')
print(f'  Status:            {data.get(\"Status\", \"N/A\")}')
print(f'  VPN Gateway ID:    {data.get(\"VpnGatewayId\", \"N/A\")}')
print(f'  Customer GW ID:    {data.get(\"CustomerGatewayId\", \"N/A\")}')
print(f'  DPD Enabled:       {data.get(\"EnableDpd\", \"N/A\")}')
print(f'  NAT Traversal:     {data.get(\"EnableNatTraversal\", \"N/A\")}')
print()

print('--- Subnet Config ---')
print(f'  Local Subnet:   {data.get(\"LocalSubnet\", \"N/A\")}')
print(f'  Remote Subnet:  {data.get(\"RemoteSubnet\", \"N/A\")}')
print()

ike = data.get('IkeConfig', {})
if ike:
    print('--- IKE Config ---')
    print(f'  IKE Version:    {ike.get(\"IkeVersion\", \"N/A\")}')
    print(f'  IKE Mode:       {ike.get(\"IkeMode\", \"N/A\")}')
    print(f'  Encryption:     {ike.get(\"IkeEncAlg\", \"N/A\")}')
    print(f'  Auth:           {ike.get(\"IkeAuthAlg\", \"N/A\")}')
    print(f'  DH Group:       {ike.get(\"IkePfs\", \"N/A\")}')
    print(f'  Lifetime:       {ike.get(\"IkeLifetime\", \"N/A\")} s')
    print(f'  Local ID:       {ike.get(\"LocalId\", \"N/A\")}')
    print(f'  Remote ID:      {ike.get(\"RemoteId\", \"N/A\")}')
    psk = ike.get('Psk', '')
    if psk:
        print(f'  PSK:            configured (value withheld)')
    else:
        print(f'  PSK:            not configured')
    print()

ipsec = data.get('IpsecConfig', {})
if ipsec:
    print('--- IPSec Config ---')
    print(f'  Encryption:     {ipsec.get(\"IpsecEncAlg\", \"N/A\")}')
    print(f'  Auth:           {ipsec.get(\"IpsecAuthAlg\", \"N/A\")}')
    print(f'  PFS (DH Group): {ipsec.get(\"IpsecPfs\", \"N/A\")}')
    print(f'  Lifetime:       {ipsec.get(\"IpsecLifetime\", \"N/A\")} s')
    print()

tunnels = data.get('TunnelOptionsSpecification', {}).get('TunnelOptions', [])
if tunnels and len(tunnels) > 0:
    print('==========================================')
    print(f' Dual-Tunnel Connection ({len(tunnels)} tunnels)')
    print('==========================================')
    print()
    for i, tunnel in enumerate(tunnels):
        tunnel_id = tunnel.get('TunnelId', 'N/A')
        role = tunnel.get('Role', 'N/A')
        print(f'--- Tunnel {i+1}: {tunnel_id} (Role: {role}) ---')
        print(f'  State:   {tunnel.get(\"State\", \"N/A\")}')
        print(f'  Status:  {tunnel.get(\"Status\", \"N/A\")}')
        t_ike = tunnel.get('TunnelIkeConfig', {})
        if t_ike:
            print(f'  IKE Version: {t_ike.get(\"IkeVersion\", \"N/A\")}')
            print(f'  Encryption:  {t_ike.get(\"IkeEncAlg\", \"N/A\")}')
            print(f'  Auth:        {t_ike.get(\"IkeAuthAlg\", \"N/A\")}')
            print(f'  DH Group:    {t_ike.get(\"IkePfs\", \"N/A\")}')
            print(f'  Local ID:    {t_ike.get(\"LocalId\", \"N/A\")}')
            print(f'  Remote ID:   {t_ike.get(\"RemoteId\", \"N/A\")}')
        t_ipsec = tunnel.get('TunnelIpsecConfig', {})
        if t_ipsec:
            print(f'  IPSec Enc:   {t_ipsec.get(\"IpsecEncAlg\", \"N/A\")}')
            print(f'  IPSec Auth:  {t_ipsec.get(\"IpsecAuthAlg\", \"N/A\")}')
            print(f'  IPSec PFS:   {t_ipsec.get(\"IpsecPfs\", \"N/A\")}')
        print()
else:
    print('--- Single-Tunnel Connection ---')
    print()

hc = data.get('VcoHealthCheck', {})
if hc:
    print('--- Health Check ---')
    print(f'  Enabled: {hc.get(\"Enable\", \"N/A\")}')
    print(f'  Src IP:  {hc.get(\"Sip\", \"N/A\")}')
    print(f'  Dst IP:  {hc.get(\"Dip\", \"N/A\")}')
    print()

" 2>&1

PARSE_EXIT=$?
if [[ $PARSE_EXIT -ne 0 ]]; then
    echo "[ERROR] Response parse failed, raw response:" >&2
    echo "$RESPONSE" | head -c 2000 >&2
    exit 1
fi

echo ""
echo "=========================================="
echo " Query complete"
echo "=========================================="
