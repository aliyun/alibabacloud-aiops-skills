# 校验模板选择与配置指南

## 模板体系概览

系统中的模板分为**内置模板**和**自定义模板**两类：

- **内置模板**（isBuiltin=1）：系统预置，规则硬编码在服务端，用户无法修改。创建任务时传 `check_template_id` 即可使用。
- **自定义模板**（isBuiltin=0）：用户在控制台创建，规则存储在数据库。支持自定义聚合方式、容差、列过滤等。

### 内置模板行为说明

| 模板 ID | 名称 | checkType | 适用字段类型 | 实际执行的校验 | 备注 |
|---------|------|-----------|-------------|---------------|------|
| 1001 | MIX | 1 (指标) | 数值 + 文本 + MAP + ARRAY | 数值: count(\*), avg, max, min; 文本: sum(length(ifnull())); MAP: map_size(); ARRAY: sum(array_size()) | **推荐**，覆盖面最广 |
| 1002 | NUM | 1 (指标) | 仅数值列 (INT/BIGINT/FLOAT/DOUBLE/DECIMAL) | count(\*), avg, max, min | 忽略字符串差异 |
| 1003 | LEN | 1 (指标) | 文本 + MAP + ARRAY | 文本: sum(length(ifnull())); MAP: map_size(); ARRAY: sum(array_size()) | 仅关注长度/大小 |
| ~~1004~~ | ~~STAT~~ | 1 (指标) | 所有列 | ~~quantiles_xxhash64~~ | **已废弃** |
| 1006 | 弱内容 | 2 (弱内容) | 可配置 | 内容哈希摘要比对 | 不暴露算法选择 |

> 内置模板的规则硬编码在服务端 MetricPlanner 中，通过模板详情接口 `GET /get` **无法**获取到具体规则内容。如需了解内置模板的行为，参考本表。

### 自定义模板支持范围

当前仅以下两种 checkType 支持创建自定义模板：

| checkType | 自定义模板类型 | 规则存储位置 | 说明 |
|-----------|-------------|-------------|------|
| 1 | 自定义指标模板 | `check_template_metric_rule` | 按数据类型分组指定校验方法和容差 |
| 2 | 自定义弱内容模板 | `check_template_weak_content_rule` | 指定参与校验的列类型和列名过滤 |

checkType 3（自定义 SQL）、4（全文比对）、5（空值率）的自定义模板后端尚未完整实现。

## 选型决策树

```
用户要做什么校验？
│
├── "快速验证数据是否一致"
│   └── 1001 (MIX) — 数值聚合 + 字符串长度，覆盖面最广
│
├── "只关心数值字段的精度"
│   └── 1002 (NUM) — avg/max/min，忽略字符串差异
│
├── "只关心字符串/大字段的内容变化"
│   └── 1003 (LEN) — sum(length())，适合 TEXT/BLOB 类字段
│
├── "需要内容级别的精确比对"
│   └── 1006 (弱内容) — 哈希摘要逐行比对
│
├── "需要自定义聚合方式和容差"
│   └── 创建自定义指标模板（checkType=1）
│       ├── 例：只对整数列做 SUM，浮点列容差 0.01
│       ├── 例：忽略数值 0 的差异
│       └── 例：指定某些列不参与校验
│
└── "需要自定义哪些列参与内容摘要比对"
    └── 创建自定义弱内容模板（checkType=2）
```

## 自定义指标模板规则配置

### 数据类型分组与可用校验方法

每条指标规则针对一个数据类型分组（DataTypeGroup），指定该组下使用哪些聚合函数。可用方法受 `check_template_base_rule` 约束，不可随意组合。

**基础类型 (data_type_classify=0):**

| 分组 (group) | 名称 | 包含类型 | 可用校验方法 |
|-------------|------|---------|-------------|
| 0 | INTEGER | TINYINT, SMALLINT, INT, BIGINT | SUM, AVG, MIN, MAX |
| 1 | FLOAT | FLOAT, DOUBLE, DECIMAL | SUM, AVG, MIN, MAX |
| 2 | BOOLEAN | BOOLEAN | SUM, AVG, MIN, MAX |
| 3 | STRING | STRING, VARCHAR, CHAR | SUM_CRC32, SUM_LENGTH, COUNT_DISTINCT |
| 4 | DATE | DATE, TIMESTAMP | MIN, MAX, SUM_CRC32, COUNT |

