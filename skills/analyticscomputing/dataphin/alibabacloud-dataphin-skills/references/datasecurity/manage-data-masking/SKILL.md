---
name: manage-data-masking
description: |-
  管理 Dataphin 数据脱敏规则配置的需求拆解、前置分类分级检查和公开 API 覆盖边界。
  当用户要给手机号、身份证号、邮箱、姓名等敏感字段配置掩码、加密、哈希、保留首尾、白名单绕过或验证查询脱敏效果时进入。
  触发词：数据脱敏、脱敏规则、动态脱敏、字段脱敏、手机号打星、身份证脱敏、邮箱脱敏、白名单、desensitize、masking、mask、FPE、MD5、NO_MASK。
  关键限制：当前 dataphin-public CLI 和版本感知 OpenAPI 索引未暴露脱敏规则 CRUD；本 Skill 不伪造内部 REST 为外部命令，只执行公开分类分级前置检查并输出可交付参数清单。
---

# 数据脱敏规则配置 Skill

## 1. Scenario Description

在 Dataphin 数据安全中，数据脱敏规则用于在即席查询、读写开发、资产访问等场景中保护敏感字段，例如手机号中间四位打星、身份证号保留首尾、邮箱 `@` 前遮盖、哈希或保留格式加密。

本 Skill 处理三类工作：

- **需求拆解**：把自然语言中的字段、脱敏算法、作用场景、白名单和验证口径整理成可执行参数清单。
- **公开前置检查**：使用 `dataphin-public` 已开放的数据分级分类命令确认目标字段是否已存在安全识别标签，因为脱敏规则通常依赖分类或分级。
- **能力边界提示**：当前公开 CLI 未暴露脱敏规则 CRUD / 白名单 / 默认配置 API；不要把页面内部 `/api/datasecurity/desensitization/...` REST 当作外部命令执行。

**Architecture**：`Tenant → Security Classify → Field Identify Result → Masking Requirement → Public API Gap / Internal REST Reference`

### 当前公开 OpenAPI 覆盖

可通过公开 CLI 做的前置检查：

- `ListSecurityIdentifyResults` / `GetSecurityIdentifyResult` — 查询目标字段是否已有分类分级标签。
- `ListSecurityIdentifyRecords` — 查询目标字段识别记录与分类状态。
- `GetSecurityClassify` — 回读分类与分级绑定信息。

未在当前公开 CLI / swagger 暴露的脱敏能力：

