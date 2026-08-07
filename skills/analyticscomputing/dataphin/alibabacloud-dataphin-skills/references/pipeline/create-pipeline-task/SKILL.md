---
name: create-pipeline-task
description: |-
  通过 CLI 创建集成管道任务（数据同步/数据搬运/ETL pipeline）。 触发场景：创建数据集成任务 / 数据同步任务 / 管道任务 / pipeline / 数据搬运 / reader-writer 配置 / MySQL→MaxCompute / Doris→PostgreSQL / 离线集成 / create-pipeline / update-pipeline / create-pipeline-node。 覆盖两条路径：两步法（create-pipeline-node 建草稿 → update-pipeline 填配置提交） 和 一步法（create-pipeline）。 关键坑：PluginConfig 必须是 JSON 字符串；columnMappings 顺序敏感且必填；空 PluginConfig 触发 ClassCastException。 触发词：创建管道任务、数据同步、数据集成、数据搬运、pipeline、create-pipeline、update-pipeline、reader writer、PluginConfig、MySQL→MaxCompute、Doris→PostgreSQL。
---
# 新建集成管道任务 skill

## 适用场景

- 通过 CLI 创建一个**离线集成管道任务**（offline pipeline / 实时 / 工作流同理）
- 典型链路：reader (MySQL/Oracle/Doris/...) → writer (MaxCompute/Hive/PostgreSQL/...) 一对一搬运

> 💡 **术语**：ODPS（Open Data Processing Service）是 MaxCompute 的旧名称，在 pipeline PluginConfig、API 参数中仍可能出现 `odps` 字样，均指 MaxCompute。
- 需要把 Steps（reader/writer 插件配置）、Hops（DAG 边）、调度 + 资源 settings 一次性提交

## 两条 CLI 路径

| 路径 | 命令组合 | 适用 |
|---|---|---|
| **A. 两步法**（推荐） | `dev create-pipeline-node`（建空草稿） → `dev update-pipeline`（填配置 + 提交） | 想分阶段：先占名/占目录，再慢慢调试 Steps |
| **B. 一步法** | `dev create-pipeline`（直接带完整 config 创建并提交） | 配置已稳定、CI 化场景 |

> 共同点：两条路径最终落库的 `pipelineDTO.steps[].pluginConfig` 结构完全相同；本 skill 的 PluginConfig 参考片段对两者通用。

---

## 通用顶层参数

```text
--tenant-id <租户ID>     必填（profile 已配置可省）；多租户共享 endpoint 时必须显式传项目所属租户，否则报 DPN.Filter.ProjectNotFound
--project-id   <项目ID>     必填（profile 已配置可省）
--env          DEV|PROD     仅 update-pipeline / create-pipeline 需要；create-pipeline-node 不需要
```

---

## 路径 A：两步法

### A-1. 创建空草稿

```bash
aliyun dataphin-public create-pipeline-node \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --pipeline-name <task-name> \
  --pipeline-type OFFLINE_PIPELINE \
  --node-type NORMAL \
  --file-info '{"FileName":"<task-name>","Directory":"/"}'
```

返回：

```jsonc
{
  "Data": {
    "PipelineId": <int>,   // 记下来，下一步要用
    "SubmitId": null,
    "Version": null,
    "NodeId": null
  },
  "Code": "OK", "Success": true
}
```

| 参数 | 说明 |
|---|---|
| `--pipeline-type` | `OFFLINE_PIPELINE` / `REAL_TIME_PIPELINE` |
| `--node-type` | `NORMAL` / `MANUAL` / `REAL_TIME` |
| `FileInfo.Directory` | 默认 `/`；非 `/` 必须先存在（否则报错） |

### A-2. 填充 Steps/Hops 并提交

```bash
aliyun dataphin-public update-pipeline \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --node-info '{"NodeName":"<task-name>","PipelineId":<上一步PipelineId>}' \
  --pipeline-config '<见下方 JSON>' \
  --schedule-config '<见下方 JSON>' \
  --settings '<见下方 JSON>' \
  --submit
```