**复合类型 (data_type_classify=1):**

| 分组 (group) | 名称 | 包含类型 | 可用校验方法 |
|-------------|------|---------|-------------|
| 5 | ARRAY | ARRAY_NUMBER, ARRAY_STR, ARRAY_TIME, ARRAY_COMPLEX | SUM_CRC32, SUM_SIZE, MAX_SIZE, MIN_SIZE |
| 6 | MAP | MAP\<K,V\> | SUM_CRC32, SUM_SIZE, MAX_SIZE, MIN_SIZE |
| 7 | STRUCT | STRUCT | 拆分为基础类型后对比（特殊处理） |

> **注意**：不能对 STRING 类型传 SUM/AVG，也不能对 INTEGER 类型传 SUM_LENGTH。必须在上述范围内选择。

### 规则参数说明

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| dataTypeClassify | int | 是 | 0=基础类型, 1=复合类型 | `0` |
| dataTypeGroup | int | 是 | 数据类型分组 (0-7) | `0` (INTEGER) |
| dataTypeList | List\<String\> | 是 | 该组下参与校验的具体类型 | `["TINYINT","SMALLINT","INT","BIGINT"]` |
| checkMethods | str | 是 | 逗号分隔的校验方法字符串，须在上方映射表范围内 | `"SUM,AVG"` |
| diffTolerateType | int | 否 | 容差模式：0=统一阈值, 1=按方法自定义 | `0` |
| diffTolerateValues | dict | 否 | 统一: `{"SAME": 0}`; 自定义: `{"SUM": 0.01, "AVG": 0.001}` | `{"SAME": 0}` |
| isCountCheck | int | 否 | 是否同时做行数校验 (0/1)，默认 1 | `1` |
| filterColumnName | String | 否 | 不参与校验的列名（逗号分隔） | `"id,created_at"` |

**扩展选项**（存储在 extra JSON 字段中）：

| 参数 | 类型 | 说明 |
|------|------|------|
| ignoreNumericZero | bool | 忽略数值 0 的差异 |
| ignoreStringEmpty | bool | 忽略空字符串与 null 的差异 |
| enableDecimalScale | bool | 启用小数精度控制 |
| setDecimalScale | int | 小数精度位数 |
| ignoreDecimalScaleSuffixZero | bool | 忽略小数末尾零的差异 |

### 配置示例

**示例 1：只校验数值精度，浮点列允许容差**

```json
{
  "metricRules": [
    {
      "dataTypeClassify": 0,
      "dataTypeGroup": 0,
      "dataTypeList": ["TINYINT", "SMALLINT", "INT", "BIGINT"],
      "checkMethods": "SUM,AVG,MIN,MAX",
      "diffTolerateType": 0,
      "diffTolerateValues": {"SAME": 0},
      "isCountCheck": 1
    },
    {
      "dataTypeClassify": 0,
      "dataTypeGroup": 1,
      "dataTypeList": ["FLOAT", "DOUBLE", "DECIMAL"],
      "checkMethods": "SUM,AVG",
      "diffTolerateType": 1,
      "diffTolerateValues": {"SUM": 0.01, "AVG": 0.001},
      "isCountCheck": 1,
      "enableDecimalScale": true,
      "setDecimalScale": 4
    }
  ]
}
```

**示例 2：数值 + 字符串长度混合（类似内置 1001 但可自定义容差）**

