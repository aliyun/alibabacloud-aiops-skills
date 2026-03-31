# RAM Permission Policies

This document details the RAM permission policies required for EMR Serverless Spark, including system policies, custom policies, and service roles.

## required_permissions

The permissions required for this Skill are declared as follows:

```yaml
required_permissions:
  - policy: AliyunEMRServerlessSparkFullAccess
    description: Administrator permissions, includes all operations such as create/delete workspaces, job management, Kyuubi service management, etc.
    actions:
      # Workspace
      - emr-serverless-spark:CreateWorkspace
      - emr-serverless-spark:DeleteWorkspace
      - emr-serverless-spark:ListWorkspaces
      - emr-serverless-spark:ListWorkspaceQueues
      - emr-serverless-spark:EditWorkspaceQueue
      # Job
      - emr-serverless-spark:StartJobRun
      - emr-serverless-spark:GetJobRun
      - emr-serverless-spark:ListJobRuns
      - emr-serverless-spark:CancelJobRun
      - emr-serverless-spark:ListLogContents
      - emr-serverless-spark:GetCuHours
      - emr-serverless-spark:GetRunConfiguration
      - emr-serverless-spark:ListJobExecutors
      # Session Cluster
      - emr-serverless-spark:CreateSessionCluster
      - emr-serverless-spark:GetSessionCluster
      - emr-serverless-spark:ListSessionClusters
      - emr-serverless-spark:StartSessionCluster
      - emr-serverless-spark:StopSessionCluster
      - emr-serverless-spark:DeleteSessionCluster
      # SQL
      - emr-serverless-spark:CreateSqlStatement
      - emr-serverless-spark:GetSqlStatement
      - emr-serverless-spark:TerminateSqlStatement
      - emr-serverless-spark:ListSqlStatementContents
      # Kyuubi Service
      - emr-serverless-spark:CreateKyuubiService
      - emr-serverless-spark:GetKyuubiService
      - emr-serverless-spark:ListKyuubiServices
      - emr-serverless-spark:StartKyuubiService
      - emr-serverless-spark:StopKyuubiService
      - emr-serverless-spark:UpdateKyuubiService
      - emr-serverless-spark:DeleteKyuubiService
      # Kyuubi Token
      - emr-serverless-spark:CreateKyuubiToken
      - emr-serverless-spark:GetKyuubiToken
      - emr-serverless-spark:ListKyuubiToken
      - emr-serverless-spark:UpdateKyuubiToken
      - emr-serverless-spark:DeleteKyuubiToken
      # Kyuubi Application
      - emr-serverless-spark:ListKyuubiSparkApplications
      - emr-serverless-spark:CancelKyuubiSparkApplication
      # Auth
      - emr-serverless-spark:AddMembers
      - emr-serverless-spark:ListMembers
      - emr-serverless-spark:GrantRoleToUsers
      # Version & Catalog
      - emr-serverless-spark:ListReleaseVersions
      - emr-serverless-spark:ListCatalogs
      # Supplementary
      - oss:ListBuckets
      - dlf:DescribeRegions
      - dlf:GetRegionStatus
      - dlf:ListCatalogs
      - dlf:ListDatabases
      - dlf:ListTables
      - emr:GetApmData
      - emr:QueryApmGrafanaData
  - policy: AliyunEMRServerlessSparkDeveloperAccess
    description: Developer permissions, includes submit jobs, manage sessions, Kyuubi operations, etc., excludes create/delete workspaces
    actions:
      # Workspace (read-only)
      - emr-serverless-spark:ListWorkspaces
      - emr-serverless-spark:ListWorkspaceQueues
      - emr-serverless-spark:EditWorkspaceQueue
      # Job
      - emr-serverless-spark:StartJobRun
      - emr-serverless-spark:GetJobRun
      - emr-serverless-spark:ListJobRuns
      - emr-serverless-spark:CancelJobRun
      - emr-serverless-spark:ListLogContents
      - emr-serverless-spark:GetCuHours
      - emr-serverless-spark:GetRunConfiguration
      - emr-serverless-spark:ListJobExecutors
      # Session Cluster
      - emr-serverless-spark:CreateSessionCluster
      - emr-serverless-spark:GetSessionCluster
      - emr-serverless-spark:ListSessionClusters
      - emr-serverless-spark:StartSessionCluster
      - emr-serverless-spark:StopSessionCluster
      - emr-serverless-spark:DeleteSessionCluster
      # SQL
      - emr-serverless-spark:CreateSqlStatement
      - emr-serverless-spark:GetSqlStatement
      - emr-serverless-spark:TerminateSqlStatement
      - emr-serverless-spark:ListSqlStatementContents
      # Kyuubi Service
      - emr-serverless-spark:CreateKyuubiService
      - emr-serverless-spark:GetKyuubiService
      - emr-serverless-spark:ListKyuubiServices
      - emr-serverless-spark:StartKyuubiService
      - emr-serverless-spark:StopKyuubiService
      - emr-serverless-spark:UpdateKyuubiService
      - emr-serverless-spark:DeleteKyuubiService
      # Kyuubi Token
      - emr-serverless-spark:CreateKyuubiToken
      - emr-serverless-spark:GetKyuubiToken
      - emr-serverless-spark:ListKyuubiToken
      - emr-serverless-spark:UpdateKyuubiToken
      - emr-serverless-spark:DeleteKyuubiToken
      # Kyuubi Application
      - emr-serverless-spark:ListKyuubiSparkApplications
      - emr-serverless-spark:CancelKyuubiSparkApplication
      # Version & Catalog
      - emr-serverless-spark:ListReleaseVersions
      - emr-serverless-spark:ListCatalogs
      # Supplementary
      - oss:ListBuckets
      - dlf:DescribeRegions
      - dlf:GetRegionStatus
      - dlf:ListCatalogs
      - dlf:ListDatabases
      - dlf:ListTables
  - policy: AliyunEmrServerlessSparkReadOnlyAccess
    description: Read-only permissions, includes Get*, List*, Query*, Is*, Check* operations
    actions:
      # Workspace
      - emr-serverless-spark:ListWorkspaces
      - emr-serverless-spark:ListWorkspaceQueues
      # Job
      - emr-serverless-spark:GetJobRun
      - emr-serverless-spark:ListJobRuns
      - emr-serverless-spark:ListLogContents
      - emr-serverless-spark:GetCuHours
      - emr-serverless-spark:GetRunConfiguration
      - emr-serverless-spark:ListJobExecutors
      # Session Cluster
      - emr-serverless-spark:GetSessionCluster
      - emr-serverless-spark:ListSessionClusters
      # SQL
      - emr-serverless-spark:GetSqlStatement
      - emr-serverless-spark:ListSqlStatementContents
      # Kyuubi Service
      - emr-serverless-spark:GetKyuubiService
      - emr-serverless-spark:ListKyuubiServices
      # Kyuubi Token
      - emr-serverless-spark:GetKyuubiToken
      - emr-serverless-spark:ListKyuubiToken
      # Kyuubi Application
      - emr-serverless-spark:ListKyuubiSparkApplications
      # Auth
      - emr-serverless-spark:ListMembers
      # Version & Catalog
      - emr-serverless-spark:ListReleaseVersions
      - emr-serverless-spark:ListCatalogs
```

