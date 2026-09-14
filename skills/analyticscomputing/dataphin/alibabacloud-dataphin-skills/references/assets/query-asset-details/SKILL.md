---
name: query-asset-details
description: |-
  一站式拼出资产目录里一个资产的完整详情页，**覆盖 5 类资产**：表（属性/字段/使用说明 + 数据预览 + 表与字段血缘 + 质量概况）、技术指标（属性 + 数据预览 + 所属字段血缘 + 所属字段质量规则）、业务指标（属性 + 相关指标 + 使用说明）、数据服务 API（属性 + API 文档）、仪表板（属性 + 图表信息）。
  当用户场景涉及 资产详情、资产画像、看这张表/这个指标/这个 API/这个报表、字段列表、使用说明、数据预览、上下游血缘、字段血缘、质量概况、相关指标、指标口径、API 文档、请求/返回参数、图表列表、目录层级 时进入。

  触发场景：给一个 GUID/名称要“这个资产的全貌”；只看其中某一板块；属性写入后回读校验。

  触发词：资产详情、资产画像、目录详情、字段列表、使用说明、数据预览、前50条、血缘、上下游、字段血缘、质量概况、质量分、相关指标、指标口径、业务指标、技术指标、API 文档、仪表板、图表信息、get-catalog-asset-details、get-biz-metric-by-name、get-data-service-api-document。

  关键限制：**先认资产类型再选板块**（业务指标无预览/无血缘；API与仪表板无预览/血缘/质量）；**汇报术语必须对齐界面**（`SimpleNodeInfos`=「产出任务」不是「调度节点」；`ReadCount`=「浏览量」；`CollectionCount`=「收藏数」）；**`IncludeDetailedAttributes` 不传则 `ReadCount`/`CollectionCount`/`SimpleNodeInfos` 恒为 null**；字段级 `Standards`/`ClassifyName`/`LevelShortName` 是活字段**必须逐列输出**，只有 `Columns[].QualityScore` 是恒 null 的死字段；**表级质量分无 OpenAPI**；**API 错误码无 OpenAPI**；**仪表板图表信息只有 GUID+名称**且放在 `Columns[]` 里；**质量模块响应体在 `PageResult`/具名键下，不在 `Data` 下**，只读 Data 会恒得 null 并误判成未授权；**质量输出不得透出「监控对象/watch」等内部词**，只说这张表下配了多少条质量规则；字段名与 SDK 文档不一致（`Id`/`Type`/`TableInfo`/`Strength`/`TestRun*`/`ValidateSuccess`）；`GetQualityWatchByObjectId` 的 WatchType/WatchObjectId 是 **query 位参数**且 TABLE 类型的 WatchObjectId **就是资产 GUID**；`ListQualityRules` 的 watchId **事实必填**；`GetBizMetricByName` 必须用 `BizMetricByNameQuery` 包裹且 **`draft` 必填**；PagedQuery* 是旧裸名会报 Unknown API；`GetTableLineages` 的 NeedUpstream/NeedDownstream **默认 false 必须显式传 true** 且 FilterQuery 必传，**单次只返回 1 跳，全链路必须客户端 BFS 递归且要先让用户选范围**；数据预览会起即席查询**消耗计算资源，需 HITL 确认**且分区表必须带分区谓词；`Instruction` 是富文本 JSON 不能直展；GetAssetAttributes 单次 GuidList ≤ 50；19 位 ID 必须字符串。
---

# 资产目录详情查询（5 类资产 × 分板块）

## 1. Scenario Description

把资产目录里一个资产的**详情页**用 OpenAPI 拼出来。**板块随资产类型变**：

| 资产类型 | 板块组合 | 主 API |
|---|---|---|
| **表** `TABLE` | 属性详情·字段列表·使用说明 + 数据预览 + 表/字段血缘 + 质量概况 | `GetCatalogAssetDetails` / `ExecuteAdHocTask` / `GetTable(Column)Lineages` / 质量三件套 |
| **技术指标** `INDEX` | 属性详情 + 数据预览 + **所属字段**血缘 + **所属字段**质量规则 | 同上，但先把指标映射到「所属表 + 字段」 |
| **业务指标** `BIZ_INDEX` | 属性详情 + **相关指标** + **使用说明** | `GetCatalogAssetDetails` + **`GetBizMetricByName`** |
| **数据服务 API** `API` | 属性详情 + **API 文档**（基本信息/请求参数/返回参数） | `GetCatalogAssetDetails` + **`GetDataServiceApiDocument`** |
| **仪表板** `PAGE` | 属性详情 + **图表信息** | `GetCatalogAssetDetails`（`IncludeColumns: true`） |

**完整矩阵、各类型非空字段差异、以及技术指标→字段的映射路径，全部在** [`references/asset-type-matrix.md`](references/asset-type-matrix.md)（已实测）。

**Architecture**：

```
资产 GUID
  └─ GetCatalogAssetDetails（所有类型的统一入口）→ AssetType + SubType
       ├─ TABLE      → 预览 / 表·字段血缘 / 质量概况
       ├─ INDEX     → AssetFullName 拆出「表名.字段名」→ 拼表 GUID → 字段血缘 + 字段质量规则
       ├─ BIZ_INDEX → GetBizMetricByName → RelatedBizMetrics / MetricDefinition / OperateInstructionContent
       ├─ API       → ApiId → GetDataServiceApiDocument → Request/Response/PublicParamList
       └─ PAGE      → Columns[] 即图表列表（ChartCount 对得上）
```

> **★ 板块④ 质量的能力边界（必须先读）**：**平台的「表级质量分」没有任何 OpenAPI 可取**。质量接口只能给出「规则清单 + 校验通过/不通过」，分数需本 skill 自算，且计分方式/权重本身也不可读。结论与实测证据见 [`references/quality-profile-feasibility.md`](references/quality-profile-feasibility.md)——**回答用户“质量分是多少”之前必须先看这份，不要把自算通过率当成平台质量分报出去。**

> 属性的**写入**请用子 skill `manage-asset-attributes`（`UpdateAssetAttributes`）；质量规则的**配置**请用 `configure-quality-rule`；业务指标的**增删改**请用 `manage-biz-metric`。

## 2. Installation

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```
（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

> **命令收录说明**：`GetAssetAttributes` 为 V6.3 新增、`GetCatalogAssetDetails` 为 V6.3 增强出参；若 `aliyun dataphin-public --help` 未列出对应 kebab-case 命令，先 `aliyun plugin update`；仍未收录时走 §8 末尾的 SDK 兜底（API 版本 `2023-06-30`）。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, print, or expose AK/SK values in the conversation or logs
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
> install/update from https://aliyuncli.alicdn.com (see `references/cli-installation-guide.md` for the OS-specific script).

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [`references/ram-policies.md`](references/ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
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
| `Guid` | 是 | 目标资产 GUID（四板块共用同一个 GUID） | — |
| 查询板块 | 是 | 要哪几块：属性 / 预览 / 血缘 / 质量。**用户没说就问，不要默认全跑**（预览要花钱、血缘可能很大） | — |
| **血缘范围** | **是（查血缘时）** | **直接上下游（1 跳）** / **全链路（客户端 BFS 递归）**，另问方向（仅上游 / 仅下游 / 双向）。接口单次只给 1 跳，见 §8 Step 3.0 | 直接上下游 |
| `GuidList` | 是（批量查属性值） | 资产 GUID 数组，单次 ≤ 50 | — |
| `AttributeCodeList` | 否 | 属性编码过滤；不传返回全部属性 | 全部 |
| `IncludeColumns` | **是（实际必传）** | 是否含字段列表（字段列表/字段血缘/**关联标准·数据分类·数据分级** 都靠它） | false（**Step 1 一律传 true**） |
| `IncludeDetailedAttributes` | **是（实际必传）** | 不只管明细属性：**`ReadCount` / `CollectionCount` / `SimpleNodeInfos`（产出任务）/ `AssetTags` / `MaintainUser*` 也只有它才回填**，不传则全为 `null` | false（**Step 1 一律传 true**） |
| 预览行数 | 否 | 预览 LIMIT | 50 |
| 预览分区 | 分区表必填 | 分区表必须钉一个分区值，见 §8 Step 2 | — |
| `NeedUpstream` / `NeedDownstream` | 否 | 血缘方向；**表血缘默认 false，要查必须显式传 true** | 见 §8 Step 3 |

> **[MUST] 数据预览需 HITL 确认**：预览会提交即席查询任务、真实读表并消耗计算资源。执行前必须把「引擎类型 / 目标表 / 完整 SQL / 分区」摆给用户确认，用户明确同意后才提交。

## 7. Observability (MUST follow for every aliyun command)

版本 `{version}`（Shell 变量 `SKILL_VERSION`）来自套件 `references/manifest.json` 的 `version` 字段，与 session-id 一同继承[父技能 §7](../../../SKILL.md#7-observability)。直接加载本子技能时先完成父层初始化；所有 CLI / SDK 调用使用父技能名称与同一版本，跨 Shell 调用须重新注入这些值。

**session-id 由父 skill `alibabacloud-dataphin-devops` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"
```

