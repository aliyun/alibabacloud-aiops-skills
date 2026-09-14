---
name: develop-metric
description: |-
  指标开发：为没有技术实现的业务指标找来源表 → 定口径 SQL → 建计算任务产出结果表 → 登记自定义指标 → 回流关联。
  触发场景：指标开发 / 找不到可用的技术指标 / 给业务指标做技术落地 / 找来源表算指标 / 新建自定义指标。
  流程：list-catalog-assets 先找现成结果表 → list-tables 找来源表 → get-table-columns 校验字段 → 产出任务草案交 update-batch-task / submit-batch-task → 【控制台人工登记自定义指标】→ 核验注册 → 交回 manage-biz-metric 关联。
  关键限制：创建自定义指标（CUSTOM_INDEX）与资产上架无 OpenAPI，必须输出控制台指引并暂停等人工；get-table-columns 走 --catalog 项目英文名，不认 --project-id；list-tables 必带 --cli-query 收窄输出。
  触发词：指标开发、自定义指标、CUSTOM_INDEX、找来源表、汇总表、指标计算任务、develop metric。
---

# 指标开发 Skill（找来源表 · 建计算任务 · 登记技术指标）

## 1. Scenario Description

当业务指标已经定义好口径，但**没有任何现成技术指标能满足它**时，进入本 Skill 做技术落地。典型上游是子 skill [`manage-biz-metric`](../manage-biz-metric/SKILL.md) 的 Step 4 判定「无可用技术指标」后转来。

本 Skill 的产出目标是**一个可被业务指标关联的技术指标**。路径分两种，按结果表是否已存在分流：

| 情况 | 处理 |
|---|---|
| **已有结果表/汇总表**能算出该指标 | 跳过任务开发，直接进 Step 4 登记自定义指标 |
| **没有结果表** | 走完整开发：找来源表 → 定口径 SQL → 建计算任务产出结果表 → 再进 Step 4 |

> **本 Skill 有一处硬断点**：创建自定义指标（`CUSTOM_INDEX`）与资产上架到目录**实测无任何 OpenAPI 命令**（插件 0.7.1 已穷举确认）。Step 4 必须输出控制台操作指引并**暂停等用户人工完成**，不得伪造命令或跳过。

### Architecture

```
上游：业务指标已定义，无可用技术指标
  → Step 1 找来源表（list-tables → get-table-columns 校验字段）
  → Step 2 定口径 SQL（可选：即席查询试算验证）
  → Step 3 建离线计算任务产出结果表（委托 update-batch-task / submit-batch-task）
  → Step 4 【人工】控制台登记自定义指标 + 上架到资产目录  ← 无 OpenAPI，暂停等人工
  → Step 5 list-catalog-assets --asset-type INDEX 确认已注册，取 AssetFullName
  → 回流：交回 manage-biz-metric Step 5 完成关联
```

### 涉及 Dataphin OpenAPI

- `ListTables` — 分页查资产表元数据（v5.4.2）
- `GetTableColumns` — 查表字段（v5.4.2）
- `ExecuteAdHocTask` / `GetAdHocTaskResult` — 即席查询试算口径（可选）
- `CreateBatchTask` / `UpdateBatchTask` / `SubmitBatchTask` — 离线计算任务（委托给已有 skill）
- `ListCatalogAssets` — 确认自定义指标已注册（v6.1.0）

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

| 变量 | 说明 | 必须 |
|------|------|------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | RAM AccessKey ID | 是 |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | RAM AccessKey Secret | 是 |

或通过 `aliyun configure` 配置 profile。

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

> 执行 `aliyun version` 确认版本 >= 3.4.8；不达标见 [references/cli-installation-guide.md](./references/cli-installation-guide.md)。

### Pre-check: Aliyun CLI plugin update required

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 skill 最小权限见 [../../ram-policies.md](../../ram-policies.md)。

## 6. IMPORTANT: Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or
> use default values without explicit user approval.

| 参数 | 必填 | 说明 |
|------|------|------|
| `--tenant-id` | 是 | 租户 ID（19 位大整数，字符串传参） |
| 目标业务指标名 | 是 | 本次开发是为哪个业务指标做技术落地 |
| 指标口径 | 是 | 统计对象 + 聚合方式 + 统计周期 + 业务限定 |
| `--project-id` / 项目英文名 | 是 | 来源表与计算任务所在项目 |
| 来源表清单 | 是 | 由 Step 1 检索后**经用户确认**，不得 Agent 自行拍定 |
| 结果表名 | 是（需开发时） | 计算任务的输出表 |
| 调度周期 | 是（需开发时） | 与指标统计周期一致 |

