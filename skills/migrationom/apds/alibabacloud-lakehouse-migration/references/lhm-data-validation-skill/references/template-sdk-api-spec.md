# 模板管理 API — SDK 新增规范

模板管理共 5 个 API，均通过 aliyun CLI（`aliyun lhm <命令>`）调用，request 模型由本地 `scripts/lhm_models.py` 构造（原 `alibabacloud_lhm20250116` SDK 已废弃、不再安装）。下表「SDK 方法名」即 `client.<方法名>(request)` 的调用入口。数据类型-校验方法映射和 ds-engine 映射为静态数据，已在 skill 知识文件 (`knowledge/patterns/template-guide.md`) 中维护，不需要对应 API。

---

## 总览

| # | RAM Action | HTTP | 路径 | SDK 方法名 |
|---|------------|------|------|-----------|
| 1 | GetDataCheckTemplateList | GET | /dataCheck/template/v3/list | `get_data_check_template_list` |
| 2 | GetDataCheckTemplate | GET | /dataCheck/template/v3/get | `get_data_check_template` |
| 3 | AddDataCheckTemplate | POST | /dataCheck/template/v3/create | `add_data_check_template` |
| 4 | UpdateDataCheckTemplate | POST | /dataCheck/template/v3/update | `update_data_check_template` |
| 5 | DeleteDataCheckTemplate | POST | /dataCheck/template/v3/delete | `delete_data_check_template` |

### 不新增的 API 及原因

| API | 原因 |
|-----|------|
| GetDataCheckTemplateBaseRule | 静态数据，已在知识文件中维护 |
| GetDataCheckTemplateEngineList | 静态数据，已在知识文件中维护 |
| ListDataCheckTemplate (page) | list 接口已返回全部，无需分页 |
| GetDataCheckEngineRelation | detail 接口已包含 dsEngineRels |
| GetDataCheckSupportDatasourceType | detail 接口已覆盖 |
| GetDataCheckSupportEngineType | detail 接口已覆盖 |
| ExecDataCheckTemplateExport | 控制台导出功能，skill 不需要 |

---

## 1. get_data_check_template_list — 模板列表

**Action**: `GetDataCheckTemplateList` · **Method**: GET · **Path**: `/dataCheck/template/v3/list`

### Request: `GetDataCheckTemplateListRequest`

| Python 字段 | 序列化键 | 类型 | 必填 | 说明 |
|------------|---------|------|------|------|
| check_type | checkType | int | 否 | 校验类型筛选 (0/1/2) |
| template_name | templateName | str | 否 | 名称模糊匹配 |
| is_builtin | isBuiltin | int | 否 | 0=自定义, 1=内置 |
| id_list | idList | List[str] | 否 | 指定模板 ID 列表 |

### ResponseBody: `GetDataCheckTemplateListResponseBody`

| Python 字段 | 序列化键 | 类型 |
|------------|---------|------|
| data | data | List[DataItem] |
| err_code | errCode | str |
| err_message | errMessage | str |
| request_id | requestId | str |
| success | success | bool |

**DataItem**: `GetDataCheckTemplateListResponseBodyData`

| Python 字段 | 序列化键 | 类型 | 说明 |
|------------|---------|------|------|
| template_id | templateId | str | |
| template_name | templateName | str | |
| check_type | checkType | int | |
| check_type_export | checkTypeExport | str | 校验类型中文名 |
| ds_types | dsTypes | str | 逗号分隔 |
| engine_types | engineTypes | str | 逗号分隔 |
| is_builtin | isBuiltin | int | |
| template_desc | templateDesc | str | |
| is_used_by_task | isUsedByTask | bool | |
| gmt_modified | gmtModified | str | |

---

## 2. get_data_check_template — 模板详情

**Action**: `GetDataCheckTemplate` · **Method**: GET · **Path**: `/dataCheck/template/v3/get`

### Request: `GetDataCheckTemplateRequest`

| Python 字段 | 序列化键 | 类型 | 必填 |
|------------|---------|------|------|
| template_id | templateId | str | 是 |

### ResponseBody: `GetDataCheckTemplateResponseBody`

| Python 字段 | 序列化键 | 类型 |
|------------|---------|------|
| data | data | DataItem |
| err_code | errCode | str |
| err_message | errMessage | str |
| request_id | requestId | str |
| success | success | bool |

**DataItem**: `GetDataCheckTemplateResponseBodyData`

