---
name: update-pipeline-task
description: |-
  修改已存在的集成管道任务配置（调度 / 通道 / 组件 / 基本信息），采用「先查后改、全量回写」模式。
  触发场景：修改管道任务调度周期 / cron / 重跑策略 / 优先级 / 上游依赖 / 资源组；修改并发数、脏数据上限、超时；修改 reader-writer 字段映射 / 过滤条件 / 分区表达式；修改后重新提交。
  触发词：修改管道任务、更新管道、修改调度配置、改 cron、修改同步任务、update-pipeline、修改并发、修改脏数据、修改字段映射、重新提交管道。
  关键限制：update-pipeline 是全量覆盖而非增量 patch——node-info / pipeline-config / schedule-config 均必填，必须先 get-pipeline-by-id 回读再改；19 位大整数 ID 字符串传参。
---

# 修改集成管道任务配置（调度 / 通道 / 组件）

## 1. Scenario Description

对**已存在**的 Dataphin 集成管道任务（离线/实时 pipeline）做配置变更，覆盖四类修改：

| 修改类别 | 对应参数 | 典型内容 |
|---|---|---|
| 调度配置 | `--schedule-config` | cron 表达式、调度周期、重跑策略、优先级、上游依赖、资源组、生效区间 |
| 通道配置 | `--settings` | 并发数、脏数据上限、SQL 超时、资源规格、重试次数 |
| 组件配置 | `--pipeline-config` | reader/writer 的 PluginConfig（字段映射、过滤条件、分区表达式） |
| 基本信息 | `--node-info` / `--comment` | 任务名、备注 |

**核心模式：先查后改、全量回写**——`update-pipeline` 的 `node-info` / `pipeline-config` / `schedule-config` 均为必填，服务端按提交内容整体覆盖。必须先用 `get-pipeline-by-id` 回读当前完整配置，只改目标字段，其余原样回传，否则会**丢失未回传的配置**。

**Architecture**：`Dataphin Tenant + Project + Pipeline（Steps/Hops + ScheduleConfig + Settings）`。

> 💡 新建管道任务请用兄弟 skill `create-pipeline-task`（经套件入口路由加载）；本 skill 只负责修改已有任务。

## 2. Installation

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```

（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

**Pre-check: Aliyun CLI >= 3.4.8 required**
> Run `aliyun version` to verify >= 3.4.8. If not installed or version too low,
> see `references/cli-installation-guide.md` for the OS-specific installation script.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [`../../ram-policies.md`](../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--tenant-id` | 是 | 租户 ID（19 位 snowflake，**字符串传**；多租户共享 endpoint 时必须显式传项目所属租户） | — |
| `--project-id` | 是 | 项目 ID | — |
| `--context` | 是 | 请求上下文：`--context Env=DEV ProjectId=<project-id>`（Env 取 `DEV`/`PROD`；与 `--project-id` 同时传） | — |
| `--pipeline-id` / `--file-id` / `--node-id` | 三选一 | 定位目标管道任务 | — |
| `--node-info` | 是 | `{"NodeName":"...","PipelineId":<id>}` | — |
| `--pipeline-config` | 是 | Steps/Hops JSON 字符串（未改动也必须完整回传） | — |
| `--schedule-config` | 是 | 调度配置 JSON 字符串 | — |
| `--settings` | 否 | 通道配置 JSON 字符串（不传可能丢失原配置，建议回传） | — |
| `--submit` | 否 | 是否提交（**缺省即提交**；显式传时必须带布尔值 `--submit true|false`，不可裸传） | true |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/update-pipeline-task/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public get-pipeline-by-id --tenant-id "1234567890123456789" \
  --user-agent AlibabaCloud-Agent-Skills/update-pipeline-task/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="..."          # 19 位字符串
PROJECT_ID="..."
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
```

### Step 1 · 回读当前完整配置（必做，禁止跳过）

```bash
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" \
  --context Env=DEV ProjectId=$PROJECT_ID \
  --pipeline-id <pipelineId> \
  --user-agent AlibabaCloud-Agent-Skills/update-pipeline-task/$SESSION_ID
