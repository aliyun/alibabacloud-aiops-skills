# GA Endpoint Group and Endpoint API Reference (Steps 5-6)

This document provides complete CLI scripts for creating, querying, and modifying Global Accelerator endpoint groups and endpoints.

> **Endpoint groups** are associated with a specific region and contain one or more endpoints. **Endpoints** are the backend services that receive user requests.

> **Two-step flow (mandatory)**: create the endpoint group WITHOUT `--endpoint-configurations`, wait until it is created, then add endpoints with `update-endpoint-group`. Always follow this order.
>
> **Idempotent finalization (mandatory)**: if `create-endpoint-group` is retried, it can land on an endpoint group created by an earlier attempt that already holds the target endpoint. Regardless of what the create call returns — a new ID, a name conflict, or an existing group found via `list-endpoint-groups` — still execute `update-endpoint-group` explicitly with the target endpoint list. Replacing that call with `describe-endpoint-group` / `list-endpoint-groups` and reporting "endpoint already present" is not completion: the run is complete only when the log contains a successful `UpdateEndpointGroup` request for the target endpoint group.

---

## 1. create-endpoint-group

Create an endpoint group (without endpoints; add them in step 2 of the flow).

```bash
aliyun ga create-endpoint-group \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --endpoint-group-region cn-hangzhou \
  --name "epg-hangzhou" \
  --traffic-percentage 100 \
  --health-check-enabled true \
  --health-check-protocol tcp \
  --health-check-port 80 \
  --health-check-interval-seconds 10 \
  --threshold-count 3 \
  --user-agent "$GA_USER_AGENT"
```

### Add endpoints after create (single endpoint, inline form)

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=Ip Endpoint="47.xxx.xxx.xxx" Weight=255 EnableClientIPPreservation=true \
  --user-agent "$GA_USER_AGENT"
```

### ECS endpoint

`update-endpoint-group` replaces the whole endpoint list — include every endpoint you want to keep.

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=ECS Endpoint="${ECS_INSTANCE_ID}" Weight=255 EnableClientIPPreservation=true \
  --user-agent "$GA_USER_AGENT"
```

### SLB endpoint

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=SLB Endpoint="${SLB_ID}" Weight=255 \
  --user-agent "$GA_USER_AGENT"
```

### ALB endpoint

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=ALB Endpoint="${ALB_ID}" Weight=255 \
  --user-agent "$GA_USER_AGENT"
```

### NLB endpoint

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=NLB Endpoint="${NLB_ID}" Weight=255 \
  --user-agent "$GA_USER_AGENT"
```

### OSS endpoint

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=OSS Endpoint="${OSS_BUCKET}.oss-cn-hangzhou.aliyuncs.com" Weight=255 \
  --user-agent "$GA_USER_AGENT"
```

### Multiple endpoints (load balancing, JSON array form)

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations '[{"Type":"Ip","Endpoint":"47.xxx.xxx.1","Weight":200,"EnableClientIPPreservation":true},{"Type":"Ip","Endpoint":"47.xxx.xxx.2","Weight":100,"EnableClientIPPreservation":true},{"Type":"ECS","Endpoint":"'"${ECS_ID}"'","Weight":50}]' \
  --user-agent "$GA_USER_AGENT"
```

### Port override

```bash
aliyun ga create-endpoint-group \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --endpoint-group-region cn-hangzhou \
  --name "epg-port-mapping" \
  --traffic-percentage 100 \
  --port-overrides ListenerPort=80 EndpointPort=8080 \
  --user-agent "$GA_USER_AGENT"

aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=Ip Endpoint="47.xxx.xxx.xxx" Weight=255 \
  --user-agent "$GA_USER_AGENT"
```

### HTTP health check

```bash
aliyun ga create-endpoint-group \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --endpoint-group-region cn-hangzhou \
  --name "epg-http-health" \
  --traffic-percentage 100 \
  --health-check-enabled true \
  --health-check-protocol http \
  --health-check-port 80 \
  --health-check-path "/health" \
  --health-check-host "www.example.com" \
  --health-check-interval-seconds 10 \
  --threshold-count 3 \
  --user-agent "$GA_USER_AGENT"
```

### Use ProxyProtocol to preserve client IP (TCP listeners only)

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=Ip Endpoint="47.xxx.xxx.xxx" Weight=255 EnableProxyProtocol=true \
  --user-agent "$GA_USER_AGENT"
```

