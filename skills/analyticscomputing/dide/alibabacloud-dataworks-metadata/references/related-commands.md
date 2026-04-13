# Related CLI Commands — DataWorks Metadata

All commands below use the **`dataworks-public`** product plugin and require `--user-agent AlibabaCloud-Agent-Skills`.

## Metadata Crawler Types

| CLI Command | API Name | Description |
|------------|----------|-------------|
| `aliyun dataworks-public list-crawler-types` | ListCrawlerTypes | 获取数据地图元数据采集器类型列表 |

## Catalog & Entity Browsing

| CLI Command | API Name | Description |
|------------|----------|-------------|
| `aliyun dataworks-public list-catalogs` | ListCatalogs | 查询数据目录列表（支持dlf、starrocks类型） |
| `aliyun dataworks-public get-catalog` | GetCatalog | 获取数据目录详情 |
| `aliyun dataworks-public get-database` | GetDatabase | 获取数据库详情 |
| `aliyun dataworks-public get-table` | GetTable | 获取数据表详情（可选含业务元数据） |
| `aliyun dataworks-public update-table-business-metadata` | UpdateTableBusinessMetadata | 更新数据表业务元数据（使用说明） |

## Field (Column) Operations

| CLI Command | API Name | Description |
|------------|----------|-------------|
| `aliyun dataworks-public list-columns` | ListColumns | 查询数据表字段列表 |
| `aliyun dataworks-public get-column` | GetColumn | 获取数据表字段详情 |
| `aliyun dataworks-public update-column-business-metadata` | UpdateColumnBusinessMetadata | 更新字段业务元数据（业务描述） |

## Partition Operations

| CLI Command | API Name | Description |
|------------|----------|-------------|
| `aliyun dataworks-public list-partitions` | ListPartitions | 查询数据表分区列表（MaxCompute/HMS） |
| `aliyun dataworks-public get-partition` | GetPartition | 获取分区详情（MaxCompute/HMS） |

## Lineage Operations

| CLI Command | API Name | Description |
|------------|----------|-------------|
| `aliyun dataworks-public list-lineages` | ListLineages | 查询实体上下游血缘列表 |
| `aliyun dataworks-public list-lineage-relationships` | ListLineageRelationships | 查询两实体间血缘关系列表 |
| `aliyun dataworks-public get-lineage-relationship` | GetLineageRelationship | 获取血缘关系详情 |
| `aliyun dataworks-public create-lineage-relationship` | CreateLineageRelationship | 注册血缘关系（至少一方为自定义对象） |
| `aliyun dataworks-public delete-lineage-relationship` | DeleteLineageRelationship | 删除血缘关系 |

## Dataset Operations

| CLI Command | API Name | Description |
|------------|----------|-------------|
| `aliyun dataworks-public create-dataset` | CreateDataset | 创建数据集（单租户最多2000个） |
| `aliyun dataworks-public list-datasets` | ListDatasets | 查询数据集列表（DataWorks/PAI） |
| `aliyun dataworks-public get-dataset` | GetDataset | 获取数据集详情 |
| `aliyun dataworks-public update-dataset` | UpdateDataset | 更新数据集信息 |
| `aliyun dataworks-public delete-dataset` | DeleteDataset | 删除数据集（级联删除版本） |

## Dataset Version Operations

| CLI Command | API Name | Description |
|------------|----------|-------------|
| `aliyun dataworks-public create-dataset-version` | CreateDatasetVersion | 创建数据集版本（最多20个版本） |
| `aliyun dataworks-public list-dataset-versions` | ListDatasetVersions | 查询数据集版本列表 |
| `aliyun dataworks-public get-dataset-version` | GetDatasetVersion | 获取数据集版本信息 |
| `aliyun dataworks-public update-dataset-version` | UpdateDatasetVersion | 更新数据集版本信息 |
| `aliyun dataworks-public delete-dataset-version` | DeleteDatasetVersion | 删除数据集版本（非v1） |
| `aliyun dataworks-public preview-dataset-version` | PreviewDatasetVersion | 预览数据集版本内容（仅OSS文本） |

## Metadata Collection Operations

| CLI Command | API Name | Description |
|------------|----------|-------------|
| `aliyun dataworks-public list-meta-collections` | ListMetaCollections | 查询集合列表（类目/数据专辑） |
| `aliyun dataworks-public create-meta-collection` | CreateMetaCollection | 创建集合对象（类目/数据专辑） |
| `aliyun dataworks-public get-meta-collection` | GetMetaCollection | 获取集合详情 |
| `aliyun dataworks-public update-meta-collection` | UpdateMetaCollection | 更新集合对象 |
| `aliyun dataworks-public delete-meta-collection` | DeleteMetaCollection | 删除集合对象 |
| `aliyun dataworks-public list-entities-in-meta-collection` | ListEntitiesInMetaCollection | 查询集合中的实体列表 |
| `aliyun dataworks-public add-entity-into-meta-collection` | AddEntityIntoMetaCollection | 向集合添加实体 |
| `aliyun dataworks-public remove-entity-from-meta-collection` | RemoveEntityFromMetaCollection | 从集合移除实体 |
