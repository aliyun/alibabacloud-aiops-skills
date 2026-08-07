---
name: pause-task-instance
description: |
  暂停/恢复 Dataphin 调度任务实例（按任务名 + 业务日期 + 运行时点定位并触发 PAUSE/RESUME）。触发场景：实例暂停 / 暂停调度 / 恢复调度 / pause / resume / operate-instance PAUSE / 阻止实例被调度拉起 / 小时任务暂停某个时点。完整流程：list-instances（按 bizdate + DueTime 筛选）→ operate-instance(PAUSE/RESUME) → get-physical-instance 验证 SchedulePaused。关键点：bizdate 默认 T-1（今日运行的实例业务日期通常是昨天）；小时任务一个 bizdate 有多个实例，需按 DueTime 选定时点；PAUSE 成功后实例 StatusList 可能仍为 WAIT_SCHEDULE，真正判据是 NodeInfo.SchedulePaused=true。触发词：暂停实例、pause、恢复实例、resume、operate-instance PAUSE、暂停调度、阻止调度。
---

# 暂停/恢复任务实例 Skill

## 1. Scenario Description

场景：周期任务在某个业务日期的实例尚未运行（`WAIT_SCHEDULE`），但需要阻止其在到达调度时间点时被拉起；或已暂停后需要恢复调度。典型用途：

- 小时任务某个时点的实例暂时不想跑（如 20:45 实例先暂停，待数据就绪后再恢复）
- 实例等待调度时临时挂起，避免占用资源或误触发

本 Skill 按「任务名 + 业务日期 + 运行时点（DueTime）」定位实例，执行 `OperateInstance --operation PAUSE`（暂停）或 `RESUME`（恢复），并给出验证方法。

### Architecture

```
用户请求 → 确认参数 → list-instances 按 bizdate 查询
  → 按 DueTime 筛选目标时点实例 → operate-instance PAUSE/RESUME
  → get-physical-instance 验证 SchedulePaused → 输出结论
```

涉及 Dataphin OpenAPI：

- `ListProjects` — 枚举项目（同名任务可能跨项目）
- `ListInstances` — 按任务名 + 业务日期查实例，输出 `DueTime`（毫秒时间戳）
- `OperateInstance` — 触发 PAUSE / RESUME
- `GetPhysicalInstance` — 验证 `NodeInfo.SchedulePaused`

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

### Pre-check: Aliyun CLI >= 3.4.8 required

> 运行 `aliyun version` 确认版本 >= 3.4.8。若未安装或版本过低，从 https://aliyuncli.alicdn.com 安装/升级（见 `references/cli-installation-guide.md`）。

### Pre-check: Aliyun CLI plugin update required

> [MUST] 运行 `aliyun configure set --auto-plugin-install true` 开启自动插件安装。
> [MUST] 运行 `aliyun plugin update` 确保插件为最新版本。

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 Skill 涉及的最小权限：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataphin:ListProjects",
        "dataphin:ListInstances",
        "dataphin:OperateInstance",
        "dataphin:GetPhysicalInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

