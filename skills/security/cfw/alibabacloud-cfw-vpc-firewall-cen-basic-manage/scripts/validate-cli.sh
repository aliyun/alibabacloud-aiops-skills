#!/usr/bin/env bash
# validate-cli.sh - Alibaba Cloud CLI readiness gate for the
# alibabacloud-cfw-vpc-firewall-cen-basic-manage skill.
#
# Checks, in order: CLI presence, version >= 3.3.3, cloudfw plugin presence,
# credential profile, and optionally a real read-only Cloud Firewall call that
# doubles as a permission probe.
#
# Dependencies: aliyun CLI, python3 (stdlib only, for JSON parsing).
# No network access unless --check-permission is passed.
#
# Output: a single JSON object on stdout. Human-readable diagnostics go to
# stderr, so stdout stays machine readable.
#
# macOS ships bash 3.2, so this script avoids ${var,,}, associative arrays and
# mapfile.
#
# Usage:
#   bash scripts/validate-cli.sh
#   SKILL_SESSION_ID=<32-hex> bash scripts/validate-cli.sh --check-permission
#   bash scripts/validate-cli.sh --install-guide

set -uo pipefail

readonly MIN_CLI_VERSION="3.3.3"
readonly PLUGIN_NAME="aliyun-cli-cloudfw"
readonly SKILL_NAME="alibabacloud-cfw-vpc-firewall-cen-basic-manage"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MANIFEST="${REPO_DIR}/references/manifest.json"

log_info() { printf '[INFO] %s\n' "$1" >&2; }
log_warn() { printf '[WARN] %s\n' "$1" >&2; }
log_err()  { printf '[ERROR] %s\n' "$1" >&2; }

usage() {
  cat >&2 <<'USAGE'
validate-cli.sh - check Alibaba Cloud CLI readiness for the CEN Basic VPC
                  firewall skill.

Options:
  --check-permission   Also issue one real read-only Cloud Firewall call to
                       verify credentials and RAM permission. Requires
                       SKILL_SESSION_ID so the call is attributable.
  --install-guide      Print CLI installation and plugin setup instructions,
                       then exit.
  -h, --help           Show this help message.

Environment:
  SKILL_SESSION_ID     32-character lowercase hex session id, reused for the
                       whole session. Needed by --check-permission.

Output:
  A JSON object on stdout. Diagnostics on stderr.
USAGE
}

# --- version comparison, bash 3.2 safe ---------------------------------------
# Returns 0 when $1 >= $2 using dot-separated numeric comparison.
version_gte() {
  local IFS=.
  # shellcheck disable=SC2206  # intentional word splitting into an array
  local a=($1) b=($2) i
  for ((i = 0; i < ${#b[@]}; i++)); do
    local n1="${a[i]:-0}" n2="${b[i]:-0}"
    case "$n1$n2" in
      *[!0-9]*) return 0 ;;   # non-numeric suffix such as -beta: do not block
    esac
    if ((n1 > n2)); then return 0; fi
    if ((n1 < n2)); then return 1; fi
  done
  return 0
}

# --- skill version, the only permitted source for the UA version segment -----
# A missing or malformed manifest is a hard stop: guessing a version would put a
# wrong value into every observability record for the session.
resolve_skill_version() {
  if [[ ! -f "$MANIFEST" ]]; then
    log_err "missing ${MANIFEST}; cannot resolve the skill version"
    return 1
  fi
  local v
  v="$(python3 -c '
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        v = json.load(fh).get("version")
except Exception as exc:
    sys.stderr.write("cannot parse manifest: %s\n" % exc)
    sys.exit(1)
if not isinstance(v, str) or not v.strip():
    sys.stderr.write("manifest has no usable top-level string version\n")
    sys.exit(1)
print(v.strip())
' "$MANIFEST" 2>&1)" || { log_err "$v"; return 1; }
  printf '%s' "$v"
}

# --- install guide -----------------------------------------------------------
if [[ "${1:-}" == "--install-guide" ]]; then
  cat <<'GUIDE'
=== Alibaba Cloud CLI installation and setup ===

1. Verify the CLI is present and new enough (>= 3.3.3):

     aliyun version

2. First install, or a major upgrade:

     /bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 \
       https://aliyuncli.alicdn.com/setup.sh)"

   Routine update, available from CLI 3.3.5:

     aliyun upgrade

   or on macOS via Homebrew:

     brew install aliyun-cli
     brew upgrade aliyun-cli

3. Enable automatic plugin installation and refresh the plugins, so the cloudfw
   plugin is present before any firewall command runs:

     aliyun configure set --auto-plugin-install true
     aliyun plugin update

   Confirm the plugin is installed:

     aliyun plugin list

   Expect a row named aliyun-cli-cloudfw.

4. Configure credentials outside of this session, then verify the profile. The
   skill relies on the default credential chain and never reads or prompts for an
   AccessKey:

     aliyun configure list

   The active profile is the row whose first column ends with " *".

5. Full instructions, including troubleshooting:

     references/cli-installation-guide.md
GUIDE
  exit 0
fi

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

CHECK_PERMISSION=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-permission) CHECK_PERMISSION=true; shift ;;
    --install-guide|-h|--help) usage; exit 0 ;;
    *) log_warn "ignoring unknown argument: $1"; shift ;;
  esac
