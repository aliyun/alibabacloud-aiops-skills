#!/bin/bash
# Live-Debug Command - create a task
# Creates a live-debug task via the CMS CLI (aliyun cms2 apm service-task create)
#
# Usage: send_command.sh <workspace> <serviceId> [targetIp] <taskType> <taskConfigJson>
#
# Arguments:
#   workspace      - ARMS workspace identifier
#   serviceId      - Service/application ID
#   targetIp       - Target instance IP address (optional, default "*")
#   taskType       - Task type (e.g., "live_debug_get_memory_info")
#   taskConfigJson - The taskConfig JSON object (the CLI serializes it into a string field)
#
# Environment Variables:
#   LIVE_DEBUG_REGION_ID    - Onboarding region (e.g. cn-hangzhou), passed explicitly as CLI --region
#   LIVE_DEBUG_CMS_ENDPOINT - CMS API endpoint (optional, passed as --endpoint to override the region)
#   LIVE_DEBUG_CMS2         - Override for how the CMS CLI is invoked (default: aliyun cms2; can be aliyuncms2 or a binary path)
#
# Example:
#   send_command.sh "cc-test" "abc@def" \
#     "live_debug_get_memory_info" '{"commandType":"GET_MEMORY_INFO","language":"java","params":{},"instanceIds":["*"]}'
#
#   send_command.sh "cc-test" "abc@def" "10.0.0.1" \
#     "live_debug_get_memory_info" '{"commandType":"GET_MEMORY_INFO","language":"java","params":{},"instanceIds":["*"]}'
#
# Returns the CLI success envelope with taskId, e.g.:
#   {"success":true,"data":{"requestId":"xxx","taskId":"yyy"}}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [ $# -lt 4 ]; then
  echo "Usage: $0 <workspace> <serviceId> [targetIp] <taskType> <taskConfigJson>"
  echo ""
  echo "Arguments:"
  echo "  workspace      ARMS workspace identifier"
  echo "  serviceId      Service/application ID"
  echo "  targetIp       Target instance IP (optional, default \"*\")"
  echo "  taskType       live_debug_{command_type}"
  echo "  taskConfigJson The task config JSON object (no escaping or taskId needed)"
  echo ""
  echo "Returns taskId in response data. Use query_task.sh / get_task.sh / list_tasks.sh as needed."
  exit 1
fi

WORKSPACE="$1"
SERVICE_ID="$2"
if [ $# -eq 4 ]; then
  TARGET_IP="*"
  TASK_TYPE="$3"
  TASK_CONFIG_JSON="$4"
else
  TARGET_IP="$3"
  TASK_TYPE="$4"
  TASK_CONFIG_JSON="$5"
fi

resolve_cms2_cli || exit 1

"${CMS2[@]}" apm service-task create \
  --workspace "$WORKSPACE" \
  --service-id "$SERVICE_ID" \
  --type "$TASK_TYPE" \
  --ip "$TARGET_IP" \
  --task-config "$TASK_CONFIG_JSON" \
  "${CMS2_ARGS[@]}" \
  -o json
