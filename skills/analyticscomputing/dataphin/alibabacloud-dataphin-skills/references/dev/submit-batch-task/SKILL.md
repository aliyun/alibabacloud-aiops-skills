---
name: submit-batch-task
description: |-
  提交离线计算任务（从开发区提交到运维区）。 触发场景：提交任务 / submit 离线任务 / 任务从 DEV 提交到生产 / submit-batch-task / 获取 SubmitId 和 NodeId。 关键点：TaskType × Engine 两级分支决定 Code 语言和 ParamList Key 规则（Python / Shell / Hive_SQL / MaxCompute_SQL 等）。 注意：不支持 --data-source-id 参数（数据源在 update-batch-task 阶段已保存）。 触发词：提交离线任务、submit-batch-task、任务提交、获取 SubmitId、获取 NodeId、DEV 提交到生产。
---
# 提交离线计算任务 skill

## 1. Scenario Description

- 将 dev 环境已开发的离线任务提交到运维区
- 任务类型涵盖 Python / Shell / SQL 类离线作业

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8），一键脚本见 ./references/cli-installation-guide.md
aliyun plugin install --names aliyun-cli-dataphin-public   # 安装 dataphin-public 插件
aliyun dataphin-public --help                               # 验证
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

> **Security Rules:**
> - **NEVER** 读取、回显或打印凭证环境变量（禁止对 AccessKey ID / Secret 做任何输出或日志）
> - **NEVER** 要求用户在会话中直接输入 AK/SK
> - **NEVER** 使用 `aliyun configure set` 写入字面量凭证
> - **ONLY** 使用 `aliyun configure list` 检查凭证状态
>
> ```bash
> aliyun configure list
> ```
> 检查输出中是否存在有效 profile。若无，请在会话外配置（终端执行 `aliyun configure` 或设置环境变量）后再继续。

### Pre-check: Aliyun CLI >= 3.4.8 required

> 运行 `aliyun version` 确认版本 >= 3.4.8。版本过低见 `references/cli-installation-guide.md` 升级。

### Pre-check: Aliyun CLI plugin update required

> [MUST] 运行 `aliyun configure set --auto-plugin-install true` 开启自动插件安装。
> [MUST] 运行 `aliyun plugin update` 确保插件为最新版本。

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** 当任一命令/API 因权限失败时：
> 1. 阅读 `../../ram-policies.md` 获取本 Skill 所需完整权限
> 2. 使用 `ram-permission-diagnose` skill 引导用户申请权限
> 3. 暂停等待用户确认权限已授予

本 Skill 最小权限（创建 + 提交 + 发布 + 验证链路）：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataphin:CreateBatchTask",
        "dataphin:SubmitBatchTask",
        "dataphin:PublishObjectList",
        "dataphin:GetBatchTaskInfo",
        "dataphin:ListFiles",
        "dataphin:CreateDirectory",
        "dataphin:GetPhysicalNode",
        "dataphin:GetNodeUpDownStream",
        "dataphin:GetPhysicalNodeContent"
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
| `--batch-task-name` | 必 | 离线任务名 | `shell_echo` |
| `--task-type` | 必 | 任务类型数值（Shell=10） | `10` |
| `--directory` | 必 | 任务目录（须已建） | `/cli` |
| `--code` | 必 | 任务代码 | `echo 1` |
| `--schedule-period` | 推荐 | DAILY/HOURLY/MINUTELY 等 | `HOURLY` |
| `--cron-expression` | 推荐 | 多时点用 `\|` 分隔 | `0 23 1 * * ?\|0 33 19 * * ?` |
| `--up-stream-list` | 推荐 | 上游依赖，传单对象 | `{"NodeType":"PHYSICAL",...}` |
| `--custom-schedule-config` | MINUTELY 必填 | 分钟级调度必须传，否则产品页面报错。内层 `SchedulePeriod` 决定语义：`DAY`=全天连续按间隔跑（如"每天每5分钟"）；`HOUR`=每小时内重新计时（如"每小时第0分钟起每5分钟"，到下一小时重置） | `{"StartTime":"00:00","EndTime":"23:59","Interval":5,"IntervalUnit":"MINUTE","SchedulePeriod":"DAY"}` |
| `--node-output-name-list` | 条件 | BASIC 模式必填 | `shell_echo` |
| `--project-id` / `--tenant-id` | 条件 | profile 已配置可省略 | `7295715579274176` |