> SDK 兜底路径请把同一字符串设置到 OpenAPI Client 的 `user_agent` 配置项，保持可观测性一致。

## 8. Core Workflow

```bash
OP_TENANT_ID="<19 位租户 ID 字符串>"
GUID="<资产 GUID>"
SESSION_ID="<inherited from alibabacloud-dataphin-devops>"
UA="AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/$SESSION_ID skill-version/$SKILL_VERSION"
```

**执行顺序**：Step 1 必须先跑——它既定资产类型（决定后续走哪几个板块），又一次性产出后续全部要用的入参。

### Step 0 · 认资产类型，定板块范围（不可跳过）

跑完 Step 1 拿到 `AssetType` + `SubType` 后，**先按下表划定板块范围再动手**：

| `AssetType` | 可用板块 | 详细步骤 |
|---|---|---|
| `TABLE` | 属性 + 预览 + 表·字段血缘 + 质量 | Step 1 → 2 → 3 → 4 |
| `INDEX`（技术指标） | 属性 + 预览（单列）+ **仅所属字段**血缘 + **仅所属字段**质量 | Step 1 → **Step 5** → 2/3/4（均限定到该字段） |
| `BIZ_INDEX`（业务指标） | 属性 + 相关指标 + 使用说明 | Step 1 → **Step 6** |
| `API` | 属性 + API 文档 | Step 1 → **Step 7** |
| `PAGE`（仪表板） | 属性 + 图表信息 | Step 1（`IncludeColumns: true`）→ **Step 8** |

> **对不支持的板块直接说明「该资产类型无此板块」，不要去硬调接口拿空结果再解释。** 例：业务指标不落物理表，没数据预览也没血缘；要看落地情况走 `AssociatedTechMetrics[]` 跳到技术指标。

### Step 1 · 资产属性详情 + 字段列表 + 使用说明（GetCatalogAssetDetails，只读）

> **[MUST] 汇报用词一律查** [`references/ui-field-mapping.md`](references/ui-field-mapping.md)：字段名必须用**界面原文**，禁止按英文字段名直译。已实测踩过的错译：`SimpleNodeInfos` → 界面叫「**产出任务**」（不是「调度节点」）、`ReadCount` → 「**浏览量**」、`CollectionCount` → 「**收藏数**」（不是「阅读数/收藏次数」）。

```bash
# ★ 两个开关都必须开：IncludeDetailedAttributes 不只管使用说明与自定义属性，
#   ReadCount / CollectionCount / SimpleNodeInfos / AssetTags / MaintainUser* 也都靠它才回填
aliyun dataphin-public get-catalog-asset-details \
  --OpTenantId "$OP_TENANT_ID" \
  --GetCatalogAssetDetailsQuery '{
    "Guid": "'"$GUID"'",
    "IncludeColumns": true,
    "IncludeDetailedAttributes": true
  }' \
  --user-agent "$UA"
```

`Data` 共 58 个字段（**实测**），按板块用途分组取用（**「界面叫法」列即汇报时该用的词**）：

| 用途 | 界面叫法 | 字段 |
|---|---|---|
| 基础信息 | 名称 / 英文名 / 子类型 / 资产来源 | `AssetDisplayName` / `AssetName` / `AssetFullName` / `AssetType` / `SubType` / `AssetDescription` / `AssetFrom` / `Guid` |
| **使用说明** | 使用说明 | **`Instruction`**（无内容时为 `null`；**有内容时是富文本 JSON 字符串，不是纯文本**，见下方） |
| 自定义属性 | 业务属性 / 技术属性 / 管理属性 | `CustomAttributes[]` |
| **字段列表** | 字段信息 | **`Columns[]`**，逐列全给，见下方「字段列表必输出项」 |
| 目录挂载 | 归属目录 | `Directories[]`（含 `TopicId/TopicName/TopicDescription/DirectoryId/DirectoryName/DirectoryDescription/DirectoryChain[]`） |
| **产出任务** | **产出任务** | **`SimpleNodeInfos[]`**：`NodeId` / `NodeName` / `SubBizType` / `Owners[]` / `Project` / `BizUnit` / `NodeScheduleType` / `Env`。**★ 不要叫「调度节点」** |
| 上下架 / 可见范围 | 初次上架时间 / 最近上架时间 / 发布人 | `FirstOnShelveTime` / `LastOnShelveTime` / `LastOnShelveUser` / `ShelveViewScopeType` / `ProfilingReportViewScopeType`（均只读） |
| 用数统计 | **收藏数** | `CollectionCount` ✅ 口径与界面一致，可直接报 |
| 用数统计 | **浏览量** | `ReadCount` ✅ 可直接报（需 `IncludeDetailedAttributes: true`，否则 `null`） |
| **→ 喂给 Step 2 预览** | — | `DatasourceId` / `DataSourceName` / `AssetFullName` / `IsPartitionTable` / `PartitionKey` / `ProjectName` |

**★ 字段列表必输出项（`Columns[]`，实测均有值，一个都不能省）**：

| 界面列名 | 字段 | 说明 |
|---|---|---|
| 字段名称 | `Name` + `DisplayName` | |
| 数据类型 | `DataType` | |
| 描述/备注 | `Description` | |
| 业务类型/关联实体 | `BizType` / `AssociatedEntity` | `BizType` 实测取值 `DIMENSION` / `INDEX` / `STAT_PERIOD` |
| **关联标准** | **`Standards[]`** | **实测有值**，结构 `[{"Id":266881,"Name":"订单编码","Code":"ORDER_CODE"}]`，可多条 |
| **数据分类** | **`ClassifyName`** | **实测有值**，路径串如 `/交易信息/`、`/研发域/项目管理/知识管理/失效分析/`，挂根上时为 `/` |
| **数据分级** | **`LevelShortName`** | **实测有值**，`L1`~`L4` |
| 质量分 | `QualityScore` | **实测恒 `null`**（60 张表逐张扫描，非空列数 0）→ 输出 `-` 并注明「表/字段级质量分无 OpenAPI」 |

> **不要因为抽查的头几列是 `null` 就把整列砍掉**——某列为空只代表该字段没打标（实测 `dim_lk_cus` 6 列全无分类分级，而 `mfg_fin_ods.d_order_sale` 125 列里 99 列有分类分级、3 列有关联标准）。**唯一恒空的只有 `QualityScore`。**

**★ 热度与产出任务为空时先查开关（实测，汇报前必读）**：

**`ReadCount`（浏览量）/ `CollectionCount`（收藏数）/ `SimpleNodeInfos`（产出任务）/ `AssetTags` / `MaintainUser*` 只有 `IncludeDetailedAttributes: true` 才回填**。只开 `IncludeColumns` 时它们全是 `null`——把 `null` 当 0 报出去就是「数字对不上」。拿到 `null` 时先想“是不是没开这个开关”，而不是直接报 0。所以 Step 1 两个开关一律都传 `true`。


`Directories[]` 层级链结构（V6.3 起无需新增入参即返回）：

```jsonc
{
  "TopicId": 113086, "TopicName": "专题B",
  "TopicDescription": null,              // 描述为空返回 null
  "DirectoryId": 1130876689044, "DirectoryName": "A1",
  "DirectoryDescription": "",            // 描述为空返回 空串
  "DirectoryChain": [                    // ★ 从根到叶子，按 Level 升序，末节点即叶子
    { "DirectoryId": 1130876689040, "DirectoryName": "根目录", "Level": 1 },
    { "DirectoryId": 1130876689044, "DirectoryName": "A1",   "Level": 2 }
  ]
}
```

要点（**已在测试环境端到端验证**）：

- `DirectoryChain` 末节点 `DirectoryId` == 外层 `DirectoryId`；一个资产可挂多个目录/专题，每项各带独立完整链。
- 空描述有两种形态：`TopicDescription` 为 `null`，`DirectoryDescription` 为 `""`，展示层要同时兼容。
- **`Columns[].QualityScore` 是死字段，不要拿它当字段级质量分**：实测在一张**确有 8 条质量规则、且当天确有校验异常**的表上，105 个字段的该字段仍全为 `null`；另对 60 张表逐张扫描，非空列数也是 0。质量相关信息一律走 Step 4。
- **其余三项字段级信息（`Standards` / `ClassifyName` / `LevelShortName`）是活字段，必须逐列输出**：与 `QualityScore` 不同，这三项实测大量回填（如 `mfg_fin_ods.t_org` 22 列中 19 列有分类分级、1 列有关联标准）。**不要把它们与 `QualityScore` 归为一类一起砍掉。**

