#!/usr/bin/env bash
# poll_task.sh — Poll PolarDB-X async task status until completion or timeout.
#
# Dependencies:
#   - aliyun CLI >= 3.3.3 (with polardbx plugin)
#   - jq >= 1.6
#   - bash >= 4.0
#
# Usage:
#   ./scripts/poll_task.sh \
#     --region <RegionId> \
#     --instance-id <DBInstanceId> \
#     --start-time <YYYY-MM-DD> \
#     --end-time <YYYY-MM-DD> \
#     --session-id <32-char-hex> \
#     [--interval <seconds>] \
#     [--timeout <seconds>]
#
# Defaults:
#   interval = 10 seconds
#   timeout  = 1800 seconds (30 minutes)
#
# Exit codes:
#   0 — All tasks completed successfully
#   1 — Task failure detected (TaskErrorCode non-empty)
#   2 — Timeout reached
#   3 — Invalid arguments

set -euo pipefail

# --- Defaults ---
INTERVAL=10
TIMEOUT=1800
REGION=""
INSTANCE_ID=""
START_TIME=""
END_TIME=""
SESSION_ID=""

# --- Argument parsing ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)        REGION="$2"; shift 2 ;;
    --instance-id)   INSTANCE_ID="$2"; shift 2 ;;
    --start-time)    START_TIME="$2"; shift 2 ;;
    --end-time)      END_TIME="$2"; shift 2 ;;
    --session-id)    SESSION_ID="$2"; shift 2 ;;
    --interval)      INTERVAL="$2"; shift 2 ;;
    --timeout)       TIMEOUT="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      exit 3
      ;;
  esac
done

# --- Validation ---
if [[ -z "$REGION" || -z "$INSTANCE_ID" || -z "$START_TIME" || -z "$END_TIME" || -z "$SESSION_ID" ]]; then
  echo "ERROR: --region, --instance-id, --start-time, --end-time, and --session-id are all required." >&2
  exit 3
fi

UA="AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/${SESSION_ID}"

# --- Polling loop ---
elapsed=0
while [[ $elapsed -lt $TIMEOUT ]]; do
  result=$(aliyun polardbx describe-tasks \
    --biz-region-id "$REGION" \
    --region "$REGION" \
    --db-instance-id "$INSTANCE_ID" \
    --start-time "$START_TIME" \
    --end-time "$END_TIME" \
    --page-number 1 \
    --page-size 100 \
    --connect-timeout 3 --read-timeout 10 \
    --user-agent "$UA" 2>&1) || true

  # Check for API errors
  if echo "$result" | jq -e '.Code' >/dev/null 2>&1; then
    error_code=$(echo "$result" | jq -r '.Code // empty')
    if [[ -n "$error_code" ]]; then
      echo "API Error: $error_code — $(echo "$result" | jq -r '.Message // empty')" >&2
      sleep "$INTERVAL"
      elapsed=$((elapsed + INTERVAL))
      continue
    fi
  fi

  # Parse tasks. DescribeTasks returns the task list in `.Items[]` (NOT `.Tasks[]`).
  tasks=$(echo "$result" | jq -r '.Items // [] | .[]')
  if [[ -z "$tasks" ]]; then
    echo "No tasks found. Waiting..."
    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
    continue
  fi

  # Check task statuses. A task is finished once `FinishTime` is non-empty; its
  # `Status` then indicates success or failure. Tasks without `FinishTime` are
  # still running.
  all_done=true
  has_failure=false

  while IFS= read -r task; do
    status=$(echo "$task" | jq -r '.Status // "UNKNOWN"')
    task_id=$(echo "$task" | jq -r '.TaskId // "N/A"')
    error_code=$(echo "$task" | jq -r '.TaskErrorCode // empty')
    finish_time=$(echo "$task" | jq -r '.FinishTime // empty')

    if [[ -n "$finish_time" ]]; then
      case "$status" in
        "FAILED"|"ERROR"|"15"|"9")
          echo "Task $task_id: FAILED — ErrorCode=$error_code, Message=$(echo "$task" | jq -r '.TaskErrorMessage // empty')" >&2
          has_failure=true
          ;;
        *)
          echo "Task $task_id: COMPLETED (status=$status)"
          ;;
      esac
    else
      case "$status" in
        "FINISH"|"SUCCESS")
          echo "Task $task_id: COMPLETED (status=$status)"
          ;;
        *)
          echo "Task $task_id: IN_PROGRESS (status=$status)"
          all_done=false
          ;;
      esac
    fi
  done < <(echo "$result" | jq -c '.Items[]')

  if [[ "$has_failure" == "true" ]]; then
    echo "RESULT: Task failure detected." >&2
    exit 1
  fi

  if [[ "$all_done" == "true" ]]; then
    echo "RESULT: All tasks completed successfully."
    exit 0
  fi

  sleep "$INTERVAL"
  elapsed=$((elapsed + INTERVAL))
done

echo "RESULT: Timeout reached after ${TIMEOUT}s." >&2
exit 2
