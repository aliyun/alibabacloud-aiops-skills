#!/usr/bin/env bash
# common.sh - Shared utilities for alibabacloud-cfw-nat-firewall-protect
# Source this file from other scripts: source "$(dirname "$0")/common.sh"
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin and Vpc plugin

set -euo pipefail

# --- Constants ---
readonly CFW_PRODUCT_CODE="Cloudfw"
readonly VPC_PRODUCT_CODE="Vpc"
readonly ECS_PRODUCT_CODE="Ecs"
readonly QUOTAS_PRODUCT_CODE="quotas"
readonly DEFAULT_READ_TIMEOUT=30
readonly DEFAULT_CONNECT_TIMEOUT=10

# --- Observability: session id + User-Agent ---
# Every aliyun CLI call carries a User-Agent of the form
#   AlibabaCloud-Agent-Skills/<skill-name>/<session-id>
# so that all API calls belonging to one Skill session can be correlated.
# session-id rule: 32-char lowercase hex, generated ONCE per session and reused
# by every call. Callers may pre-set SKILL_SESSION_ID to join an existing
# session; otherwise it is generated here.
readonly SKILL_NAME="alibabacloud-cfw-nat-firewall-protect"
if [[ -z "${SKILL_SESSION_ID:-}" ]]; then
  SKILL_SESSION_ID=$(uuidgen 2>/dev/null | tr -d '-' | tr 'A-F' 'a-f')
  if [[ ${#SKILL_SESSION_ID} -ne 32 ]]; then
    SKILL_SESSION_ID=$(od -An -tx1 -N16 /dev/urandom 2>/dev/null | tr -d ' \n')
  fi
  export SKILL_SESSION_ID
fi
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/${SKILL_NAME}/${SKILL_SESSION_ID}"

# Valid statuses of a NAT firewall (DescribeSecurityProxy.Status)
# configuring=creating, deleting=deleting, normal=enabled(open),
# abnormal=abnormal, opening=enabling, closing=disabling, closed=disabled
readonly VALID_PROXY_STATUSES="configuring deleting normal abnormal opening closing closed"

# --- Logging (all to stderr) ---

log_info() {
  echo "[INFO] $*" >&2
}

log_warn() {
  echo "[WARN] $*" >&2
}

log_error() {
  echo "[ERROR] $*" >&2
}

# --- Validation Functions ---

validate_required() {
  local name="$1"
  local value="${2:-}"
  if [[ -z "$value" ]]; then
    log_error "Required parameter --${name} is missing or empty"
    return 1
  fi
}

# Validate an option's value during argument parsing (call inside the
# `--opt) ...` branch before consuming $2). Rejects missing values, empty
# values, and values that look like another option (--xxx).
# Usage: --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
arg_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ $# -lt 2 || -z "$value" ]]; then
    log_error "Option ${flag} requires a non-empty value"
    exit 1
  fi
  if [[ "$value" == --* ]]; then
    log_error "Option ${flag} requires a value; got '${value}' which looks like another option"
    exit 1
  fi
}

validate_region() {
  local region="$1"
  if [[ ! "$region" =~ ^[a-z]+-[a-z0-9-]+$ ]]; then
    log_error "Invalid region format: ${region}"
    return 1
  fi
}

validate_member_uid() {
  local uid="$1"
  if [[ ! "$uid" =~ ^[0-9]+$ ]]; then
    log_error "Invalid member UID: ${uid}. Must be numeric"
    return 1
  fi
}

validate_proxy_id() {
  local id="$1"
  # NAT firewall proxy IDs look like "proxy-xxxxxxxx"; accept alphanumeric/hyphen IDs
  if [[ ! "$id" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{3,63}$ ]]; then
    log_error "Invalid NAT firewall ID (proxy-id): ${id}"
    return 1
  fi
}

validate_nat_gateway_id() {
  local id="$1"
  if [[ ! "$id" =~ ^ngw-[a-z0-9]+$ ]]; then
    log_error "Invalid NAT gateway ID: ${id}. Expected format: ngw-xxxxxxxx"
    return 1
  fi
}

validate_vpc_id() {
  local id="$1"
  if [[ ! "$id" =~ ^vpc-[a-z0-9]+$ ]]; then
    log_error "Invalid VPC ID: ${id}. Expected format: vpc-xxxxxxxx"
    return 1
  fi
}

validate_vswitch_id() {
  local id="$1"
  if [[ ! "$id" =~ ^vsw-[a-z0-9]+$ ]]; then
    log_error "Invalid vswitch ID: ${id}. Expected format: vsw-xxxxxxxx"
    return 1
  fi
}

validate_proxy_status() {
  local status="$1"
  local found=false
  for valid in $VALID_PROXY_STATUSES; do
    if [[ "$status" == "$valid" ]]; then
      found=true
      break
    fi
  done
  if [[ "$found" != "true" ]]; then
    log_error "Invalid NAT firewall status: ${status}. Must be one of: ${VALID_PROXY_STATUSES// /, }"
    return 1
  fi
}

validate_strict_mode() {
  local mode="$1"
  if [[ "$mode" != "0" && "$mode" != "1" ]]; then
    log_error "Invalid strict mode: ${mode}. Must be 0 (loose) or 1 (strict)"
    return 1
  fi
}

validate_proxy_name() {
  local name="$1"
  # 4~50 chars, letters/digits/underscore/Chinese, must not start with underscore.
  # Length check is byte-based here as a coarse guard; the API enforces the exact rule.
  if [[ ${#name} -lt 4 || ${#name} -gt 150 ]]; then
    log_error "Invalid proxy name: ${name}. Length must be 4~50 characters"
    return 1
  fi
  if [[ "$name" == _* ]]; then
    log_error "Invalid proxy name: ${name}. Must not start with an underscore"
    return 1
  fi
}

# Iterate over a comma-separated list, trimming whitespace, and invoke a
# validator callback for each element.
# Usage: for_each_csv <csv_values> <validator_func>
for_each_csv() {
  local csv_values="$1"
  local validator="$2"

  local saved_ifs="${IFS-$' \t\n'}"
  IFS=','
  for val in $csv_values; do
    IFS="$saved_ifs"
    val=$(printf '%s' "$val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [[ -n "$val" ]]; then
      "$validator" "$val" || return 1
    fi
  done
  IFS="$saved_ifs"
}

# --- Output Helpers ---

# Output a success JSON result to stdout
# Usage: output_success <json_data>
output_success() {
  local data="$1"
  printf '%s\n' "$data"
}

# Output an error JSON result to stdout
# Usage: output_error <error_code> <error_message>
output_error() {
  local error_code="${1:-UnknownError}"
  local error_message="${2:-An unknown error occurred}"

  cat <<EOF
{
  "success": false,
  "error_code": "${error_code}",
  "error_message": "${error_message}"
}
EOF
}

# --- Error Extraction ---
#
# CRITICAL: these helpers run on the ERROR paths, and their callers assign them
# with a plain `var=$(...)`. Under `set -e` + `pipefail` a non-matching grep
# makes the pipeline (and therefore the assignment) fail, which aborts the whole
# script BEFORE output_error can emit the structured error JSON - the caller then
# sees an empty stdout and a bare exit 1. That is exactly what happens with
# non-standard error text (network timeouts, plugin-level errors such as
# "unchecked version", SDK-level errors) which carry no `ErrorCode:` / `Message:`
# line at all. So every pipeline here MUST swallow the no-match failure and
# simply return an empty string.

extract_api_error_code() {
  local response="$1"
  printf '%s' "$response" | grep -o 'ErrorCode: [^ ]*' | head -1 | sed 's/ErrorCode: //' || true
}

extract_api_error_message() {
  local response="$1"
  printf '%s' "$response" | grep -o 'Message: .*' | head -1 | sed 's/Message: //' || true
}

extract_api_request_id() {
  local response="$1"
  # Try CLI error format first, then JSON response format
  local rid
  rid=$(printf '%s' "$response" | grep -o 'RequestId: [^ ]*' | head -1 | sed 's/RequestId: //' || true)
  if [[ -z "$rid" ]]; then
    rid=$(printf '%s' "$response" | grep -o '"RequestId"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/' || true)
  fi
  printf '%s' "$rid"
}

# --- CLI Wrapper ---

# Call CFW API via aliyun CLI (plugin mode).
# Usage: call_cfw_api <APIName> [--Param1 value1 ...]
# Returns: API response on stdout, diagnostics on stderr
call_cfw_api() {
  local api_name="$1"
  shift

  local cmd=(
    aliyun "$CFW_PRODUCT_CODE" "$api_name"
    --user-agent "$ALIBABA_CLOUD_USER_AGENT"
    --read-timeout "$DEFAULT_READ_TIMEOUT"
    --connect-timeout "$DEFAULT_CONNECT_TIMEOUT"
    "$@"
  )

  log_info "Calling: aliyun ${CFW_PRODUCT_CODE} ${api_name} ..."

  local response exit_code=0
  response=$("${cmd[@]}" 2>&1) || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    log_error "API call failed with exit code ${exit_code}"
    log_error "Response: ${response}"

    local request_id
    request_id=$(extract_api_request_id "$response")
    if [[ -n "$request_id" ]]; then
      log_error "RequestId: ${request_id} (provide this when contacting support)"
    fi

    printf '%s' "$response"
    return $exit_code
  fi

  printf '%s' "$response"
}

# Call VPC API via aliyun CLI (plugin mode). Used to auto-discover route
# entries pointing to the NAT gateway during NAT firewall creation.
# Usage: call_vpc_api <APIName> [--Param1 value1 ...]
call_vpc_api() {
  local api_name="$1"
  shift

  local cmd=(
    aliyun "$VPC_PRODUCT_CODE" "$api_name"
    --user-agent "$ALIBABA_CLOUD_USER_AGENT"
    --read-timeout "$DEFAULT_READ_TIMEOUT"
    --connect-timeout "$DEFAULT_CONNECT_TIMEOUT"
    "$@"
  )

  log_info "Calling: aliyun ${VPC_PRODUCT_CODE} ${api_name} ..."

  local response exit_code=0
  response=$("${cmd[@]}" 2>&1) || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    log_error "VPC API call failed with exit code ${exit_code}"
    log_error "Response: ${response}"
    printf '%s' "$response"
    return $exit_code
  fi

  printf '%s' "$response"
}

# Call ECS API via aliyun CLI (plugin mode). Used to verify that a manual-mode
# diversion vswitch carries no other cloud resources (ENI enumeration).
# Usage: call_ecs_api <APIName> [--Param1 value1 ...]
call_ecs_api() {
  local api_name="$1"
  shift

  local cmd=(
    aliyun "$ECS_PRODUCT_CODE" "$api_name"
    --user-agent "$ALIBABA_CLOUD_USER_AGENT"
    --read-timeout "$DEFAULT_READ_TIMEOUT"
    --connect-timeout "$DEFAULT_CONNECT_TIMEOUT"
    "$@"
  )

  log_info "Calling: aliyun ${ECS_PRODUCT_CODE} ${api_name} ..."

  local response exit_code=0
  response=$("${cmd[@]}" 2>&1) || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    log_error "ECS API call failed with exit code ${exit_code}"
    log_error "Response: ${response}"
    printf '%s' "$response"
    return $exit_code
  fi

  printf '%s' "$response"
}

# Call Quotas Center API via aliyun CLI. Used by assess to resolve the REAL
# resource quotas (route tables / vswitches / VPN custom routes / SNAT
# entries) for the post-creation quota projection. Documentation defaults
# must NOT be assumed: customers may have raised their quotas, and guessing
# the default value produces false blockers (hallucination).
# Usage: call_quotas_api <api-name-in-kebab-case> [--param-name value ...]
# NOTE: the quotas CLI runs in PLUGIN mode, which requires kebab-case for BOTH
# the API name and the flags (`get-product-quota --product-code ...`), unlike the
# Cloudfw/Vpc/Ecs plugins that keep PascalCase parameters.
call_quotas_api() {
  local api_name="$1"
  shift

  local cmd=(
    aliyun "$QUOTAS_PRODUCT_CODE" "$api_name"
    --user-agent "$ALIBABA_CLOUD_USER_AGENT"
    --read-timeout "$DEFAULT_READ_TIMEOUT"
    --connect-timeout "$DEFAULT_CONNECT_TIMEOUT"
    "$@"
  )

  log_info "Calling: aliyun ${QUOTAS_PRODUCT_CODE} ${api_name} ..."

  local response exit_code=0
  response=$("${cmd[@]}" 2>&1) || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    log_error "Quotas API call failed with exit code ${exit_code}"
    log_error "Response: ${response}"
    printf '%s' "$response"
    return $exit_code
  fi

  printf '%s' "$response"
}

# --- Help Generator ---

show_help() {
  local script_name="$1"
  local description="$2"
  local usage="$3"
  local options_text="$4"

  cat >&2 <<EOF
${script_name} - ${description}

USAGE:
  ${usage}

OPTIONS:
${options_text}

OUTPUT:
  JSON to stdout. Diagnostics to stderr.

EXIT CODES:
  0  Success
  1  Parameter validation error
  2  API call failed
EOF
  exit 0
}

# --- Error Diagnosis ---

# Provide user-friendly diagnosis for common CFW NAT firewall error codes
diagnose_cfw_error() {
  local error_code="$1"
  local error_message="${2:-}"

  case "$error_code" in
    MissingNatRouteEntryList|Missing*NatGatewayId|Missing*RegionNo|Missing*VpcId|Missing*ProxyName|Missing*ProxyId|Missing*Switch)
      log_error "Diagnosis: A required API parameter is missing."
      log_error "  Fix: Check the script usage (--help) and provide all required parameters."
      ;;
    ErrorNatGatewayNotExist|InvalidNatGatewayId.NotFound|-360838)
      log_error "Diagnosis: The NAT gateway was not found in Cloud Firewall."
      log_error "  Fix: Verify the NAT gateway ID, region, and VPC ID. New NAT gateways take 1~5 minutes to sync into Cloud Firewall — click '同步资产' in the console or retry later."
      ;;
    ErrorProxyAlreadyExist|ErrorNatFirewallAlreadyExist)
      log_error "Diagnosis: A NAT firewall already exists for this NAT gateway (one NAT gateway maps to one NAT firewall)."
      log_error "  Fix: Query existing NAT firewalls with 'nat-fw-switch.sh query --nat-gateway-id <id>' and operate on it directly."
      ;;
    ErrorProxyNotExist|ErrorNatFirewallNotExist)
      log_error "Diagnosis: The specified NAT firewall does not exist."
      log_error "  Fix: Verify the proxy-id with 'nat-fw-switch.sh query'."
      ;;
    ErrorNatFirewallQuotaExceed|ErrorInstanceSpecFull|ErrorQuotaExceed)
      log_error "Diagnosis: NAT firewall authorization quota reached the limit."
      log_error "  Fix: Purchase additional NAT firewall quotas or delete unused NAT firewalls. See 'nat-fw-lifecycle.sh quota'."
      ;;
    ErrorNatFirewallPreCheckFailed|ErrorPreCheckFailed)
      log_error "Diagnosis: NAT firewall pre-check failed."
      log_error "  Fix: Run 'nat-fw-lifecycle.sh precheck' and see references/nat-prerequisites.md for how to fix each failed check item."
      ;;
    ErrorInstanceStatusNotNormal)
      log_error "Diagnosis: CFW instance status is abnormal (may be unpaid or inactive)."
      log_error "  Fix: Check the instance status and billing in the Cloud Firewall console."
      ;;
    ErrorAuthentication)
      log_error "Diagnosis: Authentication failed — credentials are invalid or expired."
      log_error "  Fix: Run 'aliyun configure' to review and update your credential configuration."
      ;;
    NoPermission|Forbidden*|Forbidden.RAM)
      log_error "Diagnosis: Insufficient permissions (RAM ImplicitDeny)."
      log_error "  Fix: Grant the required yundun-cloudfirewall:* (and vpc:Describe* for route discovery) permissions via RAM console. See references/ram-policies.md."
      ;;
    Throttling)
      log_error "Diagnosis: API call rate limit exceeded."
      log_error "  Fix: Wait a few seconds and retry."
      ;;
    *)
      log_error "Diagnosis: Unrecognized error code '${error_code}'."
      if [[ -n "$error_message" ]]; then
        log_error "  Error message: ${error_message}"
      fi
      ;;
  esac
}
