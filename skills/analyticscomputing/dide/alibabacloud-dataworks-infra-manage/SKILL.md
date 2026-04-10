---
name: alibabacloud-dataworks-infra-manage
description: |
  DataWorks Infrastructure Management: Create and query operations for Data Sources (50 types), Compute Resources, and Serverless Resource Groups, plus connectivity testing and resource group binding/unbinding.
  Uses aliyun CLI to call dataworks-public OpenAPI (2024-05-18).
  Trigger keywords: DataWorks data source, compute resource, resource group, datasource, data source, compute resource, resource group,
  mysql/hologres/maxcompute data source, holo/mc/flink resource, Serverless resource group, DataWorks infra, create/list datasource,
  DW environment config, infrastructure initialization, connect database to DataWorks, database connection failure, configure holo/mc resource.
  Not triggered: data development tasks, scheduling configuration, MaxCompute table management, data integration tasks, ECS/RDS/OSS operations, workspace member management, data quality monitoring, data lineage, data preview.
---

# DataWorks Infrastructure Management

Unified management of **Data Sources**, **Compute Resources**, and **Resource Groups** in Alibaba Cloud DataWorks workspaces, supporting create and query operations.

## Architecture

```
DataWorks
├── Workspaces ─── Query and search workspaces
│   ├── Data Sources ─── 50 types: MySQL, Hologres, MaxCompute, ...
│   └── Compute Resources ─── Hologres, MaxCompute, Flink, Spark
└── Resource Groups ─── Serverless resource group management (cross-workspace)

Dependencies:
  Workspace ◀── Data Sources, Compute Resources (must belong to a workspace)
  Workspace ◀── Resource Groups (associated via binding; one resource group can bind to multiple workspaces)
  Connectivity Test ──depends on──▶ Resource Group (must be bound to the workspace of the data source)
  Standard Mode ──requires──▶ Dev (Development) + Prod (Production) dual data sources and compute resources
```

---

## Global Rules

### Prerequisites

1. **Aliyun CLI >= 3.3.1**: `aliyun version` (Installation guide: [references/cli-installation-guide.md](references/cli-installation-guide.md))
2. **First-time use**: `aliyun configure set --auto-plugin-install true`
3. **jq** (required for resource group operations): `which jq`
4. **Credential status**: `aliyun configure list`, verify valid credentials exist
5. **DataWorks edition**: Basic edition or above required

> **Security Rules**: **DO NOT** read/print/echo AK/SK values, **DO NOT** let users input AK/SK directly, **ONLY** use `aliyun configure list` to check credential status.

### Command Formatting

