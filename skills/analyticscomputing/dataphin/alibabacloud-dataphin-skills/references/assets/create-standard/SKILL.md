---
name: create-standard
description: |-
  创建数据标准（包括元数据监控 METADATA 和质量监控 QUALITY）。 触发场景：创建数据标准 / 新建质量规则 / 添加元数据监控 / create-standard / StandardMonitorConfigList。 监控类型 Type（METADATA / QUALITY）决定 StandardMonitorConfigList 子元素字段组合；QUALITY 需 RuleSubType / QualityRuleTemplate / RuleConfigList / RuleValidateConfigList。 触发词：创建数据标准、新建质量规则、元数据监控、create-standard、StandardMonitorConfigList、METADATA、QUALITY。
---

# 创建数据标准 Skill

## 1. Scenario Description

场景：在标准模板（StandardTemplate）+ 标准集（StandardSet）下新增一条数据标准，并为其挂载「元数据监控（METADATA）」或「数据质量监控（QUALITY）」。

### Architecture

```
用户请求 → 确认参数 → 选择监控类型 Type
  → METADATA：只校验元数据（描述/命名/属性），不查表数据
  → QUALITY：对实际表数据做指标统计 + 阈值告警
  → create-standard 提交
  → get-standard / list-standards 验证
```

### 涉及 Dataphin OpenAPI

- `CreateStandard` — 创建数据标准（[官方文档](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/CreateStandard)）
- `GetStandard` — 获取标准详情（创建后验证）
- `ListStandards` — 分页查询标准列表
- `UpdateStandard` / `OfflineStandard` / `PublishStandard` — 后续生命周期操作

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

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 仅额外要求下列变量：

| 变量 | 说明 | 必须 |
|------|------|------|
| `DATAPHIN_INSECURE` | 独立部署自签证书时设为 `true` 跳过 TLS 校验 | 独立部署必须 |

> **独立部署（非公共云）注意**：
> - 凭证 profile 必须带正确的 `--endpoint`（如 `dataphin-openapi.<your-domain>`），否则请求会打到公共云 `dataphin-public.<region>.aliyuncs.com` 报 `InvalidAccessKeyId.NotFound`。
> - 自签证书环境需 `export DATAPHIN_INSECURE=true`（推荐），或在命令**末尾**追加 `--insecure`（`--insecure` 非解析 flag，放在参数中间会吞掉下一个参数值）。

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

### Pre-check: Aliyun CLI plugin update required

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
>
> 执行前确认 CLI 与插件版本：
> ```bash
> aliyun version
> aliyun plugin list
> ```

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 skill 最小权限见 [../../ram-policies.md](../../ram-policies.md)。

## 6. IMPORTANT: Parameter Confirmation

执行 `create-standard` 前必须向用户确认以下参数，禁止静默提交：

| 参数 | 说明 |
|------|------|
| `--tenant-id` | 租户 ID（`--op-tenant-id` 的别名，profile 已配置时可省） |
| `--standard-template-reference` | 引用的标准模板 **+ 标准属性值** `{"Id":<模板 Id>,"AttributeValueList":[{"AttributeId":<属性 Id>,"Value":"<值>"}]}` |
| 标准编码 / 标准名称 / 数据类型等**属性值** | 逐项确认，**写在上一行的 `AttributeValueList` 里**（不是监控配置里，见 §7 步骤 0） |
| `--standard-set-reference` | 所属标准集 `{"Id":<标准集 Id>}` |
| 监控类型 `Type` | `METADATA`（只校验元数据）或 `QUALITY`（校验表数据） |
| `--standard-general-monitor-config` | 监控配置 JSON（**只放监控规则，不放属性值**；类型分支核心，见 §7） |

## 7. Core Workflow

### 步骤 0（必做前置）· 取模板属性的 Code → AttributeId 映射

标准的「标准编码 / 标准名称 / 数据类型 / 是否唯一 / 是否可空」等**属性值**，通过 `--standard-template-reference` 的 `AttributeValueList` 传入，元素为 `{"AttributeId":<属性 Id>,"Value":"<值>"}`——**AttributeId 是模板里属性的 Id，必须先查模板拿到**，不能凭属性编码（如 `code`/`name`）猜。

```bash
# 取模板属性清单：Id / Code / Name / Required（--cli-query 裁剪，避免整模板上万字符进上下文）
aliyun dataphin-public get-standard-template --tenant-id <tenant-id> \
  --standard-template-id <模板 Id> --nullable false \
  --cli-query 'TemplateInfo.AttributesConfig.AttributeList[].{Id:Id,Code:Code,Name:Name,Required:Required}' \
  --user-agent AlibabaCloud-Agent-Skills/create-standard/{session-id} --format json
```

