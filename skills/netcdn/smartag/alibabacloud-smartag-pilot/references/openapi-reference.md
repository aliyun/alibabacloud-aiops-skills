# SAG OpenAPI Reference

Complete parameter reference for SAG Pilot v1.0 APIs.

## CLI Convention

All CLI examples below use the **plugin mode** (requires aliyun CLI >= 3.3.3 with smartag plugin installed).

```bash
aliyun smartag <api-name-in-kebab-case> \
  --endpoint smartag.<RegionId>.aliyuncs.com \
  --biz-region-id <RegionId> \
  --read-timeout 30 \
  --connect-timeout 15 \
  [--params ...]
```

**IMPORTANT**: In plugin mode, must use `--endpoint` (not `--region`) for endpoint routing:
- `--endpoint smartag.<RegionId>.aliyuncs.com` = controls which regional endpoint the request is routed to (REQUIRED)
- `--biz-region-id` = API business parameter (RegionId)
- The plugin's `--region` flag has an incomplete mapping (eu-west-1, us-east-1, cn-zhangjiakou-spe are NOT recognized and will fallback to cn-hangzhou)
- Without `--endpoint`, all requests default to the CLI profile's region

### Parameter Naming

| Parameter | Plugin Mode | Notes |
|-----------|-------------|-------|
| Endpoint | `--endpoint smartag.<r>.aliyuncs.com` | Controls regional routing (REQUIRED) |
| RegionId | `--biz-region-id` | Business region parameter |
| SmartAGId | `--smart-ag-id` | Instance ID |
| SmartAGSn | `--smart-ag-sn` | Device serial number |
| PageSize | `--page-size` | Pagination |
| PageNumber | `--page-number` | Pagination |
| SagId | `--sag-id` | DNAT entries only |
| Size | `--size` | TopN queries |

## Common Parameters

All APIs require:
- **RegionId** (String, Required): Region of the SAG instance
- To get all supported regions, call `describe-regions` (see Region Endpoint Reference section below)

## Configuration Query APIs

### describe-smart-access-gateways

List SAG instances with filtering.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-smart-access-gateways \
  --biz-region-id cn-shanghai \
  --page-size 50 \
  --page-number 1 \
  --smart-ag-id sag-xxxxx \
  --status Active
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| RegionId | String | Yes | Region ID |
| SmartAGId | String | No | Filter by instance ID |
| Name | String | No | Filter by name (fuzzy match) |
| Status | String | No | Filter: Active, Offline, Ordered, Creating |
| AssociatedCcnId | String | No | Filter by CCN binding |
| PageSize | Integer | No | 1-50, default 10 |
| PageNumber | Integer | No | Default 1 |

**Key Response Fields**:
- `SmartAccessGateways[].SmartAGId` - Instance ID
- `SmartAccessGateways[].Name` - Instance name
- `SmartAccessGateways[].Status` - Active/Offline/Ordered
- `SmartAccessGateways[].MaxBandwidth` - Bandwidth in Mbps
- `SmartAccessGateways[].EndTime` - Expiry timestamp (ms)
- `SmartAccessGateways[].AssociatedCcnId` - Bound CCN ID
- `SmartAccessGateways[].CidrBlock` - Private CIDR
- `SmartAccessGateways[].Devices[].SerialNumber` - Device SN
- `SmartAccessGateways[].Devices[].HaState` - HA role

---

### describe-smart-access-gateway-attribute

Get detailed attributes of a single SAG instance.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-smart-access-gateway-attribute \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| RegionId | String | Yes | Region ID |
| SmartAGId | String | Yes | SAG instance ID |

**Key Response Fields**:
- `VpnStatus` - VPN tunnel status (UP/DOWN)
- `ResellerId` - Reseller ID if applicable
- `BoxControllerIp` - Controller IP
- `AccessPointId` - POP access point
- `RoutingStrategy` - Routing strategy

---

### describe-sag-device-info

Get device hardware information.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-device-info \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sagxxxxxxxxxx
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| SmartAGId | String | Yes | SAG instance ID |
| SmartAGSn | String | Yes | Device serial number |

