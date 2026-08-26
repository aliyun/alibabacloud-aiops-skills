# NLB (Network Load Balancer) API Reference and Field Descriptions

> This document defines the OpenAPI interfaces, input parameters, output fields, and business semantics for NLB health check diagnosis. When adding new interfaces or fields, update this document first.

## Interface List

| Interface | Purpose |
|-----------|---------|
| GetLoadBalancerAttribute | Query NLB instance attributes (including ZoneMappings, vSwitchId) |
| ListListeners | Query all listeners under an instance |
| GetListenerHealthStatus | Query listener health status (including NonNormalServers) |
| GetListenerAttribute | Query listener attributes |
| ListServerGroups | Query server group health check configuration |
| ListServerGroupServers | Query backend servers in a server group |

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| RegionId | Yes | Region |
| LoadBalancerIds | ListListeners / GetLoadBalancerAttribute | NLB instance ID, prefix `nlb-`, list format |
| ListenerIds | ListListeners / GetListenerHealthStatus | Listener ID, prefix `lsn-` |
| ServerGroupIds | ListServerGroups / ListServerGroupServers | Server group ID, prefix `sgp-` |

## Listener Field Descriptions

| Field | Description |
|-------|-------------|
| ListenerId | Listener unique ID (lsn- prefix) |
| ListenerProtocol | Listener protocol: TCP / UDP / TCPSSL |
| ListenerPort | Listener port (1-65535) |
| ServerGroupId | Server group ID directly associated with the listener (NLB has no forwarding rules) |
| ListenerStatus | Listener status: Provisioning / Running / Configuring / Stopped |
| LoadBalancerId | Parent NLB instance ID |
| AlpnEnabled / AlpnPolicy | ALPN protocol toggle and policy (TCPSSL) |
| ProxyProtocolEnabled | Whether Proxy Protocol is enabled (preserves client IP) |
| IdleTimeout | Connection idle timeout (seconds) |

### Listener Example Fields

```json
{
  "LoadBalancerId": "nlb-83ckzc8d4xlp8o****",
  "ListenerId": "lsn-ga6sjjcll6ou34l1et****",
  "ListenerProtocol": "TCPSSL",
  "ListenerPort": 443,
  "ServerGroupId": "sgp-ppdpc14gdm3x4o****"
}
```

## Health Status Field Descriptions

| Field | Description |
|-------|-------------|
| HeathCheckEnabled | Whether server group health check is enabled (API field name has a typo, use as-is) |
| ServerGroupId | Server group ID |
| NonNormalServers | List of backend servers with status other than Available; empty means all healthy |
| NonNormalServers[].Status | Server abnormal status: Initial / Configuring / Unavailable / Removing |
| NonNormalServers[].Port | Abnormal backend port |
| NonNormalServers[].Reason.ReasonCode | Abnormal reason code: CONNECT_TIMEOUT / CONNECT_REFUSED / RESPONSE_TIMEOUT / RESPONSE_MISMATCH etc. |
| NonNormalServers[].ServerId | Abnormal backend ECS/ENI ID |
| NonNormalServers[].ServerIp | Abnormal backend private IP |

### Health Status Example Fields

```json
{
  "HeathCheckEnabled": true,
  "ServerGroupId": "sgp-ppdpc14gdm3x4o****",
  "NonNormalServers": [
    {
      "Status": "Initial",
      "Port": 80,
      "Reason": {
        "ReasonCode": "CONNECT_TIMEOUT"
      },
      "ServerId": "i-bp1bt75jaujl7tjl****",
      "ServerIp": "192.168.8.10"
    }
  ]
}
```

## Server Group Health Check Field Descriptions

| Field | Description |
|-------|-------------|
| HealthCheckEnabled | Health check master toggle |
| HealthCheckType | Probe protocol: TCP / UDP / HTTP / HTTPS / GRPC |
| HealthCheckConnectPort | Probe port (0-65535); 0 means use backend server port |
| HealthCheckConnectTimeout | Probe connection timeout (seconds) |
| HealthCheckInterval | Probe interval (seconds) |
| HealthyThreshold | Healthy threshold (consecutive successes) |
| UnhealthyThreshold | Unhealthy threshold (consecutive failures) |
| HealthCheckDomain | HTTP probe Host header; `$SERVER_IP` means use backend IP |
| HealthCheckUrl | HTTP probe URI |
| HealthCheckHttpCode | Expected healthy status code list (http_2xx etc.) |
| HttpCheckMethod | HTTP method: GET / HEAD |
| HealthCheckReq / HealthCheckExp | UDP probe request string and expected response |
| HealthCheckHttpVersion | HTTP probe HTTP protocol version |

### Server Group Health Check Example Fields

```json
{
  "HealthCheckEnabled": false,
  "HealthCheckType": "TCP",
  "HealthCheckConnectPort": 200,
  "HealthyThreshold": 2,
  "UnhealthyThreshold": 3,
  "HealthCheckConnectTimeout": 200,
  "HealthCheckInterval": 10,
  "HealthCheckDomain": "$SERVER_IP",
  "HealthCheckUrl": "/test/index.html",
  "HealthCheckHttpCode": ["http_2xx"],
  "HttpCheckMethod": "GET",
  "HealthCheckReq": "hello",
  "HealthCheckExp": "ok",
  "HealthCheckHttpVersion": "HTTP1.0"
}
```

## Backend Server Field Descriptions

| Field | Description |
|-------|-------------|
| ServerId | Backend server ID (ECS i- / ENI eni- prefix) |
| ServerType | Backend type: Ecs / Eni / Eci / Ip |
| ServerIp | Backend private IP |
| Port | Backend service port |
| Weight | Forwarding weight (0-100), 0 means stop forwarding |
| Status | Server group dimension health status: Available / Unavailable / Initial / Configuring / Removing |
| ServerGroupId | Parent server group |
| RemoteIpEnabled | Whether client IP pass-through is enabled |

### Backend Server Example Fields

```json
{
  "Port": 80,
  "ServerId": "i-bp1f9kdprbgy9uiu****",
  "ServerIp": "192.168.XX.XX",
  "ServerType": "Ecs",
  "Status": "Available",
  "Weight": 100,
  "ServerGroupId": "sgp-qy042e1jabmprh****",
  "RemoteIpEnabled": true
}
```

## NLB Status Translation

| Original Value | Translation |
|----------------|-------------|
| Available | Available (health check passed) |
| Unavailable | Unavailable (health check failed) |
| Initial | Initializing |
| Configuring | Configuring |
| Removing | Removing |
