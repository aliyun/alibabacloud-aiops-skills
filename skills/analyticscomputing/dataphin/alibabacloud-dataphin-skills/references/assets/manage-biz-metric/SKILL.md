---
name: manage-biz-metric
description: |-
  管理 Dataphin 业务指标（BIZ_INDEX）：查询 → 语义查重并强制阻塞确认 → 创建 → 关联技术指标。
  触发场景：查看业务指标 / 新建业务指标 / 指标查重 / 有没有类似的指标 / 业务指标关联技术指标。
  流程：get-biz-metric-by-name（草稿+已发布）与 list-catalog-assets(BIZ_INDEX) 三路召回 → 有相似项必须停下等用户确认 → create-biz-metric → list-catalog-assets(INDEX) → update-biz-metric 关联。
  关键限制：无业务指标 list 接口，列表靠资产目录且只覆盖已上架资产（存在漏判需告知）；--biz-metric-name 不接受中文，中文走 --display-name；技术指标全名 = 表资产 AssetFullName + 指标名，禁用 AssetFrom；一技术指标只能被一业务指标关联；写操作需 HITL。
  触发词：业务指标、BIZ_INDEX、create-biz-metric、指标查重、关联技术指标、指标口径。
---

# 业务指标治理 Skill（查重 · 新建 · 关联技术指标）

## 1. Scenario Description

在 Dataphin「资产治理管理 → 资产 → 业务指标」中，用业务语言登记指标口径，并把它映射到可计算的**技术指标**上。业务指标解决「这个指标是什么意思、谁负责」，技术指标解决「这个数怎么算出来」。

本 Skill 覆盖两段业务动作：

1. **查重后新建业务指标** — 先召回已有指标做语义查重；**发现相似项必须停下、列出相似原因、等用户明确确认**才允许创建，避免指标口径重复建设。
2. **关联技术指标** — 查业务指标当前关联情况；未关联则在资产目录中找可用技术指标（自定义指标 `CUSTOM_INDEX` 或规范建模派生指标 `INDEX`）并建立关联。

找不到任何可用技术指标时，转交子 skill [`develop-metric`](../develop-metric/SKILL.md) 做指标开发，开发完成后回到本 skill 的 Step 5 完成关联。

### Architecture

```
用户描述指标需求
  → Step 1 三路召回已有业务指标（get-by-name×2 + 资产目录模糊搜索）
  → Step 2 语义查重 →【有相似项：阻塞，等用户确认】
  → Step 3 create-biz-metric 创建（HITL）
  → Step 4 查关联技术指标（get-biz-metric-by-name → list-catalog-assets INDEX）
  → Step 5 update-biz-metric 关联技术指标（HITL）
       └ 无可用技术指标 → 转 develop-metric skill → 回到 Step 5
```

### 涉及 Dataphin OpenAPI

- `ListCatalogAssets` — 查资产目录列表（`BIZ_INDEX` 业务指标 / `INDEX` 技术指标），上线版本 v6.1.0
- `GetBizMetricByName` — 按名称查业务指标详情，v5.5.0
- `CreateBizMetric` — 创建业务指标，v5.5.0
- `UpdateBizMetric` — 更新业务指标（含关联技术指标），v5.5.0
- `DeleteBizMetric` — 删除业务指标，v5.5.0

> **版本门槛**：资产目录相关命令需目标环境 ≥ v6.1.0；业务指标命令需 ≥ v5.5.0。低于门槛时相关命令不存在或报错，应告知用户升级而非换参数重试。

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

> **除 RAM Action 外还需 Dataphin 平台内角色**（已实测）：读写业务指标都需要**资产维护人员**或拥有**「上架管理-管理」权限**的角色。权限不足时的报错**都不是标准 403**：写操作返回顶层 `Code: OK` 但 `Data.Success=false`（见 §9），读详情返回 `DPN.Mdc.Shelve.ShelveObjectNoViewAuth`（见 §8 Step 1）。**实测赋权后同一指标同一命令即返回 `OK`**，所以遇到这两种报错应先怀疑权限，不要改参数重试。

## 6. IMPORTANT: Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or
> use default values without explicit user approval.

