#!/bin/bash
# Live-Debug - delete a task (the correct way to disable/uninstall a probe)
# Deletes a task via the CMS CLI (aliyun cms2 apm service-task delete)
#
# After deletion the server removes the task from the DB and triggers
# syncToConfigServer, which deactivates the probe on the Agent side.
# Do NOT create a new task with enabled:false to "disable" a probe - that
# does not affect already-dispatched tasks.
#
# Usage: delete_task.sh <workspace> <serviceId> <taskId> <taskType>
#
# Arguments:
#   workspace  - ARMS workspace identifier
#   serviceId  - Service/application ID
#   taskId     - Task ID to delete
#   taskType   - Exact task type (must match the task; e.g. live_debug_log_probe)
#
# Example:
#   delete_task.sh "agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9" "app@pid" "task-uuid" "live_debug_log_probe"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [ $# -lt 4 ]; then
  echo "Usage: $0 <workspace> <serviceId> <taskId> <taskType>"
  echo ""
  echo "Deletes a ServiceTask and syncs config so the probe/command is removed from agents."
  exit 1
fi

WORKSPACE="$1"
SERVICE_ID="$2"
TASK_ID="$3"
TASK_TYPE="$4"

resolve_cms2_cli || exit 1

"${CMS2[@]}" apm service-task delete \
  --workspace "$WORKSPACE" \
  --service-id "$SERVICE_ID" \
  --task-id "$TASK_ID" \
  --type "$TASK_TYPE" \
  "${CMS2_ARGS[@]}" \
  -o json
