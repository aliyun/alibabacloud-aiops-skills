# Cloud Firewall (Cloudfw) API Analysis for Exposure Detection Skill

**Product:** Cloudfw
**API Version:** 2017-12-07
**API Style:** RPC (Action-based, not RESTful)
**Endpoint:** `cloudfw.{regionId}.aliyuncs.com` (or `cloudfw.cn-hangzhou.aliyuncs.com` as default)
**Common Parameters:** All APIs accept `Action`, `AccessKeyId`, `Format`, `Version=2017-12-07`, `SignatureMethod`, `Timestamp`, `SignatureVersion`, `SignatureNonce`, `Signature`

---

## 1. Exposure Overview

### 1.1 DescribeInternetOpenStatistic
**Description:** Get internet exposure statistics — total open IPs, ports, services, and risk counts. This is the entry point for exposure analysis, providing the high-level overview before drilling into details.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| SourceIp | string | No | Source IP of visitor |
| Lang | string | No | Language: `zh` (Chinese), `en` (English) |
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

### 1.2 DescribeInternetOpenIp
**Description:** Query the list of exposed public IPs with detailed risk information, services, ports, and traffic data. Paginated. This API provides per-IP granularity for exposure analysis.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| CurrentPage | int32 | **Yes** | Page number |
| PageSize | int32 | **Yes** | Items per page |
| StartTime | string | No | Start time (seconds timestamp) |
| EndTime | string | No | End time (seconds timestamp) |
| SearchItem | string | No | Search by IP address |
| AssetsType | string | No | Asset type filter (e.g., `EcsPublicIP`, `EcsEIP`, `NatEIP`) |
| RegionNo | string | No | Region ID filter |
| ServiceName | string | No | Service name filter |
| RiskLevel | string | No | Risk level filter |
| Port | string | No | Port number filter |

**Key Response Fields:**
```
PageInfo (object):
  CurrentPage (int32)                     - Current page number
  PageSize (int32)                        - Items per page
  TotalCount (int32)                      - Total number of exposed IPs
DataList[] (array):
  PublicIp (string)                       - Public IP address
  RiskLevel (int32)                       - Risk level (0=no risk)
  PortList (string[])                     - List of exposed ports
  PortCount (int32)                       - Number of exposed ports
  ServiceNameList (string[])              - Running services (e.g., "HTTPS", "Unknown")
  HasAclRecommend (boolean)              - Whether ACL recommendation exists
  AclRecommendDetail (string)            - ACL recommendation details
  AssetsType (string)                     - Resource type (EcsPublicIP, EcsEIP, NatEIP, etc.)
  AssetsName (string)                     - Resource instance name
  AssetsInstanceId (string)              - Resource instance ID
  RiskReason (string)                    - Risk reason description
  RegionNo (string)                      - Region ID
  InBytes (int64)                        - Inbound traffic bytes
  OutBytes (int64)                       - Outbound traffic bytes
  TotalBytes (int64)                     - Total traffic bytes
  UnknownReason (string[])              - Unknown risk reason list
```

### 1.3 DescribeInternetOpenPort
**Description:** Query the list of exposed ports with risk assessment, associated IPs, and traffic data. Paginated. Identifies high-risk port exposures across all public assets.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| CurrentPage | int32 | **Yes** | Page number |
| PageSize | int32 | **Yes** | Items per page |
| StartTime | string | No | Start time (seconds timestamp) |
| EndTime | string | No | End time (seconds timestamp) |
| Port | string | No | Port number filter |
| ServiceName | string | No | Service name filter |
| RiskLevel | string | No | Risk level filter |

**Key Response Fields:**
```
PageInfo (object):
  CurrentPage (int32)                     - Current page number
  PageSize (int32)                        - Items per page
  TotalCount (int32)                      - Total number of exposed ports
DataList[] (array):
  Port (int32)                           - Port number
  Protocol (string)                      - Protocol (e.g., tcp)
  RiskLevel (int32)                      - Risk level (0=no risk)
  ServiceNameList (string[])             - Services running on this port
  PublicIpNum (int32)                    - Number of public IPs using this port
  HasAclRecommend (boolean)             - Whether ACL recommendation exists
  RiskReason (string)                   - Risk reason description
  SuggestLevel (string)                 - Suggested action level
  InBytes (int64)                       - Inbound traffic bytes
  OutBytes (int64)                      - Outbound traffic bytes
  TotalBytes (int64)                    - Total traffic bytes
```

---

## 2. Asset Protection

