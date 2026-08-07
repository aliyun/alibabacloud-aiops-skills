# KG Schema API 参数参考

> **CLI 原生支持**：KG OpenAPI 已正式发布（Online version: v6.1.1）并注册到 `aliyun-cli-dataphin-public` 插件（>= 0.7.1），直接 `aliyun dataphin-public <cmd>` 调用。以下参数基于 CLI `--help` schema 与实测环境（env19）双重验证。

## 公共入参

| 参数 | CLI 标志 | 类型 | 必填 | 说明 |
|------|---------|------|------|------|
| OpTenantId | `--op-tenant-id` | Integer | 是 | 租户 ID |
| WorkspaceId | `--workspace-id` | String | 是 | 空间 ID |

> **能力边界**：KG Schema OpenAPI 仅提供整体 Schema 操作（`export-kg-schema` / `import-kg-schema` / `publish-kg-schema` / `get-kg-schema-publish-result`），**无**实体类型 / 关系类型的细粒度单类型 CRUD API。类型 / 属性的增删改均通过编辑 YAML 后 `import-kg-schema` 整体导入。

---

## ExportKgSchema（`export-kg-schema`）

**额外入参：**
- `--output-format`（可选）：`yaml`（默认）/ `json`
- `--version-id`（可选）：空或 `-1` 返回草稿态；`0` 返回最新已发布版本；正整数返回指定版本

**出参：** `SchemaInfo.Content`（Schema 字符串）+ `SchemaInfo.OutputFormat`（注意：不是 `ExportKgSchemaResult.*`，也不是 `Data.SchemaContent`）

---

## ImportKgSchema（`import-kg-schema`）

**请求体（`--import-command` JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Content | String | 是 | Schema YAML/JSON 内容 |
| InputFormat | String | 是 | `yaml` / `json`（注意字段名是 **`InputFormat`**，不是 `Format`） |
| MergeStrategy | String | 否 | `Replace`（替换）/ `Merge`（合并），默认 Replace |

**YAML Schema 字段说明：**

*顶层：*

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | String | 否 | 空间名称（人工识别） |
| description | String | 否 | 描述 |
| workspaceId | String | 否 | 空间 ID（不参与写入逻辑） |
| entityTypes | List | 条件必填 | 实体类型列表 |
| relationTypes | List | 条件必填 | 关系类型列表 |

*实体类型（entityTypes 元素）：*

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | String | 是 | 大写字母开头，仅含大写字母/数字/下划线 |
| name | String | 是 | 显示名称 |
| description | String | 否 | 描述 |
| useSysPk | Boolean | 否 | `true`=系统主键，`false`=业务主键（默认） |
| icon | String | 否 | 图标标识符 |
| properties | List | 是 | 属性列表 |

*关系类型（relationTypes 元素）：*

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | String | 是 | 关系编码 |
| name | String | 是 | 关系名称 |
| sourceEntityCode | String | 是 | 起始实体类型编码 |
| targetEntityCode | String | 是 | 目标实体类型编码 |
| hasDirection | Boolean | 否 | 是否有向（默认 true） |
| cardinalType | String | 否 | `MULTI_TO_MULTI`/`ONE_TO_MANY`/`ONE_TO_ONE` |
| properties | List | 否 | 关系属性列表 |

*属性定义（properties 元素）：*

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | String | 是 | 小写字母开头，仅含小写字母/数字/下划线 |
| name | String | 是 | 属性显示名称 |
| dataType | String | 是 | 全大写：`STRING`/`INTEGER`/`FLOAT`/`BOOLEAN`/`DATE`/`TIMESTAMP`/`DECIMAL` |
| isPrimaryKey | Boolean | 否 | 是否主键，默认 false。每实体至少一个（useSysPk=false 时） |
| isRequired | Boolean | 否 | 是否必填，默认 false |
| isIndexed | Boolean | 否 | 是否索引，默认 false |
| isUsedShow | Boolean | 否 | **是否用于展示**，每实体至少一个 true |
| defaultValue | Any | 否 | 默认值，无默认值时传空字符串 `''` |

**合并策略说明：**
- **Replace**：完整替换草稿模型，导入中无而空间中有的类型会被删除
- **Merge**：增量合并，导入中无的类型保留不动；同名类型合并
- 以编码（Code）判定同一类型；不兼容冲突返回 `Dataphin.KG.SchemaConflict`

**出参：** `ImportResult.EntityTypeCount` + `ImportResult.RelationTypeCount`（实测键名是 `ImportResult`，不是 `ImportKgSchemaResult`）

---

## PublishKgSchema（`publish-kg-schema`）

**请求体（`--publish-command` JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Description | String | 是 | 发布备注（0-1000 字符） |
| DataAdjustmentPolicies | Array | 否 | 破坏性变更数据调整策略 |

**DataAdjustmentPolicy（CLI schema）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| PolicyType | String | 策略类型（如 `BackfillDefault`） |
| Type | String | 受影响对象类型 |
| TypeCode | String | 受影响的类型编码 |
| BackFillDefaultValuePolicy | Object | `{DefaultValue, PropertyCode}` 回填默认值策略 |

**出参：** `Data.VersionId`（预期发布后的最新模型版本号）+ `Data.WorkspaceId`。**无 TaskId**，轮询发布结果用 VersionId。

---

## GetKgSchemaPublishResult（`get-kg-schema-publish-result`）

**额外入参：** `--version-id`（可选，留空返回最近一次发布记录）

**出参字段（实测，均在 `Data` 下）：**

| 字段 | 说明 |
|------|------|
| Data.Status | `Publishing`/`Published`/`Partial`/`Failed` |
| Data.VersionId | 版本号 |
| Data.Content | 发布过程日志（含各阶段时间戳、校验与类型处理结果；失败时含失败原因） |

---

## 业务错误码

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `Dataphin.KG.InvalidParameter` | 400 | 请求参数无效 |
| `Dataphin.KG.EntityTypeNameExists` | 400 | 实体类型名称已存在 |
| `Dataphin.KG.RelationTypeNameExists` | 400 | 关系类型名称已存在 |
| `Dataphin.KG.CodeFormatInvalid` | 400 | 编码格式不合法 |
| `Dataphin.KG.CodeAlreadyUsed` | 400 | 编码已被使用 |
| `Dataphin.KG.ValidationFailed` | 400 | 验证规则校验失败 |
| `Dataphin.KG.NoPermission` | 403 | 无操作权限 |
| `Dataphin.KG.WorkspaceNotFound` | 404 | 空间不存在 |
| `Dataphin.KG.EntityTypeNotFound` | 404 | 实体类型不存在 |
| `Dataphin.KG.RelationTypeNotFound` | 404 | 关系类型不存在 |
| `Dataphin.KG.DataConflict` | 409 | 存在数据冲突 |
| `Dataphin.KG.PublishValidationFailed` | 400 | 发布校验失败 |
| `Dataphin.KG.BreakingChangeUnhandled` | 409 | 存在破坏性变更未处理 |
| `Dataphin.KG.NoDraftChanges` | 409 | 草稿无变更 |
| `Dataphin.KG.PublishInProgress` | 409 | 已有发布任务进行中 |
