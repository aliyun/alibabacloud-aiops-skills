---
name: manage-lookup-table
description: |-
  管理 Dataphin 数据标准码表（Lookup Table）的完整生命周期：创建、查询、更新、删除，码值列表整体覆盖式维护。
  触发场景：创建码表 / 新建标准代码 / 维护码值 / 更新码表 / 删除码表 / 查看码表详情 / lookup table。
  流程：get-standard-lookup-table 查询 → create-standard-lookup-table 创建 → update-standard-lookup-table 更新 → delete-standard-lookup-table 删除。
  关键点：码值元素为 JSON {Value,Name,EnglishName,Description}，Value/Name 必填且 ≤64 字符、Value 码表内唯一；码表名称目录内唯一、编码租户内唯一；无 list 型命令，查询按码表 ID 走 get；写操作需 HITL 确认。
  触发词：码表、标准代码、码值、代码值、lookup table、create-standard-lookup-table、LookupTableValueList。
---

# 数据标准码表管理 Skill

## 1. Scenario Description

在 Dataphin 资产治理「数据标准」域中管理**码表（标准代码 / Lookup Table）**。码表是一组「代码值 + 代码名称」的枚举字典（如城市码表、订单状态码表），供数据标准的值域（指定码表）引用，也是智能标准化治理（探查字段 → 抽取码表定义 → 落标）的核心产物。

本 Skill 覆盖码表的创建、查询详情、更新（含码值增删改）、删除四个原子动作。典型上游输入：对表字段做 distinct 探查得到的枚举值清单（唯一值率低、重复覆盖高的字段适合建码表）。

### Architecture

```
用户请求 → 确认参数（名称/编码/码值清单）
  → get-standard-lookup-table 查询已有码表（按 ID，避免重复创建）
  → create-standard-lookup-table 创建（返回码表 Id）
  →（可选）update-standard-lookup-table 更新（码值列表整体覆盖）
  →（可选）delete-standard-lookup-table 删除
```

### 涉及 Dataphin OpenAPI

- `CreateStandardLookupTable` — 创建码表（上线版本 v5.4.2）
- `GetStandardLookupTable` — 查询码表详情
- `UpdateStandardLookupTable` — 更新码表
- `DeleteStandardLookupTable` — 删除码表

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

执行任何写操作（create / update / delete）前必须向用户确认以下参数，禁止静默提交：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--tenant-id` | 是 | 租户 ID（19 位大整数，字符串传参） |
| `--standard-lookup-table-name` | 是（create/update） | 码表名称，**归属目录内唯一** |
| `--code` | 是（create/update） | 码表编码，**租户内唯一** |
| `--id` / `--standard-lookup-table-id` | 是（update/get/delete） | 目标码表 ID |
| `--lookup-table-value-list` | 可选 | 码值列表，每个元素一个 JSON 对象（见 §类型分支） |
| `--directory-reference` | 可选 | 归属目录，JSON `{"Directory":"/dir1/dir2"}` |
| `--description` | 可选 | 码表描述 |
| `--owner` | 可选 | 负责人用户 ID，默认为调用者 |

## 7. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/manage-lookup-table/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。本地工具命令（`configure` / `plugin` / `version`）不支持该 flag，不需携带。

## 8. Core Workflow

```bash
TENANT_ID="<19 位租户 ID，字符串>"
SESSION_ID="<继承自 alibabacloud-dataphin-skills>"
USER_AGENT="AlibabaCloud-Agent-Skills/manage-lookup-table/$SESSION_ID"

# 1) 创建码表（返回 Data = 码表 Id，记录下来供后续操作）
aliyun dataphin-public create-standard-lookup-table --tenant-id "$TENANT_ID" \
  --standard-lookup-table-name "<码表名称，如 订单状态码表>" \
  --code "<码表编码，如 ORDER_STATUS>" \
  --description "<码表描述>" \
  --lookup-table-value-list \
    '{"Value":"1","Name":"待支付","EnglishName":"PENDING","Description":"订单已创建未支付"}' \
    '{"Value":"2","Name":"已支付","EnglishName":"PAID"}' \
  --user-agent "$USER_AGENT" --format json

# 2) 查询码表详情（--nullable=false：码表不存在时抛异常而非返回 null，便于判断）
aliyun dataphin-public get-standard-lookup-table --tenant-id "$TENANT_ID" \
  --standard-lookup-table-id "<码表 ID>" --nullable false \
  --user-agent "$USER_AGENT" --format json

# 3) 更新码表（⚠ 码值列表为整体覆盖语义：先 get 拿全量码值，改完整体回传）
aliyun dataphin-public update-standard-lookup-table --tenant-id "$TENANT_ID" \
  --id "<码表 ID>" \
  --standard-lookup-table-name "<码表名称>" \
  --code "<码表编码>" \
  --lookup-table-value-list \
    '{"Value":"1","Name":"待支付","EnglishName":"PENDING"}' \
    '{"Value":"2","Name":"已支付","EnglishName":"PAID"}' \
    '{"Value":"3","Name":"已退款","EnglishName":"REFUNDED"}' \
  --user-agent "$USER_AGENT" --format json

