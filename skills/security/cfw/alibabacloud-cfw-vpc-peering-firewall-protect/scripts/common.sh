#!/usr/bin/env bash
# common.sh - Shared utilities for alibabacloud-cfw-vpc-peering-firewall-protect
# Source this file from other scripts: source "$(dirname "$0")/common.sh"
#
# Scope: Cloud Firewall VPC boundary firewall for VPCs connected by Express
# Connect / VPC peering (the "Peering Connection" tab of the VPC boundary
# firewall page). Protects the east-west traffic between two peered VPCs.
# CEN-based VPC firewalls are a DIFFERENT API family and are out of scope for
# this skill.
#
# Dependencies:
#   - aliyun CLI (>= 3.3.3) with Cloudfw plugin and Vpc plugin

set -euo pipefail

# --- Constants ---
readonly CFW_PRODUCT_CODE="Cloudfw"
readonly VPC_PRODUCT_CODE="Vpc"
readonly DEFAULT_READ_TIMEOUT=30
readonly DEFAULT_CONNECT_TIMEOUT=10

# --- Observability: manifest version + session id + User-Agent ---
# Every aliyun CLI call carries a User-Agent of the form
#   AlibabaCloud-Agent-Skills/<skill-name>/<session-id> skill-version/<skill-version>
# i.e. two space-separated product tokens: the skill/session token, then the
# version token. This lets all API calls of one Skill session AND one Skill
# release be correlated.
#
# skill-version rule: read from references/manifest.json (top-level "version",
# must be a non-empty string). This is a HARD GATE - when the manifest is
# missing, unreadable, or has no non-empty string "version", this library aborts
# the calling script immediately, so no Alibaba Cloud API request can ever be
# emitted with an incomplete User-Agent.
#
# session-id rule: 32-character lowercase hex, generated ONCE per session and
# reused identically by every call. Callers may pre-set SKILL_SESSION_ID to join
# an existing session; otherwise it is generated here.
readonly SKILL_NAME="alibabacloud-cfw-vpc-peering-firewall-protect"
COMMON_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SKILL_MANIFEST="${COMMON_SH_DIR}/../references/manifest.json"

SKILL_VERSION=$(python3 -c '
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        manifest = json.load(fh)
except Exception:
    sys.exit(1)
if not isinstance(manifest, dict):
    sys.exit(1)
version = manifest.get("version")
if not isinstance(version, str) or not version.strip():
    sys.exit(1)
print(version.strip())
' "$SKILL_MANIFEST" 2>/dev/null) || SKILL_VERSION=""

if [[ -z "$SKILL_VERSION" ]]; then
  echo "[ERROR] Missing or invalid skill manifest: ${SKILL_MANIFEST}" >&2
  echo "[ERROR] It must exist and carry a top-level non-empty string \"version\"." >&2
  echo "[ERROR] Refusing to call any Alibaba Cloud API without a versioned User-Agent." >&2
  exit 1
fi
readonly SKILL_VERSION

if [[ -z "${SKILL_SESSION_ID:-}" ]]; then
  # uuidgen is absent in minimal containers. Under `set -euo pipefail` the
  # assignment inherits its 127 and aborts here, before the fallback can run.
  SKILL_SESSION_ID=$(uuidgen 2>/dev/null | tr -d '-' | tr 'A-F' 'a-f') || SKILL_SESSION_ID=""
  if [[ ! "$SKILL_SESSION_ID" =~ ^[0-9a-f]{32}$ ]]; then
    SKILL_SESSION_ID=$(od -An -tx1 -N16 /dev/urandom 2>/dev/null | tr -d ' \n') || SKILL_SESSION_ID=""
  fi
  if [[ ! "$SKILL_SESSION_ID" =~ ^[0-9a-f]{32}$ ]]; then
    echo "[ERROR] Cannot generate a 32-character lowercase hex session id: neither uuidgen nor /dev/urandom is usable." >&2
    echo "[ERROR] Refusing to call any Alibaba Cloud API with an incomplete User-Agent." >&2
    echo "[ERROR] Export SKILL_SESSION_ID=<32 lowercase hex characters> and run the command again." >&2
    exit 1
  fi
  export SKILL_SESSION_ID
fi
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/${SKILL_NAME}/${SKILL_SESSION_ID} skill-version/${SKILL_VERSION}"

# FirewallSwitchStatus values returned by DescribeVpcFirewallList /
# DescribeVpcFirewallDetail (and accepted as the query filter):
#   opened=protection on  closed=protection off
#   notconfigured=no VPC firewall configured yet  configured=configured
#   configuring=transitional, seen for a minute or two right after
#     CreateVpcFirewallConfigure returns and before the first closed. It is
#     undocumented but real (observed live 2026-10-21); a poll loop that only
#     accepts opened/closed would treat it as an invalid state and give up.
readonly VALID_SWITCH_STATUSES="opened closed notconfigured configured configuring"

# FirewallSwitch values accepted by ModifyVpcFirewallSwitchStatus / Create.
readonly VALID_SWITCH_ACTIONS="open close"

# ConnectSubType values: vpc2vpc=Express Connect, vpcpeer=VPC peering connection.
readonly VALID_CONNECT_SUBTYPES="vpc2vpc vpcpeer"

# --- Logging (all to stderr) ---

log_info() {
  echo "[INFO] $*" >&2
}

log_warn() {
  echo "[WARN] $*" >&2
}

log_error() {
  echo "[ERROR] $*" >&2
}

# --- Validation Functions ---

validate_required() {
  local name="$1"
  local value="${2:-}"
  if [[ -z "$value" ]]; then
    log_error "Required parameter --${name} is missing or empty"
    return 1
  fi
}

# Validate an option's value during argument parsing (call inside the
# `--opt) ...` branch before consuming $2). Rejects missing values, empty
# values, and values that look like another option (--xxx).
# Usage: --vpc-id) arg_value "--vpc-id" "${@:2}"; VPC_ID="$2"; shift 2 ;;
arg_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ $# -lt 2 || -z "$value" ]]; then
    log_error "Option ${flag} requires a non-empty value"
    exit 1
  fi
  if [[ "$value" == --* ]]; then
    log_error "Option ${flag} requires a value; got '${value}' which looks like another option"
    exit 1
  fi
}

