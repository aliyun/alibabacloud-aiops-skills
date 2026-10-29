# GA Acceleration Region API Reference (Step 3)

This document provides complete CLI scripts for querying, creating, and modifying Global Accelerator acceleration regions (IpSets).

> **Acceleration regions** determine where users access the GA network. After creation, acceleration IPs are allocated in the corresponding regions.

---

## 1. list-accelerate-areas

Query all available acceleration areas and regions.

```bash
aliyun ga list-accelerate-areas \
  --user-agent "$GA_USER_AGENT" \
  --biz-region-id cn-hangzhou
```

### Format output

```bash
aliyun ga list-accelerate-areas \
  --user-agent "$GA_USER_AGENT" | jq '.Areas[] | {
    AreaId,
    LocalName,
    Regions: [.RegionList[] | {RegionId, LocalName}]
  }'
```

### Key response fields

| Field | Description | Example |
|-------|-------------|---------|
| AreaId | Acceleration area ID | `china-mainland`, `asia-pacific`, `europe`, `north-america` |
| LocalName | Area display name | Mainland China, Asia Pacific, Europe, North America |
| RegionList[].RegionId | Region ID | `cn-beijing`, `cn-shanghai`, `us-west-1` |
| RegionList[].LocalName | Region display name | China North 2 (Beijing), China East 2 (Shanghai) |

---

## 2. list-available-accelerate-areas

Query acceleration areas available for a specific instance.

```bash
aliyun ga list-available-accelerate-areas \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

---

## 3. list-isp-types

Query the public line types supported by acceleration regions.

```bash
aliyun ga list-isp-types \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

---

## 4. create-ip-sets

Create acceleration regions in batches.

### Create a single acceleration region

```bash
aliyun ga create-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerate-region AccelerateRegionId=cn-beijing Bandwidth=5 IpVersion=IPv4
```

### Create multiple acceleration regions

```bash
aliyun ga create-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerate-region '[{"AccelerateRegionId":"cn-beijing","Bandwidth":"5","IpVersion":"IPv4"},{"AccelerateRegionId":"cn-shanghai","Bandwidth":"5","IpVersion":"IPv4"},{"AccelerateRegionId":"us-west-1","Bandwidth":"3","IpVersion":"IPv4"}]'
```

### Create an IPv6 acceleration region

```bash
aliyun ga create-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerate-region AccelerateRegionId=cn-beijing Bandwidth=5 IpVersion=IPv6
```

### Create a dual-stack acceleration region

```bash
aliyun ga create-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerate-region AccelerateRegionId=cn-beijing Bandwidth=5 IpVersion=DUAL_STACK
```

### Specify BGP_PRO line type

```bash
aliyun ga create-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerate-region AccelerateRegionId=cn-hongkong Bandwidth=10 IpVersion=IPv4 IspType=BGP_PRO
```

### Parameter reference

| Parameter | Type | Required | Description | Allowed values |
|-----------|------|----------|-------------|----------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` | `cn-hangzhou` |
| AcceleratorId | string | Yes | GA instance ID | - |
| AccelerateRegion.N.AccelerateRegionId | string | Yes | Acceleration region ID | e.g. `cn-beijing`, `us-west-1` |
| AccelerateRegion.N.Bandwidth | integer | Yes | Bandwidth (Mbps) | Min `2` |
| AccelerateRegion.N.IpVersion | string | No | IP version | `IPv4` / `IPv6` / `DUAL_STACK` |
| AccelerateRegion.N.IspType | string | No | Public line type | `BGP` / `BGP_PRO` |
| ClientToken | string | No | Idempotency token | - |

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| RequestId | string | Request ID |
| IpSets | array | Acceleration region list |
| IpSets[].IpSetId | string | IpSet ID |
| IpSets[].AccelerateRegionId | string | Acceleration region |
| IpSets[].IpAddressList | array | Allocated acceleration IPs |
| IpSets[].Bandwidth | integer | Allocated bandwidth |
| IpSets[].IpVersion | string | IP version |
| IpSets[].State | string | State |

### Sample response

```json
{
  "RequestId": "6D2BFF54-6AF2-5EF8-xxxx",
  "IpSets": [
    {
      "IpSetId": "ips-bp1xxxx",
      "AccelerateRegionId": "cn-beijing",
      "IpAddressList": ["39.106.xxx.xxx"],
      "Bandwidth": 5,
      "IpVersion": "IPv4",
      "State": "active"
    }
  ]
}
```

### Error handling

| Error code | Meaning | Resolution |
|------------|---------|------------|
| StateError.Accelerator | GA instance state does not allow the operation | Retry after the instance becomes `active` |
| NotExist.BasicBandwidthPackage | No basic bandwidth package bound (PREPAY) | Complete Step 2 to bind a bandwidth package first |
| IpSetOverLimit | Too many acceleration regions | Reduce the number of acceleration regions |
| Bindwidthpackage.bindwidthNotEnough | Bandwidth package insufficient | Upgrade the bandwidth package or reduce allocated bandwidth |

---

## 5. list-ip-sets

Query the acceleration region list.

### List all acceleration regions of an instance

```bash
aliyun ga list-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --page-size 50
```

### Format output

```bash
aliyun ga list-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" | jq '.IpSets[] | {
    IpSetId,
    AccelerateRegionId,
    IpAddressList,
    Bandwidth,
    IpVersion,
    IspType,
    State
  }'
