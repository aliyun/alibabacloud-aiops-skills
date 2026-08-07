---
name: create-node-supplement
description: |
  对 Dataphin 调度节点发起补数据（按业务日期回填历史数据）。触发场景：补数据 / 补跑 / 回填数据 / backfill / supplement / create-node-supplement / dagrun 状态跟踪。流程：list-nodes（必须传 --node-sub-biz-type-list）→ create-node-supplement → 海量模式经 get-operation-submit-status 取 ExternalBizId → get-supplement-dagrun → get-supplement-dagrun-instance。关键点：bizdate 默认 T-1；--env 必须匹配 HasDev/HasProd；--node-id-list 传单个 JSON 对象字符串 {"Id":"n_xxx"}；create-node-supplement 返回的 SubmitId 是 jobId，真正 SupplementId 是 ExternalBizId；小时任务用 --min-due-time/--max-due-time。触发词：补数据、补跑、回填数据、重跑任务、backfill、supplement、create-node-supplement、dagrun。
---
# 节点补数据 Skill

## 1. Scenario Description

场景：需要按业务日期对调度节点及其下游进行历史数据回填，或修正某段时间内的产出数据。

本 Skill 覆盖从节点定位、补数据提交、到 dagrun 与实例级跟踪的完整流程，并区分普通模式与海量模式（含所有下游）。

### Background Knowledge

- **业务日期 bizdate** = 任务的"业务归属日"。Dataphin 默认 `bizdate = T-1`（昨天），即调度日 `cyctime` 凌晨产出 T-1 的数据。补数据的 `--start-biz-date` / `--end-biz-date` 是**业务日期**，不是调度日。
- **节点 ID 仅对应一个环境**：`n_xxx` 是 DEV 节点 ID 还是 PROD 节点 ID 取决于发布是否成功。`HasDev=true` 意味着 DEV 侧有节点；`HasProd=true` 意味着 PROD 侧也有节点。**未发布到 PROD 的项目用 `--env DEV`**，否则 `DPN.OP.NodeNotFound`。
- **小时调度** 一个补数据日会按 cron 展开成 N 个实例（如 `0 45 8,20 * * ?` 展开为 08:45 与 20:45 两个 due-time 实例）。`--min-due-time` / `--max-due-time` 可在小时任务中限定补哪几个时点。
- **依赖关系自动遵守**：多个根节点同 batch 提交时，按 DAG 依赖顺序执行。下游节点会等上游完成。

### Architecture

```
用户请求 → 确认参数 → list-nodes 定位节点
  → create-node-supplement（普通 / 海量模式）
  → 海量模式：get-operation-submit-status 取 ExternalBizId
  → get-supplement-dagrun 跟踪各业务日期
  → get-supplement-dagrun-instance 查看节点实例状态
```

### 涉及 Dataphin OpenAPI

- `ListNodes` — 查询节点元数据（必须传 NodeBizType / NodeSubBizTypeList / ScheduleType）
- `CreateNodeSupplement` — 发起补数据
- `GetOperationSubmitStatus` — 海量模式下由 jobId 取真正 SupplementId
- `GetSupplementDagrun` — 查询补数据 dagrun 列表
- `GetSupplementDagrunInstance` — 查询 dagrun 下节点实例
- `ListNodeDownStream` — 创建前查询下游做参考

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

执行 `create-node-supplement` 前必须向用户确认以下参数，禁止静默提交：

| 参数 | 说明 |
|------|------|
| `--env` | DEV 或 PROD（默认 PROD），必须与节点实际发布环境一致 |
| `--node-id-list` | 根节点 ID 列表（单个 JSON 对象字符串 / 节点） |
| `--start-biz-date` / `--end-biz-date` | 业务日期闭区间，格式 `yyyymmdd` |
| `--contain-all-down-stream` | 是否联动所有下游节点（海量模式） |
| `--parallelism` | 同一业务日期内实例并发上限 |

## 7. 完整命令链

