---
name: configure-quality-rule
description: |-
  通过 Dataphin OpenAPI 完成数据质量规则的全生命周期管理：创建监控对象、配置质量规则、设置调度与告警、试跑验证、启停规则、查看执行结果。

  当用户场景涉及为某张表/字段配置质量校验、设置质量调度或告警、试跑质量规则、查看质量结果时进入。

  触发场景：
  - 「给 X 表 Y 字段配非空/唯一/值域/枚举校验」
  - 「质量规则要不要试跑 / 质量试跑失败排查」
  - 「质量规则挂调度 / 质量告警通知负责人」

  触发词：质量监控、质量规则、数据质量校验、质量告警、质量试跑、质量调度、监控对象、validateCondition、upsert-quality-rule。

  关键限制 / 类型分支：监控对象类型必须先确认；监控对象名称不可让用户填写；templateId 必须用 list-quality-templates 实测获取；模板级 formProperties 必填项以界面和模板定义为准；validateCondition 无后端默认必须显式传；分区表试跑必须钉单分区；归档模式/计分方式/质量分权重 OpenAPI 不可配。
---

# 配置数据质量规则（创建 → 调度告警 → 试跑 → 监控）

## 1. Scenario Description

通过 Dataphin OpenAPI 完成一条质量规则从「监控对象 → 规则 → 调度/告警 → 试跑 → 启停 → 看板」的完整闭环。

> **核心原则**：本 skill 通过 OpenAPI 配置，但目的是让用户在**界面上看到的结果与手工配置一致、且能正常运行**。因此：
> 1. **必填项以界面为准**，不能因 API 允许省略就擅自省略——先与用户确认（见 §6）。
> 2. **监控对象类型必须先确认**：`TABLE` / `DATASOURCE_TABLE` / `DATASOURCE` / `INDEX` / `REALTIME_LOGICAL_TABLE` 会决定对象定位方式、创建参数、可用模板和调度边界；不能仅凭对象名猜类型。
> 3. **监控对象名称（WatchName/tableName）不是用户配置项**，禁止让用户填写或选择；由 skill 根据目标对象元数据自动生成/回查校验。
> 4. **模板级必填项以模板和界面为准**，不能因为 `SaveQualityRule.formProperties` 顶层标为非必填就传空；例如 `TABLE_SCHEMA_CHECK`/2600 必须先选校验表并传 `dataSourceTable`。
> 5. **API 无法指定的项**（异常归档表、计分方式、质量分权重）必须**主动向用户说明默认值**。
> 7. **规则模版的必填项都不能为空**：`template-config-catalog.json` 中 `required=true` 的配置项必须全部有值。处理方式二选一：
>    - **有合理默认值** → 自动补上（如 `timeTolerance` 默认 `>0天 且 <1天`，`validateCondition` 默认 `ERROR_NUMBER=0`）
>    - **无合理默认值** → 必须询问用户（如 `validateField` 校验字段、`doubleTableCompareTable` 比较表、`customSql` 自定义SQL）
>    - **CLI 无法安全传值** → 创建规则后主动告知用户需到界面手工补充
> 8. **调度、告警由独立命令实现**，创建规则前必须**分别询问是否需要**，不默认配也不默认跳过。

**Architecture**：`Dataphin Tenant + QualityWatch（监控对象） + QualityRule（规则） + QualitySchedule（调度） + QualityAlert（告警）`。

## 2. Installation