创建 / 更新前必须逐项确认，禁止静默填默认值：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--tenant-id` | 是 | 租户 ID（19 位大整数，字符串传参） |
| `--biz-metric-name` | 是 | 指标名称，**租户内唯一**；仅接受英文字母、数字与 `-_/\·#$^&*()%+=`，≤256 字符。**中文名会被拒绝** |
| `--display-name` | 建议必填 | 展示名称，**中文指标名放这里** |
| `--metric-definition` | 建议必填 | 指标口径；引用其他业务指标时用半角中括号 `[指标名]` 包裹 |
| `--biz-owner-name` | 否 | 业务负责人**账号用户名**（不是显示名） |
| `--description` | 否 | 描述 |
| `--catalog-ids` | 否 | 归属目录 ID 列表（list 型，取值见 §8 Step 3 说明） |
| `--labels` | 否 | 资产标签（list 型） |
| `--associated-tech-metric-full-names` | 否 | 关联技术指标全名列表（list 型，格式见 §类型分支） |
| `--related-biz-metrics` | 否 | 相关业务指标列表（list 型） |
| `--view-scope` | 否 | 可见范围（object 型） |
| `--new-name` | 否（update） | 改名时才传 |

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

### Step 1 · 三路召回已有业务指标（只读）

**以 1a/1b 精确查为权威判定，1c 用于找近义指标**（顺序与理由见下方错误码表）：

```bash
# 1a) 精确名 · 草稿/未上架态 ★ 判定「同名是否已存在」的权威路径
aliyun dataphin-public get-biz-metric-by-name --tenant-id "$TENANT_ID" \
  --biz-metric-name "<候选指标名>" --draft true \
  --user-agent "$USER_AGENT" --format json

# 1b) 精确名 · 已上架态
aliyun dataphin-public get-biz-metric-by-name --tenant-id "$TENANT_ID" \
  --biz-metric-name "<候选指标名>" --draft false \
  --user-agent "$USER_AGENT" --format json

# 1c) 语义近邻 · 资产目录模糊搜索（关键词最多 3 个，逐个搜；page-size 20）
aliyun dataphin-public list-catalog-assets --tenant-id "$TENANT_ID" \
  --asset-type BIZ_INDEX --query-mode ASSET_SEARCH \
  --keyword "<业务关键词，如 客户数>" --page-size 20 \
  --user-agent "$USER_AGENT" --format json
```

#### 错误码语义对照（全部已实测，**判定存在性只认这张表**）

| `Code` | Message | 真实含义 | 能否创建同名 |
|---|---|---|---|
| `OK` | — | 指标存在，`Data` 含完整详情 | **不能**（租户内名称唯一） |
| `DPN.Mdc.Shelve.MetaObjectNotExists` | 资产不存在！ | **真的不存在** | 可以 |
| `DPN.Mdc.Shelve.ShelveObjectNotExists` | 资产已不在上架状态 | **存在但未上架**（`--draft false` 查未上架指标即此码） | **不能** |
| `DPN.Mdc.Shelve.ShelveObjectNoViewAuth` | 暂无资产详情查看权限 | **调用账号缺权限**（缺资产维护人员 / 上架管理-管理），**无法判定存在性** | 未知，须先赋权再查 |

> **[MUST] 三条硬规则**：
> 1. **只有 `MetaObjectNotExists` 才代表「不存在、可以建」**。`ShelveObjectNotExists` 与 `ShelveObjectNoViewAuth` 都**不是**「不存在」，当成无重复去创建会撞租户内名称唯一约束，并给用户一个错的「没重复」结论。
> 2. **新建的业务指标默认「未上架」**（实测：创建成功后 `--draft false` 报 `ShelveObjectNotExists`，`list-catalog-assets` 查不到）。所以查重**必须查 `--draft true`**——它能查到未上架/草稿指标，覆盖率优于资产目录。
> 3. **1c 资产目录只覆盖已上架资产**，用于找近义指标可以，**不能用它判定同名不存在**（未上架的搜不到）。

