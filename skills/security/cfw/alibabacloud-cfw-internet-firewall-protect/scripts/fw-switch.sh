#!/usr/bin/env bash
# fw-switch.sh - Manage Cloud Firewall Internet Firewall protection switches
# Part of alibabacloud-cfw-internet-firewall-protect skill
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin
#
# Subcommands:
#   query       - Query asset protection status (DescribeAssetList)
#   enable      - Enable protection by IP/region/resource-type/ip-version (PutEnableFwSwitch)
#   disable     - Disable protection by IP/region/resource-type/ip-version (PutDisableFwSwitch)
#   enable-all  - Enable protection for ALL public IPs (PutEnableAllFwSwitch)
#   disable-all - Disable protection for ALL public IPs (PutDisableAllFwSwitch)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# --- Main Help ---
show_main_help() {
  cat >&2 <<'EOF'
fw-switch.sh - Manage Cloud Firewall Internet Firewall protection switches

USAGE:
  fw-switch.sh <subcommand> [options]

SUBCOMMANDS:
  query       Query asset protection status
  enable      Enable firewall protection (by IP/region/resource-type/ip-version)
  disable     Disable firewall protection (by IP/region/resource-type/ip-version)
  enable-all  Enable protection for ALL public IPs
  disable-all Disable protection for ALL public IPs

GLOBAL OPTIONS:
  --dry-run   Preview CLI command without executing
  --help, -h  Show help for the subcommand

EXAMPLES:
  fw-switch.sh query --status closed --page 1 --page-size 20
  fw-switch.sh enable --ips "1.2.3.4,5.6.7.8"
  fw-switch.sh enable --regions "cn-hangzhou,cn-beijing" --resource-types "EcsPublicIP"
  fw-switch.sh enable --ip-version 4
  fw-switch.sh disable --ips "1.2.3.4" --dry-run
  fw-switch.sh enable-all --yes
  fw-switch.sh disable-all --yes --dry-run

EXIT CODES:
  0  Success
  1  Parameter validation error
  2  API call failed
EOF
  exit 0
}

# --- Subcommand: query ---
cmd_query() {
  local REGION="" STATUS="" RESOURCE_TYPE="" SEARCH="" IP_VERSION=""
  local MEMBER_UID="" NEW_RESOURCE_TAG="" PAGE="1" PAGE_SIZE="10" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --region) REGION="$2"; shift 2 ;;
      --status) STATUS="$2"; shift 2 ;;
      --resource-type) RESOURCE_TYPE="$2"; shift 2 ;;
      --search) SEARCH="$2"; shift 2 ;;
      --ip-version) IP_VERSION="$2"; shift 2 ;;
      --member-uid) MEMBER_UID="$2"; shift 2 ;;
      --page) PAGE="$2"; shift 2 ;;
      --page-size) PAGE_SIZE="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "fw-switch.sh query" \
          "Query asset protection status" \
          "fw-switch.sh query [options]" \
          "  --region <id>          Filter by region (e.g. cn-hangzhou)
  --status <status>      Filter: open, opening, closed, closing
  --resource-type <type> Filter by resource type (e.g. EcsPublicIP)
  --search <ip|id>       Search by IP or instance ID
  --ip-version <4|6>     Filter by IP version (default: all)
  --member-uid <uid>     Member account UID
  --page <n>             Page number (default: 1)
  --page-size <n>        Items per page (default: 10)
  --dry-run              Preview CLI command
  --help, -h             Show this help

  Each filter accepts a single value. For multi-region or multi-type queries,
  make separate calls and let the Agent merge results."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  # Validate optional params if provided
  [[ -n "$REGION" ]] && validate_region "$REGION"
  [[ -n "$STATUS" ]] && validate_status "$STATUS"
  [[ -n "$RESOURCE_TYPE" ]] && validate_resource_type "$RESOURCE_TYPE"
  [[ -n "$IP_VERSION" ]] && validate_ip_version "$IP_VERSION"
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"

  # Build CLI args
  local CLI_ARGS=(--CurrentPage "$PAGE" --PageSize "$PAGE_SIZE" --Lang zh)
  [[ -n "$REGION" ]] && CLI_ARGS+=(--RegionNo "$REGION")
  [[ -n "$STATUS" ]] && CLI_ARGS+=(--Status "$STATUS")
  [[ -n "$RESOURCE_TYPE" ]] && CLI_ARGS+=(--ResourceType "$RESOURCE_TYPE")
  [[ -n "$SEARCH" ]] && CLI_ARGS+=(--SearchItem "$SEARCH")
  [[ -n "$IP_VERSION" ]] && CLI_ARGS+=(--IpVersion "$IP_VERSION")
  [[ -n "$MEMBER_UID" ]] && CLI_ARGS+=(--MemberUid "$MEMBER_UID")
  [[ -n "${NEW_RESOURCE_TAG:-}" ]] && CLI_ARGS+=(--NewResourceTag "$NEW_RESOURCE_TAG")

  # Dry-run
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeAssetList \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  # Execute
  local response exit_code=0
  response=$(call_cfw_api "DescribeAssetList" "${CLI_ARGS[@]}") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  # Output raw API response — Agent parses the JSON (Assets array, TotalCount, etc.)
  output_success "$response"
}