## 7. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/submit-batch-task/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 8. Commands & Official Docs

- CLI：`aliyun dataphin-public submit-batch-task --help`
- OpenAPI：[SubmitBatchTask](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/SubmitBatchTask)

## 顶层参数骨架

```text
--tenant-id <int>             必填 | 租户 ID
--submit-command <JSON>       必填 | 提交命令体
```

## 两级分支说明

1. **TaskType**（任务类型）决定 `Code` 写什么语言 / 是否需要 `DataSourceId`：
   - `1` Hive_SQL
   - `5` MaxCompute_SQL
   - `10` Shell
   - `21` Python
   - 其他类型（Spark_SQL 等）查 [UpdateBatchTask 文档](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/UpdateBatchTask)，Submit 与 Update 共享同一 TaskType 约定
2. **Engine**（执行引擎）：进一步决定语言版本 / 引擎版本
   - Python 任务：`PYTHON2_7` / `PYTHON3_7` / `PYTHON3_11`
   - SQL 任务：对应计算源底座（如 MaxCompute_SQL 自动使用项目 prod 计算源，可不传 Engine）

## SubmitCommand 通用骨架

```jsonc
{
  "ProjectId":  <int>,          // 必填，任务所属项目 Id
  "FileId":     <int>,          // 必填，目录树节点 Id（建任务时生成）
  "Name":       "<string>",     // 必填，离线任务名
  "Comment":    "<string>",     // 必填，提交备注
  "Code":       "<string>",     // 必填，任务代码内容（按 TaskType 不同语言）
  "Engine":     "<string>",     // 可选，Python 任务必填
  "NodeDescription": "<string>",

  "SchedulePeriod":  "DAILY",   // 可选，YEARLY/MONTHLY/WEEKLY/DAILY/HOURLY
  "CronExpression":  "0 0 0 * * ?",
  "CustomScheduleConfig": { ... },

  "ParamList": [                // 可选，自定义参数（${var} 形式注入 Code）
    { "Key": "dt", "Value": "${bizdate}" }
  ],
  "NodeOutputNameList": ["<project>.<name>"],
  "UpStreamList": [
    {
      "NodeType": "PHYSICAL",   // PHYSICAL | LOGICAL
      "SourceNodeId": "<id>",
      "SourceNodeOutputName": "<output-name>",
      "PeriodDiff": 0
    }
  ],
  "Priority": 5,
  "NodeStatus": 1,              // 1 正常 / 2 暂停 / 3 空跑

  "PythonModuleList": ["pandas==1.5.0"],
  "SparkClientInfo": { "SparkClientVersion": "spark-3.2" }
}
```

## 按 TaskType × Engine 的补充规则

### ⚠ Python 任务（TaskType=21）

```jsonc
{
  "Engine": "PYTHON3_11",               // PYTHON2_7 | PYTHON3_7 | PYTHON3_11
  "Code":   "import pandas as pd\nprint(pd.__version__)",
  "PythonModuleList": ["pandas==1.5.0", "numpy"]
}
```

- 选 `PYTHON3_11` 时注意 module 要兼容 3.11
- `PythonModuleList` 仅对 Python 类生效；其他 TaskType 传入会被忽略或报错

### ⚠ Shell 任务（TaskType=10）

```jsonc
{
  "Code": "#!/bin/bash\necho \"bizdate=${bizdate}\"\nhadoop fs -ls /tmp/",
  "ParamList": [{ "Key": "bizdate", "Value": "${yyyyMMdd}" }]
}
```

- 不需要 `Engine`
- Code 中可用 `${var}` 引用 `ParamList` / 系统内置变量

### ⚠ Hive_SQL 任务（TaskType=1） / MaxCompute_SQL（TaskType=5）