## System Policies

EMR Serverless Spark provides three system policies, listed in order of permission scope from large to small:

### AliyunEMRServerlessSparkFullAccess

**Applicable Role**: Administrator

**Permission Scope**:

**Workspace Management**:
- `emr-serverless-spark:CreateWorkspace` - Create workspace
- `emr-serverless-spark:DeleteWorkspace` - Delete workspace
- `emr-serverless-spark:ListWorkspaces` - List workspaces
- `emr-serverless-spark:ListWorkspaceQueues` - List resource queues
- `emr-serverless-spark:EditWorkspaceQueue` - Modify resource queue

**Job Management**:
- `emr-serverless-spark:StartJobRun` - Submit job
- `emr-serverless-spark:GetJobRun` - Query job details
- `emr-serverless-spark:ListJobRuns` - List jobs
- `emr-serverless-spark:CancelJobRun` - Cancel job
- `emr-serverless-spark:ListLogContents` - Query logs
- `emr-serverless-spark:GetCuHours` - Query CU consumption
- `emr-serverless-spark:GetRunConfiguration` - Query job configuration
- `emr-serverless-spark:ListJobExecutors` - Query Executor information

**Session Cluster**:
- `emr-serverless-spark:CreateSessionCluster` - Create session cluster
- `emr-serverless-spark:GetSessionCluster` - Query session cluster
- `emr-serverless-spark:ListSessionClusters` - List session clusters
- `emr-serverless-spark:StartSessionCluster` - Start session cluster
- `emr-serverless-spark:StopSessionCluster` - Stop session cluster
- `emr-serverless-spark:DeleteSessionCluster` - Delete session cluster

