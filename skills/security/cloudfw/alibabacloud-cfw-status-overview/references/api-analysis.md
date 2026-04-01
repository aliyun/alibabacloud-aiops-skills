# Cloud Firewall (Cloudfw) API Analysis for Status Overview Skill

**Product:** Cloudfw
**API Version:** 2017-12-07
**API Style:** RPC (Action-based, not RESTful)
**Endpoint:** `cloudfw.{regionId}.aliyuncs.com` (or `cloudfw.cn-hangzhou.aliyuncs.com` as default)
**Common Parameters:** All APIs accept `Action`, `AccessKeyId`, `Format`, `Version=2017-12-07`, `SignatureMethod`, `Timestamp`, `SignatureVersion`, `SignatureNonce`, `Signature`

---

## 1. Asset Overview

### 1.1 DescribeAssetStatistic
**Description:** Query statistical information about assets protected by Cloud Firewall - counts of protected/total IPs, specification usage.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| SourceIp | string | No | Source IP of visitor |
| Lang | string | No | Language: `zh` (Chinese), `en` (English) |

**Key Response Fields:**
```
AutoResourceEnable (boolean)              - Whether auto traffic redirection is enabled
ResourceSpecStatistic (object):
  IpNumUsed (int32)                       - Number of public IPs with protection enabled
  IpNumSpec (int32)                       - Public IP protection specification count (quota)
  SensitiveDataIpNumSpec (int64)          - Sensitive data IP spec count
  SensitiveDataIpNumUsed (int64)          - Sensitive data IP enabled count
GeneralInstanceSpecStatistic (object):    - For billing model 2.0 users
  TotalGeneralInstanceUsedCnt (int32)     - Total specification count
  TotalCfwGeneralInstanceUsedCnt (int32)  - Enabled internet firewall instances
  TotalVfwGeneralInstanceUsedCnt (int32)  - Enabled VPC firewall instances
  TotalNatGeneralInstanceUsedCnt (int32)  - Enabled NAT firewall instances
  TotalCfwGeneralInstanceCnt (int32)      - Total internet firewall instance count
  TotalNatGeneralInstanceCnt (int32)      - Total NAT firewall instance count
  CfwGeneralInstanceRegionStatistic[]     - Per-region internet FW stats
  CfwTotalGeneralInstanceRegionStatistic[] - Per-region total stats
```

### 1.2 DescribeAssetList
**Description:** Query detailed information about each asset (IP) protected by Cloud Firewall. Paginated.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| CurrentPage | string | **Yes** | Page number |
| PageSize | string | **Yes** | Items per page |
| RegionNo | string | No | Region ID filter |
| Status | string | No | Firewall status: `open`, `opening`, `closed`, `closing` |
| SearchItem | string | No | Search by asset IP or instance ID |
| ResourceType | string | No | Asset type: `EcsEIP`, `EcsPublicIP`, `EIP`, `EniEIP`, `NatEIP`, `SlbEIP`, `SlbPublicIP`, `NatPublicIP`, `HAVIP`, `BastionHostEgressIP`, `BastionHostIngressIP` |
| SgStatus | string | No | Security group status: `pass`, `block`, `unsupport` |
| IpVersion | string | No | `4` (IPv4, default), `6` (IPv6) |
| MemberUid | int64 | No | Member account UID |
| UserType | string | No | `buy` (paid), `free` |

**Key Response Fields:**
```
TotalCount (int32)                        - Total number of assets
Assets[] (array of objects):
  InternetAddress (string)                - Public IP address
  IntranetAddress (string)                - Private IP address
  Name (string)                           - Instance name
  ResourceInstanceId (string)             - Instance ID
  BindInstanceId (string)                 - Bound instance ID
  BindInstanceName (string)               - Bound instance name
  ResourceType (string)                   - Asset type (EcsEIP, SlbEIP, etc.)
  ProtectStatus (string)                  - Firewall status: open/opening/closed/closing
  RegionID (string)                       - Region ID
  IpVersion (int32)                       - IP version (4 or 6)
  SgStatus (string)                       - Security group policy status
  MemberUid (int64)                       - Member account UID
  SyncStatus (string)                     - Traffic redirection support: enable/disable
  RegionStatus (string)                   - Region support: enable/disable
  RiskLevel (string)                      - Risk level: low/middle/hight
  CreateTimeStamp (string)                - Discovery time
  Last7DayOutTrafficBytes (int64)         - Outbound traffic in last 7 days
```