```jsonc
{
  "Code": "INSERT OVERWRITE TABLE t PARTITION (ds='${bizdate}')\nSELECT ...;",
  "DataSourceId": "<id>",               // 仅 Hive_SQL 等数据库类 SQL 任务必填
  "DataSourceCatalog": "<catalog>",     // Presto 等需要
  "DataSourceSchema": "<schema>"        // Oracle 等需要
}
```

- `MaxCompute_SQL` 无需 `DataSourceId`，使用项目绑定的 MaxCompute 计算源
- Hive / Presto / Oracle SQL 等"数据库 SQL 任务"必须指定 `DataSourceId`

## 分钟级调度双语义

"每 N 分钟"在 Dataphin 里有两种实现方式，提交时必须按目标语义选择：

| 语义 | 效果 | CronExpression | CustomScheduleConfig |
|---|---|---|---|
| **每小时重置** | 每个整点起按间隔触发，下一小时重置 | `0 0/05 0-23 * * ?` | `null` 或不传 |
| **全天连续** | 从 `StartTime` 起跨小时连续触发，不重置 | `0 0 0 * * ?` | 必填 |

### 每小时重置（第一种）

适合"每个小时都要在第 0/5/10... 分钟触发"的场景：

```jsonc
{
  "SchedulePeriod": "MINUTELY",
  "CronExpression": "0 0/05 0-23 * * ?"
}
```

### 全天连续（第二种）

适合"从 00:00 开始每 5 分钟一次，跨小时连续"的场景。此时 CronExpression 固定为 `0 0 0 * * ?`，真正间隔由 `CustomScheduleConfig` 表达：

```jsonc
{
  "SchedulePeriod": "MINUTELY",
  "CronExpression": "0 0 0 * * ?",
  "CustomScheduleConfig": {
    "SchedulePeriod": "DAY",
    "Interval": 5,
    "IntervalUnit": "MINUTE",
    "StartTime": "00:00",
    "EndTime": "23:59"
  }
}
```

> 为何必须区分：以 7 分钟间隔为例，全天连续期望 `00:07, 00:14, ..., 01:03, 01:10`；每小时重置则期望 `00:07, 00:14, ..., 00:56, 01:07`。若用 `0 0/07 0-23 * * ?` 表达全天连续，会在每个整点被重置，导致语义错误。

## 上游依赖 UpStreamList

- `NodeType=PHYSICAL`：依赖真实节点，提供 `SourceNodeId`。**`SourceNodeId` 用上游节点的 output name（任务名），不是物理 `n_xxx` NodeId**——根节点用 `virtual_root_node_xxx`，真实任务节点用其任务名（与 `NodeOutputNameList` 一致）；`SourceNodeOutputName` 同填该 output name。
- `NodeType=LOGICAL`：依赖逻辑表，提供 `SourceTableName` + 可选 `FieldList`
- `PeriodDiff=0` 同周期，`1` 依赖前一个周期
- `DependPeriod.PeriodType` ∈ `CURRENT_PERIOD | LAST_PERIOD | LAST_N_PERIOD`；选 `LAST_N_PERIOD` 时必传 `PeriodOffset`

## 常见坑

