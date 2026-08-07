# 质量规则配置矩阵（界面 ↔ OpenAPI 对照 / 模板查询 / validateCondition / 模板级必填 / 调度 / 试跑坑）

> 本文件承载 `configure-quality-rule` 的详细参数矩阵与实测经验，供 Agent 在 §8 Core Workflow 各步展开时查阅。
> 31 个系统规则模板的机器可读配置目录见 [`template-config-catalog.json`](template-config-catalog.json)，其中包含每个模板支持的监控对象类型、规则配置项、必填性、可选项和校验指标。
> 命令均为公共云插件 `aliyun-cli-dataphin-public 0.5.4` 实际契约（`upsert-*` / `list-*` 命名 + **扁平参数**，复杂对象为内嵌 JSON string）；响应字段为 **PascalCase**。
> **双环境通道**：公共云（A）走 CLI；独立部署（B）因 CLI 有 `bad file descriptor` bug 改为 Python SDK 直调 OpenAPI（见 SKILL.md §3）。环境由父 SKILL.md §4.1 运行时自动判定，不询问类型。
> ⚠️ **本文中出现的 PascalCase OpenAPI Action 名（如 `SaveQualityWatch`/`PagedQueryQualityRules`/`PagedQueryQualityTemplates`/`RemoveQualityRules`/`RemoveQualityWatches` 等）部分为旧裸 OpenAPI 命名**，POC 独立部署直调可能报 `Unknown API`。**真实 Action 名 = 对应 CLI kebab 命令的 PascalCase**（如 `list-quality-rules`→`ListQualityRules`、`upsert-quality-watch`→`UpsertQualityWatch`）；拿不准统一用 `aliyun dataphin-public <command> --cli-dry-run` 导出真实 Action 名与参数再调。

## 1. 界面配置项 ↔ OpenAPI 参数对照（含必填与默认值）

| 界面分组 | 界面配置项 | 界面必填 | OpenAPI 参数 | API 是否可配 | 默认值/说明 |
|---|---|:--:|---|:--:|---|
| 基本信息 | 规则名称 | ★ | `ruleName` | ✅ 必传 | 无，须用户提供 |
| 基本信息 | 规则强度 | ★ | `ruleStrength` | ✅ 必传 | 建议 `STRONG`，须确认 |
| 基本信息 | 描述 | ○ | `ruleDescription` | ✅ 可选 | 空 |
| 基本信息 | 规则模板 | ★ | `templateId` | ✅ 必传 | 无，由维度推导 |
| 基本信息 | 规则类型 | ★ | `catalogs` | ✅ 必传 | 由模板决定 |
| 规则配置 | 校验字段 | ★ | `formProperties.validateField` | ✅ 必传 | 无，须指定真实字段 |
| 规则配置 | 数据过滤 | ○ | `formProperties.dataFilter` | ✅ 可选 | 关闭 |
| 校验配置 | **规则校验** | ★ | `validateCondition` | ✅ 可传但**无默认** | ❗最关键，不传则 `null`、界面显示「未配置」、试跑失败。空值校验推荐 `ERROR_NUMBER=0` |
| 归档配置 | 异常归档(开关) | ★ | `enableErrorArchive` | ✅ 可选 | 可设 `true`，须确认 |
| 归档配置 | 归档模式 | ★ | —（无参数） | ❌ 不可配 | **默认「仅归档异常字段」** |
| 归档配置 | 归档位置 | ★ | —（无参数） | ❌ 不可配 | **默认「默认文件服务器」** |
| 业务属性 | 开发人员/来源/负责人 | ○ | `attributeWithValueList` | ✅ 可选 | 空 |
| 调度属性 | 调度方式 | ○ | 独立命令 `assign-quality-rule-of-all-rule-scope-schedules` | ✅ 独立 | 需单独询问（见 §4） |
| 质量分配置 | 计分方式 | ★ | —（无参数） | ❌ 不可配 | **默认「质量校验状态」** |
| 质量分配置 | 质量分权重 | ○ | —（无参数） | ❌ 不可配 | **默认「1」** |

## 2. validateCondition 结构与推荐配置（★关键，无默认）

界面「规则校验」是红星必填；`validateCondition` API 标注非必填但**无任何后端默认**——不传则该字段 `null`、界面显示「未配置」、试跑失败。**任何模板都必须显式传**。

> ⚠️ **实测(env23 2023-06-30)：CLI `--validate-condition-list` 是扁平数组 + `id`/`parentId` 父子关联，不是嵌套 `subConditions`**。每个节点必须带 `id`（用 uuid），EXPRESSION 通过 `parentId` 挂到 RELATION 节点上；缺 `id` 报 `DPN.Commons.InvalidParam: Quality rule validate config miss param id`。
>
> ⚠️ **必须有 RELATION 根节点——单条件也不例外（POC 实测复现并纠正）**：条件列表里**第一个元素必须是 `type=RELATION` 的根节点**（`operator=OR/AND`、无 `parentId`），所有 `EXPRESSION` 通过 `parentId` 挂到它下面。**绝不能把单个 `EXPRESSION` 当根节点直接传**（哪怕只有一个条件）。否则即使数据写进去、`get-quality-rule` 能查到 `Metric`，**界面「校验配置→规则校验」按 RELATION 根解析，识别不了裸 EXPRESSION，导致「统计指标」显示为空/未配置**（INDEX 指标类规则尤为典型）。

