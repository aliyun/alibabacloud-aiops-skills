# 验收标准

## 套件级验收

| 检查项 | 标准 |
|--------|------|
| CLI 版本 | `aliyun version` >= 3.3.3 |
| 插件可用 | `aliyun dataphin-public --help` 无报错 |
| Profile 有效 | `aliyun configure list` 显示有效 AK |
| 路由分发 | 关键词能正确匹配到子 Skill |

## 子 Skill 验收

### create-maxcompute-data-source
- [ ] `check-data-source-connectivity` 返回 `ConnectStatus: true`
- [ ] `create-data-source` 返回 `Code: OK` 和 `ProdDataSourceId`
- [ ] `list-data-source-with-config` 按名称反查命中
- [ ] `check-data-source-connectivity-by-id` 返回 `ConnectStatus: true`
- [ ] DEV-PROD 模式可成功创建开发环境数据源
- [ ] `delete-data-source` Mode=DEV_PROD 成功删除

### create-and-publish-api
- [ ] 能查询到数据服务项目
- [ ] 能创建 SQL 模式 API
- [ ] 能发布 API 到生产环境
- [ ] 发布后能在列表中查到

### manage-app-and-bindauth
- [ ] 能创建数据服务应用
- [ ] 能为应用授权 API
- [ ] 能验证授权结果

### call-data-service-api
- [ ] 能使用 Python SDK 同步调用 API
- [ ] 能使用 Python SDK 异步调用 API
- [ ] 返回正确业务数据
- [ ] AppKey/AppSecret 通过环境变量传入

### monitor-api-operations
- [ ] 能查看 API 调用汇总
- [ ] 能查看调用趋势和日志

### manage-kg-schema
- [ ] 能导出整体 Schema（YAML，`SchemaInfo.Content`）
- [ ] 能编辑 YAML 后整体导入（无细粒度类型 CRUD，类型增删改走导出→编辑→导入）
- [ ] 能发布 Schema（返回 `Data.VersionId`）并查询发布结果（`Data.Status: Published`）
- [ ] 所有 CLI 命令为原生 kebab-case（插件 >= 0.7.1）

### manage-kg-knowledge
- [ ] 能创建实体和关系
- [ ] 能批量导入实体/关系
- [ ] 能执行 Cypher 查询
- [ ] 能遍历邻居节点
- [ ] 所有 CLI 命令为原生 kebab-case（插件 >= 0.7.1）

### query-kg
- [ ] `exec-kg-cypher` 能执行只读 Cypher 查询（返回 `Data.RowList` / `Data.NodeList`）
- [ ] `get-kg-neighbor` 能按实体遍历邻居（`--entity-data-id` + `--entity-type` 必填）
- [ ] 全程无任何写操作
- [ ] 所有 CLI 命令为原生 kebab-case（插件 >= 0.7.1）

### rerun-task-instance
- [ ] 能按任务名 + 业务日期定位到实例
- [ ] 跨项目搜索到多条时能让用户选择唯一目标
- [ ] `operate-instance --operation RERUN` 返回 `Success=true`
- [ ] 重跑后能查询实例状态变化
- [ ] 实例仍失败时能拉取日志并输出根因

### pause-task-instance
- [ ] 能按任务名 + 业务日期 + 运行时点定位实例
- [ ] bizdate 取 T-1（当日运行的实例业务日期为昨天）
- [ ] `operate-instance --operation PAUSE` 返回 `Success=true`
- [ ] 验证 `NodeInfo.SchedulePaused=true`（而非 `StatusList` 变为 PAUSED）
- [ ] `--operation RESUME` 后 `SchedulePaused` 变回 `false`

### create-project
- [ ] 能识别创建项目、新建 Dataphin 项目、初始化 DevProd / Basic 项目等意图
- [ ] 能提示当前公开 `dataphin-public` CLI 未暴露项目创建、更新、删除命令
- [ ] 能使用 `get-project-by-name` 查重，并用 `list-projects` / `get-project` 回读详情
- [ ] 能使用 `check-project-has-dependency` 做删除或迁移前依赖检查
- [ ] 能使用 `get-project-white-lists` 查询白名单，替换前必须回读旧值并 HITL 确认

### manage-data-classification
- [ ] 能清楚区分分级、分类、字段识别结果三层对象
- [ ] 能创建/更新/删除/查询分级、分类目录、分类和字段识别结果
- [ ] 字段打标优先使用 `create-security-identify-result`，不把创建分类误判为字段已打标
- [ ] `--conflict-strategy` 默认使用 `COVER_UNLOCKED`；使用 `COVER_ALL` 前必须二次确认
- [ ] 删除时按识别结果 → 分类 → 分级顺序清理，并确认脱敏、审批或资产展示依赖

