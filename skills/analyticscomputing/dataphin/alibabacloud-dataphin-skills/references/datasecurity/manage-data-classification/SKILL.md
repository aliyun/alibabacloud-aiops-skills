---
name: manage-data-classification
description: |-
  管理 Dataphin 数据分级、数据分类目录、数据分类和字段级安全识别结果。
  当用户要把手机号、身份证号、姓名、薪资等字段标记为 C1/C2/C3/C4 或 L1/L2/L3/L4，创建或调整分类分级体系，查询字段当前分类分级标签，或批量启停/删除识别结果时进入。
  触发词：数据分级分类、分类分级、数据分类、数据分级、安全等级、敏感数据标签、识别结果、identify result、security classify、security level、C1、C2、C3、C4、L1、L2、L3、L4。
  关键限制：公共 OpenAPI 管理的是分级、分类、识别结果三层对象；字段打标用 create-security-identify-result；批量覆盖需确认 conflict-strategy；写操作需 HITL 确认。
---

# 数据分级分类 Skill

## 1. Scenario Description

在 Dataphin 数据安全中管理「数据分级分类（Data Classification）」体系，用于对敏感字段进行识别、标记和安全等级划分。例如将 `id_card` 标记为 C4-绝密，将 `phone` 标记为 C3-机密，将 `user_name` 标记为 C2-内部，为后续脱敏、权限审批、资产目录展示和安全审计提供依据。

本 Skill 基于 `dataphin-public` 已开放的数据安全 OpenAPI 实现三层对象管理：

- **数据分级（Security Level）**：描述敏感程度，如 C1/C2/C3/C4 或 L1/L2/L3/L4。
- **数据分类（Security Classify）**：描述业务类别，如身份证号、手机号、姓名，并绑定一个分级。
- **安全识别结果（Security Identify Result）**：将某个表字段绑定到某个分类，形成实际字段标签。

页面内部 `/api/datasecurity/classify/addClassify`、`/api/datasecurity/level/queryLevel`、`/api/datasecurity/identify/record/queryPagedIdentifyLabels` 等 REST 可用于理解业务语义，但不是外部 Skill 的直接命令入口；外部执行必须优先使用公开 `dataphin-public` CLI。

**Architecture**：`Dataphin Tenant → Security Level → Security Classify Catalog → Security Classify → Field Identify Result → List / Get / Enable / Disable / Delete`

### 涉及 Dataphin OpenAPI

- `CreateSecurityLevel` / `UpdateSecurityLevel` / `DeleteSecurityLevel` / `GetSecurityLevel` — 管理数据分级。
- `CreateSecurityClassifyCatalog` / `UpdateSecurityClassifyCatalog` / `DeleteSecurityClassifyCatalog` — 管理分类目录。
- `CreateSecurityClassify` / `UpdateSecurityClassify` / `DeleteSecurityClassify` / `GetSecurityClassify` — 管理数据分类。
- `CreateSecurityIdentifyResult` / `GetSecurityIdentifyResult` / `ListSecurityIdentifyResults` / `ListSecurityIdentifyRecords` — 管理和查询字段识别标签。
- `UpdateSecurityIdentifyResultStatus` / `DeleteSecurityIdentifyResults` — 批量启停或删除识别结果。

> `GetSecuritySecretKey` 属于密钥管理，不属于本 Skill 的数据分级分类主链路，避免混入。

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

