---
name: manage-standard-mapping
description: |-
  管理 Dataphin「字段-数据标准」落标映射关系：按资产/标准双向查询映射、批量创建有效/无效映射、置为无效映射、删除有效/无效映射。
  触发场景：落标 / 字段关联标准 / 标准映射 / 解除映射 / 查字段映射了哪些标准 / 查标准落到哪些字段。
  流程：get-asset-mapping-relations / get-belong-asset-mapping 查现状 → create-standard-mapping 建映射 → update-standard-mapping-to-invalid 置无效 → delete-standard-valid-mapping / delete-standard-invalid-mapping 删除。
  关键点：仅「已生效」标准可建有效映射；关系已在无效映射列表时由 invalid-mapping-relation-operation-type 决定转有效或跳过；GUID 列表单次上限 1000；写操作需 HITL 确认。
  触发词：落标、标准映射、映射关系、有效映射、无效映射、create-standard-mapping、get-asset-mapping-relations、落标监控。
---

# 标准落标映射管理 Skill

## 1. Scenario Description

在 Dataphin 资产治理「数据标准」域中管理**落标映射**——把「资产字段（COLUMN）/ 指标（INDEX）」与「数据标准」建立映射关系，是标准落地监控（落标）的前提。映射分两类：

- **有效映射（VALID）**：字段应遵循该标准，参与落标监控
- **无效映射（INVALID）**：明确排除的关系（“这个字段不该映射这个标准”），可防止后续误映射

本 Skill 覆盖映射的双向查询（按资产查标准 / 按归属资产查）、批量创建、置无效、删除四类原子动作。典型上游输入：智能标准化治理推荐出的「字段-标准」映射清单，经用户审核后批量应用。

### Architecture

```
用户请求 → 确认参数（标准 ID + 资产 GUID 列表）
  → get-asset-mapping-relations / get-belong-asset-mapping 查询现状（只读）
  → create-standard-mapping 批量创建映射（VALID / INVALID）
  →（可选）update-standard-mapping-to-invalid 有效映射置为无效
  →（可选）delete-standard-valid-mapping / delete-standard-invalid-mapping 删除映射
```

### 涉及 Dataphin OpenAPI

- `CreateStandardMapping` — 批量创建映射关系（含有效/无效）
- `GetAssetMappingRelations` — 按资产对象查询映射关系
- `GetBelongAssetMapping` — 按归属资产（如表）查询其下映射关系
- `UpdateStandardMappingToInvalid` — 将映射关系置为无效映射
- `DeleteStandardValidMapping` — 删除有效映射
- `DeleteStandardInvalidMapping` — 删除无效映射

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

执行任何写操作（create / update-to-invalid / delete）前必须向用户确认以下参数，禁止静默提交：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--tenant-id` | 是 | 租户 ID（19 位大整数，字符串传参） |
| `--standard-id` | 是（create/update/delete） | 目标数据标准 ID，**须为「已生效」标准** |
| `--asset-guid-list` | 是（create） | 资产 GUID 列表（字段级 GUID） |
| `--relation-type` | 可选（create，默认 VALID） | VALID 有效映射 / INVALID 无效映射 |
| `--invalid-mapping-relation-operation-type` | 可选（create，默认 SET_INVALID_TO_VALID） | 待建关系已在无效映射列表时：SET_INVALID_TO_VALID 转有效 / KEEP_INVALID_AND_SKIP 保留并跳过。**默认会把无效映射转有效，须与用户确认策略** |
| `--guid-list` / `--belong-guid-list` | 二选一（update/delete） | 按资产 GUID 或归属资产（表）GUID 圈定范围，单次上限 1000 |

## 7. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/manage-standard-mapping/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。本地工具命令（`configure` / `plugin` / `version`）不支持该 flag，不需携带。

## 8. Core Workflow

```bash
TENANT_ID="<19 位租户 ID，字符串>"
SESSION_ID="<继承自 alibabacloud-dataphin-skills>"
USER_AGENT="AlibabaCloud-Agent-Skills/manage-standard-mapping/$SESSION_ID"

# 1) 按资产查已有映射（asset-type：COLUMN 字段 / INDEX 指标；relation-type 必填）
aliyun dataphin-public get-asset-mapping-relations --tenant-id "$TENANT_ID" \
  --guid "<字段资产 GUID>" --asset-type COLUMN --relation-type VALID \
  --user-agent "$USER_AGENT" --format json

# 2) 按归属资产（表）查其下所有字段的映射
aliyun dataphin-public get-belong-asset-mapping --tenant-id "$TENANT_ID" \
  --belong-guid "<表资产 GUID>" --relation-type VALID \
  --user-agent "$USER_AGENT" --format json

# 3) 批量创建有效映射（响应 Data.SuccessCount + FailedGuidList）
aliyun dataphin-public create-standard-mapping --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" \
  --asset-guid-list "<字段GUID1>" "<字段GUID2>" \
  --relation-type VALID \
  --invalid-mapping-relation-operation-type KEEP_INVALID_AND_SKIP \
  --user-agent "$USER_AGENT" --format json

# 4) 有效映射置为无效（“这个字段不该映射这个标准”，防再次误映射）
aliyun dataphin-public update-standard-mapping-to-invalid --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" \
  --guid-list "<字段GUID1>" \
  --user-agent "$USER_AGENT" --format json

# 5) 删除有效映射（解除落标关系）
aliyun dataphin-public delete-standard-valid-mapping --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" \
  --guid-list "<字段GUID1>" \
  --user-agent "$USER_AGENT" --format json