**召回纪律（必须遵守）**：
- 关键词从用户需求里抽**核心业务名词 ≤3 个**（如「月活客户数」→ `客户`、`月活`、`活跃`），逐个搜一遍即停。
- **禁止对 keyword 做穷举扫描**（不要连续试十几个近义词），也不要翻页超过 2 页。
- `--query-mode ASSET_SEARCH` 时用 `--keyword`；`EXACT_MATCH` 时用 `--asset-name`，两者不可混用。

### Step 2 · 语义查重 + 强制阻塞（本 skill 的核心门禁）

按三个维度判定相似（**不是只比名称**）：

| 维度 | 判定依据 |
|------|---------|
| 名称近义 | `AssetName` / `AssetDisplayName` 与目标名同义或含同一核心业务词 |
| 口径重叠 | `MetricDefinition` / `AssetDescription` 描述的统计对象与聚合方式实质相同 |
| 归属重合 | `Directories[]` 所在专题/目录相同，说明同一业务域已有近似指标 |

**判定结果分两条路径：**

- **无相似项** → 明确告知「已按 N 个关键词搜索，未发现相似指标」，可直接进 Step 3。
- **有相似项** → **必须停下**，输出相似项表格后等用户明确回复「确认新建」。不得自行判断"其实不算重复"就继续创建。

```markdown
发现 2 个可能重复的业务指标，请确认是否仍要新建：

| 已有指标名 | 展示名 | 口径 | 所属目录 | 相似原因 |
|---|---|---|---|---|
| customer_cnt | 客户总数 | 所有注册客户去重计数 | 专题B/A1 | 名称与口径均与「客户数」高度重叠 |
| active_cust_m | 月活客户数 | 近30天有下单行为的客户数 | 专题B/A1 | 统计对象相同，仅时间窗不同 |

⚠️ 覆盖率说明：以上查重仅覆盖**已上架到资产目录**的业务指标，未上架的指标搜索不到，存在漏判可能。

请回复「确认新建」以继续，或告知要复用上面哪一个指标。
```

> **[MUST]** 未拿到用户明确确认前，禁止执行 `create-biz-metric`。

### Step 3 · 创建业务指标（写操作，HITL）

```bash
aliyun dataphin-public create-biz-metric --tenant-id "$TENANT_ID" \
  --biz-metric-name "monthly_active_customer_cnt" \
  --display-name "月活客户数" \
  --description "近30天内有有效下单行为的去重客户数" \
  --metric-definition "统计周期内有支付成功订单的客户去重计数；引用 [customer_cnt] 作为分母时口径需一致" \
  --biz-owner-name "<负责人账号用户名>" \
  --labels "客户域" "月度" \
  --catalog-ids "11282677537502" \
  --user-agent "$USER_AGENT" --format json
```

**参数要点（实测）**：
- `--biz-metric-name` **不接受中文**，须用英文/数字/允许的符号；中文名一律放 `--display-name`。
- 数组类参数（`--labels` / `--catalog-ids` / `--associated-tech-metric-full-names` / `--related-biz-metrics`）是 **CLI list 型：多个值空格分隔**，不是 JSON 数组。
- `--catalog-ids` **没有目录列表接口**。取值办法：对同专题下任一已上架资产跑 `list-catalog-assets`，从返回的 `Directories[].DirectoryId` 取；取不到就问用户，**不要编造 ID**。
- `--metric-relation-diagram-switch-open` 只有在至少配了一个 `--related-biz-metrics` 时才能为 true，否则会被自动关闭。

### Step 4 · 查关联技术指标（只读）

```bash
# 4a) 看该业务指标当前关联了哪些技术指标
aliyun dataphin-public get-biz-metric-by-name --tenant-id "$TENANT_ID" \
  --biz-metric-name "monthly_active_customer_cnt" --draft false \
  --user-agent "$USER_AGENT" --format json

# 4b) 未关联 → 在资产目录里找可用技术指标
aliyun dataphin-public list-catalog-assets --tenant-id "$TENANT_ID" \
  --asset-type INDEX --query-mode ASSET_SEARCH \
  --keyword "<业务关键词>" --page-size 20 \
  --user-agent "$USER_AGENT" --format json
```

**技术指标两类来源靠 `SubType` 区分**：