> 仅**公共云（A）走 CLI** 时需要安装插件；**独立部署（B）直调 OpenAPI（见 §3 执行通道）无需安装 CLI 插件**。

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```
（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

> **执行通道（按父 §4.1 自动判定的环境选择，★重要）**：本 skill 的 OpenAPI Action 与参数语义两套环境一致，但**调用通道按部署形态区分**，由父 skill `alibabacloud-dataphin-skills` 的 §4.1 环境自动判定（endpoint / AK 前缀 / 探测，运行时推断，不询问类型）结果决定：
> - **A `public-cloud`（公共云）→ 默认用 CLI**：`aliyun dataphin-public <命令>`（下文各命令），默认 endpoint + `aliyun configure` 主/子账号 AK。
> - **B `standalone`（独立部署 / POC）→ 默认直接调 OpenAPI，不走 CLI**：独立部署环境下 `aliyun dataphin-public` 对 HTTPS endpoint 会直接报 `dial tcp ... connect: bad file descriptor`（Go CLI 已知网络层 bug，`curl` 能通、CLI 不通）。**遇到该环境不要再尝试/重试 CLI**，直接用阿里云 Python SDK（RPC 风格）调 OpenAPI，自签证书需关闭校验（`verify=False` / `ignore_ssl`）。
>   - **Action 名（★POC 实测坑）**：真实 OpenAPI Action 名 = **对应 CLI kebab 命令的 PascalCase**（如 `list-quality-watches`→`ListQualityWatches`、`upsert-quality-rule`→`UpsertQualityRule`、`get-quality-watch-by-object-id`→`GetQualityWatchByObjectId`）。**不要猜、也不要沿用文档里可能残留的旧名**——`PagedQueryQualityWatches`/`SaveQualityWatch`/`RemoveQualityRules` 这类是旧裸 OpenAPI 命名，POC 直调会报 `Unknown API`。**拿不准就先用 `aliyun dataphin-public <command> --cli-dry-run` 导出真实 Action 名与参数再调**。参数名 kebab-case → camelCase（`--watch-type`→`WatchType`），`--tenant-id`→`OpTenantId`；复杂对象（`--table-info`/`--validate-condition-list` 等）作为 JSON string/list 传同名 camelCase 参数，值语义一致。
>   - **Version / endpoint / 凭证**：`Version` 以环境实测为准（POC 独立部署实测 `2023-06-30`）；endpoint、AK/SK 从 profile / 环境变量获取。
>   - **Python SDK 骨架 + 签名要点（★POC 实测坑）**：POC standalone 的 OpenAPI **要求全部业务参数放在 query string 里参与签名**；而 `aliyunsdkcore` 默认会把参数塞进 request body，body 参数不进签名串 → 始终 `SignatureDoesNotMatch`。**所有业务参数一律用 `add_query_param` 进 query string，禁止用 body（`add_body_params`）**；若用 SDK 仍签名不过，改为**手动签名 + query string 传参**（实测这样 `ListQualityWatches` 才能正常返回）。
>     ```python
>     from aliyunsdkcore.client import AcsClient
>     from aliyunsdkcore.request import CommonRequest
>     import json, os
>     client = AcsClient(AK, SK, "cn-shanghai")          # regionId 占位即可
>     # UA 可观测（Principle 9）：SKILL_SESSION_ID 由 Agent 执行时内联注入（继承自父 skill）
>     _sid = os.environ.get("SKILL_SESSION_ID", "")
>     client.set_user_agent("AlibabaCloud-Agent-Skills/configure-quality-rule" + ("/" + _sid if _sid else ""))
>     req = CommonRequest()
>     req.set_domain(ENDPOINT)             # 如 dataphin-openapi.poc.lydaas.com，不带 https://
>     req.set_version("2023-06-30")        # 以环境实测为准
>     req.set_action_name("ListQualityWatches")   # 真实 Action = CLI list-quality-watches 的 PascalCase；拿不准用 --cli-dry-run 导出
>     req.set_method("POST"); req.set_protocol_type("https")
>     # ★所有业务参数必须用 add_query_param 进 query string 参与签名，禁用 body（add_body_params），否则 SignatureDoesNotMatch
>     req.add_query_param("OpTenantId", TENANT_ID)      # --tenant-id → OpTenantId
>     req.add_query_param("Name", KEYWORD); req.add_query_param("PageNo", 1); req.add_query_param("PageSize", 100)
>     # 自签证书：对底层 requests/urllib3 关闭校验（verify=False / urllib3.disable_warnings）
>     resp = client.do_action_with_exception(req)
>     data = json.loads(resp)
>     ```
>     > **SDK 仍报 `SignatureDoesNotMatch`（把参数落到 body）→ 手动签名**：把公共参数（`Action`/`Version`/`Format=JSON`/`AccessKeyId`/`SignatureMethod=HMAC-SHA1`/`SignatureVersion=1.0`/`SignatureNonce`/`Timestamp`）与全部业务参数一起放进 query，按 key 字典序排序拼成规范化 query 串，做 RPC 签名（`StringToSign = "POST&" + %2F + "&" + URLEncode(排序后query串)`，HMAC-SHA1 密钥为 `AccessKeySecret + "&"`，结果 base64 作 `Signature`），再把含 `Signature` 的完整 query string 发出（`requests`，`verify=False`）。
> - 环境（公共云 A / 独立部署 B）由父 §4.1 运行时自动判定，据此选通道，**不询问用户类型**。两套通道均带可观测标识：CLI 用 `--user-agent`；OpenAPI 直调把相同 UA 放进 header（如 `User-Agent`）。

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
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
> Run `aliyun version` to verify >= 3.4.8. If not installed or version too low,
> install/update from https://aliyuncli.alicdn.com (see [`references/cli-installation-guide.md`](references/cli-installation-guide.md) for the OS-specific script).

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

> **环境选择（A/B）与执行通道**：环境由父 §4.1 运行时自动判定（不询问用户类型），据此选通道。**通道按 §3「执行通道」选择：A（公共云）→ CLI；B（独立部署）→ 直接调 OpenAPI（Python SDK，`verify=False`），不要用 CLI**（独立部署下 CLI 会报 `dial tcp ... bad file descriptor`，重试 `--endpoint`/`--skip-secure-verify` 也无效）。仅 A 环境走 CLI 时才需 `aliyun configure` 主/子账号 AK。

## 5. RAM Policy

最小权限策略详见 [`../../ram-policies.md`](../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

### 6.1 面向普通用户的配置全景（用户模糊表达时先做这一步）

当用户只给模糊指令（如「帮我建个质量监控」），**不要直接抛参数术语**。先用大白话给「配置全景」，再一步步引导（一次只问一个主题）：

> 一条完整、能正常运行的质量规则主要包含：① 监控对象类型和具体对象（Dataphin 表/全域表/数据源/指标/实时元表）；② 查什么问题（非空/唯一/格式/值域/波动）；③ 多严格（规则强度 + 校验条件）；④ 多久查一次（调度，可选）；⑤ 出问题怎么通知（告警，可选）；⑥ 其他（异常归档/计分方式，一般默认）。我们先从第 1 步开始：请先确认监控对象类型，再确认具体对象。

若用户已给出明确完整指令，可跳过全景介绍，直接逐项确认缺失/关键项。

### 6.2 必须澄清的参数

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `--tenant-id` | 是 | 租户 ID（19 位 snowflake，**字符串传**） | — |
| 监控对象类型 `Type` | 是 | 必须最先确认：`TABLE` Dataphin 表 / `DATASOURCE_TABLE` 全域表 / `DATASOURCE` 数据源 / `INDEX` 指标 / `REALTIME_LOGICAL_TABLE` 实时元表 | 无 |
| 具体对象 | 是 | 按类型定位真实对象 ID：表 guid/tableId、dataSourceId、indexId 等；对象 ID 必须来自查询结果 | 无 |
| 规则名称 `RuleName` | 是 | 规则叫什么；注意这不是监控对象名称 | 无 |
| 监控对象名称 `WatchName/tableName` | ✗ | 禁止让用户填写或选择；由 skill 根据元数据自动生成（物理表=项目名.表名，逻辑表=板块名.表名，数据源表=库/schema.表名）并在创建后回查校验 | 自动推导 |
| 规则强度 `RuleStrength` | 是 | `STRONG`（强，阻断下游）/ `WEAK`（弱，仅告警） | 建议 STRONG，须确认 |
| 模板级规则配置 `formProperties` | 是 | 按模板定义补齐，不同模板不同；创建前先查 [`references/template-config-catalog.json`](references/template-config-catalog.json)，字段级规则必须有 `validateField`，值域/时间/一致性/自定义模板按 `ruleConfigItems` 补齐 | 无 |
| 校验字段 `validateField` | 字段级规则必填 | 校验哪个字段（**必须从表元数据取真实字段**，见 §8 Step 2）；表级/数据源级模板不一定有该字段 | 无 |
| 规则模板 `templateId` | 是 | 必须通过 `list-quality-templates` 按当前租户/对象类型实测获取；不要照搬文档示例 ID（速查见 [`references/quality-config-matrix.md`](references/quality-config-matrix.md)） | 无 |
| **规则校验 `validateCondition`** | 是 | ❗最关键，**无后端默认**（不传则 `null`，界面显示「未配置」，试跑会失败） | 空值/唯一校验推荐 `ERROR_NUMBER=0` |
| 异常归档 `enableErrorArchive` | 否 | 是否开启异常归档 | 须确认；归档模式/位置 API 不可配 |
| 调度 | 否 | **单独询问是否需要**；需要则必须让用户**显式指定调度类型**（`--type` 必填，5 选 1，不得默认/留空）+ 确认校验分区范围（见 §8 Step 5） | 不配则仅手动跑 |
| 告警 | 否 | **单独询问是否需要**；告警是 watch 级别，对该表所有规则生效 | 不配则不通知 |
| 试跑 | — | **默认收尾动作**：主动问一句「是否试跑（默认会跑）」，明确拒绝才跳 | 默认试跑 |

> ⚠️ **即使用户初始需求没提「调度 / 告警」，也必须主动确认**，绝不能因「没提」就默认跳过。
> ⚠️ **写规则前必须先确认模板级 formProperties**：先查 `list-quality-templates` 得到真实 `templateId`/`templateType`，再按 [`references/template-config-catalog.json`](references/template-config-catalog.json) 的 `supportWatchTypes`、`validateObjectType`、`ruleConfigItems` 和 [`references/quality-config-matrix.md`](references/quality-config-matrix.md) 补齐 `--form-property-list`。`FormPropertyList=null` 不代表模板无必填项。
> 界面配置项 ↔ OpenAPI 参数完整对照、`validateCondition` 结构、模板速查、API 能力缺口，全部见 [`references/quality-config-matrix.md`](references/quality-config-matrix.md)；31 个系统模板（含 3 个实时元表专用模板 T2700/T2800/T2900）的规则配置项与校验配置项详见 [`references/template-config-catalog.json`](references/template-config-catalog.json)。

### 6.3 监控对象类型先行与创建门控

先确认 `Type`，再定位对象；不能看到 `basic01.account_salesforce` 这类名称就默认当作 `TABLE`。类型会决定对象定位 API、`upsert-quality-watch` 的对象详情字段、可用模板和调度边界。

| Type | 对象定位结果 | 创建/更新时使用的对象详情 | 是否询问用户 |
|---|---|---|---|
| `TABLE` Dataphin 表 | 表 guid/tableId | `--table-info` / `TableInfo.Id` | 不问 ID，自动带入 |
| `DATASOURCE_TABLE` 全域表 | 数据源表 guid/tableId | `--table-info` / `TableInfo.Id` | 不问 ID，自动带入 |
| `DATASOURCE` 数据源 | dataSourceId | `--data-source-info` / `DataSourceInfo.Id` | 不问 ID，自动带入 |
| `INDEX` 指标 | indexId/indexGuid | `--index-info` / `IndexInfo.Id` | 不问 ID，自动带入 |
| `REALTIME_LOGICAL_TABLE` 实时元表 | 实时元表 guid/tableId | `--table-info` / `TableInfo.Id` | 不问 ID，自动带入 |
| 全部类型 | `QualityOwner` | 单个用户 ID | 缺失时才问 |

交互限制：允许在①对象定位不唯一（命中多条）②关键定位信息缺失（如指标缺板块/项目）③缺少 `QualityOwner` 时向用户确认——此时可主动列出还缺哪些信息、或直接请用户给最直接的 `WatchId`/`indexId`；但仍禁止让用户手写 `UpsertCommand`、`table-info`、`data-source-info`、`index-info` 或监控对象名称。对象详情必须来自前置查询/元数据定位。

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/configure-quality-rule/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public get-quality-watch-by-object-id --tenant-id "1234567890123456789" \
  --watch-type "TABLE" --watch-object-id "<表ID>" \
  --user-agent AlibabaCloud-Agent-Skills/configure-quality-rule/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

> 变量约定：`TENANT_ID`（19 位字符串）、`SESSION_ID`（继承父层）、`UA=AlibabaCloud-Agent-Skills/configure-quality-rule/$SESSION_ID`。
> 命令均为插件模式 kebab-case；括号内标注对应 OpenAPI Action 原名，响应字段为 **PascalCase**（`WatchId`/`RuleId`/`ScheduleId`）。

### Step 1: 解析业务维度
用户诉求 → 质量维度：完整性→空值校验；有效性→格式/值域校验；唯一性→唯一性校验；一致性→值一致性比较；稳定性→表波动性校验。

### Step 2: 取表字段（配字段级规则前必做，严禁猜字段）
```bash
# 已采集表：定位表（catalog 必填，项目名/业务板块名）；⚡必带 --cli-query——不带实测单次 115k 字符（每表二十多字段全量元数据）
aliyun dataphin-public list-tables --tenant-id "$TENANT_ID" \
  --catalog "<项目名>" --keyword "<表名>" \
  --cli-query 'PageResult.TableList[].{Name:Name,TableId:TableId,Guid:Guid}' \
  --user-agent "$UA"      # 注意：扁平参数，无 --list-query

