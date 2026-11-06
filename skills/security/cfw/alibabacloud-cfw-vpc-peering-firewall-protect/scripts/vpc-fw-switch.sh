#!/usr/bin/env bash
# vpc-fw-switch.sh - Query and toggle Cloud Firewall VPC boundary firewall
# (Express Connect / VPC peering) protection switches.
# Part of alibabacloud-cfw-vpc-peering-firewall-protect skill
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin
#
# Subcommands:
#   query   - Query VPC firewall list and status (DescribeVpcFirewallList)
#   detail  - Query one VPC firewall detail (DescribeVpcFirewallDetail)
#   enable  - Enable protection for specified VPC firewalls (ModifyVpcFirewallSwitchStatus open)
#   disable - Disable protection for specified VPC firewalls (ModifyVpcFirewallSwitchStatus close)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# --- Main Help ---
show_main_help() {
  cat >&2 <<'EOF'
vpc-fw-switch.sh - Query and toggle Cloud Firewall VPC boundary firewall switches
                   (Express Connect / VPC peering)

USAGE:
  vpc-fw-switch.sh <subcommand> [options]

SUBCOMMANDS:
  query    Query VPC firewall list and protection status
  detail   Query one VPC firewall detail (local/peer VPC, ENI, route entries)
  enable   Enable protection for specified VPC firewalls
  disable  Disable protection for specified VPC firewalls

GLOBAL OPTIONS:
  --dry-run   Preview CLI command without executing
  --help, -h  Show help for the subcommand

EXAMPLES:
  vpc-fw-switch.sh query --region cn-hangzhou --status closed
  vpc-fw-switch.sh query --connect-subtype vpcpeer
  vpc-fw-switch.sh detail --vpc-firewall-id vfw-m5e7dbc4yxxxx
  vpc-fw-switch.sh enable --vpc-firewall-ids "vfw-m5e7dbc4yxxxx"
  vpc-fw-switch.sh disable --vpc-firewall-ids "vfw-aaa,vfw-bbb"
  vpc-fw-switch.sh enable --vpc-firewall-ids "vfw-aaa" --dry-run

EXIT CODES:
  0  Success
  1  Parameter validation error
  2  API call failed
EOF
  exit 0
}