| `SubType` | 含义 | 来源 |
|---|---|---|
| `INDEX` | 规范建模技术指标（原子/派生指标） | 规划 → 数据架构 → 规范建模 |
| `CUSTOM_INDEX` | 自定义技术指标 | 基于已有结果表/汇总表登记 |

两类都可以被业务指标关联，**优先复用已有的**（先派生指标，再自定义指标）。若 `TotalCount` 为 0 或候选都不满足口径 → 转 [`develop-metric`](../develop-metric/SKILL.md) 做指标开发，完成后回到 Step 5。

### Step 5 · 关联技术指标（写操作，HITL）

```bash
aliyun dataphin-public update-biz-metric --tenant-id "$TENANT_ID" \
  --biz-metric-name "monthly_active_customer_cnt" \
  --associated-tech-metric-full-names "dataphin.customer_agg.avg_order_count" \
  --user-agent "$USER_AGENT" --format json
```

### 类型分支：技术指标全名怎么拼（最容易出错的一步，已实测确认）

官方描述是「所属表全名.指标名称」，其中「所属表全名」=「资产来源.所属表名」。**实测正解**：

> **技术指标全名 = 【表资产的 `AssetFullName`】 + `.` + 【指标名】**

实测样例（已验证可被服务端正确解析）：

| 对象 | 命令 | `AssetFullName` |
|---|---|---|
| 所属表 | `list-catalog-assets --asset-type TABLE` | `odps.dim_quality_test`（= 项目名.表名） |
| 技术指标 | `list-catalog-assets --asset-type INDEX` | `dim_quality_test.stat_count`（= 表名.指标名，**不含项目名**） |
| **传给 API 的全名** | — | **`odps.dim_quality_test.stat_count`** |

> **[MUST] 两条常见陷阱**：
> - **不要用技术指标自己的 `AssetFullName` 再接指标名**——它已经是 `表名.指标名`，再接会得到 `dim_quality_test.stat_count.stat_count`（错）；也不能直接用它（缺项目名前缀）。
> - **不要用 `AssetFrom` 拼**——实测同一资产 `AssetFrom = "Dataphin-通用层-odps (odps)"`，是展示用的来源描述，不是全名组件。
>
> **正确做法**：先 `list-catalog-assets --asset-type INDEX` 拿到技术指标的 `AssetName`（如 `stat_count`）与所属表名，再 `--asset-type TABLE` 拿该表的 `AssetFullName`（如 `odps.dim_quality_test`），两者用 `.` 拼接。

**1:1 硬约束（已实测）**：一个技术指标**只能被一个业务指标关联**。被占用时报（走嵌套路径：顶层 `Code: OK` 但 `Data.Success=false`）：

```
Data.Message = "技术指标已被其他业务指标关联，无法重复关联"
```

> **注意这条报错恰恰证明全名拼对了**（服务端已解析到该技术指标）。此时**绝不要改全名格式重试**——这是业务唯一性冲突，不是参数问题。正解：告知用户该技术指标已被占用，让其选择换一个技术指标，或先在原业务指标上解除关联（解除需用 `update-biz-metric` 重传不含该全名的列表，**属于修改别人的指标，必须先征得用户同意**）。
>
> 查占用者的办法：对候选业务指标跑 `get-biz-metric-by-name --draft false`，看 `AssociatedTechMetrics[].Name` 是否含目标指标名。

**关联失败时 create 是原子的**（已实测）：`create-biz-metric` 带 `--associated-tech-metric-full-names` 且关联报错时，**业务指标完全不会被创建**（反查 `MetaObjectNotExists`）——不会留下「建了但没关联」的半成品，所以可以直接修正后重试同名创建。

### 执行前确认（写操作必备 / HITL）

> 本 skill 的 create / update / delete 均为写操作，执行前必须向用户二次确认：
> - 即将执行的命令全文（脱敏后）
> - 影响范围（哪个租户 / 目录 / 指标；update 对 `--associated-tech-metric-full-names` 是**整体覆盖**，不传的会被清空）
> - 是否可回滚（delete 不可回滚；update 前应先 `get-biz-metric-by-name` 备份原值）
> - 替代方案（可先用 `--cli-dry-run` 只打印请求不实际调用）
>
> 仅当用户明确回复「确认 / yes / 执行」后才发起写命令。

## 9. Success Verification

