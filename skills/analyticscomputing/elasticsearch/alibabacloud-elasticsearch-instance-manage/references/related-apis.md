# Related APIs - Elasticsearch Instance Management

This document lists all CLI commands and APIs used in the Elasticsearch Instance Management Skill.

## Table of Contents

- [API Overview](#api-overview)
  - [Using --body Parameter](#using---body-parameter)
- [API Details](#api-details)
  - [1. createInstance - Create Elasticsearch Instance](#1-createinstance---create-elasticsearch-instance)
  - [2. DescribeInstance - Query Instance Details](#2-describeinstance---query-instance-details)
  - [3. ListInstance - List Instances](#3-listinstance---list-instances)
  - [4. RestartInstance - Restart Instance](#4-restartinstance---restart-instance)
  - [5. ListAllNode - Query Cluster Node Information](#5-listallnode---query-cluster-node-information)
  - [6. UpdateInstance - Upgrade/Downgrade Instance Configuration](#6-updateinstance---upgradedowngrade-instance-configuration)
- [Instance Status Reference](#instance-status-reference)
- [Elasticsearch Version Reference](#elasticsearch-version-reference)
- [Official Documentation](#official-documentation)

---

## API Overview

> **Note on API Style:** Elasticsearch APIs use **ROA (RESTful)** style. This means:
> - Parameters can be passed via `--body` as a JSON string representing the HTTP request body
> - Alternatively, individual flags can be used for simple parameters
> - The `--body` approach is useful for complex nested structures or when you have a ready-to-use JSON payload

### Using `--body` Parameter

The `--body` parameter allows you to specify the HTTP request body as a JSON string for RESTful API calls:

```bash
aliyun elasticsearch <command> \
  --region <RegionId> \
  --body '<JSON_PAYLOAD>' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example:**
```bash
aliyun elasticsearch create-instance \
  --region cn-hangzhou \
  --body '{
    "esAdminPassword": "YourPassword123!",
    "esVersion": "7.10_with_X-Pack",
    "nodeAmount": 2,
    "networkConfig": {
      "vpcId": "vpc-bp1xxx",
      "vswitchId": "vsw-bp1xxx",
      "type": "vpc"
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Tips:**
- Use `--body $(cat payload.json)` to read from a file
- For complex nested objects, `--body` is often more readable than multiple flags
- Both `--body` and individual flags can be used together (flags take precedence)

| Product | CLI Command | API Action | Description |
|---------|------------|------------|-------------|
| Elasticsearch | `aliyun elasticsearch create-instance` | createInstance | Create Elasticsearch Instance |
| Elasticsearch | `aliyun elasticsearch describe-instance` | DescribeInstance | Query Instance Details |
| Elasticsearch | `aliyun elasticsearch list-instance` | ListInstance | List ES Instances in a Region |
| Elasticsearch | `aliyun elasticsearch list-all-node` | ListAllNode | Query All Cluster Node Information |
| Elasticsearch | `aliyun elasticsearch restart-instance` | RestartInstance | Restart Elasticsearch Cluster |
| Elasticsearch | `aliyun elasticsearch update-instance` | UpdateInstance | Upgrade/Downgrade Instance Configuration |

---

## API Details

> **Idempotency:** For write operations (createInstance, RestartInstance, UpdateInstance), you **MUST** use the `--client-token` parameter to ensure idempotency for safe retries when requests time out.

### 1. createInstance - Create Elasticsearch Instance

> **⚠️ CRITICAL: Required Parameters and Region Validation**
>
> **1. region Parameter (Required and Must Be Validated)**
>
> The `--region` parameter **MUST be explicitly provided by the user**. Agents **MUST NOT guess or use default values**.
>
> **Pre-execution Check Steps:**
> 1. Check if the user has provided the `--region` parameter
> 2. If region is missing, **immediately ask the user**:
>    ```
>    Please provide the region where the instance is located, e.g., cn-hangzhou, cn-shanghai, cn-beijing, etc.
>    ```
> 3. If the user has provided a region, **validate its legitimacy**:
>    - Valid Alibaba Cloud region format starts with `cn-` or `ap-` prefix
>    - Common valid regions: `cn-hangzhou`, `cn-shanghai`, `cn-beijing`, `cn-shenzhen`, `cn-zhangjiakou`, `cn-hongkong`, `ap-southeast-1`, etc.
> 4. If the region is obviously invalid (e.g., empty string, pure numbers, contains special characters), **prompt the user**:
>    ```
>    The provided region "{region}" does not appear to be a valid Alibaba Cloud region.
>    Please provide a valid region ID, e.g., cn-hangzhou, cn-shanghai, cn-beijing, etc.
>    ```
>
> **Prohibited Behaviors:**
> - ❌ Do NOT use a default region (such as cn-hangzhou) to replace the user-specified region
> - ❌ Do NOT assume the user wants to create an instance in a specific region
>
> ---
>
> **2. Other Required Parameters**
>
> When creating an ES instance, the following parameters **MUST be explicitly provided by the user**. Agents **MUST NOT guess or fabricate** these values:
>
> | Parameter | Description | Example |
> |------|------|------|
> | `esAdminPassword` | Instance admin password | `YourPassword123!` |
> | `vpcId` | VPC Network ID | `vpc-bp1xxx` |
> | `vswitchId` | VSwitch ID | `vsw-bp1xxx` |
> | `vsArea` | Availability Zone ID | `cn-hangzhou-i` |
> | `paymentType` | Payment type (`postpaid` or `prepaid`) | `postpaid` |
>
> **Pre-execution Check Steps:**
> 1. Check if the user has provided all required parameters above
> 2. If any are missing, **immediately stop and prompt the user to provide**, in this format:
>    ```
>    The following parameters are required to create an ES instance, please provide:
>    - [ ] Instance password (esAdminPassword): ___
>    - [ ] VPC ID (vpcId): ___
>    - [ ] VSwitch ID (vswitchId): ___
>    - [ ] Availability Zone (vsArea): ___
>    - [ ] Payment Type (paymentType): postpaid/prepaid
>    ```
> 3. Wait for the user to explicitly provide before continuing with the create command
>
> **Prohibited Behaviors:**
> - ❌ Do NOT use example values as actual parameters
> - ❌ Do NOT guess vsArea based on region
> - ❌ Do NOT use default passwords or fabricate passwords
> - ❌ Do NOT assume the user's VPC or vswitch ID

**API Style:** ROA (RESTful)


**CLI Command (using --body for RESTful HTTP body):**
```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun elasticsearch create-instance \
  --region <RegionId> \
  --client-token $CLIENT_TOKEN \
  --body '{
    "esAdminPassword": "<Password>",
    "esVersion": "<Version>",
    "nodeAmount": <NodeCount>,
    "nodeSpec": {
      "disk": <DiskSize>,
      "diskType": "<DiskType>",
      "spec": "<Spec>"
    },
    "networkConfig": {
      "vpcId": "<VpcId>",
      "vswitchId": "<VswitchId>",
      "vsArea": "<ZoneId>",
      "type": "vpc"
    },
    "paymentType": "<postpaid|prepaid>"
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--es-admin-password` | string | Instance access password, must contain at least 3 of: uppercase letters, lowercase letters, numbers, special characters, length 8~32 |
| `--es-version` | string | Instance version, e.g., `7.10_with_X-Pack`, `7.16_with_X-Pack`, `8.5.1_with_X-Pack`, `8.15.1_with_X-Pack`, `8.17.0_with_X-Pack` |
| `--node-amount` | int | Number of data nodes, range 2~50 |
| `--network-config` | object | Network configuration, including vpcId, vswitchId, vsArea, type |
| `--client-token` | string | Idempotency token for safe retries, UUID format |


**networkConfig Parameter Format**
```json
{
    "networkConfig": {
      "vpcId": "<VpcId>",
      "vswitchId": "<VswitchId>",
      "vsArea": "<ZoneId>",
      "type": "vpc"
    }
}
```
Parameter type is fixed to vpc

Parameter vswitchId: Only supports one vswitchId. For multi-AZ instances, only one vswitchId needs to be provided.

Parameter vsArea: The availability zone where the vswitchId is located, only supports one.

Note: For multi-AZ instances, only the primary availability zone's vswitchId needs to be provided.


**Optional Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--node-spec` | object | Data node configuration: spec, disk (size in GB), diskType |
| `--payment-type` | string | Payment type: `postpaid` (pay-as-you-go), `prepaid` (subscription) |
| `--kibana-configuration` | object | Kibana node configuration |
| `--master-configuration` | object | Dedicated master node configuration |
| `--description` | string | Instance name |
| `--zone-count` | int | Number of availability zones, options: 1, 2, 3 |

**Response:**
```json
{
  "RequestId": "838D9D11-8EEF-46D8-BF0D-BC8FC2B0C2F3",
  "Result": {
    "instanceId": "es-cn-xxx****"
  }
}
```

---

### 2. DescribeInstance - Query Instance Details

> **⚠️ CRITICAL: Required User-Provided Parameters**
>
> When querying instance details, the following parameters **MUST be explicitly provided by the user**. Agents **MUST NOT guess or fabricate** these values:
>
> | Parameter | Description | Example |
> |------|------|------|
> | `--region` | Region where the instance is located | `cn-hangzhou` |
> | `--instance-id` | Instance ID | `es-cn-xxx****` |
>
> **Pre-execution Check Steps:**
> 1. Check if the user has provided region and instance ID
> 2. If region is missing, **immediately ask the user**:
>    ```
>    Please provide the region where the instance is located, e.g., cn-hangzhou, cn-shanghai, cn-beijing, etc.
>    ```
> 3. Wait for the user to explicitly provide before executing the query command
>
> **Prohibited Behaviors:**
> - ❌ Do NOT use a default region (such as cn-hangzhou) to replace the user-specified region
> - ❌ Do NOT guess region based on instance ID
> - ❌ Do NOT assume the instance is in a specific region

**CLI Command:**
```bash
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--instance-id` | string | Instance ID |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `instanceId` | string | Instance ID |
| `description` | string | Instance name |
| `status` | string | Instance status |
| `esVersion` | string | Elasticsearch version |
| `nodeAmount` | int | Number of data nodes |
| `paymentType` | string | Payment type |
| `domain` | string | Internal access address |
| `port` | int | Access port |
| `kibanaDomain` | string | Kibana access address |
| `kibanaPort` | int | Kibana port |

---

### 3. ListInstance - List Instances

> **⚠️ CRITICAL: Required Parameters and Parameter Validation**
>
> **1. region Parameter (Required)**
>
> The `--region` parameter **MUST be explicitly provided by the user**. Agents **MUST NOT guess or use default values**.
>
> | Parameter | Description | Example |
> |------|------|------|
> | `--region` | Region where instances are located | `cn-hangzhou` |
>
> **Pre-execution Check Steps:**
> 1. Check if the user has provided a region
> 2. If region is missing, **immediately ask the user**:
>    ```
>    Please provide the region where instances are located, e.g., cn-hangzhou, cn-shanghai, cn-beijing, etc.
>    ```
> 3. Wait for the user to explicitly provide before executing the query command
>
> **Prohibited Behaviors:**
> - ❌ Do NOT use a default region (such as cn-hangzhou) to replace the user-specified region
> - ❌ Do NOT assume instances are in a specific region
>
> ---
>
> **2. status Parameter Validation**
>
> When the user specifies the `--status` parameter, Agents **MUST validate the parameter value**.
>
> **Valid Values (case-sensitive, only the following values are supported):**
> | Value | Description |
> |------|------|
> | `activating` | Activating (restarting or configuration changing) |
> | `active` | Running normally |
> | `inactive` | Stopped |
> | `invalid` | Invalid |
>
> **Pre-execution Check Steps:**
> 1. Check if the user-provided status value is one of the valid values above
> 2. If the value is invalid, **immediately prompt the user**:
>    ```
>    The status parameter value is invalid. Valid values are: activating, active, inactive, invalid
>    Please provide a valid status value.
>    ```
> 3. Wait for the user to provide a valid value before executing the query command
>
> **Prohibited Behaviors:**
> - ❌ Do NOT guess or transform the user-provided status value
> - ❌ Do NOT ignore the user-provided value and query directly

**CLI Command:**
```bash
aliyun elasticsearch list-instance \
  --region <RegionId> \
  --page <PageNumber> \
  --size <PageSize> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Optional Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--page` | int | Page number, starting from 1, default 1 |
| `--size` | int | Items per page, max 100, default 10 |
| `--description` | string | Instance name, supports fuzzy search |
| `--instance-id` | string | Instance ID |
| `--es-version` | string | Instance version |
| `--vpc-id` | string | VPC ID |
| `--zone-id` | string | Availability Zone ID |
| `--status` | string | Instance status, **only supports activating, active, inactive, invalid** |
| `--payment-type` | string | Payment type |

**Response:**
```json
{
  "RequestId": "5FFD9ED4-C2EC-4E89-B22B-1ACB6FE1****",
  "Headers": {
    "X-Total-Count": 10
  },
  "Result": [
    {
      "instanceId": "es-cn-xxx****",
      "description": "my-es-instance",
      "status": "active",
      "esVersion": "7.10_with_X-Pack",
      "nodeAmount": 2,
      "paymentType": "postpaid"
    }
  ]
}
```

---

### 4. RestartInstance - Restart Instance

When restarting, it is recommended to first check the instance status and only proceed with the restart operation when the instance status is active.

**API Style:** ROA (RESTful)


**CLI Command (using --body for RESTful HTTP body):**

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun elasticsearch restart-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_BODY>' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--instance-id` | string | Instance ID |
| `--client-token` | string | Idempotency token for safe retries, UUID format |

**Optional Parameters (flags):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--force` | bool | Whether to force restart, ignoring cluster status |

**Request Body Parameters (via --body):**

| Field | Type | Description |
|-------|------|-------------|
| `restartType` | string | Restart type: `instance` (instance restart), `nodeIp` (node restart) |
| `nodes` | list | Node IP list to restart (when nodeIp type) |
| `blueGreenDep` | bool | Whether to enable blue-green deployment |
| `batchCount` | double | Concurrency for force restart |
| `force` | bool | Whether to force restart |

**Examples:**

```bash
# Generate idempotency token (use the same token when retrying after timeout)
CLIENT_TOKEN=$(uuidgen)

# Using flags
aliyun elasticsearch restart-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --force true \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills

# Using --body for simple restart
aliyun elasticsearch restart-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"restartType":"instance"}' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills

# Using --body for force restart
aliyun elasticsearch restart-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"restartType":"instance","force":true}' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills

# Using --body for restarting specific nodes
aliyun elasticsearch restart-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"restartType":"nodeIp","nodes":["10.0.XX.XX","10.0.XX.XX"]}' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response:**
```json
{
  "RequestId": "F99407AB-2FA9-489E-A259-40CF6DC****",
  "Result": {
    "instanceId": "es-cn-xxx****",
    "status": "activating"
  }
}
```

---

### 5. ListAllNode - Query Cluster Node Information

**CLI Command:**
```bash
aliyun elasticsearch list-all-node \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--instance-id` | string | Instance ID |

**Optional Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--extended` | bool | Whether to return node monitoring information, default true |

**Response:**
```json
{
  "RequestId": "0D71B597-F3FF-5B56-88D7-74F9D3F7****",
  "Result": [
    {
      "host": "10.15.XX.XX",
      "nodeType": "WORKER",
      "health": "GREEN",
      "cpuPercent": "4.2%",
      "heapPercent": "21.6%",
      "diskUsedPercent": "1.0%",
      "loadOneM": "0.12",
      "zoneId": "cn-hangzhou-i",
      "port": 9200
    }
  ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `host` | string | Node IP address |
| `nodeType` | string | Node type: MASTER/WORKER/WORKER_WARM/COORDINATING/KIBANA |
| `health` | string | Node health status: GREEN/YELLOW/RED/GRAY |
| `cpuPercent` | string | CPU usage rate |
| `heapPercent` | string | JVM memory usage rate |
| `diskUsedPercent` | string | Disk usage rate |
| `loadOneM` | string | One minute load |
| `zoneId` | string | Availability zone where the node is located |
| `port` | int | Node access port |

**Node Type Reference:**

| Type | Description |
|------|-------------|
| `MASTER` | Dedicated master node |
| `WORKER` | Hot node (data node) |
| `WORKER_WARM` | Cold node |
| `COORDINATING` | Coordinating node |
| `KIBANA` | Kibana node |

---

### 6. UpdateInstance - Upgrade/Downgrade Instance Configuration

> **⚠️ CRITICAL: Pre-update Status Check and Constraints**
>
> **1. Instance Status Check (Required)**
>
> Before executing an update operation, you **MUST** first query the instance status using `describe-instance` and confirm it is `active`.
> - **Only when the instance status is `active` can you execute the update operation**
> - **If the instance status is `activating`, `inactive`, or `invalid`, update operation is prohibited**
>
> **2. Single Node Type Per Call**
>
> Each update call can only change **one type of node**. The supported node types are:
> - Data node (`nodeAmount` / `nodeSpec`)
> - Dedicated master node (`masterConfiguration`)
> - Cold data node (`warmNodeConfiguration`)
> - Coordinating node (`clientNodeConfiguration`)
> - Kibana node (`kibanaConfiguration`)
> - Elastic data node (`elasticDataNodeConfiguration`)
>
> You **CAN** change multiple attributes of the **same** node type in one call (e.g., both `amount` and `spec` for coordinating nodes).
>
> **3. Upgrade vs Downgrade Rules**
>
> | Rule | Upgrade (default) | Downgrade (`orderActionType=downgrade`) |
> |------|-------------------|----------------------------------------|
> | Storage size | Can increase | Cannot decrease |
> | Storage type | Can upgrade | Can downgrade |
> | Node count | Can increase | Cannot decrease (use ShrinkNode API) |
> | Spec (CPU/Memory) | Can increase | Can decrease |
> | Force change | Supported | Not supported |
> | updateType | Supported | Not supported (smart change only) |
>
> **Prohibited Behaviors:**
> - ❌ Do NOT attempt to change multiple node types in a single call
> - ❌ Do NOT reduce node count via UpdateInstance (use ShrinkNode instead)
> - ❌ Do NOT reduce storage size in either upgrade or downgrade
> - ❌ Do NOT disable already-enabled nodes
> - ❌ Do NOT guess node specifications - refer to [node-specifications-by-region.md](node-specifications-by-region.md)

**API Style:** ROA (RESTful)

**CLI Command (using --body for RESTful HTTP body):**

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

# Upgrade (default orderActionType=upgrade)
aliyun elasticsearch update-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_BODY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Downgrade (must set orderActionType=downgrade)
aliyun elasticsearch update-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --order-action-type downgrade \
  --body '<JSON_BODY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Required Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--instance-id` | string | Instance ID |
| `--client-token` | string | Idempotency token for safe retries, UUID format |

**Optional Parameters (query):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `--order-action-type` | string | Change type: `upgrade` (default) or `downgrade` |
| `--force` | bool | Whether to force change (only for upgrade), default false |

**Request Body Parameters (via --body):**

| Field | Type | Description |
|-------|------|-------------|
| `nodeAmount` | int | Data node count (2~50) |
| `nodeSpec` | object | Data node configuration: `spec`, `disk`, `diskType`, `performanceLevel` |
| `masterConfiguration` | object | Dedicated master node config: `amount`, `spec`, `disk`, `diskType` |
| `clientNodeConfiguration` | object | Coordinating node config: `amount`, `spec`, `disk` |
| `warmNodeConfiguration` | object | Cold data node config: `amount`, `spec`, `disk`, `diskType` |
| `kibanaConfiguration` | object | Kibana node config: `amount`, `spec`, `disk` |
| `elasticDataNodeConfiguration` | object | Elastic data node config: `amount`, `spec`, `disk`, `diskType` |
| `updateType` | string | Change method: `blue_green` (blue-green), `normal` (in-place). Default is smart change (only for upgrade) |
| `force` | bool | Whether to force change (only for upgrade) |
| `dryRun` | bool | Pre-validation only, does not execute change |

**Request Body Examples:**

The following examples show the `--body` JSON for each common upgrade/downgrade scenario.

> **Note:** Each call can only change **one type of node**. For data nodes, `nodeAmount` and `nodeSpec` are considered the same type and can be combined in one call.

| # | Scenario | Request Body (`--body`) |
|---|----------|------------------------|
| 1 | Data node disk upgrade/downgrade | `{"nodeSpec":{"disk":40}}` |
| 2 | Data node spec upgrade/downgrade | `{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new"}}` |
| 3 | Data node disk + spec together | `{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new","disk":40}}` |
| 4 | Data node count increase/decrease | `{"nodeAmount":4}` |
| 5 | Data node count + disk + spec together | `{"nodeAmount":4,"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new","disk":40}}` |
| 6 | Master node spec upgrade/downgrade | `{"masterConfiguration":{"spec":"elasticsearch.sn2ne.xlarge"}}` |
| 7 | Kibana node spec change | `{"kibanaConfiguration":{"spec":"elasticsearch.sn1ne.large"}}` |
| 8 | Coordinating node count + spec | `{"clientNodeConfiguration":{"amount":3,"spec":"elasticsearch.sn1ne.large"}}` |
| 9 | Cold node count + disk + spec | `{"warmNodeConfiguration":{"amount":3,"spec":"elasticsearch.sn1ne.large","disk":500}}` |

**CLI Examples:**

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

# Example 1: Upgrade data node disk to 40GB
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeSpec":{"disk":40}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 2: Upgrade data node spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 3: Upgrade data node disk and spec together
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new","disk":40}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 4: Increase data node count to 4
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeAmount":4}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 5: Change data node count, disk, and spec together
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeAmount":4,"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new","disk":40}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 6: Upgrade master node spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"masterConfiguration":{"spec":"elasticsearch.sn2ne.xlarge"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 7: Change Kibana node spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"kibanaConfiguration":{"spec":"elasticsearch.sn1ne.large"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 8: Change coordinating node count and spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"clientNodeConfiguration":{"amount":3,"spec":"elasticsearch.sn1ne.large"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 9: Change cold node count, disk, and spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"warmNodeConfiguration":{"amount":3,"spec":"elasticsearch.sn1ne.large","disk":500}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 10: Downgrade data node spec (must set orderActionType=downgrade)
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --order-action-type downgrade \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.large.new"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills

# Example 11: Dry-run pre-validation (does not execute)
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new"},"dryRun":true}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response:**
```json
{
  "RequestId": "F99407AB-2FA9-489E-A259-40CF6DC****",
  "Result": {
    "instanceId": "es-cn-xxx****",
    "status": "activating"
  }
}
```

---

## Instance Status Reference

| Status | Description |
|--------|-------------|
| `active` | Running normally |
| `activating` | Activating (restarting or configuration changing) |
| `inactive` | Stopped |
| `invalid` | Invalid |

## Elasticsearch Version Reference

| Version | Description |
|---------|-------------|
| `8.5.1_with_X-Pack` | Elasticsearch 8.5.1 Commercial Edition |
| `7.10_with_X-Pack` | Elasticsearch 7.10 Commercial Edition |
| `7.7_with_X-Pack` | Elasticsearch 7.7 Commercial Edition |
| `6.8_with_X-Pack` | Elasticsearch 6.8 Commercial Edition |
| `6.7_with_X-Pack` | Elasticsearch 6.7 Commercial Edition |
| `6.3_with_X-Pack` | Elasticsearch 6.3 Commercial Edition |

## Official Documentation

- [createInstance API](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/createInstance)
- [DescribeInstance API](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/DescribeInstance)
- [ListInstance API](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/ListInstance)
- [RestartInstance API](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/RestartInstance)
- [UpdateInstance API](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/UpdateInstance)
- [Elasticsearch Pricing](https://www.aliyun.com/price/product#/elasticsearch/detail)
