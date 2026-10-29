# Import Existing GA Accelerator Reference

This document describes how to pull the full configuration of an existing GA accelerator by its ID and rebuild `ga-config.json` and `ga-listeners.json`.

> **Important**: All GA APIs use `--biz-region-id cn-hangzhou`.
>
> **Environment**: Examples use Bash + jq. Windows PowerShell users can replace `jq` with `ConvertFrom-Json`, use `$VAR` variables, and backticks `` ` `` for line continuation.

---

## 1. Import Flow Overview

```
Input GA_ID
    │
    ├─ Detect instance type (Standard / Basic)
    │
    ├─ Standard accelerator
    │    ├─ Get accelerator info (describe-accelerator)
    │    ├─ Get acceleration regions (list-ip-sets)
    │    ├─ Get listeners (list-listeners)
    │    ├─ Get endpoint groups per listener (list-endpoint-groups)
    │    ├─ Get endpoint group details (describe-endpoint-group)
    │    └─ Save as ga-config.json + ga-listeners.json
    │
    └─ Basic accelerator
         ├─ Get accelerator info (get-basic-accelerator)
         ├─ Get acceleration region (get-basic-ip-set)
         ├─ Get accelerate IPs (list-basic-accelerate-ips)
         ├─ Get endpoint group (get-basic-endpoint-group)
         ├─ Get endpoints (list-basic-endpoints)
         ├─ Get bindings (list-basic-accelerate-ip-endpoint-relations)
         └─ Save as ga-config.json
```

---

## 2. Import Standard Accelerator

### 2.1 Detect Instance Type

Resolve the type from the Basic accelerator list first. `list-basic-accelerators` returns only Basic instances, so a match there is definitive and never picks up an unrelated Standard accelerator.

```bash
GA_ID="ga-bp1xxxx"

BASIC_LIST=$(aliyun ga list-basic-accelerators \
  --biz-region-id cn-hangzhou \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT")

if [ "$(echo "$BASIC_LIST" | jq -r --arg id "$GA_ID" \
      '[.Accelerators[] | select(.AcceleratorId == $id)] | length')" -eq 1 ]; then
  echo "Basic accelerator"
  INSTANCE_TYPE="Basic"
else
  RESULT=$(aliyun ga describe-accelerator \
    --biz-region-id cn-hangzhou \
    --accelerator-id "$GA_ID" \
    --user-agent "$GA_USER_AGENT" 2>/dev/null)
  if [ -n "$RESULT" ] && [ "$(echo "$RESULT" | jq -r '.AcceleratorId // empty')" = "$GA_ID" ]; then
    echo "Standard accelerator"
    INSTANCE_TYPE="Standard"
  else
    echo "Cannot detect instance type or accelerator does not exist"
    exit 1
  fi
fi
```

**Never** answer a Basic accelerator question from `list-accelerators` / `describe-accelerator`: those return Standard instances only, so they either report the Basic instance as missing or silently match a different Standard accelerator in the same account. If `get-basic-accelerator` fails for a Basic ID, report the error instead of falling back to the Standard APIs.

**Mandatory Basic query chain** (run in this order): `list-basic-accelerators` → `get-basic-accelerator` → `list-basic-accelerate-ip-endpoint-relations`. The last call is instance-level and must always run, even on a bare instance. Only then query per-resource details (`get-basic-ip-set`, `list-basic-accelerate-ips`, `get-basic-endpoint-group`, `list-basic-endpoints`) when the corresponding IDs are non-empty.

### 2.2 One-Click Standard Import

```bash
#!/bin/bash
GA_ID="${1:?Please provide GA accelerator ID, usage: bash import_standard_ga.sh <GA_ID>}"
REGION="cn-hangzhou"

echo "=== Importing Standard GA accelerator: $GA_ID ==="

# Step 1: Accelerator info
GA_INFO=$(aliyun ga describe-accelerator \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" )

echo "Accelerator info:"
echo "$GA_INFO" | jq '{
  AcceleratorId,
  Name,
  State,
  Spec,
  InstanceChargeType,
  BandwidthBillingType,
  DnsName,
  CrossBorderStatus,
  IpSetConfig
}'

# Step 2: Acceleration regions
IP_SETS=$(aliyun ga list-ip-sets \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" )

echo ""
echo "Acceleration regions:"
echo "$IP_SETS" | jq '.IpSets[] | {
  IpSetId,
  AccelerateRegionId,
  Bandwidth,
  IpVersion,
  IspType,
  IpAddressList
}'

# Step 3: Listeners
LISTENERS=$(aliyun ga list-listeners \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" )

echo ""
echo "Listeners:"
echo "$LISTENERS" | jq '.Listeners[] | {
  ListenerId,
  Name,
  Protocol,
  PortRanges,
  Type,
  State,
  ClientAffinity
}'

# Step 3.5: Optional per-resource detail snapshots
# Use when the user needs an authoritative per-resource archive
# (for example for drift detection), or explicitly asks to fetch
# the details of each acceleration region / each listener.
for IP_SET_ID in $(echo "$IP_SETS" | jq -r '.IpSets[].IpSetId'); do
  aliyun ga describe-ip-set \
  --biz-region-id "$REGION" \
  --ip-set-id "$IP_SET_ID" \
  --user-agent "$GA_USER_AGENT" > "ip_set_${IP_SET_ID}.json"
done

for LSR_ID in $(echo "$LISTENERS" | jq -r '.Listeners[].ListenerId'); do
  aliyun ga describe-listener \
  --biz-region-id "$REGION" \
  --listener-id "$LSR_ID" \
  --user-agent "$GA_USER_AGENT" > "listener_${LSR_ID}.json"
done

# Step 4: Endpoint groups per listener
LISTENER_IDS=$(echo "$LISTENERS" | jq -r '.Listeners[].ListenerId')

EPG_DETAILS="[]"
for LID in $LISTENER_IDS; do
EPG_LIST=$(aliyun ga list-endpoint-groups \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --listener-id "$LID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" )
  EPG_IDS=$(echo "$EPG_LIST" | jq -r '.EndpointGroups[].EndpointGroupId // empty')

  for EPG_ID in $EPG_IDS; do
EPG_INFO=$(aliyun ga describe-endpoint-group \
  --biz-region-id "$REGION" \
  --endpoint-group-id "$EPG_ID" \
  --user-agent "$GA_USER_AGENT" )
    EPG_DETAILS=$(echo "$EPG_DETAILS" "$EPG_INFO" | jq -s '.[0] + [.[1]]')
  done
done

echo ""
echo "Endpoint groups:"
echo "$EPG_DETAILS" | jq '.[] | {
  EndpointGroupId,
  Name,
  EndpointGroupRegion,
  TrafficPercentage,
  HealthCheckEnabled,
  HealthCheckProtocol,
  HealthCheckPort,
  EndpointConfigurations,
  PortOverrides
}'

