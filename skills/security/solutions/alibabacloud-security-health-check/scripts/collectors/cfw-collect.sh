#!/bin/bash
# Alibaba Cloud Security Health Check - CFW Data Collection
# ================================================================
# Prerequisites:
#   1. aliyun CLI and jq installed
#   2. RAM sub-account configured (AliyunYundunCloudFirewallReadOnlyAccess)
# Usage:
#   bash cfw-collect.sh
# Output: cfw-collected.json
# Note: This script only performs read operations; no configuration is modified
# Some metrics require manual input from console (e.g., smart policy adoption rate)
# ================================================================

set -e

REGION="${REGION:-cn-hangzhou}"
OUT="cfw-collected.json"

# Generate session-id (UUID v4) for observability tracing
SESSION_ID="${SESSION_ID:-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo unknown)}"

safe_api() {
  local api="$1"
  local fallback="$2"
  shift 2
  aliyun cloudfw "$api" --region $REGION --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}" "$@" 2>/dev/null || echo "$fallback"
}

echo "[1/9] Querying internet firewall assets..."
ASSET_LIST=$(safe_api describe-asset-list '{"TotalCount":0,"Assets":[]}' --page-size 200)
TOTAL_PUBIPS=$(echo "$ASSET_LIST" | jq -r '.TotalCount // 0')
PROTECTED_PUBIPS=$(echo "$ASSET_LIST" | jq -r '[(.Assets // [])[] | select(.SyncStatus=="finish" and .ProtectStatus=="open")] | length')

echo "[2/9] Querying IPS rule config..."
IPS_CONF=$(safe_api describe-policy-advanced-config '{"RunMode":"warn","BasicRules":"medium"}')
IPS_MODE=$(echo "$IPS_CONF" | jq -r '.RunMode // "monitor"')
IPS_DEPTH=$(echo "$IPS_CONF" | jq -r '.BasicRules // "balanced"')
# RunMode: warn(observe) / block — normalize mapping
case "$IPS_MODE" in
  warn|observe|monitor) IPS_MODE_NORM="monitor" ;;
  block) IPS_MODE_NORM="block" ;;
  *) IPS_MODE_NORM="$IPS_MODE" ;;
esac

echo "[3/9] Querying north-south access control policies..."
SN_POLICIES=$(safe_api describe-control-policy '{"TotalCount":0}' --direction in --current-page 1 --page-size 200 | jq -r '.TotalCount // 0')

echo "[4/9] Querying VPC firewall list..."
VPC_FW=$(safe_api describe-vpc-firewall-list '{"TotalCount":0,"VpcFirewalls":[]}' --page-size 100)
ENABLED_VPC=$(echo "$VPC_FW" | jq -r '[(.VpcFirewalls // [])[] | select(.FirewallSwitchStatus=="opened")] | length')

echo "[5/9] Querying VPC firewall policy coverage..."
VPC_POLICY=$(safe_api describe-vpc-firewall-control-policy '{"TotalCount":0}' --current-page 1 --page-size 200 | jq -r '.TotalCount // 0')

echo "[6/9] Querying threat intelligence switch..."
TI=$(safe_api describe-user-buy-version '{"InstanceInfos":[]}')
THREAT_INTEL_STATUS=$(echo "$TI" | jq -r '
  if (.InstanceInfos // []) | map(select(.Status=="Normal")) | length > 0
  then "enabled" else "disabled" end')

echo "[7/9] Querying log audit..."
LOG_STATUS=$(safe_api describe-user-asset-ip-traffic-info '{"Status":"unknown"}' | jq -r '"enabled"')

# === Manual input section (metrics not directly exposed or complex to parse) ===
echo ""
echo "The following metrics require console verification:"
read -p "  Total VPC count: " TOTAL_VPCS
read -p "  Outbound detection enabled [enabled/disabled]: " OUTBOUND_PROT
read -p "  VPCs with custom policy / enabled VPCs (e.g. 3/4): " VPC_COVER
read -p "  Policy redundancy ratio (Console > Policy Mgmt > Policy Analysis; e.g. 0.18, enter 0 if unknown): " REDUNDANT
read -p "  Unauthorized access alert enabled [true/false]: " UNAUTH_ALERT
read -p "  Compromised host detection [enabled/disabled]: " COMPROMISED
read -p "  DNS resolution protection [enabled/disabled]: " DNS_PROT
read -p "  Smart policy recommended / accepted (e.g. 60/12, enter 0/0 if unknown): " SMART_RATIO

VPC_COV_N=$(echo "$VPC_COVER" | cut -d/ -f1); VPC_COV_D=$(echo "$VPC_COVER" | cut -d/ -f2)
SMART_REC=$(echo "$SMART_RATIO" | cut -d/ -f1); SMART_ACC=$(echo "$SMART_RATIO" | cut -d/ -f2)

echo ""
echo "[9/9] Generating output..."
cat > $OUT <<EOF
{
  "metadata": {
    "collected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "region": "$REGION"
  },
  "client_assets": {
    "TotalPublicIPs": $TOTAL_PUBIPS,
    "TotalVPCs": ${TOTAL_VPCS:-0}
  },
  "internet_firewall": {
    "TotalPublicIPs": $TOTAL_PUBIPS,
    "ProtectedPublicIPs": $PROTECTED_PUBIPS
  },
  "ips_config": {
    "RuleMode": "$IPS_MODE_NORM",
    "RuleDepth": "$IPS_DEPTH"
  },
  "outbound_protection": {
    "Status": "${OUTBOUND_PROT:-disabled}"
  },
  "policies": {
    "SouthNorthRuleCount": $SN_POLICIES,
    "VpcPolicyCovered": $VPC_POLICY,
    "VPCsWithCustomPolicy": ${VPC_COV_N:-0},
    "RedundantRuleRatio": ${REDUNDANT:-0}
  },
  "threat_intel": {
    "Status": "$THREAT_INTEL_STATUS"
  },
  "alerts": {
    "UnauthAccessAlert": ${UNAUTH_ALERT:-false}
  },
  "vpc_firewall": {
    "EnabledVPCs": $ENABLED_VPC
  },
  "log_service": {
    "Status": "$LOG_STATUS"
  },
  "compromised_detection": {
    "Status": "${COMPROMISED:-disabled}"
  },
  "dns_protection": {
    "Status": "${DNS_PROT:-disabled}"
  },
  "smart_policy": {
    "RecommendedCount": ${SMART_REC:-0},
    "AcceptedCount": ${SMART_ACC:-0}
  }
}
EOF

echo ""
echo "Collection complete: $OUT"
echo "Please return this file to the security delivery team."
