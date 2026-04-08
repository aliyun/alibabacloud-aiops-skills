# Workspace Lifecycle: Create → Query → Manage

## Table of Contents

- [1. Create Workspace](#1-create-workspace)
- [2. Query Workspace](#2-query-workspace)
- [4. Member Management](#4-member-management)
- [5. Engine Versions](#5-engine-versions)

## 1. Create Workspace

### Prerequisite: Grant Service Roles

Before creating a workspace, ensure the account has granted the following two roles:
- **AliyunServiceRoleForEMRServerlessSpark**: Service-linked role, EMR Serverless Spark service uses this role to access other cloud resources
- **AliyunEMRSparkJobRunDefaultRole**: Job execution role, Spark jobs use this role to access OSS, DLF and other resources during execution

> For first-time use, you can authorize with one click through the [EMR Serverless Spark Console](https://emr-next.console.aliyun.com/#/region/cn-hangzhou/resource/all/serverless/spark/list).

### Create Basic Workspace

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "workspaceName": "my-spark-workspace",
    "ossBucket": "oss://my-spark-bucket",
    "ramRoleName": "AliyunEMRSparkJobRunDefaultRole",
    "paymentType": "PayAsYouGo",
    "resourceSpec": {"cu": 8}
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

### Verify After Creation

Workspace creation is an asynchronous operation, initial status is `STARTING`, need to wait about 1-3 minutes to become `RUNNING` before you can operate resource queues and submit jobs.

```bash
# View workspace list to confirm creation success, wait for workspaceStatus to become RUNNING
aliyun emr-serverless-spark GET /api/v1/workspaces --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### Workspace Status Description

| Status | Description |
|--------|-------------|
| STARTING | Workspace being created, resources initializing. Cannot operate queues and submit jobs in this state |
| RUNNING | Workspace ready, can be used normally |
| TERMINATING | Workspace being deleted (async deletion) |

## 2. Query Workspace

### Workspace List

```bash
# View all workspaces
aliyun emr-serverless-spark GET /api/v1/workspaces --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills

# Paginated query
aliyun emr-serverless-spark GET /api/v1/workspaces --region cn-hangzhou --maxResults 10 --nextToken xxx --force --user-agent AlibabaCloud-Agent-Skills
```

### Workspace Details

Key information in the response:
- `workspaceId`: Workspace ID
- `name`: Workspace name
- `creator`: Creator
- `gmtCreated`: Creation time

## 3. Delete Workspace

> **STRICTLY PROHIBITED.** The `DeleteWorkspace` API must NEVER be called through this skill. Do NOT construct or execute any DELETE request to `/api/v1/workspaces/{workspaceId}`. If the user asks to delete a workspace, refuse the request and inform them: "Workspace deletion is not supported via this skill. Please delete workspaces through the [EMR Serverless Spark Console](https://emr-next.console.aliyun.com/#/region/cn-hangzhou/resource/all/serverless/spark/list)."

## 4. Member Management

### Add Members

```bash
aliyun emr-serverless-spark POST "/api/v1/auth/members?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "workspaceId": "w-xxx",
    "memberArns": ["acs:ram::123456789:user/username"]
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

### View Member List

```bash
aliyun emr-serverless-spark GET /api/v1/auth/{workspaceId}/members --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### Grant Roles

> **ARN Format Explanation**:
> - `roleArn` format is `acs:emr::{workspaceId}:role/{roleName}`, e.g. `acs:emr::w-xxx:role/Owner`
> - `userArns` format is `acs:emr::{workspaceId}:member/{userId}`, can get from `memberArn` field in ListMembers response

```bash
# First view member list to get userArn and available roles
aliyun emr-serverless-spark GET /api/v1/auth/{workspaceId}/members --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills

# Grant role
aliyun emr-serverless-spark POST "/api/v1/auth/roles/grant?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "roleArn": "acs:emr::w-xxx:role/Owner",
    "userArns": ["acs:emr::w-xxx:member/123456789"]
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

## 5. Engine Versions

### View Available Versions

```bash
aliyun emr-serverless-spark GET /api/v1/releaseVersions --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

Returns all available Spark engine versions, need to specify version number when creating jobs and sessions.

## Related Documentation

- [Getting Started](getting-started.md) - Simplified workflow for first-time workspace creation
- [Job Management](job-management.md) - Submit, monitor, diagnose Spark jobs
- [Kyuubi Service](kyuubi-service.md) - Interactive SQL gateway management
- [Scaling Guide](scaling.md) - Resource queue scaling
- [API Parameter Reference](api-reference.md) - Complete parameter documentation