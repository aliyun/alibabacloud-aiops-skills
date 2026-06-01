#!/usr/bin/env bash
# common.sh - Shared utilities for alibabacloud-cfw-internet-firewall-protect
# Source this file from other scripts: source "$(dirname "$0")/common.sh"
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin

set -euo pipefail

# --- Constants ---
readonly CFW_PRODUCT_CODE="Cloudfw"
readonly DEFAULT_READ_TIMEOUT=30
readonly DEFAULT_CONNECT_TIMEOUT=10

# Valid resource types for Internet Firewall (auto-protect + query-only BastionHostAll)
# Source: DescribeResourceTypeAutoEnable API + DescribeAssetList query-only types
readonly VALID_RESOURCE_TYPES="AiGatewayEIP AiGatewayEIPv6 AlbEIP AlbIPv6 ApiGatewayEIP ApiGatewayEIPv6 BastionHostAll BastionHostEgressIP BastionHostIngressIP BastionHostIP EIP EcdEIP EcsEIP EcsIPv6 EcsPublicIP EniEIP EniEIPv6 GaEIP GaEIPV6 HAVIP NatEIP NatPublicIP NlbEIP NlbIPv6 SlbEIP SlbIPv6 SlbPublicIP SwasEIP"

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

validate_ip() {
  local ip="$1"
  if [[ ! "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log_error "Invalid IP address format: ${ip}"
    return 1
  fi
}

validate_region() {
  local region="$1"
  if [[ ! "$region" =~ ^[a-z]+-[a-z0-9-]+$ ]]; then
    log_error "Invalid region format: ${region}"
    return 1
  fi
}

validate_resource_type() {
  local rtype="$1"
  local found=false
  for valid in $VALID_RESOURCE_TYPES; do
    if [[ "$rtype" == "$valid" ]]; then
      found=true
      break
    fi
  done
  if [[ "$found" != "true" ]]; then
    log_error "Invalid resource type: ${rtype}. Valid types: ${VALID_RESOURCE_TYPES}"
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

validate_ip_version() {
  local ver="$1"
  if [[ "$ver" != "4" && "$ver" != "6" ]]; then
    log_error "Invalid IP version: ${ver}. Must be 4 or 6"
    return 1
  fi
}

validate_status() {
  local status="$1"
  case "$status" in
    open|opening|closed|closing) ;;
    *) log_error "Invalid status: ${status}. Must be one of: open, opening, closed, closing"; return 1 ;;
  esac
}

# --- Array Parameter Expansion ---

# Expand comma-separated values into RepeatList CLI args.
# Appends directly to the caller's CLI_ARGS array (bash dynamic scoping).
# Usage: expand_repeat_list <api_param_name> <csv_values>
# Example: expand_repeat_list "IpaddrList" "1.2.3.4,5.6.7.8"
#   → appends --IpaddrList.1 1.2.3.4 --IpaddrList.2 5.6.7.8 to CLI_ARGS
expand_repeat_list() {
  local param_name="$1"
  local csv_values="$2"

  local idx=1
  local saved_ifs="${IFS-$' \t\n'}"
  IFS=','
  for val in $csv_values; do
    IFS="$saved_ifs"
    # Trim whitespace
    val=$(printf '%s' "$val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [[ -n "$val" ]]; then
      CLI_ARGS+=("--${param_name}.${idx}" "$val")
      idx=$((idx + 1))
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

extract_api_error_code() {
  local response="$1"
  printf '%s' "$response" | grep -o 'ErrorCode: [^ ]*' | head -1 | sed 's/ErrorCode: //'
}

extract_api_error_message() {
  local response="$1"
  printf '%s' "$response" | grep -o 'Message: .*' | head -1 | sed 's/Message: //'
}

extract_api_request_id() {
  local response="$1"
  # Try CLI error format first, then JSON response format
  local rid
  rid=$(printf '%s' "$response" | grep -o 'RequestId: [^ ]*' | head -1 | sed 's/RequestId: //')
  if [[ -z "$rid" ]]; then
    rid=$(printf '%s' "$response" | grep -o '"RequestId"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
  fi
  printf '%s' "$rid"
}

# --- CLI Wrapper ---

# Call CFW API via aliyun CLI.
# Usage: call_cfw_api <APIName> [--Param1 value1 ...]
# Returns: API response on stdout, diagnostics on stderr
call_cfw_api() {
  local api_name="$1"
  shift

  local cmd=(
    aliyun "$CFW_PRODUCT_CODE" "$api_name"
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

# Provide user-friendly diagnosis for common CFW error codes
diagnose_cfw_error() {
  local error_code="$1"
  local error_message="${2:-}"

  case "$error_code" in
    ErrorInstanceOpenIpNumExceed)
      log_error "Diagnosis: Protected IP count has reached the limit of the current CFW instance spec."
      log_error "  Fix: Upgrade the CFW edition to increase the IP protection quota, or disable protection on lower-priority IPs."
      ;;
    ErrorInstanceOpenIpRegionNumExceed)
      log_error "Diagnosis: Regional protection quota exceeded."
      log_error "  Fix: Upgrade the CFW edition to increase the regional protection quota."
      ;;
    ErrorBandwidthPenalty)
      log_error "Diagnosis: CFW bandwidth overuse is being enforced."
      log_error "  Fix: Wait for enforcement to complete and retry, or contact support for details."
      ;;
    ErrorGeneralInstanceSpecFull)
      log_error "Diagnosis: CFW instance spec is at full capacity."
      log_error "  Fix: Upgrade the CFW instance spec."
      ;;
    ErrorInstanceStatusNotNormal)
      log_error "Diagnosis: CFW instance status is abnormal (may be unpaid or inactive)."
      log_error "  Fix: Check the instance status and billing in the Cloud Firewall console."
      ;;
    ErrorAuthentication)
      log_error "Diagnosis: Authentication failed — credentials are invalid or expired."
      log_error "  Fix: Run 'aliyun configure' to review and update your credential configuration."
      ;;
    ErrorParamsNotEnough)
      log_error "Diagnosis: Insufficient API parameters. At least one of --ips, --regions, --resource-types, or --ip-version is required for enable/disable operations."
      ;;
    ErrorParamsInvalid)
      log_error "Diagnosis: Invalid API parameters. Check that the IP addresses, region IDs, or resource types are correct."
      ;;
    NoPermission|Forbidden*)
      log_error "Diagnosis: Insufficient permissions for Cloud Firewall operations."
      log_error "  Fix: Grant the required cloudfw:* permissions via RAM console. See references/ram-policies.md."
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