**Key Response Fields**:
- `SmartAGType` - Device model (SAG-1000, SAG-100WM, etc.)
- `Version` - Current software version
- `ControllerState` - Controller connection state
- `VpnState` - VPN state
- `ResettableStatus` - Whether device can be reset

---

### describe-smart-access-gateway-versions

Get software version info.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-smart-access-gateway-versions \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sagxxxxxxxxxx \
  --version-type Device
```

**Key Response Fields**:
- `SmartAGVersions[].CurrentVersion` - Current version
- `SmartAGVersions[].LatestVersion` - Latest available version
- `SmartAGVersions[].CreateTime` - Version release time

---

### describe-sag-wan-list

Get WAN port configurations.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-wan-list \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sagxxxxxxxxxx
```

**Key Response Fields**:
- `TaskStates[].WanInterfaces[].PortName` - Port name (eth0, etc.)
- `TaskStates[].WanInterfaces[].IPType` - DHCP/Static/PPPoE
- `TaskStates[].WanInterfaces[].IP` - WAN IP
- `TaskStates[].WanInterfaces[].Mask` - Subnet mask
- `TaskStates[].WanInterfaces[].Gateway` - Gateway IP

---

### describe-sag-wan-4g

Get 4G WAN card status.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-wan-4g \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sagxxxxxxxxxx
```

**Key Response Fields**:
- `Strength` - Signal strength
- `IP` - 4G assigned IP
- `Status` - Connection status
- `TrafficState` - Traffic state

---

### describe-sag-static-route-list

Get static route configurations.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-static-route-list \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sagxxxxxxxxxx
```

**Key Response Fields**:
- `StaticRoutes[].DestinationCidr` - Destination CIDR
- `StaticRoutes[].NextHop` - Next hop IP
- `StaticRoutes[].PortName` - Outgoing port

---

### describe-sag-route-protocol-bgp

Get BGP protocol configuration.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-route-protocol-bgp \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sagxxxxxxxxxx
```

**Key Response Fields**:
- `RouterId` - BGP Router ID
- `LocalAs` - Local AS number
- `HoldTime` - Hold timer
- `KeepAlive` - Keepalive interval
- `TaskStates[].Neighbors[]` - BGP neighbors

---

### describe-sag-route-protocol-ospf

Get OSPF protocol configuration.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-route-protocol-ospf \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sagxxxxxxxxxx
```

**Key Response Fields**:
- `RouterId` - OSPF Router ID
- `AreaId` - OSPF Area
- `DeadTime` - Dead interval
- `HelloTime` - Hello interval
- `TaskStates[].AdvertiseRoutes[]` - Advertised routes

---

### describe-cloud-connect-networks

Get CCN (Cloud Connect Network) instances.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-cloud-connect-networks \
  --biz-region-id cn-shanghai \
  --ccn-id ccn-xxxxx \
  --page-size 50
```

**Key Response Fields**:
- `CloudConnectNetworks[].CcnId` - CCN ID
- `CloudConnectNetworks[].Name` - CCN name
- `CloudConnectNetworks[].AssociatedCenId` - Bound CEN ID
- `CloudConnectNetworks[].SnatCidrBlock` - SNAT CIDR
- `CloudConnectNetworks[].CidrBlock` - CCN CIDR

---

### describe-grant-sag-rules

Get cross-account CEN authorization rules.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-grant-sag-rules \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx
```

**Key Response Fields**:
- `GrantRules[].CenUid` - Authorized CEN owner UID
- `GrantRules[].CenInstanceId` - CEN instance ID
- `GrantRules[].SmartAGId` - SAG instance
- `GrantRules[].CreateTime` - Authorization time

---

### describe-acls

Get ACL instances.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-acls \
  --biz-region-id cn-shanghai \
  --acl-ids '["acl-xxxxx"]' \
  --page-size 50
```

**Key Response Fields**:
- `Acls[].AclId` - ACL ID
- `Acls[].AclName` - ACL name
- `Acls[].SagCount` - Number of bound SAG instances

---

### describe-qoses

Get QoS policy instances.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-qoses \
  --biz-region-id cn-shanghai \
  --qos-ids '["qos-xxxxx"]'
```

