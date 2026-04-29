#!/bin/bash

# ==========================================
# Alibaba Cloud CloudMonitor Alert Parameter Validation
# ==========================================
# Usage:
#   bash validate-params.sh <rule-name> <metric-name> <warn-threshold> <critical-threshold> <warn-times> <critical-times> <contact-group> [namespace] [resources-json] [effective-interval]
#
# Use '-' for optional fields you want to skip (e.g., warn-threshold).
#
# Exit codes:
#   0 - All validations passed
#   1 - One or more validations failed
#
# Examples:
#   bash validate-params.sh ECS-CPU-Alert CPUUtilization 70 85 5 3 Default
#   bash validate-params.sh ECS-CPU-Alert CPUUtilization - 85 - 3 Default acs_ecs_dashboard
# ==========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

errors=0

log_ok()   { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; errors=$((errors + 1)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# --- Validators ---

validate_rule_name() {
  local name="$1"
  local len=${#name}
  if [ -z "$name" ]; then
    log_fail "rule-name: cannot be empty"
  elif [ $len -lt 2 ] || [ $len -gt 64 ]; then
    log_fail "rule-name: length must be 2-64 characters (got $len)"
  else
    log_ok "rule-name: '$name' ($len chars)"
  fi
}

validate_threshold() {
  local label="$1"
  local value="$2"
  local metric="$3"

  # Allow empty or skipped value for optional thresholds
  if [ -z "$value" ] || [ "$value" = "-" ]; then
    log_ok "$label: skipped (not set)"
    return
  fi

  # Must be a non-negative number (integer or decimal)
  if ! echo "$value" | grep -qE '^[0-9]+(\.[0-9]+)?$'; then
    log_fail "$label: '$value' is not a valid number"
    return
  fi

  # Percentage metrics must be 0-100
  if echo "$metric" | grep -qiE '(Utilization|Usage|Rates)'; then
    local too_low too_high
    too_low=$(echo "$value < 0" | bc -l 2>/dev/null || echo 0)
    too_high=$(echo "$value > 100" | bc -l 2>/dev/null || echo 0)
    if [ "$too_low" = "1" ] || [ "$too_high" = "1" ]; then
      log_fail "$label: percentage metric '$metric' requires threshold 0-100 (got $value)"
      return
    fi
  fi

  log_ok "$label: $value"
}

validate_times() {
  local label="$1"
  local value="$2"

  # Allow empty or skipped value
  if [ -z "$value" ] || [ "$value" = "-" ]; then
    log_ok "$label: skipped (not set)"
    return
  fi

  if ! echo "$value" | grep -qE '^[0-9]+$'; then
    log_fail "$label: '$value' is not a valid integer"
    return
  fi

  if [ "$value" -lt 1 ] || [ "$value" -gt 10 ]; then
    log_fail "$label: must be 1-10 (got $value)"
    return
  fi

  log_ok "$label: $value"
}

validate_namespace() {
  local ns="$1"
  local known_namespaces="acs_ecs_dashboard acs_rds_dashboard acs_slb_dashboard acs_oss_dashboard acs_kvstore acs_k8s acs_fc acs_kafka acs_rocketmq acs_sls_dashboard acs_cdn acs_vpn acs_nat_gateway"

  if [ -z "$ns" ]; then
    log_fail "namespace: cannot be empty"
    return
  fi

  for known in $known_namespaces; do
    if [ "$ns" = "$known" ]; then
      log_ok "namespace: $ns"
      return
    fi
  done

  log_warn "namespace: '$ns' is not in the known list (may still be valid for newer services)"
}

validate_resources_json() {
  local json="$1"

  if [ -z "$json" ]; then
    log_fail "resources: cannot be empty"
    return
  fi

  # Basic JSON array structure check
  if ! echo "$json" | grep -qE '^\[.*\]$'; then
    log_fail "resources: must be a JSON array (e.g., [{\"resource\":\"_ALL\"}])"
    return
  fi

  # Check for known patterns
  if echo "$json" | grep -qE '"resource"\s*:\s*"_ALL"'; then
    log_ok "resources: all resources"
  elif echo "$json" | grep -qE '"instanceId"\s*:\s*"'; then
    log_ok "resources: specific instance(s)"
  else
    log_warn "resources: unrecognized format, please verify"
  fi
}

validate_contact_group() {
  local group="$1"

  if [ -z "$group" ]; then
    log_fail "contact-groups: cannot be empty"
    return
  fi

  # Try to verify against the API (best-effort, don't fail if CLI is unavailable)
  if command -v aliyun >/dev/null 2>&1; then
    local result
    result=$(aliyun cms describe-contact-group-list 2>/dev/null) || true
    if [ -n "$result" ]; then
      if echo "$result" | grep -q "\"Name\": \"$group\""; then
        log_ok "contact-groups: '$group' (verified exists)"
      else
        log_warn "contact-groups: '$group' not found in existing groups"
      fi
    else
      log_warn "contact-groups: could not query API, skipping existence check"
    fi
  else
    log_warn "contact-groups: aliyun CLI not available, skipping existence check"
  fi
}

validate_effective_interval() {
  local interval="$1"

  if [ -z "$interval" ] || [ "$interval" = "-" ]; then
    return  # Optional field
  fi

  if echo "$interval" | grep -qE '^[0-2][0-9]:[0-5][0-9]-[0-2][0-9]:[0-5][0-9]$'; then
    log_ok "effective-interval: $interval"
  else
    log_fail "effective-interval: must be HH:MM-HH:MM format (got '$interval')"
  fi
}

# --- Main ---

if [ "$#" -lt 7 ]; then
  echo "Usage: $0 <rule-name> <metric-name> <warn-threshold> <critical-threshold> <warn-times> <critical-times> <contact-group> [namespace] [resources-json] [effective-interval]"
  echo ""
  echo "Use '-' for optional fields you want to skip (e.g., warn-threshold)."
  echo ""
  echo "Examples:"
  echo "  $0 ECS-CPU-Alert CPUUtilization 70 85 5 3 Default"
  echo "  $0 ECS-CPU-Alert CPUUtilization - 85 - 3 Default acs_ecs_dashboard"
  exit 1
fi

RULE_NAME="$1"
METRIC_NAME="$2"
WARN_THRESHOLD="$3"
CRITICAL_THRESHOLD="$4"
WARN_TIMES="$5"
CRITICAL_TIMES="$6"
CONTACT_GROUP="$7"
NAMESPACE="${8:-}"
RESOURCES="${9:-}"
EFFECTIVE_INTERVAL="${10:-}"

echo "=========================================="
echo "  Parameter Validation"
echo "=========================================="
echo ""

validate_rule_name "$RULE_NAME"
validate_threshold "warn-threshold" "$WARN_THRESHOLD" "$METRIC_NAME"
validate_threshold "critical-threshold" "$CRITICAL_THRESHOLD" "$METRIC_NAME"
validate_times "warn-times" "$WARN_TIMES"
validate_times "critical-times" "$CRITICAL_TIMES"
validate_contact_group "$CONTACT_GROUP"

if [ -n "$NAMESPACE" ]; then
  validate_namespace "$NAMESPACE"
fi

if [ -n "$RESOURCES" ]; then
  validate_resources_json "$RESOURCES"
fi

if [ -n "$EFFECTIVE_INTERVAL" ]; then
  validate_effective_interval "$EFFECTIVE_INTERVAL"
fi

echo ""
echo "=========================================="
if [ "$errors" -gt 0 ]; then
  log_fail "Validation failed with $errors error(s)"
  exit 1
else
  log_ok "All validations passed"
  exit 0
fi
