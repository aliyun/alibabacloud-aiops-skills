# Job Management: Submit, Monitor, Diagnose Spark Jobs

## Table of Contents

- [1. Submit Jobs](#1-submit-jobs): JAR / PySpark / SQL
- [2. Query and Monitor](#2-query-and-monitor): Status, List, Logs
- [3. Cancel Jobs](#3-cancel-jobs)
- [4. Session Clusters](#4-session-clusters)
- [5. SQL Statements](#5-sql-statements)

## 1. Submit Jobs

### Pre-submission Checklist

Before submitting Spark jobs, must confirm:
1. **Workspace ID**: Target workspaceId
2. **Resource Queue**: resourceQueueId (required, e.g., `root_queue`, `dev_queue`, get via ListWorkspaceQueues, fill the `queueName` value)
3. **Job Name**: name (required, not passing will report `MissingParameter` error)
4. **Code Type**: codeType (required: JAR / PYTHON / SQL)
5. **Engine Version**: releaseVersion
6. **Main Program Resource**: entryPoint (OSS path or local path)
7. **Spark Parameters**: executor/driver cores, memory, instances

After confirmation, display equivalent spark-submit command, get user explicit confirmation before submission.

### Submit JAR Job

```bash
aliyun emr-serverless-spark start-job-run --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --body '{
    "name": "my-jar-job",
    "jobDriver": {
      "sparkSubmit": {
        "entryPoint": "oss://my-bucket/jars/my-app.jar",
        "entryPointArguments": ["arg1", "arg2"],
        "sparkSubmitParameters": "--class com.example.MyApp --conf spark.executor.cores=4 --conf spark.executor.memory=20g --conf spark.driver.cores=4 --conf spark.driver.memory=8g --conf spark.executor.instances=2"
      }
    },
    "codeType": "JAR",
    "resourceQueueId": "root_queue",
    "releaseVersion": "esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)"
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

Equivalent spark-submit command:
```bash
spark-submit \
  --class com.example.MyApp \
  --conf spark.executor.cores=4 \
  --conf spark.executor.memory=20g \
  --conf spark.driver.cores=4 \
  --conf spark.driver.memory=8g \
  --conf spark.executor.instances=2 \
  oss://my-bucket/jars/my-app.jar \
  arg1 arg2
```

### Submit PySpark Job

```bash
aliyun emr-serverless-spark start-job-run --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --body '{
    "name": "my-pyspark-job",
    "jobDriver": {
      "sparkSubmit": {
        "entryPoint": "oss://my-bucket/scripts/my_script.py",
        "entryPointArguments": ["--input", "oss://my-bucket/data/input", "--output", "oss://my-bucket/data/output"],
        "sparkSubmitParameters": "--conf spark.executor.cores=4 --conf spark.executor.memory=20g --conf spark.driver.cores=4 --conf spark.driver.memory=8g --conf spark.executor.instances=4"
      }
    },
    "codeType": "PYTHON",
    "resourceQueueId": "root_queue",
    "releaseVersion": "esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)"
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Submit Job with Custom Configuration

```bash
aliyun emr-serverless-spark start-job-run --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --body '{
    "name": "daily-etl-job",
    "jobDriver": {
      "sparkSubmit": {
        "entryPoint": "oss://my-bucket/jars/my-etl.jar",
        "sparkSubmitParameters": "--class com.example.ETL --conf spark.executor.cores=8 --conf spark.executor.memory=32g --conf spark.driver.cores=4 --conf spark.driver.memory=16g --conf spark.executor.instances=8"
      }
    },
    "configurationOverrides": {
      "configurations": [
        {
          "configFileName": "common.conf",
          "configItemKey": "hive.metastore.type",
          "configItemValue": "USER_RDS"
        }
      ]
    },
    "codeType": "JAR",
    "resourceQueueId": "root_queue",
    "releaseVersion": "esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)"
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Common Spark Parameter Reference

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| spark.driver.cores | Driver CPU cores | 4 |
| spark.driver.memory | Driver memory | 8g-16g |
| spark.executor.cores | Executor CPU cores | 4-8 |
| spark.executor.memory | Executor memory | 20g-32g |
| spark.executor.instances | Executor instance count | Adjust based on data volume |
| spark.dynamicAllocation.enabled | Dynamic allocation | true (recommended) |

## 2. Query and Monitor

### Query Single Job

```bash
aliyun emr-serverless-spark get-job-run --workspace-id {workspaceId} --job-run-id {jobRunId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Job List

```bash
# View all jobs
aliyun emr-serverless-spark list-job-runs --workspace-id {workspaceId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage

# Paginated query
aliyun emr-serverless-spark list-job-runs --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --maxResults 20 --nextToken xxx --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Job State Machine

| Status | Description |
|--------|-------------|
| Submitted | Job submitted, queuing for resource allocation |
| Running | Job executing |
| Success | Job completed successfully |
| Failed | Job execution failed |
| Cancelled | Job cancelled by user |
| Cancelling | Job being cancelled |

### View Job Logs

```bash
# View job logs (need to get log file path from GetJobRun response first)
# Note: offset and length parameters are required, not passing will cause server error
aliyun emr-serverless-spark list-log-contents --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --fileName 'oss://my-bucket/w-xxx/spark/logs/jr-xxx/driver/stdout.log' \
  --offset 0 --length 9999 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

> **Note**: `fileName` is the OSS full path of the log file, can be obtained from the `log` field in `GetJobRun` response.
> - When job is **running**, `log` field returns HTTPS URL (Spark UI real-time log link), `listLogContents` API is not available at this time
> - When job **ends** (Success/Failed/Cancelled), `log` field returns OSS path, can call `listLogContents` at this time
> - ⚠️ **Quick-fail jobs** (e.g., error during startup) may not have log files, `log` field returns OSS path but calling `listLogContents` returns `ResourceNotFound`. Get error info from `GetJobRun`'s `stateChangeReason` field at this time
>
> Common log files:
> - `driver/stdout.log` - Standard output
> - `driver/stderr.log` - Standard error
> - `driver/syslog.log` - System log (contains Spark startup info)
> - `driver/startup.log` - Startup log
>
> **OSS Path Compatibility**:
> - Supported: `oss://bucket/path` (standard), `oss://bucket.oss-cn-hangzhou.aliyuncs.com/path` (external), `oss://bucket.oss-cn-hangzhou-internal.aliyuncs.com/path` (internal), `oss://bucket.cn-hangzhou.oss-dls.aliyuncs.com/path` (DLS endpoint, can use directly when GetJobRun returns this format)
> - Not supported: CNAME domain format

### View Executor Information

```bash
aliyun emr-serverless-spark list-job-executors --workspace-id {workspaceId} --job-run-id {jobRunId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### View Queue CU Consumption

```bash
# Query CU consumption by resource queue dimension (note: query by queue, not by individual job)
aliyun emr-serverless-spark get-cu-hours --workspace-id {workspaceId} --queue {queueName} \
  --region cn-hangzhou \
  --startTime '2024-01-01 00:00:00' --endTime '2024-01-08 00:00:00' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
# Note: Query time span cannot exceed 1 month
```

### View Job Configuration

```bash
aliyun emr-serverless-spark get-run-configuration --workspace-id {workspaceId} --run-id {jobRunId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

## 3. Cancel Jobs

### Pre-cancellation Checklist

1. **Confirm job status**: Confirm job status is Running via GetJobRun
2. **Assess impact**: Completed compute results may be lost, confirm if acceptable
3. **User explicit confirmation**: Inform user of cancellation impact

```bash
# First confirm job status
aliyun emr-serverless-spark get-job-run --workspace-id {workspaceId} --job-run-id {jobRunId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage

# ⚠️ Cancel job (completed compute results may be lost)
aliyun emr-serverless-spark cancel-job-run --workspace-id {workspaceId} --job-run-id {jobRunId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

Status change after cancellation: `Running` → `Cancelling` → `Cancelled`

## 4. Session Clusters

Session clusters provide long-running interactive environments, suitable for development debugging and Notebook usage.

### Create Session Cluster

```bash
aliyun emr-serverless-spark create-session-cluster --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --body '{
    "name": "my-session",
    "queueName": "default",
    "releaseVersion": "esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)",
    "kind": "SQL",
    "autoStopConfiguration": {
      "enable": true,
      "idleTimeoutMinutes": 30
    }
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### View Session Cluster List

```bash
aliyun emr-serverless-spark list-session-clusters --workspace-id {workspaceId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Start Session Cluster

```bash
aliyun emr-serverless-spark start-session-cluster --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --body '{
    "sessionClusterId": "sc-xxx",
    "queueName": "default"
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Stop Session Cluster

```bash
aliyun emr-serverless-spark stop-session-cluster --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --body '{
    "sessionClusterId": "sc-xxx",
    "queueName": "default"
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### View Session Cluster Details

```bash
aliyun emr-serverless-spark get-session-cluster --workspace-id {workspaceId} --session-cluster-id {sessionClusterId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Session Cluster Status Description

| Status | Description |
|--------|-------------|
| NotStarted | Session created but not started |
| starting | Session starting |
| running | Session running, can accept queries |
| stopping | Session stopping |
| stopped | Session stopped |

### Delete Session Cluster

#### Pre-deletion Checklist

1. **Confirm session stopped**: Confirm status is stopped via GetSessionCluster
2. **User explicit confirmation**: Inform user deletion is irreversible

```bash
# First confirm session cluster status
aliyun emr-serverless-spark get-session-cluster --workspace-id {workspaceId} --session-cluster-id {sessionClusterId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage

# ⚠️ Delete session cluster (irreversible)
aliyun emr-serverless-spark delete-session-cluster --workspace-id {workspaceId} --session-cluster-id {sessionClusterId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

## 5. SQL Statements

Submit and execute SQL statements through session clusters.

### Submit SQL Statement

```bash
aliyun emr-serverless-spark create-sql-statement --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --body '{
    "sqlComputeId": "sc-xxx",
    "codeContent": "SELECT * FROM my_table LIMIT 10",
    "defaultDatabase": "default"
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Query SQL Execution Status

```bash
aliyun emr-serverless-spark get-sql-statement --workspace-id {workspaceId} --statement-id {statementId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

**Status Description**:

| Status | Description |
|--------|-------------|
| waiting | Waiting to execute |
| running | Executing |
| available | Execution complete, can get results |
| error | Execution error |

### Terminate SQL Query

```bash
aliyun emr-serverless-spark terminate-sql-statement --workspace-id {workspaceId} --statement-id {statementId} --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

### Query SQL Execution Results

> **Recommended Method**: Prefer using `GetSqlStatement` to get results, response's `sqlOutputs` field directly contains query results (schema + rows).
>
> `ListSqlStatementContents` is a backup method to read results via OSS log file, requires session cluster to be stopped and logs written to OSS before available. `fileName` needs to be obtained by concatenating statementId from session cluster's associated JobRun log path.

```bash
aliyun emr-serverless-spark list-sql-statement-contents --workspace-id {workspaceId} \
  --region cn-hangzhou \
  --fileName 'oss://bucket/w-xxx/spark/logs/jr-xxx/driver/st-xxx' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-emr-spark-manage
```

## Common Job Failure Causes

| Symptom | Possible Cause | Troubleshooting Method |
|---------|----------------|------------------------|
| OOM (OutOfMemoryError) | Executor/Driver memory insufficient | Increase memory configuration or reduce partition data volume |
| Long pending | Resource queue CU insufficient | Scale up resource queue |
| ClassNotFoundException | JAR missing or path error | Check entryPoint and dependency JAR paths |
| Job running slow | Data skew or insufficient Executor count | Increase Executor count |

## Related Documentation

- [Getting Started](getting-started.md) - First-time workspace creation and job submission
- [Workspace Lifecycle](workspace-lifecycle.md) - Create, query, manage workspaces
- [Kyuubi Service](kyuubi-service.md) - Interactive SQL gateway management
- [Scaling Guide](scaling.md) - Resource queue scaling
- [API Parameter Reference](api-reference.md) - Complete parameter documentation