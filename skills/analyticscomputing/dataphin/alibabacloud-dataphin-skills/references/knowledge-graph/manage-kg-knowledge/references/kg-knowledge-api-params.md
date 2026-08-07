# KG Knowledge API 参数参考

> **CLI 原生支持**：KG OpenAPI 已正式发布（Online version: v6.1.1）并注册到 `aliyun-cli-dataphin-public` 插件（>= 0.7.1），直接 `aliyun dataphin-public <cmd>` 调用。以下参数基于 CLI `--help` schema 与实测环境（env19）双重验证。

## 公共入参

| 参数 | CLI 标志 | 类型 | 必填 | 说明 |
|------|---------|------|------|------|
| OpTenantId | `--op-tenant-id` | Integer | 是 | 租户 ID |
| WorkspaceId | `--workspace-id` | String | 是 | 空间 ID |

> **写操作请求体标志约定**：KG 写操作不使用通用 `--body`，而是对应的命令对象标志。完整映射见 §命令对象标志映射。

## 命令对象标志映射

| CLI 命令 | 请求体标志 |
|---|---|
| `create-kg-entity` | `--create-command` |
| `batch-create-kg-entity` | `--create-command` |
| `update-kg-entity` | `--update-command` |
| `create-kg-relation` | `--create-command` |
| `batch-create-kg-relation` | `--create-command` |
| `update-kg-relation` | `--update-command` |
| `exec-kg-cypher` | `--exec-command` |

---

## PropertyListItem（通用属性键值对）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Code | String | 是 | 属性编码（须匹配 Schema 定义） |
| Value | String | 是 | 属性值（统一按字符串传入） |

---

## CreateKgEntity（`create-kg-entity`）

**请求体（`--create-command` JSON）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| EntityType | String | 是 | 实体类型编码 |
| PropertyList | Array<PropertyListItem> | 是 | 属性键值对列表 |

**出参：** `CreateResult.EntityId`（实测为 UUID 字符串）

---

## UpdateKgEntity（`update-kg-entity`）

**请求体（`--update-command` JSON）：** `{EntityId, EntityType, PropertyList}`（完整属性列表替换）

**出参：** 无，以 `Success` 判断。

---

## DeleteKgEntity（`delete-kg-entity`）

**额外入参：** `--entity-type "{code}"` `--entity-id "{id}"`（均必填），无请求体。

**出参：** 无，以 `Success` 判断。

---

## GetKgEntity（`get-kg-entity`）

**额外入参：** `--entity-type "{code}"` `--entity-id "{id}"`（均必填）

**出参：** `EntityInfo` 对象，含 EntityId、EntityType、PropertyList（Code/Value/DataType）

---

## ListKgEntity（`list-kg-entity`）

**额外入参：** `--entity-type "{code}"`（必填）

**请求体（`--list-query` JSON，可选）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Keyword | String | 否 | 搜索关键词（仅匹配 Indexed=true 的属性，模糊匹配） |
| FilterList | Array | 否 | 属性过滤条件 |
| PageNum | Integer | 否 | 页码，默认 1 |
| PageSize | Integer | 否 | 每页条数，默认 20 |

**PropertyFilterItem（FilterList 元素）：**

| 参数 | 类型 | 说明 |
|------|------|------|
| PropertyCode | String | 属性编码 |
| Op | String | 操作符：`eq`/`neq`/`contains`/`gt`/`gte`/`lt`/`lte`/`like` |
| Value | String | 过滤值 |

**出参（实测）：**
- `PageResult.TotalCount`：总记录数
- `PageResult.EntityList[]`：实体数组（含 `EntityId`、`EntityType`、`PropertyList[].{Code, DataType, Value}`）

---

## BatchCreateKgEntity（`batch-create-kg-entity`）

**请求体（`--create-command` JSON）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| EntityList | Array | 是 | 实体列表，每项含 EntityType + PropertyList |

**出参：**
- `CreateResult.SuccessCount`：成功数量
- `CreateResult.FailCount`：失败数量
- `CreateResult.SuccessEntityList[]`：成功列表（仅含 EntityType + EntityId，不含 PropertyList）

---

## CreateKgRelation（`create-kg-relation`）

**请求体（`--create-command` JSON）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| RelationType | String | 是 | 关系类型编码 |
| SourceEntityId | String | 是 | 起始实体 ID |
| TargetEntityId | String | 是 | 目标实体 ID |
| PropertyList | Array<PropertyListItem> | 是 | 关系属性键值对 |

