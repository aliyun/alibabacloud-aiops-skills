---
name: manage-column-permission
description: |-
  管理 Dataphin 列级/字段级资源权限的授权、回收、查询、操作日志和权限点校验。
  当用户要控制敏感字段可见性，给手机号、身份证号、薪资等字段授予或回收 SELECT 权限，查询某张表/某个字段当前授权记录，或验证某个用户是否拥有字段权限时进入。
  触发词：列级权限、字段权限、字段级权限、column permission、field permission、敏感字段可见性、授权字段、回收字段权限、PHYSICAL_FIELD、LOGICAL_FIELD。
  关键限制：公共 OpenAPI 通过资源点授权/回收，不提供内部 grantByResource 形态；字段授权前必须先定位字段资源标识；--resource-list 元素需传 JSON 对象（如 '{"ResourceId":"field_guid"}'）；写操作需 HITL 确认。
---

# 列级权限管理 Skill

## 1. Scenario Description

在 Dataphin 平台管理 / 数据权限中对「列级权限（Column / Field Permission）」做授权、回收、查询和校验。列级权限用于控制敏感字段可见性，例如只允许 HR 角色或指定用户查看 `salary` 字段，只允许合规人员查看 `id_card` 字段。

本 Skill 基于 `dataphin-public` 已开放的资源权限 OpenAPI 实现字段级能力：先通过资产/字段查询定位字段资源点，再使用资源权限命令对 `PHYSICAL_FIELD`、`LOGICAL_FIELD`、`LABEL_FIELD`、`REALTIME_LOGICAL_FIELD`、`REALTIME_MIRROR_FIELD` 等字段资源执行授权、回收与校验。页面内部的 `grantByResource` / `submitAuthRevoke` / `queryPagedPermissionList` 属于内部 REST，不作为外部 Skill 的直接命令入口。

**Architecture**：`Dataphin Tenant → Catalog / Table → Field ResourceId → Resource Permission Grant/Revoke → Permission Record / Operation Log → Runtime Permission Check`

### 涉及 Dataphin OpenAPI

- `GetTableColumns` — 查询资产表字段，辅助定位字段候选 GUID 与字段元数据
- `GrantResourcePermission` — 通过资源点对用户授权
- `RevokeResourcePermission` — 回收用户资源授权
- `ListResourcePermissions` — 分页获取权限授权记录
- `ListResourcePermissionOperationLog` — 分页获取权限操作日志
- `CheckResourcePermission` — 校验用户是否拥有指定资源权限点
- `GetUsers` — 按用户 ID 批量获取用户信息，用于授权前确认对象

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
> 1. Obtain credentials from Alibaba Cloud Console
> 2. Configure credentials outside of this session
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

