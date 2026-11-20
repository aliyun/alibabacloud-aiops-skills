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
#   bash scripts/loongcollector/preflight.sh [--profile <name>] [--region <region>] [--min-version 3.3.3]
#                             [--need-ecs] [--need-cs] [--need-kubectl]
#                             [--need-workbench]  (deprecated alias of --need-ecs)
set -uo pipefail

MIN_VERSION="3.3.3"
PROFILE=""
REGION=""
NEED_ECS=0
NEED_CS=0
NEED_KUBECTL=0

require_value() {
  case "${2-}" in
    ""|--*|-h) echo "missing value for $1" >&2; exit 2 ;;
  esac
}

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) require_value "$@"; PROFILE="${2:-}"; shift 2 ;;
    --region) require_value "$@"; REGION="${2:-}"; shift 2 ;;
    --min-version) require_value "$@"; MIN_VERSION="${2:-}"; shift 2 ;;
    --need-ecs)       NEED_ECS=1; shift ;;
    --need-workbench) NEED_ECS=1; shift ;;
    --need-cs)        NEED_CS=1; shift ;;
    --need-kubectl)   NEED_KUBECTL=1; shift ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Reuse shared CLI observability; accept the legacy session variable as a fallback.
SLS_SKILL_SESSION_ID="${ALIBABA_CLOUD_SLS_SKILL_SESSION:-${SKILL_SESSION_ID:-}}"
if [ -z "${ALIBABA_CLOUD_USER_AGENT:-}" ] && [ -n "$SLS_SKILL_SESSION_ID" ]; then
  export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-sls/$SLS_SKILL_SESSION_ID skill-version/0.1.0"
fi

# ---- helpers -------------------------------------------------------------
declare -a CHECKS
add_check() { # name status detail
  CHECKS+=("{\"name\":\"$1\",\"status\":\"$2\",\"detail\":\"$3\"}")
}
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
ERROR_ENTRIES=""
record_error() {
  local report
  report="$(printf '%s' "$2" | python3 "$SCRIPT_DIR/classify_sls_error.py" \
    --allow-text --step "$1" 2>/dev/null)"
  if [ -z "$report" ]; then
    report="{\"step\":\"$(json_escape "$1")\",\"error_code\":\"CLI_ERROR\",\"request_id\":\"\"}"
  fi
  [ -n "$ERROR_ENTRIES" ] && ERROR_ENTRIES="$ERROR_ENTRIES,"
  ERROR_ENTRIES="$ERROR_ENTRIES$report"
}

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
    echo "[FAIL] SLS plugin missing. Run: aliyun plugin install --names sls  (see references/cli-installation-guide.md)" >&2
  fi
fi

# ---- gate 3: credential profile presence (never print secret values) -----
if command -v aliyun >/dev/null 2>&1; then
  PROFILE="${PROFILE:-${ALIBABACLOUD_PROFILE:-${ALIBABA_CLOUD_PROFILE:-${ALICLOUD_PROFILE:-}}}}"
  if PROFILE_LIST="$(aliyun configure list 2>/dev/null)" &&
     printf '%s' "$PROFILE_LIST" | python3 -c '
import re, sys
requested = sys.argv[1]
profiles, current, valid_column = {}, None, None
for line in sys.stdin:
    cells = [cell.strip() for cell in line.split("|")]
    if len(cells) < 2:
        continue
    name = cells[0]
    if name.casefold() == "profile" and cells[1].casefold() in ("credential", "authenticationmode", "mode"):
        headings = [cell.casefold() for cell in cells]
        valid_column = headings.index("valid") if "valid" in headings else None
        continue
    if not name or all(char in "-+= " for char in name):
        continue
    selected = name.endswith("*") or name.endswith("(current)")
    name = re.sub(r"\s*(?:\*|\(current\))$", "", name).strip()
    valid = valid_column is None or (
        len(cells) > valid_column and cells[valid_column].casefold() in ("valid", "true", "yes")
    )
    profiles[name] = valid
    if selected:
        current = name
selected = requested or current
sys.exit(0 if (profiles.get(selected, False) if selected else any(profiles.values())) else 1)
' "$PROFILE"; then
    add_check "credential" "pass" "configured profile is present and marked valid"
  else
    add_check "credential" "fail" "selected profile missing/invalid, or no valid profile configured"
    READY=0
    echo "[FAIL] No valid selected credential profile. Configure a profile (do NOT paste AK/SK into chat)." >&2
  fi