**★ `Instruction`（使用说明）是富文本 JSON 字符串，不能当纯文本直展**（实测）：

```jsonc
// 界面上只是一行文字 "1121112"，返回却是嵌套数组序列化后的字符串
"[\"root\",{},[\"p\",{},[\"span\",{\"data-type\":\"text\"},[\"span\",{\"data-type\":\"leaf\"},\"1121112\"]]]]"
```

展示时必须先 `json.loads` 再**递归抽取 `data-type: leaf` 节点的文本**拼成纯文本；直接把原串展给用户会满屏转义字符。解析失败时降级为“使用说明已配置，请到界面查看”，不要抛原串。

**批量读自定义属性值**（多个资产横向对比 / 属性写入后回读校验用 `GetAssetAttributes`，比逐个查详情省一个数量级）：

```bash
aliyun dataphin-public get-asset-attributes \
  --OpTenantId "$OP_TENANT_ID" \
  --QueryCommand '{
    "GuidList": ["odps.<tenant>.<project>.<table>"],
    "AttributeCodeList": ["code02", "shelve_description"]
  }' \
  --user-agent "$UA"
```

- 不传 `AttributeCodeList` → 返回该资产**全部**自定义属性；传了 → 只返回指定属性（顺序同传入）。
- **GUID 不存在**：`Success=true` 且 `AssetAttributeList` 中**不含**该资产（不报错）。
- **批量上限**：`GuidList` 单次 ≤ 50，超限整体 400 拒绝。

### Step 2 · 数据预览（即席查询跑 LIMIT 50）

> **[MUST HITL]** 本步骤**起真实计算任务**，是本 skill 唯一的非只读动作。必须先向用户展示「引擎 / 表 / SQL / 分区」并取得同意。
> **[MUST SELECT-only]** 只允许 `SELECT`。禁止把 DDL/DML（`INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER`/`TRUNCATE`/`MERGE`）拼进预览 SQL；用户要求改数据一律拒绝并改走 `execute-ad-hoc-task` 让其显式授权。

**2.1 从 Step 1 结果推导执行参数**（不要问用户重复信息）：

| Step 1 字段 | 推导出 |
|---|---|
| `SubType` = `DATASOURCE_TABLE` | 数据源表 → 用 `DatasourceId` + schema 走对应引擎 |
| `SubType` = 项目内表（`odps.` 前缀 GUID） | 用 `ProjectName` 走 `MaxCompute_SQL` |
| `DatasourceId` | 即席查询的 `--data-source-id`（**19 位，字符串传**） |
| `AssetFullName`（如 `default.ods_orders`） | `<schema>.<table>`，schema 即 `--data-source-schema` |
| `IsPartitionTable` + `PartitionKey` | 分区表必须补分区谓词，见 2.3 |

> **GUID 自带这两个入参**：数据源表 GUID 形如 `dp_ds_table.<tenant>.<datasourceId>.<schema>.<table>`——`DatasourceId` 和 schema 直接躺在 GUID 里，与 `Data.DatasourceId` / `AssetFullName` 一致（**实测**）。

**2.2 各引擎预览 SQL 方言 + OperatorType** 见 [`references/data-preview-sql.md`](references/data-preview-sql.md)。**不要一律写 `LIMIT 50`**——Oracle 用 `ROWNUM`、SQL Server 用 `TOP`、DB2 用 `FETCH FIRST`。

**2.3 分区表必须钉分区**（否则 MaxCompute 全表扫描保护直接拦、Hive/大表则可能拖垮资源）：

```bash
# 先取一个存在的分区值（推荐，避免猜分区猜空）
aliyun dataphin-public execute-ad-hoc-task --dataphin-profile <p> --env PROD \
  --project-id "$PROJECT_ID" --tenant-id "$OP_TENANT_ID" \
  --operator-type MaxCompute_SQL \
  --code "SHOW PARTITIONS <project>.<table>" \
  --user-agent "$UA" --format json
```

**2.4 提交预览并取结果**：

```bash
# MaxCompute 分区表
aliyun dataphin-public execute-ad-hoc-task --dataphin-profile <p> --env PROD \
  --project-id "$PROJECT_ID" --tenant-id "$OP_TENANT_ID" \
  --operator-type MaxCompute_SQL \
  --code "SELECT * FROM <project>.<table> WHERE ds='<分区值>' LIMIT 50" \
  --user-agent "$UA" --format json | jq '.ExecuteResult | {TaskId, SubTaskCount}'

# 数据源表（MySQL/PG/Oracle/SQLServer 等统一 DATABASE_SQL）
aliyun dataphin-public execute-ad-hoc-task --dataphin-profile <p> --env PROD \
  --project-id "$PROJECT_ID" --tenant-id "$OP_TENANT_ID" \
  --operator-type DATABASE_SQL \
  --data-source-id "<DatasourceId 字符串>" \
  --data-source-schema "<schema>" \
  --code "SELECT * FROM <schema>.<table> LIMIT 50" \
  --user-agent "$UA" --format json | jq '.ExecuteResult | {TaskId, SubTaskCount}'

# 取结果（sub-task-id 从 0 开始；刚跑完可能要等几秒）
sleep 5
aliyun dataphin-public get-ad-hoc-task-result --dataphin-profile <p> --env PROD \
  --project-id "$PROJECT_ID" --tenant-id "$OP_TENANT_ID" \
  --task-id "$TASK_ID" --sub-task-id 0 \
  --user-agent "$UA" --format json | jq -r '.ExecuteResult.Result'
```

结果格式：`[[列名...],[行...]]`；`DATABASE_SQL` 会在首行多一段 `COLUMN_TYPE:[...]` 元数据。**结果为空先别急着下"表没数据"的结论**——按 §12 常见坑逐条排（分区没选对 / 表名没写全限定名 / 结果还没上传）。

> 即席查询的完整参数矩阵、OperatorType 全枚举、报错对照表复用子 skill [`execute-ad-hoc-task`](../../dev/execute-ad-hoc-task/SKILL.md)，本 skill 不重复维护。

### Step 3 · 血缘关系（表血缘 + 字段血缘，只读）

**3.0 [MUST] 先问用户要「直接上下游」还是「全链路」——不要默认全跑**

**`GetTableLineages` / `GetTableColumnLineages` 单次调用只返回「直接（1 跳）上下游」**，不是传递闭包（实测判据见下）。所以「全链路」必须由本 skill 客户端递归，调用量成倍上升，**范围必须让用户选**：

| 用户选项 | 做法 | 调用量 |
|---|---|---|
| **① 直接上下游**（默认，未说明时先推荐这个） | 对目标 GUID 调一次，取边即完 | 1 次 |
| **② 全链路（全部上下游）** | 以目标 GUID 为起点做 **BFS 逐层展开**，每个新节点再调一次 | 未知，可能几十上百次 |

**问法（照抄）**：「血缘要查**直接上下游**（只看紧邻的一层，1 次调用，快）还是**全链路**（顺着链路一直往上/往下展开，要按层递归调用，节点多时会比较慢）？还要指定只看上游 / 只看下游 / 双向吗？」

选 ②「全链路」时的**强制约束**（不遵守会把上下文打爆、甚至无限循环）：

- **必须设深度上限并告知用户**：默认 `MAX_HOP=5`；未展开完就到顶时，明确说「已到第 N 层上限，更深层未展开」，不要假装查完了。
- **必须全局去重**：用 `(InputTableGuid, OutputTableGuid, NodeId)` 三元组去重边、用 GUID 去重待访问队列——实测相邻表之间边会重复返回。
- **必须做环检测**：已访问过的 GUID 不再入队（血缘存在互相引用的情况）。
- **单向展开不要来回跑**：查上游全链路时对每个新节点只开 `--need-upstream true`；查下游同理。双向全链路 = 两棵树分别展开，不要在同一次 BFS 里混着走，否则会横向扩散到无关分支。
- **超过 ~50 个节点先停下来汇报并问是否继续**，附上当前层数与已发现节点数。
- 汇报时**按层级组织**（第 1 层 / 第 2 层 …），不要平铺一堆边。

