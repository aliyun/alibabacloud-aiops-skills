# Related CLI Commands

Complete reference for all CLI commands used in the Hologres Instance Management skill.

## API Information

| Property | Value |
|----------|-------|
| Product | Hologram |
| API Version | 2022-06-01 |
| API Style | ROA (RESTful) |
| Endpoint | `hologram.{regionId}.aliyuncs.com` |

## Command Reference

### ListInstances - List All Hologres Instances

**API Endpoint:** `POST /api/v1/instances`

**CLI Command:**
```bash
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

**Request Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| resourceGroupId | string | No | Resource group ID | `rg-acfmvscak73zmby` |
| tag | array | No | Instance tags filter | `[{"key":"env","value":"prod"}]` |
| cmsInstanceType | string | No | Cloud Monitor instance type | `standard` |

**cmsInstanceType Values:**
- `standard` - Standard instance
- `follower` - Read-only follower instance
- `mc-acceleration` - MaxCompute acceleration instance
- `warehouse` - Warehouse instance
- `high-memory` - High memory instance
- `serverless` - Serverless instance

**Example Commands:**

```bash
# List all instances (no filters)
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# Filter by resource group
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{"resourceGroupId":"rg-acfmvscak73zmby"}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# Filter by tags
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{"tag":[{"key":"environment","value":"production"}]}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# Filter by CMS instance type
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{"cmsInstanceType":"standard"}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# Combined filters
aliyun hologram POST /api/v1/instances \
  --header "Content-Type=application/json" \
  --body '{"resourceGroupId":"rg-xxx","cmsInstanceType":"standard","tag":[{"key":"env","value":"prod"}]}' \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

**Response Structure:**

```json
{
  "RequestId": "D1303CD4-AA70-5998-8025-F55B22C50840",
  "InstanceList": [
    {
      "InstanceId": "hgpostcn-cn-aaab9ad2d8fb",
      "InstanceName": "test_instance",
      "InstanceStatus": "Running",
      "InstanceType": "Standard",
      "InstanceChargeType": "PrePaid",
      "RegionId": "cn-hangzhou",
      "ZoneId": "cn-hangzhou-h",
      "CreationTime": "2022-12-16T02:24:05Z",
      "ExpirationTime": "2023-05-04T16:00:00.000Z",
      "Version": "1.3.37",
      "EnableHiveAccess": "true",
      "EnableSSL": "true",
      "StorageType": "redundant",
      "ResourceGroupId": "rg-acfmvscak73zmby",
      "CommodityCode": "hologram_postpay_public_cn",
      "LeaderInstanceId": "hgprecn-cn-2r42sqvxm006",
      "SuspendReason": "Manual",
      "Tags": [{"Key": "tag", "Value": "value"}],
      "Endpoints": [
        {
          "Endpoint": "hgpostcn-cn-xxx.hologres.aliyuncs.com:80",
          "Type": "Internet",
          "Enabled": true,
          "VSwitchId": "vsw-xxx",
          "VpcId": "vpc-xxx",
          "VpcInstanceId": "hgpostcn-cn-xxx-frontend-st"
        }
      ]
    }
  ],
  "Success": "true",
  "HttpStatusCode": "200"
}
```

---

### GetInstance - Get Instance Details

**API Endpoint:** `GET /api/v1/instances/{instanceId}`

**CLI Command:**
```bash
aliyun hologram GET /api/v1/instances/{instanceId} \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

**Path Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| instanceId | string | Yes | The Hologres instance ID | `hgprecn-cn-i7m2v08uu00a` |

**Example Commands:**

```bash
# Get instance details
aliyun hologram GET /api/v1/instances/hgprecn-cn-i7m2v08uu00a \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# With specific region endpoint
aliyun hologram GET /api/v1/instances/hgpostcn-cn-aaab9ad2d8fb \
  --endpoint hologram.cn-hangzhou.aliyuncs.com \
  --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

**Response Structure:**

