# ALB (Application Load Balancer) API Reference and Field Descriptions

> This document defines the OpenAPI interfaces, input parameters, output fields, and business semantics for ALB health check diagnosis. When adding new interfaces or fields, update this document first.

## Interface List

| Interface | Purpose |
|-----------|---------|
| ListLoadBalancers | Query instance attributes (including ZoneMappings / VpcId) |
| ListListeners | Query all listeners under an instance |
| GetListenerHealthStatus | Query listener health status (including NonNormalServers) |
| GetListenerAttribute | Query listener attributes (including default actions) |
| ListRules | Query all forwarding rules under a listener |
| ListServerGroups | Query server group health check configuration |
| ListServerGroupServers | Query backend servers in a server group |

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| RegionId | Yes | Region |
| LoadBalancerIds | ListLoadBalancers / ListListeners | ALB instance ID, prefix `alb-`, list |
| ListenerIds | ListListeners / GetListenerAttribute / GetListenerHealthStatus | Listener ID, prefix `lsn-` |
| ServerGroupIds | ListServerGroups / ListServerGroupServers | Server group ID, prefix `sgp-` |

## Listener Field Descriptions

| Field | Description |
|-------|-------------|
| ListenerId | Listener unique ID |
| ListenerProtocol | Listener protocol: HTTP / HTTPS / QUIC |
| ListenerPort | Listener port |
| ListenerStatus | Listener status: Provisioning / Running / Configuring / Stopped |
| DefaultActions | Listener default action list (executed when no rule matches); same structure as RuleActions |
| LoadBalancerId | Parent ALB instance ID |
| SecurityPolicyId | HTTPS security policy ID |
| Http2Enabled | HTTP/2 toggle (HTTPS) |
| GzipEnabled | GZIP compression toggle |
| IdleTimeout / RequestTimeout | Idle timeout / Request timeout (seconds) |

### Listener Example Fields

```json
{
  "ListenerPort": 443,
  "ServerGroupId": "sgp-64de7qxq74tp8050sc",
  "LoadBalancerId": "alb-3g2ewztmplonwpd46q",
  "ListenerId": "lsn-hh4x7qugsnp9yjqcgu"
}
```

## Forwarding Rule Field Descriptions

| Field | Description |
|-------|-------------|
| RuleId | Rule unique ID |
| RuleName | Rule name |
| Priority | Priority (1-10000, lower value means higher priority) |
| Direction | Rule direction: Request / Response |
| RuleConditions | Rule match condition list, classified by `Type` |
| RuleActions | Rule action list, classified by `Type` |
| ListenerId | Parent listener |

### RuleConditions Types

| Type | Description |
|------|-------------|
| Host | Match domain name (HostConfig.Values) |
| Path | Match path (PathConfig.Values) |
| Method | Match HTTP method (MethodConfig.Values) |
| QueryString | Match QueryString key-value pairs (QueryStringConfig.Values) |
| Header | Match request header (HeaderConfig.Key + Values) |
| Cookie | Match Cookie (CookieConfig.Values) |
| SourceIp | Match client IP (SourceIpConfig.Values, CIDR supported) |
| ResponseStatusCode | Match response status code (response direction rules) |
| ResponseHeader | Match response header (response direction rules) |

### RuleActions Types

| Type | Key Configuration | Description |
|------|-------------------|-------------|
| ForwardGroup | ForwardGroupConfig.ServerGroupTuples[{ServerGroupId, Weight}] | Forward to server groups (supports weighted multi-group) |
| Redirect | RedirectConfig(Protocol/Host/Port/Path/Query/HttpCode) | URL redirect (301/302/303/307/308) |
| FixedResponse | FixedResponseConfig(HttpCode/ContentType/Content) | Return fixed response |
| InsertHeader | InsertHeaderConfig(Key/Value/ValueType/CoverEnabled) | Insert request or response header |
| RemoveHeader | RemoveHeaderConfig(Key) | Remove specified header |
| Rewrite | RewriteConfig(Host/Path/Query) | URL rewrite |
| TrafficLimit | TrafficLimitConfig(QPS/PerIpQps) | Traffic throttling |
| TrafficMirror | TrafficMirrorConfig(TargetType/MirrorGroupConfig) | Traffic mirroring |
| Cors | CorsConfig(AllowOrigin/AllowMethods etc.) | Cross-origin response header injection |

## Health Status Field Descriptions

| Field | Description |
|-------|-------------|
| ListenerHealthStatus[] | Returned per listener |
| ListenerHealthStatus[].ServerGroupInfos[] | All server groups referenced by the listener (including default action and forwarding rule action references) |
| ServerGroupInfos[].HealthCheckEnabled | Server group health check toggle: on / off |
| ServerGroupInfos[].ActionType | Usage action of this server group on the listener: ForwardGroup / TrafficMirror etc. |
| ServerGroupInfos[].NonNormalServers[] | Abnormal backend list, same structure as NLB |
| NonNormalServers[].Reason.ReasonCode | Abnormal reason code: CONNECT_TIMEOUT / CONNECT_REFUSED / RESPONSE_TIMEOUT / RESPONSE_MISMATCH / SSL_HANDSHAKE_ERROR etc. |
| NonNormalServers[].Reason.ActualResponse / ExpectedResponse | Actual/Expected response (populated when RESPONSE_MISMATCH) |