```

- 定位方式三选一：`--pipeline-id`（管道主键）/ `--file-id`（任务文件 ID）/ `--node-id`（调度节点 ID）
- 只知道任务名时：先用 `list-files --category offlinePipeline --directory / --recursive true` 按名称反查 fileId，再用 `--file-id` 查询
- 返回的 `Data.{NodeInfo,PipelineConfig,ScheduleConfig,Settings}` 与 update-pipeline 四个入参一一对应，分别落盘为本地 JSON（如 `current-*.json`），作为回写基线

### Step 2 · 局部修改目标字段

只改用户要求的字段，其余**原样保留**。按修改类别：

#### 2a. 修改调度配置（`--schedule-config`）

> 💡 修改场景优先直接在回读的 `Data.ScheduleConfig`（camelCase JSON，如 `cronExpression`/`priority`/`taskUpstreamNodes`）上改目标字段后原样回传，已真机验证可直接提交生效。下面的 PascalCase 骨架仅供新建任务 / 字段含义参考：

```jsonc
{
  "ScheduleType": "NORMAL",
  "CronExpression": "0 0 2 * * ?",          // ⚠ 字段名是 CronExpression，不是 ScheduleCron
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
    { "NodeType": "PHYSICAL", "SourceNodeId": "<上游节点ID>", "SourceNodeOutputName": "<上游输出名>", "PeriodDiff": 0 }
  ],
  "NodeOutputNameList": ["<本任务输出名>"]
}
```

改周期示例：天调度 → 每小时：回读 JSON 中 `cronExpression: "0 0 * * * ?"` + `scheduleIntervalType: "HOURLY"`。

#### 2b. 修改通道配置（`--settings`）

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
  "ConnectRetryTime": [ { "RetryTimes": 1, "DsId": "<reader 数据源ID>" } ]
}
```

#### 2c. 修改组件配置（`--pipeline-config`）

- Steps/Hops 结构与新建时完全相同，骨架见兄弟 skill 参考 [../create-pipeline-task/references/pipeline-config.md](../create-pipeline-task/references/pipeline-config.md)
- 每个 `Steps[].PluginConfig` 必须是 **JSON 字符串**（先 stringify 再放入）
- 修改字段映射时，reader.column 与 writer.column（及 columnMappings）必须保持一一对应、顺序一致

### 执行前确认（写操作 HITL，必须）

> 本 skill 涉及写操作（update-pipeline 会覆盖线上任务配置并默认提交），调用方执行前必须向用户二次确认：
> - 即将执行的命令全文（脱敏后）
> - **变更 diff**：哪些字段从什么值改成什么值；哪些配置原样回传
> - 影响范围（tenant / project / env / pipeline 名称与 ID）
> - 是否可回滚（Step 1 落盘的 `current-*.json` 即回滚基线，可用同一命令回写恢复）
> - 替代方案（仅回读检查不提交 / 使用 `--submit false` 保存草稿不提交）

仅当用户明确回复"确认 / yes / 执行"后才发起命令。

### Step 3 · 全量回写并提交

```bash
aliyun dataphin-public update-pipeline \
  --tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" \
  --context Env=DEV ProjectId=$PROJECT_ID \
  --node-info "$(cat current-node-info.json)" \
  --pipeline-config "$(cat pipeline-config.json)" \
  --schedule-config "$(cat schedule-config.json)" \
  --settings "$(cat settings.json)" \
  --submit true \
  --user-agent AlibabaCloud-Agent-Skills/update-pipeline-task/$SESSION_ID
```

- `--pipeline-config` / `--schedule-config` 即使**没改也必须完整回传**（必填 + 覆盖语义）
- 只想保存草稿不提交：传 `--submit false`；`--submit` 缺省即提交，但**不可裸传** `--submit`（会把后面的 flag 当作布尔值解析报错）

### 可选：异步变体（配置体量大 / 同步超时时）

```bash
aliyun dataphin-public update-pipeline-by-async \
  --tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --context Env=DEV ProjectId=$PROJECT_ID \
  --node-info '...' --pipeline-config '...' --schedule-config '...' --settings '...' --submit true \
  --user-agent AlibabaCloud-Agent-Skills/update-pipeline-task/$SESSION_ID

# 用返回的异步 ID 轮询结果
aliyun dataphin-public get-pipeline-async-result \
  --tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --async-id <asyncId> --env DEV \
  --user-agent AlibabaCloud-Agent-Skills/update-pipeline-task/$SESSION_ID
```

## 9. Success Verification

三步法：

1. 同步返回 `Code: OK` / `Success: true` ≠ 业务成功，仅代表请求受理
2. `get-pipeline-by-id` 回读，**逐字段比对**目标字段已变更、未改字段未丢失：

```bash
aliyun dataphin-public get-pipeline-by-id \
  --tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --context Env=DEV ProjectId=$PROJECT_ID \
  --pipeline-id <pipelineId> \
  --user-agent AlibabaCloud-Agent-Skills/update-pipeline-task/$SESSION_ID
```

