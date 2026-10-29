# Basic GA Accelerator API Reference

This document provides complete CLI scripts for creating, configuring, and querying Basic Global Accelerator instances.

> **Important**: All GA APIs use `--biz-region-id cn-hangzhou`, which is the GA control plane region and independent of the actual acceleration region.
>
> **Environment**: Examples use Windows PowerShell syntax. Linux/macOS users can replace `ConvertFrom-Json` with `jq` and `$env:VAR` with shell variables.

---

## Basic GA Architecture

A Basic GA accelerator works at Layer 3 (IP layer) and provides point-to-point acceleration. Unlike Standard accelerators, Basic accelerators have no listener concept; traffic is forwarded through a mapping between an **accelerate IP** and an **endpoint**.

```
User request --> Accelerate IP --> Binding relation --> Endpoint --> Backend service
```

**Core resource relationships**:

```
Basic GA Accelerator
  |
  +-- Basic IP set (exactly 1)
  |     +-- Basic Accelerate IP
  |
  +-- Basic Endpoint Group (exactly 1)
        +-- Basic Endpoint
              +-- ECS / ENI / SLB / NLB

Accelerate IP --(CreateBasicAccelerateIpEndpointRelation)--> Endpoint
```

**Key constraints**:
- A Basic accelerator supports only **one acceleration region** and **IPv4 only**.
- A Basic accelerator supports only **one endpoint group**.
- The endpoint group region **must differ** from the acceleration region.
- Basic accelerators are used for Layer 3 network acceleration and are not suitable for Layer 7 routing, multiple listeners, or multi-endpoint-group load balancing.
- With an **ECS-type** endpoint, Basic GA binds the accelerate IP onto the ECS **primary ENI**. If that ENI already carries a public IP (an EIP, or an accelerate IP held by another Basic accelerator), the binding fails with `EcsCannotBind.BasicEndpoint`. Check the primary ENI with `describe-network-interfaces` first; on conflict, report it and let the user choose (release the existing binding, use another ECS, or use an **ENI-type** endpoint on the same instance) instead of silently switching type or releasing another accelerator's binding.

---

## 1. Basic Accelerator Management

### 1.1 create-basic-accelerator

#### POSTPAY

```powershell
$Result = aliyun ga create-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --charge-type POSTPAY `
  --bandwidth-billing-type CDT `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$AcceleratorId = $Result.AcceleratorId
Write-Host "Basic GA accelerator created: $AcceleratorId"
```

#### PREPAY

**Cost gate**: this generates a prepaid order — confirm spec, pricing cycle, duration, and estimated cost with the user before executing.

```powershell
$Result = aliyun ga create-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --charge-type PREPAY `
  --bandwidth-billing-type BandwidthPackage `
  --duration 1 `
  --pricing-cycle Month `
  --auto-pay true `
  --auto-renew true `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$AcceleratorId = $Result.AcceleratorId
Write-Host "Basic GA accelerator created: $AcceleratorId"
```

#### Parameter Reference

| Parameter | Type | Required | Description |
|---|---|---|---|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| ChargeType | string | No | `PREPAY` (default) / `POSTPAY` |
| BandwidthBillingType | string | No | `BandwidthPackage` / `CDT` / `CDT95` |
| Duration | integer | No | Purchase duration (PREPAY) |
| PricingCycle | string | No | `Month` / `Year` |
| AutoPay | boolean | No | Auto payment |
| AutoRenew | boolean | No | Auto renewal |
| AutoRenewDuration | integer | No | Auto renewal duration in months |
| ResourceGroupId | string | No | Resource group ID |
| Tag.N.Key / Tag.N.Value | string | No | Tags |

#### Response Fields

| Field | Description |
|---|---|
| AcceleratorId | Basic GA accelerator ID |
| OrderId | Order ID (PREPAY only) |

---

### 1.2 get-basic-accelerator

```powershell
$GA_ID = "ga-bp1xxxx"

$Result = aliyun ga get-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$Result | Select-Object AcceleratorId, Name, State, BasicIpSetId, BasicEndpointGroupId, BandwidthBillingType
```

