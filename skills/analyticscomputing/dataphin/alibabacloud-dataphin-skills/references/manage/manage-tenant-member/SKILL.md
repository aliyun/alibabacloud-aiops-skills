---
name: manage-tenant-member
description: |
  管理 Dataphin 租户成员，包括添加成员、移除成员、查询可添加用户、查询租户成员列表、配置全局角色。触发场景：添加租户成员 / 移除租户成员 / 租户角色配置 / 批量加人 / tenant member / 租户管理员。流程：list-addable-users 定位用户 → add-tenant-members 添加 → list-tenant-members 验证；更新角色用 update-tenant-member；移除用 remove-tenant-member。关键点：add-tenant-members 的 --user-list 必须传单个 JSON 对象字符串 {"Id":"xxx"}，不能传数组；仅 SuperAdmin / 系统管理员可调用；全局角色包括 SYSTEM_ADMIN / DATASOURCE_MANAGER / SECURITY_ADMIN / QUALITY_MANAGER / EXPORT_ADMIN / DATA_STANDARD_MANAGER / LABELS_BUSINESS_MEMBER / DATAPRO_OPERATE_ADMIN 等（完整枚举以 list-addable-roles 实际返回的 Code 字段为准）。触发词：租户成员、添加租户成员、移除租户成员、租户角色、tenant member、tenant administration。
---

# 租户成员管理 Skill

## 1. Scenario Description

场景：在 Dataphin 租户维度进行组织级人员管理，包括将已有用户加入租户、调整全局角色、移除成员等。

### Architecture

```
用户请求 → 确认参数 → list-addable-users 查找可添加用户
  → add-tenant-members / add-tenant-members-by-source-user 添加
  → list-tenant-members 验证
  →（可选）update-tenant-member 更新角色
  →（可选）remove-tenant-member 移除成员
```

### 涉及 Dataphin OpenAPI

- `ListAddableUsers` — 查询可加入租户但尚未加入的用户
- `AddTenantMembers` — 按用户 ID 批量添加租户成员
- `AddTenantMembersBySourceUser` — 按来源用户批量添加租户成员
- `ListTenantMembers` — 查询当前租户成员
- `ListAddableRoles` — 查询可配置的全局角色
- `UpdateTenantMember` — 更新租户成员全局角色
- `RemoveTenantMember` — 移除租户成员

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8）
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun dataphin-public --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 仅额外要求下列变量：

| 变量 | 说明 | 必须 |
|------|------|------|
| `DATAPHIN_INSECURE` | 独立部署自签证书时设为 `true` 跳过 TLS 校验 | 独立部署必须 |

> **独立部署（非公共云）注意**：
> - 凭证 profile 必须带正确的 `--endpoint`（如 `dataphin-openapi.<your-domain>`），否则请求会打到公共云 `dataphin-public.<region>.aliyuncs.com` 报 `InvalidAccessKeyId.NotFound`。
> - 自签证书环境需 `export DATAPHIN_INSECURE=true`（推荐），或在命令**末尾**追加 `--insecure`（`--insecure` 非解析 flag，放在参数中间会吞掉下一个参数值）。

## 4. Authentication

### Pre-check: Credentials Required

> **Security Rules:**
> - **NEVER** 读取、回显或打印凭证环境变量（禁止对 AccessKey ID / Secret 做任何输出或日志）
> - **NEVER** 要求用户在本会话或命令行直接输入 AK/SK
> - **NEVER** 使用 `aliyun configure set` 写入字面量凭证
> - **ONLY** 使用 `aliyun configure list` 检查凭证状态
>
> ```bash
> aliyun configure list
> ```
> 检查输出中是否存在有效 profile（AK、STS 或 OAuth 身份）。
>
> **如果没有有效 profile，请在此停止。**
> 1. 从 [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak) 获取凭证
> 2. 在会话外配置（终端执行 `aliyun configure`，或在 shell profile 中设置环境变量）
> 3. 重新运行 `aliyun configure list` 确认有效后再继续

### Pre-check: Aliyun CLI plugin update required

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
>
> 执行前确认 CLI 与插件版本：
> ```bash
> aliyun version
> aliyun plugin list
> ```

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 skill 最小权限见 [../../ram-policies.md](../../ram-policies.md)。

## 6. IMPORTANT: Parameter Confirmation

执行任何租户成员变更命令前必须向用户确认以下参数，禁止静默提交：

| 参数 | 说明 |
|------|------|
| `--tenant-id` | 租户 ID（`--op-tenant-id` 的别名，profile 已配置时可省） |
| 用户标识 | 待添加/更新/移除的用户 ID 或来源用户 ID |
| `--member-list` | 更新角色时的成员列表 JSON（含 `UserId` + `RoleList`） |

