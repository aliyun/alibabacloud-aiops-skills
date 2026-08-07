#!/bin/bash
# Live-Debug - delete all Probe tasks under a service (batch disable)
#
# The List API filters exactly by type, so this script lists each probe type
# separately and then deletes the tasks one by one.
#
# Usage: delete_all_probes.sh <workspace> <serviceId> [--dry-run]
#
# Example:
#   delete_all_probes.sh "agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9" "app@pid" --dry-run
#   delete_all_probes.sh "agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9" "app@pid"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <workspace> <serviceId> [--dry-run]"
  echo ""
  echo "Lists and deletes all live_debug_*_probe tasks for the service."
  exit 1
fi

WORKSPACE="$1"
SERVICE_ID="$2"
DRY_RUN=false
if [ "${3:-}" = "--dry-run" ]; then
  DRY_RUN=true
fi

# Fail fast if the CMS CLI or region cannot be resolved; child scripts
# re-resolve from the same environment variables.
resolve_cms2_cli || exit 1

DELETED=0
FOUND=0

for TASK_TYPE in "${LIVE_DEBUG_PROBE_TYPES[@]}"; do
  echo "========== Listing ${TASK_TYPE} =========="
  LIST_JSON=$("${SCRIPT_DIR}/list_tasks.sh" "$WORKSPACE" "$SERVICE_ID" "$TASK_TYPE" 100) || {
    echo "Warning: list failed for ${TASK_TYPE}, skipping" >&2
    continue
  }
  echo "$LIST_JSON"

  # Extract taskId list from the CLI success envelope: {"success":true,"data":{"serviceTasks":[...]}}
  TASK_IDS=$(echo "$LIST_JSON" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if isinstance(data, dict) and isinstance(data.get("data"), dict):
    data = data["data"]
tasks = data.get("serviceTasks") or data.get("items") or []
if isinstance(tasks, dict):
    tasks = [tasks]
for t in tasks:
    tid = t.get("taskId") if isinstance(t, dict) else None
    if tid:
        print(tid)
')

  if [ -z "$TASK_IDS" ]; then
    continue
  fi

  while IFS= read -r TASK_ID; do
    [ -z "$TASK_ID" ] && continue
    FOUND=$((FOUND + 1))
    if [ "$DRY_RUN" = true ]; then
      echo "[dry-run] would delete taskId=${TASK_ID} type=${TASK_TYPE}"
      continue
    fi
    echo "Deleting taskId=${TASK_ID} type=${TASK_TYPE}"
    "${SCRIPT_DIR}/delete_task.sh" "$WORKSPACE" "$SERVICE_ID" "$TASK_ID" "$TASK_TYPE"
    DELETED=$((DELETED + 1))
  done <<< "$TASK_IDS"
done

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "Done (dry-run). Found ${FOUND} probe task(s)."
else
  echo "Done. Deleted ${DELETED} probe task(s) (found ${FOUND})."
fi
