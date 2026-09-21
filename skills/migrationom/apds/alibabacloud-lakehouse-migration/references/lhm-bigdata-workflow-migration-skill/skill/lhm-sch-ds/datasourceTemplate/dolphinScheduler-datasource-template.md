# DolphinScheduler 数据源配置模板

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dsName` | string | 是 | 数据源名称 |
| `categoryType` | string | 是 | 固定值：`WORKFLOW` |
| `dsType` | string | 是 | 固定值：`DolphinScheduler` |
| `dsStatus` | integer | 是 | 固定值：`0` |

### dsConfig 配置项

| 字段 | 类型 | 必填 | 配置要求 |
|------|------|------|----------|
| `dsVersion` | string | 是 | 只能选择一个版本，可选值：`3.2.0`、`2.0.0`、`1.3.9`。3.x 直接指向 3.2.0，其他的类推 |
| `operator` | string | 是 | 固定值：`auto` |
| `endpoint` | string | 是 | DolphinScheduler 的接入点，必须是合法的 https/http URL（例如：`https://dolphinscheduler.example.com`），需校验格式 |
| `token` | string | 是 | DolphinScheduler 的认证 token，**必填**，若用户未提供需主动追问 |
| `project` | string | 是 | 项目空间名称，**必填**，若用户未提供需主动追问 |
| `project` | string | 是 | 项目空间名称，必填，缺少需要追问                                                                                |

## 模板示例

```json
{
  "dsName": "数据源名称",
  "categoryType": "WORKFLOW",
  "dsType": "DolphinScheduler",
  "dsConfig": {
    "dsVersion": "3.2.0",
    "operator": "auto",
    "endpoint": "https",
    "token": "token123",
    "project": "sdfasf"
  },
  "dsStatus": 0
}
```