```json
{
  "metricRules": [
    {
      "dataTypeClassify": 0,
      "dataTypeGroup": 0,
      "dataTypeList": ["TINYINT", "SMALLINT", "INT", "BIGINT"],
      "checkMethods": "SUM,AVG,MIN,MAX",
      "diffTolerateType": 0,
      "diffTolerateValues": {"SAME": 0},
      "isCountCheck": 1
    },
    {
      "dataTypeClassify": 0,
      "dataTypeGroup": 1,
      "dataTypeList": ["FLOAT", "DOUBLE", "DECIMAL"],
      "checkMethods": "SUM,AVG,MIN,MAX",
      "diffTolerateType": 0,
      "diffTolerateValues": {"SAME": 0.001},
      "isCountCheck": 1
    },
    {
      "dataTypeClassify": 0,
      "dataTypeGroup": 3,
      "dataTypeList": ["STRING", "VARCHAR", "CHAR"],
      "checkMethods": "SUM_LENGTH",
      "diffTolerateType": 0,
      "diffTolerateValues": {"SAME": 0},
      "isCountCheck": 0,
      "ignoreStringEmpty": true
    }
  ]
}
```

## 自定义弱内容模板规则配置

弱内容模板对参与校验的列做内容哈希摘要后逐行比对，适合需要内容级精确比对但不做全量逐行对比的场景。

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| filterColumnTypes | List\<String\> | 否 | 参与校验的列类型 | `["INT","VARCHAR","TEXT"]` |
| filterColumnExpression | String | 否 | 列名过滤表达式 | `"^col_.*"` |

> 弱内容模板当前不支持用户选择哈希算法，使用系统默认算法。

## 数据源-引擎映射

创建模板时必须指定 `dsEngineRels`（适用的数据源和引擎类型组合）。当前系统支持的映射：

| 数据源 (dsType) | 引擎 (engineType) |
|----------------|------------------|
| MaxCompute | MaxCompute |
| Hive | MapReduce, Tez, Impala, Presto, EmrServerlessSpark |
| MySQL | MySQL |
| StarRocks | StarRocks |
| Doris | Doris |
| PostgreSQL | PG |
| Hologres | Hologres |
| ClickHouse | ClickHouse |
| AzureSynapse | Synapse |
| Databricks | Databricks |
| BigQuery | BigQuery |
| ADBMySQL | ADBMySQL |
| GaussDB | GaussDB |
| Redshift | Redshift |
| AmazonAthena | AmazonAthena |
| Paimon | EmrServerlessSpark, StarRocks |

创建模板时的 `dsEngineRels` 格式示例：
```json
[
  {"dsType": "MaxCompute", "engineTypes": ["MaxCompute"]},
  {"dsType": "Hive", "engineTypes": ["MapReduce", "Tez"]}
]
```

## AI 对话中的使用方式

当用户提到模板或校验规则配置时：

1. 先判断用户是否真的需要自定义模板。大部分场景下内置模板 1001 (MIX) 已经够用。
2. 用 `list_templates(client)` 列出当前可用模板，帮助用户选择。
3. 如果需要自定义，可优先通过 `create_template()` 编程创建；用户也可在控制台手动创建后提供 UUID。
4. 用户提供模板 UUID 后，在 `run_metric_check()` 或 `run_batch_check()` 中传入 `--check-template-id <UUID>` 即可。
5. 管理已有模板（查看、更新规则、删除）直接使用 `common.py` 的模板封装函数或 `atomic-skills/lhm-template-manage/` 的 CLI。

详细的手动配置步骤见 `knowledge/patterns/template-manual-setup.md`。

## SDK 调用陷阱

- **update 接口不能用 `metricRules`**：后端 `UpdateCmd.getMetricRules()` 无条件清空 `metricRules`，只从 `basicMetricRules` + `complexMetricRules` 合并。创建模板可用 `metricRules`，但更新必须按 `dataTypeClassify` 拆分到 `basicMetricRules`（0=基础类型）和 `complexMetricRules`（1=复合类型）。
- **内置模板 detail 返回空规则**：1001/1002/1003 的 `metric_rules` 为空，因为规则硬编码在后端 `MetricPlanner` 中，不存储在数据库。
- **detail 接口 `checkTypeExport` 为 None**：只有 list 接口返回此字段，detail 不填充。需要中文名时自行映射：1→指标比对, 2→弱内容比对。
- **`weakContentAlgorithm` 自动设为 md5**：创建弱内容模板时无需指定算法，服务端自动填充。