#### Key Response Fields

| Field | Description |
|---|---|
| AcceleratorId | Accelerator ID |
| Name | Accelerator name |
| State | `init`/`active`/`configuring`/`binding`/`unbinding`/`deleting`/`finacialLocked` |
| BasicIpSetId | IP set ID |
| BasicEndpointGroupId | Endpoint group ID |
| BasicBandwidthPackage | Basic bandwidth package info |
| CrossDomainBandwidthPackage | Cross-domain bandwidth package info |
| BandwidthBillingType | Bandwidth billing type |
| CrossBorderStatus | Cross-border status |

---

### 1.3 list-basic-accelerators

```powershell
aliyun ga list-basic-accelerators `
  --biz-region-id cn-hangzhou `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object -ExpandProperty Accelerators |
  Select-Object AcceleratorId, Name, State, InstanceChargeType, BandwidthBillingType
```

#### Pagination

```powershell
$Page = 1
$PageSize = 10

while ($true) {
  $Result = aliyun ga list-basic-accelerators `
    --biz-region-id cn-hangzhou `
    --page-number "$Page" `
    --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

  $Result.Accelerators | Select-Object AcceleratorId, Name, State
  $Total = $Result.TotalCount

  if (($Page * $PageSize) -ge $Total) { break }
  $Page++
}
```

---

### 1.4 update-basic-accelerator

```powershell
aliyun ga update-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --name "basic-ga-production" `
  --user-agent "$env:GA_USER_AGENT" `
  --description "production basic ga"
```

---

## 2. Basic IP Set Management

### 2.1 create-basic-ip-set

> A Basic accelerator supports only one IP set and IPv4.

```powershell
$Result = aliyun ga create-basic-ip-set `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --accelerate-region-id cn-shanghai `
  --bandwidth 2 `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$IpSetId = $Result.IpSetId
Write-Host "IP set created: $IpSetId"
```

#### Parameter Reference

| Parameter | Type | Required | Description |
|---|---|---|---|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| AcceleratorId | string | Yes | Basic accelerator ID |
| AccelerateRegionId | string | Yes | Acceleration region ID |
| Bandwidth | long | No | Bandwidth in Mbps, minimum 2 |
| IspType | string | No | `BGP` (default) / `BGP_PRO` |

---

### 2.2 get-basic-ip-set

```powershell
aliyun ga get-basic-ip-set `
  --biz-region-id cn-hangzhou `
  --ip-set-id "$IpSetId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object IpSetId, AccelerateRegionId, Bandwidth, IspType, State
```

---

### 2.3 update-basic-ip-set

```powershell
aliyun ga update-basic-ip-set `
  --biz-region-id cn-hangzhou `
  --ip-set-id "$IpSetId" `
  --user-agent "$env:GA_USER_AGENT" `
  --bandwidth 10
```

---

## 3. Basic Accelerate IP Management

### 3.1 create-basic-accelerate-ip

```powershell
$Result = aliyun ga create-basic-accelerate-ip `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --ip-set-id "$IpSetId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$AccelerateIpId = $Result.AccelerateIpId
Write-Host "Accelerate IP created: $AccelerateIpId"
```

---

### 3.2 list-basic-accelerate-ips

```powershell
aliyun ga list-basic-accelerate-ips `
  --biz-region-id cn-hangzhou `
  --ip-set-id "$IpSetId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object -ExpandProperty AccelerateIps |
  Select-Object AccelerateIpId, AccelerateIpAddress, State
```

---

### 3.3 get-basic-accelerate-ip

```powershell
aliyun ga get-basic-accelerate-ip `
  --biz-region-id cn-hangzhou `
  --accelerate-ip-id "$AccelerateIpId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object AccelerateIpId, AccelerateIpAddress, State
