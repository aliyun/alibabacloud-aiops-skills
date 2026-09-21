#!/bin/bash
# Shared helpers for live-debug CMS scripts.
# Source this file:  source "$(dirname "$0")/common.sh"

# Load the canonical skill version from the repository manifest. This is a
# mandatory failure gate before any CMS or SLS cloud API call.
resolve_skill_version() {
  local common_dir manifest_path
  common_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  manifest_path="${common_dir}/../../references/manifest.json"
  if [ ! -r "$manifest_path" ]; then
    echo "Error: skill manifest not found or unreadable: ${manifest_path}" >&2
    return 1
  fi
  SKILL_VERSION=$(python3 - "$manifest_path" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
except (OSError, json.JSONDecodeError) as exc:
    print(f"Error: skill manifest is unreadable or invalid: {path}: {exc}", file=sys.stderr)
    raise SystemExit(1)
version = manifest.get("version") if isinstance(manifest, dict) else None
if not isinstance(version, str) or not version.strip():
    print(f"Error: skill manifest has no non-empty string version: {path}", file=sys.stderr)
    raise SystemExit(1)
print(version.strip())
PY
  ) || return 1
}

# Resolve REGION_ID from LIVE_DEBUG_REGION_ID, then optional name suffixes.
# Callers may pre-set WORKSPACE / PROJECT for suffix inference.
resolve_region_id() {
  REGION_ID="${LIVE_DEBUG_REGION_ID:-}"
  if [ -z "$REGION_ID" ] && [ -n "${PROJECT:-}" ] && [[ "$PROJECT" =~ -(cn-[a-z0-9-]+)$ ]]; then
    REGION_ID="${BASH_REMATCH[1]}"
  fi
  if [ -z "$REGION_ID" ] && [ -n "${WORKSPACE:-}" ] && [[ "$WORKSPACE" =~ -(cn-[a-z0-9-]+)$ ]]; then
    REGION_ID="${BASH_REMATCH[1]}"
  fi
  if [ -z "$REGION_ID" ]; then
    echo "Error: regionId is required. Set LIVE_DEBUG_REGION_ID (from .arms-info regionId) or use a project/workspace ending with region suffix (e.g. cn-hangzhou)." >&2
    return 1
  fi
}

# Resolve the CMS CLI invocation into the CMS2 array.
# Priority:
#   1. LIVE_DEBUG_CMS2         - explicit override, e.g. "aliyuncms2" or "/path/to/aliyuncms2"
#   2. aliyun cms2             - Aliyun CLI plugin (standard end-user setup)
#   3. aliyuncms2 on PATH      - standalone binary (local dev)
#   4. ~/.aliyun/aliyuncms2    - default install location of the plugin binary
resolve_cms2() {
  if [ -n "${LIVE_DEBUG_CMS2:-}" ]; then
    # shellcheck disable=SC2206
    CMS2=(${LIVE_DEBUG_CMS2})
  elif command -v aliyun >/dev/null 2>&1; then
    CMS2=(aliyun cms2)
  elif command -v aliyuncms2 >/dev/null 2>&1; then
    CMS2=(aliyuncms2)
  elif [ -x "${HOME}/.aliyun/aliyuncms2" ]; then
    CMS2=("${HOME}/.aliyun/aliyuncms2")
  else
    echo "Error: CMS CLI not found. Install Aliyun CLI + aliyuncms2 (aliyun cms2), or set LIVE_DEBUG_CMS2 to the aliyuncms2 binary path." >&2
    return 1
  fi
}

# Resolve the --user-agent flag into the UA_ARGS array (skill Observability rule).
# Priority:
#   1. LIVE_DEBUG_USER_AGENT  - full user-agent string override
#   2. LIVE_DEBUG_SESSION_ID  - 32-hex session id, expanded into the skill template
# Empty when neither is set (safe expansion: ${UA_ARGS[@]+"${UA_ARGS[@]}"}).
resolve_user_agent() {
  UA_ARGS=()
  resolve_skill_version || return 1
  if [ -n "${LIVE_DEBUG_USER_AGENT:-}" ]; then
    if [[ "$LIVE_DEBUG_USER_AGENT" != *"/skill-version/${SKILL_VERSION}/"* ]]; then
      echo "Error: LIVE_DEBUG_USER_AGENT must include /skill-version/${SKILL_VERSION}/ from references/manifest.json." >&2
      return 1
    fi
    UA_ARGS=(--user-agent "$LIVE_DEBUG_USER_AGENT")
  elif [ -n "${LIVE_DEBUG_SESSION_ID:-}" ]; then
    if [[ ! "$LIVE_DEBUG_SESSION_ID" =~ ^[a-f0-9]{32}$ ]]; then
      echo "Error: LIVE_DEBUG_SESSION_ID must be exactly 32 lowercase hexadecimal characters." >&2
      return 1
    fi
    UA_ARGS=(--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/skill-version/${SKILL_VERSION}/${LIVE_DEBUG_SESSION_ID}")
  else
    echo "Error: LIVE_DEBUG_SESSION_ID is required so every cloud API call has a versioned User-Agent." >&2
    return 1
  fi
}

# Build common CMS2 flags (region/endpoint/user-agent) into the CMS2_ARGS array.
# Always pass --region/--endpoint explicitly so we never depend on the
# machine-level default region of the Aliyun CLI config.
resolve_cms2_args() {
  CMS2_ARGS=()
  resolve_user_agent || return 1
  if [ -n "${LIVE_DEBUG_CMS_ENDPOINT:-}" ]; then
    CMS2_ARGS+=(--endpoint "$LIVE_DEBUG_CMS_ENDPOINT" ${UA_ARGS[@]+"${UA_ARGS[@]}"})
    return 0
  fi
  resolve_region_id || return 1
  CMS2_ARGS+=(--region "$REGION_ID" ${UA_ARGS[@]+"${UA_ARGS[@]}"})
}

# One-shot setup used by every CMS script.
resolve_cms2_cli() {
  resolve_cms2 || return 1
  resolve_cms2_args || return 1
}

# All live_debug probe task types (List API filters by exact type).
LIVE_DEBUG_PROBE_TYPES=(
  live_debug_log_probe
  live_debug_snapshot_probe
  live_debug_metric_probe
  live_debug_span_probe
  live_debug_span_tag_probe
)