### 1.3 DescribeUserBuyVersion
**Description:** Get user's Cloud Firewall version/instance information (edition, quotas, bandwidth).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| InstanceId | string | No | Instance ID (omit for latest) |

**Key Response Fields:**
```
Version (int32)                           - Version: 2=Premium, 3=Enterprise, 4=Ultimate, 10=Pay-as-you-go
InstanceId (string)                       - CFW instance ID
InstanceStatus (string)                   - Status: normal/init/deleting/abnormal/free
UserStatus (boolean)                      - true=valid, false=invalid
StartTime (int64)                         - Activation time (ms timestamp)
Expire (int64)                            - Expiration time (ms timestamp)
IpNumber (int64)                          - Internet border protection IP quota
VpcNumber (int64)                         - VPC border protection quota
InternetBandwidth (int64)                 - Internet FW traffic processing capacity
VpcBandwidth (int64)                      - VPC FW traffic processing capacity
NatBandwidth (int64)                      - NAT FW traffic processing capacity
LogStatus (boolean)                       - Log delivery enabled
LogStorage (int64)                        - Log storage capacity
MaxOverflow (int64)                       - Elastic billing: 1000000=enabled, 0=disabled
GeneralInstance (int64)                   - General instance spec count
ThreatIntelligence (int64)               - Threat intelligence enabled
Sdl (int64)                              - Data leakage detection enabled
```

### 1.4 DescribeInternetOpenStatistic
**Description:** Get internet exposure statistics (open IPs, ports, services, risk counts).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| SourceIp | string | No | Source IP |
| Lang | string | No | Language: `zh`, `en` |
| StartTime | string | No | Start time (seconds timestamp) |
| EndTime | string | No | End time (seconds timestamp) |

**Key Response Fields:**
```
InternetIpNum (int32)                     - Total open public IPs
InternetPortNum (int32)                   - Total open ports
InternetServiceNum (int32)               - Total open applications/services
InternetUnprotectedPortNum (int32)        - Ports not protected by ACL
InternetRiskIpNum (int32)                 - Risky open public IPs
InternetRiskPortNum (int32)               - Risky ports
InternetRiskServiceNum (int32)            - Risky applications
InternetSlbIpNum (int32)                  - SLB public IPs
InternetSlbIpPortNum (int32)              - SLB public ports
```

---

## 2. Internet Border Firewall Status

### 2.1 DescribeAssetList (see Section 1.2 above)
- Use `Status` parameter to filter by protection status
- Count assets with `ProtectStatus=open` vs `ProtectStatus=closed` to determine protected/unprotected counts
- Use `TotalCount` for total number of assets

### 2.2 DescribeAssetStatistic (see Section 1.1 above)
- `ResourceSpecStatistic.IpNumUsed` = protected IPs count
- `ResourceSpecStatistic.IpNumSpec` = IP protection quota
- Protection ratio = IpNumUsed / IpNumSpec

### 2.3 DescribeInternetOpenStatistic (see Section 1.4 above)
- Provides open IP / port / service counts for internet border

---

## 3. VPC Border Firewall Status

### 3.1 DescribeVpcFirewallSummaryInfo
**Description:** Query VPC firewall summary information - aggregated view of all VPC firewalls.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| SourceIp | string | No | Source IP |

**Key Response Fields:**
```
VpcFirewallSummaryList[] (array):
  VpcFirewallId (string)                  - VPC firewall ID
  VpcFirewallName (string)                - VPC firewall name
  FirewallSwitchStatus (string)           - Switch status (open/close)
  RegionNo (string)                       - Region ID
  ConnectType (string)                    - Connection type
  PrecheckStatus (string)                 - Precheck status
```

### 3.2 DescribeTrFirewallsV2List (CEN Enterprise Edition / Transit Router)
**Description:** Query TR (Transit Router) firewall list for CEN Enterprise Edition.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| FirewallId | string | No | Firewall instance ID filter |
| FirewallName | string | No | Firewall name filter |
| FirewallSwitchStatus | string | No | Switch status filter: `open`, `close`, `creating`, `deleting` |
| RegionNo | string | No | Region ID filter |
| RouteMode | string | No | Route mode filter: `managed`, `manual` |
| TransitRouterId | string | No | Transit Router ID filter |
| CenId | string | No | CEN instance ID filter |
| PageSize | int32 | No | Page size |
| CurrentPage | int32 | No | Current page |

