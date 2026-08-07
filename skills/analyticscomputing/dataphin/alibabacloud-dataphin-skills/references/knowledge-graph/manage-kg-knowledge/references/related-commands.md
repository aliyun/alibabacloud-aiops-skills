# 相关命令索引（manage-kg-knowledge）

> **CLI 原生支持**：KG OpenAPI 已正式发布（Online version: v6.1.1）并注册到 `aliyun-cli-dataphin-public` 插件（>= 0.7.1），直接 `aliyun dataphin-public <cmd>` 调用。

## 实体管理

| 命令 | 用途 | 类型 | 必要性 |
|------|------|------|--------|
| `create-kg-entity` | 创建实体 | 写 | 必须 |
| `update-kg-entity` | 更新实体 | 写 | 按需 |
| `delete-kg-entity` | 删除实体 | 写（高危） | 按需 |
| `get-kg-entity` | 获取实体详情 | 读 | 按需 |
| `list-kg-entity` | 获取实体列表（搜索/过滤/分页） | 读 | 必须 |
| `batch-create-kg-entity` | 批量创建实体 | 写 | 按需 |

## 关系管理

| 命令 | 用途 | 类型 | 必要性 |
|------|------|------|--------|
| `create-kg-relation` | 创建关系 | 写 | 必须 |
| `update-kg-relation` | 更新关系 | 写 | 按需 |
| `delete-kg-relation` | 删除关系 | 写（高危） | 按需 |
| `get-kg-relation` | 获取关系详情 | 读 | 按需 |
| `list-kg-relation` | 获取关系列表 | 读 | 按需 |
| `batch-create-kg-relation` | 批量创建关系 | 写 | 按需 |

## 图查询

| 命令 | 用途 | 类型 | 必要性 |
|------|------|------|--------|
| `exec-kg-cypher` | 执行 Cypher 查询（只读） | 读 | 按需 |
| `get-kg-neighbor` | 获取邻居节点 | 读 | 按需 |

## 参数速查（CLI 标志）

公共入参（所有命令均需）：`--op-tenant-id`（Integer，租户 ID）、`--workspace-id`（String，空间 ID）。

### create-kg-entity
- `--create-command`（必填，JSON）：`{EntityType, PropertyList: [{Code, Value}, ...]}`
- 出参：`CreateResult.EntityId`

### batch-create-kg-entity
- `--create-command`（必填，JSON）：`{EntityList: [{EntityType, PropertyList}, ...]}`
- 出参：`CreateResult.{SuccessCount, FailCount, SuccessEntityList}`

### list-kg-entity
- `--entity-type`（必填）
- `--list-query`（可选，JSON）：`{Keyword, FilterList: [{PropertyCode, Op, Value}], PageNum, PageSize}`
- 出参：`PageResult.EntityList` + `PageResult.TotalCount`

### create-kg-relation
- `--create-command`（必填，JSON）：`{RelationType, SourceEntityId, TargetEntityId, PropertyList}`
- 出参：`CreateResult.RelationId`

### list-kg-relation
- `--relation-type`（必填）
- `--list-query`（可选，JSON）：`{SourceEntityId, TargetEntityId, PageNum, PageSize}`

### exec-kg-cypher
- `--exec-command`（必填，JSON）：`{Query, Limit（默认 100）, Params: [{DataType, Key, Value}]}`
- 出参：`Data.RowList` / `Data.NodeList` / `Data.EdgeList`

### get-kg-neighbor
- `--entity-data-id`（必填）：实体记录 ID
- `--entity-type`（必填）：实体类型编码
- `--neighbors-query`（可选，JSON）：`{Depth（默认 1）, DirectionType: In/Out/Both（默认 Both）, RelationTypes: [...]}`
- 出参：`Data.NodeList` + `Data.EdgeList`
