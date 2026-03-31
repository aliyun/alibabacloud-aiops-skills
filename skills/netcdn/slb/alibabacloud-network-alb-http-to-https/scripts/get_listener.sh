#!/usr/bin/env bash
# Query ALB listener details via aliyun CLI.
# Usage: bash get_listener.sh --region cn-hangzhou --listener-id lsn-xxx

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: get_listener.sh --region REGION --listener-id LSN_ID [--json] [--output FILE]

Query the full configuration of a single ALB listener, including default action,
certificates, ACL, security policy, and timeout settings.

Required:
  --region        Region ID (e.g. cn-hangzhou)
  --listener-id   Listener ID (e.g. lsn-xxx)

Optional:
  --json          Output raw JSON response
  --output        Write output to file
  -h, --help      Show this help
EOF
    exit 0
}

REGION=""
LISTENER_ID=""
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)        REGION="$2"; shift 2 ;;
        --listener-id)   LISTENER_ID="$2"; shift 2 ;;
        --json)          JSON_OUTPUT=true; shift ;;
        --output)        OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)       usage ;;
        *)               echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION"
require_arg "--listener-id" "$LISTENER_ID" "--listener-id lsn-bp1a2b3c4d5e6f"

RESULT=$(run_cli "Failed to query listener." \
    "${ALIYUN_CMD[@]}" alb get-listener-attribute \
    --region "$REGION" \
    --listener-id "$LISTENER_ID")

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        if ! echo "$RESULT" | normalize_json_output | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('=== Listener Details ===')
print(f\"  ListenerId:       {d.get('ListenerId', 'N/A')}\")
print(f\"  Protocol:         {d.get('ListenerProtocol', 'N/A')}\")
print(f\"  Port:             {d.get('ListenerPort', 'N/A')}\")
print(f\"  Status:           {d.get('ListenerStatus', 'N/A')}\")
print(f\"  LoadBalancerId:   {d.get('LoadBalancerId', 'N/A')}\")
print(f\"  Description:      {d.get('ListenerDescription', 'N/A')}\")
print(f\"  IdleTimeout:      {d.get('IdleTimeout', 'N/A')}s\")
print(f\"  RequestTimeout:   {d.get('RequestTimeout', 'N/A')}s\")

# Security policy (HTTPS only)
sp = d.get('SecurityPolicyId')
if sp:
    print(f\"  SecurityPolicy:   {sp}\")

# HTTP/2 (HTTPS only)
h2 = d.get('Http2Enabled')
if h2 is not None:
    print(f\"  HTTP/2:           {h2}\")

# Certificates
certs = d.get('Certificates', [])
if certs:
    print(f\"  Certificates:\")
    for c in certs:
        print(f\"    - {c.get('CertificateId', 'N/A')}\")

# Default actions
actions = d.get('DefaultActions', [])
if actions:
    print(f\"  DefaultActions:\")
    for a in actions:
        atype = a.get('Type', 'N/A')
        print(f\"    - Type: {atype}\")
        if atype == 'Redirect':
            rc = a.get('RedirectConfig', {})
            print(f\"      Protocol: {rc.get('Protocol', 'N/A')}\")
            print(f\"      Port:     {rc.get('Port', 'N/A')}\")
            print(f\"      Code:     {rc.get('HttpRedirectCode', 'N/A')}\")
        elif atype == 'ForwardGroup':
            sgs = a.get('ForwardGroupConfig', {}).get('ServerGroupTuples', [])
            for sg in sgs:
                print(f\"      ServerGroup: {sg.get('ServerGroupId', 'N/A')}\")
        elif atype == 'FixedResponse':
            fc = a.get('FixedResponseConfig', {})
            print(f\"      HttpCode: {fc.get('HttpCode', 'N/A')}\")
            print(f\"      Content:  {fc.get('Content', 'N/A')}\")

# ACL config
acl_config = d.get('AclConfig')
if acl_config:
    print(f\"  ACL:\")
    acl_rels = acl_config.get('AclRelations', [])
    for ar in acl_rels:
        print(f\"    - {ar.get('AclId', 'N/A')} ({ar.get('Status', 'N/A')})\")
    print(f\"    Type: {acl_config.get('AclType', 'N/A')}\")
 " 2>/dev/null
        then
            echo "Warning: Failed to parse listener details as JSON. Showing raw output instead." >&2
            echo "$RESULT"
        fi
    fi
}

write_output "$OUTPUT_FILE" output_result
