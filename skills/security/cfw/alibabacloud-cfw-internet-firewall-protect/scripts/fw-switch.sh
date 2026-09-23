#!/usr/bin/env bash
# fw-switch.sh - Manage Cloud Firewall Internet Firewall protection switches
# Part of alibabacloud-cfw-internet-firewall-protect skill
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin
#   - python3 (>= 3.6) for JSON merging and CSV export (--all-pages / --export-csv only)
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
  fw-switch.sh query --status open --all-pages --export-csv ./protected-assets.csv
  fw-switch.sh query --new-resource-tag "discovered in 7 days"
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
  local ALL_PAGES=false EXPORT_CSV=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --region) REGION="$2"; shift 2 ;;
      --status) STATUS="$2"; shift 2 ;;
      --resource-type) RESOURCE_TYPE="$2"; shift 2 ;;
      --search) SEARCH="$2"; shift 2 ;;
      --ip-version) IP_VERSION="$2"; shift 2 ;;
      --member-uid) MEMBER_UID="$2"; shift 2 ;;
      --new-resource-tag) NEW_RESOURCE_TAG="$2"; shift 2 ;;
      --page) PAGE="$2"; shift 2 ;;
      --page-size) PAGE_SIZE="$2"; shift 2 ;;
      --all-pages) ALL_PAGES=true; shift ;;
      --export-csv) EXPORT_CSV="$2"; shift 2 ;;
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
  --new-resource-tag <v> Filter by asset discovery time. One of:
                         'discovered in 1 hour', 'discovered in 1 day',
                         'discovered in 7 days'
  --page <n>             Page number (default: 1)
  --page-size <n>        Items per page (default: 10)
  --all-pages            Fetch every page and merge into one result
  --export-csv <file>    Write results to a CSV file (UTF-8 with BOM, opens
                         directly in Excel). Prints an export summary instead
                         of the full asset JSON.
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
  [[ -n "$NEW_RESOURCE_TAG" ]] && validate_new_resource_tag "$NEW_RESOURCE_TAG"

  # --all-pages and --export-csv require python3 for JSON merging/CSV export
  if [[ "$ALL_PAGES" == "true" || -n "$EXPORT_CSV" ]]; then
    if ! command -v python3 &>/dev/null; then
      log_error "python3 is required for --all-pages and --export-csv but not found in PATH"
      exit 1
    fi
  fi

  # --all-pages always walks from page 1, so an explicit --page would be ignored.
  if [[ "$ALL_PAGES" == "true" && "$PAGE" != "1" ]]; then
    log_warn "--all-pages ignores --page ${PAGE}; pagination always starts from page 1"
  fi

  if [[ -n "$EXPORT_CSV" ]]; then
    local csv_dir
    csv_dir=$(dirname "$EXPORT_CSV")
    if [[ ! -d "$csv_dir" ]]; then
      log_error "Cannot write CSV: directory does not exist: ${csv_dir}"
      exit 1
    fi
  fi

  # Build CLI args shared by every page request (CurrentPage is added per call)
  local BASE_ARGS=(--PageSize "$PAGE_SIZE" --Lang zh)
  [[ -n "$REGION" ]] && BASE_ARGS+=(--RegionNo "$REGION")
  [[ -n "$STATUS" ]] && BASE_ARGS+=(--Status "$STATUS")
  [[ -n "$RESOURCE_TYPE" ]] && BASE_ARGS+=(--ResourceType "$RESOURCE_TYPE")
  [[ -n "$SEARCH" ]] && BASE_ARGS+=(--SearchItem "$SEARCH")
  [[ -n "$IP_VERSION" ]] && BASE_ARGS+=(--IpVersion "$IP_VERSION")
  [[ -n "$MEMBER_UID" ]] && BASE_ARGS+=(--MemberUid "$MEMBER_UID")
  [[ -n "$NEW_RESOURCE_TAG" ]] && BASE_ARGS+=(--NewResourceTag "$NEW_RESOURCE_TAG")

  # Dry-run
  if [[ "$DRY_RUN" == "true" ]]; then
    # --all-pages restarts from page 1, so preview that instead of --page.
    local preview_page="$PAGE"
    [[ "$ALL_PAGES" == "true" ]] && preview_page=1
    log_info "Dry-run mode: showing command preview"
    echo "aliyun ${CFW_PRODUCT_CODE} DescribeAssetList \\"
    echo "  --CurrentPage '${preview_page}' \\"
    for ((i=0; i<${#BASE_ARGS[@]}; i+=2)); do
      echo "  ${BASE_ARGS[$i]} '${BASE_ARGS[$((i+1))]}' \\"
    done
    [[ "$ALL_PAGES" == "true" ]] && log_info "--all-pages: would repeat the call for each page until TotalCount is reached"
    [[ -n "$EXPORT_CSV" ]] && log_info "--export-csv: would write results to ${EXPORT_CSV}"
    exit 0
  fi

  local merged
  [[ "$DRY_RUN" == "true" ]] || require_attribution
  if [[ "$ALL_PAGES" == "true" ]]; then
    # fetch_all_asset_pages runs in a subshell, so a failing page captures its
    # error JSON into $merged instead of reaching stdout — pass it through here.
    local rc=0
    merged=$(fetch_all_asset_pages "$PAGE_SIZE" "${BASE_ARGS[@]}") || rc=$?
    if [[ $rc -ne 0 ]]; then
      printf '%s\n' "$merged"
      exit $rc
    fi
  else
    query_asset_page "$PAGE" "${BASE_ARGS[@]}" || exit $?
    merged="$QUERY_PAGE_RESPONSE"
  fi

  # CSV export replaces the JSON dump — the caller asked for a file, and echoing
  # every asset back would bloat the Agent context for large audit exports.
  if [[ -n "$EXPORT_CSV" ]]; then
    local json_tmp row_count export_rc=0
    json_tmp=$(mktemp "${TMPDIR:-/tmp}/cfw-export.XXXXXX")
    printf '%s' "$merged" >"$json_tmp"
    row_count=$(export_assets_csv "$EXPORT_CSV" "$json_tmp") || export_rc=$?
    rm -f "$json_tmp"

    if [[ $export_rc -ne 0 ]]; then
      log_error "Failed to write CSV file: ${EXPORT_CSV}"
      output_error "ExportFailed" "Could not write CSV to ${EXPORT_CSV}"
      exit 1
    fi

    log_info "Exported ${row_count} assets to ${EXPORT_CSV}"
    # Emit the summary via python3 so the file path is JSON-escaped correctly —
    # a raw heredoc would break on paths containing quotes, backslashes, etc.
    python3 -c 'import json,sys; print(json.dumps({"success": True, "exported_file": sys.argv[1], "row_count": int(sys.argv[2])}, indent=2, ensure_ascii=False))' "$EXPORT_CSV" "$row_count"
    return 0
  fi

  # Output raw API response — Agent parses the JSON (Assets array, TotalCount, etc.)
  output_success "$merged"
}

# Query a single page. Sets QUERY_PAGE_RESPONSE on success.
# Uses a global instead of stdout so that a fatal API error can propagate the
# exit code to the caller (an `exit` inside $(...) would only kill the subshell).
QUERY_PAGE_RESPONSE=""
query_asset_page() {
  local page_no="$1"
  shift

  local response exit_code=0
  response=$(call_cfw_api "DescribeAssetList" --CurrentPage "$page_no" "$@") || exit_code=$?

  # 3 is call_cfw_api's "no attribution" code: a local configuration fault, not an
  # API failure, so surface it as such instead of running error-code diagnosis on it.
  if [[ $exit_code -eq 3 ]]; then
    output_error "AttributionRequired" "SKILL_SESSION_ID or references/manifest.json version is unavailable"
    return 3
  fi

  if [[ $exit_code -ne 0 ]]; then
    local err_code err_msg
    err_code=$(extract_api_error_code "$response")
    err_msg=$(extract_api_error_message "$response")
    diagnose_cfw_error "$err_code" "$err_msg"
    output_error "${err_code:-UnknownError}" "${err_msg:-API call failed}"
    return 2
  fi

  QUERY_PAGE_RESPONSE="$response"
}

# Walk every page and merge the Assets arrays into a single JSON document.
# Echoes the merged JSON on stdout.
# Usage: fetch_all_asset_pages <page_size> <BASE_ARGS...>
fetch_all_asset_pages() {
  local page_size="$1"
  shift
  # Guard the short-page fallback below against a non-numeric --page-size.
  [[ "$page_size" =~ ^[0-9]+$ && "$page_size" -gt 0 ]] || page_size=10

  local pages_dir
  pages_dir=$(mktemp -d "${TMPDIR:-/tmp}/cfw-query.XXXXXX")
  # shellcheck disable=SC2064
  trap "rm -rf '${pages_dir}'" RETURN

  local page_no=1 total=0 collected=0
  while :; do
    query_asset_page "$page_no" "$@" || return $?
    printf '%s' "$QUERY_PAGE_RESPONSE" >"${pages_dir}/page-$(printf '%05d' "$page_no").json"

    local stats page_count
    stats=$(printf '%s' "$QUERY_PAGE_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(int(data.get('TotalCount') or 0), len(data.get('Assets') or []))
except Exception:
    print(0, 0)
")
    total="${stats%% *}"
    page_count="${stats##* }"
    collected=$((collected + page_count))
    log_info "Fetched page ${page_no}: ${page_count} assets (collected ${collected}/${total})"

    # An empty page always marks the end.
    if [[ "$page_count" -eq 0 ]]; then
      break
    fi

    if [[ "$total" -gt 0 ]]; then
      # Normal case: TotalCount tells us when everything has been collected.
      [[ "$collected" -ge "$total" ]] && break
    elif [[ "$page_count" -lt "$page_size" ]]; then
      # TotalCount missing or zero — fall back to short-page detection so a
      # partial result is never returned silently.
      log_warn "Response had no usable TotalCount; stopped at page ${page_no} (returned fewer than ${page_size} assets). Verify the result is complete."
      break
    fi

    page_no=$((page_no + 1))
    if [[ "$page_no" -gt "$MAX_QUERY_PAGES" ]]; then
      log_warn "Stopped at the ${MAX_QUERY_PAGES}-page safety cap; the result may be incomplete"
      break
    fi
  done

  python3 - "$pages_dir" <<'PY'
import sys, os, json, glob

pages_dir = sys.argv[1]
assets, request_id, total = [], "", 0

for path in sorted(glob.glob(os.path.join(pages_dir, 'page-*.json'))):
    with open(path, encoding='utf-8') as fh:
        try:
            page = json.load(fh)
        except ValueError:
            continue
    assets.extend(page.get('Assets') or [])
    if not request_id:
        request_id = page.get('RequestId') or ""
    try:
        total = max(total, int(page.get('TotalCount') or 0))
    except (TypeError, ValueError):
        pass

print(json.dumps({
    'RequestId': request_id,
    'TotalCount': total,
    'Assets': assets,
}, ensure_ascii=False, indent=2))
PY
}

# Convert the Assets array of a JSON file into a CSV file. Echoes the row count.
# The JSON arrives as a file path, not on stdin — the heredoc below already
# occupies stdin to deliver the program text.
export_assets_csv() {
  local out_path="$1"
  local json_path="$2"

  python3 - "$out_path" "$json_path" <<'PY'
import sys, json, csv

out_path, json_path = sys.argv[1], sys.argv[2]
COLUMNS = [
    'InternetAddress', 'IntranetAddress', 'ProtectStatus', 'ResourceType',
    'RegionID', 'Name', 'BindInstanceId', 'BindInstanceName',
    'ResourceInstanceId', 'IpVersion', 'MemberUid',
]

try:
    with open(json_path, encoding='utf-8') as fh:
        data = json.load(fh)
except ValueError as exc:
    sys.stderr.write('[ERROR] Could not parse API response as JSON: %s\n' % exc)
    sys.exit(1)

assets = data.get('Assets') or []

# utf-8-sig writes a BOM so Excel renders Chinese instance names correctly
# instead of mojibake when the CSV is double-clicked open.
try:
    with open(out_path, 'w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        for asset in assets:
            writer.writerow(['' if asset.get(col) is None else asset.get(col) for col in COLUMNS])
except OSError as exc:
    sys.stderr.write('[ERROR] Could not write CSV file: %s\n' % exc)
    sys.exit(1)

print(len(assets))
PY
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
  [[ "$DRY_RUN" == "true" ]] || require_attribution
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
  # The aliyun CLI may pretty-print JSON across multiple lines, so collapse newlines
  # before extracting the array — grep -o only matches within a single line.
  local abnormal_list="[]"
  local flat_response
  flat_response=$(printf '%s' "$response" | tr '\n' ' ')
  if printf '%s' "$flat_response" | grep -q '"AbnormalResourceStatusList"'; then
    abnormal_list=$(printf '%s' "$flat_response" | grep -o '"AbnormalResourceStatusList"[[:space:]]*:[[:space:]]*\[[^]]*\]' | sed 's/"AbnormalResourceStatusList"[[:space:]]*:[[:space:]]*//' || echo "[]")
    [[ -z "$abnormal_list" ]] && abnormal_list="[]"
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
  require_attribution
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
