#!/bin/bash
# Live-Debug - query task results
# Queries task status and capture results via SLS
#
# Usage: query_task.sh <taskId> [project] [logstore] [minutes]
#
# Arguments:
#   taskId    - Task ID returned when the task was created (required)
#   project   - SLS project (optional, defaults to env LIVE_DEBUG_SLS_PROJECT)
#   logstore  - SLS logstore (optional, defaults to env LIVE_DEBUG_SLS_LOGSTORE,
#               falls back to "logstore-apm-logs")
#   minutes   - Look-back minutes from now (optional, default 5)
#
# Environment Variables:
#   LIVE_DEBUG_REGION_ID     - SLS region (effectively required; taken from .arms-info regionId).
#                              The script passes it to aliyun sls --region to avoid
#                              falling back to the CLI default region.
#                              If unset, it is inferred from the project name suffix (e.g. ...-cn-hangzhou)
#   LIVE_DEBUG_SLS_PROJECT   - Default SLS project
#   LIVE_DEBUG_SLS_LOGSTORE  - Default SLS logstore
#
# Example:
#   LIVE_DEBUG_REGION_ID=cn-hangzhou \
#     query_task.sh "543057f0-3220-4767-9439-614805ea1f1b" my-project
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
  echo "Always set LIVE_DEBUG_REGION_ID from .arms-info regionId (or ensure project ends with -cn-xxx)."
  exit 1
fi

TASK_ID="$1"
PROJECT="${2:-${LIVE_DEBUG_SLS_PROJECT:-}}"
LOGSTORE="${3:-${LIVE_DEBUG_SLS_LOGSTORE:-logstore-apm-logs}}"
MINUTES="${4:-5}"

if [ -z "$PROJECT" ]; then
  echo "Error: SLS project is required. Pass as 2nd argument or set LIVE_DEBUG_SLS_PROJECT."
  exit 1
fi

resolve_region_id || exit 1
resolve_user_agent

TO_TS=$(date +%s)
if date --version >/dev/null 2>&1; then
  FROM_TS=$(date -d "-${MINUTES} minutes" +%s)
else
  FROM_TS=$((TO_TS - MINUTES * 60))
fi

STATUS_QUERY="* and \"${TASK_ID}\" | SELECT content FROM log WHERE json_extract_scalar(attributes, '\$[\"livedebug.report_type\"]') = 'status'"
CAPTURE_QUERY="* and \"${TASK_ID}\" | SELECT content FROM log WHERE json_extract_scalar(attributes, '\$[\"livedebug.report_type\"]') != 'status'"

echo "========== Task Status (region=${REGION_ID}) =========="
aliyun sls get-logs-v2 \
  --region "$REGION_ID" \
  ${UA_ARGS[@]+"${UA_ARGS[@]}"} \
  --accept-encoding gzip \
  --project "$PROJECT" \
  --logstore "$LOGSTORE" \
  --from "$FROM_TS" \
  --to "$TO_TS" \
  --query "$STATUS_QUERY"

echo ""
echo "========== Capture Results (region=${REGION_ID}) =========="
aliyun sls get-logs-v2 \
  --region "$REGION_ID" \
  ${UA_ARGS[@]+"${UA_ARGS[@]}"} \
  --accept-encoding gzip \
  --project "$PROJECT" \
  --logstore "$LOGSTORE" \
  --from "$FROM_TS" \
  --to "$TO_TS" \
  --query "$CAPTURE_QUERY"
