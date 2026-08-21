#!/usr/bin/env bash
# preflight.sh — gate check for alibabacloud-loongcollector-ops.
#
# Verifies: aliyun CLI present + version, aliyun-cli-sls plugin present, a usable
# credential profile, and (optionally) region/scope readiness. Read-only: never
# prints AK/SK or token values, never mutates config.
#
# Protocol: stdout = single JSON object; stderr = human diagnostics; exit code:
#   0 = all gates pass (ready)
#   1 = a hard gate failed (blocked)
#   2 = usage / internal error
#
# Usage:
#   bash scripts/preflight.sh [--profile <name>] [--region <region>] [--min-version 3.3.3]
set -uo pipefail

MIN_VERSION="3.3.3"
PROFILE=""
REGION=""

while [ $# -gt 0 ]; do
  case "$1" in
    --profile)     PROFILE="${2:-}"; shift 2 ;;
    --region)      REGION="${2:-}"; shift 2 ;;
    --min-version) MIN_VERSION="${2:-}"; shift 2 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---- helpers -------------------------------------------------------------
declare -a CHECKS
add_check() { # name status detail
  CHECKS+=("{\"name\":\"$1\",\"status\":\"$2\",\"detail\":\"$3\"}")
}
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

# version compare: returns 0 if $1 >= $2
ver_ge() {
  [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

READY=1

# ---- gate 1: aliyun CLI present ------------------------------------------
if command -v aliyun >/dev/null 2>&1; then
  RAW_VER="$(aliyun version 2>/dev/null | head -n1 | tr -d '\r')"
  if [ -n "$RAW_VER" ] && ver_ge "$RAW_VER" "$MIN_VERSION"; then
    add_check "cli_version" "pass" "aliyun $RAW_VER (>= $MIN_VERSION)"
  else
    add_check "cli_version" "fail" "aliyun ${RAW_VER:-unknown} < required $MIN_VERSION"
    READY=0
    echo "[FAIL] aliyun CLI version ${RAW_VER:-unknown} < $MIN_VERSION. See references/cli-installation-guide.md" >&2
  fi
else
  add_check "cli_present" "fail" "aliyun not found in PATH"
  READY=0
  echo "[FAIL] aliyun CLI not installed. See references/cli-installation-guide.md" >&2
fi

# ---- gate 2: SLS plugin present ------------------------------------------
if command -v aliyun >/dev/null 2>&1; then
  if aliyun plugin list 2>/dev/null | grep -qi "sls"; then
    add_check "sls_plugin" "pass" "aliyun-cli-sls plugin installed"
  else
    add_check "sls_plugin" "fail" "aliyun-cli-sls plugin missing"
    READY=0
    echo "[FAIL] SLS plugin missing. Run: aliyun plugin install --names aliyun-cli-sls  (see references/cli-installation-guide.md)" >&2
  fi
fi

# ---- gate 3: credential profile presence (never print secret values) -----
if command -v aliyun >/dev/null 2>&1; then
  PROFILE_LIST="$(aliyun configure list 2>/dev/null)"
  if [ -n "$PROFILE_LIST" ] && printf '%s' "$PROFILE_LIST" | grep -qiE 'profile|AccessKey'; then
    if [ -n "$PROFILE" ]; then
      if printf '%s' "$PROFILE_LIST" | grep -qw "$PROFILE"; then
        add_check "credential" "pass" "profile '$PROFILE' present"
      else
        add_check "credential" "fail" "profile '$PROFILE' not found"
        READY=0
        echo "[FAIL] profile '$PROFILE' not found in 'aliyun configure list'." >&2
      fi
    else
      add_check "credential" "pass" "at least one profile configured"
    fi
  else
    add_check "credential" "fail" "no aliyun profile configured"
    READY=0
    echo "[FAIL] No credential profile. Configure a profile (do NOT paste AK/SK into chat)." >&2
  fi
fi

# ---- gate 4: scope (region) — advisory ------------------------------------
if [ -n "$REGION" ]; then
  add_check "region" "pass" "region=$REGION (declared)"
else
  add_check "region" "warn" "region not supplied; must be confirmed before any write"
fi

# ---- emit JSON -----------------------------------------------------------
STATUS="ready"; [ "$READY" -eq 1 ] || STATUS="blocked"
IFS=,; CHECKS_JSON="[${CHECKS[*]}]"; unset IFS
printf '{"tool":"preflight","session_id":"%s","status":"%s","checks":%s}\n' \
  "$(json_escape "${SKILL_SESSION_ID:-}")" "$STATUS" "$CHECKS_JSON"

[ "$READY" -eq 1 ] && exit 0 || exit 1
