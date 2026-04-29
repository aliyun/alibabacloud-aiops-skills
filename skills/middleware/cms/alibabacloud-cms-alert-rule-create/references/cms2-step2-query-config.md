# CMS 2.0 步骤 2：查询配置（queryConfig）

## 目的

构建 queryConfig，定义需要监控的指标/数据。配置内容因告警类型而异。

---

## queryConfig 类型

| datasourceConfig.type | queryConfig.type | 说明 |
|----------------------|------------------|-------------|
| PROMETHEUS | `PROMETHEUS_SINGLE_QUERY` | 自定义 PromQL 表达式 |
| PROMETHEUS | `PROMETHEUS_PRESET_METRIC` | 预定义指标（来自 metricSet）（⚠️ 官方文档未列出此类型，可能需要确认） |
| APM | `APM_MULTI_QUERY` | 带过滤条件的应用指标 |
| UMODEL | `UMODEL_METRICSET_QUERY` | 基于实体的指标集查询 |

---

## Prometheus 查询配置

> **⚠️ PromQL 是基于用户提供的 `cluster_id`（即 Prometheus 实例 ID）和监控需求来动态生成的。**
> - 用户必须先提供 `cluster_id`（**🔴 必须询问用户**，对应 `datasourceConfig.instanceId`）
> - 然后根据用户的监控目标（如 CPU、内存、Pod 重启等）生成对应的 PromQL
> - 流程：用户提供 cluster_id + 监控目标 → 生成对应 PromQL → 填入 queryConfig

### 方式 A：自定义 PromQL（PROMETHEUS_SINGLE_QUERY）

```json
{
  "type": "PROMETHEUS_SINGLE_QUERY",
  "promQl": "<根据用户监控需求动态生成的 PromQL>",
  "enableDataCompleteCheck": true
}
```

**PromQL 生成示例：**

| 用户监控目标 | 生成的 PromQL |
|-------------|--------------|
| 节点 CPU 使用率 | `100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| 节点内存使用率 | `(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100` |
| Pod 重启次数 | `increase(kube_pod_container_status_restarts_total[1h])` |
| 容器 CPU 使用率 | `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) * 100` |

常用 PromQL 模式 → 参见 `prometheus-metrics.md`

> `enableDataCompleteCheck`（boolean）：可选，是否启用数据完整性检查。

### 方式 B：预设指标（PROMETHEUS_PRESET_METRIC）

> ⚠️ 官方文档未列出此类型，可能需要确认是否实际支持。

```json
{
  "type": "PROMETHEUS_PRESET_METRIC",
  "metricSet": "node-exporter",
  "metric": "cpu_usage"
}
```

---

## APM 查询配置（APM_MULTI_QUERY）

> **⚠️ `serviceIdList` 中的 `service_id` 必须由用户提供（**🔴 必须询问用户**），不可自行编造或使用占位符。**

```json
{
  "type": "APM_MULTI_QUERY",
  "serviceIdList": ["{user_provided_service_id}"],
  "filterList": [
    {
      "key": "interface",
      "type": "eq",
      "value": "/api/order"
    }
  ],
  "measureList": [
    {
      "measureCode": "rt",
      "windowSecs": 300,
      "groupBy": ["interface"]
    }
  ]
}
```

> service_id 是 APM 应用的唯一标识（如 `atc889zkcf@9781f3c4e12xxx`），用户可在 ARMS 控制台的应用列表中找到。

### APM 指标代码

| 指标分组 | measureCode | 说明 |
|-------------|-------------|-------------|
| APP_STAT | `rt` | 响应时间（毫秒） |
| APP_STAT | `count` | 请求次数 |
| APP_STAT | `error` | 错误次数 |
| APP_STAT | `errorRate` | 错误率（%） |
| JVM | `heapUsedPercent` | 堆内存使用率（%） |
| JVM | `gcCount` | GC 次数 |
| EXCEPTION | `exceptionCount` | 异常次数 |
| DB | `sqlRt` | SQL 响应时间（毫秒） |
| HOST | `cpuUsage` | 主机 CPU 使用率（%） |
| HOST | `memoryUsage` | 主机内存使用率（%） |

更多详情 → 参见 `apm-metrics.md`

---

## UModel 查询配置（UMODEL_METRICSET_QUERY）

```json
{
  "type": "UMODEL_METRICSET_QUERY",
  "metricSet": "ai-app-operation-metrics",
  "metric": "token-usage",
  "entityDomain": "ai-application",
  "entityType": "application",
  "entityFilters": [
    {
      "field": "app-id",
      "operator": "eq",
      "value": "app-123"
    }
  ],
  "labelFilters": [
    {
      "key": "env",
      "operator": "eq",
      "value": "prod"
    }
  ],
  "entityFields": [
    {
      "field": "app-name"
    }
  ]
}
```

### UModel queryConfig 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|-------|------|----------|-------------|
| `type` | string | 是 | `UMODEL_METRICSET_QUERY` |
| `metricSet` | string | 是 | 指标集名称 |
| `metric` | string | 是 | 指标名称 |
| `entityDomain` | string | 否 | 实体所属域 |
| `entityType` | string | 否 | 实体类型 |
| `entityFilters` | array(UmodelEntityFilter) | 否 | 实体过滤列表 |
| `labelFilters` | array(UmodelLabelFilter) | 否 | 标签过滤条件 |
| `entityFields` | array(UmodelEntityField) | 否 | 需要附带返回的实体字段 |

---

## 下一步
→ `cms2-step3-detection-config.md`
