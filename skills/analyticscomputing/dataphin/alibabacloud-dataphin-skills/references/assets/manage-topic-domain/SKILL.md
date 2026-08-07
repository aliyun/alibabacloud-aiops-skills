---
name: manage-topic-domain
description: |-
  管理 Dataphin 主题域（Data Domain）的完整生命周期：查询、创建、更新、删除，用于组织数据仓库的业务分层架构。
  主题域挂在「数据板块（业务单元 BizUnit）」之下，创建/更新/删除必须先确定所属 --biz-unit-id。
  触发场景：管理主题域 / 新建主题域 / 修改主题域 / 删除主题域 / 查询主题域列表 / 组织数据仓库分层 / 数据板块下建主题域 / 配置上级主题域（层级）。
  流程：list-data-domains/get-data-domain-info 查询 → create-data-domain 创建 → update-data-domain 修订 → delete-data-domain 删除。
  关键点：主题域无发布流程，创建即生效；biz-unit-id 为硬前置依赖；大整数 ID 用字符串传参；写操作需 HITL 确认。
  触发词：主题域、数据域、data domain、topic domain、data-domain、数据板块、业务单元、biz-unit、数据仓库分层、主题域列表、上级主题域。
---

# 主题域管理 Skill

## 1. Scenario Description

在 Dataphin 数据规划 / 数据资产建设中对「主题域（Data Domain）」做全生命周期管理。主题域是数据仓库逻辑分层的组织单元，用于把维度表、事实表、汇总表按业务主题归类。

主题域**必须挂在「数据板块（业务单元 BizUnit）」之下**——`--biz-unit-id` 是创建、更新、删除的硬前置依赖。主题域之间还可通过 `--parent-id` 组织成上下级层级树。

本 Skill 覆盖主题域的查询、创建、修订、删除等原子动作。与数据标准不同，**主题域没有 DEV/PROD 发布流程，创建即生效**，生命周期为：查询 → 创建 → 更新 → 删除。

**Architecture**：`Dataphin Tenant → BizUnit（数据板块）→ Data Domain（主题域，可多级层级）→ 逻辑表（维/事实/汇总）`

### 涉及 Dataphin OpenAPI

- `ListDataDomains` — 查询主题域列表
- `GetDataDomainInfo` — 获取主题域详情
- `CreateDataDomain` — 创建主题域
- `UpdateDataDomain` — 更新主题域
- `DeleteDataDomain` — 删除主题域

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

最小权限策略详见 [套件级 RAM 策略](../../ram-policies.md)。

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
| `--biz-unit-id` | 是（create/update/delete） | 所属数据板块（业务单元）ID | — |
| `--data-domain-id` | 是（update/delete/get） | 目标主题域 ID | — |
| `--data-domain-name` | 是（create/update） | 主题域**编码**（英文名，唯一标识） | — |
| `--display-name` | 是（create/update） | 主题域**展示名**（中文名） | — |
| `--abbreviation` | 是（create/update） | 主题域缩写 | — |
| `--description` | 否 | 主题域描述 | — |
| `--parent-id` | 否 | 上级主题域 ID（构建层级树时用） | 无（顶级） |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-topic-domain/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public list-data-domains --tenant-id "1234567890123456789" \
  --user-agent AlibabaCloud-Agent-Skills/manage-topic-domain/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
BIZ_UNIT_ID="<所属数据板块 ID>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/manage-topic-domain/$SESSION_ID"

# 0) 前置：确认数据板块（BizUnit）已存在。主题域必须挂在某个 biz-unit 下。
#    若不知道 biz-unit-id，先用「数据板块列表」相关能力获取，或询问用户。

# 1) 查询主题域列表（定位是否已存在，避免重复创建）
aliyun dataphin-public list-data-domains --tenant-id "$TENANT_ID" \
  --biz-unit-id-list "$BIZ_UNIT_ID" \
  --keyword "<主题域名/编码关键字>" \
  --user-agent "$UA" --format json

# 2) 查看某个主题域详情
aliyun dataphin-public get-data-domain-info --tenant-id "$TENANT_ID" \
  --data-domain-id "<主题域 ID>" \
  --user-agent "$UA" --format json

# 3) 创建主题域（创建即生效，无发布流程）
aliyun dataphin-public create-data-domain --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --data-domain-name "<主题域编码，如 trade>" \
  --display-name "<主题域展示名，如 交易域>" \
  --abbreviation "<缩写，如 trd>" \
  --description "<描述>" \
  --user-agent "$UA" --format json
# 如需挂在某个上级主题域下，追加 --parent-id "<上级主题域 ID>"