**★ 「只返回 1 跳」的实测判据**（POC V6.3，5 张表）：每张表返回的边里，**「既不以目标 GUID 为输入、也不以其为输出」的边恒为 0 条**；而把邻居表单独再查一次，邻居自己还有首次结果里没出现过的边（如 `mfg_fin_ods.d_order_sale` 首次返 2 条边，其上游 `fct_order_sale_df` 单独查有 3 条边、其中 2 条首次没返回）。**→ 拿一次调用的结果当「全部血缘」汇报是错的。**

```bash
# 表血缘：★ NeedUpstream / NeedDownstream 默认 false，要查必须显式传 true
#      ★ FilterQuery 事实必传——一个开关都不传实测报 DPN.Commons.InternalError
#      ★ 这一次调用只给「直接上下游」；全链路需拿返回的邻居 GUID 递归再调
aliyun dataphin-public get-table-lineages \
  --tenant-id "$OP_TENANT_ID" \
  --table-guid "$GUID" \
  --need-upstream true \
  --need-downstream true \
  --user-agent "$UA"

# 字段血缘：这两个开关默认就是 true，只想看单向时才需显式关掉
aliyun dataphin-public get-table-column-lineages \
  --tenant-id "$OP_TENANT_ID" \
  --table-guid "$GUID" \
  --need-upstream true \
  --need-downstream true \
  --user-agent "$UA"
```

要点：

- **返回负载键又是另一套**（实测）：`TableLineageList` / `TableColumnLineageList`——既不是 `Data` 也不是 `PageResult`。先打印响应顶层键。
- **返回的是边（edge）列表，不是树**：每条带 `InputTableGuid` / `OutputTableGuid`。上下游要自己拆：`OutputTableGuid == 目标GUID` → 上游；`InputTableGuid == 目标GUID` → 下游。
- **两个接口默认值相反**（`GetTableLineages` false/false，`GetTableColumnLineages` true/true）——表血缘不显式传 `true` 会拿到“看起来没血缘”的空结果。**两个都显式传，不依赖默认。**
- **`FilterQuery` 事实必传**：完全不传实测报 `DPN.Commons.InternalError`；两个开关都传 false 则返回空负载 `{}`。
- **无深度/跳数入参**（实测 api-meta 只有 `NodeEnv` / `NodeIdList` / `NeedUpstream` / `NeedDownstream` / `NeedNotExistObject` 五个过滤项）——想要多跳只能客户端递归，不要去找 `depth` / `level` 这类参数。
- `NodeId` 区分血缘来源：有值 = 由加工任务解析出来的；`null` = 注册血缘（人工/外部登记）。
- **字段血缘只覆盖有加工任务的链路**（实测）：同一张表表级有 2 条下游（均 `NodeId=null` 注册血缘），但字段级出向为 **0 条**。不要因为字段血缘为空就说“没下游”。
- **`InputTableDeleted` 表级与字段级会不一致**（实测：同一张上游表表级 `false`、字段级 `true`）——**不能拿它判定表是否真的被删**，要确认得去查该表自身详情。
- `--table-guid` 用的就是 Step 1 那个资产 GUID（query 位参数）。
- `--node-env`（`dev`/`prod`）与 `--node-id-list` 用于按加工任务过滤；只看生产链路时传 `--node-env prod`。
- `--need-not-exist-object true` 才会带出**资产清单里已不存在**的表（下游表被删/未采集时链路会断，排查断链必开）。
- 血缘规模可能很大（实测一张 105 字段的维表就有 104 条字段血缘）：**先汇总再展开**，不要把全量原始边塞进上下文。

### Step 4 · 质量概况（内部链路：watch → 规则 → 执行结果）

> **先读结论**：本步骤**拿不到平台的表级质量分**。它给出的是「这张表下配了多少条质量规则 / 都是哪些 / 最近一次校验的通过情况」，分数只能自算。判据与实测证据：[`references/quality-profile-feasibility.md`](references/quality-profile-feasibility.md)。

> **★ [MUST] 不要向用户透出「监控对象」这个词。** 界面页签叫「质量概况」，页面上没有「监控对象」——它是 OpenAPI 侧的实现概念（`QualityWatch`）。
> 汇报时直接说「**这张表下共配置了 N 条质量规则（生效 M 条）**」；未配时说「**这张表下还没有配置质量规则**」。
> `watchId` / `watchTaskId` / `watch` / `监控任务` 均只作为内部串联用，**不出现在给用户的输出里**（用户要自己去界面排查时再按需给）。完整措辞对照见 [`references/ui-field-mapping.md`](references/ui-field-mapping.md) §6。

**4.0 前置：拿到空结果先看响应顶层键（★ 实测重重踩过的坑）**

**质量模块的业务负载不在 `Data` 键下**，而在 `PageResult` / 具名键下：

| Action | 负载键 | 列表键 |
|---|---|---|
| `ListQualityWatches` | `PageResult` | `QualityWatchList` |
| `ListQualityRules` | `PageResult` | `QualityRuleList` |
| `ListQualityRuleTasks` | `PageResult` | `QualityRuleTaskList` |
| `GetQualityWatchByObjectId` | **`QualityWatchInfo`** | — |
| `GetQualityWatchTask` | **`WatchTaskInfo`** | — |
| `GetCatalogAssetDetails`（对比） | `Data` | — |

> 只取 `Data` 会让所有质量接口看起来都是 `Code=OK` + `Data=null`，极易误判成“没配置 / 没授权”。**拿到空结果的第一反应必须是打印响应顶层键，确认自己读的是不是正确的负载键**，再谈业务结论。

**同时注意：字段名与 SDK v1.0 文档不一致**（以实测为准）：`watchId`→**`Id`**、`watchType`→**`Type`**、`table`→**`TableInfo`**、`ruleStrength`→**`Strength`**、`tryRun*`→**`TestRun*`**、规则任务的 `validateResult`→**`ValidateSuccess`**(bool)。完整对照表见 [`references/quality-profile-feasibility.md`](references/quality-profile-feasibility.md) §4。

**4.1 资产 → watchId（`GetQualityWatchByObjectId`，**仅内部串联用**）**

```bash
# ★ WatchType / WatchObjectId 是 query 位参数
aliyun dataphin-public get-quality-watch-by-object-id \
  --tenant-id "$OP_TENANT_ID" \
  --watch-type DATASOURCE_TABLE \
  --watch-object-id "<对象ID>" \
  --user-agent "$UA"
```

- `WatchType` 按 Step 1 的 `SubType` 选：项目内 Dataphin 表（含逻辑表 `DIM_NORMAL` 等）→ `TABLE`；数据源表（全域表）→ `DATASOURCE_TABLE`；实时元表 → `REALTIME_LOGICAL_TABLE`；指标 → `INDEX`；数据源 → `DATASOURCE`。
- **`WatchObjectId` 对 `TABLE` 类型就是资产 GUID**（实测：传 `dp_table.<tenant>.<bizunit>.<table>` 直接命中，无需另找内部 ID）。数据源类监控（`DATASOURCE`）才传数字 `DataSourceId`。
- 命中后从 **`QualityWatchInfo`** 里读：`Id`（即 watchId）/ `Name` / `Status` / `RuleCount` / `EnabledRuleCount` / **`LatestWatchTaskId`** / `TableInfo`。
- 真的未配时返回空——但**先排除 4.0 的读错负载键问题**再下这个结论；确认未配则直接输出「这张表下还没有配置质量规则」（**不要写成「未配置监控对象」**），不再往下走。
- **同名表会有多个 watch**（实测：keyword 搜 `dim_employee` 命中 4 个：DEV/PROD × 本表/`_org` 后缀表）。用 `list-quality-watches` 兼底时，**必须用 `TableInfo.Id` 精确匹配目标 GUID**，不能取第一条。

**4.2 watchId → 规则清单（`ListQualityRules`）**

```bash
# ★ Action 名是 ListQualityRules；--watch-id 事实必填
aliyun dataphin-public list-quality-rules \
  --tenant-id "$OP_TENANT_ID" \
  --watch-id "<watchId>" \
  --page-no 1 --page-size 50 \
  --user-agent "$UA"
```

- **Action 名**：真实名是 `ListQualityRules`。用户文档里的 `PagedQueryQualityRules` 是 v1.0 SDK 旧裸名，**实测直调报 `Unknown API: PopSDKPagedQueryQualityWatches` 同类错误**，POC/独立部署必须用 CLI 命令的 PascalCase 名。
- **`watchId` 事实必填**：文档标为可选，**实测不传直接报 `DPN.Bus.ParamsValidateError: watchId is null!`**。所以 4.1 拿不到 watchId 时，4.2 根本没法跑，不要空转重试。
- 返回 `PageResult.QualityRuleList[]`：`Id` / `Name` / **`Strength`**（强弱）/ `Status`（启停）/ `TemplateId` / `TemplateType` / `CatalogList` / `ValidateObject` / `ValidateConditionList` / `ScheduleBindList`，以及 `TestRunRuleTaskStatus`、`TestRunRuleValidateResult`。
- **⚠️ 这里的 `TestRun*` 是「试跑」结果，不是生产调度的执行结果**。用试跑结果代表"这张表的质量情况"是错的——试跑是配规则时人工点的一次性验证，可能早已过期、也可能从没跑过。真实执行结果必须走 4.3。
- **注意三个不同的数**（实测易混）：`RuleCount`（配了多少）≠ `EnabledRuleCount`（生效多少）≠ 本次任务跑出的规则任务数。汇报时分母写错会严重误导（如“8 条规则只过了 0 条”）。

