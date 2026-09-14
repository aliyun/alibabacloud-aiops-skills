# 资产类型 × 板块矩阵（5 类资产各查什么、用什么接口）

> 全部为 POC V6.3 实测结论。`GetCatalogAssetDetails` 是**所有资产类型的统一入口**（属性详情板块），其余板块按类型分流。

## 0. 板块矩阵

| 资产类型 | `assetType` | GUID 前缀 | 属性详情 | 其他板块 |
|---|---|---|---|---|
| 表 | `TABLE` | `dp_table.` / `dp_ds_table.` / `odps.` | ✅ | 数据预览 + 表血缘 + 字段血缘 + 质量概况 |
| **技术指标** | `INDEX` | `dp_index.` / `cust_index.` | ✅ | 数据预览 + **所属字段血缘** + **所属字段质量规则** |
| **业务指标** | `BIZ_INDEX` | `biz_index.` | ✅ | **相关指标** + **使用说明** |
| **数据服务 API** | `API` | `dp_api.` | ✅ | **API 文档** |
| **仪表板** | `PAGE` | `qbi_page_` | ✅ | **图表信息** |

> 资产类型识别：优先看 `GetCatalogAssetDetails` 返回的 `AssetType` + `SubType`，不要凭 GUID 前缀猜（前缀有多种变体）。

> **汇报时的中文字段名一律查** [`ui-field-mapping.md`](ui-field-mapping.md)（界面原文），本文只讲「哪个类型用哪个接口、哪些字段有值」。

## 1. 属性详情：各类型的非空字段差异（实测）

`Data` 恒为 58 个键，但按类型只有一部分有值：

| 字段 | TABLE | INDEX | BIZ_INDEX | API | PAGE |
|---|---|---|---|---|---|
| `AssetName` / `AssetFullName` / `AssetType` / `SubType` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `Directories[]` / `CustomAttributes[]` / 上下架时间 / 可见范围 | ✅ | ✅ | ✅ | ✅ | ✅ |
| `Columns[]` | 字段列表 | ✗ null | ✗ null | ✗ null | **图表列表** |
| `Instruction` | 富文本 | 富文本 | 富文本 | 富文本 | 富文本 |
| **`SimpleNodeInfos[]`（界面「产出任务」）** | ✅ 有产出任务时非空 | — | ✗ | ✗ | ✗ |
| **`ReadCount` / `CollectionCount`** | ✅ | ✅ | ✅ | ✅ | ✅ | 
| `PartitionKey` / `IsPartitionTable` / `PrimaryKey` / `TableLifeCycle` | ✅ | ✗ | ✗ | ✗ | ✗ |
| `ProjectName` / `BizUnitName` | ✅ | ✅（dp_index） | ✗ | ✗ | ✗ |
| `DatasourceId` / `DataSourceName` | 数据源表 | ✅（cust_index） | ✗ | ✗ | ✅ |
| `ApiId` / `ApiGroupName` / `ApiCallMode` / `ApiRequestMethod` | ✗ | ✗ | ✗ | **✅** | ✗ |
| `BiCatalog` / `ChartCount` | ✗ | ✗ | ✗ | ✗ | **✅** |
| `SumTableGuid` / `SumTableName` / `Granularity` / `DataCellId` | — | 实测均为 null（勿依赖） | — | — | — |

> **★ `SimpleNodeInfos` / `ReadCount` / `CollectionCount` / `AssetTags` / `MaintainUser*` 只有 `IncludeDetailedAttributes: true` 才回填**（实测：只开 `IncludeColumns` 时全为 `null`）。详见 [`ui-field-mapping.md`](ui-field-mapping.md) §5。

### 1.1 `Columns[]` 各键的真实可用性（实测 60 张表）

| 键 | 界面列名 | 可用性 |
|---|---|---|
| `Name` / `DisplayName` / `Description` / `DataType` | 字段名称 / 描述备注 / 数据类型 | ✅ |
| `BizType` / `AssociatedEntity` | 业务类型/关联实体 | ✅ `BizType` 实测取值 `DIMENSION` / `INDEX` / `STAT_PERIOD` |
| **`Standards[]`** | **关联标准** | ✅ **有值**，结构 `[{"Id":266881,"Name":"订单编码","Code":"ORDER_CODE"}]`（如 `d_order_sale` 125 列中 3 列有） |
| **`ClassifyName`** | **数据分类** | ✅ **有值**，路径串 `/交易信息/`、`/研发域/项目管理/知识管理/失效分析/`；挂根上为 `/` |
| **`LevelShortName`** | **数据分级** | ✅ **有值**，`L1`~`L4`（`d_order_sale` 125 列中 99 列有） |
| `QualityScore` | 质量分 | ❌ **恒 `null`**，60 张表非空列数 0 → 输出 `-` 并注明无 OpenAPI |

