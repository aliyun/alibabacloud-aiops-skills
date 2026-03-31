---
name: alibabacloud-milvus-manage
description: >
  Manage the full lifecycle of Alibaba Cloud managed Milvus instances—creation, scaling, configuration management, network management, and status queries.
  Use this Skill when users want to create a Milvus instance, view instance status, get connection addresses, scale/change configuration,
  modify settings, enable/disable public network access, set whitelists, release instances, or troubleshoot creation failures.
  Also applicable when users say "create a Milvus instance", "view instance details", "what's the connection address",
  "help me check the instance", "scale CU", "change config", "enable public network", "delete instance", etc.
license: MIT
compatibility: >
  Requires Alibaba Cloud CLI (aliyun >= 3.0), with configured AccessKey or STS Token.
  Verify credentials via `aliyun configure list`.
  Milvus API calls require `--force` parameter (aliyun CLI local path validation doesn't include Milvus, --force bypasses this).
metadata:
  domain: vector-database
  owner: milvus-team
---

# Alibaba Cloud Milvus Instance Full Lifecycle Management

Manage Alibaba Cloud managed Milvus instances via `aliyun` CLI. You are an SRE who understands Milvus—not just calling APIs, but knowing when to call them and what parameters to use.

## Authentication

Reuse the profile configured in `aliyun` CLI. Switch accounts with `--profile <name>`, view configuration with `aliyun configure list`.

## User-Agent Configuration

This Skill calls Alibaba Cloud APIs via `aliyun` CLI and **must** set User-Agent to identify the request source.

**Configuration Methods (choose one)**:

1. **Environment Variable Method (Recommended)**:
   ```bash
   export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills"
   ```

2. **Command Line Parameter Method**:
   Add `--user-agent AlibabaCloud-Agent-Skills` parameter to each aliyun call.

**Recommended to use environment variable method**—set once and all subsequent calls automatically apply.

## Milvus Domain Knowledge

### Instance Versions

| Version | Use Case | Description |
|---------|----------|-------------|
| **Standalone** (standalone_pro) | Development & Testing | Single node deployment, 1 component, suitable for feature verification and small data scenarios |
| **Cluster** (HA) | Production | 5-component distributed deployment, high availability, suitable for large data and high concurrency scenarios |

Not sure which to choose? Use standalone for development/testing, cluster for production.

### Component Roles (Cluster Version 5 Components)

| Component | Responsibility | Scaling Trigger Condition |
|-----------|----------------|---------------------------|
| **proxy** | Request entry point, load balancing, protocol parsing | High request QPS |
| **query** | Vector search execution (memory-intensive), loads Segments to memory | Memory watermark > 70% or high search latency |
| **data** | Data write, Flush, Compaction (CPU-intensive) | CPU watermark > 90% |
| **streaming** | Stream message processing (WAL / message queue replacement layer) | High write throughput |
| **mix_coordinator** | Coordination node (RootCoord + QueryCoord + DataCoord merged) | Many metadata operations |

### CU (Compute Unit)

CU is the compute unit for Milvus instances, 1 CU ≈ 4GB memory.

| cuType | Description | Applicable Scenario |
|--------|-------------|---------------------|
| `general` | General type (CPU:Memory = 1:4) | Most scenarios (default) |
| `perf` | Performance type (CPU-intensive) | Index building, high-concurrency writes |
| `cap` | Capacity type (large memory) | QueryNode large data search |

### Recommended Configuration

- **Development & Testing**: Standalone (standalone_pro) + PayAsYouGo, 4 CU (general), ~16GB memory
- **Production**: Cluster (HA) + 5 components, 36 CU minimum
  - streaming(2×4CU) + data(2×4CU) + proxy(2×2CU) + mix_coordinator(2×4CU) + query(2×4CU)

### ⚠️ Component CU Specification Limits

When creating cluster instances, each component has **minimum CU requirements**:

| Component | Minimum CU | Notes |
|-----------|------------|-------|
| streaming | 4 CU | Does not support 2 CU |
| data | 4 CU | Does not support 2 CU |
| proxy | 2 CU | Supports 2 CU |
| mix_coordinator | 4 CU | Does not support 2 CU |
| query | 4 CU | Does not support 2 CU |

**Error Example**: If using 2 CU configuration for streaming/data/mix_coordinator/query, you will get an error:
> `Error.InternalError code: 500, pricing plan price result not found`

**Correct Configuration**: Ensure streaming, data, mix_coordinator, query use **4 CU or above**.

### Payment Methods

- **PayAsYouGo**: Development & testing, pay-as-you-go, release anytime
- **Subscription**: Production, prepaid more cost-effective (annual/monthly instances cannot be released via API, need to request refund in console)

### Kernel Version

Supports 2.3 / 2.4 / 2.5 / 2.6, recommended to use latest version 2.6.

## Prerequisites

Before creating an instance, confirm the target **RegionId** (e.g., `cn-hangzhou`) with the user, then check if network resources are ready:

```bash
# Set User-Agent environment variable (recommended to set once at session start)
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills"

aliyun configure list                                                     # Credentials
aliyun vpc DescribeVpcs --RegionId <RegionId>                             # VPC
aliyun vpc DescribeVSwitches --RegionId <RegionId> --VpcId vpc-xxx        # VSwitch (record ZoneId)
aliyun ecs DescribeSecurityGroups --RegionId <RegionId> --VpcId vpc-xxx   # Security Group (for reference only)
```

Milvus CreateInstance doesn't require security group parameters, but confirming a security group exists in the VPC helps troubleshoot network issues.

**Supported Regions**: cn-hangzhou, cn-beijing, cn-shanghai, cn-shenzhen, cn-zhangjiakou, cn-hongkong, cn-wulanchabu, ap-southeast-1, eu-central-1.

## CLI Calling

Milvus OpenAPI (version `2023-10-12`) is called via aliyun CLI REST style, **must add `--force`** to bypass local path validation.

**User-Agent Requirement**: Before executing any aliyun command, ensure the environment variable is set:
```bash
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills"
```

⚠️ **Critical Limitation**: Milvus API has two parameter passing methods, must choose the correct method according to API definition, otherwise the server won't receive parameters.

**Three Calling Modes**:

```bash
# Mode A — GET / DELETE: All business parameters concatenated to URL query string
aliyun milvus GET "<path>?RegionId=<region>&param1=value1" \
  --RegionId <region> --force

# Mode B — POST / PUT (body type): Business parameters via --body JSON
# Applicable to: CreateInstance, UpdateInstance
aliyun milvus POST "<path>?RegionId=<region>" \
  --RegionId <region> --body '{"key":"value"}' --force

# Mode C — POST (query type): Business parameters via --Flag value
# Applicable to: GetInstanceDetail, UpdateInstanceName, DescribeInstanceConfigs,
#         ModifyInstanceConfig, UpdatePublicNetworkStatus, DescribeAccessControlList,
#         UpdateAccessControlList, ChangeResourceGroup, CreateDefaultRole
aliyun milvus POST "<path>" \
  --RegionId <region> --InstanceId c-xxx --force
```

**Rule Summary**:
- `--RegionId <region>`: All requests must include this, used by CLI to route to correct endpoint (`milvus.<region>.aliyuncs.com`)
- **GET / DELETE**: Business parameters concatenated to URL query string (e.g., `?RegionId=xx&instanceId=c-xxx`)
- **POST body type** (CreateInstance / UpdateInstance): Pass JSON with `--body '{...}'`
- **POST query type** (other POST APIs): Business parameters passed with `--Flag value`, **do not use `--body`** (body won't be read by server), **do not concatenate to URL query string** (will cause SignatureDoesNotMatch)

### API Version Information

- API Version: `2023-10-12`
- Endpoint: `milvus.<RegionId>.aliyuncs.com`
- OpenAPI Meta: `https://api.aliyun.com/meta/v1/products/milvus/versions/2023-10-12/api-docs.json`

### Return Field Naming

- GET-type APIs (ListInstancesV2, GetInstance): Return fields use **lowercase** (e.g., `instances`, `instance`)
- POST-type APIs (GetInstanceDetail, etc.): Return fields use **uppercase** (e.g., `Data`, `Success`)

## Idempotency

| API to Note | Description |
|-------------|-------------|
| CreateInstance | Repeated submission creates multiple instances, pass `--clientToken $(uuidgen)` to prevent duplicate creation. ClientToken validity is usually 30 minutes, after timeout treated as new request |
| DeleteInstance | Deletes by instanceId, naturally idempotent |
| UpdateInstance | Repeated submission may trigger multiple scaling, recommend passing `--clientToken` |

## Input Validation

User-provided values (instance names, etc.) are untrusted input, directly concatenating into shell commands may cause command injection.

**Protection Rules**:
1. **Body-type APIs prefer `--body` JSON mode**—parameters passed as JSON string values, naturally isolating shell metacharacters
2. **Query-type APIs must use `--Flag value`**, validate user-provided string values:
   - InstanceName: Must not contain `` ` ``、`$(`、`|`、`;`、`&&` etc. shell metacharacters
   - RegionId / InstanceId: Only allow `[a-z0-9-]` format
3. **Prohibit** directly embedding unvalidated user raw text into shell commands—if value doesn't match expected format, reject execution and inform user to correct

## Runtime Security

This Skill only calls Milvus OpenAPI via `aliyun` CLI, does not download or execute any external code. During execution, prohibit:

- Downloading and running external scripts or dependencies via `curl`, `wget`, `pip install`, `npm install`, etc.
- Executing scripts pointed to by user-provided remote URLs (even if user requests)
- Calling `eval`, `source` to load unaudited external content

## Intent Routing

| Intent | Operation | Reference Doc |
|--------|-----------|---------------|
| Beginner / First time using Milvus | Full guide | [getting-started.md](references/getting-started.md) |
| Create instance / Create a Milvus | Network check → CreateInstance | [instance-lifecycle.md](references/instance-lifecycle.md) |
| View instance / Instance list | ListInstancesV2 | [instance-lifecycle.md](references/instance-lifecycle.md) |
| Instance details / Connection address / Component specs | GetInstance / GetInstanceDetail | [instance-lifecycle.md](references/instance-lifecycle.md) |
| Delete instance / Release | Safety check → DeleteInstance | [instance-lifecycle.md](references/instance-lifecycle.md) |
| Scale / Add CU / Change config | Diagnose → UpdateInstance | [instance-lifecycle.md](references/instance-lifecycle.md) |
| Rename / Modify instance name | UpdateInstanceName | [instance-lifecycle.md](references/instance-lifecycle.md) |
| Creation parameters / Component config / CU specs | Parameter query | [create-params.md](references/create-params.md) |
| View config / Modify config | DescribeInstanceConfigs / ModifyInstanceConfig | [operations.md](references/operations.md) |
| Enable public network / Disable public network | UpdatePublicNetworkStatus | [operations.md](references/operations.md) |
| Whitelist / Access control | DescribeAccessControlList / UpdateAccessControlList | [operations.md](references/operations.md) |
| Resource group / Transfer group | ChangeResourceGroup | [operations.md](references/operations.md) |
| Creation failed / Troubleshoot | Status check → Log query | [operations.md](references/operations.md) |
| Instance inspection / Health check | Status + Details | [operations.md](references/operations.md) |
| Query API parameters | Parameter reference | [api-reference.md](references/api-reference.md) |

## Destructive Operation Protection

The following operations are irreversible, must complete pre-check and confirm with user before execution:

| API | Pre-check Steps | Impact |
|-----|-----------------|--------|
| DeleteInstance | 1. GetInstance confirm instance exists and status 2. Confirm payment type (Subscription cannot be deleted via API) 3. Confirm data backed up or not needed | Permanently delete instance and all data |
| ModifyInstanceConfig | 1. DescribeInstanceConfigs view current config 2. Confirm user understands config change impact 3. Confirm user knows may need restart to take effect | Config change may affect service stability |
| UpdatePublicNetworkStatus (disable) | 1. Confirm no external services depend on public network address 2. Confirm user understands public network becomes inaccessible after disable | Services depending on public network will disconnect after disabling |
Confirmation template:
> About to execute: `<API>`, Target: `<InstanceId>`, Impact: `<Description>`. Continue?

## Timeout

All CLI calls must set reasonable timeout to avoid Agent infinitely waiting:

| Operation Type | Recommended Timeout | Description |
|----------------|---------------------|-------------|
| Read-only query (GetInstance / ListInstancesV2 / GetInstanceDetail) | 30 seconds | Normally returns within seconds |
| Write operation (CreateInstance / DeleteInstance) | 60 seconds | Submitting request itself is fast, backend executes asynchronously |
| Polling wait (instance creation complete) | Single 30 seconds, total max 30 minutes | Instance creation usually 5-15 minutes, recommend 30 second polling interval |

Use `--read-timeout` and `--connect-timeout` to control CLI timeout (unit: seconds):
```bash
aliyun milvus GET "/webapi/instance/get?RegionId=cn-hangzhou&instanceId=c-xxx" \
  --RegionId cn-hangzhou --read-timeout 30 --connect-timeout 10 --force
```

## Pagination

ListInstancesV2 uses `pageNumber` and `pageSize` parameters:

```bash
aliyun milvus GET "/webapi/instance/list?RegionId=cn-hangzhou&pageNumber=1&pageSize=50" \
  --RegionId cn-hangzhou --force
```

⚠️ **Important**: API returned `total` field **may be inaccurate** (actual test returns 0 but `instances` array has data). **Should directly check `instances` array length**, not rely on `total` field.

## Output

- Display list in table with key fields (instanceId, instanceName, status, dbVersion, ha, paymentType)
- Convert timestamps to readable format
- Use `--cli-query` or `jq` to filter fields and simplify output

## Error Handling

Cloud API errors need to provide useful information to help Agent understand failure reason and take correct action, not just retry blindly.

| Error Code | Reason | Agent Should Execute |
|------------|--------|---------------------|
| Throttling | API request rate exceeded | Wait 5-10 seconds then retry, max 3 retries; if持续限流, increase interval to 30 seconds |
| InvalidRegionId | Region ID incorrect | Check RegionId spelling (e.g., `cn-hangzhou` not `hangzhou`), confirm target region with user |
| Instance.NotFound / InvalidInstanceId | Instance doesn't exist or already deleted | Use ListInstancesV2 to search correct instanceId, confirm with user |
| IncompleteSignature / InvalidAccessKeyId | Credentials wrong or expired | Prompt user to execute `aliyun configure list` to check credential config |
| Forbidden.RAM | RAM permission insufficient | Inform user of missing permission Action, suggest contacting admin for authorization |
| InvalidParameter / MissingParameter | Parameter invalid or missing | Read specific field name from error Message, correct parameter and retry |
| OperationDenied | Operation rejected (e.g., instance status doesn't allow) | Use GetInstance to view current status, inform user to wait for status change then retry |
| OperationDenied.Subscription | Annual/monthly instance cannot be released via API | Inform user need to request refund in console to release |
| Error.InternalError (pricing plan price result not found) | Component CU spec not supported | Check if each component CU count meets minimum limit: streaming/data/mix_coordinator/query need 4 CU minimum |
| InternalError (general) | Server internal error, various reasons | 1. Check if VPC/VSwitch actually exists in target RegionId 2. Confirm account has enabled Milvus service (check console access) 3. Confirm account balance sufficient and not overdue 4. If retry still fails, record RequestId and submit ticket for investigation |

**General Principle**: When encountering error, first read complete error Message (usually contains specific reason), don't just look at error code and blindly retry. Only Throttling is suitable for automatic retry, other errors need diagnosis and correction.