**SQL Query**:
- `emr-serverless-spark:CreateSqlStatement` - Submit SQL
- `emr-serverless-spark:GetSqlStatement` - Query SQL status
- `emr-serverless-spark:TerminateSqlStatement` - Terminate SQL
- `emr-serverless-spark:ListSqlStatementContents` - Query SQL results

**Kyuubi Service**:
- `emr-serverless-spark:CreateKyuubiService` - Create Kyuubi service
- `emr-serverless-spark:GetKyuubiService` - Query Kyuubi service
- `emr-serverless-spark:ListKyuubiServices` - List Kyuubi services
- `emr-serverless-spark:StartKyuubiService` - Start Kyuubi service
- `emr-serverless-spark:StopKyuubiService` - Stop Kyuubi service
- `emr-serverless-spark:UpdateKyuubiService` - Update Kyuubi service
- `emr-serverless-spark:DeleteKyuubiService` - Delete Kyuubi service

**Kyuubi Token**:
- `emr-serverless-spark:CreateKyuubiToken` - Create Token
- `emr-serverless-spark:GetKyuubiToken` - Query Token
- `emr-serverless-spark:ListKyuubiToken` - List Tokens
- `emr-serverless-spark:UpdateKyuubiToken` - Update Token
- `emr-serverless-spark:DeleteKyuubiToken` - Delete Token

**Kyuubi Application**:
- `emr-serverless-spark:ListKyuubiSparkApplications` - List applications
- `emr-serverless-spark:CancelKyuubiSparkApplication` - Cancel application

**Permission Management**:
- `emr-serverless-spark:AddMembers` - Add members
- `emr-serverless-spark:ListMembers` - List members
- `emr-serverless-spark:GrantRoleToUsers` - Grant role

**Version & Catalog**:
- `emr-serverless-spark:ListReleaseVersions` - List engine versions
- `emr-serverless-spark:ListCatalogs` - List data catalogs

**Supplementary Permissions**:
- `oss:ListBuckets` - List OSS Buckets
- `dlf:DescribeRegions` - Describe DLF regions
- `dlf:GetRegionStatus` - Get DLF region status
- `dlf:ListCatalogs` - List DLF data catalogs
- `dlf:ListDatabases` - List DLF databases
- `dlf:ListTables` - List DLF data tables
- `emr:GetApmData` - Get APM data
- `emr:QueryApmGrafanaData` - Query Grafana data

**Authorization Command**:
```bash
aliyun ram AttachPolicyToUser \
  --PolicyName AliyunEMRServerlessSparkFullAccess \
  --PolicyType System \
  --UserName <username> \
  --user-agent AlibabaCloud-Agent-Skills
```

### AliyunEMRServerlessSparkDeveloperAccess

**Applicable Role**: Developer

**Permission Scope**:

**Workspace (Read-only)**:
- `emr-serverless-spark:ListWorkspaces` - List workspaces
- `emr-serverless-spark:ListWorkspaceQueues` - List resource queues
- `emr-serverless-spark:EditWorkspaceQueue` - Modify resource queue

**Job Management**:
- `emr-serverless-spark:StartJobRun` - Submit job
- `emr-serverless-spark:GetJobRun` - Query job details
- `emr-serverless-spark:ListJobRuns` - List jobs
- `emr-serverless-spark:CancelJobRun` - Cancel job
- `emr-serverless-spark:ListLogContents` - Query logs
- `emr-serverless-spark:GetCuHours` - Query CU consumption
- `emr-serverless-spark:GetRunConfiguration` - Query job configuration
- `emr-serverless-spark:ListJobExecutors` - Query Executor information

**Session Cluster**:
- `emr-serverless-spark:CreateSessionCluster` - Create session cluster
- `emr-serverless-spark:GetSessionCluster` - Query session cluster
- `emr-serverless-spark:ListSessionClusters` - List session clusters
- `emr-serverless-spark:StartSessionCluster` - Start session cluster
- `emr-serverless-spark:StopSessionCluster` - Stop session cluster
- `emr-serverless-spark:DeleteSessionCluster` - Delete session cluster

