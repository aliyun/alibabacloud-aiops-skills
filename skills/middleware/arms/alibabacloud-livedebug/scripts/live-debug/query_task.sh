#!/bin/bash
# Live-Debug - query task results
# Queries task status and capture results via SLS
# Dependencies: Bash >=3.2, Python >=3.8 (stdlib only), Aliyun CLI >=3.3.15
# with cms2 and sls commands. Shared helpers are sourced from common.sh.
#
# Usage: query_task.sh <taskId> [project] [logstore] [minutes]
#
# Arguments:
#   taskId    - Task ID returned when the task was created (required)
#   project   - Confirmed bound SLS project (optional, env LIVE_DEBUG_SLS_PROJECT)
#   logstore  - Confirmed bound logstore (optional, env LIVE_DEBUG_SLS_LOGSTORE)
#               If either is missing, discover the application's log correlation.
#   minutes   - Look-back minutes from now (optional, default 5)
#
# Environment Variables:
#   LIVE_DEBUG_SESSION_ID    - Workflow session (32 lowercase hex characters)
#   LIVE_DEBUG_REGION_ID     - CMS workspace region for binding discovery
#   LIVE_DEBUG_WORKSPACE     - Workspace for binding discovery
#   LIVE_DEBUG_SERVICE_ID    - Application service ID for binding discovery
#   LIVE_DEBUG_SLS_REGION_ID - Confirmed SLS region (otherwise use the binding's regionId)
#   LIVE_DEBUG_SLS_PROJECT   - Confirmed bound SLS project
#   LIVE_DEBUG_SLS_LOGSTORE  - Confirmed bound logstore (no fixed default)
#
# Example:
#   LIVE_DEBUG_REGION_ID=cn-hangzhou LIVE_DEBUG_WORKSPACE=my-workspace \
#     LIVE_DEBUG_SERVICE_ID=my-service query_task.sh "task-id"
#   LIVE_DEBUG_REGION_ID=cn-hangzhou \
#     query_task.sh "543057f0-3220-4767-9439-614805ea1f1b" my-project my-logstore
#   query_task.sh "543057f0-3220-4767-9439-614805ea1f1b" my-project my-logstore 10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <taskId> [project] [logstore] [minutes]"
  echo ""
  echo "Arguments:"
  echo "  taskId    Task ID returned by send_command.sh"
  echo "  project   SLS project (optional, env LIVE_DEBUG_SLS_PROJECT)"
  echo "  logstore  SLS logstore (optional, env LIVE_DEBUG_SLS_LOGSTORE)"
  echo "  minutes   Look-back minutes from now (optional, default 5)"
  echo ""
  echo "For discovery, set LIVE_DEBUG_WORKSPACE, LIVE_DEBUG_SERVICE_ID and LIVE_DEBUG_REGION_ID."
  echo "For explicit SLS targets, pass the confirmed binding's project, logstore and LIVE_DEBUG_SLS_REGION_ID."
  exit 1
fi

TASK_ID="$1"
PROJECT="${2:-${LIVE_DEBUG_SLS_PROJECT:-}}"
LOGSTORE="${3:-${LIVE_DEBUG_SLS_LOGSTORE:-}}"
MINUTES="${4:-5}"
SLS_REGION_ID="${LIVE_DEBUG_SLS_REGION_ID:-}"

resolve_user_agent || exit 1

