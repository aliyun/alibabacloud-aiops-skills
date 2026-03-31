---
name: alibabacloud-emr-spark-manage
description: >
  Manage the full lifecycle of Alibaba Cloud EMR Serverless Spark workspaces—create workspaces, submit jobs, Kyuubi interactive queries, resource queue scaling, and status queries.
  Use this Skill when users want to create Spark workspaces, submit Spark jobs, view job status and logs, execute SQL via Kyuubi,
  scale resource queues, or view workspace status.
  Also applicable when users say "create a Spark workspace", "submit Spark job", "run PySpark",
  "execute SQL via Kyuubi", "scale resource queue", "view job logs", etc.
license: MIT
compatibility: >
  Requires Alibaba Cloud CLI (aliyun >= 3.0) or Python SDK,
  API version 2023-08-08, ROA style.
  Supports Alibaba Cloud default credential chain, including environment variables, configuration files, instance roles, etc.
metadata:
  domain: aiops
  owner: spark-team
  contact: spark-agent@alibaba-inc.com
  required_roles:
    - role: AliyunServiceRoleForEMRServerlessSpark
      type: service-linked
      description: EMR Serverless Spark service-linked role, used by the service to access other cloud resources
    - role: AliyunEMRSparkJobRunDefaultRole
      type: job-run
      description: Spark job execution role, used to access OSS, DLF and other cloud resources during job execution
  service_linked_role:
    service: spark.emr-serverless.aliyuncs.com
    action: ram:CreateServiceLinkedRole
---

# Alibaba Cloud EMR Serverless Spark Workspace Full Lifecycle Management

Manage EMR Serverless Spark workspaces through Alibaba Cloud API. You are a Spark-savvy data engineer who not only knows how to call APIs, but also knows when to call them and what parameters to use.

## Domain Knowledge

### Product Architecture

EMR Serverless Spark is a fully-managed Serverless Spark service provided by Alibaba Cloud, supporting batch processing, interactive queries, and stream computing:

- **Serverless Architecture**: No need to manage underlying clusters, compute resources allocated on-demand, billed by CU
- **Multi-engine Support**: Supports Spark batch processing, Kyuubi (compatible with Hive/Spark JDBC), session clusters
- **Elastic Scaling**: Resource queues scale on-demand, no need to reserve fixed resources

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Workspace** | Top-level resource container, containing resource queues, jobs, Kyuubi services, etc. |
| **Resource Queue** | Compute resource pool within a workspace, allocated in CU units |
| **CU (Compute Unit)** | Compute resource unit, 1 CU = 1 core CPU + 4 GiB memory |
| **JobRun** | Submission and execution of a Spark job |
| **Kyuubi Service** | Interactive SQL gateway compatible with open-source Kyuubi, supports JDBC connections |
| **SessionCluster** | Long-running interactive session environment |
| **ReleaseVersion** | Available Spark engine versions |

### Job Types

| Type | Description | Applicable Scenarios |
|------|-------------|---------------------|
| **Spark JAR** | Java/Scala packaged JAR jobs | ETL, data processing pipelines |
| **PySpark** | Python Spark jobs | Data science, machine learning |
| **Spark SQL** | Pure SQL jobs | Data analysis, report queries |

### Recommended Configurations

- **Development & Testing**: Pay-as-you-go + 50 CU resource queue
- **Small-scale Production**: 200 CU resource queue
- **Large-scale Production**: 2000+ CU resource queue, elastic scaling on-demand

## Prerequisites

### 1. Credential Configuration

Alibaba Cloud CLI/SDK will automatically obtain authentication information from the default credential chain, no need to explicitly configure credentials. Supports multiple credential sources, including configuration files, environment variables, instance roles, etc.

Recommended to use Alibaba Cloud CLI to configure credentials:

```bash
aliyun configure
```

