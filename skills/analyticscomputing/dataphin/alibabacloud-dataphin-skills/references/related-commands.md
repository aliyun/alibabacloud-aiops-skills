# 相关命令索引

## create-maxcompute-data-source

| 命令 | 用途 | 类型 |
|------|------|------|
| `check-data-source-connectivity` | 创建前预检连通性 | 读 |
| `create-data-source` | 创建数据源（MaxCompute 类型） | 写 |
| `list-data-source-with-config` | 按类型/名称搜索数据源 | 读 |
| `check-data-source-connectivity-by-id` | 按 ID 检查连通性 | 读 |
| `delete-data-source` | 删除数据源 | 写 |
| `update-data-source-basic-info` | 编辑数据源基本信息 | 写 |
| `update-data-source-config` | 编辑数据源连接配置 | 写 |
| `get-data-source-dependencies` | 查询变更影响的任务 | 读 |

## create-and-publish-api

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-data-service-my-projects` | 查询我的数据服务项目 | 读 |
| `get-data-service-api-groups` | 查询 API 分组 | 读 |
| `create-data-service-api` | 创建数据服务 API | 写 |
| `publish-data-service-api` | 发布 API 到生产 | 写 |
| `list-data-service-published-apis` | 查询已发布 API | 读 |
| `get-data-service-api-document` | 获取 API 文档 | 读 |

## manage-app-and-bindauth

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-data-service-app` | 创建应用 | 写 |
| `get-data-service-app` | 查询应用详情 | 读 |
| `list-data-service-apps` | 查询应用列表 | 读 |
| `add-data-service-app-member` | 添加应用成员 | 写 |
| `grant-data-service-api` | 授权 API 给应用 | 写 |
| `revoke-data-service-api` | 回收 API 授权 | 写 |
| `list-authorized-data-service-api-details` | 查询已授权 API 详情 | 读 |
| `reset-data-service-app-secret` | 重置应用密钥 | 写 |

## call-data-service-api

> 本 Skill 不使用 `aliyun` CLI，通过 Python SDK 调用数据服务网关。

| 方法 | 用途 | 模式 |
|------|------|------|
| `DataphinApiClient.call_api()` | 同步调用 API | 同步 |
| `async_call_api()` | 异步调用并轮询 | 异步 |

## monitor-api-operations

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-data-service-api-call-summary` | 调用汇总统计 | 读 |
| `get-data-service-api-call-trend` | 调用趋势分析 | 读 |
| `list-data-service-api-calls` | 调用日志列表 | 读 |
| `list-data-service-api-call-statistics` | 调用统计信息 | 读 |
| `get-data-service-api-error-impact` | 异常影响汇总 | 读 |
| `list-data-service-api-impacts` | 异常调用明细 | 读 |

## manage-kg-schema

> KG OpenAPI 已发布（`--help` 实测 v6.1.1）并注册到 CLI 插件（>= 0.7.1），CLI 原生调用。仅提供整体 Schema 操作，无实体/关系类型的细粒度 CRUD 命令。

| 命令 | 用途 | 类型 |
|------|------|------|
| `export-kg-schema` | 导出整体 Schema（YAML/JSON） | 读 |
| `import-kg-schema` | 导入整体 Schema | 写 |
| `publish-kg-schema` | 发布 Schema（异步） | 写 |
| `get-kg-schema-publish-result` | 查询发布结果 | 读 |

## manage-kg-knowledge

> KG OpenAPI 已发布（`--help` 实测 v6.1.1）并注册到 CLI 插件（>= 0.7.1），CLI 原生调用。

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-kg-entity` / `update-kg-entity` / `delete-kg-entity` | 实体 CRUD | 写 |
| `get-kg-entity` / `list-kg-entity` | 实体查询 | 读 |
| `batch-create-kg-entity` | 批量创建实体 | 写 |
| `create-kg-relation` / `update-kg-relation` / `delete-kg-relation` | 关系 CRUD | 写 |
| `get-kg-relation` / `list-kg-relation` | 关系查询 | 读 |
| `batch-create-kg-relation` | 批量创建关系 | 写 |
| `exec-kg-cypher` | Cypher 图查询（只读，**仅 Neo4j 引擎**） | 读 |
| `get-kg-neighbor` | 邻居节点遍历（引擎无关） | 读 |

## query-kg

> 纯只读 Skill。KG OpenAPI 已发布（`--help` 实测 v6.1.1）并注册到 CLI 插件（>= 0.7.1），CLI 原生调用。
> **命令可用性随图引擎变化**，详见 [图引擎能力矩阵](./knowledge-graph/graph-engine-capabilities.md)。

