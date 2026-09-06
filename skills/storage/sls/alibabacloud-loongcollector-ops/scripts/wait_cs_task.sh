#!/usr/bin/env bash
# wait_cs_task.sh — bounded poll of an ACK addon instance until active/failed.
#
# stdout = one JSON object; stderr = progress. exit 0 ready, 1 timeout/failed, 2 usage.
#
# Usage:
#   bash scripts/wait_cs_task.sh --cluster-id <id> [--addon-name loongcollector]
#                                [--region <r>] [--interval 15] [--attempts 8]
set -uo pipefail

CLUSTER_ID=""
ADDON_NAME="loongcollector"
REGION=""
INTERVAL=15
ATTEMPTS=8

while [ $# -gt 0 ]; do
  case "$1" in
    --cluster-id) CLUSTER_ID="${2:-}"; shift 2 ;;
    --addon-name) ADDON_NAME="${2:-}"; shift 2 ;;
    --region)     REGION="${2:-}"; shift 2 ;;
    --interval)   INTERVAL="${2:-}"; shift 2 ;;
    --attempts)   ATTEMPTS="${2:-}"; shift 2 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$CLUSTER_ID" ]; then
  echo "missing --cluster-id" >&2
  exit 2
fi
if [ "$ADDON_NAME" = "loongcollector-ds" ]; then
  echo "addon name must be loongcollector, not loongcollector-ds" >&2
  exit 2
fi

json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

UA="AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops session/${SKILL_SESSION_ID:-local}"
REGION_FLAG=()
[ -n "$REGION" ] && REGION_FLAG=(--region "$REGION")

LAST=""
STATE="unknown"
i=1
while [ "$i" -le "$ATTEMPTS" ]; do
  LAST="$(aliyun cs describe-cluster-addon-instance \
    --cluster-id "$CLUSTER_ID" \
    --addon-name "$ADDON_NAME" \
    "${REGION_FLAG[@]}" \
    --user-agent "$UA" 2>/dev/null || true)"
  STATE="$(printf '%s' "$LAST" | python3 -c '
import json,sys
raw=sys.stdin.read().strip()
if not raw:
    print("empty"); raise SystemExit
try:
    obj=json.loads(raw)
except Exception:
    print("unparsed"); raise SystemExit
for key in ("state","status","addon_status","healthy"):
    v=obj.get(key)
    if v:
        print(str(v).lower()); raise SystemExit
print("unknown")
' 2>/dev/null || echo unknown)"
  echo "[wait_cs_task] attempt=$i/$ATTEMPTS addon=$ADDON_NAME state=$STATE" >&2
  case "$STATE" in
    active|healthy|running|installed|true)
      printf '{"tool":"wait_cs_task","session_id":"%s","status":"ready","addon_name":"%s","cluster_id":"%s","state":"%s","attempts":%s}\n' \
        "$(json_escape "${SKILL_SESSION_ID:-}")" "$(json_escape "$ADDON_NAME")" \
        "$(json_escape "$CLUSTER_ID")" "$(json_escape "$STATE")" "$i"
      exit 0
      ;;
    failed|error|unhealthy|false)
      printf '{"tool":"wait_cs_task","session_id":"%s","status":"failed","addon_name":"%s","cluster_id":"%s","state":"%s","attempts":%s}\n' \
        "$(json_escape "${SKILL_SESSION_ID:-}")" "$(json_escape "$ADDON_NAME")" \
        "$(json_escape "$CLUSTER_ID")" "$(json_escape "$STATE")" "$i"
      exit 1
      ;;
  esac
  i=$((i + 1))
  [ "$i" -le "$ATTEMPTS" ] && sleep "$INTERVAL"
done

printf '{"tool":"wait_cs_task","session_id":"%s","status":"timeout","addon_name":"%s","cluster_id":"%s","state":"%s","attempts":%s}\n' \
  "$(json_escape "${SKILL_SESSION_ID:-}")" "$(json_escape "$ADDON_NAME")" \
  "$(json_escape "$CLUSTER_ID")" "$(json_escape "$STATE")" "$ATTEMPTS"
exit 1
