---
name: update-batch-task
description: |-
  编辑/更新已存在的离线计算任务（代码、数据源、调度配置、上下游依赖）。触发场景：修改任务代码 / 更新任务调度 / 切换数据源 / 设置 cron 表达式 / 配置 CustomScheduleConfig / 调整上游依赖 / update-batch-task。关键点：TaskType 必填且不可改类型；FileId 不能从 list-nodes 直接获得，需通过 list-files 按任务名查找；大整数 DataSourceId 必须按字符串传参，否则报 NumberFormatException；DEV_PROD 项目里 update-batch-task 即使 --env DEV 也要用生产数据源 ID；分钟级调度分"每小时重置"与"全天连续"两种，后者 CronExpression 固定为 "0 0 0 * * ?" 并用 CustomScheduleConfig 表达间隔；Update 后若要生效到 PROD 仍需 submit + publish-object-list。触发词：修改任务代码、更新任务调度、切换数据源、update-batch-task、设置 cron、配置 CustomScheduleConfig、更新上游依赖、每5分钟调度。
---

# 编辑离线计算任务 Skill

## 1. Scenario Description

场景：修改已存在的离线批任务，常见包括：

- 调整任务 Code（SQL / Shell / Python 等）
- 修改调度周期或 cron 表达式
- 切换数据源 / Schema / Catalog
- 配置全天连续间隔调度（每 N 分钟）
- 调整节点输出名、优先级、参数等

本 Skill 覆盖从定位任务 FileId、读取当前配置、构造 Update 命令到验证的全流程。

### Architecture

```
用户请求 → 确认参数
  → list-files 按任务名找 FileId
  → get-batch-task-info 读取当前配置作为模板
  → 构造 update-batch-task 命令
  → 更新后 get-batch-task-info / get-physical-node 验证
  → 如需生效到 PROD：submit-batch-task → publish-object-list
```

### 涉及 Dataphin OpenAPI

- `UpdateBatchTask` — 编辑离线任务
- `GetBatchTaskInfo` — 读取当前任务配置
- `ListFiles` — 按任务名查找 FileId
- `SubmitBatchTask` — 更新后生成待发布记录
- `PublishObjectList` — 发布到生产环境
- `GetPhysicalNode` — 验证生产环境已上线节点的调度

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8）
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun dataphin-public --help
aliyun dataphin-public update-batch-task --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

> **Security Rules:**
> - **NEVER** 读取、回显或打印凭证环境变量
> - **NEVER** 要求用户在本会话或命令行直接输入 AK/SK
> - **NEVER** 使用 `aliyun configure set` 写入字面量凭证
> - **ONLY** 使用 `aliyun configure list` 检查凭证状态
>
> ```bash
> aliyun configure list
> ```

### Pre-check: Aliyun CLI >= 3.4.8 required

> 运行 `aliyun version` 确认版本 >= 3.4.8。

### Pre-check: Aliyun CLI plugin update required

> [MUST] 运行 `aliyun configure set --auto-plugin-install true` 开启自动插件安装。
> [MUST] 运行 `aliyun plugin update` 确保插件为最新版本。

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** 当任一命令/API 因权限失败时：
> 1. 阅读 `../../ram-policies.md` 获取本 Skill 所需完整权限
> 2. 使用 `ram-permission-diagnose` skill 引导用户申请权限
> 3. 暂停等待用户确认权限已授予

本 Skill 最小权限：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataphin:UpdateBatchTask",
        "dataphin:GetBatchTaskInfo",
        "dataphin:ListFiles",
        "dataphin:SubmitBatchTask",
        "dataphin:PublishObjectList",
        "dataphin:GetPhysicalNode",
        "dataphin:GetNodeUpDownStream"
      ],
      "Resource": "*"
    }
  ]
}
```

详见 [RAM 策略参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or
> use default values without explicit user approval.

执行前必须向用户确认：

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--env` | 推荐 | DEV 或 PROD（编辑必须在 DEV 进行） | `DEV` |
| `--project-id` / `--tenant-id` | 条件 | profile 已配置可省略 | `7295715579274176` |
| 任务名 / FileId | 必 | 要更新的任务标识 | `cli_test` / `7295946868284416` |
| `--task-type` | 必 | 任务类型数值，不可改类型 | `998`（DATABASE_SQL） |
| `--code` | 必 | 更新后的任务代码 | `select * from demo01;` |
| `--schedule-period` | 条件 | 修改调度时必填 | `MINUTELY` |
| `--cron-expression` | 条件 | 修改调度时必填 | `0 0 0 * * ?` |
| `--custom-schedule-config` | 条件 | 全天连续间隔调度时必填 | `{"Interval":5,...}` |
| `--data-source-id` | 条件 | 数据库 SQL 类任务 | `"7471047829105603136"` |
| `--data-source-schema` | 条件 | 数据库 SQL 类任务 | `public` |
| `--node-output-name-list` | 条件 | 节点输出名 | `test1_dev.cli_test` |
| `--priority` | 可选 | 优先级 1-9 | `5` |