> 四项中**只有 `QualityScore` 是死字段**；其余三项必须逐列输出，不要因为抽查到的列为空就整列省略。
> 不同表差异很大：`dim_lk_cus` 6 列全无分类分级，而 `mfg_fin_ods.t_org` 22 列中 19 列有。

`SubType` 实测取值：
- TABLE：`DIM_NORMAL`（维度逻辑表）/ `SUM_BIZ_UNIT`（板块汇总表）/ `DATASOURCE_TABLE`（全域表）
- INDEX：`INDEX`（标准技术指标，`dp_index.`）/ `CUSTOM_INDEX`（自定义指标，`cust_index.`）
- BIZ_INDEX：`BIZ_INDEX`；API：`DP_API`；PAGE：`QBI_PAGE`

## 2. 技术指标（INDEX）

### 2.1 ★ 核心：定位「指标属于所属表的哪个字段」

**`AssetFullName` = `<所属表名>.<字段名>`**（实测，两类指标都成立）。拆开后拼出表 GUID：

| 指标类型 | AssetFullName 示例 | 表 GUID 拼法 | 实测验证 |
|---|---|---|---|
| `dp_index.`（标准指标） | `dws_guoshou_customer2.order_cnt_cm` | `dp_table.<tenant>.<BizUnitName 小写>.<表名>` | ✅ 命中 `LD_Dummy.dws_guoshou_customer2`（SUM_BIZ_UNIT） |
| `cust_index.`（自定义指标） | `auto_sr_sql02.id` | `dp_ds_table.<tenant>.<DatasourceId>.<schema>.<表名>`（schema 从 GUID 中段取） | GUID 本身已含 datasourceId 与 schema |

拼出表 GUID 后**必须回读校验**：`GetCatalogAssetDetails(表GUID, includeColumns=true)`，确认

1. 返回非空（GUID 拼对了）；
2. `Columns[]` 里存在 `Name == <字段名>` 的那一列（指标确实是该表的字段）。

字段 GUID = `<表GUID>.<字段名>`（实测：`dp_table.300023201.ld_dummy.dws_guoshou_customer2.order_cnt_cm`）。

> **不要用 `SumTableGuid`**——实测该字段在技术指标上恒为 `null`，靠不住。

### 2.2 字段血缘（只看指标对应的那一列）

调 `GetTableColumnLineages(TableGuid=<所属表GUID>)` 拿全表字段血缘，再**客户端过滤**
`InputColumnName == <字段名> or OutputColumnName == <字段名>`。

- 接口**没有按列过滤的入参**，只能全表拉回来自己筛。
- 实测：`dws_guoshou_customer2` 全表 8 条字段血缘 → 过滤到 `order_cnt_cm` 命中 **2 条**（两个上游字段 `guoshou_order_liucheng_id`、`guoshou_order_pay_time` 经同一任务 `n_7138102124034457600` 汇总成该指标）。
- 一个指标字段有多条入向血缘是正常的（多字段汇总），要全列出来，不要只取第一条。

### 2.3 该字段上的质量规则

```
GetQualityWatchByObjectId(WatchType=TABLE, WatchObjectId=<所属表GUID>) → QualityWatchInfo.Id
  → ListQualityRules(WatchId) → PageResult.QualityRuleList[]
    → 过滤 ValidateObject.Type == "COLUMN" && ValidateObject.Name == <字段名>
```

**`ValidateObject` 结构（实测）**：`{"Type": "COLUMN", "Name": "<字段名>"}` —— 可精确匹配。

每条命中规则汇报：`Id` / `Name` / `Strength`（STRONG/WEAK）/ `Status`（ENABLE/DISABLE）/ `TemplateId` + `TemplateName`（规则类型）/ `ValidateConditionList`（阈值）。

执行结果再按 §Step 4.3 走 `GetQualityWatchTask` + `ListQualityRuleTasks`，并按 `ValidateObjectName == <字段名>` 过滤。

> **所属表没配 watch 时**（实测 `dws_guoshou_customer2` 就没配，`QualityWatchInfo` 为空）→ 直接输出「该指标所属表未配置质量监控」，不要继续往下调。

### 2.4 数据预览

同表的预览逻辑，但 SQL 只取该指标字段（外加分区键与业务主键更可读）：
`SELECT <字段名> FROM <表全名> WHERE <分区键>='<分区值>' LIMIT 50`。分区表仍必须钉分区。

