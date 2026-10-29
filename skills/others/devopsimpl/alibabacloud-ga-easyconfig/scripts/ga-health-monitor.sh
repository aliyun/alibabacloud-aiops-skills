#!/bin/bash
# ga-health-monitor.sh
# Bounded health monitoring for a GA listener.
#
# Usage:
#   bash ga-health-monitor.sh <GA_ID> <LISTENER_ID> [INTERVAL_SECONDS] [OPTIONS]
#
# Options:
#   --count N            Number of checks before exiting (default: 10)
#   --max-duration SEC   Wall-clock budget for the whole run (default: 600)
#   --unbounded          Ignore the count/duration budget and run until Ctrl+C.
#                        Interactive terminals only - never in an automated call.
#
# The run always returns once either budget is exhausted, so it is safe to run
# in the foreground of a tool call. Exit code is 0 only when the last check
# reported "normal"; 1 when the last check was abnormal or failed; 2 on usage error.

set -euo pipefail

usage() {
  sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GA_ID=""
LISTENER_ID=""
CHECK_INTERVAL=60
COUNT=10
MAX_DURATION=600
UNBOUNDED=false
POSITIONAL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --count)
      [ $# -ge 2 ] || { echo "ERROR: --count requires a value" >&2; exit 2; }
      COUNT="$2"; shift 2 ;;
    --max-duration)
      [ $# -ge 2 ] || { echo "ERROR: --max-duration requires a value" >&2; exit 2; }
      MAX_DURATION="$2"; shift 2 ;;
    --unbounded)
      UNBOUNDED=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    -*)
      echo "ERROR: unknown option '$1'" >&2; usage >&2; exit 2 ;;
    *)
      POSITIONAL=$((POSITIONAL + 1))
      case "$POSITIONAL" in
        1) GA_ID="$1" ;;
        2) LISTENER_ID="$1" ;;
        3) CHECK_INTERVAL="$1" ;;
        *) echo "ERROR: unexpected argument '$1'" >&2; usage >&2; exit 2 ;;
      esac
      shift ;;
  esac
done

is_positive_int() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
    *) [ "$1" -gt 0 ] ;;
  esac
}

[ -n "$GA_ID" ] || { echo "ERROR: GA_ID is required" >&2; usage >&2; exit 2; }
[ -n "$LISTENER_ID" ] || { echo "ERROR: LISTENER_ID is required" >&2; usage >&2; exit 2; }
printf '%s' "$GA_ID" | grep -Eq '^ga-[a-z0-9]+$' || { echo "ERROR: invalid GA_ID '$GA_ID' (expected format: ga-<lowercase alphanumeric>)" >&2; exit 2; }
printf '%s' "$LISTENER_ID" | grep -Eq '^lsr-[a-z0-9]+$' || { echo "ERROR: invalid LISTENER_ID '$LISTENER_ID' (expected format: lsr-<lowercase alphanumeric>)" >&2; exit 2; }
for pair in "INTERVAL_SECONDS:$CHECK_INTERVAL" "count:$COUNT" "max-duration:$MAX_DURATION"; do
  name="${pair%%:*}"
  value="${pair#*:}"
  is_positive_int "$value" || { echo "ERROR: $name must be a positive integer, got '$value'" >&2; exit 2; }
done
[ "$CHECK_INTERVAL" -le 3600 ] || { echo "ERROR: INTERVAL_SECONDS must be 3600 or less" >&2; exit 2; }
[ "$COUNT" -le 1000 ] || { echo "ERROR: count must be 1000 or less" >&2; exit 2; }
[ "$MAX_DURATION" -le 86400 ] || { echo "ERROR: max-duration must be 86400 or less" >&2; exit 2; }

if [ -z "${GA_USER_AGENT:-}" ]; then
  # shellcheck source=init-session.sh
  source "$SCRIPT_DIR/init-session.sh"
fi

REGION="cn-hangzhou"
START_TS=$(date +%s)
ATTEMPT=0
EXIT_CODE=1

if [ "$UNBOUNDED" = true ]; then
  echo "Starting GA health monitoring (interval: ${CHECK_INTERVAL}s, unbounded - press Ctrl+C to stop)"
else
  echo "Starting GA health monitoring (interval: ${CHECK_INTERVAL}s, count: ${COUNT}, max-duration: ${MAX_DURATION}s)"
fi
echo "Listener: ${LISTENER_ID}"
echo ""

while :; do
  ATTEMPT=$((ATTEMPT + 1))
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

  HEALTH=""
  HEALTH=$(aliyun ga get-health-status \
    --biz-region-id "$REGION" \
    --accelerator-id "$GA_ID" \
    --listener-id "$LISTENER_ID" \
    --user-agent "$GA_USER_AGENT" 2>/dev/null) || HEALTH=""

  if [ -z "$HEALTH" ]; then
    OVERALL="error"
  else
    OVERALL=$(printf '%s' "$HEALTH" | jq -r '.HealthStatus // "error"' 2>/dev/null) || OVERALL="error"
    [ -n "$OVERALL" ] || OVERALL="error"
  fi

  case "$OVERALL" in
    "normal")
      echo "[$TIMESTAMP] [OK] All endpoints healthy"
      EXIT_CODE=0
      ;;
    "partiallyAbnormal")
      echo "[$TIMESTAMP] [WARN] Some endpoints abnormal:"
      printf '%s' "$HEALTH" | jq -r '.EndpointGroups[].Endpoints[] | select(.HealthStatus != "Healthy") | "  - \(.Address): \(.HealthStatus)"' 2>/dev/null || true
      EXIT_CODE=1
      ;;
    "abnormal")
      echo "[$TIMESTAMP] [CRITICAL] All endpoints abnormal!"
      printf '%s' "$HEALTH" | jq -r '.EndpointGroups[].Endpoints[] | "  - \(.Address): \(.HealthStatus) \(.HealthDetail // "")"' 2>/dev/null || true
      EXIT_CODE=1
      ;;
    *)
      echo "[$TIMESTAMP] [ERROR] Unable to get health status: $OVERALL"
      EXIT_CODE=1
      ;;
  esac

  if [ "$UNBOUNDED" = true ]; then
    sleep "$CHECK_INTERVAL"
    continue
  fi

  if [ "$ATTEMPT" -ge "$COUNT" ]; then
    break
  fi
  ELAPSED=$(( $(date +%s) - START_TS ))
  REMAINING=$(( MAX_DURATION - ELAPSED ))
  if [ "$REMAINING" -le 0 ]; then
    break
  fi
  SLEEP_FOR="$CHECK_INTERVAL"
  if [ "$SLEEP_FOR" -gt "$REMAINING" ]; then
    SLEEP_FOR="$REMAINING"
  fi
  sleep "$SLEEP_FOR"
done

ELAPSED=$(( $(date +%s) - START_TS ))
echo ""
echo "Stopped after ${ATTEMPT} check(s) in ${ELAPSED}s. Last status: ${OVERALL}"
exit "$EXIT_CODE"
