#!/bin/bash
# ga-validate-deployment.sh
# Post-deployment validation checklist for a Standard GA accelerator.
# Usage: bash ga-validate-deployment.sh <GA_ID>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GA_ID="${1:?Please provide GA accelerator ID, usage: bash ga-validate-deployment.sh <GA_ID>}"
if ! printf '%s' "$GA_ID" | grep -Eq '^ga-[a-z0-9]+$'; then
  echo "ERROR: invalid GA accelerator ID '$GA_ID' (expected format: ga-<lowercase alphanumeric>)" >&2
  exit 2
fi

if [ -z "${GA_USER_AGENT:-}" ]; then
  # shellcheck source=init-session.sh
  source "$SCRIPT_DIR/init-session.sh"
fi

REGION="cn-hangzhou"
PASS=0
FAIL=0

check() {
  local desc="$1"
  local result="$2"
  if [ "$result" = "true" ]; then
    echo "  [PASS] $desc"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $desc"
    FAIL=$((FAIL + 1))
  fi
}

echo "========================================="
echo "  GA deployment validation checklist"
echo "========================================="

# 1. Instance state
GA_STATE=$(aliyun ga describe-accelerator \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq -r '.State')
check "GA instance state is active" "$([ "$GA_STATE" = "active" ] && echo true || echo false)"

# 2. Acceleration regions
IPSET_COUNT=$(aliyun ga list-ip-sets \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq '.IpSets | length')
check "At least 1 acceleration region configured (current: $IPSET_COUNT)" "$([ "$IPSET_COUNT" -ge 1 ] && echo true || echo false)"

IPSET_ACTIVE=$(aliyun ga list-ip-sets \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq '[.IpSets[] | select(.State == "active")] | length')
check "All acceleration regions are active ($IPSET_ACTIVE/$IPSET_COUNT)" "$([ "$IPSET_ACTIVE" -eq "$IPSET_COUNT" ] && echo true || echo false)"

# 3. Listeners
LISTENER_COUNT=$(aliyun ga list-listeners \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq '.Listeners | length')
check "At least 1 listener configured (current: $LISTENER_COUNT)" "$([ "$LISTENER_COUNT" -ge 1 ] && echo true || echo false)"

# 4. Endpoint groups (iterate all listeners)
LISTENERS=$(aliyun ga list-listeners \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq -r '.Listeners[]?.ListenerId // empty')

while IFS= read -r LID; do
  [ -n "$LID" ] || continue
  if ! printf '%s' "$LID" | grep -Eq '^lsr-[a-z0-9]+$'; then
    echo "  [SKIP] Unexpected listener identifier: $LID"
    continue
  fi
  EPG_COUNT=$(aliyun ga list-endpoint-groups \
    --biz-region-id "$REGION" \
    --accelerator-id "$GA_ID" \
    --listener-id "$LID" \
    --user-agent "$GA_USER_AGENT" | jq '.EndpointGroups | length')
  check "Listener $LID has at least 1 endpoint group (current: $EPG_COUNT)" "$([ "$EPG_COUNT" -ge 1 ] && echo true || echo false)"

  # 5. Health status
  HEALTH=$(aliyun ga get-health-status \
    --biz-region-id "$REGION" \
    --accelerator-id "$GA_ID" \
    --listener-id "$LID" \
    --user-agent "$GA_USER_AGENT" 2>/dev/null | jq -r '.HealthStatus // "unknown"')
  check "Listener $LID health status is normal (current: $HEALTH)" "$([ "$HEALTH" = "normal" ] && echo true || echo false)"
done

echo ""
echo "========================================="
echo "  Result: $PASS passed / $FAIL failed"
echo "========================================="

if [ $FAIL -eq 0 ]; then
  echo "  GA deployment validation passed."
else
  echo "  $FAIL check(s) failed. Investigate and retry."
fi
