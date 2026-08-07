---
name: manage-data-standard
description: |
  管理 Dataphin 数据标准的完整生命周期：创建、更新、发布、下线、删除、查询，支持元数据监控（METADATA）与数据质量监控（QUALITY）。
  触发场景：管理数据标准 / 新建标准 / 修改标准 / 发布标准 / 下线标准 / 删除标准 / 查询标准列表 / 质量规则 / 元数据监控。
  流程：list-standards/get-standard 查询 → create-standard 创建 → publish-standard 发布 → update-standard 修订 → offline/delete-standard 下线删除。
  关键点：19 位大整数 ID 用字符串传参；monitor-config 的 Type（METADATA/QUALITY）决定字段组合；写操作需 HITL 确认。
  触发词：数据标准、管理标准、发布标准、下线标准、删除标准、标准列表、质量规则、元数据监控、data standard、METADATA、QUALITY。
---

# 数据标准管理 Skill

## 1. Scenario Description

在 Dataphin 资产治理中对「数据标准」做全生命周期管理。数据标准挂在「标准模板（StandardTemplate）+ 标准集（StandardSet）」之下，可为其配置元数据监控（METADATA，仅校验元数据本身）或数据质量监控（QUALITY，对实际表数据做指标+阈值校验）。

本 Skill 覆盖标准的创建、修订、提交审批与发布、下线、删除、查询等原子动作，是 `create-standard`（仅创建）与 `update-standard`（仅更新）之上的完整生命周期管理入口。

### Architecture

```
用户请求 → 确认参数
  → list-standards / get-standard 查询定位（只读）
  → create-standard 创建（DRAFT 草稿态）
  → publish-standard 提交审批 + 自动发布（DEV → PROD）
  →（可选）update-standard 修订已有标准
  →（可选）offline-standard 下线 / delete-standard 删除
```

### 涉及 Dataphin OpenAPI

- `CreateStandard` — 创建数据标准
- `UpdateStandard` — 更新（修订）数据标准
- `PublishStandard` — 提交审批并（默认）自动发布
- `OfflineStandard` — 下线标准
- `DeleteStandard` — 删除标准
- `ListStandards` — 分页查询标准列表
- `GetStandard` — 获取标准详情

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

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

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

### Pre-check: Aliyun CLI >= 3.4.8 required

> 执行 `aliyun version` 确认版本 >= 3.4.8；不达标见 [references/cli-installation-guide.md](./references/cli-installation-guide.md)。

### Pre-check: Aliyun CLI plugin update required

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 skill 最小权限见 [../../ram-policies.md](../../ram-policies.md)。

## 6. IMPORTANT: Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or
> use default values without explicit user approval.

执行任何写操作（create / update / publish / offline / delete）前必须向用户确认以下参数，禁止静默提交：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--tenant-id` | 是 | 租户 ID（19 位大整数，字符串传参） |
| `--standard-set-reference` | 是（create/update） | 所属标准集引用，JSON，如 `{"Id":22}` |
| `--standard-template-reference` | 是（create/update） | 所属标准模板引用，JSON，如 `{"Id":11}` |
| `--standard-id` | 是（update/publish/offline/delete/get） | 目标标准 ID |
| `--standard-status` | 是（update） | 标准状态 |
| `--standard-general-monitor-config` | 可选 | 标准监控配置，含 Type 分支，详见 [references/monitor-config-matrix.md](./references/monitor-config-matrix.md) |
| `--comment` | 是（publish/offline） | 审核备注，最多 128 字符 |
| `--standard-stage` | 可选 | 阶段 DEV / PROD |

## 7. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/manage-data-standard/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。本地工具命令（`configure` / `plugin` / `version`）不支持该 flag，不需携带。

## 8. Core Workflow

```bash
TENANT_ID="<19 位租户 ID，字符串>"
SESSION_ID="<继承自 alibabacloud-dataphin-skills>"
USER_AGENT="AlibabaCloud-Agent-Skills/manage-data-standard/$SESSION_ID"

# 1) 查询已有标准（定位是否已存在，避免重复创建）
aliyun dataphin-public list-standards --tenant-id "$TENANT_ID" \
  --standard-stage DEV --keyword "<标准名/编码关键字>" \
  --page-no 1 --page-size 20 \
  --user-agent "$USER_AGENT" --format json

# 2) 查看某个标准详情
aliyun dataphin-public get-standard --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" --standard-stage prod --need-relation true \
  --user-agent "$USER_AGENT" --format json

# 3) 创建标准（新建后为 DRAFT 草稿态；监控配置见 §类型分支）
aliyun dataphin-public create-standard --tenant-id "$TENANT_ID" \
  --standard-template-reference '{"Id":11}' \
  --standard-set-reference '{"Id":22}' \
  --description "<标准描述>" \
  --standard-general-monitor-config '<见 references/monitor-config-matrix.md>' \
  --user-agent "$USER_AGENT" --format json

