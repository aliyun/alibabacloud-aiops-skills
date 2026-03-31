# Getting Started: Create Your First Spark Workspace from Scratch and Submit a Job

This guide helps first-time users complete: Prerequisites check → Create workspace → Submit first job → View results.

## Prerequisites

### 1. CLI Environment

```bash
# Verify Alibaba Cloud CLI is installed
aliyun version

# Verify credentials are configured (should display current profile)
aliyun configure list
```

### 2. Grant Service Roles (Required for First-time Use)

Before using EMR Serverless Spark, you need to grant the account the following two roles:

| Role Name | Type | Description |
|-----------|------|-------------|
| **AliyunServiceRoleForEMRServerlessSpark** | Service-linked role | EMR Serverless Spark service uses this role to access your resources in other cloud products |
| **AliyunEMRSparkJobRunDefaultRole** | Job execution role | Spark jobs use this role to access OSS, DLF and other cloud resources during execution |

> For first-time use, you can authorize with one click through the [EMR Serverless Spark Console](https://emr-serverless-spark.console.aliyun.com), or manually create in the RAM console.

### 3. OSS Storage

Spark jobs need OSS storage to store program files and output data. **Confirm RegionId with user before execution** (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`, etc.):

```bash
# Check for available OSS Buckets
aliyun oss ls --user-agent AlibabaCloud-Agent-Skills

# If none, create one
aliyun oss mb oss://my-spark-bucket --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

### 4. Confirm Region Information

Record the following information, will be used when creating workspace and submitting jobs:
- RegionId (e.g., `cn-hangzhou`)
- OSS Bucket name and path

## Step 1: View Available Engine Versions

```bash
aliyun emr-serverless-spark GET /api/v1/releaseVersions --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

Note the latest `releaseVersion` (e.g., `esr-4.7.0 (Spark 3.5.2, Scala 2.12, Java Runtime)`), will be needed when submitting jobs later.

## Step 2: Create Workspace

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "workspaceName": "my-first-spark-workspace",
    "ossBucket": "oss://my-spark-bucket",
    "ramRoleName": "AliyunEMRSparkJobRunDefaultRole",
    "paymentType": "PayAsYouGo",
    "resourceSpec": {"cu": 8}
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

Returns `workspaceId` (e.g., `w-xxx`), note it for subsequent operations.

> **Note**: Workspace creation is an async operation, initial status is `STARTING`, need to wait about 1-3 minutes to become `RUNNING` before you can operate resource queues and submit jobs.

### Wait for Workspace Ready

```bash
# View workspace status, wait for workspaceStatus to become RUNNING
aliyun emr-serverless-spark GET /api/v1/workspaces --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

**Workspace Status Description**:

| Status | Description |
|--------|-------------|
| STARTING | Workspace being created, resources initializing |
| RUNNING | Workspace ready, can be used normally |
| TERMINATING | Workspace being deleted |

## Step 3: View Resource Queues

After workspace is ready, there will be default resource queues:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/{workspaceId}/queues --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

Note the `queueName` (e.g., `root_queue`, `dev_queue`), fill in `resourceQueueId` field when submitting jobs.

## Step 4: Submit First Spark Job

### Submit Spark SQL Example (Simplest Way to Get Started)

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces/{workspaceId}/jobRuns?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "my-first-sql-job",
    "jobDriver": {
      "sparkSubmit": {
        "entryPoint": "local:///tmp/spark-sql.sh",
        "sparkSubmitParameters": "--conf spark.executor.cores=4 --conf spark.executor.memory=20g --conf spark.driver.cores=4 --conf spark.driver.memory=8g --conf spark.executor.instances=1 --conf spark.emr.sql.content=SELECT 1 as test_value"
      }
    },
    "codeType": "SQL",
    "resourceQueueId": "root_queue",
    "releaseVersion": "<replace with version from step 1>"
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

> **Important**:
> - `name` is a required field, not passing will report `MissingParameter` error
> - `releaseVersion` needs to be replaced with actual version from step 1 (e.g., `esr-4.7.0 (Spark 3.5.2, Scala 2.12, Java Runtime)`)
> - `resourceQueueId` fill with queue name from step 3

Returns `jobRunId` (e.g., `jr-xxx`), note it for querying status.

### Submit PySpark Example

```bash
# First upload Python script to OSS
# aliyun oss cp my_script.py oss://my-spark-bucket/scripts/my_script.py

aliyun emr-serverless-spark POST "/api/v1/workspaces/{workspaceId}/jobRuns?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "my-pyspark-job",
    "jobDriver": {
      "sparkSubmit": {
        "entryPoint": "oss://my-spark-bucket/scripts/my_script.py",
        "sparkSubmitParameters": "--conf spark.executor.cores=4 --conf spark.executor.memory=20g --conf spark.driver.cores=4 --conf spark.driver.memory=8g --conf spark.executor.instances=1"
      }
    },
    "codeType": "PYTHON",
    "resourceQueueId": "root_queue",
    "releaseVersion": "<replace with version from step 1>"
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

## Step 5: View Job Status

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/{workspaceId}/jobRuns/{jobRunId} --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

**Status Flow**: `Submitted` → `Running` → `Success` / `Failed` / `Cancelled`

Wait for `state` to become `Success` to indicate job completion.

### Job Status Description

| Status | Description |
|--------|-------------|
| Submitted | Job submitted, queuing for resources |
| Running | Job running |
| Success | Job completed successfully |
| Failed | Job execution failed |
| Cancelled | Job cancelled by user |
| Cancelling | Job being cancelled |

## Step 6: View Job Logs

```bash
# View standard output (need to get log file path from GetJobRun response first)
# Note: offset and length parameters are required, not passing will cause server error
aliyun emr-serverless-spark GET /api/v1/workspaces/{workspaceId}/action/listLogContents \
  --region cn-hangzhou \
  --fileName 'oss://my-spark-bucket/w-xxx/spark/logs/jr-xxx/driver/stdout.log' \
  --offset 0 --length 9999 \
  --force --user-agent AlibabaCloud-Agent-Skills
```

> **Note**: `fileName` path is obtained from the `log` field in `GetJobRun` response.
> - When job is **running**, `log` field returns HTTPS URL (Spark UI real-time log link), `listLogContents` API is not available at this time
> - When job **ends** (Success/Failed/Cancelled), `log` field returns OSS path, can call `listLogContents` at this time
>
> Supported OSS path formats:
> - `oss://bucket/path` (standard format, recommended)
> - `oss://bucket.oss-cn-hangzhou.aliyuncs.com/path` (external endpoint)
> - `oss://bucket.oss-cn-hangzhou-internal.aliyuncs.com/path` (internal endpoint)
> - `oss://bucket.cn-hangzhou.oss-dls.aliyuncs.com/path` (DLS endpoint, can use directly when GetJobRun returns this format)
>
> **Not Supported** CNAME domain format.

## Cleanup: Watch Costs

- Serverless Spark is billed by actual CU hours used, no ongoing costs after job ends
- Resource queues don't incur costs when idle
- Kyuubi service consumes resources continuously while running, recommend stopping when not in use

## Common Issues

| Symptom | Possible Cause | Troubleshooting Method |
|---------|----------------|------------------------|
| Job pending for long time | Resource queue CU insufficient | Check queue configuration, consider scaling up |
| Job failed | Program error or configuration error | View job logs |
| Submission failed InvalidParameter | Invalid parameters | Check engine version, entryPoint path, etc. |
| Forbidden.RAM | Insufficient RAM permissions | Check RAM user permission configuration |

## Next Steps

- Need to submit more job types? → Refer to [Job Management](job-management.md)
- Need interactive queries? → Refer to [Kyuubi Service](kyuubi-service.md)
- Need to scale? → Refer to [Scaling Guide](scaling.md)
- API parameter lookup? → Refer to [API Parameter Reference](api-reference.md)