CLI 正确写法（`--validate-condition-list` 是 list，两个元素分别传）：
```
--validate-condition-list '{"id":"<uuid-root>","type":"RELATION","operator":"OR"}' '{"id":"<uuid-expr>","parentId":"<uuid-root>","type":"EXPRESSION","operator":"EQUAL","metric":"ERROR_NUMBER","value":"0"}'
```
（等价的逻辑语义：外层 RELATION(OR) 下挂一个 EXPRESSION：ERROR_NUMBER EQUAL 0）

| 指标 metric | 含义 | 推荐配置 | 适用 |
|---|---|---|---|
| `ERROR_NUMBER` | 异常数据量 | `EQUAL` 0 | ⭐空值/唯一性——有 1 条异常即不通过（最严格） |
| `NORMAL_RATE` | 正常率(%) | `LARGE_OR_EQUAL` 95，`unit="%"` | 按比例容忍少量异常 |
| `ERROR_RATE` | 异常率(%) | `SMALLER_OR_EQUAL` 阈值 | 波动/值域类阈值判定 |
| `STATISTICAL_VALUE` | 统计值 | `LARGE_OR_EQUAL` 0 | INDEX/表 字段稳定性(T2100)、自定义统计(T2300) |
| `ONE_DAY_FLUCTUATE` 等 | 波动率(%) | `SMALLER_OR_EQUAL` 阈值，`unit="%"` | INDEX/表 字段波动性(T2200)：另有 `SEVEN_DAY_FLUCTUATE`/`THIRTY_DAY_FLUCTUATE`/`LAST_MONTH_FLUCTUATE`/`LAST_YEAR_FLUCTUATE` 等，取值见 catalog |

> 各模板的 `metric` 合法选项以 [`template-config-catalog.json`](template-config-catalog.json) 的 `validateConfigItems.metric.options` 为准（如 T2100 仅 `STATISTICAL_VALUE`，T2200 为多种波动率）。

操作符：`EQUAL`/`NOT_EQUAL`/`LARGER`/`SMALLER`/`LARGE_OR_EQUAL`/`SMALLER_OR_EQUAL`；多条件加多个 EXPRESSION 元素，均以同一 RELATION 节点为 `parentId`，RELATION 的 `operator` 取 `AND/OR`。

**复杂条件（多个统计指标之间 与/或，CLI 扁平数组写法）**：多个 `EXPRESSION` 挂同一 RELATION 根即为“同级 AND/OR”；需要“与中带或”时，再插入一个**内层 RELATION** 节点（自带 `id`、`parentId` 指向根），把要“或”的 EXPRESSION 的 `parentId` 指向该内层 RELATION。示例 `STATISTICAL_VALUE≥0 AND ( STATISTICAL_VALUE<10 OR STATISTICAL_VALUE>1000 )`：
```
--validate-condition-list \
  '{"id":"r","type":"RELATION","operator":"AND"}' \
  '{"id":"e1","parentId":"r","type":"EXPRESSION","metric":"STATISTICAL_VALUE","operator":"LARGE_OR_EQUAL","value":"0"}' \
  '{"id":"r2","parentId":"r","type":"RELATION","operator":"OR"}' \
  '{"id":"e2","parentId":"r2","type":"EXPRESSION","metric":"STATISTICAL_VALUE","operator":"SMALLER","value":"10"}' \
  '{"id":"e3","parentId":"r2","type":"EXPRESSION","metric":"STATISTICAL_VALUE","operator":"LARGER","value":"1000"}'
```
> 多指标只需把各 EXPRESSION 的 `metric` 换成不同统计指标；每个节点的 `id` 用唯一值（示例用 r/e1/… 便于阅读，实战建议 uuid）。

> 若用户选「不配置」，必须明确告知后果（规则不完整、试跑失败、需到界面补配），确认后才继续。

## 3. templateId 查询与速查表

### 3.1 标准查询命令

`templateId` 必须从目标租户实测获取，不要照搬文档示例。CLI 对应 OpenAPI `ListQualityTemplates`，命令为 `list-quality-templates`；单模板详情为 `get-quality-template`。

```bash
# 通用格式：按监控对象类型查系统模板
aliyun dataphin-public list-quality-templates --tenant-id "$TENANT_ID" \
  --watch-type-list TABLE DATASOURCE_TABLE \
  --template-source-list SYSTEM \
  --page-no 1 --page-size 100 \
  --user-agent "$UA"

# env23 独立部署标准格式：--endpoint 不带 https://
aliyun --profile env23 dataphin-public list-quality-templates \
  --endpoint dataphin-openapi.env23.aliyun.com \
  --op-tenant-id 300001414 \
  --watch-type-list TABLE DATASOURCE_TABLE \
  --template-source-list SYSTEM \
  --page-no 1 --page-size 100 \
  --format json \
  --user-agent "$UA"

# 单模板详情
aliyun dataphin-public get-quality-template --tenant-id "$TENANT_ID" \
  --quality-template-id "<templateId>" --user-agent "$UA"
```

> env23 实测返回结构为 `PageResult.QualityTemplateList[]`，字段为 `Id`/`Name`/`Type`/`Catalog`；不要按旧 SDK 的 `Data.data.TemplateId` 写解析逻辑。
> `FormPropertyList=null` 不代表模板无必填项，只代表这个列表接口/环境未返回表单定义；仍必须结合模板类型、界面红星项和本矩阵的模板级必填项补齐。

### 3.2 templateId 速查表（env23 系统模板实测）