执行任何写操作（grant / revoke）前必须向用户确认以下参数，禁止静默提交：

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--tenant-id` | 是 | 租户 ID（大整数，建议字符串传） | — |
| `--catalog` | 查询字段时必填 | 资产表 catalog：业务板块或项目空间名称 | — |
| `--table-name` | 查询字段时必填 | 目标表名 | — |
| `--resource-type` | grant/revoke/check 必填 | 资源类型；字段权限常用 `PHYSICAL_FIELD` / `LOGICAL_FIELD` / `LABEL_FIELD` | — |
| `--resource-list` | grant/revoke/check 必填 | 资源权限 API 可识别的字段/表资源点列表；每个元素必须传 JSON 对象，如 `'{"ResourceId":"field_resource_id"}'`。注意：`get-table-columns` 返回的字段 `Guid` 只是候选标识，需用权限记录或 check 结果确认是否可作为资源点 | — |
| `--user-id-list` | grant 必填 | 待授权用户 ID 列表，CLI 原生 list 格式 | — |
| `--user-id` | revoke/check 必填 | 单个待回收或校验用户 ID | — |
| `--operate-list` | grant 必填、revoke 可选 | 操作列表；字段查看通常为 `SELECT` | — |
| `--operate` | check 必填 | 单个操作类型，如 `SELECT` | — |
| `--effective-end` | grant 必填 | 授权有效期时间戳（毫秒） | — |
| `--reason` | grant/revoke 可选但推荐 | 授权或回收原因，便于审计 | — |
| `--tab-type` | list 必填 | 授权记录/操作日志页签；表与字段权限使用 `TABLE` | `TABLE` |
| `--search-text` | list 可选 | 表名、字段名、账号等关键字 | — |
| `--page` / `--page-size` | list 必填 | 分页参数 | `1` / `10` |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-column-permission/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public list-resource-permissions --tenant-id "1234567890123456789" \
  --tab-type TABLE --page 1 --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/manage-column-permission/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/manage-column-permission/$SESSION_ID"

# 0) 确认用户身份。授权前先确认 userId 对应的真实用户。
aliyun dataphin-public get-users --tenant-id "$TENANT_ID" \
  --user-id-list "<用户ID>" \
  --user-agent "$UA" --format json

# 1) 定位目标字段候选信息。字段级授权不能只凭字段名；get-table-columns 返回的 Guid 需再与权限记录或 check 结果核对。
# ⚡ 带 --cli-query 只取必要字段（完整返回单表可达 2万+ 字符，白吃上下文）
aliyun dataphin-public get-table-columns --tenant-id "$TENANT_ID" \
  --catalog "<业务板块或项目空间名称>" \
  --table-name "<表名>" \
  --cli-query 'ColumnList[].{Name:Name,DataType:DataType,Guid:Guid}' \
  --user-agent "$UA" --format json

# 2) 查询现有授权记录。表/字段权限记录使用 TABLE 页签。
aliyun dataphin-public list-resource-permissions --tenant-id "$TENANT_ID" \
  --tab-type TABLE --search-text "<表名或字段名>" \
  --page 1 --page-size 10 \
  --user-agent "$UA" --format json

# 3) 授予字段 SELECT 权限。--resource-list 每个元素必须是 JSON 对象。
aliyun dataphin-public grant-resource-permission --tenant-id "$TENANT_ID" \
  --resource-type PHYSICAL_FIELD \
  --resource-list '{"ResourceId":"<字段资源ID或GUID>"}' \
  --user-id-list "<用户ID>" \
  --operate-list SELECT \
  --effective-end "<毫秒时间戳>" \
  --reason "<授权原因>" \
  --user-agent "$UA" --format json

# 4) 校验指定用户是否拥有字段权限。
aliyun dataphin-public check-resource-permission --tenant-id "$TENANT_ID" \
  --resource-type PHYSICAL_FIELD \
  --resource-list '{"ResourceId":"<字段资源ID或GUID>"}' \
  --user-id "<用户ID>" \
  --operate SELECT \
  --user-agent "$UA" --format json

# 5) 查询权限操作日志，确认 GRANT/REVOKE 进入审计链路。
aliyun dataphin-public list-resource-permission-operation-log --tenant-id "$TENANT_ID" \
  --tab-type TABLE --search-text "<表名或字段名>" \
  --page 1 --page-size 10 \
  --user-agent "$UA" --format json

# 6) 回收字段权限。回收前必须确认权限记录、用户和字段资源一致。
aliyun dataphin-public revoke-resource-permission --tenant-id "$TENANT_ID" \
  --resource-type PHYSICAL_FIELD \
  --resource-list '{"ResourceId":"<字段资源ID或GUID>"}' \
  --user-id "<用户ID>" \
  --operate-list SELECT \
  --reason "<回收原因>" \
  --user-agent "$UA" --format json
```

### 资源类型选择

| 场景 | `--resource-type` | 说明 |
|---|---|---|
| 物理表字段 | `PHYSICAL_FIELD` | 最常见字段级权限场景 |
| 事实逻辑表字段 | `LOGICAL_FIELD` | 事实逻辑表字段 |
| 标签逻辑表字段 | `LABEL_FIELD` | 标签字段 |
| 实时元表字段 | `REALTIME_LOGICAL_FIELD` | 实时元表字段 |
| 实时镜像表字段 | `REALTIME_MIRROR_FIELD` | 实时镜像字段 |

