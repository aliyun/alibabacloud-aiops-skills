#!/bin/bash
# Live-Debug - get a single task
# Fetches one task via the CMS CLI (aliyun cms2 apm service-task get)
#
# Usage: get_task.sh <workspace> <serviceId> <taskId> <taskType>
#
# Arguments:
#   workspace  - ARMS workspace identifier
#   serviceId  - Service/application ID
#   taskId     - Task ID returned by create
#   taskType   - Exact task type (e.g. live_debug_log_probe)
#
# Example:
#   get_task.sh "agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9" "app@pid" "task-uuid" "live_debug_log_probe"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [ $# -lt 4 ]; then
  echo "Usage: $0 <workspace> <serviceId> <taskId> <taskType>"
  exit 1
fi

WORKSPACE="$1"
SERVICE_ID="$2"
TASK_ID="$3"
TASK_TYPE="$4"

resolve_cms2_cli || exit 1

"${CMS2[@]}" apm service-task get \
  --workspace "$WORKSPACE" \
  --service-id "$SERVICE_ID" \
  --task-id "$TASK_ID" \
  --type "$TASK_TYPE" \
  "${CMS2_ARGS[@]}" \
  -o json
