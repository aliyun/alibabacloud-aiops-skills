# 相关命令（manage-kg-schema）

> **CLI 原生支持**：KG OpenAPI 已正式发布（Online version: v6.1.1）并注册到 `aliyun-cli-dataphin-public` 插件（>= 0.7.1），直接 `aliyun dataphin-public <cmd>` 调用。
>
> **能力边界**：KG Schema OpenAPI **仅提供整体 Schema 操作**，**没有**实体类型 / 关系类型的细粒度单类型 CRUD 命令（`create-kg-entity-type` / `update-kg-entity-type` 等均不存在）。类型 / 属性的增删改，统一通过「导出 YAML → 本地编辑 → 整体导入 → 发布」完成。

## Schema 管理（全部命令）

| 命令 | 用途 | 类型 | 必要性 |
|------|------|------|--------|
| `export-kg-schema` | 导出整体 Schema（YAML/JSON） | 读 | 必须（编辑基线 / 校验） |
| `import-kg-schema` | 导入整体 Schema（YAML/JSON） | 写（高危） | 必须 |
| `publish-kg-schema` | 发布 Schema（异步） | 写（高危） | 必须 |
| `get-kg-schema-publish-result` | 查询发布结果 | 读 | 必须 |

## 辅助脚本（仅旧环境兜底）

> 以下 SDK 脚本仅用于独立部署 < v6.1.1、KG OpenAPI 尚未发布的旧环境；新环境一律优先 CLI 原生命令。

| 脚本 | 封装的 API | 用途 |
|------|----------|------|
| `scripts/export-schema.py` | `ExportKgSchema` | **只读**导出 Schema YAML（侦察 / 取基线 / 变更后复验），支持 `--output` / `--quiet` / `--ignore-ssl` |
| `scripts/import-schema.py` | `ImportKgSchema` + `PublishKgSchema` + `GetKgSchemaPublishResult` | 端到端导入发布（预校验→导出基线→导入→验证→发布→轮询），**必定写远端** |

## 参数速查（CLI 标志）

公共入参（4 个命令均需）：`--op-tenant-id`（Integer，租户 ID）、`--workspace-id`（String，空间 ID）。

### export-kg-schema
- `--output-format`（可选）：`yaml`（默认）/ `json`
- `--version-id`（可选）：空或 `-1` 为草稿态；`0` 为最新已发布版本；正整数为指定版本
- 出参：`SchemaInfo.Content`（Schema 字符串）+ `SchemaInfo.OutputFormat`

### import-kg-schema
- `--import-command`（必填，JSON）：`{Content, InputFormat: yaml/json, MergeStrategy: Replace/Merge}`（注意字段名是 **InputFormat**，不是 Format）
- 出参：`ImportResult.EntityTypeCount` / `ImportResult.RelationTypeCount`

### publish-kg-schema
- `--publish-command`（必填，JSON）：`{Description（必填）, DataAdjustmentPolicies（可选）}`
- 出参：`Data.VersionId` + `Data.WorkspaceId`（**无 TaskId**，轮询用 VersionId）

### get-kg-schema-publish-result
- `--version-id`（可选）：留空返回最近一次发布记录
- 出参：`Data.Status`（Publishing/Published/Partial/Failed）+ `Data.VersionId` + `Data.Content`（发布日志）