# Step 5: Generate ga-config.json
cat > ga-config.json <<EOF
{
  "accelerator_id": $(echo "$GA_INFO" | jq '.AcceleratorId'),
  "accelerator_name": $(echo "$GA_INFO" | jq '.Name'),
  "instance_charge_type": $(echo "$GA_INFO" | jq '.InstanceChargeType'),
  "bandwidth_billing_type": $(echo "$GA_INFO" | jq '.BandwidthBillingType'),
  "dns_name": $(echo "$GA_INFO" | jq '.DnsName'),
  "ip_set_config": $(echo "$GA_INFO" | jq '.IpSetConfig'),
  "bandwidth_packages": [],
  "ip_sets": $(echo "$IP_SETS" | jq '[.IpSets[] | {
    ip_set_id: .IpSetId,
    accelerate_region_id: .AccelerateRegionId,
    ip_version: .IpVersion,
    isp_type: .IspType,
    bandwidth: .Bandwidth,
    accelerate_ips: .IpAddressList
  }]'),
  "listeners": $(echo "$LISTENERS" | jq '[.Listeners[] | {
    listener_id: .ListenerId,
    name: .Name,
    protocol: .Protocol,
    port: (.PortRanges[0].FromPort),
    client_affinity: .ClientAffinity,
    endpoint_groups: []
  }]'),
  "cross_border_status": $(echo "$GA_INFO" | jq '.CrossBorderStatus // false')
}
EOF

# Step 6: Generate ga-listeners.json
cat > ga-listeners.json <<EOF
{
  "listeners": $(echo "$LISTENERS" | jq '[.Listeners[] | {
    listener_id: .ListenerId,
    name: .Name,
    protocol: .Protocol,
    port_ranges: .PortRanges,
    type: .Type,
    client_affinity: .ClientAffinity,
    certificates: (.Certificates // []),
    security_policy_id: .SecurityPolicyId,
    endpoint_groups: []
  }]')
}
EOF

# Fill endpoint groups into ga-listeners.json
for LID in $LISTENER_IDS; do
EPG_LIST=$(aliyun ga list-endpoint-groups \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --listener-id "$LID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" )
  EPG_IDS=$(echo "$EPG_LIST" | jq -r '.EndpointGroups[].EndpointGroupId // empty')

  for EPG_ID in $EPG_IDS; do