**4.3 执行结果（★ 优先用 `GetQualityWatchTask` 的 `RuleCountInfo`）**

```bash
# ★ 最接近界面「质量概况」的聚合数据：按强/弱/校验三类给计数
aliyun dataphin-public get-quality-watch-task \
  --tenant-id "$OP_TENANT_ID" \
  --watch-task-id "<LatestWatchTaskId>" \
  --user-agent "$UA"

# 需要逐条异常明细时再拉规则任务列表
aliyun dataphin-public list-quality-rule-tasks \
  --tenant-id "$OP_TENANT_ID" \
  --watch-task-id "<LatestWatchTaskId>" \
  --page-no 1 --page-size 50 \
  --user-agent "$UA"
```

`WatchTaskInfo.RuleCountInfo` 结构（**实测**）——三类规则各给四个计数，直接就是质量概况要的数：

```jsonc
"RuleCountInfo": {
  "ValidateRuleCount": { "TotalRuleCount": 0, "FinishedRuleCount": 0,
                         "ErrorRuleCount": 0, "SuccessRuleCount": 0 },
  "StrongRuleCount":   { "TotalRuleCount": 1, "FinishedRuleCount": 1,
                         "ErrorRuleCount": 1, "SuccessRuleCount": 0 },  // 强规则 1 条异常
  "WeakRuleCount":     { "TotalRuleCount": 0, "FinishedRuleCount": 0,
                         "ErrorRuleCount": 0, "SuccessRuleCount": 0 }
}
```

逐条明细看 `PageResult.QualityRuleTaskList[]`：`RuleId` / `Status`（任务状态）/ **`ValidateSuccess`（bool，是否通过——字段名不是文档里的 `ValidateResult`）** / `ValidateObjectType` / `ValidateObjectName`（校验对象）/ `ValidatePartition`（校验分区）/ `BizDate`。也可用 `--biz-date` 取某天的结果。

> **`Status=SUCCESS` 不等于校验通过**（实测共存：`Status=SUCCESS` + `ValidateSuccess=false`）——前者是“任务跑完了”，后者是“数据没问题”。汇报质量情况只能看 `ValidateSuccess`。

**4.4 历史趋势（可选，`ListQualityWatchTasks`）**

```bash
# 没有 watchId 过滤参数，用表名 keyword 拉回来后在客户端按 WatchId 筛
aliyun dataphin-public list-quality-watch-tasks \
  --tenant-id "$OP_TENANT_ID" \
  --keyword "<表名>" --page-no 1 --page-size 50 \
  --user-agent "$UA"
```

`PageResult.QualityWatchTaskList[]` 每条 = 一个业务日期的一次监控，自带 `RuleCountInfo` + `BizDate` + `WatchId` + `Status`，**直接就能排出逐日异常趋势**（实测：同一 watch 连续 3 天强规则 `ErrorRuleCount=1`，属于长期未修复）。

- **无 `--watch-id` 过滤**，必须客户端按 `WatchId` 筛；keyword 会把同名/同前缀表的 watch 一起带回来。
- 该接口返回体里 **`WatchInfo` 为空**，认不出是哪张表——只能靠 `WatchId` 关联 4.1 的结果。
- 判断“是否新发生”时必看趋势，不要只拿当天一点下结论。

**4.5 汇总为「质量概况」**

输出必须区分**平台事实**与**自算指标**，不能混；且**一律用「这张表下的质量规则」口径叙述，不出现「监控对象」**：

| 项 | 来源 | 口径 |
|---|---|---|
| 这张表下有没有配质量规则 | 4.1 `QualityWatchInfo` 非空 | 平台事实（**表述为「已配置 N 条质量规则」，不说「已配监控对象」**） |
| 规则总数 / 生效规则数 | `RuleCount` / `EnabledRuleCount` | 平台事实 |
| 强/弱规则分布 | 4.2 `Strength` | 平台事实 |
| **强/弱/校验规则的 总数·已完成·异常·通过** | **4.3 `RuleCountInfo`** | **平台事实（首选）** |
| 最近一次校验的状态与业务日期 | `LatestWatchTaskStatus` + 4.3 `BizDate` | 平台事实 |
| **逐日异常趋势** | **4.4 `ListQualityWatchTasks`** 的 `RuleCountInfo` + `BizDate` | 平台事实 |
| 异常规则明细 | 4.3 中 `ValidateSuccess=false` 的条目（强规则优先列） | 平台事实 |
| **规则通过率（自算）** | `SuccessRuleCount / FinishedRuleCount` | **本 skill 自算，≠ 平台质量分**，必须显式标注口径与分母 |
| ~~字段级质量分~~ | ~~`Columns[].QualityScore`~~ | **实测死字段，恒为 `null`，不可用** |
| **表级平台质量分** | — | **当前无 OpenAPI（待补项）**，只能到界面看，必须在输出末尾如实告知 |

**固定输出模板（照此格式交付，不要自创；注意里面没有「监控对象」「watchId」）**：

```text
质量概况（<表全名>，<Env>，业务日期 <BizDate>）
├─ 质量规则
│   ├─ 这张表下共配置了 <RuleCount> 条质量规则（生效 <EnabledRuleCount> 条，禁用 <RuleCount-EnabledRuleCount> 条）
│   ├─ 强弱分布：强规则 <n> 条 / 弱规则 <n> 条
│   └─ 质量负责人：<QualityOwnerName>
├─ 最近一次质量校验（<Status>）
│   ├─ 强规则：总 <T> / 已完成 <F> / 异常 <E> / 通过 <S>
│   ├─ 弱规则：同上四个计数
│   └─ 校验规则：同上四个计数
├─ 异常明细（强规则优先，无则写“无”）
│   └─ 规则「<Name>」（<TemplateName>）
│        校验对象 <ValidateObjectName>（<ValidateObjectType>），分区 <ValidatePartition>
├─ 逐日趋势（近 N 天）
│   └─ <BizDate>：强规则异常 <E> 条 → 连续 <n> 天异常 / 当日新增
├─ 自算指标（非平台质量分）
│   └─ 规则通过率 = 通过 <S> / 已完成 <F> = <x>%
│      口径：取最近一次质量校验的规则计数；未执行规则已排除；未做强弱加权
└─ 说明：平台口径的「表级质量分」暂无 OpenAPI，需到 Dataphin 界面查看
```

四条硬要求：

1. **分母必须写全**——`RuleCount`（配了多少）/ `EnabledRuleCount`（生效多少）/ `FinishedRuleCount`（本次跑完多少）三个数分开列，不能只报一个。
2. **末尾那句质量分说明不得省略**——用户问“质量分多少”时尤其不能拿通过率充数。
3. **未配规则时不要套模板**——直接一句「这张表下还没有配置质量规则」，并先确认不是 4.0 的读错负载键问题。
4. **不得出现「监控对象」「watch」「watchId」「watchTaskId」「监控任务」**这些内部词；`watchId` 之类 ID 只在用户明确要求排查线索时才附上，并说明是「内部标识」。

### Step 5 · 技术指标（INDEX）→ 定位所属表与字段

技术指标的预览/血缘/质量**全部依赖这一步**，先做完再跑 Step 2/3/4。

**5.1 拆 `AssetFullName` 拼表 GUID**（实测：`AssetFullName` = `<所属表名>.<字段名>`）

| 指标类型 | 表 GUID 拼法 |
|---|---|
| `dp_index.`（标准指标） | `dp_table.<tenant>.<BizUnitName 小写>.<表名>` |
| `cust_index.`（自定义指标） | `dp_ds_table.<tenant>.<DatasourceId>.<schema>.<表名>`（schema 从指标 GUID 中段取） |

**5.2 必须回读校验**（两项都要过，否则不往下走）：

```bash
aliyun dataphin-public get-catalog-asset-details \
  --OpTenantId "$OP_TENANT_ID" \
  --GetCatalogAssetDetailsQuery '{"Guid":"<拼出的表GUID>","IncludeColumns":true}' \
  --user-agent "$UA"
```

