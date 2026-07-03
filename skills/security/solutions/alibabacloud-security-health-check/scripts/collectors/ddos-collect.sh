#!/bin/bash
# Alibaba Cloud Security Health Check - DDoS Pro Data Collection
# ================================================================
# Prerequisites:
#   1. aliyun CLI and jq installed
#   2. RAM sub-account configured (AliyunYundunDDoSCooReadOnlyAccess)
#   3. Only supports DDoS Pro (DDoSCoo); if customer uses Native Protection 2.0
#      (ddos basic), fill in the native_protection section from console
# Usage:
#   bash ddos-collect.sh
# Output: ddos-collected.json
# Note: This script only performs read operations; no configuration is modified
# ================================================================

set -e

REGION="${REGION:-cn-hangzhou}"
OUT="ddos-collected.json"

# Generate session-id (UUID v4) for observability tracing
SESSION_ID="${SESSION_ID:-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo unknown)}"

safe_api() {
  local api="$1"
  local fallback="$2"
  shift 2
  aliyun ddoscoo "$api" --region $REGION --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}" "$@" 2>/dev/null || echo "$fallback"
}

echo "[1/8] Querying DDoS Pro instance specs..."
INSTANCES=$(safe_api describe-instances '{"Instances":[]}' --page-size 50)
INSTANCE_ID=$(echo "$INSTANCES" | jq -r '(.Instances // [])[0].InstanceId // empty')

if [ -z "$INSTANCE_ID" ]; then
  echo "No DDoS Pro instance found; only basic fields will be collected"
fi

INSTANCE_SPEC=$(safe_api describe-instance-specs '{"InstanceSpecs":[]}' --instance-ids "[\"$INSTANCE_ID\"]")
ELASTIC_BW=$(echo "$INSTANCE_SPEC" | jq -r '(.InstanceSpecs // [])[0].ElasticBandwidth // 0')
DOMAIN_QUOTA=$(echo "$INSTANCE_SPEC" | jq -r '(.InstanceSpecs // [])[0].DomainLimit // 0')

echo "[2/8] Querying onboarded domains (web services)..."
DOMAINS=$(safe_api describe-domains '{"TotalCount":0,"Domains":[]}' --page-number 1 --page-size 100)
DOMAIN_COUNT=$(echo "$DOMAINS" | jq -r '.TotalCount // 0')

# Domains with health check enabled (domain.HealthCheck != null)
HEALTH_DOMAINS=$(echo "$DOMAINS" | jq -r '[(.Domains // [])[] | select(.HealthCheck != null and .HealthCheck.Type != null)] | length')

echo "[3/8] Querying HTTPS certificate and encrypted back-to-origin..."
HTTPS_DOMAINS=$(echo "$DOMAINS" | jq -r '[(.Domains // [])[] | select(.HttpsExt != null and .Https2Http != true)] | length')
ENCRYPTED_DOMAINS=$(echo "$DOMAINS" | jq -r '[(.Domains // [])[] | select(.HttpsExt != null and .HttpsExt.Http2Enable == true)] | length')

echo "[4/8] Querying custom CC protection rules..."
CC_RULES=$(safe_api describe-web-cc-protect-switch '{"DomainConfigs":[]}' | jq -r '[(.DomainConfigs // [])[] | select(.AiRuleEnable==1 or .CcEnable==1)] | length')

echo "[5/8] Querying port forwarding rules..."
PORT_FWD=$(safe_api describe-port-rules '{"NetworkRules":[]}' --instance-id "$INSTANCE_ID" --page-size 200)
PORT_COUNT=$(echo "$PORT_FWD" | jq -r '(.NetworkRules // []) | length')

echo "[6/8] Querying blacklist/whitelist..."
BLACK=$(safe_api describe-blackhole-status '[]' --instance-ids "[\"$INSTANCE_ID\"]" | jq -r '(. // []) | length')
WHITE=$(safe_api describe-auto-cc-list-count '{"BlackCount":0,"WhiteCount":0}')
BL_TOTAL=$(echo "$WHITE" | jq -r '(.BlackCount // 0) + (.WhiteCount // 0)')

echo "[7/8] Querying origin concealment (Host-to-Origin resolution comparison)..."
# In production, per-domain nslookup comparison is needed; here ProxyTypes field is used as rough check
HIDDEN_COUNT=$(echo "$DOMAINS" | jq -r '[(.Domains // [])[] | select((.RealServers // []) | length > 0)] | length')

# === Manual input section ===
echo ""
echo "The following metrics are not directly exposed by API. Please verify from console:"
read -p "  Total public-facing domains (including those not onboarded to DDoS Pro): " TOTAL_DOMAIN_PUB
read -p "  CC protection current mode [normal/emergency/strict]: " CC_MODE
read -p "  Scrubbing threshold / peak traffic (e.g. biz 50Gbps threshold 90Gbps enter 1.8): " CLEAN_RATIO
read -p "  Native protection bound IPs / IP quota (e.g. 35/50, enter 0/0 if not purchased): " NATIVE_RATIO
read -p "  Geo-blocking policy configured [true/false]: " GEO_BLOCK
read -p "  WebSocket forwarding configured [true/false]: " WS_CONF
read -p "  TCP/UDP proxy configured [true/false]: " TCPUDP_CONF
read -p "  Intelligent protection switch [enabled/disabled]: " INTELLIGENT

NATIVE_BOUND=$(echo "$NATIVE_RATIO" | cut -d/ -f1); NATIVE_QUOTA=$(echo "$NATIVE_RATIO" | cut -d/ -f2)

echo ""
echo "[8/8] Generating output..."
cat > $OUT <<EOF
{
  "metadata": {
    "collected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "region": "$REGION",
    "instance_id": "$INSTANCE_ID"
  },
  "origin_exposure": {
    "TotalDomains": ${TOTAL_DOMAIN_PUB:-0},
    "HiddenOriginCount": $HIDDEN_COUNT
  },
  "cc_protection": {
    "Mode": "${CC_MODE:-normal}"
  },
  "instance": {
    "ElasticBandwidth": $ELASTIC_BW,
    "DomainCount": $DOMAIN_COUNT,
    "DomainQuota": $DOMAIN_QUOTA
  },
  "cleaning_threshold": {
    "BusinessRatio": ${CLEAN_RATIO:-0}
  },
  "custom_rules": {
    "Count": $CC_RULES
  },
  "health_check": {
    "EnabledDomains": $HEALTH_DOMAINS
  },
  "https_origin": {
    "HttpsEnabledDomains": $HTTPS_DOMAINS,
    "EncryptedDomains": $ENCRYPTED_DOMAINS
  },
  "port_forward": {
    "OpenPortCount": $PORT_COUNT
  },
  "native_protection": {
    "BoundIpCount": ${NATIVE_BOUND:-0},
    "IpQuota": ${NATIVE_QUOTA:-0}
  },
  "ip_lists": {
    "TotalEntries": $BL_TOTAL
  },
  "geo_block": {
    "PolicyConfigured": ${GEO_BLOCK:-false}
  },
  "websocket": {
    "Configured": ${WS_CONF:-false}
  },
  "tcp_udp_proxy": {
    "Configured": ${TCPUDP_CONF:-false}
  },
  "intelligent_protection": {
    "Status": "${INTELLIGENT:-disabled}"
  }
}
EOF

echo ""
echo "Collection complete: $OUT"
echo "Please return this file to the security delivery team."
