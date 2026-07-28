#!/usr/bin/env bash
# Dynamically list RocketMQ instances (4.x and/or 5.x).
# Output: TSV "<instanceId>\t<version>\t<region>\t<name>"
set -u

SKILL_SESSION_ID="${SKILL_SESSION_ID:-}"
UA="AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection${SKILL_SESSION_ID:+/${SKILL_SESSION_ID}}"

VERSION="both"
REGION="cn-hangzhou"

while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --region)  REGION="$2";  shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--version 4|5|both] [--region cn-hangzhou|all]" >&2
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

list_4x() {
  local out
  out=$(aliyun --user-agent "$UA" ons ons-instance-in-service-list --region "$REGION" 2>&1)
  if [ $? -ne 0 ]; then
    echo "WARN: 4.x list-instances failed (region=$REGION): $(echo "$out" | head -c 200)" >&2
    return 0
  fi
  echo "$out" | jq -r --arg r "$REGION" '
    (.Data.InstanceVO // [])[]
    | [.InstanceId, "4", $r, (.InstanceName // "")]
    | @tsv
  '
}

list_5x() {
  local out page=1 total_seen=0
  while :; do
    out=$(aliyun --user-agent "$UA" rocketmq list-instances --region "$REGION" --page-size 100 --page-number "$page" 2>&1)
    if [ $? -ne 0 ]; then
      echo "WARN: 5.x list-instances failed (region=$REGION, page=$page): $(echo "$out" | head -c 200)" >&2
      return 0
    fi
    # Compatible 5.x response shapes: data.list[] / data[] / Data[]
    local rows
    rows=$(echo "$out" | jq -r --arg r "$REGION" '
      ((.data.list // .data // .Data // []) | if type == "array" then . else [] end)[]
      | [(.instanceId // .InstanceId // ""), "5", $r, (.instanceName // .InstanceName // "")]
      | select(.[0] != "")
      | @tsv
    ' 2>/dev/null)
    [ -z "$rows" ] && break
    echo "$rows"
    local cnt
    cnt=$(echo "$rows" | wc -l | tr -d ' ')
    total_seen=$((total_seen + cnt))
    [ "$cnt" -lt 100 ] && break
    page=$((page + 1))
    [ "$page" -gt 100 ] && { echo "WARN: 5.x list-instances paging exceeded 100, aborting" >&2; break; }
    sleep 0.05
  done
}

scan_one_region() {
  local r="$1"
  REGION="$r"
  case "$VERSION" in
    4)    list_4x ;;
    5)    list_5x ;;
    both) list_4x; list_5x ;;
    *)    echo "Invalid --version: $VERSION (expected 4|5|both)" >&2; exit 2 ;;
  esac
}

# Mainstream Alibaba Cloud regions where RocketMQ may exist (4.x + 5.x combined)
ALL_REGIONS="
cn-hangzhou cn-shanghai cn-beijing cn-shenzhen cn-qingdao cn-zhangjiakou
cn-chengdu cn-hongkong cn-huhehaote cn-wulanchabu cn-heyuan cn-guangzhou
ap-southeast-1 ap-southeast-2 ap-southeast-3 ap-southeast-5
ap-northeast-1 us-east-1 us-west-1 eu-central-1 eu-west-1 me-east-1
"

if [ "$REGION" = "all" ]; then
  for r in $ALL_REGIONS; do
    scan_one_region "$r"
  done
else
  scan_one_region "$REGION"
fi