| templateId | 校验类型 | catalogs 维度 | templateType | 关键 formProperties |
|---|---|---|---|---|
| 100 | 字段空值 | COMPLETENESS | FIELD_NULL_VALUE_VALIDATE | validateField |
| 200 | 字段空字符串 | COMPLETENESS | FIELD_EMPTY_STRING_VALIDATE | validateField |
| 300 | 字段唯一性 | UNIQUENESS | FIELD_UNIQUE_VALIDATE | validateField |
| 400 | 字段唯一值个数 | UNIQUENESS | FIELD_GROUP_COUNT_VALIDATE | validateField |
| 500 | 字段重复值个数 | UNIQUENESS | FIELD_DUPLICATE_VALUE_COUNT_VALIDATE | validateField |
| 600 | 时间函数比较 | TIMELINESS | FUNCTION_TIME_COMPARE | validateField + 时间函数/阈值配置 + timeTolerance；字段/表达式必须是日期时间类型 |
| 700 | 单表时间字段比较 | TIMELINESS | SINGLE_TABLE_TIME_COMPARE | validateField + compareField/时间差配置 + timeTolerance；两侧字段必须是日期时间类型 |
| 800 | 两表时间字段比较 | TIMELINESS | DOUBLE_TABLE_TIME_COMPARE | validateField + doubleTableCompareTable + doubleTableJoinCondition + timeTolerance；两侧字段必须是日期时间类型 |
| 900 | 字段格式校验 | EFFECTIVE | FIELD_FORMAT_VALIDATE | validateField + contentIdentifyMethod/Expression/Regex/Like |
| 1000 | 字段长度校验 | EFFECTIVE | FIELD_LENGTH_VALIDATE | validateField + valueRange |
| 1100 | 字段值域校验 | EFFECTIVE | FIELD_VALUE_RANGE_VALIDATE | validateField + valueRangeType + valueRange |
| 1200 | 码表参照对比 | EFFECTIVE | CODE_TABLE_COMPARE | validateField + code table/compare config |
| 1250 | 数据标准码表参照对比 | EFFECTIVE | STANDARD_CODE_TABLE_COMPARE | validateField + standard code table config |
| 1300 | 单表字段值一致性比较 | CONSISTENT | SINGLE_TABLE_FIELD_VALUE_COMPARE | validateField + compareField（不是值域校验） |
| 1400 | 单表字段统计值一致性比较 | CONSISTENT | SINGLE_TABLE_FIELD_STATISTICAL_COMPARE | validateField + compareField/statisticalMethod |
| 1500 | 单表字段业务逻辑一致性比较 | CONSISTENT | SINGLE_TABLE_FIELD_EXP_COMPARE | validateField + expression/business logic config |
| 1600 | 两表字段值一致性比较 | CONSISTENT | DOUBLE_TABLE_FIELD_VALUE_COMPARE | validateField + validateItem + compareItem + doubleTableCompareTable + doubleTableJoinCondition |
| 1700 | 两表字段统计值一致性比较 | CONSISTENT | DOUBLE_TABLE_FIELD_STATISTICAL_COMPARE | validateField + statisticalMethod + doubleTableCompareTable + doubleTableJoinCondition |
| 1750 | 跨源两表字段统计值一致性比较 | CONSISTENT | CROSS_DOUBLE_TABLE_FIELD_STATISTICAL_COMPARE | validateField + cross-source compare table + join/statistical config |
| 1800 | 两表字段业务逻辑一致性比较 | CONSISTENT | DOUBLE_TABLE_FIELD_EXP_COMPARE | validateField + contentIdentifyExpression + 变量实例化项（如 T1.total_sales/T2.unit_price） + doubleTableCompareTable + joinMethod + doubleTableJoinCondition；业务逻辑必须用 `${T1.字段}`/`${T2.字段}` 变量表达式 |
| 1900 | 表稳定性校验 | STABILITY | TABLE_STABILITY_VALIDATE | 表级监控粒度；无校验字段；无额外 dynamicForm 配置 |
| 2000 | 表波动性校验 | STABILITY | TABLE_FLUCTUATION_VALIDATE | 表级监控粒度；`sqlPreSet` 可选；校验指标为各类波动率 |
| 2100 | 字段稳定性校验 | STABILITY | FIELD_STABILITY_VALIDATE | `validateField` 必填；INDEX 场景含 `statisticalMethod`（统计方式，11 枚举）+ `dataFilter`（数据过滤，可选）；`sqlPreSet` 可选；校验指标为统计值 |
| 2200 | 字段波动性校验 | STABILITY | FIELD_FLUCTUATION_VALIDATE | `validateField` 必填；INDEX 场景含 `statisticalMethod` + `dataFilter`（可选）；`sqlPreSet` 可选；校验指标为各类波动率 |
| 2300 | 自定义统计指标校验 | CUSTOM | CUSTOM_STATISTICAL_VALIDATE | `customSql` 必填；`sqlPreSet` 可选 |
| 2400 | 自定义数据详情校验 | CUSTOM | CUSTOM_DATA_DETAILS_VALIDATE | custom SQL/detail config |
| 2500 | 数据源连通性监测 | STABILITY | DATASOURCE_AVAILABLE_CHECK | 空配置可用 |
| 2600 | 表结构异动监测 | STABILITY | TABLE_SCHEMA_CHECK | **dataSourceTable 必填**，dataSourceTableCatalog 可选 |
| 2700 | 实时离线对比 | CONSISTENT | REAL_TIME_OFFLINE_COMPARE | 仅实时元表；validateObjectType=CHAIN；公共 validateField/calculateMethod/valueType/timeCondition/timeZone/enableCondition + `offlineCompareChain`（先选离线表再写 offlineSql，参考规则实例 7394638）；校验指标 REALTIME_OFFLINE_CHAIN_DIFF(%) |
| 2800 | 实时统计值监测 | STABILITY | REAL_TIME_STATISTICAL_VALIDATE | 仅实时元表；validateObjectType=REALTIME；无特有 formProperty；校验指标 4 选：REALTIME_STATISTICAL_VALUE / 一天·七天·三十天波动值(%) |
| 2900 | 实时多链路对比 | CONSISTENT | REAL_TIME_MULTI_CHAIN_COMPARE | 仅实时元表；validateObjectType=REALTIME；`realTimeCompareChainsCount`(DOUBLE_CHAIN/TRIPLE_CHAIN) + `realTimeCompareChains`(实时表数组)；双链路仅 REALTIME_COMPARE_CHAIN_1_DIFF，三链路加 REALTIME_COMPARE_CHAIN_2_DIFF |