### manage-topic-domain
- [ ] 能查询主题域列表与详情
- [ ] 能在指定数据板块下创建主题域
- [ ] 能更新主题域并回读字段确认
- [ ] 能删除主题域并反查为空
- [ ] create/update/delete 必带 `--biz-unit-id`

### manage-biz-entity
- [ ] 能查询业务实体列表与详情
- [ ] 能创建业务对象（BIZ_OBJECT）或业务活动（BIZ_PROCESS）
- [ ] 能上线/下线业务实体并反查状态变化
- [ ] 能更新业务实体并回读字段确认
- [ ] 能删除业务实体并反查为空
- [ ] `--type` 与 `--biz-object` / `--biz-process` 分支匹配，OpenAPI JSON 使用 PascalCase 字段

### manage-biz-metric
- [ ] 能创建业务指标定义并回读草稿态详情
- [ ] 能更新业务指标展示名、描述、指标口径、目录等字段并回读确认
- [ ] 能按名称查询草稿态与已发布态详情，正确使用 `--draft true/false`
- [ ] 能删除业务指标定义并反查目标不存在
- [ ] 不伪造 `publish-biz-metric`、`online-biz-metric`、`offline-biz-metric` 等不存在命令

### manage-row-level-permission
- [ ] 能分页查询行级权限列表
- [ ] 能创建行级权限，并通过 list 反查 `rowPermissionId`
- [ ] 能按表 GUID 查询目标表上的行级权限
- [ ] 能更新行级权限规则并回读确认
- [ ] 能查询某规则下的授权账号和某用户拥有的行级权限
- [ ] 能删除行级权限并反查目标不存在
- [ ] `mappingColumns` / `rules` / `tables` 使用每个数组元素一个 JSON 对象字符串的 CLI list 格式
- [ ] update 前回读并完整回填，避免清空已有规则或关联表

### manage-column-permission
- [ ] 能通过 `get-table-columns` 定位目标表字段候选 GUID，并确认权限 API 可识别的 `ResourceId`
- [ ] 能通过 `list-resource-permissions --tab-type TABLE` 查询表/字段权限授权记录
- [ ] 能通过 `grant-resource-permission` 为字段资源授予 `SELECT` 权限
- [ ] 能通过 `check-resource-permission` 校验用户对字段资源的权限点
- [ ] 能通过 `list-resource-permission-operation-log` 查询授权/回收操作日志
- [ ] 能通过 `revoke-resource-permission` 回收字段资源授权
- [ ] `--resource-list` 使用 JSON 对象元素格式，如 `--resource-list '{"ResourceId":"field_guid"}'`
- [ ] 字段权限与行级权限边界清晰，不伪造内部 REST 命令

### manage-data-masking
- [ ] 能识别手机号、身份证、邮箱、姓名等字段脱敏需求，并拆解算法、作用范围、场景和白名单
- [ ] 能通过公开识别结果、识别记录和分类查询命令完成字段分类分级前置检查
- [ ] 能明确说明当前公开命令集与版本感知 OpenAPI 索引未暴露脱敏规则 CRUD / 白名单 / 默认配置命令
- [ ] 不伪造 `create-desensitize-rule`、`update-desensitize-rule` 等不存在的公开 CLI 命令
- [ ] 不直接调用页面内部脱敏 REST，只作为业务语义参考
- [ ] 能输出包含字段、分类、算法、范围、场景、白名单和验证方式的完整需求清单
- [ ] 能说明分类分级是脱敏前置标签，不等于查询结果已经脱敏

### update-pipeline-task
- [ ] 能按 `--pipeline-id` / `--file-id` / `--node-id` 定位任务并回读完整配置
- [ ] 修改前已落盘回滚基线，HITL 确认信息含变更 diff
- [ ] `update-pipeline` 全量回写返回 `Code: OK`
- [ ] 回写后反查：目标字段已变更、未改字段未丢失
### create-unstructured-workflow
- [ ] 设计稿（算子链 + 数据集五不可变字段 + 表 schema + 提示词）经用户确认后才执行写操作
- [ ] `list-datasets` 先搜索复用；新建/复用均 `get-dataset` 回读成功
- [ ] 工作流 JSON 结构自检全过（id/hop 一致、字段契约、环境值无占位串）
- [ ] `create-work-flow-by-json` 默认 `TaskType=3 + Submit=false`，返回 `Code: OK` + `Data.PipelineId`
- [ ] 输出界面回显 + 试跑验证指引
- [ ] `delete-dataset` 前已自查下游引用且逐次人工确认