> **Note**: `EnableClientIPPreservation` and `EnableProxyProtocol` cannot both be `true`.

### Parameter reference

| Parameter | Type | Required | Description | Allowed values |
|-----------|------|----------|-------------|----------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` | `cn-hangzhou` |
| AcceleratorId | string | Yes | GA instance ID | - |
| ListenerId | string | Yes | Listener ID | - |
| EndpointGroupRegion | string | Yes | Endpoint group region | e.g. `cn-hangzhou`, `us-west-1` |
| Name | string | No | Endpoint group name | 1~128 characters |
| Description | string | No | Description | Max 200 characters |
| EndpointGroupType | string | No | Endpoint group type | `default` / `virtual` |
| TrafficPercentage | integer | No | Traffic percentage | `1`~`100` |
| HealthCheckEnabled | boolean | No | Whether to enable health checks | `true` / `false` |
| HealthCheckProtocol | string | No | Health check protocol | `tcp` / `http` / `https` |
| HealthCheckPort | integer | No | Health check port | `1`~`65535` |
| HealthCheckPath | string | No | Health check path (http/https only) | e.g. `/`, `/health` |
| HealthCheckHost | string | No | Health check host | - |
| HealthCheckIntervalSeconds | integer | No | Health check interval (seconds) | `1`~`50` |
| ThresholdCount | integer | No | Consecutive threshold count | `2`~`10`, default `3` |
| EndpointIpVersion | string | No | Backend IP protocol | `IPv4` / `IPv6` / `ProtocolAffinity` |

### EndpointConfigurations sub-parameters

| Parameter | Type | Required | Description | Allowed values |
|-----------|------|----------|-------------|----------------|
| EndpointConfigurations.N.Type | string | Yes | Endpoint type | `Ip`/`Domain`/`ECS`/`SLB`/`ALB`/`NLB`/`OSS`/`ENI`/`PublicIp`/`IpTarget` |
| EndpointConfigurations.N.Endpoint | string | Yes | Endpoint address | IP address / domain / instance ID |
| EndpointConfigurations.N.Weight | integer | Yes | Weight | `0`~`255`, `0` pauses forwarding |
| EndpointConfigurations.N.EnableClientIPPreservation | boolean | No | Preserve client IP automatically | `true` / `false` |
| EndpointConfigurations.N.EnableProxyProtocol | boolean | No | Preserve client IP via ProxyProtocol (TCP only) | `true` / `false` |
| EndpointConfigurations.N.EndpointRequestProtocol | string | No | Backend protocol (HTTP/HTTPS listeners only) | `HTTP` / `HTTPS` |
| EndpointConfigurations.N.EndpointProtocolVersion | string | No | Backend protocol version | `HTTP1.1` / `HTTP2` |

### PortOverrides sub-parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| PortOverrides.N.ListenerPort | integer | Listener port |
| PortOverrides.N.EndpointPort | integer | Endpoint port |

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| RequestId | string | Request ID |
| EndpointGroupId | string | Endpoint group ID |

### Error handling

| Error code | Meaning | Resolution |
|------------|---------|------------|
| StateError.Accelerator | GA instance state does not allow the operation | Retry after the instance becomes `active` |
| StateError.Listener | Listener state does not allow the operation | Retry after the listener becomes `active` |
| EndpointGroupOverLimit | Too many endpoint groups | Delete unnecessary endpoint groups |
| EndpointOverLimit | Too many endpoints | Reduce the number of endpoints |
| ClientIPPreservation.Conflict | Client IP preservation conflict | `EnableClientIPPreservation` and `EnableProxyProtocol` cannot both be `true` |

---

## 2. create-endpoint-groups

Create multiple endpoint groups in batches.

Use this to create several endpoint groups under one listener, for example for multi-region backends:

```bash
aliyun ga create-endpoint-groups \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --endpoint-group-configurations '[{"EndpointGroupRegion":"cn-hangzhou","EndpointGroupName":"epg-hangzhou","EndpointGroupType":"default","TrafficPercentage":70,"HealthCheckEnabled":true,"HealthCheckProtocol":"tcp","HealthCheckPort":80,"ThresholdCount":3,"EndpointConfigurations":[{"Type":"Ip","Endpoint":"47.xxx.xxx.1","Weight":255}]},{"EndpointGroupRegion":"us-west-1","EndpointGroupName":"epg-us","EndpointGroupType":"default","TrafficPercentage":30,"HealthCheckEnabled":true,"HealthCheckProtocol":"tcp","HealthCheckPort":80,"ThresholdCount":3,"EndpointConfigurations":[{"Type":"Ip","Endpoint":"47.xxx.xxx.2","Weight":255}]}]' \
  --user-agent "$GA_USER_AGENT"