| Python 字段 | 序列化键 | 类型 | 说明 |
|------------|---------|------|------|
| template_id | templateId | str | |
| template_name | templateName | str | |
| check_type | checkType | int | |
| check_type_export | checkTypeExport | str | |
| template_desc | templateDesc | str | |
| ds_engine_rels | dsEngineRels | List[DsEngineRelItem] | |
| metric_rules | metricRules | List[MetricRuleItem] | checkType=1 时有值 |
| basic_metric_rules | basicMetricRules | List[MetricRuleItem] | 基础类型规则 |
| complex_metric_rules | complexMetricRules | List[MetricRuleItem] | 复合类型规则 |
| weak_content_rule | weakContentRule | WeakContentRuleItem | checkType=2 时有值 |

**DsEngineRelItem**: `GetDataCheckTemplateResponseBodyDataDsEngineRels`

| Python 字段 | 序列化键 | 类型 |
|------------|---------|------|
| ds_type | dsType | str |
| engine_types | engineTypes | List[str] |

**MetricRuleItem**: `GetDataCheckTemplateResponseBodyDataMetricRules`

| Python 字段 | 序列化键 | 类型 | 说明 |
|------------|---------|------|------|
| rule_id | ruleId | str | |
| data_type_classify | dataTypeClassify | int | 0=基础, 1=复合 |
| data_type_group | dataTypeGroup | int | 0-7 |
| data_type_list | dataTypeList | List[str] | 具体类型列表 |
| check_methods | checkMethods | str | 逗号分隔，如 `"SUM,AVG,MIN,MAX"` |
| diff_tolerate_type | diffTolerateType | int | 0=统一, 1=自定义 |
| diff_tolerate_values | diffTolerateValues | dict | 统一: `{"SAME": 0}`; 自定义: `{"SUM": 0.01, "AVG": 0.001}` |
| is_count_check | isCountCheck | int | 0/1 |
| filter_column_name | filterColumnName | str | 过滤列名 |
| ignore_numeric_zero | ignoreNumericZero | bool | extra 字段 |
| ignore_string_empty | ignoreStringEmpty | bool | extra 字段 |
| enable_decimal_scale | enableDecimalScale | bool | extra 字段 |
| set_decimal_scale | setDecimalScale | int | extra 字段 |
| ignore_decimal_scale_suffix_zero | ignoreDecimalScaleSuffixZero | bool | extra 字段 |

**WeakContentRuleItem**: `GetDataCheckTemplateResponseBodyDataWeakContentRule`

| Python 字段 | 序列化键 | 类型 | 说明 |
|------------|---------|------|------|
| rule_id | ruleId | str | |
| filter_column_types | filterColumnTypes | List[str] | 参与校验的列类型 |
| filter_column_expression | filterColumnExpression | str | 列名过滤表达式 |

---

## 3. add_data_check_template — 创建模板

**Action**: `AddDataCheckTemplate` · **Method**: POST · **Path**: `/dataCheck/template/v3/create`

### Request: `AddDataCheckTemplateRequest`

| Python 字段 | 序列化键 | 类型 | 必填 | 说明 |
|------------|---------|------|------|------|
| template_name | templateName | str | 是 | 模板名称 |
| check_type | checkType | int | 是 | 1=指标, 2=弱内容 |
| template_desc | templateDesc | str | 否 | |
| ds_engine_rels | dsEngineRels | List[DsEngineRelCmd] | 是 | 数据源-引擎映射 |
| metric_rules | metricRules | List[MetricRuleCmd] | 条件 | checkType=1 必填 |
| weak_content_rule | weakContentRule | WeakContentRuleCmd | 条件 | checkType=2 必填 |

**DsEngineRelCmd**: `AddDataCheckTemplateRequestDsEngineRels`

| Python 字段 | 序列化键 | 类型 |
|------------|---------|------|
| ds_type | dsType | str |
| engine_types | engineTypes | List[str] |

**MetricRuleCmd**: `AddDataCheckTemplateRequestMetricRules`