---

## 路径 B：一步法

```bash
aliyun dataphin-public create-pipeline \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --pipeline-type 0 \
  --mode PIPELINE \
  --node-info '{"NodeName":"<task-name>","Directory":"/"}' \
  --pipeline-config '<见下方 JSON>' \
  --schedule-config '<见下方 JSON>' \
  --settings '<见下方 JSON>' \
  --submit
```

`--pipeline-type` 取值：`0` = 离线集成（默认） / `1` = 实时 / `14` = 工作流。

---

## `--pipeline-config` 完整骨架

pipeline-config 是集成任务最复杂的字段（含 reader/writer/transformer/column 映射），按 reader/writer 类型组合的完整骨架抽离到独立 reference：

> 📖 详见 [references/pipeline-config.md](references/pipeline-config.md)（涵盖 MySQL→MaxCompute / Doris→PG / Oracle→Hive 等常用组合）

关键规则速查：
- **CLI 的 autocreate 不生效**：目标表必须手动预建
- **类型映射陷阱**：Doris LARGEINT→PG NUMERIC、Doris TINYINT→PG SMALLINT
- **column 顺序**：reader.column 与 writer.column 必须一一对应、长度一致

## `--schedule-config` 完整骨架

```jsonc
{
  "ScheduleType": "NORMAL",
  "CronExpression": "0 0 0 * * ?",          // ⚠ 字段名是 CronExpression，不是 ScheduleCron
  "ScheduleStartTime": "1970-01-01 00:00:00",
  "ScheduleEndTime":   "9999-01-01 00:00:00",
  "ScheduleIntervalType": "DAILY",          // DAILY/HOURLY/WEEKLY/MONTHLY/CRON
  "ReRunMode": "ALL_ALLOWED",               // ALL_DENIED | FAILURE_ALLOWED | ALL_ALLOWED
  "NodeStatus": 1,                          // 1 正常 / 2 暂停 / 3 空跑
  "Priority": 5,                            // 1~9
  "ResourceGroupId": "default",
  "DevResourceGroupId": "default",
  "ExecuteTimeOutConfig":  { "FollowSystem": true },
  "ExecuteRerunConfig":    { "FollowSystem": true },
  "UpStreamList": [
    {
      "NodeType": "PHYSICAL",
      "SourceNodeId": "<上游节点ID>",
      "SourceNodeOutputName": "<上游输出名>",
      "PeriodDiff": 0
    }
    // 缺省上游时使用租户虚拟根节点 virtual_root_node_<DagId 数字>
    // 详见 ../../dev/find-tenant-root-node/SKILL.md
  ],
  "NodeOutputNameList": ["<本任务输出名，UUID 或 project.table>"]
}
```

## `--settings` 完整骨架

```jsonc
{
  "RequiredResource": { "Cpus": 0.5, "MemoryInMb": 1024 },
  "JvmOption": "",
  "NoFlowTimeout": 30,
  "Engine": { "Name": "dlink" },
  "ErrorLimit": { "Record": 0 },             // 脏数据上限
  "TimeZone": "Asia/Shanghai",
  "SqlTimeout": 30,
  "Speed": { "Concurrent": 3 },              // 并发数
  "ConnectRetryTime": [
    { "RetryTimes": 1, "DsId": "<reader 数据源ID>" }
  ]
}
```

---

## 校验

```bash
# 用 PipelineId 查
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --pipeline-id <pipelineId>
```

只建草稿没填 Steps 时，`Data` 可能为 `null`（预期）；填好 Steps 后再查应返回完整 `Steps` / `Hops` / `Settings`。

---

## 常见坑