**Key Response Fields:**
```
TotalCount (int32)                        - Total firewall count
VpcTrFirewalls[] (array):
  FirewallId (string)                     - Firewall instance ID
  FirewallName (string)                   - Firewall name
  FirewallSwitchStatus (string)           - Switch status: open/close/creating/deleting
  RegionNo (string)                       - Region ID
  RouteMode (string)                      - Route mode: managed/manual
  CenId (string)                          - CEN instance ID
  CenName (string)                        - CEN instance name
  TransitRouterId (string)                - Transit Router ID
  ResultCode (string)                     - Result code
  FirewallStatus (string)                 - Firewall status (creating/deleting/ready)
  PrecheckStatus (string)                 - Precheck status
  OwnerId (int64)                         - Owner UID
  VpcCidr (string)                        - VPC CIDR block
  VpcId (string)                          - VPC ID
  VSwitchId (string)                      - VSwitch ID
  IpsConfig (object):                     - IPS configuration
    BasicRules (int32)                    - Basic rules switch
    EnableAllPatch (int32)                - Virtual patches switch
    RunMode (int32)                       - IPS run mode
```

### 3.3 DescribeVpcFirewallCenList (CEN Basic Edition)
**Description:** Query VPC firewall list for CEN Basic Edition connections.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| VpcFirewallId | string | No | VPC firewall instance ID |
| VpcFirewallName | string | No | VPC firewall name filter |
| FirewallSwitchStatus | string | No | Switch status: `opened`, `closed`, `notconfigured`, `configured`, `opening`, `closing` |
| CenId | string | No | CEN instance ID |
| NetworkInstanceId | string | No | Network instance ID |
| RegionNo | string | No | Region ID |
| MemberUid | string | No | Member account UID |
| PageSize | string | No | Page size |
| CurrentPage | string | No | Current page |
| RouteMode | string | No | Route mode: `auto`, `manual` |
| TransitRouterType | string | No | Transit Router type: `Basic`, `Enterprise` |
| OwnerId | string | No | Owner ID |

**Key Response Fields:**
```
TotalCount (int32)                        - Total count
VpcFirewalls[] (array):
  VpcFirewallId (string)                  - VPC firewall instance ID
  VpcFirewallName (string)                - VPC firewall name
  FirewallSwitchStatus (string)           - Switch status: opened/closed/notconfigured/configured/opening/closing
  CenId (string)                          - CEN instance ID
  CenName (string)                        - CEN instance name
  ConnectType (string)                    - Connection type
  RegionStatus (string)                   - Region status
  LocalVpc (object):                      - Local VPC info
    VpcId (string)                        - VPC ID
    VpcName (string)                      - VPC name
    RegionNo (string)                     - Region ID
    OwnerId (int64)                       - Owner UID
  PeerVpc (object):                       - Peer VPC info (same structure)
  MemberUid (string)                      - Member UID
```

### 3.4 DescribeVpcFirewallList (Express Connect / VPN)
**Description:** Query VPC firewall list for Express Connect connections.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| VpcFirewallId | string | No | VPC firewall instance ID |
| VpcFirewallName | string | No | VPC firewall name filter |
| FirewallSwitchStatus | string | No | Switch status: `opened`, `closed`, `notconfigured`, `configured` |
| VpcId | string | No | VPC ID filter |
| RegionNo | string | No | Region filter |
| MemberUid | int64 | No | Member UID |
| PeerUid | string | No | Peer account UID |
| ConnectSubType | string | No | Sub connection type |
| PageSize | string | No | Page size |
| CurrentPage | string | No | Current page |

**Key Response Fields:**
```
TotalCount (int32)                        - Total count
VpcFirewalls[] (array):
  VpcFirewallId (string)                  - VPC firewall instance ID
  VpcFirewallName (string)                - VPC firewall name
  FirewallSwitchStatus (string)           - Switch status: opened/closed/notconfigured/configured
  ConnectType (string)                    - Connection type
  ConnectSubType (string)                 - Sub connection type
  Bandwidth (int32)                       - Bandwidth
  RegionStatus (string)                   - Region support status
  LocalVpc (object):                      - Local VPC info
    VpcId (string), VpcName (string), RegionNo (string), OwnerId (int64)
  PeerVpc (object):                       - Peer VPC info (same structure)
  MemberUid (string)                      - Member UID
  IpsConfig (object):                     - IPS configuration
    BasicRules (int32), EnableAllPatch (int32), RunMode (int32)
```

