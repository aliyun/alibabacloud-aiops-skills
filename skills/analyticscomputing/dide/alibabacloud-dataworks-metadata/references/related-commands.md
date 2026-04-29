# Related CLI Commands — DataWorks Metadata

All commands below use the **`dataworks-public`** product plugin. The user-agent `AlibabaCloud-Agent-Skills/alibabacloud-dataworks-metadata` is bound session-wide via AI-Mode (`aliyun configure ai-mode enable` + `aliyun configure ai-mode set-user-agent --user-agent "..."`) per `SKILL.md`, so no per-command `--user-agent` flag is needed. Disable AI-Mode (`aliyun configure ai-mode disable`) when the Skill's work is complete.

Every command MUST be invoked with `--read-timeout 60 --connect-timeout 10` to bound network waits.

> **Scope note** — This Skill exposes **read + non-destructive write** APIs only. The 5 destructive APIs (`DeleteLineageRelationship`, `DeleteDataset`, `DeleteDatasetVersion`, `DeleteMetaCollection`, `RemoveEntityFromMetaCollection`) exist in the upstream DataWorks API but are intentionally NOT exposed and MUST NOT be invoked. Perform deletions in the DataWorks console.

> **Idempotency** — Every `Create*` / `Add*` action below MUST be preceded by a check-then-act read (matching `List*` / `Get*`) to avoid creating duplicates on retry. See SKILL.md `Rules → [MUST] Idempotency`.

## Metadata Crawler Types

| CLI Command | API Name | R/W | Description |
|------------|----------|-----|-------------|
| `aliyun dataworks-public list-crawler-types` | ListCrawlerTypes | R | 获取数据地图元数据采集器类型列表 |

## Catalog & Entity Browsing

| CLI Command | API Name | R/W | Description |
|------------|----------|-----|-------------|
| `aliyun dataworks-public list-catalogs` | ListCatalogs | R | 查询数据目录列表（支持dlf、starrocks类型） |
| `aliyun dataworks-public get-catalog` | GetCatalog | R | 获取数据目录详情 |
| `aliyun dataworks-public get-database` | GetDatabase | R | 获取数据库详情 |
| `aliyun dataworks-public get-table` | GetTable | R | 获取数据表详情（可选含业务元数据） |
| `aliyun dataworks-public update-table-business-metadata` | UpdateTableBusinessMetadata | W | 更新数据表业务元数据（使用说明） |

## Field (Column) Operations

| CLI Command | API Name | R/W | Description |
|------------|----------|-----|-------------|
| `aliyun dataworks-public list-columns` | ListColumns | R | 查询数据表字段列表 |
| `aliyun dataworks-public get-column` | GetColumn | R | 获取数据表字段详情 |
| `aliyun dataworks-public update-column-business-metadata` | UpdateColumnBusinessMetadata | W | 更新字段业务元数据（业务描述） |

## Partition Operations

| CLI Command | API Name | R/W | Description |
|------------|----------|-----|-------------|
| `aliyun dataworks-public list-partitions` | ListPartitions | R | 查询数据表分区列表（MaxCompute/HMS） |
| `aliyun dataworks-public get-partition` | GetPartition | R | 获取分区详情（MaxCompute/HMS） |

## Lineage Operations

| CLI Command | API Name | R/W | Description |
|------------|----------|-----|-------------|
| `aliyun dataworks-public list-lineages` | ListLineages | R | 查询实体上下游血缘列表 |
| `aliyun dataworks-public list-lineage-relationships` | ListLineageRelationships | R | 查询两实体间血缘关系列表 |
| `aliyun dataworks-public get-lineage-relationship` | GetLineageRelationship | R | 获取血缘关系详情 |
| `aliyun dataworks-public create-lineage-relationship` | CreateLineageRelationship | W | 注册血缘关系（至少一方为自定义对象；调用前先 list 检查重复） |

## Dataset Operations

| CLI Command | API Name | R/W | Description |
|------------|----------|-----|-------------|
| `aliyun dataworks-public create-dataset` | CreateDataset | W | 创建数据集（单租户最多 2000 个；调用前先 list 检查同名） |
| `aliyun dataworks-public list-datasets` | ListDatasets | R | 查询数据集列表（DataWorks/PAI） |
| `aliyun dataworks-public get-dataset` | GetDataset | R | 获取数据集详情 |
| `aliyun dataworks-public update-dataset` | UpdateDataset | W | 更新数据集信息（同值幂等） |

## Dataset Version Operations

| CLI Command | API Name | R/W | Description |
|------------|----------|-----|-------------|
| `aliyun dataworks-public create-dataset-version` | CreateDatasetVersion | W | 创建数据集版本（最多 20 个；调用前先 list 检查重复 Url+MountPath） |
| `aliyun dataworks-public list-dataset-versions` | ListDatasetVersions | R | 查询数据集版本列表 |
| `aliyun dataworks-public get-dataset-version` | GetDatasetVersion | R | 获取数据集版本信息 |
| `aliyun dataworks-public update-dataset-version` | UpdateDatasetVersion | W | 更新数据集版本信息（同值幂等） |
| `aliyun dataworks-public preview-dataset-version` | PreviewDatasetVersion | R | 预览数据集版本内容（仅 OSS 文本） |

## Metadata Collection Operations

| CLI Command | API Name | R/W | Description |
|------------|----------|-----|-------------|
| `aliyun dataworks-public list-meta-collections` | ListMetaCollections | R | 查询集合列表（类目/数据专辑） |
| `aliyun dataworks-public create-meta-collection` | CreateMetaCollection | W | 创建集合对象（调用前先 list 检查同名同 parent） |
| `aliyun dataworks-public get-meta-collection` | GetMetaCollection | R | 获取集合详情 |
| `aliyun dataworks-public update-meta-collection` | UpdateMetaCollection | W | 更新集合对象（同值幂等） |
| `aliyun dataworks-public list-entities-in-meta-collection` | ListEntitiesInMetaCollection | R | 查询集合中的实体列表 |
| `aliyun dataworks-public add-entity-into-meta-collection` | AddEntityIntoMetaCollection | W | 向集合添加实体（调用前先 list 检查实体是否已存在） |
