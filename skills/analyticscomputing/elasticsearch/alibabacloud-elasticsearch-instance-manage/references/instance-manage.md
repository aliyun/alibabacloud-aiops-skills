# Elasticsearch Instance Management

> Routing entry: [../SKILL.md](../SKILL.md)
>
> This document covers the **6 instance lifecycle APIs**: create, describe, list, restart, update (upgrade/downgrade), and node-info query.
> Global conventions (Authentication, Observability, common CLI args, idempotency, RAM rules) are defined in `SKILL.md` and apply to every command below.

## Table of Contents

- [Common Conventions](#common-conventions)
- [API Details](#api-details)
  - [1. createInstance](#1-createinstance)
  - [2. DescribeInstance](#2-describeinstance)
  - [3. ListInstance](#3-listinstance)
  - [4. RestartInstance](#4-restartinstance)
  - [5. UpdateInstance](#5-updateinstance)
  - [6. ListAllNode](#6-listallnode)
- [Instance Status Reference](#instance-status-reference)
- [Elasticsearch Version Reference](#elasticsearch-version-reference)
- [Official Documentation](#official-documentation)

---

## Common Conventions

| Item | Rule |
|---|---|
| Common CLI args | **`--user-agent` applies ONLY to business API commands** (e.g. `aliyun elasticsearch ...`); such commands MUST pass `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}` (see `SKILL.md#observability` for `SESSION_ID` generation rule). **System / tool commands** (`aliyun configure`, `aliyun version`, `aliyun plugin update`, `aliyun help`, etc.) **MUST NOT** carry `--user-agent` — they do not support the flag. Each business command also appends `--connect-timeout 3 --read-timeout 10` (write op: `--read-timeout 30`). |
| Region | `--region` is REQUIRED and MUST be explicitly provided by the user. Do NOT guess. |
| Idempotency | Write APIs (`createInstance`, `RestartInstance`, `UpdateInstance`) MUST pass `--client-token $(uuidgen)`. Use the SAME token when retrying after timeout. |
| API style | All APIs use ROA (RESTful). `--body` accepts a JSON string for HTTP request body. |

---

## API Details

### 1. createInstance

Create a new Elasticsearch instance.

- **API**: `createInstance`
- **HTTP**: `POST /openapi/instances`
- **Idempotent**: Yes — `clientToken` is REQUIRED.

**Pre-check (CRITICAL)**

> The following parameters MUST be explicitly provided by the user. Agents MUST NOT guess, fabricate or use defaults.

| Parameter | Why | Example |
|---|---|---|
| `--region` | Determines API endpoint and resource locality. Must look like `cn-*` / `ap-*`. | `cn-hangzhou` |
| `esAdminPassword` | Admin password, 8~32 chars, must contain ≥3 of: uppercase / lowercase / digit / special char | `YourPassword123!` |
| `vpcId` | VPC network ID | `vpc-bp1xxx` |
| `vswitchId` | VSwitch ID (multi-AZ: only the primary AZ vswitch) | `vsw-bp1xxx` |
| `vsArea` | Availability zone of `vswitchId` | `cn-hangzhou-i` |
| `paymentType` | `postpaid` or `prepaid` | `postpaid` |

If any of the above is missing, immediately stop and ask the user with this checklist:

```
The following parameters are required to create an ES instance, please provide:
- [ ] Region (--region): ___
- [ ] Instance password (esAdminPassword): ___
- [ ] VPC ID (vpcId): ___
- [ ] VSwitch ID (vswitchId): ___
- [ ] Availability Zone (vsArea): ___
- [ ] Payment Type (paymentType): postpaid/prepaid
```

**Prohibited Behaviors:**
- Do NOT use example values as actual parameters
- Do NOT guess `vsArea` based on region
- Do NOT use default passwords or fabricate passwords
- Do NOT assume the user's VPC or VSwitch ID
- Region format MUST start with `cn-` or `ap-` prefix; if the provided value is obviously invalid (empty, pure numbers, special characters), reject and ask again

**Required Body Fields**

| Field | Type | Description |
|---|---|---|
| `esAdminPassword` | string | Instance admin password |
| `esVersion` | string | e.g. `7.10_with_X-Pack`, `7.16_with_X-Pack`, `8.5.1_with_X-Pack`, `8.15.1_with_X-Pack`, `8.17.0_with_X-Pack` |
| `nodeAmount` | int | Data node count, range 2~50 |
| `networkConfig` | object | `{vpcId, vswitchId, vsArea, type:"vpc"}`. `type` is fixed to `vpc`. For multi-AZ only the primary AZ vswitch is provided. |

**Optional Body Fields**

| Field | Type | Description |
|---|---|---|
| `nodeSpec` | object | Data node config: `spec`, `disk` (GB), `diskType` |
| `paymentType` | string | `postpaid` / `prepaid` |
| `kibanaConfiguration` | object | Kibana node config |
| `masterConfiguration` | object | Dedicated master node (REQUIRED for multi-AZ) |
| `description` | string | Instance name |
| `zoneCount` | string/int | `1` / `2` / `3` for multi-AZ deployment |

**Multi-AZ Notes**

1. `networkConfig.vswitchId` only takes the primary AZ vswitch; other AZs are auto-allocated. Do NOT pass `zoneInfos` to specify per-AZ vswitches manually — let the platform allocate.
2. `zoneCount` controls the AZ number. Multi-AZ MUST include `masterConfiguration`.

**CLI Template**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch create-instance \
  --region <RegionId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_BODY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example: Single-AZ instance**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch create-instance \
  --region cn-hangzhou \
  --client-token $CLIENT_TOKEN \
  --body '{
    "esAdminPassword": "YourPassword123!",
    "esVersion": "7.10_with_X-Pack",
    "nodeAmount": 2,
    "nodeSpec": {"disk": 20, "diskType": "cloud_ssd", "spec": "elasticsearch.sn2ne.large.new"},
    "networkConfig": {"vpcId": "vpc-bp1xxx", "vswitchId": "vsw-bp1xxx", "vsArea": "cn-hangzhou-i", "type": "vpc"},
    "paymentType": "postpaid",
    "description": "my-es-instance",
    "kibanaConfiguration": {"spec": "elasticsearch.sn1ne.large", "amount": 1, "disk": 0}
  }' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example: Multi-AZ instance**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch create-instance \
  --region cn-hangzhou \
  --client-token $CLIENT_TOKEN \
  --body '{
    "esAdminPassword": "YourPassword123!",
    "esVersion": "7.10_with_X-Pack",
    "nodeAmount": 2,
    "nodeSpec": {"disk": 20, "diskType": "cloud_ssd", "spec": "elasticsearch.sn2ne.large.new"},
    "networkConfig": {"vpcId": "vpc-bp1xxx", "vswitchId": "vsw-bp1xxx", "vsArea": "cn-hangzhou-i", "type": "vpc"},
    "paymentType": "postpaid",
    "description": "my-es-instance",
    "zoneCount": "2",
    "kibanaConfiguration": {"spec": "elasticsearch.sn1ne.large", "amount": 1},
    "masterConfiguration": {"amount": 3, "disk": 20, "diskType": "cloud_essd", "spec": "elasticsearch.sn2ne.xlarge"}
  }' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Error Handling**

- "Order parameters do not meet validation conditions" → likely an invalid data node spec for the chosen region. Do NOT guess; refer the user to [node-specifications-by-region.md](node-specifications-by-region.md).

**Response**: `{"RequestId":"...","Result":{"instanceId":"es-cn-xxx****"}}`.

---

### 2. DescribeInstance

Query full details of one instance.

- **API**: `DescribeInstance`
- **HTTP**: `GET /openapi/instances/[InstanceId]`

**Pre-check**

| Parameter | Required | Description |
|---|---|---|
| `--region` | Yes | User-provided. Do NOT guess from instance ID. |
| `--instance-id` | Yes | User-provided. |

**Prohibited Behaviors:**
- Do NOT use a default region (such as `cn-hangzhou`) to replace the user-specified region
- Do NOT guess region based on instance ID
- Do NOT assume the instance is in a specific region
- If region is missing, immediately ask: "Please provide the region where the instance is located, e.g., cn-hangzhou, cn-shanghai, cn-beijing, etc."

**CLI Template**

```bash
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example**

```bash
aliyun elasticsearch describe-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields (selected)**

| Field | Type | Description |
|---|---|---|
| `instanceId` | string | Instance ID |
| `description` | string | Instance name |
| `status` | string | Instance status (see [Instance Status Reference](#instance-status-reference)) |
| `esVersion` | string | Elasticsearch version |
| `nodeAmount` | int | Data node count |
| `paymentType` | string | Payment type |
| `domain` / `port` | string/int | Internal access endpoint |
| `kibanaDomain` / `kibanaPort` | string/int | Kibana endpoint |

---

### 3. ListInstance

List instances in a region with optional filters.

- **API**: `ListInstance`
- **HTTP**: `GET /openapi/instances`

**Pre-check**

| Parameter | Required | Description |
|---|---|---|
| `--region` | Yes | User-provided. Do NOT guess. |
| `--status` | No | If provided, MUST be one of: `activating` / `active` / `inactive` / `invalid` (case-sensitive). Reject any other value. |

**Status Parameter Validation (CRITICAL):**

When the user specifies `--status`, the agent MUST validate the value before executing:
1. Check if the user-provided status value is one of the 4 valid values above
2. If the value is invalid (e.g., "running", "stopped", "healthy"), immediately prompt:
   ```
   The status parameter value is invalid. Valid values are: activating, active, inactive, invalid
   Please provide a valid status value.
   ```
3. Wait for the user to provide a valid value before executing

**Prohibited Behaviors:**
- Do NOT guess or transform the user-provided status value (e.g., do NOT silently convert "running" to "active")
- Do NOT ignore the user-provided invalid value and query without the filter
- Do NOT use a default region — if missing, ask immediately

**Optional Parameters**

| Parameter | Type | Description |
|---|---|---|
| `--page` | int | Page number from 1, default 1 |
| `--size` | int | Page size, max 100, default 10 |
| `--description` | string | Instance name (fuzzy match) |
| `--instance-id` | string | Filter by instance ID |
| `--es-version` | string | Filter by ES version |
| `--vpc-id` | string | Filter by VPC ID |
| `--zone-id` | string | Filter by AZ ID |
| `--status` | string | One of `activating` / `active` / `inactive` / `invalid` |
| `--payment-type` | string | `postpaid` / `prepaid` |

**CLI Template**

```bash
aliyun elasticsearch list-instance \
  --region <RegionId> \
  --page 1 \
  --size 10 \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example: list active instances and project key fields**

```bash
aliyun elasticsearch list-instance \
  --region cn-hangzhou \
  --status active \
  --size 50 \
  --cli-query "Result[].{Id:instanceId,Name:description,Version:esVersion,Status:status,Nodes:nodeAmount}" \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

---

### 4. RestartInstance

Restart instance (whole instance, with optional force, or specific node IPs).

- **API**: `RestartInstance`
- **HTTP**: `POST /openapi/instances/[InstanceId]/actions/restart`
- **Idempotent**: Yes — `clientToken` is REQUIRED.

**Pre-check (CRITICAL)**

- Instance status MUST be `active`. Run `describe-instance --cli-query "Result.status"` first.
- If status is `activating` / `inactive` / `invalid`, REJECT the restart and inform the user.

**Required Parameters**

| Parameter | Location | Required | Description |
|---|---|---|---|
| `--region` | flag | Yes | User-provided |
| `--instance-id` | path | Yes | Instance ID |
| `--client-token` | query | Yes | UUID, reuse on retry |

**Optional Query Parameters (flag-style, NOT in `--body`)**

| Parameter | Type | Description |
|---|---|---|
| `--force` | bool | Whether to ignore cluster status and force-restart. `true`: force, `false` (default): not force. **MUST be passed as a flag** — it is a Query parameter on the HTTP request, NOT a body field. |

**Body Fields (`--body` JSON)**

| Field | Type | Description |
|---|---|---|
| `restartType` | string | `instance` (default, whole-instance restart) / `nodeIp` (restart specific nodes by IP) / `nodeEcsId` (restart specific nodes by ECS ID). Empty string is treated as `instance`. |
| `nodes` | array<string> | Node IP or ECS ID list. REQUIRED when `restartType=nodeIp` / `nodeEcsId`. |
| `blueGreenDep` | bool | Enable blue-green deployment when restarting nodes. Default `false`. Ignored when `restartType=instance`. |
| `batchCount` | double | Concurrency for force restart. When `force=true`, MUST be `0 < batchCount ≤ 100` (otherwise `RestartBatchValueError`). When `force=false`, MUST be `0` / unset (otherwise `NormalRestartNotSupportBatch`). Ignored when `restartType=nodeIp`. |
| `batchUnit` | string | Unit of `batchCount`, default `percent`. |

**CLI Template**

```bash
CLIENT_TOKEN=$(uuidgen)
aliyun elasticsearch restart-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_BODY>' \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Examples**

```bash
CLIENT_TOKEN=$(uuidgen)

# Normal restart (whole instance)
aliyun elasticsearch restart-instance \
  --region cn-hangzhou --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"restartType":"instance"}' \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Force restart — `force` is a QUERY parameter (--force flag), NOT a body field
# When force=true, batchCount MUST be set in (0, 100]
aliyun elasticsearch restart-instance \
  --region cn-hangzhou --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --force true \
  --body '{"restartType":"instance","batchCount":50}' \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Restart specific nodes (by IP) with blue-green deployment
aliyun elasticsearch restart-instance \
  --region cn-hangzhou --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"restartType":"nodeIp","nodes":["10.0.XX.XX","10.0.XX.XX"],"blueGreenDep":true}' \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response**: `{"Result":{"instanceId":"es-cn-xxx****","status":"activating"}}`.

---

### 5. UpdateInstance

Upgrade or downgrade configuration of an existing instance.

- **API**: `UpdateInstance`
- **HTTP**: `POST /openapi/instances/[InstanceId]/actions/update`
- **Idempotent**: Yes — `clientToken` is REQUIRED.

**Pre-check (CRITICAL)**

1. Instance status MUST be `active` — confirm via `describe-instance` first.
2. Each call may change ONLY ONE node type. Supported node types:
   - Data node (`nodeAmount` / `nodeSpec`) — `nodeAmount` and `nodeSpec` are the SAME type; can be combined.
   - Master node (`masterConfiguration`)
   - Cold data node (`warmNodeConfiguration`)
   - Coordinating node (`clientNodeConfiguration`)
   - Kibana node (`kibanaConfiguration`)
   - Elastic data node (`elasticDataNodeConfiguration`)
3. Upgrade vs Downgrade rules:

| Rule | Upgrade (default) | Downgrade (`--order-action-type downgrade`) |
|---|---|---|
| Storage size | Can increase | Cannot decrease |
| Storage type | Can change | Can change |
| Node count | Can increase | Cannot decrease (use ShrinkNode API) |
| Spec (CPU/Mem) | Can increase | Can decrease |
| Force change | Supported | NOT supported |
| `updateType` (blue_green/normal) | Supported | NOT supported |

**Prohibited**

- Changing multiple node types in a single call
- Reducing node count via UpdateInstance
- Reducing storage size in either direction
- Disabling already-enabled nodes
- Guessing specs — refer to [node-specifications-by-region.md](node-specifications-by-region.md)

**Required Parameters**

| Parameter | Location | Required | Description |
|---|---|---|---|
| `--region` | flag | Yes | User-provided |
| `--instance-id` | flag | Yes | Instance ID |
| `--client-token` | flag | Yes | UUID |
| `--order-action-type` | query | When downgrading | `upgrade` (default) or `downgrade` |
| `--force` | query | No | Force change, upgrade only |

**Body Fields (`--body` JSON)**

| Field | Type | Description |
|---|---|---|
| `nodeAmount` | int | Data node count (2~50) |
| `nodeSpec` | object | Data node: `spec`, `disk`, `diskType`, `performanceLevel` |
| `masterConfiguration` | object | `amount`, `spec`, `disk`, `diskType` |
| `clientNodeConfiguration` | object | `amount`, `spec`, `disk` |
| `warmNodeConfiguration` | object | `amount`, `spec`, `disk`, `diskType` |
| `kibanaConfiguration` | object | `amount`, `spec`, `disk` |
| `elasticDataNodeConfiguration` | object | `amount`, `spec`, `disk`, `diskType` |
| `instanceCategory` | string | Version type: `x-pack` / `advanced` / `IS` / `community` |
| `updateType` | string | `blue_green` / `normal`. Upgrade only. |
| `dryRun` | bool | Pre-validation only, no real change |

**CLI Template**

```bash
CLIENT_TOKEN=$(uuidgen)

# Upgrade
aliyun elasticsearch update-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --body '<JSON_BODY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Downgrade
aliyun elasticsearch update-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --client-token $CLIENT_TOKEN \
  --order-action-type downgrade \
  --body '<JSON_BODY>' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Body Cookbook**

> Each call can only change **one type of node**. For data nodes, `nodeAmount` and `nodeSpec` are considered the same type and can be combined in one call.

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

**CLI Examples**

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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 2: Upgrade data node spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 3: Upgrade data node disk and spec together
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new","disk":40}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 4: Increase data node count to 4
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeAmount":4}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 5: Change data node count, disk, and spec together
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeAmount":4,"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new","disk":40}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 6: Upgrade master node spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"masterConfiguration":{"spec":"elasticsearch.sn2ne.xlarge"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 7: Change Kibana node spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"kibanaConfiguration":{"spec":"elasticsearch.sn1ne.large"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 8: Change coordinating node count and spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"clientNodeConfiguration":{"amount":3,"spec":"elasticsearch.sn1ne.large"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 9: Change cold node count, disk, and spec
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"warmNodeConfiguration":{"amount":3,"spec":"elasticsearch.sn1ne.large","disk":500}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 10: Downgrade data node spec (must set orderActionType=downgrade)
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --order-action-type downgrade \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.large.new"}}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Example 11: Dry-run pre-validation (does not execute)
aliyun elasticsearch update-instance \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --client-token $CLIENT_TOKEN \
  --body '{"nodeSpec":{"spec":"elasticsearch.sn2ne.xlarge.new"},"dryRun":true}' \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Error Handling**

1. "Order parameters do not meet validation conditions" → invalid spec for the region. Refer to [node-specifications-by-region.md](node-specifications-by-region.md).
2. Status not `active` → ask the user to wait for recovery before retrying.
3. Multiple node types in one body → only ONE node type is allowed per call.

**Response**: `{"Result":{"instanceId":"es-cn-xxx****","status":"activating"}}`.

---

### 6. ListAllNode

List all cluster nodes with optional monitoring info.

- **API**: `ListAllNode`
- **HTTP**: `GET /openapi/instances/[InstanceId]/nodes`

**Required Parameters**

| Parameter | Required | Description |
|---|---|---|
| `--region` | Yes | User-provided |
| `--instance-id` | Yes | Instance ID |
| `--extended` | No | Whether to return monitoring fields, default `true` |

**CLI Template**

```bash
aliyun elasticsearch list-all-node \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Key Example: project key fields**

```bash
aliyun elasticsearch list-all-node \
  --region cn-hangzhou \
  --instance-id es-cn-xxx**** \
  --cli-query "Result[].{Host:host,Type:nodeType,Health:health,CPU:cpuPercent,Heap:heapPercent,Disk:diskUsedPercent}" \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `host` | Node IP |
| `nodeType` | `MASTER` / `WORKER` (hot data) / `WORKER_WARM` (cold data) / `COORDINATING` / `KIBANA` |
| `health` | `GREEN` / `YELLOW` / `RED` / `GRAY` |
| `cpuPercent` | CPU usage |
| `heapPercent` | JVM heap usage |
| `diskUsedPercent` | Disk usage |
| `loadOneM` | 1-min load average |
| `zoneId` | Availability zone |
| `port` | Access port |

---

## Instance Status Reference

| Status | Description |
|---|---|
| `active` | Running normally |
| `activating` | Activating (restarting / configuration changing) |
| `inactive` | Stopped |
| `invalid` | Invalid |

## Elasticsearch Version Reference

| Version | Description |
|---|---|
| `8.17.0_with_X-Pack` | Elasticsearch 8.17.0 Commercial |
| `8.15.1_with_X-Pack` | Elasticsearch 8.15.1 Commercial |
| `8.5.1_with_X-Pack` | Elasticsearch 8.5.1 Commercial |
| `7.16_with_X-Pack` | Elasticsearch 7.16 Commercial |
| `7.10_with_X-Pack` | Elasticsearch 7.10 Commercial |
| `7.7_with_X-Pack` | Elasticsearch 7.7 Commercial |
| `6.8_with_X-Pack` | Elasticsearch 6.8 Commercial |

## Official Documentation

- [createInstance](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/createInstance)
- [DescribeInstance](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/DescribeInstance)
- [ListInstance](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/ListInstance)
- [RestartInstance](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/RestartInstance)
- [UpdateInstance](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/UpdateInstance)
- [ListAllNode](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/ListAllNode)
- [Elasticsearch Pricing](https://www.aliyun.com/price/product#/elasticsearch/detail)