- **User-Agent (mandatory)**: All `aliyun` CLI commands **must** include the `--user-agent AlibabaCloud-Agent-Skills` parameter to identify the source.
- **Single-line commands**: When executing Bash commands, **must** construct as a **single-line string**; do not use `\` for line breaks.
- **jq step-by-step execution**: First execute the `aliyun` command to get JSON, then format with `jq` (to avoid multi-line security prompts).
- **Endpoint mandatory**: When specifying the `--region` parameter, you **must** also add `--endpoint dataworks.<REGION_ID>.aliyuncs.com`. Not needed when `--region` is not specified.

### Parameter Confirmation

> Before executing any command, all user-customizable parameters **must** be confirmed by the user. Do not assume or use default values.
> **Exception**: When the user has **explicitly specified** parameter values in the conversation, use them directly without re-confirmation.

**Resource group related parameters (mandatory user selection)**: VPC, VSwitch, Resource Group ID (for binding/connectivity testing) — involve networking and billing, **DO NOT auto-select**; must display a list for the user to explicitly choose. Confirm even if there is only one option.

### ⚠️ Write API Execution Gate — MUST Check Before Every Write Operation

> **MANDATORY**: Before calling **any** Write API (Create / Update / Delete / Bind / Unbind / Associate / Dissociate / Test), you **MUST** perform the following checks in order:
>
> 1. **Scan the entire SKILL.md** for a Security Restriction or Disabled Operations notice that mentions the target API or module.
> 2. **If a restriction exists**: **BLOCK the operation immediately**. Do NOT call the API. Respond to the user with:
>    - What operation is blocked and why
>    - The recommended alternative (e.g., use the DataWorks console, contact administrator)
> 3. **If no restriction exists**: Proceed normally with parameter confirmation and execution.
>
> **This check is NOT optional.** It applies to every single write operation without exception. Never skip this step.
>
> **Quick Reference — Blocked APIs in this skill**:
> | Module | Blocked APIs | Reason |
> |--------|-------------|--------|
> | Data Sources (Module 1) | `UpdateDataSource`, `DeleteDataSource` | Prevent accidental data loss, credential exposure, disruption of running tasks |
> | Compute Resources (Module 2) | `UpdateComputeResource`, `DeleteComputeResource` | Prevent disruption of running development and scheduling tasks |
>
> **Allowed Write APIs**: `CreateDataSource`, `CreateComputeResource`, `CreateResourceGroup`, `AssociateProjectToResourceGroup`, `DissociateProjectFromResourceGroup`, `TestDataSourceConnectivity`

### RAM Permissions

All operations require `dataworks:<APIAction>` permissions. Creating resource groups additionally requires `AliyunBSSOrderAccess` and `vpc:DescribeVpcs`, `vpc:DescribeVSwitches`.
> Full permission matrix: [references/ram-policies.md](references/ram-policies.md)

---

## Quick Start: New Workspace Infrastructure Initialization

When the user is **unsure about specific operations** or has vague requirements, guide them through the following process:

1. **Environment check** — Check CLI and credentials per Prerequisites
2. **Confirm workspace** — Use `ListProjects` to locate the workspace, `GetProject` to confirm the mode (Simple/Standard)
3. **Create compute resources** — Guide engine type selection; the system will **automatically create corresponding data sources**. Standard Mode requires Dev+Prod pairs. Only pure storage-type data sources (MySQL, Kafka, etc.) need separate data source creation
4. **Create/bind resource groups** — Query existing resource groups → let user select → bind. Guide creation when no resource groups are available
5. **Test connectivity** — Test with bound resource groups; when all pass, inform "Infrastructure configuration complete"

> After each step, proactively suggest the next action.

---

## Next Step Guidance

After each write operation is completed and verified, **proactively suggest** follow-up actions:

| Completed Operation | Recommended Next Step |
|-----------|-----------|
| Create compute resource | Standard Mode: "Create the corresponding Dev resource?"; "Test connectivity?" |
| Create data source separately | "Test connectivity?"; Standard Mode: "Create Dev/Prod environment data sources?" |
| Create resource group | "Bind to a workspace?" |
| Bind resource group | "Test data source connectivity?" |
| Connectivity test passed | "Infrastructure is ready." |
| Connectivity test failed | Analyze the error cause, guide the fix |
| Unbind resource group | "Bind to another workspace?" |

---

## Trigger Rules

**Trigger scenarios**: Data source create/query, compute resource create/query, resource group management, infrastructure initialization, colloquial aliases (DW database connection failure, configure holo/mc resources, create rg)

**Not triggered**: Data development tasks, scheduling configuration, MaxCompute table management, data integration tasks, ECS/RDS/OSS, workspace member management, data quality/lineage/preview. Standalone workspace queries are handled by the `alibabacloud-dataworks-workspace-manage` skill.

## Interaction Flow

All operations follow: **Identify module → Environment check → Collect parameters → Execute command → Verify result → Guide next step**

Common aliases: DW=DataWorks, holo=Hologres, mc/MC/odps=MaxCompute, pg=PostgreSQL, rg=Resource Group, ds=Data Source, RDS=InstanceMode MySQL/PG/SQLServer, ADB=AnalyticDB

Naming suggestions: Data source `{type}_{business}_{purpose}`, Compute resource `{type}_{business}`, Resource group `dw_{purpose}_rg_{env}`

---

# Module 0: Workspace Query

> If the `alibabacloud-dataworks-workspace-manage` skill is available, prefer using it for workspace queries. The following is only a fallback.

```bash
aliyun dataworks-public ListProjects --user-agent AlibabaCloud-Agent-Skills --Status Available --PageSize 100
```

When searching by name, first get the full list then filter `.PagingInfo.Projects[]` by Name/DisplayName using `jq`.

---

# Module 1: Data Source Management

Supports **50** data source types. See [references/data-sources/README.md](references/data-sources/README.md) for details.

> **When do you need to create a data source separately?** Creating a compute resource (Module 2) will **automatically create the corresponding data source**. Only pure storage-type databases (MySQL, PostgreSQL, Kafka, MongoDB, etc.) need separate creation.

> **Note**: The following types do not currently support OpenAPI: `hdfs`

Connection modes: **UrlMode** (self-hosted databases, requires host/port) or **InstanceMode** (Alibaba Cloud managed instances, requires instanceId). When unsure, proactively ask the user. InstanceMode is preferred.

> Instance query APIs: [references/data-sources/instance-apis.md](references/data-sources/instance-apis.md)

## ⚠️ Security Restriction — See Write API Execution Gate (Global Rules) for mandatory pre-check

> **IMPORTANT**: The `DeleteDataSource` and `UpdateDataSource` APIs are supported by the DataWorks service, but this skill has **disabled** modifying or deleting data sources for security reasons. **Before attempting any write operation, the agent MUST check the Write API Execution Gate section.**
> If you need to modify or delete a data source, please use the DataWorks console directly or contact your administrator.

### Connection Mode Quick Reference

`ConnectionPropertiesMode` selection determines required fields. InstanceMode is preferred when both are available.

| Mode | Types | Count |
|------|-------|-------|
| **Both** | mysql, postgresql, sqlserver, polardb, polardbo, polardb-x-2-0, apsaradb_for_oceanbase, drds, starrocks, analyticdb_for_mysql, analyticdb_for_postgresql, milvus, mongodb, redis, elasticsearch, kafka | 16 |
| **InstanceMode only** | hologres, dlf, opensearch | 3 |
| **UrlMode only** | oracle, mariadb, dm, db2, tidb, vertica, gbase8a, kingbasees, saphana, snowflake, maxcompute, hive, clickhouse, doris, selectdb, redshift, hbase, lindorm, oss, s3, ftp, ssh, tablestore, memcache, graph_database, datahub, loghub, restapi, salesforce, httpfile, bigquery | 31 |

> `hdfs` — not supported via OpenAPI.
> Full details: [references/data-sources/README.md](references/data-sources/README.md)

### Workspace Mode

> **Environment note**: **Prod (Production)** is for production data processing; **Dev (Development)** is for development and debugging, physically isolated from production.

`aliyun dataworks-public GetProject --user-agent AlibabaCloud-Agent-Skills --Id <PROJECT_ID>` — check `DevEnvironmentEnabled`:
- `false` → Simple Mode (1 data source, envType=Prod)
- `true` → Standard Mode (2 data sources, Dev + Prod, physically isolated)

> Full mode comparison: [references/data-sources/README.md](references/data-sources/README.md)

## Task 1.1: Create Data Source (CreateDataSource)

```bash
aliyun dataworks-public CreateDataSource --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --ProjectId <PROJECT_ID> --Name <NAME> --Type <TYPE> --ConnectionPropertiesMode <UrlMode|InstanceMode> --ConnectionProperties '<JSON>' --Description "<DESC>"
```

**ConnectionProperties common structure**:
- **UrlMode**: `{"envType":"Prod","address":[{"host":"<IP>","port":<PORT>}],"database":"<DB>","username":"<USER>","password":"<PWD>"}`
- **InstanceMode**: `{"envType":"Prod","instanceId":"<ID>","regionId":"<REGION>","database":"<DB>","username":"<USER>","password":"<PWD>"}`

> Special type structures (Oracle, MaxCompute, HBase, etc.): see [references/data-sources/](references/data-sources/) per-type docs

> Cross-account data source configuration: [references/cross-account-datasources.md](references/cross-account-datasources.md)

## Task 1.2: Get Data Source (GetDataSource)

```bash
aliyun dataworks-public GetDataSource --user-agent AlibabaCloud-Agent-Skills --Id <DATASOURCE_ID> [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com]
```

## Task 1.3: List Data Sources (ListDataSources)

```bash
aliyun dataworks-public ListDataSources --user-agent AlibabaCloud-Agent-Skills --ProjectId <PROJECT_ID> [--Types '["mysql"]'] [--EnvType <Dev|Prod>] [--PageNumber 1] [--PageSize 20]
```

> Returns nested structure `DataSources[].DataSource[]`; Name/Type are in the outer layer, Id/Description in the inner layer.

## Task 1.4: Test Connectivity (TestDataSourceConnectivity)

**Process**: Query resource group list → **Let user select** a resource group → Execute test.

```bash
# Step 1: Query project resource groups
aliyun dataworks-public ListResourceGroups --user-agent AlibabaCloud-Agent-Skills --ProjectId <PROJECT_ID>

