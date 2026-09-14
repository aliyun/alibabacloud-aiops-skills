---
name: create-project
description: |-
  管理 Dataphin 项目创建场景的需求拆解、公开项目查询与创建 API 覆盖边界。
  当用户要创建 Dataphin 项目、初始化 Basic 或 DevProd 项目、检查项目是否已存在、确认项目依赖、配置项目白名单或准备项目创建参数时进入。
  触发词：创建项目、新建项目、Dataphin 项目、项目初始化、DevProd、Basic、项目白名单、项目依赖、create project、project initialization。
  关键限制：项目生命周期命令按模式拆分为 create-basic-project / create-dev-prod-project / update-basic-project / update-dev-prod-project / delete-project（无 create-project 形态）；创建命令走单一 --create-command JSON 对象参数而非扁平 flag；创建项目前必须确保数据板块与计算源已就绪（DevProd 需 dev/prod 两套计算源）；19 位大整数 ID 一律字符串传参。
---

# 创建 Dataphin 项目 Skill

## 1. Scenario Description

Dataphin 项目是数据开发工作的容器和起点，承载计算源、数据源、成员、任务、调度、发布和权限等后续配置。用户常见诉求包括创建 Basic 项目、创建 DevProd 项目、确认项目是否已存在、准备项目成员与白名单、或删除前检查项目是否存在依赖。

当前公开 `dataphin-public` CLI 已覆盖项目全生命周期（创建 / 更新 / 删除）以及查询、依赖校验、白名单与成员管理。因此本 Skill 的交付边界是：

- **需求拆解**：整理项目名称、英文名、模式、业务板块、计算源、成员、白名单等创建参数。
- **公开前置检查**：使用 `list-projects` / `get-project-by-name` / `get-project` 判断项目是否存在，使用 `check-project-has-dependency` 做删除前保护，使用 `get-project-white-lists` 查询白名单。
- **完整创建链路**：先确保数据板块与计算源就绪（DevProd 需 dev / prod 两套计算源），再调用 `create-basic-project` / `create-dev-prod-project` 完成创建并回读验证。

**Architecture**：`Tenant → Project Requirement → Public Project Query → Dependency / Whitelist Check → BizUnit / Compute Source Readiness → Create / Update / Delete Project → Read-back Verification`

### 当前公开 OpenAPI 覆盖

- `CreateBasicProject` / `CreateDevProdProject` — 创建 Basic（单环境）或 DevProd（双环境）项目。
- `UpdateBasicProject` / `UpdateDevProdProject` — 更新项目基础信息（项目英文名不可修改）。
- `DeleteProject` — 删除项目（Basic / DevProd 均适用）。
- `ListProjects` / `GetProject` / `GetProjectByName` — 查询项目列表、详情或按名称定位项目。
- `CheckProjectHasDependency` — 删除或迁移前检查项目是否被任务、模型、资产等对象依赖。
- `GetProjectWhiteLists` / `ReplaceProjectWhiteLists` — 查询或替换项目白名单。
- `AddProjectMember` / `UpdateProjectMember` / `RemoveProjectMember` / `ListProjectMembers` — 项目成员管理，主要由 `manage-project-member` 承接。

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
| `Name` | 创建必填 | 项目英文名（`--create-command` 内字段） | — |
| `DisplayName` | 创建必填 | 项目显示名 | — |
| `BizUnitId` | 创建必填 | 所属数据板块 ID | — |
| `DevComputeSourceId` | DevProd 创建必填 | 开发计算源 ID | — |
| `ProdComputeSourceId` | DevProd 创建必填 | 生产计算源 ID | — |
| `ComputeSourceId` | Basic 创建必填 | 计算源 ID（Basic 单环境） | — |
| `NameSpaceTag` | 创建可选 | `PUBLIC` / `GENERAL` | `PUBLIC` |
| `memberList` | 创建后配置可选 | 项目成员与角色，建议交给 `manage-project-member` | — |
| `whiteList` | 白名单场景可选 | 项目 IP 白名单或访问白名单，更新前需回读现有值 | — |

> **注意**：`create-basic-project` / `create-dev-prod-project` 的参数不是扁平 flag，全部收拢在单一 `--create-command` JSON 对象里（见 §8）。

## 7. Observability (MUST follow for every aliyun command)

