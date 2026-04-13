# Related APIs - Elasticsearch Instance Network Management

This document lists all APIs and CLI commands related to Elasticsearch instance network management.

---

## Important Constraints

> **Required Parameter Handling Principles**
>
> - **No guessing**: If user does not provide required parameters, Agent is **prohibited** from guessing or fabricating parameter values
> - **Must ask**: When required parameters are missing, must ask user and obtain exact values before executing
> - **Clear notification**: Inform user which required parameters are missing, their purpose and format requirements
>
> **Core Required Parameters (needed for all operations):**
>
> | Parameter | Description | Requirement |
> |-----------|-------------|-------------|
> | `InstanceId` | Elasticsearch Instance ID | **Must be provided by user**, format like `es-cn-xxxxxx`, no guessing or using example values |
> | `RegionId` | Region ID | **Must be provided or confirmed by user**, like `cn-hangzhou`, `cn-shanghai`, no assuming defaults |
>
> **Other Required Parameters Example:**
>
> EnableKibanaPvlNetwork also requires `vpcId`, `vswitchId`, `zoneId`, `securityGroups` etc. If user does not provide them, must ask user to obtain them; cannot use example or default values.

---

## API List

### 1. TriggerNetwork - Enable/Disable Public/Private Network Access

| Property | Value |
|----------|-------|
| **API** | TriggerNetwork |
| **HTTP Method** | POST |
| **Path** | /openapi/instances/{InstanceId}/actions/network-trigger |
| **CLI Command** | `aliyun elasticsearch trigger-network` |
| **Description** | Enable or disable public or private network access for Elasticsearch or Kibana clusters |

**Request Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| InstanceId | String | Path | Yes | Instance ID |
| clientToken | String | Query | No | For request idempotency, max 64 ASCII characters |
| nodeType | String | Body | Yes | Instance type: KIBANA (Kibana cluster) / WORKER (Elasticsearch cluster) |
| networkType | String | Body | Yes | Network type: PUBLIC / PRIVATE |
| actionType | String | Body | Yes | Action type: OPEN (enable) / CLOSE (disable) |

**CLI Examples:**

```bash
# Enable Kibana public network access
aliyun elasticsearch trigger-network \
  --instance-id es-cn-xxxxxx \
  --body '{
    "nodeType": "KIBANA",
    "networkType": "PUBLIC",
    "actionType": "OPEN"
  }' \
  --user-agent AlibabaCloud-Agent-Skills

# Disable Elasticsearch public network access
aliyun elasticsearch trigger-network \
  --instance-id es-cn-xxxxxx \
  --body '{
    "nodeType": "WORKER",
    "networkType": "PUBLIC",
    "actionType": "CLOSE"
  }' \
  --user-agent AlibabaCloud-Agent-Skills

# Enable Elasticsearch private network access
aliyun elasticsearch trigger-network \
  --instance-id es-cn-xxxxxx \
  --body '{
    "nodeType": "WORKER",
    "networkType": "PRIVATE",
    "actionType": "OPEN"
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameter Values:**

| Parameter | Values | Description |
|-----------|--------|-------------|
| nodeType | KIBANA | Kibana cluster |
| nodeType | WORKER | Elasticsearch cluster |
| networkType | PUBLIC | Public network |
| networkType | PRIVATE | Private network |
| actionType | OPEN | Enable |
| actionType | CLOSE | Disable |

**Restrictions:**
- Only supports **basic management architecture** instances (archType != public)
- For cloud-native instances, use EnableKibanaPvlNetwork / DisableKibanaPvlNetwork

---

### 2. EnableKibanaPvlNetwork - Enable Kibana Private Network Access

| Property | Value |
|----------|-------|
| **API** | EnableKibanaPvlNetwork |
| **HTTP Method** | POST |
| **Path** | /openapi/instances/{InstanceId}/actions/enable-kibana-private |
| **CLI Command** | `aliyun elasticsearch enable-kibana-pvl-network` |
| **Description** | Enable Kibana private network access (PrivateLink) for Elasticsearch instance |

> **Prerequisites**:
> 1. This API **only supports cloud-native instances** (archType=public). For basic management instances, use TriggerNetwork
> 2. Kibana specification must be **greater than 1 core 2GB**

**Request Parameters (Path):**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| InstanceId | String | Path | Yes | Instance ID |

**Request Parameters (Body):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| endpointName | String | Yes | Endpoint name, recommended format: `{InstanceId}-kibana-endpoint` |
| securityGroups | Array<String> | Yes | Security group ID array |
| vSwitchIdsZone | Array | Yes | VSwitch and availability zone information |
| vSwitchIdsZone[].vswitchId | String | Yes | Virtual switch ID |
| vSwitchIdsZone[].zoneId | String | Yes | Availability zone ID |
| vpcId | String | Yes | VPC instance ID |

**CLI Examples:**

```bash
# Enable Kibana private network access (full parameters)
aliyun elasticsearch enable-kibana-pvl-network \
  --instance-id es-cn-xxxxxx \
  --body '{
    "endpointName": "es-cn-xxxxxx-kibana-endpoint",
    "securityGroups": ["sg-bp1abqv5dbxwcsabumv1"],
    "vSwitchIdsZone": [
      {
        "vswitchId": "vsw-bp1x936kmfj670gzt0l6g",
        "zoneId": "cn-hangzhou-i"
      }
    ],
    "vpcId": "vpc-bp156dwhpk7x1fuix74h3"
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Get Required Parameters:**

