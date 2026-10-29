#!/bin/bash
# ga-diagnostics.sh
# Full-link diagnostics for a Standard GA accelerator.
# Usage: bash ga-diagnostics.sh <GA_ID>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GA_ID="${1:?Please provide GA accelerator ID, usage: bash ga-diagnostics.sh <GA_ID>}"
if ! printf '%s' "$GA_ID" | grep -Eq '^ga-[a-z0-9]+$'; then
  echo "ERROR: invalid GA accelerator ID '$GA_ID' (expected format: ga-<lowercase alphanumeric>)" >&2
  exit 2
fi

if [ -z "${GA_USER_AGENT:-}" ]; then
  # shellcheck source=init-session.sh
  source "$SCRIPT_DIR/init-session.sh"
fi

REGION="cn-hangzhou"

echo "========================================="
echo "  GA full-link diagnostics"
echo "========================================="

# Step 1: Check GA instance state
echo ""
echo "--- [1/4] GA instance state ---"
GA_INFO=$(aliyun ga describe-accelerator \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT")

GA_STATE=$(echo "$GA_INFO" | jq -r '.State')
GA_NAME=$(echo "$GA_INFO" | jq -r '.Name')
DNS_NAME=$(echo "$GA_INFO" | jq -r '.DnsName')

if [ "$GA_STATE" = "active" ]; then
  echo "  [OK] Instance: $GA_ID ($GA_NAME)"
  echo "  [OK] State: $GA_STATE"
  echo "  [OK] CNAME: $DNS_NAME"
else
  echo "  [FAIL] Instance: $GA_ID state abnormal: $GA_STATE"
  echo "  Check whether the instance is normal or overdue."
  exit 1
fi

# Step 2: Check acceleration regions
echo ""
echo "--- [2/4] Acceleration regions ---"
aliyun ga list-ip-sets \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" | jq -r '.IpSets[] |
    if .State == "active" then
      "  [OK] \(.AccelerateRegionId) | Bandwidth: \(.Bandwidth)Mbps | IPs: \(.IpAddressList | join(",")) | State: \(.State)"
    else
      "  [WARN] \(.AccelerateRegionId) | State: \(.State)"
    end'

# Step 3: Check listener states
echo ""
echo "--- [3/4] Listener states ---"
LISTENERS=$(aliyun ga list-listeners \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT")

echo "$LISTENERS" | jq -r '.Listeners[] |
  if .State == "active" then
    "  [OK] \(.ListenerId) | \(.Protocol):\([.PortRanges[] | "\(.FromPort)-\(.ToPort)"] | join(",")) | Type: \(.Type) | State: \(.State)"
  else
    "  [WARN] \(.ListenerId) | State: \(.State)"
  end'

# Step 4: Check endpoint health
echo ""
echo "--- [4/4] Endpoint health ---"
LISTENER_IDS=$(echo "$LISTENERS" | jq -r '.Listeners[]?.ListenerId // empty')

while IFS= read -r LID; do
  [ -n "$LID" ] || continue
  if ! printf '%s' "$LID" | grep -Eq '^lsr-[a-z0-9]+$'; then
    echo "  [WARN] Skipping unexpected listener identifier: $LID"
    continue
  fi
  echo "  Listener: $LID"
  HEALTH=$(aliyun ga get-health-status \
    --biz-region-id "$REGION" \
    --accelerator-id "$GA_ID" \
    --listener-id "$LID" \
    --user-agent "$GA_USER_AGENT" 2>/dev/null) || HEALTH=""

  if [ -n "$HEALTH" ]; then
    OVERALL=$(echo "$HEALTH" | jq -r '.HealthStatus // "unknown"')
    echo "    Overall health: $OVERALL"

    echo "$HEALTH" | jq -r '
      .EndpointGroups[]? |
      "    Endpoint group: \(.EndpointGroupId) [\(.HealthStatus // "unknown")]",
      (.Endpoints[]? |
        if .HealthStatus == "Healthy" then
          "      [OK] \(.Address) (\(.Type)) Weight:\(.Port // "-") State: \(.HealthStatus)"
        else
          "      [FAIL] \(.Address) (\(.Type)) State: \(.HealthStatus) Detail: \(.HealthDetail // "N/A")"
        end
      )'
  else
    echo "    [INFO] Unable to get health status (endpoint group may not be configured)"
  fi
  echo ""
done

echo "========================================="
echo "  Diagnostics complete"
echo "========================================="
