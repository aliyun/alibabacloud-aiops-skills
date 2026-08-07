# RAM 策略参考

本文件是全套件唯一的 RAM 权限声明文件：既提供套件级并集策略，也按子 Skill 分组给出各场景的最小权限。子 Skill 运行中遇权限错误时，按其 SKILL.md 中的 Permission Failure Handling 指引读取本文件对应分组。

## 套件级 RAM 策略（所有子 Skill 并集）

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataphin:CreateDataSource",
        "dataphin:DeleteDataSource",
        "dataphin:CheckDataSourceConnectivity",
        "dataphin:CheckDataSourceConnectivityById",
        "dataphin:ListDataSourceWithConfig",
        "dataphin:UpdateDataSourceBasicInfo",
        "dataphin:UpdateDataSourceConfig",
        "dataphin:GetDataSourceDependencies",
        "dataphin:CreateComputeSource",
        "dataphin:UpdateComputeSource",
        "dataphin:GetComputeSource",
        "dataphin:ListComputeSource",
        "dataphin:CheckComputeSourceConnectivity",
        "dataphin:CheckComputeSourceConnectivityById",
        "dataphin:DeleteComputeSource",
        "dataphin:AddProjectMember",
        "dataphin:RemoveProjectMember",
        "dataphin:UpdateProjectMember",
        "dataphin:ListProjectMembers",
        "dataphin:ListAddableUsers",
        "dataphin:AddTenantMembers",
        "dataphin:AddTenantMembersBySourceUser",
        "dataphin:ListTenantMembers",
        "dataphin:ListAddableRoles",
        "dataphin:UpdateTenantMember",
        "dataphin:RemoveTenantMember",
        "dataphin:ExecuteAdHocTask",
        "dataphin:GetAdHocTaskResult",
        "dataphin:GetAdHocTaskLog",
        "dataphin:CreateBatchTask",
        "dataphin:UpdateBatchTask",
        "dataphin:SubmitBatchTask",
        "dataphin:GetBatchTaskInfo",
        "dataphin:PublishObjectList",
        "dataphin:ListFiles",
        "dataphin:CreateDirectory",
        "dataphin:GetPhysicalNode",
        "dataphin:GetNodeUpDownStream",
        "dataphin:GetPhysicalNodeContent",
        "dataphin:ListProjects",
        "dataphin:ListInstances",
        "dataphin:OperateInstance",
        "dataphin:GetPhysicalInstance",
        "dataphin:GetPhysicalInstanceLog",
        "dataphin:ListNodes",
        "dataphin:CreateNodeSupplement",
        "dataphin:GetSupplementDagrun",
        "dataphin:GetSupplementDagrunInstance",
        "dataphin:ResumePhysicalNode",
        "dataphin:FixData",
        "dataphin:GetInstanceDownStream",
        "dataphin:GetOperationSubmitStatus",
        "dataphin:ListNodeDownStream",
        "dataphin:CreatePipelineNode",
        "dataphin:UpdatePipeline",
        "dataphin:CreatePipeline",
        "dataphin:GetPipelineById",
        "dataphin:GetPipelineAsyncResult",
        "dataphin:UpdatePipelineByAsync",
        "dataphin:CreateStandard",
        "dataphin:UpdateStandard",
        "dataphin:GetStandard",
        "dataphin:ListStandards",
        "dataphin:PublishStandard",
        "dataphin:OfflineStandard",
        "dataphin:DeleteStandard",
        "dataphin:GetStandardSet",
        "dataphin:GetStandardTemplate",
        "dataphin:CreateStandardLookupTable",
        "dataphin:GetStandardLookupTable",
        "dataphin:UpdateStandardLookupTable",
        "dataphin:DeleteStandardLookupTable",
        "dataphin:CreateStandardMapping",
        "dataphin:GetAssetMappingRelations",
        "dataphin:GetBelongAssetMapping",
        "dataphin:UpdateStandardMappingToInvalid",
        "dataphin:DeleteStandardValidMapping",
        "dataphin:DeleteStandardInvalidMapping",
        "dataphin:GetQualityWatchByObjectId",
        "dataphin:SaveQualityWatch",
        "dataphin:SearchCatalogTable",
        "dataphin:ListCatalogTableColumns",
        "dataphin:PagedQueryQualityTemplates",
        "dataphin:SaveQualityRule",
        "dataphin:ListQualitySchedules",
        "dataphin:SaveQualitySchedule",
        "dataphin:AssignQualityRuleSchedules",
        "dataphin:RemoveQualityRuleSchedules",
        "dataphin:SaveQualityAlert",
        "dataphin:GetQualityAlert",
        "dataphin:SubmitQualityRuleTasks",
        "dataphin:GetQualityRuleTask",
        "dataphin:GetQualityRuleTaskLog",
        "dataphin:OpenCloseQualityRules",
        "dataphin:GetQualityWatchTask",
        "dataphin:PagedQueryQualityRules",
        "dataphin:PagedQueryQualityRuleTasks",
        "dataphin:ListTablePartitions",
        "dataphin:SearchDataSourceConfig",
        "dataphin:CreateJdbcConnection",
        "dataphin:ExecSqlByJdbc",
        "dataphin:QuerySqlTaskStatus",
        "dataphin:FetchSqlResult",
        "dataphin:CloseJdbcConnection",
        "dataphin:GetProjectProduceUser",
        "dataphin:GrantResourcePermission",
        "dataphin:RevokeResourcePermission",
        "dataphin:ListResourcePermissions",
        "dataphin:ListResourcePermissionOperationLog",
        "dataphin:CheckResourcePermission",
        "dataphin:GetUsers",
        "dataphin:ListPublishRecords",
        "dataphin:CreateRowPermission",
        "dataphin:UpdateRowPermission",
        "dataphin:DeleteRowPermission",
        "dataphin:ListRowPermission",
        "dataphin:GetRowPermissionByTableGuids",
        "dataphin:GetAccountByRowPermissionId",
        "dataphin:ListRowPermissionByUserId",
        "dataphin:GetTableColumns",
        "dataphin:GetSecurityClassify",
        "dataphin:GetSecurityIdentifyResult",
        "dataphin:ListSecurityIdentifyRecords",
        "dataphin:ListSecurityIdentifyResults",
        "dataphin:GetProject",
        "dataphin:GetProjectByName",
        "dataphin:CheckProjectHasDependency",
        "dataphin:GetProjectWhiteLists",
        "dataphin:ReplaceProjectWhiteLists",
        "dataphin:CreateDataDomain",
        "dataphin:UpdateDataDomain",
        "dataphin:DeleteDataDomain",
        "dataphin:GetDataDomainInfo",
        "dataphin:ListDataDomains",
        "dataphin:ListBizEntities",
        "dataphin:GetBizEntityInfo",
        "dataphin:GetBizEntityInfoByVersion",
        "dataphin:CreateBizEntity",
        "dataphin:UpdateBizEntity",
        "dataphin:OnlineBizEntity",
        "dataphin:OfflineBizEntity",
        "dataphin:DeleteBizEntity",
        "dataphin:CreateBizMetric",
        "dataphin:UpdateBizMetric",
        "dataphin:GetBizMetricByName",
        "dataphin:DeleteBizMetric",
        "dataphin:CreateSecurityLevel",
        "dataphin:UpdateSecurityLevel",
        "dataphin:DeleteSecurityLevel",
        "dataphin:GetSecurityLevel",
        "dataphin:CreateSecurityClassifyCatalog",
        "dataphin:UpdateSecurityClassifyCatalog",
        "dataphin:DeleteSecurityClassifyCatalog",
        "dataphin:CreateSecurityClassify",
        "dataphin:UpdateSecurityClassify",
        "dataphin:DeleteSecurityClassify",
        "dataphin:CreateSecurityIdentifyResult",
        "dataphin:UpdateSecurityIdentifyResultStatus",
        "dataphin:DeleteSecurityIdentifyResults",
        "dataphin:GetDataServiceMyProjects",
        "dataphin:GetDataServiceApiGroups",
        "dataphin:CreateDataServiceApi",
        "dataphin:PublishDataServiceApi",
        "dataphin:ListDataServicePublishedApis",
        "dataphin:GetDataServiceApiDocument",
        "dataphin:CreateDataServiceApp",
        "dataphin:GetDataServiceApp",
        "dataphin:ListDataServiceApps",
        "dataphin:GetDataServiceAppGroups",
        "dataphin:AddDataServiceAppMember",
        "dataphin:GrantDataServiceApi",
        "dataphin:RevokeDataServiceApi",
        "dataphin:ListAuthorizedDataServiceApiDetails",
        "dataphin:ResetDataServiceAppSecret",
        "dataphin:GetDataServiceApiCallSummary",
        "dataphin:GetDataServiceApiCallTrend",
        "dataphin:ListDataServiceApiCalls",
        "dataphin:GetDataServiceApiErrorImpact",
        "dataphin:ListDataServiceApiImpacts",
        "dataphin:ListDataServiceApiCallStatistics",
        "dataphin:ExportKgSchema",
        "dataphin:ImportKgSchema",
        "dataphin:PublishKgSchema",
        "dataphin:GetKgSchemaPublishResult",
        "dataphin:CreateKgEntity",
        "dataphin:UpdateKgEntity",
        "dataphin:DeleteKgEntity",
        "dataphin:GetKgEntity",
        "dataphin:ListKgEntity",
        "dataphin:BatchCreateKgEntity",
        "dataphin:CreateKgRelation",
        "dataphin:UpdateKgRelation",
        "dataphin:DeleteKgRelation",
        "dataphin:GetKgRelation",
        "dataphin:ListKgRelation",
        "dataphin:BatchCreateKgRelation",
        "dataphin:ExecKgCypher",
        "dataphin:GetKgNeighbor",
        "dataphin:SearchKgBySemantic",
        "dataphin:CreateDataset",
        "dataphin:GetDataset",
        "dataphin:ListDatasets",
        "dataphin:UpdateDataset",
        "dataphin:DeleteDataset",
        "dataphin:CreateWorkFlowByJson"
      ],
      "Resource": "*"
    }
  ]
}
```

## 按子 Skill 分组

### dataplan

#### create-data-source
- `dataphin:CreateDataSource`
- `dataphin:CheckDataSourceConnectivity`
- `dataphin:CheckDataSourceConnectivityById`
- `dataphin:ListDataSourceWithConfig`
- `dataphin:UpdateDataSourceConfig`

#### check-data-source-connectivity
- `dataphin:CheckDataSourceConnectivity`
- `dataphin:CheckDataSourceConnectivityById`
- `dataphin:ListDataSourceWithConfig`

> 连通性校验为只读探测（operationType=get），不创建/修改任何数据源资源。

#### create-maxcompute-compute-source（目录 create-compute-source/create-maxcompute-compute-source）
- `dataphin:CreateComputeSource`
- `dataphin:CheckComputeSourceConnectivity`
- `dataphin:CheckComputeSourceConnectivityById`
- `dataphin:ListComputeSource`
- `dataphin:GetComputeSource`
- `dataphin:DeleteComputeSource`（Cleanup 用）

#### update-compute-source
- `dataphin:UpdateComputeSource`
- `dataphin:GetComputeSource`
- `dataphin:ListComputeSource`

#### check-compute-source-connectivity
- `dataphin:CheckComputeSourceConnectivity`
- `dataphin:ListComputeSource`

#### create-maxcompute-data-source
- `dataphin:CreateDataSource`
- `dataphin:DeleteDataSource`
- `dataphin:CheckDataSourceConnectivity`
- `dataphin:CheckDataSourceConnectivityById`
- `dataphin:ListDataSourceWithConfig`
- `dataphin:UpdateDataSourceBasicInfo`
- `dataphin:UpdateDataSourceConfig`
- `dataphin:GetDataSourceDependencies`

#### create-project
- `dataphin:ListProjects`
- `dataphin:GetProject`
- `dataphin:GetProjectByName`
- `dataphin:CheckProjectHasDependency`
- `dataphin:GetProjectWhiteLists`
- `dataphin:ReplaceProjectWhiteLists`

#### manage-project-member
- `dataphin:AddProjectMember` — 添加项目成员
- `dataphin:RemoveProjectMember` — 移除项目成员
- `dataphin:UpdateProjectMember` — 更新成员角色
- `dataphin:ListProjectMembers` — 查询项目成员列表（用于验证变更生效）

### manage

#### manage-tenant-member
- `dataphin:ListAddableUsers`
- `dataphin:AddTenantMembers`
- `dataphin:AddTenantMembersBySourceUser`
- `dataphin:ListTenantMembers`
- `dataphin:ListAddableRoles`
- `dataphin:UpdateTenantMember`
- `dataphin:RemoveTenantMember`

> 注意：这些 Action 通常仅限租户 SuperAdmin 或系统管理员调用。普通租户成员无法执行成员增删改操作。

#### manage-row-level-permission
- `dataphin:CreateRowPermission`
- `dataphin:UpdateRowPermission`
- `dataphin:DeleteRowPermission`
- `dataphin:ListRowPermission`
- `dataphin:GetRowPermissionByTableGuids`
- `dataphin:GetAccountByRowPermissionId`
- `dataphin:ListRowPermissionByUserId`

#### manage-column-permission
- `dataphin:GetTableColumns`
- `dataphin:GrantResourcePermission`
- `dataphin:RevokeResourcePermission`
- `dataphin:ListResourcePermissions`
- `dataphin:ListResourcePermissionOperationLog`
- `dataphin:CheckResourcePermission`
- `dataphin:GetUsers`

### dev

#### execute-ad-hoc-task
- `dataphin:ExecuteAdHocTask`
- `dataphin:GetAdHocTaskResult`
- `dataphin:GetAdHocTaskLog`
- `dataphin:ListDataSourceWithConfig`

#### submit-batch-task
- `dataphin:CreateBatchTask`
- `dataphin:SubmitBatchTask`
- `dataphin:PublishObjectList`
- `dataphin:GetBatchTaskInfo`
- `dataphin:ListFiles`
- `dataphin:CreateDirectory`
- `dataphin:GetPhysicalNode`
- `dataphin:GetNodeUpDownStream`
- `dataphin:GetPhysicalNodeContent`

#### update-batch-task
- `dataphin:UpdateBatchTask`
- `dataphin:GetBatchTaskInfo`
- `dataphin:ListFiles`
- `dataphin:SubmitBatchTask`
- `dataphin:PublishObjectList`
- `dataphin:GetPhysicalNode`
- `dataphin:GetNodeUpDownStream`
- `dataphin:ListDataSourceWithConfig`

#### find-tenant-root-node
- `dataphin:GetBatchTaskInfo`
- `dataphin:ListFiles`
- `dataphin:CreateBatchTask` — 方式 B（空项目）需创建临时任务读取 DagId
- `dataphin:ListNodes`

#### get-batch-task-info-by-name
- `dataphin:ListFiles`
- `dataphin:GetBatchTaskInfo`

#### get-bizdate
- 无云端 API 调用（本地命令），无需任何 RAM 权限

### ops

#### create-node-supplement
- `dataphin:ListNodes`
- `dataphin:ListNodeDownStream`
- `dataphin:CreateNodeSupplement`
- `dataphin:GetOperationSubmitStatus`
- `dataphin:GetSupplementDagrun`
- `dataphin:GetSupplementDagrunInstance`

#### rerun-task-instance
- `dataphin:ListProjects`
- `dataphin:ListInstances`
- `dataphin:OperateInstance`
- `dataphin:GetPhysicalInstance`
- `dataphin:GetPhysicalInstanceLog`
- `dataphin:GetInstanceDownStream`
- `dataphin:FixData`

#### monitor-task-instance
- `dataphin:ListInstances`
- `dataphin:GetPhysicalInstance`
- `dataphin:GetPhysicalInstanceLog`
- `dataphin:ListNodes`

> 若需进一步操作（如恢复暂停节点），额外需要 `dataphin:ResumePhysicalNode`。

#### pause-task-instance
- `dataphin:ListProjects`
- `dataphin:ListInstances`
- `dataphin:OperateInstance`
- `dataphin:GetPhysicalInstance`

### pipeline

#### create-pipeline-task
- `dataphin:CreatePipelineNode`
- `dataphin:UpdatePipeline`
- `dataphin:CreatePipeline`
- `dataphin:GetPipelineById`

#### update-pipeline-task
- `dataphin:GetPipelineById`
- `dataphin:ListFiles`
- `dataphin:UpdatePipeline`
- `dataphin:UpdatePipelineByAsync`
- `dataphin:GetPipelineAsyncResult`

### assets

#### create-standard
- `dataphin:CreateStandard`
- `dataphin:GetStandardSet`（反查标准集）
- `dataphin:GetStandardTemplate`（反查标准模板）
- `dataphin:GetStandard`
- `dataphin:ListStandards`
- `dataphin:DeleteStandard`（Cleanup 用）

#### update-standard
- `dataphin:UpdateStandard`
- `dataphin:GetStandard`
- `dataphin:GetStandardSet`
- `dataphin:GetStandardTemplate`
- `dataphin:ListStandards`

#### manage-data-standard
- `dataphin:CreateStandard` — create-standard（写）
- `dataphin:UpdateStandard` — update-standard（写）
- `dataphin:PublishStandard` — publish-standard（写）
- `dataphin:OfflineStandard` — offline-standard（写）
- `dataphin:DeleteStandard` — delete-standard（写）
- `dataphin:ListStandards` — list-standards（读）
- `dataphin:GetStandard` — get-standard（读）

> 数据标准管理通常还需具备全局角色 `DATA_STANDARD_MANAGER`。

#### manage-lookup-table
- `dataphin:CreateStandardLookupTable` — create-standard-lookup-table（写）
- `dataphin:GetStandardLookupTable` — get-standard-lookup-table（读）
- `dataphin:UpdateStandardLookupTable` — update-standard-lookup-table（写）
- `dataphin:DeleteStandardLookupTable` — delete-standard-lookup-table（写）

> 码表操作通常还需具备全局角色 `DATA_STANDARD_MANAGER`。

#### manage-standard-mapping
- `dataphin:CreateStandardMapping` — create-standard-mapping（写）
- `dataphin:GetAssetMappingRelations` — get-asset-mapping-relations（读）
- `dataphin:GetBelongAssetMapping` — get-belong-asset-mapping（读）
- `dataphin:UpdateStandardMappingToInvalid` — update-standard-mapping-to-invalid（写）
- `dataphin:DeleteStandardValidMapping` — delete-standard-valid-mapping（写）
- `dataphin:DeleteStandardInvalidMapping` — delete-standard-invalid-mapping（写）

> 映射操作需映射关系管理权限（超级管理员 / 数据标准管理员 / 标准负责人）。

#### manage-topic-domain
- `dataphin:ListDataDomains`
- `dataphin:GetDataDomainInfo`
- `dataphin:CreateDataDomain`
- `dataphin:UpdateDataDomain`
- `dataphin:DeleteDataDomain`

#### manage-biz-entity
- `dataphin:ListBizEntities`
- `dataphin:GetBizEntityInfo`
- `dataphin:GetBizEntityInfoByVersion`
- `dataphin:CreateBizEntity`
- `dataphin:UpdateBizEntity`
- `dataphin:OnlineBizEntity`
- `dataphin:OfflineBizEntity`
- `dataphin:DeleteBizEntity`

#### manage-biz-metric
- `dataphin:CreateBizMetric`
- `dataphin:UpdateBizMetric`
- `dataphin:GetBizMetricByName`
- `dataphin:DeleteBizMetric`

#### configure-quality-rule
- `dataphin:GetQualityWatchByObjectId`
- `dataphin:SaveQualityWatch`
- `dataphin:SearchCatalogTable`
- `dataphin:ListCatalogTableColumns`
- `dataphin:PagedQueryQualityTemplates`
- `dataphin:SaveQualityRule`
- `dataphin:ListQualitySchedules`
- `dataphin:SaveQualitySchedule`
- `dataphin:AssignQualityRuleSchedules`
- `dataphin:RemoveQualityRuleSchedules`
- `dataphin:SaveQualityAlert`
- `dataphin:GetQualityAlert`
- `dataphin:SubmitQualityRuleTasks`
- `dataphin:GetQualityRuleTask`
- `dataphin:GetQualityRuleTaskLog`
- `dataphin:OpenCloseQualityRules`
- `dataphin:GetQualityWatchTask`
- `dataphin:PagedQueryQualityRules`
- `dataphin:PagedQueryQualityRuleTasks`
- `dataphin:ListTablePartitions`

> 未采集外部数据源表取字段场景另需：`dataphin:SearchDataSourceConfig`、`dataphin:CreateJdbcConnection`、`dataphin:ExecSqlByJdbc`、`dataphin:QuerySqlTaskStatus`、`dataphin:FetchSqlResult`、`dataphin:CloseJdbcConnection`。

### datasecurity

#### grant-data-source-permission
- `dataphin:GetProjectProduceUser`
- `dataphin:ListDataSourceWithConfig`
- `dataphin:GrantResourcePermission`
- `dataphin:ListResourcePermissions`
- `dataphin:ListPublishRecords`
- `dataphin:ListNodes`

#### manage-data-classification
- `dataphin:CreateSecurityLevel`
- `dataphin:UpdateSecurityLevel`
- `dataphin:DeleteSecurityLevel`
- `dataphin:GetSecurityLevel`
- `dataphin:CreateSecurityClassifyCatalog`
- `dataphin:UpdateSecurityClassifyCatalog`
- `dataphin:DeleteSecurityClassifyCatalog`
- `dataphin:CreateSecurityClassify`
- `dataphin:UpdateSecurityClassify`
- `dataphin:DeleteSecurityClassify`
- `dataphin:GetSecurityClassify`
- `dataphin:CreateSecurityIdentifyResult`
- `dataphin:GetSecurityIdentifyResult`
- `dataphin:ListSecurityIdentifyResults`
- `dataphin:ListSecurityIdentifyRecords`
- `dataphin:UpdateSecurityIdentifyResultStatus`
- `dataphin:DeleteSecurityIdentifyResults`

#### manage-data-masking
- `dataphin:ListSecurityIdentifyResults` — 查询字段安全识别结果
- `dataphin:GetSecurityIdentifyResult` — 查询识别结果详情
- `dataphin:ListSecurityIdentifyRecords` — 查询表字段识别记录与分类状态
- `dataphin:GetSecurityClassify` — 回读分类与分级绑定

### dataservice

#### create-and-publish-api
- `dataphin:GetDataServiceMyProjects`
- `dataphin:GetDataServiceApiGroups`
- `dataphin:CreateDataServiceApi`
- `dataphin:PublishDataServiceApi`
- `dataphin:ListDataServicePublishedApis`
- `dataphin:GetDataServiceApiDocument`

#### manage-app-and-bindauth
- `dataphin:CreateDataServiceApp`
- `dataphin:GetDataServiceApp`
- `dataphin:GetDataServiceAppGroups`
- `dataphin:ListDataServiceApps`
- `dataphin:AddDataServiceAppMember`
- `dataphin:GrantDataServiceApi`
- `dataphin:RevokeDataServiceApi`
- `dataphin:ListAuthorizedDataServiceApiDetails`
- `dataphin:ResetDataServiceAppSecret`

#### call-data-service-api

> 本 Skill 不使用 RAM 认证，使用数据服务应用认证（AppKey/AppSecret）。
> 无需额外 RAM 权限。调用权限通过 `manage-app-and-bindauth` 的应用授权机制控制。

#### monitor-api-operations
- `dataphin:GetDataServiceApiCallSummary`
- `dataphin:GetDataServiceApiCallTrend`
- `dataphin:ListDataServiceApiCalls`
- `dataphin:GetDataServiceApiErrorImpact`
- `dataphin:ListDataServiceApiImpacts`
- `dataphin:ListDataServiceApiCallStatistics`

### knowledge-graph

#### manage-kg-schema
- `dataphin:ExportKgSchema`
- `dataphin:ImportKgSchema`
- `dataphin:PublishKgSchema`
- `dataphin:GetKgSchemaPublishResult`

> KG OpenAPI 已发布并注册到 CLI 插件（>= 0.7.1），仅提供整体 Schema 操作，无实体/关系类型细粒度 CRUD 权限需求。

#### manage-kg-knowledge
- `dataphin:CreateKgEntity` / `UpdateKgEntity` / `DeleteKgEntity` / `GetKgEntity` / `ListKgEntity`
- `dataphin:BatchCreateKgEntity`
- `dataphin:CreateKgRelation` / `UpdateKgRelation` / `DeleteKgRelation` / `GetKgRelation` / `ListKgRelation`
- `dataphin:BatchCreateKgRelation`

#### query-kg（只读）
- `dataphin:ExecKgCypher` — 执行 Cypher 图查询（只读，**仅 Neo4j 引擎空间可用**）
- `dataphin:GetKgNeighbor` — 获取指定实体的邻居节点（引擎无关）
- `dataphin:SearchKgBySemantic` — 关键词+语义混合搜索（引擎无关，**仅实体搜索**，V6.2.3+）

> KG 相关权限不足时（`Dataphin.KG.NoPermission`），还需确认用户在知识图谱空间中有对应的数据权限。
>
> 图引擎差异：Lindorm 图引擎空间不支持 Cypher（`ExecKgCypher` 报 `DPN.Commons.InternalError`），而 `ExecKgGremlin` 尚未上线；完整矩阵见 [图引擎能力矩阵](./knowledge-graph/graph-engine-capabilities.md)。

### unstructured-data

#### create-unstructured-workflow
- `dataphin:ListDatasets`（查重/复用）
- `dataphin:CreateDataset`
- `dataphin:GetDataset`（回读验证）
- `dataphin:UpdateDataset`
- `dataphin:DeleteDataset`（Cleanup 用）
- `dataphin:CreateWorkFlowByJson`

#### update-unstructured-workflow
- `dataphin:GetPipelineById`（回读工作流）
- `dataphin:UpdatePipeline`
- `dataphin:GetDataset`

#### create-dataset
- `dataphin:ListDatasets`
- `dataphin:CreateDataset`
- `dataphin:GetDataset`
- `dataphin:UpdateDataset`
- `dataphin:DeleteDataset`

#### update-dataset-schema
- `dataphin:ListDatasets`
- `dataphin:GetDataset`
- `dataphin:UpdateDataset`
- `dataphin:ExecuteAdHocTask`（ALTER TABLE 加列）
- `dataphin:GetAdHocTaskLog`
- `dataphin:GetAdHocTaskResult`

## Permission Failure Handling

若遇到权限错误（HTTP 403 或 ErrorCode 含 `Forbidden`/`NoPermission`），请：
1. 确认 RAM 用户已附加上述策略（套件级并集，或本 skill 对应分组的最小权限）
2. 确认策略中 Resource 范围覆盖目标租户
3. 联系租户管理员授权
