# MMS OpenAPI & CLI Commands

MMS 通过 MaxCompute OpenAPI（产品代码 `MaxCompute`，版本 `2022-01-04`）提供 API 能力。
CLI 调用格式：`aliyun maxcompute <command> [params] --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service`

## 数据源管理

### ListMmsDataSources — 列出数据源

```bash
aliyun maxcompute list-mms-data-sources \
  --name <name> \
  --type <Hive|BigQuery|Snowflake|Redshift|Databricks|MaxCompute> \
  --region <region> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

| 参数 | 类型 | 说明 |
|------|------|------|
| name | string | 按名称过滤 |
| type | string | 按数据源类型过滤 |
| region | string | 按地域过滤 |
| pageNum | integer | 页码 |
| pageSize | integer | 每页条数 |

### GetMmsDataSource — 获取数据源详情

```bash
aliyun maxcompute get-mms-data-source \
  --source-id <sourceId> \
  --with-config true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### 创建/更新/删除数据源

> **[MUST] 数据源的创建、更新、删除操作，引导用户到控制台完成。**
> 控制台地址：`https://maxcompute.console.aliyun.com/{region}/mma/datasource`

## 元数据扫描（盘点）

### CreateMmsFetchMetadataJob — 发起元数据盘点

```bash
aliyun maxcompute create-mms-fetch-metadata-job \
  --source-id <sourceId> \
  --body '{ ... }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### GetMmsFetchMetadataJob — 查看盘点状态

```bash
aliyun maxcompute get-mms-fetch-metadata-job \
  --source-id <sourceId> \
  --scan-id <scanId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

## 元数据管理

### ListMmsDbs — 列出数据库

```bash
aliyun maxcompute list-mms-dbs \
  --source-id <sourceId> \
  --name <name> \
  --status <status> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### GetMmsDb — 获取数据库详情

```bash
aliyun maxcompute get-mms-db \
  --source-id <sourceId> \
  --db-id <dbId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### ListMmsTables — 列出表

```bash
aliyun maxcompute list-mms-tables \
  --source-id <sourceId> \
  --db-name <dbName> \
  --name <name> \
  --status <status> \
  --has-partitions true \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

| 参数 | 类型 | 说明 |
|------|------|------|
| dbId | integer | 按数据库 ID 过滤 |
| dbName | string | 按数据库名过滤 |
| name | string | 按表名过滤 |
| dstProjectName | string | 按目标项目名过滤 |
| dstSchemaName | string | 按目标 Schema 过滤 |
| type | string | 按表类型过滤 |
| hasPartitions | boolean | 是否有分区 |
| status | array | 按状态过滤 |

### GetMmsTable — 获取表详情

```bash
aliyun maxcompute get-mms-table \
  --source-id <sourceId> \
  --table-id <tableId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### ListMmsPartitions — 列出分区

```bash
aliyun maxcompute list-mms-partitions \
  --source-id <sourceId> \
  --db-name <dbName> \
  --table-name <tableName> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### GetMmsPartition — 获取分区详情

```bash
aliyun maxcompute get-mms-partition \
  --source-id <sourceId> \
  --partition-id <partitionId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

## 迁移作业管理

### CreateMmsJob — 创建迁移作业

```bash
aliyun maxcompute create-mms-job \
  --source-id <sourceId> \
  --body '{ "name": "job_name", "srcDbName": "db_name", ... }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

> **创建后自动开始执行**，无需手动调用 StartMmsJob。

### ListMmsJobs — 列出迁移作业

```bash
aliyun maxcompute list-mms-jobs \
  --source-id <sourceId> \
  --name <name> \
  --src-db-name <srcDbName> \
  --status <status> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

| 参数 | 类型 | 说明 |
|------|------|------|
| name | string | 按作业名过滤 |
| srcDbName | string | 按源数据库名过滤 |
| srcTableName | string | 按源表名过滤 |
| status | string | 按状态过滤 |
| stopped | integer | 是否已停止 |
| timerId | integer | 按定时器 ID 过滤 |

### GetMmsJob — 获取迁移作业详情

```bash
aliyun maxcompute get-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### StartMmsJob — 启动/恢复迁移作业

```bash
aliyun maxcompute start-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

> 仅用于恢复被 StopMmsJob 停止的作业。

### StopMmsJob — 停止迁移作业