返回形如（Id 为 19 位以内大整数，JSON 里按数值传，展示时按字符串保留精度）：

```json
[
  { "Id": 1011, "Code": "code", "Name": "标准编码", "Required": true },
  { "Id": 1012, "Code": "name", "Name": "标准名称", "Required": true },
  { "Id": 1013, "Code": "data_type", "Name": "数据类型", "Required": true }
]
```

把它转成 `Code → Id` 映射后，按业务值组装：

```bash
--standard-template-reference '{
  "Id": 11,
  "AttributeValueList": [
    { "AttributeId": 1011, "Value": "CUSTOMER_CODE" },
    { "AttributeId": 1012, "Value": "客户编码标准" },
    { "AttributeId": 1013, "Value": "STRING" }
  ]
}'
```

> **Required=true 的属性一个都不能漏**，否则报 `DPN.DataStandard.Standard.RequiredAttributeValueIsBlank: 必填属性:[标准编码] 的值 为空`（见 §9 坑 1）。
> 若希望标准编码由平台按编码规则自动生成，加 `--need-generate-standard-code true`，此时 `AttributeValueList` 里填的标准编码会被忽略。
> 属性值受模板的 `ValueConfig` 约束（`SINGLE_ENUM` / `LOOKUP_TABLE` / `RANGE` 等只能取合法值），组装前先看步骤 0 返回里的 `ValueConfig`。

### 顶层参数骨架

```text
--tenant-id <int>                        必填 | 租户 ID（--op-tenant-id 别名）
--standard-template-reference <JSON>     必填 | 引用的标准模板 + AttributeValueList（★ 标准属性值在此）
--standard-set-reference <JSON>          必填 | 所属标准集
--effective-time-config <JSON>           可选 | 生效时间配置
--description <string>                   可选 | 描述
--owner <string>                         可选 | 负责人 ID（不传为当前用户）
--standard-general-monitor-config <JSON> 可选 | 标准监控配置 ★ 类型分支核心
--need-generate-standard-code            可选 | 是否基于规则重新生成标准编码
```

### StandardMonitorConfigList 单元素结构（类型分支核心）

> 本段是**监控规则**配置，与标准属性值无关。属性值只走 `--standard-template-reference.AttributeValueList`（步骤 0）。

```jsonc
{
  "Id": 1,                       // 可选 | 已有配置 ID 时表示更新；为空表示新增
  "RuleName": "test",            // 必填 | 规则名称
  "Description": "test",         // 可选 | 规则描述
  "Type": "METADATA|QUALITY",    // ★ 必填 | 监控类型，决定下方字段是否必填
  "MonitorFrom": "BY_USER|BY_SYSTEM_ATTRIBUTE", // 必填 | 添加方式
  "AttributeId": 112,            // 可选 | 关联属性 Id（BY_SYSTEM_ATTRIBUTE 时常用）
  "AttributeName": "...",        // 可选 | 属性名
  "AttributeMonitorConfig": {    // 可选 | 关联属性的监控配置
    "Type": "METADATA|QUALITY",
    "ColumnName": "column1",
    "IsCaseSensitive": false
  },

  // === 当 Type = QUALITY 时以下 4 项必填 ===
  "RuleSubType": "BY_ATTRIBUTE|CUSTOMIZED",
  "QualityRuleTemplate": {
    "Id": 22,
    "Type": "FROM_SYSTEM|CUSTOMIZED", // 模板来源
    "Name": "..."
  },
  "RuleConfigList": [
    { "Key": "k1", "Value": "v1" }
  ],
  "RuleValidateConfigList": [
    {
      "Id": "abc",                // 业务侧生成的唯一字符串
      "ParentId": "a",            // 可选；父校验配置 Id（父必为 RELATION）
      "Type": "RELATION|EXPRESSION",
      "Operator": "AND|OR | EQUAL|NOT_EQUAL|LARGER|LARGE_OR_EQUAL|SMALLER|SMALLER_OR_EQUAL",
      "Metric": "a",              // EXPRESSION 时必填
      "MetricName": "test",       // EXPRESSION 时必填
      "Value": "1"                // 比较值
    }
  ]
}
```

### 分支 1 · Type = METADATA（元数据监控）

只对元数据本身（是否有描述、字段命名是否合规、属性是否填齐）做检查，**不查询表数据**。无需 `RuleSubType / QualityRuleTemplate / RuleConfigList / RuleValidateConfigList`。