- 创建、更新、启停、删除动态脱敏规则。
- 创建、启停、删除脱敏白名单规则。
- 更新默认脱敏配置。
- 查询脱敏规则详情、按分类查询规则、验证脱敏效果。

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
> Run `aliyun version` to verify >= 3.4.8. If not installed or version too low, install/update from https://aliyuncli.alicdn.com (see [references/cli-installation-guide.md](references/cli-installation-guide.md)).

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [../../ram-policies.md](../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call, ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--tenant-id` | 是 | 租户 ID（大整数，建议字符串传） | — |
| `--table-catalog` | 是 | 表 Catalog；逻辑表通常为板块英文名，物理表为项目英文名，数据源表为 db/schema | — |
| `--table-name` | 是 | 目标表名 | — |
| `--field-name` | 是 | 需要脱敏的字段名，如 `phone`、`id_card`、`email` | — |
| `--classify-id` | 脱敏规则执行前必需 | 字段所属数据分类 ID；公开 CLI 只能回读/验证，不能创建脱敏规则 | — |
| `algorithmCode` | 需求清单必需 | 脱敏算法，如 `MASK`、`MD5`、`FPE_FF1_ENCRYPT`、`NO_MASK` 等，以租户实际枚举为准 | — |
| `ruleScopes` | 需求清单必需 | 作用范围，如业务板块、项目、平台、场景、账号、表范围 | — |
| `whiteListAccount` | 白名单场景必需 | 允许绕过脱敏的账号 | — |
| `effectiveDateRange` | 白名单场景必需 | 白名单生效起止日期 | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-data-masking/{session-id}
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/manage-data-masking/$SESSION_ID"

# 1) 核对版本感知 OpenAPI 索引与本 Skill 使用的公开前置检查命令。
#    当前索引没有脱敏规则 CRUD；不要拉取裸 dataphin-public --help 全量输出。
aliyun dataphin-public list-security-identify-results --help
aliyun dataphin-public list-security-identify-records --help
aliyun dataphin-public get-security-classify --help

# 2) 查询目标字段是否已有分类分级标签。没有标签时，应提示先完成字段分类分级。
aliyun dataphin-public list-security-identify-results --tenant-id "$TENANT_ID" \
  --keyword "<表名或字段名>" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

# 3) 对目标字段做精确识别记录回读，确认 table-catalog / table-name / field-name 口径正确。
aliyun dataphin-public list-security-identify-records --tenant-id "$TENANT_ID" \
  --table-catalog "<项目英文名或板块英文名或数据源 schema>" \
  --table-name "<表名>" \
  --field-name "<字段名>" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

# 4) 回读分类详情，确认分类状态、分级和后续脱敏规则所需 classifyId。
aliyun dataphin-public get-security-classify --tenant-id "$TENANT_ID" \
  --security-classify-id "<分类ID>" \
  --user-agent "$UA" --format json
```

### 脱敏需求清单生成

当公开 CLI 缺少脱敏规则命令时，Agent 必须输出以下需求清单，而不是执行内部 REST：

| 项 | 示例 | 说明 |
|---|---|---|
| 目标字段 | `LD_dummy_practice_dev.dim_product.product_fullname` | 用公开识别结果回读确认 |
| 分类 ID | `7302017061078464` | 脱敏规则通常绑定分类 |
| 脱敏算法 | `MASK` / `MD5` / `FPE_FF1_ENCRYPT` | 以租户页面枚举或产品文档为准 |
| 生效场景 | `TEMP_QUERY`、`WRITE_DEV` | 即席查询、读写开发等 |
| 作用范围 | `BIZ_UNIT`、`PROJECT`、`PLATFORM`、`SCENE` | 不要默认全租户，需用户确认 |
| 白名单 | 账号 + 生效日期 | 白名单会绕过脱敏，需二次确认 |
| 验证方式 | 即席查询结果不等于明文 | 需有测试数据与查询权限 |

### 执行前确认（写操作必备 / HITL）

> 当前公开 CLI 不支持脱敏规则写操作，因此本 Skill 不发起 create/update/delete/toggle 脱敏规则命令。
> 若未来版本暴露对应 OpenAPI，执行前必须二次确认：命令全文、影响字段、作用范围、白名单账号、是否可回滚、清理顺序。

## 9. Success Verification

本 Skill 的成功标准不是“已创建脱敏规则”，而是完成外部能力范围内的安全交付：

1. **CLI 覆盖验证**：版本感知 OpenAPI 索引和公开命令集中未发现脱敏规则 CRUD 时，必须明确告知能力缺口。
2. **字段标签验证**：`list-security-identify-results` 能定位目标字段或确认缺少字段标签。
3. **识别记录验证**：`list-security-identify-records` 能确认字段口径、分类状态和 `ClassifyId`。
4. **分类验证**：`get-security-classify` 能回读分类与分级绑定。
5. **需求清单验证**：输出包含字段、分类、算法、范围、场景、白名单、验证方式的完整清单。
6. **边界验证**：不把内部 REST、录制用例或页面接口伪装成公开 CLI 命令。

## 10. Cleanup

本 Skill 当前不执行脱敏规则写操作，因此无需清理脱敏规则对象。若仅执行公开前置检查，不会产生资源。

如果未来版本支持脱敏规则写操作，清理顺序必须是：白名单规则 → 脱敏规则 → 字段识别结果 → 分类 → 分级；不要先删分类或字段标签，否则可能留下规则依赖或影响查询结果。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices

- 先确认字段是否已有分类分级标签；没有标签时提示先完成字段分类分级，再继续脱敏需求交付。
- 脱敏规则作用范围不能默认全租户，尤其是 `BIZ_UNIT=.*`、`PROJECT=.*`、`SCENE=TEMP_QUERY/WRITE_DEV` 必须让用户确认。
- 白名单不是授权本身，而是让特定账号在时间窗口内绕过脱敏，风险高于普通查询。
- 默认脱敏配置是租户级全局设置，不能并行随意修改；若未来开放 API，必须先记录旧值再恢复。
- 当前公开命令集与版本感知 OpenAPI 索引均未发现脱敏规则 CRUD；不要伪造不存在命令。
- 页面内部 REST 可作为业务理解参考，外部执行必须使用公开 OpenAPI。

### ✗ 平台限制：当前无公开脱敏规则 CLI

- 限制描述：`addDesensitizeRule`、`updateDesensitizeRule`、`desensitizeRule/open`、`desensitizeRule/close`、`addDesensitizeWhiteListRule` 等接口仅在 autotest/页面内部 REST 语义中出现，未在当前公开 CLI / swagger OpenAPI 中暴露。
- 替代方案：输出脱敏需求清单，完成字段分类分级前置检查，等待公开 OpenAPI 或由具备内部系统权限的流程执行。

### 常见坑

#### [Agent 自主发现] 把分类分级误认为脱敏已生效
- 现象：字段已打上 `ClassifyId` 和 `LevelName`，但查询结果仍是明文。
- 结论：分类分级只是脱敏规则的前置标签，不等于脱敏规则已创建或已生效。

#### [Agent 自主发现] 把内部 REST 当成外部命令
- 现象：autotest 里有 `/api/datasecurity/desensitization/addDesensitizeRule`，但 `aliyun dataphin-public --help` 中没有对应命令。
- 结论：外部 Skill 不能伪造内部 REST 入口；必须明确能力缺口。

#### [Agent 自主发现] 白名单会反向绕过脱敏
- 现象：创建白名单后，指定账号看到明文或低强度脱敏结果。
- 结论：白名单是高风险例外配置，必须确认账号、场景和有效期。

### Reference Links

- [references/cli-installation-guide.md](references/cli-installation-guide.md)
- [套件级 RAM 策略](../../ram-policies.md)
- [references/acceptance-criteria.md](references/acceptance-criteria.md)
- [references/related-commands.md](references/related-commands.md)
