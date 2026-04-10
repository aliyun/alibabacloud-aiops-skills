---
name: alibabacloud-elasticsearch-instance-manage
description: |
  Alibaba Cloud Elasticsearch Instance Management Skill. Use for creating, querying, listing, restarting, and upgrading/downgrading Elasticsearch instances on Alibaba Cloud.
  Triggers: "elasticsearch", "ES instance", "elasticsearch instance", "create ES", "query ES instance", "restart ES", "ES node", "cluster node", "upgrade ES", "downgrade ES", "scale ES", "resize ES"
---

# Elasticsearch Instance Management
Manage Alibaba Cloud Elasticsearch instances: create, describe, list, restart, upgrade/downgrade configuration, and query node information.
## Architecture
```
Alibaba Cloud Elasticsearch Instance Management
├── createInstance     (Create Instance)
├── DescribeInstance   (Query Instance Details)
├── ListInstance       (List Instances)
├── ListAllNode        (Query Cluster Node Info)
├── RestartInstance    (Restart Instance)
└── UpdateInstance     (Upgrade/Downgrade Instance Configuration)
```
## Prerequisites
> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
# Verify CLI version
aliyun version

# Enable auto plugin installation
aliyun configure set --auto-plugin-install true
```
---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**

> **Security Rules (MUST FOLLOW):**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation
> - **NEVER** use `aliyun configure set` with literal credential values
> - **NEVER** accept AK/SK provided directly by users in the conversation
> - **ONLY** read credentials from environment variables or pre-configured CLI profiles
>
> **⚠️ CRITICAL: Handling User-Provided Credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "My AK is xxx, SK is yyy"):
> 1. **STOP immediately** - Do NOT execute any command
> 2. **Reject the request politely** with the following message:
>    ```
>    For your account security, please do not provide Alibaba Cloud AccessKey ID and AccessKey Secret directly in the conversation.
>
>    Please use the following secure methods to configure credentials:
>
>    Method 1: Interactive configuration via aliyun configure (Recommended)
>        aliyun configure
>        # Enter AK/SK as prompted, credentials will be securely stored in local config file
>
>    Method 2: Configure via environment variables
>        export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
>        export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
>
>    After configuration, please retry your request.
>    ```
> 3. **Do NOT proceed** with any Alibaba Cloud operations until credentials are properly configured
>
> **Check CLI configuration**:
> ```bash
>    aliyun configure list
> ```
>    Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid credentials exist, STOP here.**

---

## RAM Policy

Ensure the RAM user has the required permissions. See [references/ram-policies.md](references/ram-policies.md) for detailed policy configurations.

**Minimum Required Permissions:**
- `elasticsearch:CreateInstance`
- `elasticsearch:DescribeInstance`
- `elasticsearch:ListInstance`
- `elasticsearch:ListAllNode`
- `elasticsearch:RestartInstance`
- `elasticsearch:UpdateInstance`

---

## Core Workflow

> **Note:** Elasticsearch APIs use **ROA (RESTful)** style. You can use `--body` to specify the HTTP request body as a JSON string. See examples in each task below.

> **Idempotency:** For write operations (create, restart, delete, etc.), you **MUST** use the `--client-token` parameter to ensure idempotency.
> - Use a UUID format unique identifier as clientToken
> - When a request times out or fails, you can safely retry with **the same clientToken**. When retrying after timeout, it is recommended to wait 10 seconds before retrying
> - Duplicate requests with the same clientToken will not execute the operation repeatedly
> - Generation method: Prefer using uuidgen or PowerShell GUID; if the environment doesn't support it, generate a UUID format string directly; if strict randomness is not required, use idem-timestamp-semantic-identifier as a fallback. Do not interrupt the process due to unavailable commands.

### Task 1: Create Elasticsearch Instance

[node-specifications-by-region.md](references/node-specifications-by-region.md) Different roles in different regions support different specifications when creating instances, refer to this document.

> **⚠️ CRITICAL: Required Parameters and Region Validation**
>
> When creating an ES instance, parameters such as `--region`, `esAdminPassword`, `vpcId`, `vswitchId`, `vsArea`, `paymentType` **MUST be explicitly provided by the user**.
>
> **Important Notes:**
> - The `--region` parameter **MUST NOT be guessed or use default values**
> - If the user does not provide a region or provides an invalid region, you **MUST clearly prompt the user** to provide a valid region
>
> For detailed validation rules, refer to [related-apis.md - createInstance Required Parameters and Region Validation](references/related-apis.md#1-createinstance---create-elasticsearch-instance)

**Method 2: Using --body to specify HTTP request body (RESTful style)**

```bash
# Generate idempotency token first
CLIENT_TOKEN=$(uuidgen)