## 7. 完整命令链

### Step 1: 定位 FileId

`list-nodes` 返回的 `FileId` 通常为 null，应使用 `list-files` 按任务名查找：

```bash
aliyun dataphin-public list-files \
  --dataphin-profile <profile> --env DEV \
  --project-id <project-id> --tenant-id <tenant-id> \
  --category codeManage --directory / --recursive true \
  --format json | jq '.FileList[] | select(.Name == "cli_test") | {Id, FileType, Directory}'
```

### Step 2: 读取当前配置作为模板

```bash
aliyun dataphin-public get-batch-task-info \
  --dataphin-profile <profile> --env DEV \
  --project-id <project-id> --tenant-id <tenant-id> \
  --file-id <file-id> --format json | jq '.TaskInfo'
```

### Step 3: 构造并执行 update-batch-task

推荐使用 `--update-command` 一次性传入 JSON 对象：

```bash
aliyun dataphin-public update-batch-task \
  --dataphin-profile <profile> --env DEV \
  --project-id <project-id> --tenant-id <tenant-id> \
  --update-command '{
    "ProjectId": <project-id>,
    "FileId": <file-id>,
    "Name": "cli_test",
    "TaskType": 998,
    "Code": "select * from demo01;",
    "DataSourceId": "<data-source-id-string>",
    "DataSourceSchema": "public",
    "NodeOutputNameList": ["test1_dev.cli_test"],
    "SchedulePeriod": "MINUTELY",
    "CronExpression": "0 0 0 * * ?",
    "CustomScheduleConfig": {
      "SchedulePeriod": "DAY",
      "Interval": 5,
      "IntervalUnit": "MINUTE",
      "StartTime": "00:00",
      "EndTime": "23:59"
    },
    "Priority": 5
  }' --format json
```

### Step 4: 验证 DEV 配置

```bash
aliyun dataphin-public get-batch-task-info \
  --dataphin-profile <profile> --env DEV \
  --project-id <project-id> --tenant-id <tenant-id> \
  --file-id <file-id> --format json | jq '.TaskInfo | {CronExpression, SchedulePeriod, CustomScheduleConfig}'
```

### Step 5: 生效到 PROD（需要时）

Update 只改 DEV 文件，要生效到 PROD 必须 submit + publish：

```bash
# 提交生成 SubmitId
RESULT=$(aliyun dataphin-public submit-batch-task \
  --dataphin-profile <profile> --env DEV \
  --project-id <project-id> --tenant-id <tenant-id> \
  --file-id <file-id> --batch-task-name cli_test \
  --code "select * from demo01;" \
  --comment "更新调度为每5分钟")
SUBMIT_ID=$(echo "$RESULT" | jq -r '.CreateResult.SubmitId')

# 发布到生产
aliyun dataphin-public publish-object-list \
  --dataphin-profile <profile> \
  --project-id <project-id> --tenant-id <tenant-id> \
  --submit-id-list "$SUBMIT_ID" \
  --comment "发布 cli_test 调度更新"

# 验证生产节点
aliyun dataphin-public get-physical-node \
  --dataphin-profile <profile> --env PROD \
  --project-id <project-id> --tenant-id <tenant-id> \
  --node-id <node-id> --format json | jq '.NodeInfo | {CronExpression, ScheduleType, Status}'
```

## 8. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/update-batch-task/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 9. TaskType 与调度配置

### TaskType 枚举（Update 必填且不可改）

| 值 | 任务类型 | 说明 |
|---|---|---|
| `1` | Hive_SQL | Hive 数据库 SQL |
| `5` | MaxCompute_SQL | MaxCompute SQL |
| `10` | Shell | Shell 脚本 |
| `21` | Python | Python 任务 |
| `998` | DATABASE_SQL | 通用数据库 SQL（PostgreSQL/MySQL/Oracle 等） |
| 其他 | Spark_SQL / DB_SQL 等 | 查阅官方文档 |

分钟级调度“每小时重置”与“全天连续”两种语义、`CustomScheduleConfig` 详情以及多时点 cron 注意事项见 [schedule-config.md](./references/schedule-config.md)。