## 3. 业务指标（BIZ_INDEX）

### 3.1 专用详情接口

```bash
aliyun dataphin-public get-biz-metric-by-name \
  --tenant-id "$OP_TENANT_ID" --name "<指标英文名>" --draft false --user-agent "$UA"
```

**契约坑（实测连踩两次）**：
1. 业务参数必须包在 **`BizMetricByNameQuery`** 里（顶层平铺报 `Missing required argument: BizMetricByNameQuery`）；
2. **`draft` 必填**（只传 name 报 `DPN.Commons.InvalidParam: draft cannot be null`）。`draft=false` 取已发布态，`true` 取草稿态。

负载键是 `Data`。实测键集：

| 字段 | 说明 |
|---|---|
| `Guid` / `Name` / `DisplayName` / `Description` | 基本信息 |
| **`MetricDefinition`** | **指标口径/定义公式**（如 `客户订单金额 = SUM(...)`）——业务指标最核心的信息 |
| **`RelatedBizMetrics[]`** | **相关指标**：`Guid` / `Name` / `DisplayName` / `Description` / **`RelationType`**（实测取值 `POSITIVE`）/ `SubType` / `ListStatus`（`ON_SHELVE` / `ON_SHELVE_MODIFY`） |
| **`AssociatedTechMetrics[]`** | **关联的技术指标**——业务指标到物理落地的桥梁，汇报时应一并给出 |
| `Catalogs[]` | 目录挂载，含 `TopicName` / `CatalogName` / **`ParentPath`**（如 `/业财一体客户/客户A/`），比 `GetCatalogAssetDetails.Directories` 的层级信息更直观 |
| **`OperateInstructionContent`** + `OperateInstructionEnabled` | **使用说明（纯文本）** |
| `MetricRelationDiagramSwitchOpen` / `MetricRelationDiagramExpression` | 指标关系图开关与表达式 |
| `Labels` / `BizOwnerName` / `ViewScope` / `CustomAttribute` | 标签 / 负责人 / 可见范围 / 自定义属性 |

### 3.2 ★ 使用说明有两个来源，取值形态不同

| 来源 | 字段 | 形态 |
|---|---|---|
| `GetBizMetricByName` | `OperateInstructionContent` | **纯文本**，可直接展示 |
| `GetCatalogAssetDetails` | `Instruction` | **富文本 JSON**，需解析 leaf |

**业务指标优先用 `OperateInstructionContent`**（免解析）；两者应一致，不一致时以专用接口为准。

### 3.3 板块边界

业务指标**没有**数据预览与血缘（它是纯业务定义、不落物理表）。要看落地情况走 `AssociatedTechMetrics[]` 跳到技术指标。

## 4. 数据服务 API

### 4.1 API 文档

```bash
# Id 直接用 GetCatalogAssetDetails 返回的 ApiId
aliyun dataphin-public get-data-service-api-document \
  --tenant-id "$OP_TENANT_ID" --data-service-api-document-id <ApiId> --user-agent "$UA"
```

负载键 `Data`，实测 37 个字段，按用户关心的四块归类：

| 分块 | 字段 |
|---|---|
| **基本信息** | `ApiId` / `Name` / `Description` / `GroupId` + `GroupName`（分组）/ `ProjectId` + `ProjectName` / `Version` / `Env` / `Mode` / `Protocol` / `RequestMethod` / `ReturnType` / `CreateType` / `ScriptType`（如 `NORMAL_SQL`）/ `IsLogicalTable` / `IsPagedQuery` / `IsSpecialSql` / `UpdateRate` |
| **请求参数** | **`RequestParamList[]`** + **`PublicParamList[]`**（公共参数，实测 3 个）。每项含 `Name` / `MappingColumn` / `Type` / `Sample` / `IsRequired` / `IsOptional` / `Operator` / `DefaultValue` / `DateFormat` / `Location` / `Rule` |
| **返回参数** | **`ResponseParamList[]`**（实测 41 个），字段同上；外加 **`ResultSample`**（返回示例 JSON 串） |
| 运行配置 / 数据源 | `ApiTimeout` / `Timeout` / `ReturnLimit` / `OpenCache` / `CacheTime` / `ResourceGroupId` + `Name` / `DirectDatasourceId` + `Name` / `TableName` / `BizUnitName` / `AppName` / `ApiRegisterInfo` / **`Sql`**（API 背后的 SQL 全文） |

### 4.2 ✗ 错误码拿不到

**实测 `Data` 的 37 个键里没有任何错误码字段**（无 `ErrorCode` / `ErrorCodeList` / `ErrorInfo`），CLI 也没有单独的错误码查询命令。