For more credential configuration methods, refer to [Alibaba Cloud CLI Credential Management](https://help.aliyun.com/document_detail/110341.html).

### 2. Grant Service Roles (Required for First-time Use)

Before using EMR Serverless Spark, you need to grant the account the following two roles (see [RAM Permission Policies](references/ram-policies.md#service-roles) for details):

| Role Name | Type | Description |
|-----------|------|-------------|
| **AliyunServiceRoleForEMRServerlessSpark** | Service-linked role | EMR Serverless Spark service uses this role to access your resources in other cloud products |
| **AliyunEMRSparkJobRunDefaultRole** | Job execution role | Spark jobs use this role to access OSS, DLF and other cloud resources during execution |

> For first-time use, you can authorize through the [EMR Serverless Spark Console](https://emr-serverless-spark.console.aliyun.com) with one click, or manually create in the RAM console.

### 3. RAM Permissions

RAM users need corresponding permissions to operate EMR Serverless Spark. For detailed permission policies, specific Action lists, and authorization commands, refer to [RAM Permission Policies](references/ram-policies.md).

### 4. OSS Storage

Spark jobs typically need OSS storage for JAR packages, Python scripts, and output data:

```bash
# Check for available OSS Buckets
aliyun oss ls --user-agent AlibabaCloud-Agent-Skills
```

## CLI/SDK Invocation

### Invocation Method

All APIs are version `2023-08-08`, request method is ROA style (RESTful).

```bash
# Using Alibaba Cloud CLI (ROA style)
# Important:
#   1. Must add --force --user-agent AlibabaCloud-Agent-Skills parameters, otherwise local metadata validation will report "can not find api by path" error
#   2. Recommend always adding --region parameter to specify region (GET can omit if CLI has default Region configured, but recommend explicit specification; must add if not configured, otherwise server reports MissingParameter.regionId error)
#   3. POST/PUT/DELETE write operations need to append ?regionId=cn-hangzhou at end of URL, --region alone is not enough
#      GET requests only need --region

# POST request (note URL append ?regionId=cn-hangzhou)
aliyun emr-serverless-spark POST "/api/v1/workspaces?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{"workspaceName":"my-workspace","ossBucket":"oss://my-bucket","ramRoleName":"AliyunEMRSparkJobRunDefaultRole","paymentType":"PayAsYouGo","resourceSpec":{"cu":8}}' \
  --force --user-agent AlibabaCloud-Agent-Skills

# GET request (only need --region)
aliyun emr-serverless-spark GET /api/v1/workspaces --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills

# DELETE request (note URL append ?regionId=cn-hangzhou)
aliyun emr-serverless-spark DELETE "/api/v1/workspaces/{workspaceId}/jobRuns/{jobRunId}?regionId=cn-hangzhou" \
  --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### Idempotency Rules

The following operations recommend using idempotency tokens to avoid duplicate submissions:

| API | Description |
|-----|-------------|
| CreateWorkspace | Duplicate submission will create multiple workspaces |
| StartJobRun | Duplicate submission will submit multiple jobs |
| CreateSessionCluster | Duplicate submission will create multiple session clusters |

## Intent Routing

| Intent | Operation | Reference |
|---------|-----------|-----------|
| Beginner / First-time use | Full guide | `getting-started.md` |
| Create workspace / New Spark | Plan → CreateWorkspace | `workspace-lifecycle.md` |
| Delete workspace / Destroy | DeleteWorkspace | `workspace-lifecycle.md` |
| Query workspace / List / Details | ListWorkspaces | `workspace-lifecycle.md` |
| Submit Spark job / Run task | StartJobRun | `job-management.md` |
| Query job status / Job list | GetJobRun / ListJobRuns | `job-management.md` |
| View job logs | ListLogContents | `job-management.md` |
| Cancel job / Stop job | CancelJobRun | `job-management.md` |
| View CU consumption | GetCuHours | `job-management.md` |
| Create Kyuubi service | CreateKyuubiService | `kyuubi-service.md` |
| Start / Stop Kyuubi | Start/StopKyuubiService | `kyuubi-service.md` |
| Execute SQL via Kyuubi | Connect Kyuubi Endpoint | `kyuubi-service.md` |
| Manage Kyuubi Token | Create/List/DeleteKyuubiToken | `kyuubi-service.md` |
| Scale resource queue / Not enough resources | EditWorkspaceQueue | `scaling.md` |
| View resource queue | ListWorkspaceQueues | `scaling.md` |
| Create session cluster | CreateSessionCluster | `job-management.md` |
| Query engine versions | ListReleaseVersions | `api-reference.md` |
| Check API parameters | Parameter reference | `api-reference.md` |

## Destructive Operation Protection

The following operations are irreversible. Before execution, must complete pre-check and confirm with user:

| API | Pre-check Steps | Impact |
|-----|-----------------|--------|
| DeleteWorkspace | 1. ListJobRuns to confirm no running jobs 2. ListSessionClusters to confirm no running sessions 3. ListKyuubiServices to confirm no running Kyuubi 4. User explicit confirmation | Permanently delete workspace and all associated resources |
| CancelJobRun | 1. GetJobRun to confirm job status is Running 2. User explicit confirmation | Abort running job, compute results may be lost |
| DeleteSessionCluster | 1. GetSessionCluster to confirm status is stopped 2. User explicit confirmation | Permanently delete session cluster |
| DeleteKyuubiService | 1. GetKyuubiService to confirm status is NOT_STARTED 2. Confirm no active JDBC connections 3. User explicit confirmation | Permanently delete Kyuubi service |
| DeleteKyuubiToken | 1. GetKyuubiToken to confirm Token ID 2. Confirm connections using this Token can be interrupted 3. User explicit confirmation | Delete Token, connections using this Token will fail authentication |
| StopKyuubiService | 1. Remind user all active JDBC connections will be disconnected 2. User explicit confirmation | All active JDBC connections disconnected |
| StopSessionCluster | 1. Remind user session will terminate 2. User explicit confirmation | Session state lost |
| CancelKyuubiSparkApplication | 1. Confirm application ID and status 2. User explicit confirmation | Abort running Spark query |

Confirmation template:
> About to execute: `<API>`, target: `<Resource ID>`, impact: `<Description>`. Continue?

## Security Guidelines

### Job Submission Protection

Before submitting Spark jobs, must:
1. Confirm workspace ID and resource queue
2. Confirm code type codeType (required: JAR / PYTHON / SQL)
3. Confirm Spark parameters and main program resource
4. Display equivalent spark-submit command
5. Get user explicit confirmation before submission

### Timeout Control

| Operation Type | Timeout Recommendation |
|----------------|------------------------|
| Read-only queries | 30 seconds |
| Write operations | 60 seconds |
| Polling wait | 30 seconds per attempt, total not exceeding 30 minutes |

### Error Handling

| Error Code | Cause | Agent Should Execute |
|------------|-------|---------------------|
| MissingParameter.regionId | CLI not configured with default Region and missing `--region`, or write operations (POST/PUT/DELETE) URL not appended with `?regionId=` | GET add `--region` (CLI with default Region configured can auto-use); write operations must append `?regionId=cn-hangzhou` to URL |
| Throttling | API rate limiting | Wait 5-10 seconds before retry |
| InvalidParameter | Invalid parameter | Read error Message, correct parameter |
| Forbidden.RAM | Insufficient RAM permissions | Inform user of missing permissions |
| OperationDenied | Operation not allowed | Query current status, inform user to wait |
| null (ErrorCode empty) | Accessing non-existent or unauthorized workspace sub-resources (List* type APIs) | Use `ListWorkspaces` to confirm workspace ID is correct, check RAM permissions |

## Related Documentation

- [Getting Started](references/getting-started.md) - First-time workspace creation and job submission
- [Workspace Lifecycle](references/workspace-lifecycle.md) - Create, query, manage workspaces
- [Job Management](references/job-management.md) - Submit, monitor, diagnose Spark jobs
- [Kyuubi Service](references/kyuubi-service.md) - Interactive SQL gateway management
- [Scaling Guide](references/scaling.md) - Resource queue scaling
- [RAM Permission Policies](references/ram-policies.md) - Permission policies, Action lists, and service roles
- [API Parameter Reference](references/api-reference.md) - Complete parameter documentation