> catalog 枚举正确值：`CONSISTENT`/`EFFECTIVE`/`TIMELINESS`/`ACCURATE`/`UNIQUENESS`/`COMPLETENESS`/`STABILITY`/`CUSTOM`。部分旧文档可能写 `TIMELINESE`，以 `list-quality-templates` 实测返回为准；是 `EFFECTIVE` 不是 `EFFECTIVENESS`。
> 响应字段 PascalCase/当前 CLI 字段并存：列表可能返回 `Id`/`Name`/`Type`/`Catalog`，旧 SDK/文档可能称 `TemplateId`/`TemplateName`/`TemplateType`。实现时先兼容实测返回。
> 模板配置 JSON 来源：POC 页面接口 `/api/quality/rule/querySupportTemplatesOfWatch`、`/api/quality/template/queryTemplateDynamicForm`、`/api/quality/rule/listValidateConditionMetrics`；用于补足 CLI 模板列表可能缺失的 `FormPropertyList`。

### 模板级 formProperties 必填项门控

创建规则前必须按模板级必填项组装 `--form-property-list`。不要只看 `upsert-quality-rule` 顶层是否要求 `--form-property-list`；接口允许省略不代表界面配置完整。**31 个系统模板的精确规则配置项以 [`template-config-catalog.json`](template-config-catalog.json) 的 `ruleConfigItems` 为准**：字段级模板看 `validateObjectType=COLUMN` 并补 `validateField`，表级模板不传校验字段；动态项按 `required/options` 补齐。

| 模板类型 | 典型 templateId | 必填/关键配置 | 注意 |
|---|---:|---|---|
| 字段空值/空字符串/唯一性/重复值 | 100/200/300/400/500 | `validateField` | 字段必须来自元数据，不猜字段 |
| 字段格式 | 900 | `validateField` + `contentIdentifyMethod` + 对应表达式/正则/like | 按界面选择识别方式补齐 |
| 时间类（时间函数/单表时间/两表时间） | 600/700/800 | `validateField` + `validateItem` + `compareItem` + `timeTolerance` | `timeTolerance` 必须传 3 元素 JSON 数组：`[{"checked":true,"operate":">","time":0,"type":"DAY"},{"checked":true,"operate":"<","time":1,"type":"DAY"},{"timeCompareMethod":"VALIDATE_SUB_COMPARE"}]`。默认建议：`>0天 且 <1天`。**字段/表达式必须是 DATE/DATETIME/TIMESTAMP/TIMESTAMP_NTZ 等时间类型**；禁止用 `id`、BIGINT 时间戳、yyyymmdd 数字等非时间类型，否则试跑会报 `datediff(BIGINT, BIGINT, STRING)` 无匹配重载。传单对象 JSON 或简单字符串会导致数据损坏 |
| 字段长度 | 1000 | `validateField` + `valueRange` | `valueRange` 为 JSON 字符串 |
| 字段值域 | 1100 | `validateField` + `valueRangeType` + `valueRange` | 枚举/区间结构见下方 |
| 单表字段值一致性 | 1300 | `validateField` + `compareField` | 不是值域校验，别混用 |
| 两表/跨源比较 | 1600/1700/1750/1800 | `validateField` + `doubleTableCompareTable` + `joinMethod` + `doubleTableJoinCondition` + 比较字段/统计方法/业务逻辑 | 必须先定位比较表和字段；界面“选择比较表”字段名是 `doubleTableCompareTable`，值为 JSON 字符串：`{"doubleTableCompareTable":"项目或数据源目录.表名","doubleTableCompareField":"比较字段"}`。关联方式字段名是 `joinMethod`，值如 `left join`；关联表达式 `doubleTableJoinCondition` 必须是字符串表达式，内置数据表参数 `T1` 为检测表、`T2` 为比较表，示例：`T1.id = T2.id`。T1800 的业务逻辑 `contentIdentifyExpression` 必须用 `${T1.字段}`/`${T2.字段}` 变量引用实际字段，且每个变量必须实例化为独立 formProperty，例如 `{"Name":"T1.total_sales","Value":"total_sales"}`、`{"Name":"T2.unit_price","Value":"unit_price"}`。旧字段 `doubleCompareTable` 不会让界面回显选择比较表，旧 JSON 关联结构 `{leftField/rightField/operator}` 也不符合界面表达式写法 |
| 表/字段稳定性与波动性 | 1900/2000/2100/2200 | T1900 仅表级监控粒度；T2000 仅 `sqlPreSet` 可选；T2100/T2200 字段级必须 `validateField`，`sqlPreSet` 可选；**INDEX 指标场景 T2100/T2200 还需 `statisticalMethod`（统计方式，11 枚举：FIELD_COUNT/FIELD_DISTINCT_COUNT/FIELD_SUM/FIELD_AVG/FIELD_MAX/FIELD_MIN/FIELD_DUPLICATE_COUNT/FIELD_DUPLICATE_RATE/FIELD_GROUP_COUNT/FIELD_NULL_COUNT/FIELD_NULL_RATE），可选 `dataFilter`** | 稳定性/波动性的阈值主要在 `validateCondition.metric/operator/value` 中配置，支持指标见 `template-config-catalog.json` |
| 实时元表（实时离线/统计值/多链路） | 2700/2800/2900 | 公共 `validateField`+`calculateMethod`(VALUE/COUNT/DISTINCT/SUM/MAX/MIN/AVG)+`valueType`(SINGLE_VALUE/MULTI_VALUE)+`timeCondition`+`timeZone`+`enableCondition`；T2700 加 `offlineCompareChain`（离线表元数据+offlineSql），T2900 加 `realTimeCompareChainsCount`+`realTimeCompareChains` | **仅 REALTIME_LOGICAL_TABLE 监控对象可用**；`validateCondition` 为嵌套 RELATION>EXPRESSION 结构（非扁平 id/parentId）；T2700 offlineSql 必须针对所选离线表编写（参考规则实例 7394638）；T2900 双链路 1 个校验指标、三链路 2 个 |
| 数据源连通性 | 2500 | 空 formProperties + `validateCondition` | 校验指标固定 **`DATASOURCE_CONNECTIVE`**（数据源连通性），推荐 `EQUAL "true"`；即使传其它指标名后端也会归一化为该值 |
| 表结构异动监测 | 2600 | **`dataSourceTable`**，可选 `dataSourceTableCatalog` | 界面“选择校验表”为必填；必须先定位具体数据源表，不能传空配置；校验指标固定 **`TABLE_SCHEMA_CHANGED`**，推荐 `EQUAL "false"` |

