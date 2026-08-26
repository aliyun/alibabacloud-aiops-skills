# CLB (Classic Load Balancer) API Reference and Field Descriptions

> This document defines the OpenAPI interfaces, input parameters, output fields, and business semantics for CLB health check diagnosis. When adding new interfaces or fields, update this document first.

## Instance and Listener Related Interfaces

| Interface | Purpose |
|-----------|---------|
| DescribeLoadBalancerAttribute | Query instance attributes (listener list, default backends) |
| DescribeLoadBalancerListeners | Query all listeners under an instance (some STS roles lack this permission, use as fallback) |
| DescribeLoadBalancerTCPListenerAttribute | Query TCP listener attributes (including health check) |
| DescribeLoadBalancerUDPListenerAttribute | Query UDP listener attributes |
| DescribeLoadBalancerHTTPListenerAttribute | Query HTTP listener attributes |
| DescribeLoadBalancerHTTPSListenerAttribute | Query HTTPS listener attributes |

### Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| RegionId | Yes | Instance region, e.g. `cn-hangzhou` |
| LoadBalancerId | Yes | CLB instance ID, prefix `lb-` |
| ListenerPort | Yes (per protocol interface) | Listener port (1-65535), used to precisely identify a listener |

### Listener Common Field Descriptions

| Field | Description |
|-------|-------------|
| ListenerPort | Listener port (CLB listeners have no independent ListenerId, identified by `protocol_port`) |
| ListenerProtocol / Protocol | Listener protocol: tcp / udp / http / https |
| Status | Listener status: running / stopped |
| VServerGroupId | Associated virtual server group ID (rsp- prefix), mutually exclusive with MasterSlaveServerGroupId |
| MasterSlaveServerGroupId | Associated active/standby server group ID, mutually exclusive with VServerGroupId; both empty means use instance default backends |
| BackendServerPort | Port to which the listener forwards to backends; for HTTP/HTTPS listeners, 0 means pass through client port |
| Bandwidth | Listener bandwidth peak (Mbps), -1 means no throttling |
| Scheduler | Scheduling algorithm: wrr / rr / wlc / sch / tch / qch |
| StickySession | Session persistence toggle (HTTP/HTTPS): on / off |

### Health Check Field Descriptions (Shared by CLB Listener / Rule)

| Field | Description |
|-------|-------------|
| HealthCheck | Health check master toggle: on / off (TCP listeners use `HealthCheck`, HTTP/HTTPS listeners use the same field name) |
| HealthCheckType | Health check type: tcp / http; TCP listeners can be set to http (layer-7 probe) |
| HealthCheckConnectPort | Health check port; 0 means use backend server port |
| HealthCheckURI | Health check URI (required for HTTP/HTTPS) |
| HealthCheckDomain | Health check request Host header |
| HealthCheckMethod | Health check HTTP method: get / head |
| HealthCheckHttpCode | Healthy status code set: http_2xx / http_3xx / http_4xx / http_5xx, comma-separated |
| HealthCheckHttpVersion | Probe request HTTP protocol version: http1.0 / http1.1 |
| HealthCheckConnectTimeout | TCP connection timeout (seconds), used for TCP listeners |
| HealthCheckTimeout | HTTP request timeout (seconds) |
| HealthCheckInterval | Health check interval (seconds) |
| HealthyThreshold | Healthy threshold (consecutive successes to determine healthy) |
| UnhealthyThreshold | Unhealthy threshold (consecutive failures to determine unhealthy) |

### Listener Health Check Example Fields

```json
{
  "VServerGroupId": "rsp-bp1zvupi85frg",
  "ListenerPort": 443,
  "HealthCheckInterval": 2,
  "UnhealthyThreshold": 3,
  "HealthCheckURI": "/",
  "HealthCheck": "on",
  "HealthCheckHttpVersion": "http1.0",
  "HealthCheckTimeout": 5,
  "HealthCheckMethod": "head",
  "HealthyThreshold": 3,
  "HealthCheckDomain": "",
  "HealthCheckHttpCode": "http_2xx,http_3xx",
  "HealthCheckType": "http",
  "ListenerProtocol": "https"
}
```

