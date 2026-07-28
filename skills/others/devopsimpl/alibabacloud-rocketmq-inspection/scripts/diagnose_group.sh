#!/usr/bin/env bash
# Single-group deep diagnosis (4.x / 5.x auto-detect).
# Usage:
#   diagnose_group.sh <instanceId> <groupId> [--region cn-hangzhou]
# Output: Markdown report to ./group-diagnose-{groupId}-{YYYYMMDD-HHmm}.md
#
# Read-only policy: only Describe* / List* / Get* / *Status / *Info APIs.
set -u

SKILL_SESSION_ID="${SKILL_SESSION_ID:-}"
UA="AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection${SKILL_SESSION_ID:+/${SKILL_SESSION_ID}}"

IID="${1:?usage: diagnose_group.sh <instanceId> <groupId> [--region <r>]}"
GID="${2:?usage: diagnose_group.sh <instanceId> <groupId> [--region <r>]}"
shift 2
REGION="cn-hangzhou"
while [ $# -gt 0 ]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Auto-detect version from instance ID prefix
case "$IID" in
  rmq-*)     VER="5" ;;
  MQ_INST_*) VER="4" ;;
  *)         echo "Cannot detect instance version (prefix is neither rmq- nor MQ_INST_): $IID" >&2; exit 2 ;;
esac

NOW=$(date '+%Y-%m-%d %H:%M:%S')
OUT="$(pwd)/group-diagnose-${GID}-$(date '+%Y%m%d-%H%M').md"

echo "-> Diagnose [$VER.x] $IID / $GID @ $REGION" >&2

{
  echo "# Group deep diagnosis -- \`$GID\`"
  echo ""
  echo "- Instance: \`$IID\` (${VER}.x, $REGION)"
  echo "- Diagnosed at: $NOW"
  echo ""
} > "$OUT"

if [ "$VER" = "5" ]; then
  CFG=$(aliyun --user-agent "$UA" rocketmq get-consumer-group --instance-id "$IID" --consumer-group-id "$GID" --region "$REGION" 2>&1)
  CONNS=$(aliyun --user-agent "$UA" rocketmq list-consumer-connections --instance-id "$IID" --consumer-group-id "$GID" --region "$REGION" 2>&1)
  LAG=$(aliyun --user-agent "$UA" rocketmq get-consumer-group-lag --instance-id "$IID" --consumer-group-id "$GID" --region "$REGION" 2>&1)

  if ! echo "$CFG" | jq -e '.data' >/dev/null 2>&1; then
    {
      echo "## Group not found or fetch failed"
      echo ""
      echo '```'
      echo "$CFG" | head -c 500
      echo '```'
    } >> "$OUT"
    echo "FAIL, see $OUT" >&2
    exit 1
  fi

  {
    echo "## Configuration"
    echo ""
    echo "$CFG" | jq -r '.data
      | "| Field | Value |\n|------|------|",
        "| Consume model | \(.messageModel) |",
        "| Delivery order | \(.deliveryOrderType) |",
        "| Status | \(.status) |",
        "| Max retry times | \(.consumeRetryPolicy.maxRetryTimes) |",
        "| Retry policy | \(.consumeRetryPolicy.retryPolicy) |",
        "| Remark | \(.remark // "-") |",
        "| Created at | \(.createTime) |"'
    echo ""

    CONN_COUNT=$(echo "$CONNS" | jq '.data.connections | length' 2>/dev/null || echo 0)
    echo "## Client connections (count = ${CONN_COUNT})"
    echo ""
    if [ "$CONN_COUNT" -eq 0 ]; then
      echo "**No consumer connections.** This usually explains backlog / latency -- clients are stopped, offline, or unreachable."
    else
      echo "| Client ID | Host | Language | Version |"
      echo "|---|---|---|---|"
      echo "$CONNS" | jq -r '.data.connections[] | "| `\(.clientId // "?")` | \(.hostName // .remoteIp // "?") | \(.language // "?") | \(.version // "?") |"'
    fi
    echo ""

    echo "## Lag broken down by Topic"
    echo ""
    TOTAL=$(echo "$LAG" | jq '.data.totalLag')
    if [ -z "$TOTAL" ] || [ "$TOTAL" = "null" ]; then
      echo "_no lag data_"
    else
      echo "**Total**:"
      echo ""
      echo "$LAG" | jq -r '.data.totalLag
        | "- Inflight: **\(.inflightCount)** msgs (cap = 2500)",
          "- Ready: \(.readyCount) msgs",
          "- Delivery duration: \(.deliveryDuration) ms",
          "- Last consume time: \(.lastConsumeTimestamp / 1000 | strftime("%Y-%m-%d %H:%M:%S UTC"))"'
      echo ""
      echo "**Per-topic**:"
      echo ""
      echo "| Topic | Inflight | Ready | Duration(ms) | Last consume time |"
      echo "|-------|----------|-------|--------------|-------------------|"
      echo "$LAG" | jq -r '.data.topicLagMap // {} | to_entries[]
        | "| `\(.key)` | \(.value.inflightCount // 0) | \(.value.readyCount // 0) | \(.value.deliveryDuration // 0) | \(.value.lastConsumeTimestamp / 1000 | strftime("%Y-%m-%d %H:%M:%S UTC")) |"'
    fi
    echo ""

    # Conclusion
    READY=$(echo "$LAG" | jq -r '.data.totalLag.readyCount // 0')
    INFLIGHT=$(echo "$LAG" | jq -r '.data.totalLag.inflightCount // 0')
    echo "## Conclusion"
    echo ""
    if [ "$CONN_COUNT" -eq 0 ] && [ "$READY" -gt 0 ]; then
      echo "[critical] Consumer fully offline and ${READY} ready messages unconsumed -> start a consumer and the backlog should drain immediately."
    elif [ "$CONN_COUNT" -eq 0 ]; then
      echo "[watch] Consumer offline, no backlog right now; business not impacted. Start a consumer to keep the subscription active."
    elif [ "$INFLIGHT" -ge 2000 ]; then
      echo "[critical] Inflight messages ${INFLIGHT} close to the 2500 cap (5.x limit) -> review consumer logic for blocking / processing timeouts."
    elif [ "$READY" -gt 1000 ]; then
      echo "[watch] ${READY} ready messages waiting for delivery; consume rate may not keep up with produce rate."
    else
      echo "[healthy] State looks normal."
    fi
  } >> "$OUT"