# 4) 删除码表（不可回滚；被标准值域引用的码表删除会失败，先解除引用）
aliyun dataphin-public delete-standard-lookup-table --tenant-id "$TENANT_ID" \
  --standard-lookup-table-id "<码表 ID>" \
  --user-agent "$USER_AGENT" --format json
```

### 类型分支：lookup-table-value-list 码值元素

`--lookup-table-value-list` 每个元素是一个 JSON 对象（CLI list 参数，多个元素空格分隔）：

| 字段 | 必填 | 约束 |
|------|------|------|
| `Value` | 是 | 代码值，**码表内唯一，最多 64 字符**（常直接取字段 distinct 值） |
| `Name` | 是 | 代码名称，**最多 64 字符** |
| `EnglishName` | 否 | 代码英文名 |
| `Description` | 否 | 代码描述 |

业务约束（与控制台一致）：每张码表最多 10000 个码值；从字段值逆向抽取码表时，`Value` 与字段值完全一致、`Name` 可由语义生成，提交前需检查唯一性与长度，否则创建/更新报「不符合输入规范」。

### 执行前确认（写操作必备 / HITL）

> 本 skill 的 create / update / delete 均为写操作，执行前必须向用户二次确认：
> - 即将执行的命令全文（脱敏后）
> - 影响范围（哪个 tenant / 目录 / 码表；update 是整体覆盖，会替换全部码值）
> - 是否可回滚（delete 不可回滚；update 覆盖前应先 get 备份原码值）
> - 替代方案（可先用 `--cli-dry-run` 只打印请求不实际调用）
>
> 仅当用户明确回复「确认 / yes / 执行」后才发起写命令。

## 9. Success Verification

写操作「同步返回 Code: OK」不等于业务生效，需两步校验：

1. 同步响应含 `Code: OK`，create 返回 `Data`（码表 Id）
2. `get-standard-lookup-table --nullable false` 反查：名称/编码/码值数与预期一致

```bash
aliyun dataphin-public get-standard-lookup-table --tenant-id "$TENANT_ID" \
  --standard-lookup-table-id "<码表 ID>" --nullable false \
  --user-agent "$USER_AGENT" --format json
```

## 10. Cleanup

```bash
# 删除测试码表（不可回滚，需二次确认；被标准值域引用时需先在标准侧解除引用）
aliyun dataphin-public delete-standard-lookup-table --tenant-id "$TENANT_ID" \
  --standard-lookup-table-id "<码表 ID>" \
  --user-agent "$USER_AGENT" --format json
```

## 11. Command Tables

详见 [references/related-commands.md](./references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参，示例中用引号包住
2. 写操作（create / update / delete）执行前必须 HITL 二次确认
3. update 是**整体覆盖**：先 `get` 拿全量码值，在其基础上增删改后整体回传，防止丢码值
4. 读命令带 `--nullable false`，码表不存在立刻抛异常，避免拿到 null 误判成功
5. 「常见坑」每条标注来源 `[Agent 自主发现] / [人工注入]`

### ✗ 平台限制

#### ✗ 无 list 型码表查询命令
- 限制描述：OpenAPI 只有 `get-standard-lookup-table`（按 ID 查详情），无「分页列出所有码表」命令；不知道码表 ID 时无法用 CLI 枚举
- 替代方案：让用户从控制台「标准-标准代码（码表）」页获取码表 ID，或在创建时记录返回的 `Data`（码表 Id）

### 常见坑

#### [人工注入] 码值直接取字段值可能不符合输入规范
- 现象：从字段 distinct 值逆向生成码表时，原始值可能超 64 字符或含重复值，应用时报「代码值不符合输入规范：需要码表内唯一，最多输入64字符」
- 结论：提交前先在本地对码值清单做去重与长度校验，超限的截断需经用户确认

#### [人工注入] 码表编码租户内唯一、名称目录内唯一
- 现象：与已有码表重名/重码时创建失败
- 结论：创建前与用户确认编码命名（建议大写下划线风格，如 `ORDER_STATUS`）；重名报错时改名重试而非静默换名

### Reference Links

- [references/cli-installation-guide.md](./references/cli-installation-guide.md)
- [../../ram-policies.md](../../ram-policies.md)
- [references/acceptance-criteria.md](./references/acceptance-criteria.md)
- [references/related-commands.md](./references/related-commands.md)
- 关联 skill：`manage-data-standard`（标准生命周期，值域可引用本 skill 产出的码表）、`manage-standard-mapping`（字段-标准落标映射）