# 已采集表：拉字段列表（返回 Name/DataType/Pt/AllowEmpty/Cn）；⚡必带 --cli-query 裁剪——全量返回单表实测 18k 字符，裁剪后 ~2.5k（-86%）
aliyun dataphin-public get-table-columns --tenant-id "$TENANT_ID" \
  --catalog "<项目名>" --table-name "<表名>" \
  --cli-query 'ColumnList[].{Name:Name,DataType:DataType,Pt:Pt,AllowEmpty:AllowEmpty,Cn:Cn}' \
  --user-agent "$UA"
```
> ⚠️ **未采集的外部数据源表** `list-tables`/`get-table-columns` 拿不到字段：改用「数据库SQL任务」`execute-ad-hoc-task` 直连数据源跑 `SELECT * FROM 库.表 LIMIT 1` 取字段（公共云 A / 独立部署 B 同一套），详见 [`references/quality-config-matrix.md`](references/quality-config-matrix.md) §7。

### Step 3: 定位/创建监控对象（线性主路径，勿绕圈）

先按 §6.3 确认监控对象类型 `Type`，然后**严格按 ①→②→③ 线性走**，全程只围绕「监控对象」本身，不要在「找资产」上绕圈：

**① 查监控对象是否已存在** → `ListQualityWatches`（CLI `list-quality-watches`），把用户给的信息**全部映射成过滤参数**（类型→`--watch-type-list`、板块→`--biz-unit-name-list`、项目→`--project-name-list`、负责人→`--*-owner-list`；`--keyword` 只对表名有效，别拿它搜指标）。

```bash
aliyun dataphin-public list-quality-watches --tenant-id "$TENANT_ID" \
  --watch-type-list '["INDEX"]' \
  --biz-unit-name-list '["LD_train"]' --project-name-list '["train"]' \
  --page-no 1 --page-size 100 --user-agent "$UA"
```

在返回列表按英文 code / 中文名匹配目标。**命中 → 复用其 `WatchId`，直接跳到 Step 4**；命中多条 / 关键信息不够 → **直接问用户补 <板块/项目/负责人> 或给 `WatchId`**，不自行盲搜。

**② 不存在 → 新建监控对象**（先拿对象 ID）：
- **表（TABLE / DATASOURCE_TABLE）** → 用 `list-tables --catalog <项目/板块名> --keyword <表名>` 定位 `tableId`（见 Step 2）。
- **指标（INDEX）** → 无 list 接口可搜，**直接请用户提供 `indexId`**（或让用户先在界面建好监控对象，回到 ① 查）。

拿到对象 ID 后 `upsert-quality-watch`（真实 Action `UpsertQualityWatch`）。门控：`Type` + 单个 `QualityOwner` + 按类型对象详情，不让用户自由填一堆字段。创建报错 → **原样告知并引导用户订正**（确认 `Type`/对象是否存在/是否已发布/`catalog`），不吞错、不盲搜。

**③ 拿到 `WatchId`** → 进入 Step 4 创建质量规则。

<details><summary>⚠️ 避坑清单（POC 实测，点开）</summary>

- **别只靠 `--keyword` 搜**：`Keyword` 定义是「监控表名称」，对 INDEX 指标匹配不到；指标靠「板块 + 项目 + 类型」过滤。
- **别用 `GetBizMetricByName` / `list-catalog-assets` 找监控对象**：前者只查业务指标 `BIZ_INDEX`（查不到技术指标）；后者只查资产目录**已上架**资产，而监控对象取自「资产清单」，大量搜不到。表→`list-tables`，指标→直接要 `indexId`。
- **Action 名**：真实名 = CLI 命令的 PascalCase；旧裸名 `PagedQueryQualityWatches` / `SaveQualityWatch` POC 直调报 `Unknown API`，拿不准用 `--cli-dry-run` 导出。
- **`ListQualityWatches` 完整过滤参数**：`--watch-type-list` / `--biz-unit-name-list`(板块) / `--project-name-list`(项目) / `--index-owner-list`·`--table-owner-list`·`--quality-owner-list` / `--data-source-id-list`·`--data-source-type-list` / `--keyword`(仅表名) / `--page-no` / `--page-size`。
- 已知对象 ID 时直接精确查 `get-quality-watch-by-object-id --watch-type <Type> --watch-object-id <对象ID>`。

</details>

```bash
# TABLE / DATASOURCE_TABLE / REALTIME_LOGICAL_TABLE：用 --table-info
aliyun dataphin-public upsert-quality-watch --tenant-id "$TENANT_ID" \
  --type "TABLE" --quality-owner "<单个用户ID>" \
  --table-info '{"tableId":"<id>","tableName":"<自动推导全名>","dataSourceId":"<id>"}' \
  --user-agent "$UA"