# --- Subcommand: query ---
cmd_query() {
  local REGION="" STATUS="" VPC_ID="" FW_ID="" FW_NAME="" CONNECT_SUBTYPE="" PEER_UID=""
  local MEMBER_UID="" PAGE="1" PAGE_SIZE="10" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --region) arg_value "--region" "${@:2}"; REGION="$2"; shift 2 ;;
      --status) arg_value "--status" "${@:2}"; STATUS="$2"; shift 2 ;;
      --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
      --vpc-firewall-id) arg_value "--vpc-firewall-id" "${@:2}"; FW_ID="$2"; shift 2 ;;
      --vpc-firewall-name) arg_value "--vpc-firewall-name" "${@:2}"; FW_NAME="$2"; shift 2 ;;
      --connect-subtype) arg_value "--connect-subtype" "${@:2}"; CONNECT_SUBTYPE="$2"; shift 2 ;;
      --peer-uid) arg_value "--peer-uid" "${@:2}"; PEER_UID="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --page) arg_value "--page" "${@:2}"; PAGE="$2"; shift 2 ;;
      --page-size) arg_value "--page-size" "${@:2}"; PAGE_SIZE="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "vpc-fw-switch.sh query" \
          "Query VPC boundary firewall list and protection status" \
          "vpc-fw-switch.sh query [options]" \
          "  --region <id>              Filter by region of the local VPC (e.g. cn-hangzhou)
  --status <status>          Filter: opened, closed, notconfigured, configured
  --vpc-id <id>              Filter by (local) VPC ID (vpc-xxxx)
  --vpc-firewall-id <id>     Filter by VPC firewall ID (vfw-xxxx)
  --vpc-firewall-name <name> Filter by VPC firewall name
  --connect-subtype <type>   Filter: vpc2vpc (Express Connect) | vpcpeer (peering)
  --peer-uid <uid>           Filter by the peer VPC account UID
  --member-uid <uid>         Member account UID under a management account
  --page <n>                 Page number (default: 1)
  --page-size <n>            Items per page (default: 10, max: 50)
  --dry-run                  Preview CLI command
  --help, -h                 Show this help

  Each filter accepts a single value. For multi-region queries, make separate
  calls and let the Agent merge results.

  Status semantics:
    opened=protection on   closed=protection off
    notconfigured=no VPC firewall configured yet   configured=configured"
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  # Validate optional params if provided
  [[ -n "$REGION" ]] && validate_region "$REGION"
  [[ -n "$STATUS" ]] && validate_switch_status "$STATUS"
  [[ -n "$VPC_ID" ]] && validate_vpc_id "$VPC_ID"
  [[ -n "$FW_ID" ]] && validate_vpc_firewall_id "$FW_ID"
  [[ -n "$CONNECT_SUBTYPE" ]] && validate_connect_subtype "$CONNECT_SUBTYPE"
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"
  [[ -n "$PEER_UID" ]] && validate_member_uid "$PEER_UID"

  if [[ "$PAGE_SIZE" -gt 50 ]]; then
    log_error "--page-size must not exceed 50 (API limit)"
    exit 1
  fi

  # Build CLI args. NOTE: DescribeVpcFirewallList paginates with CurrentPage
  # (NOT PageNo) - unlike DescribeSecurityProxy.
  local CLI_ARGS=(--CurrentPage "$PAGE" --PageSize "$PAGE_SIZE" --Lang zh)
  [[ -n "$REGION" ]] && CLI_ARGS+=(--RegionNo "$REGION")
  [[ -n "$STATUS" ]] && CLI_ARGS+=(--FirewallSwitchStatus "$STATUS")
  [[ -n "$VPC_ID" ]] && CLI_ARGS+=(--VpcId "$VPC_ID")
  [[ -n "$FW_ID" ]] && CLI_ARGS+=(--VpcFirewallId "$FW_ID")
  [[ -n "$FW_NAME" ]] && CLI_ARGS+=(--VpcFirewallName "$FW_NAME")
  [[ -n "$CONNECT_SUBTYPE" ]] && CLI_ARGS+=(--ConnectSubType "$CONNECT_SUBTYPE")
  [[ -n "$PEER_UID" ]] && CLI_ARGS+=(--PeerUid "$PEER_UID")
  [[ -n "$MEMBER_UID" ]] && CLI_ARGS+=(--MemberUid "$MEMBER_UID")

  # Dry-run
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeVpcFirewallList \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  # Execute
  local response exit_code=0
  response=$(call_cfw_api "DescribeVpcFirewallList" "${CLI_ARGS[@]}") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

  # Output raw API response - Agent parses the JSON (VpcFirewalls array, TotalCount).
  output_success "$response"
}

