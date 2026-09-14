---
name: resolve-asset-guid
description: |-
  把用户能说出的业务信息（板块/项目/数据源 + 表名/字段名/资产名）拼成资产 GUID，回读校验后交给下游 skill。
  当用户要 GUID、界面查不到 GUID、下游接口要传 Guid/TableGuid/WatchObjectId 时进入。

  触发场景：只知表名却要 GUID（写资产属性/配质量规则/查资产详情/落标）；问 GUID 怎么拼；核对已有 GUID。

  触发词：资产GUID、拼GUID、Guid、TableGuid、dp_table、dp_ds_table、odps.、dp_index、cust_index、biz_index、dp_api、qbi_page。

  关键限制：**开场必问两事（资产类型 + 该类型所需信息），类型不得从名字推断；每段取值须逐段确认后才能拼**，禁止按表名相似外推；含内部ID的类型(dp_index/biz_index/dp_api/qbi_page)只能查；逻辑表第三段是板块名；项目名转小写不加_dev；前缀由引擎定(19种)、表名大小写看引擎；dp_ds_table 段数不定；GUID 错了接口不报错，必须回读校验。
---

# 资产 GUID 解析（按类型拼接 + 回读校验）

## 1. Scenario Description

Dataphin 资产 GUID 是资产的唯一标识，**界面上不直接展示**，但大量 OpenAPI 与子 skill 都以它为入参（`Guid` / `GuidList` / `TableGuid` / `WatchObjectId`）。用户手里通常只有业务信息（"fashion 板块的 dim_lk_cus 表"、"customers 表的 email 字段"），于是卡在第一步。

本 skill 负责这一段转换：**业务信息 → GUID → 回读校验 → 交付**。它是下列子 skill 的前置：

| 下游 skill | 需要的 GUID |
|---|---|
| [`manage-asset-attributes`](../manage-asset-attributes/SKILL.md) | 覆盖写属性的 `Guid`（TABLE / COLUMN） |
| [`query-asset-details`](../query-asset-details/SKILL.md) | 四板块共用的资产 `Guid`、`GuidList` |
| [`configure-quality-rule`](../configure-quality-rule/SKILL.md) | `WatchObjectId`（TABLE 类型就是资产 GUID） |
| [`manage-standard-mapping`](../manage-standard-mapping/SKILL.md) | 建落标映射的字段 GUID |
| [`manage-row-level-permission`](../manage-row-level-permission/SKILL.md) | `get-row-permission-by-table-guids` 的表 GUID |

**Architecture**：`Tenant → (BizUnit | Project | DataSource) → Table → Column`，GUID 就是这条归属链的字符串编码；指标 / API / 仪表板类资产的 GUID 含内部 ID，不在编码链上。

两条路径（选路规则见 §8 Step 1）：

```
业务信息
  ├─ 路径 A 可拼接：按公式拼 → 回读校验 → 交付
  └─ 路径 B 必须查：搜索接口命中 → 逐条比对选中 → 交付
```

> 完整公式与段语义见 [`references/guid-composition-matrix.md`](references/guid-composition-matrix.md)；每段从哪个接口取见 [`references/segment-resolution.md`](references/segment-resolution.md)。

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

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> install/update from https://aliyuncli.alicdn.com (see [`references/cli-installation-guide.md`](references/cli-installation-guide.md) for the OS-specific script).

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见套件级 [`../../ram-policies.md`](../../ram-policies.md)（子 skill 不自带，统一收口套件级文件）。本 skill 全部为只读 Action。

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
| `OpTenantId` | 是 | 操作租户 ID（19 位 snowflake，**字符串传**） | — |
| 资产类型 | 是 | 逻辑表 / 项目内物理对象 / 实时元表 / 镜像表 / 标签表 / 数据源表 / DataWorks 采集表 / 字段 / 各类指标 / API / 仪表板 | 不得默认，见 Step 0 |
| 归属对象 | 视类型 | 数据板块名（逻辑表）/ 项目名 + 引擎（项目内对象）/ 数据源名或 ID + schema（数据源表）/ DataWorks 空间 id + 数据源 id + 逻辑 Schema（DataWorks 采集表） | — |
| 资产名 | 是 | 表名 / 字段名 / 指标名 / API 名 / 仪表板名 | — |
| 环境 | 视类型 | `DEV` / `PROD`（同名表两环境各有独立 GUID；`dp_index.` GUID 自带环境段） | 不得默认，须与用户确认 |

### ★ [硬规则] 开场两个必问，不许猜

收到“给我 xxx 的 GUID”时，**先问两件事，问完再动手**（用 AskUserQuestion，一次问完）：

