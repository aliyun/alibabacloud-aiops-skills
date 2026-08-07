---
name: manage-biz-entity
description: |-
  管理 Dataphin 业务实体（业务对象/业务活动）的查询、创建、更新、上线、下线、删除。
  当用户要管理业务实体、业务对象、业务活动，或进行维度/事实/汇总逻辑建模前的业务模型配置时进入。
  触发词：业务实体、业务对象、业务活动、biz entity、biz object、biz process、BIZ_OBJECT、BIZ_PROCESS、维度建模、事实建模。
  关键限制：--type 决定 JSON 分支；BIZ_OBJECT 用 --biz-object，BIZ_PROCESS 用 --biz-process；JSON 字段必须使用 OpenAPI PascalCase；写操作需 HITL 确认。
---

# 业务实体管理 Skill

## 1. Scenario Description

在 Dataphin 数据规划 / 数据资产建设中对「业务实体（Biz Entity）」做全生命周期管理。业务实体用于描述数据仓库逻辑模型中的核心业务概念，主要分为两类：

- **业务对象（BIZ_OBJECT）**：用于承载对象类实体，如客户、商品、门店，通常用于维度逻辑表建模。
- **业务活动（BIZ_PROCESS）**：用于承载事件/快照/流程类实体，如下单、支付、发货，通常用于事实逻辑表与指标建模。

业务实体**必须挂在「数据板块（BizUnit）」与「主题域（DataDomain）」之下**。因此 `--biz-unit-id` 与 `--data-domain-id` 是创建、更新的硬前置依赖。

本 Skill 覆盖业务实体的查询、创建、修订、上线、下线、删除和按版本查询。与主题域不同，业务实体存在上线/下线生命周期：创建后通常先处于开发/草稿态，需要 `online-biz-entity` 后才能作为建模对象被下游使用。

**Architecture**：`Dataphin Tenant → BizUnit（数据板块）→ DataDomain（主题域）→ BizEntity（BIZ_OBJECT / BIZ_PROCESS）→ 维度/事实/汇总逻辑表`

### 涉及 Dataphin OpenAPI

- `ListBizEntities` — 查询业务实体列表
- `GetBizEntityInfo` — 获取业务实体详情
- `GetBizEntityInfoByVersion` — 按版本获取业务实体详情
- `CreateBizEntity` — 创建业务实体
- `UpdateBizEntity` — 更新业务实体
- `OnlineBizEntity` — 上线业务实体
- `OfflineBizEntity` — 下线业务实体
- `DeleteBizEntity` — 删除业务实体

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

执行任何写操作（create / update / online / offline / delete）前必须向用户确认以下参数，禁止静默提交：

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--tenant-id` | 是 | 租户 ID（大整数，**字符串传**） | — |
| `--biz-unit-id` | 是（create/update/online/offline/delete） | 所属数据板块（业务单元）ID | — |
| `--data-domain-id` | 是（create/update） | 所属主题域 ID | — |
| `--biz-entity-id` | 是（get/update/online/offline/delete/by-version） | 目标业务实体 ID | — |
| `--type` | 是 | 业务实体大类：`BIZ_OBJECT` 或 `BIZ_PROCESS` | — |
| `--biz-object` | BIZ_OBJECT 创建/更新时是 | 业务对象 JSON；仅当 `--type BIZ_OBJECT` 使用 | — |
| `--biz-process` | BIZ_PROCESS 创建/更新时是 | 业务活动 JSON；仅当 `--type BIZ_PROCESS` 使用 | — |
| `--comment` | 是（online/offline） | 上线/下线备注 | — |
| `--version-id` | 是（by-version） | 业务实体版本 ID | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-biz-entity/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public list-biz-entities --tenant-id "1234567890123456789" \
  --user-agent AlibabaCloud-Agent-Skills/manage-biz-entity/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
BIZ_UNIT_ID="<所属数据板块 ID>"
DATA_DOMAIN_ID="<所属主题域 ID>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/manage-biz-entity/$SESSION_ID"

# 0) 前置：确认数据板块与主题域已存在。业务实体必须同时挂在 biz-unit 与 data-domain 下。
#    若不知道 data-domain-id，可先使用 manage-topic-domain 的 list-data-domains 反查。

# 1) 查询业务实体列表（定位是否已存在，避免重复创建）
aliyun dataphin-public list-biz-entities --tenant-id "$TENANT_ID" \
  --keyword "<业务实体编码/展示名关键字>" \
  --filter-criteria '{"BizUnitIdList":["<数据板块 ID>"],"DataDomainIdList":["<主题域 ID>"]}' \
  --page 1 --page-size 10 \
  --user-agent "$UA" --format json

# 2) 查看某个业务实体详情
aliyun dataphin-public get-biz-entity-info --tenant-id "$TENANT_ID" \
  --type "BIZ_OBJECT" \
  --biz-entity-id "<业务实体 ID>" \
  --user-agent "$UA" --format json

# 3A) 创建业务对象（BIZ_OBJECT）：如客户、商品、门店，用于维度建模
aliyun dataphin-public create-biz-entity --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --data-domain-id "$DATA_DOMAIN_ID" \
  --type BIZ_OBJECT \
  --biz-object '{"Name":"<业务对象编码>","DisplayName":"<业务对象展示名>","Type":"NORMAL","OwnerUserId":"<负责人用户ID>","Description":"<描述>"}' \
  --user-agent "$UA" --format json

# 3B) 创建业务活动（BIZ_PROCESS）：如交易下单、支付，用于事实建模/指标建模
aliyun dataphin-public create-biz-entity --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --data-domain-id "$DATA_DOMAIN_ID" \
  --type BIZ_PROCESS \
  --biz-process '{"Name":"<业务活动编码>","DisplayName":"<业务活动展示名>","Type":"BIZ_EVENT","OwnerUserId":"<负责人用户ID>","Description":"<描述>"}' \
  --user-agent "$UA" --format json

# 4) 上线业务实体（创建后如需被下游建模使用，通常需要上线）
aliyun dataphin-public online-biz-entity --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --type "BIZ_OBJECT" \
  --biz-entity-id "<业务实体 ID>" \
  --comment "<上线备注>" \
  --user-agent "$UA" --format json

# 5) 更新业务实体（注意：按类型回填完整 JSON，关联列表不回填会被清空）
aliyun dataphin-public update-biz-entity --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --data-domain-id "$DATA_DOMAIN_ID" \
  --biz-entity-id "<业务实体 ID>" \
  --type BIZ_OBJECT \
  --biz-object '{"Name":"<业务对象编码>","DisplayName":"<新展示名>","Type":"NORMAL","OwnerUserId":"<负责人用户ID>","Description":"<新描述>","RefBizEntityIdList":[]}' \
  --user-agent "$UA" --format json

# 6) 下线业务实体
aliyun dataphin-public offline-biz-entity --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --type "BIZ_OBJECT" \
  --biz-entity-id "<业务实体 ID>" \
  --comment "<下线备注>" \
  --user-agent "$UA" --format json

# 7) 删除业务实体（不可回滚；删除前必须先确认无逻辑表/指标依赖）
aliyun dataphin-public delete-biz-entity --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --type "BIZ_OBJECT" \
  --biz-entity-id "<业务实体 ID>" \
  --user-agent "$UA" --format json
```