1. **`PluginConfig` 必须是 JSON 字符串**：CLI 不会递归序列化嵌套对象。把每个插件 config 用 `JSON.stringify` 转字符串后再放进 `Steps[].PluginConfig`。
2. **空 `PluginConfig: "{}"` 触发 ClassCastException**：服务端反序列化为 `DefaultOutputPluginConfig` 与 `BaseOutputPluginConfig` 类型转换失败。最少要带 `dsName`/`dsId`/`dsType`/`table`/`columns`。
3. **`--tenant-id` 必须与项目所属租户一致**：多租户共享同一 endpoint 时，profile 中的 `tenant_id` 与目标项目的租户可能不同，必须显式传项目租户，否则 `DPN.Filter.ProjectNotFound`。
4. **`columnMappings` 必填且顺序敏感**：MaxCompute writer 必须显式声明每一列的 `sourceColumn → targetColumn`，`inputColumnIndex` 从 0 开始且与 reader `columns` 顺序对齐，否则跑批数据错位。
5. **大整数 ID 字符串化**：`dsId` / `nodeId` / `fileId` 体量超 `Number.MAX_SAFE_INTEGER`（如 `7445807200604583744`）必须以字符串传入，避免 JS JSON.parse 精度丢失。
6. **缺省上游需挂租户虚拟根节点**：`UpStreamList` 不能为空，否则提交时报 `NodeWithoutUpstream`。租户虚拟根节点的查找见 [find-tenant-root-node](../../dev/find-tenant-root-node/SKILL.md)（经套件入口路由加载）。
7. **`Directory` 必须已存在**：默认 `/` 永远存在；自定义目录前需先建好对应类型为 `offlinePipeline` 的目录。
8. **`prodTableNotExistAction: autocreate` 在 CLI 不生效**：`create-pipeline` / `update-pipeline` 走 OpenAPI 路径时会先校验目标表存在（`DPN.Os.TableNotFound`），即使配置了 `autocreate` 也不行。**必须先用 `execute-ad-hoc-task --operator-type MaxCompute_SQL` 执行 DDL 建好目标表**，再提交 pipeline 配置。
9. **`schedule-config` 的 cron 字段名是 `CronExpression`**（不是 `ScheduleCron`），用错会报「调度周期表达式为空」。
10. **查询 MySQL 源表字段用 `execute-ad-hoc-task --operator-type DATABASE_SQL`**：MySQL/Oracle/PostgreSQL/SQLServer 等关系型数据库统一使用 `DATABASE_SQL`，必须同时传 `--data-source-id` 和 `--data-source-schema`。查询结果在 `get-ad-hoc-task-result --sub-task-id 0`（从 **0** 开始）的 `Result` 字段中。
11. **`prodTableDdl` 仅在前端 UI `autocreate` 流程生效**：CLI 场景下仅作为元信息保存，不会自动执行建表。
12. **`get-project-produce-user` 需显式传 `--tenant-id`**：多租户共享 endpoint 时，不传 `--tenant-id` 会报 `DPN.Filter.ProjectNotFound`，即使 profile 中已配置 tenant_id。查生产账号时必须显式加上
13. **自定义目录必须逐级预建**：如需将任务放在 `/cli/pipeline` 目录，必须先 `create-directory /cli`，再 `create-directory /cli/pipeline`，直接传多级目录报 `DPN.Resource.DirectoryNotFound`
14. **目标数据源表必须预建**：即使 PluginConfig 中配了 `prodTableNotExistAction: autocreate`，CLI 场景下也不会自动建表。必须先用 `execute-ad-hoc-task` 在目标数据源上执行 DDL 建好表，再提交 pipeline 配置

---

## 完整示例 1（路径 A，MySQL→MaxCompute 一对一搬运）