done

# --- CLI presence and version ------------------------------------------------
CLI_INSTALLED=false
CLI_VERSION="unknown"
CLI_VERSION_OK="not_checked"
if command -v aliyun >/dev/null 2>&1; then
  CLI_INSTALLED=true
  CLI_VERSION="$(aliyun version 2>/dev/null | head -1 || echo unknown)"
  if [[ "$CLI_VERSION" != "unknown" ]]; then
    if version_gte "$CLI_VERSION" "$MIN_CLI_VERSION"; then
      CLI_VERSION_OK=true
    else
      CLI_VERSION_OK=false
      log_warn "CLI ${CLI_VERSION} is below the minimum ${MIN_CLI_VERSION}; run 'aliyun upgrade' or see --install-guide"
    fi
  fi
else
  log_warn "aliyun CLI not installed; run: bash scripts/validate-cli.sh --install-guide"
fi

# --- plugin presence ---------------------------------------------------------
PLUGIN_INSTALLED=false
PLUGIN_VERSION=""
if [[ "$CLI_INSTALLED" == "true" ]]; then
  plugin_line="$(aliyun plugin list 2>/dev/null | grep -F "$PLUGIN_NAME" | head -1 || true)"
  if [[ -n "$plugin_line" ]]; then
    PLUGIN_INSTALLED=true
    PLUGIN_VERSION="$(printf '%s' "$plugin_line" | awk '{print $2}')"
  else
    log_warn "${PLUGIN_NAME} plugin not found; run: aliyun configure set --auto-plugin-install true && aliyun plugin update"
  fi
fi