```bash
aliyun dataphin-public create-standard \
  --tenant-id <tenant-id> \
  --standard-template-reference '{"Id":11,"AttributeValueList":[{"AttributeId":1011,"Value":"CUSTOMER_CODE"},{"AttributeId":1012,"Value":"客户编码标准"},{"AttributeId":1013,"Value":"STRING"}]}' \
  --standard-set-reference     '{"Id":22}' \
  --description "元数据标准示例" \
  --standard-general-monitor-config '{
    "StandardMonitorConfigList": [
      {
        "RuleName": "字段必须有描述",
        "Type": "METADATA",
        "MonitorFrom": "BY_SYSTEM_ATTRIBUTE",
        "AttributeId": 112,
        "AttributeMonitorConfig": {
          "Type": "METADATA",
          "ColumnName": "description",
          "IsCaseSensitive": false
        }
      }
    ]
  }' \
  --user-agent AlibabaCloud-Agent-Skills/create-standard/{session-id}
```

### 分支 2 · Type = QUALITY（数据质量监控）

对**实际表数据**做指标统计 + 阈值告警（主键唯一、字段非空、值域、跨表关联等）。

| RuleSubType | 含义 | 必填字段 |
|-------------|------|---------|
| `BY_ATTRIBUTE` | 沿用标准属性预置的质量规则 | AttributeId / AttributeMonitorConfig（指向具体列） |
| `CUSTOMIZED` | 自由配置规则模板和阈值 | QualityRuleTemplate / RuleConfigList / RuleValidateConfigList |

CUSTOMIZED 示例：

```bash
aliyun dataphin-public create-standard \
  --tenant-id <tenant-id> \
  --standard-template-reference '{"Id":11,"AttributeValueList":[{"AttributeId":1011,"Value":"ORDER_AMOUNT"},{"AttributeId":1012,"Value":"订单金额标准"},{"AttributeId":1013,"Value":"DOUBLE"}]}' \
  --standard-set-reference     '{"Id":22}' \
  --standard-general-monitor-config '{
    "StandardMonitorConfigList": [
      {
        "RuleName": "金额非负且小于 10000",
        "Type": "QUALITY",
        "MonitorFrom": "BY_USER",
        "RuleSubType": "CUSTOMIZED",
        "QualityRuleTemplate": { "Id": 22, "Type": "CUSTOMIZED", "Name": "区间校验" },
        "RuleConfigList": [ { "Key": "column", "Value": "amount" } ],
        "RuleValidateConfigList": [
          { "Id": "v1", "Type": "RELATION", "Operator": "AND" },
          { "Id": "v2", "ParentId": "v1", "Type": "EXPRESSION", "Operator": "LARGE_OR_EQUAL", "Metric": "amount", "MetricName": "amount", "Value": "0" },
          { "Id": "v3", "ParentId": "v1", "Type": "EXPRESSION", "Operator": "SMALLER", "Metric": "amount", "MetricName": "amount", "Value": "10000" }
        ]
      }
    ]
  }' \
  --user-agent AlibabaCloud-Agent-Skills/create-standard/{session-id}
```

> RuleValidateConfigList 是一棵「父 RELATION + 子 EXPRESSION」的树：
> - `RELATION` 节点（AND/OR）作为分组，子节点的 `ParentId` 指向其 `Id`
> - `EXPRESSION` 节点（EQUAL/NOT_EQUAL/LARGER/LARGE_OR_EQUAL/SMALLER/SMALLER_OR_EQUAL）是叶子，必填 `Metric`、`MetricName`、`Value`

### 分支判定速查

| 你想做的事 | Type | RuleSubType | 是否需要 QualityRuleTemplate / RuleConfigList / RuleValidateConfigList |
|------------|------|-------------|----------------------------------------------------------------------|
| 检查元数据合规 | `METADATA` | — | 否 |
| 用属性预置质量规则 | `QUALITY` | `BY_ATTRIBUTE` | 否（依赖 AttributeId） |
| 自定义质量规则 | `QUALITY` | `CUSTOMIZED` | **是（三项都要）** |

## 8. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/create-standard/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 9. 常见坑

