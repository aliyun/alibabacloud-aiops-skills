# Postpay Bandwidth and Spec Adjustment Reference

This document describes how to adjust bandwidth and specifications for pay-as-you-go (POSTPAY) Global Accelerator instances.

> **Important**: In POSTPAY mode, bandwidth is usually billed through CDT (Cloud Data Transfer). You do not need to purchase a fixed bandwidth package in advance.

---

## 1. POSTPAY vs PREPAY Bandwidth Differences

| Attribute | POSTPAY (CDT) | PREPAY |
|---|---|---|
| Bandwidth ceiling | Configured on IpSet/EndpointGroup | Limited by bandwidth package |
| Billing | Pay for actual traffic | Pay for fixed bandwidth package |
| Adjustment | Modify IpSet `Bandwidth` field | Upgrade/downgrade bandwidth package |
| Effective time | Usually immediate | May require purchasing a new package |

---

## 2. Update Standard Accelerator Region Bandwidth

```bash
IP_SET_ID="ips-bp1xxxx"
NEW_BANDWIDTH=100

aliyun ga update-ip-set \
  --biz-region-id cn-hangzhou \
  --ip-set-id "$IP_SET_ID" \
  --user-agent "$GA_USER_AGENT" \
  --bandwidth "$NEW_BANDWIDTH"
```

---

## 3. Update Basic Accelerator Region Bandwidth

```bash
IP_SET_ID="ips-bp1xxxx"
NEW_BANDWIDTH=50

aliyun ga update-basic-ip-set \
  --biz-region-id cn-hangzhou \
  --ip-set-id "$IP_SET_ID" \
  --user-agent "$GA_USER_AGENT" \
  --bandwidth "$NEW_BANDWIDTH"
```

---

## 4. Batch Update All Acceleration Region Bandwidth

```bash
#!/bin/bash
GA_ID="${1:?Please provide GA accelerator ID}"
NEW_BANDWIDTH="${2:?Please provide new bandwidth in Mbps}"
REGION="cn-hangzhou"

echo "=== Updating all acceleration region bandwidth for $GA_ID to $NEW_BANDWIDTH Mbps ==="

# Standard accelerator
IPSET_IDS=$(aliyun ga list-ip-sets \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" | jq -r '.IpSets[].IpSetId // empty' )
for IPSET_ID in $IPSET_IDS; do
aliyun ga update-ip-set \
  --biz-region-id "$REGION" \
  --ip-set-id "$IPSET_ID" \
  --bandwidth "$NEW_BANDWIDTH" \
  --user-agent "$GA_USER_AGENT"
  echo "Updated: $IPSET_ID"
done

# Basic accelerator fallback
BASIC_IPSET_ID=$(aliyun ga get-basic-accelerator \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" 2>/dev/null --user-agent "$GA_USER_AGENT" | jq -r '.BasicIpSetId // empty' )
if [ -n "$BASIC_IPSET_ID" ]; then
aliyun ga update-basic-ip-set \
  --biz-region-id "$REGION" \
  --ip-set-id "$BASIC_IPSET_ID" \
  --bandwidth "$NEW_BANDWIDTH" \
  --user-agent "$GA_USER_AGENT"
  echo "Updated basic acceleration region: $BASIC_IPSET_ID"
fi
```

---

## 5. Upgrade Standard Accelerator Specification

```bash
GA_ID="ga-bp1xxxx"

aliyun ga update-accelerator \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" \
  --spec "large"
```

### Common Specifications

| Spec | Use Case |
|---|---|
| small | Small applications, low concurrency |
| medium | Medium-sized applications |
| large | Large applications, high concurrency |
| xlarge | Very large scale applications |

---

## 6. Update Basic Accelerator Attributes

```bash
GA_ID="ga-bp1xxxx"

aliyun ga update-basic-accelerator \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" \
  --name "ga-basic-upgraded"
```

---

## 7. CDT Bandwidth Package Association (POSTPAY)

To set a bandwidth ceiling in POSTPAY mode, configure a CDT bandwidth package:

```bash
# List existing bandwidth packages
aliyun ga list-bandwidth-packages \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '.BandwidthPackages[] | {BandwidthPackageId, Name, Bandwidth, State}'

# Bind a bandwidth package (PREPAY scenario)
aliyun ga bind-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --bandwidth-package-id "cbwp-bp1xxxx" \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "$GA_ID"
```

---

## 8. Upgrade/Downgrade Workflow

### Upgrade Scenario

1. Monitoring shows traffic approaching the bandwidth ceiling.
2. Call `update-ip-set` to increase region bandwidth.
3. If higher concurrency is needed, call `update-accelerator` to upgrade the spec.
4. Verify with `describe-accelerator` and `list-ip-sets`.

### Downgrade Scenario

1. Monitoring shows long-term bandwidth utilization below 20%.
2. Call `update-ip-set` to reduce bandwidth during off-peak hours.
3. Confirm no business impact before keeping the new configuration.

---

## 9. Skill Integration Notes

In the management section, ask:

```
Question: What bandwidth operation do you want to perform?
- Option 1: View current bandwidth configuration
- Option 2: Upgrade acceleration region bandwidth
- Option 3: Downgrade acceleration region bandwidth
- Option 4: Upgrade accelerator specification

Based on the choice:
1. Call list-ip-sets / get-basic-ip-set to query current bandwidth.
2. Ask for the target bandwidth value.
3. Call update-ip-set / update-basic-ip-set / update-accelerator.
4. Call describe-accelerator to verify.
```

---

## 10. Notes

1. POSTPAY + CDT mode does not use a fixed bandwidth package; bandwidth adjustments mainly modify the `Bandwidth` field of acceleration regions.
2. `update-accelerator` may briefly change the instance state to `configuring`.
3. Cross-border bandwidth adjustments may be restricted by compliance approval.
4. Minimum bandwidth granularity varies by region, commonly 1 Mbps.
5. Changes usually take effect immediately, but monitoring data may lag.