1. **`--task-type` 必须为数值**：CLI 和 OpenAPI 要求数值枚举（如 Shell=`10`），传字符串 `"Shell"` 会报 `NumberFormatException`。完整枚举见 `aliyun dataphin-public create-batch-task --help`
2. **基础模式（BASIC）项目必须指定 `--node-output-name-list`**：否则报 `DPN.DataProcess.NodeWithoutDownstream`（无下游依赖，禁止提交）。DEV_PROD 模式无此限制。推荐填 `["<任务名>"]`
3. **NodeOutputNameList** 命名规范：`<项目英文名>.<任务名>` 或直接 `<任务名>`，下游任务依赖你时用此名
4. **先建文件再 Submit**：必须先 `dev create-batch-task` 获得 `FileId`，再 Submit；Submit 不会自动建文件
5. **Engine 与 TaskType 错配**：Python TaskType 传 `PYTHON3_11` 合法；Shell TaskType 传 Engine 会被拒
6. **`UpStreamList.SourceNodeId` 和 `SourceNodeOutputName` 都填节点 Name（output name）**：根节点填 `virtual_root_node_xxx`；**真实任务节点填其 output name（即任务名）**，不是物理 `n_xxx` NodeId。实测依赖链 shell_b→shell_a 时 `SourceNodeId=shell_a`（任务名）成功，传 `n_xxx` 会报 `DPN.DataProcess.NodeUpstreamNotExist`。
7. **小时调度多时间点 cron**：分钟相同时用单 cron 多小时，如 `0 45 8,20 * * ?`（08:45、20:45）；**分钟不同时用 `|` 分隔多条 cron**，如 `0 23 1 * * ?|0 33 19 * * ?`（01:23、19:33），无需 `CustomScheduleConfig`（实测 `CustomScheduleConfig=null`）。❌ 笛卡尔积 `0 23,33 1,19 * * ?` 会展开成 01:23/01:33/19:23/19:33 共 4 个时点，是错误的。
8. **`submit-batch-task` 不支持 `--data-source-id`**：传 `--data-source-id` 会报 `error: unknown option '--data-source-id'`。数据源在 `update-batch-task` 阶段已保存，提交时无需重传
9. **离线计算任务目录必须预建**：`create-batch-task --folder-path "/cli/dbsql"` 时，目录 `/cli/dbsql` 必须已存在，否则报 `DPN.Resource.DirectoryNotFound`。需先 `create-directory /cli`，再 `create-directory /cli/dbsql` 逐级创建
10. **submit ≠ 上线，必须 publish**：`submit-batch-task` 成功返回 `NodeId`/`SubmitId` 后，节点**并未**进入运维区调度，`get-physical-node` 会报 `DPN.OP.NodeNotExist: 租户下不存在对应节点`。必须再用 `publish-object-list --submit-id-list <SubmitId> --comment "..."` 发布，节点才上线（`Status=normal`）。完整链路：`create-batch-task`(--env DEV) → `submit-batch-task` → `publish-object-list`。
11. **`--up-stream-list` 传单对象，不带外层 `[]`**：实测传 `"[{...}]"` 会报 `Expected BEGIN_OBJECT but was BEGIN_ARRAY at path $.upStreamList[0]`；正确写法是直接传对象 `"{"NodeType":"PHYSICAL",...}"`。多个上游用空格分隔多个对象。同理 `--node-output-name-list` 传单值即可（如 `cli_test`），无需 `"[...]"`。
12. **`MINUTELY`（分钟级）调度必须传 `--custom-schedule-config`，否则产品页面显示异常**：只传 `--schedule-period MINUTELY --cron-expression "0 0/5 * * * ?"` 时接口返回成功、`CronExpression` 也能查到，但产品页面任务编辑页会显示 `cron 表达式不能为空` 且时间区间显示 `Invalid`，因为分钟调度的前端表单依赖结构化的 `CustomScheduleConfig` 渲染。**内层 `SchedulePeriod` 枚举值决定调度语义，务必按需求选对，不能随便试**：
    - 全天连续、不按小时重置（"每天从 00:00 到 23:59，每 N 分钟跑一次"，最常见的"每 5 分钟调度一次"就是这个）→ `SchedulePeriod: "DAY"`
      ```json
      {"StartTime":"00:00","EndTime":"23:59","Interval":5,"IntervalUnit":"MINUTE","SchedulePeriod":"DAY"}
      ```
    - 每小时内独立计时、到点重置（"每小时第 0 分钟起，每 N 分钟跑一次，下一小时从头开始"）→ `SchedulePeriod: "HOUR"`
      ```json
      {"StartTime":"00:00","EndTime":"23:59","Interval":5,"IntervalUnit":"MINUTE","SchedulePeriod":"HOUR"}
      ```
    - ⚠️ 枚举值坑：`update-batch-task` 对该字段**不做枚举校验**，传 `HOURLY`/`DAILY` 等错误值也会返回成功并原样存下来（陷阱！），但 `submit-batch-task` 会真正校验，传 `HOURLY` 报 `No enum constant ...CustomIntervalPeriodEnum.HOURLY`，传 `DAILY` 报 `No enum constant ...CustomIntervalPeriodEnum.DAILY`。**唯一合法值是 `DAY` 和 `HOUR`**（官方 CLI 帮助文档里的示例字符串 `DAILY`是文档笔误，不能直接照抄，务必以 `submit-batch-task` 实际调用结果为准）
    - `IntervalUnit` 用 `MINUTE`；`Interval` 是数值间隔（如每 5 分钟传 `5`）
    - `StartTime`/`EndTime` 格式 `HH:mm`，表示当天调度的生效时间窗口
    - 每次 `submit-batch-task`（含改调度）都要带上完整 `--custom-schedule-config`，同 `--up-stream-list` 一样不是增量 patch
    - 验证是否生效必须用 `submit-batch-task` 拿到新 `SubmitId` 后 `get-batch-task-info` 查看 `CustomScheduleConfig`，因为 `update-batch-task` 阶段的"成功"不代表值合法（见上）

