---
name: rerun-task-instance
description: |
  重跑 Dataphin 调度任务实例，支持两种模式：①单实例/批量重跑（operate-instance RERUN）；②重跑下游链路（fix-data，联动重跑根实例及所有下游）。触发场景：周期实例失败需要重跑 / rerun / 重跑实例 / operate-instance / fix-data / 重跑下游 / 修复链路数据 / 实例恢复 / 任务运维。模式①流程：list-projects → list-instances → operate-instance(RERUN) → get-physical-instance-log 验证。模式②流程：list-instances → fix-data(--root-instance-id) → get-physical-instance-log 验证 taskrun。关键点：实例必须属于指定的 project-id；bizdate 默认 T-1；fix-data 的 --root-instance-id 必须传 JSON 对象 {"Id":"t_xxx"}；fix-data 不创建新实例而是创建新 taskrun，验证需查 taskrun 日志。触发词：重跑实例、rerun、任务重跑、operate-instance、fix-data、重跑下游、修复链路数据、实例恢复、补跑实例。
---

# 重跑任务实例 Skill

## 1. Scenario Description

场景：已发布/运行的周期任务在某个业务日期的实例状态异常（FAILED、WAIT_SCHEDULE 超时、被 PAUSE 等），需要手动触发重新执行。

本 Skill 支持两种重跑模式：
- **模式① — 单实例/批量重跑**：按「任务名称 + 业务日期」定位实例，执行 `OperateInstance --operation RERUN`。
- **模式② — 重跑下游链路（fix-data）**：以根实例为起点，联动重跑该实例及其所有下游节点，适用于修复整条数据链路。

### Architecture

```
模式①（单实例重跑）：
用户请求 → 确认参数 → 遍历项目定位实例 → operate-instance RERUN
  → 查询实例状态 → 若失败则拉日志诊断 → 输出结论

模式②（重跑下游链路）：
用户请求 → 确认参数 → 定位根实例 → fix-data(--root-instance-id, --downstream-range)
  → 查询各实例 taskrun 日志 → 验证重跑结果 → 输出结论
```

涉及 Dataphin OpenAPI：

- `ListProjects` — 枚举项目（同名任务可能跨项目）
- `ListInstances` — 按任务名 + 业务日期查实例
- `OperateInstance` — 触发 RERUN（模式①）
- `FixData` — 重跑下游链路，联动重跑根实例及所有下游（模式②）
- `GetPhysicalInstance` / `GetPhysicalInstanceLog` — 验证状态与日志
- `GetInstanceDownStream` — 查询实例下游拓扑（模式②辅助）

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
        "dataphin:FixData",
        "dataphin:GetPhysicalInstance",
        "dataphin:GetPhysicalInstanceLog",
        "dataphin:GetInstanceDownStream"
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
| `--dataphin-profile` / `--profile` | 条件 | 本地 profile 名；省略则使用 `dataphin-public` current profile | `env23` |
| `--env` | 推荐 | `DEV` / `PROD`（默认 `PROD`） | `PROD` |
| `TASK_NAME` | 必 | 要重跑的任务名称 | `oracle` |
| `BIZ_DATE` | 推荐 | 业务日期 `yyyymmdd`；省略则取 T-1 | `20260629` |
| `PROJECT_ID` | 可选 | 若已知项目 ID，可直接指定，跳过跨项目遍历 | `7283355458594816` |

### fix-data 专属参数（模式②）

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--root-instance-id` | 必 | 根实例 ID，**必须传 JSON 对象** `{"Id":"t_xxx"}`，不能传裸字符串 | `{"Id":"t_8127255632277340160_20260629_8127264978126241798"}` |
| `--downstream-range` | 推荐 | 下游范围：`ALL_INSTANCE`（所有实例）/ `ALL_FAILED_INSTANCE`（所有失败实例）/ `ALL_FINAL_INSTANCE`（所有终态实例）；不传则需手动传 `--down-stream-instance-id-list` | `ALL_INSTANCE` |
| `--contain-root-instance` | 可选 | 根实例是否重跑，默认 `true` | `true` |
| `--force-rerun` | 可选 | 是否强制重跑 | `true` |

## 7. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id}
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
  --page 1 --page-size 20 \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id} \
  | jq '.PageResult.Data[] | {InstanceId:.Id, NodeName:.NodeInfo.Name, NodeId:.NodeInfo.Id, StatusList, BizDate:.BizDate}'
```

#### 未知项目 ID（跨项目搜索）