# DATASOURCE：用 --data-source-info
aliyun dataphin-public upsert-quality-watch --tenant-id "$TENANT_ID" \
  --type "DATASOURCE" --quality-owner "<单个用户ID>" \
  --data-source-info '{"dataSourceId":"<dataSourceId>","dataSourceName":"<name>","dataSourceType":"<type>","dataSourceEnv":"PROD"}' \
  --user-agent "$UA"
```
> ⚠️ 监控对象名称（WatchName/tableName）禁止让用户自填；需要 `tableName` 时由 skill 从元数据自动生成全名（物理表=项目名.表名 / 逻辑表=板块名.表名 / 数据源表=库或schema.表名），创建后再用 `get-quality-watch-by-object-id` / `get-quality-watch` 回查展示名。
> ⚠️ **数据源类型监控对象**用 `--data-source-info`（而非 `--table-info`），内部字段按当前 CLI 契约；旧 API/封装里曾出现 `dataSource` 驼峰字段坑，实际写入前以 `--help` 和返回为准。
> ⚠️ **逻辑表必须在 `--table-info` 传完整字段**（`tableType=LOGIC_DIM_TABLE`/`tableCatalog`/`projectId`/`bizUnitId`/`dataSourceId`），仅传 `tableId` 会「半创建」——接口虽返回 WatchId，但后续 `upsert-quality-schedule`/`upsert-quality-watch-alert` 报 `DPN.UniversalQuality.watchTableNotExists`。完整字段清单见 [`references/quality-config-matrix.md`](references/quality-config-matrix.md) §9。

### Step 4: 选模板 + 创建规则（★写操作，先确认，见 §8 执行前确认）
```bash
# 先查当前租户/当前对象类型支持的真实模板。不要照搬文档示例 templateId。
aliyun dataphin-public list-quality-templates --tenant-id "$TENANT_ID" \
  --watch-type-list "TABLE" "DATASOURCE_TABLE" \
  --template-source-list "SYSTEM" --page-no 1 --page-size 100 \
  --user-agent "$UA"

# 独立部署/env23 示例：--endpoint 不带 https://
aliyun --profile env23 dataphin-public list-quality-templates \
  --endpoint dataphin-openapi.env23.aliyun.com \
  --op-tenant-id 300001414 \
  --watch-type-list TABLE DATASOURCE_TABLE \
  --template-source-list SYSTEM \
  --page-no 1 --page-size 100 --format json \
  --user-agent "$UA"

# 单模板详情（可查 Id/Name/Type/Catalog；注意某些环境 FormPropertyList 可能为 null）
aliyun dataphin-public get-quality-template --tenant-id "$TENANT_ID" \
  --quality-template-id "<templateId>" --user-agent "$UA"

# 组装规则配置前，读取 references/template-config-catalog.json：
# - supportWatchTypes：确认当前监控对象类型是否支持
# - validateObjectType：COLUMN 需 validateField，TABLE 不需要校验字段
# - ruleConfigItems：逐项补齐 --form-property-list（Name/Value）
# - validateConfigItems.metric.options：选择合法校验指标

# 创建规则；--validate-condition-list 为★关键必填、无默认
# ⚠实测(env23 2023-06-30)：--form-property-list 键名必须是 Name/Value（PascalCase），
#   误用 propertyName/propertyValue 会导致 validateField 不生效、模板变量 ${validateField} 不被替换、试跑 FAILED。
# ⚠--validate-condition-list 是扁平数组 + id/parentId 父子关联（不是嵌套 subConditions），否则报 "validate config miss param id"。
# ⚠必须有 RELATION 根节点——单条件也不例外：第一个元素必须是 type=RELATION 根（operator=OR/AND、无 parentId），
#   所有 EXPRESSION 用 parentId 挂到它下面；绝不能把单个 EXPRESSION 当根直接传。否则界面「校验配置→规则校验」
#   识别不了裸 EXPRESSION，「统计指标」显示为空/未配置（INDEX 指标类规则尤为典型，POC 实测已复现）。
aliyun dataphin-public upsert-quality-rule --tenant-id "$TENANT_ID" \
  --quality-rule-name "<名>" --strength "STRONG" --watch-id "<wid>" \
  --template-id 100 --template-type "FIELD_NULL_VALUE_VALIDATE" \
  --catalog-list "COMPLETENESS" \
  --form-property-list '{"Name":"validateField","Value":"<字段>"}' \
  --validate-condition-list '{"id":"<uuid-root>","type":"RELATION","operator":"OR"}' '{"id":"<uuid-expr>","parentId":"<uuid-root>","type":"EXPRESSION","operator":"EQUAL","metric":"ERROR_NUMBER","value":"0"}' \
  --enable-error-archive true \
  --user-agent "$UA"      # → 返回 RuleId
