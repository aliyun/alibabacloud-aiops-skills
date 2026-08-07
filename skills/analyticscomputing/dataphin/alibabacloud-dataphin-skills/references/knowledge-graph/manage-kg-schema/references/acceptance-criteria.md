# 验收标准（manage-kg-schema）

## 功能验收

| 步骤 | 验收标准 |
|------|---------|
| 导出 Schema（基线） | `export-kg-schema` 返回 `SchemaInfo.Content`（YAML 字符串） |
| 导入 Schema | `import-kg-schema` 返回 `ImportResult.EntityTypeCount` / `RelationTypeCount` |
| 发布 Schema | `publish-kg-schema` 返回 `Data.VersionId`（无 TaskId） |
| 查询发布结果 | `get-kg-schema-publish-result` 返回 `Data.Status: Published` |
| 变更生效 | 再次 `export-kg-schema` 的 `SchemaInfo.Content` 含本次增删改后的类型/属性 |

> **能力边界**：KG Schema OpenAPI 仅支持整体 Schema 操作（Export/Import/Publish），无实体类型/关系类型的细粒度 CRUD；类型级增删改通过编辑 YAML 后整体导入验证。

## 非功能验收

- [ ] SKILL.md 行数 <= 500
- [ ] 所有 CLI 命令为原生 kebab-case 且含 `--user-agent`
- [ ] CLI 插件版本 >= 0.7.1（KG 命令已注册）
- [ ] 写操作含 HITL 确认
- [ ] 高危操作（Delete/Import/Publish）明确标注
- [ ] session-id 继承自父层
- [ ] 错误码覆盖 KG 业务错误码