# --- credential profile ------------------------------------------------------
# `aliyun configure list` prints a pipe-separated table whose active row has a
# first column ending in " *". A plain grep for '*' would also match masked
# credential cells such as AK:***rpY, so anchor on the column boundary.
PROFILE_CONFIGURED=false
CURRENT_PROFILE=""
CURRENT_REGION=""
if [[ "$CLI_INSTALLED" == "true" ]]; then
  config_out="$(aliyun configure list 2>/dev/null || true)"
  active_line="$(printf '%s' "$config_out" | grep -E '^[^|]*\*[[:space:]]*\|' | head -1 || true)"
  if [[ -n "$active_line" ]]; then
    PROFILE_CONFIGURED=true
    CURRENT_PROFILE="$(printf '%s' "$active_line" | awk -F'|' '{print $1}' | tr -d '*' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    CURRENT_REGION="$(printf '%s' "$active_line" | awk -F'|' '{print $4}' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  else
    log_warn "no active credential profile; configure credentials outside this session, then re-run"
  fi
fi

# --- skill version -----------------------------------------------------------
SKILL_VERSION=""
VERSION_OK=false
if SKILL_VERSION="$(resolve_skill_version)"; then
  VERSION_OK=true
else
  SKILL_VERSION=""
  log_err "stopping: the UA version segment must come from references/manifest.json"
fi

# --- optional real permission probe ------------------------------------------
# A read-only summary call. It is a genuine cloud call, so it carries the same
# session-scoped User-Agent as every other call: a permission probe missing from
# the session trace would leave a gap in exactly the diagnostic trail this script
# exists to produce.
PERMISSION_OK="not_checked"
PERMISSION_ERROR=""
if [[ "$CHECK_PERMISSION" == "true" ]]; then
  if [[ "$PROFILE_CONFIGURED" != "true" ]]; then
    PERMISSION_OK="skipped"
    PERMISSION_ERROR="NoProfileConfigured"
    log_warn "skipping the permission probe: no profile configured"
  elif [[ -z "${SKILL_SESSION_ID:-}" ]]; then
    PERMISSION_OK="skipped"
    PERMISSION_ERROR="AttributionUnavailable"
    log_warn "skipping the permission probe: SKILL_SESSION_ID is not set, and an unattributed API call would be missing from the session trace"
  elif [[ "$VERSION_OK" != "true" ]]; then
    PERMISSION_OK="skipped"
    PERMISSION_ERROR="VersionUnavailable"
  else
    ua="${SKILL_NAME}/${SKILL_SESSION_ID}"
    probe="$(aliyun cloudfw describe-vpc-firewall-cen-summary-list \
      --transit-router-type Basic --page-size 1 --lang zh \
      --user-agent "AlibabaCloud-Agent-Skills/${ua} skill-version/${SKILL_VERSION}" 2>&1)"
    if printf '%s' "$probe" | grep -q '"RequestId"'; then
      PERMISSION_OK=true
    else
      PERMISSION_OK=false
      PERMISSION_ERROR="$(printf '%s' "$probe" | grep -oE 'Code: [^ ]+' | head -1 | sed 's/Code: //' || true)"
      [[ -z "$PERMISSION_ERROR" ]] && PERMISSION_ERROR="UnknownError"
      log_warn "Cloud Firewall probe failed (${PERMISSION_ERROR})."
      log_warn "Check credentials with 'aliyun configure list', and confirm yundun-cloudfirewall:DescribeVpcFirewallCenSummaryList is granted - see references/ram-policies.md."
    fi
  fi
fi

# --- optional edition probe ---------------------------------------------------
# The official procedure checks the purchased edition first, because VPC border
# firewalls need Enterprise, Ultimate or the pay-as-you-go plan and Premium cannot use
# them at all. This stays a warning rather than a gate: the numeric Version field has
# no documented mapping to an edition name, so blocking on it would be guesswork that
# turns away accounts which actually work. Reported so the operator can judge, and so
# a missing entitlement surfaces here rather than deep inside a failed attach.
EDITION_CHECK="not_checked"
EDITION_VERSION=""
if [[ "$CHECK_PERMISSION" == "true" && "$PERMISSION_OK" == "true" ]]; then
  # Reuses the permission probe's preconditions: profile, session id and version are
  # all known good by this point. Note this action takes no --lang flag.
  edition="$(aliyun cloudfw describe-user-buy-version \
    --user-agent "AlibabaCloud-Agent-Skills/${SKILL_NAME}/${SKILL_SESSION_ID} skill-version/${SKILL_VERSION}" 2>&1)"
  if printf '%s' "$edition" | grep -q '"Version"'; then
    EDITION_CHECK="reported"
    EDITION_VERSION="$(printf '%s' "$edition" | grep -oE '"Version"[[:space:]]*:[[:space:]]*[0-9]+' | grep -oE '[0-9]+$' | head -1 || true)"
    log_warn "purchased edition reported as Version=${EDITION_VERSION}. VPC border firewalls require Enterprise, Ultimate or pay-as-you-go; Premium cannot use them."
  else
    EDITION_CHECK="unavailable"
    log_warn "could not read the purchased edition; continuing, since this is advisory only"
  fi
fi

# --- machine-readable result -------------------------------------------------
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

cat <<EOF
{
  "cli_installed": ${CLI_INSTALLED},
  "cli_version": "$(json_escape "$CLI_VERSION")",
  "cli_version_ok": "${CLI_VERSION_OK}",
  "min_cli_version": "${MIN_CLI_VERSION}",
  "plugin_installed": ${PLUGIN_INSTALLED},
  "plugin_name": "${PLUGIN_NAME}",
  "plugin_version": "$(json_escape "$PLUGIN_VERSION")",
  "profile_configured": ${PROFILE_CONFIGURED},
  "current_profile": "$(json_escape "$CURRENT_PROFILE")",
  "current_region": "$(json_escape "$CURRENT_REGION")",
  "skill_version": "$(json_escape "$SKILL_VERSION")",
  "skill_version_ok": ${VERSION_OK},
  "session_id_present": $([[ -n "${SKILL_SESSION_ID:-}" ]] && echo true || echo false),
  "permission_check": "${PERMISSION_OK}",
  "permission_error": "$(json_escape "$PERMISSION_ERROR")",
  "edition_check": "${EDITION_CHECK}",
  "edition_version": "$(json_escape "$EDITION_VERSION")"
}
EOF

# Exit non-zero only when the environment cannot support the skill at all, so a
# caller can gate on the status rather than parsing the JSON. The edition probe is
# deliberately absent from this condition: it is advisory, and its numeric answer is
# not documented well enough to refuse work over.
if [[ "$CLI_INSTALLED" != "true" || "$CLI_VERSION_OK" == "false" \
      || "$PLUGIN_INSTALLED" != "true" || "$VERSION_OK" != "true" ]]; then
  exit 1
fi
exit 0
