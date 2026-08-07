# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`（kebab-case）
- 查询列表命令为 `list-row-permission`（单数 permission），不是 `list-row-permissions`
- 按表查询命令为 `get-row-permission-by-table-guids`
- 查询授权账号命令为 `get-account-by-row-permission-id`

### 2. 参数确认与 HITL
- 所有用户自定义参数执行前需用户确认
- 写操作（create / update / delete）执行前必须 HITL 二次确认
- 不硬编码 tenant-id、row-permission-id、table-guid、project-id、datasource-id 等业务参数
- 大整数 ID 一律字符串传参（引号包住）

### 3. 必填参数完整
- create 必带 `--tenant-id`、`--row-permission-name`、`--mapping-columns`
- update 必带 `--tenant-id`、`--row-permission-id`、`--row-permission-name`、`--mapping-columns`
- delete 必带 `--tenant-id`、`--row-permission-id`
- list 必带 `--tenant-id`、`--page-num`、`--page-size`
- get-account 必带 `--row-permission-id` 与 `--rule-ids`

### 4. 复杂字段结构正确
- `--mapping-columns`、`--rules`、`--tables` 使用 CLI list 参数：每个数组元素一个 JSON 对象字符串
- 不把整个 JSON 数组字符串作为一个 list 元素传入
- JSON 对象字段使用 OpenAPI PascalCase，如 `ColumnName`、`RuleName`、`ScopeType`、`UserMappingList`
- `Tables` 至少包含表 GUID、表名、资源类型；真实创建建议包含项目、数据源、业务板块和管控字段完整元数据
- 规则表达式支持 `IN` / `LIKE` / `EQUAL`，条件结构必须包含 `ColumnId`、`Operator`、`Values`

### 5. 端到端校验
- create 返回成功后，必须 `list-row-permission --keyword` 反查 `rowPermissionId`
- create/update 后通过 `get-row-permission-by-table-guids` 验证表绑定关系
- 需要确认授权账号时通过 `get-account-by-row-permission-id` 查询规则账号映射
- delete 后通过 list 或 get-by-table 反查目标不存在
- 若验证运行时过滤效果，需另走授权申请/审批/实际 SQL 查询链路，不能仅凭 create/update 判定已生效

### 6. Observability
- 所有调用 API 的 `aliyun` 命令携带 `--user-agent AlibabaCloud-Agent-Skills/manage-row-level-permission/{session-id}`
- session-id 继承父 skill，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/table/project/datasource ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ create 后直接假设响应里有 `rowPermissionId`
- ❌ update 只传要改的规则，导致 `mappingColumns`、`tables` 或已有规则被覆盖清空
- ❌ 将页面内部 camelCase 字段原样用于 OpenAPI JSON，导致字段不生效
- ❌ 混淆 `PERSONAL` 个人账号与 `PRODUCE` 生产账号的授权语义
- ❌ 仅以 OpenAPI create/update 成功断言运行时查询已过滤，不做实际查询或授权验证