else
  # 4.x diagnosis
  STATUS=$(aliyun --user-agent "$UA" ons ons-consumer-status --instance-id "$IID" --group-id "$GID" --detail true --region "$REGION" 2>&1)
  if ! echo "$STATUS" | jq -e '.Data' >/dev/null 2>&1; then
    {
      echo "## Group not found or fetch failed"
      echo ""
      echo '```'
      echo "$STATUS" | head -c 500
      echo '```'
    } >> "$OUT"
    echo "FAIL, see $OUT" >&2
    exit 1
  fi

  {
    echo "## Status overview"
    echo ""
    echo "$STATUS" | jq -r '.Data
      | "| Field | Value |\n|------|------|",
        "| Consume model | \(.ConsumeModel) |",
        "| Online | \(if .Online then "yes" else "no" end) |",
        "| Rebalance OK | \(if .RebalanceOK then "yes" else "no" end) |",
        "| Subscription consistent | \(if .SubscriptionSame then "yes" else "no" end) |",
        "| Consume TPS | \(.ConsumeTps) |",
        "| Delay (ms) | \(.DelayTime) |",
        "| Backlog total | \(.TotalDiff) |"'
    echo ""

    CONN_COUNT=$(echo "$STATUS" | jq '.Data.ConnectionSet.ConnectionDo | length' 2>/dev/null || echo 0)
    echo "## Client connections (count = ${CONN_COUNT})"
    echo ""
    if [ "$CONN_COUNT" -eq 0 ]; then
      echo "**No consumer connections.**"
    else
      echo "| Client ID | Internal IP | Public IP | Language | Version |"
      echo "|---|---|---|---|---|"
      echo "$STATUS" | jq -r '.Data.ConnectionSet.ConnectionDo[] | "| `\(.ClientId)` | \(.ClientAddr) | \(.RemoteIP // "-") | \(.Language) | \(.Version) |"'
    fi
    echo ""

    echo "## Per-topic backlog"
    echo ""
    TOPIC_DETAILS=$(echo "$STATUS" | jq '.Data.DetailInTopicList.DetailInTopicDo // []')
    if [ "$(echo "$TOPIC_DETAILS" | jq 'length')" -eq 0 ]; then
      echo "_no per-topic detail_"
    else
      echo "| Topic | Backlog | Delay(ms) | Last consume time |"
      echo "|-------|---------|-----------|-------------------|"
      echo "$TOPIC_DETAILS" | jq -r '.[] | "| `\(.Topic)` | \(.TotalDiff) | \(.DelayTime) | \(if .LastTimestamp > 0 then (.LastTimestamp / 1000 | strftime("%Y-%m-%d %H:%M:%S UTC")) else "-" end) |"'
    fi
    echo ""

    echo "## Consumer runtime data"
    echo ""
    CINFO=$(echo "$STATUS" | jq '.Data.ConsumerConnectionInfoList.ConsumerConnectionInfoDo // []')
    if [ "$(echo "$CINFO" | jq 'length')" -eq 0 ]; then
      echo "_no runtime data_"
    else
      echo "$CINFO" | jq -r '.[] | "**Client `\(.ClientId)`** (threads \(.ThreadCount), \(.ConsumeType))",
        (.RunningDataList.ConsumerRunningDataDo[] | "- Topic `\(.Topic)`: OK TPS \(.OkTps), failed TPS \(.FailedTps), failures/hour \(.FailedCountPerHour), avg RT \(.Rt) ms")'
    fi
  } >> "$OUT"
fi

echo "Diagnose report: $OUT" >&2