```

---

## 4. Basic Endpoint Group Management

### 4.1 create-basic-endpoint-group

> A Basic accelerator supports only one endpoint group, and its region must differ from the acceleration region.

```powershell
$Result = aliyun ga create-basic-endpoint-group `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --endpoint-group-region cn-hangzhou `
  --name "basic-epg-hangzhou" `
  --description "basic endpoint group" `
  --endpoint-type ENI `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$EndpointGroupId = $Result.EndpointGroupId
Write-Host "Endpoint group created: $EndpointGroupId"
```

#### Parameter Reference

| Parameter | Type | Required | Description |
|---|---|---|---|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| AcceleratorId | string | Yes | Basic accelerator ID |
| EndpointGroupRegion | string | Yes | Endpoint group region |
| Name | string | No | Name |
| Description | string | No | Description |
| EndpointType | string | No | `ENI` / `SLB` / `ECS` |
| EndpointAddress | string | No | Endpoint address |
| EndpointSubAddress | string | No | Secondary private IP |

---

### 4.2 get-basic-endpoint-group

```powershell
aliyun ga get-basic-endpoint-group `
  --biz-region-id cn-hangzhou `
  --endpoint-group-id "$EndpointGroupId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object EndpointGroupId, Name, State, EndpointGroupRegion, EndpointType, EndpointAddress
```

---

### 4.3 update-basic-endpoint-group

```powershell
aliyun ga update-basic-endpoint-group `
  --biz-region-id cn-hangzhou `
  --endpoint-group-id "$EndpointGroupId" `
  --name "basic-epg-updated" `
  --endpoint-type ECS `
  --endpoint-address "i-bp1xxxx" `
  --user-agent "$env:GA_USER_AGENT" `
  --endpoint-sub-address "172.16.1.10"
```

---

## 5. Basic Endpoint Management

### 5.1 create-basic-endpoint

```powershell
$Result = aliyun ga create-basic-endpoint `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --endpoint-group-id "$EndpointGroupId" `
  --name "ep-01" `
  --endpoint-type ENI `
  --endpoint-address "eni-bp1xxxx" `
  --endpoint-sub-address "172.16.1.10" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$EndpointId = $Result.EndpointId
Write-Host "Endpoint created: $EndpointId"
```

#### Parameter Reference

| Parameter | Type | Required | Description |
|---|---|---|---|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| AcceleratorId | string | Yes | Basic accelerator ID |
| EndpointGroupId | string | Yes | Endpoint group ID |
| Name | string | No | Name |
| EndpointType | string | Yes | `ENI` / `SLB` / `ECS` / `NLB` |
| EndpointAddress | string | Yes | Endpoint address (resource ID) |
| EndpointSubAddress | string | No | Secondary private IP |
| EndpointSubAddressType | string | No | `primary` / `secondary` |
| EndpointZoneId | string | No | Availability zone ID (required for NLB) |

---

### 5.2 create-basic-endpoints (batch)

```powershell
aliyun ga create-basic-endpoints `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --endpoint-group-id "$EndpointGroupId" `
  --Endpoints.1.Name "ep-01" `
  --Endpoints.1.EndpointType ENI `
  --Endpoints.1.EndpointAddress "eni-bp1xxxx" `
  --Endpoints.1.EndpointSubAddress "172.16.1.10" `
  --Endpoints.2.Name "ep-02" `
  --Endpoints.2.EndpointType ECS `
  --Endpoints.2.EndpointAddress "i-bp1yyyy" `
  --user-agent "$env:GA_USER_AGENT" `
  --Endpoints.2.EndpointSubAddress "172.16.1.11"
```

---

### 5.3 list-basic-endpoints

```powershell
aliyun ga list-basic-endpoints `
  --biz-region-id cn-hangzhou `
  --endpoint-group-id "$EndpointGroupId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object -ExpandProperty Endpoints |
  Select-Object EndpointId, Name, EndpointType, EndpointAddress, State
```

---

### 5.4 get-basic-endpoint

```powershell
aliyun ga get-basic-endpoint `
  --biz-region-id cn-hangzhou `
  --endpoint-id "$EndpointId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object EndpointId, Name, EndpointType, EndpointAddress, State
```

