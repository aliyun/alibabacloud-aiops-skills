#!/usr/bin/env bash
# auto-protect.sh - Manage auto-protection settings for new assets
# Part of alibabacloud-cfw-internet-firewall-protect skill
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin
#   - python3 (>= 3.6) — used for JSON parsing and merging of API responses
#
# Subcommands:
#   query  - Query current auto-protection settings (DescribeResourceTypeAutoEnable)
#   modify - Modify auto-protection settings (ModifyResourceTypeAutoEnable)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# --- Main Help ---
show_main_help() {
  cat >&2 <<'EOF'
auto-protect.sh - Manage auto-protection settings for new assets

USAGE:
  auto-protect.sh <subcommand> [options]

SUBCOMMANDS:
  query   Query current auto-protection configuration
  modify  Modify auto-protection settings (incremental or full)

EXAMPLES:
  auto-protect.sh query
  auto-protect.sh modify --enable "EIP,NatEIP" --disable "SlbEIP" --yes
  auto-protect.sh modify --config '{"EIP":true,"NatEIP":false}' --yes

EXIT CODES:
  0  Success
  1  Parameter validation error
  2  API call failed
EOF
  exit 0
}

# --- Subcommand: query ---
cmd_query() {
  local DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "auto-protect.sh query" \
          "Query current auto-protection configuration" \
          "auto-protect.sh query [--dry-run]" \
          "  --dry-run   Preview CLI command
  --help, -h  Show this help"
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeResourceTypeAutoEnable \\"
    echo "  --Lang 'zh' \\"
    exit 0
  fi

  local response exit_code=0
  response=$(call_cfw_api "DescribeResourceTypeAutoEnable" --Lang zh) || exit_code=$?

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

# --- Subcommand: modify ---
cmd_modify() {
  local ENABLE_TYPES="" DISABLE_TYPES="" CONFIG_JSON="" REGION="" YES=false DRY_RUN=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --enable) ENABLE_TYPES="$2"; shift 2 ;;
      --disable) DISABLE_TYPES="$2"; shift 2 ;;
      --config) CONFIG_JSON="$2"; shift 2 ;;
      --region) REGION="$2"; shift 2 ;;
      --yes) YES=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      --help|-h)
        show_help "auto-protect.sh modify" \
          "Modify auto-protection settings for new assets" \
          "auto-protect.sh modify [options] --yes" \
          "  --enable <t1,t2,...>   Resource types to enable auto-protection
  --disable <t1,t2,...>  Resource types to disable auto-protection
  --config <json>        Full JSON config (mutually exclusive with --enable/--disable)
  --region <id>          Region filter (optional)
  --yes                  Confirm execution (required)
  --dry-run              Preview the merged config and CLI command
  --help, -h             Show this help

  Use --enable/--disable for incremental changes (reads current config, merges, writes).
  Use --config for full replacement with a JSON object."
        ;;
      *) log_error "Unknown option: $1"; exit 1 ;;
    esac
  done

  # Validate: must have some change to apply
  if [[ -z "$ENABLE_TYPES" && -z "$DISABLE_TYPES" && -z "$CONFIG_JSON" ]]; then
    log_error "At least one of --enable, --disable, or --config is required"
    exit 1
  fi

  # Validate: --config is mutually exclusive with --enable/--disable
  if [[ -n "$CONFIG_JSON" && ( -n "$ENABLE_TYPES" || -n "$DISABLE_TYPES" ) ]]; then
    log_error "--config cannot be used together with --enable/--disable"
    exit 1
  fi

  # Validate resource types in --enable/--disable
  if [[ -n "$ENABLE_TYPES" ]]; then
    local _ifs_save="${IFS-$' \t\n'}"
    IFS=','
    for rt in $ENABLE_TYPES; do
      IFS="$_ifs_save"
      rt=$(printf '%s' "$rt" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      [[ -n "$rt" ]] && validate_resource_type "$rt"
    done
    IFS="$_ifs_save"
  fi
  if [[ -n "$DISABLE_TYPES" ]]; then
    local _ifs_save="${IFS-$' \t\n'}"
    IFS=','
    for rt in $DISABLE_TYPES; do
      IFS="$_ifs_save"
      rt=$(printf '%s' "$rt" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      [[ -n "$rt" ]] && validate_resource_type "$rt"
    done
    IFS="$_ifs_save"
  fi

  [[ -n "$REGION" ]] && validate_region "$REGION"

  # Determine final config JSON
  local final_config=""

  if [[ -n "$CONFIG_JSON" ]]; then
    # Direct config mode
    final_config="$CONFIG_JSON"
  else
    # Incremental mode: read current → merge → write
    log_info "Reading current auto-protection settings..."
    local current_response current_exit=0
    current_response=$(call_cfw_api "DescribeResourceTypeAutoEnable" --Lang zh) || current_exit=$?

    if [[ $current_exit -ne 0 ]]; then
      local err_code err_msg
      err_code=$(extract_api_error_code "$current_response")
      err_msg=$(extract_api_error_message "$current_response")
      diagnose_cfw_error "$err_code" "$err_msg"
      output_error "${err_code:-UnknownError}" "Failed to read current config: ${err_msg:-unknown}"
      exit 2
    fi

    # Extract the ResourceTypeAutoEnable JSON object from response
    # The response is multi-line pretty-printed JSON; use python3 for reliable parsing.
    local current_config
    current_config=$(printf '%s' "$current_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    obj = data.get('ResourceTypeAutoEnable', {})
    print(json.dumps(obj, separators=(',', ':')))
except:
    print('{}')
" 2>/dev/null)

    if [[ -z "$current_config" || "$current_config" == "{}" ]]; then
      log_warn "Could not parse current config, starting with empty config"
      current_config="{}"
    fi

    # Apply --enable and --disable changes via python3 for reliable JSON manipulation
    final_config=$(printf '%s' "$current_config" | python3 -c "
import sys, json
config = json.load(sys.stdin)
enable_types = '${ENABLE_TYPES}'.strip()
disable_types = '${DISABLE_TYPES}'.strip()
if enable_types:
    for rt in enable_types.split(','):
        rt = rt.strip()
        if rt:
            config[rt] = True
if disable_types:
    for rt in disable_types.split(','):
        rt = rt.strip()
        if rt:
            config[rt] = False
print(json.dumps(config, separators=(',', ':')))
" 2>/dev/null)

    if [[ -z "$final_config" ]]; then
      log_error "Failed to merge config changes"
      output_error "ConfigMergeError" "Could not merge enable/disable types into current config"
      exit 1
    fi
  fi

  # Build CLI args
  local CLI_ARGS=(--ResourceTypeAutoEnable "$final_config" --Lang zh)
  [[ -n "$REGION" ]] && CLI_ARGS+=(--RegionNo "$REGION")

  # Dry-run
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry-run mode: showing merged config and command preview"
    log_info "Final config: ${final_config}"
    echo "aliyun ${CFW_PRODUCT_CODE} ModifyResourceTypeAutoEnable \\"
    echo "  --ResourceTypeAutoEnable '${final_config}' \\"
    echo "  --Lang 'zh' \\"
    [[ -n "$REGION" ]] && echo "  --RegionNo '${REGION}' \\"
    exit 0
  fi

  # Safety check
  if [[ "$YES" != "true" ]]; then
    log_error "Modifying auto-protection settings requires --yes to confirm."
    output_error "NotConfirmed" "Operation requires --yes flag to confirm"
    exit 1
  fi

  # Execute
  log_info "Modifying auto-protection settings..."
  local response exit_code=0
  response=$(call_cfw_api "ModifyResourceTypeAutoEnable" "${CLI_ARGS[@]}") || exit_code=$?

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
  "action": "modify-auto-protect",
  "applied_config": ${final_config},
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
  modify)
    cmd_modify "$@"
    ;;
  *)
    log_error "Unknown subcommand: ${SUBCOMMAND}"
    log_error "Run 'auto-protect.sh --help' for usage"
    exit 1
    ;;
esac