# --- Subcommand: enable / disable ---
cmd_enable_disable() {
  local ACTION="$1"  # "enable" or "disable"
  shift

  local API_NAME
  if [[ "$ACTION" == "enable" ]]; then
    API_NAME="PutEnableFwSwitch"
  else
    API_NAME="PutDisableFwSwitch"
  fi

  local IPS="" REGIONS="" RESOURCE_TYPES="" IP_VERSION="" MEMBER_UID="" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --ips) IPS="$2"; shift 2 ;;
      --regions) REGIONS="$2"; shift 2 ;;
      --resource-types) RESOURCE_TYPES="$2"; shift 2 ;;
      --ip-version) IP_VERSION="$2"; shift 2 ;;
      --member-uid) MEMBER_UID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        local action_cap="$(printf '%s' "${ACTION:0:1}" | tr '[:lower:]' '[:upper:]')${ACTION:1}"
        show_help "fw-switch.sh ${ACTION}" \
          "${action_cap} firewall protection for specified assets" \
          "fw-switch.sh ${ACTION} [options]" \
          "  --ips <ip1,ip2,...>              Comma-separated IP list
  --regions <r1,r2,...>            Comma-separated region list
  --resource-types <t1,t2,...>     Comma-separated resource types
  --ip-version <4|6>               IP version filter
  --member-uid <uid>               Member account UID
  --dry-run                        Preview CLI command
  --help, -h                       Show this help

  At least one of --ips, --regions, --resource-types, --ip-version is required.
  Parameters can be combined for compound filtering."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  # Must have at least one filter dimension
  if [[ -z "$IPS" && -z "$REGIONS" && -z "$RESOURCE_TYPES" && -z "$IP_VERSION" ]]; then
    log_error "At least one of --ips, --regions, --resource-types, --ip-version is required"
    exit 1
  fi

  # Validate individual values in comma-separated lists
  if [[ -n "$IPS" ]]; then
    local _ifs_save="${IFS-$' \t\n'}"
    IFS=','
    for ip in $IPS; do
      IFS="$_ifs_save"
      ip=$(printf '%s' "$ip" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      [[ -n "$ip" ]] && validate_ip "$ip"
    done
    IFS="$_ifs_save"
  fi
  if [[ -n "$REGIONS" ]]; then
    local _ifs_save="${IFS-$' \t\n'}"
    IFS=','
    for r in $REGIONS; do
      IFS="$_ifs_save"
      r=$(printf '%s' "$r" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      [[ -n "$r" ]] && validate_region "$r"
    done
    IFS="$_ifs_save"
  fi
  if [[ -n "$RESOURCE_TYPES" ]]; then
    local _ifs_save="${IFS-$' \t\n'}"
    IFS=','
    for rt in $RESOURCE_TYPES; do
      IFS="$_ifs_save"
      rt=$(printf '%s' "$rt" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      [[ -n "$rt" ]] && validate_resource_type "$rt"
    done
    IFS="$_ifs_save"
  fi
  [[ -n "$IP_VERSION" ]] && validate_ip_version "$IP_VERSION"
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"

  # Build CLI args
  local CLI_ARGS=(--Lang zh)
  [[ -n "$IPS" ]] && expand_repeat_list "IpaddrList" "$IPS"
  [[ -n "$REGIONS" ]] && expand_repeat_list "RegionList" "$REGIONS"
  [[ -n "$RESOURCE_TYPES" ]] && expand_repeat_list "ResourceTypeList" "$RESOURCE_TYPES"
  [[ -n "$IP_VERSION" ]] && CLI_ARGS+=(--IpVersion "$IP_VERSION")
  [[ -n "$MEMBER_UID" ]] && CLI_ARGS+=(--MemberUid "$MEMBER_UID")

  # Dry-run
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} ${API_NAME} \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  # Execute
  local action_label="$(printf '%s' "${ACTION:0:1}" | tr '[:lower:]' '[:upper:]')${ACTION:1}"
  log_info "${action_label} firewall protection..."
  local response exit_code=0
  response=$(call_cfw_api "$API_NAME" "${CLI_ARGS[@]}") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  # Build success output
  local request_id
  request_id=$(extract_api_request_id "$response")

  # Check for abnormal resources (PutEnableFwSwitch returns AbnormalResourceStatusList)
  local abnormal_list="[]"
  if printf '%s' "$response" | grep -q '"AbnormalResourceStatusList"'; then
    abnormal_list=$(printf '%s' "$response" | grep -o '"AbnormalResourceStatusList"[[:space:]]*:[[:space:]]*\[.*\]' | sed 's/"AbnormalResourceStatusList"[[:space:]]*:[[:space:]]*//' || echo "[]")
  fi

  cat <<EOF
{
  "success": true,
  "action": "${ACTION}",
  "request_id": "${request_id:-}",
  "abnormal_resources": ${abnormal_list}
}
EOF
}

# --- Subcommand: enable-all / disable-all ---
cmd_enable_disable_all() {
  local ACTION="$1"  # "enable-all" or "disable-all"
  shift

  local API_NAME
  if [[ "$ACTION" == "enable-all" ]]; then
    API_NAME="PutEnableAllFwSwitch"
  else
    API_NAME="PutDisableAllFwSwitch"
  fi

  local INSTANCE_ID="" YES=false DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --instance-id) INSTANCE_ID="$2"; shift 2 ;;
      --yes) YES=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        local action_cap="$(printf '%s' "${ACTION:0:1}" | tr '[:lower:]' '[:upper:]')${ACTION:1}"
        show_help "fw-switch.sh ${ACTION}" \
          "${action_cap} firewall protection for ALL public IPs" \
          "fw-switch.sh ${ACTION} --yes [options]" \
          "  --instance-id <id>  Cloud Firewall instance ID (optional)
  --yes               Confirm execution (required for safety)
  --dry-run           Preview CLI command
  --help, -h          Show this help"
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  # Build CLI args
  local CLI_ARGS=(--Lang zh)
  [[ -n "$INSTANCE_ID" ]] && CLI_ARGS+=(--InstanceId "$INSTANCE_ID")

  # Dry-run
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} ${API_NAME} \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  # Safety check
  if [[ "$YES" != "true" ]]; then
    log_error "This operation affects ALL public IPs. Pass --yes to confirm."
    output_error "NotConfirmed" "Operation requires --yes flag to confirm"
    exit 1
  fi

  # Execute
  log_info "Executing ${ACTION} for all public IPs..."
  local response exit_code=0
  response=$(call_cfw_api "$API_NAME" "${CLI_ARGS[@]}") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  local request_id
  request_id=$(extract_api_request_id "$response")

  cat <<EOF
{
  "success": true,
  "action": "${ACTION}",
  "request_id": "${request_id:-}"
}
EOF
}

# --- Main Router ---

SUBCOMMAND="${1:-}"
if [[ -z "$SUBCOMMAND" || "$SUBCOMMAND" == "--help" || "$SUBCOMMAND" == "-h" ]]; then
  show_main_help
fi
shift

case "$SUBCOMMAND" in
  query)
    cmd_query "$@"
    ;;
  enable)
    cmd_enable_disable "enable" "$@"
    ;;
  disable)
    cmd_enable_disable "disable" "$@"
    ;;
  enable-all)
    cmd_enable_disable_all "enable-all" "$@"
    ;;
  disable-all)
    cmd_enable_disable_all "disable-all" "$@"
    ;;
  *)
    log_error "Unknown subcommand: ${SUBCOMMAND}"
    log_error "Run 'fw-switch.sh --help' for usage"
    exit 1
    ;;
esac