**Key Response Fields**:
- `QosPolicies[].QosId` - QoS ID
- `QosPolicies[].QosName` - Name
- `QosPolicies[].SagCount` - Bound SAG count

---

### describe-dnat-entries / describe-snat-entries

Get NAT rules.

**⚠️ PARAMETER NAME DIFFERENCE**: `describe-dnat-entries` uses `--sag-id` (NOT `--smart-ag-id`). This is inconsistent with other SAG APIs. `describe-snat-entries` uses standard `--smart-ag-id`.

**CLI (plugin mode)**:
```bash
# DNAT - Note: parameter is --sag-id, NOT --smart-ag-id
aliyun smartag describe-dnat-entries \
  --biz-region-id cn-shanghai \
  --sag-id sag-xxxxx \
  --page-size 50

# SNAT - uses standard --smart-ag-id
aliyun smartag describe-snat-entries \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --page-size 50
```

**Parameters (describe-dnat-entries)**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| RegionId | String | Yes | Region ID |
| SagId | String | Yes | SAG instance ID (--sag-id in plugin mode) |
| PageSize | Integer | No | Default 10 |

**Parameters (describe-snat-entries)**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| RegionId | String | Yes | Region ID |
| SmartAGId | String | Yes | SAG instance ID |
| PageSize | Integer | No | Default 10 |

**Key Response Fields (DNAT)**:
- `DnatEntries[].ExternalIp` / `ExternalPort`
- `DnatEntries[].InternalIp` / `InternalPort`
- `DnatEntries[].IpProtocol` - tcp/udp

---

### describe-flow-logs

Get flow log configurations.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-flow-logs \
  --biz-region-id cn-shanghai \
  --flow-log-id fl-xxxxx
```

**Key Response Fields**:
- `FlowLogs[].FlowLogId` - Flow log ID
- `FlowLogs[].Status` - Active/Inactive
- `FlowLogs[].ProjectName` - SLS project
- `FlowLogs[].LogStoreName` - SLS logstore
- `FlowLogs[].SmartAGId` - Bound SAG

---

### describe-health-checks

Get health check configurations.

**⚠️ Note**: This API has been observed to return `InvalidApi.NotFound` in the 2018-03-13 version in some regions (tested 2026-05). If encountered, skip this check gracefully and note in report. This may be resolved in future versions.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-health-checks \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx
```

**Key Response Fields**:
- `HealthChecks[].HcInstanceId` - Health check ID
- `HealthChecks[].Name` - Name
- `HealthChecks[].DstIpAddr` - Probe target IP
- `HealthChecks[].ProbeInterval` - Interval (seconds)
- `HealthChecks[].FailCountThreshold` - Failure threshold
- `HealthChecks[].Status` - ok/failed

---

### describe-smart-access-gateway-client-users

Get SAG APP client users.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-smart-access-gateway-client-users \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --page-size 50
```

**Key Response Fields**:
- `Users[].UserName` - Username (email)
- `Users[].State` - 0=normal, 1=disabled
- `Users[].Bandwidth` - Allocated bandwidth (Kbps)
- `Users[].ClientIp` - Assigned IP

---

### describe-sag-online-client-statistics

Get online client statistics.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-online-client-statistics \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx
```

**Key Response Fields**:
- `SagStatistics[].OnlineCount` - Current online users
- `SagStatistics[].SmartAGId` - SAG instance

---

### describe-sag-current-dns

Get current DNS configuration.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-current-dns \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sagxxxxxxxxxx
```

**Key Response Fields**:
- `MasterDns` - Primary DNS
- `SlaveDns` - Secondary DNS

---

## Inspection-Specific APIs

### describe-smart-access-gateway-ha

Get HA (High Availability) status.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-smart-access-gateway-ha \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx
```

**Key Response Fields**:
- `DeviceLevelBackupState` - Device-level HA state
- `LinkBackupInfoList[].MainLinkId` - Primary link
- `LinkBackupInfoList[].BackupLinkId` - Backup link
- `LinkBackupInfoList[].MainLinkState` - Primary state
- `LinkBackupInfoList[].BackupLinkState` - Backup state