```
> `list-quality-templates` 返回结构以当前 CLI 为准，env23 实测为 `PageResult.QualityTemplateList[]`，字段为 `Id`/`Name`/`Type`/`Catalog`，不是旧文档里的 `Data.data.TemplateId`。
> **模板级必填项门控**：`FormPropertyList=null` 不代表该模板没有界面必填项；创建前必须按 [`references/template-config-catalog.json`](references/template-config-catalog.json) 的 `ruleConfigItems` 逐项判断必填项。字段级模板（`validateObjectType=COLUMN`）必须传 `validateField`；表级模板（`validateObjectType=TABLE`）不传校验字段；模板动态配置如 `contentIdentifyMethod`、`valueRangeType`、`timeTolerance`、`statisticalMethod`、`customSql` 等按 JSON 中的 `required/options` 组装。
> **两表/跨源比较表字段名**：界面“选择比较表”识别的 formProperty 名称是 `doubleTableCompareTable`，不是旧脚本里的 `doubleCompareTable`。T800/T1600/T1700/T1750/T1800 等两表模板必须传：`{"Name":"doubleTableCompareTable","Value":"{\"doubleTableCompareTable\":\"项目或数据源目录.表名\",\"doubleTableCompareField\":\"比较字段\"}"}`；否则 `get-quality-rule` 虽可能看到 `doubleCompareTable`，但界面“选择比较表”仍为空。
> **两表/跨源关联表达式写法**：`doubleTableJoinCondition` 必须传表达式字符串，不是 `{leftField/rightField/operator}` JSON。内置数据表参数：`T1` 为检测表，`T2` 为比较表；标准示例：`{"Name":"doubleTableJoinCondition","Value":"T1.id = T2.id"}`。
> **T1800 两表字段业务逻辑写法**：`contentIdentifyExpression` 必须传业务逻辑表达式，并用 `${T1.字段名}` / `${T2.字段名}` 变量引用实际表字段，不能写裸字段名如 `col1=col2`。`T1` 为检测表，`T2` 为比较表，最多支持双表；示例：`{"Name":"contentIdentifyExpression","Value":"${T1.total_sales}=${T2.unit_price}*${T2.sales_volume}"}`。表达式中的变量还必须逐个实例化：去掉 `${}` 后的变量名作为独立 `formProperty.Name`，实际字段作为 `Value`，例如 `{"Name":"T1.total_sales","Value":"total_sales"}`、`{"Name":"T2.unit_price","Value":"unit_price"}`、`{"Name":"T2.sales_volume","Value":"sales_volume"}`。两表类还需传关联方式：`{"Name":"joinMethod","Value":"left join"}`，并配合 `doubleTableCompareTable` 和 `doubleTableJoinCondition`。
> **T1100 字段值域校验枚举写法**：枚举不是只传 `valueRangeScopeNumber`，而是外层 `valueRangeType` + 内层 `valueRange` JSON 字符串两层结构。env23 实测 `T1100_字段值域校验_col1` 返回：
> ```
> {"Name":"valueRangeType","Value":"number"}
> {"Name":"valueRange","Value":"{\"enumType\":\"in\",\"enumValue\":\"1,2,3,4,5\",\"intervalLeftType\":\">=\",\"intervalLeftValue\":null,\"intervalRightType\":\"<=\",\"intervalRightValue\":null,\"valueRangeType\":\"enum\"}"}
> ```
> - 外层 `valueRangeType` 表示字段值类型：`number`/`text`/`date`/`time`/`custom`
> - 内层 `valueRange.valueRangeType=enum` 表示值域范围类型为枚举
> - `enumType=in` 表示字段值必须在枚举内；`enumValue` 用英文逗号拼接枚举值，如 `1,2,3,4,5`
> - 区间校验才使用 `valueRange.valueRangeType=interval` + `intervalLeftType/intervalLeftValue/intervalRightType/intervalRightValue`
> - 创建后必须回查 `FormPropertyList`，确认 `valueRange` 是可解析 JSON 字符串且 `enumValue` 未被转义/截断
> **`timeTolerance`（时间差）传参格式**：T600/T700/T800 时间类模板的 `timeTolerance` 是 `TIME_TOLERANCE` 复合组件，**必须传 3 元素 JSON 数组**作为 `Value`：
> ```
> Name=timeTolerance  Value=[{"checked":true,"operate":">","time":0,"type":"DAY"},{"checked":true,"operate":"<","time":1,"type":"DAY"},{"timeCompareMethod":"VALIDATE_SUB_COMPARE"}]
> ```
> - 元素1：条件1（`checked`=是否启用，`operate`=比较符 `</<=/==/>=/>`，`time`=数值，`type`=单位 `DAY/HOUR/MINUTE/SECOND`）
> - 元素2：条件2（同上）
> - 元素3：比较类型（`timeCompareMethod`：`VALIDATE_SUB_COMPARE`=校验字段-比较字段，`COMPARE_SUB_VALIDATE`=比较字段-校验字段）
> - **默认建议值**：`>0天 且 <1天`（即上例格式），创建时自动补上
> - **注意**：传单对象 JSON（如 `{"unit":"d","value":"1","operator":"<"}`）或简单字符串（如 `<1d`）会导致后端数据损坏，必须用上述 3 元素数组格式
> **时间类字段类型门控**：T600/T700/T800 底层会生成 `datediff(校验项, 比较项, '单位')` 这类表达式，参与 `datediff` 的字段/表达式必须是 `DATE`/`DATETIME`/`TIMESTAMP`/`TIMESTAMP_NTZ` 等时间类型（部分引擎二参 datediff 支持 STRING，但三参带单位时不能依赖 STRING/BIGINT）。**禁止用 `id`、订单号、自增键、BIGINT 时间戳、yyyymmdd 数字等非时间类型字段做 validateField/validateItem/compareItem**；否则试跑会报 `function datediff cannot match any overloaded functions with (BIGINT, BIGINT, STRING)`。若源字段是 BIGINT 时间戳或 yyyymmdd 数字，需先让用户提供已转换的日期时间字段，或改用自定义 SQL 模板显式 `cast/to_date/from_unixtime`。
> templateId + templateType 速查、`validateField`/`valueRange` 值域配置法、2600 `dataSourceTable`、`--form-property-list` 键名(`Name`/`Value`)、`--validate-condition-list` 扁平结构、能力缺口等，见 [`references/quality-config-matrix.md`](references/quality-config-matrix.md)；31 个系统模板的支持对象类型、规则配置项、校验指标选项以 [`references/template-config-catalog.json`](references/template-config-catalog.json) 为准。
> **不可配项**：归档模式（默认仅归档异常字段）、归档位置（默认文件服务器）、计分方式（质量校验状态）、质量分权重（1）——须主动告知用户，如需自定义只能到界面。

### Step 5: 调度与告警（先分别询问是否需要）
```bash
# 调度三步：查已有 → 创建 → 绑定（仅创建调度不会自动绑定！）
aliyun dataphin-public get-quality-schedules-by-watch-id --tenant-id "$TENANT_ID" --watch-id "<wid>" --user-agent "$UA"
aliyun dataphin-public upsert-quality-schedule --tenant-id "$TENANT_ID" \
  --upsert-quality-schedule-name "<调度名>" --watch-id "<wid>" \
  --type "PERIOD_SCHEDULE" --cron-expression "0 0 2 * * ?" --user-agent "$UA"       # → ScheduleId
# ⚠实测(env23)：--rule-id-list/--schedule-id-list 必须空格分隔多值（不是逗号）；
#   本命令即使入参无效也会静默返回 {"Success":true}，绑定并不生效！
aliyun dataphin-public assign-quality-rule-of-all-rule-scope-schedules --tenant-id "$TENANT_ID" \
  --watch-id "<wid>" --rule-id-list <rid1> <rid2> --schedule-id-list <sid> --user-agent "$UA"
