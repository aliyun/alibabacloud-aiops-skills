---
name: manage-biz-metric
description: |-
  管理 Dataphin 业务指标定义的创建、更新、查询和删除。
  当用户要定义 GMV、DAU、订单转化率等可复用业务口径，或维护业务指标名称、展示名、口径、目录、负责人、可见范围、相关指标、关联技术指标时进入。
  触发词：业务指标、业务口径、指标定义、biz metric、GMV、DAU、转化率、指标关系图、业务指标口径。
  关键限制：OpenAPI 仅覆盖业务指标定义 CRUD；发布/上架/下架属于资产上架链路，需另走资产管理能力；写操作需 HITL 确认。
---

# 业务指标管理 Skill

## 1. Scenario Description

在 Dataphin 资产治理 / 指标管理中对「业务指标（Biz Metric）」做定义级管理。业务指标用于把 GMV、DAU、转化率、支付订单数等业务度量沉淀为统一口径，供数据团队、业务团队和下游应用复用。

本 Skill 覆盖 `dataphin-public` 已开放的业务指标 OpenAPI：创建、更新、按名称查询、删除。它解决的是「业务指标定义」本身的维护，包括名称、展示名、指标口径、目录归属、业务负责人、标签、可见范围、相关业务指标、关联技术指标和指标关系图等。

**重要边界**：业务指标在资产目录中的发布/上架/下架不由 `create-biz-metric` / `update-biz-metric` 直接完成。发布/上架能力属于资产上架管理链路，当前 `dataphin-public` 业务指标命令仅开放定义 CRUD；如用户要求“发布指标”“上架指标”“下架指标”，必须先说明该边界，再路由到资产上架相关能力或请求人工确认替代方案。

**Architecture**：`Dataphin Tenant → Catalog（指标目录）→ BizMetric（业务指标定义）→ 相关业务指标 / 技术指标 / 指标关系图 → 资产上架链路`

### 涉及 Dataphin OpenAPI

- `CreateBizMetric` — 创建业务指标定义
- `UpdateBizMetric` — 更新业务指标定义
- `GetBizMetricByName` — 按名称查询草稿态或已发布业务指标详情
- `DeleteBizMetric` — 删除业务指标定义

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
| `--biz-metric-name` | 是 | 业务指标英文名/编码；租户内唯一 | — |
| `--new-name` | update 可选 | 更新后的业务指标名称 | — |
| `--display-name` | 建议 | 展示名，便于业务用户理解 | — |
| `--metric-definition` | 建议 | 指标口径；引用其他业务指标时用半角中括号包裹，如 `[GMV] / [订单数]` | — |
| `--catalog-ids` | 建议 | 归属目录 ID 列表；需确认目录已存在，CLI list 参数用空格分隔多个值 | — |
| `--biz-owner-name` | 可选 | 业务负责人账号用户名，非展示昵称 | — |
| `--labels` | 可选 | 资产标签列表，CLI list 参数用空格分隔多个值 | — |
| `--related-biz-metrics` | 可选 | 相关业务指标列表；开启关系图前至少要有相关指标 | — |
| `--associated-tech-metric-full-names` | 可选 | 关联技术指标全名列表，格式为“所属表全名.指标名称” | — |
| `--metric-relation-diagram-switch-open` | 可选 | 是否开启指标关系图；没有相关指标时会自动关闭 | `false` |
| `--view-scope` | 可选 | 可见范围对象 | — |
| `--custom-attribute` | 可选 | 自定义属性数组 | — |
| `--draft` | get 必填 | 查询草稿态或已发布详情：`true` 草稿态，`false` 已发布 | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-biz-metric/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public get-biz-metric-by-name --tenant-id "1234567890123456789" \
  --biz-metric-name "gmv" --draft true \
  --user-agent AlibabaCloud-Agent-Skills/manage-biz-metric/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/manage-biz-metric/$SESSION_ID"

# 0) 前置：确认这是“业务指标定义 CRUD”需求。
#    若用户要求发布/上架/下架业务指标，先说明当前 OpenAPI 边界：业务指标命令不含 publish/online/offline。

# 1) 查询业务指标是否已存在（创建前防重、更新/删除前定位）
aliyun dataphin-public get-biz-metric-by-name --tenant-id "$TENANT_ID" \
  --biz-metric-name "<业务指标名称>" \
  --draft true \
  --user-agent "$UA" --format json

# 2) 创建业务指标定义
aliyun dataphin-public create-biz-metric --tenant-id "$TENANT_ID" \
  --biz-metric-name "<业务指标名称>" \
  --display-name "<业务展示名>" \
  --description "<指标说明>" \
  --metric-definition "<指标口径，如 支付金额/订单数 或 [GMV]/[订单数]>" \
  --catalog-ids "<指标目录 ID>" \
  --biz-owner-name "<负责人账号用户名>" \
  --labels "核心指标" \
  --metric-relation-diagram-switch-open false \
  --operate-instruction-enabled false \
  --user-agent "$UA" --format json