```bash
ENV=PROD
TASK_NAME="<task-name>"
BIZDATE="<biz-date>"

# 1) 取项目列表
PROJECTS=$(aliyun dataphin-public list-projects \
  --env "$ENV" \
  --page-no 1 --page-size 100 \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id} \
  | jq -r '.PageResult.ProjectList[] | "\(.Id) \(.Name)"')

# 2) 在每个项目中搜索实例
MATCHES=""
while read -r PID PNAME; do
  IDS=$(aliyun dataphin-public list-instances \
    --env "$ENV" \
    --project-id "$PID" \
    --schedule-type NORMAL \
    --search-text "$TASK_NAME" \
    --min-biz-date "$BIZDATE" \
    --max-biz-date "$BIZDATE" \
    --page 1 --page-size 20 \
    --format json \
    --user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id} \
    | jq -r --arg pid "$PID" --arg pname "$PNAME" '
        .PageResult.Data[]? |
        "\(.Id)\t\(.NodeInfo.Name)\t\(.NodeInfo.Id)\t\($pid)\t\($pname)\t\(.StatusList | join(","))"
      ')
  MATCHES="$MATCHES$IDS"
done <<< "$PROJECTS"

echo "$MATCHES"
```

如果匹配到多条实例，**必须向用户展示并确认唯一目标**，不要直接全部重跑。

### 8.3 HITL 确认

在执行写操作前，向用户确认：

> 即将对以下实例执行 RERUN：
> - 实例 ID：`t_xxxx`
> - 任务名：`oracle`
> - 节点 ID：`n_xxxx`
> - 项目：`dataphin_basic01 (7283355458594816)`
> - 环境：`PROD`
> - 业务日期：`20260629`
>
> 确认执行？（yes/no）

### 8.4 触发重跑

```bash
ENV=PROD
PROJECT_ID="<project-id>"
INSTANCE_ID="<instance-id>"

aliyun dataphin-public operate-instance \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --operation RERUN \
  --instance-id-list "{\"Id\":\"$INSTANCE_ID\"}" \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id}
```

返回成功仅表示运维指令已下发，不代表实例最终成功。必须继续验证。

### 8.5 验证与诊断（模式①）

#### 查看实例最新状态

```bash
aliyun dataphin-public get-physical-instance \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --instance-id "$INSTANCE_ID" \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id} \
  | jq '{Id, StatusList, StartExecuteTime, EndExecuteTime, Duration}'
```

#### 若仍为 FAILED，拉取运行日志

```bash
aliyun dataphin-public get-physical-instance-log \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --instance-id "$INSTANCE_ID" \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id} \
  | jq -r '.TaskrunLogList[-1].LogContent'
```

> 日志可能很长，建议重定向到文件后检索 `ERROR`、`Exception`、`失败` 等关键字。

### 8.6 重跑下游链路（fix-data，模式②）

适用于需要联动重跑根实例及其所有下游节点的场景（如修复整条数据链路）。

#### 步骤 1：定位根实例

按 §8.1/§8.2 定位根实例，记录其实例 ID。

#### 步骤 2：HITL 确认

> 即将对以下根实例执行 fix-data（重跑下游链路）：
> - 根实例 ID：`t_xxxx`
> - 任务名：`shell_a`
> - 项目：`test1 (7295715579274176)`
> - 环境：`PROD`
> - 业务日期：`20260629`
> - 下游范围：`ALL_INSTANCE`（所有实例）
> - 包含根实例：`true`
>
> 确认执行？（yes/no）

#### 步骤 3：执行 fix-data

```bash
ENV=PROD
PROJECT_ID="<project-id>"
ROOT_INSTANCE_ID="<root-instance-id>"

aliyun dataphin-public fix-data \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --root-instance-id "{\"Id\":\"$ROOT_INSTANCE_ID\"}" \
  --contain-root-instance true \
  --downstream-range ALL_INSTANCE \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id}
```

> **关键坑：`--root-instance-id` 必须传 JSON 对象 `{"Id":"t_xxx"}`**，不能传裸字符串（会报 `invalid JSON`）或 JSON 字符串（会报 `Expected BEGIN_OBJECT but was STRING`）。

返回 `Success=true` + `SubmitId` 表示重跑指令已下发。

#### 步骤 4：验证重跑结果

**fix-data 不创建新实例，而是在同一实例下创建新 taskrun**。因此：
- `list-instances` 中实例状态不变（如原来 SUCCESS 仍为 SUCCESS）
- 必须用 `get-physical-instance-log` 查看是否有新增 taskrun