1. 返回非空 → 表 GUID 拼对了；
2. `Columns[]` 里存在 `Name == <字段名>` 那一列 → 指标确实是该表的字段。

字段 GUID = `<表GUID>.<字段名>`。

> **不要用 `SumTableGuid`**——实测该字段在技术指标上**恒为 `null`**，靠不住。

**5.3 三个板块的限定方式**

| 板块 | 做法 |
|---|---|
| 数据预览 | `SELECT <字段名> FROM <表全名> WHERE <分区键>='<分区值>' LIMIT 50`（分区表仍须钉分区） |
| 字段血缘 | 调 `GetTableColumnLineages(TableGuid=<表GUID>)` 拿全表，再**客户端过滤** `InputColumnName == <字段名> or OutputColumnName == <字段名>`——接口**无按列过滤的入参** |
| 字段质量 | 按 Step 4 拿到该表 watch 与规则后，过滤 `ValidateObject.Type == "COLUMN" && ValidateObject.Name == <字段名>`（实测 `ValidateObject` 结构就是 `{"Type":"COLUMN","Name":"<字段名>"}`）；执行结果再按 `ValidateObjectName == <字段名>` 过滤 |

要点：

- **一个指标字段可能有多条入向血缘**（多字段汇总）——实测 `order_cnt_cm` 由 2 个上游字段经同一任务汇总而成，**要全列出，不要只取第一条**。
- **所属表没配质量规则时**（实测很常见）直接输出「该指标所属表下还没有配置质量规则」，不要继续调。

### Step 6 · 业务指标（BIZ_INDEX）→ 相关指标 + 使用说明

```bash
aliyun dataphin-public get-biz-metric-by-name \
  --tenant-id "$OP_TENANT_ID" --name "<指标英文名>" --draft false --user-agent "$UA"
```

**两个契约坑（实测连踩两次）**：

1. 业务参数必须包在 **`BizMetricByNameQuery`** 里（顶层平铺报 `Missing required argument: BizMetricByNameQuery`）；
2. **`draft` 必填**（只传 name 报 `DPN.Commons.InvalidParam: draft cannot be null`）。`false`=已发布态，`true`=草稿态。

负载键 `Data`，汇报这几项：

| 信息 | 字段 |
|---|---|
| **指标口径/定义** | **`MetricDefinition`**（业务指标最核心的信息） |
| **相关指标** | **`RelatedBizMetrics[]`**：`Name` / `DisplayName` / `Description` / **`RelationType`**（实测 `POSITIVE`）/ `ListStatus`（`ON_SHELVE` / `ON_SHELVE_MODIFY`） |
| **关联技术指标** | **`AssociatedTechMetrics[]`**——业务指标到物理落地的桥梁，应一并给出 |
| **使用说明** | **`OperateInstructionContent`**（+ `OperateInstructionEnabled`） |
| 目录 | `Catalogs[]`，带 `ParentPath`（如 `/业财一体客户/客户A/`），比 Step 1 的 `Directories` 更直观 |
| 其他 | `Labels` / `BizOwnerName` / `ViewScope` / `MetricRelationDiagramSwitchOpen` + `Expression` |

> **★ 使用说明有两个来源、形态不同**：这里的 `OperateInstructionContent` 是**纯文本**，而 Step 1 的 `Instruction` 是**富文本 JSON**。**业务指标优先用 `OperateInstructionContent`**（免解析）；不一致时以专用接口为准。

### Step 7 · 数据服务 API → API 文档

```bash
# Id 直接用 Step 1 返回的 ApiId
aliyun dataphin-public get-data-service-api-document \
  --tenant-id "$OP_TENANT_ID" --data-service-api-document-id <ApiId> --user-agent "$UA"
```

负载键 `Data`，实测 37 个字段，按四块组织输出：

| 分块 | 字段 |
|---|---|
| 基本信息 | `ApiId` / `Name` / `Description` / `GroupName` / `ProjectName` / `Version` / `Env` / `Protocol` / `RequestMethod` / `ReturnType` / `ScriptType` / `IsPagedQuery` / `UpdateRate` |
| 请求参数 | **`RequestParamList[]`** + **`PublicParamList[]`**（公共参数）；每项含 `Name`/`Type`/`Sample`/`IsRequired`/`Operator`/`DefaultValue` |
| 返回参数 | **`ResponseParamList[]`** + **`ResultSample`**（返回示例） |
| 运行配置 / 数据源 | `ApiTimeout` / `ReturnLimit` / `OpenCache` + `CacheTime` / `ResourceGroupName` / `DirectDatasourceName` / `TableName` / **`Sql`** |

**两条硬要求**：

- **错误码拿不到**：实测 37 个键里无任何 `ErrorCode*` 字段，CLI 也无单独命令。必须如实说明「错误码 OpenAPI 未提供，需到界面 API 文档页查看」，**不要用 HTTP 状态码或自编一套充数**。
- **`Sql` 谨慎输出**：它是 API 背后的完整查询语句，含库表名与业务逻辑。默认只汇总（涉及哪张表、几个参数占位符），用户明确要求时才贴全文。

### Step 8 · 仪表板（PAGE）→ 图表信息

**图表列表就在 `Columns[]` 里**（实测：`ChartCount=10` 且 `Columns` 返 10 项）——仪表板复用了这个字段，**必须传 `IncludeColumns: true`**：

```jsonc
{
  "Guid": "qbi_component_<tenant>_<dsId>_<pageId>_<componentUuid>",
  "Name": "指标趋势图",        // ← 图表名称，唯一有效信息
  "DataType": null, "Standards": null, "QualityScore": null   // 对图表无意义，恒为 null
}
```

要点：

- **只有图表 GUID 与名称**（实测名称形如 `明细表`、`仪表盘-ent_bizenddate_918237`、`指标趋势图`）。
- **`Name` 不可靠，两种退化情况均实测到过**：
  - **未命名图表的 `Name` 直接等于其 UUID**（如 `e1e04d63-11a7-465d-b669-9997d6d0a5cd`）——展示时应转写为「未命名图表」并附 UUID 片段，**不要直出一串 UUID 当图表名**；判定方法：`Name` 与 `Guid` 末段相等。
  - **图表名会重复**（实测同一仪表板出现 3 个 `指标趋势图-资产总量计数表`）——**唯一标识只能用 GUID**，不要按名称去索引/去重。
- 一致性校验：`len(Columns) == ChartCount`，不等说明有图表未被采集。
- 另两个可用信息：**`BiCatalog`**（BI 侧目录路径，如 `dataphin测试空间/dpv5test/dp5报表上架`）、`AssetFrom`（BI 工具来源，如 `Quick BI`）。
- **需要逐图表创建/修改时间时**：图表 GUID 本身就是资产 GUID（`AssetType=COMPONENT`），对它单独调 `GetCatalogAssetDetails` 可多拿 `CreateTime`/`ModifyTime`（`Columns[]` 不带时间）。N 个图表 = N 次调用，**只在用户关心“哪些图表最近改过”时才做**。
- **✗ 图表类型/绑定数据集/字段/查询条件拿不到**——三条路已穷尽（`ListCatalogAssets assetType=COMPONENT` 返 `TotalCount=0` 不可枚举；图表与仪表板血缘均返空数组；自定义属性 `AttributeList` 为空）。**不要重复探**，直接告知需到 BI 工具查。

### SDK 兜底路径（命令未收录时）

新增/增强 Action 未进本地插件时，用通用 OpenAPI SDK 直调（Python 示例，API 版本 `2023-06-30`，RPC 风格）：

```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as om
from alibabacloud_tea_util import models as um
import json, os

conf = om.Config(
    access_key_id=os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
    access_key_secret=os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
    endpoint=os.environ["DATAPHIN_OPENAPI_ENDPOINT"],  # 独立部署必填
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(os.environ["SUITE_ROOT"]) / "references/scripts"))
from skill_user_agent import build_user_agent
conf.user_agent = build_user_agent()
client = OpenApiClient(conf)

params = om.Params(action="GetCatalogAssetDetails", version="2023-06-30",
    protocol="HTTPS", method="POST", auth_type="AK", style="RPC",
    pathname="/", req_body_type="formData", body_type="json")
body = {"GetCatalogAssetDetailsQuery": json.dumps(
    {"guid": "<GUID>", "includeColumns": True}, ensure_ascii=False)}
req = om.OpenApiRequest(query={"OpTenantId": "<tenant>"}, body=body)
runtime = um.RuntimeOptions(); runtime.ignore_ssl = True   # 独立部署自签证书
resp = client.call_api(params, req, runtime)["body"]
print(resp)
```