**SQL Query**:
- `emr-serverless-spark:CreateSqlStatement` - Submit SQL
- `emr-serverless-spark:GetSqlStatement` - Query SQL status
- `emr-serverless-spark:TerminateSqlStatement` - Terminate SQL
- `emr-serverless-spark:ListSqlStatementContents` - Query SQL results

**Kyuubi Service**:
- `emr-serverless-spark:CreateKyuubiService` - Create Kyuubi service
- `emr-serverless-spark:GetKyuubiService` - Query Kyuubi service
- `emr-serverless-spark:ListKyuubiServices` - List Kyuubi services
- `emr-serverless-spark:StartKyuubiService` - Start Kyuubi service
- `emr-serverless-spark:StopKyuubiService` - Stop Kyuubi service
- `emr-serverless-spark:UpdateKyuubiService` - Update Kyuubi service
- `emr-serverless-spark:DeleteKyuubiService` - Delete Kyuubi service

**Kyuubi Token**:
- `emr-serverless-spark:CreateKyuubiToken` - Create Token
- `emr-serverless-spark:GetKyuubiToken` - Query Token
- `emr-serverless-spark:ListKyuubiToken` - List Tokens
- `emr-serverless-spark:UpdateKyuubiToken` - Update Token
- `emr-serverless-spark:DeleteKyuubiToken` - Delete Token

**Kyuubi Application**:
- `emr-serverless-spark:ListKyuubiSparkApplications` - List applications
- `emr-serverless-spark:CancelKyuubiSparkApplication` - Cancel application

**Version & Catalog**:
- `emr-serverless-spark:ListReleaseVersions` - List engine versions
- `emr-serverless-spark:ListCatalogs` - List data catalogs

**Supplementary Permissions**:
- `oss:ListBuckets` - List OSS Buckets
- `dlf:DescribeRegions` - Describe DLF regions
- `dlf:GetRegionStatus` - Get DLF region status
- `dlf:ListCatalogs` - List DLF data catalogs
- `dlf:ListDatabases` - List DLF databases
- `dlf:ListTables` - List DLF data tables

> **Note**: Does not include `CreateWorkspace` and `DeleteWorkspace` permissions

**Authorization Command**:
```bash
aliyun ram AttachPolicyToUser \
  --PolicyName AliyunEMRServerlessSparkDeveloperAccess \
  --PolicyType System \
  --UserName <username> \
  --user-agent AlibabaCloud-Agent-Skills
```

### AliyunEmrServerlessSparkReadOnlyAccess

**Applicable Role**: Audit, read-only viewing

**Permission Scope**:

**Workspace**:
- `emr-serverless-spark:ListWorkspaces` - List workspaces
- `emr-serverless-spark:ListWorkspaceQueues` - List resource queues

**Job Management**:
- `emr-serverless-spark:GetJobRun` - Query job details
- `emr-serverless-spark:ListJobRuns` - List jobs
- `emr-serverless-spark:ListLogContents` - Query logs
- `emr-serverless-spark:GetCuHours` - Query CU consumption
- `emr-serverless-spark:GetRunConfiguration` - Query job configuration
- `emr-serverless-spark:ListJobExecutors` - Query Executor information

**Session Cluster**:
- `emr-serverless-spark:GetSessionCluster` - Query session cluster
- `emr-serverless-spark:ListSessionClusters` - List session clusters

**SQL Query**:
- `emr-serverless-spark:GetSqlStatement` - Query SQL status
- `emr-serverless-spark:ListSqlStatementContents` - Query SQL results

**Kyuubi Service**:
- `emr-serverless-spark:GetKyuubiService` - Query Kyuubi service
- `emr-serverless-spark:ListKyuubiServices` - List Kyuubi services

**Kyuubi Token**:
- `emr-serverless-spark:GetKyuubiToken` - Query Token
- `emr-serverless-spark:ListKyuubiToken` - List Tokens

**Kyuubi Application**:
- `emr-serverless-spark:ListKyuubiSparkApplications` - List applications

**Permission Management**:
- `emr-serverless-spark:ListMembers` - List members

