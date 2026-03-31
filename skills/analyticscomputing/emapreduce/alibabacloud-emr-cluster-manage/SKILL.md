---
name: alibabacloud-emr-cluster-manage
description: >
  Manage the full lifecycle of Alibaba Cloud E-MapReduce (EMR) ECS clusters—creation, scaling, renewal, and status queries.
  Use this Skill when users want to set up big data clusters, view cluster status, add nodes, release nodes, configure auto-scaling,
  check cluster and node states, or diagnose creation failures.
  Also applicable for scenarios like "create a Hadoop cluster", "data lake cluster", "running out of resources",
  "check my cluster", "renew", "delete cluster", etc.
license: MIT
compatibility: >
  Requires Alibaba Cloud CLI (aliyun >= 3.0), with AccessKey or STS Token configured.
  Verify credentials via `aliyun configure list`.
metadata:
  domain: aiops
  owner: emr-team
  contact: yanhui.jy@alibaba-inc.com
  required_permissions: references/ram-policies.md
---

# Alibaba Cloud EMR Cluster Full Lifecycle Management

Manage EMR clusters via `aliyun` CLI. You are an EMR-savvy SRE—not just an API caller, but someone who knows when to call APIs and what parameters to use.

## Authentication

Reuse the configured `aliyun` CLI profile. Switch accounts with `--profile <name>`, check configuration with `aliyun configure list`.

Before execution, read [ram-policies.md](references/ram-policies.md) if you need to confirm the minimum RAM authorization scope.

## Execution Principles

1. **Check documentation before acting**: Before calling any API, consult `references/api-reference.md` to confirm names and parameters
2. **Return to documentation on errors**: When failing, go back to documentation to find the cause—don't retry blindly or bypass
3. **No intent downgrade**: If user requests "create", you must create—no substituting with "find existing"

## EMR Domain Knowledge