> ⚠️ **DATASOURCE 监控对象（2500/2600）必须建在 PROD 数据源 ID 上**。POC 实测用 DEV 数据源 ID 建 watch（`SaveQualityWatch`）时，后端会忽略传入的 `dataSourceEnv=DEV`/`dataSourceCatalog`，强制存成 `env=PROD` 且 catalog 为空，产生脏 watch，后续 `PagedQueryQualityRules`（界面打开规则列表）会报 `DPN.Commons.InternalError：系统内部错误`。定位监控对象用 `GetQualityWatchByObjectId watchType=DATASOURCE watchObjectId=<PROD 数字 DataSourceId>`（传 catalog 编码如 `ds_oracle` 会报内部错误）。清理脏数据：`RemoveQualityRules {ruleIds:[...]}` + `RemoveQualityWatches {watchIds:[...]}`（v1.0 无 DeleteQualityRules）。

### INDEX（指标）监控对象特殊点（POC 实测）

- **模板范围**：INDEX 类型可用模板 = 5 个系统模板（T400 字段唯一值个数、T500 字段重复值个数、T2100 字段稳定性、T2200 字段波动性、T2300 自定义统计指标）+ 若干租户自建的 `CUSTOM_STATISTICAL_VALIDATE` 自定义模板。用 `PagedQueryQualityTemplates watchTypes=['INDEX']` 查，`SystemTemplate=true` 区分系统/自定义。
- **字段级模板无需 validateField**：T400/T500/T2100/T2200 在 TABLE/DATASOURCE_TABLE 上需 `validateField`，但在 **INDEX 上无需**（指标自身即校验列）；ValidateObject.Field=null。各模板校验指标：T400=`FIELD_GROUP_COUNT`、T500=`FIELD_DUPLICATE_COUNT`、T2100 需 formProperty `statisticalMethod`（如 `FIELD_AVG`）+指标 `STATISTICAL_VALUE`、T2200 需 `statisticalMethod`+指标 `ONE_DAY_FLUCTUATE`(unit `%`)。
- **自定义模板内嵌 SQL**：`CUSTOM_STATISTICAL_VALIDATE` 自定义模板的 `customSql` 已内置在模板定义里（用 `${t1}`=指标底表、`${bizdate}`=分区占位），建规则时传 `monitoringIntensity=TABLE` 即可沿用，无需重传；只有基础模板 T2300 需自行传 `customSql`。
- **定位指标对象**：`GetQualityWatchByObjectId watchType=INDEX`；已有 watch 的 `Index.IndexGuid` 格式=`dp_index.{tenant}.prod.{indexId}`，底表在 `Index.CellSumLogicTableName`（逻辑汇总表）。
- **建规则避重名**：`SaveQualityRule` 同一 watch 内规则名唯一，否则报 `DPN.UniversalQuality.RuleDuplicateName`（系统 T2300 名“自定义统计指标校验”易与同名自定义模板冲突，需手动加后缀）。

**2600 表结构异动监测 formProperty 示例**：
```bash
--form-property-list \
  '{"Name":"dataSourceTableCatalog","Value":"<库/schema/catalog>"}' \
  '{"Name":"dataSourceTable","Value":"<目标表完整元数据JSON字符串>"}'
```
`dataSourceTable` 的值应是目标数据源表完整元数据 JSON 字符串，至少包含租户、数据源 ID、数据源类型、库/schema、表名等足以让界面回显“选择校验表”的字段；实际字段以当前环境从数据源表查询/已有规则反查得到的结构为准。

