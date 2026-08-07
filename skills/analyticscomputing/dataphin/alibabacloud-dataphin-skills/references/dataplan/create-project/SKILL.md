---
name: create-project
description: |-
  管理 Dataphin 项目创建场景的需求拆解、公开项目查询与创建 API 覆盖边界。
  当用户要创建 Dataphin 项目、初始化 Basic 或 DevProd 项目、检查项目是否已存在、确认项目依赖、配置项目白名单或准备项目创建参数时进入。
  触发词：创建项目、新建项目、Dataphin 项目、项目初始化、DevProd、Basic、项目白名单、项目依赖、create project、project initialization。
  关键限制：当前 dataphin-public CLI 未暴露 create-project/update-project/delete-project；本 Skill 不伪造内部 REST，只能执行公开查询、依赖与白名单命令，并输出项目创建参数清单。
---

# 创建 Dataphin 项目 Skill

## 1. Scenario Description

Dataphin 项目是数据开发工作的容器和起点，承载计算源、数据源、成员、任务、调度、发布和权限等后续配置。用户常见诉求包括创建 Basic 项目、创建 DevProd 项目、确认项目是否已存在、准备项目成员与白名单、或删除前检查项目是否存在依赖。

当前公开 `dataphin-public` CLI 仅覆盖项目查询、依赖校验、白名单与成员管理，不覆盖项目创建、更新、删除本体操作。因此本 Skill 的交付边界是：

- **需求拆解**：整理项目名称、英文名、模式、业务板块、计算源、资源组、成员、白名单等创建参数。
- **公开前置检查**：使用 `list-projects` / `get-project-by-name` / `get-project` 判断项目是否存在，使用 `check-project-has-dependency` 做删除前保护，使用 `get-project-white-lists` 查询白名单。
- **能力边界提示**：页面内部 `/api/project/basic`、`/api/project/update`、`/api/project/{projectId}` 等 REST 只作业务语义参考，不作为外部命令入口。

**Architecture**：`Tenant → Project Requirement → Public Project Query → Dependency / Whitelist Check → Public API Gap / Internal REST Reference`

### 当前公开 OpenAPI 覆盖

- `ListProjects` / `GetProject` / `GetProjectByName` — 查询项目列表、详情或按名称定位项目。
- `CheckProjectHasDependency` — 删除或迁移前检查项目是否被任务、模型、资产等对象依赖。
- `GetProjectWhiteLists` / `ReplaceProjectWhiteLists` — 查询或替换项目白名单。
- `AddProjectMember` / `UpdateProjectMember` / `RemoveProjectMember` / `ListProjectMembers` — 项目成员管理，主要由 `manage-project-member` 承接。

### 当前未公开的项目生命周期能力

- 创建 Basic 项目或 DevProd 项目。
- 更新项目基础信息或项目模式。
- 删除项目。
- 绑定计算源、资源组、开发/生产环境的完整创建链路。

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
> - **NEVER** 读取、回显或打印凭证环境变量
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile.
>
> **If no valid profile exists, STOP here.**

