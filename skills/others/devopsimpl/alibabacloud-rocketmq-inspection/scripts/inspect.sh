#!/usr/bin/env bash
# RocketMQ inspection main entrypoint.
#
# Read-only policy: this script and every aliyun CLI command it issues must be
# read-only (Describe* / List* / Get* / *Info / *Status). No Create / Delete /
# Update / Modify / Set / Put or any other mutating API. See SKILL.md.
set -u

SKILL_SESSION_ID="${SKILL_SESSION_ID:-}"
UA="AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection${SKILL_SESSION_ID:+/${SKILL_SESSION_ID}}"

SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FETCH="$SKILL_ROOT/scripts/fetch_metric.sh"
LIST_INST="$SKILL_ROOT/scripts/list_instances.sh"
RENDER="$SKILL_ROOT/scripts/render_report.py"
THRESH_DEFAULT="$SKILL_ROOT/assets/thresholds.default.yaml"
THRESH_USER="$SKILL_ROOT/thresholds.yaml"

# ------- Argument parsing -------
INSTANCES_ARG=""
CONFIG_FILE=""
ALL=0
VERSION="both"
WINDOW="24h"
REGION="cn-hangzhou"

while [ $# -gt 0 ]; do
  case "$1" in
    --instances) INSTANCES_ARG="$2"; shift 2 ;;
    --config)    CONFIG_FILE="$2";   shift 2 ;;
    --all)       ALL=1;              shift   ;;
    --version)   VERSION="$2";       shift 2 ;;
    --window)    WINDOW="$2";        shift 2 ;;
    --region)    REGION="$2";        shift 2 ;;
    -h|--help)
      cat <<EOF
Usage: $0 [--instances <id1,id2>] [--config <yaml>] [--all]
          [--version 4|5|both] [--window 24h] [--region cn-hangzhou|all]

Instance source priority: --instances > --config > --all
EOF
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ------- Threshold load -------
if [ ! -f "$THRESH_USER" ]; then
  cp "$THRESH_DEFAULT" "$THRESH_USER"
  cat >&2 <<EOF
[i] Default threshold file generated at $THRESH_USER
    Edit it to match your business tolerance. The current run continues with defaults.

EOF
fi

# ------- Time window -------
parse_window_seconds() {
  local w="$1"
  case "$w" in
    *d) echo $(( ${w%d} * 86400 )) ;;
    *h) echo $(( ${w%h} * 3600 )) ;;
    *m) echo $(( ${w%m} * 60 )) ;;
    *s) echo "${w%s}" ;;
    *)  echo "Invalid --window: $w (expected like 2d, 24h, 30m, 600s)" >&2; return 1 ;;
  esac
}
WINDOW_S=$(parse_window_seconds "$WINDOW") || exit 2

if date -u -v-1H '+%s' >/dev/null 2>&1; then
  # BSD date (macOS)
  END_TS=$(date -u '+%s')
  START_TS=$((END_TS - WINDOW_S))
  START=$(date -u -r $START_TS '+%Y-%m-%dT%H:%M:%SZ')
  END=$(date -u -r $END_TS '+%Y-%m-%dT%H:%M:%SZ')
else
  # GNU date (Linux)
  START=$(date -u -d "$WINDOW_S seconds ago" '+%Y-%m-%dT%H:%M:%SZ')
  END=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
fi

# ------- Instance resolution -------
# Unified TSV output: <instanceId>\t<version>\t<region>\t<name>
detect_version() {
  case "$1" in
    rmq-*)     echo "5" ;;
    MQ_INST_*) echo "4" ;;
    *)         echo "${2:-5}" ;;
  esac
}

INSTANCES_TSV=$(mktemp)
trap 'rm -f "$INSTANCES_TSV"' EXIT

if [ -n "$INSTANCES_ARG" ]; then
  IFS=',' read -ra IDS <<< "$INSTANCES_ARG"
  for id in "${IDS[@]}"; do
    id=$(echo "$id" | xargs)
    [ -z "$id" ] && continue
    v=$(detect_version "$id" "$VERSION")
    printf "%s\t%s\t%s\t%s\n" "$id" "$v" "$REGION" "" >> "$INSTANCES_TSV"
  done