> **外部数据源表（Oracle/PG 等）元数据获取路径**（`SearchCatalogTable` 对未采集进 catalog 的外部数据源返空时使用）：
> 1. **即席查询任务**（推荐）：对目标数据源发起即席查询（如 Oracle `SELECT owner, table_name FROM all_tables`、`SELECT column_name, data_type FROM all_tab_columns WHERE table_name='...'`），拿到真实的 schema/表名/字段，再手工拼 `dataSourceTable` 元数据（guid 格式 `dp_ds_table.{tenant}.{dataSourceId}.{schema小写}.{table小写}`）。
> 2. **反查已有规则**：若该数据源已有 2600 规则，用 `PagedQueryQualityRules {watchId}` + `GetQualityRule {ruleId}` 读 `ValidateObject.Name` / formProperties 里的 `dataSourceTable`，直接复用其表元数据结构。

### 值域校验（templateId=1100）配置法（严禁写死字段）

1. 拿全字段（Step 2）→ 得字段名 + dataType + 是否分区键。
2. 筛候选：数值型→区间校验；低基数编码/标志位→枚举校验；分区键通常不作值域字段。
3. 即席 SQL 探分布（数值型查 min/max，低基数查 group by）定合理值域。
4. 逐字段建 1100 规则，字段名/值域全部来自探测结果，不硬编码。

`valueRange`（传给 formProperties 的 JSON 字符串）两种形态：
```
枚举: 外层 {"Name":"valueRangeType","Value":"number"}  # 或 text/date/time/custom
      内层 {"Name":"valueRange","Value":"{\"enumType\":\"in\",\"enumValue\":\"1,2,3,4,5\",\"intervalLeftType\":\">=\",\"intervalLeftValue\":null,\"intervalRightType\":\"<=\",\"intervalRightValue\":null,\"valueRangeType\":\"enum\"}"}
区间: 外层 {"Name":"valueRangeType","Value":"number"}
      内层 {"Name":"valueRange","Value":"{\"valueRangeType\":\"interval\",\"intervalLeftType\":\">=\",\"intervalLeftValue\":0,\"intervalRightType\":\"<=\",\"intervalRightValue\":100}"}
```
> 枚举写法以 env23 `T1100_字段值域校验_col1` 回查为准：外层 `valueRangeType` 表示字段值类型，内层 `valueRange.valueRangeType=enum` 表示范围类型为枚举，`enumValue` 用英文逗号拼接。
> ⚠️ **实测(env23 2023-06-30)：CLI `--form-property-list` 每个元素键名必须是 `Name`/`Value`（PascalCase），不是 `propertyName`/`propertyValue`**。误用后者不报错但 `validateField` 不被赋值（存成 `Name:null/Value:null`），导致模板变量 `${validateField}` 不被替换、试跑 FAILED（任务 `ValidateObjectName` 残留 `${validateField}`）。正确：`--form-property-list '{"Name":"validateField","Value":"<字段>"}'`；值域类再追加 `{"Name":"valueRange","Value":"<上面的JSON字符串>"}`。
> `upsert-quality-rule` 修改规则时 `--upsert-quality-rule-id` 传**单个数字**（传数组报 `Expected NUMBER but was BEGIN_ARRAY`）。
> 扁平参数对应：`--quality-rule-name` / `--strength` / `--template-id` / `--template-type`（如 `FIELD_NULL_VALUE_VALIDATE`）/ `--watch-id` / `--catalog-list` / `--form-property-list`（JSON，用 `Name`/`Value`）/ `--validate-condition-list`（JSON 扁平数组 + `id`/`parentId`）/ `--enable-error-archive`。

## 4. 调度（upsert-quality-schedule）

> **★`--type`（调度类型）必填，不得为空，也不得默认**：创建调度前必须让用户从以下 5 个枚举值中**显式指定**，禁止 Agent 擅自选择、默认或留空。
>
> | 枚举值 | 中文名 | 说明 |
> |---|---|---|
> | `PERIOD_SCHEDULE` | 定时调度 | cron 周期触发，如 `--cron-expression "0 0 2 * * ?"`（每天凌晨2点） |
> | `MANUAL_SCHEDULE` | 手动触发 | 不设周期，仅手动/试跑触发 |
> | `CODE_CHECK_TRIGGER` | 代码检查触发 / 数据更新触发 | 产出该对象的加工任务运行时触发，无需节点ID |
> | `STATIC_TASK_TRIGGER` | 固定任务触发 | `--trigger-type <触发时机>` + `--trigger-node-list`（真实节点ID，否则报 `NodeNotFoundByIdAndTenantId`）；触发时机 3 选 1（见下表） |
> | `DEPENDENCY_SCHEDULE` | 依赖调度 | 依赖上游调度 |

扁平参数：`--type` / `--watch-id` / `--cron-expression` / `--trigger-type` / `--trigger-node-list` / `--partition-type` / `--partition-expression` / `--validate-partition-type`。

**★调度类型 × 监控对象类型支持矩阵**（仅列 3 种核心触发式调度）：

| 监控对象类型 | 定时 `PERIOD_SCHEDULE` | 数据更新触发 `CODE_CHECK_TRIGGER` | 固定任务触发 `STATIC_TASK_TRIGGER` |
|---|:--:|:--:|:--:|
| `TABLE` Dataphin 表 | ✅ | ✅ | ✅ |
| `DATASOURCE_TABLE` 全域表 | ✅ | ❌ | ✅ |
| `DATASOURCE` 数据源 | ✅ | ❌ | ✅ |
| `INDEX` 指标 | ✅ | ✅ | ✅ |
| `REALTIME_LOGICAL_TABLE` 实时元表 | ✅ | ✅ | ✅ |