validate_region() {
  local region="$1"
  if [[ ! "$region" =~ ^[a-z]+-[a-z0-9-]+$ ]]; then
    log_error "Invalid region format: ${region}"
    return 1
  fi
}

validate_member_uid() {
  local uid="$1"
  if [[ ! "$uid" =~ ^[0-9]+$ ]]; then
    log_error "Invalid member UID: ${uid}. Must be numeric"
    return 1
  fi
}

validate_vpc_firewall_id() {
  local id="$1"
  # VPC firewall instance IDs look like "vfw-xxxxxxxx"; accept alnum/hyphen IDs.
  if [[ ! "$id" =~ ^vfw-[A-Za-z0-9]+$ ]]; then
    log_error "Invalid VPC firewall ID (vpc-firewall-id): ${id}. Expected format: vfw-xxxxxxxx"
    return 1
  fi
}

validate_vpc_id() {
  local id="$1"
  if [[ ! "$id" =~ ^vpc-[a-z0-9]+$ ]]; then
    log_error "Invalid VPC ID: ${id}. Expected format: vpc-xxxxxxxx"
    return 1
  fi
}

validate_switch_status() {
  local status="$1"
  local found=false
  for valid in $VALID_SWITCH_STATUSES; do
    if [[ "$status" == "$valid" ]]; then
      found=true
      break
    fi
  done
  if [[ "$found" != "true" ]]; then
    log_error "Invalid VPC firewall switch status: ${status}. Must be one of: ${VALID_SWITCH_STATUSES// /, }"
    return 1
  fi
}

validate_connect_subtype() {
  local subtype="$1"
  local found=false
  for valid in $VALID_CONNECT_SUBTYPES; do
    if [[ "$subtype" == "$valid" ]]; then
      found=true
      break
    fi
  done
  if [[ "$found" != "true" ]]; then
    log_error "Invalid connect subtype: ${subtype}. Must be one of: ${VALID_CONNECT_SUBTYPES// /, }"
    return 1
  fi
}