### Health Status Example Fields

```json
{
  "ListenerHealthStatus": [
    {
      "ListenerId": "lsn-o4u54y73wq7b******",
      "ListenerPort": 80,
      "ListenerProtocol": "http",
      "ServerGroupInfos": [
        {
          "HealthCheckEnabled": "on",
          "NonNormalServers": [
            {
              "Port": 90,
              "Reason": {
                "ActualResponse": "302",
                "ExpectedResponse": "HTTP_2xx",
                "ReasonCode": "RESPONSE_MISMATCH"
              },
              "ServerId": "i-uf62h8v******",
              "ServerIp": "192.168.8.10",
              "Status": "Initial"
            }
          ],
          "ServerGroupId": "sgp-8ilqs4axp6******",
          "ActionType": "TrafficMirror"
        }
      ]
    }
  ]
}
```

### Forwarding Rule Example Fields

```json
{
  "RuleActions": [
    {
      "Type": "ForwardGroup",
      "ServerGroupId": "sgp-64de7qxq74tp8050sc",
      "Weight": 100
    }
  ],
  "RuleId": "rule-ptc53zdcrwr3qkbspt",
  "LoadBalancerId": "alb-3g2ewztmplonwpd46q",
  "ListenerId": "lsn-jberplwadvab6oyf4h"
}
```

## Server Group Health Check Field Descriptions

| Field | Description |
|-------|-------------|
| HealthCheckEnabled | Health check toggle |
| HealthCheckProtocol | Probe protocol: HTTP / HTTPS / TCP / GRPC |
| HealthCheckConnectPort | Probe port; 0 means use backend port |
| HealthCheckHost | Probe Host header |
| HealthCheckPath | Probe URI |
| HealthCheckMethod | HTTP method: GET / HEAD / POST |
| HealthCheckCodes | Expected status codes: http_2xx / http_3xx / http_4xx / http_5xx |
| HealthCheckHttpVersion | HTTP protocol version: HTTP1.0 / HTTP1.1 |
| HealthCheckInterval | Probe interval (seconds) |
| HealthCheckTimeout | Probe timeout (seconds) |
| HealthyThreshold / UnhealthyThreshold | Healthy / Unhealthy threshold |
| Protocol | Forwarding protocol between server group and backend: HTTP / HTTPS / GRPC |
| ServerGroupName | Server group name (user-defined) |
| ServerCount | Number of backend servers |
| ScheduleAlgorithm | Scheduling algorithm: Wrr / Wlc / Sch |

### Server Group Health Check Example Fields

```json
{
  "HealthCheckConfig": {
    "HealthCheckConnectPort": 80,
    "HealthCheckEnabled": true,
    "HealthCheckHost": "www.example.com",
    "HealthCheckCodes": ["http_2xx"],
    "HealthCheckHttpVersion": "HTTP1.1",
    "HealthCheckInterval": 5,
    "HealthCheckMethod": "HEAD",
    "HealthCheckPath": "/test/index.html",
    "HealthCheckProtocol": "HTTP",
    "HealthCheckTimeout": 3,
    "HealthyThreshold": 4,
    "UnhealthyThreshold": 4
  },
  "Protocol": "HTTP",
  "RelatedLoadBalancerIds": ["alb-n5qw04uq8savfe****"],
  "ServerGroupId": "sgp-cige6j****",
  "ServerGroupName": "Group3",
  "VpcId": "vpc-bp15zckdt37pq72zv****",
  "Ipv6Enabled": false,
  "ServerCount": 1,
  "ServiceName": "test"
}
```

## Backend Server Field Descriptions

| Field | Description |
|-------|-------------|
| ServerId | Backend server ID |
| ServerType | Backend type: Ecs / Eni / Eci / Ip / Fc (Function Compute) |
| ServerIp | Backend private IP |
| Port | Backend service port |
| Weight | Weight (0-100), 0 means no forwarding |
| ServerGroupId | Parent server group |
| Description | Description |
| ZoneId | Availability zone of the backend |
| Status | Server group dimension health status: Available / Unavailable / Initial / Configuring / Removing |

### Backend Server Example Fields

```json
{
  "ServerId": "i-bp67acfmxazb4p****",
  "ServerType": "Ecs",
  "ServerIp": "192.168.2.1",
  "Port": 80,
  "ServerGroupId": "sgp-atstuj3rtoptyui****",
  "Description": "ECS",
  "ZoneId": "cn-hangzhou-a",
  "Status": "Available"
}
```

## ALB Status Translation

| Original Value | Translation |
|----------------|-------------|
| Available | Available (health check passed) |
| Unavailable | Unavailable (health check failed) |
| Initial | Initializing |
| Configuring | Configuring |
| Removing | Removing |