### update-unstructured-workflow
- [ ] 修改建立在 `get-pipeline-by-id` 回读结果之上（基线 JSON 已保存），未凭记忆重建
- [ ] 变更设计稿（diff 摘要）经用户确认后才执行写操作
- [ ] 已有 step 的 UUID/stepId 未变；删 step 时关联 hops 已清理；环境值成组替换
- [ ] `update-pipeline` 默认 `--submit false` + `--pipeline-type 14`；先 `--cli-dry-run`；返回 `Code: OK`
- [ ] 更新后回读 diff 确认变更生效且未变更部分与基线一致

### create-dataset
- [ ] 设计稿（名称 + 五个不可变字段 + 表 schema）经用户确认后才执行写操作
- [ ] `list-datasets` 查重完成（命中一致配置则复用）
- [ ] `create-dataset` 返回 `Code: OK` + `DatasetId`；`get-dataset` 回读与设计稿逐项一致
- [ ] Milvus 时主键(INT64/VARCHAR)+向量字段齐备；向量列 Dimension 与 Embedding 算子一致
- [ ] `update-dataset` 携带回读的 FileId；`delete-dataset` 前已自查下游引用且逐次人工确认

### update-dataset-schema
- [ ] 变更设计稿（列 diff + ALTER SQL + 完整新 TableSchema）经用户确认；已自查下游工作流引用
- [ ] 顺序为：先即席查询 DDL（TaskStatus=SUCCESS）→ 后 update-dataset 提交完整列清单
- [ ] 回读目标版本 TableSchema 与物理表逐列一致
- [ ] 删列/改类型逐条人工确认（原则只加不减）

### create-standard / update-standard
- [ ] 标准属性值（标准编码/名称/数据类型等）写在 `--standard-template-reference.AttributeValueList`，**不得放进 `--standard-general-monitor-config`**
- [ ] `AttributeId` 先由 `get-standard-template --cli-query 'TemplateInfo.AttributesConfig.AttributeList[].{Id:Id,Code:Code,Required:Required}'` 取得，Required 属性全部给值
- [ ] 报 `RequiredAttributeValueIsBlank` 时不得在 monitor-config 内换字段名反复重试（同一错误码连续 2 次即停下报告）
- [ ] update 时 `AttributeValueList` 整体覆盖：先 `get-standard` 取现有值再合并

### manage-lookup-table
- [ ] create/update 必带码表名称 + 编码；码值元素 Value/Name 必填且 ≤64 字符、Value 码表内唯一
- [ ] update 前先 get 备份全量码值（覆盖语义防丢失）；写操作 HITL 二次确认
- [ ] 创建后 get-standard-lookup-table --nullable false 反查名称/编码/码值数一致

### manage-standard-mapping
- [ ] 建映射前确认标准已发布（已生效）；无效映射冲突策略显式与用户确认
- [ ] create 响应 SuccessCount 与入参 GUID 数一致，FailedGuidList 不为空时逐个报告原因
- [ ] get-asset-mapping-relations / get-belong-asset-mapping 反查命中；GUID 单次 ≤1000

# 新增迁移 Skill 验收标准

以下 skill 由 `dataphin-cli/skills/analyticscomputing` 迁移而来，已做如下适配：

1. **命令前缀**：`dataphin <module>` 统一改为 `aliyun dataphin-public`
2. **frontmatter**：精简为 `name` + `description`
3. **目录结构**：按业务域归入 `<module>/<sub-skill>`，子 skill 名去掉 `dataphin-` 前缀
4. **references**：补充 `cli-installation-guide.md`、`ram-policies.md`、`acceptance-criteria.md`、`related-commands.md`

## 通用正确模式

- ✅ 使用 `aliyun dataphin-public <verb-resource>` 插件模式命令
- ✅ 大整数 ID（19 位 snowflake）在 JSON 中按字符串传参
- ✅ 写操作前进行 HITL 确认
- ✅ 每个 `aliyun` API 命令携带 `--user-agent AlibabaCloud-Agent-Skills/{SkillName}/{session-id}`

## 通用错误模式

- ❌ 使用旧 `dataphin` 二进制命令
- ❌ 硬编码 tenant-id / project-id / AK/SK
- ❌ 遗漏 `--user-agent`
