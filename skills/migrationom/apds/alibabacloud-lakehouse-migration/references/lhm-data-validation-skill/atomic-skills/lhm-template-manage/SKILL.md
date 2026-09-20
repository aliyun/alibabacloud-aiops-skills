---
name: lhm-template-manage
version: 1.0.0
description: Manages CRUD operations (list/detail/create/update/delete) for LHM data validation templates.
---

# lhm-template-manage

Dispatches template CRUD operations via `--action`. All operations reuse the template wrapper functions in the outer `scripts/common.py`.

## Steps

### 0. Prerequisites

- aliyun CLI + aliyun-cli-lhm plugin (including the template APIs; see "Environment Preparation" in the root README)
- Credentials configured in `~/.lhm/data_validation_config.yaml` or environment variables
- The template APIs have been released to production (currently only available in staging)

### 1. List Available Templates

```bash
python atomic-skills/lhm-template-manage/scripts/run.py \
  --action list \
  [--check-type 1] [--name "MIX"] [--is-builtin 1]
```

### 2. View Template Details

```bash
python atomic-skills/lhm-template-manage/scripts/run.py \
  --action detail \
  --template-id <UUID or built-in ID>
```

### 3. Create a Metric Template

```bash
python atomic-skills/lhm-template-manage/scripts/run.py \
  --action create \
  --name "自定义指标模板" \
  --check-type 1 \
  --ds-engine-rels-json '[{"dsType":"MaxCompute","engineTypes":["MaxCompute"]}]' \
  --metric-rules-json '[{"dataTypeClassify":0,"dataTypeGroup":0,"dataTypeList":["INT","BIGINT"],"checkMethods":"SUM,AVG","diffTolerateType":0,"diffTolerateValues":{"SAME":0},"isCountCheck":1}]'
```

### 4. Create a Weak-Content Template

```bash
python atomic-skills/lhm-template-manage/scripts/run.py \
  --action create \
  --name "自定义弱内容模板" \
  --check-type 2 \
  --ds-engine-rels-json '[{"dsType":"MaxCompute","engineTypes":["MaxCompute"]}]' \
  --weak-content-rule-json '{"filterColumnTypes":["TEXT","BLOB"],"filterColumnExpression":".*_bak"}'
```

### 5. Update a Template (upsert semantics)

```bash
python atomic-skills/lhm-template-manage/scripts/run.py \
  --action update \
  --template-id <UUID> \
  --metric-rules-json '[{"ruleId":"<existing ruleId>","dataTypeClassify":0,"dataTypeGroup":0,"dataTypeList":["INT","BIGINT"],"checkMethods":"SUM,AVG,MIN,MAX","diffTolerateType":0,"diffTolerateValues":{"SAME":0},"isCountCheck":1}]'
```

> **Upsert semantics**: rules with a `ruleId` are updated, rules without a `ruleId` are added, and rules not present in the list are deleted.

### 6. Delete Templates

```bash
python atomic-skills/lhm-template-manage/scripts/run.py \
  --action delete \
  --template-ids <UUID1>,<UUID2>
```

## Pitfalls

- **`metricRules` cannot be used on update**: the backend `UpdateCmd.getMetricRules()` clears `metricRules`; you must use `basicMetricRules` (dataTypeClassify=0) and `complexMetricRules` (dataTypeClassify=1). `run.py` automatically splits them by `dataTypeClassify` internally.
- **`checkMethods` is a comma-separated string**: pass `"SUM,AVG,MIN,MAX"`, not a list `["SUM","AVG"]`.
- **`diffTolerateValues` format**: use `{"SAME": 0}` for uniform tolerance, or `{"SUM": 0.01, "AVG": 0.001}` for per-method customization; keys are uppercase.
- **Built-in templates cannot be modified/deleted**: 1001/1002/1003 are system built-ins; detail returns empty rules (hardcoded in MetricPlanner).
- **Backend required fields on update**: the backend requires `checkType`, `dsEngineRels`, and the rules to be present (even when only renaming), otherwise `E500R100`/`E500R102`/`E501R104` is reported. When not provided, `update_template()` back-fills them automatically from the existing template, transparently to the caller.
- **`idList` cannot filter built-in templates**: the `idList` parameter of the list interface has no effect on built-in templates; use `--is-builtin 1` instead.

## Verification

```bash
# List all templates
python atomic-skills/lhm-template-manage/scripts/run.py --action list
# Expected: {"ok": true, "templates": [...]}

# View built-in template details
python atomic-skills/lhm-template-manage/scripts/run.py --action detail --template-id 1001
# Expected: {"ok": true, "template": {"templateId": "1001", ..., "metricRules": []}}

# Full create → detail → update → delete flow
python atomic-skills/lhm-template-manage/scripts/run.py --action create --name "test" --check-type 1 \
  --ds-engine-rels-json '[{"dsType":"MaxCompute","engineTypes":["MaxCompute"]}]' \
  --metric-rules-json '[{"dataTypeClassify":0,"dataTypeGroup":0,"dataTypeList":["INT"],"checkMethods":"SUM"}]'
# Expected: {"ok": true, "templateId": "<UUID>"}
```

## Input/Output Examples

### list — list metric-type built-in templates

```bash
python atomic-skills/lhm-template-manage/scripts/run.py \
  --action list --check-type 1 --is-builtin 1
```

```json
{
  "ok": true,
  "templates": [
    {"templateId": "1001", "templateName": "CUSTOM_METRIC_MIX", "checkType": 1, "isBuiltin": 1},
    {"templateId": "1002", "templateName": "CUSTOM_METRIC_NUM", "checkType": 1, "isBuiltin": 1},
    {"templateId": "1003", "templateName": "CUSTOM_METRIC_LEN", "checkType": 1, "isBuiltin": 1}
  ]
}
```

### detail — view a custom template

```bash
python atomic-skills/lhm-template-manage/scripts/run.py \
  --action detail --template-id cb9f7fc11b2948c5a5a07e45844ffe80
```

```json
{
  "ok": true,
  "template": {
    "templateId": "cb9f7fc11b2948c5a5a07e45844ffe80",
    "templateName": "SDK验证_指标模板",
    "checkType": 1,
    "metricRules": [
      {"ruleId": "...", "dataTypeGroup": 0, "checkMethods": "SUM,AVG", "dataTypeList": ["TINYINT","SMALLINT","INT","BIGINT"]}
    ]
  }
}
```