**Pre-check: Aliyun CLI >= 3.4.8 required**
> Run `aliyun version` to verify >= 3.4.8.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [套件级 RAM 策略](../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call, ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--tenant-id` | 是 | 租户 ID（大整数，建议字符串传） | — |
| `--project-name` | 查询必填 | 项目英文名或项目名，用于 `get-project-by-name` | — |
| `--project-id` | 查询/依赖/白名单必填 | 项目 ID | — |
| `projectDisplayName` | 创建参数清单必填 | 项目显示名 | — |
| `projectMode` | 创建参数清单必填 | `BASIC` 或 `DEV_PROD` | — |
| `bizUnitId` | 创建参数清单必填 | 所属数据板块 ID | — |
| `computeEngineId` | 创建参数清单必填 | 绑定计算源 ID | — |
| `resourceGroupId` | 创建参数清单必填 | 调度资源组 ID | — |
| `memberList` | 创建后配置可选 | 项目成员与角色，建议交给 `manage-project-member` | — |
| `whiteList` | 白名单场景可选 | 项目 IP 白名单或访问白名单，更新前需回读现有值 | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/create-project/{session-id}
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/create-project/$SESSION_ID"

# 1) 先确认当前公开 CLI 是否已支持项目创建命令。
aliyun dataphin-public --help

# 2) 按名称查询项目，判断是否已存在。
aliyun dataphin-public get-project-by-name --tenant-id "$TENANT_ID" \
  --project-name "<项目英文名>" \
  --user-agent "$UA" --format json

# 3) 分页查询项目列表，辅助用户选择目标项目。
aliyun dataphin-public list-projects --tenant-id "$TENANT_ID" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

# 4) 按项目 ID 回读详情。
aliyun dataphin-public get-project --tenant-id "$TENANT_ID" \
  --project-id "<项目ID>" \
  --user-agent "$UA" --format json

# 5) 删除或迁移前检查依赖。
aliyun dataphin-public check-project-has-dependency --tenant-id "$TENANT_ID" \
  --project-id "<项目ID>" \
  --user-agent "$UA" --format json

# 6) 查询项目白名单。更新白名单是写操作，需单独 HITL 确认。
aliyun dataphin-public get-project-white-lists --tenant-id "$TENANT_ID" \
  --project-id "<项目ID>" \
  --user-agent "$UA" --format json
```

### 项目创建需求清单

当公开 CLI 缺少 `create-project` 时，Agent 必须输出以下需求清单，而不是调用内部 REST：

| 项 | 示例 | 说明 |
|---|---|---|
| 项目英文名 | `dummy_practice_dev` | 用 `get-project-by-name` 查重 |
| 项目显示名 | `达米零售实操_开发` | 面向页面展示 |
| 项目模式 | `BASIC` / `DEV_PROD` | DevProd 通常涉及开发/生产双环境 |
| 所属数据板块 | `bizUnitId` | 项目归属的业务板块 |
| 计算源 | `computeEngineId` | 与项目执行引擎绑定 |
| 调度资源组 | `resourceGroupId` | 内部创建链路会查询可用资源组 |
| 成员与角色 | 项目管理员、开发者、访客 | 建议由 `manage-project-member` 承接 |
| 白名单 | IP / 网段列表 | 更新前必须回读并保留已有值 |
| 初始化后验证 | 列表/详情/成员/白名单 | 当前公开 CLI 可验证 |

### 执行前确认（写操作必备 / HITL）

> 当前公开 CLI 不支持项目创建 / 更新 / 删除，因此本 Skill 不发起这些写操作。
> `replace-project-white-lists` 是公开写命令，执行前必须二次确认旧白名单、新白名单、影响项目和回滚方案。

## 9. Success Verification

本 Skill 的成功标准不是“已创建项目”，而是完成外部能力范围内的安全交付：

1. **CLI 覆盖验证**：`aliyun dataphin-public --help` 中未发现 `create-project` / `delete-project` 时，必须明确告知能力缺口。
2. **项目查重验证**：`get-project-by-name` 能定位已有项目，或返回不存在并形成创建需求清单。
3. **列表验证**：`list-projects` 可分页返回项目列表。
4. **详情验证**：`get-project` 可按 ID 回读项目信息。
5. **依赖验证**：`check-project-has-dependency` 可在删除/迁移前判断项目依赖。
6. **白名单验证**：`get-project-white-lists` 可回读项目白名单；更新白名单必须 HITL。
7. **边界验证**：不把内部 `/api/project/...` REST、录制用例或页面接口伪装成公开 CLI 命令。

## 10. Cleanup

本 Skill 当前不执行项目创建 / 删除写操作，因此不会产生项目资源。

如果未来公开 API 支持创建项目，清理顺序必须是：下线并删除项目内任务、模型、资源文件和发布对象 → 移除或回滚项目成员与白名单 → 检查 `check-project-has-dependency` → 删除项目。DevProd 模式需要分别关注 DEV / PROD 环境对象。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices

- 项目创建是所有数据开发 Skill 的前置依赖，但当前公开 CLI 不支持直接创建项目。
- 先用 `get-project-by-name` 查重，避免重复申请同名项目。
- 项目模式必须由用户确认：Basic 与 DevProd 的资源、成员、发布链路和清理口径不同。
- 删除或迁移前必须先做依赖校验，存在任务、模型、资源或发布对象时不能直接删除。
- 白名单更新需先回读旧值并合并，禁止用空列表或单个新值覆盖未知存量。
- 页面内部 REST 可作为业务理解参考，外部执行必须使用公开 OpenAPI。

### ✗ 平台限制：当前无公开项目创建 CLI

- 限制描述：`/api/project/basic`、`/api/project/update`、`DELETE /api/project/{projectId}` 等项目生命周期接口存在于 autotest/页面内部 REST 语义中，但未在当前公开 `dataphin-public` CLI 暴露为 `create-project`、`update-project`、`delete-project`。
- 替代方案：完成项目创建需求清单和公开前置检查，等待公开 OpenAPI 或由具备内部系统权限的流程执行。

### 常见坑

#### [Agent 自主发现] 把内部 REST 当成外部命令
- 现象：autotest 中有 `/api/project/basic`，但 `aliyun dataphin-public --help` 中没有 `create-project`。
- 结论：外部 Skill 不能伪造内部 REST 入口；必须明确能力缺口。

#### [Agent 自主发现] DevProd 与 Basic 项目模式混淆
- 现象：用户只说“创建项目”，但未说明项目模式。
- 结论：必须确认 Basic / DevProd；DevProd 涉及开发和生产双环境，后续发布、成员和清理口径不同。

#### [Agent 自主发现] 删除项目前未做依赖检查
- 现象：项目内仍有任务或模型时尝试删除。
- 结论：必须先用 `check-project-has-dependency` 或等价依赖检查确认无依赖，再考虑删除。

### Reference Links

- [references/cli-installation-guide.md](references/cli-installation-guide.md)
- [套件级 RAM 策略](../../ram-policies.md)
- [references/acceptance-criteria.md](references/acceptance-criteria.md)
- [references/related-commands.md](references/related-commands.md)