### 类型分支：`BIZ_OBJECT`（业务对象）

用于描述对象类实体，如客户、商品、门店。创建/更新时传 `--type BIZ_OBJECT`，并传 `--biz-object` JSON。

| JSON 字段 | 必填 | 说明 |
|---|---|---|
| `Name` | 是 | 业务对象编码，64 字符以内；仅允许字母、数字、下划线（ADB_PG 引擎编码名称长度为 40 位） |
| `DisplayName` | 是 | 展示名，64 字符以内；允许汉字、字母、数字、下划线、中划线 |
| `Type` | 是 | 业务对象细分类型：`NORMAL`（普通对象）、`ENUM`（枚举对象）、`VIRTUAL`（虚拟对象）、`HIERARCHY`（层级对象） |
| `OwnerUserId` | 创建可选，更新建议必填 | 负责人用户 ID；更新 API metadata 标记为必填 |
| `Description` | 否 | 描述，128 字符以内 |
| `ParentId` | 否 | 继承实体；仅普通对象支持，且只能继承已上线业务对象 |
| `RefBizEntityIdList` | 否 | 关联已上线业务实体 ID 列表；update 时若不传，原有关联会被清空 |

### 类型分支：`BIZ_PROCESS`（业务活动）

用于描述事件/快照/流程类实体，如下单、支付、发货。创建/更新时传 `--type BIZ_PROCESS`，并传 `--biz-process` JSON。

| JSON 字段 | 必填 | 说明 |
|---|---|---|
| `Name` | 是 | 业务活动编码，64 字符以内；仅允许字母、数字、下划线 |
| `DisplayName` | 是 | 业务活动展示名，64 字符以内 |
| `Type` | 是 | 业务活动细分类型：`BIZ_EVENT`（业务事件）、`BIZ_SNAPSHOT`（业务快照）、`BIZ_PROCESS`（业务流程） |
| `OwnerUserId` | 创建可选，更新建议必填 | 负责人用户 ID；更新 API metadata 标记为必填 |
| `Description` | 否 | 描述，128 字符以内 |
| `RefBizEntityIdList` | 否 | 关联已上线业务实体 ID 列表；update 时若不传，原有关联会被清空 |
| `BizEventEntityIdList` | 业务流程时按需 | 当 `Type=BIZ_PROCESS` 时有效：流程包含的业务事件活动 ID 列表 |
| `PreBizProcessIdList` | 业务流程时按需 | 业务流程活动的前序业务流程活动 ID 列表 |

### 字段语义速查