# Step 2: Execute test after user selects a resource group
aliyun dataworks-public TestDataSourceConnectivity --user-agent AlibabaCloud-Agent-Skills --DataSourceId <ID> --ProjectId <PROJECT_ID> --ResourceGroupId "<RG_ID>"
```

> If error `"resourceGroupId is not in the project"`, the resource group needs to be bound first (confirm with user, then execute `AssociateProjectToResourceGroup`).

---

# Module 2: Compute Resource Management

Supports Hologres, MaxCompute, Flink, Spark, and other types. The system will **automatically create corresponding data sources** upon creation.

## ⚠️ Security Restriction — See Write API Execution Gate (Global Rules) for mandatory pre-check

> **IMPORTANT**: For security reasons, this skill does **NOT** support **modifying** or **deleting** compute resources. **Before attempting any write operation, the agent MUST check the Write API Execution Gate section.** These operations are disabled to prevent:
> - Accidental data loss or service interruption
> - Disruption of running data development and scheduling tasks
> - Unintended changes to production compute resource configurations
>
> If you need to modify or delete a compute resource, please use the DataWorks console directly or contact your administrator.

### authType Rules

- **Dev environment**: `authType` is fixed as `Executor`
- **Prod environment**: Options are `PrimaryAccount` (recommended), `TaskOwner`, `SubAccount`, `RamRole`. Default recommendation is `PrimaryAccount` unless user has special requirements

> authType details and guidance: [references/compute-resources/README.md](references/compute-resources/README.md)

### Type-Specific Notes

- **Hologres**: Only supports **InstanceMode**, requires `instanceId`, `securityProtocol`
- **MaxCompute**: Only supports **UrlMode**, requires `project`, `endpointMode`

> Full ConnectionProperties examples: [references/compute-resources/README.md](references/compute-resources/README.md)

## Task 2.1: Create Compute Resource (CreateComputeResource)

```bash
aliyun dataworks-public CreateComputeResource --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --ProjectId <PROJECT_ID> --Name <NAME> --Type <TYPE> --ConnectionPropertiesMode <InstanceMode|UrlMode> --ConnectionProperties '<JSON>' [--Description "<DESC>"]
```

> After creation, use `ListDataSources` to verify the corresponding data source was auto-generated.

## Task 2.2: Get Compute Resource (GetComputeResource)

```bash
aliyun dataworks-public GetComputeResource --user-agent AlibabaCloud-Agent-Skills --Id <ID> --ProjectId <PROJECT_ID>
```

## Task 2.3: List Compute Resources (ListComputeResources)

```bash
aliyun dataworks-public ListComputeResources --user-agent AlibabaCloud-Agent-Skills --ProjectId <PROJECT_ID> [--Name <FILTER>] [--EnvType <Dev|Prod>] [--PageSize 20] [--SortBy CreateTime] [--Order Desc]
```

> Returns nested structure `ComputeResources[].ComputeResource[]`; Name/Type are in the outer layer, Id in the inner layer.

---

# Module 3: Resource Group Management

Manages the full lifecycle of Serverless resource groups.

## Task 3.1: Create Resource Group (CreateResourceGroup)

> Requires `AliyunBSSOrderAccess` permission.

**Interaction flow** (let user choose at each step, DO NOT auto-select):

1. **Query and select VPC**:
```bash
aliyun vpc DescribeVpcs --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION_ID>" --PageSize 50
```
If the list is empty, guide the user to create a VPC; **DO NOT** auto-create.

2. **Query and select VSwitch**:
```bash
aliyun vpc DescribeVSwitches --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION_ID>" --VpcId "<VPC_ID>" --PageSize 50
```

3. **Confirm name and specification** → Execute creation:
```bash
aliyun dataworks-public CreateResourceGroup --user-agent AlibabaCloud-Agent-Skills [--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com] --Name "<NAME>" --PaymentType PostPaid --VpcId "<VPC_ID>" --VswitchId "<VSWITCH_ID>" --ClientToken "$(uuidgen 2>/dev/null || echo "token-$(date +%s)")" --Remark "Created by Agent"
```

After creation, poll `GetResourceGroup` until status becomes `Normal` (every 10 seconds, up to 10 minutes).

## Task 3.2: Get Resource Group (GetResourceGroup)

```bash
aliyun dataworks-public GetResourceGroup --user-agent AlibabaCloud-Agent-Skills --Id "<ID>"
```

## Task 3.3: List Resource Groups (ListResourceGroups)

```bash
aliyun dataworks-public ListResourceGroups --user-agent AlibabaCloud-Agent-Skills [--ProjectId <PROJECT_ID>] [--Statuses '["Normal"]'] --PageSize 100
```

## Task 3.4: Bind Resource Group (AssociateProjectToResourceGroup)

**Process**: Query available resource groups → **Display list for user to select** → Bind after user confirms.

```bash
aliyun dataworks-public AssociateProjectToResourceGroup --user-agent AlibabaCloud-Agent-Skills --ResourceGroupId "<RG_ID>" --ProjectId "<PROJECT_ID>"
```

## Task 3.5: Query Binding Relationships

```bash
aliyun dataworks-public ListResourceGroupAssociateProjects --user-agent AlibabaCloud-Agent-Skills --ResourceGroupId "<RG_ID>"
```

## Task 3.6: Unbind Resource Group (DissociateProjectFromResourceGroup)

```bash
aliyun dataworks-public DissociateProjectFromResourceGroup --user-agent AlibabaCloud-Agent-Skills --ResourceGroupId "<RG_ID>" --ProjectId "<PROJECT_ID>"
```

---

## Success Verification

After all write operations, use the corresponding Get/List command to verify the result.

## Common Errors

| Error Code | Solution |
|--------|----------|
| Forbidden.Access / PermissionDenied | Check RAM permissions, see [references/ram-policies.md](references/ram-policies.md) |
| InvalidParameter | Check ConnectionProperties JSON and required parameters |
| EntityNotExists | Verify the ID and Region are correct |
| QuotaExceeded | Delete unused resources or request a quota increase |
| Duplicate* | Use a different name |

## Region

Common: `cn-hangzhou`, `cn-shanghai`, `cn-beijing`, `cn-shenzhen`. Endpoint: `dataworks.<region-id>.aliyuncs.com`
> Full list: [references/related-apis.md](references/related-apis.md)

## Best Practices

1. **Query before action** — Confirm current state before create operations
2. **Manage by environment** — Manage Dev and Prod resources separately
3. **Verify operations** — Use Get/List to verify after each write operation
4. **Proactive guidance** — Suggest the next step after each step completes
5. **Protect data sources and compute resources** — Never modify or delete data sources or compute resources via this skill; use the DataWorks console for such operations

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/data-sources/README.md](references/data-sources/README.md) | Data source type list and ConnectionProperties examples |
| [references/data-sources/](references/data-sources/) | Detailed configuration docs for each data source type (50 files) |
| [references/cross-account-datasources.md](references/cross-account-datasources.md) | Cross-account data source configuration guide |
| [references/compute-resources/README.md](references/compute-resources/README.md) | Compute resource ConnectionProperties examples |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission configuration and policy examples |
| [references/related-apis.md](references/related-apis.md) | API parameter details and Region Endpoints |
