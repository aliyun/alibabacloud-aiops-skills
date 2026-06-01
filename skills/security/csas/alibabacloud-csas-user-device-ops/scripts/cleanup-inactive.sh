#!/usr/bin/env bash
# cleanup-inactive.sh - Lock inactive terminal devices (reversible, idempotent)
#
# Scans all devices, identifies those with UpdateTime older than --days threshold,
# and locks them using update-user-devices-status --device-action Locked.
#
# Three-phase workflow:
#   1. --dry-run: Preview devices that would be locked
#   2. (no flag): Refuse to execute, prompt for --yes
#   3. --yes: Execute batch lock
#
# Usage:
#   bash scripts/cleanup-inactive.sh --days N [--dry-run | --yes] [OPTIONS]

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# ============================================================
# Parameters
# ============================================================

days=""
max_days=""
dry_run=false
confirm=false
PAGE_SIZE="$DEFAULT_PAGE_SIZE"
help=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days) days="$2"; shift 2 ;;
    --max-days) max_days="$2"; shift 2 ;;
    --dry-run) dry_run=true; shift ;;
    --yes) confirm=true; shift ;;
    --page-size) PAGE_SIZE="$2"; shift 2 ;;
    --help|-h) help=true; shift ;;
    *) log_error "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ "$help" == "true" ]]; then
  show_help "cleanup-inactive.sh" \
    "Lock inactive terminal devices (reversible via unlock, idempotent)" \
    "bash scripts/cleanup-inactive.sh --days N [--max-days M] [--dry-run | --yes]" \
    "  --days N      Inactivity threshold in days (>=1, required)
  --max-days M  Upper bound (optional). Selects devices with last_active
                between (today - max_days) and (today - days).
  --dry-run     Preview only, no changes made
  --yes         Confirm and execute the lock operation
  --page-size N Page size for device scan (default: 100, max: 500)
  --help, -h    Show this help message"
fi

# Validate parameters
validate_required "days" "$days" || exit 1
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
# Lock devices in batches
# ============================================================