---

### describe-sag-traffic-topn

Get traffic top-N statistics.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-traffic-topn \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --size 10
```

**Key Response Fields**:
- `TrafficTopN[].InstanceId` - Instance
- `TrafficTopN[].TrafficRate` - Current rate (bps)
- `TrafficTopN[].Name` - Instance name

---

### describe-sag-drop-topn

Get packet drop top-N statistics.

**CLI (plugin mode)**:
```bash
aliyun smartag describe-sag-drop-topn \
  --biz-region-id cn-shanghai \
  --size 10
```

**Key Response Fields**:
- `DropTopN[].InstanceId` - Instance
- `DropTopN[].DropRate` - Drop rate percentage
- `DropTopN[].Name` - Instance name

---

## Region Endpoint Reference

**IMPORTANT**: Do NOT rely on this static table for "query all regions" scenarios. Always call `describe-regions` first to get the authoritative, up-to-date list.

### describe-regions

```bash
aliyun smartag describe-regions \
  --endpoint smartag.cn-shanghai.aliyuncs.com \
  --read-timeout 30 \
  --connect-timeout 15
```

Returns an array of `{ RegionId, LocalName, RegionEndpoint }` for all SAG-supported regions.

### Known Regions (for reference only, may be outdated)

| Region | RegionId | Endpoint |
|--------|----------|----------|
| 华东2（上海） | cn-shanghai | smartag.cn-shanghai.aliyuncs.com |
| 中国香港 | cn-hongkong | smartag.cn-hongkong.aliyuncs.com |
| 新加坡 | ap-southeast-1 | smartag.ap-southeast-1.aliyuncs.com |
| 马来西亚（吉隆坡） | ap-southeast-3 | smartag.ap-southeast-3.aliyuncs.com |
| 印度尼西亚（雅加达） | ap-southeast-5 | smartag.ap-southeast-5.aliyuncs.com |
| 日本（东京） | ap-northeast-1 | smartag.ap-northeast-1.aliyuncs.com |
| 德国（法兰克福） | eu-central-1 | smartag.eu-central-1.aliyuncs.com |
| 英国（伦敦） | eu-west-1 | smartag.eu-west-1.aliyuncs.com |
| 美国（弗吉尼亚） | us-east-1 | smartag.us-east-1.aliyuncs.com |
| 张北SPE | cn-zhangjiakou-spe | smartag.cn-zhangjiakou-spe.aliyuncs.com |

---

## Response Structure Notes (Fault Tolerance)

SAG API responses have **inconsistent list wrapping**. When parsing responses, MUST handle all of the following patterns:

### Pattern 1: Standard nested structure (most common)

```json
{
  "Wans": {
    "Wan": [
      {"PortName": "1", "IP": "192.168.1.1"},
      {"PortName": "2", "IP": "192.168.2.1"}
    ]
  }
}
```

### Pattern 2: Single item not wrapped in array

When only one item exists, it may be returned as a dict instead of a single-element array:

```json
{
  "Wans": {
    "Wan": {"PortName": "1", "IP": "192.168.1.1"}
  }
}
```

### Pattern 3: Container is directly a list

Rarely, the intermediate container may be a list instead of a dict:

```json
{
  "Wans": [
    {"PortName": "1", "IP": "192.168.1.1"}
  ]
}
```

### Recommended Parsing Pattern

Always use this defensive extraction pattern when parsing list data from SAG API responses:

```python
def safe_extract_list(data, container_key, item_key):
    """
    Safely extract a list from SAG API response.
    Handles all known response structure variations.
    
    Example: safe_extract_list(response, "Wans", "Wan")
    """
    if not isinstance(data, dict):
        return []
    
    container = data.get(container_key, {})
    
    # Pattern 3: container is directly a list
    if isinstance(container, list):
        return container
    
    # Pattern 1 & 2: container is a dict with item_key
    if isinstance(container, dict):
        items = container.get(item_key, [])
        # Pattern 2: single item as dict
        if isinstance(items, dict):
            return [items]
        # Pattern 1: normal list
        if isinstance(items, list):
            return items
    
    return []