1. **报 `RequiredAttributeValueIsBlank: 必填属性:[标准编码] 的值 为空` → 属性值放错了位置（实测高频坑）**：属性值**只能**放 `--standard-template-reference` 的 `AttributeValueList`（元素 `{"AttributeId":<属性 Id>,"Value":"..."}`）。往 `--standard-general-monitor-config` 里放任何形式的属性值都无效——实测曾有 Agent 依次试 `{"code":...}` / `AttributeValues` / `StandardAttributeValueList` / `StandardAttributeList` / `AttributeList` **五种写法全部报同一个错**。**看到这个错不要在 monitor-config 里换字段名重试**，直接回到 §7 步骤 0：先 `get-standard-template` 取 `AttributeList[].{Id,Code,Required}`，再把值挂到 `AttributeValueList`。
2. **AttributeId 不能用属性编码代替**：`AttributeValueList` 只认 `AttributeId`（数值），不认 `AttributeCode`；必须从模板查出 Id。
3. **不要手拼 `--create-command` 整个 body**：该 flag 虽能被接受但 `--help` 不列，自拼顶层字段会报 `Error: unknown field: xxx`（实测曾连续 9 次换字段名全失败）。一律用 `--help` 列出的扁平参数（`--standard-template-reference` / `--standard-set-reference` / …）；看到 `unknown field` 就停下来查 `--help`，不要穷举字段名。
4. **RuleValidateConfigList 的 Id 必须业务侧生成且唯一**：建议用 `v1/v2/v3` 或 UUID
5. **ParentId 仅指向 RELATION 节点**：表达式之间的「且/或」必须通过一个 RELATION 父节点串联，不能两个 EXPRESSION 平铺
6. **Operator 与 Type 严格对应**：`RELATION` 只能 `AND/OR`；`EXPRESSION` 只能比较运算符
7. **MonitorFrom**：纯手工添加用 `BY_USER`；走系统属性预置（绑定 AttributeId）用 `BY_SYSTEM_ATTRIBUTE`
8. **EffectiveTimeConfig.Type=TIME_PERIOD 时**必须同时给 `StartTime` + `EndTime`，格式 `YYYY-MM-DD HH:mm:ss`
9. **`--standard-general-monitor-config` 传 JSON 字符串**：bash 用外单内双 `'{"...":"..."}'`；含中文描述时 LANG/LC_ALL 设为 UTF-8
10. **标准集重名不要重建**：`create-standard-set` 报 `StandardSetWithDuplicatedNameDetected` 时，错误消息里已给出已有标准集 Id，直接用它当 `--standard-set-reference`，不要改名新建。

## 10. Cleanup

创建产生的标准如需清理（如验证阶段真实创建的测试标准），先查出 standard-id 再删除：

```bash
# 查出标准 Id（需指定阶段 DEV/PROD）
aliyun dataphin-public list-standards --tenant-id <tenant-id> \
  --standard-stage DEV \
  --user-agent AlibabaCloud-Agent-Skills/create-standard/{session-id} --format json

# 删除标准（create-standard 的反向操作）
aliyun dataphin-public delete-standard --tenant-id <tenant-id> \
  --standard-id <standard-id> \
  --user-agent AlibabaCloud-Agent-Skills/create-standard/{session-id} --format json
```

> `delete-standard` 为直接删除；若只需状态下线而保留标准，用 `offline-standard`（额外必填 `--comment`）。
> 执行前可先加 `--cli-dry-run` 预检请求体，确认无误后再去掉该 flag 正式执行。

## 11. Command Tables

详见 [`references/related-commands.md`](./references/related-commands.md)。

## 12. Best Practices + Reference Links

1. **先选对 Type 再填 config**：METADATA 与 QUALITY 的必填字段完全不同，先定分支再拼 JSON
2. **写操作先 dry-run 预检**：正式执行前加 `--cli-dry-run` 校验请求体结构
3. **写操作必须 HITL 确认**：创建标准前向用户确认模板/标准集 Id 与监控配置
4. **大整数 ID 字符串传参**：owner / 属性 Id 等如为大整数，用引号包住避免精度丢失
5. **命令名以 `--help` 为准**：查询列表命令是 `list-standards`（复数），不是 `list-standard`

### Reference Links

- [`references/cli-installation-guide.md`](./references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](./references/acceptance-criteria.md)
- [`references/related-commands.md`](./references/related-commands.md)

## 13. 相关命令

- `aliyun dataphin-public update-standard` — 修改已建标准的监控配置，结构同构，见 `update-standard`（经套件入口路由加载）
- `aliyun dataphin-public offline-standard` — 下线标准
- `aliyun dataphin-public publish-standard` — 发布标准
- `aliyun dataphin-public list-standards` / `get-standard` — 查询已存在标准（可参考现有标准怎么填 RuleConfigList）