### 2.1 DescribeAssetList
**Description:** Query detailed information about each asset (IP) protected by Cloud Firewall, including firewall status, risk level, resource type, and discovery time. Paginated.

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
| NewResourceTag | string | No | New resource filter (e.g., `discovered in 7 days`) |

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
  CreateTimeStamp (string)                - Discovery time (format: "2026-03-17 11:18:52")
  NewResourceTag (string)                 - New discovery tag
  Last7DayOutTrafficBytes (int64)         - Outbound traffic in last 7 days
```

### 2.2 DescribeAssetRiskList
**Description:** Query detailed risk reasons for specific IP addresses. Accepts a list of IPs (max 20 per call) and returns per-IP risk assessment.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| IpVersion | int32 | No | IP version: `4` (IPv4), `6` (IPv6) |
| IpAddrList | string (JSON array) | No | JSON array of IP addresses, e.g., `'["1.2.3.4","5.6.7.8"]'` (max 20 IPs per call) |

**Key Response Fields:**
```
AssetList[] (array of objects):
  Ip (string)                             - IP address
  RiskLevel (string)                      - Risk level: high/middle/low
  Reason (string)                         - Risk reason description
```

---

## 3. Vulnerability & Attack

### 3.1 DescribeVulnerabilityProtectedList
**Description:** Query vulnerability protection coverage — lists vulnerabilities with their protection status, attack counts, and whether rules/patches need to be enabled. Paginated.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| CurrentPage | int32 | **Yes** | Page number |
| PageSize | int32 | **Yes** | Items per page |
| StartTime | string | No | Start time (seconds timestamp) |
| EndTime | string | No | End time (seconds timestamp) |
| VulnLevel | string | No | Vulnerability level filter: `high`, `medium`, `low` |
| VulnType | string | No | Vulnerability type filter |
| VulnStatus | string | No | Protection status filter |
| SortKey | string | No | Sort field |
| Order | string | No | Sort order: `asc`, `desc` |
| UserType | string | No | User type filter |
| AttackType | string | No | Attack type filter |
| MemberUid | string | No | Member UID filter |
| BuyVersion | int64 | No | Purchased version |
| ResourceType | string | No | Resource type filter |

**Key Response Fields:**
```
TotalCount (int32)                        - Total vulnerability count
VulnList[] (array of objects):
  VulnName (string)                       - Vulnerability name
  VulnLevel (string)                      - Vulnerability level: high/medium/low
  VulnStatus (string)                     - Protection status
  CveId (string)                          - CVE identifier
  AttackCnt (int32)                       - Number of attack attempts
  ResourceCnt (int32)                     - Number of affected resources
  NeedOpenBasicRule (boolean)            - Whether basic rules need to be enabled
  NeedOpenVirtualPatche (boolean)        - Whether virtual patches need to be enabled
  NeedOpenRunMode (int32)                - Required IPS run mode
  NeedRuleClass (int32)                  - Required rule class
  HighlightTag (int32)                   - Highlight tag
```

### 3.2 DescribeRiskEventGroup
**Description:** Query intrusion detection event groups — aggregated attack events with source/destination, attack type, and geographic information. Paginated.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| CurrentPage | string | **Yes** | Page number |
| PageSize | string | **Yes** | Items per page |
| StartTime | string | **Yes** | Start time (seconds timestamp) |
| EndTime | string | **Yes** | End time (seconds timestamp) |
| DataType | string | No | Data type: `1` (IPS events) |
| Direction | string | No | Direction: `in` (inbound), `out` (outbound) |
| SrcIP | string | No | Source IP filter |
| DstIP | string | No | Destination IP filter |
| VulLevel | string | No | Vulnerability level: `1` (low), `2` (medium), `3` (high) |
| AttackType | string | No | Attack type code filter |
| RuleResult | string | No | Rule action result filter |
| AttackApp | string | No | Attack application filter |
| SrcNetworkInstanceId | string | No | Source network instance ID |
| DstNetworkInstanceId | string | No | Destination network instance ID |
| FirewallType | string | No | Firewall type filter |
| NoLocation | string | No | Exclude location info |
| Sort | string | No | Sort field |
| Order | string | No | Sort order: `asc`, `desc` |

**Key Response Fields:**
```
TotalCount (int32)                        - Total event group count
DataList[] (array of objects):
  EventName (string)                      - Event name (e.g., "Trin00 password attempt")
  EventCount (int32)                      - Number of events in group
  SrcIP (string)                          - Source IP address
  DstIP (string)                          - Destination IP address
  AttackType (int32)                      - Attack type code
  AttackApp (string)                      - Attack application (e.g., "Host")
  VulLevel (int32)                        - Vulnerability level: 1=low, 2=medium, 3=high
  RuleResult (int32)                      - Action result: 1=observe, 2=block
  Direction (string)                      - Direction: in/out
  Description (string)                    - Event description
  ResourcePrivateIPList[] (array):        - Attacked private resources
    ResourcePrivateIP (string)            - Private IP
    ResourceInstanceId (string)           - Instance ID
    ResourceInstanceName (string)         - Instance name
    ResourceType (string)                 - Resource type
  IPLocationInfo (object):                - Source geographic location
    CountryName (string)                  - Country name
    CityName (string)                     - City name
    CountryId (string)                    - Country ID
    CityId (string)                       - City ID
  FirstEventTime (int64)                  - First event timestamp (seconds)
  LastEventTime (int64)                   - Last event timestamp (seconds)
  ResourceType (string)                   - Attacked resource type
  Tag (string)                            - Event tag
  RuleSource (int32)                      - Rule source
  SrcPrivateIPList[] (string[])           - Source private IP list