版本 `{version}`（Shell 变量 `SKILL_VERSION`）来自套件 `references/manifest.json` 的 `version` 字段，与 session-id 一同继承[父技能 §7](../../../SKILL.md#7-observability)。直接加载本子技能时先完成父层初始化；所有 CLI / SDK 调用使用父技能名称与同一版本，跨 Shell 调用须重新注入这些值。

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/$SESSION_ID skill-version/$SKILL_VERSION"
```

### Step 1：查重与前置检查

```bash
# 1) 按名称查询项目，判断是否已存在。
aliyun dataphin-public get-project-by-name --tenant-id "$TENANT_ID" \
  --project-name "<项目英文名>" --user-agent "$UA" --format json

# 2) 分页查询项目列表，辅助用户选择目标项目。
aliyun dataphin-public list-projects --tenant-id "$TENANT_ID" \
  --page-no 1 --page-size 10 --user-agent "$UA" --format json
```

### Step 2：确认数据板块与计算源就绪（DevProd）

```bash
# 3) 查数据板块：无合适板块时先 create-biz-unit（DevProd 项目需 DEV_PROD 模式板块）。
aliyun dataphin-public list-biz-units --tenant-id "$TENANT_ID" --user-agent "$UA"

# 4) 查计算源：同一 MaxCompute project 只能绑定一个计算源，
#    租户内全部 MAX_COMPUTE 计算源已被绑定时必须新建（见 create-maxcompute-compute-source）。
aliyun dataphin-public list-compute-sources --tenant-id "$TENANT_ID" \
  --type MAX_COMPUTE --user-agent "$UA"
```

### Step 3：创建项目

```bash
# DevProd 项目
aliyun dataphin-public create-dev-prod-project --tenant-id "$TENANT_ID" \
  --create-command '{
    "Name": "<项目英文名>",
    "DisplayName": "<项目显示名>",
    "BizUnitId": <数据板块ID>,
    "DevComputeSourceId": <开发计算源ID>,
    "ProdComputeSourceId": <生产计算源ID>,
    "NameSpaceTag": "PUBLIC"
  }' --user-agent "$UA"

# Basic 项目
aliyun dataphin-public create-basic-project --tenant-id "$TENANT_ID" \
  --create-command '{
    "Name": "<项目英文名>",
    "DisplayName": "<项目显示名>",
    "BizUnitId": <数据板块ID>,
    "ComputeSourceId": <计算源ID>,
    "NameSpaceTag": "PUBLIC"
  }' --user-agent "$UA"
```

`--create-command` 完整结构（以 `--help` 输出为准）：

- DevProd：`{BizUnitId, DevComputeSourceId, DevDescription, DevStreamComputeSourceId, DisplayName, Name, NameSpaceTag, ProdComputeSourceId, ProdDescription, ProdStreamComputeSourceId, WhiteLists}`
- Basic：`{BizUnitId, ComputeSourceId, Description, DisplayName, Name, NameSpaceTag, StreamComputeSourceId, Type, WhiteLists}`

### Step 4：回读验证

```bash
aliyun dataphin-public get-project-by-name --tenant-id "$TENANT_ID" \
  --project-name "<项目英文名>" --user-agent "$UA" --format json
