#!/usr/bin/env bash
# ensure_ack_prereq.sh — first-use ACK enablement (Skill capability).
#
# Opens ACK Pro+Basic (`open-ack-service --type propayasgo`) and creates missing
# Container Service RAM roles. Idempotent. Does NOT create a cluster, VPC, or ECS.
# Eval hooks also call the same APIs to pre-warm fixtures; Skill must still run
# this on a real first-use account after INSTALL_CONFIRMATION.
#
# Protocol: stdout = single JSON object; stderr = human diagnostics; exit code:
#   0 = service opened or already on, and AliyunCSDefaultRole is present
#   1 = DefaultRole still missing (RAM denied) — Agent uses RAM HITL, not PREFLIGHT_FAILED
#   2 = usage / CLI missing
#
# Usage:
#   bash scripts/ensure_ack_prereq.sh [--region <region>]
set -uo pipefail

REGION=""
while [ $# -gt 0 ]; do
  case "$1" in
    --region) REGION="${2:-}"; shift 2 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if ! command -v aliyun >/dev/null 2>&1; then
  echo "[FAIL] aliyun CLI not found" >&2
  exit 2
fi

json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

UA="${SLS_USER_AGENT:-AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops}"
[ -n "${SKILL_SESSION_ID:-}" ] && UA="$UA session/$SKILL_SESSION_ID"

cs() {
  if [ -n "$REGION" ]; then
    aliyun cs "$@" --region "$REGION" --user-agent "$UA"
  else
    aliyun cs "$@" --user-agent "$UA"
  fi
}

# ---- open-ack-service (idempotent) ----------------------------------------
SERVICE_STATUS="failed"
OPEN_RAW=""
if OPEN_RAW="$(cs open-ack-service --type propayasgo 2>&1)"; then
  SERVICE_STATUS="opened"
  echo "[OK] open-ack-service type=propayasgo accepted" >&2
else
  case "$OPEN_RAW" in
    *ErrorNotEnabled*|*cskpro*|*NotEnabled*)
      SERVICE_STATUS="failed"
      echo "[WARN] open-ack-service did not enable ACK" >&2
      ;;
    *)
      # Already-enabled / conflict / no-op all look like API errors.
      SERVICE_STATUS="already"
      echo "[OK] ACK service already enabled or open-ack-service no-op" >&2
      ;;
  esac
fi

# ---- CS service roles -----------------------------------------------------
CS_TRUST='{"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":["cs.aliyuncs.com"]}}],"Version":"1"}'
declare -a ROLE_JSON
DEFAULT_ROLE_OK=0

while IFS='|' read -r ROLE_NAME POLICY_NAME; do
  [ -n "$ROLE_NAME" ] || continue
  ROLE_STATUS="failed"
  if aliyun ram get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
    ROLE_STATUS="exists"
    echo "[OK] ram role $ROLE_NAME exists" >&2
  else
    echo "[INFO] create ram role $ROLE_NAME" >&2
    if aliyun ram create-role --role-name "$ROLE_NAME" \
         --assume-role-policy-document "$CS_TRUST" \
         --description "ACK managed cluster service role" >/dev/null 2>&1 \
       && aliyun ram attach-policy-to-role --role-name "$ROLE_NAME" \
         --policy-type System --policy-name "$POLICY_NAME" >/dev/null 2>&1; then
      ROLE_STATUS="created"
      echo "[OK] created $ROLE_NAME + $POLICY_NAME" >&2
    elif aliyun ram get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
      ROLE_STATUS="exists"
      echo "[OK] ram role $ROLE_NAME exists after create race" >&2
    else
      ROLE_STATUS="failed"
      echo "[WARN] create-role $ROLE_NAME failed (403 → RAM HITL / 控制台容器服务角色授权)" >&2
    fi
  fi
  ROLE_JSON+=("{\"name\":\"$(json_escape "$ROLE_NAME")\",\"status\":\"$ROLE_STATUS\"}")
  if [ "$ROLE_NAME" = "AliyunCSDefaultRole" ] && [ "$ROLE_STATUS" != "failed" ]; then
    DEFAULT_ROLE_OK=1
  fi
done <<'ROLES'
AliyunCSDefaultRole|AliyunCSDefaultRolePolicy
AliyunCSManagedKubernetesRole|AliyunCSManagedKubernetesRolePolicy
AliyunCSManagedNetworkRole|AliyunCSManagedNetworkRolePolicy
AliyunCSManagedLogRole|AliyunCSManagedLogRolePolicy
AliyunCSManagedCmsRole|AliyunCSManagedCmsRolePolicy
AliyunCSManagedCsiRole|AliyunCSManagedCsiRolePolicy
AliyunCSManagedAutoScalerRole|AliyunCSManagedAutoScalerRolePolicy
ROLES

IFS=,; ROLES_JSON="[${ROLE_JSON[*]}]"; unset IFS
STATUS="ready"
[ "$DEFAULT_ROLE_OK" -eq 1 ] || STATUS="blocked"
printf '{"tool":"ensure_ack_prereq","session_id":"%s","status":"%s","service":"%s","roles":%s}\n' \
  "$(json_escape "${SKILL_SESSION_ID:-}")" "$STATUS" "$SERVICE_STATUS" "$ROLES_JSON"

[ "$DEFAULT_ROLE_OK" -eq 1 ] && exit 0 || exit 1
