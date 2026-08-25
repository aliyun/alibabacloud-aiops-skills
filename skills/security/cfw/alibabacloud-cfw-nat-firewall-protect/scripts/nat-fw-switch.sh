#!/usr/bin/env bash
# nat-fw-switch.sh - Query and toggle Cloud Firewall NAT firewall protection switches
# Part of alibabacloud-cfw-nat-firewall-protect skill
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin
#
# Subcommands:
#   query   - Query NAT firewall list and status (DescribeSecurityProxy)
#   enable  - Enable protection for specified NAT firewalls (SwitchSecurityProxy open)
#   disable - Disable protection for specified NAT firewalls (SwitchSecurityProxy close)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# --- Main Help ---
show_main_help() {
  cat >&2 <<'EOF'
nat-fw-switch.sh - Query and toggle Cloud Firewall NAT firewall protection switches

USAGE:
  nat-fw-switch.sh <subcommand> [options]

SUBCOMMANDS:
  query    Query NAT firewall list and protection status
  enable   Enable protection for specified NAT firewalls
  disable  Disable protection for specified NAT firewalls

GLOBAL OPTIONS:
  --dry-run   Preview CLI command without executing
  --help, -h  Show help for the subcommand

EXAMPLES:
  nat-fw-switch.sh query --region cn-hangzhou --status closed
  nat-fw-switch.sh query --nat-gateway-id ngw-bp1xxxx
  nat-fw-switch.sh enable --proxy-ids "proxy-bp1xxxx"
  nat-fw-switch.sh disable --proxy-ids "proxy-bp1xxxx,proxy-bp2yyyy"
  nat-fw-switch.sh enable --proxy-ids "proxy-bp1xxxx" --dry-run

EXIT CODES:
  0  Success
  1  Parameter validation error
  2  API call failed
EOF
  exit 0
}

# --- Subcommand: query ---
cmd_query() {
  local REGION="" STATUS="" NAT_GATEWAY_ID="" VPC_ID="" PROXY_ID="" PROXY_NAME=""
  local MEMBER_UID="" PAGE="1" PAGE_SIZE="10" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --region) arg_value "--region" "${@:2}"; REGION="$2"; shift 2 ;;
      --status) arg_value "--status" "${@:2}"; STATUS="$2"; shift 2 ;;
      --nat-gateway-id) arg_value "--nat-gateway-id" "${@:2}"; NAT_GATEWAY_ID="$2"; shift 2 ;;
      --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
      --proxy-id) arg_value "--proxy-id" "${@:2}"; PROXY_ID="$2"; shift 2 ;;
      --proxy-name) arg_value "--proxy-name" "${@:2}"; PROXY_NAME="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --page) arg_value "--page" "${@:2}"; PAGE="$2"; shift 2 ;;
      --page-size) arg_value "--page-size" "${@:2}"; PAGE_SIZE="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "nat-fw-switch.sh query" \
          "Query NAT firewall list and protection status" \
          "nat-fw-switch.sh query [options]" \
          "  --region <id>           Filter by region (e.g. cn-hangzhou)
  --status <status>       Filter: configuring, deleting, normal, abnormal,
                          opening, closing, closed
  --nat-gateway-id <id>   Filter by NAT gateway ID (ngw-xxxx)
  --vpc-id <id>           Filter by VPC ID (vpc-xxxx)
  --proxy-id <id>         Filter by NAT firewall ID (proxy-xxxx)
  --proxy-name <name>     Filter by NAT firewall name
  --member-uid <uid>      Member account UID
  --page <n>              Page number (default: 1)
  --page-size <n>         Items per page (default: 10, max: 50)
  --dry-run               Preview CLI command
  --help, -h              Show this help

  Each filter accepts a single value. For multi-region queries,
  make separate calls and let the Agent merge results.

  Status semantics:
    normal=protection enabled  closed=protection disabled
    opening=enabling  closing=disabling
    configuring=creating  deleting=deleting  abnormal=abnormal"
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  # Validate optional params if provided
  [[ -n "$REGION" ]] && validate_region "$REGION"
  [[ -n "$STATUS" ]] && validate_proxy_status "$STATUS"
  [[ -n "$NAT_GATEWAY_ID" ]] && validate_nat_gateway_id "$NAT_GATEWAY_ID"
  [[ -n "$VPC_ID" ]] && validate_vpc_id "$VPC_ID"
  [[ -n "$PROXY_ID" ]] && validate_proxy_id "$PROXY_ID"
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"

  if [[ "$PAGE_SIZE" -gt 50 ]]; then
    log_error "--page-size must not exceed 50 (API limit)"
    exit 1
  fi

  # Build CLI args
  local CLI_ARGS=(--PageNo "$PAGE" --PageSize "$PAGE_SIZE" --Lang zh)
  [[ -n "$REGION" ]] && CLI_ARGS+=(--RegionNo "$REGION")
  [[ -n "$STATUS" ]] && CLI_ARGS+=(--Status "$STATUS")
  [[ -n "$NAT_GATEWAY_ID" ]] && CLI_ARGS+=(--NatGatewayId "$NAT_GATEWAY_ID")
  [[ -n "$VPC_ID" ]] && CLI_ARGS+=(--VpcId "$VPC_ID")
  [[ -n "$PROXY_ID" ]] && CLI_ARGS+=(--ProxyId "$PROXY_ID")
  [[ -n "$PROXY_NAME" ]] && CLI_ARGS+=(--ProxyName "$PROXY_NAME")
  [[ -n "$MEMBER_UID" ]] && CLI_ARGS+=(--MemberUid "$MEMBER_UID")

  # Dry-run
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeSecurityProxy \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  # Execute
  local response exit_code=0
  response=$(call_cfw_api "DescribeSecurityProxy" "${CLI_ARGS[@]}") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  # Output raw API response — Agent parses the JSON (SecurityProxies array, TotalCount, etc.)
  output_success "$response"
}