### 条件调度（Conditional Schedule）

> 条件调度目前主要通过 Dataphin UI 配置，对应内部接口 `/api/dataProcess/{projectId}/nodes/{fileId}/config` 中的 `conditionScheduleParamDTOList` 字段。公共 OpenAPI `UpdateBatchTask` 暂未直接暴露该结构，但 Agent 在处理"仅周六运行"、"节假日空跑"、"上游参数为某值时空跑"等需求时应识别其数据模型。

开启条件调度的两个顶层开关：

```jsonc
{
  "conditionScheduleEnable": true,
  "conditionScheduleParamDTOList": [ ... ]
}
```

单条规则核心字段：

| 字段 | 说明 | 示例 |
|---|---|---|
| `conditionName` | 规则名称 | `"周六8点运行"` |
| `nodeStatus` | 满足条件时节点状态：`1` 正常执行，`3` 空跑 | `1` / `3` |
| `cronExpression` | 满足条件时使用的 cron | `"0 00 08 * * ?"` |
| `scheduleConditionDTO.operator` | 子条件组合：`AND` / `OR` | `AND` |
| `expression.expressionType` | 条件类型：`BIZDATE`（业务日期/日历）/ `CROSS_NODE_PARAM`（上游输出参数） | `BIZDATE` / `CROSS_NODE_PARAM` |
| `expression.operator` | `BIZDATE` 用 `BELONG` / `NOT_BELONG`；`CROSS_NODE_PARAM` 用 `EQUAL` / `NOT_EQUAL` | `BELONG` / `EQUAL` |
| `expressionValueDTO.expressionValueType` | `CUSTOM_CALENDAR` 普通日历 / `PUBLIC_CALENDAR` 公共日历 / `CROSS_NODE_PARAM` 跨节点参数 | `CUSTOM_CALENDAR` |
| `expressionValueDTO.period` | 普通日历周期：`WEEK` / `MONTH` | `WEEK` |
| `expressionValueDTO.values` | 取值：星期 `["6"]`、公共日历 `["WORK_DAY"]` | `["6"]` |
| `expressionValueDTO.paramName` | 跨节点参数：上游输出参数名 | `"var"` |
| `expressionValueDTO.nodeId` | 跨节点参数：上游节点物理 NodeId | `"n_8127255632277340160"` |
| `expressionValueDTO.nodeName` | 跨节点参数：上游节点名 / output name | `"shell_a"` |
| `publicCalendarCode` | 公共日历 Code | `"xx"` |

完整结构、字段说明以及"周六且为假日时 8 点运行"、"上游 `shell_a.var == 1` 时空跑"的示例见 [conditional-scheduling.md](./references/conditional-scheduling.md)。

## 10. 数据源与 ID 传参

### DataSourceId 必须字符串化

DataSourceId 是 19 位 snowflake，JSON 数字会被解析为浮点科学计数法，导致：

```
NumberFormatException: For input string: "7.471047878493533e+18"
```

**正确**：JSON 中写 `"DataSourceId": "7471047829105603136"`。

### DEV_PROD 项目的数据源选择

在 DEV_PROD 双环境项目中，即使 `--env DEV`，`update-batch-task` 也可能要求使用**生产数据源 ID**，否则报错：

```
DPN.DataProcess.DataSourceNotProd: Datasource xxx is not a production datasource
```

应先通过 `list-data-source-with-config` 分别确认 DEV/PROD 的 `DevDataSourceInfo.Id` 与 `ProdDataSourceInfo.Id`，Update 时传 PROD 数据源 ID。

## 11. 常见报错

| 错误码 | 原因 | 处理 |
|---|---|---|
| `NumberFormatException` | DataSourceId / 大整数 ID 按数字传参 | 用字符串包裹 |
| `DPN.DataProcess.DataSourceNotProd` | DEV_PROD 项目传了 DEV 数据源 ID | 改用 PROD 数据源 ID |
| `DPN.DataProcess.NodeWithoutUpstream` | 提交时无上游依赖 | 用 `find-tenant-root-node` 找 `virtual_root_node_<DagId>` 并挂为上游；如 CLI 无法更新 UpStreamList，可在 UI 中补依赖后再 submit |
| `DPN.Resource.DirectoryNotFound` | create-batch-task 时目录不存在 | 先 create-directory |
| `DPN.DataProcess.NodeUpstreamNotExist` | UpStreamList.SourceNodeId 拼错 | 根节点用 `virtual_root_node_xxx`，真实节点用 output name |

## 12. ✗ 不要做