```bash
aliyun dataphin-public get-physical-instance-log \
  --env "$ENV" \
  --project-id "$PROJECT_ID" \
  --instance-id "$ROOT_INSTANCE_ID" \
  --format json \
  --user-agent AlibabaCloud-Agent-Skills/rerun-task-instance/{session-id} \
  | jq '[.TaskrunLogList[] | {TaskrunId, Status, StartTime, EndTime, Duration}]'
```

重跑成功后，每个实例应有 **2 条及以上 taskrun 日志**（原始 + 重跑）。

根实例的重跑日志中 `Schedule type` 显示 `RERUN_FORCIBLY`，下游实例显示 `AUTO_SCHEDULED`（由上游重跑自动触发）。

#### 步骤 5：验证下游实例

对依赖链中的下游实例逐一执行 `get-physical-instance-log`，确认每个实例均有新增 taskrun 且状态为 `SUCCESS`。

> 可用 `get-instance-down-stream --instance-id <root-id> --node-type DATA_PROCESS --down-stream-depth 6` 查询下游拓扑，获取所有下游实例 ID。

## 9. Success Verification Method

### 模式①（operate-instance RERUN）

- `operate-instance` 返回 `Success=true`，说明 RERUN 指令下发成功。
- 通过 `get-physical-instance` 或 `list-instances` 确认实例状态从 `FAILED` 变为 `RUNNING`，最终变为 `SUCCESS`。
- 若状态仍为 `FAILED`，则通过 `get-physical-instance-log` 定位根因；常见根因包括：
  - 数据源权限不足
  - 目标表/列不存在
  - Pipeline 列映射配置错误（如把字段类型字符串当成目标列名）
  - 计算资源排队或限流

### 模式②（fix-data 重跑下游）

- `fix-data` 返回 `Success=true` + `SubmitId`，说明重跑指令已下发。
- **不能用 `list-instances` 验证**（fix-data 不创建新实例，实例状态不变）。
- **必须用 `get-physical-instance-log` 验证**：每个实例应有新增 taskrun，新 taskrun 状态为 `SUCCESS`。
- 根实例新 taskrun 日志中 `Schedule type` 为 `RERUN_FORCIBLY`，下游实例为 `AUTO_SCHEDULED`。
- 重跑按依赖顺序执行（上游先完成，下游后触发）。

## 10. Cleanup

本 Skill 仅触发实例重跑，不创建新的 Dataphin 资源，无需清理。

## 11. Command Tables

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

1. **实例与项目必须匹配**：`operate-instance` 的 `--project-id` 必须是实例所属项目，否则报 `DPN.OP.ProjectNotExist`。
2. **业务日期不是调度日**：Dataphin 默认 `bizdate = T-1`，请用业务日期而非运行日期查询实例。
3. **跨项目搜索后务必让用户选择**：同名任务可能存在于多个项目，避免误操作。
4. **重跑不等于修复**：如果任务配置或源数据本身有问题，重跑仍会失败，必须结合日志诊断。
5. **大整数 ID 作为字符串传递**：实例 ID / 节点 ID / 项目 ID 在 JSON 参数中都要用引号包裹。
6. **日志中关注最后一次运行**：`get-physical-instance-log` 可能返回多条记录（多次重跑），取数组最后一个元素查看最新一次日志。
7. **fix-data 的 `--root-instance-id` 必须传 JSON 对象**：`{"Id":"t_xxx"}`，传裸字符串报 `invalid JSON`，传 JSON 字符串（带引号）报 `Expected BEGIN_OBJECT but was STRING`。
8. **fix-data 不创建新实例**：在同一实例下创建新 taskrun，实例 ID 不变。验证重跑结果必须用 `get-physical-instance-log` 看 taskrun 数量，不能用 `list-instances`（实例状态不变）。
9. **fix-data 按依赖顺序执行**：根实例先重跑，下游实例自动按依赖顺序触发。根实例日志 `Schedule type: RERUN_FORCIBLY`，下游实例 `Schedule type: AUTO_SCHEDULED`。
10. **fix-data 与 operate-instance 的选择**：单实例重跑用 `operate-instance RERUN`；需要联动重跑整条下游链路用 `fix-data`。

## 13. Reference Links

| 文档 | 说明 |
|------|------|
| [CLI 安装指南](./references/cli-installation-guide.md) | aliyun CLI 与 dataphin-public 插件安装 |
| [RAM 策略参考](../../ram-policies.md) | 最小 RAM 权限与失败处理 |
| [验收标准](./references/acceptance-criteria.md) | 正确/错误命令模式 |
| [相关命令索引](./references/related-commands.md) | 本 Skill 涉及的 CLI 命令 |
