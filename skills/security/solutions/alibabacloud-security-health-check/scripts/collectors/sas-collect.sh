#!/bin/bash
# Alibaba Cloud Security Health Check - Security Center (SAS) Data Collection
# ================================================================
# Prerequisites:
#   1. aliyun CLI and jq installed
#   2. RAM sub-account configured (AliyunYundunSASReadOnlyAccess)
#   3. Region defaults to cn-hangzhou; override via REGION env variable
# Usage:
#   bash sas-collect.sh
# Output: sas-collected.json
# Note: This script only performs read operations; no configuration is modified
# Some metrics (e.g., alert MTTR, image scan total repos) are not directly
# exposed by SAS API and require manual input from customer
# ================================================================

set -e

REGION="${REGION:-cn-hangzhou}"
OUT="sas-collected.json"

# Generate session-id (UUID v4) for observability tracing
SESSION_ID="${SESSION_ID:-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo unknown)}"

safe_api() {
  local api="$1"
  local fallback="$2"
  shift 2
  aliyun sas "$api" --region $REGION --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-security-health-check/${SESSION_ID}" "$@" 2>/dev/null || echo "$fallback"
}

echo "[1/10] Querying agent asset overview..."
ASSETS=$(safe_api describe-field-statistics '{"AliyunCount":0,"OfflineMachineCount":0}')
TOTAL_AGENT=$(echo "$ASSETS" | jq -r '(.AliyunCount // .TotalCount // 0)')
OFFLINE=$(echo "$ASSETS" | jq -r '(.OfflineMachineCount // 0)')
ONLINE=$((TOTAL_AGENT - OFFLINE))

echo "[2/10] Querying Linux high-risk vulnerability list..."
VULN_TOTAL=$(safe_api describe-vul-list '{"TotalCount":0}' --type sys --necessity asap | jq -r '.TotalCount // 0')
VULN_HANDLED=$(safe_api describe-vul-list '{"TotalCount":0}' --type sys --necessity asap --dealed y | jq -r '.TotalCount // 0')

echo "[3/10] Querying container clusters (KSPM enrollment)..."
CLUSTERS=$(safe_api describe-container-cluster '{"ClusterList":[]}')
TOTAL_CLUSTER=$(echo "$CLUSTERS" | jq -r '(.ClusterList // []) | length')
KSPM_CLUSTER=$(echo "$CLUSTERS" | jq -r '[(.ClusterList // [])[] | select(.KspmStatus=="enabled" or .Status=="running")] | length')

echo "[4/10] Querying baseline check items..."
BASELINE_TOTAL=$(safe_api describe-strategy '{"TotalCount":0}' | jq -r '.TotalCount // 0')
BASELINE_PASS=$(safe_api describe-check-ecs-warnings '{"PassedCount":0}' | jq -r '.PassedCount // 0')

# === Manual input section (metrics not directly exposed by API) ===
echo ""
echo "The following metrics are not directly exposed by SAS API. Please verify from console:"
read -p "  Avg high-severity alert MTTR in last 7 days (hours, Console > Alert Mgmt > Stats): " AVG_MTTR
read -p "  Automated response policy count (Console > Response > Automation Policies): " AUTO_POLICY
read -p "  RASP protected apps / total apps (e.g. 3/12): " RASP_RATIO
read -p "  Tamper-proof protected directory count (Console > Active Defense): " TAMPER_DIRS
read -p "  FIM file integrity monitoring status [enabled/disabled]: " FIM_STATUS
read -p "  Abnormal login policy configured [true/false]: " ABNORMAL_LOGIN
read -p "  Image scan scanned repos / total repos (e.g. 5/8): " IMG_RATIO
read -p "  Application whitelist status [enabled/disabled]: " APPWL_STATUS
read -p "  Honeypot deployed count: " HONEYPOT
read -p "  AK leak monitoring status [enabled/disabled]: " AK_MON
read -p "  Multi-cloud asset synced accounts / total cloud accounts (e.g. 4/6): " ASSET_RATIO

# Parse a/b ratio format
parse_ratio() {
  local s="$1"; local field="$2"
  local n=$(echo "$s" | cut -d/ -f1)
  local d=$(echo "$s" | cut -d/ -f2)
  [ -z "$n" ] && n=0
  [ -z "$d" ] && d=0
  if [ "$field" = "n" ]; then echo "$n"; else echo "$d"; fi
}

RASP_PROT=$(parse_ratio "$RASP_RATIO" n); RASP_TOTAL=$(parse_ratio "$RASP_RATIO" d)
IMG_SCAN=$(parse_ratio "$IMG_RATIO" n);   IMG_TOTAL=$(parse_ratio "$IMG_RATIO" d)
ASSET_SYNC=$(parse_ratio "$ASSET_RATIO" n); ASSET_CLOUD=$(parse_ratio "$ASSET_RATIO" d)

echo ""
echo "[10/10] Generating output..."
cat > $OUT <<EOF
{
  "metadata": {
    "collected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "region": "$REGION"
  },
  "agent_stats": {
    "TotalCount": $TOTAL_AGENT,
    "OnlineCount": $ONLINE
  },
  "vulnerabilities": {
    "linux_high": {
      "TotalCount": $VULN_TOTAL,
      "HandledCount": $VULN_HANDLED
    }
  },
  "container_assets": {
    "TotalClusters": $TOTAL_CLUSTER,
    "KspmEnabledClusters": $KSPM_CLUSTER
  },
  "baseline": {
    "TotalItems": $BASELINE_TOTAL,
    "PassedItems": $BASELINE_PASS
  },
  "alerts": {
    "high": {
      "AvgMttrHours": ${AVG_MTTR:-0}
    }
  },
  "auto_response": {
    "PolicyCount": ${AUTO_POLICY:-0}
  },
  "rasp": {
    "TotalApps": ${RASP_TOTAL:-0},
    "ProtectedApps": ${RASP_PROT:-0}
  },
  "tamper_proof": {
    "ProtectedDirs": ${TAMPER_DIRS:-0}
  },
  "fim": {
    "Status": "${FIM_STATUS:-disabled}"
  },
  "abnormal_login": {
    "PolicyConfigured": ${ABNORMAL_LOGIN:-false}
  },
  "container_image": {
    "TotalRepos": ${IMG_TOTAL:-0},
    "ScannedRepos": ${IMG_SCAN:-0}
  },
  "app_whitelist": {
    "Status": "${APPWL_STATUS:-disabled}"
  },
  "honeypot": {
    "DeployedCount": ${HONEYPOT:-0}
  },
  "ak_leak_monitor": {
    "Status": "${AK_MON:-disabled}"
  },
  "asset_sync": {
    "TotalCloudAccounts": ${ASSET_CLOUD:-0},
    "SyncedAccounts": ${ASSET_SYNC:-0}
  }
}
EOF

echo ""
echo "Collection complete: $OUT"
echo "Please return this file to the security delivery team."