## 7. 完整命令链

```bash
TENANT_ID=<tenant-id>
USER_AGENT="AlibabaCloud-Agent-Skills/manage-tenant-member/{session-id}"

# 1) 查找可添加用户（支持按姓名/账号搜索）
aliyun dataphin-public list-addable-users --dataphin-profile <p> --tenant-id $TENANT_ID \
  --search-text "<姓名或账号>" --page 1 --page-size 10 \
  --user-agent "$USER_AGENT" --format json \
  | jq '.PageResult.UserList[] | {Id, Name, AccountName, DisplayName, SourceType}'

# 2) 添加租户成员（按用户 ID）
#    --user-list 每个参数是一个 JSON 对象字符串，不能传 JSON 数组
aliyun dataphin-public add-tenant-members --dataphin-profile <p> --tenant-id $TENANT_ID \
  --user-list '{"Id":"<user-id-1>"}' '{"Id":"<user-id-2>"}' \
  --user-agent "$USER_AGENT" --format json

# 3) 验证已加入租户
aliyun dataphin-public list-tenant-members --dataphin-profile <p> --tenant-id $TENANT_ID \
  --search-text "<姓名或账号>" --page 1 --page-size 10 \
  --user-agent "$USER_AGENT" --format json \
  | jq '.PageResult.UserList[] | {Id, Name, AccountName, RoleList}'

# 4) 查看可配置的全局角色
#    注意：字段名是 Code / Name，不是 RoleCode / RoleName
aliyun dataphin-public list-addable-roles --dataphin-profile <p> --tenant-id $TENANT_ID \
  --user-agent "$USER_AGENT" --format json \
  | jq '.RoleList[] | {Code, Name}'

# 5) 更新成员全局角色
#    --member-list 每个成员一个 JSON 对象字符串，含 UserId + RoleList 数组
#    可选字段：MobilePhone / Mail / DingNumber
aliyun dataphin-public update-tenant-member --dataphin-profile <p> --tenant-id $TENANT_ID \
  --member-list '{"UserId":"<user-id>","RoleList":["SYSTEM_ADMIN","DATASOURCE_MANAGER"]}' \
  --user-agent "$USER_AGENT" --format json

# 6) 移除租户成员
#    --source-id 为用户来源 Id（即成员的用户 Id）
aliyun dataphin-public remove-tenant-member --dataphin-profile <p> --tenant-id $TENANT_ID \
  --source-id '<user-id>' \
  --user-agent "$USER_AGENT" --format json
```

## 8. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/manage-tenant-member/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 9. 参数要点

| 参数 | 必填 | 取值 | 备注 |
|---|---|---|---|
| `--tenant-id` | 必 | int | 租户 ID；`--op-tenant-id` 的别名；profile 已配置时可省略 |
| `--user-list`（add-tenant-members） | 必 | 每个用户一个 JSON 对象字符串：`{"Id":"xxx"}` | **不能传 JSON 数组**；支持一次添加多个用户 |
| `--source-user-list`（add-tenant-members-by-source-user） | 可 | 每个来源用户一个 JSON 对象字符串（含 `SourceId` 等） | 按来源系统用户添加 |
| `--member-list`（update-tenant-member） | 必 | 每个成员一个 JSON 对象字符串：`{"UserId":"xxx","RoleList":[...]}` | **不是 `--user-id`/`--role-list`**；可选 `MobilePhone`/`Mail`/`DingNumber`；全局角色枚举以 `list-addable-roles` 返回的 `Code` 为准（如 `SYSTEM_ADMIN`/`DATASOURCE_MANAGER`/`LABELS_BUSINESS_MEMBER`/`DATAPRO_OPERATE_ADMIN`） |
| `--source-id`（remove-tenant-member） | 必 | string | 待移除成员的用户来源 Id（**不是 `--user-id`**） |
| `--search-text`（list） | 可 | string | 按姓名/账号模糊搜索 |