| 命令 | 用途 | 类型 | 适用引擎 |
|------|------|------|------|
| `exec-kg-cypher` | Cypher 图查询（只读） | 读 | **仅 Neo4j**（Lindorm 报 `DPN.Commons.InternalError`） |
| `get-kg-neighbor` | 邻居节点遍历 | 读 | Neo4j + Lindorm |
| `search-kg-by-semantic` | 关键词+语义混合搜索（**仅实体**，V6.2.3+；body 字段实测为 `SearchCommand`） | 读 | Neo4j + Lindorm（插件 0.7.x 尚未注册命令，需 SDK 或工作台工具） |
| ~~`exec-kg-gremlin`~~ | Gremlin 查询 | — | **API 尚未上线，命令不存在** |

## manage-project-member

| 命令 | 用途 | 类型 |
|------|------|------|
| `add-project-member` | 添加项目成员并分配角色 | 写 |
| `remove-project-member` | 移除项目成员 | 写 |
| `update-project-member` | 更新成员角色 | 写 |
| `list-project-members` | 查询项目成员列表 | 读 |

## create-data-source

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-data-source` | 创建数据源 | 写 |
| `check-data-source-connectivity` | 创建前预检连通性 | 读/写 |
| `list-data-source-with-config` | 按类型/名称搜索数据源 | 读 |

## check-data-source-connectivity

| 命令 | 用途 | 类型 |
|------|------|------|
| `check-data-source-connectivity` | 按类型检查数据源连通性 | 写 |
| `check-data-source-connectivity-by-id` | 按 ID 检查数据源连通性 | 写 |
| `list-data-source-with-config` | 查询数据源列表 | 读 |

## create-maxcompute-compute-source

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-compute-source` | 创建计算源 | 写 |
| `check-compute-source-connectivity` | 创建前预检连通性 | 写 |
| `list-compute-source` | 查询计算源列表 | 读 |

## update-compute-source

| 命令 | 用途 | 类型 |
|------|------|------|
| `update-compute-source` | 更新计算源 | 写 |
| `get-compute-source` | 查询计算源详情 | 读 |
| `list-compute-source` | 查询计算源列表 | 读 |

## check-compute-source-connectivity

| 命令 | 用途 | 类型 |
|------|------|------|
| `check-compute-source-connectivity` | 检查计算源连通性 | 写 |
| `list-compute-source` | 查询计算源列表 | 读 |

## create-node-supplement

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-nodes` | 查询节点列表 | 读 |
| `create-node-supplement` | 创建补数据任务 | 写 |
| `get-supplement-dagrun` | 查询补数据 DAG | 读 |
| `get-supplement-dagrun-instance` | 查询补数据实例 | 读 |

## rerun-task-instance

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-projects` | 枚举项目 | 读 |
| `list-instances` | 按任务名/业务日期查询实例 | 读 |
| `operate-instance` | 批量运维实例（RERUN 等） | 写 |
| `get-physical-instance` | 查询实例状态 | 读 |
| `get-physical-instance-log` | 获取实例运行日志 | 读 |

## pause-task-instance

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-projects` | 枚举项目 | 读 |
| `list-instances` | 按任务名/业务日期查询实例，输出 DueTime | 读 |
| `operate-instance` | 批量运维实例（PAUSE / RESUME） | 写 |
| `get-physical-instance` | 验证 `NodeInfo.SchedulePaused` | 读 |

## create-pipeline-task

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-pipeline-node` | 创建管道草稿 | 写 |
| `update-pipeline` | 更新并提交管道 | 写 |
| `create-pipeline` | 一步创建管道 | 写 |
| `get-pipeline-by-id` | 查询管道详情 | 读 |

## update-pipeline-task

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-pipeline-by-id` | 回读管道任务完整配置 | 读 |
| `list-files` | 按任务名反查 fileId | 读 |
| `update-pipeline` | 全量回写管道配置并提交 | 写 |
| `update-pipeline-by-async` | 异步更新管道配置 | 写 |
| `get-pipeline-async-result` | 查询异步更新结果 | 读 |

## create-standard

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-standard` | 创建数据标准 | 写 |
| `list-standard` | 查询标准列表 | 读 |

## update-standard

| 命令 | 用途 | 类型 |
|------|------|------|
| `update-standard` | 更新数据标准 | 写 |
| `get-standard` | 查询标准详情 | 读 |
| `list-standard` | 查询标准列表 | 读 |

