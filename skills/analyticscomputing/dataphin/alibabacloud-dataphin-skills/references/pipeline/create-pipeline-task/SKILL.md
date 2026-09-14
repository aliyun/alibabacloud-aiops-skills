---
name: create-pipeline-task
description: |-
  通过 CLI 创建集成管道任务（数据同步/数据搬运/ETL pipeline）。 触发场景：创建数据集成任务 / 数据同步任务 / 管道任务 / pipeline / 数据搬运 / reader-writer 配置 / MySQL→MaxCompute / MySQL→Hive / Doris→PostgreSQL / 离线集成 / create-pipeline / update-pipeline / create-pipeline-node。 覆盖两条路径：两步法（create-pipeline-node 建草稿 → update-pipeline 填配置提交） 和 一步法（create-pipeline）。 关键坑：PluginConfig 必须是 JSON 字符串；columnMappings 顺序敏感且必填；Hive 输出 Key 必须是 hadoophiveoutput 不能是 hiveoutput；空 PluginConfig 触发 ClassCastException。 触发词：创建管道任务、数据同步、数据集成、数据搬运、pipeline、create-pipeline、update-pipeline、reader writer、PluginConfig、MySQL→MaxCompute、MySQL→Hive、Doris→PostgreSQL。
---
# 新建集成管道任务 skill