执行任何写操作（create / update / delete / enable / disable）前必须向用户确认以下参数，禁止静默提交：

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--tenant-id` | 是 | 租户 ID（大整数，建议字符串传） | — |
| `--security-level-name` | 创建/更新/删除分级时必填 | 分级名称，如 C4-绝密、L3 | — |
| `--index` | 获取分级必填，创建/更新/删除分级可选 | 分级顺序或敏感等级；数值越高通常表示敏感程度越高，需以租户实际配置为准 | — |
| `--security-classify-name` | 创建/更新/删除分类时必填 | 分类名称，如 身份证号、手机号 | — |
| `--level-name` | 创建/更新分类必填 | 分类绑定的数据分级名称 | — |
| `--parent-path` | 分类/目录可选 | 分类目录父路径，根目录为 `/` | `/` |
| `--priority` | 分类可选 | 分类优先级，默认 5；多规则命中时可能影响最终标签 | `5` |
| `--advanced-condition-list` | 分类可选 | 高级识别条件，CLI list，每个元素建议传 JSON 对象 | — |
| `--feature-name-list` | 分类可选 | 引用的识别特征名称列表 | — |
| `--table-catalog` | 识别结果必填 | 表 Catalog；数据源表为 db/schema，Dataphin 物理表为项目英文名，逻辑表为板块英文名 | — |
| `--table-name` / `--field-name` | 识别结果必填 | 目标表名与字段名 | — |
| `--classify-id` | 识别结果必填 | 分类 ID；创建识别结果前需先确认分类详情 | — |
| `--conflict-strategy` | 创建识别结果必填 | `COVER_UNLOCKED` 仅覆盖未锁定标签；`COVER_ALL` 覆盖线上全部打标，风险更高 | 推荐 `COVER_UNLOCKED` |
| `--enable` | 创建或更新识别结果状态可选/必填 | 是否生效，true/false | true |
| `--identify-result-id-list` | 批量启停/删除必填 | 识别结果 ID 列表 | — |
| `--is-datasource-table` | 数据源表场景可选 | true 表示数据源表；false 表示 Dataphin 表 | false |
| `--datasource-name` / `--datasource-env` | 数据源表场景必填 | 数据源名称与环境标识 | — |

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/manage-data-classification/{session-id}
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<大整数租户 ID，字符串>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/manage-data-classification/$SESSION_ID"

# 1) 查询已有识别结果，先确认是否已经打标。
aliyun dataphin-public list-security-identify-results --tenant-id "$TENANT_ID" \
  --keyword "<表名或字段名>" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

# 2) 创建或确认数据分级。若租户已有 C4-绝密，可跳过创建并用 get-security-level 回读。
aliyun dataphin-public create-security-level --tenant-id "$TENANT_ID" \
  --security-level-name "<分级名称>" \
  --abbreviation "<分级简称>" \
  --index "<分级顺序>" \
  --description "<分级描述>" \
  --user-agent "$UA" --format json

aliyun dataphin-public get-security-level --tenant-id "$TENANT_ID" \
  --index "<分级顺序>" \
  --user-agent "$UA" --format json

# 3) 创建分类目录（可选）。目录用于组织分类，不等同于字段标签。
aliyun dataphin-public create-security-classify-catalog --tenant-id "$TENANT_ID" \
  --directory-name "<目录名称>" \
  --parent-path "/" \
  --visible-type PUBLIC \
  --user-agent "$UA" --format json

# 4) 创建数据分类，并绑定分级。高级条件可用于后续自动识别，但不会自动替代手动字段打标。
aliyun dataphin-public create-security-classify --tenant-id "$TENANT_ID" \
  --security-classify-name "<分类名称>" \
  --abbreviation "<分类简称>" \
  --parent-path "/" \
  --level-name "<分级名称>" \
  --priority 5 \
  --status ENABLE \
  --advanced-condition-list '{"Property":"FIELD_NAME","Operate":"EXPRESSION","Relation":"EXPRESSION","Values":["^id_card$"]}' \
  --user-agent "$UA" --format json

aliyun dataphin-public get-security-classify --tenant-id "$TENANT_ID" \
  --security-classify-id "<分类ID>" \
  --user-agent "$UA" --format json

# 5) 给具体表字段创建安全识别结果，也就是把字段打上分类/分级标签。
aliyun dataphin-public create-security-identify-result --tenant-id "$TENANT_ID" \
  --table-catalog "<项目英文名或板块英文名或数据源 schema>" \
  --table-name "<表名>" \
  --field-name "<字段名>" \
  --classify-id "<分类ID>" \
  --enable true \
  --conflict-strategy COVER_UNLOCKED \
  --user-agent "$UA" --format json

# 6) 回读识别结果列表和详情，验证字段标签已生成。
aliyun dataphin-public list-security-identify-results --tenant-id "$TENANT_ID" \
  --classify-id "<分类ID>" \
  --keyword "<表名或字段名>" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

aliyun dataphin-public get-security-identify-result --tenant-id "$TENANT_ID" \
  --security-identify-result-id "<识别结果ID>" \
  --user-agent "$UA" --format json

# 7) 查询指定表字段的识别记录历史。
aliyun dataphin-public list-security-identify-records --tenant-id "$TENANT_ID" \
  --table-catalog "<项目英文名或板块英文名或数据源 schema>" \
  --table-name "<表名>" \
  --field-name "<字段名>" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

# 8) 批量启停识别结果。disable/delete 会影响安全治理、脱敏联动和权限审批判断，必须二次确认。
aliyun dataphin-public update-security-identify-result-status --tenant-id "$TENANT_ID" \
  --enable false \
  --identify-result-id-list "<识别结果ID>" \
  --user-agent "$UA" --format json
```