if [[ ! "$MINUTES" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: minutes must be a positive integer." >&2
  exit 1
fi

if [ -z "$PROJECT" ] || [ -z "$LOGSTORE" ]; then
  WORKSPACE="${LIVE_DEBUG_WORKSPACE:-}"
  SERVICE_ID="${LIVE_DEBUG_SERVICE_ID:-}"
  if [ -z "$WORKSPACE" ] || [ -z "$SERVICE_ID" ]; then
    echo "Error: set LIVE_DEBUG_WORKSPACE and LIVE_DEBUG_SERVICE_ID to discover the application's bound logstore, or supply the confirmed project and logstore explicitly." >&2
    exit 1
  fi
  resolve_cms2_cli || exit 1
  BINDING_JSON=$("${CMS2[@]}" apm log-correlation get \
    --workspace "$WORKSPACE" --service-id "$SERVICE_ID" "${CMS2_ARGS[@]}" -o json) || exit 1
  BINDING_FIELDS=$(printf '%s' "$BINDING_JSON" | python3 -c '
import json, sys
try:
    response = json.load(sys.stdin)
    if response.get("success") is False:
        raise ValueError("log-correlation get returned success=false")
    record = response.get("data", response).get("record")
    if not isinstance(record, dict):
        raise ValueError("application has no log correlation record")
    content = record.get("recordContent")
    if isinstance(content, str):
        content = json.loads(content)
    if not isinstance(content, dict):
        raise ValueError("recordContent must be a JSON object")
    if content.get("bindType", "logstore") != "logstore":
        raise ValueError("binding is not a logstore; this script requires a confirmed logstore target")
    fields = [content.get(key) for key in ("project", "storeName", "regionId")]
    if any(not isinstance(v, str) or not v or any(c.isspace() for c in v) for v in fields):
        raise ValueError("binding requires non-empty project, storeName and regionId")
    print("\t".join(fields))
except (ValueError, AttributeError, TypeError) as exc:
    print(f"Error: cannot resolve application log binding: {exc}", file=sys.stderr)
    sys.exit(1)
') || exit 1
  IFS=$'\t' read -r BOUND_PROJECT BOUND_LOGSTORE BOUND_REGION <<< "$BINDING_FIELDS"
  if { [ -n "$PROJECT" ] && [ "$PROJECT" != "$BOUND_PROJECT" ]; } || \
     { [ -n "$LOGSTORE" ] && [ "$LOGSTORE" != "$BOUND_LOGSTORE" ]; } || \
     { [ -n "$SLS_REGION_ID" ] && [ "$SLS_REGION_ID" != "$BOUND_REGION" ]; }; then
    echo "Error: explicit SLS parameters conflict with the application's log correlation binding." >&2
    exit 1
  fi
  PROJECT="$BOUND_PROJECT"
  LOGSTORE="$BOUND_LOGSTORE"
  SLS_REGION_ID="$BOUND_REGION"
fi

if [ -z "$SLS_REGION_ID" ]; then
  resolve_region_id || exit 1
  SLS_REGION_ID="$REGION_ID"
fi

TO_TS=$(date +%s)
if date --version >/dev/null 2>&1; then
  FROM_TS=$(date -d "-${MINUTES} minutes" +%s)
else
  FROM_TS=$((TO_TS - MINUTES * 60))
fi

STATUS_QUERY="* and \"${TASK_ID}\" | SELECT content FROM log WHERE json_extract_scalar(attributes, '\$[\"livedebug.report_type\"]') = 'status'"
CAPTURE_QUERY="* and \"${TASK_ID}\" | SELECT content FROM log WHERE json_extract_scalar(attributes, '\$[\"livedebug.report_type\"]') != 'status'"

echo "========== Task Status (region=${SLS_REGION_ID}) =========="
aliyun sls get-logs-v2 \
  --region "$SLS_REGION_ID" \
  "${UA_ARGS[@]}" \
  --accept-encoding gzip \
  --project "$PROJECT" \
  --logstore "$LOGSTORE" \
  --from "$FROM_TS" \
  --to "$TO_TS" \
  --query "$STATUS_QUERY"

echo ""
echo "========== Capture Results (region=${SLS_REGION_ID}) =========="
aliyun sls get-logs-v2 \
  --region "$SLS_REGION_ID" \
  "${UA_ARGS[@]}" \
  --accept-encoding gzip \
  --project "$PROJECT" \
  --logstore "$LOGSTORE" \
  --from "$FROM_TS" \
  --to "$TO_TS" \
  --query "$CAPTURE_QUERY"