| CLI / JSON 字段 | 业务含义 | 说明 |
|---|---|---|
| `--type` | 业务实体大类 | 只能是 `BIZ_OBJECT` 或 `BIZ_PROCESS` |
| `BizObject.Type` | 业务对象细分类型 | `NORMAL` / `ENUM` / `VIRTUAL` / `HIERARCHY` |
| `BizProcess.Type` | 业务活动细分类型 | `BIZ_EVENT` / `BIZ_SNAPSHOT` / `BIZ_PROCESS` |
| `Name` | 编码（英文名） | 唯一标识；建成后不建议改 |
| `DisplayName` | 展示名（中文名） | 页面上可读名称 |
| `OwnerUserId` | 负责人 | 传用户 ID，非花名/昵称 |
| `RefBizEntityIdList` | 关联业务实体 | 仅允许关联已上线业务实体 |
| `--biz-unit-id` | 数据板块 ID | 归属容器，硬前置 |
| `--data-domain-id` | 主题域 ID | 归属主题域，硬前置 |

### 执行前确认（**写操作必备 / HITL**）

> 本 skill 的 create / update / online / offline / delete 均为写操作，执行前必须向用户二次确认：
> - 即将执行的命令全文（脱敏后）
> - 影响范围（哪个 tenant / biz-unit / data-domain / 业务实体）
> - 是否可回滚（delete 不可回滚；update 可能清空未回填的关联列表）
> - 替代方案（可先用 `--cli-dry-run` 只打印请求不实际调用；可先 list/get 反查）
>
> 仅当用户明确回复「确认 / yes / 执行」后才发起写命令。

## 9. Success Verification

写操作「同步返回 Code: OK」不等于业务生效，需按动作做反查校验（详见 [references/acceptance-criteria.md](references/acceptance-criteria.md)）：

1. create/update：同步响应含 `Code: OK`，再用 `list-biz-entities` 按 keyword + filter 反查，或 `get-biz-entity-info` 按 ID 回读字段。
2. online/offline：上线/下线可能存在异步状态变化，需 `list-biz-entities` / `get-biz-entity-info` 轮询确认状态字段变化。
3. delete：删除后 `get-biz-entity-info` 应查不到或返回空；若存在逻辑表/指标依赖，服务端可能拒绝删除，需先清理下游依赖。

```bash
# 反查确认（创建/更新后按 biz-unit + data-domain + keyword 过滤）
aliyun dataphin-public list-biz-entities --tenant-id "$TENANT_ID" \
  --keyword "<业务实体编码>" \
  --filter-criteria '{"BizUnitIdList":["<数据板块 ID>"],"DataDomainIdList":["<主题域 ID>"]}' \
  --user-agent "$UA" --format json
```

## 10. Cleanup

```bash
# 删除业务实体（不可回滚，需二次确认；删除前先 get/list 确认目标和依赖）
aliyun dataphin-public delete-biz-entity --tenant-id "$TENANT_ID" \
  --biz-unit-id "$BIZ_UNIT_ID" \
  --type "BIZ_OBJECT" \
  --biz-entity-id "<业务实体 ID>" \
  --user-agent "$UA" --format json
```

> 删除前须确认业务实体未被维度逻辑表、事实逻辑表、汇总逻辑表、指标或其它业务实体依赖，否则服务端可能拒绝删除。必要时先 `offline-biz-entity`，再执行删除。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（tenant-id / biz-unit-id / data-domain-id / biz-entity-id / version-id）一律字符串传参。
2. 写操作（create/update/online/offline/delete）必须执行前 HITL 二次确认。
3. `--type` 与 JSON 分支必须一致：`BIZ_OBJECT` 只传 `--biz-object`；`BIZ_PROCESS` 只传 `--biz-process`。
4. `--biz-object` / `--biz-process` 内字段必须使用 OpenAPI PascalCase（如 `DisplayName`、`OwnerUserId`），不要使用页面内部 REST 字段名。
5. update 前先 `get-biz-entity-info` 回读现值，尤其是 `RefBizEntityIdList`；未回填的关联列表会被清空。
6. 「常见坑」每条标来源 `[Agent 自主发现] / [人工注入]`。

### 常见坑

#### [Agent 自主发现] OpenAPI JSON 字段与页面内部 REST 字段不同
- 现象：页面内部接口常见字段为 `cn` / `owner` / `bizObjectType=1`，但 OpenAPI metadata 要求 `DisplayName` / `OwnerUserId` / `Type=NORMAL`。
- 结论：外部 skill 必须以 OpenAPI metadata 为准，`--biz-object` / `--biz-process` 使用 PascalCase 字段。

#### [Agent 自主发现] update-biz-entity 会清空未回填的关联列表
- 现象：OpenAPI metadata 明确标注 `RefBizEntityIdList` 在 update 时「若不填写：原有的值会被清空」。
- 结论：更新前必须先 get 回读并确认关联列表，若要保留关联，必须在 JSON 中完整回填。

#### [Agent 自主发现] online-biz-entity 的 comment 描述写成“下线备注”
- 现象：`online-biz-entity --help` 与 metadata 中 `--comment` 文案均显示为“下线备注”，但上线命令同样必填该字段。
- 结论：这是文案复用，不影响使用；上线时仍传上线备注。

### Reference Links

- [references/cli-installation-guide.md](references/cli-installation-guide.md)
- [套件级 RAM 策略](../../ram-policies.md)
- [references/acceptance-criteria.md](references/acceptance-criteria.md)
- [references/related-commands.md](references/related-commands.md)
