#!/bin/bash
# Live-Debug - list tasks
# Lists tasks by exact type via the CMS CLI (aliyun cms2 apm service-task list)
#
# Usage: list_tasks.sh <workspace> <serviceId> <taskType> [maxResults]
#
# Arguments:
#   workspace   - ARMS workspace identifier
#   serviceId   - Service/application ID
#   taskType    - Exact task type (e.g. live_debug_log_probe). List filters exactly by type.
#   maxResults  - Optional, default 100 (API max 100)
#
# Environment Variables: same as send_command.sh (LIVE_DEBUG_REGION_ID / CMS_ENDPOINT / CMS2)
#
# Example:
#   list_tasks.sh "agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9" "app@pid" "live_debug_log_probe"
#   list_tasks.sh "agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9" "app@pid" "live_debug_snapshot_probe" 50

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [ $# -lt 3 ]; then
  echo "Usage: $0 <workspace> <serviceId> <taskType> [maxResults]"
  echo ""
  echo "Lists ServiceTask records filtered by exact taskType."
  echo "For all probe types, call once per type or use delete_all_probes.sh."
  exit 1
fi

WORKSPACE="$1"
SERVICE_ID="$2"
TASK_TYPE="$3"
MAX_RESULTS="${4:-100}"

resolve_cms2_cli || exit 1

"${CMS2[@]}" apm service-task list \
  --workspace "$WORKSPACE" \
  --service-id "$SERVICE_ID" \
  --type "$TASK_TYPE" \
  --max-results "$MAX_RESULTS" \
  "${CMS2_ARGS[@]}" \
  -o json