## manage-lookup-table

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-standard-lookup-table` | 创建码表 | 写 |
| `get-standard-lookup-table` | 查询码表详情 | 读 |
| `update-standard-lookup-table` | 更新码表（码值整体覆盖） | 写 |
| `delete-standard-lookup-table` | 删除码表 | 写 |

## manage-standard-mapping

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-asset-mapping-relations` | 按资产查映射关系 | 读 |
| `get-belong-asset-mapping` | 按归属资产（表）查映射 | 读 |
| `create-standard-mapping` | 批量创建映射（有效/无效） | 写 |
| `update-standard-mapping-to-invalid` | 映射置为无效 | 写 |
| `delete-standard-valid-mapping` | 删除有效映射 | 写 |
| `delete-standard-invalid-mapping` | 删除无效映射 | 写 |

## execute-ad-hoc-task

| 命令 | 用途 | 类型 |
|------|------|------|
| `execute-ad-hoc-task` | 执行即席任务 | 写 |
| `get-ad-hoc-task-result` | 查询即席任务结果 | 读 |
| `list-data-source-with-config` | 查询数据源 | 读 |

## find-tenant-root-node

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-batch-task-info` | 获取任务详情（含 DagId） | 读 |
| `list-files` | 按名称搜索任务文件 | 读 |
| `list-nodes` | 查询节点列表 | 读 |

## get-batch-task-info-by-name

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-files` | 按名称搜索任务文件 | 读 |
| `get-batch-task-info` | 获取任务详情 | 读 |

## get-bizdate

| 命令 | 用途 | 类型 |
|------|------|------|
| `date` | 本地系统命令获取业务日期 | 本地 |

## grant-data-source-permission

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-project-produce-user` | 查询项目生产账号 | 读 |
| `grant-resource-permission` | 授权资源权限 | 写 |
| `list-publish-records` | 查询发布记录 | 读 |
| `list-nodes` | 查询 PROD 节点 | 读 |

## create-project

当前公开 CLI 未暴露项目创建、更新、删除命令。

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-projects` | 分页查询项目列表 | 读 |
| `get-project` | 按项目 ID 获取项目详情 | 读 |
| `get-project-by-name` | 按项目名查重并定位项目 | 读 |
| `check-project-has-dependency` | 检查项目依赖 | 读 |
| `get-project-white-lists` | 查询项目白名单 | 读 |
| `replace-project-white-lists` | 替换项目白名单，执行前必须回读并 HITL | 写 |

## manage-topic-domain

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-data-domains` | 查询主题域列表 | 读 |
| `get-data-domain-info` | 获取主题域详情 | 读 |
| `create-data-domain` | 创建主题域 | 写 |
| `update-data-domain` | 更新主题域 | 写 |
| `delete-data-domain` | 删除主题域（不可回滚） | 写 |

## manage-biz-entity

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-biz-entities` | 查询业务实体列表 | 读 |
| `get-biz-entity-info` | 获取业务实体详情 | 读 |
| `get-biz-entity-info-by-version` | 查询指定版本详情 | 读 |
| `create-biz-entity` | 创建业务实体 | 写 |
| `update-biz-entity` | 更新业务实体 | 写 |
| `online-biz-entity` | 上线业务实体 | 写 |
| `offline-biz-entity` | 下线业务实体 | 写 |
| `delete-biz-entity` | 删除业务实体 | 写 |

## manage-biz-metric

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-biz-metric` | 创建业务指标定义 | 写 |
| `update-biz-metric` | 更新业务指标定义 | 写 |
| `get-biz-metric-by-name` | 按名称查询草稿态或已发布业务指标详情 | 读 |
| `delete-biz-metric` | 删除业务指标定义 | 写 |

## manage-data-classification

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-security-level` | 创建数据分级 | 写 |
| `update-security-level` | 更新数据分级 | 写 |
| `delete-security-level` | 删除数据分级 | 写 |
| `get-security-level` | 查询数据分级 | 读 |
| `create-security-classify-catalog` | 创建分类目录 | 写 |
| `update-security-classify-catalog` | 更新分类目录 | 写 |
| `delete-security-classify-catalog` | 删除分类目录 | 写 |
| `create-security-classify` | 创建数据分类 | 写 |
| `update-security-classify` | 更新数据分类 | 写 |
| `delete-security-classify` | 删除数据分类 | 写 |
| `get-security-classify` | 查询数据分类 | 读 |
| `create-security-identify-result` | 创建字段安全识别结果 | 写 |
| `get-security-identify-result` | 查询识别结果详情 | 读 |
| `list-security-identify-results` | 查询字段识别结果列表 | 读 |
| `list-security-identify-records` | 查询字段识别记录 | 读 |
| `update-security-identify-result-status` | 批量启停识别结果 | 写 |
| `delete-security-identify-results` | 批量删除识别结果 | 写 |