# 3) 回读草稿态详情，确认名称、展示名、口径和目录正确
aliyun dataphin-public get-biz-metric-by-name --tenant-id "$TENANT_ID" \
  --biz-metric-name "<业务指标名称>" \
  --draft true \
  --user-agent "$UA" --format json

# 4) 更新业务指标定义（更新前先回读现值，避免误清空目录、标签、关联指标等可选字段）
aliyun dataphin-public update-biz-metric --tenant-id "$TENANT_ID" \
  --biz-metric-name "<当前业务指标名称>" \
  --display-name "<新展示名>" \
  --description "<新指标说明>" \
  --metric-definition "<新指标口径>" \
  --catalog-ids "<需保留的指标目录 ID>" \
  --metric-relation-diagram-switch-open false \
  --user-agent "$UA" --format json

# 5) 查询已发布态详情（若该指标已通过资产上架链路发布）
aliyun dataphin-public get-biz-metric-by-name --tenant-id "$TENANT_ID" \
  --biz-metric-name "<业务指标名称>" \
  --draft false \
  --user-agent "$UA" --format json

# 6) 删除业务指标定义（不可回滚；删除前必须确认无下游引用）
aliyun dataphin-public delete-biz-metric --tenant-id "$TENANT_ID" \
  --biz-metric-name "<业务指标名称>" \
  --user-agent "$UA" --format json
```

### 指标口径与关联关系

| 配置项 | 规则 | 示例 |
|---|---|---|
| `--metric-definition` | 普通文本或计算表达式；引用业务指标时用半角中括号包裹 | `支付金额 / 下单用户数`、`[GMV] / [订单数]` |
| `--related-biz-metrics` | 相关业务指标列表；用于关系图和业务解释 | `[ {"Name":"gmv","Relation":"组成"} ]` |
| `--associated-tech-metric-full-names` | 技术指标全名数组；一个技术指标只能关联一个业务指标 | `["maxcompute.project.table.pay_amount"]` |
| `--metric-relation-diagram-expression` | 仅关系图开启时读取；指标名需半角中括号包裹 | `[GMV] / [订单数]` |

> [Agent 自主发现] 内部资产上架接口使用 `metaBizIndex.metricDefinition`、`shelveDirectoryIds` 等 camelCase 字段；OpenAPI CLI 使用独立参数与 PascalCase API 字段映射。不要把内部 REST 字段直接写到 CLI 参数中。

### 发布 / 上架 / 下架边界

当前业务指标 OpenAPI 命令不包含 `publish-biz-metric`、`online-biz-metric`、`offline-biz-metric` 或 `list-biz-metrics`。因此：

- 用户说“创建/更新/查询/删除业务指标定义” → 使用本 Skill。
- 用户说“发布/上架/下架业务指标” → 先告知该动作属于资产上架管理链路，不是本 Skill 的直接 OpenAPI 能力。
- 如果环境已有资产上架 Skill 或内部流程，需经用户确认后切换到对应能力；不能伪造不存在的 CLI 命令。

## 9. Success Verification

每次执行后必须进行结果验证：

1. **create 验证**：`create-biz-metric` 返回成功后，立即 `get-biz-metric-by-name --draft true` 回读字段。
2. **update 验证**：`update-biz-metric` 返回成功后，回读确认展示名、描述、口径、目录、标签等目标字段已变化。
3. **get 验证**：用户要求查草稿态时使用 `--draft true`；查已发布态时使用 `--draft false`，不要混淆。
4. **delete 验证**：删除后再次 `get-biz-metric-by-name --draft true`，目标应不存在或返回空/明确错误。
5. **边界验证**：遇到发布/上架/下架需求时，不输出不存在的 CLI；说明需资产上架链路。

## 10. Cleanup

业务指标删除不可回滚，清理前必须确认：

- 无下游报表、指标关系图、相关业务指标、技术指标绑定或资产目录引用依赖。
- 若指标已发布/上架，先按资产上架链路完成下架，再删除定义。
- 删除前向用户展示目标名称、展示名、指标口径、目录和依赖检查结论，并等待明确确认。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices

- 业务指标名称需租户内唯一，且只使用英文字母、数字及允许的特殊符号。
- 业务展示名尽量使用中文业务语义，名称/编码保持稳定，避免下游引用失效。
- `--metric-definition` 写给业务用户看，应包含清晰口径、统计范围、时间口径和过滤条件。
- 引用其他业务指标时必须用半角中括号 `[ ]` 包裹指标名称。
- 开启指标关系图前，先配置 `--related-biz-metrics`；否则关系图开关可能自动关闭。
- 关联技术指标前确认该技术指标没有被其他业务指标占用。
- update 前先 get 回读现值；保留目录、标签、关联指标、自定义属性时需要完整回填。
- 所有写操作前必须 HITL 二次确认，所有 API 命令必须携带 `--user-agent`。
