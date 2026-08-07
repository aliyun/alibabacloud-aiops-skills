---
name: monitor-task-instance
description: |
  监控 Dataphin 调度任务实例的运行状态、获取执行日志、排查未运行或失败原因。触发场景：查看实例状态 / 查日志 / 任务没跑 / 实例 WAIT_SCHEDULE / 实例 FAILED / 任务运行失败 / 排查未运行原因 / 获取 taskrun 日志。流程：list-instances 定位实例 → get-physical-instance 查看详情 → get-physical-instance-log 获取日志。关键点：bizdate 默认 T-1；list-instances 返回字段在 .PageResult.Data[].NodeInfo.Name 和 .StatusList；多时点调度的同一业务日期会有多个实例；WAIT_SCHEDULE 且 DueTime 未到、BlockType/WaitReason 为空属正常；SchedulePaused=true 表示节点被暂停。触发词：实例状态、查看日志、任务没跑、WAIT_SCHEDULE、FAILED、任务监控、实例监控、taskrun、运行日志、排查实例。
---

# 任务实例监控与日志查询 Skill

## 1. Scenario Description

场景：需要查看 Dataphin 周期任务某个业务日期的实例状态、拉取执行日志，或诊断实例为何未运行/失败。

本 Skill 覆盖实例定位、状态查看、日志拉取、常见未运行原因诊断的完整流程。

### Architecture

```
用户请求 → 确认参数 → list-instances 定位实例
  → get-physical-instance 查看实例详情与状态
  → get-physical-instance-log 拉取 taskrun 日志
  → 根据状态与字段诊断原因
```

### 涉及 Dataphin OpenAPI

- `ListInstances` — 按任务名 + 业务日期查询实例列表
- `GetPhysicalInstance` — 查询单个实例详情（含状态、暂停标记、阻塞原因、上下游）
- `GetPhysicalInstanceLog` — 查询实例 taskrun 日志

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8）
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun dataphin-public --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

> **Security Rules:**
> - **NEVER** 读取、回显或打印凭证环境变量（禁止对 AccessKey ID / Secret 做任何输出或日志）
> - **NEVER** 要求用户在本会话或命令行直接输入 AK/SK
> - **NEVER** 使用 `aliyun configure set` 写入字面量凭证
> - **ONLY** 使用 `aliyun configure list` 检查凭证状态
>
> ```bash
> aliyun configure list
> ```
> 检查输出中是否存在有效 profile（AK、STS 或 OAuth 身份）。
>
> **如果没有有效 profile，请在此停止。**
> 1. 从 [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak) 获取凭证
> 2. 在会话外配置（终端执行 `aliyun configure`，或在 shell profile 中设置环境变量）
> 3. 重新运行 `aliyun configure list` 确认有效后再继续

### Pre-check: Aliyun CLI plugin update required

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
>
> 执行前确认 CLI 与插件版本：
> ```bash
> aliyun version
> aliyun plugin list
> ```

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 skill 最小权限见 [../../ram-policies.md](../../ram-policies.md)。

## 6. IMPORTANT: Parameter Confirmation

执行查询前必须向用户确认以下参数：

| 参数 | 说明 |
|------|------|
| `--env` | DEV 或 PROD（默认 PROD） |
| `--project-id` | 项目 ID |
| `--search-text` | 任务/节点名称 |
| `--min-biz-date` / `--max-biz-date` | 业务日期闭区间，格式 `yyyymmdd` |

## 7. 完整命令链

```bash
TENANT_ID=<tenant-id>
PROJECT_ID=<project-id>
ENV=PROD
USER_AGENT="AlibabaCloud-Agent-Skills/monitor-task-instance/{session-id}"

# 1) 取真实业务日期（绝对不要依赖会话上下文时间）
TODAY=$(date "+%Y%m%d")
BIZDATE=$(date -v-1d "+%Y%m%d")  # macOS；Linux: date -d "-1 day" "+%Y%m%d"
echo "今天=$TODAY 业务日期(T-1)=$BIZDATE"

# 2) 定位实例（同一业务日期可能有多个 due-time 实例）
aliyun dataphin-public list-instances --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --schedule-type NORMAL --search-text "<task-name>" \
  --min-biz-date $BIZDATE --max-biz-date $BIZDATE \
  --page 1 --page-size 20 \
  --user-agent "$USER_AGENT" --format json \
  | jq '.PageResult.Data[] | {
       InstanceId: .Id,
       NodeName: .NodeInfo.Name,
       BizDate: (.BizDate/1000|todate),
       DueTime: (.DueTime/1000|todate),
       Status: .StatusList,
       Duration,
       StartTime: (if .StartExecuteTime then .StartExecuteTime/1000|todate else null end),
       EndTime: (if .EndExecuteTime then .EndExecuteTime/1000|todate else null end)
     }'

# 3) 查看单个实例详情（含阻塞/暂停/等待原因）
INSTANCE_ID=<上一步返回的 Id>
aliyun dataphin-public get-physical-instance --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --instance-id $INSTANCE_ID \
  --user-agent "$USER_AGENT" --format json \
  | jq '.Instance | {
       Id,
       Name,
       BizDate: (.BizDate/1000|todate),
       DueTime: (.DueTime/1000|todate),
       StatusList,
       SchedulePaused,
       BlockType,
       WaitReason,
       UpStreamList: (.UpStreamList | length),
       DownStreamList: (.DownStreamList | length)
     }'

# 4) 拉取实例日志（taskrun 级）
aliyun dataphin-public get-physical-instance-log --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --instance-id $INSTANCE_ID \
  --user-agent "$USER_AGENT" --format json \
  | jq '.TaskrunLogList[] | {TaskrunId, Status, StartTime, EndTime, Duration, LogContent}'
```

