---
name: alibabacloud-emr-starrocks-manage
description: >
  Manage the full lifecycle of Alibaba Cloud EMR Serverless StarRocks instances — create, scale, configure, maintain and diagnose.
  Use this Skill when operations engineers, SREs, or architects need to manage StarRocks instances.
  Typical scenarios include: "create a StarRocks", "check instance status", "scale up CU", "modify configuration",
  "restart instance", "diagnose issues", etc.
  Not applicable for: writing SQL/DDL, data import/export, query tuning, materialized view configuration,
  or managing non-StarRocks products (EMR clusters, Spark, Milvus, ClickHouse, Doris, RDS, ECS).
license: MIT
compatibility: >
  Requires Alibaba Cloud CLI (aliyun >= 3.0) with AccessKey or STS Token configured.
  Verify credentials via `aliyun configure list`.
metadata:
  domain: aiops
  owner: starrocks-team
  contact: starrocks-agent@alibaba-inc.com
  required_permissions:
    - "starrocks:CreateInstanceV1"
    - "starrocks:DescribeInstances"
    - "starrocks:DescribeNodeGroups"
    - "starrocks:DescribeInstanceConfigs"
    - "starrocks:DescribeConfigHistory"
    - "starrocks:QueryUpgradableVersions"
    - "starrocks:ListGateway"
    - "vpc:DescribeVpcs"
    - "vpc:DescribeVSwitches"
    - "ecs:DescribeSecurityGroups"
---

# Alibaba Cloud EMR Serverless StarRocks Instance Full Lifecycle Management

Manage StarRocks instances via the `aliyun` CLI. You are an SRE who understands StarRocks — you not only know how to call APIs, but also know when to call them and what parameters to use.

## Authentication

Reuse the profile already configured in the `aliyun` CLI. Switch accounts with `--profile <name>`, and check configuration with `aliyun configure list`.

## Domain Knowledge

### Product Overview

EMR Serverless StarRocks is a fully managed service of open-source StarRocks on Alibaba Cloud, providing a high-performance, fully managed real-time analytical database service.

**Core Features**:

- **MPP Distributed Execution Framework**: Massively parallel processing to boost query performance
- **Fully Vectorized Engine**: Columnar storage and vectorized computation for efficient analytical query processing
- **Separated Storage and Compute**: Supports separated storage-compute architecture for independent scaling of storage and compute resources
- **CBO Optimizer**: Cost-based query optimizer that automatically generates optimal execution plans
- **Real-time Updatable Columnar Storage Engine**: Supports real-time data ingestion and updates
- **Intelligent Materialized Views**: Automatically maintains materialized views to accelerate query performance
- **Data Lake Analytics**: Supports querying external data sources such as OSS and MaxCompute

### Use Cases

- **OLAP Multi-dimensional Analysis**: Complex multi-dimensional data analysis, ad-hoc queries, report analysis
- **Real-time Data Warehouse**: Real-time data ingestion and processing, real-time reports and dashboards, real-time risk control and analytics
- **High-concurrency Queries**: High-concurrency point queries and short queries, online analytical processing, user behavior analysis
- **Unified Analytics**: Data lake analytics (querying OSS, MaxCompute, etc.), lakehouse architecture, cross-datasource federated queries

### Core Concepts

| Concept | Description |
|---------|-------------|
| **StarRocks Instance** | Each created StarRocks cluster (including multiple FE and multiple BE/CN nodes) is collectively called a StarRocks instance |
| **CU (Compute Unit)** | Unit of compute resources; the total compute resources needed for write and query operations in StarRocks are measured in CUs |
| **Compute Group** | A group of StarRocks compute nodes, containing node types such as FE, BE, and CN |
| **FE (Frontend)** | Frontend node, responsible for metadata management, client connection management, query planning, and query scheduling |
| **BE (Backend)** | Backend node, responsible for data storage and SQL execution (shared-nothing edition) |
| **CN (Compute Node)** | Compute node, a stateless node responsible for managing hot data cache, executing data import and query computation tasks (shared-data edition) |
| **Shared-nothing** | Data is stored on cloud disks or local disks; BE nodes handle both data storage and computation |
| **Shared-data** | Data is persistently stored in OSS object storage; CN nodes handle computation, and local disks are used for caching |