```bash
# Get VPC and VSwitch info from instance details
aliyun elasticsearch describe-instance \
  --instance-id es-cn-xxxxxx | jq '.Result.networkConfig | {vpcId, vswitchId, vsArea}'

# Query security groups under VPC
aliyun ecs DescribeSecurityGroups \
  --VpcId vpc-xxxxxx \
  --RegionId cn-hangzhou | jq '.SecurityGroups.SecurityGroup[] | {SecurityGroupId, SecurityGroupName}'
```

---

### 3. DisableKibanaPvlNetwork - Disable Kibana Private Network Access

| Property | Value |
|----------|-------|
| **API** | DisableKibanaPvlNetwork |
| **HTTP Method** | DELETE |
| **Path** | /openapi/instances/{InstanceId}/kibana-private-network |
| **CLI Command** | `aliyun elasticsearch disable-kibana-pvl-network` |
| **Description** | Disable Kibana private network access for Elasticsearch instance |

> **Prerequisites**: This API **only supports cloud-native instances** (archType=public). For basic management instances, use TriggerNetwork.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |
| resourceGroupId | String | No | Resource group ID |

**CLI Examples:**

```bash
# Disable Kibana PVL
aliyun elasticsearch disable-kibana-pvl-network \
  --instance-id es-cn-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills

# With resource group specified
aliyun elasticsearch disable-kibana-pvl-network \
  --instance-id es-cn-xxxxxx \
  --resource-group-id rg-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 4. UpdateKibanaPvlNetwork - Update Kibana Private Network Access Configuration

| Property | Value |
|----------|-------|
| **API** | UpdateKibanaPvlNetwork |
| **HTTP Method** | POST |
| **Path** | /openapi/instances/{InstanceId}/actions/update-kibana-private |
| **CLI Command** | `aliyun elasticsearch update-kibana-pvl-network` |
| **Description** | Update Kibana private network access information, mainly for modifying security groups |

> **Prerequisites**:
> 1. This API **only supports cloud-native instances** (archType=public). For basic management instances, use TriggerNetwork
> 2. Kibana specification must be **greater than 1 core 2GB**
> 3. Instance must have Kibana private network access enabled

**Use Case**: Use this API when cloud-native instances need to modify Kibana private network access security groups (whitelist control), because ModifyWhiteIps does not support Kibana private network whitelist modification for cloud-native instances.

**Request Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| InstanceId | String | Path | Yes | Instance ID |
| pvlId | String | Query | Yes | Kibana private network connection ID, format: `{InstanceId}-kibana-internal-internal` |
| endpointName | String | Body | No | Endpoint name |
| securityGroups | Array<String> | Body | No | Security group ID array |

**CLI Examples:**

```bash
# Update Kibana private network access security groups
aliyun elasticsearch update-kibana-pvl-network \
  --instance-id es-cn-xxxxxx \
  --pvl-id es-cn-xxxxxx-kibana-internal-internal \
  --body '{"securityGroups": ["sg-bp1newgroup123"]}' \
  --user-agent AlibabaCloud-Agent-Skills

# Update both endpoint name and security groups
aliyun elasticsearch update-kibana-pvl-network \
  --instance-id es-cn-xxxxxx \
  --pvl-id es-cn-xxxxxx-kibana-internal-internal \
  --body '{"endpointName": "new-kibana-endpoint", "securityGroups": ["sg-bp1newgroup123"]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**pvlId Description:**
- Format is `{InstanceId}-kibana-internal-internal`
- For example, if instance ID is `es-cn-xxxxxx`, then pvlId is `es-cn-xxxxxx-kibana-internal-internal`