详见 [RAM 策略参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

执行前必须向用户确认以下参数：

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--op-tenant-id` / `--tenant-id` | 条件 | 租户 ID；profile 已配置时可省略 | `300115489` |
| `--dataphin-profile` / `--profile` | 条件 | 本地 profile 名；省略则使用 current profile | `env23` |
| `--env` | 推荐 | `DEV` / `PROD`（默认 `PROD`） | `PROD` |
| `TASK_NAME` | 必 | 要暂停/恢复的任务名称 | `cli_test` |
| `BIZ_DATE` | 推荐 | 业务日期 `yyyymmdd`；省略则取 T-1 | `20260629` |
| `DUE_TIME` | 可选 | 目标运行时点 `HH:MM`；小时任务多实例时用于筛选 | `20:45` |
| `OPERATION` | 必 | `PAUSE` 或 `RESUME` | `PAUSE` |
| `PROJECT_ID` | 可选 | 若已知项目 ID，可直接指定，跳过跨项目遍历 | `7295715579274176` |

## 7. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/pause-task-instance/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 8. Core Workflow

### 8.1 计算业务日期

```bash
# 优先使用真实系统日期，不要依赖会话上下文时间
TODAY=$(date "+%Y%m%d")
# macOS
BIZDATE=$(date -v-1d "+%Y%m%d")
# Linux 用：BIZDATE=$(date -d "-1 day" "+%Y%m%d")
echo "today=$TODAY bizdate=$BIZDATE"
```

> **关键**：Dataphin 默认 `bizdate = T-1`。用户说「当日 20:45 运行的实例」时，该实例的业务日期通常是**昨天**（T-1），而不是今天。若用今日作为 bizdate 查不到实例，请回退到 T-1。

### 8.2 定位目标实例

#### 已知项目 ID

```bash
ENV=PROD
PROJECT_ID="<project-id>"
TASK_NAME="<task-name>"
BIZDATE="<biz-date>"

aliyun dataphin-public list-instances \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --schedule-type NORMAL \
  --search-text "$TASK_NAME" \
  --min-biz-date "$BIZDATE" \
  --max-biz-date "$BIZDATE" \
  --page 1 --page-size 50 \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/pause-task-instance/{session-id} \
  | jq -r '.PageResult.Data[]? | "\(.Id)\t\(.NodeInfo.Name)\t\(.DueTime)\t\(.StatusList|join(","))"'
```

#### 按运行时点筛选（小时任务）

`DueTime` 是毫秒时间戳。将其转为 `HH:MM` 后筛选目标时点：

```bash
TARGET_HHMM="20:45"

aliyun dataphin-public list-instances \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --schedule-type NORMAL \
  --search-text "$TASK_NAME" \
  --min-biz-date "$BIZDATE" \
  --max-biz-date "$BIZDATE" \
  --page 1 --page-size 50 \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/pause-task-instance/{session-id} \
  | jq -r '.PageResult.Data[]? | "\(.Id)\t\(.DueTime)"' \
  | while IFS=$'\t' read -r ID DUE; do
      HM=$(date -r $((DUE/1000)) "+%H:%M")
      if [[ "$HM" == "$TARGET_HHMM" ]]; then
        echo "$ID $HM"
      fi
    done
```

> Linux 上 `date -r` 改为 `date -d @<秒>`。

#### 未知项目 ID（跨项目搜索）

```bash
PROJECTS=$(aliyun dataphin-public list-projects \
  --env "$ENV" \
  --page-no 1 --page-size 100 \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/pause-task-instance/{session-id} \
  | jq -r '.PageResult.ProjectList[] | "\(.Id) \(.Name)"')

while read -r PID PNAME; do
  aliyun dataphin-public list-instances \
    --env "$ENV" \
    --project-id "$PID" \
    --schedule-type NORMAL \
    --search-text "$TASK_NAME" \
    --min-biz-date "$BIZDATE" \
    --max-biz-date "$BIZDATE" \
    --page 1 --page-size 50 \
    --format json \
    --user-agent AlibabaCloud-Agent-Skills/pause-task-instance/{session-id} \
    | jq -r --arg pid "$PID" --arg pname "$PNAME" \
        '.PageResult.Data[]? | "\(.Id)\t\(.NodeInfo.Name)\t\(.DueTime)\t\($pid)\t\($pname)\t\(.StatusList|join(","))"'
done <<< "$PROJECTS"
```

如果匹配到多条实例，**必须向用户展示并确认唯一目标**，不要直接全部暂停。

### 8.3 HITL 确认

在执行写操作前，向用户确认：

> 即将对以下实例执行 `$OPERATION`（PAUSE / RESUME）：
> - 实例 ID：`t_xxxx`
> - 任务名：`cli_test`
> - 节点 ID：`n_xxxx`
> - 项目：`test1_dev (7295715579274176)`
> - 环境：`PROD`
> - 业务日期：`20260629`
> - 运行时点：`20:45`
>
> 确认执行？（yes/no）

### 8.4 触发暂停/恢复

```bash
ENV=PROD
PROJECT_ID="<project-id>"
INSTANCE_ID="<instance-id>"
OPERATION=PAUSE   # 恢复时改为 RESUME

aliyun dataphin-public operate-instance \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --operation "$OPERATION" \
  --instance-id-list "{\"Id\":\"$INSTANCE_ID\"}" \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/pause-task-instance/{session-id}
```

返回 `Success=true` 且 `InstanceStatusList[].Status == "SUCCESS"` 仅表示运维指令已下发，必须继续验证。

> **RESUME 语义**：恢复调度后实例回到 `WAIT_SCHEDULE`，到点（DueTime）会被调度自动拉起执行。
> - 若需**立即手动触发**执行，不要用 RESUME（它只恢复调度等待），应改用 `--operation RERUN`（见同套件子 skill `rerun-task-instance`，经套件入口路由加载）。
> - RESUME 不改变实例已有的 `StatusList`（如仍为 `WAIT_SCHEDULE`），只把 `SchedulePaused` 从 `true` 切回 `false`。

### 8.5 验证

```bash
aliyun dataphin-public get-physical-instance \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --instance-id "$INSTANCE_ID" \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/pause-task-instance/{session-id} \
  | jq '.Instance | {Id, StatusList, SchedulePaused:.NodeInfo.SchedulePaused, DueTime, BizDate}'
```

> **验证要点**：`get-physical-instance` 返回结构是 `.Instance`（不是顶层）。PAUSE 成功的判据是 `.Instance.NodeInfo.SchedulePaused == true`，**而不是 `StatusList` 变为 `PAUSED`**。暂停后实例 `StatusList` 仍可能显示 `WAIT_SCHEDULE`，这是正常的——它表示实例仍在等待，但调度已被挂起，不会被拉起。

## 9. Success Verification Method

- `operate-instance` 返回 `Success=true` 且 `InstanceStatusList[].Status == "SUCCESS"`，说明指令下发成功。
- `get-physical-instance` 确认：
  - PAUSE 后：`.Instance.NodeInfo.SchedulePaused == true`
  - RESUME 后：`.Instance.NodeInfo.SchedulePaused == false`
- **RESUME 后 `StatusList` 仍为 `WAIT_SCHEDULE` 属正常**：表示实例已回到正常等待调度状态，到点会自动执行；判据是 `SchedulePaused=false`，不是 `StatusList` 变化。
- 若 `SchedulePaused` 未变化，检查 `--project-id` / `--env` 是否与实例匹配。

## 10. Cleanup

本 Skill 仅切换实例调度状态，不创建新的 Dataphin 资源，无需清理。
若需要恢复，执行 `--operation RESUME` 即可。

## 11. Command Tables

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

1. **业务日期默认 T-1**：用户说「当日运行的实例」时，bizdate 通常是昨天。用今日查不到实例应回退到 T-1。
2. **小时任务按 DueTime 筛选**：一个 bizdate 可能展开成多个时点实例（如 `0 45 8,20 * * ?` → 08:45 / 20:45），必须按 `DueTime` 选定，不能凭 bizdate 唯一定位。
3. **PAUSE 验证看 SchedulePaused**：暂停后 `StatusList` 可能仍是 `WAIT_SCHEDULE`，判据是 `NodeInfo.SchedulePaused=true`。
4. **实例与项目必须匹配**：`operate-instance` 的 `--project-id` 必须是实例所属项目，否则报 `DPN.OP.ProjectNotExist`。
5. **大整数 ID 作为字符串传递**：`--instance-id-list` 的 `Id` 值必须用引号包裹。
6. **恢复用 RESUME**：暂停后如需继续调度，用 `--operation RESUME`，不要用 RERUN（RERUN 是重新执行，不是恢复调度）。

## 13. Reference Links

| 文档 | 说明 |
|------|------|
| [CLI 安装指南](./references/cli-installation-guide.md) | aliyun CLI 与 dataphin-public 插件安装 |
| [RAM 策略参考](../../ram-policies.md) | 最小 RAM 权限与失败处理 |
| [验收标准](./references/acceptance-criteria.md) | 正确/错误命令模式 |
| [相关命令索引](./references/related-commands.md) | 本 Skill 涉及的 CLI 命令 |
