# GA Accelerator Management API Reference (Step 1)

This document provides complete CLI scripts for creating, querying, and modifying Global Accelerator instances.

> **Important**: All GA APIs use `--biz-region-id cn-hangzhou`, which is the GA control plane region and is independent of the actual acceleration region.

---

## 1. create-accelerator

Create a GA accelerator.

### POSTPAY instance

POSTPAY creates no order — it is billed by traffic through CDT, so `--auto-pay` is unnecessary and `--spec` is rejected (see the error table below).

```bash
aliyun ga create-accelerator \
  --biz-region-id cn-hangzhou \
  --name "${GA_NAME}" \
  --instance-charge-type POSTPAY \
  --bandwidth-billing-type CDT \
  --ip-set-config AccessMode=UserDefine \
  --user-agent "$GA_USER_AGENT"
```

### PREPAY instance

**Cost gate**: this generates a prepaid order — confirm spec, pricing cycle, duration, and estimated cost with the user before executing.

```bash
aliyun ga create-accelerator \
  --biz-region-id cn-hangzhou \
  --name "${GA_NAME}" \
  --instance-charge-type PREPAY \
  --spec 1 \
  --duration 1 \
  --pricing-cycle Month \
  --bandwidth-billing-type BandwidthPackage \
  --auto-pay true \
  --auto-renew true \
  --user-agent "$GA_USER_AGENT" \
  --auto-renew-duration 1 \
  --ip-set-config AccessMode=UserDefine
```

### Anycast mode (Anycast EIP)

```bash
aliyun ga create-accelerator \
  --biz-region-id cn-hangzhou \
  --name "${GA_NAME}" \
  --instance-charge-type POSTPAY \
  --bandwidth-billing-type CDT \
  --bandwidth 200 \
  --ip-set-config AccessMode=Anycast \
  --user-agent "$GA_USER_AGENT"
```

### Quota pre-check (run before create)

```bash
aliyun ga list-accelerators --biz-region-id cn-hangzhou --page-size 50 \
  --user-agent "$GA_USER_AGENT" \
| jq --arg name "${GA_NAME}" '{TotalCount, SameName: [.Accelerators[]? | select(.Name == $name) | {AcceleratorId, State, InstanceChargeType}]}'
```

GA instance count is capped by an account-level quota (commonly 10; confirm the current value in Quota Center). When `TotalCount` is at or near the limit, creating another instance fails with `QuotaExceeded.Accelerator` — report this to the user before doing any further work. Instance names are not unique, so a non-empty `SameName` list is normal: report those instances and ask whether to reuse one or create another.

### Parameter reference

| Parameter | Type | Required | Description | Allowed values |
|-----------|------|----------|-------------|----------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` | `cn-hangzhou` |
| Name | string | No | Instance name | 1~128 characters |
| InstanceChargeType | string | No | Billing type | `PREPAY` / `POSTPAY` |
| Spec | string | No | Instance specification (required for PREPAY) | `1` ~ `200` |
| Duration | integer | No | Purchase duration (required for PREPAY) | Month: 1~9, Year: 1~3 |
| PricingCycle | string | No | Billing cycle (required for PREPAY) | `Month` / `Year` |
| BandwidthBillingType | string | No | Bandwidth billing type | `BandwidthPackage` / `CDT` |
| IpSetConfig.AccessMode | string | No | Acceleration IP access mode | `UserDefine` / `Anycast` |
| Bandwidth | integer | No | Instance bandwidth (Mbps, required for Anycast) | 200~5000 |
| AutoPay | boolean | No | Auto payment | `true` / `false` |
| AutoRenew | boolean | No | Auto renewal | `true` / `false` |
| AutoRenewDuration | integer | No | Auto renewal duration (months) | 1~12 |
| ResourceGroupId | string | No | Resource group ID | - |
| DryRun | boolean | No | Dry run | `true` / `false` |

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| RequestId | string | Request ID |
| AcceleratorId | string | GA instance ID |
| OrderId | string | Order ID (returned for PREPAY only) |

### Sample response

```json
{
  "RequestId": "F5B2A4E4-2D72-5B38-xxxx",
  "AcceleratorId": "ga-bp1odcab8tmno0hdq****",
  "OrderId": "2082574xxxx"
}
```

### Error handling

| Error code | Meaning | Resolution |
|------------|---------|------------|
| IllegalParameter.Spec | Invalid specification | Check whether Spec is in the allowed range |
| AccountNotOpenGaService | GA service not activated | Call `open-accelerator-service` first |
| NotExist.ResourceGroup | Resource group does not exist | Check ResourceGroupId |
| NotSupportSpecification.PostPayAccelerator / InvalidateBandwidthBillingType.PostPayAccelerator | `--spec` or a non-CDT billing type was passed for a POSTPAY instance | Drop `--spec` and use `--bandwidth-billing-type CDT`; spec is PREPAY-only |
| QuotaExceeded.Accelerator | Account GA instance quota is exhausted | Do NOT delete anything on your own. List all instances, identify empty/leftover ones, then present numbered options (release one specific ID after explicit confirmation, raise the quota in Quota Center, or reuse an existing instance) and stop — follow the Blocked-State Protocol in `SKILL.md` |

---

## 2. describe-accelerator

Query GA instance details.

### Basic call

```bash
aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