# 4) 提交审批并发布（--auto-publish-after-approval 默认 true）
aliyun dataphin-public publish-standard --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" --comment "<审核备注>" \
  --standard-stage DEV \
  --user-agent "$USER_AGENT" --format json

# 5) 更新（修订）已有标准
aliyun dataphin-public update-standard --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" \
  --standard-template-reference '{"Id":11}' \
  --standard-set-reference '{"Id":22}' \
  --standard-status "<标准状态>" \
  --description "<新描述>" \
  --user-agent "$USER_AGENT" --format json

# 6) 下线标准
aliyun dataphin-public offline-standard --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" --comment "<下线原因>" \
  --user-agent "$USER_AGENT" --format json

# 7) 删除标准
aliyun dataphin-public delete-standard --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" \
  --user-agent "$USER_AGENT" --format json
```

### 类型分支：standard-general-monitor-config

`--standard-general-monitor-config` 内的 `StandardMonitorConfigList[]` 每个元素由 `Type` 决定字段组合：

- **METADATA**：仅校验元数据本身（如字段是否有描述、命名合规），无需质量模板字段
- **QUALITY**：对实际表数据做指标统计 + 阈值校验，`RuleSubType=CUSTOMIZED` 时需 `QualityRuleTemplate` / `RuleConfigList` / `RuleValidateConfigList`

完整 JSON 骨架、字段矩阵与分支速查见 [references/monitor-config-matrix.md](./references/monitor-config-matrix.md)。

### 执行前确认（写操作必备 / HITL）

> 本 skill 的 create / update / publish / offline / delete 均为写操作，执行前必须向用户二次确认：
> - 即将执行的命令全文（脱敏后）
> - 影响范围（哪个 tenant / 标准集 / 标准）
> - 是否可回滚（delete 不可回滚；offline 可重新发布）
> - 替代方案（可先用 `--cli-dry-run` 只打印请求不实际调用）
>
> 仅当用户明确回复「确认 / yes / 执行」后才发起写命令。

## 9. Success Verification

写操作「同步返回 Code: OK」不等于业务生效，需三步校验：

1. 同步响应含 `Code: OK` / 返回 StandardId
2. `list-standards` / `get-standard` 反查命中目标标准
3. 发布场景轮询状态：DEV Stage `IN_PUBLISH` → PROD Stage `ACTIVE` 表示已生效

```bash
# 反查确认（发布后查 PROD 阶段是否 ACTIVE）
aliyun dataphin-public get-standard --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" --standard-stage prod \
  --user-agent "$USER_AGENT" --format json
```

## 10. Cleanup

```bash
# 下线（可恢复）
aliyun dataphin-public offline-standard --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" --comment "cleanup" \
  --user-agent "$USER_AGENT" --format json

# 删除（不可回滚，需二次确认）
aliyun dataphin-public delete-standard --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" \
  --user-agent "$USER_AGENT" --format json
```

## 11. Command Tables

详见 [references/related-commands.md](./references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参，示例中用引号包住
2. 写操作（create / update / publish / offline / delete）执行前必须 HITL 二次确认
3. `list-standards` 的 `--standard-stage` 为必填（DEV / PROD），漏传会报参数错误
4. 删除前先 `get-standard` 确认目标，delete 不可回滚
5. 「常见坑」每条标注来源 `[Agent 自主发现] / [人工注入]`

### ✗ 平台限制

#### ✗ 命令名单复数差异
- 限制描述：查询列表命令为 `list-standards`（复数），非 `list-standard`（单数）；填错会报「命令不存在」
- 替代方案：统一以 `aliyun dataphin-public --help` 输出的命令名为准

### 常见坑

#### [Agent 自主发现] list-standards 缺 standard-stage 报错
- 现象：不传 `--standard-stage` 直接查列表会报参数缺失
- 结论：`--standard-stage`（DEV / PROD）为必填项，查询前必须指定阶段

#### [Agent 自主发现] update 与 create 参数差异
- 现象：`update-standard` 比 `create-standard` 多 `--standard-id` 和 `--standard-status` 两个必填项
- 结论：修订走 update 时须先拿到 standard-id 与当前状态，可先 `get-standard` 获取

### Reference Links

- [references/cli-installation-guide.md](./references/cli-installation-guide.md)
- [../../ram-policies.md](../../ram-policies.md)
- [references/acceptance-criteria.md](./references/acceptance-criteria.md)
- [references/related-commands.md](./references/related-commands.md)
- [references/monitor-config-matrix.md](./references/monitor-config-matrix.md)
- 单动作 skill：`create-standard`、`update-standard`（通过套件入口 alibabacloud-dataphin-skills 的场景路由表加载，本 skill 不直接引用其文件）