## 8. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/monitor-task-instance/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 9. 参数要点

| 参数 | 必填 | 取值 | 备注 |
|---|---|---|---|
| `--search-text` | 推荐 | 任务/节点名称 | list-instances 支持模糊搜索 |
| `--min-biz-date` / `--max-biz-date` | 推荐 | `yyyymmdd` 字符串 | 闭区间；默认 T-1 |
| `--schedule-type` | 可 | `NORMAL` / `MANUAL` / `SUPPLEMENT` | 默认 PROD 下周期实例用 `NORMAL` |
| `--instance-id` | 必（get/log） | `t_xxx` 字符串 | list-instances 返回的 `.Id` |
| `--env` | 可 | `DEV` / `PROD`（默认 PROD） | 必须与实例所在环境一致 |

## 10. 状态诊断

| 状态 | 含义 | 排查方向 |
|---|---|---|
| `WAIT_SCHEDULE` | 等待调度 | 正常：检查 `DueTime` 是否已到；异常：检查 `BlockType` / `WaitReason` |
| `WAITING` | 等待上游或资源 | 查看 `UpStreamList` 是否全部 SUCCESS；检查资源组排队 |
| `RUNNING` | 运行中 | 拉日志观察实时进度 |
| `SUCCESS` | 成功 | 可拉日志确认产出与耗时 |
| `FAILED` | 失败 | 必须拉日志看错误堆栈 |
| `PAUSED` | 实例被暂停 | 检查节点 `SchedulePaused` 或实例暂停状态 |

### WAIT_SCHEDULE 诊断

```bash
aliyun dataphin-public get-physical-instance --dataphin-profile <p> --env $ENV \
  --project-id $PROJECT_ID --tenant-id $TENANT_ID \
  --instance-id $INSTANCE_ID --format json \
  | jq '.Instance | {DueTime: (.DueTime/1000|todate), StatusList, SchedulePaused, BlockType, WaitReason}'
```

判断逻辑：
- `DueTime` 未到 + `BlockType`/`WaitReason` 为空 → **正常等待**，到点自动调度
- `DueTime` 已过 + 仍为 `WAIT_SCHEDULE` → 检查 `SchedulePaused` / `BlockType` / `WaitReason`
- `SchedulePaused=true` → 节点被暂停，需 `resume-physical-node`
- `BlockType`/`WaitReason` 非空 → 按具体原因处理（上游未就绪、资源不足等）

## 11. 常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| `list-instances` 返回空 | 任务名拼写错误 / bizdate 范围错误 / `--env` 不匹配 | 核对任务名，使用 T-1 业务日期，确认 `--env` |
| `get-physical-instance` 返回空 / 404 | instance-id 错误或 `--env` 与实例环境不一致 | 用 list-instances 重新确认实例 ID 和环境 |
| `get-physical-instance-log` 返回空 `TaskrunLogList` | 实例尚未运行（WAIT_SCHEDULE）或从未产生 taskrun | 实例运行后再查；WAIT_SCHEDULE 正常无日志 |
| `.NodeInfo.Name` 为 null | list-instances 返回的可能是 summary 字段 | 使用完整路径 `.PageResult.Data[].NodeInfo.Name` |

## 12. ✗ 不要做

- ✗ 用调度日填 `bizdate`：实例按业务日期索引，默认 T-1
- ✗ 未确认 `--env` 就查询：DEV/PROD 实例隔离
- ✗ 看到 `WAIT_SCHEDULE` 直接判定异常：先对比 `DueTime` 和当前时间
- ✗ 未带 `--user-agent` 调用 aliyun API 命令
- ✗ 硬编码真实 tenant-id / project-id / instance-id

## 13. 相关命令

- `aliyun dataphin-public list-instances` — 按任务名 + 业务日期查实例
- `aliyun dataphin-public get-physical-instance` — 单个实例详情（状态、阻塞、暂停）
- `aliyun dataphin-public get-physical-instance-log` — taskrun 执行日志
- `aliyun dataphin-public list-nodes` — 查询节点元数据（含 SchedulePaused）
- `aliyun dataphin-public resume-physical-node` — 恢复被暂停的节点
- `rerun-task-instance` — 实例重跑（经套件入口 alibabacloud-dataphin-skills 路由加载）
- `pause-task-instance` — 实例暂停/恢复（经套件入口路由加载）