fi

# ---- gate 4: scope (region) — advisory ------------------------------------
if [ -n "$REGION" ]; then
  add_check "region" "pass" "region=$REGION (declared)"
else
  add_check "region" "warn" "region not supplied; must be confirmed before any write"
fi

# ---- optional install adapters -------------------------------------------
# ECS run-command / kubectl are channel probes, not hard gates. Missing adapter →
# warn + continue (READY stays 1). Skill asks HITL / AWAITING, never PREFLIGHT_FAILED.
if [ "$NEED_ECS" -eq 1 ]; then
  if command -v aliyun >/dev/null 2>&1 && aliyun ecs run-command --help >/dev/null 2>&1; then
    add_check "ecs_runcommand" "pass" "aliyun ecs run-command available"
  else
    add_check "ecs_runcommand" "warn" "ecs run-command help failed; still ask ECS install HITL"
    echo "[WARN] aliyun ecs run-command not confirmed. Still ask: Do you confirm installing LoongCollector on the ECS instances listed above?" >&2
    echo "[WARN] Do not emit [BLOCKED: PREFLIGHT_FAILED] for this. Use run-command after confirm." >&2
  fi
fi

if [ "$NEED_CS" -eq 1 ]; then
  if command -v aliyun >/dev/null 2>&1 && aliyun plugin list 2>/dev/null | grep -qiE 'cs|aliyun-cli-cs'; then
    add_check "cs_plugin" "pass" "aliyun-cli-cs plugin installed"
    # First-use ACK not opened is a warn: Skill runs ensure_ack_prereq.sh after
    # INSTALL_CONFIRMATION. Do not PREFLIGHT_FAILED on ErrorNotEnabled / cskpro.
    CS_PROBE=""
    CS_FLAGS=()
    [ -n "$REGION" ] && CS_FLAGS+=(--region "$REGION")
    [ -n "$PROFILE" ] && CS_FLAGS+=(--profile "$PROFILE")
    if CS_PROBE="$(aliyun cs describe-clusters "${CS_FLAGS[@]}" 2>&1)"; then
      add_check "ack_service" "pass" "CS describe-clusters succeeded (possibly an empty list)"
    else
      record_error "cs describe-clusters" "$CS_PROBE"
      case "$CS_PROBE" in
      *ErrorNotEnabled*|*cskpro*|*NotEnabled*)
        add_check "ack_service" "warn" "ACK not enabled; after install confirm run scripts/loongcollector/ensure_ack_prereq.sh"
        echo "[WARN] ACK service not enabled (ErrorNotEnabled/cskpro). Not a hard gate." >&2
        echo "[WARN] After INSTALL_CONFIRMATION: bash scripts/loongcollector/ensure_ack_prereq.sh --region <r>" >&2
        ;;
      *)
        add_check "ack_service" "fail" "CS describe-clusters failed; ACK availability is unverified"
        READY=0
        echo "[FAIL] CS describe-clusters failed; resolve the CLI/API error before continuing." >&2
        ;;
      esac
    fi
  else
    add_check "cs_plugin" "fail" "aliyun-cli-cs plugin missing"
    READY=0
    echo "[FAIL] CS plugin missing. Run: aliyun plugin install --names aliyun-cli-cs" >&2
  fi
fi

if [ "$NEED_KUBECTL" -eq 1 ]; then
  if command -v kubectl >/dev/null 2>&1; then
    add_check "kubectl" "pass" "kubectl present"
  else
    add_check "kubectl" "warn" "kubectl not found; ask AWAITING KUBECONFIG (not PREFLIGHT_FAILED)"
    echo "[WARN] kubectl missing. Ask: Please provide a working kubectl and the target cluster context." >&2
    echo "[WARN] End the turn with [AWAITING: KUBECONFIG]. Do not emit [BLOCKED: PREFLIGHT_FAILED]." >&2
  fi
fi

# ---- emit JSON -----------------------------------------------------------
STATUS="ready"; [ "$READY" -eq 1 ] || STATUS="blocked"
IFS=,; CHECKS_JSON="[${CHECKS[*]}]"; unset IFS
printf '{"tool":"preflight","session_id":"%s","status":"%s","checks":%s,"errors":[%s]}\n' \
  "$(json_escape "$SLS_SKILL_SESSION_ID")" "$STATUS" "$CHECKS_JSON" "$ERROR_ENTRIES"

[ "$READY" -eq 1 ] && exit 0 || exit 1
