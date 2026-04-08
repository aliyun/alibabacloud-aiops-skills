# API Parameter Reference

All APIs are version `2023-08-08`, request method is ROA style (RESTful).

> **Important**: When calling this product's API with Alibaba Cloud CLI:
> 1. Must add `--force` parameter to skip local API metadata validation, otherwise will report `can not find api by path` error.
> 2. Recommend always adding `--region <regionId>` parameter to specify region (e.g., `cn-hangzhou`). If CLI has no default Region configured and `--region` not specified, server reports `MissingParameter.regionId` error.
> 3. **POST / PUT / DELETE write operations** need to append `?regionId=cn-hangzhou` at end of URL, `--region` alone is not enough. GET requests only need `--region`.
>
> All examples already include `--force` and `--region`, write operation examples have appended `?regionId=cn-hangzhou` to URL.

## Table of Contents

- [Workspace Management](#workspace-management)
- [Job Management](#job-management)
- [Session Cluster](#session-cluster)
- [SQL Statement](#sql-statement)
- [Kyuubi Service](#kyuubi-service)
- [Kyuubi Token](#kyuubi-token)
- [Kyuubi Application](#kyuubi-application)
- [Permission Management](#permission-management)
- [Version Management](#version-management)
- [Data Catalog](#data-catalog)

## Workspace Management

### CreateWorkspace - Create Workspace

**Method**: POST `/api/v1/workspaces`

**Request Parameters (Body)**:

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| workspaceName | string | Yes | Workspace name |
| ossBucket | string | Yes | OSS Bucket path (e.g., `oss://my-bucket`) |
| ramRoleName | string | Yes | RAM role name, fixed value `AliyunEMRSparkJobRunDefaultRole` (need to authorize beforehand, also need to grant service-linked role `AliyunServiceRoleForEMRServerlessSpark`) |
| paymentType | string | Yes | Payment type: `PayAsYouGo` (pay-as-you-go) or `Subscription` (annual/monthly subscription) |
| resourceSpec | object | Yes | Resource specification |
| └─ cu | integer | Yes | Compute resource limit (CU) |
| clientToken | string | No | Idempotency token, prevent duplicate submission |
| dlfCatalogId | string | No | DLF data catalog ID |
| autoPayOrder | boolean | No | Whether to auto-pay order (Subscription mode) |
| resourceGroupId | string | No | Resource group ID |

**Example**:

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "workspaceName": "my-workspace",
    "ossBucket": "oss://my-spark-bucket",
    "ramRoleName": "AliyunEMRSparkJobRunDefaultRole",
    "paymentType": "PayAsYouGo",
    "resourceSpec": {"cu": 8}
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

### ListWorkspaces - Query Workspace List

**Method**: GET `/api/v1/workspaces`

**Request Parameters (Query)**:

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| regionId | string | No | Region ID |
| nextToken | string | No | Pagination token |
| maxResults | integer | No | Max results per page |
| name | string | No | Filter by workspace name |
| state | string | No | Filter by status |
| resourceGroupId | string | No | Filter by resource group ID |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

### ListWorkspaceQueues - Query Resource Queues

**Method**: GET `/api/v1/workspaces/{workspaceId}/queues`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| regionId | string | No | query | Region ID |
| environment | string | No | query | Environment type (e.g., dev / production) |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/queues --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

### EditWorkspaceQueue - Modify Resource Queue

**Method**: POST `/api/v1/workspaces/queues/action/edit`

**Request Parameters (Body)**:

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| workspaceId | string | Yes | Workspace ID |
| workspaceQueueName | string | Yes | Queue name |
| resourceSpec | object | Yes | Resource specification |
| └─ cu | integer | No | Queue resource limit (CU) |
| └─ maxCu | integer | No | Queue elastic max CU |
| regionId | string | No | Region ID |
| environments | array | No | Queue environment types (e.g., dev / production) |

**Example**:

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces/queues/action/edit?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{"workspaceId":"w-xxx","workspaceQueueName":"dev_queue","resourceSpec":{"cu":32,"maxCu":64}}' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

## Job Management

### StartJobRun - Submit Job

**Method**: POST `/api/v1/workspaces/{workspaceId}/jobRuns`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| jobDriver | object | Yes | body | Job driver configuration |
| └─ sparkSubmit | object | Yes | | Spark Submit configuration |
| 　└─ entryPoint | string | Yes | | Main program path (OSS or local) |
| 　└─ entryPointArguments | array | No | | Main program argument list |
| 　└─ sparkSubmitParameters | string | No | | Spark Submit command line parameters |
| configurationOverrides | object | No | body | Configuration overrides |
| └─ configurations | array | No | | Configuration item list |
| 　└─ configFileName | string | No | | Configuration file name |
| 　└─ configItemKey | string | No | | Configuration item key |
| 　└─ configItemValue | string | No | | Configuration item value |
| releaseVersion | string | No | body | Spark engine version |
| name | string | Yes | body | Job name (required, not passing will report MissingParameter error) |
| codeType | string | Yes | body | Code type: JAR / PYTHON / SQL (not passing will cause server error) |
| tags | array | No | body | Job tags, format: `[{"key":"k","value":"v"}]` |
| resourceQueueId | string | Yes | body | Resource queue ID (not passing will report `queueName: null is not valid` error, get via ListWorkspaceQueues) |
| fusion | boolean | No | body | Whether to enable Fusion engine acceleration |
| executionTimeoutSeconds | integer | No | body | Job execution timeout (seconds) |
| clientToken | string | No | body | Idempotency token, prevent duplicate submission |

**Example**:

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces/w-xxx/jobRuns?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "my-job",
    "jobDriver": {
      "sparkSubmit": {
        "entryPoint": "oss://bucket/app.jar",
        "entryPointArguments": ["arg1"],
        "sparkSubmitParameters": "--class com.example.Main --conf spark.executor.instances=2"
      }
    },
    "codeType": "JAR",
    "resourceQueueId": "root_queue",
    "releaseVersion": "esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)"
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

### GetJobRun - Query Job Details

**Method**: GET `/api/v1/workspaces/{workspaceId}/jobRuns/{jobRunId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| jobRunId | string | Yes | path | Job run ID |
| regionId | string | No | query | Region ID |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/jobRuns/jr-xxx --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

### ListJobRuns - Query Job List

**Method**: GET `/api/v1/workspaces/{workspaceId}/jobRuns`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| nextToken | string | No | query | Pagination token |
| maxResults | integer | No | query | Max results per page |
| jobRunId | string | No | query | Filter by job run ID |
| name | string | No | query | Filter by job name |
| creator | string | No | query | Filter by creator |
| state | string | No | query | Filter by status |
| startTime | string | No | query | Start time filter |
| endTime | string | No | query | End time filter |
| resourceQueueId | string | No | query | Filter by resource queue ID |
| tags | string | No | query | Filter by tags |
| regionId | string | No | query | Region ID |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/jobRuns --region cn-hangzhou --maxResults 20 --force --user-agent AlibabaCloud-Agent-Skills
```

---

### CancelJobRun - Cancel Job

**Method**: DELETE `/api/v1/workspaces/{workspaceId}/jobRuns/{jobRunId}`

⚠️ **Destructive Operation**: Abort running job, completed compute results may be lost.

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| jobRunId | string | Yes | path | Job run ID |
| regionId | string | No | query | Region ID |

**Example**:

```bash
aliyun emr-serverless-spark DELETE "/api/v1/workspaces/w-xxx/jobRuns/jr-xxx?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

### ListLogContents - Query Job Logs

**Method**: GET `/api/v1/workspaces/{workspaceId}/action/listLogContents`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| fileName | string | Yes | query | Log file full path name (OSS path) |
| offset | integer | Yes | query | Query start row (not passing will cause server error), recommend passing 0 |
| length | integer | Yes | query | Log length (not passing will cause server error), recommend passing 9999 |
| regionId | string | No | query | Region ID |

> **Note**: fileName can be obtained from the `log` field in GetJobRun response, format like:
> `oss://my-bucket/w-xxx/spark/logs/jr-xxx/driver/stdout.log`
>
> **Supported OSS Path Formats**:
> - `oss://bucket/path` (standard format, recommended)
> - `oss://bucket.oss-cn-hangzhou.aliyuncs.com/path` (external endpoint)
> - `oss://bucket.oss-cn-hangzhou-internal.aliyuncs.com/path` (internal endpoint)
> - `oss://bucket.cn-hangzhou.oss-dls.aliyuncs.com/path` (DLS endpoint, can use directly when GetJobRun returns this format)
>
> **Not Supported**: CNAME domain format

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/action/listLogContents \
  --region cn-hangzhou \
  --fileName 'oss://my-bucket/w-xxx/spark/logs/jr-xxx/driver/stdout.log' \
  --offset 0 --length 9999 \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

### GetCuHours - Query Queue CU Consumption

**Method**: GET `/api/v1/workspaces/{workspaceId}/metric/cuHours/{queue}`

> **Note**: This API queries CU consumption by **resource queue** dimension, not by individual job.

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| queue | string | Yes | path | Queue name (e.g., root_queue, dev_queue) |
| startTime | string | Yes | query | Query start time, format: `YYYY-MM-DD HH:mm:ss` |
| endTime | string | Yes | query | Query end time, format: `YYYY-MM-DD HH:mm:ss` |

> **Constraint**: Query time span cannot exceed **1 month**, otherwise server returns `Invalid Parameters: Query interval over one month not allowed!`.

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/metric/cuHours/root_queue \
  --region cn-hangzhou \
  --startTime '2024-01-01 00:00:00' --endTime '2024-01-08 00:00:00' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

### GetRunConfiguration - Query Job Configuration

**Method**: GET `/api/v1/workspaces/{workspaceId}/runs/{runId}/action/getRunConfiguration`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| runId | string | Yes | path | Run task ID (i.e., jobRunId) |
| regionId | string | No | query | Region ID |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/runs/jr-xxx/action/getRunConfiguration --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

### ListJobExecutors - Query Executor Information

**Method**: GET `/api/v1/workspaces/{workspaceId}/jobRuns/{jobRunId}/executors`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| jobRunId | string | Yes | path | Job run ID |
| regionId | string | No | query | Region ID |
| nextToken | string | No | query | Pagination token |
| maxResults | integer | No | query | Max results per page |
| status | string | No | query | Filter by Executor status |
| executorType | string | No | query | Filter by Executor type |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/jobRuns/jr-xxx/executors --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

## Session Cluster

### CreateSessionCluster - Create Session Cluster

**Method**: POST `/api/v1/workspaces/{workspaceId}/sessionClusters`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| name | string | No | body | Session name |
| queueName | string | No | body | Queue name |
| releaseVersion | string | No | body | Spark engine version number |
| kind | string | No | body | Session type, default SQL |
| applicationConfigs | array | No | body | Spark application configuration |
| autoStartConfiguration | object | No | body | Auto start configuration |
| autoStopConfiguration | object | No | body | Auto stop configuration |
| └─ enable | boolean | No | | Whether to enable |
| └─ idleTimeoutMinutes | integer | No | | Idle timeout minutes |
| fusion | boolean | No | body | Whether to enable Fusion engine acceleration |
| publicEndpointEnabled | boolean | No | body | Whether to enable public endpoint |
| clientToken | string | No | body | Idempotency token |

**Example**:

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces/w-xxx/sessionClusters?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{"name":"my-session","queueName":"default","kind":"SQL"}' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

### GetSessionCluster - Query Session Cluster Details

**Method**: GET `/api/v1/workspaces/{workspaceId}/sessionClusters/{sessionClusterId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| sessionClusterId | string | Yes | path | Session cluster ID |
| regionId | string | No | query | Region ID |

---

### ListSessionClusters - Query Session Cluster List

**Method**: GET `/api/v1/workspaces/{workspaceId}/sessionClusters`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| sessionClusterId | string | No | query | Filter by session ID |
| queueName | string | No | query | Filter by queue name |
| kind | string | No | query | Filter by session type |
| nextToken | string | No | query | Pagination token |
| maxResults | integer | No | query | Max results per page |
| regionId | string | No | query | Region ID |

---

### StartSessionCluster - Start Session Cluster

**Method**: POST `/api/v1/workspaces/{workspaceId}/sessionClusters/action/startSessionCluster`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| sessionClusterId | string | No | body | Session cluster ID |
| queueName | string | No | body | Queue name |

---

### StopSessionCluster - Stop Session Cluster

**Method**: POST `/api/v1/workspaces/{workspaceId}/sessionClusters/action/stopSessionCluster`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| sessionClusterId | string | No | body | Session cluster ID |
| queueName | string | No | body | Queue name |

---

### DeleteSessionCluster - Delete Session Cluster

**Method**: DELETE `/api/v1/workspaces/{workspaceId}/sessionClusters/{sessionClusterId}`

⚠️ **Destructive Operation**: Irreversible, session cluster will be permanently deleted.

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| sessionClusterId | string | Yes | path | Session cluster ID |
| regionId | string | No | query | Region ID (URL append `?regionId=cn-hangzhou`) |

**Example**:

```bash
aliyun emr-serverless-spark DELETE "/api/v1/workspaces/w-xxx/sessionClusters/sc-xxx?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

## SQL Statement

### CreateSqlStatement - Submit SQL Query

**Method**: PUT `/api/interactive/v1/workspace/{workspaceId}/statement`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| codeContent | string | Yes | body | SQL code (supports one or more SQL statements) |
| sqlComputeId | string | Yes | body | SQL session ID (create in workspace session management) |
| defaultDatabase | string | No | body | Default database name |
| defaultCatalog | string | No | body | Default DLF Catalog ID |
| limit | integer | No | body | Result row limit, 1-10000, default 1000 |
| taskBizId | string | No | body | Task business ID |
| regionId | string | No | query | Region ID |

**Example**:

```bash
aliyun emr-serverless-spark PUT "/api/interactive/v1/workspace/w-xxx/statement?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{"sqlComputeId":"sc-xxx","codeContent":"SHOW TABLES","defaultDatabase":"default"}' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

### GetSqlStatement - Query SQL Execution Status

**Method**: GET `/api/interactive/v1/workspace/{workspaceId}/statement/{statementId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| statementId | string | Yes | path | Interactive query ID |
| regionId | string | No | query | Region ID |

**Status Values**: waiting / running / available / error

**Example**:

```bash
aliyun emr-serverless-spark GET /api/interactive/v1/workspace/w-xxx/statement/st-xxx --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

### TerminateSqlStatement - Terminate SQL Query

**Method**: POST `/api/interactive/v1/workspace/{workspaceId}/statement/{statementId}/terminate`

⚠️ **Destructive Operation**: Terminate executing SQL query.

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| statementId | string | Yes | path | Interactive query ID |
| regionId | string | No | query | Region ID |

**Example**:

```bash
aliyun emr-serverless-spark POST "/api/interactive/v1/workspace/w-xxx/statement/st-xxx/terminate?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

### ListSqlStatementContents - Query SQL Execution Results

**Method**: GET `/api/v1/workspaces/{workspaceId}/action/listSqlStatementContents`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| fileName | string | Yes | query | Result file full path name (OSS path) |
| nextToken | string | No | query | Pagination token |
| maxResults | integer | No | query | Max results per page, default 2000 |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/action/listSqlStatementContents \
  --region cn-hangzhou \
  --fileName 'oss://bucket/w-xxx/spark/logs/jr-xxx/driver/st-xxx' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

## Kyuubi Service

### CreateKyuubiService - Create Kyuubi Service

**Method**: POST `/api/v1/kyuubi/{workspaceId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| name | string | No | body | Service name |
| queue | string | No | body | Run queue |
| releaseVersion | string | No | body | Spark engine version |
| computeInstance | string | No | body | Service specification |
| publicEndpointEnabled | boolean | No | body | Whether to enable public network access, default false |
| replica | integer | No | body | High availability replica count |
| kyuubiConfigs | string | No | body | Kyuubi configuration |
| sparkConfigs | string | No | body | Spark configuration |
| kyuubiReleaseVersion | string | No | body | Kyuubi engine version |

**Example**:

```bash
aliyun emr-serverless-spark POST "/api/v1/kyuubi/w-xxx?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{"name":"my-kyuubi","queue":"default","releaseVersion":"esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)"}' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

---

### GetKyuubiService - Query Kyuubi Service Details

**Method**: GET `/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| regionId | string | No | query | Region ID |

---

### ListKyuubiServices - Query Kyuubi Service List

**Method**: GET `/api/v1/kyuubi/{workspaceId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| regionId | string | No | query | Region ID |

---

### StartKyuubiService - Start Kyuubi Service

**Method**: POST `/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/start`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| regionId | string | No | query | Region ID (URL append `?regionId=cn-hangzhou`) |

---

### StopKyuubiService - Stop Kyuubi Service

**Method**: POST `/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/stop`

⚠️ **Destructive Operation**: All active JDBC connections will be disconnected.

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| regionId | string | No | query | Region ID (URL append `?regionId=cn-hangzhou`) |

---

### UpdateKyuubiService - Modify Kyuubi Service

**Method**: PUT `/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| name | string | Yes | body | Name (server constraint cannot be empty) |
| queue | string | Yes | body | Run queue (server constraint cannot be empty) |
| releaseVersion | string | No | body | Spark engine version number |
| computeInstance | string | No | body | Service specification |
| publicEndpointEnabled | boolean | No | body | Whether to enable public network access |
| replica | integer | No | body | High availability replica count |
| kyuubiConfigs | string | No | body | Kyuubi configuration |
| sparkConfigs | string | No | body | Spark configuration |
| kyuubiReleaseVersion | string | No | body | Kyuubi engine version |
| restart | boolean | No | body | Whether to restart |

---

### DeleteKyuubiService - Delete Kyuubi Service

**Method**: DELETE `/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}`

⚠️ **Destructive Operation**: Irreversible, Kyuubi service will be permanently deleted.

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| regionId | string | No | query | Region ID (URL append `?regionId=cn-hangzhou`) |

---

## Kyuubi Token

### CreateKyuubiToken - Create Token

**Method**: POST `/api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| name | string | No | body | Token name |
| token | string | Yes | body | Token content (>= 32 characters) |
| autoExpireConfiguration | object | No | body | Auto expire configuration |
| memberArns | array | No | body | Authorized user ARN list |

---

### GetKyuubiToken - Query Token Details

**Method**: GET `/api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token/{tokenId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| tokenId | string | Yes | path | Token ID |
| regionId | string | No | query | Region ID |

---

### ListKyuubiToken - Query Token List

**Method**: GET `/api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| regionId | string | No | query | Region ID |

---

### UpdateKyuubiToken - Modify Token

**Method**: PUT `/api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token/{tokenId}`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| tokenId | string | Yes | path | Token ID |
| name | string | No | body | Token name |
| token | string | No | body | Token content |
| autoExpireConfiguration | object | No | body | Auto expire configuration |
| memberArns | array | No | body | Authorized user ARN list |

---

### DeleteKyuubiToken - Delete Token

**Method**: DELETE `/api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token/{tokenId}`

⚠️ **Destructive Operation**: After deletion, connections using this Token will fail authentication.

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| tokenId | string | Yes | path | Token ID |
| regionId | string | No | query | Region ID |

---

## Kyuubi Application

### ListKyuubiSparkApplications - Query Kyuubi Application List

**Method**: GET `/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/applications`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| nextToken | string | No | query | Pagination token |
| maxResults | integer | No | query | Max results per page |
| applicationId | string | No | query | Filter by application ID |
| applicationName | string | No | query | Filter by application name |
| resourceQueueId | string | No | query | Filter by queue ID |
| minDuration | integer | No | query | Min runtime filter |

---

### CancelKyuubiSparkApplication - Cancel Kyuubi Application

**Method**: DELETE `/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/application/{applicationId}`

⚠️ **Destructive Operation**: Abort running Spark query.

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| kyuubiServiceId | string | Yes | path | Kyuubi service ID |
| applicationId | string | Yes | path | Spark application ID |
| regionId | string | No | query | Region ID (URL append `?regionId=cn-hangzhou`) |

---

## Permission Management

### AddMembers - Add Members

**Method**: POST `/api/v1/auth/members`

**Request Parameters (Body)**:

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| workspaceId | string | Yes | Workspace ID |
| memberArns | array | Yes | RAM user/role ARN list |

---

### ListMembers - Query Member List

**Method**: GET `/api/v1/auth/{workspaceId}/members`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| nextToken | string | No | query | Pagination token |
| maxResults | integer | No | query | Max results per page |

---

### GrantRoleToUsers - Grant Role

**Method**: POST `/api/v1/auth/roles/grant`

**Request Parameters (Body)**:

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| roleArn | string | Yes | Role ARN, format: `acs:emr::{workspaceId}:role/{roleName}` (e.g., `acs:emr::w-xxx:role/Owner`) |
| userArns | array | Yes | User ARN list, format: `acs:emr::{workspaceId}:member/{userId}` (get from ListMembers) |

---

## Version Management

### ListReleaseVersions - Query Engine Versions

**Method**: GET `/api/v1/releaseVersions`

**Request Parameters (Query)**:

| Parameter Name | Type | Required | Description |
|----------------|------|----------|-------------|
| regionId | string | No | Region ID |
| releaseVersion | string | No | Filter by version number |
| releaseVersionStatus | string | No | Filter by version status |
| releaseType | string | No | Filter by release type |
| workspaceId | string | No | Filter by workspace ID |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/releaseVersions --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

## Data Catalog

### ListCatalogs - Query Data Catalog List

**Method**: GET `/api/v1/workspaces/{workspaceId}/catalogs`

**Request Parameters**:

| Parameter Name | Type | Required | Location | Description |
|----------------|------|----------|----------|-------------|
| workspaceId | string | Yes | path | Workspace ID |
| environment | string | No | query | Environment type (dev / production) |
| regionId | string | No | query | Region ID |

**Example**:

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/w-xxx/catalogs --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

---

## Related Documentation

- [Getting Started](getting-started.md) - First-time workspace creation and job submission
- [Workspace Lifecycle](workspace-lifecycle.md) - Create, query, manage workspaces
- [Job Management](job-management.md) - Submit, monitor, diagnose Spark jobs
- [Kyuubi Service](kyuubi-service.md) - Interactive SQL gateway management
- [Scaling Guide](scaling.md) - Resource queue scaling