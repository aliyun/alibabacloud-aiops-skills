#!/bin/bash
# Poll `aliyun cs describe-task-info` until the task reaches a terminal state.
#
# Usage:
#   ./wait-for-task.sh <task-id> <region-id> [interval-seconds] [timeout-seconds]
#
# Examples:
#   ./wait-for-task.sh T-69ce1022aa09ae010300000b cn-hangzhou
#   ./wait-for-task.sh T-69ce1022aa09ae010300000b cn-hangzhou 30 1800
#
# Why region is required: task IDs are region-scoped; calling without the
# right --region either fails or routes through the default endpoint with
# extra latency. See SKILL.md §6 Rule B.
#
# Note: the cs plugin's global flag is `--region` (value is a region ID like
# cn-hangzhou), not `--region-id`. Don't confuse with `--biz-region-id`, which
# is the business parameter on `*ForRegion` APIs.
#
# Exits 0 on `success`, 1 on `failed`/`canceled`/timeout, 2 on usage error.
# Prints the final task envelope on stdout when terminal.
#
# Requires: aliyun (>= 3.3.3 with `cs` plugin), jq.

set -e

TASK_ID="${1:-}"
REGION="${2:-}"
INTERVAL="${3:-30}"
TIMEOUT="${4:-1800}"

if [ "$TASK_ID" = "--help" ] || [ "$TASK_ID" = "-h" ]; then
    cat <<EOF
Usage: $0 <task-id> <region-id> [interval-seconds] [timeout-seconds]

Poll 'aliyun cs describe-task-info' until terminal state. Region is required
because task IDs are region-scoped.

Defaults: interval=30s, timeout=1800s.
Exits 0 on success, 1 on failed/canceled/timeout, 2 on usage error.
Final task envelope printed to stdout when terminal.

Example: $0 T-69ce1022aa09ae010300000b cn-hangzhou 30 1800
EOF
    exit 0
fi

if [ -z "$TASK_ID" ] || [ -z "$REGION" ]; then
    echo "Usage: $0 <task-id> <region-id> [interval-seconds] [timeout-seconds]" >&2
    echo "Run '$0 --help' for full usage." >&2
    exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is required but not found in PATH" >&2
    exit 2
fi

echo "Polling task $TASK_ID in $REGION every ${INTERVAL}s (timeout ${TIMEOUT}s)..." >&2

START=$(date +%s)
LAST_STAGE=""

while :; do
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))

    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "Timeout after ${ELAPSED}s — task still not terminal." >&2
        aliyun cs describe-task-info --task-id "$TASK_ID" --region "$REGION" || true
        exit 1
    fi

    RESP=$(aliyun cs describe-task-info --task-id "$TASK_ID" --region "$REGION" 2>/dev/null || echo '{}')
    STATE=$(echo "$RESP" | jq -r '.state // "unknown"')
    STAGE=$(echo "$RESP" | jq -r '.current_stage // ""')

    if [ "$STAGE" != "$LAST_STAGE" ] && [ -n "$STAGE" ]; then
        echo "[${ELAPSED}s] state=${STATE} stage=${STAGE}" >&2
        LAST_STAGE="$STAGE"
    else
        echo "[${ELAPSED}s] state=${STATE}" >&2
    fi

    # ACK uses several spellings for the failure terminal state across task
    # types: `failed`, `fail`, `error`. Treat all of them as terminal failure.
    case "$STATE" in
        success|succeeded)
            echo "$RESP"
            exit 0
            ;;
        failed|fail|error|canceled|cancelled)
            echo "Task ended with state=${STATE}" >&2
            echo "$RESP" | jq '.error // .' >&2
            echo "$RESP"
            exit 1
            ;;
        running|paused|pending|"")
            sleep "$INTERVAL"
            ;;
        unknown)
            echo "Could not parse task state — response was:" >&2
            echo "$RESP" >&2
            sleep "$INTERVAL"
            ;;
        *)
            echo "Unexpected state '$STATE' — continuing to poll" >&2
            sleep "$INTERVAL"
            ;;
    esac
done