### 3.5 DescribeVpcFirewallCenSummaryList (CEN Summary)
**Description:** Query VPC firewall CEN summary list - high-level view per CEN instance.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language |
| CenId | string | No | CEN instance ID filter |
| FirewallSwitchStatus | string | No | Status filter |
| RegionNo | string | No | Region filter |
| MemberUid | string | No | Member UID |
| PageSize | string | No | Page size |
| CurrentPage | string | No | Current page |

**Key Response Fields:**
```
TotalCount (int32)                        - Total count
VpcFirewallGroupList[] (array):
  CenId (string)                          - CEN instance ID
  CenName (string)                        - CEN instance name
  VpcFirewallCount (int32)                - Total VPC firewall count
  OpenVpcFirewallCount (int32)            - Opened VPC firewall count
  ClosedVpcFirewallCount (int32)          - Closed VPC firewall count
  NotConfiguredVpcFirewallCount (int32)   - Not configured VPC firewall count
  MemberUid (string)                      - Member UID
```

---

## 4. NAT Border Firewall Status

### 4.1 DescribeNatFirewallList
**Description:** Query NAT firewall list with status, VPC, and NAT gateway details.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| NatGatewayId | string | No | NAT gateway instance ID filter |
| FirewallSwitch | string | No | Switch status: `open`, `close` |
| VpcId | string | No | VPC ID filter |
| ProxyId | string | No | NAT firewall proxy ID filter |
| ProxyName | string | No | NAT firewall proxy name filter |
| RegionNo | string | No | Region ID filter |
| PageNo | int32 | No | Page number (default: 1) |
| PageSize | int32 | No | Items per page (default: 10) |
| MemberUid | int64 | No | Member account UID |
| Status | string | No | Status filter |

**Key Response Fields:**
```
TotalCount (int32)                        - Total NAT firewall count
NatFirewallList[] (array):
  ProxyId (string)                        - NAT firewall proxy ID
  ProxyName (string)                      - NAT firewall proxy name
  ProxyStatus (string)                    - Status: configuring/deleting/normal/abnormal/creating
  RegionId (string)                       - Region ID
  VpcId (string)                          - VPC instance ID
  VpcName (string)                        - VPC name
  NatGatewayId (string)                   - NAT gateway instance ID
  NatGatewayName (string)                 - NAT gateway name
  FirewallSwitch (string)                 - Firewall switch: open/close
  StrictMode (int32)                      - Strict mode: 0=disabled, 1=enabled
  DnsProxyStatus (string)                 - DNS proxy status
  AliUid (int64)                          - Alibaba Cloud account UID
  MemberUid (int64)                       - Member account UID
  ErrorDetail (string)                    - Error detail message
  NatRouteEntryList[] (array):
    DestinationCidr (string)              - Destination CIDR
    NextHopId (string)                    - Next hop ID
    NextHopType (string)                  - Next hop type
    RouteTableId (string)                 - Route table ID
```

---

## 5. Traffic Overview

### 5.1 DescribeInternetTrafficTrend
**Description:** Query internet traffic trends over a time period, including bandwidth, sessions, and connections.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| Direction | string | No | Traffic direction: `in` (inbound), `out` (outbound) |
| StartTime | string | **Yes** | Start time (seconds timestamp) |
| EndTime | string | **Yes** | End time (seconds timestamp) |
| SourceCode | string | **Yes** | Source code, e.g. `yundun` |
| SrcPrivateIP | string | No | Source private IP filter |
| DstPrivateIP | string | No | Destination private IP filter |
| SrcPublicIP | string | No | Source public IP filter |
| DstPublicIP | string | No | Destination public IP filter |
| TrafficType | string | No | Traffic type filter |

**Key Response Fields:**
```
TotalBps (int64)                          - Total bits per second
TotalPps (int64)                          - Total packets per second
TotalSession (int64)                      - Total sessions
AvgInBps (int64)                          - Average inbound bps
AvgOutBps (int64)                         - Average outbound bps
MaxInBps (int64)                          - Peak inbound bps
MaxOutBps (int64)                         - Peak outbound bps
MaxSession (int64)                        - Peak sessions
MaxNewConn (int64)                        - Peak new connections
AvgTotalBps (int64)                       - Average total bps
DataList[] (array):                       - Time-series data
  Time (int64)                            - Timestamp
  InBps (int64)                           - Inbound bps
  OutBps (int64)                          - Outbound bps
  InPps (int64)                           - Inbound pps
  OutPps (int64)                          - Outbound pps
  SessionCount (int64)                    - Session count
  NewConn (int64)                         - New connections
  TotalBps (int64)                        - Total bps
InternetTrafficTrendList[] (array):       - Same structure as DataList
```