# 4) 更新（修订）已有主题域（注意：create 的全部必填字段 update 同样必填）
aliyun dataphin-public update-data-domain --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --data-domain-id "<主题域 ID>" \
  --data-domain-name "<主题域编码>" \
  --display-name "<新展示名>" \
  --abbreviation "<缩写>" \
  --description "<新描述>" \
  --user-agent "$UA" --format json

# 5) 删除主题域（不可回滚）
aliyun dataphin-public delete-data-domain --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --data-domain-id "<主题域 ID>" \
  --user-agent "$UA" --format json
```

### 字段语义速查

| CLI 参数 | 业务含义 | 说明 |
|---|---|---|
| `--data-domain-name` | 主题域**编码** | 英文唯一标识，如 `trade`；建库后不建议改 |
| `--display-name` | 主题域**展示名** | 中文名，如 `交易域` |
| `--abbreviation` | 缩写 | 用于逻辑表命名前缀拼接，如 `trd` |
| `--parent-id` | 上级主题域 ID | 不传 = 顶级主题域；传了 = 挂在该上级下 |
| `--biz-unit-id` | 数据板块 ID | 主题域的归属容器，硬前置 |

### 执行前确认（**写操作必备 / HITL**）

> 本 skill 的 create / update / delete 均为写操作，执行前必须向用户二次确认：
> - 即将执行的命令全文（脱敏后）
> - 影响范围（哪个 tenant / biz-unit / 主题域）
> - 是否可回滚（delete 不可回滚；update 会覆盖原有编码/展示名/缩写）
> - 替代方案（可先用 `--cli-dry-run` 只打印请求不实际调用）
>
> 仅当用户明确回复「确认 / yes / 执行」后才发起写命令。

## 9. Success Verification

写操作「同步返回 Code: OK」不等于业务生效，需两步校验（详见 [references/acceptance-criteria.md](references/acceptance-criteria.md)）：

1. 同步响应含 `Code: OK`
2. `list-data-domains`（按 `--biz-unit-id-list` + `--keyword` 过滤）/ `get-data-domain-info` 反查命中目标主题域

```bash
# 反查确认（创建/更新后按 biz-unit + 关键字过滤）
aliyun dataphin-public list-data-domains --tenant-id "$TENANT_ID" \
  --biz-unit-id-list "$BIZ_UNIT_ID" --keyword "<主题域编码>" \
  --user-agent "$UA" --format json
```

> 主题域**无异步发布状态**，不需要轮询 PublishStatus/Stage。同步 Code: OK + 反查命中即视为生效。

## 10. Cleanup

```bash
# 删除主题域（不可回滚，需二次确认；删除前先 get 确认目标）
aliyun dataphin-public delete-data-domain --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --data-domain-id "<主题域 ID>" \
  --user-agent "$UA" --format json
```

> 删除主题域前须确保其下已无关联逻辑表（维/事实/汇总），否则服务端可能拒绝删除。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（tenant-id / biz-unit-id / data-domain-id / parent-id）一律字符串传参，示例中用引号包住
2. 写操作（create / update / delete）执行前必须 HITL 二次确认
3. 创建前先 `list-data-domains` 按 `--biz-unit-id-list` + `--keyword` 查重，避免重复创建
4. 删除前先 `get-data-domain-info` 确认目标，delete 不可回滚
5. 「常见坑」每条标注来源 `[Agent 自主发现] / [人工注入]`

### ✗ 平台限制

#### ✗ 主题域必须依附数据板块
- 限制描述：主题域不能独立存在，create/update/delete 都必须传 `--biz-unit-id`（所属数据板块）。缺失 biz-unit-id 无法定位主题域。
- 替代方案：先确保目标数据板块已创建并拿到其 ID；`--biz-unit-id` 无法从主题域侧创建。

### 常见坑

#### [Agent 自主发现] update 必填字段与 create 一致
- 现象：`update-data-domain` 除多出 `--data-domain-id` 外，`--abbreviation`/`--biz-unit-id`/`--display-name`/`--data-domain-name` 与 create 一样均为必填。
- 结论：修订主题域须回传全部必填字段（可先 `get-data-domain-info` 取当前值再改），只传要改的字段会报参数缺失。

#### [Agent 自主发现] 主题域无发布流程
- 现象：主题域没有 `publish-*` / `offline-*` 命令，也无 DEV/PROD 阶段参数。
- 结论：create/update 同步返回 Code: OK 即生效，验证只需 list/get 反查，不要去轮询发布状态。

### Reference Links

- [references/cli-installation-guide.md](references/cli-installation-guide.md)
- [套件级 RAM 策略](../../ram-policies.md)
- [references/acceptance-criteria.md](references/acceptance-criteria.md)
- [references/related-commands.md](references/related-commands.md)