## 7. Observability

版本 `{version}`（Shell 变量 `SKILL_VERSION`）来自套件 `references/manifest.json` 的 `version` 字段，与 session-id 一同继承[父技能 §7](../../../SKILL.md#7-observability)。直接加载本子技能时先完成父层初始化；所有 CLI / SDK 调用使用父技能名称与同一版本，跨 Shell 调用须重新注入这些值。

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。本地工具命令（`configure` / `plugin` / `version`）不支持该 flag，不需携带。

## 8. Core Workflow

```bash
TENANT_ID="<19 位租户 ID，字符串>"
SESSION_ID="<继承自 alibabacloud-dataphin-skills>"
USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/$SESSION_ID skill-version/$SKILL_VERSION"
```

### Step 0 · 先判断是否已有结果表可用

先在资产目录里搜一遍汇总表/结果表，命中就**跳过 Step 1~3 直接进 Step 4**，避免重复建任务：

```bash
aliyun dataphin-public list-catalog-assets --tenant-id "$TENANT_ID" \
  --asset-type TABLE --query-mode ASSET_SEARCH \
  --keyword "<业务关键词，如 客户 汇总>" --page-size 20 \
  --user-agent "$USER_AGENT" --format json
```

关注返回项的 `AssetFullName`（后续拼技术指标全名要用）、`AssetDescription`、`SubType`。

### Step 1 · 找来源表（只读）

```bash
# 1a) 先只取总数，判断检索范围大小（避免一次拉回巨量元数据）
aliyun dataphin-public list-tables --tenant-id "$TENANT_ID" \
  --project-id "<项目ID>" --page-size 1 \
  --cli-query 'PageResult.TotalCount' \
  --user-agent "$USER_AGENT"

# 1b) 只取表名清单（必须收窄投影，否则单次响应可达十万级字符）
aliyun dataphin-public list-tables --tenant-id "$TENANT_ID" \
  --project-id "<项目ID>" --page-num 1 --page-size 50 \
  --cli-query 'PageResult.TableList[].Name' \
  --user-agent "$USER_AGENT"
```

**检索纪律（必须遵守）**：
- `list-tables` 是**扁平参数**，**没有 `--list-query`**；不带 `--cli-query` 时单次输出极大，必须收窄投影。
- 先取 `TotalCount` 再决定翻几页；**空页不要重试**。
- 投影返回字面 `null` 时，**去掉 `--cli-query` 原样重跑一次**——服务端返回错误体时 JMESPath 匹配不到会输出 `null` 且退出码 0，看起来像"查到了但没数据"，实际可能是接口报错（如 403 功能未开通）。

### Step 2 · 校验字段能否支撑口径（只读）

```bash
# get-table-columns 走 catalog 维度：--catalog 传项目英文名，不认 --project-id / --env
aliyun dataphin-public get-table-columns --tenant-id "$TENANT_ID" \
  --catalog "<项目英文名>" --table-name "<表名>" \
  --user-agent "$USER_AGENT" --format json
```

逐条核对口径需要的字段是否齐备：统计对象主键、度量列、时间分区列、业务限定列。缺字段就回 Step 1 换表，**不要硬凑 SQL**。

### Step 3 · 定口径 SQL 并建计算任务

#### 3a）（可选）即席查询试算验证口径

复用子 skill [`execute-ad-hoc-task`](../../dev/execute-ad-hoc-task/SKILL.md)。两个实测要点：

- `get-ad-hoc-task-result` 必填 `--project-id` / `--task-id` / `--sub-task-id`，且 **`--sub-task-id` 是 0 起始下标**（传 1 会报 `DPN.DataProcess.CodeNotFound`）。
- 响应 `Result:""` 表示任务**还在跑**，需继续轮询，**不是失败**。

#### 3b）产出任务草案并委托建任务

本 Skill **不重复实现**离线任务的参数细节，只产出草案交给已有子 skill 执行：

```markdown
## 指标计算任务草案（待你确认后交 update-batch-task 执行）

- 目标业务指标：月活客户数（monthly_active_customer_cnt）
- 项目：<项目英文名>
- 结果表：dws_customer_active_monthly
- 调度周期：日调度（与指标统计周期一致）
- 来源表：<Step 1 确认的表清单>
- 口径 SQL：
  ```sql
  INSERT OVERWRITE TABLE dws_customer_active_monthly PARTITION (ds='${bizdate}')
  SELECT COUNT(DISTINCT customer_id) AS active_customer_cnt
  FROM <来源表>
  WHERE ds BETWEEN ... AND pay_status = 'SUCCESS';
  ```
```

用户确认后按场景转交：

| 需求 | 转交 skill |
|---|---|
| 新建 / 修改任务代码与调度 | [`update-batch-task`](../../dev/update-batch-task/SKILL.md) |
| 提交任务并发布 | [`submit-batch-task`](../../dev/submit-batch-task/SKILL.md) |
| 任务缺默认上游（挂虚拟根节点） | [`find-tenant-root-node`](../../dev/find-tenant-root-node/SKILL.md) |
| 首次跑历史数据 | [`create-node-supplement`](../../ops/create-node-supplement/SKILL.md) |

> 任务的建/提/发均为写操作，由被委托 skill 各自走 HITL 确认；本 skill 不代替确认。

### Step 4 · 【人工兜底】登记自定义指标并上架（无 OpenAPI，必须暂停）

结果表就绪后，需要把它登记为**自定义指标**才能被业务指标关联。此步骤**无任何 CLI/OpenAPI 命令可用**，必须输出如下指引并**停下等用户回复完成**：

```markdown
⚠️ 下一步需要你在控制台手工完成（该操作 Dataphin OpenAPI 暂未开放，无法自动执行）

**路径**：资产治理管理 → 资产 → 目录管理（或资产清单中定位结果表）→ 新建自定义指标

**请按以下信息填写**：

| 项 | 值 |
|---|---|
| 所属表 | `<结果表全名，如 dataphin.dws_customer_active_monthly>` |
| 指标名称 | `active_customer_cnt`（建议与结果表度量列同名，便于对齐） |
| 指标口径 | 近30天有支付成功订单的客户去重计数 |
| 聚合方式 | COUNT(DISTINCT customer_id) |
| 统计周期 | 月 |
| 上架目录 | `<与目标业务指标同一专题/目录>` |

**完成后请回复「已建好」**，我会自动核验注册结果并把它关联到业务指标 `monthly_active_customer_cnt`。
```

> **[MUST]** 不得为此步骤编造 `create-custom-index` 之类不存在的命令，也不得跳过直接去关联（关联会因技术指标不存在而失败）。

### Step 5 · 核验注册结果并回流

```bash
# 确认自定义指标已注册进资产目录，并取出它的 AssetFullName
aliyun dataphin-public list-catalog-assets --tenant-id "$TENANT_ID" \
  --asset-type INDEX --query-mode ASSET_SEARCH \
  --keyword "<指标名，如 active_customer_cnt>" --page-size 20 \
  --user-agent "$USER_AGENT" --format json
```

- 命中且 `SubType = CUSTOM_INDEX` → 登记成功。
- `TotalCount` 为 0 → 大概率**建了但没上架到目录**（资产目录只收录已上架资产），请用户在控制台补上架后重试。

拿到 `AssetFullName` 后，**交回** [`manage-biz-metric`](../manage-biz-metric/SKILL.md) 的 Step 5 执行关联：技术指标全名 = 该表资产的 `AssetFullName` + `.` + 指标名。

### 执行前确认（写操作必备 / HITL）

> 本 skill 自身只发只读命令；写操作（建任务/提交/发布/补数据）全部由被委托的子 skill 执行，各自走 HITL 二次确认，需包含：
> - 即将执行的命令全文（脱敏后）
> - 影响范围（哪个项目 / 任务 / 结果表；是否影响生产调度）
> - 是否可回滚
> - 替代方案（可先 `--cli-dry-run`）

## 9. Success Verification

| 阶段 | 校验方式 | 通过标准 |
|---|---|---|
| 来源表选定 | `get-table-columns` | 口径所需字段全部存在 |
| 口径正确 | 即席查询试算 | 结果量级与业务预期一致 |
| 任务生效 | 被委托 skill 的验证步骤 | 任务已提交且发布成功，结果表有产出分区 |
| 指标注册 | `list-catalog-assets --asset-type INDEX` | 命中且 `SubType=CUSTOM_INDEX` |
| 最终关联 | `get-biz-metric-by-name --draft false` | 业务指标的关联技术指标列表含目标全名 |

详见 [references/acceptance-criteria.md](./references/acceptance-criteria.md)。

## 10. Cleanup

本 skill 自身不创建资源。若需回滚整条开发链路，按**逆序**清理：

1. 解除业务指标关联（`update-biz-metric` 重传不含该全名的列表）
2. 控制台下架/删除自定义指标（无 OpenAPI，人工）
3. 下线并删除计算任务（`offline-batch-task` → `delete-batch-task`，见 `submit-batch-task` skill）
4. 结果表按项目规范处理（不在本 skill 范围）

## 11. Command Tables

详见 [references/related-commands.md](./references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 先查有没有现成结果表（Step 0），别一上来就建任务
2. `list-tables` 必带 `--cli-query` 收窄投影；先取 `TotalCount` 再翻页；空页不重试
3. `get-table-columns` 用 `--catalog <项目英文名>`，不是 `--project-id`
4. 投影返回 `null` 一律去掉 `--cli-query` 重跑核实，防「假成功」
5. 任务参数细节不在本 skill 复制，统一委托 `update-batch-task` / `submit-batch-task`
6. Step 4 的人工兜底指引必须给全字段值，让用户一次填对

### ✗ 平台限制

#### ✗ 无法通过 OpenAPI 创建自定义指标（CUSTOM_INDEX）
- 限制描述：实测插件 0.7.1 全量命令中不存在任何创建技术指标/自定义指标的命令（`aliyun dataphin-public --help` grep `metric|index` 仅返回业务指标 4 个 + 资产目录 2 个）。
- 替代方案：Step 4 输出控制台操作指引并暂停等人工完成，再由 Step 5 核验。

#### ✗ 无法通过 OpenAPI 上架资产到目录
- 限制描述：无 shelve / register-asset 类命令；而 `list-catalog-assets` 只能查到**已上架**资产。
- 替代方案：人工上架；Step 5 查不到时优先怀疑「建了未上架」而非「建失败」。

#### ✗ 无法通过 OpenAPI 创建规范建模派生指标
- 限制描述：数据架构域仅有 `biz-unit` / `biz-entity` / `data-domain` 相关命令，无原子/派生指标命令。
- 替代方案：派生指标只能控制台建；本 skill 走「结果表 + 自定义指标」路径。

### 常见坑

#### [人工注入] `get-table-columns` 传 `--project-id` 无效
- 现象：按直觉传 `--project-id` / `--env` 报参数错误。
- 结论：该命令走 catalog 维度，必须 `--catalog <项目英文名>` + `--table-name`。

#### [人工注入] `list-tables` 不带投影会打爆上下文
- 现象：不带 `--cli-query` 单次响应可达十万级字符。
- 结论：固定用 `--cli-query 'PageResult.TableList[].Name'` 取名单，需要详情时再对单表 `get-table-columns`。

#### [Agent 自主发现] 自定义指标建了但资产目录搜不到
- 现象：用户已在控制台建了自定义指标，Step 5 却 `TotalCount=0`。
- 结论：资产目录只收录**已上架**资产。先让用户确认是否已上架到目录，而不是判定登记失败重新建一遍。

#### [人工注入] 即席查询 `Result:""` 被误判为失败
- 现象：`get-ad-hoc-task-result` 返回空结果串就认为试算失败。
- 结论：`Result:""` 表示还在跑，需继续轮询；且 `--sub-task-id` 是 0 起始下标。

### Reference Links

- [references/cli-installation-guide.md](./references/cli-installation-guide.md)
- [../../ram-policies.md](../../ram-policies.md)
- [references/acceptance-criteria.md](./references/acceptance-criteria.md)
- [references/related-commands.md](./references/related-commands.md)
- 上下游 skill：[`manage-biz-metric`](../manage-biz-metric/SKILL.md)（上游定义 + 下游关联）、[`update-batch-task`](../../dev/update-batch-task/SKILL.md)、[`submit-batch-task`](../../dev/submit-batch-task/SKILL.md)、[`execute-ad-hoc-task`](../../dev/execute-ad-hoc-task/SKILL.md)