```

---

## 3. describe-endpoint-group

Query endpoint group details.

```bash
aliyun ga describe-endpoint-group \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --endpoint-group-id "${EPG_ID}"
```

### Extract key fields

```bash
aliyun ga describe-endpoint-group \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    EndpointGroupId,
    Name,
    State,
    EndpointGroupRegion,
    TrafficPercentage,
    HealthCheckEnabled,
    HealthCheckProtocol,
    HealthCheckPort,
    HealthCheckPath,
    EndpointConfigurations: [.EndpointConfigurations[] | {
      Type, Endpoint, Weight, EnableClientIPPreservation
    }],
    PortOverrides
  }'
```

### Poll until the endpoint group is active

```bash
EPG_ID="epg-bp1xxxx"
MAX_WAIT=30
for i in $(seq 1 $MAX_WAIT); do
  STATE=$(aliyun ga describe-endpoint-group \
    --biz-region-id cn-hangzhou \
    --endpoint-group-id "$EPG_ID" \
    --user-agent "$GA_USER_AGENT" | jq -r '.State')

  if [ "$STATE" = "active" ]; then
    echo "Endpoint group is active."
    break
  fi

  echo "Waiting for endpoint group to become active... [$i/$MAX_WAIT] current state: $STATE"
  sleep 10
done
```

### Key response fields

| Field | Type | Description |
|-------|------|-------------|
| EndpointGroupId | string | Endpoint group ID |
| Name | string | Name |
| State | string | State: `init`/`active`/`creating`/`configuring`/`deleting` |
| EndpointGroupRegion | string | Region |
| TrafficPercentage | integer | Traffic percentage |
| HealthCheckEnabled | boolean | Whether health checks are enabled |
| EndpointConfigurations | array | Endpoint configuration list |
| PortOverrides | array | Port override list |

---

## 4. list-endpoint-groups

Query the endpoint group list.

```bash
aliyun ga list-endpoint-groups \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --page-size 50
```

### Format output

```bash
aliyun ga list-endpoint-groups \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" | jq '.EndpointGroups[] | {
    EndpointGroupId,
    Name,
    State,
    EndpointGroupRegion,
    TrafficPercentage,
    HealthCheckEnabled,
    EndpointCount: (.EndpointConfigurations | length)
  }'
```

---

## 5. update-endpoint-group

Modify an endpoint group.

### Replace endpoints (full replacement)

> **Important**: `update-endpoint-group` replaces the entire `EndpointConfigurations` list. Include every endpoint you want to keep.

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations '[{"Type":"Ip","Endpoint":"47.xxx.xxx.1","Weight":255,"EnableClientIPPreservation":true},{"Type":"Ip","Endpoint":"47.xxx.xxx.2","Weight":128,"EnableClientIPPreservation":true}]' \
  --user-agent "$GA_USER_AGENT"
```

### Modify health check configuration

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --health-check-enabled true \
  --health-check-protocol http \
  --health-check-port 8080 \
  --health-check-path "/health" \
  --health-check-interval-seconds 5 \
  --user-agent "$GA_USER_AGENT" \
  --threshold-count 2
```

### Modify traffic percentage

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --traffic-percentage 70
```

### Add port override

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --port-overrides ListenerPort=80 EndpointPort=8080 \
  --user-agent "$GA_USER_AGENT"
```

### Suspend an endpoint (set weight to 0)

```bash
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations '[{"Type":"Ip","Endpoint":"47.xxx.xxx.1","Weight":255},{"Type":"Ip","Endpoint":"47.xxx.xxx.2","Weight":0}]' \
  --user-agent "$GA_USER_AGENT"
