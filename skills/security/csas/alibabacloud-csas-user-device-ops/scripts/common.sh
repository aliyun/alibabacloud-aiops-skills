#!/usr/bin/env bash
# common.sh - Shared utilities for SASE user & device operations
# Sourced by other scripts; do not execute directly.

# NOTE: Do not set shell options here. Each calling script sets its own
# (e.g. set -uo pipefail). This file is sourced as a library.

# ============================================================
# Constants
# ============================================================

readonly PRODUCT_CODE="csas"
readonly API_VERSION="2023-01-20"
readonly DEFAULT_PAGE_SIZE=100
readonly MAX_PAGE_SIZE=500
readonly MAX_BATCH_SIZE=100

# API timeout (seconds) — explicit to prevent indefinite hangs on network issues
readonly API_CONNECT_TIMEOUT=10
readonly API_READ_TIMEOUT=30

# ============================================================
# Logging
# ============================================================

log_info()  { echo "[INFO] $*" >&2; }
log_warn()  { echo "[WARN] $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

# ============================================================
# Validation Helpers
# ============================================================

# Validate --days parameter (positive integer, no upper limit)
validate_days() {
  local val="$1"
  if ! [[ "$val" =~ ^[0-9]+$ ]]; then
    log_error "Invalid --days value '${val}': must be a positive integer"
    return 1
  fi
  if [[ "$val" -lt 1 ]]; then
    log_error "Invalid --days value '${val}': must be >= 1"
    return 1
  fi
  return 0
}

# Validate a required parameter is non-empty
validate_required() {
  local name="$1" value="$2"
  if [[ -z "$value" ]]; then
    log_error "Missing required parameter: --${name}"
    return 1
  fi
  return 0
}

# Validate page-size (1-500)
validate_page_size() {
  local val="$1"
  if ! [[ "$val" =~ ^[0-9]+$ ]] || [[ "$val" -lt 1 || "$val" -gt $MAX_PAGE_SIZE ]]; then
    log_error "Invalid --page-size '${val}': must be between 1 and ${MAX_PAGE_SIZE}"
    return 1
  fi
  return 0
}

# ============================================================
# Date Helpers
# ============================================================

# Get ISO date string N days ago (YYYY-MM-DD)
get_date_days_ago() {
  local days="$1"
  if date --version >/dev/null 2>&1; then
    # GNU date
    date -d "-${days} days" '+%Y-%m-%d'
  else
    # BSD/macOS date
    date -v-"${days}"d '+%Y-%m-%d'
  fi
}

# ============================================================
# JSON Helpers (pure bash, no jq dependency)
# ============================================================

# Extract a single string field value from JSON
json_get_field() {
  local json="$1" field="$2"
  printf '%s' "$json" | grep -o "\"${field}\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" 2>/dev/null | head -1 | \
    sed "s/.*\"${field}\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/" || true
}

# Extract a numeric field value from JSON
json_get_number() {
  local json="$1" field="$2"
  printf '%s' "$json" | grep -o "\"${field}\"[[:space:]]*:[[:space:]]*[0-9]*" 2>/dev/null | head -1 | \
    sed "s/.*\"${field}\"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/" || true
}

# Extract all string values of a field from JSON (one per line)
json_extract_all() {
  local json="$1" field="$2"
  printf '%s\n' "$json" | \
    grep -o "\"${field}\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" 2>/dev/null | \
    sed "s/.*\"${field}\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/" || true
}

# Escape a string for safe JSON embedding
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

# ============================================================
# CLI Invocation (plugin mode)
# ============================================================

# Call a CSAS API using plugin mode (kebab-case)
# Usage: call_csas_api <kebab-case-command> [--param value ...]
# Example: call_csas_api list-user-devices --current-page 1 --page-size 100
call_csas_api() {
  local cmd="$1"
  shift
  aliyun csas "$cmd" \
    --connect-timeout "$API_CONNECT_TIMEOUT" \
    --read-timeout "$API_READ_TIMEOUT" \
    "$@" 2>/dev/null
}

# Paginate through a CSAS API, accumulating all JSON responses.
# First line of stdout is `__TOTAL__=N`, followed by concatenated JSON pages.
# Usage:
#   raw=$(paginate_api <command> [--param val ...]) || exit 2
#   total=$(paginate_total "$raw")
#   body=$(paginate_body "$raw")
paginate_api() {
  local cmd="$1"
  shift
  local p_size="${PAGE_SIZE:-$DEFAULT_PAGE_SIZE}"
  local page=1 total_pages=1 total=0
  local all=""

  while [[ $page -le $total_pages ]]; do
    local resp
    resp=$(call_csas_api "$cmd" --current-page "$page" --page-size "$p_size" "$@") || return 2

    if [[ $page -eq 1 ]]; then
      total=$(json_get_number "$resp" "TotalNum")
      total="${total:-0}"
      if [[ "$total" -eq 0 ]]; then
        printf '__TOTAL__=0\n%s' "$resp"
        return 0
      fi
      total_pages=$(( (total + p_size - 1) / p_size ))
      log_info "Total records: ${total}, pages: ${total_pages}"
    fi

    all+="${resp}"$'\n'

    if [[ $total_pages -gt 1 && $((page % 5)) -eq 0 ]]; then
      log_info "Fetched page ${page}/${total_pages}"
    fi
    page=$((page + 1))
  done

  printf '__TOTAL__=%s\n%s' "$total" "$all"
}

# Extract total from paginate_api output
paginate_total() {
  local raw="$1"
  local first_line="${raw%%$'\n'*}"
  echo "${first_line#__TOTAL__=}"
}

# Extract JSON body from paginate_api output (strips the __TOTAL__= header)
paginate_body() {
  local raw="$1"
  printf '%s' "${raw#*$'\n'}"
}

# ============================================================
# Output Helpers
# ============================================================

# Output a structured JSON error to stdout
output_error() {
  local code="$1" message="$2"
  cat <<EOF
{
  "success": false,
  "error": "${code}",
  "message": "$(json_escape "$message")"
}
EOF
}

# Show formatted help message and exit 0
show_help() {
  local cmd="$1" desc="$2" usage="$3" options="$4"
  cat >&2 <<EOF

${cmd} - ${desc}

Usage:
  ${usage}

Options:
${options}

EOF
  exit 0
}
