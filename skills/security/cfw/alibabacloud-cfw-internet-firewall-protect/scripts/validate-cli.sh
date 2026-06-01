#!/usr/bin/env bash
# validate-cli.sh - Check Alibaba Cloud CLI installation, credentials, and plugin configuration
# Part of alibabacloud-cfw-internet-firewall-protect skill
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin
#
# Covers: CLI installation, version check (>= 3.3.3), plugin setup,
#         credential validation, and CFW API permission check.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

readonly MIN_CLI_VERSION="3.3.3"

# --- Help ---
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  show_help "validate-cli.sh" \
    "Check Alibaba Cloud CLI installation and credential configuration" \
    "validate-cli.sh [--check-permission] [--install-guide]" \
    "  --check-permission  Verify CFW API access with a real read-only call
  --install-guide     Show CLI installation and setup instructions
  --help, -h          Show this help message"
fi

CHECK_PERMISSION=false
INSTALL_GUIDE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-permission) CHECK_PERMISSION=true; shift ;;
    --install-guide) INSTALL_GUIDE=true; shift ;;
    *) shift ;;
  esac
done

# --- Install Guide ---
if [[ "$INSTALL_GUIDE" == "true" ]]; then
  cat >&2 <<'GUIDE'
=== Alibaba Cloud CLI Installation & Setup Guide ===

1. Install CLI (>= 3.3.3):
   curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash

2. Verify installation:
   aliyun version