```

---

## 6. update-endpoint-group-attribute

Modify only the endpoint group name and description.

```bash
aliyun ga update-endpoint-group-attribute \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --name "${NEW_NAME}" \
  --user-agent "$GA_USER_AGENT" \
  --description "${NEW_DESC}"
```

---

## 7. update-endpoint-groups

Modify multiple endpoint groups in batches.

```bash
aliyun ga update-endpoint-groups \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --endpoint-group-configurations '[{"EndpointGroupId":"'"${EPG_ID_1}"'","TrafficPercentage":60},{"EndpointGroupId":"'"${EPG_ID_2}"'","TrafficPercentage":40}]' \
  --user-agent "$GA_USER_AGENT"
```

---

## 8. Endpoint type quick reference

| Type value | Description | Endpoint format | Use case |
|------------|-------------|-----------------|----------|
| `Ip` | Custom IP | Public/private IP address | General purpose |
| `Domain` | Custom domain | Domain address | Domain backend |
| `ECS` | Alibaba Cloud ECS | ECS instance ID | ECS backend |
| `SLB` | Classic Load Balancer | SLB instance ID | CLB backend |
| `ALB` | Application Load Balancer | ALB instance ID | ALB backend |
| `NLB` | Network Load Balancer | NLB instance ID | NLB backend |
| `OSS` | Object Storage Service | bucket.oss-region.aliyuncs.com | OSS backend |
| `ENI` | Elastic Network Interface | ENI instance ID | ENI backend |
| `PublicIp` | Alibaba Cloud public IP | EIP instance ID | EIP backend |
| `IpTarget` | Private IP in VPC | Private IP (VpcId required) | VPC private backend |

---

## Complete example: create an endpoint group and add endpoints

```bash
#!/bin/bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"

# Step 1: Create an endpoint group (WITHOUT endpoint configurations)
echo "Creating endpoint group..."
EPG_RESULT=$(aliyun ga create-endpoint-group \
  --user-agent "$GA_USER_AGENT" \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --endpoint-group-region cn-hangzhou \
  --name "epg-production" \
  --traffic-percentage 100 \
  --health-check-enabled true \
  --health-check-protocol tcp \
  --health-check-port 80 \
  --health-check-interval-seconds 10 \
  --threshold-count 3)

EPG_ID=$(echo "$EPG_RESULT" | jq -r '.EndpointGroupId')
echo "Endpoint group created: $EPG_ID"

# Step 2: Wait for the endpoint group to become active
echo "Waiting for endpoint group to become active..."
for i in $(seq 1 30); do
  STATE=$(aliyun ga describe-endpoint-group \
    --biz-region-id cn-hangzhou \
    --endpoint-group-id "$EPG_ID" \
    --user-agent "$GA_USER_AGENT" | jq -r '.State')

  if [ "$STATE" = "active" ]; then
    echo "Endpoint group is active."
    break
  fi
  echo "Waiting... [$i/30] state: $STATE"
  sleep 10
done

# Step 2.5 (two-step flow): add endpoints via update-endpoint-group
echo "Adding endpoints..."
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "$EPG_ID" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations Type=Ip Endpoint="47.xxx.xxx.xxx" Weight=255 EnableClientIPPreservation=true \
  --user-agent "$GA_USER_AGENT"

# Step 3: Display endpoint group information
echo ""
echo "=== Endpoint group configuration ==="
aliyun ga describe-endpoint-group \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    EndpointGroupId,
    Name,
    State,
    EndpointGroupRegion,
    TrafficPercentage,
    HealthCheck: {
      Enabled: .HealthCheckEnabled,
      Protocol: .HealthCheckProtocol,
      Port: .HealthCheckPort
    },
    Endpoints: [.EndpointConfigurations[] | {
      Type, Endpoint, Weight
    }]
  }'

# Step 4 (optional): replace endpoint list (include existing endpoints too)
echo ""
echo "Appending second endpoint..."
aliyun ga update-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "$EPG_ID" \
  --endpoint-group-region cn-hangzhou \
  --endpoint-configurations '[{"Type":"Ip","Endpoint":"47.xxx.xxx.xxx","Weight":255,"EnableClientIPPreservation":true},{"Type":"ECS","Endpoint":"'"${ECS_ID}"'","Weight":128,"EnableClientIPPreservation":true}]' \
  --user-agent "$GA_USER_AGENT"

echo "Endpoint configuration complete."
```