- ❌ 直接按 `list-nodes` 的 `FileId` 更新（通常为 null）
- ❌ 把 `DataSourceId` 当数字传
- ❌ 认为 Update 后 PROD 会自动生效（必须 submit + publish）
- ❌ 用 `0 0/05 0-23 * * ?` 表达"全天连续每 5 分钟"却忽略 `CustomScheduleConfig`
- ❌ 在 Update 时尝试修改 `TaskType`（会报错，应删后重建）

## 13. 相关命令

详见 [相关命令索引](./references/related-commands.md)。

- `aliyun dataphin-public list-files` — 按任务名查找 FileId
- `aliyun dataphin-public get-batch-task-info --file-id <N>` — 读取当前任务详情
- `aliyun dataphin-public update-batch-task` — 编辑任务
- `aliyun dataphin-public submit-batch-task` — 生成待发布记录
- `aliyun dataphin-public publish-object-list` — 发布到生产
- `aliyun dataphin-public get-physical-node --node-id <N> --env PROD` — 验证生产节点调度
- `submit-batch-task` — 初次提交流程（经套件入口 alibabacloud-dataphin-skills 路由加载）
- `find-tenant-root-node` — 查找虚拟根节点（经套件入口路由加载）
---
name: update-batch-task
description: |-
  编辑/更新离线计算任务（代码、数据源、调度配置）。 触发场景：修改任务代码 / 更新任务调度 / 切换数据源 / update-batch-task / 设置 cron 表达式 / 配置上游依赖 / 设置 ScheduleConfig。 关键点：TaskType 必填（明确枚举）且 Engine 依 TaskType 而定；与 submit-batch-task 同构但多了 TaskType 与 DataSource 相关字段。 触发词：修改任务代码、更新任务调度、切换数据源、update-batch-task、设置 cron、配置上游依赖、ScheduleConfig。
---
# 编辑离线计算任务 skill

## 适用场景

- 修改已存在的离线任务 Code / 调度 / 依赖 / 参数
- 调整 Python Engine 版本（PYTHON2_7 → PYTHON3_11）
- 切换 SQL 类任务的 `DataSourceId` / `DataSourceCatalog` / `DataSourceSchema`

## 命令 & 官方文档

- CLI：`aliyun dataphin-public update-batch-task --help`
- OpenAPI：[UpdateBatchTask](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/UpdateBatchTask)

## 顶层参数骨架

```text
--tenant-id <int>          必填 | 租户 ID
--update-command <JSON>       必填 | 更新命令体
```

## TaskType 枚举（Update 中明确，Submit 复用同值）

| 值 | TaskType | 说明 |
|---|---|---|
| `1`  | Hive_SQL | Hive 数据库 SQL 任务 |
| `5`  | MaxCompute_SQL | MaxCompute SQL |
| `10` | Shell | Shell 脚本 |
| `21` | Python | Python 任务 |
| 其他 | Spark_SQL / DB_SQL 等 | 请查阅官方文档 |

## Engine 枚举

- **Python 任务**（TaskType=21）：`PYTHON2_7` / `PYTHON3_7` / `PYTHON3_11`
- **SQL 类任务**：Engine 一般不传，底层按计算源决定

## UpdateCommand 通用骨架

```jsonc
{
  "ProjectId": <int>,            // 必填
  "FileId":    <int>,            // 必填，目录树节点 Id
  "Name":      "<string>",       // 必填
  "Code":      "<string>",       // 必填，任务代码
  "TaskType":  21,               // 必填！Update 比 Submit 多要求 TaskType
  "Engine":    "PYTHON3_11",     // Python 任务必填

  "NodeDescription":   "<string>",
  "NodeOutputNameList": ["<project>.<name>"],

  "SchedulePeriod":  "DAILY",    // YEARLY/MONTHLY/WEEKLY/DAILY/HOURLY
  "CronExpression":  "0 0 0 * * ?",
  "CustomScheduleConfig": { ... },

  "ParamList": [
    { "Key": "bizdate", "Value": "${yyyyMMdd}" }
  ],

  "UpStreamList": [
    {
      "NodeType": "PHYSICAL",
      "SourceNodeId": "<id>",
      "SourceNodeOutputName": "<output-name>",
      "PeriodDiff": 0,
      "DependPeriod": { "PeriodType": "CURRENT_PERIOD" },
      "DependStrategy": "ALL"
    }
  ],

  "Priority": 5,
  "NodeStatus": 1,

  "DataSourceId":      "<id>",        // 仅 SQL 类（Hive/Presto/Oracle/...）必填
  "DataSourceCatalog": "<catalog>",   // 仅 Presto 等需要
  "DataSourceSchema":  "<schema>",    // 仅 Oracle 等需要

  "PythonModuleList": ["pandas"],     // 仅 Python
  "SparkClientInfo":  { "SparkClientVersion": "spark-3.2" }
}
```