---

### 5. ModifyWhiteIps - Modify Whitelist

| Property | Value |
|----------|-------|
| **API** | ModifyWhiteIps |
| **HTTP Method** | PATCH/POST |
| **Path** | /openapi/instances/{InstanceId}/actions/modify-white-ips |
| **CLI Command** | `aliyun elasticsearch modify-white-ips` |
| **Description** | Update access whitelist for specified instance, supports two methods: IP whitelist and IP whitelist groups |

> **Notes**: 
> - Cannot update when instance status is activating, invalid, or inactive
> - Cannot use both methods simultaneously
> - Public network whitelist does not support private IPs; private network whitelist does not support public IPs
> - **Cloud-native instances (archType=public) Kibana private network whitelist cannot be modified through this API**, use UpdateKibanaPvlNetwork API via security group changes instead

**Request Parameters (Path/Query):**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| InstanceId | String | Path | Yes | Instance ID |
| clientToken | String | Query | No | For request idempotency, max 64 ASCII characters |

**Method 1: IP Whitelist (Body Parameters)**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| whiteIpList | Array<String> | Yes | IP whitelist, will update Default group |
| nodeType | String | Yes | Node type: WORKER (ES cluster) / KIBANA |
| networkType | String | Yes | Network type: PUBLIC / PRIVATE |

**Method 2: IP Whitelist Group (Body Parameters)**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| modifyMode | String | No | Modify mode: Cover (overwrite, default) / Append / Delete |
| whiteIpGroup.groupName | String | Yes | Whitelist group name |
| whiteIpGroup.ips | Array<String> | Yes | IP address list |
| whiteIpGroup.whiteIpType | String | No | Whitelist type (see table below) |

**whiteIpType Values:**

| Value | Description |
|-------|-------------|
| `PRIVATE_ES` | Elasticsearch private network whitelist |
| `PUBLIC_ES` | Elasticsearch public network whitelist |
| `PRIVATE_KIBANA` | Kibana private network whitelist |
| `PUBLIC_KIBANA` | Kibana public network whitelist |

**CLI Examples:**

```bash
# Method 1: IP whitelist - Modify ES public network whitelist
aliyun elasticsearch modify-white-ips \
  --instance-id es-cn-xxxxxx \
  --body '{"nodeType":"WORKER","networkType":"PUBLIC","whiteIpList":["59.0.0.0/8","120.0.0.0/8"]}' \
  --user-agent AlibabaCloud-Agent-Skills

# Method 1: IP whitelist - Modify ES private network whitelist
aliyun elasticsearch modify-white-ips \
  --instance-id es-cn-xxxxxx \
  --body '{"nodeType":"WORKER","networkType":"PRIVATE","whiteIpList":["192.168.1.0/24","10.0.0.0/8"]}' \
  --user-agent AlibabaCloud-Agent-Skills

# Method 2: IP whitelist group - Cover mode
aliyun elasticsearch modify-white-ips \
  --instance-id es-cn-xxxxxx \
  --body '{"modifyMode":"Cover","whiteIpGroup":{"groupName":"default","ips":["59.0.0.0/8","120.0.0.0/8"],"whiteIpType":"PUBLIC_ES"}}' \
  --user-agent AlibabaCloud-Agent-Skills

# Method 2: IP whitelist group - Append mode (group must exist)
aliyun elasticsearch modify-white-ips \
  --instance-id es-cn-xxxxxx \
  --body '{"modifyMode":"Append","whiteIpGroup":{"groupName":"default","ips":["172.16.0.0/12"],"whiteIpType":"PRIVATE_ES"}}' \
  --user-agent AlibabaCloud-Agent-Skills

# Method 2: IP whitelist group - Delete mode (at least one IP must remain)
aliyun elasticsearch modify-white-ips \
  --instance-id es-cn-xxxxxx \
  --body '{"modifyMode":"Delete","whiteIpGroup":{"groupName":"default","ips":["192.168.1.100"],"whiteIpType":"PRIVATE_ES"}}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**modifyMode Description:**

| Mode | Description |
|------|-------------|
| `Cover` | Cover mode (default). Empty ips deletes the group, non-existent groupName creates new |
| `Append` | Append mode. Group must exist, otherwise NotFound error |
| `Delete` | Delete mode. Remove specified IPs, at least one IP must remain |

---

### 6. OpenHttps - Enable HTTPS

| Property | Value |
|----------|-------|
| **API** | OpenHttps |
| **HTTP Method** | POST |
| **Path** | /openapi/instances/{InstanceId}/actions/open-https |
| **CLI Command** | `aliyun elasticsearch open-https` |
| **Description** | Enable HTTPS access for Elasticsearch instance |

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |
| resourceGroupId | String | No | Resource group ID |

**CLI Examples:**

```bash
# Enable HTTPS
aliyun elasticsearch open-https \
  --instance-id es-cn-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills

# With resource group specified
aliyun elasticsearch open-https \
  --instance-id es-cn-xxxxxx \
  --resource-group-id rg-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 7. CloseHttps - Disable HTTPS

| Property | Value |
|----------|-------|
| **API** | CloseHttps |
| **HTTP Method** | POST |
| **Path** | /openapi/instances/{InstanceId}/actions/close-https |
| **CLI Command** | `aliyun elasticsearch close-https` |
| **Description** | Disable HTTPS access for Elasticsearch instance |

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |
| resourceGroupId | String | No | Resource group ID |

**CLI Examples:**

```bash
# Disable HTTPS
aliyun elasticsearch close-https \
  --instance-id es-cn-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills

# With resource group specified
aliyun elasticsearch close-https \
  --instance-id es-cn-xxxxxx \
  --resource-group-id rg-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 8. DescribeInstance - View Instance Details

| Property | Value |
|----------|-------|
| **API** | DescribeInstance |
| **HTTP Method** | GET |
| **Path** | /openapi/instances/{InstanceId} |
| **CLI Command** | `aliyun elasticsearch describe-instance` |
| **Description** | View detailed information of Elasticsearch instance, used to verify network configuration changes |

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| InstanceId | String | Yes | Instance ID |

**CLI Examples:**

```bash
# View instance details
aliyun elasticsearch describe-instance \
  --instance-id es-cn-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills

# Check architecture type (for TriggerNetwork support)
aliyun elasticsearch describe-instance \
  --instance-id es-cn-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills | jq '.Result.archType'
```

**Response Fields (Network Related):**

| Field | Type | Description |
|-------|------|-------------|
| archType | String | Architecture type: exclusive (basic management) / public (cloud-native) |
| status | String | Instance status (e.g., active) |
| enablePublic | Boolean | Whether cluster public network is enabled |
| enableKibanaPublicNetwork | Boolean | Whether Kibana public network is enabled |
| enableKibanaPrivateNetwork | Boolean | Whether Kibana private network is enabled |
| protocol | String | Instance protocol: HTTP or HTTPS (use this to check HTTPS status) |
| networkConfig | Object | Network configuration |
| networkConfig.vpcId | String | VPC ID |
| networkConfig.vswitchId | String | VSwitch ID |
| networkConfig.whiteIpList | Array | Whitelist |
| kibanaConfiguration | Object | Kibana configuration |

---

## API Version Information

| Property | Value |
|----------|-------|
| Product | elasticsearch |
| API Version | 2017-06-13 |
| Endpoint | elasticsearch.{regionId}.aliyuncs.com |

---

## Architecture Type Description

### archType Field

| Value | Description | Network Features |
|-------|-------------|------------------|
| `exclusive` | Basic management | Supports TriggerNetwork |
| `public` | Cloud-native | Does not support TriggerNetwork for Kibana private network, use EnableKibanaPvlNetwork/DisableKibanaPvlNetwork instead |

### Check Architecture Type

```bash
# Check instance architecture type
arch_type=$(aliyun elasticsearch describe-instance \
  --instance-id es-cn-xxxxxx \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Result.archType')

if [ "$arch_type" == "public" ]; then
  echo "Cloud-native instance"
else
  echo "Basic management instance"
fi
```

---

## Reference Links

- [TriggerNetwork API Documentation](https://help.aliyun.com/zh/es/developer-reference/api-triggernetwork)
- [EnableKibanaPvlNetwork API Documentation](https://help.aliyun.com/zh/es/developer-reference/api-enablekibanapvlnetwork)
- [DisableKibanaPvlNetwork API Documentation](https://help.aliyun.com/zh/es/developer-reference/api-disablekibanapvlnetwork)
- [ModifyWhiteIps API Documentation](https://help.aliyun.com/zh/es/developer-reference/api-modifywhiteips)
- [OpenHttps API Documentation](https://help.aliyun.com/zh/es/developer-reference/api-openhttps)
- [CloseHttps API Documentation](https://help.aliyun.com/zh/es/developer-reference/api-closehttps)
- [DescribeInstance API Documentation](https://help.aliyun.com/zh/es/developer-reference/api-describeinstance)
