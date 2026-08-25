#!/usr/bin/env bash
# validate-cli.sh - Check Alibaba Cloud CLI installation, credentials, and plugin configuration
# Part of alibabacloud-cfw-nat-firewall-protect skill
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
    "validate-cli.sh [--check-permission] [--mode auto|manual] [--region <region>] [--install-guide]" \
    "  --check-permission  Verify CFW API access with a real read-only call
  --mode <auto|manual>
                      With --check-permission and mode=manual, additionally
                      probe the VPC write permissions required by manual-mode
                      preparation (CreateVSwitch/CreateRouteTable/
                      AssociateRouteTable + cleanup permissions). Probes use
                      fake resource IDs; nothing is created.
  --region <region>   Region used for manual-mode permission probes
                      (default: current profile region or cn-hangzhou)
  --install-guide     Show CLI installation and setup instructions
  --help, -h          Show this help message"
fi

CHECK_PERMISSION=false
INSTALL_GUIDE=false
MODE="auto"
PROBE_REGION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-permission) CHECK_PERMISSION=true; shift ;;
    --install-guide) INSTALL_GUIDE=true; shift ;;
    --mode)
      MODE="${2:-}"
      if [[ -z "$MODE" || "$MODE" == --* ]]; then
        log_error "Option --mode requires a value: auto or manual"
        exit 1
      fi
      if [[ "$MODE" == "manual" ]]; then CHECK_PERMISSION=true; fi
      if [[ $# -ge 2 ]]; then shift 2; else shift; fi
      ;;
    --region)
      PROBE_REGION="${2:-}"
      if [[ $# -ge 2 ]]; then shift 2; else shift; fi
      ;;
    *) shift ;;
  esac
done
if [[ "$MODE" != "auto" && "$MODE" != "manual" ]]; then
  log_error "Invalid --mode '${MODE}'. Must be 'auto' or 'manual'"
  exit 1
fi

# --- Install Guide ---
if [[ "$INSTALL_GUIDE" == "true" ]]; then
  cat >&2 <<'GUIDE'
=== Alibaba Cloud CLI Installation & Setup Guide ===

1. Install CLI (>= 3.3.3):
   curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash

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
  # Strip any non-digit prefix
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
      log_warn "CLI version ${CLI_VERSION} is below minimum ${MIN_CLI_VERSION}. Run: curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash"
    fi
  fi
else
  log_warn "Alibaba Cloud CLI not installed. Install with: curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash"
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
# Rely on `aliyun configure list` only. Real credential validity is verified
# later via the actual business API call in --check-permission, avoiding an
# extra cross-product (sts) invocation that would also break the plugin-mode
# requirement.
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
if [[ "$CHECK_PERMISSION" == "true" ]]; then
  if [[ "$CREDENTIAL_VALID" == "true" ]]; then
    perm_result=$(aliyun "$CFW_PRODUCT_CODE" DescribeSecurityProxy --PageNo 1 --PageSize 1 --Lang zh 2>&1) || true
    if printf '%s' "$perm_result" | grep -q '"RequestId"'; then
      PERMISSION_OK="true"
    else
      PERMISSION_OK="false"
      err=$(printf '%s' "$perm_result" | grep -o 'ErrorCode: [^ ]*' | head -1 | sed 's/ErrorCode: //' || true)
      [[ -n "$err" ]] && CREDENTIAL_ERROR="$err"
      log_warn "CFW API call failed (ErrorCode: ${err:-unknown})."
      log_warn "This usually means invalid/expired credentials or missing yundun-cloudfirewall:DescribeSecurityProxy permission."
      log_warn "Run 'aliyun configure' to reconfigure, or see references/ram-policies.md."
    fi
  else
    PERMISSION_OK="skipped"
    log_warn "Skipping CFW permission check — no profile configured."
  fi
fi

# --- Manual-mode VPC write permission probes (--mode manual) ---
# The manual diversion workflow needs vpc:CreateVSwitch / CreateRouteTable /
# AssociateRouteTable (plus Delete/Unassociate for cleanup). Probe each action
# by calling it with deliberately fake but FORMAT-VALID resource IDs
# (some APIs validate ID format BEFORE the RAM check - malformed IDs yield
# Incorrect*/InvalidParameter* errors that say nothing about permissions).
# Classification ORDER matters (verified 2026-08-13):
#   - *NotFound* (incl. Forbidden.VpcNotFound = business-layer resource check)
#                                       -> RAM check passed, permission granted
#   - Forbidden.RAM / NoPermission      -> permission missing
#   - success (should not happen)       -> permission granted
#   - other errors (format/throttling)  -> unknown (inconclusive)
MANUAL_PERMS_JSON=""
probe_vpc_write_permission() {
  local action="$1"; shift
  local resp exit_code=0 err_code
  resp=$(aliyun "$VPC_PRODUCT_CODE" "$action" \
    --read-timeout "$DEFAULT_READ_TIMEOUT" \
    --connect-timeout "$DEFAULT_CONNECT_TIMEOUT" \
    --RegionId "$PROBE_REGION" "$@" 2>&1) || exit_code=$?
  if [[ $exit_code -eq 0 ]]; then
    echo "granted"
    return 0
  fi
  err_code=$(printf '%s' "$resp" | grep -o 'ErrorCode: [^ ]*' | head -1 | sed 's/ErrorCode: //' || true)
  case "$err_code" in
    *NotFound*)
      # Business layer ran (resource not found) => RAM authorization passed.
      # NOTE: Forbidden.VpcNotFound is a resource error, NOT a RAM denial.
      echo "granted" ;;
    Forbidden.RAM|NoPermission|Forbidden.AccessDenied|Forbidden)
      echo "missing" ;;
    *)
      log_warn "Probe vpc:${action} returned inconclusive error '${err_code:-unknown}'; treat as unknown and verify during 'prepare'."
      echo "unknown" ;;
  esac
}