> **[MUST] 第一步：先看 `Data.Success`，不是顶层 `Code`**（已实测）。
> `create-biz-metric` / `update-biz-metric` 存在**嵌套假成功**：业务失败时仍返回顶层 `Code: OK` + `HttpStatusCode: 200` + `Success: true`，真正的结果在 `Data.Success` 与 `Data.Message` 里。实测样例：
>
> ```jsonc
> {
>   "Code": "OK", "HttpStatusCode": 200, "Success": true,   // ← 全绿，但并未创建
>   "Data": {
>     "Success": false,                                      // ← 真实结果在这里
>     "Message": "资产信息保存失败。失败原因：暂无权限，仅资产维护人员或拥有 上架管理-管理 权限的角色可操作"
>   }
> }
> ```
>
> **判定顺序：`Data.Success == true` 才算提交成功（成功时 `Data.Message` = 「资产保存成功」/「资产删除成功」）；为 false 时必须把 `Data.Message` 原文告知用户**，绝不能因为 `Code: OK` 就汇报「创建成功」。推荐投影：`--cli-query 'Data.{ok:Success,msg:Message}'`。注：`Data.Data` 恒为 `{}`，**创建不返回指标 ID**，需反查取 `Guid`。

第二步：反查确认业务生效。**新建指标默认未上架，所以必须用 `--draft true` 反查**（用 `list-catalog-assets` 或 `--draft false` 反查新建指标**一定查不到**，会误判成失败）：

```bash
# ★ 主路径：草稿/未上架态详情反查
aliyun dataphin-public get-biz-metric-by-name --tenant-id "$TENANT_ID" \
  --biz-metric-name "<指标名>" --draft true \
  --user-agent "$USER_AGENT" --format json

# 辅路径：仅当指标**已上架**时才能命中
aliyun dataphin-public list-catalog-assets --tenant-id "$TENANT_ID" \
  --asset-type BIZ_INDEX --query-mode EXACT_MATCH --asset-name "<指标名>" \
  --user-agent "$USER_AGENT" --format json
```

- 创建成功：`Data.Success=true` **且** `--draft true` 反查返回 `OK`，`Name`/`DisplayName`/`MetricDefinition`/`Labels` 与提交一致，`Guid` 形如 `biz_index.<tenantId>.<logicId>`。
- 创建失败：`Data.Success=false`（看 `Data.Message`）或 `--draft true` 反查报 `MetaObjectNotExists`。
- 关联成功：`--draft true` 反查的 `AssociatedTechMetrics[]` 含目标指标。**注意该数组返回的是 `Name` / `Guid` 而非全名**（已实测结构），不要拿入参的全名去做字符串比对：
  ```jsonc
  "AssociatedTechMetrics": [{
    "Name": "stat_count",                 // ← 比对这个
    "DisplayName": "统计计数",
    "Description": "某种行为或事件的统计次数",
    "Guid": "cust_index.<tenantId>.odps.dim_quality_test.stat_count",  // ← 或比对这个
    "SubType": "CUSTOM_INDEX",           // INDEX 派生 / CUSTOM_INDEX 自定义
    "ListStatus": "ON_SHELVE",           // 上架状态
    "RelationType": null
  }]
  ```
- 删除成功：`--draft true` 反查报 `MetaObjectNotExists`（「资产不存在！」）。

> **注意投影吞错**：读命令若加了 `--cli-query`，服务端返回错误体时 JMESPath 匹配不到会输出字面 `null` 且退出码 0，看起来像「查询成功但没数据」。拿到 `null` 时**必须去掉 `--cli-query` 原样重跑一次**确认是真空值还是接口报错。

详见 [references/acceptance-criteria.md](./references/acceptance-criteria.md)。

## 10. Cleanup

```bash
# 删除测试业务指标（不可回滚，需二次确认）
aliyun dataphin-public delete-biz-metric --tenant-id "$TENANT_ID" \
  --biz-metric-name "<指标名>" \
  --user-agent "$USER_AGENT" --format json
```

关联关系随业务指标删除一并解除；被解除的技术指标可重新被其他业务指标关联。

## 11. Command Tables