```bash
aliyun maxcompute stop-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### RetryMmsJob — 重试迁移作业

```bash
aliyun maxcompute retry-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### DeleteMmsJob — 删除迁移作业

```bash
aliyun maxcompute delete-mms-job \
  --source-id <sourceId> \
  --job-id <jobId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

## 迁移任务管理

### ListMmsTasks — 列出迁移任务

```bash
aliyun maxcompute list-mms-tasks \
  --source-id <sourceId> \
  --job-id <jobId> \
  --status <status> \
  --src-table-name <srcTableName> \
  --page-num 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

| 参数 | 类型 | 说明 |
|------|------|------|
| jobId | integer | 按作业 ID 过滤 |
| jobName | string | 按作业名过滤 |
| srcDbName | string | 按源数据库名过滤 |
| srcTableName | string | 按源表名过滤 |
| status | string | 按状态过滤 |
| partition | string | 按分区过滤 |

### GetMmsTask — 获取迁移任务详情

```bash
aliyun maxcompute get-mms-task \
  --source-id <sourceId> \
  --task-id <taskId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### ListMmsTaskLogs — 查看迁移任务日志

```bash
aliyun maxcompute list-mms-task-logs \
  --source-id <sourceId> \
  --task-id <taskId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

## 异步任务

### GetMmsAsyncTask — 查看异步任务状态

```bash
aliyun maxcompute get-mms-async-task \
  --source-id <sourceId> \
  --async-task-id <asyncTaskId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

## API 概览

| API | Method | Path | 说明 |
|-----|--------|------|------|
| ListMmsDataSources | GET | /api/v1/mms/datasources | 列出数据源 |
| GetMmsDataSource | GET | /api/v1/mms/datasources/{sourceId} | 获取数据源详情 |
| CreateMmsDataSource | - | - | **引导用户到控制台创建** |
| UpdateMmsDataSource | - | - | **引导用户到控制台更新** |
| DeleteMmsDataSource | - | - | **引导用户到控制台删除** |
| CreateMmsFetchMetadataJob | POST | /api/v1/mms/datasources/{sourceId}/scans | 发起元数据盘点 |
| GetMmsFetchMetadataJob | GET | /api/v1/mms/datasources/{sourceId}/scans/{scanId} | 查看盘点状态 |
| ListMmsDbs | GET | /api/v1/mms/datasources/{sourceId}/dbs | 列出数据库 |
| GetMmsDb | GET | /api/v1/mms/datasources/{sourceId}/dbs/{dbId} | 获取数据库详情 |
| ListMmsTables | GET | /api/v1/mms/datasources/{sourceId}/tables | 列出表 |
| GetMmsTable | GET | /api/v1/mms/datasources/{sourceId}/tables/{tableId} | 获取表详情 |
| ListMmsPartitions | GET | /api/v1/mms/datasources/{sourceId}/partitions | 列出分区 |
| GetMmsPartition | GET | /api/v1/mms/datasources/{sourceId}/partitions/{partitionId} | 获取分区详情 |
| CreateMmsJob | POST | /api/v1/mms/datasources/{sourceId}/jobs | 创建迁移作业 |
| ListMmsJobs | GET | /api/v1/mms/datasources/{sourceId}/jobs | 列出迁移作业 |
| GetMmsJob | GET | /api/v1/mms/datasources/{sourceId}/jobs/{jobId} | 获取作业详情 |
| StartMmsJob | POST | /api/v1/mms/datasources/{sourceId}/jobs/{jobId}/start | 启动作业 |
| StopMmsJob | POST | /api/v1/mms/datasources/{sourceId}/jobs/{jobId}/stop | 停止作业 |
| RetryMmsJob | POST | /api/v1/mms/datasources/{sourceId}/jobs/{jobId}/retry | 重试作业 |
| DeleteMmsJob | POST | /api/v1/mms/datasources/{sourceId}/jobs/{jobId} | 删除作业 |
| ListMmsTasks | GET | /api/v1/mms/datasources/{sourceId}/tasks | 列出迁移任务 |
| GetMmsTask | GET | /api/v1/mms/datasources/{sourceId}/tasks/{taskId} | 获取任务详情 |
| ListMmsTaskLogs | GET | /api/v1/mms/datasources/{sourceId}/tasks/{taskId}/logs | 查看任务日志 |
| GetMmsAsyncTask | GET | /api/v1/mms/datasources/{sourceId}/asyncTasks/{asyncTaskId} | 查看异步任务 |
