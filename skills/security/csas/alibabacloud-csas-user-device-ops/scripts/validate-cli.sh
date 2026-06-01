#!/usr/bin/env bash
# validate-cli.sh - Validate Aliyun CLI environment for SASE operations
#
# Checks:
#   1. aliyun CLI installed
#   2. Version >= 3.3.3
#   3. Auto-plugin-install enabled + plugin update
#   4. Credentials configured
#   5. Permission probe (optional, --check-permission)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# ============================================================
# Version comparison (semver)
# ============================================================

version_gte() {
  local v1="$1" v2="$2"
  local IFS='.'
  local -a a1=($v1) a2=($v2)
  for i in 0 1 2; do
    local n1="${a1[$i]:-0}" n2="${a2[$i]:-0}"
    if [[ "$n1" -gt "$n2" ]]; then return 0; fi
    if [[ "$n1" -lt "$n2" ]]; then return 1; fi
  done
  return 0
}

# ============================================================
# Main
# ============================================================

check_permission=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-permission) check_permission=true; shift ;;
    --help|-h)
      show_help "validate-cli.sh" \
        "Validate Aliyun CLI environment for SASE operations" \
        "bash scripts/validate-cli.sh [--check-permission]" \
        "  --check-permission  Run RAM permission probe (default: skip)
  --help, -h          Show this help message"
      ;;
    *) log_error "Unknown option: $1"; exit 1 ;;
  esac
done

checks_json=""
all_passed=true

# --- Check 1: CLI installed ---
cli_path=$(command -v aliyun 2>/dev/null || true)
if [[ -z "$cli_path" ]]; then
  checks_json+="\"cli_installed\": { \"passed\": false, \"message\": \"aliyun CLI not found in PATH\" },"
  all_passed=false
  # Cannot proceed without CLI
  cat <<EOF
{
  "success": false,
  "checks": { ${checks_json%,} },
  "message": "aliyun CLI not installed. See references/cli-installation-guide.md"
}
EOF
  exit 1
fi

# --- Check 2: Version >= 3.3.3 ---
cli_version=$(aliyun version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)
if [[ -z "$cli_version" ]]; then
  checks_json+="\"cli_installed\": { \"passed\": true },"
  checks_json+="\"cli_version_ok\": { \"passed\": false, \"message\": \"Unable to determine version\" },"
  all_passed=false
elif version_gte "$cli_version" "3.3.3"; then
  checks_json+="\"cli_installed\": { \"passed\": true, \"version\": \"${cli_version}\" },"
  checks_json+="\"cli_version_ok\": { \"passed\": true, \"version\": \"${cli_version}\" },"
else
  checks_json+="\"cli_installed\": { \"passed\": true, \"version\": \"${cli_version}\" },"
  checks_json+="\"cli_version_ok\": { \"passed\": false, \"version\": \"${cli_version}\", \"required\": \"3.3.3\" },"
  all_passed=false
fi

# --- Check 3: Enable auto-plugin-install and update ---
aliyun configure set --auto-plugin-install true >/dev/null 2>&1 || true
log_info "Auto-plugin-install enabled"

plugin_update_ok=true
if ! aliyun plugin update >/dev/null 2>&1; then
  plugin_update_ok=false
  log_warn "Plugin update failed (non-critical)"
fi
checks_json+="\"plugin_setup\": { \"passed\": ${plugin_update_ok}, \"auto_install\": true },"

# --- Check 4: Credentials configured ---
profile_output=$(aliyun configure list 2>/dev/null || true)
if echo "$profile_output" | grep -qE '(AK|StsToken|RamRoleArn|EcsRamRole)'; then
  current_profile=$(echo "$profile_output" | grep '\*' | awk '{print $1}' || echo "default")
  checks_json+="\"credential_configured\": { \"passed\": true, \"profile\": \"${current_profile}\" },"
else
  checks_json+="\"credential_configured\": { \"passed\": false, \"message\": \"No valid profile found\" },"
  all_passed=false
fi

# --- Check 5: Permission probe (optional) ---
if [[ "$check_permission" == "true" ]]; then
  if aliyun csas list-users --current-page 1 --page-size 1 >/dev/null 2>&1; then
    checks_json+="\"permission_check\": { \"passed\": true },"
  else
    checks_json+="\"permission_check\": { \"passed\": false, \"message\": \"Permission denied or API error. See references/ram-policies.md\" },"
    all_passed=false
  fi
fi

# --- Output result ---
cat <<EOF
{
  "success": ${all_passed},
  "checks": { ${checks_json%,} }
}
EOF

if [[ "$all_passed" == "true" ]]; then
  exit 0
else
  exit 1
fi