调用 CLI / SDK 前，继承[父技能 §7](../../../SKILL.md#7-observability) 初始化的 session-id 与套件 `references/manifest.json` 中的 `version`；直接加载时先完成父层初始化。API 命令统一附带 `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"`，使用父技能名称与同一会话、版本。

## 适用场景

- 通过 CLI 创建一个**离线集成管道任务**（offline pipeline / 实时 / 工作流同理）
- 典型链路：reader (MySQL/Oracle/Doris/Hive/...) → writer (MaxCompute/Hive/PostgreSQL/...) 一对一搬运

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
--env          DEV|PROD     create-pipeline 用（必填）；create-pipeline-node 不需要
--context      Env+ProjectId  update-pipeline 专用（必填），格式 --context 'Env=DEV ProjectId=<项目ID>'；update-pipeline 无 --env 参数
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
  --context 'Env=DEV ProjectId=<project-id>' \
  --node-info '{"NodeName":"<task-name>","PipelineId":<上一步PipelineId>}' \
  --pipeline-config '<见下方 JSON>' \
  --schedule-config '<见下方 JSON>' \
  --settings '<见下方 JSON>' \
  --submit=true
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

> 📖 详见 [references/pipeline-config.md](references/pipeline-config.md)（涵盖 MySQL reader / MaxCompute writer / Hive writer / Doris reader / PostgreSQL writer 及 MySQL→Hive、MySQL→MaxCompute、Doris→PG 等常用组合）

关键规则速查：
- **CLI 的 autocreate 不生效**：目标表必须手动预建。`prodTableNotExistAction` 仅两个合法值：`"ignore"`（默认，忽略）和 `"autocreate"`（自动建表），**不存在 `"error"` 值**（虽 CLI 可能接受，但非 Java `TableNotExistAction` 枚举成员）
- **类型映射陷阱**：Doris LARGEINT→PG NUMERIC、Doris TINYINT→PG SMALLINT
- **column 顺序**：reader.column 与 writer.column 必须一一对应、长度一致

### ⚠️ Hive 输出组件专用陷阱

**Hive writer 的 `Key` 必须是 `hadoophiveoutput`，不是 `hiveoutput`！**

| 错误写法 | 正确写法 |
|---|---|
| `Step.Key = "hiveoutput"` | `Step.Key = "hadoophiveoutput"` |
| `PluginConfig.pluginAlias = "hiveoutput"` | `PluginConfig.pluginAlias = "hadoophiveoutput"` |
| `PluginConfig.webPluginKey = "hiveoutput"` | `PluginConfig.webPluginKey = "hadoophiveoutput"` |

> **根因**：Java 模型 `OAHiveOutputConfig.stepKey()` 固定返回 `"hadoophiveoutput"`，UI 通过 `Key` 匹配组件类型。用 `"hiveoutput"` 虽然 API 能接受（服务端自动回填正确字段），但 UI 无法识别该组件类型，导致输出端"数据源"下拉框不显示、页面渲染异常。

**Hive writer 的 `dsId` / `dsName` 指向计算源**（不是数据源）：
- `dsId`：项目的 Hive 计算源 ID（如 `"7004766411885056"`）
- `dsName`：计算源名称（如 `"mdc_dev"`）
- `dsProjectId`：必填，String 类型，项目 ID（如 `"7004768582924800"`），服务端通过它解析计算源

> **Hive reader 同理**：`Key` 必须是 `hadoophiveinput`，不是 `hiveinput`。

详细信息见 [references/pipeline-config.md](references/pipeline-config.md) 的 Hive writer 章节。

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

> ⚠ **键必须用 camelCase**（`engine.name` / `requiredResource.cpus`…），不能用 PascalCase；否则服务端识别不到引擎，报 `compute engine not found`（实测 v3.4.2）。

```jsonc
{
  "requiredResource": { "cpus": 0.5, "memoryInMb": 1024 },
  "jvmOption": "",
  "noFlowTimeout": 30,
  "engine": { "name": "dlink" },
  "errorLimit": { "record": 0 },             // 脏数据上限
  "timeZone": "Asia/Shanghai",
  "sqlTimeout": 30,
  "speed": { "concurrent": 3 },              // 并发数
  "connectRetryTime": [
    { "retryTimes": 1, "dsId": "<reader 数据源ID>" }
  ]
}
```

---

## 校验

```bash
# 用 PipelineId 查（注意：get-pipeline-by-id 同样用 --context，不用 --env）
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --context 'Env=DEV ProjectId=<project-id>' \
  --pipeline-id <pipelineId>
```

只建草稿没填 Steps 时，`Data` 可能为 `null`（预期）；填好 Steps 后再查应返回完整 `Steps` / `Hops` / `Settings`。

---

## 目标表预建（MaxCompute 目标必读）

> ⚠ **实测结论（务必遵守）**：`prodTableNotExistAction: autocreate` 在 **CLI 提交的管道运行时并不会自动建表**（多次实跑验证：实例直接报 `ODPS-0130131 Table not found`，日志中无任何建表动作）。**目标表必须在跑批前预先建好**，不要依赖 autocreate。

按目标类型选择建表方式：

| 目标类型 | CLI 能否预建目标表 | 建表方式 |
|---|---|---|
| 关系型（MySQL/PostgreSQL/Oracle/SQLServer/StarRocks…） | ✅ 可以 | `execute-ad-hoc-task --operator-type DATABASE_SQL --data-source-id <目标dsId> --code 'CREATE TABLE ...'`（`--data-source-id` 对关系型生效，直接建到目标数据源库中）|
| **MaxCompute** | ❌ **CLI 无法预建** | 页面「一键建表」（走 `/api/pipeline/gss/ddl/{dsType}/execute`，OpenAPI 未暴露）。**原因**：`execute-ad-hoc-task --operator-type MaxCompute_SQL` 忽略 `--data-source-id`，只会建到**项目计算源**的 ODPS project，而 writer 数据源常指向另一个 ODPS project，两者不一致 → 跑批报表不存在 |

> **MaxCompute 目标的标准流程**：控制台对该任务点一次「一键建表」把目标表建到 writer 数据源对应的 ODPS project → 再用 CLI 提交/运行。

---

## 运行验证（补数据触发实跑）

提交只是让任务可调度；要**实际跑一次产出数据**（如验证端到端），用「补数据」触发 DEV 实跑：

```bash
# 1. 触发补数据（node-id-list 是对象数组，元素形如 {"Id":"n_xxx"}）
aliyun dataphin-public create-node-supplement \
  --tenant-id <tenant-id> --project-id <project-id> --env DEV \
  --node-id-list '{"Id":"<提交后返回的 NodeId>"}' \
  --start-biz-date 2026-07-22 --end-biz-date 2026-07-22 \
  --node-supplement-name <补数据名> \
  --context ... # 视版本，一般 --tenant-id/--project-id/--env 即可
# 返回 SubmitId（形如 f_xxx_日期_xxx）

# 2. 轮询 Dagrun 状态（用返回的 SubmitId）
aliyun dataphin-public get-supplement-dagrun \
  --tenant-id <tenant-id> --env DEV --supplement-id <SubmitId>
# DagrunList[].Status：RUNNING → SUCCESS / FAILED

# 3. 取该 Dagrun 下节点实例
aliyun dataphin-public get-supplement-dagrun-instance \
  --tenant-id <tenant-id> --env DEV --dagrun-id <Dagrun Id>

# 4. 看实例执行日志（结果在 TaskrunLogList[].LogContent，找 "Current task status: SUCCESS"）
aliyun dataphin-public get-physical-instance-log \
  --tenant-id <tenant-id> --project-id <project-id> --env DEV \
  --instance-id <实例Id>
```

关键点：
- **`--node-id-list` 必须是对象数组**：`'{"Id":"n_xxx"}'`，裸传 `n_xxx` 或字符串都会报 JSON 解析/`Expected BEGIN_OBJECT` 错误。
- 即席/补数据任务都是**异步**，调度到 agent 有排队（数十秒），需轮询状态，不要一次取结果就判定。
- 实例日志的最终判定看 `Current task status: SUCCESS` / `FAILED`；失败时日志尾部有 ODPS/DB 报错原因。

---

## 按任务名提交已有任务（保留页面调度）

已在页面建好、保存为草稿（未提交，`NodeId=null`）的任务，只有任务名时，按下列四步提交，并**原样保留页面已设的调度**（cron/上游/优先级/资源组）：

1. **定位** FileId：`list-files --category offlinePipeline --directory / --recursive true --env DEV`，按 `Name` 精确匹配
2. **读配置**：`get-pipeline-by-id --file-id <id> --context 'Env=DEV ProjectId=<pid>'` → 拿 `Data.{PipelineConfig,ScheduleConfig,Settings,NodeInfo}`，与 update-pipeline 四个入参一一对应
3. **四块配置全部原样回传**（已真机验证）：回读的 `ScheduleConfig` 虽是 camelCase 读取格式（`cronExpression/upstreams/...`），**无需转 PascalCase，直接原样传给 `--schedule-config` 即可提交生效且调度不丢**（回读验证 cron/上游/优先级均保留）。PipelineConfig（Steps 的 PluginConfig 已是字符串）与 Settings 同理原样复用
4. **提交**：`update-pipeline --context 'Env=DEV ProjectId=<pid>' --node-info '{"NodeName":..,"PipelineId":..}' --pipeline-config <原样> --schedule-config <原样> --settings <原样> --submit=true`

> 修改已有任务配置（改 cron/并发/字段映射等）请用兄弟 skill [update-pipeline-task](../update-pipeline-task/SKILL.md)（先查后改、全量回写 + 回滚基线）；其「camelCase 回读原样回传」结论与本节一致。
> 备注：若需从零手写调度（非回传场景），仍按上文「`--schedule-config` 完整骨架」的 PascalCase 写入格式；两种格式服务端都接受。

---

## 常见坑

1. **`PluginConfig` 必须是 JSON 字符串**：CLI 不会递归序列化嵌套对象。把每个插件 config 用 `JSON.stringify` 转字符串后再放进 `Steps[].PluginConfig`。
2. **空 `PluginConfig: "{}"` 触发 ClassCastException**：服务端反序列化为 `DefaultOutputPluginConfig` 与 `BaseOutputPluginConfig` 类型转换失败。最少要带 `dsName`/`dsId`/`dsType`/`table`/`columns`。
3. **`--tenant-id` 必须与项目所属租户一致**：多租户共享同一 endpoint 时，profile 中的 `tenant_id` 与目标项目的租户可能不同，必须显式传项目租户，否则 `DPN.Filter.ProjectNotFound`。
4. **`columnMappings` 必填且顺序敏感**：MaxCompute writer 必须显式声明每一列的 `sourceColumn → targetColumn`，`inputColumnIndex` 从 0 开始且与 reader `columns` 顺序对齐，否则跑批数据错位。
5. **大整数 ID 字符串化**：`dsId` / `nodeId` / `fileId` 体量超 `Number.MAX_SAFE_INTEGER`（如 `7445807200604583744`）必须以字符串传入，避免 JS JSON.parse 精度丢失。
6. **缺省上游需挂租户虚拟根节点**：`UpStreamList` 不能为空，否则提交时报 `NodeWithoutUpstream`。租户虚拟根节点的查找见 [find-tenant-root-node](../../dev/find-tenant-root-node/SKILL.md)（经套件入口路由加载）。
7. **`Directory` 必须已存在**：默认 `/` 永远存在；自定义目录前需先建好对应类型为 `offlinePipeline` 的目录。
8. **`prodTableNotExistAction: autocreate` 在 CLI 提交的管道运行时不生效**（实测）：不仅提交校验会先查表（`DPN.Os.TableNotFound`），跑批运行时也**不会**自动建表（实例报 `ODPS-0130131 Table not found`，日志无建表动作）。详见上文「目标表预建」——关系型目标用 `execute-ad-hoc-task DATABASE_SQL --data-source-id` 预建；**MaxCompute 目标 CLI 无法预建，需页面「一键建表」**（`MaxCompute_SQL` / `HIVE_SQL` 即席任务忽略 `--data-source-id`，只打到项目计算源）。另：`prodTableNotExistAction` 仅两个合法值 `"ignore"` / `"autocreate"`（Java `TableNotExistAction` 枚举），**不存在 `"error"`**。
9. **`schedule-config` 的 cron 字段名是 `CronExpression`**（不是 `ScheduleCron`），用错会报「调度周期表达式为空」。
10. **查询 MySQL 源表字段用 `execute-ad-hoc-task --operator-type DATABASE_SQL`**：MySQL/Oracle/PostgreSQL/SQLServer 等关系型数据库统一使用 `DATABASE_SQL`，必须同时传 `--data-source-id` 和 `--data-source-schema`。查询结果在 `get-ad-hoc-task-result --sub-task-id 0`（从 **0** 开始）的 `Result` 字段中。
11. **`prodTableDdl` 仅在前端 UI `autocreate` 流程生效**：CLI 场景下仅作为元信息保存，不会自动执行建表。
12. **`get-project-produce-user` 需显式传 `--tenant-id`**：多租户共享 endpoint 时，不传 `--tenant-id` 会报 `DPN.Filter.ProjectNotFound`，即使 profile 中已配置 tenant_id。查生产账号时必须显式加上
13. **自定义目录必须逐级预建**：如需将任务放在 `/cli/pipeline` 目录，必须先 `create-directory /cli`，再 `create-directory /cli/pipeline`，直接传多级目录报 `DPN.Resource.DirectoryNotFound`
14. **目标数据源表必须预建**（详见上文「目标表预建」章节）：`autocreate` 运行时不生效，必须先建表；MaxCompute / Hive 目标 CLI 无法预建（`MaxCompute_SQL` / `HIVE_SQL` 即席均只打到项目计算源，不认 `--data-source-id`），只能走页面「一键建表」；关系型目标可用 `execute-ad-hoc-task DATABASE_SQL --data-source-id` 直接建到目标库
15. **`update-pipeline` 用 `--context` 而非 `--env`**（v3.4.2+）：`update-pipeline` **无 `--env` 参数**，环境与项目通过必填的 `--context 'Env=DEV ProjectId=<项目ID>'` 传入，缺失会报 `--context is required`。注意 `create-pipeline` 仍用 `--env`，两者不要混用。`get-pipeline-by-id` 同样用 `--context`
16. **`--submit` 必须带值**：该 flag 是带值布尔，裸写 `--submit` 会吞掉下一个参数，报 `invalid boolean value: --endpoint`；写 `--submit=true` 提交、`--submit=false` 仅存草稿（实测 v3.4.2）
17. **`--settings` 键用 camelCase**：用 PascalCase（`Engine.Name`）服务端识别不到引擎，报 `compute engine not found`；正确为 `engine.name` / `requiredResource.cpus` 等
18. **Step 的 `Key` 必须与 Java 模型 `stepKey()` 一致**：`Key` 在管道的 `Steps` 数组中对应 Java 配置类的 `stepKey()` 返回值。不一致时 API 可能仍接受（服务端自动纠正），但 UI 无法识别插件类型导致页面渲染异常。常见易错：Hive writer= `hadoophiveoutput`（非 `hiveoutput`），Hive reader= `hadoophiveinput`（非 `hiveinput`）
19. **Hive 输出 `dsId` / `dsName` 指向计算源**：Hive writer 不通过普通数据源连接，而是通过项目绑定的计算源。`dsProjectId` 必填（String 类型），服务端通过它解析 Hive 连接信息。不要把计算源 ID 和项目 ID 混淆
20. **`dsProjectId` 必须是 String 类型**（实测已验证）：Java 模型 `OABasePluginConfig` 中 `dsProjectId` 定义为 String。传整数（如 `7189934383558528`）而非字符串（`"7189934383558528"`）会被当作计算引擎解析，提交报 `compute engine not found`；改为字符串后提交成功
21. **管道损坏后用 `offline-pipeline` 删除**：若因配置错误导致管道无法读取（`get-pipeline-by-id` 报 NPE），需先 `offline-pipeline --delete` 再重建。无法通过 `update-pipeline` 修复已损坏的管道

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
  --context 'Env=DEV ProjectId=<project-id>' \
  --node-info "{\"NodeName\":\"<task-name>\",\"PipelineId\":${PID}}" \
  --pipeline-config "$(cat pipeline-config.json)" \
  --schedule-config "$(cat schedule-config.json)" \
  --settings "$(cat settings.json)" \
  --submit=true

# 4. 校验
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --context 'Env=DEV ProjectId=<project-id>' \
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
  --context 'Env=DEV ProjectId=<project-id>' \
  --node-info "{\"NodeName\":\"<task-name>\",\"PipelineId\":${PID}}" \
  --pipeline-config "$(cat pipeline-config.json)" \
  --schedule-config "$(cat schedule-config.json)" \
  --settings "$(cat settings.json)" \
  --submit=true

# 3. 校验
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --context 'Env=DEV ProjectId=<project-id>' \
  --pipeline-id "${PID}"
```

> **PostgreSQL 目标端踩坑速查**：
> 1. `schemaName` 必填——PG 有 schema 概念（常见 `public` 或自定义），不传会报表不存在
> 2. 目标表必须手动预建——`prodTableNotExistAction: autocreate` 在 CLI/OpenAPI 场景不生效
> 3. 类型不能照搬源端——Doris `LARGEINT` 在 PG 不存在，需映射为 `NUMERIC`；`TINYINT` 需映射为 `SMALLINT`
> 4. `columnMappings[].originalType` 填 PG 目标类型，不是 Doris 源类型
> 5. PostgreSQL 建表用 `--operator-type DATABASE_SQL`（关系型数据库统一入口），必须同时传 `--data-source-id` 和 `--data-source-schema`

## 完整示例 3（路径 B，MySQL→Hive 一对一搬运）

```bash
# 0. 在 Hive 中预建目标表
# ⚠ Hive 表在计算源对应的 Hive 仓库中，通过即席 SQL 执行
# ⚠ 如果目标 Hive 表已存在，跳过此步骤
aliyun dataphin-public execute-ad-hoc-task \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --operator-type MaxCompute_SQL \
  --code "CREATE TABLE IF NOT EXISTS <目标库>.ods_<table> (
    <col1> string, <col2> string, ...
  ) PARTITIONED BY (ds string) STORED AS ORC;"

