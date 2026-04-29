# CMS 2.0 步骤 3：检测配置（conditionConfig）

## 目的

构建 conditionConfig，定义告警阈值和检测行为。

---

## 严重等级

CMS 2.0 使用 P 级严重等级（与 CMS 1.0 的 critical/warn/info 不同）：

| 等级 | 名称 | 说明 | 推荐场景 |
|-------|------|-------------|----------------|
| P1 | 严重 | 紧急，需要立即处理 | 服务宕机、数据丢失风险 |
| P2 | 错误 | 重要，需要尽快关注 | 性能下降、高错误率 |
| P3 | 警告 | 值得注意，需要排查 | 接近阈值 |
| P4 | 信息 | 仅供参考 | 监控感知 |

---

## conditionConfig 类型

| datasourceConfig.type | conditionConfig.type | 说明 |
|----------------------|---------------------|-------------|
| PROMETHEUS | `PROMETHEUS_SIMPLE_CONDITION` | 单一阈值条件 |
| APM | `APM_SIMPLE_CONDITION` | 单/多阈值（按严重等级） |
| APM | `APM_COMPOSITE_CONDITION` | 多条件组合，支持 AND/OR 逻辑 |
| UMODEL | `UMODEL_METRICSET_CONDITION` | 实体指标阈值 |

---

## Prometheus 条件配置

```json
{
  "type": "PROMETHEUS_SIMPLE_CONDITION",
  "durationSecs": 300,
  "severity": "P2"
}
```

> Prometheus 的阈值和比较逻辑在 PromQL 表达式中定义，conditionConfig 仅配置持续时间和严重等级。

### durationSecs

| 值 | 说明 |
|-------|-------------|
| 0 | 即时告警（无持续时间要求） |
| 60 | 持续 1 分钟 |
| 300 | 持续 5 分钟 |

---

## APM 简单条件（APM_SIMPLE_CONDITION）

支持在一条规则中配置多个严重等级阈值：

```json
{
  "type": "APM_SIMPLE_CONDITION",
  "aggregate": "AVG",
  "operator": "GreaterThanThreshold",
  "thresholdList": [
    { "severity": "P1", "threshold": 1000 },
    { "severity": "P2", "threshold": 500 }
  ]
}
```

### 可用运算符（APM / UModel）

| 运算符 | 说明 |
|----------|-------------|
| `GreaterThanThreshold` | 大于阈值 |
| `GreaterThanOrEqualToThreshold` | 大于等于阈值 |
| `LessThanThreshold` | 小于阈值 |
| `LessThanOrEqualToThreshold` | 小于等于阈值 |

## APM 组合条件（APM_COMPOSITE_CONDITION）

多条件组合逻辑：

```json
{
  "type": "APM_COMPOSITE_CONDITION",
  "severity": "P2",
  "relation": "AND",
  "compareList": [
    {
      "aggregate": "AVG",
      "measureCode": "rt",
      "operator": "GreaterThanThreshold",
      "threshold": 500,
      "severity": "P2"
    },
    {
      "aggregate": "SUM",
      "measureCode": "errorRate",
      "operator": "GreaterThanThreshold",
      "threshold": 5,
      "severity": "P2"
    }
  ]
}
```

---

## UModel 条件配置

```json
{
  "type": "UMODEL_METRICSET_CONDITION",
  "durationSecs": 300,
  "severity": "P2",
  "operator": "GreaterThanThreshold",
  "threshold": 100000
}
```

---

## scheduleConfig

检测间隔配置：

| 字段 | 类型 | 说明 |
|-------|------|-------------|
| `type` | string | 调度类型：`FIXED`（固定间隔）/ `CRON`（定时） |
| `intervalSecs` | integer | 调度间隔（秒），type=FIXED 时使用 |

### FIXED 调度

```json
{
  "type": "FIXED",
  "intervalSecs": 60
}
```

常用间隔：60（1 分钟）、300（5 分钟）、900（15 分钟）

---

## 下一步
→ **步骤 4：通知（Webhook）** — 调用 `ListAlertWebhooks` 查询 webhook，让用户选择 → 放入 `notifyConfig`。其他通知类型请提醒用户在云监控控制台中配置。
→ `cms2-step5-preview-execute.md`（预览与执行）