```bash
TENANT_ID=<tenant-id>
PROJECT_ID=<project-id>
ENV=DEV   # 或 PROD（必须该任务已成功发布到 PROD，HasProd=true）
USER_AGENT="AlibabaCloud-Agent-Skills/create-node-supplement/{session-id}"

# 1) 取真实业务日期（绝对不要依赖会话上下文时间）
TODAY=$(date "+%Y%m%d")
BIZDATE=$(date -v-1d "+%Y%m%d")  # macOS；Linux: date -d "-1 day" "+%Y%m%d"
echo "今天=$TODAY 业务日期(T-1)=$BIZDATE"

# 2) 拿目标节点 ID（list-nodes 必须传 node-biz-type / node-sub-biz-type-list / schedule-type / env）
#    SHELL 任务：--node-biz-type SCRIPT --node-sub-biz-type-list SHELL
#    SQL 任务：--node-biz-type SCRIPT --node-sub-biz-type-list MAX_COMPUTE_SQL / HIVE_SQL 等
#    逻辑表任务：--node-biz-type LOGICAL_TABLE
aliyun dataphin-public list-nodes --dataphin-profile <p> --env $ENV \
  --node-biz-type SCRIPT --node-sub-biz-type-list SHELL --schedule-type NORMAL \
  --search-text "<task-name>" --page 1 --page-size 10 \
  --user-agent "$USER_AGENT" --format json \
  | jq '.PageResult.NodeList[] | {Id,Name,HasProd,HasDev,SubDetailType}'

# 3) 发起补数据（一次可多个根节点，每个节点一个 JSON 对象字符串）
#    注意：--node-id-list 不是 JSON 数组，而是多个 JSON 对象参数
aliyun dataphin-public create-node-supplement --dataphin-profile <p> --env $ENV \
  --node-id-list '{"Id":"n_8005597591266000896"}' '{"Id":"n_8005606971474444288"}' \
  --start-biz-date $BIZDATE --end-biz-date $BIZDATE \
  --node-supplement-name "supp_$(date +%Y%m%d_%H%M%S)" \
  --parallelism 1 --user-agent "$USER_AGENT" --format json
# 返回 SubmitId（普通模式下即为 SupplementId；海量模式下是 jobId，需第 4 步转换）

# 海量模式：联动根节点及其所有下游
aliyun dataphin-public create-node-supplement --dataphin-profile <p> --env $ENV \
  --node-id-list '{"Id":"n_8005597591266000896"}' \
  --start-biz-date $BIZDATE --end-biz-date $BIZDATE \
  --contain-all-down-stream true \
  --node-supplement-name "supp_$(date +%Y%m%d_%H%M%S)" \
  --parallelism 1 --user-agent "$USER_AGENT" --format json

# 4) 取真正的 SupplementId
#    普通模式：SupplementId = 上一步返回的 SubmitId
#    海量模式：SubmitId 是 jobId，必须用 get-operation-submit-status 取 ExternalBizId
JOB_ID=<上一步返回的 SubmitId>
aliyun dataphin-public get-operation-submit-status --dataphin-profile <p> --env $ENV \
  --job-id $JOB_ID --user-agent "$USER_AGENT" --format json \
  | jq '.OperationSubmitJob | {JobId, OperationStatus, Progress, ExternalBizId}'
# ExternalBizId 形如 f_<rootNodeId>_<date>_<random>，这才是真正的 SupplementId/FlowId

# 5) 跟踪工作流（按业务日期分 dagrun）
SUPPLEMENT_ID=<ExternalBizId>
aliyun dataphin-public get-supplement-dagrun --dataphin-profile <p> --env $ENV \
  --supplement-id $SUPPLEMENT_ID --user-agent "$USER_AGENT" --format json \
  | jq '.DagrunList[] | {Id,BizDate,Status,Duration}'
# Status: INIT / WAITING / RUNNING / SUCCESS / FAILED

# 6) 查 dagrun 下所有节点实例
DAGRUN_ID=<上一步返回的 Id>
aliyun dataphin-public get-supplement-dagrun-instance --dataphin-profile <p> --env $ENV \
  --dagrun-id $DAGRUN_ID --user-agent "$USER_AGENT" --format json \
  | jq '.InstanceList[] | {NodeName:.NodeInfo.Name,Index,DueTime,Status:.StatusList,Duration}'
```

## 8. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/create-node-supplement/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 9. 参数要点

| 参数 | 必填 | 取值 | 备注 |
|---|---|---|---|
| `--node-id-list` | 必 | 每个节点传一个 JSON 对象字符串：`{"Id":"n_xxx"}` | 多个根节点传多个参数；逻辑表节点可加 `FieldIdList`。**不能传 JSON 数组** `[{"Id":"n_xxx"}]` |
| `--start-biz-date` / `--end-biz-date` | 必 | `yyyymmdd` 字符串 | 闭区间；同日补一天传相同值 |
| `--env` | 可 | `DEV` / `PROD`（默认 PROD） | 与节点存在环境匹配，否则 `NodeNotFound` |
| `--parallelism` | 可 | 默认 1 | 同一业务日期内的实例并发上限 |
| `--min-due-time` / `--max-due-time` | 可 | `HH:MM` | **小时任务专用**，限定补哪几个时点 |
| `--contain-all-down-stream` | 可 | bool | 海量模式：自动包含所有下游。需 `true` / `false`，不可裸写 flag |
| `--down-stream-node-id-list` | 可 | 每个节点一个 JSON 对象字符串 | 列表模式：手动指定下游 |
| `--filter-list` | 可 | 与海量模式搭配 | 按 PROJECT/NODE_NAME/NODE_ID 等正反选 |
| `--global-param-list` / `--node-params-list` | 可 | 键值对 | 运行时覆盖参数 |
| `--node-supplement-name` | 可 | 字符串 | 不传系统生成；建议带日期便于排查 |

