#!/usr/bin/env bash
# validate-cli.sh - Check Alibaba Cloud CLI installation, credentials, and plugin
# configuration for alibabacloud-cfw-vpc-peering-firewall-protect.
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin
#
# Covers: CLI installation, version check (>= 3.3.3), plugin setup, credential
#         validation, CFW read permission check, and (with --mode create) a probe
#         of the VPC read permissions used by create's route auto-discovery.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

readonly MIN_CLI_VERSION="3.3.3"

# --- Help ---
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  show_help "validate-cli.sh" \
    "Check Alibaba Cloud CLI installation and credential configuration" \
    "validate-cli.sh [--check-permission] [--mode query|create] [--region <region>] [--install-guide]" \
    "  --check-permission  Verify CFW API access with a real read-only call
  --mode <query|create>
                      With --check-permission and mode=create, additionally probe
                      the VPC read permissions used by 'create' route
                      auto-discovery (DescribeRouteTableList / DescribeRouteEntryList).
                      Probes use fake resource IDs; nothing is created.
  --region <region>   Region used for the create-mode VPC read probes
                      (default: current profile region or cn-hangzhou)
  --install-guide     Show CLI installation and setup instructions
  --help, -h          Show this help message"
fi

CHECK_PERMISSION=false
INSTALL_GUIDE=false
MODE="query"
PROBE_REGION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-permission) CHECK_PERMISSION=true; shift ;;
    --install-guide) INSTALL_GUIDE=true; shift ;;
    --mode)
      MODE="${2:-}"
      if [[ -z "$MODE" || "$MODE" == --* ]]; then
        log_error "Option --mode requires a value: query or create"
        exit 1
      fi
      if [[ "$MODE" == "create" ]]; then CHECK_PERMISSION=true; fi
      if [[ $# -ge 2 ]]; then shift 2; else shift; fi
      ;;
    --region)
      PROBE_REGION="${2:-}"
      if [[ $# -ge 2 ]]; then shift 2; else shift; fi
      ;;
    *) shift ;;
  esac
done
if [[ "$MODE" != "query" && "$MODE" != "create" ]]; then
  log_error "Invalid --mode '${MODE}'. Must be 'query' or 'create'"
  exit 1
fi

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
  v1=$(printf '%s' "$v1" | sed 's/^[^0-9]*//')
  v2=$(printf '%s' "$v2" | sed 's/^[^0-9]*//')

  local IFS='.'
  local -a a1 a2
  read -r -a a1 <<< "$v1"
  read -r -a a2 <<< "$v2"

  local i
  for i in 0 1 2; do
    local n1="${a1[$i]:-0}" n2="${a2[$i]:-0}"
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
PROFILE_CONFIGURED=false
CURRENT_PROFILE=""
CURRENT_REGION=""
if [[ "$CLI_INSTALLED" == "true" ]]; then
  local_config=$(aliyun configure list 2>/dev/null || true)
  # Match the row whose first column ends with " *" (the active profile marker).
  # A plain `grep '\*'` would also match Credential cells like `AK:***rpY`.
  current_line=$(printf '%s' "$local_config" | grep -E '^[^|]*\*[[:space:]]*\|' | head -1 || true)
  if [[ -n "$current_line" ]]; then
    PROFILE_CONFIGURED=true
    CURRENT_PROFILE=$(printf '%s' "$current_line" | awk -F'|' '{print $1}' | sed 's/\*//g; s/^[[:space:]]*//; s/[[:space:]]*$//')
    CURRENT_REGION=$(printf '%s' "$current_line" | awk -F'|' '{print $4}' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
  fi
fi

# --- Check credential configuration (no real API call) ---
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
    perm_result=$(aliyun "$CFW_PRODUCT_CODE" DescribeVpcFirewallList --CurrentPage 1 --PageSize 1 --Lang zh --user-agent "$ALIBABA_CLOUD_USER_AGENT" 2>&1) || true
    if printf '%s' "$perm_result" | grep -q '"RequestId"'; then
      PERMISSION_OK="true"
    else
      PERMISSION_OK="false"
      err=$(printf '%s' "$perm_result" | grep -o 'ErrorCode: [^ ]*' | head -1 | sed 's/ErrorCode: //' || true)
      [[ -n "$err" ]] && CREDENTIAL_ERROR="$err"
      log_warn "CFW API call failed (ErrorCode: ${err:-unknown})."
      log_warn "This usually means invalid/expired credentials or missing yundun-cloudfirewall:DescribeVpcFirewallList permission."
      log_warn "Run 'aliyun configure' to reconfigure, or see references/ram-policies.md."
    fi
  else
    PERMISSION_OK="skipped"
    log_warn "Skipping CFW permission check - no profile configured."
  fi
fi

# --- Create-mode VPC read permission probes (--mode create) ---
# Route auto-discovery during 'create'/'assess' needs vpc:DescribeRouteTableList
# and vpc:DescribeRouteEntryList. Probe each with a deliberately fake but
# FORMAT-VALID VPC ID so ID-format validation passes and the RAM check runs.
# Classification:
#   - *NotFound* / success        -> permission granted
#   - Forbidden.RAM / NoPermission -> permission missing
#   - other (format/throttling)    -> unknown (inconclusive)
CREATE_PERMS_JSON=""
probe_vpc_read_permission() {
  local action="$1"; shift
  local resp exit_code=0 err_code
  resp=$(aliyun "$VPC_PRODUCT_CODE" "$action" \
    --user-agent "$ALIBABA_CLOUD_USER_AGENT" \
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
      echo "granted" ;;
    Forbidden.RAM|NoPermission|Forbidden.AccessDenied|Forbidden)
      echo "missing" ;;
    *)
      log_warn "Probe vpc:${action} returned inconclusive error '${err_code:-unknown}'; treat as unknown."
      echo "unknown" ;;
  esac
}

if [[ "$MODE" == "create" ]]; then
  if [[ "$PERMISSION_OK" == "true" || "$PERMISSION_OK" == "not_checked" ]]; then
    if [[ -z "$PROBE_REGION" ]]; then
      PROBE_REGION="${CURRENT_REGION:-cn-hangzhou}"
      [[ -z "$PROBE_REGION" ]] && PROBE_REGION="cn-hangzhou"
    fi
    log_info "Probing create-mode VPC read permissions in region ${PROBE_REGION} (fake resource IDs, nothing is created)..."

    FAKE_VPC="vpc-bp1000000000000000000"
    FAKE_RTB="vtb-bp1000000000000000000"
    P_LIST_RT=$(probe_vpc_read_permission "DescribeRouteTableList" --VpcId "$FAKE_VPC")
    P_LIST_RE=$(probe_vpc_read_permission "DescribeRouteEntryList" --RouteTableId "$FAKE_RTB")

    MISSING_REQUIRED=()
    [[ "$P_LIST_RT" == "missing" ]] && MISSING_REQUIRED+=("vpc:DescribeRouteTableList")
    [[ "$P_LIST_RE" == "missing" ]] && MISSING_REQUIRED+=("vpc:DescribeRouteEntryList")

    CREATE_MODE_READY=false
    if [[ ${#MISSING_REQUIRED[@]} -eq 0 ]]; then
      CREATE_MODE_READY=true
      log_info "Create-mode VPC read permissions look sufficient (route auto-discovery should work)."
    else
      log_warn "Missing VPC read permission(s): ${MISSING_REQUIRED[*]}"
      log_warn "Grant them via RAM (see references/ram-policies.md) for route auto-discovery, or pass --local-cidr-json/--peer-cidr-json explicitly to 'create'."
    fi

    missing_json=""
    for m in ${MISSING_REQUIRED[@]+"${MISSING_REQUIRED[@]}"}; do
      [[ -z "$m" ]] && continue
      missing_json+="\"${m}\", "
    done
    missing_json="${missing_json%, }"

    CREATE_PERMS_JSON=',
  "probe_region": "'"${PROBE_REGION}"'",
  "create_mode_read_permissions": {
    "vpc:DescribeRouteTableList": "'"${P_LIST_RT}"'",
    "vpc:DescribeRouteEntryList": "'"${P_LIST_RE}"'"
  },
  "missing_required_permissions": ['"${missing_json}"'],
  "create_mode_ready": '"${CREATE_MODE_READY}"''
  else
    CREATE_PERMS_JSON=',
  "create_mode_read_permissions": "skipped",
  "create_mode_ready": false'
    log_warn "Skipping create-mode permission probes - CFW permission check did not pass (credentials may be invalid)."
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
  "permission_check": "${PERMISSION_OK}"${CREATE_PERMS_JSON}
}
EOF
