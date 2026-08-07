---
name: update-standard
description: |-
  更新/编辑已有数据标准（含元数据监控 METADATA 和质量监控 QUALITY）。 触发场景：修改数据标准 / 更新质量规则 / 调整监控配置 / update-standard。 监控类型 Type（METADATA / QUALITY）决定 StandardMonitorConfigList 子元素字段组合，QUALITY 需 RuleSubType / QualityRuleTemplate 等。 StandardMonitorConfigList 子元素的 Id 决定新增/更新/删除。 触发词：修改数据标准、更新质量规则、调整监控配置、update-standard、StandardMonitorConfigList、METADATA、QUALITY。
---

# 更新数据标准 Skill

## 1. Scenario Description

场景：修改已有数据标准——调整描述/负责人/生效时间，或新增/修改/删除其监控配置（METADATA / QUALITY），也可切换监控类型或 RuleSubType。

### Architecture

```
用户请求 → get-standard 拉取当前全量配置（避免漏列触发误删）
  → 确认参数（--standard-id / --standard-status 必填）
  → 按 StandardMonitorConfigList[i].Id 决定新增(无 Id)/更新(带现有 Id)/删除(省略现有 Id)
  → update-standard 提交
  → get-standard / list-standards 验证
```

### 涉及 Dataphin OpenAPI

- `UpdateStandard` — 更新数据标准（[官方文档](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/UpdateStandard)）
- `GetStandard` — 更新前拉取当前配置、更新后验证
- `ListStandards` — 分页查询标准列表（定位 `--standard-id`）
- `CreateStandard` / `OfflineStandard` / `PublishStandard` — 相关生命周期操作

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

执行 `update-standard` 前必须向用户确认以下参数，禁止静默提交：

| 参数 | 说明 |
|------|------|
| `--tenant-id` | 租户 ID（`--op-tenant-id` 的别名，profile 已配置时可省） |
| `--standard-id` | **必填**：待更新的标准 Id |
| `--standard-status` | **必填**：标准状态（如 `EFFECTIVE` / `DRAFT`，不确定时先 `get-standard` 看现状回填） |
| `--standard-template-reference` | 引用的标准模板 **+ 标准属性值** `{"Id":<模板 Id>,"AttributeValueList":[{"AttributeId":<属性 Id>,"Value":"<值>"}]}` |
| 标准编码 / 标准名称 / 数据类型等**属性值** | 逐项确认，**写在上一行的 `AttributeValueList` 里**（不是监控配置里，见 §7 步骤 0） |
| `--standard-set-reference` | 所属标准集 `{"Id":<标准集 Id>}` |
| `--standard-general-monitor-config` | 监控配置 JSON（**只放监控规则，不放属性值**）；**注意子元素 Id 决定增/改/删（见 §7）** |

## 7. Core Workflow

### 步骤 0（必做前置）· 属性值走 AttributeValueList，且是整体覆盖

标准的「标准编码 / 标准名称 / 数据类型」等**属性值**只能通过 `--standard-template-reference.AttributeValueList` 传，元素 `{"AttributeId":<属性 Id>,"Value":"<值>"}`；**放到 `--standard-general-monitor-config` 里无效**（会报 `RequiredAttributeValueIsBlank`，见 §9 坑 1）。

更新前必做两件事：

```bash
# 1) 取现有属性值（避免覆盖丢字段）
aliyun dataphin-public get-standard --tenant-id <tenant-id> --standard-id "<标准 Id>" \
  --nullable false --user-agent AlibabaCloud-Agent-Skills/update-standard/{session-id} --format json

# 2) 取模板属性 Code → Id 映射（--cli-query 裁剪）
aliyun dataphin-public get-standard-template --tenant-id <tenant-id> \
  --standard-template-id <模板 Id> --nullable false \
  --cli-query 'TemplateInfo.AttributesConfig.AttributeList[].{Id:Id,Code:Code,Name:Name,Required:Required}' \
  --user-agent AlibabaCloud-Agent-Skills/update-standard/{session-id} --format json
```

> `AttributeValueList` 与监控配置不同，**没有逐元素增/改/删语义——传什么就是全量**：只想改一个属性也必须把其他属性值一并带上，否则 Required 属性会变空而报错。
> 带 `--need-generate-standard-code true` 时，`AttributeValueList` 里的标准编码被忽略（平台按规则重新生成）。

### 顶层参数骨架

```text
--tenant-id <int>                        必填 | 租户 ID（--op-tenant-id 别名）
--standard-id <int>                      必填 | 待更新的标准 Id
--standard-status <string>               必填 | 标准状态（EFFECTIVE / DRAFT 等）
--standard-template-reference <JSON>     必填 | 引用的标准模板 + AttributeValueList（★ 标准属性值在此，整体覆盖）
--standard-set-reference <JSON>          必填 | 所属标准集
--version <int>                          可选 | 版本号（不传服务端按当前版本）
--effective-time-config <JSON>           可选 | 生效时间配置
--description <string>                   可选 | 描述
--owner <string>                         可选 | 负责人 ID（不传为当前用户）
--standard-general-monitor-config <JSON> 可选 | 标准监控配置 ★ 类型分支 + 增改删核心
--need-generate-standard-code            可选 | 是否基于规则重新生成标准编码
```