3. 带 `--submit` 提交的变更，如需发布到 PROD，走 `grant-data-source-permission` skill 的发布生效校验链（`publish-object-list` → `list-publish-records`）

## 10. Cleanup

本 skill 不新建资源，无需清理。误改回滚方式：

```bash
# 用 Step 1 落盘的回滚基线原样回写
aliyun dataphin-public update-pipeline \
  --tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --context Env=DEV ProjectId=$PROJECT_ID \
  --node-info "$(cat current-node-info.json)" \
  --pipeline-config "$(cat current-pipeline-config.json)" \
  --schedule-config "$(cat current-schedule-config.json)" \
  --settings "$(cat current-settings.json)" \
  --submit true \
  --user-agent AlibabaCloud-Agent-Skills/update-pipeline-task/$SESSION_ID
```

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参
2. 写操作必须执行前 HITL 二次确认，且确认信息中包含**变更 diff**
3. 修改前必须落盘回滚基线（`current-*.json`）
4. 「常见坑」每条标来源 `[Agent 自主发现] / [人工注入]`

### 常见坑

#### [Agent 自主发现] update-pipeline 是全量覆盖，不是增量 patch
- 现象：只传改动的 `--schedule-config`、漏传/简传 `--pipeline-config`，提交后 Steps 配置丢失或报参数缺失
- 结论：`node-info` / `pipeline-config` / `schedule-config` 均为 CLI 必填；必须先 `get-pipeline-by-id` 回读完整配置，只改目标字段、其余原样回传

#### [Agent 自主发现] `--context Env=xxx ProjectId=xxx` 是必填参数
- 现象：只传 `--env DEV` 或只传 `--project-id`，报 `Error: --context is required` / `--project-id is required`
- 结论：`get-pipeline-by-id` / `update-pipeline` / `update-pipeline-by-async` 均需同时传 `--context Env=<DEV|PROD> ProjectId=<project-id>` 和 `--project-id`（真机验证）

#### [Agent 自主发现] `--submit` 裸传会吞掉下一个 flag
- 现象：`--submit --user-agent ...` 报 `invalid boolean value: --user-agent`；另外缺省即默认提交，本想只存草稿结果直接进入调度
- 结论：`--submit` 为 bool 参数，显式传时必须带值（`--submit true` / `--submit false`）；仅保存草稿需显式传 `--submit false`

#### [Agent 自主发现] 回读配置可原样回传（camelCase round-trip）
- 现象：回读的 `Data.ScheduleConfig` 为 camelCase（`cronExpression` 等），与骨架里的 PascalCase 不同
- 结论：`Data.{NodeInfo,PipelineConfig,ScheduleConfig,Settings}` 与 update-pipeline 四个入参一一对应，直接在回读 JSON 上改字段后原样回传即可提交生效（真机验证：改 cron → 提交 → 反查生效 → 回滚成功）

#### [人工注入] 调度 cron 字段名是 `CronExpression`
- 现象：用 `ScheduleCron` 报「调度周期表达式为空」
- 结论：`schedule-config` 中 cron 字段名固定为 `CronExpression`

#### [人工注入] `PluginConfig` 必须是 JSON 字符串
- 现象：嵌套对象直接传入触发反序列化失败；空 `"{}"` 触发 ClassCastException
- 结论：每个插件 config 先 stringify 再放进 `Steps[].PluginConfig`，且最少带 `dsName`/`dsId`/`dsType`/`table`/`columns`

#### [人工注入] `--tenant-id` 必须与项目所属租户一致
- 现象：多租户共享 endpoint 时报 `DPN.Filter.ProjectNotFound`
- 结论：即使 profile 已配 tenant_id，也要显式传项目所属租户 ID

#### [人工注入] `UpStreamList` 不能为空
- 现象：清空上游后提交报 `NodeWithoutUpstream`
- 结论：无业务上游时挂租户虚拟根节点，见 `find-tenant-root-node`（经套件入口路由加载）

#### [人工注入] `columnMappings` 顺序敏感
- 现象：调整字段映射后跑批数据错位
- 结论：`inputColumnIndex` 从 0 开始且必须与 reader `columns` 顺序对齐

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
- [`../create-pipeline-task/references/pipeline-config.md`](../create-pipeline-task/references/pipeline-config.md)（Steps/Hops/PluginConfig 完整骨架）
- `create-pipeline-task`（经套件入口路由加载）（新建管道任务）