# 6) 删除无效映射（解除排除关系，之后才能重新建有效映射）
aliyun dataphin-public delete-standard-invalid-mapping --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" \
  --guid-list "<字段GUID1>" \
  --user-agent "$USER_AGENT" --format json
```

### 类型分支：relation-type 与无效映射冲突策略

| 场景 | 参数组合 | 结果 |
|------|---------|------|
| 正常建立落标 | `--relation-type VALID`（默认） | 字段进入有效映射，参与落标监控 |
| 明确排除关系 | `--relation-type INVALID` | 记录“不该映射”，阻止后续误映射 |
| 待建关系已在无效列表 + 转有效 | `--invalid-mapping-relation-operation-type SET_INVALID_TO_VALID`（默认） | 先解除无效、再建有效（等价控制台“将无效映射置为有效映射”） |
| 待建关系已在无效列表 + 跳过 | `--invalid-mapping-relation-operation-type KEEP_INVALID_AND_SKIP` | 保留无效映射，该 GUID 进 FailedGuidList（等价控制台“跳过不添加”） |

### 执行前确认（写操作必备 / HITL）

> 本 skill 的 create / update-to-invalid / delete 均为写操作，执行前必须向用户二次确认：
> - 即将执行的命令全文（脱敏后）
> - 影响范围（哪个 tenant / 标准 / 多少个字段 GUID）
> - 无效映射冲突策略（默认 SET_INVALID_TO_VALID 会覆盖先前的排除决策，需用户明确选择）
> - 是否可回滚（delete-valid-mapping 可重建；delete-invalid-mapping 解除排除后可能被再次误映射）
>
> 仅当用户明确回复「确认 / yes / 执行」后才发起写命令。

## 9. Success Verification

写操作「同步返回 Code: OK」不等于全部生效，需两步校验：

1. `create-standard-mapping` 响应 `Data.SuccessCount` 与入参 GUID 数一致，`FailedGuidList` 为空；不为空时逐个排查失败原因（常见：标准非「已生效」、字段已不存在、关系已在无效映射列表且策略为跳过）
2. `get-asset-mapping-relations` / `get-belong-asset-mapping` 反查：目标字段的映射列表命中该标准（响应含 Guid / StandardId / StandardName / StandardCode / StandardSetId 等快照字段）

```bash
aliyun dataphin-public get-asset-mapping-relations --tenant-id "$TENANT_ID" \
  --guid "<字段资产 GUID>" --asset-type COLUMN --relation-type VALID \
  --user-agent "$USER_AGENT" --format json
```

## 10. Cleanup

```bash
# 删除测试建立的有效映射
aliyun dataphin-public delete-standard-valid-mapping --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" --guid-list "<字段GUID>" \
  --user-agent "$USER_AGENT" --format json

# 删除测试建立的无效映射
aliyun dataphin-public delete-standard-invalid-mapping --tenant-id "$TENANT_ID" \
  --standard-id "<标准 ID>" --guid-list "<字段GUID>" \
  --user-agent "$USER_AGENT" --format json
```

## 11. Command Tables

详见 [references/related-commands.md](./references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参，示例中用引号包住
2. 写操作执行前必须 HITL 二次确认，尤其是无效映射冲突策略（默认转有效，会覆盖先前排除决策）
3. 建映射前先双向反查现状，避免重复创建与覆盖
4. 批量 GUID 单次上限 1000，超限分批提交
5. 「常见坑」每条标注来源 `[Agent 自主发现] / [人工注入]`

### ✗ 平台限制

#### ✗ 仅「已生效」标准可建有效映射
- 限制描述：标准无「已生效」版本时创建有效映射失败（控制台同款校验「标准状态不存在已生效版本」）
- 替代方案：先用 `manage-data-standard` 的 `publish-standard` 把标准发布到 PROD/ACTIVE，再建映射

#### ✗ 无按标准分页列映射的独立查询命令
- 限制描述：查询入口是「按资产」（get-asset-mapping-relations）与「按归属资产」（get-belong-asset-mapping），没有「按标准 ID 列出全部映射」的 list 命令
- 替代方案：以表为单位用 `get-belong-asset-mapping` 拉取后本地按 StandardId 过滤

### 常见坑

#### [人工注入] 无效映射列表会拦截有效映射创建
- 现象：字段-标准关系已在无效映射列表时，默认策略 SET_INVALID_TO_VALID 会静默转为有效映射；若业务上该排除是有意的，会破坏先前决策
- 结论：批量应用推荐映射时先与用户确认冲突策略；保守场景一律用 KEEP_INVALID_AND_SKIP，再对 FailedGuidList 逐个人工判断

#### [人工注入] 资产 GUID 需先从资产侧获取
- 现象：本 skill 所有命令以资产 GUID 为主键，用户通常只知道表名/字段名
- 结论：先通过资产查询能力（如 `list-tables` / `query-asset-details` skill 的 GetAssetAttributes/GetCatalogAssetDetails）把「表名.字段名」解析为 GUID，再执行映射操作

### Reference Links

- [references/cli-installation-guide.md](./references/cli-installation-guide.md)
- [../../ram-policies.md](../../ram-policies.md)
- [references/acceptance-criteria.md](./references/acceptance-criteria.md)
- [references/related-commands.md](./references/related-commands.md)
- 关联 skill：`manage-data-standard`（先发布标准至已生效）、`manage-lookup-table`（码表）、`query-asset-details`（GUID 解析）
