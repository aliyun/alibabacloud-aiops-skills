# 条件调度（Conditional Schedule）数据结构

> 本文件补充说明 Dataphin 离线任务条件调度的数据结构，数据来源于 UI 接口 `/api/dataProcess/{projectId}/nodes/{fileId}/config` 的实际响应。公共 OpenAPI `UpdateBatchTask` 暂未直接暴露该结构。

## 顶层开关

```jsonc
{
  "conditionScheduleEnable": true,
  "conditionScheduleParamDTOList": [ ... ]
}
```

## 单条条件规则结构

```jsonc
{
  "conditionName": "非周六空跑(即仅周六运行)",   // 条件名称
  "enable": true,                              // 是否启用
  "followScheduleParam": false,                // 是否跟随主调度参数
  "nodeStatus": 3,                             // 1=正常运行, 3=空跑
  "cronExpression": "0 0 0 * * ?",             // 满足条件时的调度 cron
  "scheduleTime": null,                        // 具体调度时刻（可选）
  "scheduleConditionDTO": {                    // 条件表达式
    "type": "RELATION",
    "operator": "AND",                         // AND | OR
    "expression": null,
    "subConditions": [
      {
        "type": "EXPRESSION",
        "operator": null,
        "expression": {
          "expressionType": "BIZDATE",         // 固定为业务日期
          "operator": "NOT_BELONG",            // BELONG | NOT_BELONG
          "expressionValueDTO": {
            "expressionValueType": "CUSTOM_CALENDAR",  // CUSTOM_CALENDAR | PUBLIC_CALENDAR
            "publicCalendarName": null,
            "publicCalendarCode": null,
            "type": "DATE_TYPE",               // DATE_TYPE
            "period": "WEEK",                  // WEEK | MONTH 等
            "values": ["6"]                    // 星期：1=周一 ... 6=周六, 0=周日
          }
        },
        "subConditions": null
      }
    ]
  }
}
```

## 关键字段说明

| 字段 | 说明 | 示例 |
|---|---|---|
| `conditionScheduleEnable` | 是否开启条件调度 | `true` |
| `conditionScheduleParamDTOList` | 条件规则列表，按顺序匹配 | 数组 |
| `conditionName` | 规则名称 | `"周六8点运行"` |
| `nodeStatus` | 满足条件时的节点状态：`1` 正常执行，`3` 空跑 | `1` / `3` |
| `cronExpression` | 满足条件时使用的 cron | `"0 00 08 * * ?"` |
| `scheduleConditionDTO.type` | 固定为 `RELATION` | `RELATION` |
| `scheduleConditionDTO.operator` | 子条件组合方式：`AND` / `OR` | `AND` |
| `expressionType` | 固定为 `BIZDATE` | `BIZDATE` |
| `operator` | `BELONG`（属于）/ `NOT_BELONG`（不属于） | `BELONG` |
| `expressionValueDTO.expressionValueType` | `CUSTOM_CALENDAR` 普通日历 / `PUBLIC_CALENDAR` 公共日历 | `CUSTOM_CALENDAR` |
| `expressionValueDTO.type` | 固定为 `DATE_TYPE` | `DATE_TYPE` |
| `expressionValueDTO.period` | 普通日历周期：`WEEK` / `MONTH` 等 | `WEEK` |
| `expressionValueDTO.values` | 对应取值：星期 `["6"]`、公共日历 `["WORK_DAY"]` 等 | `["6"]` |
| `publicCalendarCode` | 使用公共日历时填写公共日历 Code | `"xx"` |

## 示例：周六且为假日时运行

三条规则组合实现：

1. **非周六空跑**：业务日期不属于星期六 → `nodeStatus=3` 空跑
2. **周六为工作日时空跑**：业务日期属于星期六 **AND** 公共日历类型为工作日 → `nodeStatus=3` 空跑
3. **周六8点运行**：业务日期属于星期六 → `nodeStatus=1` 正常执行，cron 为 `0 00 08 * * ?`

```jsonc
{
  "conditionScheduleEnable": true,
  "conditionScheduleParamDTOList": [
    {
      "conditionName": "非周六空跑(即仅周六运行)",
      "enable": true,
      "followScheduleParam": false,
      "nodeStatus": 3,
      "cronExpression": "0 0 0 * * ?",
      "scheduleConditionDTO": {
        "type": "RELATION",
        "operator": "AND",
        "subConditions": [
          {
            "type": "EXPRESSION",
            "expression": {
              "expressionType": "BIZDATE",
              "operator": "NOT_BELONG",
              "expressionValueDTO": {
                "expressionValueType": "CUSTOM_CALENDAR",
                "type": "DATE_TYPE",
                "period": "WEEK",
                "values": ["6"]
              }
            }
          }
        ]
      }
    },
    {
      "conditionName": "周六为工作日时空跑",
      "enable": true,
      "followScheduleParam": false,
      "nodeStatus": 3,
      "cronExpression": "0 0 0 * * ?",
      "scheduleConditionDTO": {
        "type": "RELATION",
        "operator": "AND",
        "subConditions": [
          {
            "type": "EXPRESSION",
            "expression": {
              "expressionType": "BIZDATE",
              "operator": "BELONG",
              "expressionValueDTO": {
                "expressionValueType": "CUSTOM_CALENDAR",
                "type": "DATE_TYPE",
                "period": "WEEK",
                "values": ["6"]
              }
            }
          },
          {
            "type": "EXPRESSION",
            "expression": {
              "expressionType": "BIZDATE",
              "expressionValueDTO": {
                "expressionValueType": "PUBLIC_CALENDAR",
                "publicCalendarCode": "xx",
                "type": "DATE_TYPE",
                "values": ["WORK_DAY"]
              }
            }
          }
        ]
      }
    },
    {
      "conditionName": "周六8点运行",
      "enable": true,
      "followScheduleParam": false,
      "nodeStatus": 1,
      "cronExpression": "0 00 08 * * ?",
      "scheduleConditionDTO": {
        "type": "RELATION",
        "operator": "OR",
        "subConditions": [
          {
            "type": "EXPRESSION",
            "expression": {
              "expressionType": "BIZDATE",
              "operator": "BELONG",
              "expressionValueDTO": {
                "expressionValueType": "CUSTOM_CALENDAR",
                "type": "DATE_TYPE",
                "period": "WEEK",
                "values": ["6"]
              }
            }
          }
        ]
      }
    }
  ]
}
```

