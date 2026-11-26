#!/bin/bash
# Live-Debug - query task results
# Queries task status and capture results via SLS
# Dependencies: Bash >=3.2, Python >=3.8 (stdlib only), Aliyun CLI >=3.3.15
# with cms2 and sls commands. Shared helpers are sourced from common.sh.
#
# Usage: query_task.sh <taskId> [trace-project] [logstore-apm-logs] [minutes]
# Project can also be set with LIVE_DEBUG_SLS_PROJECT. Set LIVE_DEBUG_SLS_REGION_ID
# to the trace project's region. The third argument is retained for existing callers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <taskId> [trace-project] [logstore-apm-logs] [minutes]"
  exit 1
fi

TASK_ID="$1"
# The ID is inserted into a quoted SLS search term.
case "$TASK_ID" in
  ''|*[!abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-]*)
    echo "Error: taskId must contain only ASCII letters, digits, underscores or hyphens." >&2
    exit 1 ;;
esac
PROJECT="${2:-${LIVE_DEBUG_SLS_PROJECT:-}}"
LOGSTORE="logstore-apm-logs"
MINUTES="${4:-5}"
SLS_REGION_ID="${LIVE_DEBUG_SLS_REGION_ID:-}"

resolve_user_agent || exit 1

if [[ ! "$MINUTES" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: minutes must be a positive integer." >&2
  exit 1
fi

if [ -z "$PROJECT" ]; then
  echo "Error: supply the workspace trace project or set LIVE_DEBUG_SLS_PROJECT." >&2
  exit 1
fi
if [ -n "${3:-}" ] && [ "$3" != "$LOGSTORE" ]; then
  echo "Error: Live Debug queries use the fixed logstore $LOGSTORE." >&2
  exit 1
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