## manage-data-masking

> 当前公开命令集未暴露脱敏规则 CRUD；以下命令仅用于字段分类分级前置检查。

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-security-identify-results` | 查询字段安全识别结果 | 读 |
| `get-security-identify-result` | 查询识别结果详情 | 读 |
| `list-security-identify-records` | 查询表字段识别记录与分类状态 | 读 |
| `get-security-classify` | 回读分类与分级绑定 | 读 |

## submit-batch-task

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-batch-task` | 创建批任务骨架 | 写 |
| `update-batch-task` | 更新批任务 | 写 |
| `submit-batch-task` | 提交批任务到调度 | 写 |
| `get-batch-task-info` | 查询批任务详情 | 读 |

## update-batch-task

| 命令 | 用途 | 类型 |
|------|------|------|
| `update-batch-task` | 更新批任务 | 写 |
| `get-batch-task-info` | 查询批任务详情 | 读 |
| `list-files` | 按名称搜索任务文件 | 读 |

## manage-row-level-permission

| 命令 | 用途 | 类型 |
|------|------|------|
| `create-row-permission` | 创建行级权限 | 写 |
| `update-row-permission` | 更新行级权限 | 写 |
| `delete-row-permission` | 删除行级权限（不可回滚） | 写 |
| `list-row-permission` | 分页查询行级权限 | 读 |
| `get-row-permission-by-table-guids` | 按表 GUID 查询行级权限 | 读 |
| `get-account-by-row-permission-id` | 查询某规则下授权账号 | 读 |
| `list-row-permission-by-user-id` | 查询指定用户行级权限 | 读 |

## manage-column-permission

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-table-columns` | 查询资产表字段，定位字段候选 GUID | 读 |
| `get-users` | 按用户 ID 批量获取用户信息 | 读 |
| `list-resource-permissions` | 分页获取表/字段权限授权记录 | 读 |
| `grant-resource-permission` | 通过字段资源点授权 | 写 |
| `check-resource-permission` | 校验用户是否有字段权限点 | 读 |
| `list-resource-permission-operation-log` | 查询权限操作日志 | 读 |
| `revoke-resource-permission` | 回收字段资源授权 | 写 |

## create-unstructured-workflow

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-datasets` | 按关键词搜索数据集（复用判定） | 读 |
| `create-dataset` | 创建数据集（表 schema 按链路末端算子输出设计） | 写 |
| `get-dataset` | 回读 DatasetDTO + VersionList（工作流环境值唯一来源） | 读 |
| `update-dataset` | 更新数据集（FileId 必填） | 写 |
| `create-work-flow-by-json` | JSON 脚本模式创建非结构化工作流（仅 BASIC 项目） | 写 |
| `delete-dataset` | 删除测试数据集（高危：先自查下游引用） | 写 |

## update-unstructured-workflow

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-pipeline-by-id` | 回读工作流现有全量配置（基线 + 更新后验证） | 读 |
| `update-pipeline` | 提交工作流更新（PipelineType=14，全量覆盖式） | 写 |
| `get-dataset` | 切换数据集版本/表时回读环境值 | 读 |

## create-dataset

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-datasets` | 按关键词/类型/场景分页查询（查重复用） | 读 |
| `create-dataset` | 创建数据集（含 VersionConfig / TableSchema） | 写 |
| `get-dataset` | 回读 DatasetDTO + VersionList（验证 + 下游环境值来源） | 读 |
| `update-dataset` | 更新数据集（Id 与 FileId 必填） | 写 |
| `delete-dataset` | 删除数据集（高危：无回收站、不自查下游引用） | 写 |

## update-dataset-schema

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-datasets` / `get-dataset` | 回读表结构/元数据源/FileId | 读 |
| `execute-ad-hoc-task` | DATABASE_SQL 直连元数据 PG 执行 ALTER DDL | 写（高危） |
| `get-ad-hoc-task-log` / `get-ad-hoc-task-result` | 确认 DDL 执行成功/反查列生效 | 读 |
| `update-dataset` | 重新提交完整 TableSchema（等价"重新加载表结构"） | 写 |
