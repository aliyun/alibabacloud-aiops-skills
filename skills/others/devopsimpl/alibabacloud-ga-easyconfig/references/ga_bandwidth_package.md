# GA Bandwidth Package API Reference (Step 2)

This document provides complete CLI scripts for creating, binding, querying, and modifying Global Accelerator bandwidth packages.

> **Note**: In POSTPAY mode you do not need to create a bandwidth package separately; bandwidth is specified directly when creating acceleration regions (`create-ip-sets`). This document mainly serves PREPAY scenarios.
>
> **Cost gate**: `create-bandwidth-package --charge-type PREPAY` generates a prepaid order. Before running it, present bandwidth, billing type, duration, and auto-renew to the user and obtain an explicit second confirmation; if the user does not confirm, offer the POSTPAY + CDT alternative instead.

---

## 1. create-bandwidth-package

Create a bandwidth package.

### Create a basic bandwidth package (PREPAY)

```bash
aliyun ga create-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --type Basic \
  --bandwidth 10 \
  --bandwidth-type Basic \
  --charge-type PREPAY \
  --duration 1 \
  --pricing-cycle Month \
  --auto-pay true \
  --auto-renew true \
  --user-agent "$GA_USER_AGENT" \
  --auto-renew-duration 1
```

### Create an enhanced bandwidth package

```bash
aliyun ga create-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --type Basic \
  --bandwidth 50 \
  --bandwidth-type Enhanced \
  --charge-type PREPAY \
  --duration 1 \
  --pricing-cycle Month \
  --user-agent "$GA_USER_AGENT" \
  --auto-pay true
```

### Create a premium acceleration bandwidth package

```bash
aliyun ga create-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --type Basic \
  --bandwidth 10 \
  --bandwidth-type Advanced \
  --charge-type PREPAY \
  --duration 1 \
  --pricing-cycle Month \
  --user-agent "$GA_USER_AGENT" \
  --auto-pay true
```

### Cross-domain acceleration bandwidth package (manual operations only)

> **Manual-only**: `--type CrossDomain` requires cross-border compliance approval. This skill must NOT run `create-bandwidth-package --type CrossDomain` (nor bind such a package with `bandwidth-package-add-accelerator`) under any circumstances. Instead, output a manual console operation guide for the user — submit the cross-border compliance application, wait for approval (1-5 business days), purchase the package in the GA console, then bind it to the instance. The parameters in the table below remain valid as console-input reference.

### Create a POSTPAY bandwidth package (pay-by-traffic)

```bash
aliyun ga create-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --type Basic \
  --bandwidth 100 \
  --bandwidth-type Basic \
  --charge-type POSTPAY \
  --user-agent "$GA_USER_AGENT" \
  --billing-type PayByTraffic
```

### Parameter reference

| Parameter | Type | Required | Description | Allowed values |
|-----------|------|----------|-------------|----------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` | `cn-hangzhou` |
| Type | string | Yes | Bandwidth package type | `Basic` / `CrossDomain` |
| Bandwidth | integer | Yes | Bandwidth value (Mbps) | `2` ~ `2000` |
| BandwidthType | string | No | Bandwidth type (required when Type=Basic) | `Basic` / `Enhanced` / `Advanced` |
| ChargeType | string | No | Billing type | `PREPAY` / `POSTPAY` |
| Duration | string | No | Purchase duration (required for PREPAY) | Month: 1~9, Year: 1~3 |
| PricingCycle | string | No | Billing cycle (required for PREPAY) | `Month` / `Year` |
| BillingType | string | No | POSTPAY billing method | `PayByTraffic` / `PayBY95` |
| Ratio | integer | No | 95th-percentile floor ratio | `30`~`100`, only for `PayBY95` |
| AutoPay | boolean | No | Auto payment | `true` / `false` |
| AutoRenew | boolean | No | Auto renewal | `true` / `false` |
| AutoRenewDuration | integer | No | Auto renewal duration (months) | `1`~`12` |
| ResourceGroupId | string | No | Resource group ID | - |

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| RequestId | string | Request ID |
| BandwidthPackageId | string | Bandwidth package ID |
| OrderId | string | Order ID (returned for PREPAY only) |

### Sample response

```json
{
  "RequestId": "4B6DBBB0-2D01-5B6D-xxxx",
  "BandwidthPackageId": "gbwp-bp1sgzldyj6l4l3****",
  "OrderId": "2082578xxxx"
}
```

---

## 2. bandwidth-package-add-accelerator

Bind a bandwidth package to a GA instance.

```bash
aliyun ga bandwidth-package-add-accelerator \
  --biz-region-id cn-hangzhou \
  --bandwidth-package-id "${BWP_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