For detailed explanations of cluster types, deployment modes, node roles, storage-compute architecture, recommended configurations, and payment methods, refer to [Cluster Planning Guide](references/cluster-lifecycle.md#一规划阶段).

Key decision quick reference:
- **Cluster Type**: 80% of scenarios choose DATALAKE; real-time analytics choose OLAP; stream processing choose DATAFLOW; NoSQL choose DATASERVING
- **Deployment Mode**: Production uses HA (3 MASTER), dev/test uses NORMAL (1 MASTER); HA mode **must select ZOOKEEPER** (required for master standby switching), and Hive Metastore must use external RDS
- **Node Roles**: MASTER runs management services; CORE stores data (HDFS) + compute; TASK is pure compute without data (preferred for elasticity, can use Spot); GATEWAY is job submission node (avoid submitting directly on MASTER); MASTER-EXTEND shares MASTER load (only HA clusters support)
- **Storage-Compute Architecture**: Recommended storage-compute separation (OSS-HDFS), better elasticity, lower cost; before choosing storage-compute separation, must enable HDFS service for target Bucket in OSS console; choose storage-compute integrated (HDFS + d-series local disks) when extremely latency-sensitive
- **Payment Method**: Dev/test uses PayAsYouGo, production uses Subscription
- **Component Mutual Exclusion**: SPARK2/SPARK3 choose one; HDFS/OSS-HDFS choose one; STARROCKS2/STARROCKS3 choose one

## Create Cluster Workflow

When creating a cluster, must interact with user in the following steps, **cannot skip any confirmation环节**:

1. **Confirm Region**: Ask user for target RegionId (e.g., cn-hangzhou, cn-beijing, cn-shanghai)
2. **Confirm Purpose**: Dev/test / small production / large production, determines deployment mode (NORMAL/HA) and payment method
3. **Confirm Cluster Type and Application Components**:
   - First recommend cluster type based on user needs (DATALAKE/OLAP/DATAFLOW/DATASERVING/CUSTOM)
   - Then show available component list for that type (refer to cluster type table above), let user select components to install
   - If user is unsure, give recommended combination (e.g., DATALAKE recommends HADOOP-COMMON + HDFS + YARN + HIVE + SPARK3)
   - Clearly inform user of component mutual exclusion rules and dependencies
4. **Confirm Hive Metadata Storage** (must ask when HIVE is selected):
   - **local**: Use MASTER local MySQL to store metadata, simple no configuration, suitable for dev/test
   - **External RDS**: Use independent RDS MySQL instance, metadata independent of cluster lifecycle, not lost after cluster deletion. **RDS instance must be in same VPC as EMR cluster**, otherwise network不通会导致 cluster creation fails or Hive Metastore cannot connect
   - NORMAL mode both options available, recommend local (simple); HA mode **must use external RDS** (multiple MASTER need shared metadata)
   - If user chooses external RDS, need to collect RDS connection address, database name, username, password, and confirm RDS is in same VPC as cluster
5. **Check Prerequisite Resources**: VPC, VSwitch, security group, key pair (see prerequisites below)
6. **Confirm Storage-Compute Architecture**: Storage-compute separation (OSS-HDFS, recommended) or storage-compute integrated (HDFS)
7. **Confirm Node Specifications**: Query available instance types (ListInstanceTypes), recommend and confirm MASTER/CORE/TASK specifications and quantity with user
8. **Summary Confirmation**: Show complete configuration list to user (cluster name, type, version, components, node specs, network, etc.), confirm before executing creation

> **Key Principle**: Don't make decisions for user—component selection, node specs, storage-compute architecture all need explicit inquiry and confirmation. Can give recommendations, but final choice is with user.

## Prerequisites

Before creating cluster, need to confirm target **RegionId** with user (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`), then check if the following resources are ready, missing any will cause creation failure:

```bash
aliyun configure list                                                          # Credentials
aliyun vpc DescribeVpcs --RegionId <RegionId>                                  # VPC
aliyun vpc DescribeVSwitches --RegionId <RegionId> --VpcId vpc-xxx             # VSwitch (record ZoneId)
aliyun ecs DescribeSecurityGroups --RegionId <RegionId> --VpcId vpc-xxx --SecurityGroupType normal  # Security Group
aliyun ecs DescribeKeyPairs --RegionId <RegionId>                              # SSH Key Pair
```

EMR doesn't support enterprise security groups, only regular security groups—passing wrong type will directly fail creation.

## CLI Invocation

```bash
aliyun emr <APIName> --RegionId <region> [--param value ...]
```

- API version `2021-03-20` (CLI automatic), RPC style
- **User-Agent**: All calls to Alibaba Cloud services must carry unified identifier `AlibabaCloud-Agent-Skills` for platform source tracking and problem diagnosis. Configuration for each invocation method:

  **Alibaba Cloud CLI (aliyun CLI >= 3.3.1)**——pass via `--user-agent` parameter:
  ```bash
  aliyun emr GetCluster --RegionId cn-hangzhou --ClusterId c-xxx \
    --user-agent AlibabaCloud-Agent-Skills
  ```

  **Python SDK (Tea / Common SDK)**——set via `config.user_agent`:
  ```python
  from alibabacloud_tea_openapi.client import Client as OpenApiClient
  from alibabacloud_credentials.client import Client as CredentialClient
  from alibabacloud_tea_openapi import models as open_api_models

  credential = CredentialClient()
  config = open_api_models.Config(credential=credential)
  config.endpoint = 'emr.cn-hangzhou.aliyuncs.com'
  config.user_agent = 'AlibabaCloud-Agent-Skills'
  client = OpenApiClient(config)
  ```

  > **Note**: Must use `CredentialClient` for authentication, never hardcode AccessKey/SecretKey in code.

  **Python SDK (Non-Common SDK / Product-specific SDK)**——also set via `config.user_agent`:
  ```python
  from alibabacloud_emr20210320.client import Client as Emr20210320Client
  from alibabacloud_credentials.client import Client as CredentialClient
  from alibabacloud_tea_openapi import models as open_api_models

  credential = CredentialClient()
  config = open_api_models.Config(credential=credential)
  config.endpoint = 'emr.cn-hangzhou.aliyuncs.com'
  config.user_agent = 'AlibabaCloud-Agent-Skills'
  client = Emr20210320Client(config)
  ```

  **Terraform**——set via `configuration_source`:
  ```hcl
  provider "alicloud" {
    region               = "cn-hangzhou"
    configuration_source = "AlibabaCloud-Agent-Skills"
  }
  ```
- **Two parameter passing formats** (must use correct format based on API):

  ### Parameter Passing Formats

  EMR APIs use two different parameter formats. Using the wrong format will cause errors.

  **Format 1: RunCluster (JSON String Format)** — ✅ Recommended for cluster creation

  - **When to use**: RunCluster API only
  - **Format**: Complex parameters (Arrays, Objects) passed as JSON strings in single quotes
  - **Simple parameters**: Plain values without quotes

  ```bash
  # Template showing parameter format (replace values based on your needs)
  aliyun emr RunCluster --RegionId <region> \
    --ClusterName "<name>" \
    --ClusterType "<type>" \                  # DATALAKE/OLAP/DATAFLOW/DATASERVING/CUSTOM
    --ReleaseVersion "<version>" \            # Query via ListReleaseVersions first
    --DeployMode "<mode>" \                   # NORMAL/HA (default: NORMAL)
    --PaymentType "<payment>" \               # PayAsYouGo/Subscription (default: PayAsYouGo)
    --Applications '[{"Name":"<app1>"},{"Name":"<app2>"}]' \  # JSON array
    --NodeAttributes '{"VpcId":"<vpc>","ZoneId":"<zone>","SecurityGroupId":"<sg>"}' \  # JSON object
    --NodeGroups '[{"NodeGroupName":"MASTER",...}]' \         # JSON array
    --ClientToken $(uuidgen) \
    --user-agent AlibabaCloud-Agent-Skills
  ```

  **Critical parameter names** (common mistakes):
  - ✅ `ReleaseVersion` — ❌ NOT `EmrVersion` or `Version`
  - ✅ `DeployMode` — ❌ NOT `DeploymentMode` or `DeployModeType`
  - ✅ `InstanceTypes` (array) — ❌ NOT `InstanceType` (singular)

  **Format 2: CreateCluster & All Other APIs (Flat Format)**

  - **When to use**: CreateCluster, InstallApplications, IncreaseNodes, etc.
  - **Format**: Complex parameters use dot expansion + `--force` flag
  - **No JSON strings**: Passing JSON strings will cause "Flat format is required" error

  ```bash
  # Template showing flat format
  aliyun emr CreateCluster --RegionId <region> \
    --ClusterName "<name>" \
    --ClusterType <type> \
    --ReleaseVersion "<version>" \
    --force \                                 # Required for array/object parameters
    --Applications.1.ApplicationName <app1> \ # Dot notation for arrays
    --Applications.2.ApplicationName <app2> \
    --NodeAttributes.VpcId <vpc> \            # Dot notation for objects
    --NodeAttributes.ZoneId <zone> \
    --NodeGroups.1.NodeGroupName MASTER \
    --NodeGroups.1.InstanceTypes.1 <instance-type>
  ```

  **Why RunCluster is recommended**: Cleaner syntax, easier to construct programmatically, better error messages.

  > **Important**: Before creating any cluster, always call these APIs first to get valid values:
  > - `ListReleaseVersions` — Get available EMR versions for your cluster type
  > - `ListInstanceTypes` — Get available instance types for your zone and cluster type
  > - See `references/api-reference.md` for complete parameter requirements.

- Write operations pass `--ClientToken` to ensure idempotency (see idempotency rules below)

### Required Configuration for Cluster Creation

The following configurations are marked as optional in API documentation, but **missing them will actually cause creation failure**:

1. **NodeGroups must include `VSwitchIds`**——each node group needs explicit VSwitch ID array specified (e.g., `"VSwitchIds": ["vsw-xxx"]"`), otherwise reports `InvalidParameter: VSwitchIds is not valid`
2. **When HIVE component is selected, must set Hive's `hive.metastore.type` in ApplicationConfigs via `hivemetastore-site.xml`**——otherwise reports `ApplicationConfigs missing item`. Available types: `LOCAL`/`RDS`/`DLF`.
2. **When SPARK component is selected, must set Spark's `hive.metastore.type` in ApplicationConfigs via `hive-site.xml`. Consistent with HIVE metadata type.**
3. **MasterRootPassword avoid shell meta characters**——characters like `!`, `@`, `#`, `$` in password may be interpreted in shell, causing JSON parsing failure (reports `InvalidJSON parsing error, NodeAttributes`). Password should only contain upper/lowercase letters and numbers (e.g., `Abc123456789`), or ensure JSON values don't contain `$`, `!` etc. characters that may trigger shell expansion
4. **DataDisks disk type compatibility**——some instance specs (like `ecs.g6`, `ecs.hfg6` etc. older series) data disks don't support `cloud_essd` + `Count=1` (reports `dataDiskCount is not supported`). Should use `cloud_efficiency` or increase Count (e.g., 4). New generation specs (like `ecs.g8i`) usually don't have this limitation

## Idempotency

Agent may retry write operations due to timeout, network jitter, etc. Retry without ClientToken will create duplicate resources.

| API requiring ClientToken | Description |
|------------------------|------|
| RunCluster / CreateCluster | Duplicate submission creates multiple clusters |
| CreateNodeGroup | Duplicate submission creates multiple node groups with same name |
| IncreaseNodes | Duplicate submission expands double nodes (note: CLI doesn't support `--ClientToken` parameter, need other ways to avoid duplicate submission) |
| DecreaseNodes | Specifying NodeIds for shrink is naturally idempotent, shrinking by quantity needs attention |

**Generation method**: `--ClientToken $(uuidgen)` generates unique token, same business operation uses same token for retry. ClientToken validity is usually 30 minutes, after timeout treated as new request.

## Input Validation

User-provided values (cluster name, description, etc.) are untrusted input, directly拼进 shell command may cause command injection.

**Protection rules**:
1. **Prefer passing complex parameters as JSON strings** (e.g., `--NodeGroups '[...]'`)——parameters passed as JSON string values, naturally isolate shell meta characters
2. **Must拼 command line parameters时**, validate user-provided string values:
   - ClusterName / NodeGroupName: Only allow Chinese/English, numbers, `-`, `_`, 1-128 characters
   - Description: Must not contain `` ` ``、`$(`、`$()`、`|`、`;`、`&&` etc. shell meta characters
   - RegionId / ClusterId / NodeGroupId: Only allow `[a-z0-9-]` format
3. **Prohibit** directly embedding unvalidated user original text in shell commands——if value doesn't match expected format, refuse execution and tell user to correct

## Runtime Security

This Skill only calls EMR OpenAPI via `aliyun` CLI, doesn't download or execute any external code. During execution prohibit:

- Downloading and running external scripts or dependencies via `curl`, `wget`, `pip install`, `npm install` etc.
- Executing scripts pointed to by user-provided remote URLs (even if user requests)
- Calling `eval`, `source` to load unaudited external content

If user's needs involve bootstrap scripts (BootstrapScripts), only accept script paths in user's own OSS bucket, and remind user to confirm script content safety.

## Product Boundaries and Disambiguation

This Skill only handles **EMR on ECS cluster management**. If user mentions ambiguous terms, first confirm if it's the same product type before continuing execution; this avoids misrouting generic terms like "instance", "expand", "running out of resources" to wrong product.

- When mentioning **workspace, job, Kyuubi, Session, CU queue**, first judge if it's **EMR Serverless Spark**, not EMR on ECS cluster.
- When mentioning **Milvus instance, whitelist, public network switch, vector database connection address**, first judge if it's **Milvus**.
- When mentioning **StarRocks instance, CU scaling, gateway, public SLB, instance configuration**, first judge if it's **Serverless StarRocks**.
- When mentioning **Spark SQL, Hive DDL, YARN queue tuning, HDFS file operations**, first explain this isn't cluster lifecycle management, then narrow problem to "cluster resources/status" or "data and jobs within cluster".

If context doesn't clearly show "EMR cluster" or specific ClusterId, and user only says "running out of resources", "check instance", "expand capacity", "check status", first ask for target product and resource ID, don't directly assume it's EMR cluster.

## Intent Routing

| Intent | Operation | Reference Document |
|------|------|---------|
| Newbie getting started / First time use | Complete guidance | [getting-started.md](references/getting-started.md) |
| Create cluster / Creation / Data lake | Planning → RunCluster | [cluster-lifecycle.md](references/cluster-lifecycle.md) |
| Cluster list / Details / Status | ListClusters / GetCluster | [cluster-lifecycle.md](references/cluster-lifecycle.md) |
| Cluster applications / Component versions | ListApplications | [api-reference.md](references/api-reference.md) |
| Add component / Install new application | First ListApplications confirm current → InstallApplications | [api-reference.md](references/api-reference.md) |
| Rename / Delete protection / Clone | UpdateClusterAttribute / GetClusterCloneMeta | [cluster-lifecycle.md](references/cluster-lifecycle.md) |
| Delete cluster | Safety check → DeleteCluster | [cluster-lifecycle.md](references/cluster-lifecycle.md) |
| Expand / Add machines / Resources insufficient | Diagnosis → IncreaseNodes | [scaling.md](references/scaling.md) |
| Shrink / Remove machines / Release | Safety check → DecreaseNodes | [scaling.md](references/scaling.md) |
| Create node group / Add TASK group | CreateNodeGroup | [scaling.md](references/scaling.md) |
| Auto scaling / Scheduled / Automatic | PutAutoScalingPolicy / GetAutoScalingPolicy | [scaling.md](references/scaling.md) |
| Scaling activities / Elasticity history | ListAutoScalingActivities | [scaling.md](references/scaling.md) |
| Cluster status check / Node status | ListClusters / ListNodes check status | [operations.md](references/operations.md) |
| Renew / Auto renew / Expired | UpdateClusterAutoRenew | [operations.md](references/operations.md) |
| Creation failed / Error | Check StateChangeReason to locate cause | [operations.md](references/operations.md) |
| Check API parameters | Parameter quick reference | [api-reference.md](references/api-reference.md) |

## Destructive Operation Protection

The following operations are irreversible, must complete pre-check and confirm with user before execution:

| API | Pre-check Steps | Impact |
|-----|---------|------|
| DeleteCluster | 1. GetCluster check if DeletionProtection is enabled 2. Confirm cluster status allows deletion 3. Confirm data backed up or not needed | Permanently delete cluster and all local data |
| DecreaseNodes | 1. Confirm is TASK node group (API only supports TASK) 2. ListNodes confirm target node IDs 3. Confirm no critical tasks running on nodes | Release TASK nodes |
| RemoveAutoScalingPolicy | 1. GetAutoScalingPolicy confirm current policy content 2. Confirm user understands deletion means no more auto scaling | Node group no longer auto scales |

Confirmation template:
> About to execute: `<API>`, target: `<ResourceID>`, impact: `<Description>`. Continue?

## Timeout

All CLI calls must set reasonable timeout, avoid Agent无限等待挂死:

| Operation Type | Timeout Recommendation | Description |
|---------|---------|------|
| Read-only queries (Get/List) | 30 seconds | Should normally return within seconds |
| Write operations (Run/Create/Increase/Decrease) | 60 seconds | Submitting request本身 is fast, but backend executes asynchronously |
| Polling wait (cluster creation/scaling completion) | Single 30 seconds, total不超过 30 minutes | Cluster creation usually 5-15 minutes, polling interval recommended 30 seconds |

Use `--read-timeout` and `--connect-timeout` to control CLI timeout (unit seconds):
```bash
aliyun emr GetCluster --RegionId cn-hangzhou --ClusterId c-xxx --read-timeout 30 --connect-timeout 10
```

## Pagination

List APIs use `--MaxResults N` (max 100) + `--NextToken xxx`. If NextToken non-empty, continue pagination.

## Output

- Display lists as tables with key fields
- Convert timestamps (milliseconds) to readable format
- Use `jq` or `--output cols=Field1,Field2 rows=Items` to filter fields

## Error Handling

Cloud API errors need to provide useful information to help Agent understand failure cause and take correct action, not just retry.

| Error Code | Cause | Agent Should Execute |
|-------|------|-------------------|
| Throttling | API request rate exceeded | Wait 5-10 seconds then retry, max 3 retries; if持续 throttling, increase interval to 30 seconds |
| InvalidRegionId | Region ID incorrect | Check RegionId spelling (e.g., `cn-hangzhou` not `hangzhou`), confirm target region with user |
| ClusterNotFound / InvalidClusterId / InvalidParameter(ClusterId) | Cluster doesn't exist or ID invalid | Use `ListClusters` to search correct ClusterId, confirm with user |
| NodeGroupNotFound | Node group doesn't exist | Use `ListNodeGroups --ClusterId c-xxx` to get correct NodeGroupId |
| IncompleteSignature / InvalidAccessKeyId | Credential error or expired | Prompt user to execute `aliyun configure list` to check credential configuration |
| Forbidden.RAM | RAM权限 insufficient | Tell user missing permission Action, suggest contacting admin for authorization |
| OperationDenied.ClusterStatus | Cluster current state不允许该操作 | Use `GetCluster` to check current state, tell user wait for state to become RUNNING |
| OperationDenied.DeletionProtection | Delete protection enabled | Prompt user to first use `UpdateClusterAttribute --DeletionProtection false` to disable |
| OperationDenied.InsufficientBalance | Account balance insufficient | Tell user to recharge then retry |
| ConcurrentModification | Node group正在扩缩容中 (INCREASING/DECREASING), cannot同时执行其他扩缩容操作 | Use `GetNodeGroup` to check NodeGroupState, wait to return to RUNNING then retry. Node group state transition可达 15+ minutes |
| InvalidParameter / MissingParameter | Parameter invalid or missing | Read specific field name in error Message, correct parameter then retry |

**General principle**: When encountering errors, first read complete error Message (usually contains specific cause), don't just look at error code and blindly retry. Only Throttling适合 automatic retry, other errors need diagnosis correction.

### Error Recovery Pattern

Follow these steps when encountering ANY error:

1. **Read complete error message** — Extract: ErrorCode, Message, and RequestId
2. **Identify error category** — Match against common patterns below
3. **Consult documentation** — Check `references/api-reference.md` for correct API/parameters
4. **Apply specific fix** — Based on error category (see below)
5. **Retry with correction** — Never retry blindly without fixing the root cause

**Prohibited actions**:
- ❌ Switching to alternative APIs without understanding why the original failed
- ❌ Giving up or downgrading user's goal without exhausting recovery options
- ❌ Retrying the same failed command without modification

### Common Error Categories and Solutions

#### Category 1: Parameter Errors

**Symptoms**: `InvalidParameter`, `MissingParameter`, `Parameter not valid`

**Root causes**:
- Wrong parameter name (e.g., `--EmrVersion` instead of `--ReleaseVersion`)
- Wrong parameter format (JSON vs flat format)
- Missing required parameters
- Invalid parameter value

**Recovery steps**:
1. Check exact parameter name in `references/api-reference.md`
2. Verify parameter format matches API requirements (RunCluster uses JSON, others use flat)
3. Confirm all required parameters are present
4. Validate parameter values against API constraints

**Common parameter name mistakes**:
| API | Wrong | Correct | Notes |
|-----|-------|---------|-------|
| RunCluster/CreateCluster | `--EmrVersion` | `--ReleaseVersion` | Version format: "EMR-X.Y.Z" |
| RunCluster/CreateCluster | `--DeploymentMode` | `--DeployMode` | Values: NORMAL or HA |
| RunCluster/CreateCluster | `--InstanceType` | `--InstanceTypes` | Array format in NodeGroups |
| All APIs | `--VpcId` (top-level) | `--NodeAttributes.VpcId` | VPC goes in NodeAttributes |

#### Category 2: API Name Errors

**Symptoms**: CLI exits with code 2 or 3, "command not found", "API does not exist"

**Root causes**:
- Incorrect API name spelling
- Using deprecated API name
- API not available in current region

**Recovery steps**:
1. Verify API name in `references/api-reference.md`
2. Check API availability with `aliyun emr help`
3. Ensure region supports the API

**Common API name mistakes**:
| Wrong API | Correct API | Purpose |
|-----------|-------------|---------|
| `ListClusterVersions` | `ListReleaseVersions` | Query available EMR versions |
| `GetInstanceTypes` | `ListInstanceTypes` | Query available instance types |
| `DescribeClusters` | `ListClusters` | List clusters |

#### Category 3: Missing Required Parameters

**Symptoms**: `MissingParameter`, `MissingZoneId`, `MissingSecurityGroupId`

**Common APIs with hidden required parameters**:

**ListInstanceTypes** requires:
```bash
aliyun emr ListInstanceTypes --RegionId <region> \
  --ZoneId <zone> \              # ← Required: Get from DescribeVSwitches
  --ClusterType <type> \         # ← Required: DATALAKE/OLAP/DATAFLOW/etc.
  --PaymentType <payment> \      # ← Required: PayAsYouGo/Subscription
  --NodeGroupType <role>         # ← Required: MASTER/CORE/TASK
```

**RunCluster/CreateCluster** requires in NodeAttributes:
```bash
--NodeAttributes '{"VpcId":"...","ZoneId":"...","SecurityGroupId":"..."}'
# All three are required even if marked optional in API docs
```

#### Category 4: Resource Constraints

**Symptoms**: `QuotaExceeded`, `ResourceNotEnough`, `InvalidResourceType.NotSupported`

**Root causes**:
- Instance type not available in zone
- Account quota exceeded
- Resource type not supported by EMR

**Recovery steps**:
1. Call `ListInstanceTypes` with correct parameters to see available types
2. Try different availability zone (use different VSwitch)
3. Check account quotas in console
4. Try alternative instance type families

#### Category 5: State Conflicts

**Symptoms**: `OperationDenied.ClusterStatus`, `ConcurrentModification`

**Root causes**:
- Cluster/node group in transition state (STARTING/TERMINATING/INCREASING)
- Another operation in progress

**Recovery steps**:
1. Call `GetCluster` or `GetNodeGroup` to check current state
2. Wait for state to stabilize (RUNNING for clusters, RUNNING for node groups)
3. Poll every 30 seconds, timeout after 15 minutes
4. Retry operation after state stabilizes

### Error Recovery Decision Tree

```
Error encountered
    ├─ Parameter error?
    │   ├─ Wrong name → Check api-reference.md, use correct name
    │   ├─ Wrong format → Switch JSON ↔ flat format based on API
    │   └─ Missing → Add required parameter (check hidden requirements)
    │
    ├─ API name error?
    │   └─ Verify correct API name in api-reference.md
    │
    ├─ Resource constraint?
    │   ├─ Zone issue → Try different zone (different VSwitch)
    │   ├─ Quota issue → Check quotas, try smaller instance type
    │   └─ Type not supported → Call ListInstanceTypes for valid types
    │
    └─ State conflict?
        └─ Wait for state transition, then retry
```

**Golden rule**: When in doubt, consult `references/api-reference.md` for the exact API specification.