#!/bin/bash
# Alibaba Cloud Security Health Check - WAF Data Collection
# ================================================================
# Prerequisites:
#   1. aliyun CLI installed
#   2. RAM sub-account configured (AliyunYundunWAFReadOnlyAccess)
#   3. jq installed
# Usage:
#   bash waf-collect.sh
# Output: waf-collected.json
# Note: This script only performs read operations; no configuration is modified
# ================================================================

set -e

REGION="${REGION:-cn-hangzhou}"
OUT="waf-collected.json"

# Generate session-id (UUID v4) for observability tracing
SESSION_ID="${SESSION_ID:-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo unknown)}"

echo "[1/7] Querying WAF instance..."
INSTANCE=$(aliyun waf-openapi describe-instance --region-id $REGION --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}")
INSTANCE_ID=$(echo $INSTANCE | jq -r '.InstanceId // empty')

if [ -z "$INSTANCE_ID" ]; then
  echo "No WAF 3.0 instance found. If using WAF 2.0, contact delivery team for alternative script."
  exit 1
fi

# === Manual input section (confirm before collection) ===
read -p "Enter total number of public domains (for coverage calculation): " TOTAL_DOMAINS
read -p "Enter total number of public IPs (for origin exposure detection): " TOTAL_PUBLIC_IPS

echo "[2/7] Querying instance details..."
INSTANCE_INFO=$(aliyun waf-openapi describe-instance-info --instance-id $INSTANCE_ID --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}")

echo "[3/7] Querying defense resources..."
DEFENSE_RES=$(aliyun waf-openapi describe-defense-resources --instance-id $INSTANCE_ID --page-number 1 --page-size 200 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}")

echo "[4/7] Querying custom rules..."
DEFENSE_RULES=$(aliyun waf-openapi describe-defense-rules --instance-id $INSTANCE_ID --defense-scene custom_acl --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}" 2>/dev/null || echo '{}')

echo "[5/7] Querying bot protection config..."
BOT_CONFIG=$(aliyun waf-openapi describe-defense-rules --instance-id $INSTANCE_ID --defense-scene anti_scan --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}" 2>/dev/null || echo '{}')

echo "[6/7] Querying log service status..."
LOG_STATUS=$(aliyun waf-openapi describe-waf-source-ip-segment --instance-id $INSTANCE_ID --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}" 2>/dev/null || echo '{"Status":"unknown"}')

echo "[7/7] Generating output..."
cat > $OUT <<EOF
{
  "metadata": {
    "collected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "region": "$REGION",
    "instance_id": "$INSTANCE_ID"
  },
  "client_assets": {
    "TotalDomains": $TOTAL_DOMAINS,
    "TotalPublicIPs": $TOTAL_PUBLIC_IPS
  },
  "instance": $INSTANCE_INFO,
  "defense_resources": $DEFENSE_RES,
  "defense_rules": $DEFENSE_RULES,
  "bot_config": $BOT_CONFIG,
  "log_service": $LOG_STATUS
}
EOF

echo ""
echo "Collection complete: $OUT"
echo "Please return this file to the security delivery team."