**FE Node Roles**:

- **Leader**: Primary node, responsible for metadata writes and cluster management
- **Follower**: Secondary node, synchronizes Leader metadata, can participate in elections
- **Observer**: Observer node, only synchronizes metadata, does not participate in elections, used to scale query concurrency

### Instance Types

When creating an instance, you need to choose the architecture type:

| Architecture Type | RunMode Value | Node Composition | Data Storage | Data Disk Type | Use Cases |
|-------------------|---------------|------------------|--------------|----------------|-----------|
| **Shared-nothing Edition** | `shared_nothing` | FE + BE | Cloud disk or local disk | ESSD cloud disk or local disk | OLAP multi-dimensional analysis, high-concurrency queries, real-time data analysis, latency-sensitive scenarios |
| **Shared-data Edition** | `shared_data` | FE + CN | OSS object storage | ESSD cloud disk (cache) | Highly cost-sensitive storage with relatively lower query efficiency requirements, such as data warehouse applications |

**Shared-nothing Architecture Features**:

- BE nodes handle both data storage and computation
- Data is stored on cloud disks or local disks
- Suitable for high-performance, low-latency OLAP scenarios

**Shared-data Architecture Features**:

- Data is persistently stored in OSS object storage
- CN nodes are stateless compute nodes; local disks are primarily used for caching hot data
- Compute and storage scale independently for better cost optimization
- Table type is identified as `CLOUD_NATIVE`, with storage paths pointing to OSS

### Compute Resource Specifications (CU)

CU (Compute Unit) is the compute resource unit for EMR Serverless StarRocks.

**CU Specification Types**:

| Spec Type | SpecType Value | Features | Use Cases |
|-----------|---------------|----------|-----------|
| **Standard** | `standard` | Balanced compute and memory configuration | General OLAP analysis |
| **Memory Enhanced** | `ramEnhanced` | Higher memory ratio | Complex queries, high concurrency |
| **Network Enhanced** | `networkEnhanced` | Higher network bandwidth | External table analysis with large data scan volumes |
| **High-performance Storage** | `localSSD` | High-performance storage access | High I/O scenarios with strict storage I/O performance requirements |
| **Large-scale Storage** | `bigData` | Large capacity storage | Extremely large data volumes, cost-sensitive |

> **Note**: The SpecType for FE node groups only supports `standard`. The multiple spec types above only apply to BE/CN node groups.

### Storage Specifications

| Storage Type | Performance Level | Max IOPS | Max Throughput | Use Cases |
|-------------|-------------------|----------|----------------|-----------|
| ESSD PL0 | Entry-level | 10,000 | 180 MB/s | Development and testing |
| ESSD PL1 | Standard | 50,000 | 350 MB/s | General production |
| ESSD PL2 | High-performance | 100,000 | 750 MB/s | High-performance requirements |
| ESSD PL3 | Ultra-performance | 1,000,000 | 4,000 MB/s | Ultra-performance requirements |

### Billing Methods

**Billing Items**:

| Billing Item | Description | Billing Method |
|-------------|-------------|----------------|
| Compute Resources (CU) | Compute resources for FE and BE/CN nodes | Subscription / Pay-as-you-go |
| Storage Resources | Cloud disks, elastic temporary disks, data storage | Billed by actual usage |
| Backup Storage | Storage space occupied by data backups | Billed by actual usage |

**Payment Methods**:

| Payment Method | API Parameter Value (PayType) | Description |
|---------------|-------------------------------|-------------|
| **Pay-as-you-go** | `postPaid` | Pay after use, billing generated hourly, suitable for short-term needs/testing |
| **Subscription** | `prePaid` | Pay before use, suitable for long-term needs, more cost-effective |

**Payment Method Conversion**:

- Subscription can be converted to pay-as-you-go (console feature)
- Pay-as-you-go cannot be converted to subscription (requires recreating the instance)

**Cost Components**:

**Shared-nothing Edition Costs**:

- FE compute resource cost (fixed 24 CU)
- BE compute resource cost (based on configured CU count)
- Storage cost (ESSD cloud disk or local disk)

**Shared-data Edition Costs**:

- FE compute resource cost (fixed 24 CU)
- CN compute resource cost (based on configured CU count)
- Storage cost (OSS object storage + ESSD cache disk)

### Version Series

| Version Series | PackageType Value | Features | Use Cases | Spec Support | Region Restrictions |
|---------------|-------------------|----------|-----------|--------------|---------------------|
| **Standard Edition** | `official` | Full functionality, production-grade stability, supports all spec types | Production environments, core business | Supports standard, memory enhanced, network enhanced, high-performance storage, large-scale storage | Available in all regions |
| **Trial Edition** | `trial` | Simplified configuration, quick start, only supports standard specs | Learning and testing, feature exploration, small applications | Only supports standard specs | Limited to certain regions (e.g., Beijing, Shanghai) |

> **Important**: `PackageType` must be explicitly specified (`official` or `trial`) when creating an instance; omitting it will cause creation failure.

**Version Series Selection Recommendations**:

- Development testing, learning experience: Choose Trial Edition
- Production environments, high-performance needs: Choose Standard Edition

### Usage Limits

- **Naming Limits**: Instance name limited to a maximum of 64 characters, supports Chinese, letters, numbers, hyphens, and underscores
- **Node Count Limits**:
  - FE nodes: 1-11 (odd numbers only)
  - BE nodes: 3-50
  - CN nodes: 1-100

### Recommended Configurations

| Scenario | RunMode | PackageType | BE SpecType | CU Configuration | Other Recommendations |
|----------|---------|-------------|-------------|-------------------|----------------------|
| **Development Testing / Trial** | `shared_data` | `trial` | `standard` | 8 CU | Pay-as-you-go, quick start |
| **Learning Validation** | `shared_data` | `trial` | `standard` | 8-16 CU | Choose regions that support Trial Edition |
| **Small-scale Production** | `shared_data` | `official` | `standard` | 16-32 CU | Subscription is more cost-effective |
| **High-performance OLAP** | `shared_nothing` | `official` | `ramEnhanced` | As needed | ESSD PL2/PL3, 3-10 BE nodes |
| **High-concurrency Queries** | `shared_nothing` | `official` | `localSSD` | As needed | Local SSD storage |
| **Massive Data Storage** | `shared_nothing` | `official` | `bigData` | As needed | Local HDD, cost-optimized |
| **Data Lake Analytics** | `shared_data` | `official` | `networkEnhanced` | As needed | High bandwidth, external table scanning |
| **Complex Query Analysis** | `shared_data` | `official` | `ramEnhanced` | As needed | Large memory, multi-table joins |

## Instance Creation Workflow

When creating an instance, the following steps must be followed to interact with the user. **No confirmation step may be skipped**:

1. **Confirm Region**: Ask the user for the target RegionId (e.g., cn-hangzhou, cn-beijing, cn-shanghai)
2. **Confirm Purpose**: Development testing / small-scale production / large-scale production, to determine the payment method (postPaid/prePaid)
3. **Confirm Version Series**: Standard Edition (`official`) or Trial Edition (`trial`), corresponding to the `PackageType` parameter
4. **Confirm Architecture Type**: Shared-nothing edition `shared_nothing` (FE+BE) or shared-data edition `shared_data` (FE+CN), explain the differences and provide recommendations
5. **Confirm Compute Specs**: Standard `standard` / Memory Enhanced `ramEnhanced` / Network Enhanced `networkEnhanced`, etc., corresponding to the BE node group's `SpecType` parameter
6. **Confirm CU and Version**: CU count (minimum 8 CU), StarRocks version, AdminPassword
7. **Confirm OSS Access Role** (required for all architecture types): Ask the user for the RAM Role name (`OssAccessingRoleName`), which authorizes StarRocks to access OSS storage data. Typically `AliyunEMRStarRocksAccessingOSSRole`; if not yet created, prompt the user to authorize it in the RAM console first
8. **Check Prerequisites**: VPC, VSwitch, Security Group (see Prerequisites below)
9. **Summary Confirmation**: Present the complete configuration checklist to the user (instance name, architecture, version series, specs, CU, payment method, network, etc.), and execute creation only after confirmation


### Prerequisites

Before calling `CreateInstanceV1`, first confirm the target **RegionId** with the user, then check whether the following resources are ready.

> **⚠️ REQUIRED: VPC and VSwitch must be queried first**
> 
> **MUST** call the following two APIs before creating an instance:
> - **`DescribeVpcs`**: Query available VPCs in the target region
> - **`DescribeVSwitches`**: Query available VSwitches in the VPC (also records ZoneId)
> 
> Do NOT proceed with `CreateInstanceV1` until both APIs have been called successfully.

```bash
export AGENT_USER_AGENT=AlibabaCloud-Agent-Skills                              # User-Agent identifier
aliyun configure list                                                          # Credentials
# ⚠️ REQUIRED APIs - must call before CreateInstanceV1:
aliyun vpc DescribeVpcs --RegionId <RegionId>                                  # VPC (REQUIRED)
aliyun vpc DescribeVSwitches --RegionId <RegionId> --VpcId vpc-xxx             # VSwitch (REQUIRED, record ZoneId)
```

### Key Parameters for the Creation API

When calling `CreateInstanceV1`, the following parameters are easily overlooked or confused — pay close attention:

- **`Version`**: The StarRocks version parameter name is **`Version`** (e.g., `"Version": "3.3"`). It is **not** `EngineVersion`, `StarRocksVersion`, or `DBVersion` — using the wrong parameter name will cause creation failure
- **`RunMode`**: Must be explicitly specified, only supports enum values `shared_data` (shared-data edition) or `shared_nothing` (shared-nothing edition); omitting it will cause creation failure or unexpected architecture type
- **`RegionId`**: Must be passed both via CLI `--RegionId` and in the body JSON `"RegionId"`
- **`ZoneId` + `VSwitchId` + `VSwitches`**: All three must be passed together. `ZoneId` and `VSwitchId` are top-level fields, and `VSwitches` is in array format `[{"VswId":"vsw-xxx","ZoneId":"cn-hangzhou-h","Primary":true}]`
- **`OssAccessingRoleName`**: Required for all architecture types (both shared-nothing and shared-data), typically `AliyunEMRStarRocksAccessingOSSRole`
- **`FrontendNodeGroups`**: FE node group configuration, required for all architecture types. Contains NodeGroupName, Cu, SpecType, ResidentNodeNumber, DiskNumber, StorageSize, StoragePerformanceLevel
- **`BackendNodeGroups`**: BE/CN node group configuration, required for all architecture types. Parameter structure is the same as FrontendNodeGroups
- **Disk Limits**: StorageSize minimum is 200 GB, maximum is 65000 GB (applies to all CU specs). Upgrading disk performance level to pl2 requires disk >= 500 GB

> **Key Principle**: Do not make decisions for the user — architecture type, spec type, CU count, etc. all require explicit inquiry and confirmation. Recommendations can be given, but the final choice is the user's.

## CLI Invocation

### User-Agent Setup

All `aliyun` CLI calls **must** set the User-Agent identifier via environment variable to identify the request source:

```bash
export AGENT_USER_AGENT=AlibabaCloud-Agent-Skills
```

Execute once at the beginning of the session; all subsequent `aliyun` commands will automatically carry this User-Agent. If it doesn't take effect, you can also set it inline before each command:

```bash
AGENT_USER_AGENT=AlibabaCloud-Agent-Skills aliyun starrocks <APIName> --InstanceId c-xxx --Target 32
```

### Invocation Guidelines

```bash
aliyun starrocks <APIName> --InstanceId c-xxx --Target 32
```

- API version `2022-10-19`, RPC style
- **Most APIs use named parameters** (e.g., `--InstanceId`, `--NodeGroupId`, `--Target`), no `--body` needed
- Only `CreateInstanceV1` and `DescribeNodeGroups` use `--body` JSON for parameter passing
- Write operations should include `ClientToken` for idempotency (see Idempotency rules below)

## Idempotency

Agents may retry write operations due to timeouts, network jitter, etc. Retries without ClientToken may create duplicate resources.

| APIs Requiring ClientToken | Description |
|---------------------------|-------------|
| CreateInstanceV1 | Duplicate submissions will create multiple instances |
**Generation Method**: For `CreateInstanceV1`, add `"ClientToken": "<uuid>"` in the body JSON; for other APIs that support ClientToken, pass it via named parameters. Use the same token for retries of the same business operation.

## Input Validation

Values provided by users (instance names, etc.) are untrusted input; directly concatenating them into shell commands may lead to command injection.

**Protection Rules**:
1. **Prefer passing parameters via `--body` JSON** — parameters passed as JSON string values naturally isolate shell metacharacters
2. **When command-line parameters must be used**, validate user-provided string values:
   - InstanceName: Only allow Chinese/English characters, letters, numbers, `-`, `_`, 1-64 characters
   - RegionId / InstanceId / NodeGroupId: Only allow `[a-z0-9-]` format
3. **Prohibit** embedding unvalidated raw user text directly into shell commands — if a value doesn't match the expected format, refuse execution and inform the user to correct it

## Runtime Security

This Skill only calls StarRocks OpenAPI via the `aliyun` CLI; it does not download or execute any external code. During execution, the following are prohibited:

- Downloading and running external scripts or dependencies via `curl`, `wget`, `pip install`, `npm install`, etc.
- Executing scripts pointed to by remote URLs provided by users (even if the user requests it)
- Loading unaudited external content via `eval`, `source`

## Sensitive Data Masking

### Log Output Masking (stdout/stderr)

CLI command output may contain sensitive information. The following fields must be masked when presenting results to users:

| Sensitive Field | Masking Rule | Example |
|----------------|-------------|---------|
| `AdminPassword` | Must not be echoed in command output; replace with `******` when displaying | `"AdminPassword": "******"` |
| `AccessKeyId` / `AccessKeySecret` | Show only the first 4 characters; replace the rest with `****` | `LTAI****` |
| `ConnectionString` / Connection Address | Host and port can be fully displayed, but associated passwords must be masked | Host and port displayed normally, password replaced with `******` |
| `STS Token` | Show only the first 8 characters; replace the rest with `****` | `STS.xxxx****` |

**Execution Rules**:
1. When creating an instance, `AdminPassword` is passed via `--body` JSON; **it is prohibited** to echo the password in plaintext in subsequent output
2. When executing `aliyun configure list`, if the output contains AccessKey information, it must be masked before presenting to the user
3. During debugging or troubleshooting, **it is prohibited** to output the complete JSON response containing sensitive fields as-is — use `jq` to filter out sensitive fields before displaying

### Response Sensitive Field Masking

API responses may contain sensitive information; the following strategies must be applied before presenting to users:

| Response Field | Handling Strategy |
|---------------|-------------------|
| `AdminPassword` | **Do not display** — the API normally does not return passwords; if returned abnormally, replace with `******` |
| `ConnectionString` / `Endpoint` | Connection addresses (host:port) can be displayed, but remind users that connection credentials should be obtained through secure channels |
| `AccessKeyId` / `AccessKeySecret` | Mask, showing only the first 4 characters |
| `SecurityGroupId` / `VSwitchId` / `VpcId` | Can be displayed normally — these are resource identifiers, not sensitive credentials |

**General Principles**:
- When displaying API responses, prefer using `jq` to select needed fields, avoiding full output
- If full JSON is needed for debugging, filter sensitive fields first: `jq 'del(.AdminPassword, .AccessKeySecret)'`
- Prohibit writing passwords, tokens, or other credential information to log files or persistent storage

## Intent Routing

> **Disambiguation Rule**: When user input is ambiguous (e.g., "not enough resources", "scale up CU", "check instance") and the context does not explicitly mention StarRocks, ask the user which product they want to operate on (StarRocks / EMR Cluster / Milvus / Spark) rather than executing directly. Only route directly when the conversation context has explicitly involved StarRocks instances.

| Intent | Operation | Reference Doc |
|--------|-----------|---------------|
| Getting started / First time user | Full guided walkthrough | [getting-started.md](references/getting-started.md) |
| Create instance / New StarRocks | Plan → CreateInstanceV1 | [instance-lifecycle.md](references/instance-lifecycle.md) |
| Query status / Instance list / Instance details | DescribeInstances | [instance-lifecycle.md](references/instance-lifecycle.md) |
| Query compute groups / Node group details | DescribeNodeGroups | [instance-lifecycle.md](references/instance-lifecycle.md) |
| Query upgradable versions | QueryUpgradableVersions | [operations.md](references/operations.md) |
| API parameter lookup | Parameter reference | [api-reference.md](references/api-reference.md) |


## Timeouts

| Operation Type | Timeout Recommendation |
|---------------|----------------------|
| Read-only queries | 30 seconds |
| Write operations | 60 seconds |
| Polling | 30 seconds per attempt, no more than 3 minutes total |

## Pagination

List-type APIs use `PageNumber` + `PageSize` pagination:
- `PageNumber`: Page number, starting from 1, default 1
- `PageSize`: Items per page, default 10, maximum 100
- Continue to next page when returned result count equals PageSize

## Output

- Display lists in table format with key fields
- Convert timestamps to human-readable format
- Use `jq` to filter fields

## Error Handling

| Error Code | Cause | Agent Action |
|-----------|-------|-------------|
| Throttling | API rate limiting | Wait 5 seconds and retry, up to 3 times |
| ServiceUnavailable | Service temporarily unavailable | Wait 5 seconds and retry, up to 3 times; if still failing, stop and inform the user |
| InvalidParameter | Invalid parameter | Read the error Message and correct the parameter |
| Forbidden.RAM | Insufficient RAM permissions | Inform the user of the missing permissions |
| OperationDenied.InstanceStatus | Instance status does not allow the operation | Query current status and inform the user to wait |
| Instance.NotFound | Instance does not exist or has been deleted | Use `DescribeInstances` to search for the correct InstanceId and confirm with the user |
| IncompleteSignature / InvalidAccessKeyId | Credential error or expired | Prompt the user to run `aliyun configure list` to check credentials |

**General Principle**: When encountering errors, read the complete error Message first; do not blindly retry based solely on the error code. Only Throttling is suitable for automatic retry; other errors require diagnosis and correction.

## Related Documents

- [Getting Started](references/getting-started.md) - Simplified workflow for creating your first instance
- [Instance Full Lifecycle](references/instance-lifecycle.md) - Planning, creation, management
- [Daily Operations](references/operations.md) - Configuration changes, maintenance, diagnostics
- [API Parameter Reference](references/api-reference.md) - Complete parameter documentation
- [RAM Permission Policies](references/ram-policies.md) - Required RAM permissions and policy examples