### 5.2 DescribeNatFirewallTrafficTrend
**Description:** Query NAT firewall traffic trends.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| NatFirewallId | string | No | NAT firewall instance ID |
| StartTime | string | **Yes** | Start time (seconds timestamp) |
| EndTime | string | **Yes** | End time (seconds timestamp) |
| Direction | string | No | Direction: `in`, `out` |

**Key Response Fields:**
```
MaxInBps (int64)                          - Peak inbound bps
MaxOutBps (int64)                         - Peak outbound bps
MaxTotalBps (int64)                       - Peak total bps
AvgInBps (int64)                          - Average inbound bps
AvgOutBps (int64)                         - Average outbound bps
AvgTotalBps (int64)                       - Average total bps
MaxSession (int64)                        - Peak session count
MaxNewConn (int64)                        - Peak new connections
DataList[] (array):
  Time (int64), InBps (int64), OutBps (int64), InPps (int64), OutPps (int64),
  SessionCount (int64), NewConn (int64), TotalBps (int64)
```

### 5.3 DescribeInternetDropTrafficTrend
**Description:** Query internet firewall interception/block trends.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language |
| Direction | string | No | Direction: `in`, `out` |
| StartTime | string | **Yes** | Start time (seconds timestamp) |
| EndTime | string | **Yes** | End time (seconds timestamp) |
| SourceCode | string | **Yes** | Source code, e.g. `yundun` |

**Key Response Fields:**
```
DropSessionMax (int64)                    - Peak block count in period
RingRatioAverage (string)                 - Traffic rate percentage
DataList[] (array):
  Time (int64)                            - Timestamp
  AclDrop (int64)                         - ACL block count
  IpsDrop (int64)                         - IPS block count
  TotalSession (int64)                    - Total requests
  DropSession (int64)                     - Blocked count
  DataTime (string)                       - Time point string
  DropRatio (string)                      - Drop ratio
```

### 5.4 DescribeVpcFirewallDropTrafficTrend
**Description:** Query VPC firewall interception/block trends.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| SourceIp | string | No | Source IP |
| StartTime | int64 | No | Start time (seconds timestamp) |
| EndTime | int64 | No | End time (seconds timestamp) |
| TrafficTime | int64 | No | Traffic time point |
| Sort | string | No | Sort field, e.g. `LastTime` |
| Order | string | No | Sort order: `asc`, `desc` |

**Key Response Fields:**
```
DropSessionMax (int64)                    - Peak block count
DataList[] (array):
  Time (int64)                            - Timestamp
  AclDrop (int64)                         - ACL block count
  IpsDrop (int64)                         - IPS block count
  TotalSession (int64)                    - Total sessions
  DropSession (int64)                     - Blocked count
  DataTime (string)                       - Time point string
```

### 5.5 DescribeNatFirewallDropTrafficTrend
**Description:** Query NAT firewall interception/block trends.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| SourceIp | string | No | Source IP |
| StartTime | int64 | No | Start time (seconds timestamp) |
| EndTime | int64 | No | End time (seconds timestamp) |

**Key Response Fields:**
```
DropSessionMax (int64)                    - Peak block value
DropSessionMaxTime (string)              - Period of peak block
DataList[] (array):
  Time (int64)                            - Timestamp
  TotalSession (int64)                    - Total requests
  DropSession (int64)                     - Blocked count
```

### 5.6 DescribeInternetTrafficTop
**Description:** Query top IPs by internet traffic volume.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language |
| StartTime | string | **Yes** | Start time (seconds timestamp) |
| EndTime | string | **Yes** | End time (seconds timestamp) |
| Direction | string | No | Direction: `in`, `out` |
| Sort | string | No | Sort field |
| Order | string | No | Sort order: `asc`, `desc` |
| PageSize | int32 | No | Items per page |
| CurrentPage | int32 | No | Current page |
| TrafficType | string | No | Traffic type |
| SourceCode | string | **Yes** | Source code, e.g. `yundun` |
| RegionNo | string | No | Region ID |
| SearchItem | string | No | Search keyword |

