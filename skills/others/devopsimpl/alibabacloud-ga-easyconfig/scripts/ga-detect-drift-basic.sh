#!/bin/bash
# ga-detect-drift-basic.sh
# Basic GA accelerator configuration drift detection.
# Usage: bash ga-detect-drift-basic.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${GA_USER_AGENT:-}" ]; then
  # shellcheck source=init-session.sh
  source "$SCRIPT_DIR/init-session.sh"
fi

REGION="cn-hangzhou"
GA_ID=$(jq -r '.accelerator_id // empty' ga-config.json)
if ! printf '%s' "$GA_ID" | grep -Eq '^ga-[a-z0-9]+$'; then
  echo "ERROR: ga-config.json has a missing or invalid accelerator_id ('$GA_ID'); expected ga-<lowercase alphanumeric>" >&2
  exit 2
fi

echo "=== Basic GA configuration drift detection: $GA_ID ==="

DRIFT_COUNT=0

# 1. Accelerator info
LOCAL_NAME=$(jq -r '.accelerator_name' ga-config.json)
CLOUD_NAME=$(aliyun ga get-basic-accelerator --biz-region-id "$REGION" --accelerator-id "$GA_ID" --user-agent "$GA_USER_AGENT" | jq -r '.Name')

if [ "$LOCAL_NAME" != "$CLOUD_NAME" ]; then
  echo "[DRIFT] Accelerator name mismatch: local=$LOCAL_NAME, cloud=$CLOUD_NAME"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

# 2. Acceleration region
LOCAL_IPSET=$(jq '.ip_sets[0] | {accelerate_region_id, bandwidth}' ga-config.json)
IP_SET_ID=$(aliyun ga get-basic-accelerator --biz-region-id "$REGION" --accelerator-id "$GA_ID" --user-agent "$GA_USER_AGENT" | jq -r '.BasicIpSetId // empty')
if ! printf '%s' "$IP_SET_ID" | grep -Eq '^ips-[a-z0-9]+$'; then
  echo "ERROR: cloud response has a missing or invalid BasicIpSetId ('$IP_SET_ID'); expected ips-<lowercase alphanumeric>" >&2
  exit 1
fi
CLOUD_IPSET=$(aliyun ga get-basic-ip-set --biz-region-id "$REGION" --ip-set-id "$IP_SET_ID" --user-agent "$GA_USER_AGENT" | jq '{accelerate_region_id: .AccelerateRegionId, bandwidth: .Bandwidth}')

if [ "$LOCAL_IPSET" != "$CLOUD_IPSET" ]; then
  echo "[DRIFT] Acceleration region mismatch"
  echo "  Local: $LOCAL_IPSET"
  echo "  Cloud: $CLOUD_IPSET"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

# 3. Accelerate IPs
LOCAL_IPS=$(jq '[.ip_sets[0].accelerate_ips[]] | sort' ga-config.json)
CLOUD_IPS=$(aliyun ga list-basic-accelerate-ips --biz-region-id "$REGION" --ip-set-id "$IP_SET_ID" --max-results 50 --user-agent "$GA_USER_AGENT" | jq '[.AccelerateIps[].AccelerateIpAddress] | sort')

if [ "$LOCAL_IPS" != "$CLOUD_IPS" ]; then
  echo "[DRIFT] Accelerate IP mismatch"
  echo "  Local: $LOCAL_IPS"
  echo "  Cloud: $CLOUD_IPS"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

# 4. Endpoint group
LOCAL_EPG=$(jq '.basic_endpoint_group | {endpoint_group_region, endpoint_type, endpoint_address}' ga-config.json)
EPG_ID=$(aliyun ga get-basic-accelerator --biz-region-id "$REGION" --accelerator-id "$GA_ID" --user-agent "$GA_USER_AGENT" | jq -r '.BasicEndpointGroupId // empty')
if ! printf '%s' "$EPG_ID" | grep -Eq '^epg-[a-z0-9]+$'; then
  echo "ERROR: cloud response has a missing or invalid BasicEndpointGroupId ('$EPG_ID'); expected epg-<lowercase alphanumeric>" >&2
  exit 1
fi
CLOUD_EPG=$(aliyun ga get-basic-endpoint-group --biz-region-id "$REGION" --endpoint-group-id "$EPG_ID" --user-agent "$GA_USER_AGENT" | jq '{endpoint_group_region: .EndpointGroupRegion, endpoint_type: .EndpointType, endpoint_address: .EndpointAddress}')

if [ "$LOCAL_EPG" != "$CLOUD_EPG" ]; then
  echo "[DRIFT] Endpoint group mismatch"
  echo "  Local: $LOCAL_EPG"
  echo "  Cloud: $CLOUD_EPG"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

# 5. Endpoints
LOCAL_EPS=$(jq '[.basic_endpoints[] | {endpoint_type, endpoint_address}] | sort_by(.endpoint_address)' ga-config.json)
CLOUD_EPS=$(aliyun ga list-basic-endpoints --biz-region-id "$REGION" --endpoint-group-id "$EPG_ID" --max-results 50 --user-agent "$GA_USER_AGENT" | jq '[.Endpoints[] | {endpoint_type: .EndpointType, endpoint_address: .EndpointAddress}] | sort_by(.endpoint_address)')

if [ "$LOCAL_EPS" != "$CLOUD_EPS" ]; then
  echo "[DRIFT] Endpoint mismatch"
  echo "  Local: $LOCAL_EPS"
  echo "  Cloud: $CLOUD_EPS"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

# 6. Relations
LOCAL_RELATIONS=$(jq '[.accelerate_ip_endpoint_relations[] | {accelerate_ip_id, endpoint_id}] | sort_by(.accelerate_ip_id)' ga-config.json)
CLOUD_RELATIONS=$(aliyun ga list-basic-accelerate-ip-endpoint-relations --biz-region-id "$REGION" --accelerator-id "$GA_ID" --max-results 50 --user-agent "$GA_USER_AGENT" | jq '[.Relations[] | {accelerate_ip_id: .AccelerateIpId, endpoint_id: .EndpointId}] | sort_by(.accelerate_ip_id)')

if [ "$LOCAL_RELATIONS" != "$CLOUD_RELATIONS" ]; then
  echo "[DRIFT] Accelerate IP–endpoint relation mismatch"
  echo "  Local: $LOCAL_RELATIONS"
  echo "  Cloud: $CLOUD_RELATIONS"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

echo ""
if [ $DRIFT_COUNT -eq 0 ]; then
  echo "✅ No configuration drift detected"
else
  echo "⚠️ $DRIFT_COUNT drift item(s) detected"
fi