# --- Subcommand: detail ---
cmd_detail() {
  local FW_ID="" LOCAL_VPC_ID="" PEER_VPC_ID="" DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vpc-firewall-id) arg_value "--vpc-firewall-id" "${@:2}"; FW_ID="$2"; shift 2 ;;
      --local-vpc-id) arg_value "--local-vpc-id" "${@:2}"; LOCAL_VPC_ID="$2"; shift 2 ;;
      --peer-vpc-id) arg_value "--peer-vpc-id" "${@:2}"; PEER_VPC_ID="$2"; shift 2 ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "vpc-fw-switch.sh detail" \
          "Query one VPC boundary firewall detail" \
          "vpc-fw-switch.sh detail --vpc-firewall-id <vfw-xxxx> [--local-vpc-id <id>] [--peer-vpc-id <id>]" \
          "  --vpc-firewall-id <id>  VPC firewall ID (vfw-xxxx, required)
  --local-vpc-id <id>     Local VPC ID (optional disambiguator)
  --peer-vpc-id <id>      Peer VPC ID (optional disambiguator)
  --dry-run               Preview CLI command
  --help, -h              Show this help

  Returns the local/peer VPC facts (ENI, router interface, CIDR/route tables),
  IPS config and ACL strict mode - the authoritative source for the route
  entries used by 'vpc-fw-lifecycle.sh update'."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "vpc-firewall-id" "$FW_ID" || exit 1
  validate_vpc_firewall_id "$FW_ID" || exit 1
  [[ -n "$LOCAL_VPC_ID" ]] && validate_vpc_id "$LOCAL_VPC_ID"
  [[ -n "$PEER_VPC_ID" ]] && validate_vpc_id "$PEER_VPC_ID"

  local CLI_ARGS=(--VpcFirewallId "$FW_ID" --Lang zh)
  [[ -n "$LOCAL_VPC_ID" ]] && CLI_ARGS+=(--LocalVpcId "$LOCAL_VPC_ID")
  [[ -n "$PEER_VPC_ID" ]] && CLI_ARGS+=(--PeerVpcId "$PEER_VPC_ID")

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeVpcFirewallDetail \\"
    for ((i=0; i<${#CLI_ARGS[@]}; i+=2)); do
      echo "  ${CLI_ARGS[$i]} '${CLI_ARGS[$((i+1))]}' \\"
    done
    exit 0
  fi

  local response exit_code=0
  response=$(call_cfw_api "DescribeVpcFirewallDetail" "${CLI_ARGS[@]}") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    exit 2
  fi

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

  local FW_IDS="" MEMBER_UID="" DRY_RUN=false YES=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vpc-firewall-ids) arg_value "--vpc-firewall-ids" "${@:2}"; FW_IDS="$2"; shift 2 ;;
      --member-uid) arg_value "--member-uid" "${@:2}"; MEMBER_UID="$2"; shift 2 ;;
      --yes|-y) YES=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        local action_cap
        action_cap="$(printf '%s' "${ACTION:0:1}" | tr '[:lower:]' '[:upper:]')${ACTION:1}"
        show_help "vpc-fw-switch.sh ${ACTION}" \
          "${action_cap} protection for specified VPC firewalls" \
          "vpc-fw-switch.sh ${ACTION} --vpc-firewall-ids <id1,id2,...> [--member-uid <uid>] [--yes]" \
          "  --vpc-firewall-ids <id1,id2,...>  Comma-separated VPC firewall IDs (required)
  --member-uid <uid>               Operate under a member account
  --yes                            Non-interactive confirmation for the write
  --dry-run                        Preview CLI commands
  --help, -h                       Show this help

  Without --yes this subcommand stops at a hard gate: it prints the impact
  preview and exits 2 with error_code=ConfirmationRequired, and calls nothing.

  WARNING: Opening/closing a VPC boundary firewall triggers route re-learning
  and takes about 5~30 minutes (depends on the route entry count). During the
  switch, long-lived connections suffer a second-level interruption (short
  connections are unaffected). Perform this during off-peak hours."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  validate_required "vpc-firewall-ids" "$FW_IDS" || exit 1
  for_each_csv "$FW_IDS" validate_vpc_firewall_id || exit 1
  [[ -n "$MEMBER_UID" ]] && validate_member_uid "$MEMBER_UID"

  # Collect trimmed IDs
  local ids=()
  local saved_ifs="${IFS-$' \t\n'}"
  IFS=','
  for id in $FW_IDS; do
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
      echo "aliyun ${CFW_PRODUCT_CODE} ModifyVpcFirewallSwitchStatus \\"
      echo "  --VpcFirewallId '${id}' \\"
      echo "  --FirewallSwitch '${SWITCH_VALUE}' \\"
      [[ -n "$MEMBER_UID" ]] && echo "  --MemberUid '${MEMBER_UID}' \\"
      echo "  --Lang 'zh'"
    done
    exit 0
  fi

  local action_label
  action_label="$(printf '%s' "${ACTION:0:1}" | tr '[:lower:]' '[:upper:]')${ACTION:1}"

  if [[ "$YES" != "true" ]]; then
    # HARD GATE. Switching re-learns routes for 5~30 minutes and flaps long-lived
    # connections, and this was the only write in the skill that ran without any
    # confirmation flag: one command from an Agent was enough to open or close a
    # real firewall. --dry-run above only prints commands; this branch is what
    # stops an unconfirmed write.
    local ids_csv="" switch_preview="" id gerund
    if [[ "$ACTION" == "enable" ]]; then gerund="Enabling"; else gerund="Disabling"; fi
    for id in ${ids[@]+"${ids[@]}"}; do
      ids_csv="${ids_csv:+${ids_csv},}${id}"
      switch_preview="${switch_preview:+${switch_preview} | }aliyun ${CFW_PRODUCT_CODE} ModifyVpcFirewallSwitchStatus --VpcFirewallId '${id}' --FirewallSwitch '${SWITCH_VALUE}' --Lang 'zh'"
    done
    log_warn "${action_label} is a write operation. NOTHING was switched."
    log_warn "  Present the impact preview to the user, get an explicit confirmation, then re-run the same command with --yes."
    cat <<EOF
{
  "success": false,
  "error_code": "ConfirmationRequired",
  "error_message": "${gerund} VPC firewall protection is a write operation. Review the impact preview, get explicit user confirmation, then re-run the same command with --yes.",
  "action": "$(json_escape "$ACTION")",
  "target_switch": "$(json_escape "$SWITCH_VALUE")",
  "vpc_firewall_ids": "$(json_escape "$ids_csv")",
  "affected_count": ${#ids[@]},
  "impact": "Route re-learning takes about 5~30 minutes and long-lived connections suffer a second-level interruption, so operate in an off-peak window. Closing stops inspection of the east-west traffic between the two VPCs but keeps the instance, its ACL policies and its IPS config; opening resumes inspection once the route re-learning completes.",
  "command_preview": "$(json_escape "$switch_preview")"
}
EOF
    exit 2
  fi

  # Execute - ModifyVpcFirewallSwitchStatus accepts a single VpcFirewallId per
  # call; loop over IDs.
  log_warn "${action_label}: VPC firewall switching re-learns routes and takes 5~30 minutes; long-lived connections flap for a few seconds."

  local succeeded=() failed_items="" id
  for id in ${ids[@]+"${ids[@]}"}; do
    log_info "${action_label} VPC firewall ${id} ..."
    local SWITCH_ARGS=(--VpcFirewallId "$id" --FirewallSwitch "$SWITCH_VALUE" --Lang zh)
    [[ -n "$MEMBER_UID" ]] && SWITCH_ARGS+=(--MemberUid "$MEMBER_UID")
    local response exit_code=0
    response=$(call_cfw_api "ModifyVpcFirewallSwitchStatus" "${SWITCH_ARGS[@]}") || exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
      local err_code err_msg
      err_code=$(extract_api_error_code "$response")
      err_msg=$(extract_api_error_message "$response")
      diagnose_cfw_error "$err_code" "$err_msg"
      failed_items="${failed_items}{\"vpc_firewall_id\":\"${id}\",\"error_code\":\"${err_code:-UnknownError}\",\"error_message\":\"${err_msg:-API call failed}\"},"
    else
      local request_id
      request_id=$(extract_api_request_id "$response")
      succeeded+=("$id")
      log_info "Accepted: ${id} (RequestId: ${request_id:-})"
    fi
  done

  # Build success/failure summary.
  # NOTE: ModifyVpcFirewallSwitchStatus returns a bare RequestId; it does not
  # prove the switch finished. The transition takes 5~30 minutes. Always verify
  # the final status with 'vpc-fw-switch.sh query --vpc-firewall-id <id>'.
  failed_items="${failed_items%,}"
  local succeeded_json=""
  if [[ ${#succeeded[@]} -gt 0 ]]; then
    succeeded_json=$(printf '"%s",' "${succeeded[@]}")
    succeeded_json="${succeeded_json%,}"
  fi

  # Derive "success" from the actual per-ID results. It must NEVER be a hardcoded
  # true: a caller that reads the JSON body (rather than the exit code) would
  # otherwise report "protection enabled" when every single ID failed.
  local ok_count=${#succeeded[@]}
  local fail_count=0
  if [[ -n "$failed_items" ]]; then
    fail_count=$(printf '%s' "$failed_items" | grep -o '"vpc_firewall_id"' | wc -l | tr -d ' ' || true)
  fi
  fail_count="${fail_count:-0}"

  local overall_success="false" note
  if [[ $ok_count -gt 0 && $fail_count -eq 0 ]]; then
    overall_success="true"
    note="Switch accepted for ${ok_count} firewall(s); route re-learning takes 5~30 minutes. Verify final status with query (opened/closed)."
  elif [[ $ok_count -gt 0 && $fail_count -gt 0 ]]; then
    note="PARTIAL FAILURE: ${ok_count} firewall(s) accepted, ${fail_count} rejected - see failed[]. The accepted ones are still re-learning routes (5~30 minutes); the rejected ones were NOT switched. Verify each ID with query and report the failures explicitly."
  elif [[ $fail_count -gt 0 ]]; then
    note="FAILURE: no firewall was switched (${fail_count} rejected) - see failed[]. Nothing changed; do NOT report the switch as applied."
  else
    note="No firewall IDs were processed; nothing changed."
  fi

  cat <<EOF
{
  "success": ${overall_success},
  "action": "${ACTION}",
  "firewall_switch": "${SWITCH_VALUE}",
  "succeeded": [${succeeded_json}],
  "failed": [${failed_items}],
  "succeeded_count": ${ok_count},
  "failed_count": ${fail_count},
  "note": "${note}"
}
EOF

  if [[ "$overall_success" != "true" ]]; then
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
  detail)
    cmd_detail "$@"
    ;;
  enable)
    cmd_enable_disable "enable" "$@"
    ;;
  disable)
    cmd_enable_disable "disable" "$@"
    ;;
  *)
    log_error "Unknown subcommand: ${SUBCOMMAND}"
    log_error "Run 'vpc-fw-switch.sh --help' for usage"
    exit 1
    ;;
esac
