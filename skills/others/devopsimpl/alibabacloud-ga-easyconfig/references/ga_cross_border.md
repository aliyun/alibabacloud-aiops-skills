# Cross-Border Compliance Reference

This document describes how to detect, enable, and query cross-border compliance status for Global Accelerator configurations involving mainland China and overseas regions.

> **Important**: Cross-border acceleration requires Alibaba Cloud cross-border compliance approval.

---

## 1. Cross-Border Scenarios

- Acceleration region is in mainland China (e.g., Beijing, Shanghai, Hangzhou) and endpoints are overseas (e.g., Hong Kong, Singapore, US).
- Acceleration region is overseas and endpoints are in mainland China.
- Any GA configuration with traffic between mainland China and overseas.

---

## 2. Detect Cross-Border Requirement

```bash
ACCELERATE_REGION="cn-hangzhou"
ENDPOINT_GROUP_REGION="cn-hongkong"

MAINLAND_REGIONS=("cn-qingdao" "cn-beijing" "cn-zhangjiakou" "cn-huhehaote" "cn-wulanchabu" "cn-hangzhou" "cn-shanghai" "cn-shenzhen" "cn-heyuan" "cn-guangzhou" "cn-chengdu" "cn-nanjing" "cn-fuzhou" "cn-wuhan" "cn-zhoushan")

is_mainland() {
  local region="$1"
  for r in "${MAINLAND_REGIONS[@]}"; do
    [ "$r" = "$region" ] && return 0
  done
  return 1
}

if (is_mainland "$ACCELERATE_REGION" && ! is_mainland "$ENDPOINT_GROUP_REGION") || \
   (! is_mainland "$ACCELERATE_REGION" && is_mainland "$ENDPOINT_GROUP_REGION"); then
  echo "⚠️ Cross-border configuration detected; cross-border capability must be enabled."
  CROSS_BORDER=true
else
  echo "✅ No cross-border configuration detected."
  CROSS_BORDER=false
fi
```

---

## 3. Query Accelerator Cross-Border Status

```bash
GA_ID="ga-bp1xxxx"

aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    AcceleratorId,
    CrossBorderStatus,
    CrossBorderMode
  }'
```

### Response Fields

| Field | Description |
|---|---|
| CrossBorderStatus | `true` if enabled, `false` otherwise |
| CrossBorderMode | Cross-border mode, e.g., `bgp`, `crossborder` |

---

## 4. Enable Cross-Border

> Enablement requires real-name verification and cross-border compliance approval.

```bash
aliyun ga update-accelerator-cross-border-status \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" \
  --cross-border-status true
```

---

## 5. Query Approval Status

```bash
aliyun ga query-cross-border-approval-status \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    ApprovalStatus,
    ApprovalMessage,
    CrossBorderStatus
  }'
```

### Approval Status Values

| Status | Meaning |
|---|---|
| approved | Approved |
| approving | Under review |
| rejected | Rejected |
| not_submitted | Not submitted |

---

## 6. Disable Cross-Border

```bash
aliyun ga update-accelerator-cross-border-status \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" \
  --cross-border-status false
```

---

## 7. Full Detection Script

```bash
#!/bin/bash
GA_ID="${1:?Please provide GA accelerator ID}"
REGION="cn-hangzhou"

MAINLAND_REGIONS=("cn-qingdao" "cn-beijing" "cn-zhangjiakou" "cn-huhehaote" "cn-wulanchabu" "cn-hangzhou" "cn-shanghai" "cn-shenzhen" "cn-heyuan" "cn-guangzhou" "cn-chengdu" "cn-nanjing" "cn-fuzhou" "cn-wuhan" "cn-zhoushan")

is_mainland() {
  local region="$1"
  for r in "${MAINLAND_REGIONS[@]}"; do
    [ "$r" = "$region" ] && return 0
  done
  return 1
}

echo "=== Cross-border compliance check: $GA_ID ==="

GA_INFO=$(aliyun ga describe-accelerator \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT")
CROSS_BORDER_STATUS=$(echo "$GA_INFO" | jq -r '.CrossBorderStatus // "false"')

IP_SETS=$(aliyun ga list-ip-sets \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT")
ACC_REGIONS=$(echo "$IP_SETS" | jq -r '.IpSets[].AccelerateRegionId')

EPG_REGIONS=$(aliyun ga list-endpoint-groups \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" | jq -r '.EndpointGroups[].EndpointGroupRegion' | sort -u)

echo "Acceleration regions:"
echo "$ACC_REGIONS"
echo ""
echo "Endpoint group regions:"
echo "$EPG_REGIONS"

NEEDS_CROSS_BORDER=false
for AR in $ACC_REGIONS; do
  for ER in $EPG_REGIONS; do
    if (is_mainland "$AR" && ! is_mainland "$ER") || (! is_mainland "$AR" && is_mainland "$ER"); then
      NEEDS_CROSS_BORDER=true
      echo "⚠️ Cross-border configuration detected: $AR <-> $ER"
    fi
  done
done

if [ "$NEEDS_CROSS_BORDER" = true ]; then
  echo ""
  echo "Current cross-border status: $CROSS_BORDER_STATUS"
  if [ "$CROSS_BORDER_STATUS" != "true" ]; then
    echo "❌ Cross-border capability must be enabled."
    echo "Complete cross-border compliance approval first, then run:"
    echo "  aliyun ga update-accelerator-cross-border-status --biz-region-id "$REGION" --accelerator-id "$GA_ID" --cross-border-status true --user-agent \"$GA_USER_AGENT\""
  else
    echo "✅ Cross-border is already enabled."
  fi
else
  echo "✅ No cross-border configuration detected."
fi
```

---

## 8. Skill Integration Notes

After Step 3 (acceleration region) and Step 5 (endpoint group region) are complete, automatically:

1. Detect whether mainland China and overseas regions are involved.
2. If yes, run the read-only checks: `describe-accelerator` (read `CrossBorderStatus`) and `query-cross-border-approval-status` (read `ApprovalStatus`).
3. **CrossDomain bandwidth package purchase/binding is NEVER automated** — regardless of approval status. Output a manual operation guide for the user and stop:

   | ApprovalStatus | Manual guide content |
   |---|---|
   | `not_submitted` | How to submit the cross-border compliance application in the GA console (real-name verification required; approval takes 1-5 business days), then how to purchase and bind the CrossDomain bandwidth package in the console after approval |
   | `approving` | The application is under review; wait for the result, then purchase and bind in the console after approval |
   | `rejected` | Show `ApprovalMessage`, help correct the application materials, and resubmit in the console |
   | `approved` | Guide the user to purchase the CrossDomain bandwidth package in the console and bind it to the GA instance |

4. The guide must state explicitly that these steps are completed by the user in the console. The assistant does not run `create-bandwidth-package --type CrossDomain` or `bandwidth-package-add-accelerator` for a CrossDomain package, even when the user asks to proceed.
5. For the non-cross-border parts (instance, Basic bandwidth package, acceleration regions, listeners, endpoint groups), continue the normal automated workflow.

---

## 9. Notes

1. Compliance approval is mandatory for cross-border traffic.
2. Approval may take 1–5 business days; plan ahead.
3. Basic accelerators are also subject to cross-border compliance.
4. The mainland China region list may expand; refer to the console or official documentation for the latest list.