elif [ -n "$CONFIG_FILE" ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERR: parsing --config requires python3" >&2; exit 1
  fi
  python3 - "$CONFIG_FILE" "$REGION" >> "$INSTANCES_TSV" <<'PY'
import sys, os
try:
    import yaml
except ImportError:
    print("ERR: PyYAML required, run: pip3 install pyyaml", file=sys.stderr); sys.exit(1)
path, default_region = sys.argv[1], sys.argv[2]
with open(path) as f:
    cfg = yaml.safe_load(f) or {}
defaults = cfg.get('defaults', {}) or {}
for inst in (cfg.get('instances') or []):
    iid  = inst.get('id', '')
    if not iid: continue
    ver  = str(inst.get('version', '5'))
    reg  = inst.get('region', defaults.get('region', default_region))
    name = inst.get('name', '')
    print(f"{iid}\t{ver}\t{reg}\t{name}")
PY
elif [ $ALL -eq 1 ]; then
  bash "$LIST_INST" --version "$VERSION" --region "$REGION" >> "$INSTANCES_TSV"
else
  echo "ERR: one of --instances / --config / --all is required" >&2
  exit 2
fi

INST_COUNT=$(wc -l < "$INSTANCES_TSV" | tr -d ' ')
if [ "$INST_COUNT" -eq 0 ]; then
  echo "ERR: no instances to inspect" >&2; exit 1
fi

# ------- Metric pulling -------
PID=$$
WORK="/tmp/rocketmq-inspection-$PID"
mkdir -p "$WORK"
trap 'rm -f "$INSTANCES_TSV"' EXIT  # keep WORK for the renderer

ERR_LOG="$WORK/errors.log"
: > "$ERR_LOG"

INSTANCE_METRICS=(
  # Traffic & TPS
  InstanceApiCallTps InstanceApiCallTpsMax
  InstanceTpsUtilization
  InstanceSendApiCallTps InstanceSendTpsUtilization
  InstanceReceiveApiCallTps InstanceReceiveTpsUtilization
  SendMessageCountPerInstance ReceiveMessageCountPerInstance
  # Clients / connections
  InstanceOnlineClients InstanceOnlineClientsUtilization
  InstanceActiveConnection
  # Throttling
  ThrottledSendRequestsPerInstance ThrottledReceiveRequestsPerInstance
  # Public bandwidth (5.0 internet-enabled instances)
  InstanceTrafficRX InstanceTrafficTX
  InstanceTrafficRXUtilization InstanceTrafficTXUtilization
  InstanceDropTrafficRX InstanceDropTrafficTX
  InstanceInternetFlowoutBandwidth
  # Storage (5.0)
  InstanceStorageSize
)
GROUP_METRICS=(
  ConsumerLag ConsumerLagLatencyPerGid
  ReadyMessages ReadyMessageQueueTime
  ReceiveMessageCountPerGid
  ThrottledReceiveRequestsPerGid SendDLQMessageCountPerGid
)
TOPIC_METRICS=(
  SendMessageCountPerTopic ReceiveMessageCountPerTopic
  ThrottledSendRequestsPerTopic
)

TOTAL_CALLS=$(( INST_COUNT * (${#INSTANCE_METRICS[@]} + ${#GROUP_METRICS[@]} + ${#TOPIC_METRICS[@]}) ))
DONE_CALLS=0

fetch_one() {
  local metric="$1" iid="$2" out_path="$3"
  local dims="[{\"instanceId\":\"$iid\"}]"
  if bash "$FETCH" "$metric" 60 "$START" "$END" "$dims" > "$out_path" 2>>"$ERR_LOG"; then
    return 0
  else
    echo "[$iid] $metric: fetch failed (see stderr above)" >> "$ERR_LOG"
    echo "[]" > "$out_path"
    return 1
  fi
}

echo "Window: ${START} -> ${END} (UTC)" >&2
echo "Instances: ${INST_COUNT}, expected API calls: ${TOTAL_CALLS}" >&2
echo "" >&2

count_quota() {
  # Output JSON: {group_count, topic_count, retention_hours}
  local iid="$1" ver="$2" reg="$3"
  local gcnt tcnt retention
  if [ "$ver" = "5" ]; then
    gcnt=$(aliyun --user-agent "$UA" rocketmq list-consumer-groups --instance-id "$iid" --page-size 100 --region "$reg" 2>>"$ERR_LOG" \
      | jq -r '(.data.list // .data // []) | length' 2>/dev/null)
    tcnt=$(aliyun --user-agent "$UA" rocketmq list-topics --instance-id "$iid" --page-size 100 --region "$reg" 2>>"$ERR_LOG" \
      | jq -r '(.data.list // .data // []) | length' 2>/dev/null)
    # 5.x retention from GetInstance: productInfo or instanceQuotas
    retention=$(aliyun --user-agent "$UA" rocketmq get-instance --instance-id "$iid" --region "$reg" 2>>"$ERR_LOG" \
      | jq -r '(.data.productInfo.messageRetentionTime // .data.instanceQuotas.messageReserveTime // empty)' 2>/dev/null)
  else
    gcnt=$(aliyun --user-agent "$UA" ons ons-group-list --instance-id "$iid" --region "$reg" 2>>"$ERR_LOG" \
      | jq -r '(.Data.SubscribeInfoDo // []) | length' 2>/dev/null)
    tcnt=$(aliyun --user-agent "$UA" ons ons-topic-list --instance-id "$iid" --region "$reg" 2>>"$ERR_LOG" \
      | jq -r '(.Data.PublishInfoDo // []) | length' 2>/dev/null)
    # 4.x retention is fixed at 3 days (72 hours), not configurable
    retention=72
  fi
  [ -z "$gcnt" ] && gcnt=null
  [ -z "$tcnt" ] && tcnt=null
  [ -z "$retention" ] && retention=null
  echo "{\"group_count\":$gcnt,\"topic_count\":$tcnt,\"retention_hours\":$retention}"
}

count_region_instances() {
  # Count 4.x + 5.x instances in the given region, output JSON
  local reg="$1"
  local cnt_4 cnt_5
  cnt_4=$(aliyun --user-agent "$UA" ons ons-instance-in-service-list --region "$reg" 2>/dev/null \
    | jq -r '(.Data.InstanceVO // []) | length' 2>/dev/null)
  cnt_5=$(aliyun --user-agent "$UA" rocketmq list-instances --region "$reg" --page-size 100 2>/dev/null \
    | jq -r '(.data.list // .data // []) | length' 2>/dev/null)
  [ -z "$cnt_4" ] && cnt_4=0
  [ -z "$cnt_5" ] && cnt_5=0
  local total=$((cnt_4 + cnt_5))
  echo "{\"region\":\"$reg\",\"instance_4x\":$cnt_4,\"instance_5x\":$cnt_5,\"instance_total\":$total}"
}

probe_instance() {
  # Probe whether the instance really exists.
  # Print the raw response so the caller can grep for Instance.NotFound.
  local iid="$1" ver="$2" reg="$3"
  if [ "$ver" = "5" ]; then
    aliyun --user-agent "$UA" rocketmq get-instance --instance-id "$iid" --region "$reg" 2>&1
  else
    aliyun --user-agent "$UA" ons ons-instance-base-info --instance-id "$iid" --region "$reg" 2>&1
  fi
}

# Region quota: count instances per region appearing in the input list
echo "-> Counting region quota..." >&2
REGIONS_UNIQ=$(awk -F'\t' 'NF>=3 && $3!="" {print $3}' "$INSTANCES_TSV" | sort -u)
echo "[]" > "$WORK/regions.json"
for REG in $REGIONS_UNIQ; do
  ONE=$(count_region_instances "$REG")
  jq --argjson new "$ONE" '. + [$new]' "$WORK/regions.json" > "$WORK/regions.json.tmp" \
    && mv "$WORK/regions.json.tmp" "$WORK/regions.json"
done

echo "[]" > "$WORK/ghosts.json"

while IFS=$'\t' read -r IID VER REG NAME; do
  [ -z "$IID" ] && continue
  echo "-> [$VER] $IID${NAME:+ ($NAME)}" >&2

  # Ghost-instance probe
  PROBE=$(probe_instance "$IID" "$VER" "$REG")
  if echo "$PROBE" | grep -qE 'Instance\.NotFound|AccountId.NotFound|InvalidInstanceId'; then
    echo "  [skip] instance not found or released" >&2
    REASON=$(echo "$PROBE" | grep -oE 'Message:[^]]*' | head -1 | sed 's/Message: *//')
    [ -z "$REASON" ] && REASON="Instance.NotFound"
    jq --arg id "$IID" --arg ver "$VER" --arg reg "$REG" --arg reason "$REASON" \
      '. + [{instanceId:$id, version:$ver, region:$reg, reason:$reason}]' \
      "$WORK/ghosts.json" > "$WORK/ghosts.json.tmp" && mv "$WORK/ghosts.json.tmp" "$WORK/ghosts.json"
    DONE_CALLS=$((DONE_CALLS + ${#INSTANCE_METRICS[@]} + ${#GROUP_METRICS[@]} + ${#TOPIC_METRICS[@]}))
    continue
  fi

  OUTDIR="$WORK/$IID"
  mkdir -p "$OUTDIR/instance" "$OUTDIR/group" "$OUTDIR/topic" "$OUTDIR/consumer_status"
  printf '{"instanceId":"%s","version":"%s","region":"%s","name":"%s"}\n' \
    "$IID" "$VER" "$REG" "$NAME" > "$OUTDIR/meta.json"

  # Resource quota (group/topic count + retention)
  count_quota "$IID" "$VER" "$REG" > "$OUTDIR/quota.json"

  # Consumer runtime state
  if [ "$VER" = "4" ]; then
    GROUP_IDS=$(aliyun --user-agent "$UA" ons ons-group-list --instance-id "$IID" --region "$REG" 2>>"$ERR_LOG" \
      | jq -r '(.Data.SubscribeInfoDo // [])[].GroupId' 2>/dev/null)
    for GID in $GROUP_IDS; do
      [ -z "$GID" ] && continue
      aliyun --user-agent "$UA" ons ons-consumer-status --instance-id "$IID" --group-id "$GID" --detail true --region "$REG" 2>>"$ERR_LOG" \
        | jq -c '{
            groupId: "'"$GID"'",
            online: .Data.Online,
            rebalanceOk: .Data.RebalanceOK,
            subscriptionSame: .Data.SubscriptionSame,
            consumeTps: .Data.ConsumeTps,
            delayTime: .Data.DelayTime,
            totalDiff: .Data.TotalDiff,
            inflightCount: null,
            connectionCount: ((.Data.ConnectionSet.ConnectionDo // []) | length),
            consumeRt: ((.Data.ConsumerConnectionInfoList.ConsumerConnectionInfoDo // [])
                        | map((.RunningDataList.ConsumerRunningDataDo // [])[].Rt // null) | add // null)
          }' > "$OUTDIR/consumer_status/$GID.json" 2>/dev/null \
        || echo '{}' > "$OUTDIR/consumer_status/$GID.json"
      sleep 0.05
    done
  elif [ "$VER" = "5" ]; then
    # 5.x: combine get-consumer-group + list-consumer-connections + get-consumer-group-lag
    GROUP_IDS=$(aliyun --user-agent "$UA" rocketmq list-consumer-groups --instance-id "$IID" --page-size 100 --region "$REG" 2>>"$ERR_LOG" \
      | jq -r '(.data.list // .data // [])[].consumerGroupId' 2>/dev/null)
    for GID in $GROUP_IDS; do
      [ -z "$GID" ] && continue
      GROUP_CFG=$(aliyun --user-agent "$UA" rocketmq get-consumer-group --instance-id "$IID" --consumer-group-id "$GID" --region "$REG" 2>>"$ERR_LOG")
      CONNS=$(aliyun --user-agent "$UA" rocketmq list-consumer-connections --instance-id "$IID" --consumer-group-id "$GID" --region "$REG" 2>>"$ERR_LOG")
      LAG=$(aliyun --user-agent "$UA" rocketmq get-consumer-group-lag --instance-id "$IID" --consumer-group-id "$GID" --region "$REG" 2>>"$ERR_LOG")
      jq -nc \
        --argjson cfg "${GROUP_CFG:-{\}}" \
        --argjson conns "${CONNS:-{\}}" \
        --argjson lag "${LAG:-{\}}" \
        --arg gid "$GID" '
        {
          groupId: $gid,
          online: (($conns.data.connections // []) | length > 0),
          rebalanceOk: null,
          subscriptionSame: null,
          messageModel: $cfg.data.messageModel,
          deliveryOrderType: $cfg.data.deliveryOrderType,
          status: $cfg.data.status,
          consumeTps: null,
          delayTime: ($lag.data.totalLag.deliveryDuration // null),
          totalDiff: (($lag.data.totalLag.readyCount // 0) + ($lag.data.totalLag.inflightCount // 0)),
          inflightCount: ($lag.data.totalLag.inflightCount // null),
          connectionCount: (($conns.data.connections // []) | length),
          consumeRt: null,
          topicLagMap: ($lag.data.topicLagMap // {})
        }' > "$OUTDIR/consumer_status/$GID.json" 2>/dev/null \
        || echo '{}' > "$OUTDIR/consumer_status/$GID.json"
      sleep 0.05
    done
  fi

  for m in "${INSTANCE_METRICS[@]}"; do
    fetch_one "$m" "$IID" "$OUTDIR/instance/$m.json"
    DONE_CALLS=$((DONE_CALLS + 1))
    sleep 0.05
  done
  for m in "${GROUP_METRICS[@]}"; do
    fetch_one "$m" "$IID" "$OUTDIR/group/$m.json"
    DONE_CALLS=$((DONE_CALLS + 1))
    sleep 0.05
  done
  for m in "${TOPIC_METRICS[@]}"; do
    fetch_one "$m" "$IID" "$OUTDIR/topic/$m.json"
    DONE_CALLS=$((DONE_CALLS + 1))
    sleep 0.05
  done
  echo "  ($DONE_CALLS / $TOTAL_CALLS)" >&2
done < "$INSTANCES_TSV"

# ------- Metadata -------
cat > "$WORK/meta.json" <<EOF
{
  "window": "$WINDOW",
  "start_utc": "$START",
  "end_utc": "$END",
  "instance_count": $INST_COUNT,
  "thresholds_file": "$THRESH_USER"
}
EOF

# ------- Render report -------
REPORT_NAME="rocketmq-inspection-$(date '+%Y%m%d-%H%M').md"
REPORT_PATH="$(pwd)/$REPORT_NAME"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERR: rendering requires python3" >&2; exit 1
fi

python3 "$RENDER" "$WORK" "$THRESH_USER" "$REPORT_PATH"
RC=$?

if [ $RC -eq 0 ]; then
  echo "" >&2
  echo "Report: $REPORT_PATH" >&2
  if [ -s "$ERR_LOG" ]; then
    ERR_COUNT=$(grep -c 'fetch failed' "$ERR_LOG" 2>/dev/null) || ERR_COUNT=0
    [ "$ERR_COUNT" -gt 0 ] && echo "[warn] $ERR_COUNT metric(s) failed to fetch, see report 'Failed fetches' section and $ERR_LOG" >&2
  fi
  echo "Intermediate data: ${WORK} (safe to remove)" >&2
else
  echo "ERR: rendering failed, raw data kept at: $WORK" >&2
  exit 1
fi