EPG_INFO=$(aliyun ga describe-endpoint-group \
  --biz-region-id "$REGION" \
  --endpoint-group-id "$EPG_ID" \
  --user-agent "$GA_USER_AGENT" )

    EPG_OBJ=$(echo "$EPG_INFO" | jq '{
      endpoint_group_id: .EndpointGroupId,
      name: .Name,
      endpoint_group_region: .EndpointGroupRegion,
      endpoint_group_type: (.EndpointGroupType // "default"),
      traffic_percentage: (.TrafficPercentage // 100),
      health_check: {
        enabled: .HealthCheckEnabled,
        protocol: .HealthCheckProtocol,
        port: .HealthCheckPort,
        path: .HealthCheckPath,
        interval_seconds: .HealthCheckIntervalSeconds,
        threshold_count: .ThresholdCount
      },
      endpoint_group_ip_list: (.EndpointGroupIpAddressList // []),
      endpoints: [.EndpointConfigurations[] | {
        type: .Type,
        endpoint: .Endpoint,
        sub_address: .EndpointSubAddress,
        weight: .Weight,
        enable_client_ip_preservation: .EnableClientIPPreservation,
        enable_proxy_protocol: .EnableProxyProtocol
      }],
      port_overrides: (.PortOverrides // [])
    }')

    jq --arg lid "$LID" --argjson epg "$EPG_OBJ" '
      .listeners |= map(
        if .listener_id == $lid then
          .endpoint_groups += [$epg]
        else
          .
        end
      )
    ' ga-listeners.json > ga-listeners.json.tmp && mv ga-listeners.json.tmp ga-listeners.json
  done
done

echo ""
echo "=== Import complete ==="
echo "ga-config.json generated"
echo "ga-listeners.json generated"
```

---

## 3. Import Basic Accelerator

> **Query chain**: `list-basic-accelerators` → `get-basic-accelerator` → `list-basic-accelerate-ip-endpoint-relations`. The first call confirms the ID belongs to a Basic accelerator; the last one is instance-level and always runs. Do not substitute `describe-accelerator` for any of these.
>
> **Bare instance handling**: `BasicIpSetId` / `BasicEndpointGroupId` are empty on an accelerator that has never been configured. Skip only Steps 2-5 in that case (they need an IP set / endpoint group ID) and report those parts as "not configured". Step 6 MUST still run: `list-basic-accelerate-ip-endpoint-relations --accelerator-id` is an instance-level query, succeeds on a bare instance and returns an empty `AccelerateIpEndpointRelations` list with a real `RequestId`.
>
> **Data integrity**: every result file you save must be the raw output of a real API call (it contains `RequestId`). Never synthesize placeholder JSON for a query that was skipped or failed — save the real error or state the gap in the report instead.

```bash
#!/bin/bash
GA_ID="${1:?Please provide Basic GA accelerator ID, usage: bash import_basic_ga.sh <GA_ID>}"
REGION="cn-hangzhou"

echo "=== Importing Basic GA accelerator: $GA_ID ==="

# Step 1: Accelerator info
GA_INFO=$(aliyun ga get-basic-accelerator \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" )

# Step 2-3: Acceleration region + accelerate IPs (only when configured)
IP_SET_ID=$(echo "$GA_INFO" | jq -r '.BasicIpSetId // empty')
if [ -n "$IP_SET_ID" ]; then
  IP_SET_INFO=$(aliyun ga get-basic-ip-set \
    --biz-region-id "$REGION" \
    --ip-set-id "$IP_SET_ID" \
    --user-agent "$GA_USER_AGENT" )

  ACCELERATE_IPS=$(aliyun ga list-basic-accelerate-ips \
    --biz-region-id "$REGION" \
    --ip-set-id "$IP_SET_ID" \
    --max-results 50 \
    --user-agent "$GA_USER_AGENT" )
else
  IP_SET_INFO=""
  ACCELERATE_IPS='{"AccelerateIps":[]}'
fi

# Step 4-5: Endpoint group + endpoints (only when configured)
EPG_ID=$(echo "$GA_INFO" | jq -r '.BasicEndpointGroupId // empty')
if [ -n "$EPG_ID" ]; then
  EPG_INFO=$(aliyun ga get-basic-endpoint-group \
    --biz-region-id "$REGION" \
    --endpoint-group-id "$EPG_ID" \
    --user-agent "$GA_USER_AGENT" )

  ENDPOINTS=$(aliyun ga list-basic-endpoints \
    --biz-region-id "$REGION" \
    --endpoint-group-id "$EPG_ID" \
    --max-results 50 \
    --user-agent "$GA_USER_AGENT" )
else
  EPG_INFO=""
  ENDPOINTS='{"Endpoints":[]}'
fi

# Step 6: Bindings — ALWAYS run, even for a bare instance (instance-level query)
RELATIONS=$(aliyun ga list-basic-accelerate-ip-endpoint-relations \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --max-results 50 \
  --user-agent "$GA_USER_AGENT" )

# Generate ga-config.json
cat > ga-config.json <<EOF
{
  "accelerator_id": $(echo "$GA_INFO" | jq '.AcceleratorId'),
  "accelerator_name": $(echo "$GA_INFO" | jq '.Name'),
  "instance_type": "Basic",
  "instance_charge_type": $(echo "$GA_INFO" | jq '.InstanceChargeType'),
  "bandwidth_billing_type": $(echo "$GA_INFO" | jq '.BandwidthBillingType'),
  "cross_border_status": $(echo "$GA_INFO" | jq '.CrossBorderStatus // false'),
  "ip_sets": $(if [ -n "$IP_SET_INFO" ]; then echo "$IP_SET_INFO" | jq --argjson ips "$ACCELERATE_IPS" '[{
    ip_set_id: .IpSetId,
    accelerate_region_id: .AccelerateRegionId,
    ip_version: "IPv4",
    isp_type: (.IspType // "BGP"),
    bandwidth: .Bandwidth,
    accelerate_ips: [$ips.AccelerateIps[].AccelerateIpAddress]
  }]'; else echo '[]'; fi),
  "basic_endpoint_group": $(if [ -n "$EPG_INFO" ]; then echo "$EPG_INFO" | jq '{
    endpoint_group_id: .EndpointGroupId,
    endpoint_group_region: .EndpointGroupRegion,
    name: .Name,
    endpoint_type: .EndpointType,
    endpoint_address: .EndpointAddress
  }'; else echo null; fi),
  "basic_endpoints": $(echo "$ENDPOINTS" | jq '[.Endpoints[] | {
    endpoint_id: .EndpointId,
    name: .Name,
    endpoint_type: .EndpointType,
    endpoint_address: .EndpointAddress,
    endpoint_sub_address: .EndpointSubAddress,
    endpoint_sub_address_type: .EndpointSubAddressType,
    endpoint_zone_id: .EndpointZoneId
  }]'),
  "accelerate_ip_endpoint_relations": $(echo "$RELATIONS" | jq '[.AccelerateIpEndpointRelations[] | {
    accelerate_ip_id: .AccelerateIpId,
    endpoint_id: .EndpointId,
    state: .State
  }]')
}
EOF

echo ""
echo "=== Import complete ==="
echo "ga-config.json generated"
```

---

## 4. Post-Import Validation

```bash
# Validate JSON syntax
jq empty ga-config.json
jq empty ga-listeners.json

# Simple structure overview
echo "=== ga-config.json keys ==="
jq 'keys' ga-config.json

echo "=== ga-listeners.json keys ==="
jq 'keys' ga-listeners.json

# Check accelerator state
GA_ID=$(jq -r '.accelerator_id' ga-config.json)
aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq '{AcceleratorId, Name, State}'
```

---

## 5. PowerShell Adaptation

On Windows, replace `jq` with `ConvertFrom-Json`. The core logic remains the same:

```powershell
$GA_ID = "ga-bp1xxxx"
$GA_INFO = aliyun ga describe-accelerator `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
$GA_INFO | Select-Object AcceleratorId, Name, State, InstanceChargeType, BandwidthBillingType
```

To save JSON files:

```powershell
$GA_INFO | ConvertTo-Json -Depth 10 | Out-File ga-config.json -Encoding UTF8
```

---

## 6. Common Issues

### Issue 1: `ga-config.json` listeners are empty after import

**Cause**: The Standard accelerator has no listeners.

**Solution**: Confirm the accelerator is fully configured or that only the base info was imported.

### Issue 2: Basic accelerator cannot use `describe-accelerator`

**Cause**: Basic accelerators use a separate API namespace (`Basic*`).

**Solution**: Resolve the type with `list-basic-accelerators` first, then use `get-basic-accelerator` for a Basic instance. Never treat a `describe-accelerator` failure as "instance does not exist", and never fall back to a Standard instance with a similar name — the two namespaces are disjoint.

### Issue 3: Endpoint group fields are missing

**Cause**: `describe-endpoint-group` return fields may not exactly match the `ga-listeners.json` template.

**Solution**: Add additional field mappings in the script as needed (e.g., `EndpointRequestProtocol`, `EnableClientIPPreservation`).
