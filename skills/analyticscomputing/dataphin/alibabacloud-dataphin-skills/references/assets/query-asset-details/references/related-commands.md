# 相关命令

> 本 skill 涉及的 Dataphin OpenAPI Action 及其插件模式命令。除数据预览外全部只读。
> V6.3 新增/增强 Action 若插件未收录，用 OpenAPI SDK 兜底（版本 `2023-06-30`）。

## ① 属性详情 / 字段列表 / 使用说明（只读，**全 5 类资产通用**）

| OpenAPI Action | 插件命令 | 用途 |
|---|---|---|
| `GetCatalogAssetDetails` | `aliyun dataphin-public get-catalog-asset-details` | **所有资产类型的统一入口**：属性 + `Columns[]`（表=字段列表，仪表板=图表列表）+ `Instruction` 使用说明 + `Directories[]` 目录层级链 + `AssetType`/`SubType`（定板块范围） |
| `GetAssetAttributes` | `aliyun dataphin-public get-asset-attributes` | 按 GUID **批量**查自定义属性值（单次 ≤ 50） |
| `ListCatalogAssets` | `aliyun dataphin-public list-catalog-assets` | 按名称/关键词找资产 GUID；`assetType` 可取 `TABLE`/`INDEX`/`BIZ_INDEX`/`API`/`PAGE` |

## ② 数据预览（**起任务，耗计算资源**）

| OpenAPI Action | 插件命令 | 用途 |
|---|---|---|
| `ExecuteAdHocTask` | `aliyun dataphin-public execute-ad-hoc-task` | 提交 `SELECT ... LIMIT 50` 预览查询 |
| `GetAdHocTaskResult` | `aliyun dataphin-public get-ad-hoc-task-result` | 取预览结果（`--sub-task-id` 从 0 开始） |
| `GetAdHocTaskLog` | `aliyun dataphin-public get-ad-hoc-task-log` | 仅在结果为空/报错时查状态 |
| `ListDataSourceWithConfig` | `aliyun dataphin-public list-data-source-with-config` | 反查 DataSourceId（详情已给则不必调） |

## ③ 血缘关系（只读）

| OpenAPI Action | 插件命令 | 用途 |
|---|---|---|
| `GetTableLineages` | `aliyun dataphin-public get-table-lineages` | 表级血缘。**`--need-upstream`/`--need-downstream` 默认 false，必须显式传 true** |
| `GetTableColumnLineages` | `aliyun dataphin-public get-table-column-lineages` | 字段级血缘（这两个开关默认 true） |
| `GetTableColumns` | `aliyun dataphin-public get-table-columns` | 按 catalog + 表名查字段（详情已含 `Columns[]` 时不必调） |

## ④ 质量概况（只读）

| OpenAPI Action | 插件命令 | 用途 |
|---|---|---|
| `GetQualityWatchByObjectId` | `aliyun dataphin-public get-quality-watch-by-object-id` | 对象 ID → 监控对象（watchId）。**参数在 query 位** |
| `ListQualityWatches` | `aliyun dataphin-public list-quality-watches` | 按表名关键词反查 watch（`GetQualityWatchByObjectId` 拿不到时的兜底） |
| `ListQualityRules` | `aliyun dataphin-public list-quality-rules` | watchId → 规则清单。**`--watch-id` 事实必填** |
| `ListQualityRuleTasks` | `aliyun dataphin-public list-quality-rule-tasks` | 规则**真实执行**结果（`ValidateResult` / `BizDate`） |
| `ListQualityWatchTasks` | `aliyun dataphin-public list-quality-watch-tasks` | 监控任务列表（按 bizDate 找历史执行批次） |
| `GetQualityRuleTask` / `GetQualityRuleTaskLog` | `... get-quality-rule-task` / `... get-quality-rule-task-log` | 单条规则任务详情/日志（下钻排查异常规则） |

> **旧裸名警告**：`PagedQueryQualityRules` / `PagedQueryQualityWatches` / `PagedQueryQualityRuleTasks` 是 v1.0 SDK 命名，直调报 `Unknown API`。真实 Action = 上表 CLI 命令的 PascalCase。

## ⑤ 业务指标专用（只读）

| OpenAPI Action | 插件命令 | 用途 |
|---|---|---|
| `GetBizMetricByName` | `aliyun dataphin-public get-biz-metric-by-name` | **相关指标**（`RelatedBizMetrics[]`）+ **关联技术指标**（`AssociatedTechMetrics[]`）+ **指标口径**（`MetricDefinition`）+ **使用说明**（`OperateInstructionContent`，纯文本）。**包裹参数 `BizMetricByNameQuery`，`draft` 必填** |

## ⑥ 数据服务 API 专用（只读）

| OpenAPI Action | 插件命令 | 用途 |
|---|---|---|
| `GetDataServiceApiDocument` | `aliyun dataphin-public get-data-service-api-document` | **API 文档**：基本信息 + `RequestParamList[]` + `PublicParamList[]` + `ResponseParamList[]` + `ResultSample` + `Sql`。`Id` 直接用资产详情的 `ApiId`；**无错误码字段** |

## ⑦ 仪表板（只读）

无专用接口。**图表列表就在 `GetCatalogAssetDetails` 的 `Columns[]` 里**（需 `IncludeColumns: true`），只含图表 `Guid` + `Name`；另可用 `BiCatalog`（BI 目录路径）与 `AssetFrom`（BI 工具）。

## 相关子 skill

| 需求 | 去哪 |
|---|---|
| 属性**写入** | `manage-asset-attributes`（`UpdateAssetAttributes`） |
| 质量规则**配置**（建监控对象/建规则/调度告警/试跑） | `configure-quality-rule` |
| 业务指标**增删改** | `manage-biz-metric` |
| 数据服务 API **创建/发布** | `create-and-publish-api` |
| 预览之外的即席查询（建表/改数/复杂 SQL） | `execute-ad-hoc-task` |