# ⚠绑定后必须回查确认：get-quality-rule 返回的 QualityRuleInfo.ScheduleBindList 应为
#   [{"ScheduleId":<sid>,...}]，若为 null 则未绑定成功。（调度侧 IsRefByRule 恒为 null，不可用于判断）
aliyun dataphin-public get-quality-rule --tenant-id "$TENANT_ID" --quality-rule-id "<rid>" --user-agent "$UA"   # 校验 ScheduleBindList

# 告警（watch 级别，对该表所有规则生效）；--quality-alert-info 为内嵌 JSON
aliyun dataphin-public upsert-quality-watch-alert --tenant-id "$TENANT_ID" \
  --watch-id "<wid>" \
  --quality-alert-info '{"alertQualityOwner":true,"alertQualityOwnerChannels":["MAIL"]}' --user-agent "$UA"
```
> **★调度类型（`--type`）必填，不得为空，也不得默认**：创建调度前必须让用户从以下 5 个枚举值中**显式指定**要创建哪种调度，禁止 Agent 擅自默认或留空：
>   - `PERIOD_SCHEDULE` 定时调度（cron 周期触发）
>   - `MANUAL_SCHEDULE` 手动触发（不设周期，仅手动/试跑触发）
>   - `CODE_CHECK_TRIGGER` 代码检查触发 / 数据更新触发（产出该对象的加工任务运行时触发）
>   - `STATIC_TASK_TRIGGER` 固定任务触发（指定真实调度节点 + 触发时机）。**触发时机 `--trigger-type` 必填且 3 选 1，需给用户推荐**：`ALL_TASKS_FINISHED`（所有任务成功后——多上游合并产出）/ `ONE_TASKS_FINISHED`（每个任务每次成功后——多来源/分区增量即时校验）/ `PRE_ONE_TASKS_START`（每个任务每次运行前——源表前置质量卡口）；详见 [`references/quality-config-matrix.md`](references/quality-config-matrix.md) §4
>   - `DEPENDENCY_SCHEDULE` 依赖调度
> **★调度类型 × 监控对象类型支持矩阵**（仅列 3 种核心触发式调度）：
>
> | 监控对象类型 | 定时 `PERIOD_SCHEDULE` | 数据更新触发 `CODE_CHECK_TRIGGER` | 固定任务触发 `STATIC_TASK_TRIGGER` |
> |---|:--:|:--:|:--:|
> | `TABLE` Dataphin 表 | ✅ | ✅ | ✅ |
> | `DATASOURCE_TABLE` 全域表 | ✅ | ❌ | ✅ |
> | `DATASOURCE` 数据源 | ✅ | ❌ | ✅ |
> | `INDEX` 指标 | ✅ | ✅ | ✅ |
> | `REALTIME_LOGICAL_TABLE` 实时元表 | ✅ | ✅ | ✅ |
>
> 即：`TABLE`/`INDEX`/`REALTIME_LOGICAL_TABLE` 支持全部 3 种；`DATASOURCE_TABLE`/`DATASOURCE` **只支持定时 + 固定任务触发，不支持数据更新触发**（OpenAPI 对其配 `CODE_CHECK_TRIGGER` 不报错但语义不该配，须自行规避）。`MANUAL_SCHEDULE`/`DEPENDENCY_SCHEDULE` 为合法枚举值，与对象类型的支持关系以界面为准。
> **★固定任务触发的节点获取引导（不要直接向用户要节点ID）**：
> 1. **先主动查产出节点**：用 `list-tables`（OpenAPI `ListTables`，参数名 `TableQuery`）按 `keyword`+`projectId`+`env` 定位目标表，读返回的 **`nodeIds`（List<String>，即产出任务节点）**——这就是 `--trigger-node-list` 要的值。注：`SearchCatalogTable` 的 `NodeIds` 恒为 null、不可用；取产出节点请用 `ListTables.nodeIds`。
> 2. **`nodeIds` 非空** → 列成候选清单给用户选：“该表的产出任务节点有 ①…②…，要监听哪个（可多选）跑完后触发校验？”
> 3. **`nodeIds` 为空 / 查不到**（如未绑定产出任务的逻辑表）→ 兜底问用户：“这张表没查到产出加工任务，固定任务触发需你指定一个真实调度节点，请给出要监听的任务名或节点ID。”
> 4. 拿到节点后必须确保是本租户真实存在的节点（否则 `assign`/创建报 `NodeNotFoundByIdAndTenantId`）。
> **触发时机同样不直接问枚举**：问业务场景（多上游合并/多来源增量/加工前卡口），再映射到 `ALL_TASKS_FINISHED`/`ONE_TASKS_FINISHED`/`PRE_ONE_TASKS_START`。
> **分区表调度必填校验范围表达式**（`validatePartitionType`/`partitionType=CUSTOM`/`partitionExpression`/`dateFormat`），详见 [`references/quality-config-matrix.md`](references/quality-config-matrix.md) §4。

### Step 6: 试跑验证（★默认收尾动作，先问一句）
```bash
# 分区表试跑必须钉单分区：--partition-expression-from CUSTOM + --partition-expression "ds=<真实分区值>"
aliyun dataphin-public submit-quality-rule-tasks --tenant-id "$TENANT_ID" \
  --is-test-run true \
  --watch-rule-id-list '{"watchId":"<wid>","ruleId":"<rid>"}' \
  --partition-expression-from "CUSTOM" --partition-expression "ds=20160710" \
  --user-agent "$UA"      # → RuleTaskId
aliyun dataphin-public get-quality-rule-task --tenant-id "$TENANT_ID" --rule-task-id "<tid>" --user-agent "$UA"
aliyun dataphin-public get-quality-rule-task-log --tenant-id "$TENANT_ID" --rule-task-id "<tid>" --user-agent "$UA"
```
> **★分区表必须钉单分区**（真实分区值 + `--partition-expression-from CUSTOM`），否则 OneService 拒绝全表扫描报错；真实分区值用「数据库SQL任务」跑 `SHOW PARTITIONS` 读取（见 quality-config-matrix.md §7）。
> **★判定结果三态**：`status=SUCCESS`+`validateResult=true`→通过；`SUCCESS`+`false`→校验不通过（真实检出异常，规则有效）；`status=FAILED`→**执行报错**（非校验不通过，真因看 log）。切勿只看 `validateResult` 下结论。
> **★试跑报错就直接抛出 + 分析日志给建议，不要一直卡着**：只要试跑任务**触发成功**（已拿到 `RuleTaskId`），轮询后无论 `status=FAILED`（执行报错）还是 `SUCCESS`+`validateResult=false`（校验不通过），都**不要反复重跑 / 静默重试 / 停在原地干等**。标准动作：① 立即 `get-quality-rule-task-log` 拉错误日志；② 把关键报错**原样抛给用户**（错误码 / 报错行 / 缺失字段 / 函数签名不匹配等）；③ 基于日志给出**具体修改建议**（如字段类型不符→换时间类型字段或改自定义 SQL；分区未钉→补 `--partition-expression`；`validateCondition` 缺失/缺 RELATION 根→按下方「常见坑」补齐；SQL 语法/权限错→指出对应行），可对照下方「常见坑」与 §8 各字段门控；④ 交回用户决策，由其订正后再决定是否重跑。**试跑失败不删除、不回滚已创建的规则**（见「执行前确认」，试跑结果仅如实告知）。

### Step 7: 开启校验开关
```bash
aliyun dataphin-public update-quality-rule-switch --tenant-id "$TENANT_ID" \
  --open true --rule-id-list "<rid>" --user-agent "$UA"