## 10. 常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| `Error: required flags missing: --page, --page-size` | `list-addable-users` / `list-tenant-members` 未传分页参数（插件在 CLI 层拦截） | 加 `--page 1 --page-size 10` |
| `Expected BEGIN_OBJECT but was BEGIN_ARRAY at path $.userList[0]` | `--user-list` 传了 JSON 数组 `[{"Id":"xxx"}]` | 改成单个 JSON 对象字符串 `{"Id":"xxx"}`；多用户传多个参数 |
| `Error: --member-list is required` | update-tenant-member 误用了 `--user-id` / `--role-list` | 改用 `--member-list '{"UserId":"xxx","RoleList":[...]}'` |
| `Error: --source-id is required` | remove-tenant-member 误用了 `--user-id` | 改用 `--source-id '<user-id>'` |
| `InvalidAccessKeyId.NotFound`（endpoint 为 `dataphin-public.<region>.aliyuncs.com`） | 独立部署环境的凭证打到了公共云 endpoint | 使用带 endpoint 的 profile，或显式传 `--endpoint <DATAPHIN_OPENAPI_ENDPOINT>` |
| `x509: certificate is not trusted` / `SSL/TLS 证书验证失败` | 独立部署使用自签证书 | 设 `DATAPHIN_INSECURE=true`（推荐）；或将 `--insecure` 放在命令**末尾**（放中间会吞掉下一个参数值） |
| `DPN.OP.NoPermission: 没有权限` | 当前调用者不是 SuperAdmin / 系统管理员 | 确认调用者具备租户成员管理权限 |
| `UserNotFound / 用户不存在` | 用户 ID 错误或该用户不在可添加列表 | 先用 `list-addable-users` 确认用户 ID |

## 11. ✗ 不要做

- ✗ 静默添加/移除租户成员：必须先确认用户身份和权限
- ✗ `--user-list` 传 JSON 数组：CLI 把每个参数当做一个 JSON 对象解析
- ✗ update/remove 误用 `--user-id` / `--role-list`：真实参数是 `--member-list` / `--source-id`
- ✗ 未确认当前调用者角色：仅 SuperAdmin / 系统管理员可操作
- ✗ 硬编码真实 tenant-id / user-id：应通过变量或用户确认后填充
- ✗ 未带 `--user-agent` 调用 aliyun API 命令

## 12. 验证与诊断

写操作（add / update / remove）成功判据：

1. **同步返回**：响应 `Code: "OK"` 且 `HttpStatusCode: 200` 表示请求被接受
2. **list 反查**：执行 `list-tenant-members` 确认成员/角色变更已生效
3. **传播延迟**：成员变更可能有短暂延迟（通常 < 5s），反查为空时稍候重试

```bash
# 确认成员已加入
aliyun dataphin-public list-tenant-members --dataphin-profile <p> --tenant-id $TENANT_ID \
  --search-text "<姓名>" --page 1 --page-size 10 \
  --user-agent "$USER_AGENT" --format json \
  | jq '.PageResult.UserList[] | {Id, Name, AccountName, RoleList}'
```

## 13. Cleanup

移除通过本 skill 添加的测试成员（如验证阶段 `add-tenant-members` 真实加入的用户）：

```bash
aliyun dataphin-public remove-tenant-member --dataphin-profile <p> --tenant-id $TENANT_ID \
  --source-id '<user-id>' \
  --user-agent "$USER_AGENT" --format json
```

> `--source-id` 为成员的用户来源 Id；建议先用 `list-tenant-members --search-text "<姓名>"` 反查确认后再移除。
> 执行前可先加 `--cli-dry-run` 预检请求体，确认无误后再去掉该 flag 正式执行。

## 14. 相关命令

- `aliyun dataphin-public list-addable-users` — 查询可加入租户的用户
- `aliyun dataphin-public add-tenant-members` — 按用户 ID 添加租户成员
- `aliyun dataphin-public add-tenant-members-by-source-user` — 按来源用户添加租户成员
- `aliyun dataphin-public list-tenant-members` — 查询当前租户成员
- `aliyun dataphin-public list-addable-roles` — 查询可配置的全局角色
- `aliyun dataphin-public update-tenant-member` — 更新租户成员角色
- `aliyun dataphin-public remove-tenant-member` — 移除租户成员
- `manage-project-member`（dataplan 模块） — 项目级别成员管理（经套件入口 alibabacloud-dataphin-skills 路由加载）

## 15. 最佳实践与参考链接

1. **大整数 ID 字符串传参**：用户 ID / 租户 ID 为 9~19 位 snowflake，一律用引号包住，避免精度丢失（如 `--source-id '1234567890123456789'`）
2. **写操作先 dry-run 预检**：add / update / remove 正式执行前先加 `--cli-dry-run` 校验请求体结构，确认无误再去掉该 flag
3. **写操作必须 HITL 确认**：添加/更新/移除成员前向用户确认身份与权限，禁止静默操作
4. **`--user-list` 传单个 JSON 对象**：每个用户一个 `{"Id":"xxx"}`，多用户传多个参数，不能传 JSON 数组
5. **update / remove 用对参数**：更新用 `--member-list`（`{"UserId":"x","RoleList":[...]}`），移除用 `--source-id`，不是 `--user-id`/`--role-list`

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