**出参：** `CreateResult.RelationId`

---

## UpdateKgRelation（`update-kg-relation`）

**请求体（`--update-command` JSON）：** `{RelationId, RelationType, PropertyList}`（完整替换）

---

## DeleteKgRelation（`delete-kg-relation`）

**额外入参：** `--relation-type "{code}"` `--relation-id "{id}"`（均必填），无请求体。

---

## GetKgRelation（`get-kg-relation`）

**额外入参：** `--relation-type "{code}"` `--relation-id "{id}"`（均必填）

**出参：** `RelationInfo` 对象，含 RelationId、RelationType、SourceEntityId、TargetEntityId、PropertyList

---

## ListKgRelation（`list-kg-relation`）

**额外入参：** `--relation-type "{code}"`（必填）

**请求体（`--list-query` JSON，可选）：**

| 参数 | 类型 | 说明 |
|------|------|------|
| SourceEntityId | String | 起始实体 ID 筛选 |
| TargetEntityId | String | 目标实体 ID 筛选 |
| PageNum / PageSize | Integer | 分页 |

**出参：**
- `PageResult.TotalCount`：总数
- `PageResult.RelationList[]`：关系数组（含 RelationId、SourceEntityId、TargetEntityId、RelationType、PropertyList）

---

## BatchCreateKgRelation（`batch-create-kg-relation`）

**请求体（`--create-command` JSON）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| RelationList | Array | 是 | 关系列表，每项含 RelationType + SourceEntityId + TargetEntityId + PropertyList |

**出参：**
- `CreateResult.SuccessCount` / `CreateResult.FailCount`
- `CreateResult.SuccessRelationList[]`（含 RelationType + RelationId）

---

## ExecKgCypher（`exec-kg-cypher`）

**请求体（`--exec-command` JSON）：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Query | String | 是 | Cypher 查询语句 |
| Params | Array | 否 | 查询参数，元素为 `{DataType, Key, Value}` |
| Limit | Integer | 否 | 返回条数上限，默认 100 |

> 仅支持查询数据，不支持修改及写入知识图谱。

**出参（实测，均在 `Data` 下）：**
- `Data.RowList[]`：表格结果行（如聚合查询）
- `Data.NodeList[]` / `Data.EdgeList[]`：图结构结果（返回节点/边时）

> **⚠️ 实测已知问题**：`RETURN n` 返回整节点时，节点的 `DataId` 可能为 null。需要实体 ID 时改用 `list-kg-entity` 或在 Cypher 中 RETURN 具体属性。

---

## GetKgNeighbor（`get-kg-neighbor`）

**额外入参：**

| CLI 标志 | 类型 | 必填 | 说明 |
|---------|------|------|------|
| `--entity-data-id` | String | 是 | 实体记录 ID |
| `--entity-type` | String | 是 | 实体类型编码 |
| `--neighbors-query` | Object | 否 | 遍历控制（JSON） |

**`--neighbors-query` 结构：**

| 字段 | 类型 | 说明 |
|------|------|------|
| Depth | Integer | 扩展深度，默认 1 |
| DirectionType | String | `In`/`Out`/`Both`，默认 Both（注意字段名是 **DirectionType**，不是 Direction） |
| RelationTypes | Array<String> | 关系类型编码列表 |

**出参（实测，均在 `Data` 下）：**
- `Data.NodeList[]`：邻居节点列表
- `Data.EdgeList[]`：连接关系列表

---

## 业务错误码

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `Dataphin.KG.InvalidParameter` | 400 | 请求参数无效 |
| `Dataphin.KG.EntityTypeNotFound` | 404 | 实体类型不存在（Schema 未发布） |
| `Dataphin.KG.RelationTypeNotFound` | 404 | 关系类型不存在 |
| `Dataphin.KG.EntityNotFound` | 404 | 实体不存在 |
| `Dataphin.KG.RelationNotFound` | 404 | 关系不存在 |
| `Dataphin.KG.ValidationFailed` | 400 | 验证规则校验失败（属性不匹配 Schema） |
| `Dataphin.KG.DataConflict` | 409 | 数据冲突 |
| `Dataphin.KG.GraphEngineConnectionFailed` | 500 | 图引擎连接失败 |
| `Dataphin.KG.GraphEngineExecutionFailed` | 500 | 图引擎执行失败 |