| Python 字段 | 序列化键 | 类型 | 必填 | 说明 |
|------------|---------|------|------|------|
| data_type_classify | dataTypeClassify | int | 是 | 0=基础, 1=复合 |
| data_type_group | dataTypeGroup | int | 是 | 0-7 |
| data_type_list | dataTypeList | List[str] | 是 | 具体类型列表 |
| check_methods | checkMethods | str | 是 | 逗号分隔字符串，如 `"SUM,AVG"`，须在 base_rule 范围内 |
| diff_tolerate_type | diffTolerateType | int | 否 | 0=统一(默认), 1=自定义 |
| diff_tolerate_values | diffTolerateValues | dict | 否 | 统一: `{"SAME": 0}`; 自定义: `{"SUM": 0.01, "AVG": 0.001}` |
| is_count_check | isCountCheck | int | 否 | 默认 1 |
| filter_column_name | filterColumnName | str | 否 | 不参与校验的列名 |
| ignore_numeric_zero | ignoreNumericZero | bool | 否 | |
| ignore_string_empty | ignoreStringEmpty | bool | 否 | |
| enable_decimal_scale | enableDecimalScale | bool | 否 | |
| set_decimal_scale | setDecimalScale | int | 否 | |
| ignore_decimal_scale_suffix_zero | ignoreDecimalScaleSuffixZero | bool | 否 | |

**WeakContentRuleCmd**: `AddDataCheckTemplateRequestWeakContentRule`

| Python 字段 | 序列化键 | 类型 | 必填 |
|------------|---------|------|------|
| filter_column_types | filterColumnTypes | List[str] | 否 |
| filter_column_expression | filterColumnExpression | str | 否 |

### ResponseBody: `AddDataCheckTemplateResponseBody`

| Python 字段 | 序列化键 | 类型 | 说明 |
|------------|---------|------|------|
| data | data | str | 新建的模板 ID (UUID) |
| err_code | errCode | str | |
| err_message | errMessage | str | |
| request_id | requestId | str | |
| success | success | bool | |

---

## 4. update_data_check_template — 更新模板

**Action**: `UpdateDataCheckTemplate` · **Method**: POST · **Path**: `/dataCheck/template/v3/update`

### Request: `UpdateDataCheckTemplateRequest`

| Python 字段 | 序列化键 | 类型 | 必填 | 说明 |
|------------|---------|------|------|------|
| template_id | templateId | str | 是 | 要更新的模板 ID |
| template_name | templateName | str | 否 | |
| check_type | checkType | int | 否 | |
| template_desc | templateDesc | str | 否 | |
| ds_engine_rels | dsEngineRels | List[DsEngineRelCmd] | 否 | 同 create |
| basic_metric_rules | basicMetricRules | List[BasicMetricRuleCmd] | 条件 | checkType=1 时必须用此字段 |
| complex_metric_rules | complexMetricRules | List[ComplexMetricRuleCmd] | 条件 | 复合类型规则 |
| weak_content_rule | weakContentRule | WeakContentRuleCmd | 否 | 同 create |

> **⚠️ 关键陷阱：update 不能用 `metric_rules`**
>
> 后端 `CheckTemplateUpdateCmd.getMetricRules()` 会无条件清空 `metricRules` 字段，只从 `basicMetricRules` + `complexMetricRules` 合并。这与 `AddCmd` 不同（Add 在 `metricRules` 非空时直接使用）。如果 update 传 `metric_rules`，后端会收到空规则列表，报 `E501R104: Metric template rule is empty`。
>
> **正确做法**：`dataTypeClassify=0` 的规则放 `basic_metric_rules`，`dataTypeClassify=1` 的放 `complex_metric_rules`。

> **upsert 语义**：有 `ruleId` 的规则做更新，没有 `ruleId` 的新增，库中已有但请求中未包含的会被删除。全量替换时需先通过 detail 接口获取现有规则的 `ruleId`。

> **`update_template()` 自动回填**：后端要求 `checkType`、`dsEngineRels` 和规则必传（即使只改名称），否则报 `E500R100`/`E500R102`/`E501R104`。封装函数 `update_template()` 未传这些字段时自动从现有模板回填，调用方无感。传空列表 `[]` 则视为显式清空。

子模型 BasicMetricRuleCmd / ComplexMetricRuleCmd / DsEngineRelCmd / WeakContentRuleCmd 字段与 create 接口的对应模型完全相同（类名不同：`UpdateDataCheckTemplateRequestBasicMetricRules` 等）。

### ResponseBody: `UpdateDataCheckTemplateResponseBody`

标准信封（data=null, errCode, errMessage, requestId, success）。

---

## 5. delete_data_check_template — 删除模板

**Action**: `DeleteDataCheckTemplate` · **Method**: POST · **Path**: `/dataCheck/template/v3/delete`

### Request: `DeleteDataCheckTemplateRequest`

| Python 字段 | 序列化键 | 类型 | 必填 | 说明 |
|------------|---------|------|------|------|
| template_ids | templateIds | List[str] | 是 | 支持批量 |

