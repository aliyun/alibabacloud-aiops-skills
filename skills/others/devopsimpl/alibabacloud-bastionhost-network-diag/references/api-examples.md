# Bastion Host Network Diagnosis API Examples

This file contains the `aliyun-cli` command examples and response format descriptions involved in the diagnosis process.

## Table of Contents

- [1. DescribeInstances - Query Bastion Host Instance List](#1-describeinstances-query-bastion-host-instance-list)
- [2. DescribeInstanceAttribute - Query Bastion Host Instance Attributes](#2-describeinstanceattribute-query-bastion-host-instance-attributes)
- [3. DescribeAssetList - Query Cloud Firewall Protection Status](#3-describeassetlist-query-cloud-firewall-protection-status)
- [4. DescribeTrafficLog - Query Cloud Firewall Traffic Logs](#4-describetrafficlog-query-cloud-firewall-traffic-logs)

---

## 1. DescribeInstances Query Bastion Host Instance List

**Purpose**: Obtain the Bastion Host instance ID, public/private domain names, and other basic information based on the region.

**CLI Command**:

```bash
aliyun yundun-bastionhost describe-instances --biz-region-id cn-hangzhou --region cn-hangzhou --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"
```

**Successful Response Example** (instance found):

```json
{
  "Instances": [
    {
      "BandWidth": 17,
      "DelayProduce": false,
      "DelayProduceStatus": "PENDING",
      "ExpireTime": 1791388800000,
      "ImageVersion": "V3.2.51",
      "InstanceId": "bastionhost-cn-xxxxxx03",
      "InstanceStatus": "RUNNING",
      "InternetEndpoint": "xxxxxxxx-public.bastionhost.aliyuncs.com",
      "IntranetEndpoint": "xxxxxxxx.bastionhost.aliyuncs.com",
      "Legacy": false,
      "LicenseCode": "bhah_ent_50_asset",
      "PlanCode": "cloudbastion_ha",
      "PublicNetworkAccess": true,
      "RegionId": "cn-hangzhou",
      "ResourceGroupId": "rg-xxxxxxxxxx",
      "SlaveVswitchId": "vsw-xxxxxxxxxx",
      "StartTime": 1734507544000,
      "VpcId": "vpc-xxxxxxxxxx",
      "VswitchId": "vsw-xxxxxxxxxx"
    }
  ],
  "RequestId": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "TotalCount": 1
}
```

**Key Field Descriptions**:

| Field | Description |
|-------|-------------|
| `InstanceId` | Bastion Host instance ID; required for all subsequent queries |
| `InternetEndpoint` | Public domain name (contains the `-public` identifier) |
| `IntranetEndpoint` | Private domain name |
| `PublicNetworkAccess` | Public network access switch status |
| `RegionId` | Region where the instance is located |
| `ImageVersion` | Bastion Host version number |

**Response When No Instance Is Found**:

```json
{
  "Instances": [],
  "TotalCount": 0,
  "RequestId": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

---

## 2. DescribeInstanceAttribute Query Bastion Host Instance Attributes

**Purpose**: Obtain the detailed Bastion Host configuration — public network switch, whitelist, custom ports, etc.

**CLI Command**:

```bash
aliyun yundun-bastionhost describe-instance-attribute --instance-id bastionhost-cn-xxxxxx03 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"
```

**Investigation Points**:

- **Public network switch**: Check whether public network access is enabled
- **Whitelist**: Check whether an IP whitelist is configured and whether the client IP is in the whitelist
- **Custom ports**: Standard ports are SSH `60022`, RDP `63389`, HTTPS `443`; if custom ports are configured, inform the user

---

## 3. DescribeAssetList Query Cloud Firewall Protection Status

**Purpose**: Check whether the Bastion Host public ingress IP is added to Cloud Firewall protection.

**CLI Command**:

```bash
aliyun cloudfw describe-asset-list --current-page 1 --page-size 10 --search-item bastionhost-cn-xxxxxx03 --resource-type BastionHostIngressIP --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"
```

**Note**: `--resource-type` must be fixed to `BastionHostIngressIP`.

**Response Scenario Descriptions**:

**ProtectStatus = open (added to Cloud Firewall protection)**:

```json
{
  "Assets": [
    {
      "InternetAddress": "x.x.x.x",
      "ProtectStatus": "open",
      "ResourceType": "BastionHostIngressIP"
    }
  ]
}
```

- Extract `InternetAddress` as the Bastion Host public ingress IP for subsequent traffic log queries
- Continue to execute the Cloud Firewall traffic log query

**ProtectStatus = closed (Cloud Firewall activated but not added to protection)**:

```json
{
  "Assets": [
    {
      "InternetAddress": "x.x.x.x",
      "ProtectStatus": "closed",
      "ResourceType": "BastionHostIngressIP"
    }
  ]
}
```

- The Bastion Host ingress IP is not protected by Cloud Firewall; skip the Cloud Firewall traffic log query

**Assets is empty (Cloud Firewall not activated)**:

```json
{
  "Assets": []
}
```

- Cloud Firewall is not activated; skip the entire Cloud Firewall diagnosis process

---

## 4. DescribeTrafficLog Query Cloud Firewall Traffic Logs

**Purpose**: Query whether Cloud Firewall dropped traffic related to the Bastion Host.

**CLI Command**:

```bash
aliyun cloudfw describe-traffic-log \
  --start-time <start-timestamp> \
  --end-time <end-timestamp> \
  --source-code yundun \
  --direction in \
  --rule-result 2 \
  --src-ip <client-ip> \
  --dst-ip <bastionhost-public-ip> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"
```

**Parameter Descriptions**:

| Parameter | Fixed / Dynamic | Description |
|-----------|-----------------|-------------|
| `--source-code` | Fixed to `yundun` | Data source identifier |
| `--direction` | Fixed to `in` | Inbound traffic |
| `--rule-result` | Fixed to `2` | Indicates Cloud Firewall drop action |
| `--src-ip` | Dynamic | Client public IP |
| `--dst-ip` | Dynamic | Bastion Host public ingress IP (from the previous step) |
| `--start-time` | Dynamic | Query start time (Unix timestamp in seconds) |
| `--end-time` | Dynamic | Query end time (Unix timestamp in seconds) |

**Time Range Rules**:
- Only data within the last 7 days can be queried
- It is recommended that a single query does not exceed one day
- Exceeding the 7-day range will return the `ErrorTimeError` error

**Response When No Interception Records Exist** (normal scenario):

```json
{
  "DataList": [],
  "PageInfo": {
    "CurrentPage": 1,
    "PageSize": 10,
    "TotalCount": 0
  },
  "RequestId": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

**Response When Time Range Exceeds the Limit**:

```json
{
  "RequestId": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "HostId": "cloudfw.aliyuncs.com",
  "Code": "ErrorTimeError",
  "Message": "The time is invalid."
}
```

**Response When Interception Records Exist** (when `DataList` is non-empty):

Focus on the following fields to locate the blocking reason:

| Field | Description |
|-------|-------------|
| `RuleName` | Name of the rule that triggered the interception |
| `DstPort` | Destination port that was intercepted |
| `Proto` | Protocol type (TCP/UDP) |
| `SrcIP` | Source IP |
| `DstIP` | Destination IP |
| `Action` | Action executed |
