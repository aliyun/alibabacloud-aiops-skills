#!/usr/bin/env bash
# ensure_ack_prereq.sh — first-use ACK enablement (Skill capability).
#
# Opens ACK Pro+Basic (`open-ack-service --type propayasgo`) and creates missing
# Container Service RAM roles. Idempotent. Does NOT create a cluster, VPC, or ECS.
# Run this on a first-use account after installation has been authorized.
#
# Protocol: stdout = single JSON object; stderr = human diagnostics; exit code:
#   0 = service available and all listed roles have their required policies
#   1 = service or role setup failed — Agent uses the reported failure stage
#   2 = usage / CLI missing
#
# Usage:
#   bash scripts/loongcollector/ensure_ack_prereq.sh [--region <region>] [--profile <name>]
set -uo pipefail

REGION=""
PROFILE=""
require_value() {
  case "${2-}" in
    ""|--*|-h) echo "missing value for $1" >&2; exit 2 ;;
  esac
}

while [ $# -gt 0 ]; do
  case "$1" in
    --region) require_value "$@"; REGION="${2:-}"; shift 2 ;;
    --profile) require_value "$@"; PROFILE="$2"; shift 2 ;;
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

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
ERROR_ENTRIES=""
record_error() {
  local report
  report="$(printf '%s' "$2" | python3 "$SCRIPT_DIR/classify_sls_error.py" \
    --allow-text --step "$1" 2>/dev/null)"
  if [ -z "$report" ]; then
    report="{\"step\":\"$(json_escape "$1")\",\"error_code\":\"CLI_ERROR\",\"request_id\":\"\"}"
  fi
  [ -n "$ERROR_ENTRIES" ] && ERROR_ENTRIES="$ERROR_ENTRIES,"
  ERROR_ENTRIES="$ERROR_ENTRIES$report"
}

# Reuse shared CLI observability; accept the legacy session variable as a fallback.
SLS_SKILL_SESSION_ID="${ALIBABA_CLOUD_SLS_SKILL_SESSION:-${SKILL_SESSION_ID:-}}"
if [ -z "${ALIBABA_CLOUD_USER_AGENT:-}" ] && [ -n "$SLS_SKILL_SESSION_ID" ]; then
  export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-sls/$SLS_SKILL_SESSION_ID skill-version/0.1.0"
fi

PROFILE_FLAGS=()
[ -n "$PROFILE" ] && PROFILE_FLAGS=(--profile "$PROFILE")

ram() {
  aliyun ram "$@" "${PROFILE_FLAGS[@]}"
}

cs() {
  if [ -n "$REGION" ]; then
    aliyun cs "$@" --region "$REGION" "${PROFILE_FLAGS[@]}"
  else
    aliyun cs "$@" "${PROFILE_FLAGS[@]}"
  fi
}

# ---- open-ack-service (idempotent) ----------------------------------------
SERVICE_STATUS="failed"
ROLES_JSON="[]"
emit_report() {
  printf '{"tool":"ensure_ack_prereq","session_id":"%s","status":"%s","service":"%s","roles":%s,"errors":[%s]}\n' \
    "$(json_escape "$SLS_SKILL_SESSION_ID")" "$1" "$SERVICE_STATUS" "$ROLES_JSON" "$ERROR_ENTRIES"
}

OPEN_RAW=""
if OPEN_RAW="$(cs open-ack-service --type propayasgo 2>&1)"; then
  SERVICE_STATUS="opened"
  echo "[OK] open-ack-service type=propayasgo accepted" >&2
else
  record_error "cs open-ack-service" "$OPEN_RAW"
  echo "[FAIL] open-ack-service failed; no RAM changes attempted" >&2
  emit_report blocked
  exit 1
fi

# ---- CS service roles -----------------------------------------------------
CS_TRUST='{"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":["cs.aliyuncs.com"]}}],"Version":"1"}'
ROLE_JSON=()
ALL_ROLES_OK=1

while IFS='|' read -r ROLE_NAME POLICY_NAME; do
  [ -n "$ROLE_NAME" ] || continue
  ROLE_STATUS="failed"
  ROLE_AVAILABLE=0
  ROLE_CREATED=0
  if ROLE_RAW="$(ram get-role --role-name "$ROLE_NAME" 2>&1)"; then
    ROLE_AVAILABLE=1
  else
    case "$ROLE_RAW" in
      *EntityNotExist.Role*)
        echo "[INFO] create ram role $ROLE_NAME" >&2
        if CREATE_RAW="$(ram create-role --role-name "$ROLE_NAME" \
             --assume-role-policy-document "$CS_TRUST" \
             --description "ACK managed cluster service role" 2>&1)"; then
          ROLE_AVAILABLE=1
          ROLE_CREATED=1
        elif RECHECK_RAW="$(ram get-role --role-name "$ROLE_NAME" 2>&1)"; then
          ROLE_AVAILABLE=1
        else
          record_error "ram create-role $ROLE_NAME" "$CREATE_RAW"
          record_error "ram get-role $ROLE_NAME" "$RECHECK_RAW"
        fi
        ;;
      *)
        record_error "ram get-role $ROLE_NAME" "$ROLE_RAW"
        echo "[FAIL] get-role $ROLE_NAME failed; role absence is unconfirmed" >&2
        ;;
    esac
  fi
  if [ "$ROLE_AVAILABLE" -eq 1 ]; then
    POLICY_PRESENT=""
    if POLICY_PRESENT="$(ram list-policies-for-role --role-name "$ROLE_NAME" \
         --cli-query "contains(Policies.Policy[?PolicyType=='System'].PolicyName, '$POLICY_NAME')" 2>&1)"; then
      POLICY_PRESENT="$(printf '%s' "$POLICY_PRESENT" | tr -d '[:space:]')"
      case "$POLICY_PRESENT" in
        true) ROLE_STATUS="exists" ;;
        false)
          if ATTACH_RAW="$(ram attach-policy-to-role --role-name "$ROLE_NAME" \
               --policy-type System --policy-name "$POLICY_NAME" 2>&1)"; then
            ROLE_STATUS="exists"
          else
            record_error "ram attach-policy-to-role $ROLE_NAME" "$ATTACH_RAW"
          fi
          ;;
        *)
          record_error "ram list-policies-for-role $ROLE_NAME" '{"errorCode":"INVALID_CLI_RESPONSE","message":"Expected boolean policy lookup result"}'
          echo "[FAIL] policy lookup for $ROLE_NAME returned an unexpected result" >&2
          ;;
      esac
    else
      record_error "ram list-policies-for-role $ROLE_NAME" "$POLICY_PRESENT"
      echo "[FAIL] list-policies-for-role $ROLE_NAME failed" >&2
    fi
    if [ "$ROLE_STATUS" != "failed" ] && [ "$ROLE_CREATED" -eq 1 ]; then
      ROLE_STATUS="created"
    fi
  fi
  ROLE_JSON+=("{\"name\":\"$(json_escape "$ROLE_NAME")\",\"status\":\"$ROLE_STATUS\"}")
  if [ "$ROLE_STATUS" = "failed" ]; then
    ALL_ROLES_OK=0
    echo "[FAIL] role/policy setup for $ROLE_NAME is incomplete; stopping" >&2
    break
  fi
  echo "[OK] $ROLE_NAME and $POLICY_NAME are ready" >&2
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
[ "$ALL_ROLES_OK" -eq 1 ] || STATUS="blocked"
emit_report "$STATUS"

[ "$ALL_ROLES_OK" -eq 1 ] && exit 0 || exit 1
