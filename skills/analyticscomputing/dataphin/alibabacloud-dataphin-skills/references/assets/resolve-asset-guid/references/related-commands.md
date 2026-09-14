# 相关命令索引（resolve-asset-guid）

> 全部只读。独立部署环境下每条命令追加 `--profile dataphin-standalone --skip-secure-verify --op-tenant-id <OpTenantId>`。

## ① 段值解析（拼接路径用）

| OpenAPI Action | 插件命令 | 用途 | 关键参数 |
|---|---|---|---|
| `ListBizUnits` | `aliyun dataphin-public list-biz-units` | 取数据板块名（`dp_table.` 第三段，拼前转小写） | `--tenant-id` |
| `ListProjects` | `aliyun dataphin-public list-projects` | 取项目名（`odps.` 第三段） | `--mode`（事实必填，`BASIC` / `DEV_PROD` 各查一次）`--env` `--page-no` `--page-size` |
| `ListDataSourceWithConfig` | `aliyun dataphin-public list-data-source-with-config` | 取 `DataSourceId`（`dp_ds_table.` 第三段） | `--data-source-name` `--page`（必传）`--type-list` |
| `GetTableColumns` | `aliyun dataphin-public get-table-columns` | 取字段名原样大小写（字段 GUID 末段） | `--catalog`（必传）`--table-name`（必传） |

## ② 反查取官方 GUID（查询路径 / 校验失败兜底）

| OpenAPI Action | 插件命令 | 覆盖范围 | 关键参数 |
|---|---|---|---|
| `ListTables` | `aliyun dataphin-public list-tables` | **主路径：反查真实 `Guid`**（资产清单，含未上架表） | `--catalog`（**必传**，项目名或数据板块名）`--keyword` `--page-no` `--page-size`；扁平参数，无 `--list-query` |
| `ListTables`（内部网关） | Action `ListTables` + `TableQuery` 包裹 | 同上，但**可仅用 `keyword` 全租户搜**（不需 catalog），反查阶段优先用 | `{"keyword":"<表名>","env":"PROD\|DEV","paginationCriteria":{"page":1,"pageSize":100}}`；**必翻页拉全**（实测单关键词可达 143 条） |
| `ListCatalogAssets` | `aliyun dataphin-public list-catalog-assets` | **资产目录已上架**资产（TABLE / INDEX / BIZ_INDEX / API / PAGE） | `--asset-type` `--query-mode`（`EXACT_MATCH` / `ASSET_SEARCH`）`--asset-name` `--keyword` `--page-num` `--page-size` |
| `GetBizMetricByName` | `aliyun dataphin-public get-biz-metric-by-name` | 业务指标 GUID 直取（`Data.Guid`） | `--biz-metric-name`（必传）`--draft`（**必填**：`false` 已发布 / `true` 草稿） |

## ③ 回读校验

| OpenAPI Action | 插件命令 | 用途 | 关键参数 |
|---|---|---|---|
| `GetCatalogAssetDetails` | `aliyun dataphin-public get-catalog-asset-details` | 校验 GUID 是否命中、类型与归属是否一致；`IncludeColumns` 同时用于取仪表板图表 GUID | `--OpTenantId` `--GetCatalogAssetDetailsQuery '{"Guid":"…","IncludeColumns":true}'`（需 6.1+） |
| `GetAssetAttributes` | （SDK 通道，Action `GetAssetAttributes`，6.3+） | 可选的下游可用性验证（单次 `GuidList` ≤ 50） | `GuidList` |

## ④ 下游 skill 对该 GUID 的参数名

| 下游 skill | 参数 |
|---|---|
| `manage-asset-attributes` | `AssetAttributeUpdateList[].Guid` |
| `query-asset-details` | `GetCatalogAssetDetailsQuery.Guid` / `GuidList` / `--table-guid` |
| `configure-quality-rule` | `WatchObjectId`（`WatchType=TABLE` 时即资产 GUID） |
| `manage-standard-mapping` | 字段 GUID 列表 |
| `manage-row-level-permission` | `get-row-permission-by-table-guids` 的表 GUID |