```

### Step 8: 定期检查与看板
```bash
aliyun dataphin-public get-quality-watch-task --tenant-id "$TENANT_ID" --watch-task-id "<wtid>" --user-agent "$UA"       # 查监控任务详情
aliyun dataphin-public list-quality-rule-tasks --tenant-id "$TENANT_ID" --watch-task-id "<wtid>" --user-agent "$UA"  # 按 watchTaskId 查每条规则的执行结果
aliyun dataphin-public list-quality-rules --tenant-id "$TENANT_ID" --watch-id "<wid>" --user-agent "$UA"    # 按 watchId 查规则定义与状态
```
> ⚠️ 两者不可互替：`list-quality-rules` 按 `watch-id` 查规则**定义/状态**；`list-quality-rule-tasks` 按 `watch-task-id` 查每条规则的**执行结果**。

### 执行前确认（写操作必备 / HITL）

> 本 skill 涉及写操作（`upsert-quality-watch` / `upsert-quality-rule` / `upsert-quality-schedule` / `assign-quality-rule-of-all-rule-scope-schedules` / `upsert-quality-watch-alert` / `submit-quality-rule-tasks` / `update-quality-rule-switch`）。调用 `upsert-quality-rule` **之前必须**向用户完整复述配置清单（表 / 字段 / 模板 / 维度 / 规则强度 / validateCondition / 归档 / 调度 / 告警）并明确请求确认：
> - **用户确认** → 执行；确认即承诺，此后**即使试跑失败也不删除、不回滚规则**（试跑结果仅如实告知）。
> - **用户未确认** → 一条规则都不创建。
> - 仅当创建过程**中途某步 API 报错**（产生半成品）时，才清理本次已建规则/调度以保持原子性。

仅当用户明确回复「确认 / yes / 执行」后才发起写命令。

## 9. Success Verification

> **重要原则**：命令行返回 `Code: OK` / `Success:true` 只表示请求受理，不等于界面配置完整。最终以 Dataphin 界面实际可见状态为唯一可信事实；自动化侧必须通过 `get-quality-watch*`、`list-quality-rules`、`get-quality-rule`、`get-quality-rule-task*` 等回查验证配置是否完整、规则是否启用、调度是否绑定、试跑是否成功。

三步法：
1. 同步返回 `Code: OK` ≠ 业务成功（写命令返回的 `WatchId`/`RuleId` 非空才算受理）。
2. `list-quality-rules` 反查命中新建规则，`ruleStatus` 正确。
3. 异步状态轮询：`get-quality-rule-task` 的 `status`（INIT/RUNNING/SUCCESS/FAILED）+ `validateResult`；FAILED 时 `get-quality-rule-task-log` 看真因。

详见 [`references/acceptance-criteria.md`](references/acceptance-criteria.md)。

## 10. Cleanup

```bash
# 解除调度绑定（如需）
aliyun dataphin-public remove-quality-rule-schedules --tenant-id "$TENANT_ID" \
  --watch-id "<wid>" --rule-id "<rid>" --schedule-id-list "<sid>" --user-agent "$UA"
# 关闭规则
aliyun dataphin-public update-quality-rule-switch --tenant-id "$TENANT_ID" \
  --open false --rule-id-list "<rid>" --user-agent "$UA"