**Key Response Fields:**
```
TotalCount (int32)                        - Total count
TrafficTopList[] (array):
  SrcIP (string)                          - Source IP
  DstIP (string)                          - Destination IP
  SrcPrivateIP (string)                   - Source private IP
  DstPrivateIP (string)                   - Destination private IP
  RegionNo (string)                       - Region ID
  ResourceInstanceId (string)             - Resource instance ID
  ResourceInstanceName (string)           - Resource instance name
  ResourceType (string)                   - Resource type
  InBps (int64)                           - Inbound bps
  OutBps (int64)                          - Outbound bps
  TotalBps (int64)                        - Total bps
  InPps (int64)                           - Inbound pps
  OutPps (int64)                          - Outbound pps
  SessionCount (int64)                    - Session count
  NewConn (int64)                         - New connections
  InBytes (int64)                         - Inbound bytes
  OutBytes (int64)                        - Outbound bytes
  TotalBytes (int64)                      - Total bytes
```

---

## Summary: APIs Needed for Status Overview Skill

| Functional Area | API | Purpose |
|----------------|-----|---------|
| **Asset Overview** | `DescribeUserBuyVersion` | Get CFW edition, quotas, bandwidth specs |
| **Asset Overview** | `DescribeAssetStatistic` | Get protected/total IP counts, spec usage |
| **Asset Overview** | `DescribeInternetOpenStatistic` | Get internet exposure stats (open IPs, ports, risks) |
| **Internet Border FW** | `DescribeAssetList` | Get per-asset protection status (paginated) |
| **Internet Border FW** | `DescribeAssetStatistic` | Get aggregate protection counts |
| **VPC Border FW** | `DescribeVpcFirewallSummaryInfo` | Get VPC FW summary (all types) |
| **VPC Border FW** | `DescribeTrFirewallsV2List` | Get CEN Enterprise Edition VPC FW list |
| **VPC Border FW** | `DescribeVpcFirewallCenList` | Get CEN Basic Edition VPC FW list |
| **VPC Border FW** | `DescribeVpcFirewallCenSummaryList` | Get CEN VPC FW summary (counts) |
| **VPC Border FW** | `DescribeVpcFirewallList` | Get Express Connect VPC FW list |
| **NAT Border FW** | `DescribeNatFirewallList` | Get NAT FW list with switch status |
| **Traffic Overview** | `DescribeInternetTrafficTrend` | Internet traffic trends (bps, sessions) |
| **Traffic Overview** | `DescribeNatFirewallTrafficTrend` | NAT FW traffic trends |
| **Traffic Overview** | `DescribeInternetDropTrafficTrend` | Internet FW block/interception trends |
| **Traffic Overview** | `DescribeVpcFirewallDropTrafficTrend` | VPC FW block/interception trends |
| **Traffic Overview** | `DescribeNatFirewallDropTrafficTrend` | NAT FW block/interception trends |
| **Traffic Overview** | `DescribeInternetTrafficTop` | Top IPs by traffic volume |

### Recommended Primary APIs for the Skill

For a concise "Status Overview" dashboard, the **minimum essential** APIs are:

1. **`DescribeUserBuyVersion`** - Edition info, quotas (no params required)
2. **`DescribeAssetStatistic`** - Protected IP counts (no params required)
3. **`DescribeInternetOpenStatistic`** - Internet exposure stats (no params required)
4. **`DescribeNatFirewallList`** - NAT FW status list (paginated)
5. **`DescribeVpcFirewallCenSummaryList`** - VPC FW summary with open/closed counts
6. **`DescribeTrFirewallsV2List`** - TR/CEN Enterprise VPC FW list
7. **`DescribeVpcFirewallList`** - Express Connect VPC FW list
8. **`DescribeInternetTrafficTrend`** - Traffic trends with peak bandwidth (requires StartTime, EndTime, SourceCode)

### API Endpoint Format

All Cloudfw APIs use the RPC style:
```
POST https://cloudfw.cn-hangzhou.aliyuncs.com/
  ?Action=DescribeAssetStatistic
  &Version=2017-12-07
  &Format=JSON
  &AccessKeyId=<AK>
  &SignatureMethod=HMAC-SHA1
  &Timestamp=<ISO8601>
  &SignatureVersion=1.0
  &SignatureNonce=<random>
  &Signature=<computed>
  &Lang=zh
```

Or using Alibaba Cloud SDK:
```python
from alibabacloud_cloudfw20171207.client import Client
from alibabacloud_cloudfw20171207 import models

client = Client(config)
request = models.DescribeAssetStatisticRequest(lang='zh')
response = client.describe_asset_statistic(request)
```
