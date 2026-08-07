# KG Query API 参数参考

> **CLI 原生支持**：KG OpenAPI 已正式发布（Online version: v6.1.1）并注册到 `aliyun-cli-dataphin-public` 插件（>= 0.7.1），推荐直接使用 CLI 命令。以下参数名和响应结构基于 CLI `--help` schema 与实测环境（env19）双重验证。

## 公共入参

| 参数 | CLI 标志 | 类型 | 必填 | 说明 |
|------|---------|------|------|------|
| OpTenantId | `--op-tenant-id` | Integer | 是 | 租户 ID |
| WorkspaceId | `--workspace-id` | String | 是 | 空间 ID |

---

## ExecKgCypher（`exec-kg-cypher`）

**调用方式**：`aliyun dataphin-public exec-kg-cypher`

**`--exec-command` JSON 对象结构：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Query | String | 是 | Cypher 查询语句 |
| Limit | Integer | 否 | 返回条数上限，默认 100 |
| Params | Array<{DataType, Key, Value}> | 否 | 参数化查询参数列表 |

```bash
aliyun dataphin-public exec-kg-cypher \
  --op-tenant-id "{OpTenantId}" --workspace-id "{WorkspaceId}" \
  --exec-command '{"Query": "MATCH (n:Drug) RETURN n.product_name LIMIT 10", "Limit": 100}'
```

> **限制**：仅支持查询数据，不支持 `CREATE`、`MERGE`、`DELETE`、`SET` 等写入/修改语句。
> **SDK 兜底**（独立部署 < v6.1.1）：Tea SDK `call_api()` 泛化调用时 formData 参数名是 **`ExecCommand`**（不是文档中的 `ExecKgCypherCommand`），且需 POST 方法。

**实际响应结构（实测）：**

```json
{
  "Code": "OK",
  "Data": {
    "NodeList": [
      {
        "DataId": "0a259156-d9f9-4bc1-be44-9b942a0b0e1a",
        "EntityType": "Drug",
        "Properties": [{"Code": "drug_code", "Value": "D002"}, ...]
      }
    ],
    "EdgeList": [
      {
        "RelationId": "...",
        "SourceEntityId": "...",
        "TargetEntityId": "...",
        "RelationType": "COMPETES_WITH",
        "PropertyList": [{"Code": "...", "Value": "...", "DataType": "..."}]
      }
    ],
    "RowList": [
      {
        "Columns": [
          {"Code": "type", "Value": "[\"Drug\"]"},
          {"Code": "cnt", "Value": "25"}
        ]
      }
    ],
    "ExecuteCypher": "MATCH (n:Drug) ..."
  },
  "RequestId": "...",
  "Success": true
}
```

**字段说明：**

| 字段 | 说明 |
|------|------|
| `Data.NodeList[]` | 匹配到的节点（`RETURN n` 时返回），含 `DataId`、`EntityType`、`Properties[].Code/Value` |
| `Data.EdgeList[]` | 匹配到的边（`RETURN r` 时返回），含 `RelationId`、`RelationType`、`SourceEntityId`、`TargetEntityId` |
| `Data.RowList[].Columns[].Code/Value` | RETURN 子句的标量值（如 `RETURN n.name, count(*)`） |
| `Data.ExecuteCypher` | 实际执行的 Cypher 语句 |

> **DataId vs EntityId**：`NodeList[].DataId` 是实体的唯一标识（UUID 格式），用于 GetKgNeighbor 的 `EntityDataId` 参数。与 Cypher 的 `id(n)` 函数返回的内部整数 ID 不同。

**Cypher 语法要点：**

| 语法 | 说明 |
|------|------|
| `MATCH (n:Type)` | 匹配指定类型节点 |
| `-[r:RELATION]->` | 匹配有向关系 |
| `WHERE n.prop = 'value'` | 属性过滤 |
| `RETURN n.prop, count(*)` | 返回列 + 聚合 |
| `LIMIT N` | 限制返回数 |
| `ORDER BY n.prop DESC` | 排序 |
| `[*1..3]` | 可变长路径（1~3 跳） |

---