3. Configure credentials:
   aliyun configure
   (AccessKey from https://ram.console.aliyun.com/manage/ak)

4. Enable auto plugin install:
   aliyun configure set --auto-plugin-install true

5. Update all plugins:
   aliyun plugin update

6. Re-run this script to verify:
   bash scripts/validate-cli.sh --check-permission
GUIDE
  exit 0
fi

# --- Version comparison helper ---
# Returns 0 if $1 >= $2 (semver without 'v' prefix)
version_gte() {
  local v1="$1" v2="$2"
  # Strip any non-numeric prefix
  v1=$(printf '%s' "$v1" | sed 's/^[^0-9]*//')
  v2=$(printf '%s' "$v2" | sed 's/^[^0-9]*//')

  local IFS='.'
  local -a a1 a2
  read -r -a a1 <<< "$v1"
  read -r -a a2 <<< "$v2"

  local i
  for i in 0 1 2; do
    local n1="${a1[$i]:-0}" n2="${a2[$i]:-0}"
    # Strip non-numeric suffix (e.g. "3-beta" -> "3")
    n1=$(printf '%s' "$n1" | sed 's/[^0-9].*//')
    n2=$(printf '%s' "$n2" | sed 's/[^0-9].*//')
    [[ -z "$n1" ]] && n1=0
    [[ -z "$n2" ]] && n2=0
    if [[ "$n1" -gt "$n2" ]]; then return 0; fi
    if [[ "$n1" -lt "$n2" ]]; then return 1; fi
  done
  return 0
}

# --- Check CLI installation ---
CLI_INSTALLED=false
CLI_VERSION=""
CLI_VERSION_OK="not_checked"
if command -v aliyun &>/dev/null; then
  CLI_INSTALLED=true
  CLI_VERSION=$(aliyun version 2>/dev/null || echo "unknown")
  if [[ "$CLI_VERSION" != "unknown" ]]; then
    if version_gte "$CLI_VERSION" "$MIN_CLI_VERSION"; then
      CLI_VERSION_OK="true"
    else
      CLI_VERSION_OK="false"
      log_warn "CLI version ${CLI_VERSION} is below minimum ${MIN_CLI_VERSION}. Run: curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash"
    fi
  fi
else
  log_warn "Alibaba Cloud CLI not installed. Install with: curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash"
fi

# --- Check auto plugin install ---
AUTO_PLUGIN_INSTALL="not_checked"
if [[ "$CLI_INSTALLED" == "true" ]]; then
  auto_plugin=$(aliyun configure list 2>/dev/null | grep -i 'auto-plugin-install' || true)
  if printf '%s' "$auto_plugin" | grep -qi 'true'; then
    AUTO_PLUGIN_INSTALL="true"
  else
    AUTO_PLUGIN_INSTALL="false"
    log_warn "Auto plugin install is not enabled. Run: aliyun configure set --auto-plugin-install true"
  fi
fi

# --- Check profile ---
# `aliyun configure list` outputs a pipe-separated table:
#   Profile | Credential | Valid | Region | Language
# The current profile is the row whose first column ends with " *".
PROFILE_CONFIGURED=false
CURRENT_PROFILE=""
CURRENT_REGION=""
if [[ "$CLI_INSTALLED" == "true" ]]; then
  local_config=$(aliyun configure list 2>/dev/null || true)
  # Match the row whose first column ends with " *" (the active profile marker).
  # NOTE: a plain `grep '\*'` would also match Credential cells like `AK:***rpY`.
  current_line=$(printf '%s' "$local_config" | grep -E '^[^|]*\*[[:space:]]*\|' | head -1 || true)
  if [[ -n "$current_line" ]]; then
    PROFILE_CONFIGURED=true
    CURRENT_PROFILE=$(printf '%s' "$current_line" | awk -F'|' '{print $1}' | sed 's/\*//g; s/^[[:space:]]*//; s/[[:space:]]*$//')
    CURRENT_REGION=$(printf '%s' "$current_line" | awk -F'|' '{print $4}' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
  fi
fi

# --- Check credential configuration (no real API call) ---
# Per alicloud-skill-creator Principle 3: rely on `aliyun configure list` only.
# Real credential validity is verified later via the actual business API call
# in --check-permission, avoiding an extra cross-product (sts) invocation that
# would also break the plugin-mode requirement.
CREDENTIAL_VALID="not_checked"
CREDENTIAL_ERROR=""
if [[ "$CLI_INSTALLED" == "true" ]]; then
  if [[ "$PROFILE_CONFIGURED" == "true" ]]; then
    CREDENTIAL_VALID="true"
  else
    CREDENTIAL_VALID="false"
    CREDENTIAL_ERROR="NoProfileConfigured"
    log_warn "No profile configured. Run 'aliyun configure' to set up credentials."
  fi
fi

# --- Check CFW permission (optional, also doubles as real credential check) ---
PERMISSION_OK="not_checked"
ACCOUNT_ID=""
if [[ "$CHECK_PERMISSION" == "true" ]]; then
  if [[ "$CREDENTIAL_VALID" == "true" ]]; then
    perm_result=$(aliyun "$CFW_PRODUCT_CODE" DescribeAssetList --CurrentPage 1 --PageSize 1 --Lang zh 2>&1) || true
    if printf '%s' "$perm_result" | grep -q '"RequestId"'; then
      PERMISSION_OK="true"
      # Pull AliUid from the first asset if present (best-effort, optional)
      ACCOUNT_ID=$(printf '%s' "$perm_result" | grep -o '"AliUid"[[:space:]]*:[[:space:]]*[0-9]*' | head -1 | sed 's/.*: *//' || true)
    else
      PERMISSION_OK="false"
      err=$(printf '%s' "$perm_result" | grep -o 'ErrorCode: [^ ]*' | head -1 | sed 's/ErrorCode: //' || true)
      [[ -n "$err" ]] && CREDENTIAL_ERROR="$err"
      log_warn "CFW API call failed (ErrorCode: ${err:-unknown})."
      log_warn "This usually means invalid/expired credentials or missing yundun-cloudfirewall:DescribeAssetList permission."
      log_warn "Run 'aliyun configure' to reconfigure, or see references/ram-policies.md."
    fi
  else
    PERMISSION_OK="skipped"
    log_warn "Skipping CFW permission check — no profile configured."
  fi
fi

# --- Output ---
cat <<EOF
{
  "cli_installed": ${CLI_INSTALLED},
  "cli_version": "${CLI_VERSION}",
  "cli_version_ok": "${CLI_VERSION_OK}",
  "auto_plugin_install": "${AUTO_PLUGIN_INSTALL}",
  "profile_configured": ${PROFILE_CONFIGURED},
  "current_profile": "${CURRENT_PROFILE}",
  "current_region": "${CURRENT_REGION}",
  "credential_valid": "${CREDENTIAL_VALID}",
  "account_id": "${ACCOUNT_ID}",
  "credential_error": "${CREDENTIAL_ERROR}",
  "permission_check": "${PERMISSION_OK}"
}
EOF