```
> 已确认创建的规则默认保留；仅在中途报错产生半成品时清理本次资源。

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参，示例中用引号包住。
2. 写操作（upsert/assign/submit/switch）执行前必须 HITL 二次确认。
3. 监控对象类型是首问项；对象 ID、WatchName/tableName、复杂对象 JSON 均由查询结果自动推导，禁止让用户手写。
4. `templateId` 必须用 `list-quality-templates` 按当前租户/对象类型实测获取，不能照搬文档示例。
5. `formProperties` 必须按模板级必填项补齐；`FormPropertyList=null` 不能作为空配置依据；31 个系统模板以 `references/template-config-catalog.json` 为准。
6. `validateCondition` 无后端默认，**任何模板都必须显式传**，否则界面显示「未配置」且试跑失败。
7. 分区表试跑 / 调度必须钉真实单分区，避免全表扫描被拒。
8. 调度需 `assign-quality-rule-of-all-rule-scope-schedules` 显式绑定，仅创建不生效。

### ✗ 平台限制

#### ✗ 归档模式 / 归档位置 / 计分方式 / 质量分权重 OpenAPI 不可配
- 限制描述：`upsert-quality-rule` 请求参数不含这些字段，创建后后端自动填默认（归档=仅归档异常字段、位置=默认文件服务器、计分=质量校验状态、权重=1）。
- 替代方案：如需自定义只能到界面手工操作。

#### ✗ 单规则级告警不支持
- 限制描述：告警是 watch 级别，对该监控对象下所有规则生效。
- 替代方案：N/A（无法按单规则配）。

### 常见坑

#### [用户纠偏] 独立部署 CLI 报 `bad file descriptor` → 改走 OpenAPI 直调
- 现象：独立部署/POC 环境下 `aliyun dataphin-public` 对 HTTPS endpoint 直接报 `dial tcp ... connect: bad file descriptor`，`curl` 能通但 Go CLI 不通；加 `--endpoint`/`--skip-secure-verify`/重试均无效。
- 结论：这是 POC 独立部署已知 CLI 网络层 bug。**判定为独立部署时默认直接调 OpenAPI**（阿里云 Python SDK，RPC，自签证书 `verify=False`），不要再走 CLI；公共云才用 CLI。详见 §3「执行通道」。

#### [用户纠偏] OpenAPI 直调报 `Unknown API` → Action 名用 `--cli-dry-run` 导出
- 现象：独立部署直调 OpenAPI 时，用文档里的 `PagedQueryQualityWatches`/`SaveQualityWatch` 等名报 `Unknown API`；换用 `--cli-dry-run` 导出才拿到真实名 `ListQualityWatches`/`UpsertQualityRule` 等。
- 根因：`PagedQuery*`/`Save*`/`Remove*` 是旧裸 OpenAPI 命名；POC 的 CLI 插件对应的真实 Action 名 = **CLI kebab 命令的 PascalCase**（`list-quality-watches`→`ListQualityWatches`、`upsert-quality-rule`→`UpsertQualityRule`）。
- 结论：拿不准就 `aliyun dataphin-public <command> --cli-dry-run` 导出真实 Action 名与参数再用 Python SDK 调；不要硬编码/猜名。详见 §3「执行通道」。

#### [用户纠偏] POC 直调签名失败 `SignatureDoesNotMatch` → 业务参数必须进 query string 参与签名
- 现象：Python SDK 直调 OpenAPI 签名始终失败（`SignatureDoesNotMatch`），即使 AK/SK 正确、Action 名正确、endpoint 可达。
- 根因：POC standalone 要求业务参数放在 query string 里参与签名；而 `aliyunsdkcore` 默认把参数塞进 request body，body 参数不进签名串 → 签名不一致。
- 结论：所有业务参数用 `add_query_param` 进 query string，禁用 body（`add_body_params`）；SDK 仍不过就**手动签名 + query string 传参**（实测 `ListQualityWatches` 可正常返回）。详见 §3 Python SDK 骨架与签名要点。

#### [用户纠偏] 卡在“找资产” → 有效信息全用上查 watch，不够就主动问用户
- 现象：为定位对象 ID 反复用 `GetBizMetricByName`/`ListTables`（draft true/false、多种名称组合）都返回「资产不存在」，卡住无法推进；或只用 `--keyword` 搜指标 code 搜不到（`Keyword` 只匹配「监控表名称」，对 INDEX 无效）。
- 结论：不要盲搜资产。① **把用户给的有效信息全部映射成 `ListQualityWatches` 过滤参数**（类型→`--watch-type-list`、板块→`--biz-unit-name-list`、项目→`--project-name-list`、负责人→`--index-owner-list` 等），命中就复用 `WatchId`；② **命中多条 / 关键信息不足 → 主动告知用户还缺什么、或直接要 `WatchId`/`indexId`**；③ 确认无 watch 需新建但缺对象 ID：表用 `list-tables` 定位，指标无 list 接口可搜→直接请用户给 `indexId`（不能用 `list-catalog-assets` 兜底，它只查资产目录已上架资产，监控对象取自资产清单）；④ 创建报错原样告知并引导。详见 §8 Step 3。

#### [Agent 自主发现] validateCondition 不传 → 规则不完整
- 现象：`upsert-quality-rule` 不传 `--validate-condition-list` 时，界面打开显示「未配置」，试跑失败。
- 结论：任何模板都必须显式传 `validateCondition`，空值/唯一校验推荐 `ERROR_NUMBER=0`。

#### [用户纠偏] 缺 RELATION 根节点 → 界面「统计指标」为空
- 现象：`--validate-condition-list` 只传了单个 `EXPRESSION`（当根节点、无 `parentId`），或漏了 `type=RELATION` 根。虽然 `get-quality-rule` 能查到 `Metric`，但界面「校验配置→规则校验」的「统计指标」显示为空/未配置。INDEX（指标）稳定性/波动性规则尤为典型。
- 根因：界面按「RELATION 根 + 其下 EXPRESSION（`parentId` 关联）」的嵌套语义解析，识别不了裸 EXPRESSION。
- 结论：条件列表**第一个元素必须是 `type=RELATION` 根**（`operator=OR/AND`），所有 `EXPRESSION` 通过 `parentId` 挂到根（或内层 RELATION）下——**单条件也不例外**。复杂多指标「与/或」写法见 [`references/quality-config-matrix.md`](references/quality-config-matrix.md) §2。

#### [用户纠偏] 只看 API 顶层必填 → 漏掉模板级必填项
- 现象：`SaveQualityRule.formProperties` / CLI `--form-property-list` 顶层看似可选，规则也可能返回创建成功，但界面里模板配置为空或必填项缺失。
- 例子：`TABLE_SCHEMA_CHECK` / templateId `2600`「表结构异动监测」在界面必须选择校验表；创建时必须传 `dataSourceTable`（完整表元数据 JSON），不能传空 `formProperties`。
- 结论：创建规则前先查 `list-quality-templates` 获取真实 `Id/Type/Catalog`，再按模板定义和界面必填项补齐 `--form-property-list`。

#### [用户纠偏] templateId 不能照搬文档示例
- 现象：文档示例里的模板 ID 在目标租户可能不存在，直接创建会报模板不存在。
- 结论：使用 `list-quality-templates` 按 `--watch-type-list` / `--template-source-list SYSTEM` 查询当前租户真实模板；env23 实测返回在 `PageResult.QualityTemplateList[]` 中，字段为 `Id`/`Name`/`Type`/`Catalog`。

#### [Agent 自主发现] timeTolerance（时间差）必须传 3 元素 JSON 数组
- 现象：T600/T700/T800 时间类模板的 `timeTolerance` 是 `TIME_TOLERANCE` 复合组件。早期传单对象 JSON（如 `{"unit":"d","value":"1","operator":"<"}`）或简单字符串（如 `<1d`）导致后端数据损坏：`get-quality-rule` 返回 `InternalError`，拖垮 `list-quality-rules` 接口。
- 根因：后端期望 `timeTolerance` 的 `Value` 是 3 元素 JSON 数组（条件1 + 条件2 + 比较类型），传单对象格式触发反序列化异常。
- 正确格式：`Value=[{"checked":true,"operate":">","time":0,"type":"DAY"},{"checked":true,"operate":"<","time":1,"type":"DAY"},{"timeCompareMethod":"VALIDATE_SUB_COMPARE"}]`
- 结论：`timeTolerance` 可以通过 CLI 正确传值，**必须使用 3 元素 JSON 数组格式**，默认建议 `>0天 且 <1天`。

#### [Agent 自主发现] 时间类模板字段必须是日期时间类型
- 现象：T600/T700/T800 试跑报 `Semantic analysis exception - function datediff cannot match any overloaded functions with (BIGINT, BIGINT, STRING)`。
- 根因：时间类模板底层生成 `datediff(校验项, 比较项, '单位')`，但配置时把 `id` 等 BIGINT 字段填到了 `validateField`/`validateItem`/`compareItem`，导致 `datediff(BIGINT, BIGINT, STRING)` 无可匹配重载。
- 结论：时间类模板只能选择 `DATE`/`DATETIME`/`TIMESTAMP`/`TIMESTAMP_NTZ` 等真实时间字段或时间表达式；禁止用 BIGINT 主键、订单号、时间戳数字、yyyymmdd 数字直接配置。若业务时间存为 BIGINT，需提供转换后的时间字段，或改用自定义 SQL 模板显式转换。

#### [Agent 自主发现] 分区表试跑不指定分区 → 全表扫描被拒
- 现象：分区表试跑不带 `--partition-expression` 时报 `full scan with all partitions`。
- 结论：用 `partitionType=CUSTOM` + 具体真实分区值钉单分区（连唯一性校验也钉单分区）。

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
- [`references/quality-config-matrix.md`](references/quality-config-matrix.md)（界面↔API 对照 / 模板查询 / 模板级必填 / validateCondition / 调度矩阵 / 试跑坑 / 数据源表取字段）
- [`references/template-config-catalog.json`](references/template-config-catalog.json)（31 个系统规则模板的支持监控对象类型 / 规则配置项 / 校验配置指标与选项，含 3 个实时元表专用模板）