**★ 兜底时业务参数的位置不能一律照抄**（实测踩坑，见 §12）：

| Action | 包裹参数 | 位置 |
|---|---|---|
| `GetCatalogAssetDetails` | `GetCatalogAssetDetailsQuery` | body |
| `GetAssetAttributes` | `QueryCommand` | body |
| **`GetBizMetricByName`** | **`BizMetricByNameQuery`**（且 `draft` 必填） | body |
| `ListQualityRules` / `ListQualityRuleTasks` / `ListQualityWatches` | `ListQuery` | body |
| **`GetQualityWatchByObjectId`** | `WatchType` / `WatchObjectId`（平铺，无包裹） | **query（参与签名）** |
| **`GetDataServiceApiDocument`** | `Id` / `VersionId`（平铺） | **query** |
| **`GetTableLineages` / `GetTableColumnLineages`** | `TableGuid` 在 query；`FilterQuery` 在 body | 混合 |

## 9. Success Verification

- **属性/字段/说明**：`Success=true`；`Columns[]` 条数与界面一致；**两个开关（`IncludeColumns` + `IncludeDetailedAttributes`）都已传 true**（否则 `ReadCount`/`CollectionCount`/`SimpleNodeInfos` 恒为 `null`）；字段级的**关联标准 / 数据分类 / 数据分级**已逐列输出（而非整列省略）；术语已对齐界面（**产出任务** / **浏览量** / **收藏数**）；`Directories[].DirectoryChain` 存在且 `Level` 升序、末节点为叶子。
- **数据预览**：任务 `TaskStatus=SUCCESS` 且 `Result` 行数 ≤ 请求上限；分区表已带分区谓词；SQL 为纯 `SELECT`。
- **血缘**：`NeedUpstream`/`NeedDownstream` 已**显式**传值；空结果已排除"默认 false"这一误因；**已先跟用户确认过要「直接上下游」还是「全链路」**，选全链路时已做 BFS 递归并告知深度上限（未拿一次 1 跳结果冒充全量血缘）。
- **质量概况**：4.1 拿到 `WatchId`（或明确判定这张表下没配规则）；4.2 传了 `watchId`；输出中「自算通过率」与「平台质量分不可得」都已如实标注；**输出里未出现「监控对象」「watch」类内部词**。
- 详见 [`references/acceptance-criteria.md`](references/acceptance-criteria.md)。

## 10. Cleanup

- 板块 ①③④ 纯只读，无资源产生。
- 板块 ② 会留下即席查询任务记录（Dataphin 侧历史记录，不占持久化任务位、无需也无法通过 OpenAPI 删除）。预览产生的计算费用已实际发生——这正是执行前必须 HITL 的原因。

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. **Step 1 先跑、只跑一次，且两个开关都开**：它一次性喂饱后面三步（预览入参、血缘 GUID、质量对象类型），避免重复查询；漏传 `IncludeDetailedAttributes` 会让热度与产出任务全变 `null`。
2. **汇报用词先查** [`references/ui-field-mapping.md`](references/ui-field-mapping.md)，不要拿字段英文名直译成中文标签。
3. **按需取板块**：预览花钱、血缘可能巨大；用户没点名要全部时先问要哪几块，**查血缘还要多问一句要直接上下游还是全链路**。
4. 大整数 ID（19 位 snowflake）一律字符串传参（参 [`../../../../.qoder/rules/repo-conventions.md`](../../../../.qoder/rules/repo-conventions.md)）。
5. 只查关心的属性时传 `AttributeCodeList`，减少响应体积；大批量按 50 一片分片。
6. **回答质量相关问题前先读** [`references/quality-profile-feasibility.md`](references/quality-profile-feasibility.md)，不要把自算通过率说成平台质量分。

### ✗ 平台限制

#### ✗ 近 30 天访问次数（visitCnt30d）无 OpenAPI
- 限制描述：界面/内部接口有 `visitCnt30d`（近 30 天访问次数），但 `GetCatalogAssetDetails` 不返回。浏览量（`ReadCount`）与收藏数（`CollectionCount`）则正常返回（需 `IncludeDetailedAttributes: true`）。
- 替代方案：需近 30 天访问次数只能到界面看，不要自编。

#### ✗ 血缘接口单次只给 1 跳，无深度入参
- 限制描述：`GetTableLineages` / `GetTableColumnLineages` 的 `FilterQuery` 只有 `NodeEnv` / `NodeIdList` / `NeedUpstream` / `NeedDownstream` / `NeedNotExistObject` 五个项，**没有 depth / level / hop 类参数**；返回的也只是直接（1 跳）上下游。实测 5 张表，返回边中「与目标 GUID 无关的边」恒为 0 条，而邻居表单独再查还会出新边。
- 替代方案：全链路由本 skill 客户端 BFS 递归（设 `MAX_HOP`、去重、环检测），且**范围必须先让用户选**（见 §8 Step 3.0）。

#### ✗ 表级质量分无 OpenAPI（字段级也拿不到）
- 限制描述：对一张已配 8 条规则的真实表跑完全链路后，对 `ListQualityWatches` / `ListQualityRules` / `ListQualityRuleTasks` / `GetQualityWatchTask` 返回体做 `score|weight|grade` 递归扫描，**命中 0 个**；计分方式与质量分权重连配置都不支持 OpenAPI（见 `configure-quality-rule`）；`Columns[].QualityScore` 字段存在但**实测恒不回填**。
- 替代方案：① 用 `GetQualityWatchTask.RuleCountInfo` 的 `SuccessRuleCount / FinishedRuleCount` 自算通过率（须标注口径）；② 要平台口径的表级质量分只能到界面看。

#### ✗ API 错误码无 OpenAPI
- 限制描述：`GetDataServiceApiDocument` 返回的 37 个字段里**没有任何错误码字段**（无 `ErrorCode` / `ErrorCodeList` / `ErrorInfo`），CLI 也无单独的错误码查询命令。
- 替代方案：如实告知需到界面 API 文档页查看；**不得用 HTTP 状态码或自编错误码充数**。

#### ✗ 仪表板图表信息只到“名称”粒度
- 限制描述：图表列表复用 `Columns[]`，但**只有 `Guid` 与 `Name`**（单独查 COMPONENT GUID 可多拿 `CreateTime`/`ModifyTime`）；图表类型、绑定数据集、字段、查询条件全部没有。**三条路已穷尽**：`ListCatalogAssets assetType=COMPONENT` 返 `TotalCount=0`（不可枚举）、图表与仪表板血缘均返空数组（BI 侧无血缘）、自定义属性 `AttributeList` 为空。
- 替代方案：需要图表构成只能到 BI 工具（`AssetFrom` 会告诉你是哪个 BI）。

#### ✗ 业务指标无数据预览与血缘
- 限制描述：业务指标是纯业务定义、不落物理表，因此无预览、无血缘、无质量监控。
- 替代方案：走 `AssociatedTechMetrics[]` 跳到对应技术指标，再按 Step 5 看其所属字段的预览/血缘/质量。

#### ✗ 字段血缘与质量规则都无法按列过滤
- 限制描述：`GetTableColumnLineages` 没有按列过滤的入参；`ListQualityRules` 也只能按 `watchId` 拉全表规则。
- 替代方案：全表拉回后客户端过滤（血缘比 `Input/OutputColumnName`，规则比 `ValidateObject.Name`）；大宽表要注意返回体体量。

#### ✗ 批量条数上限
- 限制描述：`GetAssetAttributes` 单次 `GuidList` ≤ 50，超限整体拒绝。
- 替代方案：客户端分片，每片 ≤ 50 个 GUID 循环查询。

#### ✗ 质量规则列表无法跨表/跨对象查
- 限制描述：`ListQualityRules` 的 `watchId` 事实必填，无法"一把捞出全租户规则"。
- 替代方案：先 `ListQualityWatches` 拿 watch 列表，再逐个 `ListQualityRules`。

### 常见坑

#### [测试反馈] 拿字段英文名直译成中文标签，与界面对不上
- 现象：把 `SimpleNodeInfos` 报成「调度节点」（界面叫「**产出任务**」）、把 `ReadCount`/`CollectionCount` 报成「阅读数、收藏次数」（界面是「**浏览量**」「**收藏数**」）。
- 结论：字段名一律取 [`references/ui-field-mapping.md`](references/ui-field-mapping.md) 的界面原文，**不允许自己给字段起中文名**。

