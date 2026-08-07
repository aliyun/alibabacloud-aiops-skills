# standard-general-monitor-config 参数矩阵与类型分支

> 数据标准的监控配置 `--standard-general-monitor-config` 是一个 JSON 字符串，核心是 `StandardMonitorConfigList[]` 数组。
> 每个元素由 `Type` 字段决定字段组合（METADATA / QUALITY）。本文件抽取字段结构与枚举值，供填参参考。

## StandardMonitorConfigList 单元素结构

```jsonc
{
  "Id": 1,                       // 可选 | 已有配置 ID 表示更新；为空表示新增
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
    "Type": "FROM_SYSTEM|CUSTOMIZED",
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

## 分支 1：Type = METADATA（元数据监控）

只对元数据本身（是否有描述、命名是否合规、属性是否填齐）做检查，**不查询表数据**。无需 `RuleSubType / QualityRuleTemplate / RuleConfigList / RuleValidateConfigList`。

```bash
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
}'
```

## 分支 2：Type = QUALITY（数据质量监控）

对**实际表数据**做指标统计 + 阈值告警。RuleSubType 二级分支：

| RuleSubType | 含义 | 必填字段 |
|-------------|------|---------|
| `BY_ATTRIBUTE` | 沿用标准属性预置的质量规则 | AttributeId / AttributeMonitorConfig |
| `CUSTOMIZED` | 自由配置规则模板和阈值 | QualityRuleTemplate / RuleConfigList / RuleValidateConfigList |

CUSTOMIZED 最小骨架：

```bash
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
}'
```

## 分支判定速查

| 你想做的事 | Type | RuleSubType | 是否需要 QualityRuleTemplate / RuleConfigList / RuleValidateConfigList |
|------------|------|-------------|----------------------------------------------------------------------|
| 检查元数据合规 | `METADATA` | — | 否 |
| 用属性预置质量规则 | `QUALITY` | `BY_ATTRIBUTE` | 否（依赖 AttributeId） |
| 自定义质量规则 | `QUALITY` | `CUSTOMIZED` | 是（三项都要） |

## 填参坑点（源自 create-standard 沉淀）

1. **RuleValidateConfigList 的 Id 必须业务侧生成且唯一**：建议用 `v1/v2/v3` 或 UUID
2. **ParentId 仅指向 RELATION 节点**：表达式之间的"且/或"必须通过一个 RELATION 父节点串联，不能两个 EXPRESSION 平铺
3. **Operator 与 Type 严格对应**：`RELATION` 只能 `AND/OR`；`EXPRESSION` 只能比较运算符
4. **MonitorFrom**：纯手工添加用 `BY_USER`；走系统属性预置（绑定 AttributeId）用 `BY_SYSTEM_ATTRIBUTE`
5. **EffectiveTimeConfig.Type=TIME_PERIOD 时**必须同时给 `StartTime` + `EndTime`，格式 `YYYY-MM-DD HH:mm:ss`

> 单动作创建/更新的更详细分支说明见同模块子 skill `create-standard` 与 `update-standard`（通过套件入口 alibabacloud-dataphin-skills 的场景路由表加载）。