---

### 5.5 update-basic-endpoint

```powershell
aliyun ga update-basic-endpoint `
  --biz-region-id cn-hangzhou `
  --endpoint-group-id "$EndpointGroupId" `
  --endpoint-id "$EndpointId" `
  --user-agent "$env:GA_USER_AGENT" `
  --name "ep-renamed"
```

---

## 6. Accelerate IP–Endpoint Binding Relations

### 6.1 create-basic-accelerate-ip-endpoint-relation

```powershell
$Result = aliyun ga create-basic-accelerate-ip-endpoint-relation `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --accelerate-ip-id "$AccelerateIpId" `
  --endpoint-id "$EndpointId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

Write-Host "Binding relation submitted: $($Result.RequestId)"
```

---

### 6.2 list-basic-accelerate-ip-endpoint-relations

```powershell
aliyun ga list-basic-accelerate-ip-endpoint-relations `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object -ExpandProperty AccelerateIpEndpointRelations |
  Select-Object AccelerateIpId, EndpointId, State
```

---

### 6.3 get-basic-accelerate-ip-endpoint-relation

```powershell
aliyun ga get-basic-accelerate-ip-endpoint-relation `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --accelerate-ip-id "$AccelerateIpId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object AccelerateIpId, EndpointId, State
```

---

## 7. Complete Deployment Flow (PowerShell)

The following script demonstrates how to create and configure a Basic GA accelerator from scratch.

```powershell
# ============================================
# Basic GA one-click deployment script (PowerShell)
# ============================================

$GA_NAME = "basic-ga-demo"
$ACCELERATE_REGION = "cn-shanghai"     # acceleration region
$ENDPOINT_GROUP_REGION = "cn-hangzhou" # endpoint group region (must differ from acceleration region)
$ENDPOINT_TYPE = "ENI"
$ENDPOINT_ADDRESS = "eni-bp1xxxx"      # replace with actual resource ID
$ENDPOINT_SUB_ADDRESS = "172.16.1.10"  # replace with actual private IP
$ISP_TYPE = "BGP"
$BANDWIDTH = 2

# Step 1: Create Basic accelerator
Write-Host "=== Step 1: Create Basic GA accelerator ==="
$GaResult = aliyun ga create-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --charge-type POSTPAY `
  --bandwidth-billing-type CDT `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$GA_ID = $GaResult.AcceleratorId
Write-Host "Accelerator ID: $GA_ID"

# Wait for accelerator to become active
$MaxWait = 30
for ($i = 1; $i -le $MaxWait; $i++) {
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
  if ($Info.State -eq "active") {
    Write-Host "Accelerator is active"
    break
  }
  Write-Host "Waiting for accelerator... [$i/$MaxWait] current state: $($Info.State)"
  Start-Sleep -Seconds 10
}

# Step 2: Create IP set
Write-Host ""
Write-Host "=== Step 2: Create IP set ==="
$IpSetResult = aliyun ga create-basic-ip-set `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --accelerate-region-id "$ACCELERATE_REGION" `
  --bandwidth "$BANDWIDTH" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$IpSetId = $IpSetResult.IpSetId
Write-Host "IP set ID: $IpSetId"

# Wait for IP set to become active
for ($i = 1; $i -le 30; $i++) {
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
  if ($IpSet.State -eq "active") {
    Write-Host "IP set is active"
    break
  }
  Start-Sleep -Seconds 10
}

# Step 3: Create accelerate IP
Write-Host ""
Write-Host "=== Step 3: Create accelerate IP ==="
$IpResult = aliyun ga create-basic-accelerate-ip `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$AccelerateIpId = $IpResult.AccelerateIpId
Write-Host "Accelerate IP ID: $AccelerateIpId"

# Wait for accelerate IP to become active
for ($i = 1; $i -le 30; $i++) {
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
  if ($IpInfo.State -eq "active") {
    Write-Host "Accelerate IP is active: $($IpInfo.AccelerateIpAddress)"
    break
  }
  Start-Sleep -Seconds 10
}

# Step 4: Create endpoint group
Write-Host ""
Write-Host "=== Step 4: Create endpoint group ==="
$EpgResult = aliyun ga create-basic-endpoint-group `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --endpoint-group-region "$ENDPOINT_GROUP_REGION" `
  --name "$GA_NAME-epg" `
  --endpoint-type "$ENDPOINT_TYPE" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$EndpointGroupId = $EpgResult.EndpointGroupId