#### [测试反馈] 漏传 `IncludeDetailedAttributes` → 热度与产出任务全 `null`，再当 0 报出去
- 现象：只传 `IncludeColumns: true`，`ReadCount` / `CollectionCount` / `SimpleNodeInfos` / `AssetTags` / `MaintainUser*` 全为 `null`；把 `null` 当 0 汇报，用户一对界面就发现对不上。
- 结论：这个开关**不只管 `Instruction` / `CustomAttributes`**。Step 1 两个开关一律都传 `true`；拿到 `null` 时先想“是不是没开开关”，而不是直接报 0。

#### [测试反馈] 把字段级关联标准/数据分类/数据分级当死字段一起砍掉
- 现象：因为知道 `Columns[].QualityScore` 是死字段，就连 `Standards` / `ClassifyName` / `LevelShortName` 也一并不输出；或抽查头几列是 `null` 就下结论“这些信息接口不返回”。
- 结论：实测这三项**大量有值**（`mfg_fin_ods.d_order_sale` 125 列中 99 列有分类分级、3 列有关联标准），**必须逐列输出**；只有 `QualityScore` 是恒空的。

#### [测试反馈] 拿一次血缘调用的结果当「全部血缘」汇报
- 现象：调一次 `get-table-lineages` 就说「这张表的上下游就这么多」；实际邻居表往上/往下还有一大片未展开。
- 结论：接口只给 1 跳。要么明确说「**直接上下游**」，要么做 BFS 递归拿全链路——**先问用户要哪个**，不要自己替用户选完又措辞模糊。

#### [测试反馈] 质量输出透出「监控对象」这类内部词
- 现象：输出里写「监控对象：已配质量监控（watchId=3925946）」——界面上根本没有「监控对象」这个概念，用户看不懂。
- 结论：改成「**这张表下共配置了 8 条质量规则（生效 3 条）**」；`watch` / `watchId` / `watchTaskId` / `监控任务` 一律不出现在给用户的输出里。

#### [Agent 自主发现] GUID 不存在不会报错
- 现象：查询不存在的 GUID 时 `Success=true`，只是结果里没有该资产。
- 结论：不能凭 `Success` 判断 GUID 有效性，须核对 `AssetAttributeList` 是否真的返回了目标 GUID。

#### [Agent 自主发现] 空描述有两种空值形态
- 现象：`TopicDescription` 空时为 `null`，`DirectoryDescription` 空时为 `""`。
- 结论：展示层需同时兼容 `null` 与空串，避免误判"字段缺失"。

#### [Agent 自主发现] 表血缘不显式传 true 会"看起来没血缘"
- 现象：`get-table-lineages` 不传 `--need-upstream` / `--need-downstream` 时返回空，误判为该表无血缘；而 `get-table-column-lineages` 同样不传却有结果。
- 结论：两个接口默认值相反（表血缘 false/false，字段血缘 true/true）。**两个都显式传值**，空结果先排除这一误因再下结论。

#### [Agent 自主发现] 质量接口的参数位置不统一，放错位置会静默返回空
- 现象：把 `WatchType`/`WatchObjectId` 当 body 参数传 `GetQualityWatchByObjectId`，报 `Missing required argument: WatchType`；而 `ListQuery` 系列放 body 才对。
- 结论：`GetQualityWatchByObjectId` 是 query 位参数、`List*` 是 body 包裹参数（对照表见 §8 末尾）。位置错时报 `Missing required argument`，好排查；真正难排的是读错负载键导致的静默空（见下一条）。

#### [Agent 自主发现] 旧裸 Action 名报 Unknown API
- 现象：直调 `PagedQueryQualityWatches` 报 `Unknown API: PopSDKPagedQueryQualityWatches`；`PagedQueryQualityRules` 同理。
- 结论：v1.0 SDK 文档里的 `PagedQuery*` 是旧裸名，真实 Action = **CLI kebab 命令的 PascalCase**（`list-quality-rules` → `ListQualityRules`）。拿不准先 `aliyun dataphin-public <command> --cli-dry-run` 导出真实 Action 名。

#### [Agent 自主发现] 用试跑结果冒充质量现状
- 现象：`ListQualityRules` 返回的 `TestRunRuleValidateResult` 看着就是"校验结果"，直接拿来报质量情况。
- 结论：那是**配规则时人工试跑**的一次性结果，与生产调度无关，可能从未跑过或早已过期。表述当前质量状况必须用 `GetQualityWatchTask.RuleCountInfo` 或 `ListQualityRuleTasks` 的 `ValidateSuccess` + `BizDate`。

#### [Agent 自主发现] 只读 `Data` 键 → 把自己的解析 bug 误判成“未授权”
- 现象：质量模块（及 `ListTables`）的负载在 `PageResult` / `QualityWatchInfo` / `WatchTaskInfo` 等具名键下，**不在 `Data` 下**。探针只取 `body["Data"]` 时，所有质量接口看起来都是 `Code=OK` + `Data=null`。实测中据此一路推理出“该 AK 未授权质量模块”、还编了一套用 `ListQualityTemplates` 做阳性对照的诊断法——**全是错的**；改成打印完整响应体后看到 `PageResult.TotalCount=96`，数据一直都在。
- 结论：**拿到空结果的第一反应是 `print(list(body.keys()))`**，先确认读的是正确负载键，再谈“没数据 / 没配置 / 没授权”。包裹键跨模块不统一，不能拿一个接口的经验往全局套。

#### [Agent 自主发现] 字段名直接抬 SDK v1.0 文档
- 现象：按文档取 `watchId` / `watchType` / `table` / `ruleStrength` / `validateResult`，全部为 `None`，看着像“字段没返回”。
- 结论：实际返回是 `Id` / `Type` / `TableInfo` / `Strength` / `ValidateSuccess`。**以实测返回为准**，拿不准就打印 `sorted(obj.keys())`，不要凭文档猜字段名。

#### [Agent 自主发现] 同名表取错 watch
- 现象：`list-quality-watches --keyword dim_employee` 命中 4 个 watch（DEV/PROD × 本表/`_org` 后缀表）；取第一条拿到的是 DEV 且 `RuleCount=0` 那个，结论就变成了“这张表没规则”。
- 结论：**必须用 `TableInfo.Id` 精确匹配目标资产 GUID**（它就等于 GUID）并核对 `TableInfo.Env`；能直接用 `GetQualityWatchByObjectId` 就不要绕 keyword 搜。

#### [Agent 自主发现] 把 `Status=SUCCESS` 当成校验通过
- 现象：规则任务 `Status=SUCCESS`，直接报“质量正常”；而实测同一条记录 `ValidateSuccess=false`（强规则异常）。
- 结论：`Status` 是“任务跑完了没”，`ValidateSuccess` 才是“数据有没问题”，两者必须分开读。

#### [Agent 自主发现] 使用说明当纯文本直展
- 现象：`Instruction` 看着是字符串，直接展出来却是 `["root",{},["p",{}…]]` 这种富文本 JSON，满屏转义字符。
- 结论：先 `json.loads` 再递归抽 `data-type: leaf` 的文本；解析失败就降级提示到界面看，不抛原串。

#### 预览分区表不带分区谓词
- 现象：MaxCompute 报全表扫描禁止；大表 Hive/DB 查询长时间挂住。
- 结论：`IsPartitionTable=true` 时必须按 `PartitionKey` 钉一个分区值；分区值先用 `SHOW PARTITIONS` 取真实值，别猜。

#### 预览表名未用全限定名
- 现象：写裸表名查出 0 行但**任务状态仍为成功**，误判"表无数据"。
- 结论：一律用 `<project|schema>.<table>`（`AssetFullName` 直接给了）；结果为空先换全限定名重试再下结论。

### Reference Links

- [`references/ui-field-mapping.md`](references/ui-field-mapping.md) — ★ **界面标签 ↔ 字段对照（汇报用词的唯一依据）**；含「浏览量」口径差异与 `IncludeDetailedAttributes` 硬依赖的实测证据
- [`references/asset-type-matrix.md`](references/asset-type-matrix.md) — ★ 5 类资产 × 板块矩阵、各类型非空字段差异、技术指标→字段映射路径
- [`references/quality-profile-feasibility.md`](references/quality-profile-feasibility.md) — ★ 质量分可行性结论与实测证据
- [`references/data-preview-sql.md`](references/data-preview-sql.md) — 各引擎预览 SQL 方言与 OperatorType 映射
- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`references/ram-policies.md`](references/ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
- 复用子 skill：[`execute-ad-hoc-task`](../../dev/execute-ad-hoc-task/SKILL.md)（预览引擎参数）、[`configure-quality-rule`](../configure-quality-rule/SKILL.md)（质量规则配置）、[`manage-asset-attributes`](../manage-asset-attributes/SKILL.md)（属性写入）、[`manage-biz-metric`](../manage-biz-metric/SKILL.md)（业务指标增删改）