> 与 `create-standard` 的关键差异：
> 1. **多了必填 `--standard-id` + `--standard-status`（及可选 `--version`）**
> 2. body 包装是 `UpdateCommand` 而非 `CreateCommand`（CLI 已处理，无需手填）

### StandardMonitorConfigList[i].Id 决定新增 / 更新 / 删除（更新特有）

| 场景 | 子元素 Id | 说明 |
|------|-----------|------|
| 新增一条监控 | **不传 Id** | 服务端新增 |
| 更新已有监控 | **传现有 Id** | 服务端按 Id 更新该条 |
| 删除某条监控 | **在请求中省略该 Id** | 已有 Id 未列出即视为删除 |

> ⚠ **更新前务必先 `get-standard` 拉取当前 `StandardMonitorConfigList` 全量**，在其基础上增删改后回传完整列表，避免漏列已有 Id 触发误删。

### StandardMonitorConfigList 单元素结构（与 create-standard 同构，更新场景带 Id）

```jsonc
{
  "Id": 1001,                    // ★ 更新已有配置时必填；新增时省略
  "RuleName": "test",            // 必填 | 规则名称
  "Type": "METADATA|QUALITY",    // ★ 必填 | 监控类型，决定下方字段是否必填
  "MonitorFrom": "BY_USER|BY_SYSTEM_ATTRIBUTE", // 必填
  "AttributeId": 112,            // 可选 | 关联属性 Id
  "AttributeMonitorConfig": { "Type": "METADATA|QUALITY", "ColumnName": "column1", "IsCaseSensitive": false },

  // === 当 Type = QUALITY 时以下按 RuleSubType 必填 ===
  "RuleSubType": "BY_ATTRIBUTE|CUSTOMIZED",
  "QualityRuleTemplate": { "Id": 22, "Type": "FROM_SYSTEM|CUSTOMIZED", "Name": "..." },
  "RuleConfigList": [ { "Key": "k1", "Value": "v1" } ],
  "RuleValidateConfigList": [
    { "Id": "abc", "ParentId": "a", "Type": "RELATION|EXPRESSION",
      "Operator": "AND|OR | EQUAL|NOT_EQUAL|LARGER|LARGE_OR_EQUAL|SMALLER|SMALLER_OR_EQUAL",
      "Metric": "a", "MetricName": "test", "Value": "1" }
  ]
}
```

### 分支 1 · Type = METADATA（更新元数据监控）

只校验元数据本身，**不查询表数据**。无需 `RuleSubType / QualityRuleTemplate / RuleConfigList / RuleValidateConfigList`。

```bash
aliyun dataphin-public update-standard \
  --tenant-id <tenant-id> \
  --standard-id <standard-id> \
  --standard-status EFFECTIVE \
  --standard-template-reference '{"Id":11,"AttributeValueList":[{"AttributeId":1011,"Value":"CUSTOMER_CODE"},{"AttributeId":1012,"Value":"客户编码标准"},{"AttributeId":1013,"Value":"STRING"}]}' \
  --standard-set-reference     '{"Id":22}' \
  --description "更新后的元数据标准描述" \
  --standard-general-monitor-config '{
    "StandardMonitorConfigList": [
      {
        "Id": 1001,
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
  --user-agent AlibabaCloud-Agent-Skills/update-standard/{session-id}
```

### 分支 2 · Type = QUALITY（更新数据质量监控）

对**实际表数据**做指标统计 + 阈值告警。

| RuleSubType | 含义 | 必填字段 |
|-------------|------|---------|
| `BY_ATTRIBUTE` | 沿用标准属性预置的质量规则 | AttributeId / AttributeMonitorConfig（指向具体列） |
| `CUSTOMIZED` | 自由配置规则模板和阈值 | QualityRuleTemplate / RuleConfigList / RuleValidateConfigList |

CUSTOMIZED 示例（在待更新子元素上带 `Id`）：

```bash
aliyun dataphin-public update-standard \
  --tenant-id <tenant-id> \
  --standard-id <standard-id> \
  --standard-status EFFECTIVE \
  --standard-template-reference '{"Id":11,"AttributeValueList":[{"AttributeId":1011,"Value":"CUSTOMER_CODE"},{"AttributeId":1012,"Value":"客户编码标准"},{"AttributeId":1013,"Value":"STRING"}]}' \
  --standard-set-reference     '{"Id":22}' \
  --standard-general-monitor-config '{
    "StandardMonitorConfigList": [
      {
        "Id": 1003,
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
  --user-agent AlibabaCloud-Agent-Skills/update-standard/{session-id}
```

