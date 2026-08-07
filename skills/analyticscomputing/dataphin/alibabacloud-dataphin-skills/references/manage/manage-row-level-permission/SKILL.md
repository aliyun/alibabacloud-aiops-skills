---
name: manage-row-level-permission
description: |-
  管理 Dataphin 行级权限的查询、创建、更新、删除、按表查询、按用户查询和授权账号查询。
  当用户要按字段值控制表数据行可见范围，维护行级权限规则、管控列、关联表、规则授权账号，或排查某张表/某个用户拥有哪些行级权限时进入。
  触发词：行级权限、行权限、row permission、row-level permission、按行过滤、管控规则、规则授权账号、受影响账号、数据行可见范围。
  关键限制：create 返回 true 不返回 ID，需 list 反查；复杂数组参数每个元素传 JSON 对象字符串；update 需完整回填 mappingColumns/rules/tables；写操作需 HITL 确认。
---

# 行级权限管理 Skill

## 1. Scenario Description

在 Dataphin 平台管理 / 数据权限中对「行级权限（Row-Level Permission）」做生命周期管理。行级权限用于根据表字段值控制数据行可见范围，例如只允许某些用户查看 `region='华东'` 的订单，或只允许生产账号读取满足特定管控规则的数据行。

本 Skill 覆盖 `dataphin-public` 已开放的行级权限 OpenAPI：创建、更新、删除、分页查询、按表 GUID 查询、按用户查询，以及按行级权限 ID 查询授权账号。行级权限本身不单独提供“发布/上线/下线”命令；权限生效通常与规则配置、授权申请、审批和缓存同步相关。

**Architecture**：`Dataphin Tenant → Project / DataSource / Physical Table → Mapping Columns → Row Permission Rules → User/Produce Account Authorization → Query/DataService/Task Runtime Filtering`

### 涉及 Dataphin OpenAPI

- `CreateRowPermission` — 创建行级权限
- `UpdateRowPermission` — 更新行级权限与规则
- `DeleteRowPermission` — 删除行级权限
- `ListRowPermission` — 分页查询行级权限
- `GetRowPermissionByTableGuids` — 按表 GUID 查询行级权限
- `GetAccountByRowPermissionId` — 查询某个行级权限规则下的授权账号
- `ListRowPermissionByUserId` — 查询指定用户拥有的行级权限

## 2. Installation

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```

各操作系统一键安装脚本与版本要求详见 [references/cli-installation-guide.md](references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** 读取、回显或打印凭证环境变量（禁止对 AccessKey ID / Secret 做任何输出或日志）
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

**Pre-check: Aliyun CLI >= 3.4.8 required**
> Run `aliyun version` to verify >= 3.4.8. If not installed or version too low, install/update from https://aliyuncli.alicdn.com (see [references/cli-installation-guide.md](references/cli-installation-guide.md) for the OS-specific script).

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [../../ram-policies.md](../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

执行任何写操作（create / update / delete）前必须向用户确认以下参数，禁止静默提交：

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--tenant-id` | 是 | 租户 ID（大整数，**字符串传**） | — |
| `--row-permission-id` | update/delete/get-account 必填 | 行级权限 ID；create 返回 true 后需 list 反查 | — |
| `--row-permission-name` | create/update 必填 | 行级权限名称 | — |
| `--row-permission-desc` | 可选 | 行级权限描述 | — |
| `--mapping-columns` | create/update 必填 | 管控/映射字段列表；每个元素传一个 JSON 对象字符串 | — |
| `--rules` | create/update 可选 | 行级权限规则列表；每个元素传一个 JSON 对象字符串 | — |
| `--tables` | create/update 可选 | 关联表列表；每个元素传一个 JSON 对象字符串 | — |
| `--keyword` | list 可选 | 分页查询关键字 | — |
| `--page-num` | list/list-by-user 必填 | 分页页码 | `1` |
| `--page-size` | list/list-by-user 必填 | 分页大小 | `10` |
| `--table-guids` | get-by-table 必填 | 表 GUID 列表，CLI list 参数用空格分隔多个值 | — |
| `--rule-ids` | get-account 必填 | 行级权限规则 ID 列表，CLI list 参数用空格分隔多个值 | — |
| `--operator` | list-by-user 必填 | 指定操作人/用户 ID 或账号 | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-row-level-permission/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public list-row-permission --tenant-id "1234567890123456789" \
  --page-num 1 --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/manage-row-level-permission/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/manage-row-level-permission/$SESSION_ID"