### ResponseBody: `DeleteDataCheckTemplateResponseBody`

标准信封。

---

## SDK 文件清单

5 个 API × 3 文件 = **15 个新模型文件** + `__init__.py` 追加 15 个 export + `client.py` 追加 5 组方法（每组 sync/async/with_options 共 3 个方法）。

```
models/
├── _get_data_check_template_list_request.py
├── _get_data_check_template_list_response.py
├── _get_data_check_template_list_response_body.py
├── _get_data_check_template_request.py
├── _get_data_check_template_response.py
├── _get_data_check_template_response_body.py
├── _add_data_check_template_request.py
├── _add_data_check_template_response.py
├── _add_data_check_template_response_body.py
├── _update_data_check_template_request.py
├── _update_data_check_template_response.py
├── _update_data_check_template_response_body.py
├── _delete_data_check_template_request.py
├── _delete_data_check_template_response.py
├── _delete_data_check_template_response_body.py
└── __init__.py  (追加 15 个 export)
```

## 命名规范速查

| 场景 | 规范 | 示例 |
|------|------|------|
| Python 字段 | snake_case | `check_template_id` |
| 序列化键 | camelCase | `'checkTemplateId'` |
| 客户端方法 | snake_case | `add_data_check_template` |
| Action 字符串 | PascalCase | `'AddDataCheckTemplate'` |
| Request 类 | PascalCase + Request | `AddDataCheckTemplateRequest` |
| Response 类 | PascalCase + Response | `AddDataCheckTemplateResponse` |
| ResponseBody 类 | PascalCase + ResponseBody | `AddDataCheckTemplateResponseBody` |
| 子模型类 | 父类名 + 字段名 PascalCase | `AddDataCheckTemplateRequestMetricRules` |
| 文件名 | `_` + snake_case | `_add_data_check_template_request.py` |

---

## 预发环境验证结果 (SDK 2.0.1 + lhm-pre)

6 个场景、54 项断言全部通过 (54/54 = 100%)。

| 场景 | 接口 | 结果 | 备注 |
|------|------|------|------|
| 1. list | get_data_check_template_list | ✓ | checkType/isBuiltin/name 过滤正确；`idList` 过滤内置模板返回 0 |
| 2. detail 内置 | get_data_check_template(1001/1002/1003) | ✓ | `metric_rules` 为空（硬编码在 MetricPlanner）；不存在 ID 抛 RuntimeError |
| 3a. create 指标 | add_data_check_template(checkType=1) | ✓ | 2 条规则完整回读，ruleId 自动分配 |
| 3b. create 弱内容 | add_data_check_template(checkType=2) | ✓ | `weakContentAlgorithm` 自动设为 `md5` |
| 4a. update upsert | update_data_check_template | ✓ | 更新(带ruleId)/新增(无ruleId)/删除(不传) 三种语义正确 |
| 4b. update 部分 | update_data_check_template | ✓ | 仅改名称时 auto-fill 保留 checkType/dsEngineRels/规则 |
| 5. delete batch | delete_data_check_template | ✓ | 批量删除后 detail 返回空 data |
| 6. 异常处理 | check_resp 统一格式 | ✓ | get 不存在模板抛 `[GetDataCheckTemplate]` 格式错误；后端对 create/update/delete 宽容 |

### 验证中发现的关键问题

| # | 问题 | 影响 | 根因 | 解决方案 |
|---|------|------|------|---------|
| 1 | update 传 `metric_rules` 报 E501R104 | update API 直接不可用 | `UpdateCmd.getMetricRules()` 无条件清空 metricRules | **必须用 `basic_metric_rules`/`complex_metric_rules`**，`update_template()` 已自动拆分 |
| 2 | update 不传 checkType/dsEngineRels/规则报 E500R100/E500R102/E501R104 | 部分更新（如改名）失败 | 后端 update 不做 null 判断直接拆箱 | **`update_template()` 自动回填**，调用方无需关心 |
| 3 | idList 过滤内置模板返回 0 | list 的 idList 无法筛选内置 | 后端未将内置模板 ID 纳入匹配 | 用 checkType/isBuiltin 组合筛选替代 |
| 4 | detail 的 checkTypeExport 为 None | 无法获取校验类型中文名 | detail 接口未填充 | 前端/skill 自行映射 |
| 5 | 后端对 create/update/delete 极宽容 | 非法 dsType、不存在 ID 均不报错 | 后端未做严格校验 | 非功能性问题，记录即可 |