### 三层对象选择

| 用户意图 | 优先命令 | 说明 |
|---|---|---|
| “新增 C4 绝密等级” | `create-security-level` | 创建分级，不会给任何字段打标 |
| “新增身份证号分类，并绑定 C4” | `create-security-classify` | 创建分类，绑定分级，可配置高级识别条件 |
| “把 ods_user.id_card 标为 C4” | `create-security-identify-result` | 给具体字段生成识别标签 |
| “查看某字段当前标签” | `list-security-identify-results` / `get-security-identify-result` | 列表按 keyword / classifyId / project / datasource 过滤，再查详情 |
| “停用某个标签” | `update-security-identify-result-status` | 只启停识别结果，不删除分类或分级 |
| “删除分类/分级” | `delete-security-classify` / `delete-security-level` | 高风险，需先确认没有识别结果、识别规则或分类绑定 |

> [Agent 自主发现] 数据分级、数据分类、字段识别结果不是同一个对象。用户说“把字段标为机密”时，若分类已存在，应优先创建或更新 `security-identify-result`；不要误以为创建 `security-level` 或 `security-classify` 就已经完成字段打标。
>
> [Agent 自主发现] poc 真实写链路验证中，不传 `--index` 创建分级会触发服务端自动分配；当租户已有较多分级时可能分配到越界值并返回 `DPN.DataSecurity.LevelIndexOutOfRange`。创建临时分级或生产分级前应先用 `get-security-level --index <n>` 确认目标 index 为空，再显式传 `--index`。
>
> [Agent 自主发现] `--advanced-condition-list` dry-run 可以映射为对象数组，但真实服务端会校验特征条件上下文，随意传 `{"Property":"FIELD_NAME"...}` 可能返回 `Security feature condition miss param id`。没有明确特征条件 ID 时，不要为分类伪造高级条件；字段级手动打标应使用 `create-security-identify-result`。

## 9. Success Verification

每次执行后必须进行结果验证：

1. **分级验证**：创建或更新分级后，用 `get-security-level --index <index>` 回读名称、简称和描述。
2. **分类验证**：创建或更新分类后，用 `get-security-classify --security-classify-id <id>` 回读分类名称、状态、路径和绑定分级。
3. **字段标签验证**：创建识别结果后，用 `list-security-identify-results --keyword <table-or-field>` 确认返回记录包含目标 `tableName`、`fieldName`、`classifyName`、`levelName`、`levelIndex` 和识别结果 `status`。
4. **分类状态验证**：识别结果自身 `Status` 与记录中的 `ClassifyStatus` 是不同维度；即使识别结果为 `ENABLE`，分类也可能是 `DISABLE`，需要分别回读判断是否真正参与后续治理联动。
5. **识别记录验证**：对具体字段执行 `list-security-identify-records`，确认该字段存在识别记录并可追溯来源。
6. **启停验证**：批量 disable/enable 后再次 list/get，确认状态变化。
7. **联动边界**：分类分级成功不等于脱敏或权限审批立即改变；实际联动还依赖脱敏规则、审批规则、扫描任务、缓存同步和资产目录展示链路。