# 0) 前置：确认目标物理表、表 GUID、管控字段、项目、业务板块、数据源等元数据已存在。
#    行级权限 create/update 不是只传表名即可，tables 需要完整资源元数据。

# 1) 分页查询行级权限（创建前查重，创建后反查 ID）
aliyun dataphin-public list-row-permission --tenant-id "$TENANT_ID" \
  --keyword "<行级权限名称关键字>" \
  --page-num 1 --page-size 10 \
  --user-agent "$UA" --format json

# 2) 创建行级权限。复杂数组参数每个元素传一个 JSON 对象字符串；CLI 会组装成数组。
aliyun dataphin-public create-row-permission --tenant-id "$TENANT_ID" \
  --row-permission-name "<行级权限名称>" \
  --row-permission-desc "<描述>" \
  --mapping-columns '{"ColumnName":"<字段名>","ColumnType":"<字段类型>","ColumnId":"<字段ID>","ColumnDesc":""}' \
  --rules '{"RuleName":"<规则名>","ScopeType":"ALL_COLUMN","Expressions":[],"UserMappingList":[],"Status":1,"IsDelete":false}' \
  --tables '{"ResourceId":"<表GUID>","ResourceName":"<表名>","ResourceType":"PHYSICAL_TABLE","ResourceEnv":"DEV","ResourceBizUnit":{"BizUnitId":"<数据板块ID>","BizUnitName":"<数据板块名>","BizUnitEnv":"dev"},"ResourceProject":{"ProjectId":"<项目ID>","ProjectName":"<项目名>","ProjectEnv":"dev"},"ResourceDatasource":{"DatasourceId":"<数据源ID>","DatasourceEnv":"dev","DatasourceType":"MAX_COMPUTE","DatasourceTypeAlias":"MaxCompute"},"ResourceProperties":{"AuthResourceKey":"<项目ID>.<表名>","StorageType":"MAX_COMPUTE"},"ControlColumnList":[{"ColumnId":"<字段ID>","ColumnName":"<字段名>","ColumnConfigItem":{"ColumnName":"<字段名>","ColumnType":"<字段类型>","ColumnDesc":"","ColumnId":"<字段ID>"},"SelectColumns":[]}],"ColumnName":"<字段名>","MappingColumnId":"<字段ID>"}' \
  --user-agent "$UA" --format json

# 3) create 只返回成功布尔值，不返回 rowPermissionId。必须 list 反查精确定位 ID。
aliyun dataphin-public list-row-permission --tenant-id "$TENANT_ID" \
  --keyword "<行级权限名称>" \
  --page-num 1 --page-size 20 \
  --user-agent "$UA" --format json

# 4) 按表 GUID 查询某张表上的行级权限
aliyun dataphin-public get-row-permission-by-table-guids --tenant-id "$TENANT_ID" \
  --table-guids "<表GUID>" \
  --user-agent "$UA" --format json

# 5) 更新行级权限。更新前先回读/list，完整回填 mappingColumns/rules/tables，避免覆盖清空。
aliyun dataphin-public update-row-permission --tenant-id "$TENANT_ID" \
  --row-permission-id "<行级权限ID>" \
  --row-permission-name "<行级权限名称>" \
  --row-permission-desc "<新描述>" \
  --mapping-columns '{"ColumnName":"<字段名>","ColumnType":"<字段类型>","ColumnId":"<字段ID>","ColumnDesc":""}' \
  --rules '{"RuleName":"<规则名>","ScopeType":"SELECT_COLUMN","Expressions":[{"Parent":"null","Type":"RELATION","Operator":"OR","SubConditions":[{"Type":"EXPRESSION","SubConditions":[],"ColumnId":"<字段ID>","Parent":"-999","Operator":"IN","Values":["华东","华南"]}]}],"UserMappingList":[],"Status":1,"IsDelete":false}' \
  --tables '{"ResourceId":"<表GUID>","ResourceName":"<表名>","ResourceType":"PHYSICAL_TABLE"}' \
  --user-agent "$UA" --format json