aliyun elasticsearch create-instance \
  --region <RegionId> \
  --client-token $CLIENT_TOKEN \
  --body '{
    "esAdminPassword": "<Password>",
    "esVersion": "7.10_with_X-Pack",
    "nodeAmount": 2,
    "nodeSpec": {"disk": 20, "diskType": "cloud_ssd","spec": "elasticsearch.sn2ne.large.new"},
    "networkConfig": {"vpcId": "<VpcId>","vswitchId": "<VswitchId>", "vsArea": "<ZoneId>", "type": "vpc"},
    "paymentType": "postpaid",
    "description": "<InstanceName>"
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```
**Example: Create Single Availability Zone Instance**
```bash
# Generate idempotency token (use the same token when retrying after timeout)
CLIENT_TOKEN=$(uuidgen)

aliyun elasticsearch create-instance \
  --region cn-hangzhou \
  --client-token $CLIENT_TOKEN \
  --body '{
    "esAdminPassword": "YourPassword123!",
    "esVersion": "7.10_with_X-Pack",
    "nodeAmount": 2,
    "nodeSpec": {
      "disk": 20,
      "diskType": "cloud_ssd",
      "spec": "elasticsearch.sn2ne.large.new"
    },
    "networkConfig": {
      "vpcId": "vpc-bp1xxx",
      "vswitchId": "vsw-bp1xxx",
      "vsArea": "cn-hangzhou-i",
      "type": "vpc"
    },
    "paymentType": "postpaid",
    "description": "my-es-instance",
    "kibanaConfiguration": {
      "spec": "elasticsearch.sn1ne.large",
      "amount": 1,
      "disk": 0
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example: Create Multi-Availability Zone Instance**

1. For multi-AZ instances, networkConfig.vswitchId only supports the primary availability zone vSwitch, and networkConfig.vsArea only supports the primary availability zone name. Nodes will be automatically distributed to different availability zones. Do not specify availability zones and vSwitches through zoneInfos when creating, let the cloud provider allocate automatically.
2. Specify the number of availability zones through zoneCount. For multi-AZ instances, you must create master nodes.

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun elasticsearch create-instance \
  --region cn-hangzhou \
  --client-token $CLIENT_TOKEN \
  --body '{
    "esAdminPassword": "YourPassword123!",
    "esVersion": "7.10_with_X-Pack",
    "nodeAmount": 2,
    "nodeSpec": {
      "disk": 20,
      "diskType": "cloud_ssd",
      "spec": "elasticsearch.sn2ne.large.new"
    },
    "networkConfig": {
      "vpcId": "vpc-bp1xxx", "vswitchId": "vsw-bp1xxx", "vsArea": "cn-hangzhou-i", "type": "vpc"
    },
    "paymentType": "postpaid",
    "description": "my-es-instance",
    "zoneCount": "2",
    "kibanaConfiguration": {
      "spec": "elasticsearch.sn1ne.large",
      "amount": 1
    },
    "masterConfiguration": {
      "amount": 3,
      "disk": 20,
      "diskType": "cloud_essd",
      "spec": "elasticsearch.sn2ne.xlarge"
    }
  }' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Error Handling**
1. When an error occurs indicating that order parameters do not meet validation conditions, it may be due to incorrect data node specifications. You should prompt the user to use the correct specifications and not guess on your own. Refer to the specifications document [node-specifications-by-region.md](references/node-specifications-by-region.md)

### Task 2: Describe Instance Details

> **⚠️ Important: Required Parameters Must Be Provided by User**
> When querying instance details, `--region` and `--instance-id` must be explicitly provided by the user. Do not guess the region.
> For detailed instructions, refer to [related-apis.md - DescribeInstance Required Parameters](references/related-apis.md#2-describeinstance---query-instance-details)

```bash
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example:**
```bash
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Task 3: List Instances

> **⚠️ Important: Required Parameters and Parameter Validation**
> - The `--region` parameter must be explicitly provided by the user. Do not guess or use default values.
> - The `--status` parameter only supports valid values: `activating`, `active`, `inactive`, `invalid` (case-sensitive)
> - For detailed instructions, refer to [related-apis.md - ListInstance Required Parameters and Parameter Validation](references/related-apis.md#3-listinstance---list-instances)

```bash
aliyun elasticsearch list-instance \
  --region <RegionId> \
  --page 1 \
  --size 10 \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

For detailed parameters, filter examples, and response format, refer to [related-apis.md - ListInstance](references/related-apis.md#3-listinstance---list-instances)

### Task 4: Restart Instance

> **⚠️ CRITICAL: Pre-restart Check Requirements**
>
> **Before executing a restart operation, you must first query the instance status and confirm it is `active`:**
> **Pre-check Rules:**
> - **Only when the instance status is `active` can you execute the restart operation**
> - **If the instance status is abnormal (such as `activating`, `inactive`, `invalid`, etc.), restart operation is prohibited**
> - If the instance status is abnormal, you should inform the user that the current status is not suitable for restart and recommend waiting for the instance to recover or contacting Alibaba Cloud technical support

**Using --body to specify HTTP request body (RESTful style)**

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

**Example (using --body):**
```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

# Normal restart
aliyun elasticsearch restart-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"restartType":"instance"}' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills

# Force restart
aliyun elasticsearch restart-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"restartType":"instance","force":true}' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills

# Restart specific nodes
aliyun elasticsearch restart-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"restartType":"nodeIp","nodes":["10.0.XX.XX","10.0.XX.XX"]}' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Task 5: Update Instance Configuration (Upgrade/Downgrade)

> **⚠️ CRITICAL: Pre-update Check Requirements**
>
> **Before executing an update operation, you must first query the instance status and confirm it is `active`:**
> - **Only when the instance status is `active` can you execute the update operation**
> - **If the instance status is abnormal (such as `activating`, `inactive`, `invalid`), update operation is prohibited**
> - If the instance status is abnormal, inform the user that the current status is not suitable for configuration change and recommend waiting for the instance to recover
>
> **Important Constraints:**
> - Each update call can only change **one type of node** (data node, dedicated master node, cold data node, coordinating node, Kibana node, or elastic node)
> - **Upgrade**: Cannot reduce storage size, storage type, node count, or spec CPU/memory
> - **Downgrade**: Cannot increase storage size, storage type, node count, or spec CPU/memory. The `orderActionType` query parameter **MUST** be set to `downgrade`. Cannot reduce node count via this API (use ShrinkNode instead). Force change and updateType are not supported for downgrade
> - Storage size reduction is not supported in either direction
> - Enabled nodes cannot be disabled
>
> For detailed API usage, parameters, and examples, refer to [related-apis.md - UpdateInstance](references/related-apis.md#6-updateinstance---upgradedowngrade-instance-configuration)

[node-specifications-by-region.md](references/node-specifications-by-region.md) Different roles in different regions support different specifications, refer to this document.

**CLI Command (using --body for RESTful HTTP body):**

```bash
# Generate idempotency token
CLIENT_TOKEN=$(uuidgen)

aliyun elasticsearch update-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_BODY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example: Upgrade data node spec**
```bash
CLIENT_TOKEN=$(uuidgen)

aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Example: Downgrade data node spec (must set orderActionType=downgrade)**
```bash
CLIENT_TOKEN=$(uuidgen)

aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --order-action-type downgrade \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.large.new"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

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

**Error Handling**
1. When an error occurs indicating order parameters do not meet validation conditions, it may be due to incorrect node specifications. Refer to [node-specifications-by-region.md](references/node-specifications-by-region.md)
2. If the instance status is not `active`, prompt the user to wait for the instance to recover before retrying
3. If attempting to change multiple node types at once, inform the user that only one node type can be changed per operation

### Task 6: List All Nodes (Query Cluster Node Information)

```bash
aliyun elasticsearch list-all-node \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | Instance ID |
| `--extended` | No | Whether to return node monitoring information, default true |

**Example:**
```bash
# List all nodes with monitoring info
aliyun elasticsearch list-all-node \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills

# Query specific fields
aliyun elasticsearch list-all-node \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result[].{Host:host,Type:nodeType,Health:health,CPU:cpuPercent,Heap:heapPercent,Disk:diskUsedPercent}" \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response Fields:**

| Field | Description |
|-------|-------------|
| `host` | Node IP address |
| `nodeType` | Node type: MASTER/WORKER/WORKER_WARM/COORDINATING/KIBANA |
| `health` | Node health status: GREEN/YELLOW/RED/GRAY |
| `cpuPercent` | CPU usage rate |
| `heapPercent` | JVM memory usage rate |
| `diskUsedPercent` | Disk usage rate |
| `loadOneM` | One minute load |
| `zoneId` | Availability zone where the node is located |
| `port` | Node access port |

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

**Quick Verification:**
```bash
# Check instance status
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result.status" \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

Expected status: `active`

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [related-apis.md](references/related-apis.md) | API and CLI command details |
| [ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification steps |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect patterns |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [node-specifications-by-region.md](references/node-specifications-by-region.md) | Node specifications by region and role |
| [Elasticsearch Product Page](https://www.aliyun.com/product/bigdata/elasticsearch) | Official product page |
| [Elasticsearch API Reference](https://next.api.aliyun.com/product/elasticsearch) | Official API reference |