# Lock a batch of devices by DeviceTag (reversible via Unlocked action).
# Accepts device_tags array by name; processes in batches of MAX_BATCH_SIZE.
# Outputs locked_count to stdout. Returns 0 if all succeeded, 1 if any failed.
lock_devices() {
  local -n _tags_ref="$1"
  local total=${#_tags_ref[@]}

  if [[ "$total" -eq 0 ]]; then
    echo "0"
    return 0
  fi

  local locked=0 failed=0
  local batch_start=0

  while [[ $batch_start -lt $total ]]; do
    local batch_tags=()
    local batch_end=$((batch_start + MAX_BATCH_SIZE))
    [[ $batch_end -gt $total ]] && batch_end=$total

    for ((j=batch_start; j<batch_end; j++)); do
      batch_tags+=("${_tags_ref[$j]}")
    done

    local batch_count=$((batch_end - batch_start))
    log_info "Locking device batch: ${batch_count} devices (${batch_start}..${batch_end}/${total})"

    if call_csas_api update-user-devices-status \
        --device-action Locked --device-tags "${batch_tags[@]}" >/dev/null 2>&1; then
      locked=$((locked + batch_count))
    else
      failed=$((failed + batch_count))
      log_error "Batch lock failed for ${batch_count} devices"
    fi

    batch_start=$batch_end
  done

  echo "$locked"
  [[ $failed -gt 0 ]] && return 1
  return 0
}

# ============================================================
# Main workflow
# ============================================================

cutoff_date=$(get_date_days_ago "$days")
cutoff_max_date=""
if [[ -n "$max_days" ]]; then
  cutoff_max_date=$(get_date_days_ago "$max_days")
  log_info "Device cleanup: range=${days}d~${max_days}d, window=${cutoff_max_date}~${cutoff_date}"
else
  log_info "Device cleanup: inactive threshold=${days}d, cutoff=${cutoff_date}"
fi

# Step 1: Scan ALL devices (reverse traversal, O(D) complexity)
log_info "Scanning all devices..."
raw=$(paginate_api list-user-devices) || {
  output_error "ApiCallFailed" "Failed to list devices"
  exit 2
}
total_scanned=$(paginate_total "$raw")
all_devices=$(paginate_body "$raw")

if [[ "$total_scanned" -eq 0 ]]; then
  cat <<EOF
{
  "success": true,
  "mode": "dry_run",
  "threshold_days": ${days},
  "cutoff_date": "${cutoff_date}",
  "total_devices_scanned": 0,
  "inactive_devices": 0,
  "devices": [],
  "summary": "No devices found in SASE"
}
EOF
  exit 0
fi

log_info "Scanned ${total_scanned} devices, filtering by cutoff=${cutoff_date}..."

# Extract parallel arrays
tags=(); usernames=(); hostnames=(); types=(); update_times=()
while IFS= read -r v; do tags+=("$v"); done < <(json_extract_all "$all_devices" "DeviceTag")
while IFS= read -r v; do usernames+=("$v"); done < <(json_extract_all "$all_devices" "Username")
while IFS= read -r v; do hostnames+=("$v"); done < <(json_extract_all "$all_devices" "Hostname")
while IFS= read -r v; do types+=("$v"); done < <(json_extract_all "$all_devices" "DeviceType")
while IFS= read -r v; do update_times+=("$v"); done < <(json_extract_all "$all_devices" "UpdateTime")

# Step 2: Classify inactive devices
inactive_tags=(); inactive_users=(); inactive_hosts=(); inactive_types=(); inactive_times=()

for i in "${!tags[@]}"; do
  ut="${update_times[$i]:-}"
  is_inactive=false
  if [[ -z "$ut" ]]; then
    [[ -z "$cutoff_max_date" ]] && is_inactive=true
  else
    update_date="${ut:0:10}"
    if [[ -n "$cutoff_max_date" ]]; then
      [[ ! "$update_date" < "$cutoff_max_date" && "$update_date" < "$cutoff_date" ]] && is_inactive=true
    else
      [[ "$update_date" < "$cutoff_date" ]] && is_inactive=true
    fi
  fi

  if [[ "$is_inactive" == "true" ]]; then
    inactive_tags+=("${tags[$i]}")
    inactive_users+=("${usernames[$i]:-unknown}")
    inactive_hosts+=("${hostnames[$i]:-unknown}")
    inactive_types+=("${types[$i]:-unknown}")
    inactive_times+=("${ut:-never}")
  fi
done

inactive_count=${#inactive_tags[@]}
log_info "Found ${inactive_count} inactive devices out of ${total_scanned}"

# Step 3: Dry-run or no --yes → output preview
if [[ "$dry_run" == "true" || "$confirm" != "true" ]]; then
  devices_json=""
  for i in "${!inactive_tags[@]}"; do
    [[ -n "$devices_json" ]] && devices_json+=","
    devices_json+="
    {
      \"device_tag\": \"${inactive_tags[$i]}\",
      \"username\": \"$(json_escape "${inactive_users[$i]}")\",
      \"hostname\": \"$(json_escape "${inactive_hosts[$i]}")\",
      \"device_type\": \"${inactive_types[$i]}\",
      \"last_active\": \"${inactive_times[$i]}\"
    }"
  done

  cat <<EOF
{
  "success": true,
  "mode": "dry_run",
  "threshold_days": ${days},
  "cutoff_date": "${cutoff_date}",
  "total_devices_scanned": ${total_scanned},
  "inactive_devices": ${inactive_count},
  "planned_action": "lock (reversible via unlock)",
  "devices": [${devices_json}
  ],
  "action_required": "pass --yes to execute lock operation"
}
EOF
  exit 0
fi

# Step 4: Execute with --yes — lock inactive devices
log_info "Locking ${inactive_count} inactive devices..."
locked=$(lock_devices inactive_tags) || true
lock_rc=$?
failed_count=$((inactive_count - locked))

failures_json=""
if [[ $lock_rc -ne 0 ]]; then
  failures_json="\"Some device batches failed to lock (${failed_count} devices)\""
fi

# Step 5: Output execution summary
cat <<EOF
{
  "success": true,
  "mode": "execute",
  "threshold_days": ${days},
  "cutoff_date": "${cutoff_date}",
  "summary": {
    "total_devices_scanned": ${total_scanned},
    "inactive_devices": ${inactive_count},
    "devices_locked": ${locked},
    "devices_lock_failed": ${failed_count}
  },
  "failures": [${failures_json}],
  "note": "Lock is reversible. Use 'aliyun csas update-user-devices-status --device-action Unlocked --device-tags ...' to unlock."
}
EOF