```

确认 `ProjectInfo.Id` 与创建返回的 `CreateResult.Id` 一致，且 `Mode`、`BizUnitId`、计算源绑定正确。

### 项目创建参数清单

创建项目前必须收集并确认以下参数（DevProd 与 Basic 的差异见参数说明）：

| 项 | 示例 | 说明 |
|---|---|---|
| 项目英文名 | `dummy_practice_dev` | 用 `get-project-by-name` 查重 |
| 项目显示名 | `达米零售实操_开发` | 面向页面展示 |
| 项目模式 | `BASIC` / `DEV_PROD` | DevProd 通常涉及开发/生产双环境 |
| 所属数据板块 | `BizUnitId` | 项目归属的业务板块；DevProd 项目需 DEV_PROD 模式板块 |
| 计算源 | `DevComputeSourceId` / `ProdComputeSourceId` | DevProd 分别绑定开发/生产计算源；Basic 绑定单个 `ComputeSourceId` |
| 成员与角色 | 项目管理员、开发者、访客 | 创建者与板块架构师由系统自动带入，其余建议由 `manage-project-member` 承接 |
| 白名单 | IP / 网段列表 | 更新前必须回读并保留已有值 |
| 初始化后验证 | 列表/详情/成员/白名单 | 当前公开 CLI 可验证 |

### 执行前确认（写操作必备 / HITL）

> 项目创建 / 更新 / 删除均为写操作，执行前必须向用户确认项目名、模式、数据板块、计算源等全部参数，得到明确同意后才能发起。
> `replace-project-white-lists` 执行前必须二次确认旧白名单、新白名单、影响项目和回滚方案。
> 删除项目前必须先执行 `check-project-has-dependency` 确认无依赖。

## 9. Success Verification

本 Skill 的成功标准是完成项目全生命周期的安全交付：

1. **创建验证**：`create-basic-project` / `create-dev-prod-project` 返回 `Code: OK` 且 `CreateResult.Id` 非空，并通过 `get-project` / `get-project-by-name` 回读确认。
2. **项目查重验证**：创建前 `get-project-by-name` 查重，同名项目已存在时必须先与用户确认。
3. **列表验证**：`list-projects` 可分页返回项目列表。
4. **详情验证**：`get-project` 可按 ID 回读项目信息。
5. **依赖验证**：`check-project-has-dependency` 可在删除/迁移前判断项目依赖。
6. **白名单验证**：`get-project-white-lists` 可回读项目白名单；更新白名单必须 HITL。
7. **成员验证**：`list-project-members`（DevProd 需传 `Env`）可回读成员，确认创建者与板块架构师已自动带入。
8. **边界验证**：不把内部 `/api/project/...` REST、录制用例或页面接口伪装成公开 CLI 命令。

## 10. Cleanup

本 Skill 创建的测试项目资源，清理顺序必须是：下线并删除项目内任务、模型、资源文件和发布对象 → 移除或回滚项目成员与白名单 → 检查 `check-project-has-dependency` → 删除项目。DevProd 模式需要分别关注 DEV / PROD 环境对象。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices

- 项目创建是所有数据开发 Skill 的前置依赖，当前公开 CLI 已支持直接创建项目。
- 先用 `get-project-by-name` 查重，避免重复申请同名项目。
- 项目模式必须由用户确认：Basic 与 DevProd 的资源、成员、发布链路和清理口径不同。
- DevProd 项目创建前必须确认数据板块（DEV_PROD 模式）与 dev / prod 两套计算源全部就绪；租户内计算源全部被绑定时需先新建计算源。
- 删除或迁移前必须先做依赖校验，存在任务、模型、资源或发布对象时不能直接删除。
- 白名单更新需先回读旧值并合并，禁止用空列表或单个新值覆盖未知存量。
- 页面内部 REST 可作为业务理解参考，外部执行必须使用公开 OpenAPI。

### 平台限制

- 命令命名：项目生命周期命令按项目模式拆分命名，不存在 `create-project` 形态；必须用 `aliyun dataphin-public --help` 全量核对后再判断能力边界。
- 参数形态：创建 / 更新命令使用单一 `--create-command` JSON 对象参数，不是扁平 flag；JSON 字段名使用 OpenAPI PascalCase。
- 页面内部 `/api/project/...` REST 只作业务语义参考，不作为外部命令入口。

### 常见坑

#### [Agent 自主发现] 按 create-project 查找误判能力缺失
- 现象：`aliyun dataphin-public --help` 中没有 `create-project`，只有 `create-basic-project` / `create-dev-prod-project`。
- 结论：项目生命周期命令按模式拆分命名；必须先 `--help` 全量核对，不能按假设的命令名 grep 就下“未公开”结论。

#### [实战验证] 项目成员由系统自动带入
- 现象：创建项目后页面上已有成员，但创建参数里没有成员字段。
- 结论：创建者（当前 AK 对应账号）与数据板块架构师（`create-biz-unit` 的 BizUnitAccountList）会被系统自动带入为项目成员，无需显式添加；其余成员用 `add-project-member` 补充。

#### [实战验证] DevProd 计算源全部被占用
- 现象：`list-compute-sources` 返回的所有 MAX_COMPUTE 计算源 `BindProject: true`。
- 结论：同一 MaxCompute project 只能绑定一个计算源；新建项目时需先 `create-compute-source` 新建 dev / prod 两套，再传入项目创建参数。

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