## GetKgNeighbor（`get-kg-neighbor`）

**调用方式**：`aliyun dataphin-public get-kg-neighbor`

**入参：**

| 参数 | CLI 标志 | 类型 | 必填 | 说明 |
|------|---------|------|------|------|
| EntityDataId | `--entity-data-id` | String | **是** | 起始实体 DataId（从 exec-kg-cypher 的 `NodeList[].DataId` 或 list-kg-entity 的 `EntityList[].EntityId` 获取） |
| EntityType | `--entity-type` | String | **是** | 起始实体类型（如 `Drug`、`Disease`） |
| NeighborsQuery | `--neighbors-query` | Object | 否 | 遍历指令 JSON：`{Depth: integer, DirectionType: string, RelationTypes: [string, ...]}` |

**`--neighbors-query` JSON 对象结构：**

| 字段 | 类型 | 可选值 | 说明 |
|------|------|--------|------|
| DirectionType | String | `In` / `Out` / `Both` | 遍历方向，默认 Both（注意字段名**不是** `Direction`） |
| Depth | Integer | 1~N | 扩展深度，默认 1 |
| RelationTypes | Array\<String\> | 关系类型编码数组 | 仅遍历指定关系类型 |

```bash
aliyun dataphin-public get-kg-neighbor \
  --op-tenant-id "{OpTenantId}" --workspace-id "{WorkspaceId}" \
  --entity-data-id "{DataId}" --entity-type "Drug" \
  --neighbors-query '{"Depth": 1, "DirectionType": "Both"}'
```

> **SDK 兜底**（独立部署 < v6.1.1）：Tea SDK `call_api()` 泛化调用时 query 参数名是 **`EntityDataId`**（不是文档中的 `EntityId`）、`EntityType` 必填、需 POST 方法（GET 返回 `Forbidden Request Method: GET`）；遍历参数以平铺 query 传入（`Direction`/`Depth`/`RelationTypes`）。

**实际响应结构（实测）：**

```json
{
  "Code": "OK",
  "Data": {
    "NodeList": [
      {
        "EntityId": "0a259156-d9f9-4bc1-be44-9b942a0b0e1a",
        "EntityType": "Drug",
        "PropertyList": [
          {"Code": "drug_code", "Value": "D002", "DataType": "STRING"},
          {"Code": "product_name", "Value": "益赛拓", "DataType": "STRING"}
        ]
      }
    ],
    "EdgeList": [
      {
        "RelationId": "fdd70da9-...",
        "SourceEntityId": "0a259156-...",
        "TargetEntityId": "98ae32f5-...",
        "RelationType": "TREATS",
        "PropertyList": [
          {"Code": "approval_status", "Value": "已批准", "DataType": "STRING"}
        ]
      }
    ]
  }
}
```

**字段说明：**

| 字段 | 说明 |
|------|------|
| `Data.NodeList[]` | 邻居节点（含起始节点自身），`EntityId`/`EntityType`/`PropertyList[].Code/Value/DataType` |
| `Data.EdgeList[]` | 连接关系，含 `RelationId`/`RelationType`/`SourceEntityId`/`TargetEntityId`/`PropertyList[]` |

---

## 业务错误码

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `Dataphin.KG.InvalidParameter` | 400 | 请求参数无效（如 Cypher 语法错误） |
| `Dataphin.KG.EntityNotFound` | 404 | 实体不存在（GetKgNeighbor 的 EntityDataId 无效） |
| `Dataphin.KG.ValidationFailed` | 400 | 验证规则校验失败 |
| `Dataphin.KG.GraphEngineConnectionFailed` | 500 | 图引擎连接失败（Schema 未发布到图引擎） |
| `Dataphin.KG.GraphEngineExecutionFailed` | 500 | 图引擎执行失败（查询超时或资源不足） |
| `Dataphin.KG.NoPermission` | 403 | 无查询权限 |
| `Dataphin.KG.WorkspaceNotFound` | 404 | 空间不存在 |
| `DPN.Planning.KgEntityNotExists` | 400 | 实体类型不存在于最新发布版本（GetKgNeighbor 的 EntityType 无效） |