1. **这是什么类型的表 / 资产？** —— 选项：逻辑表 / 项目内物理表·视图·物化视图 / 实时元表 / 镜像表 / 标签表 / 数据源表 / DataWorks 采集表 / 字段 / 指标 / API / 仪表板。
2. **该类型 GUID 需要的具体信息**（照 §0.2 清单逐项列出，已知的标已有、未知的直接要）。

**四条绝对禁止**：

1. **禁止从名称形态推断类型**。看到 `LD_xxx.表名` 不得当逻辑表、看到 `a.b` 不得当 schema.表 或 项目.表、看到 `dim_`/`dws_`/`_tmp` 不得推表类型。实测：`dws_ai_ready_insight` 同时是 MaxCompute 项目表与 Doris 数据源表；`load_test.orders` 同时存在于两个 StarRocks 数据源。
2. **禁止用“表名相似”外推任何段**。`all_type0123` 与 `all_type` 名字相近，**不构成**它们同数据源 / 同空间 / 同 schema 的任何证据。
3. **禁止把“照抄同数据源已有表中段”当默认路径**。照抄的前提是用户已确认目标表与模板表**同源同 schema**；未确认就照抄 = 猜。
4. **禁止在有任何一段未确认时输出 GUID 全文**。可以输出段值确认表并标出缺哪一段，但不得给出一条可直接复制的完整串。

> **反查的定位边界**：反查（`list-tables` 等）只能用来① 校验用户已确认的信息、② 在类型与归属已定后取真值、③ 命中多条时**列候选让用户选**。它**不能**用来替用户断定“这是哪一类资产”或“你要的就是这条”。

### ★ [硬规则] 提问与列候选必须用业务语言，不能拿 ID 让用户选

问的时候**直接问缺的那样东西**，用用户在界面上看得到的名字：

| 场景 | ✅ 应该这么问 | ❌ 不要这么问 |
|---|---|---|
| 数据源歧义 | “**数据源是哪一个？**” + 列出 `数据源名(编码)`，如 `数据服务API行级权限_数据源(ds_demo)` | “选 A 还是 B”、或直接摆两串 19 位 `dataSourceId` |
| 项目歧义 | “**哪个项目？**” + 列项目名（必要时注明模式 BASIC/DEV_PROD） | 列 `ProjectId` 让用户认 |
| 板块歧义 | “**哪个数据板块？**” + 列板块名（如 `LD_SFC_train`） | 列 `BizUnitId` |
| 环境歧义 | “**开发还是生产？**” | 只写 `DEV/PROD` 而不说它们会导致不同 GUID |

内部 ID（`dataSourceId` / `ProjectId` / `BizUnitId`）**只作为附注**附在名字后面供核对，不作为用户的选择依据。

> 数据源名与编码是两个字段：`Name`（显示名，如“数据服务API行级权限_数据源”）与 `DataSourceCatalog`（编码，如 `ds_demo`，**DEV 侧带 `_dev`**）。用户习惯用任一种指代数据源，两者都要列；而 GUID 里用的是 `dataSourceId`，需做一次 名称/编码 → ID 的映射 `[实测]`。

### ★ [硬规则] 逐段确认才能拼

GUID 的每一段都必须有**确定的取值来源**，且在拼接前以表单 / 问答形式**与用户逐段确认**。拼错一段的症状与“资产不存在”完全相同，而接口不报错，所以“看着很像”的段值比缺值更危险。

**段值确认表（拼接前必须向用户输出这张表）**：

| # | 段 | 取值 | 来源 | 状态 |
|---|---|---|---|---|
| 1 | `tenantId` | … | 会话租户上下文 | ✅ 已确认 |
| 2 | …（按类型列齐所有段） | … | 用户提供 / 接口查得（列出命令）/ 用户确认同源后照抄 | ⚠️ 待确认 |

`状态` 只有三种：`✅ 已确认`（用户直给，或接口查得且用户核对）/ `⚠️ 待确认` / `❌ 无法获取`。**全部为 `✅` 才能进 Step 2 拼接。**

**收集方式三选一（用 AskUserQuestion 让用户选）**：

| 模式 | 含义 | 适用 |
|---|---|---|
| ① 我直接给全部段值 | 输出空白确认表当模板，用户逐段填 | 用户手上有界面信息；或接口不可用 |
| ② 你去查，我来确认（推荐） | AI 逐段调接口取候选值，附上命令与返回证据，请用户核对 | 凭证可用且有权限 |
| ③ 我给一部分，其余你查 | 用户先给关键归属（如数据源名 / 板块），AI 补齐其余段并回读 | 混合情形（最常见） |