Write-Host "Endpoint group ID: $EndpointGroupId"

for ($i = 1; $i -le 30; $i++) {
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
  if ($Epg.State -eq "active") {
    Write-Host "Endpoint group is active"
    break
  }
  Start-Sleep -Seconds 10
}

# Step 5: Create endpoint
Write-Host ""
Write-Host "=== Step 5: Create endpoint ==="
$EpResult = aliyun ga create-basic-endpoint `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --endpoint-group-id "$EndpointGroupId" `
  --name "$GA_NAME-ep" `
  --endpoint-type "$ENDPOINT_TYPE" `
  --endpoint-address "$ENDPOINT_ADDRESS" `
  --endpoint-sub-address "$ENDPOINT_SUB_ADDRESS" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json

$EndpointId = $EpResult.EndpointId
Write-Host "Endpoint ID: $EndpointId"

for ($i = 1; $i -le 30; $i++) {
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
  if ($Ep.State -eq "active") {
    Write-Host "Endpoint is active"
    break
  }
  Start-Sleep -Seconds 10
}

# Step 6: Bind accelerate IP to endpoint
Write-Host ""
Write-Host "=== Step 6: Bind accelerate IP to endpoint ==="
aliyun ga create-basic-accelerate-ip-endpoint-relation `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --accelerate-ip-id "$AccelerateIpId" `
  --endpoint-id "$EndpointId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object RequestId

# Wait for binding to become active
for ($i = 1; $i -le 30; $i++) {
  $Relation = aliyun ga get-basic-accelerate-ip-endpoint-relation `
    --biz-region-id cn-hangzhou `
    --accelerator-id "$GA_ID" `
    --accelerate-ip-id "$AccelerateIpId" `
    --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
  if ($Relation.State -eq "active") {
    Write-Host "Binding relation is active"
    break
  }
  Start-Sleep -Seconds 10
}

# Deployment summary
Write-Host ""
Write-Host "========================================="
Write-Host "  Basic GA deployment complete"
Write-Host "========================================="
Write-Host "Accelerator ID:        $GA_ID"
Write-Host "Acceleration region:   $ACCELERATE_REGION"
Write-Host "Accelerate IP ID:      $AccelerateIpId"
Write-Host "Endpoint group ID:     $EndpointGroupId"
Write-Host "Endpoint ID:           $EndpointId"
Write-Host "========================================="
```

---

## 8. Diagnostic Commands

### Mandatory query chain

Run these three calls in order, and only these three, to establish the basic instance state:

1. `list-basic-accelerators` — confirm the ID is a Basic accelerator (`.Accelerators[]`).
2. `get-basic-accelerator` — `State`, `BasicIpSetId`, `BasicEndpointGroupId`, `BandwidthBillingType`.
3. `list-basic-accelerate-ip-endpoint-relations --accelerator-id` — instance-level bindings; always call it, even on a bare instance (empty `AccelerateIpEndpointRelations` plus a real `RequestId` is a valid result).

`describe-accelerator` / `list-accelerators` return Standard accelerators only and must never be used as a fallback for a Basic ID — doing so reports the Basic instance as missing or silently matches an unrelated Standard instance.

### Query accelerator state

```powershell
$Acc = aliyun ga get-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
$Acc | Select-Object Name, State, BasicIpSetId, BasicEndpointGroupId
$IP_SET_ID = $Acc.BasicIpSetId
```

### Query accelerate IPs and bindings