## 10. 常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| `Error: --node-sub-biz-type-list is required` | `list-nodes` 缺少必填的子业务类型参数 | 按任务类型加 `--node-sub-biz-type-list SHELL` / `MAX_COMPUTE_SQL` / `HIVE_SQL` 等 |
| `Expected BEGIN_OBJECT but was BEGIN_ARRAY at path $.nodeIdList[0]` | `--node-id-list` 传了 JSON 数组 `[{"Id":"n_xxx"}]` | 改成单个 JSON 对象字符串 `{"Id":"n_xxx"}`；多节点传多个参数 |
| `failed to resolve contain-all-down-stream: invalid boolean value: ...` | `--contain-all-down-stream` 后缺少 `true`/`false` | 必须写 `--contain-all-down-stream true` |
| `DPN.OP.NodeNotFound: 节点未找到:[task:n_xxx]` | `--env` 与节点环境不匹配（最常见：项目未发布 PROD 却用了默认 PROD）| `list-nodes --env DEV/PROD` 验证 `HasProd/HasDev` 后选对应 env |
| `DPN.OP.FlowNotExist: 租户下不存在对应FLOW:[<SubmitId>]` | 用 `create-node-supplement` 返回的 `SubmitId` 直接查 `get-supplement-dagrun`，但海量模式下 `SubmitId` 是 jobId 而非 SupplementId | 先用 `get-operation-submit-status --job-id <SubmitId>` 取 `ExternalBizId`，再用 ExternalBizId 查 dagrun |
| `DPN.OP.FlowNotExist: 租户下不存在对应FLOW` | `get-supplement-dagrun` / `get-supplement-dagrun-instance` 的 `--env` 与 `create-node-supplement` 不一致（如补数据用 DEV 创建，但查询时默认 PROD） | 查询 dagrun 时必须传与 `create-node-supplement` 相同的 `--env` |
| 提交成功但 dagrun 长时间 `WAITING` | 调度依赖未就绪 / 资源组排队 | `get-supplement-dagrun-instance` 看实例 StatusList |

## 11. ✗ 不要做

- ✗ 用调度日填 `bizdate`：bizdate 默认 T-1，调度日填业务日期会导致补数据范围错位
- ✗ 直接复制 IDE 页面 URL 中的 `nodeId`：URL 上有时是 `bizNodeId`（pipeline 草稿 ID）而非节点 ID
- ✗ 多个项目跨补：同一次 `create-node-supplement` 仅支持当前 profile 项目，不支持跨项目
- ✗ 用 `--start-biz-date today` 形式：必须 `yyyymmdd` 数字字符串
- ✗ `list-nodes` 不传 `--node-sub-biz-type-list`：该参数必填，否则直接报错
- ✗ `--node-id-list` 传 JSON 数组：CLI 把每个参数当做一个 JSON 对象解析，数组会被当成第一个元素解析而报错
- ✗ 海量模式下把 `SubmitId` 当 SupplementId 用：必须经 `get-operation-submit-status` 取 `ExternalBizId`
- ✗ 裸写 `--contain-all-down-stream`：该参数是 bool 类型，必须带 `true` / `false`

## 12. 验证与诊断

循环检查各业务日期的 dagrun 与实例状态：

```bash
# 总览
aliyun dataphin-public get-supplement-dagrun --dataphin-profile <p> --env $ENV \
  --supplement-id $SUPPLEMENT_ID --user-agent "$USER_AGENT" --format json \
  | jq '.DagrunList[] | {BizDate,Status,Duration}'

# 单个 dagrun 实例明细
aliyun dataphin-public get-supplement-dagrun-instance --dataphin-profile <p> --env $ENV \
  --dagrun-id $DAGRUN_ID --user-agent "$USER_AGENT" --format json \
  | jq '.InstanceList[] | {NodeName:.NodeInfo.Name,Status:.StatusList,Duration}'
```

## 13. 相关命令

- `aliyun dataphin-public list-nodes` — 查节点 ID（必须传 `--node-biz-type` / `--node-sub-biz-type-list` / `--schedule-type`）
- `aliyun dataphin-public create-node-supplement` — 发起补数据
- `aliyun dataphin-public get-operation-submit-status` — 海量模式下由 jobId（SubmitId）取真正 SupplementId（ExternalBizId）
- `aliyun dataphin-public get-supplement-dagrun` — 工作流总览（需真正 SupplementId）
- `aliyun dataphin-public get-supplement-dagrun-instance` — 实例级状态
- `aliyun dataphin-public list-node-down-stream` — 创建前查询下游做参考
- [find-tenant-root-node.md](./find-tenant-root-node.md) — 节点 ID / DagId 等知识
- [grant-data-source-permission.md](./grant-data-source-permission.md) — 若节点需 PROD 但 `HasProd=false`，先按此 skill 处理发布
