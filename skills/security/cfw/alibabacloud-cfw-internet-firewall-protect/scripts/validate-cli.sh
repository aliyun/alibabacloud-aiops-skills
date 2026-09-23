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
   /bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
   Routine updates afterwards: aliyun upgrade --yes

2. Verify installation:
   aliyun version

3. Configure credentials (do this outside the Agent session):
   aliyun configure
   Obtain credentials from the RAM console: https://ram.console.aliyun.com/manage/ak
   The CLI then resolves them automatically via its default credential chain —
   this Skill never reads, echoes, or handles credentials itself.

4. Optional — auto-install missing plugins (local, idempotent convenience switch):
   aliyun configure set --auto-plugin-install true
   The CLI cannot read this setting back, so validate-cli.sh reports it as
   "unknown" rather than "false"; not enabling it does not break this Skill.

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
      log_warn "CLI version ${CLI_VERSION} is below minimum ${MIN_CLI_VERSION}. Run: aliyun upgrade --yes (or reinstall via the setup.sh command in --install-guide)"
    fi
  fi
else
  log_warn "Alibaba Cloud CLI not installed. Install it with the setup.sh command shown by: bash scripts/validate-cli.sh --install-guide"
fi

# --- Check auto plugin install ---
# NOTE: this setting cannot actually be read back. It lives per-profile inside
# ~/.aliyun/config.json, but `aliyun configure list` only prints the profile
# table (Profile | Credential | Valid | Region | Language) and never mentions it,
# and `aliyun configure get` returns empty for both the kebab and snake spelling.
# Grepping the config file directly would be ambiguous across profiles, so rather
# than always reporting a wrong "false" (which made every run re-apply the set
# command), report "unknown" and let the caller decide. Enabling it is a local,
# idempotent convenience setting — not a prerequisite for this Skill.
AUTO_PLUGIN_INSTALL="not_checked"
if [[ "$CLI_INSTALLED" == "true" ]]; then
  AUTO_PLUGIN_INSTALL="unknown"
  log_info "Auto plugin install state is not readable from the CLI (reported as unknown). To enable it once: aliyun configure set --auto-plugin-install true"
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
# This is a real cloud call, so it carries the same session-scoped User-Agent as
# every other call: a permission probe missing from the session trace would leave
# a gap in exactly the diagnostic trail this script exists to produce.
check_cfw_permission() {
  if [[ -z "${SKILL_SESSION_ID:-}" ]]; then
    log_warn "SKILL_SESSION_ID is not set; skipping the CFW permission check rather than issuing an unattributed API call"
    printf 'skipped_no_session'
    return 0
  fi

  local skill_version
  if ! skill_version=$(resolve_skill_version); then
    printf 'skipped_no_version'
    return 0
  fi

  local out rc=0
  out=$(aliyun "$CFW_PRODUCT_CODE" DescribeAssetList \
    --CurrentPage 1 --PageSize 1 --Lang zh \
    --read-timeout "$DEFAULT_READ_TIMEOUT" \
    --connect-timeout "$DEFAULT_CONNECT_TIMEOUT" \
    --user-agent "${SKILL_UA_PREFIX}/${SKILL_SESSION_ID} skill-version/${skill_version}" 2>&1) || rc=$?
  printf '%s' "$out"
  return $rc
}

PERMISSION_OK="not_checked"
ACCOUNT_ID=""
if [[ "$CHECK_PERMISSION" == "true" ]]; then
  if [[ "$CREDENTIAL_VALID" == "true" ]]; then
    perm_result=$(check_cfw_permission) || true
    case "$perm_result" in
      skipped_no_session|skipped_no_version)
        PERMISSION_OK="skipped"
        CREDENTIAL_ERROR="AttributionUnavailable"
        ;;
      *)
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
        ;;
    esac
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
