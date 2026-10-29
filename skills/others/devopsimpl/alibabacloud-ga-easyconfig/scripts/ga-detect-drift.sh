#!/bin/bash
# ga-detect-drift.sh
# Standard GA accelerator configuration drift detection.
# Usage: bash ga-detect-drift.sh

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

echo "=== GA configuration drift detection: $GA_ID ==="

DRIFT_COUNT=0

# 1. Accelerator name drift
LOCAL_NAME=$(jq -r '.accelerator_name' ga-config.json)
CLOUD_NAME=$(aliyun ga describe-accelerator --biz-region-id "$REGION" --accelerator-id "$GA_ID" --user-agent "$GA_USER_AGENT" | jq -r '.Name')

if [ "$LOCAL_NAME" != "$CLOUD_NAME" ]; then
  echo "[DRIFT] Accelerator name mismatch"
  echo "  Local: $LOCAL_NAME"
  echo "  Cloud: $CLOUD_NAME"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

# 2. Acceleration region drift
LOCAL_IPSETS=$(jq '[.ip_sets[] | {ip_set_id, accelerate_region_id, bandwidth}] | sort_by(.ip_set_id)' ga-config.json)
CLOUD_IPSETS=$(aliyun ga list-ip-sets --biz-region-id "$REGION" --accelerator-id "$GA_ID" --page-size 50 --user-agent "$GA_USER_AGENT" | jq '[.IpSets[] | {ip_set_id: .IpSetId, accelerate_region_id: .AccelerateRegionId, bandwidth: .Bandwidth}] | sort_by(.ip_set_id)')

if [ "$LOCAL_IPSETS" != "$CLOUD_IPSETS" ]; then
  echo "[DRIFT] Acceleration region mismatch"
  echo "  Local: $LOCAL_IPSETS"
  echo "  Cloud: $CLOUD_IPSETS"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

# 3. Listener drift
LOCAL_LISTENERS=$(jq '[.listeners[] | {listener_id, protocol, port_ranges}] | sort_by(.listener_id)' ga-listeners.json)
CLOUD_LISTENERS=$(aliyun ga list-listeners --biz-region-id "$REGION" --accelerator-id "$GA_ID" --page-size 50 --user-agent "$GA_USER_AGENT" | jq '[.Listeners[] | {listener_id: .ListenerId, protocol: .Protocol, port_ranges: .PortRanges}] | sort_by(.listener_id)')

if [ "$LOCAL_LISTENERS" != "$CLOUD_LISTENERS" ]; then
  echo "[DRIFT] Listener mismatch"
  echo "  Local: $LOCAL_LISTENERS"
  echo "  Cloud: $CLOUD_LISTENERS"
  DRIFT_COUNT=$((DRIFT_COUNT + 1))
fi

# 4. Endpoint group drift
LISTENER_IDS=$(echo "$CLOUD_LISTENERS" | jq -r '.[].listener_id // empty')

while IFS= read -r LID; do
  [ -n "$LID" ] || continue
  if ! printf '%s' "$LID" | grep -Eq '^lsr-[a-z0-9]+$'; then
    echo "[WARN] Skipping unexpected listener identifier from cloud response: $LID"
    continue
  fi
  EPG_CLOUD=$(aliyun ga list-endpoint-groups --biz-region-id "$REGION" --accelerator-id "$GA_ID" --listener-id "$LID" --page-size 50 --user-agent "$GA_USER_AGENT" | jq '[.EndpointGroups[] | {endpoint_group_id: .EndpointGroupId, endpoint_group_region: .EndpointGroupRegion, traffic_percentage: .TrafficPercentage}] | sort_by(.endpoint_group_id)')
  EPG_LOCAL=$(jq --arg lid "$LID" '[.listeners[] | select(.listener_id == $lid) | .endpoint_groups[] | {endpoint_group_id, endpoint_group_region, traffic_percentage}] | sort_by(.endpoint_group_id)' ga-listeners.json)

  if [ "$EPG_LOCAL" != "$EPG_CLOUD" ]; then
    echo "[DRIFT] Endpoint group mismatch for listener $LID"
    echo "  Local: $EPG_LOCAL"
    echo "  Cloud: $EPG_CLOUD"
    DRIFT_COUNT=$((DRIFT_COUNT + 1))
  fi

  # Endpoints
  EPG_IDS=$(echo "$EPG_CLOUD" | jq -r '.[].endpoint_group_id // empty')
  while IFS= read -r EPG_ID; do
    [ -n "$EPG_ID" ] || continue
    if ! printf '%s' "$EPG_ID" | grep -Eq '^epg-[a-z0-9]+$'; then
      echo "[WARN] Skipping unexpected endpoint group identifier from cloud response: $EPG_ID"
      continue
    fi
    EP_CLOUD=$(aliyun ga describe-endpoint-group --biz-region-id "$REGION" --endpoint-group-id "$EPG_ID" --user-agent "$GA_USER_AGENT" | jq '[.EndpointConfigurations[] | {type: .Type, endpoint: .Endpoint, weight: .Weight}] | sort_by(.endpoint)')
    EP_LOCAL=$(jq --arg epg "$EPG_ID" '[.listeners[] | .endpoint_groups[] | select(.endpoint_group_id == $epg) | .endpoints[] | {type, endpoint, weight}] | sort_by(.endpoint)' ga-listeners.json)

    if [ "$EP_LOCAL" != "$EP_CLOUD" ]; then
      echo "[DRIFT] Endpoint mismatch for endpoint group $EPG_ID"
      echo "  Local: $EP_LOCAL"
      echo "  Cloud: $EP_CLOUD"
      DRIFT_COUNT=$((DRIFT_COUNT + 1))
    fi
  done <<< "$EPG_IDS"
done <<< "$LISTENER_IDS"

echo ""
if [ $DRIFT_COUNT -eq 0 ]; then
  echo "✅ No configuration drift detected"
else
  echo "⚠️ $DRIFT_COUNT drift item(s) detected"
  echo "Re-import the configuration or update cloud resources accordingly."
fi