> - `TABLE`/`INDEX`/`REALTIME_LOGICAL_TABLE` 支持全部 3 种。
> - `DATASOURCE_TABLE`/`DATASOURCE` **只支持定时 + 固定任务触发，不支持数据更新触发**（OpenAPI 对其配 `CODE_CHECK_TRIGGER` 不报错，但语义不该配，需自行规避）。
> - `MANUAL_SCHEDULE`/`DEPENDENCY_SCHEDULE` 为合法枚举值，与对象类型的支持关系以界面为准（未在本矩阵逐一约束）。

**★固定任务触发（`STATIC_TASK_TRIGGER`）的 3 种触发时机（`--trigger-type`，必填，需给用户推荐）**：

| 触发时机枚举 | 界面含义 | 语义 | 推荐场景 |
|---|---|---|---|
| `ALL_TASKS_FINISHED` | 所有任务都运行成功后触发 | 监听的多个节点**全部**成功跑完才校验一次 | 目标表由**多个上游合并产出**，要数据齐全后再校验（避免校验到半成品） |
| `ONE_TASKS_FINISHED` | 每个任务每次运行成功后均触发 | **任一**节点每成功跑完一次就校验一次 | 表被**多来源/多分区分别增量更新**，每批新数据落地就即时校验 |
| `PRE_ONE_TASKS_START` | 每个任务每次运行前均触发 | 在节点**开始运行之前**先校验一次 | 对上游**源/输入表做前置质量卡口**，加工前先验证源数据（配强规则可阻断） |

> 推荐逻辑：多上游合并产出→`ALL_TASKS_FINISHED`；多来源/分区增量、要每批即时校验→`ONE_TASKS_FINISHED`；想在加工前做源表前置卡口→`PRE_ONE_TASKS_START`。创建固定任务触发时必须让用户显式选定触发时机，不得默认。

**★监听节点（`--trigger-node-list`）的获取方法（不直接向用户要节点ID）**：

1. **先主动查产出节点**：调 `list-tables`（OpenAPI `ListTables`，参数名 `TableQuery`，按 `keyword`+`projectId`+`env` 定位），读返回的 **`nodeIds`（List<String>，即产出任务节点）** ——就是 `--trigger-node-list` 要的值。
   > ⚠ `SearchCatalogTable` 的 `NodeIds` 恒为 null、不可用；取产出节点必须用 `ListTables.nodeIds`。
2. **`nodeIds` 非空** → 列成候选清单给用户选（“该表产出任务节点有 ①…②…，监听哪个（可多选）？”）。
3. **`nodeIds` 为空 / 查不到**（如未绑定产出任务的逻辑表）→ 向用户要一个真实调度节点（“未查到产出加工任务，请给出要监听的任务名或节点ID”）。
4. 节点必须是本租户真实存在的，否则 `assign`/创建报 `NodeNotFoundByIdAndTenantId`。

**校验范围表达式（分区表必填！）**：
```
--validate-partition-type "USER_DEFINED_PARTITION"
--partition-type "CUSTOM"
--partition-expression "ds='${yyyyMMdd}'"
```
常用 partitionType：`EVERY_DAY`/`PRE_DAY`/`TODAY`/`CUSTOM`/`NONE_PARTITIONS`。

> 仅创建调度不会自动绑定，必须 `assign-quality-rule-of-all-rule-scope-schedules` 显式绑定（`--watch-id` / `--rule-id-list` / `--schedule-id-list`，多值空格分隔）；解绑用 `remove-quality-rule-schedules`。
>
> ⚠实测：assign 命令即使入参无效也会静默返回 `{"Success":true}`，绑定不一定生效。**绑定后必须回查** `get-quality-rule` 的 `QualityRuleInfo.ScheduleBindList`（成功为 `[{"ScheduleId":...}]`，`null` 表示未绑定）。调度侧 `IsRefByRule` 恒为 `null`，不可用于判断。

## 5. 告警（upsert-quality-watch-alert，watch 级别）

```
--watch-id <wid> --quality-alert-info '{"alertQualityOwner":true,"alertQualityOwnerChannels":["MAIL","DINGTALK_ROBOT"]}'
```
查询已有告警：`get-quality-alert-of-all-rule-scope-by-watch-id`（`--watch-id`）。
> **限制**：告警是 watch 级别，对该监控对象下所有规则生效，不支持单规则级告警。

## 6. 试跑（submit-quality-rule-tasks）与结果判定

```
--is-test-run true --watch-rule-id-list '{"watchId":"<wid>","ruleId":"<rid>"}' \
--partition-expression-from "CUSTOM" --partition-expression "ds=20160710"
```
> **★分区表必须用 `--partition-expression` 钉单分区**（真实 API 无 `partitionFilter`）。只传 `--biz-date` / 用 `ALL_PARTITIONS` / `PRE_DAY` 都可能仍触发全表扫描被拒——务必 `--partition-expression-from CUSTOM` + 具体分区值。
> 找真实分区：公共云插件无 `list-table-partitions`，统一用【数据库SQL任务】`execute-ad-hoc-task`（`--code "SHOW PARTITIONS <表>"`）→ `get-ad-hoc-task-result` 读分区值；若返回 0 分区则从试跑日志成功 SQL 的 `DS >= 'xxx'` 区间下界取一个确定存在的分区值。