```bash
# 0. 查 MySQL 源表字段（DATABASE_SQL 适用于 MySQL/Oracle/PostgreSQL/SQLServer）
TASK_ID=$(aliyun dataphin-public execute-ad-hoc-task \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --operator-type DATABASE_SQL \
  --data-source-id <mysql-ds-id> \
  --data-source-schema <db-name> \
  --code "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns WHERE table_schema='<db>' AND table_name='<table>' ORDER BY ORDINAL_POSITION" \
  --output json | jq -r '.ExecuteResult.TaskId')

# 查结果（sub-task-id 从 0 开始）
aliyun dataphin-public get-ad-hoc-task-result \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --task-id "${TASK_ID}" \
  --sub-task-id 0

# 1. 在 MaxCompute 中预建目标表（⚠ CLI 的 autocreate 不生效，必须手动建表）
aliyun dataphin-public execute-ad-hoc-task \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --operator-type MaxCompute_SQL \
  --code "CREATE TABLE IF NOT EXISTS <table> (<col1> string, <col2> double, ...) PARTITIONED BY (ds string) LIFECYCLE 3600;"

# 2. 建空草稿，记下 PipelineId
PID=$(aliyun dataphin-public create-pipeline-node \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --pipeline-name <task-name> \
  --pipeline-type OFFLINE_PIPELINE \
  --node-type NORMAL \
  --file-info '{"FileName":"<task-name>","Directory":"/"}' \
  --output json | jq -r '.Data.PipelineId')

# 3. 填配置 + 提交
aliyun dataphin-public update-pipeline \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --node-info "{\"NodeName\":\"<task-name>\",\"PipelineId\":${PID}}" \
  --pipeline-config "$(cat pipeline-config.json)" \
  --schedule-config "$(cat schedule-config.json)" \
  --settings "$(cat settings.json)" \
  --submit

# 4. 校验
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --pipeline-id "${PID}"
```

## 完整示例 2（路径 A，Doris→PostgreSQL 一对一搬运）

```bash
# 0. 在 PG 目标数据源上预建目标表（⚠ CLI 的 autocreate 不生效，必须手动建表）
# ⚠ 类型映射注意：Doris LARGEINT→PG NUMERIC，Doris TINYINT→PG SMALLINT
aliyun dataphin-public execute-ad-hoc-task \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --operator-type DATABASE_SQL \
  --data-source-id <pg-ds-id> \
  --data-source-schema <schema-name> \
  --code 'CREATE TABLE IF NOT EXISTS demo02 (
    user_id         NUMERIC         NOT NULL,
    username        VARCHAR(50)     NOT NULL,
    city            VARCHAR(20),
    age             SMALLINT,
    sex             SMALLINT,
    PRIMARY KEY (user_id, username)
  );'

# 1. 建空草稿，记下 PipelineId
PID=$(aliyun dataphin-public create-pipeline-node \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --pipeline-name <task-name> \
  --pipeline-type OFFLINE_PIPELINE \
  --node-type NORMAL \
  --file-info '{"FileName":"<task-name>","Directory":"/"}' \
  --output json | jq -r '.Data.PipelineId')

# 2. 填配置 + 提交（pipeline-config.json 含 dorisinput + postgresqloutput）
aliyun dataphin-public update-pipeline \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --node-info "{\"NodeName\":\"<task-name>\",\"PipelineId\":${PID}}" \
  --pipeline-config "$(cat pipeline-config.json)" \
  --schedule-config "$(cat schedule-config.json)" \
  --settings "$(cat settings.json)" \
  --submit

# 3. 校验
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --pipeline-id "${PID}"
```

> **PostgreSQL 目标端踩坑速查**：
> 1. `schemaName` 必填——PG 有 schema 概念（常见 `public` 或自定义），不传会报表不存在
> 2. 目标表必须手动预建——`prodTableNotExistAction: autocreate` 在 CLI/OpenAPI 场景不生效
> 3. 类型不能照搬源端——Doris `LARGEINT` 在 PG 不存在，需映射为 `NUMERIC`；`TINYINT` 需映射为 `SMALLINT`
> 4. `columnMappings[].originalType` 填 PG 目标类型，不是 Doris 源类型
> 5. PostgreSQL 建表用 `--operator-type DATABASE_SQL`（关系型数据库统一入口），必须同时传 `--data-source-id` 和 `--data-source-schema`