- 汇报时必须如实说明「错误码 OpenAPI 未提供，需到界面 API 文档页查看」。
- **不要用通用的 HTTP 状态码或自己编一套错误码充数。**

### 4.3 `Sql` 字段要谨慎输出

`Sql` 是 API 背后的完整查询语句，可能含库表名与业务逻辑。默认只汇总（涉及哪张表、有几个参数占位符），**用户明确要求时才贴全文**。

## 5. 仪表板（PAGE）

### 5.1 ★ 图表信息就在 `Columns[]` 里

实测 `ChartCount = 10` 且 `Columns` 返回 10 项 —— **仪表板的图表列表复用了 `Columns` 这个字段**：

```jsonc
{
  "Guid": "qbi_component_<tenant>_<dsId>_<pageId>_<componentUuid>",
  "Name": "指标趋势图",       // ← 图表名称，唯一有效信息
  "DisplayName": "", "Description": "",
  "DataType": null, "BizType": null, "AssociatedEntity": null,
  "Standards": null, "QualityScore": null,
  "ClassifyName": null, "LevelShortName": null   // 这些对图表无意义，恒为 null/空
}
```

- 必须传 `IncludeColumns: true` 才返回。
- **只有图表 GUID 与名称**（实测名称形如 `明细表`、`仪表盘-ent_bizenddate_918237`、`指标趋势图`）；**没有图表类型、绑定数据集、字段、查询条件**等更多信息。
- 校验一致性：`len(Columns) == ChartCount`，不等说明有图表未被采集。

### 5.1.1 单图表可多拿一点：对 COMPONENT GUID 单独查详情

图表 GUID **本身就是资产 GUID**（`AssetType=COMPONENT`、`SubType=QBI_COMPONENT`），可单独调 `GetCatalogAssetDetails`，但**只比 `Columns[]` 多三个字段**（实测非空字段共 9 个）：

| 多拿到的 | 价值 |
|---|---|
| **`CreateTime` / `ModifyTime`** | 逐图表的创建/修改时间——可看出哪些图表最近改过（仪表板的 `Columns[]` 不带时间） |
| `DatasourceId` / `AssetType` / `SubType` | BI 数据源与类型标识 |

> 仅当用户关心“哪些图表最近变更”时才逐个调（N 个图表 = N 次调用）；否则直接用仪表板的 `Columns[]` 就够。

### 5.1.2 ✗ 已穷尽的三条路（不要重复探）

图表的**类型 / 绑定数据集 / 字段 / 查询条件 / 图表配置** 经以下三条路均确认**拿不到**（POC 实测）：

| 尝试 | 结果 |
|---|---|
| `ListCatalogAssets` 枚举 `assetType=COMPONENT` | `TotalCount=0`（`QBI_COMPONENT` / `CHART` 非法枚举值，返 null）——**图表不可枚举** |
| `GetTableLineages` 查图表/仪表板血缘（想知道消费了哪张表） | 两者均 `Code=OK` + `TableLineageList=[]`——**BI 侧资产无血缘数据** |
| `GetAssetAttributes` 查图表自定义属性 | `AttributeList: []` 空 |

**结论**：图表信息就是「GUID + 名称（+ 单查时的创建/修改时间）」，到此为止。更细的图表构成只能到 BI 工具（`AssetFrom` 告诉你是哪个 BI）。

### 5.2 其他可用信息

- **`BiCatalog`**：BI 侧的目录路径（实测 `dataphin测试空间/dpv5test/dp5报表上架`）
- `AssetFrom`：BI 工具来源（实测 `Quick BI`）
- `DatasourceId`：BI 数据源 ID

### 5.3 板块边界

仪表板**没有**数据预览、血缘、质量概况（它是消费端资产）。图表的字段级构成需到 BI 工具查看。

## 6. 各类型的板块边界速查（避免白调接口）

| 板块 | TABLE | INDEX | BIZ_INDEX | API | PAGE |
|---|---|---|---|---|---|
| 属性详情 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 数据预览 | ✅ | ✅（单列） | ✗ 无物理数据 | ✗ | ✗ |
| 血缘 | ✅ 表+字段 | ✅ 仅所属字段 | ✗ | ✗ | ✗ |
| 质量概况 | ✅ | ✅ 仅所属字段规则 | ✗ | ✗ | ✗ |
| 专用板块 | — | — | 相关指标 / 使用说明 | API 文档 | 图表信息 |

> 对不支持的板块，**直接说明「该资产类型无此板块」，不要去硬调接口拿空结果再解释**。