if [[ "$MODE" == "manual" ]]; then
  if [[ "$PERMISSION_OK" == "true" || "$PERMISSION_OK" == "not_checked" ]]; then
    if [[ -z "$PROBE_REGION" ]]; then
      PROBE_REGION="${CURRENT_REGION:-cn-hangzhou}"
      [[ -z "$PROBE_REGION" ]] && PROBE_REGION="cn-hangzhou"
    fi
    log_info "Probing manual-mode VPC write permissions in region ${PROBE_REGION} (fake resource IDs, nothing is created)..."

    # Format-valid but non-existent resource IDs (hex suffix matches the
    # real ID alphabet so format validation passes and the RAM check runs).
    FAKE_VPC="vpc-bp1000000000000000000"
    FAKE_VSW="vsw-bp1000000000000000000"
    FAKE_RTB="vtb-bp1000000000000000000"

    P_CREATE_VSW=$(probe_vpc_write_permission "CreateVSwitch" --VpcId "$FAKE_VPC" --ZoneId "${PROBE_REGION}-z" --CidrBlock "192.0.2.0/28")
    P_CREATE_RTB=$(probe_vpc_write_permission "CreateRouteTable" --VpcId "$FAKE_VPC")
    P_ASSOC_RTB=$(probe_vpc_write_permission "AssociateRouteTable" --RouteTableId "$FAKE_RTB" --VSwitchId "$FAKE_VSW")
    P_DELETE_VSW=$(probe_vpc_write_permission "DeleteVSwitch" --VSwitchId "$FAKE_VSW")
    P_DELETE_RTB=$(probe_vpc_write_permission "DeleteRouteTable" --RouteTableId "$FAKE_RTB")
    P_UNASSOC_RTB=$(probe_vpc_write_permission "UnassociateRouteTable" --RouteTableId "$FAKE_RTB" --VSwitchId "$FAKE_VSW")

    MISSING_REQUIRED=()
    [[ "$P_CREATE_VSW" == "missing" ]] && MISSING_REQUIRED+=("vpc:CreateVSwitch")
    [[ "$P_CREATE_RTB" == "missing" ]] && MISSING_REQUIRED+=("vpc:CreateRouteTable")
    [[ "$P_ASSOC_RTB" == "missing" ]] && MISSING_REQUIRED+=("vpc:AssociateRouteTable")

    MANUAL_MODE_READY=false
    if [[ ${#MISSING_REQUIRED[@]} -eq 0 ]]; then
      MANUAL_MODE_READY=true
      log_info "Manual-mode write permissions look sufficient (required probes passed)."
    else
      log_warn "Missing required VPC write permission(s): ${MISSING_REQUIRED[*]}"
      log_warn "Grant them via RAM (see references/ram-policies.md, section 'Manual Mode Preparation Permissions') before running 'nat-fw-lifecycle.sh prepare'."
    fi
    if [[ "$P_DELETE_VSW" == "missing" || "$P_DELETE_RTB" == "missing" || "$P_UNASSOC_RTB" == "missing" ]]; then
      log_warn "Cleanup permission(s) missing or inconclusive (DeleteVSwitch/DeleteRouteTable/UnassociateRouteTable). 'prepare' will still work, but removing the diversion assets later may require the console or extra permissions."
    fi

    missing_json=""
    for m in "${MISSING_REQUIRED[@]:-}"; do
      [[ -z "$m" ]] && continue
      missing_json+="\"${m}\", "
    done
    missing_json="${missing_json%, }"

    MANUAL_PERMS_JSON=',
  "probe_region": "'"${PROBE_REGION}"'",
  "manual_mode_write_permissions": {
    "vpc:CreateVSwitch": "'"${P_CREATE_VSW}"'",
    "vpc:CreateRouteTable": "'"${P_CREATE_RTB}"'",
    "vpc:AssociateRouteTable": "'"${P_ASSOC_RTB}"'",
    "vpc:DeleteVSwitch (cleanup)": "'"${P_DELETE_VSW}"'",
    "vpc:DeleteRouteTable (cleanup)": "'"${P_DELETE_RTB}"'",
    "vpc:UnassociateRouteTable (cleanup)": "'"${P_UNASSOC_RTB}"'"
  },
  "missing_required_permissions": ['"${missing_json}"'],
  "manual_mode_ready": '"${MANUAL_MODE_READY}"''
  else
    MANUAL_PERMS_JSON=',
  "manual_mode_write_permissions": "skipped",
  "manual_mode_ready": false'
    log_warn "Skipping manual-mode permission probes — CFW permission check did not pass (credentials may be invalid)."
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
  "credential_error": "${CREDENTIAL_ERROR}",
  "permission_check": "${PERMISSION_OK}"${MANUAL_PERMS_JSON}
}
EOF