## 完整示例（Shell 任务，小时调度 + 租户根节点）

```bash
# 1. 创建目录（如不存在）
aliyun dataphin-public create-directory \
  --profile env25 --project-id <project-id> --tenant-id <tenant-id> \
  --category codeManage --directory-name shell --directory /cli

# 2. 创建任务文件
FILE_ID=$(aliyun dataphin-public create-batch-task \
  --profile env25 --project-id <project-id> --tenant-id <tenant-id> \
  --directory /cli/shell --batch-task-name cli_test \
  --description "CLI test" --schedule-type 1 --task-type 10 \
  --output json | jq -r '.CreateResult.FileId')

# 3. 获取根节点（读 DagId）
ROOT=$(aliyun dataphin-public get-batch-task-info \
  --profile env25 --project-id <project-id> --tenant-id <tenant-id> \
  --file-id $FILE_ID --output json \
  | jq -r '.TaskInfo.DagId | sub("^d_";"")')
ROOT_NODE="virtual_root_node_${ROOT}"

# 4. 提交（capture NodeId/SubmitId；--up-stream-list 传单对象，不带外层 []）
RESULT=$(aliyun dataphin-public submit-batch-task \
  --profile env25 --project-id <project-id> --tenant-id <tenant-id> \
  --file-id $FILE_ID --batch-task-name cli_test \
  --comment "创建Shell任务" \
  --code 'echo "this is a test"' \
  --schedule-period HOURLY \
  --cron-expression "0 45 8,20 * * ?" \
  --node-output-name-list cli_test \
  --up-stream-list "{\"NodeType\":\"PHYSICAL\",\"SourceNodeId\":\"${ROOT_NODE}\",\"SourceNodeOutputName\":\"${ROOT_NODE}\",\"PeriodDiff\":0}")
NODE_ID=$(echo "$RESULT" | jq -r '.CreateResult.NodeId')
SUBMIT_ID=$(echo "$RESULT" | jq -r '.CreateResult.SubmitId')

# 5. 发布上线（submit 仅生成“待发布记录”；不 publish 则 get-physical-node 报 DPN.OP.NodeNotExist）
aliyun dataphin-public publish-object-list \
  --profile env25 --project-id <project-id> --tenant-id <tenant-id> \
  --submit-id-list "$SUBMIT_ID" \
  --comment "发布 cli_test 任务"

# 6. 验证（发布后 .NodeInfo 可查，Status=normal）
aliyun dataphin-public get-physical-node \
  --profile env25 --project-id <project-id> --tenant-id <tenant-id> \
  --node-id "$NODE_ID" --env PROD | jq '.NodeInfo | {Name,ScheduleType,CronExpression,Status}'
# 上游确认：get-node-up-down-stream --id "$NODE_ID" --env PROD → .NodeDagInfo.UpStreamNodeList
# 代码确认：get-physical-node-content --node-id "$NODE_ID" --env PROD → .Data.CodeContent
```

## 相关命令

- `update-batch-task` — 已提交任务的后续编辑（经套件入口 alibabacloud-dataphin-skills 路由加载）
- `find-tenant-root-node` — 获取虚拟根节点（经套件入口路由加载）
- `aliyun dataphin-public create-batch-task` — 先建文件（得到 FileId）
- `aliyun dataphin-public get-batch-task-info --file-id <N>` — 查看任务详情 / 获取 DagId
- `aliyun dataphin-public list-nodes` / `list-instances` — 提交后跟踪运行情况