```

---

## 4. ACL Policy

### 4.1 DescribeControlPolicy
**Description:** Query internet border access control (ACL) policies — lists firewall rules with source/destination, ports, actions, and hit counts. Paginated.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | No | Language: `zh`, `en` |
| Direction | string | **Yes** | Traffic direction: `in` (inbound), `out` (outbound) |
| CurrentPage | string | **Yes** | Page number |
| PageSize | string | **Yes** | Items per page |
| Source | string | No | Source address filter |
| Destination | string | No | Destination address filter |
| Description | string | No | Rule description filter |
| Proto | string | No | Protocol filter: `TCP`, `UDP`, `ICMP`, `ANY` |
| AclAction | string | No | Action filter: `accept`, `drop`, `log` |
| Release | string | No | Enable status: `true`, `false` |
| AclUuid | string | No | ACL rule UUID filter |
| IpVersion | string | No | IP version: `4`, `6` |
| MemberUid | int64 | No | Member account UID |

**Key Response Fields:**
```
TotalCount (int32)                        - Total policy count
Policys[] (array of objects):
  AclUuid (string)                        - ACL rule UUID
  Source (string)                         - Source address/CIDR
  SourceType (string)                    - Source type: net/group/location
  Destination (string)                   - Destination address/CIDR
  DestinationType (string)              - Destination type: net/group/domain/location
  DestPort (string)                      - Destination port or port range
  DestPortType (string)                 - Port type: port/group
  Proto (string)                         - Protocol: TCP/UDP/ICMP/ANY
  AclAction (string)                     - Action: accept/drop/log
  HitTimes (int64)                       - Number of times rule was hit
  HitLastTime (int64)                    - Last hit timestamp (seconds)
  Release (string)                       - Whether rule is enabled: true/false
  Order (int32)                          - Rule priority order
  Direction (string)                     - Direction: in/out
  Description (string)                   - Rule description
  ApplicationNameList[] (string[])       - Application name list
  CreateTime (int64)                     - Rule creation timestamp
  ModifyTime (int64)                     - Last modification timestamp
  MemberUid (string)                     - Member account UID
```

---

## Summary: APIs Needed for Exposure Detection Skill

| Functional Area | API | Purpose |
|----------------|-----|---------|
| **Exposure Overview** | `DescribeInternetOpenStatistic` | Get internet exposure stats (open IPs, ports, risks) |
| **Exposure Overview** | `DescribeInternetOpenIp` | Get per-IP exposure details with risk info |
| **Exposure Overview** | `DescribeInternetOpenPort` | Get per-port exposure details with risk assessment |
| **Asset Protection** | `DescribeAssetList` | Get asset firewall protection status and new discoveries |
| **Asset Protection** | `DescribeAssetRiskList` | Get detailed risk reasons per IP |
| **Vulnerability & Attack** | `DescribeVulnerabilityProtectedList` | Get vulnerability protection coverage |
| **Vulnerability & Attack** | `DescribeRiskEventGroup` | Get recent intrusion attack events |
| **ACL Policy** | `DescribeControlPolicy` | Get internet border ACL rules |

### API Endpoint Format

All Cloudfw APIs use the RPC style:
```
POST https://cloudfw.cn-hangzhou.aliyuncs.com/
  ?Action=DescribeInternetOpenStatistic
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

Or using Aliyun CLI (recommended):
```bash
aliyun cloudfw describe-internet-open-statistic \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-exposure-detection
```