### Parameter reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| BandwidthPackageId | string | Yes | Bandwidth package ID |
| AcceleratorId | string | Yes | GA instance ID |

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| RequestId | string | Request ID |
| BandwidthPackageId | string | Bound bandwidth package ID |
| Accelerators | array | List of bound GA instance IDs |

### Error handling

| Error code | Meaning | Resolution |
|------------|---------|------------|
| StateError.Accelerator | GA instance state does not allow binding | Retry after the instance becomes `active` |
| StateError.BandwidthPackage | Bandwidth package state does not allow binding | Retry after the package is ready |
| NotExist.BandwidthPackage | Bandwidth package does not exist | Check BandwidthPackageId |
| BandwidthPackageCannotBind | Bandwidth package cannot be bound | Check whether the package type matches the instance type |

---

## 3. bandwidth-package-remove-accelerator

Unbind a bandwidth package.

> **Important**: Before unbinding a bandwidth package, delete all acceleration regions (IpSets) under the instance.

```bash
aliyun ga bandwidth-package-remove-accelerator \
  --biz-region-id cn-hangzhou \
  --bandwidth-package-id "${BWP_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

---

## 4. describe-bandwidth-package

Query bandwidth package details.

```bash
aliyun ga describe-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --bandwidth-package-id "${BWP_ID}"
```

### Extract key fields

```bash
aliyun ga describe-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    BandwidthPackageId,
    Name,
    State,
    Type,
    Bandwidth,
    BandwidthType,
    ChargeType,
    Accelerators
  }'
```

---

## 5. list-bandwidth-packages

Query the bandwidth package list.

### List all bandwidth packages

```bash
aliyun ga list-bandwidth-packages \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --page-size 50
```

### Filter by state

```bash
aliyun ga list-bandwidth-packages \
  --biz-region-id cn-hangzhou \
  --state active \
  --user-agent "$GA_USER_AGENT" \
  --page-size 50
```

### Format output

```bash
aliyun ga list-bandwidth-packages \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '.BandwidthPackages[] | {
    BandwidthPackageId,
    Name,
    State,
    Type,
    Bandwidth,
    BandwidthType,
    ChargeType
  }'
```

---

## 6. update-bandwidth-package

Modify a bandwidth package.

### Change bandwidth value

```bash
aliyun ga update-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --bandwidth-package-id "${BWP_ID}" \
  --bandwidth 50 \
  --user-agent "$GA_USER_AGENT" \
  --auto-pay true
```

### Change name

```bash
aliyun ga update-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --bandwidth-package-id "${BWP_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --name "${NEW_NAME}"
```

---

## 7. replace-bandwidth-package

Replace the bandwidth package bound to a GA instance.

```bash
aliyun ga replace-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --bandwidth-package-id "${NEW_BWP_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

---

## Complete example: create and bind a basic bandwidth package

```bash
#!/bin/bash
GA_ID="ga-bp1xxxx"

# Step 1: Create a basic bandwidth package
echo "Creating basic bandwidth package..."
BWP_RESULT=$(aliyun ga create-bandwidth-package \
  --user-agent "$GA_USER_AGENT" \
  --biz-region-id cn-hangzhou \
  --type Basic \
  --bandwidth 10 \
  --bandwidth-type Basic \
  --charge-type PREPAY \
  --duration 1 \
  --pricing-cycle Month \
  --auto-pay true)

BWP_ID=$(echo "$BWP_RESULT" | jq -r '.BandwidthPackageId')
echo "Bandwidth package created: $BWP_ID"

# Step 2: Wait for the bandwidth package to become active
echo "Waiting for bandwidth package to become active..."
for i in $(seq 1 20); do
STATE=$(aliyun ga describe-bandwidth-package \
  --biz-region-id cn-hangzhou \
  --bandwidth-package-id "$BWP_ID" \
  --user-agent "$GA_USER_AGENT" | jq -r '.State')

  if [ "$STATE" = "active" ]; then
    echo "Bandwidth package is active."
    break
  fi
  echo "Waiting... [$i/20] state: $STATE"
  sleep 10
done

# Step 3: Bind the bandwidth package to the GA instance
echo "Binding bandwidth package to GA instance..."
aliyun ga bandwidth-package-add-accelerator \
  --biz-region-id cn-hangzhou \
  --bandwidth-package-id "$BWP_ID" \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "$GA_ID"

echo "Binding complete. Bandwidth package: $BWP_ID -> GA instance: $GA_ID"
```