```

### Known Parameter Name Inconsistencies

| API (plugin mode) | Parameter | Notes |
|-------------------|-----------|-------|
| describe-dnat-entries | --sag-id | Only this API uses --sag-id (NOT --smart-ag-id) |
| describe-snat-entries | --smart-ag-id | Standard naming |
| describe-sag-wan-list | --smart-ag-sn | Requires device SN |
| describe-sag-current-dns | --smart-ag-sn | Requires device SN |

### Common Error Codes Reference

| Error Code | Meaning | Recommended Handling |
|-----------|---------|---------------------|
| MissingSmartAGSn | Device SN not provided | Skip - instance has no physical device |
| SmartAccessGatewayNotOnline | Device offline | Record status, cannot query live config |
| Sag.DeviceNotExist | SN doesn't match any device | Check if multi-SN needs splitting |
| InstanceNotExit | Instance or device not found | May be a multi-SN issue (see below) |
| InvalidApi.NotFound | API may not exist in current version | Skip gracefully, note in report |
| MissingSagId | describe-dnat-entries needs --sag-id | Use --sag-id instead of --smart-ag-id |

### Multi-SN Device Handling

Some SAG instances have HA (dual device) configuration. The `SerialNumber` field contains comma-separated SNs:

```
SerialNumber: "sag61dacczh,sag61daccq6"
```

**MUST split and query individually**:
```python
sn_field = instance.get("SerialNumber", "")
sn_list = [s.strip() for s in sn_field.split(",") if s.strip()]

# Query each device separately
for idx, sn in enumerate(sn_list):
    role = "主设备" if idx == 0 else "备设备"
    device_info = run_cli("describe-sag-device-info", smart_ag_sn=sn)
    wan_config = run_cli("describe-sag-wan-list", smart_ag_sn=sn)
    # ... other device-level queries
```

Passing the full comma-separated string will return `Sag.DeviceNotExist` or `InstanceNotExit`.

### Response Field Format Quirks

SAG API 的部分响应字段返回值格式不符合直觉，直接拼接展示会导致显示异常。**在生成报告或脚本时，必须对以下字段做规范化处理**：

| API | 字段 | 实际返回值格式 | 常见误用 | 正确处理 |
|-----|------|--------------|---------|---------|
| describe-smart-access-gateway-attribute | `MaxBandwidth` | 带单位后缀的字符串，如 `"10M"`, `"2M"`, `"0M"` | 直接拼接 "Mbps" 导致 "10MMbps" | 先 strip 末尾的 "M" 再拼接单位 |
| describe-smart-access-gateway-attribute | `EndTime` | 毫秒级 Unix 时间戳，如 `1780934405000` | 直接输出原始数字 | `datetime.fromtimestamp(int(v)/1000)` 转换 |
| describe-smart-access-gateway-attribute | `CreateTime` | 毫秒级 Unix 时间戳 | 同上 | 同上 |
| describe-smart-access-gateways (列表) | `EndTime` | 毫秒级 Unix 时间戳 | 同上 | 同上 |
| describe-smart-access-gateways (列表) | `DataPlan` | 流量值（字节数），`0` 表示不限流 | 直接当作 MB/GB 显示 | 需除以 1024^n 并判断 0 特殊含义 |
| describe-sag-wan-4g | `SignalStrength` | 枚举字符串: `"Unavailable"`, `"Low"`, `"Middle"`, `"High"` | 假设为数值 | 直接作为文本展示 |
| describe-smart-access-gateway-attribute | `VpnStatus` | 枚举: `"up"`, `"down"`, 空字符串 | 空串当作有效状态 | 空串显示为 "-" |

**通用原则**:
- 时间戳字段（`EndTime`, `CreateTime` 等）统一为**毫秒**级，需要除以 1000 再传给 `datetime.fromtimestamp()`
- 带宽字段已自带单位后缀 `"M"`（Megabit），脚本不应再追加 "M" 或 "Mbps"
- 返回空字符串 `""` 和 未返回该字段（KeyError）要区分处理：空串用 `"-"` 展示，缺字段用默认值
