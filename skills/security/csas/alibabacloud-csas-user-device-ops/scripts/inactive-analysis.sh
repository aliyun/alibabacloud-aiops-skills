#!/usr/bin/env bash
# inactive-analysis.sh - Analyze inactive devices
#
# Read-only analysis: identifies devices that have not been active
# within the specified threshold. No write operations are performed.
#
# Usage:
#   bash scripts/inactive-analysis.sh --days N [--max-days M] [OPTIONS]

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# ============================================================
# Parameters
# ============================================================

days=30
max_days=""
department=""
device_type=""
PAGE_SIZE="$DEFAULT_PAGE_SIZE"
help=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days) days="$2"; shift 2 ;;
    --max-days) max_days="$2"; shift 2 ;;
    --department) department="$2"; shift 2 ;;
    --device-type) device_type="$2"; shift 2 ;;
    --page-size) PAGE_SIZE="$2"; shift 2 ;;
    --help|-h) help=true; shift ;;
    *) log_error "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ "$help" == "true" ]]; then
  show_help "inactive-analysis.sh" \
    "Analyze inactive devices (read-only)" \
    "bash scripts/inactive-analysis.sh --days N [--max-days M] [OPTIONS]" \
    "  --days N            Inactivity threshold in days (>=1, default: 30)
  --max-days M        Upper bound of inactivity window (optional)
                      When set, only devices with last_active between
                      (today - max_days) and (today - days) are selected.
  --department DEPT   Filter by department
  --device-type TYPE  Filter by device type
  --page-size N       Page size for API calls (default: 100, max: 500)
  --help, -h          Show this help message"
fi

# Validate parameters
validate_days "$days" || exit 1
if [[ -n "$max_days" ]]; then
  validate_days "$max_days" || exit 1
  if [[ "$max_days" -le "$days" ]]; then
    log_error "--max-days (${max_days}) must be greater than --days (${days})"
    exit 1
  fi
fi
validate_page_size "$PAGE_SIZE" || exit 1

# ============================================================
# Calculate cutoff date(s)
# ============================================================

cutoff_date=$(get_date_days_ago "$days")
cutoff_max_date=""
if [[ -n "$max_days" ]]; then
  cutoff_max_date=$(get_date_days_ago "$max_days")
  log_info "Inactive analysis: range=${days}d~${max_days}d, window=${cutoff_max_date}~${cutoff_date}"
else
  log_info "Inactive analysis: threshold=${days}d, cutoff=${cutoff_date}"
fi

# ============================================================
# Analyze inactive DEVICES
# ============================================================

analyze_devices() {
  local dev_args=()
  [[ -n "$device_type" ]] && dev_args+=(--device-types "$device_type")
  [[ -n "$department" ]] && dev_args+=(--department "$department")

  local raw
  raw=$(paginate_api list-user-devices "${dev_args[@]+"${dev_args[@]}"}") || {
    output_error "ApiCallFailed" "Failed to list devices"
    return 2
  }
  local total_scanned
  total_scanned=$(paginate_total "$raw")
  local all_devices
  all_devices=$(paginate_body "$raw")

  if [[ "$total_scanned" -eq 0 ]]; then
    echo "\"device_analysis\": { \"total_scanned\": 0, \"inactive_devices\": 0, \"devices\": [] }"
    return 0
  fi

  # Extract fields
  local tags=() usernames=() hostnames=() types=() update_times=() departments=()
  while IFS= read -r v; do tags+=("$v"); done < <(json_extract_all "$all_devices" "DeviceTag")
  while IFS= read -r v; do usernames+=("$v"); done < <(json_extract_all "$all_devices" "Username")
  while IFS= read -r v; do hostnames+=("$v"); done < <(json_extract_all "$all_devices" "Hostname")
  while IFS= read -r v; do types+=("$v"); done < <(json_extract_all "$all_devices" "DeviceType")
  while IFS= read -r v; do update_times+=("$v"); done < <(json_extract_all "$all_devices" "UpdateTime")
  while IFS= read -r v; do departments+=("$v"); done < <(json_extract_all "$all_devices" "Department")

  # Filter inactive devices
  local inactive_json="" inactive_count=0
  for i in "${!tags[@]}"; do
    local ut="${update_times[$i]:-}"
    local is_inactive=false
    if [[ -z "$ut" ]]; then
      # No UpdateTime: treat as inactive (only when no --max-days range)
      [[ -z "$cutoff_max_date" ]] && is_inactive=true
    else
      local update_date="${ut:0:10}"
      if [[ -n "$cutoff_max_date" ]]; then
        # Range mode: cutoff_max_date <= update_date < cutoff_date
        [[ ! "$update_date" < "$cutoff_max_date" && "$update_date" < "$cutoff_date" ]] && is_inactive=true
      else
        # Threshold mode: update_date < cutoff_date
        [[ "$update_date" < "$cutoff_date" ]] && is_inactive=true
      fi
    fi

    if [[ "$is_inactive" == "true" ]]; then
      inactive_count=$((inactive_count + 1))
      [[ -n "$inactive_json" ]] && inactive_json+=","
      inactive_json+="
      {
        \"device_tag\": \"${tags[$i]}\",
        \"username\": \"$(json_escape "${usernames[$i]:-unknown}")\",
        \"hostname\": \"$(json_escape "${hostnames[$i]:-unknown}")\",
        \"department\": \"$(json_escape "${departments[$i]:-}")\",
        \"device_type\": \"${types[$i]:-unknown}\",
        \"last_active\": \"${ut:-never}\"
      }"
    fi
  done

  echo "\"device_analysis\": { \"total_scanned\": ${total_scanned}, \"inactive_devices\": ${inactive_count}, \"devices\": [${inactive_json}] }"
}

# ============================================================
# Main Output
# ============================================================

device_result=$(analyze_devices) || exit $?

cat <<EOF
{
  "success": true,
  "threshold_days": ${days},
  "max_days": ${max_days:-null},
  "cutoff_date": "${cutoff_date}",
  "cutoff_max_date": "${cutoff_max_date:-null}",
  ${device_result},
  "note": "This is a read-only analysis. Use cleanup-inactive.sh to lock devices, or visit SASE console for user/device deletion."
}
EOF