> **接口不可用（凭证失效 / 无超管权限 / 网关无该 Action）时的强制出口**：立即告知用户“反查与回读都不可用”，转模式 ① / ③ 索取段值，**不得用任何形式的推断填补中段**。
>
> ★ **定为“接口不可用”前必须先排掉 `OpUserId` 问题**：403 `no permission to assume role of other users` 往往不是权限不够，而是请求带的 `OpUserId` 不是 AK 属主；去掉该参数重试即可（实测）。

> **[硬规则] 类型与归属对象不得猜**：这两项猜错必然产出一个「看起来对、查不到」的 GUID。用户没说清时先问，不要默认 PROD、不要默认板块=项目。

## 7. Observability (MUST follow for every aliyun command)

版本 `{version}`（Shell 变量 `SKILL_VERSION`）来自套件 `references/manifest.json` 的 `version` 字段，与 session-id 一同继承[父技能 §7](../../../SKILL.md#7-observability)。直接加载本子技能时先完成父层初始化；所有 CLI / SDK 调用使用父技能名称与同一版本，跨 Shell 调用须重新注入这些值。

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public list-biz-units --tenant-id "1234567890123456789" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 skill-version/{version}"
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
OP_TENANT_ID="<19 位租户 ID 字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/$SESSION_ID skill-version/$SKILL_VERSION"
```

> 独立部署环境下每条命令追加 `--profile dataphin-standalone --skip-secure-verify --op-tenant-id "$OP_TENANT_ID"`（父 skill §4.1）。

### Step 0 · 定资产类型 + 摊开该类型的必要信息（不可跳过）

**开场两件事，顺序不能反，且两项都靠“问”不靠“猜”**：① 先让用户明确资产类型；② 立即把该类型的**必要信息清单**摊给用户，缺哪项问哪项。

> **例外（省掉提问的唯一情形）**：Step 1 的 `ListTables` 反查**唯一命中**时，类型与归属已由平台返回值确定（`Type`/`Env`/`ProjectName`/`BizUnitName`/`DataSourceId`），此时不必再问类型，直接交付并把归属摊出来让用户核对。命中多条或 0 条时，本节两个必问仍全量生效。

> **[硬规则] 类型不得从名字推导**：用户没明说类型时，**直接问**，不要从限定名形态（`LD_xxx.表`、`a.b`）、前后缀（`dim_`/`dws_`/`_tmp`）或历史样本去推。实测反例：`dws_ai_ready_insight` 同时存在于 MaxCompute 项目与 Doris 数据源；`load_test.orders` 同时存在于两个 StarRocks 数据源 —— 光看名字无法定类型也无法定归属。

#### 0.1 先定类型

GUID 的前缀由资产类型唯一决定，**类型没定就没有公式**；只知道“是张表”也不够 —— `AssetType=TABLE` 下就有 6 族前缀。按用户描述归类到下表；描述含糊（只说"那张表"、"那个指标"）时**先问清**：

| 用户描述特征 | 资产类型 | GUID 前缀 |
|---|---|---|
| 维度表 / 事实表 / 汇总表 / 标签表、挂在"数据板块"下 | Dataphin 逻辑表 | `dp_table.` |
| 项目里的物理表 / 物理视图 / 物化视图，说得出项目名 | 项目内物理对象 | **引擎前缀**（19 个取值，查引擎对照表；MaxCompute = `odps.`） |
| 实时元表 / Flink 元表 | 实时元表 | `stream_table.` |
| 镜像表 | 镜像表 | `mirror_table.` |
| 标签表 | 标签表 | `label_table.` |
| 数据源里的表（MySQL / Hologres / Doris / Oracle…）、全域表 | 数据源表 | `dp_ds_table.`（5 段） |
| 从 DataWorks 采集过来的表 | DataWorks 采集表（独立特例） | `dp_ds_table.`（**7 段**） |
| 某张表的某个字段 / 列 | 字段 | 表 GUID + `.列名` |
| 规范建模指标、派生指标（原子指标+修饰词） | 技术指标 | `dp_index.` |
| 自定义指标（表字段登记成指标） | 技术指标 | `cust_index.` |
| 业务口径指标、GMV/DAU 这类业务定义 | 业务指标 | `biz_index.` |
| 数据服务 API | API | `dp_api.` |
| 报表 / 仪表板 / 图表 | 仪表板 / 图表 | `qbi_page_` / `qbi_component_` |

> ★ **项目内对象的前缀由项目的计算引擎决定**（共 19 个取值：`odps` / `hologres` / `starrocks` / `doris` / `adb_for_pg` / `hadoop` / `tdh_hadoop` / `aws_emr` / `argodb` / `lindorm_engine` / `gaussdb` / `databricks` / `selectdb` / `oushudb` / `emr_spark_serverless` / `dp_table` / `stream_table` / `mirror_table` / `label_table`）。完整对照表（含大小写开关）见 [`references/guid-composition-matrix.md`](references/guid-composition-matrix.md) §1.2；不确定引擎时用 `list-tables --catalog <项目名>` 取任意一张表的 `Guid` 照抄前缀。

#### 0.2 再摊必要信息清单（按类型）

类型一定，立即把对应行念给用户，明确“你必须告诉我什么 / 我负责查什么”，缺项当场问：

| 资产类型 | 用户必须提供 | AI 负责查 / 推导 |
|---|---|---|
| 逻辑表 | 数据板块名 + 表名 + 环境 | 板块名精确写法（`list-biz-units`）、小写归一 |
| 项目内物理对象 | **项目名 + 表名 + 存储格式/计算引擎 + 对象类型**（表/物理视图/物化视图/实时元表/镜像表/标签表）+ 环境 | 引擎→前缀映射、项目精确名与模式（BASIC 项目无 DEV）、大小写归一 |
| 数据源表 | **数据源名 + 库/schema + 表名 + 环境** | `dataSourceId`（分环境，`SearchDataSourceConfig` / `list-data-source-with-config`） |
| DataWorks 采集表 | 数据源名 + **DataWorks 空间 id + DataWorks 数据源 id** + 逻辑 Schema + 表名 | `dataSourceId`（两个 DataWorks 内部 ID **Dataphin 侧无接口可取**，必须用户给） |
| 字段 | 所属表的全部必要信息 + 字段名 | 表 GUID 先独立确认，再核列存在性 |
| 指标 / API / 仪表板 | 名称 + 子类型（派生/自定义/业务指标）+ 环境 | 不拼，直接反查取 `Guid` |

> **环境一项的例外**：项目为 `ModeEnum=BASIC` 时只有一套（`Env=PROD`，无 DEV 变体），此时环境不必再问 —— 但这一点需由接口确认（`ListProjects` 返回 `ModeEnum`），不能默认 `[实测]`。

### Step 1 · 先用 `ListTables` 反查取真值（主路径，优于拼接）

**能从平台查到就不要自己拼** —— `ListTables` 返回的 `Guid` 就是真值，比“拼 + 回读 + 排错”既准又快。先用表名做关键词反查，**并且 PROD / DEV 两个环境都查**，然后按命中数分三支：

| 命中数 | 处理 |
|---|---|
| **唯一 1 条** | 直接采用返回的 `Guid`。类型由返回的 `Type` 给出（这是**读数据**，不是推断），无歧义时不必再问类型；交付时把归属（数据源名/项目名/板块名、环境）摊出来让用户核对 |
| **多条** | **不得自行挑选**。按业务语言列候选（`数据源名(编码)` / 项目名 / 板块名 + 环境）让用户选，选完再交付 |
| **0 条** | 才进入拼接兜底：按 Step 0 问清类型 + 必要信息 → Step 2 逐段确认后拼 → Step 3 回读。同时要判断“是未采集还是未上架”并告知用户 |

反查实操要点（均实测）：

- **必须翻页拉全**：`keyword` 是模糊匹配，实测 `orders` 在 PROD 命中 143 条、超单页 100；只看第一页会漏真正目标。
- **客户端精确过滤**：拉全后按 `Name` 等值 + schema/项目/板块段筛，不能拿模糊命中的第一条当结果。
- **两个环境都要查**：实测有表只存于 DEV（`performance_schema.innodb_redo_log_files`）、也有只存于 PROD（BASIC 项目的表），默认只查 PROD 会误报“不存在”。
- **两个通道参数不同**：公共云 CLI `list-tables` 的 `--catalog`（项目名/板块名）**必填**，不填报 400 `MissingCatalog`；独立部署内部网关的 `ListTables`（业务参数包在 `TableQuery`）**可仅用 `keyword` 全租户搜**，不需 catalog —— 反查阶段优先用它。
- 返回项自带 `Type` / `Env` / `ProjectName` / `BizUnitName` / `DataSourceId`，这些就是交付时的校验证据。

### Step 1.2 · 反查不到时的选路：可拼 or 必须查

> 前提：Step 0 两个必问已得到用户明确回答。**类型未确认时不得进入拼接**。

| 类型 | 路径 | 理由 |
|---|---|---|
| `dp_table.` / 引擎前缀 / `stream_table.` / `mirror_table.` / `label_table.` / 字段 / `cust_index.` | **A 拼接** | 段全是名字 |
| `dp_ds_table.`（5 段，普通数据源表） | A 拼接 | dataSourceId + 单层 schema，可查可拼 |
| `dp_ds_table.`（7 段，DataWorks 采集表） | A 拼接（拿到两个中段 ID 即可），否则 **B 查** | 公式固定为 7 段特例，但 DataWorks 空间 id / 数据源 id 在 Dataphin 侧拿不到 |
| `dp_index.` / `biz_index.` / `dp_api.` / `qbi_page_` / `qbi_component_` | **B 查** | 含 `logicIndexId` / `logicId` / `apiId` / UUID，拼不出来 |

> 判定一个 `dp_ds_table.` 是不是 DataWorks 采集表：段数 > 5，且 `dataSourceId` 后紧跟**两个纯数字段**（DataWorks 空间 id、DataWorks 数据源 id）。**这是独立特例，不能套 5 段普通数据源表公式**；两个中段的取值优先问用户，其次照抄同数据源已有表 GUID 中段，都拿不到再反查。

### Step 2 · 路径 A：逐段确认后拼装

**Step 2.0 先出段值确认表（不可跳过）**：按 §6 的硬规则，先列齐本类型的全部段、逐段标出取值/来源/状态，并用 AskUserQuestion 让用户选收集方式（① 全给 / ② 你查我确认 / ③ 给一部分）。**所有段 `✅ 已确认` 才能往下走**。

公式（完整版见 [`references/guid-composition-matrix.md`](references/guid-composition-matrix.md)）：

```
dp_table.<tenantId>.<bizUnitName 小写>.<tableName 小写>                  # 逻辑表
<引擎前缀>.<tenantId>.<projectName 小写>.<对象名>                     # 物理表 / 物理视图 / 物化视图
stream_table.<tenantId>.<projectName 小写>.<表名 小写>                 # 实时元表
mirror_table.<tenantId>.<projectName 小写>.<表名 小写>                 # 镜像表
label_table.<tenantId>.<projectName 小写>.<表名 小写>                  # 标签表
dp_ds_table.<tenantId>.<dataSourceId>.<schema 小写>.<tableName 小写>    # 普通数据源表
dp_ds_table.<tenantId>.<dataSourceId>.<DataWorks空间id>.<DataWorks数据源id>.<逻辑Schema>.<tableName>   # DataWorks 采集表（独立特例）
<表 GUID>.<columnName>                                              # 字段
cust_index.<字段 GUID 去掉前缀后的全部内容>                        # 自定义指标
```

**大小写归一（硬规则，拼错了回读就是空）**：

| 部位 | 处理 |
|---|---|
| 逻辑表的板块名 + 表名 | 全部转小写 |
| **所有引擎的项目名** | 恒转小写 |
| 物理表类的表名 | 引擎不区分大小写（odps / hadoop / stream_table / mirror_table / label_table 等）→ 转小写；引擎区分大小写（hologres / starrocks / doris / adb_for_pg / selectdb / oushudb）→ **原样保留** |
| 数据源表的 schema + 表名 | 全部转小写 |

段值获取（命令与裁剪写法见 [`references/segment-resolution.md`](references/segment-resolution.md)）：

```bash
# 数据板块名（逻辑表第三段，拼进 GUID 前转小写）
aliyun dataphin-public list-biz-units --tenant-id "$OP_TENANT_ID" \
  --cli-query 'BizUnitList[].{Id:Id,Name:Name}' --user-agent "$UA"

# 项目名（项目内对象第三段；--mode 事实必填，BASIC/DEV_PROD 各查一次）
aliyun dataphin-public list-projects --mode DEV_PROD --page-no 1 --page-size 100 \
  --cli-query 'PageResult.ProjectList[].{Id:Id,Name:Name,Mode:Mode}' --user-agent "$UA"

# 数据源 ID（数据源表第三段）
aliyun dataphin-public list-data-source-with-config --tenant-id "$OP_TENANT_ID" \
  --data-source-name "<数据源名>" --page 1 \
  --cli-query 'PageResult.DataSourceList[].{Id:Id,Name:Name,Type:Type}' --user-agent "$UA"

# 字段名原样大小写（字段 GUID 用）
aliyun dataphin-public get-table-columns --tenant-id "$OP_TENANT_ID" \
  --catalog "<项目名或数据板块名>" --table-name "<表名>" \
  --cli-query 'ColumnList[].{Name:Name,DataType:DataType}' --user-agent "$UA"
```

三条硬规则（各自都有真实踩坑记录）：

0. **每一段都得有来源且经用户确认**（§6 硬规则）—— 未确认的段不得用“同名前缀的其它表”或任何相似性推断填上。
1. **逻辑表第三段是数据板块名，不是项目名**（实测 `BizUnitName=LD_Fashion` / `ProjectName=fashion_cdm` → GUID 段 `ld_fashion`）。同一业务下逻辑表用板块名、物理表用项目名（实测：`dp_table.….ld_train.…` vs `odps.….train_dev.…`），不能互代。
2. **项目名转小写但不加后缀**：DEV 项目名本身就带 `_dev`（实测 `train_dev` / `ods_cw_dev`），取 `ListProjects` 的 `Name` 转小写即可。
3. **前缀与大小写查表、不猜**：引擎前缀与表名大小写开关一律查 [`guid-composition-matrix.md`](references/guid-composition-matrix.md) §1.2；DataWorks 中段、数据源 schema 拿不准时直接转 Step 4 反查。

### Step 3 · 回读校验（**唯一放行判据，不可跳过**）

```bash
aliyun dataphin-public get-catalog-asset-details \
  --OpTenantId "$OP_TENANT_ID" \
  --GetCatalogAssetDetailsQuery '{"Guid":"<拼出的 GUID>","IncludeColumns":true}' \
  --user-agent "$UA"
```

四项全部满足才算通过：

1. 负载非空 → GUID 存在；
2. `AssetType`（必要时 `SubType`）与 Step 0 判定一致；
3. `AssetName` / `AssetFullName` 与用户描述一致（含板块/项目/数据源归属）；
4. 字段级 GUID 另需 `Columns[]` 中存在同名列。

> **★ GUID 错了接口不报错**：`GetCatalogAssetDetails` 查不存在的 GUID 只是负载为空，`GetAssetAttributes` 更是 `Success=true` 但结果里不含该 GUID（均为实测）。所以「命令没报错」绝不能当作校验通过。
>
> **6.0 环境降级校验**（`get-catalog-asset-details` 需 6.1+）：用 `list-tables --catalog <…> --keyword <表名>` 精确比对返回 `Guid` 是否与拼出的字符串完全相等。

### Step 4 · 路径 B / 校验失败 → 反查取官方 GUID

```bash
# 表（含未上架）：资产清单。--catalog 必填，不填报 400 MissingCatalog
aliyun dataphin-public list-tables --tenant-id "$OP_TENANT_ID" \
  --catalog "<项目名或数据板块名>" --keyword "<表名>" \
  --cli-query 'PageResult.TableList[].{Name:Name,Guid:Guid,Type:Type,Env:Env}' --user-agent "$UA"

# 任意类型（仅已上架）：资产目录
aliyun dataphin-public list-catalog-assets --tenant-id "$OP_TENANT_ID" \
  --asset-type INDEX --query-mode ASSET_SEARCH --keyword "<指标关键词>" \
  --page-size 20 --user-agent "$UA" --format json

# 业务指标：直取 Data.Guid（业务参数须包在 BizMetricByNameQuery；draft 必填）
aliyun dataphin-public get-biz-metric-by-name --tenant-id "$OP_TENANT_ID" \
  --biz-metric-name "<指标英文名>" --draft false --user-agent "$UA"

# 图表：从所属仪表板详情的 Columns[] 取（图表不可枚举）
aliyun dataphin-public get-catalog-asset-details --OpTenantId "$OP_TENANT_ID" \
  --GetCatalogAssetDetailsQuery '{"Guid":"<仪表板 GUID>","IncludeColumns":true}' --user-agent "$UA"
```

选路要点：

- `list-catalog-assets` 只覆盖资产目录**已上架**资产；**未上架**的表只能用 `list-tables`（资产清单）。搜不到时先判断是"没上架"还是"元数据没采集"，不要换写法反复重试。
- **命中多条必须逐条比对再选**：同名表 DEV/PROD 各一条、`_org` 后缀表是另一个资产（均为实测）。按板块/项目/数据源 + 环境比对，不要取第一条。
- `dp_index.` 命中项自带环境段（`dev` / `prod`）：**取到哪个环境的 GUID，后续接口就必须用同一环境**，否则详情/血缘恒返回 `data: null`。

### Step 5 · 交付

输出必须含五项，缺一不可：

1. **GUID 全文**（可直接复制）
2. **段值确认表**（逐段标明取值与来源：用户提供 / 接口查得 / 用户确认同源后照抄）
3. **资产类型**（`AssetType` + 必要时 `SubType`）
4. **校验证据**（用哪个接口回读的、`AssetName`/`AssetFullName`/`Env` 是什么）
5. **下游用法**（该 GUID 在目标接口里对应哪个参数：`Guid` / `TableGuid` / `WatchObjectId`）

两类情形**不得交付 GUID 全文**，只能交确认表 + 缺口说明：

- 有任何一段处于 `⚠️ 待确认` / `❌ 无法获取`；
- 段值全齐但 Step 3 回读未通过（此时需说明已排除项：板块/项目段、schema 段、大小写、环境、是否已采集/已上架）。

> 回读因**凭证/权限**而无法执行时：必须在交付中显式标注「未经回读校验」并说明阻塞原因，**不得用“段值都对”冒充校验通过**；同时告知用户可在界面自验的路径。

### 执行前确认（本 skill 为只读）

本 skill 只调用只读接口，不创建/修改/删除任何资源，无需写操作 HITL 确认。但有一条交接约束：

> **[硬规则] 未通过 Step 3 校验的 GUID 禁止交给写类 skill**（如 `manage-asset-attributes` 覆盖写属性、`manage-standard-mapping` 建映射）。GUID 错误不会在写入时报错，只会表现为"写了但界面上看不到"，且覆盖写不可自动回滚。

## 9. Success Verification

三步法（详见 [`references/acceptance-criteria.md`](references/acceptance-criteria.md)）：

1. **同步返回 `Code: OK` ≠ 成功**：必须核对返回体里真的有目标资产（GUID 不存在时接口不报错）。
2. **类型与归属反查一致**：回读得到的 `AssetType` / `AssetFullName` / `Env` 与 Step 0 判定和用户描述逐项对齐。
3. **下游可用性验证**（推荐）：把 GUID 交给下游前，先用一个只读下游接口试一次（如 `get-asset-attributes` 或 `get-quality-watch-by-object-id`），确认目标接口认这个 GUID。

## 10. Cleanup

本 skill 全程只读，不创建任何资源，无需清理。解析结果（GUID）仅在会话内传递给下游 skill，不落盘。

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. **先分类，再逐段确认，最后才拼**：跳过分类直接拼、或跳过逐段确认直接拼，是所有 GUID 问题的共同起点；分类要细到“哪一种表”（逻辑表 / 项目内物理对象 / 实时元表 / 镜像表 / 标签表 / 数据源表 / DataWorks 采集表）而不是“是张表”。
2. **能反查到就不拼，但歧义一律交用户**：`ListTables` 返回的 `Guid` 就是真值（Step 1 主路径）；唯一命中直接用，多条命中按业务语言列候选让用户选，0 条才转拼接。不拿反查结果替用户挑候选。
3. **前缀、大小写、中段一律查表或照抄，不得外推**：引擎前缀与表名大小写开关查 `guid-composition-matrix.md` §1.2；数据源 schema、DataWorks 中段取自同项目/同数据源已有对象的 GUID。
4. **19 位 ID 一律字符串**（`OpTenantId` / `DataSourceId`），JSON 与命令行都加引号。
5. **只读查询必带 `--cli-query` 裁剪**：`list-tables` 不裁剪单次实测可达 115k 字符，`get-table-columns` 单表约 18k 字符。
6. **不要拉裸 `aliyun dataphin-public --help`**（全量帮助实测 44.5k 字符），按关键词检索命令名即可。

### ✗ 平台限制

#### ✗ GUID 在界面上不可见，也没有"按名称转 GUID"的专用接口
- 限制描述：Dataphin 界面不展示资产 GUID，OpenAPI 也没有 `GetGuidByName` 这类专用换算接口。
- 替代方案：本 skill 的两条路径（按公式拼 + 回读校验 / 搜索接口反查）即为替代方案。

#### ✗ `ListCatalogAssets` 只覆盖已上架资产
- 限制描述：资产目录接口查不到未上架资产，容易被误判成"资产不存在"。
- 替代方案：改用 `list-tables`（资产清单，含未上架），`--catalog` 必填。

#### ✗ 图表（COMPONENT）不可枚举
- 限制描述：`list-catalog-assets --asset-type COMPONENT` 返 `TotalCount=0`。
- 替代方案：从所属仪表板详情的 `Columns[]` 取图表 GUID。

### 常见坑

#### [人工注入] 逻辑表 GUID 用项目名拼 → 静默查不到
- 现象：`dp_table.<tenant>.<项目名>.<表名>` 回读为空。
- 结论：第三段必须是**数据板块名转小写**（实测 `LD_Fashion` → `ld_fashion`，同表项目名是 `fashion_cdm`，二者不同）。

#### [人工注入] 给项目名手工加 `_dev` 后缀 → 查不到
- 现象：`odps.<tenant>.<项目名>_dev.<表名>` 查不到，返回空。
- 结论：DEV 项目的名字本身就带后缀，取 `list-projects` 返回的 `Name` 转小写即可，不要自己补后缀。

#### [人工注入] 把项目内对象的前缀一律当成 `odps.`
- 现象：实时元表 / 镜像表 / 标签表、或 Hologres / StarRocks 项目的表拼成 `odps.<tenant>.<项目>.<表>` 后回读为空。
- 结论：前缀共 19 个取值，由项目计算引擎或对象类型定（`hologres` / `starrocks` / `doris` / `stream_table` / `mirror_table` / `label_table`…），查 `guid-composition-matrix.md` §1.2 对照表。物理视图 / 物化视图与物理表同构，不需特殊处理。

#### [人工注入] 大小写没归一 → 回读恒为空
- 现象：拿界面上的 `LD_Fashion` / `Train_Dev` / 大写表名直接拼进 GUID，查不到任何资产。
- 结论：逻辑表（板块+表名）、数据源表（schema+表名）、**所有引擎的项目名** 都转小写；只有**区分大小写引擎（hologres / starrocks / doris / adb_for_pg / selectdb / oushudb）的表名**保留原样。这一条尚无真机样本，首次遇到时先拼原样回读、不中再试小写。

#### [人工注入] 用“表名相似”外推中段（本 skill 实测踩过的坑）
- 现象：只知道表名 `all_type0123`，就拿同前缀的 `all_type` 的 GUID 把数据源 id / 空间 id / DW 数据源 id / schema 四段整段搬过来，包装成“照抄模板”。
- 结论：名字相似不是同源证据。实测样本池（24 张表）里就有 6 个数据源、5 种 schema 路径。**四段里只有租户与表名是有据的，其余必须逐段确认**（§6）。

#### [人工注入] 反查不可用时仍然“先拼一个”
- 现象：凭证失效 / 非超管导致 `list-tables` 与回读全部 403，却仍给出一条看起来很确定的 GUID。
- 结论：A 路（拼）与 B 路（查）会**同时**被权限卡死。此时必须告知用户并转为向用户索取段值（§6 模式 ①/③），交付时标注「未经回读校验」。

#### [Agent 自主发现] `OpUserId` 不匹配 → 全线 403，极易误判为“无权限 / 凭证失效”
- 现象：数据源与元数据接口全部报 `Dataphin.OpenAPI.Forbidden: Current user is not the super admin … no permission to assume role of other users`，看起来像“AK 不是超管”。
- 结论：真正原因是请求里带的 `OpUserId` 不是 AK 属主（需 assume role 权限）。**去掉 `OpUserId` 后同一把 AK 立即可用**（实测）。宣布“接口不可用、转人工索取段值”之前，**必须先排除这一项**，否则会白白退化成问用户要 ID。

#### [Agent 自主发现] 数据源 DEV / PROD 各有独立 ID，且同库同表名可挂在多个数据源
- 现象：`mysql_dlink_1010` 实测返回两个 ID（PROD `7375744037241779648` / DEV `7375744037594101184`）；而 `dataphin03.store_sales_detail` 同时存在于两个不同数据源下。
- 结论：`dp_ds_table.` 第三段随**环境**变，所以环境必须先确认；且“库名+表名”不足以定位，**必须指定数据源**，反查命中多条时按 `DataSourceId` 逐条比对后再选。

#### [人工注入] 把 DataWorks 采集表当普通数据源表拼成 5 段
- 现象：拼成 `dp_ds_table.<tenant>.<dsId>.<schema>.<表>` 查不到。
- 结论：DataWorks 采集表是**独立特例**，固定 7 段：`dsId` 后还有 DataWorks 空间 id 与 DataWorks 数据源 id。两者在 Dataphin 侧拿不到 → 优先问用户要这两个 ID，其次照抄同数据源已有表中段，最后才反查。

#### [人工注入] 按点号切 `qbi_page_` / `qbi_component_` GUID → 切错段
- 现象：报表类 GUID 用 `.` split 得到一整段。
- 结论：**只有报表类用下划线分隔，其余类型全部用点**；且 `报表id` 本身是带连字符的 UUID（实测 `qbi_page_<tenant>_<dsId>_498f84a6-9beb-4aab-a511-d20e862b8f9b`），只能查不能拼。

#### [人工注入] 把 `$_$VALID` / `$_$INVALID` 后缀的对象 ID 当资产 GUID
- 现象：`dp_table.<tenant>.<板块>.<表>$_$VALID` 查资产详情为空。
- 结论：带该后缀的是**落标映射 / 发布对象 ID**，不是资产 GUID。

#### [人工注入] 用 `SumTableGuid` 拿技术指标的所属表 GUID
- 现象：字段恒为 `null`。
- 结论：改用 `AssetFullName` 拆出「表名.字段名」后按公式拼表 GUID 并回读校验。

### Reference Links

- [`references/guid-composition-matrix.md`](references/guid-composition-matrix.md) — 各类型公式、段语义、实测样例（含 15 个 POC 实测样本对照表）、坑
- [`references/segment-resolution.md`](references/segment-resolution.md) — 每段从哪个接口取（含裁剪写法）
- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)（套件级 RAM，子 skill 不自带）
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
- [`../query-asset-details/references/asset-type-matrix.md`](../query-asset-details/references/asset-type-matrix.md) — 拿到 GUID 之后各类型能查哪些板块