详见 [references/related-commands.md](./references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参，示例中用引号包住
2. 写操作执行前必须 HITL 二次确认；**查重确认是额外一道业务门禁，不能用命令级确认代替**
3. 查重先召回再判断，召回关键词 ≤3 个，禁止穷举扫描关键词
4. 中文指标名放 `--display-name`，`--biz-metric-name` 只用英文/数字
5. 技术指标全名直接取资产的 `AssetFullName` 再接指标名，不要自行推导「资产来源」
6. `update-biz-metric` 的列表型字段是整体覆盖，改之前先 `get` 备份

### ✗ 平台限制

#### ✗ 无「业务指标 list」专用接口
- 限制描述：业务指标只有 create / update / get-by-name / delete 四个命令，没有分页列表接口。列表只能借 `list-catalog-assets --asset-type BIZ_INDEX`。
- 替代方案：精确名用 `get-biz-metric-by-name`（草稿/已发布各查一次）；模糊查用资产目录搜索，并向用户声明覆盖范围限制。

#### ✗ 资产目录只覆盖「已上架」资产
- 限制描述：`list-catalog-assets` 查的是资产目录，**未上架到目录的指标搜不到**，因此查重存在漏判。
- 替代方案：查重结论必须附覆盖率声明（见 §8 Step 2 模板）；对关键指标建议用户在控制台再核一遍。

#### ✗ 无法通过 OpenAPI 创建技术指标 / 上架资产
- 限制描述：实测插件 0.7.1 无任何创建自定义指标（`CUSTOM_INDEX`）、创建派生指标、资产上架/注册的命令。
- 替代方案：技术指标的创建走 [`develop-metric`](../develop-metric/SKILL.md) 的人工兜底路径，本 skill 只负责关联已存在的技术指标。

### 常见坑

#### [Agent 自主发现] update 整体覆盖 + `--view-scope` help 不展结构 = 改别人指标的高风险组合
- 现象：`--view-scope` 的 `--help` 只写 `string, Visibility scope`，**完全不展开嵌套结构**；而出参是对象（实测 `{"ScopeType":"PART_USERS_CAN_NOT_VIEW","UserIds":["..."],"UserGroupIds":[],"UserNames":[...],"UserGroupNames":null}`）。叠上列表/对象字段整体覆盖语义，update 不传就会被清空。
- 结论：**对已配了可见范围的存量指标做 update 前必须停下**——不要凭出参反推入参 JSON（出入参 schema 未必一致，`UserIds` vs `UserNames` 无法从 help 确认），猜错会静默改掉或清空权限。正解：向用户说明风险，让其在控制台改可见范围；或先用 `--cli-dry-run` 与用户确认 body 结构再提交。

#### [Agent 自主发现] 把技术指标自己的 `AssetFullName` 当表全名用
- 现象：技术指标资产的 `AssetFullName` 实测是 `dim_quality_test.stat_count`（**表名.指标名，不含项目名**），而表资产的是 `odps.dim_quality_test`（项目名.表名）。直接用前者会缺项目名前缀，再接一次指标名则得到 `dim_quality_test.stat_count.stat_count`。
- 结论：全名只能用**表资产的 `AssetFullName`** 接指标名（本例 = `odps.dim_quality_test.stat_count`）。报「技术指标已被其他业务指标关联」反而说明全名拼对了（服务端已解析到），此时不要改格式重试。

#### [Agent 自主发现] 新建指标默认未上架，用资产目录反查会误判成失败
- 现象：`create-biz-metric` 返回 `Data.Success=true`「资产保存成功」，但 `list-catalog-assets --query-mode EXACT_MATCH` 仍为 `TotalCount=0`，`get-biz-metric-by-name --draft false` 报 `ShelveObjectNotExists`「资产已不在上架状态」；只有 `--draft true` 能查到完整详情。
- 结论：指标**已创建但未上架**。反查新建指标必须用 `--draft true`；看到 `TotalCount=0` 不要当创建失败去重建（会撞名称唯一约束）。

#### [Agent 自主发现] `--catalog-ids` 能挂目录，但**挂目录 ≠ 上架**
- 现象：`update-biz-metric --catalog-ids <DirectoryId>` 返回「资产保存成功」，`--draft true` 反查 `Catalogs` 确已写入（带 `CatalogId`/`CatalogName`/`TopicName`），但指标**仍未上架**（`--draft false` 仍报 `ShelveObjectNotExists`，资产目录仍查不到）。
- 结论：挂目录与上架是**两个独立动作**，上架无 OpenAPI。不要以为传了 `--catalog-ids` 就上架了，也不要为此反复试参数；需上架时告知用户去控制台操作。

#### [Agent 自主发现] update 整体覆盖已实测：只改目录会把标签清空
- 现象：创建时 `Labels=['客户域','月度']`；之后只执行 `update-biz-metric --catalog-ids <id>`（**未**传 `--labels`），反查发现 `Labels=[]`。
- 结论：列表型字段是**整体覆盖而非增量合并**，不传就被清空。改任何一个字段前先 `get-biz-metric-by-name --draft true` 取全量，把不改的字段一并回传。

#### [Agent 自主发现] 写操作的嵌套假成功：`Code: OK` 但 `Data.Success=false`
- 现象：权限不足时 `create-biz-metric` 返回顶层 `Code: "OK"` + `HttpStatusCode: 200` + `Success: true`，而 `Data.Success=false`、`Data.Message="资产信息保存失败。失败原因：暂无权限..."`；资产目录反查 `TotalCount=0`（确实没建）。
- 结论：**只看顶层 `Code` 会把失败汇报成成功**——这比白跑一轮严重，因为用户会以为指标已建。判定必须以 `Data.Success` 为准，为 false 时原文转达 `Data.Message`，并告知需要「资产维护人员或上架管理-管理权限」。

#### [Agent 自主发现] `get-biz-metric-by-name` 报无权限被误读成「指标不存在」
- 现象：同一个已上架指标，`list-catalog-assets` 能列出（`TotalCount=1`），但 `get-biz-metric-by-name` 返回 `DPN.Mdc.Shelve.ShelveObjectNoViewAuth`「暂无资产详情查看权限」（HTTP 400）；**赋予资产维护人员/上架管理权限后，同一命令即返回 `OK`**。
- 结论：这是**调用账号的角色权限不足**，不是指标不存在、也不是指标自身的可见范围配置问题。此码下**无法判定存在性**，应先让用户赋权再查，而不是当「无重复」去创建。

#### [Agent 自主发现] `--biz-metric-name` 传中文直接被拒
- 现象：把「月活客户数」直接传给 `--biz-metric-name`，报名称不符合输入规范。
- 结论：`--biz-metric-name` 只接受英文字母、数字与 `-_/\·#$^&*()%+=`；中文一律放 `--display-name`，两个字段各司其职。

#### [Agent 自主发现] `get-biz-metric-by-name` 漏查草稿态导致误判「不存在」
- 现象：`--draft false` 查不到就认为指标不存在，实际它是草稿态。
- 结论：`--draft` 是必填且无默认值，查重时**两个取值都要查**。

#### [Agent 自主发现] 用 `AssetFrom` 拼技术指标全名必然失败
- 现象：手册写「资产来源.所属表名」，把 `AssetFrom`（`dataworks-DataWorks2-...`）当资产来源拼进全名，关联报找不到技术指标。
- 结论：全名前半段就是资产返回的 `AssetFullName`（实测形如 `dataphin.all_data_types`），直接取用不要推导。

#### [人工注入] 技术指标已被占用时不要盲试
- 现象：关联报「一个技术指标只能被一个业务指标关联」，模型开始换字段名/换全名格式反复重试。
- 结论：这是业务唯一性约束不是参数格式问题，立刻停手并告知用户「该技术指标已被 X 关联」，让其选择换指标或先解除原关联。

### Reference Links

- [references/cli-installation-guide.md](./references/cli-installation-guide.md)
- [../../ram-policies.md](../../ram-policies.md)
- [references/acceptance-criteria.md](./references/acceptance-criteria.md)
- [references/related-commands.md](./references/related-commands.md)
- 关联 skill：[`develop-metric`](../develop-metric/SKILL.md)（无可用技术指标时的指标开发链路）、`query-asset-details`（资产画像/目录层级）、`configure-quality-rule`（给指标配质量监控）