# 6) 查询某个行级权限规则下的授权账号
aliyun dataphin-public get-account-by-row-permission-id --tenant-id "$TENANT_ID" \
  --row-permission-id "<行级权限ID>" \
  --rule-ids "<规则ID>" \
  --user-agent "$UA" --format json

# 7) 查询某个用户拥有/涉及的行级权限
aliyun dataphin-public list-row-permission-by-user-id --tenant-id "$TENANT_ID" \
  --operator "<用户ID或账号>" \
  --page-num 1 --page-size 10 \
  --user-agent "$UA" --format json

# 8) 删除行级权限（不可回滚；删除前确认无审批中申请与下游应用依赖）
aliyun dataphin-public delete-row-permission --tenant-id "$TENANT_ID" \
  --row-permission-id "<行级权限ID>" \
  --user-agent "$UA" --format json
```

### 规则表达式结构

| 配置 | 说明 | 示例 |
|---|---|---|
| `ScopeType=ALL_COLUMN` | 授权所有映射列/全部范围，常用于默认规则 | `"Expressions":[]` |
| `ScopeType=SELECT_COLUMN` | 只对指定字段值范围授权 | 通过 `Expressions[].SubConditions[]` 配置条件 |
| `Operator=IN` | 多值包含 | `"Values":["男","女"]` |
| `Operator=LIKE` | 模糊匹配 | `"Values":["张"]` |
| `Operator=EQUAL` | 精确匹配 | `"Values":["华东"]` |
| `UserMappingList` | 规则授权账号映射 | `PERSONAL` 个人账号或 `PRODUCE` 生产账号 |

> [Agent 自主发现] 页面内部接口字段为 camelCase（如 `rowPermissionName`、`mappingColumns`、`resourceBizUnit`），OpenAPI 请求体字段会由 CLI 映射为 PascalCase（如 `RowPermissionName`、`MappingColumns`、`ResourceBizUnit`）。复杂数组元素建议使用 PascalCase JSON 对象，避免字段被服务端忽略。

## 9. Success Verification

每次执行后必须进行结果验证：

1. **create 验证**：`create-row-permission` 返回成功后，必须用 `list-row-permission --keyword <name>` 反查并定位 `rowPermissionId`。
2. **table 验证**：用 `get-row-permission-by-table-guids --table-guids <table-guid>` 确认目标表已绑定行级权限。
3. **update 验证**：更新后用 list / get-by-table / get-account 回读规则、映射字段、关联表与授权账号。
4. **account 验证**：`get-account-by-row-permission-id` 使用规则 ID 查询授权账号；`--rule-ids` 是 CLI list 参数，多个规则 ID 用空格分隔。
5. **delete 验证**：删除后再次 list 或 get-by-table，目标权限不应再出现。
6. **边界验证**：行级权限申请、审批通过、运行时 SQL 过滤通常涉及内部授权/审批链路与缓存同步，不能仅凭 create/update 成功断言“运行时已生效”。

## 10. Cleanup

行级权限删除不可回滚，清理前必须确认：

- 无正在进行中的行级权限申请或审批单。
- 无下游任务、数据服务 API、生产账号或个人账号依赖该规则。
- 已记录 `rowPermissionId`、规则 ID、关联表 GUID 与删除前状态。
- 删除后执行 list/get-by-table 反查，确认目标行级权限已不存在。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices

- 创建前先查询同名行级权限，避免重复配置。
- create 只返回 true，不返回 ID；所有后续 update/delete 都必须先 list 反查 ID。
- update 前必须回读并完整回填 `mappingColumns`、`rules`、`tables`，否则可能清空原有规则或关联表。
- 复杂 list 参数不要传整个 JSON 数组字符串，而是每个数组元素单独传一个 JSON 对象字符串。
- 个人账号（`PERSONAL`）与生产账号（`PRODUCE`）语义不同，申请、审批与运行时生效范围不同，不能混用。
- 查询受影响生产账号依赖表血缘；没有下游血缘时返回空数组也可能是正常结果。
- 权限申请审批通过后可能存在缓存/同步延迟，需要通过实际查询或应用调用验证运行时过滤效果。
- 所有写操作前必须 HITL 二次确认，所有 API 命令必须携带 `--user-agent`。