### Extract key fields with jq

```bash
aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    AcceleratorId,
    Name,
    State,
    Spec,
    InstanceChargeType,
    BandwidthBillingType,
    DnsName,
    AccessMode: .IpSetConfig.AccessMode,
    BasicBandwidthPackage,
    CrossDomainBandwidthPackage
  }'
```

### Poll until the instance is active

```bash
GA_ID="ga-bp1xxxx"
MAX_WAIT=30
for i in $(seq 1 $MAX_WAIT); do
RESULT=$(aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" )
  STATE=$(echo "$RESULT" | jq -r '.State')

  if [ "$STATE" = "active" ]; then
    echo "GA instance is ready."
    echo "$RESULT" | jq '{AcceleratorId, Name, State, DnsName}'
    break
  fi

  echo "Waiting for GA instance to become active... [$i/$MAX_WAIT] current state: $STATE"
  sleep 20
done

if [ "$STATE" != "active" ]; then
  echo "Timeout: GA instance did not become active, current state: $STATE"
fi
```

### Parameter reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| AcceleratorId | string | Yes | GA instance ID |

### Key response fields

| Field | Type | Description |
|-------|------|-------------|
| AcceleratorId | string | Instance ID |
| Name | string | Instance name |
| State | string | State: `init`/`active`/`configuring`/`binding`/`unbinding`/`deleting`/`inactive`/`creating` |
| Spec | string | Instance specification |
| DnsName | string | CNAME address |
| InstanceChargeType | string | Billing type |
| BandwidthBillingType | string | Bandwidth billing type |
| IpSetConfig.AccessMode | string | Acceleration IP access mode |
| BasicBandwidthPackage | object | Basic bandwidth package info |
| CrossDomainBandwidthPackage | object | Cross-domain bandwidth package info |
| CreateTime | integer | Creation timestamp |
| ExpiredTime | integer | Expiration timestamp |
| CrossBorderStatus | boolean | Whether cross-border line is enabled |

---

## 3. list-accelerators

Query the GA instance list.

### List all active instances

```bash
aliyun ga list-accelerators \
  --biz-region-id cn-hangzhou \
  --state active \
  --user-agent "$GA_USER_AGENT" \
  --page-size 50
```

### Format output

```bash
aliyun ga list-accelerators \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '.Accelerators[] | {
    AcceleratorId,
    Name,
    State,
    Spec,
    InstanceChargeType,
    BandwidthBillingType,
    AccessMode: .IpSetConfig.AccessMode
  }'
```

### Paginated query

```bash
PAGE=1
PAGE_SIZE=10
MAX_PAGES=50

while true; do
RESULT=$(aliyun ga list-accelerators \
  --biz-region-id cn-hangzhou \
  --page-number "$PAGE" \
  --page-size "$PAGE_SIZE" \
  --user-agent "$GA_USER_AGENT")

  TOTAL=$(echo "$RESULT" | jq -r '.TotalCount')
  echo "$RESULT" | jq '.Accelerators[] | {AcceleratorId, Name, State}'

  if [ $((PAGE * PAGE_SIZE)) -ge $TOTAL ]; then
    break
  fi
  if [ "$PAGE" -ge "$MAX_PAGES" ]; then
    echo "WARN: stopped at MAX_PAGES=$MAX_PAGES before reaching TotalCount=$TOTAL" >&2
    break
  fi
  PAGE=$((PAGE + 1))
done
```

### Parameter reference

| Parameter | Type | Required | Description | Allowed values |
|-----------|------|----------|-------------|----------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` | - |
| PageNumber | integer | No | Page number | Default `1` |
| PageSize | integer | No | Page size | Max `50`, default `10` |
| AcceleratorId | string | No | Filter by instance ID | - |
| State | string | No | Filter by state | `init`/`active`/`configuring`/`binding`/`unbinding`/`deleting`/`inactive`/`creating` |
| ResourceGroupId | string | No | Filter by resource group | - |

---

## 4. update-accelerator

Modify a GA instance.

### Change instance name

```bash
aliyun ga update-accelerator \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --name "${NEW_NAME}"
```

### Change instance specification (PREPAY)

```bash
aliyun ga update-accelerator \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --spec 2 \
  --user-agent "$GA_USER_AGENT" \
  --auto-pay true
```

### Parameter reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| AcceleratorId | string | Yes | GA instance ID |
| Name | string | No | New name |
| Spec | string | No | New specification |
| AutoPay | boolean | No | Auto payment |
| Description | string | No | Description |

---

## 5. update-accelerator-confirm

Confirm a specification change.

After modifying the instance specification, call this interface to confirm:

```bash
aliyun ga update-accelerator-confirm \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

---

## 6. open-accelerator-service

Activate the GA POSTPAY service.

```bash
aliyun ga open-accelerator-service \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT"
```

## 7. describe-accelerator-service-status

Query the GA service activation status.

```bash
aliyun ga describe-accelerator-service-status \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT"
```