## 按 TaskType 的具体要求

### ⚠ Python（TaskType=21）

```jsonc
{
  "TaskType": 21,
  "Engine":   "PYTHON3_11",
  "Code":     "import pandas\nprint('ok')",
  "PythonModuleList": ["pandas==1.5.0"]
}
```

### ⚠ Shell（TaskType=10）

```jsonc
{
  "TaskType": 10,
  "Code":     "#!/bin/bash\necho hi"
}
```

不需要 Engine / DataSource / PythonModuleList。

### ⚠ Hive_SQL（TaskType=1）

```jsonc
{
  "TaskType": 1,
  "Code":     "SELECT * FROM t WHERE ds='${bizdate}'",
  "DataSourceId": "7453342690811205056"
}
```

### ⚠ MaxCompute_SQL（TaskType=5）

```jsonc
{
  "TaskType": 5,
  "Code":     "CREATE TABLE IF NOT EXISTS t (id BIGINT);"
}
```

不需要 DataSourceId（用项目绑定的 MaxCompute 计算源）。

## 常见坑

1. **TaskType 必填且不可改类型**：Update 语义是"更新同类型任务"，把 Python 改成 Shell 通常会被拒，应删后重建
2. **Code 中转义字符**：在 shell 里用单引号包 JSON，JSON 内 `\n` 原样写即可，Dataphin 接受 `\n` 字符串并自动按 TaskType 解析
3. **UpStreamList 不是 patch**：每次 Update 要传完整依赖清单；漏传 = 清空依赖
4. **未全量覆盖**：所有 Update 示例未经全量实战，优先用 `aliyun dataphin-public get-batch-task-info --file-id <N>` 读取当前配置作为模板
5. **`update-batch-task` 不会自动推送到生产**：它只更新 DEV 区代码/调度，不返回 `SubmitId`；想让改动真正生效，必须再调一次 `submit-batch-task`（携带相同的代码/调度/上游依赖，若无上游会报 `NodeWithoutUpstream`）拿到新 `SubmitId`，再 `publish-object-list --submit-id-list <SubmitId>` 发布。完整链路：`update-batch-task` → `submit-batch-task`（带上游）→ `publish-object-list`
6. **`MINUTELY`（分钟级）调度必须传 `--custom-schedule-config`，否则产品页面显示异常**：只传 `--schedule-period MINUTELY --cron-expression "0 0/5 * * * ?"` 接口返回成功，但产品页面会报 `cron 表达式不能为空` 且时间区间显示 `Invalid`。**内层 `SchedulePeriod` 枚举值决定调度语义，务必按需求选对**：
    - 全天连续、不按小时重置（如"每天每 5 分钟调度一次"）→ `SchedulePeriod: "DAY"`
      ```json
      {"StartTime":"00:00","EndTime":"23:59","Interval":5,"IntervalUnit":"MINUTE","SchedulePeriod":"DAY"}
      ```
    - 每小时内独立重新计时（如"每小时第0分钟起每5分钟，下一小时重置"）→ `SchedulePeriod: "HOUR"`
      ```json
      {"StartTime":"00:00","EndTime":"23:59","Interval":5,"IntervalUnit":"MINUTE","SchedulePeriod":"HOUR"}
      ```
    - ⚠️ **陷阱**：`update-batch-task` 对该字段不做枚举校验，传错值（如 `HOURLY`/`DAILY`）也会返回成功并原样存下，但后续 `submit-batch-task` 会报 `No enum constant ...CustomIntervalPeriodEnum.XXX` 真正报错。**唯一合法值是 `DAY` 和 `HOUR`**，`IntervalUnit` 用 `MINUTE`，`StartTime`/`EndTime` 格式 `HH:mm`。详见同套件子 skill `submit-batch-task` 常见坑 #12（经套件入口路由加载）。

## 相关命令

- [submit-batch-task.md](./submit-batch-task.md) — 初次提交流程
- `aliyun dataphin-public get-batch-task-info --file-id <N>` — 读出当前任务详情作为 Update payload 模板
- `aliyun dataphin-public submit-batch-task` — Update 后重新提交生成 SubmitId
- `aliyun dataphin-public publish-object-list --submit-id-list <SubmitId>` — 发布到 prod 才真正生效
