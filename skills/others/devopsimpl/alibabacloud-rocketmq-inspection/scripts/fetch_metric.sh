#!/usr/bin/env bash
# Pull a single CMS metric with automatic pagination + retry.
# Usage:
#   fetch_metric.sh <metric> <period> <start> <end> <dimensions_json>
# Output: merged Datapoints array (one line of JSON). Non-zero exit on failure.
set -u

SKILL_SESSION_ID="${SKILL_SESSION_ID:-}"
UA="AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection${SKILL_SESSION_ID:+/${SKILL_SESSION_ID}}"

METRIC="${1:?metric name required}"
PERIOD="${2:?period required}"
START="${3:?start time required}"
END="${4:?end time required}"
DIMENSIONS="${5:?dimensions json required}"

call_once() {
  local next="$1"
  local extra=()
  [ -n "$next" ] && extra=(--next-token "$next")
  aliyun --user-agent "$UA" cms describe-metric-list \
    --namespace acs_rocketmq \
    --metric-name "$METRIC" \
    --period "$PERIOD" \
    --start-time "$START" \
    --end-time "$END" \
    --dimensions "$DIMENSIONS" \
    --length 1000 \
    ${extra[@]+"${extra[@]}"} 2>&1
}

ALL_POINTS="[]"
NEXT=""
PAGE=0
MAX_PAGES=50

while :; do
  PAGE=$((PAGE + 1))
  if [ $PAGE -gt $MAX_PAGES ]; then
    echo "ERR[$METRIC]: page count exceeded $MAX_PAGES, aborting" >&2
    break
  fi

  # Exponential backoff retry
  ATTEMPT=0
  while :; do
    ATTEMPT=$((ATTEMPT + 1))
    OUT=$(call_once "$NEXT")
    RC=$?
    if [ $RC -eq 0 ] && echo "$OUT" | jq -e '.Datapoints' >/dev/null 2>&1; then
      break
    fi
    if [ $ATTEMPT -ge 3 ]; then
      echo "ERR[$METRIC]: call failed (retried ${ATTEMPT} times): $(echo "$OUT" | head -c 300)" >&2
      exit 1
    fi
    SLEEP_S=$((ATTEMPT * 2))
    echo "WARN[$METRIC]: attempt $ATTEMPT failed, retry in ${SLEEP_S}s" >&2
    sleep $SLEEP_S
  done

  # Datapoints is a stringified JSON; parse twice
  PAGE_POINTS=$(echo "$OUT" | jq -r '.Datapoints // "[]"' | jq -c '. // []')
  if [ -z "$PAGE_POINTS" ] || [ "$PAGE_POINTS" = "null" ]; then
    PAGE_POINTS="[]"
  fi
  ALL_POINTS=$(echo "$ALL_POINTS $PAGE_POINTS" | jq -s -c 'add')

  NEXT=$(echo "$OUT" | jq -r '.NextToken // empty')
  [ -z "$NEXT" ] && break
  sleep 0.05
done

echo "$ALL_POINTS"