# 1. 一键创建并提交（⚠ 输出 Step.Key 必须是 hadoophiveoutput，不是 hiveoutput！）
PID=$(aliyun dataphin-public create-pipeline \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --node-info '{"NodeName":"<task-name>","Directory":"/"}' \
  --pipeline-config "$(cat pipeline-config.json)" \
  --schedule-config "$(cat schedule-config.json)" \
  --settings "$(cat settings.json)" \
  --output json | jq -r '.Data.PipelineId')

# 2. 校验
# ⚠ 确认输出 Step 的 Key 为 "hadoophiveoutput"（不是 "hiveoutput"）
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id <tenant-id> \
  --project-id <project-id> \
  --env DEV \
  --pipeline-id "${PID}"
```

> **Hive 输出端 pipeline-config 关键点**：
> - `Steps[输出].Key` = `"hadoophiveoutput"`（**不是** `"hiveoutput"`）
> - `PluginConfig.pluginAlias` = `"hadoophiveoutput"`
> - `PluginConfig.dsId` = 计算源 ID（**不是**数据源 ID）
> - `PluginConfig.dsProjectId` = `"<project-id>"`（String 类型，必填）
> - `PluginConfig.loadStrategy` 默认 `"truncateAll"`（不同于 MaxCompute 的 `"overwrite"`）
> - 完整 PluginConfig 骨架见 [references/pipeline-config.md](references/pipeline-config.md) Hive writer 章节
