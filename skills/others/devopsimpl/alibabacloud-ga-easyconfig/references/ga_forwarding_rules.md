# Layer-7 Forwarding Rules Reference

This document describes how to configure forwarding rules for GA HTTP/HTTPS listeners. Rules can match by domain, path, HTTP header, cookie, query string, method, or source IP.

> **Important**: Forwarding rules apply only to **HTTP/HTTPS listeners**. Basic accelerators do not support forwarding rules.

---

## 1. Core Concepts

- **RuleConditions**: Match conditions; support `Host`, `Path`, `RequestHeader`, `Query`, `Method`, `Cookie`, `SourceIP`.
- **RuleActions**: Actions executed on match; support `ForwardGroup`, `Redirect`, `FixResponse`, `Rewrite`, `AddHeader`, `RemoveHeader`, `Drop`.
- **Priority**: Rule priority from 1 to 10000; lower values are evaluated first.
- **Order**: Action order; `Rewrite`/`AddHeader`/`RemoveHeader` must precede `ForwardGroup`.

> **AI-mode CLI syntax**: pass `--forwarding-rules` as a JSON array string. `RuleConditionValue` and `RuleActionValue` are JSON strings themselves, so inner quotes must be escaped with `\"`.

---

## 2. Forward by Domain and Path

```bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"

aliyun ga create-forwarding-rules \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --forwarding-rules '[{"Priority":1,"RuleConditions":[{"RuleConditionType":"Host","RuleConditionValue":"[\"api.example.com\"]"},{"RuleConditionType":"Path","RuleConditionValue":"[\"/v1/*\"]"}],"RuleActions":[{"Order":1,"RuleActionType":"ForwardGroup","RuleActionValue":"{\"type\":\"endpointgroup\",\"value\":\"epg-bp1api1234\"}"}]}]' \
  --user-agent "$GA_USER_AGENT"
```

---

## 3. Return a Fixed Response

```bash
aliyun ga create-forwarding-rules \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --forwarding-rules '[{"Priority":10,"RuleConditions":[{"RuleConditionType":"Path","RuleConditionValue":"[\"/healthz\"]"}],"RuleActions":[{"Order":1,"RuleActionType":"FixResponse","RuleActionValue":"{\"code\":\"200\",\"type\":\"text/plain\",\"content\":\"ok\"}"}]}]' \
  --user-agent "$GA_USER_AGENT"
```

---

## 4. Redirect HTTP to HTTPS

```bash
aliyun ga create-forwarding-rules \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --forwarding-rules '[{"Priority":5,"RuleConditions":[{"RuleConditionType":"Host","RuleConditionValue":"[\"www.example.com\"]"}],"RuleActions":[{"Order":1,"RuleActionType":"Redirect","RuleActionValue":"{\"protocol\":\"HTTPS\",\"port\":\"443\",\"code\":\"301\"}"}]}]' \
  --user-agent "$GA_USER_AGENT"
```

---

## 5. Add Custom HTTP Headers

```bash
aliyun ga create-forwarding-rules \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --forwarding-rules '[{"Priority":3,"RuleConditions":[{"RuleConditionType":"Host","RuleConditionValue":"[\"app.example.com\"]"}],"RuleActions":[{"Order":1,"RuleActionType":"AddHeader","RuleActionValue":"[{\"name\":\"X-Forwarded-By\",\"type\":\"system-defined\",\"value\":\"ClientSrcIp\"}]"},{"Order":2,"RuleActionType":"ForwardGroup","RuleActionValue":"{\"type\":\"endpointgroup\",\"value\":\"epg-bp1app5678\"}"}]}]' \
  --user-agent "$GA_USER_AGENT"
```

---

## 6. Query Forwarding Rules

### Single rule

```bash
aliyun ga get-forwarding-rule \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    ForwardingRuleId,
    Priority,
    RuleConditions,
    RuleActions,
    ForwardingRuleStatus
  }'
```

### All rules under a listener

```bash
aliyun ga list-forwarding-rules \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --user-agent "$GA_USER_AGENT" | jq '.ForwardingRules[] | {
    ForwardingRuleId,
    Priority,
    ForwardingRuleStatus,
    RuleConditionCount: (.RuleConditions | length),
    RuleActionCount: (.RuleActions | length)
  }'
```

---

## 7. Update Forwarding Rule

```bash
aliyun ga update-forwarding-rule-attribute \
  --biz-region-id cn-hangzhou \
  --forwarding-rule-id "fr-bp1xxxx" \
  --user-agent "$GA_USER_AGENT" \
  --priority 2
```

---

## 8. Batch Creation Example

```bash
#!/bin/bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"
REGION="cn-hangzhou"

echo "=== Creating forwarding rules ==="

# Rule 1: API domain -> API endpoint group
aliyun ga create-forwarding-rules \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --forwarding-rules '[{"Priority":1,"RuleConditions":[{"RuleConditionType":"Host","RuleConditionValue":"[\"api.example.com\"]"}],"RuleActions":[{"Order":1,"RuleActionType":"ForwardGroup","RuleActionValue":"{\"type\":\"endpointgroup\",\"value\":\"epg-bp1api1234\"}"}]}]' \
  --user-agent "$GA_USER_AGENT"

# Rule 2: static assets by domain + path -> static endpoint group
aliyun ga create-forwarding-rules \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --forwarding-rules '[{"Priority":2,"RuleConditions":[{"RuleConditionType":"Host","RuleConditionValue":"[\"www.example.com\"]"},{"RuleConditionType":"Path","RuleConditionValue":"[\"/static/*\"]"}],"RuleActions":[{"Order":1,"RuleActionType":"ForwardGroup","RuleActionValue":"{\"type\":\"endpointgroup\",\"value\":\"epg-bp1static5678\"}"}]}]' \
  --user-agent "$GA_USER_AGENT"

# Rule 3: health check fallback -> fixed response
aliyun ga create-forwarding-rules \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --forwarding-rules '[{"Priority":100,"RuleConditions":[{"RuleConditionType":"Path","RuleConditionValue":"[\"/healthz\"]"}],"RuleActions":[{"Order":1,"RuleActionType":"FixResponse","RuleActionValue":"{\"code\":\"200\",\"type\":\"text/plain\",\"content\":\"ok\"}"}]}]' \
  --user-agent "$GA_USER_AGENT"

echo "=== Forwarding rules created ==="
```

---

## 9. Priority Recommendations

| Priority Range | Use Case |
|---|---|
| 1–10 | Exact matches (e.g., API, admin consoles) |
| 11–100 | Business traffic splitting (by domain/path) |
| 101–1000 | General fallback (default forward, health checks) |
| 10000 | Final default rule |

---

## 10. Skill Integration Notes

After Step 4 (create listener), optionally ask:

```
Question: Do you want to configure layer-7 forwarding rules for this HTTP/HTTPS listener?
- Option 1: No (default)
- Option 2: Yes, forward by domain
- Option 3: Yes, forward by path
- Option 4: Yes, custom rules

If yes:
1. Ask for the existing endpoint group ID.
2. Ask for domain/path/action type.
3. Call create-forwarding-rules in batch.
```

---

## 11. Notes

1. Forwarding rules are supported only on HTTP/HTTPS listeners.
2. `AddHeader`/`RemoveHeader`/`Rewrite` actions must be ordered before `ForwardGroup`.
3. When multiple rules match, the rule with the lowest `Priority` value wins.
4. ForwardGroup targets are subject to API constraints; verify the endpoint group type in the official documentation.
5. `create-forwarding-rules` does not support concurrent creation within the same accelerator.