**Version & Catalog**:
- `emr-serverless-spark:ListReleaseVersions` - List engine versions
- `emr-serverless-spark:ListCatalogs` - List data catalogs

**Authorization Command**:
```bash
aliyun ram AttachPolicyToUser \
  --PolicyName AliyunEmrServerlessSparkReadOnlyAccess \
  --PolicyType System \
  --UserName <username> \
  --user-agent AlibabaCloud-Agent-Skills
```

## Custom Policies

If fine-grained permission control is needed, you can create custom policies.

### Action Format

All EMR Serverless Spark API Actions have the format:

```
emr-serverless-spark:<ActionName>
```

Examples:
- `emr-serverless-spark:StartJobRun` - Submit job
- `emr-serverless-spark:GetJobRun` - Query job
- `emr-serverless-spark:ListWorkspaces` - List workspaces

### Custom Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "emr-serverless-spark:ListWorkspaces",
        "emr-serverless-spark:GetWorkspace",
        "emr-serverless-spark:ListJobRuns",
        "emr-serverless-spark:GetJobRun",
        "emr-serverless-spark:StartJobRun"
      ],
      "Resource": "*"
    }
  ]
}
```

## Supplementary Permissions

EMR Serverless Spark jobs may need to access other cloud services, below are commonly used supplementary permissions:

| Service | Action | Description |
|---------|--------|-------------|
| OSS | `oss:ListBuckets` | List OSS Buckets |
| DLF | `dlf:DescribeRegions` | Describe DLF regions |
| DLF | `dlf:GetRegionStatus` | Get region status |
| DLF | `dlf:ListCatalogs` | List data catalogs |
| DLF | `dlf:ListDatabases` | List databases |
| DLF | `dlf:ListTables` | List data tables |
| EMR APM | `emr:GetApmData` | Get APM data |
| EMR APM | `emr:QueryApmGrafanaData` | Query Grafana data |

## Service Roles

### AliyunServiceRoleForEMRServerlessSpark

**Type**: Service-linked role

**Purpose**: EMR Serverless Spark service uses this role to access your resources in other cloud products.

**Auto Creation**: When using EMR Serverless Spark for the first time, the system will prompt you to create this role.

**Manual Creation**:
```bash
aliyun ram CreateServiceLinkedRole \
  --ServiceName spark.emr-serverless.aliyuncs.com \
  --user-agent AlibabaCloud-Agent-Skills
```

**Trust Policy**:
```json
{
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "spark.emr-serverless.aliyuncs.com"
        ]
      }
    }
  ],
  "Version": "1"
}
```

### AliyunEMRSparkJobRunDefaultRole

**Type**: Job execution role

**Purpose**: Spark jobs use this role to access OSS, DLF and other cloud resources during execution.

**Creation Methods**:
1. One-click authorization through EMR Serverless Spark console
2. Manual creation in RAM console

**Required Permissions**:
- OSS read/write permissions (to access job code and output data)
- DLF metadata access permissions (if using DLF data catalog)

## Permission Checklist

Before using EMR Serverless Spark for the first time, please confirm:

- [ ] RAM user has been granted corresponding system policy or custom policy
- [ ] Service-linked role `AliyunServiceRoleForEMRServerlessSpark` has been created
- [ ] Job execution role `AliyunEMRSparkJobRunDefaultRole` has been created
- [ ] OSS Bucket has been created and is accessible
- [ ] If using DLF, corresponding metadata permissions have been configured

## Common Permission Issues

### Forbidden.RAM

**Error Message**: `You are not authorized to perform this operation`

**Solution**:
1. Check if RAM user has been granted corresponding policy
2. Check if service-linked role has been created
3. Confirm custom policy's Action and Resource configuration is correct

### Service-linked Role Creation Failed

**Error Message**: `You are not authorized to create service linked role`

**Solution**:
Need RAM administrator permissions or `ram:CreateServiceLinkedRole` permission to create service-linked role. Please contact account administrator for assistance.

### Job Execution Insufficient Permissions

**Error Message**: OSS or DLF access permission error during job execution

**Solution**:
1. Confirm `AliyunEMRSparkJobRunDefaultRole` has been created
2. Confirm the role has been granted necessary OSS and DLF permissions
3. Confirm the role name configured in workspace is correct