```

### Parameter reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| AcceleratorId | string | Yes | GA instance ID |
| PageNumber | integer | No | Page number, default `1` |
| PageSize | integer | No | Page size, max `50`, default `10` |

### Key response fields

| Field | Type | Description |
|-------|------|-------------|
| IpSetId | string | IpSet ID |
| AccelerateRegionId | string | Acceleration region |
| IpAddressList | array | Allocated acceleration IPs |
| Bandwidth | integer | Allocated bandwidth (Mbps) |
| IpVersion | string | IP version |
| IspType | string | Line type |
| State | string | State: `init`/`active`/`updating`/`deleting` |

---

## 6. describe-ip-set

Query details of a single acceleration region.

```bash
aliyun ga describe-ip-set \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --ip-set-id "${IP_SET_ID}"
```

---

## 7. update-ip-set

Modify the bandwidth of a single acceleration region.

```bash
aliyun ga update-ip-set \
  --biz-region-id cn-hangzhou \
  --ip-set-id "${IP_SET_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --bandwidth 10
```

### Parameter reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| IpSetId | string | Yes | IpSet ID |
| Bandwidth | integer | Yes | New bandwidth value (Mbps) |
| ClientToken | string | No | Idempotency token |

---

## 8. update-ip-sets

Modify multiple acceleration regions in batches.

```bash
aliyun ga update-ip-sets \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --ip-sets '[{"IpSetId":""${IP_SET_ID_1}"","Bandwidth":"10"},{"IpSetId":""${IP_SET_ID_2}"","Bandwidth":"20"}]'
```

---

## 9. get-ipsets-bandwidth-limit

Query the bandwidth limit of acceleration regions.

```bash
aliyun ga get-ipsets-bandwidth-limit \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

---

## Complete example: create acceleration regions and retrieve IPs

```bash
#!/bin/bash
GA_ID="ga-bp1xxxx"

# Step 1: Query available acceleration areas
echo "=== Available acceleration areas ==="
aliyun ga list-accelerate-areas \
  --user-agent "$GA_USER_AGENT" | jq '.Areas[] | "\(.AreaId) - \(.LocalName): \([.RegionList[].RegionId] | join(", "))"' -r

# Step 2: Create acceleration regions in batches
echo ""
echo "Creating acceleration regions..."
CREATE_RESULT=$(aliyun ga create-ip-sets \
  --user-agent "$GA_USER_AGENT" \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --accelerate-region '[{"AccelerateRegionId":"cn-beijing","Bandwidth":"5","IpVersion":"IPv4"},{"AccelerateRegionId":"us-west-1","Bandwidth":"3","IpVersion":"IPv4"}]')

echo "$CREATE_RESULT" | jq '.IpSets[] | "  \(.AccelerateRegionId): \(.IpAddressList | join(", ")) (Bandwidth: \(.Bandwidth)Mbps)"' -r

# Step 3: Wait for the acceleration regions to become active
echo ""
echo "Waiting for acceleration regions to become active..."
sleep 10

# Step 4: Query and display the final result
echo ""
echo "=== Acceleration region configuration ==="
aliyun ga list-ip-sets \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq '.IpSets[] | {
    Region: .AccelerateRegionId,
    Bandwidth: "\(.Bandwidth) Mbps",
    IpVersion: .IpVersion,
    AccelerationIPs: (.IpAddressList | join(", ")),
    State: .State
  }'
```