# --- Subcommand: enable / disable ---
cmd_enable_disable() {
  local ACTION="$1"  # "enable" or "disable"
  shift

  local SWITCH_VALUE
  if [[ "$ACTION" == "enable" ]]; then
    SWITCH_VALUE="open"
  else
    SWITCH_VALUE="close"
  fi

  local PROXY_IDS="" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --proxy-ids) arg_value "--proxy-ids" "${@:2}"; PROXY_IDS="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        local action_cap="$(printf '%s' "${ACTION:0:1}" | tr '[:lower:]' '[:upper:]')${ACTION:1}"
        show_help "nat-fw-switch.sh ${ACTION}" \
          "${action_cap} protection for specified NAT firewalls" \
          "nat-fw-switch.sh ${ACTION} --proxy-ids <id1,id2,...>" \
          "  --proxy-ids <id1,id2,...>  Comma-separated NAT firewall IDs (required)
  --dry-run                  Preview CLI commands
  --help, -h                 Show this help

  WARNING: Switching a NAT firewall triggers a NAT route change and causes
  a 1~2 second interruption of long-lived connections (short connections
  are not affected). Perform this during off-peak hours."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "proxy-ids" "$PROXY_IDS" || exit 1
  for_each_csv "$PROXY_IDS" validate_proxy_id || exit 1

  # Collect trimmed IDs
  local ids=()
  local saved_ifs="${IFS-$' \t\n'}"
  IFS=','
  for id in $PROXY_IDS; do
    IFS="$saved_ifs"
    id=$(printf '%s' "$id" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -n "$id" ]] && ids+=("$id")
  done
  IFS="$saved_ifs"

  # Dry-run
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    local id
    # Guarded expansion: bash 3.2 (macOS default) aborts on "${arr[@]}" when the
    # array is empty under `set -u`.
    for id in ${ids[@]+"${ids[@]}"}; do
      echo "aliyun ${CFW_PRODUCT_CODE} SwitchSecurityProxy \\"
      echo "  --ProxyId '${id}' \\"
      echo "  --Switch '${SWITCH_VALUE}' \\"
      echo "  --Lang 'zh'"
    done
    exit 0
  fi

  # Execute — SwitchSecurityProxy accepts a single ProxyId per call; loop over IDs
  local action_label="$(printf '%s' "${ACTION:0:1}" | tr '[:lower:]' '[:upper:]')${ACTION:1}"
  log_warn "${action_label}: NAT route switching causes a 1~2 second interruption of long-lived connections."

  local succeeded=() failed_items="" id
  for id in ${ids[@]+"${ids[@]}"}; do
    log_info "${action_label} NAT firewall ${id} ..."
    local response exit_code=0
    response=$(call_cfw_api "SwitchSecurityProxy" --ProxyId "$id" --Switch "$SWITCH_VALUE" --Lang zh) || exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
      local err_code err_msg
      err_code=$(extract_api_error_code "$response")
      err_msg=$(extract_api_error_message "$response")
      diagnose_cfw_error "$err_code" "$err_msg"
      failed_items="${failed_items}{\"proxy_id\":\"${id}\",\"error_code\":\"${err_code:-UnknownError}\",\"error_message\":\"${err_msg:-API call failed}\"},"
    else
      local request_id
      request_id=$(extract_api_request_id "$response")
      succeeded+=("$id")
      log_info "Accepted: ${id} (RequestId: ${request_id:-})"
    fi
  done

  # Build success/failure summary.
  # NOTE: SwitchSecurityProxy does NOT validate proxy existence — an unknown
  # ProxyId also returns success. Always verify the final status with
  # 'nat-fw-switch.sh query --proxy-id <id>' after switching.
  failed_items="${failed_items%,}"
  cat <<EOF
{
  "success": true,
  "action": "${ACTION}",
  "switch": "${SWITCH_VALUE}",
  "succeeded": [$(printf '"%s",' "${succeeded[@]}" | sed 's/,$//')],
  "failed": [${failed_items}],
  "note": "API accepts unknown proxy IDs silently — verify final status with query"
}
EOF

  if [[ -n "$failed_items" ]]; then
    exit 2
  fi
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
  *)
    log_error "Unknown subcommand: ${SUBCOMMAND}"
    log_error "Run 'nat-fw-switch.sh --help' for usage"
    exit 1
    ;;
esac