> [Agent 自主发现] `grant-resource-permission` / `revoke-resource-permission` / `check-resource-permission` 的 `--resource-list` 是 list，元素会按 JSON 解析且真实服务端要求对象；传 `--resource-list field_guid` 会报 `invalid JSON element`，传 `--resource-list '"field_guid"'` 会在真实调用时报 `Expected BEGIN_OBJECT but was STRING`。正确写法是 `--resource-list '{"ResourceId":"field_guid"}'`，CLI 最终映射为 `ResourceList:[{"ResourceId":"field_guid"}]`。

## 9. Success Verification

每次执行后必须进行结果验证：

1. **字段定位验证**：`get-table-columns` 返回目标字段，并记录字段候选 `Guid`、字段名、字段类型和所属表；该 `Guid` 需再与权限记录或 `check-resource-permission` 可识别的 `ResourceId` 核对。
2. **授权前查重**：执行 grant 前先用 `list-resource-permissions --tab-type TABLE --search-text <表/字段>` 检查是否已有相同用户 + 相同字段 + 相同操作权限。
3. **grant 验证**：授权返回成功后，执行 `check-resource-permission` 校验目标用户对目标字段的 `SELECT` 权限。
4. **审计验证**：执行 `list-resource-permission-operation-log`，确认授权或回收动作进入操作日志。
5. **revoke 验证**：回收后再次执行 `check-resource-permission` 或查询授权记录，确认目标字段权限已失效。
6. **运行时边界**：OpenAPI 授权成功不等于所有查询链路立即可见；运行时效果可能受审批、缓存同步、引擎侧鉴权和跨项目查询链路影响。

## 10. Cleanup

字段权限回收可能影响用户、任务、数据服务 API、消费任务或报表访问。清理前必须确认：

- 已记录授权前后状态、字段资源标识、用户 ID、操作类型和有效期。
- 无正在执行的任务或消费链路依赖该字段权限。
- 回收前向用户展示影响范围并获得明确确认。
- 回收后执行 `check-resource-permission` 和授权记录/操作日志查询。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices

- 先定位字段候选信息，再确认资源权限 API 可识别的 `ResourceId`；不要只凭字段中文名、表名或展示名执行写操作。
- `--resource-list` 字段资源必须按 JSON 对象元素传参，例如 `'{"ResourceId":"field_resource_id"}'`。
- 字段权限常用 `SELECT`，不要误用表级 `ALTER` / `UPDATE` / `DELETE` 等操作，除非用户明确要求并确认资源类型支持。
- `grant-resource-permission` 支持一次多个用户和多个资源，但批量授权前必须逐项展示并确认，避免误授敏感字段。
- `revoke-resource-permission` 是写操作且可能影响生产链路，必须二次确认。
- `list-resource-permissions` 和操作日志只有 `TABLE` / `DATASOURCE` 页签；字段权限归入 `TABLE` 页签查询。
- 页面内部接口 `grantByResource`、`queryPagedPermissionList`、`queryUserPermissions` 可作为业务理解参考，但外部 Skill 必须优先使用公开 OpenAPI。
- 所有 API 命令必须携带 `--user-agent`。

## 13. Troubleshooting

| 现象 | 常见原因 | 处理方式 |
|---|---|---|
| `invalid JSON element` | `--resource-list` 直接传裸字符串 | 改为 `--resource-list '{"ResourceId":"<resource>"}'` |
| `Expected BEGIN_OBJECT but was STRING` | `--resource-list` 传了 JSON 字符串元素 | 改为 JSON 对象元素，至少包含 `ResourceId` |
| 授权成功但运行时仍不可见 | 缓存同步、审批状态、跨项目引擎侧鉴权未完成 | 等待同步并通过实际查询链路复核 |
| 查询不到字段 | `catalog` 或 `table-name` 不匹配资产目录 | 先确认资产所在项目/业务板块，再执行 `get-table-columns` |
| 403 / Forbidden | 当前 RAM 或租户角色无资源权限管理权限 | 读取 RAM 策略并引导用户补齐权限 |
| list 查不到字段级记录 | 使用了错误页签或搜索词过窄 | 使用 `--tab-type TABLE`，尝试表名、字段名、用户关键字分别搜索 |