```json
{
  "RequestId": "865A02C2-B374-5DD4-9B34-0CA15DA1AEBD",
  "Instance": {
    "InstanceId": "hgpostcn-cn-tl32s6cgw00b",
    "InstanceName": "test",
    "InstanceStatus": "Running",
    "InstanceType": "Standard",
    "InstanceChargeType": "PrePaid",
    "InstanceOwner": "12345678900000",
    "RegionId": "cn-hangzhou",
    "ZoneId": "cn-hangzhou-h",
    "Cpu": 32,
    "Memory": 128,
    "Disk": "500",
    "ColdStorage": 800,
    "ComputeNodeCount": 2,
    "GatewayCount": 2,
    "GatewayCpu": 4,
    "GatewayMemory": 16,
    "CreationTime": "2021-02-03T13:06:06Z",
    "ExpirationTime": "2021-02-03T13:06:06Z",
    "Version": "r1.3.37",
    "AutoRenewal": "true",
    "EnableHiveAccess": "true",
    "EnableServerless": true,
    "EnableSSL": true,
    "StorageType": "redundant",
    "ResourceGroupId": "rg-aekzuq7hpybze2i",
    "CommodityCode": "hologram_combo_public_cn",
    "LeaderInstanceId": "hgpostcn-cn-i7m2ncd6w002",
    "SuspendReason": "Manual",
    "ReplicaRole": "Active",
    "Tags": [{"Key": "tag", "Value": "value"}],
    "Endpoints": [
      {
        "Endpoint": "hgprecn-cn-xxx.hologres.aliyuncs.com:80",
        "Type": "Internet",
        "Enabled": true,
        "VSwitchId": "vsw-bp1jqwp2ys6kp7tc9t983",
        "VpcId": "vpc-uf66jjber3hgvwhki3wna",
        "VpcInstanceId": "hgprecn-cn-uqm362o1b001-frontend-st",
        "AlternativeEndpoints": "hgprecn-cn-xxx.hologres.aliyuncs.com:80"
      }
    ]
  },
  "Success": true,
  "HttpStatusCode": "200"
}
```

---

## Response Field Reference

### Instance Status Values

| Value | Description |
|-------|-------------|
| Creating | Instance is being created |
| Running | Instance is running normally |
| Suspended | Instance is suspended |
| Allocating | Instance is being allocated |

### Instance Type Values

| Value | Description |
|-------|-------------|
| Standard | Standard instance |
| Warehouse | Compute group instance |
| Follower | Read-only follower instance |
| Serverless | Serverless instance |
| Shared | Shared instance |

### Instance Charge Type Values

| Value | Description |
|-------|-------------|
| PostPaid | Pay-as-you-go |
| PrePaid | Subscription (yearly/monthly) |

### Endpoint Type Values

| Value | Description |
|-------|-------------|
| VPCSingleTunnel | VPC private network |
| Intranet | Internal network |
| Internet | Public network |
| VPCAnyTunnel | (Deprecated for new instances) |

### Storage Type Values

| Value | Description |
|-------|-------------|
| redundant | 3-AZ redundant storage |
| local | Single-AZ local storage |

### Suspend Reason Values

| Value | Description |
|-------|-------------|
| Indebet | Suspended due to overdue payment |
| Manual | Manually suspended |
| Overdue | Subscription expired |

---

## Quick Reference

| Action | HTTP Method | Path | Description |
|--------|-------------|------|-------------|
| ListInstances | POST | `/api/v1/instances` | List all instances |
| GetInstance | GET | `/api/v1/instances/{instanceId}` | Get instance details |

## Important Notes

1. **User-Agent Header**: All commands must include `--user-agent AlibabaCloud-Agent-Skills`
2. **Timeout**: All commands must include `--read-timeout 4` (4 seconds)
3. **Content-Type**: POST requests require `--header "Content-Type=application/json"`
4. **ROA Style**: These APIs use RESTful style, not RPC
5. **Region**: Ensure you're querying the correct region where instances exist
6. **Credentials**: Rely on default credential chain; never handle AK/SK explicitly
