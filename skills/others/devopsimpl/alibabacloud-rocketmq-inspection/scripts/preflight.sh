#!/usr/bin/env bash
# RocketMQ inspection preflight: aliyun CLI, credentials, jq, CMS plugin availability.
# Auto-installs aliyun-cli plugins (cms/sts/ons/rocketmq) on first run.
set -u

SKILL_SESSION_ID="${SKILL_SESSION_ID:-}"
UA="AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection${SKILL_SESSION_ID:+/${SKILL_SESSION_ID}}"

PASS="✅"
FAIL="❌"
WARN="⚠️"
EXIT=0

say() { printf "%s\n" "$*"; }
ok()  { say "  ${PASS} $*"; }
err() { say "  ${FAIL} $*"; EXIT=1; }
wrn() { say "  ${WARN} $*"; }

say "RocketMQ Inspection Preflight"
say "============================="

# 1. aliyun CLI
say ""
say "[1/6] aliyun CLI"
if command -v aliyun >/dev/null 2>&1; then
  V=$(aliyun version 2>&1 | head -1)
  ok "aliyun installed: $V"
else
  err "aliyun CLI not found. Install: brew install aliyun-cli  or  https://help.aliyun.com/document_detail/121541.html"
fi

# 2. Credentials
say ""
say "[2/6] Aliyun credentials"
STS_OUT=$(aliyun --user-agent "$UA" --auto-plugin-install true sts get-caller-identity 2>&1)
if echo "$STS_OUT" | grep -q '"AccountId"'; then
  ACCOUNT_ID=$(echo "$STS_OUT" | jq -r '.AccountId // empty' 2>/dev/null)
  ok "Credentials valid, AccountId=$ACCOUNT_ID"
else
  err "Credentials invalid or unset. Run: aliyun configure"
  say "    response: $STS_OUT"
fi

# 3. jq
say ""
say "[3/6] jq"
if command -v jq >/dev/null 2>&1; then
  ok "jq installed: $(jq --version)"
else
  err "jq not found. Install: brew install jq"
fi

# 4. Auto-install required plugins (cms, ons, rocketmq) — kebab-case mode
say ""
say "[4/6] aliyun CLI plugins (cms / ons / rocketmq)"
for PRODUCT in cms ons rocketmq; do
  if [ -d ~/.aliyun/plugins/aliyun-cli-$PRODUCT ]; then
    ok "aliyun-cli-$PRODUCT plugin already installed"
  else
    say "    installing aliyun-cli-$PRODUCT ..."
    aliyun --user-agent "$UA" --auto-plugin-install true $PRODUCT --help >/dev/null 2>&1 || true
    if [ -d ~/.aliyun/plugins/aliyun-cli-$PRODUCT ]; then
      ok "aliyun-cli-$PRODUCT plugin installed"
    else
      wrn "aliyun-cli-$PRODUCT plugin install attempt finished but plugin dir not found"
    fi
  fi
done

# 5. CMS namespace probe (must use plugin / kebab-case)
say ""
say "[5/6] CMS namespace acs_rocketmq"
META=$(aliyun --user-agent "$UA" cms describe-metric-meta-list --namespace acs_rocketmq --page-size 200 2>&1)
COUNT=$(echo "$META" | jq -r '.Resources.Resource | length' 2>/dev/null)
if [ -n "$COUNT" ] && [ "$COUNT" != "null" ] && [ "$COUNT" -gt 0 ] 2>/dev/null; then
  ok "CMS reachable, $COUNT metrics under acs_rocketmq"
else
  err "describe-metric-meta-list failed or empty"
  say "    response: $(echo "$META" | head -c 300)"
fi

# 6. Management APIs (optional, non-blocking)
say ""
say "[6/6] Management APIs (optional)"
ONS_OK=0
RMQ_OK=0
if aliyun --user-agent "$UA" ons ons-instance-in-service-list --region cn-hangzhou >/dev/null 2>&1; then
  ok "ons API (4.x classic) reachable"
  ONS_OK=1
fi
if aliyun --user-agent "$UA" rocketmq list-instances --region cn-hangzhou >/dev/null 2>&1; then
  ok "rocketmq API (5.x serverless) reachable"
  RMQ_OK=1
fi
if [ $ONS_OK -eq 0 ] && [ $RMQ_OK -eq 0 ]; then
  wrn "Both management APIs unreachable. --all mode will not work; --instances <id> mode still works."
fi

say ""
say "============================="
if [ $EXIT -eq 0 ]; then
  say "${PASS} Preflight passed"
else
  say "${FAIL} Preflight failed, fix the items above"
fi
exit $EXIT