validate_firewall_name() {
  local name="$1"
  # The API enforces the exact rule; this is a coarse guard. 2~128 chars, must
  # not start with a digit/underscore-only. Byte-length guard is intentionally
  # loose to allow multibyte names.
  if [[ ${#name} -lt 2 || ${#name} -gt 200 ]]; then
    log_error "Invalid VPC firewall name: ${name}. Length must be 2~128 characters"
    return 1
  fi
}

# Iterate over a comma-separated list, trimming whitespace, and invoke a
# validator callback for each element.
# Usage: for_each_csv <csv_values> <validator_func>
for_each_csv() {
  local csv_values="$1"
  local validator="$2"

  local saved_ifs="${IFS-$' \t\n'}"
  IFS=','
  for val in $csv_values; do
    IFS="$saved_ifs"
    val=$(printf '%s' "$val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [[ -n "$val" ]]; then
      "$validator" "$val" || return 1
    fi
  done
  IFS="$saved_ifs"
}

# --- Output Helpers ---

# Output a success JSON result to stdout
# Usage: output_success <json_data>
output_success() {
  local data="$1"
  printf '%s\n' "$data"
}

# Escape a value so it can be interpolated inside a JSON double-quoted string.
# Most structured output here is assembled with a heredoc or printf rather than a
# JSON encoder, so a quote, backslash or control character inside an interpolated
# value - an API error message, a firewall name, a --*-cidr-json blob echoed into
# a command preview - would otherwise corrupt the whole document and leave the
# caller with unparsable output. Non-ASCII is escaped to \uXXXX, which also keeps
# script output pure ASCII.
json_escape() {
  printf '%s' "$1" | python3 -c 'import json, sys; sys.stdout.write(json.dumps(sys.stdin.read())[1:-1])'
}

# Output an error JSON result to stdout
# Usage: output_error <error_code> <error_message>
output_error() {
  local error_code="${1:-UnknownError}"
  local error_message="${2:-An unknown error occurred}"

  cat <<EOF
{
  "success": false,
  "error_code": "$(json_escape "$error_code")",
  "error_message": "$(json_escape "$error_message")"
}
EOF
}

# --- Error Extraction ---
#
# CRITICAL: these helpers run on the ERROR paths, and their callers assign them
# with a plain `var=$(...)`. Under `set -e` + `pipefail` a non-matching grep
# makes the pipeline (and therefore the assignment) fail, which aborts the whole
# script BEFORE output_error can emit the structured error JSON - the caller then
# sees an empty stdout and a bare exit 1. That is exactly what happens with
# non-standard error text (network timeouts, plugin-level errors such as
# "unchecked version", SDK-level errors) which carry no `ErrorCode:` / `Message:`
# line at all. So every pipeline here MUST swallow the no-match failure and
# simply return an empty string.

extract_api_error_code() {
  local response="$1"
  local code=""
  # 1) aliyun CLI plugin error text: "ErrorCode: Xxx"
  code=$(printf '%s' "$response" | grep -o 'ErrorCode: [^ ]*' | head -1 | sed 's/ErrorCode: //' || true)
  # 2) SDK error text: a standalone "   Code: Xxx" line. The (^|space) anchor is
  #    load-bearing - without it the "StatusCode: 400" line above matches first
  #    and the real code is lost.
  if [[ -z "$code" ]]; then
    code=$(printf '%s' "$response" | grep -oE '(^|[[:space:]])Code:[[:space:]]+[A-Za-z0-9._-]+' | head -1 | sed -E 's/^[[:space:]]*Code:[[:space:]]+//' || true)
  fi
  # 3) JSON error body: "Code":"Xxx"
  if [[ -z "$code" ]]; then
    code=$(printf '%s' "$response" | grep -o '"Code"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/' || true)
  fi
  printf '%s' "$code"
}

extract_api_error_message() {
  local response="$1"
  printf '%s' "$response" | grep -o 'Message: .*' | head -1 | sed 's/Message: //' || true
}

extract_api_request_id() {
  local response="$1"
  # Try CLI error format first, then JSON response format
  local rid
  rid=$(printf '%s' "$response" | grep -o 'RequestId: [^ ]*' | head -1 | sed 's/RequestId: //' || true)
  if [[ -z "$rid" ]]; then
    rid=$(printf '%s' "$response" | grep -o '"RequestId"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/' || true)
  fi
  printf '%s' "$rid"
}

# --- CLI Wrapper ---

# Call CFW API via aliyun CLI (plugin mode).
# Usage: call_cfw_api <APIName> [--Param1 value1 ...]
# Returns: API response on stdout, diagnostics on stderr
call_cfw_api() {
  local api_name="$1"
  shift

  local cmd=(
    aliyun "$CFW_PRODUCT_CODE" "$api_name"
    --user-agent "$ALIBABA_CLOUD_USER_AGENT"
    --read-timeout "$DEFAULT_READ_TIMEOUT"
    --connect-timeout "$DEFAULT_CONNECT_TIMEOUT"
    "$@"
  )

  log_info "Calling: aliyun ${CFW_PRODUCT_CODE} ${api_name} ..."

  local response exit_code=0
  response=$("${cmd[@]}" 2>&1) || exit_code=$?

  # Kebab-case API names resolve only through the lowercase-keyed cloudfw plugin;
  # a registry lacking them answers 'unknown product "Cloudfw"' (measured in eval
  # run 37, 2026-11-04: Cloudfw+kebab exit 1, cloudfw+kebab exit 0 with a
  # RequestId). Without this retry the whole IPS path is dead there, and the agent
  # gets pushed into the bare CLI call the evals forbid.
  if [[ $exit_code -ne 0 && "$response" == *'unknown product'* ]]; then
    local lc_product
    lc_product=$(printf '%s' "$CFW_PRODUCT_CODE" | tr '[:upper:]' '[:lower:]')
    log_warn "product ${CFW_PRODUCT_CODE} did not resolve ${api_name}; retrying as ${lc_product}"
    cmd[1]="$lc_product"
    exit_code=0
    response=$("${cmd[@]}" 2>&1) || exit_code=$?
  fi

  if [[ $exit_code -ne 0 ]]; then
    log_error "API call failed with exit code ${exit_code}"
    log_error "Response: ${response}"

    local request_id
    request_id=$(extract_api_request_id "$response")
    if [[ -n "$request_id" ]]; then
      log_error "RequestId: ${request_id} (provide this when contacting support)"
    fi

    printf '%s' "$response"
    return $exit_code
  fi

  printf '%s' "$response"
}

# Call VPC API via aliyun CLI (plugin mode). Used to auto-discover the peering
# route entries (LocalVpcCidrTableList / PeerVpcCidrTableList) during VPC
# firewall creation, and to read VPC/route-table facts during assessment.
# Usage: call_vpc_api <APIName> [--Param1 value1 ...]
call_vpc_api() {
  local api_name="$1"
  shift

  local cmd=(
    aliyun "$VPC_PRODUCT_CODE" "$api_name"
    --user-agent "$ALIBABA_CLOUD_USER_AGENT"
    --read-timeout "$DEFAULT_READ_TIMEOUT"
    --connect-timeout "$DEFAULT_CONNECT_TIMEOUT"
    "$@"
  )

  log_info "Calling: aliyun ${VPC_PRODUCT_CODE} ${api_name} ..."

  local response exit_code=0
  response=$("${cmd[@]}" 2>&1) || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    log_error "VPC API call failed with exit code ${exit_code}"
    log_error "Response: ${response}"
    printf '%s' "$response"
    return $exit_code
  fi

  printf '%s' "$response"
}

# --- Help Generator ---

show_help() {
  local script_name="$1"
  local description="$2"
  local usage="$3"
  local options_text="$4"

  cat >&2 <<EOF
${script_name} - ${description}

USAGE:
  ${usage}

OPTIONS:
${options_text}

OUTPUT:
  JSON to stdout. Diagnostics to stderr.

EXIT CODES:
  0  Success
  1  Parameter validation error
  2  API call failed
EOF
  exit 0
}

# --- Error Diagnosis ---

# Provide user-friendly diagnosis for common CFW VPC boundary firewall error
# codes. Every code handled here MUST also be documented in
# references/api-errors.md (enforced by tests/run_unit_tests.sh guard D3).
diagnose_cfw_error() {
  local error_code="$1"
  local error_message="${2:-}"

  case "$error_code" in
    Missing*VpcFirewallId|Missing*FirewallSwitch|Missing*VpcFirewallName|Missing*LocalVpcId|Missing*PeerVpcId|Missing*Region|Missing*CidrTableList)
      log_error "Diagnosis: A required API parameter is missing."
      log_error "  Fix: Check the script usage (--help) and provide all required parameters."
      ;;
    ErrorFirewallId|ErrorVpcFirewallNotFound|ErrorFirewallNotFound)
      log_error "Diagnosis: The specified VPC firewall does not exist."
      log_error "  Fix: Verify the vpc-firewall-id with 'vpc-fw-switch.sh query'. It may be a stale ID from an earlier report."
      ;;
    ErrorParametersFirewallId)
      log_error "Diagnosis: The VPC firewall ID is not valid for this API. The usual cause is a firewall that has never been configured (FirewallSwitchStatus 'notconfigured'): it carries no IPS/ACL engine instance, so the engine APIs reject its ID."
      log_error "  Fix: Confirm the state with 'vpc-fw-switch.sh query'. If it is notconfigured, create and open the firewall first (vpc-fw-lifecycle.sh assess / create, then vpc-fw-switch.sh open) before tuning the engine."
      ;;
    ErrorFirewallSwitch)
      log_error "Diagnosis: The firewall switch parameter is incorrect."
      log_error "  Fix: FirewallSwitch must be exactly 'open' or 'close'."
      ;;
    ErrorFirewallCannotOpen|ErrorVpcFirewall.CannotOpen|ErrorFirewallStatus)
      log_error "Diagnosis: The VPC firewall is in a transitional/invalid state for this operation."
      log_error "  Fix: Switching takes 5~30 minutes (route learning). Wait for the state to settle, then retry. Poll with 'vpc-fw-switch.sh query --vpc-firewall-id <id>'."
      ;;
    ErrorFirewallStatusCannotModify)
      log_error "Diagnosis: The firewall's current status does not allow this modification - it is transitioning, or the target engine instance is not ready."
      log_error "  Fix: Wait for the state to settle (creation and switching take 5~30 minutes), then retry the same command. Poll with 'vpc-fw-switch.sh query --vpc-firewall-id <id>'."
      ;;
    ErrorVpcFirewallExist)
      log_error "Diagnosis: A VPC firewall already exists for this peering connection (one peering pair maps to one firewall)."
      log_error "  Fix: Query it with 'vpc-fw-switch.sh query' and use the switch workflow instead of creating."
      ;;
    ErrorVpcIdError|ErrorRegionNoError|ErrorVpcIdPara|ErrorLocalVpcIdPeerVpcIdError)
      log_error "Diagnosis: A VPC ID or region parameter is invalid or inconsistent."
      log_error "  Fix: Confirm LocalVpcId/LocalVpcRegion and PeerVpcId/PeerVpcRegion with 'vpc-fw-lifecycle.sh assess'."
      ;;
    ErrorDestCidrError|ErrorDestCidrEmpty|ErrorSameCidrIp|ErrorCidrFormat|ErrorCidrIpAddress|ErrorCustomRouteEntryMax|ErrorRouteTableIdNotFound)
      log_error "Diagnosis: The route/CIDR table list is invalid (bad CIDR, empty target, duplicate CIDR, too many entries, or unknown route table)."
      log_error "  Fix: Re-run 'vpc-fw-lifecycle.sh assess --local-vpc-id <id> --peer-vpc-id <id>' to re-discover the peering route entries, or pass a corrected --local-cidr-json/--peer-cidr-json. See references/vpc-prerequisites.md."
      ;;
    ErrorFirewallName)
      log_error "Diagnosis: The VPC firewall name is invalid."
      log_error "  Fix: Provide a name of 2~128 characters."
      ;;
    ErrorFirewallQuotaNotEmpty|ErrorGeneralInstanceSpecFull|ErrorBandwidthPenalty)
      log_error "Diagnosis: VPC firewall quota exhausted, CFW instance spec full, or bandwidth over-use penalty in effect."
      log_error "  Fix: Purchase additional VPC firewall quota / upgrade the CFW spec in the Cloud Firewall console, then retry."
      ;;
    ErrorCenVpcEcConflict)
      log_error "Diagnosis: A CEN VPC conflicts with this Express Connect VPC - the two connection types cannot both protect the same VPC."
      log_error "  Fix: Choose one connection type for this VPC pair. This skill covers the Express Connect / peering family only (see references/vpc-prerequisites.md)."
      ;;
    ErrorInvalidMemberUid|ErrorInvalidMemberUidStatus|ErrorAliUid)
      log_error "Diagnosis: The member UID / aliuid is invalid or in an unsupported state."
      log_error "  Fix: Verify --member-uid refers to a member account of the current management account."
      ;;
    ErrorNetworkInterfaceNotFound)
      log_error "Diagnosis: The firewall ENI is invalid - the firewall's network configuration is broken."
      log_error "  Fix: Do not modify the CFW-created vswitch/route table/security group. Contact support with the RequestId."
      ;;
    ErrorAuthentication)
      log_error "Diagnosis: Authentication failed - credentials are invalid or expired."
      log_error "  Fix: Run 'aliyun configure' to review and update your credential configuration."
      ;;
    NoPermission|Forbidden*|Forbidden.RAM)
      log_error "Diagnosis: Insufficient permissions (RAM ImplicitDeny)."
      log_error "  Fix: Grant the required yundun-cloudfirewall:* (and vpc:Describe* for route discovery) permissions via RAM console. See references/ram-policies.md."
      ;;
    Throttling)
      log_error "Diagnosis: API call rate limit exceeded (VPC firewall APIs are capped at 10 QPS)."
      log_error "  Fix: Wait a few seconds and retry."
      ;;
    *)
      log_error "Diagnosis: Unrecognized error code '${error_code}'."
      if [[ -n "$error_message" ]]; then
        log_error "  Error message: ${error_message}"
      fi
      ;;
  esac
}