```powershell
# List accelerate IPs
$Ips = aliyun ga list-basic-accelerate-ips `
  --biz-region-id cn-hangzhou `
  --ip-set-id "$IP_SET_ID" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
$Ips.AccelerateIps | Select-Object AccelerateIpId, AccelerateIpAddress, State

# List binding relations
$Relations = aliyun ga list-basic-accelerate-ip-endpoint-relations `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
$Relations.AccelerateIpEndpointRelations | Select-Object AccelerateIpId, EndpointId, State
```

### Check endpoint status

```powershell
aliyun ga list-basic-endpoints `
  --biz-region-id cn-hangzhou `
  --endpoint-group-id "$EndpointGroupId" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json |
  Select-Object -ExpandProperty Endpoints |
  Select-Object EndpointId, Name, EndpointType, EndpointAddress, State
```

### Report configuration before health

A Basic accelerator has no listener, so `get-health-status` does not apply. When no IP set, endpoint group, or endpoint exists, report health as "not applicable" — not "abnormal" — and structure the answer in three sections: **Configured**, **Not configured / Abnormal**, and **Next steps**. Each missing layer needs a concrete next step (create the IP set, create the endpoint group with a region different from the acceleration region, then create the endpoint and bind it), together with the exact command and its constraints.

---

## 9. Common Issues

### Issue 1: `InvalidateRegion.BasicAccelerator` when creating endpoint group

**Cause**: The endpoint group region is the same as the acceleration region.

**Solution**: Choose a region different from `$ACCELERATE_REGION` as `$ENDPOINT_GROUP_REGION`.

### Issue 2: `NotExist.BasicBandwidthPackage` when creating IP set

**Cause**: A PREPAY Basic accelerator is not bound to a basic bandwidth package.

**Solution**: Create and bind a basic bandwidth package first, or switch to POSTPAY + CDT.

### Issue 3: Cannot create a second acceleration region

**Cause**: A Basic accelerator supports only one acceleration region.

**Solution**: Use a Standard GA accelerator for multi-region acceleration.

### Issue 4: `ConvertFrom-Json` error in PowerShell

**Cause**: The aliyun CLI output may be empty or contain non-JSON content.

**Solution**: Check the CLI return value first; if necessary, write to a file before parsing:

```powershell
--user-agent "$env:GA_USER_AGENT" aliyun ga get-basic-accelerator --biz-region-id cn-hangzhou --accelerator-id "$GA_ID" > ga.json
Get-Content ga.json | ConvertFrom-Json
```

---

## 10. API Quick Reference

| Feature | API | Description |
|---|---|---|
| Create accelerator | `create-basic-accelerator` | Create Basic accelerator |
| Query accelerator | `get-basic-accelerator` | Query accelerator details |
| List accelerators | `list-basic-accelerators` | List accelerators |
| Update accelerator | `update-basic-accelerator` | Update name/description |
| Create IP set | `create-basic-ip-set` | Create IP set |
| Query IP set | `get-basic-ip-set` | Query IP set |
| Update IP set | `update-basic-ip-set` | Update bandwidth |
| Create accelerate IP | `create-basic-accelerate-ip` | Create accelerate IP |
| Query accelerate IP | `get-basic-accelerate-ip` / `list-basic-accelerate-ips` | Query accelerate IP |
| Create endpoint group | `create-basic-endpoint-group` | Create endpoint group |
| Query endpoint group | `get-basic-endpoint-group` | Query endpoint group |
| Update endpoint group | `update-basic-endpoint-group` | Update endpoint group |
| Create endpoint | `create-basic-endpoint` / `create-basic-endpoints` | Create endpoint |
| Query endpoint | `get-basic-endpoint` / `list-basic-endpoints` | Query endpoint |
| Update endpoint | `update-basic-endpoint` | Update endpoint name |
| Create relation | `create-basic-accelerate-ip-endpoint-relation` | Bind accelerate IP to endpoint |
| Query relation | `get-basic-accelerate-ip-endpoint-relation` / `list-basic-accelerate-ip-endpoint-relations` | Query binding relation |