## Forwarding Rule Related Interfaces

| Interface | Purpose |
|-----------|---------|
| DescribeRules | Query all forwarding rules under a listener |
| DescribeRuleAttribute | Query specified forwarding rule details (including rule-level health check) |

### Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| RegionId | Yes | Region |
| LoadBalancerId | Required for DescribeRules | CLB instance ID |
| ListenerPort | Required for DescribeRules | Associated HTTP/HTTPS listener port |
| RuleId | Required for DescribeRuleAttribute | Rule ID (rule- prefix) |

### Rule Field Descriptions

| Field | Description |
|-------|-------------|
| RuleId | Rule unique ID |
| RuleName | Rule name (user-defined) |
| Domain | Match domain name |
| Url | Match URL path |
| VServerGroupId | Virtual server group associated with the rule (forward to this group on match) |
| ListenerSync | Whether to inherit listener health check config: on (inherit) / off (rule-level independent config) |
| Cookie / CookieTimeout | Rule-level session persistence parameters |

### Forwarding Rule Health Check Example Fields

```json
{
  "HealthCheckHttpCode": "http_3xx",
  "VServerGroupId": "rsp-6cejjzl****",
  "Domain": "www.example.com",
  "HealthCheckInterval": 5,
  "Url": "/cache",
  "HealthCheckURI": "/example",
  "RuleName": "Rule2",
  "RuleId": "rule-tybqi6****",
  "HealthCheckConnectPort": 45,
  "HealthCheckTimeout": 34,
  "HealthyThreshold": 5,
  "HealthCheckDomain": "www.example.com",
  "UnhealthyThreshold": 2,
  "HealthCheck": "off"
}
```

## Server Group Related Interfaces

| Interface | Purpose |
|-----------|---------|
| DescribeVServerGroups | List all virtual server groups under an instance |
| DescribeVServerGroupAttribute | Query virtual server group attributes and backend servers |
| DescribeMasterSlaveServerGroups | List all active/standby server groups under an instance |
| DescribeMasterSlaveServerGroupAttribute | Query active/standby server group attributes |
| DescribeHealthStatus | Query health status of all backend servers under a listener (including server groups referenced by rules) |

### Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| RegionId | Yes | Region |
| LoadBalancerId | Required for DescribeHealthStatus | CLB instance ID |
| ListenerPort | Optional for DescribeHealthStatus | Specify listener port; omit to return all listeners of the instance |
| VServerGroupId | Required for DescribeVServerGroupAttribute | Virtual server group ID |
| MasterSlaveServerGroupId | Required for DescribeMasterSlaveServerGroupAttribute | Active/standby server group ID |

### Backend Server Field Descriptions

| Field | Description |
|-------|-------------|
| ServerId | Backend server ID (i- prefix, ECS instance ID) |
| Type / ServerType | Backend type: ecs / eni / eci |
| ServerIp | Backend private IP (not returned by some interfaces) |
| Port | Backend service port; 0 means listener pass-through |
| Weight | Forwarding weight (0-100), 0 means stop forwarding |
| Description | Description |
| ServerHealthStatus | Health status: normal / abnormal / unavailable (CLB specific) |

### Backend Server Example Fields

```json
{
  "Type": "ecs",
  "Weight": 100,
  "Description": "The description of the server group.",
  "ServerIp": "192.XX.XX.11",
  "Port": 90,
  "ServerId": "vm-233"
}
```

## CLB Status Translation

| Original Value | Translation |
|----------------|-------------|
| normal | Normal (health check passed) |
| abnormal | Abnormal (health check failed) |
| unavailable | Unavailable (health check not enabled or no backend port) |
