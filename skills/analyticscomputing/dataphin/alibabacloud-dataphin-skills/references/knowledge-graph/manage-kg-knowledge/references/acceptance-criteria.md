# 验收标准（manage-kg-knowledge）

## 功能验收

| 步骤 | 验收标准 |
|------|---------|
| 创建实体 | `create-kg-entity` 返回 `CreateResult.EntityId` |
| 批量创建实体 | `batch-create-kg-entity` 返回 SuccessCount > 0, FailCount = 0 |
| 查询实体详情 | `get-kg-entity` 返回 EntityInfo 含正确属性 |
| 列出实体 | `list-kg-entity` 返回 `PageResult.EntityList` 含创建的实体 |
| 创建关系 | `create-kg-relation` 返回 RelationId |
| 批量创建关系 | `batch-create-kg-relation` 返回 SuccessCount > 0 |
| Cypher 查询 | `exec-kg-cypher` 返回 `Data.RowList` / `Data.NodeList` 非空 |
| 邻居遍历 | `get-kg-neighbor` 返回 `Data.NodeList` 邻居节点 |

## 非功能验收

- [ ] SKILL.md 行数 <= 500
- [ ] 所有 CLI 命令为原生 kebab-case 且含 `--user-agent`
- [ ] CLI 插件版本 >= 0.7.1（KG 命令已注册）
- [ ] 写操作含 HITL 确认
- [ ] 高危操作（Delete 实体/关系）明确标注
- [ ] session-id 继承自父层
- [ ] 错误码覆盖 KG 业务错误码
- [ ] 前置依赖（manage-kg-schema）明确声明