**判定三态（试跑失败 ≠ 校验不通过）**：
- `status=SUCCESS` + `validateResult=true` → ✅ 通过
- `status=SUCCESS` + `validateResult=false` → ⚠️ 校验不通过（真实检出异常，规则有效）
- `status=FAILED` → ❌ 执行报错（全表扫描/SQL 翻译失败等，**不是**校验不通过）

> `get-quality-rule-task` 不返回错误字段（`ErrorMessage` 恒 None）；FAILED 真因必须调 `get-quality-rule-task-log` 看日志（含 `Physical Sql`/`Error Message`/`full scan`）。
> 无论结果如何，只要用户已确认创建，都不删除规则。

## 7. 数据源表取字段（未采集外部数据源）

未采集的外部数据源表 `list-tables` / `get-table-columns` 查不到字段，**统一走【计算任务-数据库SQL任务】`execute-ad-hoc-task`**（A公共云 / B独立部署同一套方式）：

1. `list-data-source-with-config`（`--page` / `--page-size` / `--data-source-name`）→ 拿 `DataSourceId` + `DataSourceCatalog`（PROD 形如 `ds_demo_mysql`、DEV 形如 `ds_demo_mysql_dev`）。⚠️直接传显示名报 `ProjectAndDataSourceNotFound`，数据源编码须用 `ds_` 前缀。
2. `execute-ad-hoc-task`（`--operator-type` 数据库SQL任务 + `--data-source-id <上一步 DataSourceId>` + `--code "SELECT * FROM 库.表 LIMIT 1"` + `--project-id`）→ 拿 `TaskId`。拿字段最稳用 `SELECT * ... LIMIT 1`。
3. `get-ad-hoc-task-result`（`--task-id` + `--sub-task-id` + `--project-id`）→ `Data.MetaData` 是列元信息（columnName/columnTypeName），`Data.Result` 是数据行。必要时 `get-ad-hoc-task-log` 看执行日志、`stop-ad-hoc-task` 兜底。

未采集数据源表 guid 拼接规则：`dp_ds_table.{租户id}.{数据源id}.{库名}.{表名}`，可直接用于 `get-quality-watch-by-object-id` / `upsert-quality-watch`。

> ⚠️ 分区表即席查询禁止全表扫描：扫描 SQL 必须带分区谓词（如 `WHERE ds=20160805`）。
> ⚠️ 公共云插件无 JDBC 直连系列命令（`create-jdbc-connection` 等均不存在），即席查询统一走上述【数据库SQL任务】`execute-ad-hoc-task` → `get-ad-hoc-task-result` 两步链路。

## 8. API 能力缺口速查（用户追问时用此解释）

| 界面配置项 | OpenAPI 能力 | 不可配默认值 | 如需自定义 |
|---|---|---|---|
| 归档模式 | ❌ 无参数 | 仅归档异常字段 | 到界面手工改 |
| 归档位置 / 异常归档表 | ❌ 无参数 | 默认文件服务器 | 到界面手工指定 |
| 计分方式 | ❌ 无参数 | 质量校验状态 | 到界面手工改 |
| 质量分权重 | ❌ 无参数 | 1 | 到界面手工改 |
| 规则校验(validateCondition) | ✅ 可传，**无默认** | 无（不传则 null） | **必须显式传**，空值校验推荐 `ERROR_NUMBER=0` |
| 单规则级告警 |  不支持 | 告警为 watch 级别 | 无法按单规则配 |
| 时间差(timeTolerance) | ✅ 支持 | 3 元素 JSON 数组（条件1+条件2+比较类型） | 必须用数组格式，传单对象 JSON 或简单字符串会导致数据损坏 |

> 这些缺口是产品/接口现状，不是 skill 的 bug；向用户解释时区分「接口不支持」与「skill 没做」。

## 9. upsert-quality-watch 字段命名与逻辑表完整字段（避免半创建）

**字段大小写（实测）**：`--table-info` 内嵌 JSON 中 DATASOURCE 类型必须用驼峰 `dataSource`（大写 S），误用 `datasource`（全小写）或 `DataSource`（PascalCase）均报 `DPN.Bus.ParamsValidateError: dataSource is null!`；TABLE 类型则兼容小写 `datasource`。

**逻辑表监控对象必须传完整 `table` 字段**（实测：仅传 `tableId` 会半创建，后续调度/告警报 `DPN.UniversalQuality.watchTableNotExists`）：

| 字段 | 说明 |
|---|---|
| `tableId` | 逻辑表 ID（对象标识是 TableId 而非 Guid） |
| `tableType` | 固定 `LOGIC_DIM_TABLE`（逻辑维度表）/ 对应事实表类型 |
| `tableCatalog` | 表所属 catalog（业务板块） |
| `projectId` | 项目 ID |
| `bizUnitId` | 业务板块/业务单元 ID |
| `dataSourceId` | 关联数据源 ID |
| `tableName` | 全名（板块名.表名） |

> 物理表/数据源表通常只需 `tableId`+`tableName`(+`dataSourceId`)；逻辑表因非物理存储、需完整上下文才能完成后续调度绑定。字段值可从 `list-tables` 返回的表元数据（guid/projectId/tableId 等）提取。

> **实测状态说明**：以上参数结构与实测经验来自 POC 环境 Python 直连 OpenAPI 的验证结果，已按公共云插件 `aliyun-cli-dataphin-public 0.5.4` 实际契约改写为 `upsert-*` / `list-*` 命令 + 扁平参数形式。A（public-cloud）与 B（standalone）共用同一套命令，仅由 profile/endpoint 区分；命令与参数名在目标 endpoint 的实际可达性需联网运行时验证（见 `acceptance-criteria.md` L2/L3）。