> 规则按列表顺序匹配，前两条把“非周六”和“周六工作日”置为空跑，第三条让剩下的“周六假日”在 8:00 正常执行。

---

## 跨节点输出参数条件（CROSS_NODE_PARAM）

除业务日期/公共日历外，条件调度还支持引用**上游节点的输出参数**，实现“上游参数值满足某条件时，本节点空跑/正常执行”。

### 典型场景

- 上游 Shell 任务 `shell_a` 通过 `setv` 命令设置输出参数：
  ```bash
  echo "chain-shell_a"
  setv "var" "2"
  ```
- 下游任务 `shell_b` 配置条件调度：当 `shell_a.var == 1` 时本节点空跑，否则正常调度。

### 单条规则结构（CROSS_NODE_PARAM）

```jsonc
{
  "conditionName": "跨节点参数shell_a.var为1时空跑",
  "enable": true,
  "followScheduleParam": false,
  "nodeStatus": 3,                        // 满足条件时空跑；正常执行传 1
  "cronExpression": "0 0 0 * * ?",
  "scheduleConditionDTO": {
    "type": "RELATION",
    "operator": "AND",
    "subConditions": [
      {
        "type": "EXPRESSION",
        "expression": {
          "expressionType": "CROSS_NODE_PARAM",
          "operator": "EQUAL",           // EQUAL | NOT_EQUAL
          "expressionValueDTO": {
            "expressionValueType": "CROSS_NODE_PARAM",
            "paramName": "var",          // 上游节点输出参数名
            "nodeId": "n_8127255632277340160",   // 上游节点物理 NodeId
            "nodeName": "shell_a"        // 上游节点名（任务名/output name）
          }
        }
      }
    ]
  }
}
```

### 关键字段说明

| 字段 | 说明 | 示例 |
|---|---|---|
| `expressionType` | 固定为 `CROSS_NODE_PARAM` | `CROSS_NODE_PARAM` |
| `operator` | 比较操作：`EQUAL`（等于）/ `NOT_EQUAL`（不等于） | `EQUAL` |
| `expressionValueDTO.paramName` | 要引用的上游输出参数名 | `"var"` |
| `expressionValueDTO.nodeId` | 上游节点物理 NodeId（`n_xxx`） | `"n_8127255632277340160"` |
| `expressionValueDTO.nodeName` | 上游节点名 / output name | `"shell_a"` |

### 上游输出参数设置方式

Shell 任务在 Code 中使用 Dataphin 内置命令 `setv` 写入输出参数：

```bash
# shell_a 代码示例
setv "var" "1"
```

- `setv` 语法：`setv "<参数名>" "<参数值>"`
- 参数值会被下游通过 `CROSS_NODE_PARAM` 引用
- 若上游未输出该参数，条件调度可能无法正确评估

### 示例：shell_b 根据 shell_a.var 决定空跑或正常执行

```jsonc
{
  "conditionScheduleEnable": true,
  "conditionScheduleParamDTOList": [
    {
      "conditionName": "跨节点参数shell_a.var为1时空跑",
      "enable": true,
      "followScheduleParam": false,
      "nodeStatus": 3,
      "cronExpression": "0 0 0 * * ?",
      "scheduleConditionDTO": {
        "type": "RELATION",
        "operator": "AND",
        "subConditions": [
          {
            "type": "EXPRESSION",
            "expression": {
              "expressionType": "CROSS_NODE_PARAM",
              "operator": "EQUAL",
              "expressionValueDTO": {
                "expressionValueType": "CROSS_NODE_PARAM",
                "paramName": "var",
                "nodeId": "n_8127255632277340160",
                "nodeName": "shell_a"
              }
            }
          }
        ]
      }
    },
    {
      "conditionName": "默认正常调度",
      "enable": true,
      "followScheduleParam": false,
      "nodeStatus": 1,
      "cronExpression": "0 0 0 * * ?",
      "scheduleConditionDTO": {
        "type": "RELATION",
        "operator": "OR",
        "subConditions": []
      }
    }
  ]
}
```

> 规则按顺序匹配：第一条命中（`shell_a.var == 1`）则空跑；否则落到第二条默认规则正常执行。