> RuleValidateConfigList 是一棵「父 RELATION + 子 EXPRESSION」的树：
> - `RELATION` 节点（AND/OR）作为分组，子节点的 `ParentId` 指向其 `Id`
> - `EXPRESSION` 节点（EQUAL/NOT_EQUAL/LARGER/LARGE_OR_EQUAL/SMALLER/SMALLER_OR_EQUAL）是叶子，必填 `Metric`、`MetricName`、`Value`

### 分支判定速查

| 你想做的事 | Type | RuleSubType | 子元素 Id | 是否需要 QualityRuleTemplate / RuleConfigList / RuleValidateConfigList |
|------------|------|-------------|-----------|----------------------------------------------------------------------|
| 新增元数据监控 | `METADATA` | — | 不传 | 否 |
| 更新已有质量监控 | `QUALITY` | `CUSTOMIZED` | 传现有 Id | **是（三项都要）** |
| 用属性预置质量规则 | `QUALITY` | `BY_ATTRIBUTE` | 视情况 | 否（依赖 AttributeId） |
| 删除某条监控 | — | — | 省略该 Id | — |

## 8. Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/update-standard/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 9. 常见坑

1. **报 `RequiredAttributeValueIsBlank: 必填属性:[标准编码] 的值 为空` → 属性值放错了位置（实测高频坑）**：属性值**只能**放 `--standard-template-reference` 的 `AttributeValueList`（元素 `{"AttributeId":<属性 Id>,"Value":"..."}`），往 `--standard-general-monitor-config` 里放任何形式都无效。**看到这个错不要在 monitor-config 里换字段名重试**，回到 §7 步骤 0 先取模板属性 Id 映射。`AttributeValueList` 传什么就是全量，改一个属性也要把其余属性值带上。
2. **不要手拼 `--update-command` 整个 body**：自拼顶层字段会报 `Error: unknown field: xxx`（实测连续 9 次换字段名全失败）；一律用 `--help` 列出的扁平参数，看到 `unknown field` 立即停下查 `--help`。
3. **更新前先 `get-standard` 拿全量 `StandardMonitorConfigList`**：在其基础上增删改，避免漏列已有 Id 触发误删
4. **`--standard-status` 必填且为合法枚举**：常见 `EFFECTIVE` / `DRAFT` / `OFFLINED`；不知道时先 `get-standard` 看现状回填
5. **切换监控类型** METADATA → QUALITY：必须同时补齐 `RuleSubType` 及对应必填项，否则服务端校验失败
6. **RuleValidateConfigList 的 Id 唯一 + ParentId 仅指向 RELATION**：不能两个 EXPRESSION 平铺
7. **EffectiveTimeConfig.Type=TIME_PERIOD 时**必须同时给 `StartTime` + `EndTime`，格式 `YYYY-MM-DD HH:mm:ss`
8. **`--standard-general-monitor-config` 传 JSON 字符串**：bash 用外单内双 `'{"...":"..."}'`；含中文描述时 LANG/LC_ALL 设为 UTF-8

## 10. Cleanup

update-standard **修改的是已有标准，不产生新资源**，因此没有「删除残留」意义上的清理。若测试阶段真实改动了标准，回滚方式为：

```bash
# 更新前先备份当前全量配置（改动前执行）
aliyun dataphin-public get-standard --tenant-id <tenant-id> \
  --standard-id <standard-id> \
  --user-agent AlibabaCloud-Agent-Skills/update-standard/{session-id} --format json > standard-backup.json

# 如需回滚，用备份中的原值再 update-standard 一次即可
```

> 验证建议全程用 `--cli-dry-run`，不产生真实改动即无需回滚。

## 11. Command Tables

详见 [`references/related-commands.md`](./references/related-commands.md)。

## 12. Best Practices + Reference Links

1. **改前必 `get-standard`**：先取全量再增删改，避免误删已有监控配置
2. **写操作先 dry-run 预检**：正式执行前加 `--cli-dry-run` 校验请求体结构
3. **写操作必须 HITL 确认**：更新标准前向用户确认 `--standard-id` / `--standard-status` 与监控配置
4. **大整数 ID 字符串传参**：owner / 属性 Id 等如为大整数，用引号包住避免精度丢失
5. **命令名以 `--help` 为准**：查询列表命令是 `list-standards`（复数），不是 `list-standard`

### Reference Links

- [`references/cli-installation-guide.md`](./references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](./references/acceptance-criteria.md)
- [`references/related-commands.md`](./references/related-commands.md)

## 13. 相关命令

- `aliyun dataphin-public create-standard` — 新建标准，结构同构，见 `create-standard`（经套件入口路由加载）
- `aliyun dataphin-public get-standard` — 拉取当前标准全量配置，作为 update 前的取数依据
- `aliyun dataphin-public offline-standard` — 下线标准
- `aliyun dataphin-public publish-standard` — 发布标准
- `aliyun dataphin-public list-standards` — 列表，用于定位 `--standard-id`
