# Elasticsearch Instance Management

> Routing entry: [../SKILL.md](../SKILL.md)
>
> This document covers the **13 instance lifecycle APIs**: create, describe, list, restart, update (upgrade/downgrade), node-info query, admin password update, description update, charge type conversion, version upgrade (info + execute), change-record query, plus gray-upgrade continuation.
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
  - [7. UpdateAdminPassword](#7-updateadminpassword)
  - [8. UpdateDescription](#8-updatedescription)
  - [9. UpdateInstanceChargeType](#9-updateinstancechargetype)
  - [10. UpgradeInfo](#10-upgradeinfo)
  - [11. UpgradeEngineVersion](#11-upgradeengineversion)
  - [12. ListActionRecords](#12-listactionrecords)
  - [13. ContinueEsVersionUpgrade](#13-continueesversionupgrade)
- [Instance Status Reference](#instance-status-reference)
- [Elasticsearch Version Reference](#elasticsearch-version-reference)
- [Official Documentation](#official-documentation)

---

## Common Conventions

| Item | Rule |
|---|---|
| Common CLI args | **`--user-agent` applies ONLY to business API commands** (e.g. `aliyun elasticsearch ...`); such commands MUST pass `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}` (see `SKILL.md#observability` for `SESSION_ID` generation rule). **System / tool commands** (`aliyun configure`, `aliyun version`, `aliyun plugin update`, `aliyun help`, etc.) **MUST NOT** carry `--user-agent` — they do not support the flag. Each business command also appends `--connect-timeout 3 --read-timeout 10` (write op: `--read-timeout 30`). |
| Region | `--region` is REQUIRED and MUST be explicitly provided by the user. Do NOT guess. |
| Idempotency | Write APIs (`createInstance`, `RestartInstance`, `UpdateInstance`, `UpdateInstanceChargeType`) MUST pass `--client-token $(uuidgen)`. Use the SAME token when retrying after timeout. `ContinueEsVersionUpgrade` uses `X-Request-ChangeId` (the change id from `ListActionRecords`) instead of `clientToken`. |
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

### 7. UpdateAdminPassword

Update the elastic admin account password for a specified Elasticsearch instance.

- **API**: `UpdateAdminPassword`
- **HTTP**: `POST /openapi/instances/{InstanceId}/admin-pwd`
- **Idempotent**: Yes — `clientToken` recommended.

> **Note**: This API cannot be called when the instance is in `activating`, `invalid`, or `inactive` status.

> **Important behaviors**:
> - Password reset does **NOT** trigger an instance restart.
> - The new password takes effect in approximately **5 minutes**.
> - Only the `elastic` built-in account is affected; other custom users are not impacted.
> - Best practice: avoid using the `elastic` account for programmatic access — create dedicated users with appropriate roles instead.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `clientToken` | Query | No | Idempotency token (max 64 ASCII chars) |
| `esAdminPassword` | Body | Yes | New password. Must contain ≥3 of: uppercase / lowercase / digit / special char (`!@#$%^&*()_+-=`). Length: 8–32 chars. |

**CLI Example**

```bash
aliyun elasticsearch update-admin-password --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '{"esAdminPassword":"NewPass@123"}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | `true` if password updated successfully, `false` otherwise |
| `RequestId` | Request ID |

---

### 8. UpdateDescription

Update the name (description) of a specified Elasticsearch instance.

- **API**: `UpdateDescription`
- **HTTP**: `POST /openapi/instances/{InstanceId}/description`
- **Idempotent**: Yes — `clientToken` recommended.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `clientToken` | Query | No | Idempotency token (max 64 ASCII chars) |
| `description` | Body | Yes | New instance name. Constraints: 0–128 chars; must start with a letter (upper/lower), digit, or Chinese character; may contain underscore (`_`) or hyphen (`-`). |

**CLI Example**

```bash
aliyun elasticsearch update-description --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '{"description":"my_test_instance"}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result.description` | The updated instance name |
| `RequestId` | Request ID |

---

### 9. UpdateInstanceChargeType

Convert a pay-as-you-go (postpaid) Elasticsearch instance to subscription (prepaid).

- **API**: `UpdateInstanceChargeType`
- **HTTP**: `POST /openapi/instances/{InstanceId}/actions/convert-pay-type`
- **Idempotent**: Yes — `clientToken` recommended.

> **Important Behaviors**
> - Only supports converting **postpaid → prepaid** (pay-as-you-go to subscription). Reverse conversion is not supported via this API.
> - The `paymentType` field must be fixed to `"prepaid"`.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `clientToken` | Query | No | Idempotency token (max 64 ASCII chars) |

**Request Body**

```json
{
  "paymentInfo": {
    "duration": 1,
    "pricingCycle": "Month"
  },
  "paymentType": "prepaid"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `paymentType` | String | Yes | Fixed value: `prepaid` |
| `paymentInfo.duration` | Integer | Yes | Duration. If `pricingCycle` is `Year`: 1–3; if `Month`: 1–9 |
| `paymentInfo.pricingCycle` | String | Yes | Billing cycle: `Year` or `Month` |

**CLI Example**

```bash
aliyun elasticsearch update-instance-charge-type --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '{"paymentInfo":{"duration":1,"pricingCycle":"Month"},"paymentType":"prepaid"}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | `true` if conversion succeeded; `false` otherwise |
| `RequestId` | Request ID |

---

### 10. UpgradeInfo

Query whether there are available upgrade versions (ES major version or kernel patch) for the specified instance.

- **API**: `UpgradeInfo`
- **HTTP**: `GET /openapi/instances/{InstanceId}/upgradeInfo`
- **Read-only**: Yes — no `clientToken` needed.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |

**CLI Example**

```bash
aliyun elasticsearch upgrade-info --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result.UpgradeInfo.Upgrade` | `true` if an upgrade is available; `false` otherwise |
| `Result.UpgradeInfo.curEsVersion` | Current ES version (e.g. `8.17.0`) |
| `Result.UpgradeInfo.upgradeEsVersion` | Available ES upgrade version (e.g. `8.17.0`) |
| `Result.UpgradeInfo.curApackVersion` | Current kernel (apack) version (e.g. `2.2.4`) |
| `Result.UpgradeInfo.upgradeApackVersion` | Available kernel upgrade version (e.g. `2.2.4`) |
| `Result.UpgradeInfo.CurRepoVersion` | Current repo version (e.g. `1.7.3`) |
| `Result.UpgradeInfo.UpdateRepoVersion` | Available repo upgrade version (e.g. `1.7.3`) |
| `RequestId` | Request ID |

---

### 11. UpgradeEngineVersion

Upgrade the Elasticsearch instance major version or kernel patch version.

- **API**: `UpgradeEngineVersion`
- **HTTP**: `POST /openapi/instances/{InstanceId}/actions/upgrade-version`
- **Idempotent**: Yes — `clientToken` recommended.

> **Important Behaviors**
> - The instance must be in `active` status before calling this API.
> - **[MANDATORY GATE]** You MUST call with `dryRun=true` first and it MUST pass before the actual upgrade. The validation checks cluster health, config/plugin compatibility, resources, and snapshots. If the dry-run reports any error, STOP and resolve it — do NOT execute the upgrade until the dry-run passes.
> - Version upgrade paths differ by instance architecture:
>   - **v2 basic architecture**: version upgrade via this API/CLI is **NOT supported** for now. Direct the user to perform the upgrade in the [Elasticsearch console](https://elasticsearch.console.aliyun.com/) instead.
>   - **v3 cloud-native architecture**: the available target version(s) must be queried via `UpgradeInfo` (see §10) before upgrading.
> - Kernel patch upgrade (`type=aliVersion`) follows different versioning (e.g. `2.2.8`).
> - **Major version upgrade (`engineVersion`) only — [MANDATORY GATE]** — before executing, check installed **user (custom) plugins** (`ListUserPlugin`, see plugin-manage.md) for target-version compatibility: compare each installed plugin's `elasticsearchVersion` against the TARGET ES version. **A version mismatch WILL make the upgrade get stuck**, so if any custom plugin's version does NOT match the target (or dry-run reports `errorType=clusterConfigPlugins`), you MUST STOP, prompt the user, and require them to first upload the target-version plugin via `PluginAnalysis` (see plugin-manage.md → PluginAnalysis). Do NOT execute the upgrade until resolved. After a successful upload, pass the target-version plugin metadata (from `ListUserPlugin` → `Result[].bingoPlugins[]`) in the `plugins` array of the `UpgradeEngineVersion` request body — the upgrade will then re-install the compatible plugins as part of the upgrade.
> - **Major version upgrade (`engineVersion`) only** — the upgrade runs as a gray (canary) change: after the gray batch completes (`ListActionRecords` → `detail.grayType == "grayDone"`), call `ContinueEsVersionUpgrade` (see §13) with the change id to finish upgrading the remaining nodes. Kernel patch upgrade does NOT need this continuation step.
> - Upgrade may trigger a cluster restart depending on the version gap.
>
> **Upgrade Precautions** (inform the user before executing):
> 1. If you use any Elasticsearch plugins, ensure each plugin is compatible with the target version — otherwise the plugin may not work after upgrade.
> 2. Test the upgrade process on a test environment or test instance before upgrading production clusters.
> 3. Ensure you have a recent snapshot of the cluster data before upgrading. The dry-run's `checkClusterSnapshot` REQUIRES a completed snapshot within the last hour; if it fails (`errorCode=WithInvalidElasticsearchSnapshots`), BLOCK and ASK the user whether to create one now via `CreateSnapshot` (see config-manage.md), then re-run the dry-run. Downgrade is NOT possible after upgrade; you must restore from snapshot if issues occur.
> 4. If you also use Logstash, APM, Beats, Fleet/Elastic Agent, Elastic Security, or Enterprise Search, ensure they are compatible with the target version.
> 5. Breaking changes may exist between your current version and the target version. Versions 8.9, 8.14, and 8.15 contain breaking changes; other 8.x versions have minor changes only. Refer to [Elastic official docs](https://www.elastic.co/guide/en/elasticsearch/reference/current/breaking-changes.html).
> 6. Perform upgrades during **off-peak hours** on production clusters.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `clientToken` | Query | No | Idempotency token (max 64 ASCII chars) |
| `dryRun` | Query | No | Default `false`. Set `true` to perform pre-upgrade validation only (does not execute upgrade). **Strongly recommended before actual upgrade.** |

**Request Body**

```json
{
  "type": "engineVersion",
  "version": "6.7"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | Upgrade type: `engineVersion` (major version) or `aliVersion` (kernel patch) |
| `version` | string | Yes | Target version. For `engineVersion`: e.g. `6.7`. For `aliVersion`: e.g. `2.2.8` |
| `plugins` | array | No | **Major version upgrade only.** Required when the instance has custom (USER) plugins whose version does not match the target. Each element is the target-version plugin metadata obtained from `ListUserPlugin` → `Result[].bingoPlugins[]` (fields: `elasticsearchVersion`, `pluginType`, `imageBuiltin`, `name`, `description`, `state`, `source`, `version`, `fileVersion`). The upgrade re-installs these compatible plugins as part of the upgrade. |

**CLI Examples**

Each upgrade type (major version OR kernel patch) is an independent operation — only one can be performed at a time.

```bash
## === Major Version Upgrade (engineVersion) ===

# Step 1: Query available upgrade versions
aliyun elasticsearch upgrade-info --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
# If Result.UpgradeInfo.Upgrade == true, use upgradeEsVersion as target version

# Step 2: [MANDATORY GATE] Dry-run validation — MUST be run and MUST pass before executing the upgrade.
# It validates cluster health, config/plugin compatibility, resources and snapshots.
aliyun elasticsearch upgrade-engine-version --instance-id es-cn-xxxxx --dry-run true \
  --region cn-hangzhou \
  --body '{"type":"engineVersion","version":"6.7"}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
# Inspect Result[].status per validateType. If ANY check has status=failed you MUST STOP and resolve it before Step 4:
#   - checkClusterSnapshot failed (errorType=clusterSnapshot, e.g. errorCode=WithInvalidElasticsearchSnapshots,
#     errorMsg "最近一个小时内未有已完成的集群快照，请进行快照备份"): a COMPLETED snapshot within the last hour is REQUIRED.
#     BLOCK and ASK the user whether to create a snapshot now. If yes, trigger CreateSnapshot
#     (see config-manage.md → CreateSnapshot: aliyun elasticsearch create-snapshot --instance-id es-cn-xxxxx --client-token $(uuidgen) ...),
#     wait until the snapshot completes, then re-run this dry-run.
#   - checkConfigCompatible failed with errorType=clusterConfigPlugins: handle custom plugins per Step 3.
#   - checkClusterHealth / checkClusterResource failed: resolve the cluster health/resource issue first.
# Do NOT run the actual upgrade until the dry-run passes (every check status=success).

# Step 3: [MANDATORY GATE] Check installed user (custom) plugins for target-version compatibility (major version upgrade only)
# Call ListUserPlugin and compare each installed plugin's elasticsearchVersion against the TARGET version.
aliyun elasticsearch list-user-plugin --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
# STRICT RULE — a version mismatch WILL make the upgrade get STUCK. If ANY installed custom plugin's
# elasticsearchVersion != target version (e.g. installed 8.15.1 but upgrading to 8.17.0), you MUST:
#   1) STOP here. Do NOT run Step 4. Prompt the user that a target-version plugin must be uploaded first.
#   2) Have the user upload the target-version plugin via PluginAnalysis (see plugin-manage.md → PluginAnalysis: dry-run, then --dry-run false to actually upload).
#   3) After a successful upload, re-run ListUserPlugin to get the target-version plugin metadata
#      (Result[].bingoPlugins[] where elasticsearchVersion == target version, state=UNINSTALLED).
#   4) Only then proceed to Step 4, putting that metadata into the UpgradeEngineVersion body's `plugins` array.

# Step 4: Execute upgrade (only after dry-run passes)
# When the instance has custom plugins, include the target-version plugin metadata (from ListUserPlugin) in `plugins`;
# the upgrade re-installs the compatible plugins as part of the upgrade.
aliyun elasticsearch upgrade-engine-version --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '{"version":"8.17.0","type":"engineVersion","plugins":[{"elasticsearchVersion":"8.17.0","pluginType":"CUSTOM_PLUGIN","imageBuiltin":false,"name":"analysis-icu","description":"The ICU Analysis plugin integrates the Lucene ICU module into Elasticsearch, adding ICU-related analysis components.","state":"UNINSTALLED","source":"USER","version":"8.17.0","fileVersion":"CAEQigEYgYCAg_eehPoZIiA5YzM2MzY1M2U4MTE0NDliYWY2YjQ2ZmIwNWJiMGY0ZA--"}]}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
# No custom plugins? Use a minimal body: {"version":"8.17.0","type":"engineVersion"}

# Step 5: Poll change progress until the gray batch is done
aliyun elasticsearch list-action-records --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
# Wait until Result[].detail.grayType == "grayDone"; take Result[].requestId (= detail.changeId) as the change id

# Step 6: Continue upgrading the remaining nodes (gray done → finish upgrade)
# General (ROA) invocation: `--roa 2017-06-13` + `--force` are REQUIRED to bypass plugin path validation.
aliyun elasticsearch POST "/openapi/instances/es-cn-xxxxx/actions/continueEsVersionUpgrade?X-Request-ChangeId=<changeId>" \
  --roa 2017-06-13 --force \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

```bash
## === Kernel Patch Upgrade (aliVersion) ===

# Step 1: Query available upgrade versions
aliyun elasticsearch upgrade-info --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
# If Result.UpgradeInfo.Upgrade == true, use upgradeApackVersion as target version

# Step 2: [MANDATORY GATE] Dry-run validation — MUST be run and MUST pass before executing the upgrade.
# It validates cluster health, config compatibility, resources and snapshots.
aliyun elasticsearch upgrade-engine-version --instance-id es-cn-xxxxx --dry-run true \
  --region cn-hangzhou \
  --body '{"version":"2.2.8","type":"aliVersion"}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
# Inspect Result[].status per validateType. If ANY check has status=failed you MUST STOP and resolve it before Step 3:
#   - checkClusterSnapshot failed (errorType=clusterSnapshot, e.g. errorCode=WithInvalidElasticsearchSnapshots,
#     errorMsg "最近一个小时内未有已完成的集群快照，请进行快照备份"): a COMPLETED snapshot within the last hour is REQUIRED.
#     BLOCK and ASK the user whether to create a snapshot now. If yes, trigger CreateSnapshot
#     (see config-manage.md → CreateSnapshot: aliyun elasticsearch create-snapshot --instance-id es-cn-xxxxx --client-token $(uuidgen) ...),
#     wait until the snapshot completes, then re-run this dry-run.
#   - checkClusterHealth / checkConfigCompatible / checkClusterResource failed: resolve the reported issue first.
# Do NOT run the actual upgrade until the dry-run passes (every check status=success).

# Step 3: Execute upgrade (only after dry-run passes)
aliyun elasticsearch upgrade-engine-version --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --body '{"version":"2.2.8","type":"aliVersion"}' \
  --client-token $(uuidgen) \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields (dryRun=true)**

When `dryRun=true`, the response contains validation results for 4 checks:

| Field | Description |
|---|---|
| `Result[].validateType` | Check type: `checkClusterHealth` / `checkConfigCompatible` / `checkClusterResource` / `checkClusterSnapshot` |
| `Result[].status` | `success` or `failed` |
| `Result[].validateResult[].errorType` | Error category: `clusterStatus` / `clusterConfigYml` / `clusterConfigPlugins` / `clusterResource` / `clusterSnapshot` |
| `Result[].validateResult[].errorCode` | Error code (e.g. `ClusterStatusNotHealth`, `ClusterYamlNotCompatible`, `WithInvalidElasticsearchSnapshots`) |
| `Result[].validateResult[].errorMsg` | Error message |
| `RequestId` | Request ID |

**Response Fields (dryRun=false / actual upgrade)**

| Field | Description |
|---|---|
| `Result` | Upgrade result |
| `RequestId` | Request ID |

---

### 12. ListActionRecords

Query the management change records (action records) of an instance over a time window. Use this to **track how a version upgrade / config change is progressing** (e.g. how far the gray restart has advanced, how many nodes are done).

- **API**: `ListActionRecords`
- **HTTP**: `GET /openapi/instances/{InstanceId}/action-records`
- **Read-only**: Yes — no `clientToken` needed.

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `actionNames` | Query | No | Filter by action name(s), e.g. the upgrade action |
| `filter` | Query | No | Additional filter expression |
| `requestId` | Query | No | Filter by the request ID of a specific change |
| `userId` | Query | No | Filter by operator user ID |
| `startTime` | Query | No | Start time (epoch millis) |
| `endTime` | Query | No | End time (epoch millis) |
| `page` | Query | No | Page number |
| `size` | Query | No | Page size |

**CLI Example**

```bash
aliyun elasticsearch list-action-records --instance-id es-cn-xxxxx \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `RequestId` | Request ID |
| `Headers.X-Total-Count` / `Headers.totalCount` | Total number of change records |
| `Result[]` | Array of change records |
| `Result[].actionName` | Change action name, e.g. `UpgradeEngineVersion` (use as `actionNames` filter) |
| `Result[].actionParams.type` | Action sub-type, e.g. `engineVersion` (major version) / `aliVersion` (kernel patch) |
| `Result[].instanceId` | Instance ID |
| `Result[].stateType` | Overall change state, e.g. `ACTIVATING` (in progress) / `FINISHED` |
| `Result[].requestId` | **Change ID** of this action record (the id needed to continue an in-progress change) |
| `Result[].startTime` | Start time (epoch millis) |
| `Result[].metaOld` / `Result[].metaNow` | Source / target version, e.g. `"8.15.1_with_X-Pack"` → `"8.17.0_with_X-Pack"` |
| `Result[].recordDiff` | Change diff, e.g. `upgradeSetting/version.old` / `.now` |
| `Result[].canCancelable` / `Result[].interruptible` | Whether the change can be cancelled / interrupted |
| `Result[].statusInfo[]` | High-level phase list |
| `Result[].statusInfo[].subState` | Phase name, e.g. `INITIALLY` / `updating-task` |
| `Result[].statusInfo[].stateType` | Phase state: `FINISHED` / `ACTIVATING` |
| `Result[].statusInfo[].detail.pendingOperationNodesCount` | Number of nodes still pending operation |
| `Result[].changeDetail.stateType` | Detailed change state, e.g. `UPDATING` / `OK` |
| `Result[].changeDetail.grayType` | Gray state (mirror of `detail.grayType`) |
| `Result[].changeDetail.detail.hasDoneNodeCount` / `.totalNodeCount` | Completed / total node count (gray progress) |
| `Result[].changeDetail.detail.subTasks[]` | Nested sub-tasks (`initially` / `createNode` / `deleteNode` / `ending`) each with `stateType`, `progress`, `startTime`, `endTime`, and `detail.nodeStatusRecordList[]` per-node status |
| `Result[].detail.changeId` | Change ID (same as `requestId`) |
| `Result[].detail.grayType` | **Gray state** — `grayDone` means the gray batch is complete (ready to continue the remaining nodes). Use this field to judge gray completion. |
| `Result[].detail.elasticsearchStatus` | Instance status during the change, e.g. `Updating` |
| `Result[].detail.updateItem[]` | Per-node update items: `name`, `phase`, `ready`, `restartCount`, `pendingOperation.type` (`Remove` / `None`) |

> **Tip — judging gray completion**: when `detail.grayType == "grayDone"`, the gray phase has finished and the remaining nodes can be continued via the continuation API using `Result[].requestId` (= `detail.changeId`) as the change id.

---

### 13. ContinueEsVersionUpgrade

Continue a gray version upgrade: after the gray batch of nodes has been upgraded and validated (i.e. `ListActionRecords` shows `detail.grayType == "grayDone"`), call this API to **continue upgrading the remaining nodes** and finish the change.

- **API**: `ContinueEsVersionUpgrade`
- **HTTP**: `POST /openapi/instances/{InstanceId}/actions/continueEsVersionUpgrade`
- **Write**: Yes — uses `X-Request-ChangeId` (not `clientToken`).
- **CLI note**: This API is not yet published as a named subcommand (`aliyun elasticsearch continue-es-version-upgrade` does NOT exist in the CLI). Use the general ROA method+url form shown below until it is available. The general invocation REQUIRES `--roa 2017-06-13` and `--force` to bypass plugin API path validation (otherwise it fails with `can not find api by path`). `X-Request-ChangeId` MUST be passed as a URL **query** parameter, NOT a header.

> **Important Behaviors**
> - Only call this after the gray batch has completed (`ListActionRecords` → `detail.grayType == "grayDone"`); it proceeds to upgrade the remaining nodes.
> - `X-Request-ChangeId` identifies which in-progress upgrade to continue — obtain it from `ListActionRecords` (`Result[].requestId`, i.e. `detail.changeId`).

**Parameters**

| Name | Position | Required | Description |
|---|---|---|---|
| `InstanceId` | Path | Yes | Instance ID |
| `X-Request-ChangeId` | Query | No | Change ID of the in-progress gray upgrade to continue (from `ListActionRecords`) |

**CLI Example**

```bash
aliyun elasticsearch POST "/openapi/instances/es-cn-xxxxx/actions/continueEsVersionUpgrade?X-Request-ChangeId=<changeId>" \
  --roa 2017-06-13 --force \
  --region cn-hangzhou \
  --connect-timeout 3 \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

**Response Fields**

| Field | Description |
|---|---|
| `Result` | `true` if the continuation was triggered successfully |
| `RequestId` | Request ID |

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
- [UpdateAdminPassword](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/UpdateAdminPassword)
- [UpdateDescription](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/UpdateDescription)
- [UpdateInstanceChargeType](https://help.aliyun.com/zh/es/developer-reference/api-updateinstancechargetype)
- [UpgradeInfo](https://api.aliyun.com/api/elasticsearch/2017-06-13/UpgradeInfo)
- [UpgradeEngineVersion](https://help.aliyun.com/zh/es/developer-reference/api-upgradeengineversion)
- [ListActionRecords](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/ListActionRecords)
- [ContinueEsVersionUpgrade](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/ContinueEsVersionUpgrade)
- [Elasticsearch Pricing](https://www.aliyun.com/price/product#/elasticsearch/detail)
