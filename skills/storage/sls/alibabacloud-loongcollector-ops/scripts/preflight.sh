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
#                             [--need-ecs] [--need-cs] [--need-kubectl]
#                             [--need-workbench]  (deprecated alias of --need-ecs)
set -uo pipefail

MIN_VERSION="3.3.3"
PROFILE=""
REGION=""
NEED_ECS=0
NEED_CS=0
NEED_KUBECTL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --profile)     PROFILE="${2:-}"; shift 2 ;;
    --region)      REGION="${2:-}"; shift 2 ;;
    --min-version) MIN_VERSION="${2:-}"; shift 2 ;;
    --need-ecs)       NEED_ECS=1; shift ;;
    --need-workbench) NEED_ECS=1; shift ;;
    --need-cs)        NEED_CS=1; shift ;;
    --need-kubectl)   NEED_KUBECTL=1; shift ;;
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

# ---- optional install adapters -------------------------------------------
# ECS run-command / kubectl are channel probes, not hard gates. Missing adapter →
# warn + continue (READY stays 1). Skill asks HITL / AWAITING, never PREFLIGHT_FAILED.
if [ "$NEED_ECS" -eq 1 ]; then
  if command -v aliyun >/dev/null 2>&1 && aliyun ecs run-command --help >/dev/null 2>&1; then
    add_check "ecs_runcommand" "pass" "aliyun ecs run-command available"
  else
    add_check "ecs_runcommand" "warn" "ecs run-command help failed; still ask ECS install HITL"
    echo "[WARN] aliyun ecs run-command not confirmed. Still ask: 是否确认在上述 ECS 上安装 LoongCollector？" >&2
    echo "[WARN] Do not emit [BLOCKED: PREFLIGHT_FAILED] for this. Use run-command after confirm." >&2
  fi
fi

if [ "$NEED_CS" -eq 1 ]; then
  if command -v aliyun >/dev/null 2>&1 && aliyun plugin list 2>/dev/null | grep -qiE 'cs|aliyun-cli-cs'; then
    add_check "cs_plugin" "pass" "aliyun-cli-cs plugin installed"
    # First-use ACK not opened is a warn: Skill runs ensure_ack_prereq.sh after
    # INSTALL_CONFIRMATION. Do not PREFLIGHT_FAILED on ErrorNotEnabled / cskpro.
    CS_PROBE=""
    if [ -n "$REGION" ]; then
      CS_PROBE="$(aliyun cs describe-clusters --region "$REGION" 2>&1 || true)"
    else
      CS_PROBE="$(aliyun cs describe-clusters 2>&1 || true)"
    fi
    case "$CS_PROBE" in
      *ErrorNotEnabled*|*cskpro*|*NotEnabled*)
        add_check "ack_service" "warn" "ACK not enabled; after install confirm run scripts/ensure_ack_prereq.sh"
        echo "[WARN] ACK service not enabled (ErrorNotEnabled/cskpro). Not a hard gate." >&2
        echo "[WARN] After INSTALL_CONFIRMATION: bash scripts/ensure_ack_prereq.sh --region <r>" >&2
        ;;
      *)
        add_check "ack_service" "pass" "CS describe-clusters reachable (or empty list)"
        ;;
    esac
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
    echo "[WARN] kubectl missing. Ask: 请提供可用的 kubectl 与目标集群 context。" >&2
    echo "[WARN] End the turn with [AWAITING: KUBECONFIG]. Do not emit [BLOCKED: PREFLIGHT_FAILED]." >&2
  fi
fi

# ---- emit JSON -----------------------------------------------------------
STATUS="ready"; [ "$READY" -eq 1 ] || STATUS="blocked"
IFS=,; CHECKS_JSON="[${CHECKS[*]}]"; unset IFS
printf '{"tool":"preflight","session_id":"%s","status":"%s","checks":%s}\n' \
  "$(json_escape "${SKILL_SESSION_ID:-}")" "$STATUS" "$CHECKS_JSON"

[ "$READY" -eq 1 ] && exit 0 || exit 1
