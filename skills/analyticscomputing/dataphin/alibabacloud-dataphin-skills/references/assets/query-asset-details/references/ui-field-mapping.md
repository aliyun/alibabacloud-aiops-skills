# 界面标签 ↔ OpenAPI 字段对照（汇报用词的唯一依据）

> **本文是「叫什么名字」的唯一依据。** 汇报资产详情时的每一个字段名，必须用本文左列的界面原文，
> **不允许**按字段英文名直译（`SimpleNodeInfos` → “调度节点”、`ReadCount` → “阅读数” 都是错的）。
> 全部标签取自 POC V6.3 资产目录详情页实截（`/market/catalog/detail/table/<guid>`）。

## 1. 资产详情页整体结构（界面原文）

页签顺序：**属性信息 · 字段信息 · 数据预览 · 数据探查 · 使用说明 · 血缘关系 · 质量概况 · 元数据变更**

右侧栏两块：**用数统计**（浏览量 / 收藏数）、**基本信息**（初次上架时间 / 最近上架时间 / 发布人 / 归属目录）。

> 汇报板块名请对齐这套页签名（如说「血缘关系」而不是「血缘图」，说「质量概况」而不是「质量报告」）。

## 2. 表级字段对照

| 界面标签（原文） | OpenAPI 字段 | 备注 |
|---|---|---|
| **产出任务** | **`SimpleNodeInfos[]`** | ★ **不是「调度节点」**。资产清单里是独立 Tab「产出任务」，数据集详情里是右侧栏字段「产出任务」。每项含 `NodeId` / `NodeName` / `SubBizType` / `Owners[]` / `Project` / `BizUnit` / `NodeScheduleType` / `Env` |
| **浏览量** | **`ReadCount`** | 界面 tooltip：「在资产目录中被浏览的资产详情的次数」。**需 `IncludeDetailedAttributes: true` 才回填**（见 §5） |
| **收藏数** | **`CollectionCount`** | 界面 tooltip：「包含从元数据清单的收藏数和从资产目录入口收藏的收藏数」。**同样需 `IncludeDetailedAttributes: true`** |
| 初次上架时间 / 最近上架时间 | `FirstOnShelveTime` / `LastOnShelveTime` | |
| 发布人 | `LastOnShelveUser`（`FirstOnShelveUser` 为初次） | |
| 归属目录 | `Directories[].DirectoryChain[]` | 界面显示为 `全渠道数...../test1` 这样的路径 |
| 资产来源 | `AssetFrom` | |
| 所属数据板块 / 所属项目 | `BizUnitName` / `ProjectName` | |
| 平台类型 | `DataSourceName` 所属引擎（`dbType` 语义） | |
| 子类型 | `SubType` | 界面显示中文（如「物理表」= `PHYSICAL_TABLE`） |
| 使用说明 | `Instruction` | 富文本 JSON，须解析 leaf |

## 3. 字段信息（字段列表）表头对照

界面表头从左到右原文：**序号 · 字段名称 · 数据类型 · 描述/备注 · 业务类型/关联实体 · 关联标准 · 样例数据 · 质量分 · 数据分类 · 数据分级**

| 界面列名（原文） | `Columns[]` 字段 | 实测可用性 |
|---|---|---|
| 字段名称 | `Name`（+ `DisplayName` 中文名） | ✅ |
| 数据类型 | `DataType` | ✅ |
| 描述/备注 | `Description` | ✅ |
| 业务类型/关联实体 | `BizType` / `AssociatedEntity` | ✅ `BizType` 取值实测有 `DIMENSION` / `INDEX` / `STAT_PERIOD`；`AssociatedEntity` 为维度对象 |
| **关联标准** | **`Standards[]`** | ✅ **有值，必须输出**。结构 `[{"Id":266881,"Name":"订单编码","Code":"ORDER_CODE"}]`，可多条 |
| 样例数据 | — | ✗ 本接口不返回，需数据预览（Step 2） |
| **质量分** | `QualityScore` | ❌ **实测恒为 `null`**（见 §5），输出 `-` 并注明无 OpenAPI |
| **数据分类** | **`ClassifyName`** | ✅ **有值，必须输出**。路径串，如 `/交易信息/`、`/研发域/项目管理/知识管理/失效分析/`；挂在根上时为 `/` |
| **数据分级** | **`LevelShortName`** | ✅ **有值，必须输出**。取值 `L1`~`L4` |

> 这四项（关联标准 / 质量分 / 数据分类 / 数据分级）**都必须 `IncludeColumns: true`**，且必须**每列都列出来**——
> 某一列为空是这一列没打标，不是接口不返回。**不要因为抽查的头几列是 null 就整列不输出。**

## 4. 浏览量 = `ReadCount`（口径以文档为准；注意字段列表里同名字段无关）

- **浏览量** → `GetCatalogAssetDetails.ReadCount`；**收藏数** → `CollectionCount`。两者都需 `IncludeDetailedAttributes: true`（见 §5）。
- 另有一个 `visitCnt30d`（近 30 天访问次数）内部接口有、但 `GetCatalogAssetDetails` 不返回，不要自编。
- **不要把 `Columns[]` 里的同名字段当浏览量**：字段对象没有 `ReadCount`；浏览量/收藏数是**表级**字段，取 `Data.ReadCount` / `Data.CollectionCount`。

## 5. ★ 这批字段只有 `IncludeDetailedAttributes: true` 才回填（否则全 `null`）

实测同一 GUID、四组入参组合：

| `GetCatalogAssetDetailsQuery` | `ReadCount` | `CollectionCount` | `SimpleNodeInfos` |
|---|---|---|---|
| `{}` | `null` | `null` | `null` |
| `{"includeColumns": true}` | `null` | `null` | `null` |
| `{"includeDetailedAttributes": true}` | **136** | **0** | **2 项** |
| `{"includeColumns": true, "includeDetailedAttributes": true}` | **136** | **0** | **2 项** |

即：**`IncludeDetailedAttributes` 不只管 `Instruction` / `CustomAttributes`**，还管
`ReadCount` / `CollectionCount` / `SimpleNodeInfos` / `AssetTags` / `MaintainUserIds` / `MaintainUserGroups` /
`ShelveViewScope*` / `ProfilingReportViewScope*` / `AssetDetailUrl`。

> **Step 1 一律两个开关都开**（`IncludeColumns: true` + `IncludeDetailedAttributes: true`）。
> 只开 `IncludeColumns` 会拿到一片 `null`，再把 `null` 当 0 汇报出去 —— 这正是「热度数字对不上界面」被报缺陷的直接原因。

`QualityScore` 是唯一**两个开关都开也不回填**的字段：60 张表逐张扫描，**非空列数 0**，与 §3 结论一致。

## 6. 质量概况板块的措辞（不要透出内部对象名）

界面页签叫「**质量概况**」，页面上**没有「监控对象」这个词** —— 它是 OpenAPI 侧的实现概念（`QualityWatch`）。

| 禁止说 | 改成 |
|---|---|
| 「监控对象」/「watch」/「watchId」 | 直接说「这张表」，例：`这张表下共配置了 8 条质量规则（生效 3 条）` |
| 「该资产未配置监控对象」 | `这张表下还没有配置质量规则` |
| 「监控任务」 | 「最近一次质量校验」 |

`watchId` / `watchTaskId` 只作为内部串联用，**不出现在给用户的输出里**（用户要排查时再按需给）。
