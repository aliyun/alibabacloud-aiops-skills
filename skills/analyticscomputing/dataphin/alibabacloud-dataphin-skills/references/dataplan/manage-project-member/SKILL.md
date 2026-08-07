---
name: manage-project-member
description: |-
  管理 Dataphin 项目成员（添加 / 移除 / 更新角色 / 查询列表）。
  当用户场景涉及项目成员变更、角色分配、权限调整时进入。

  触发场景：
  - 需要给项目添加开发者或运维人员
  - 需要调整成员角色（如从访客改为开发者）
  - 需要批量移除项目成员
  - 查询项目当前成员列表

  触发词：项目成员、添加成员、移除成员、更新角色、成员管理、add-project-member、remove-project-member、update-project-member。

  关键限制：角色码为整数枚举（1-5）；DEV_PROD 模式项目需指定 Env（DEV/PROD）；19 位 ID 必须字符串呈现。
---

# 项目成员管理 skill

## 1. Scenario Description

管理 Dataphin 项目的成员与角色，支持：添加成员并分配角色、移除成员、更新成员角色、查询成员列表。

**Architecture**：`Dataphin Tenant → Project → ProjectMember（User + Role + Env）`

## 2. Installation

```bash
aliyun plugin install aliyun-cli-dataphin-public
```
（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values to terminal or logs
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
> Run `aliyun version` to verify >= 3.4.8. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [`../../ram-policies.md`](../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--op-tenant-id` | 是 | 租户 ID（19 位 snowflake，**字符串传**） | — |
| `--id` | 是 | 项目 ID（19 位 snowflake） | — |
| `Env` | 否 | 环境标识：`DEV` 或 `PROD`；DEV_PROD 模式项目需指定 | — |
| `UserId` | 是 | 目标用户 ID（字符串） | — |
| `RoleList` | 是（添加/更新时） | 角色码数组 | — |

### 角色码枚举

| 码值 | 角色 |
|---|---|
| 1 | 项目管理员 |
| 2 | 开发者 |
| 3 | 访客 |
| 4 | 分析师 |
| 5 | 运维 |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-project-member/{session-id}
```

## 8. Core Workflow

```bash
TENANT_ID="<your-tenant-id>"        # 19 位字符串
PROJECT_ID="<your-project-id>"      # 19 位字符串
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
```

### 8.1 添加项目成员

```bash
aliyun dataphin-public add-project-member \
  --op-tenant-id "$TENANT_ID" \
  --id "$PROJECT_ID" \
  --add-command '{
    "Env": "DEV",
    "UserList": [
      {
        "UserId": "<target-user-id>",
        "RoleList": [2]
      }
    ]
  }' \
  --user-agent AlibabaCloud-Agent-Skills/manage-project-member/$SESSION_ID
```

### 8.2 更新成员角色

```bash
aliyun dataphin-public update-project-member \
  --op-tenant-id "$TENANT_ID" \
  --id "$PROJECT_ID" \
  --update-command '{
    "Env": "DEV",
    "UserList": [
      {
        "UserId": "<target-user-id>",
        "RoleList": [1, 2]
      }
    ]
  }' \
  --user-agent AlibabaCloud-Agent-Skills/manage-project-member/$SESSION_ID
```

### 8.3 移除项目成员

```bash
aliyun dataphin-public remove-project-member \
  --op-tenant-id "$TENANT_ID" \
  --id "$PROJECT_ID" \
  --remove-command '{
    "Env": "DEV",
    "UserIdList": ["<target-user-id>"]
  }' \
  --user-agent AlibabaCloud-Agent-Skills/manage-project-member/$SESSION_ID
```

### 8.4 查询成员列表

```bash
aliyun dataphin-public list-project-members \
  --op-tenant-id "$TENANT_ID" \
  --id "$PROJECT_ID" \
  --list-query '{
    "Env": "DEV",
    "PageSize": 20,
    "PageNo": 1
  }' \
  --user-agent AlibabaCloud-Agent-Skills/manage-project-member/$SESSION_ID
```

### 执行前确认（**写操作必备 / HITL 章节**）

> 本 skill 涉及写操作（添加 / 移除 / 更新成员），调用方执行前必须二次确认：
> - 即将执行的命令全文（脱敏后）
> - 影响范围（哪个 tenant / project / 用户）
> - 是否可回滚（移除成员后可重新添加；角色更新后可再次更新恢复）
> - 替代方案（先用 `list-project-members` 只读查看当前状态）

仅当用户明确回复"确认 / yes / 执行"后才发起命令。

## 9. Success Verification

1. **同步返回**：响应 `Code: "OK"` 或 `code: "0"` 表示请求被接受
2. **list 反查**：执行 `list-project-members` 确认成员/角色变更已生效
3. **异步传播**：DEV_PROD 模式下 DEV 和 PROD 成员可能有短暂不一致（通常 < 5s）

## 10. Cleanup

移除通过本 skill 添加的成员：

```bash
aliyun dataphin-public remove-project-member \
  --op-tenant-id "$TENANT_ID" \
  --id "$PROJECT_ID" \
  --remove-command '{"UserIdList": ["<user-id>"]}' \
  --user-agent AlibabaCloud-Agent-Skills/manage-project-member/$SESSION_ID
```

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参，示例中用引号包住
2. 写操作（add/remove/update）执行前必须 HITL 确认
3. DEV_PROD 模式项目建议显式传 `Env` 字段；BASIC 模式可省略
4. 批量添加多个成员时，`UserList` 数组可包含多个对象

### 常见坑

#### [Agent 自主发现] DEV_PROD 项目不传 Env 时行为不确定
- 现象：DEV_PROD 模式项目调用 `add-project-member` 不传 `Env` 时，成员可能只加到一侧环境
- 结论：DEV_PROD 模式项目**建议始终显式传 `Env`**，如需两侧同步则分别调用 DEV 和 PROD

#### [Agent 自主发现] RoleList 传空数组不报错但无效
- 现象：`"RoleList": []` 请求成功但成员无有效角色
- 结论：`RoleList` 至少包含 1 个角色码

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