## 10. Cleanup

数据安全标签会影响脱敏、权限审批、资产目录展示和审计，不要在未确认影响范围时删除或覆盖线上标签。清理顺序建议：

1. 若只是临时打标，优先使用 `update-security-identify-result-status --enable false` 停用识别结果。
2. 需要删除标签时，先 `get-security-identify-result` 确认 ID、表、字段和分类，再 `delete-security-identify-results`。
3. 删除分类前，确认无识别结果、识别规则或脱敏联动依赖该分类。
4. 删除分级前，确认无分类绑定该分级；否则服务端可能拒绝或造成治理体系断裂。
5. 分类目录删除前确认目录下无子目录和分类。

## 11. Command Tables

详见 [references/related-commands.md](references/related-commands.md)。

## 12. Best Practices

- 把“分级”“分类”“识别结果”分开确认：分级描述敏感程度，分类描述敏感类型，识别结果才落到表字段。
- 字段打标优先使用 `create-security-identify-result`，不要只创建分类后就声称字段已完成分级分类。
- `--conflict-strategy` 默认建议 `COVER_UNLOCKED`，只有用户明确确认要覆盖锁定/线上全部标签时才使用 `COVER_ALL`。
- `--table-catalog` 的含义随表来源变化：数据源表填 db/schema，Dataphin 物理表填项目英文名，逻辑表填板块英文名。
- `--advanced-condition-list` 是识别规则/分类匹配条件，不等同于立即给某个字段打标签；真实服务端还会校验特征条件上下文，没有明确条件 ID 时不要伪造，字段手动打标应走 `create-security-identify-result`。
- 删除分级或分类前必须先回读并确认绑定关系，避免破坏已有脱敏、审批和资产展示。
- 页面内部 REST 可作为业务理解参考，外部执行必须使用公开 OpenAPI。
- 所有 API 命令必须携带 `--user-agent`。

## 13. Troubleshooting

| 现象 | 常见原因 | 处理方式 |
|---|---|---|
| 字段 list 查不到目标标签 | `table-catalog` / `table-name` / `field-name` 与资产口径不一致，或扫描/打标尚未完成 | 分别用表名、字段名 keyword 搜索；确认表来源和 catalog 口径 |
| 创建识别结果覆盖了旧标签 | `--conflict-strategy COVER_ALL` 覆盖范围过大 | 默认用 `COVER_UNLOCKED`，写前展示覆盖策略并确认 |
| 创建分级不传 `--index` 失败 | 服务端自动分配到越界 index，例如返回 `DPN.DataSecurity.LevelIndexOutOfRange` | 先用 `get-security-level --index <n>` 找空位，再显式传 `--index` |
| 高级条件真实调用失败 | `--advanced-condition-list` 缺少服务端需要的特征条件上下文或条件 ID | 不伪造高级条件；没有明确条件 ID 时先创建分类，再用 `create-security-identify-result` 手动打标 |
| 删除分级失败 | 仍有分类绑定该分级 | 先查询并迁移/删除分类，再删除分级 |
| 删除分类失败 | 仍有识别结果、识别规则或脱敏联动依赖 | 先停用/删除识别结果并确认规则依赖 |
| 分类创建成功但字段未打标 | 分类只是规则定义，没有创建识别结果或未跑扫描任务 | 手动字段打标用 `create-security-identify-result`；自动识别需扫描任务链路 |
| 识别结果 `Status=ENABLE` 但联动不生效 | 关联分类 `ClassifyStatus` 可能为 `DISABLE`，或脱敏/审批/资产目录链路尚未同步 | 同时检查 `get-security-identify-result` 和 `list-security-identify-records` 返回的分类状态与识别结果状态 |
| 403 / Forbidden | 当前 RAM 或租户角色无数据安全管理权限 | 读取 RAM 策略并引导用户补齐权限 |
