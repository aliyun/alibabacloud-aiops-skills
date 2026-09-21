# Airflow 数据源配置模板

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dsName` | string | 是 | 数据源的名称 |
| `categoryType` | string | 是 | 固定值：`WORKFLOW` |
| `dsType` | string | 是 | 固定值：`Airflow` |
| `dsStatus` | integer | 是 | 固定值：`-1` |

### dsConfig 配置项

| 字段 | 类型 | 必填 | 配置要求 |
|------|------|------|----------|
| `dsVersion` | string | 是 | 只能选择一个版本，可选值：`1.4.0` |
| `operator` | string | 是 | 固定值：`manual` |
| `source-file-path` | string | 否 | 本地元数据文件路径。**若提供相对路径，需主动追问绝对路径**；若为空则跳过上传步骤 |

## 模板示例

```json
{
  "dsName": "数据源的名称",
  "categoryType": "WORKFLOW",
  "dsType": "Airflow",
  "dsConfig": {
    "dsVersion": "1.4.0",
    "operator": "manual",
    "source-file-path": "文件路径"
  },
  "dsStatus": -1
}
```
