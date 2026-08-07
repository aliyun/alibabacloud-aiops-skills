# 验收标准（query-kg）

## 必检项

- [ ] CLI 插件 >= 0.7.1（`exec-kg-cypher --help` 可正常输出参数 schema）
- [ ] `exec-kg-cypher` 查询返回有效结果（`Data.RowList` 标量查询 或 `Data.NodeList`/`Data.EdgeList` 节点查询）
- [ ] `get-kg-neighbor` 返回邻居节点列表（`Data.NodeList`）和连接关系（`Data.EdgeList`）
- [ ] `exec-kg-cypher` 使用 `--exec-command` JSON 传入 `{Query, Limit}`
- [ ] `get-kg-neighbor` 传入 `--entity-data-id` + `--entity-type`（均必填），遍历控制用 `--neighbors-query`（方向字段 `DirectionType`）
- [ ] Cypher 查询仅包含只读语句（无 CREATE/MERGE/DELETE/SET）
- [ ] 查询结果含 LIMIT 限制
- [ ] 旧版本独立部署（< v6.1.1）时 SDK 兜底脚本 `scripts/query-kg.py` 可跑通

## 失败标准

- CLI 报 unknown command（插件未更新到 >= 0.7.1）
- API 返回 HTTP 4xx/5xx 错误
- `get-kg-neighbor` 返回 `DPN.Planning.KgEntityNotExists`（EntityType 不在最新发布版本中）
- `Dataphin.KG.GraphEngineConnectionFailed`（图引擎不可用）
