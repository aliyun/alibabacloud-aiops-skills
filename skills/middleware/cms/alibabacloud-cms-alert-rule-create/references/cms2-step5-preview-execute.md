# CMS 2.0 步骤 5：预览与执行

## 目的

向用户展示配置摘要，获得确认后执行 manage-alert-rules CLI 命令。

---

## 核心规则

> **必须先向用户展示配置摘要并等待确认，然后再执行 CLI 命令。**

> ⚠️ **CMS 2.0 不使用联系人或联系人组。** 请勿在此流程中调用 `PutContact`、`PutContactGroup` 或 `DescribeContactGroupList`。通知仅通过 webhook 实现（`ListAlertWebhooks`）。其他通知类型请提醒用户在规则创建后到云监控控制台中配置。

---

## 配置摘要模板

执行前向用户展示：

| 项目 | 值 |
|------|-------|
| 告警类型 | Prometheus / APM / UModel |
| Workspace | `{user_provided_workspace}`（🔴 用户提供） |
| **Prometheus: cluster_id** | `{user_provided_cluster_id}`（🔴 用户提供，即 instanceId） |
| **APM: service_id** | `{user_provided_service_id}`（🔴 用户提供，用于 datasourceConfig.instanceId + serviceIdList） |
| 规则名称 | （规则名称） |
| 内容模板 | （可选） |
| 数据源 | type + instanceId（如适用） |
| 查询 | （PromQL / APM 指标 / UModel 实体） |
| 严重等级 | P1/P2/P3/P4 |
| 阈值 | 运算符 + 值 |
| 持续时间 | X 秒 |
| 检测间隔 | X 秒 |
| 通知（Webhook） | 用户选择的 webhook 名称（或"无 — 请在控制台中配置"） |
| 通知（其他） | ⚠️ 其他通知类型 → 创建后在云监控控制台中配置 |
| 标签 | （可选） |
| 注解 | （可选） |

---

## 步骤 4：查询 Webhook（通知）

在构建 CLI 命令之前，查询用户可用的 webhook：

```bash
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-cms-alert-rule-create"

aliyun cms list-alert-webhooks --page-size 50 --workspace "{user_provided_workspace}" --read-timeout 30
```

响应包含 `webhooks` 数组。向用户展示列表供其选择：

| 字段 | 说明 |
|-------|-------------|
| `webhookId` | 唯一标识符（用于 notifyConfig） |
| `name` | 显示名称 |
| `url` | Webhook URL |
| `method` | HTTP 方法（GET/POST） |

**流程：**
1. 调用 `list-alert-webhooks` 获取 webhook 列表
2. 向用户展示 webhook 列表，让其选择一个或多个
3. 如果用户需要 webhook → 将选择的 `webhookId` 放入 `notifyConfig.channels`
4. 如果没有可用 webhook 或用户需要其他通知类型（联系人组等） → 提醒用户在规则创建后到云监控控制台中配置

---

## CLI 命令

```bash
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-cms-alert-rule-create"

aliyun cms manage-alert-rules --body '{
  "action": "CREATE",
  "workspace": "{user_provided_workspace}",
  "displayName": "<rule-name>",
  "contentTemplate": "",
  "enabled": true,
  "datasourceConfig": {
    "type": "<PROMETHEUS|APM|UMODEL>",
    "instanceId": "<instance-id>",
    "regionId": "<region-id>"
  },
  "queryConfig": {
    "type": "<query-type>",
    ...
  },
  "conditionConfig": {
    "type": "<condition-type>",
    "severity": "<P1|P2|P3|P4>",
    "operator": "<operator>",
    "threshold": <value>,
    "durationSecs": <seconds>
  },
  "scheduleConfig": {
    "type": "FIXED",
    "intervalSecs": 60
  },
  "actionIntegrationConfig": {
    "enabled": false,
    "actions": []
  },
  "armsIntegrationConfig": {
    "enabled": false
  },
  "notifyConfig": {
    "type": "DIRECT_NOTIFY",
    "channels": [
      {
        "type": "webhook",
        "identifiers": ["{webhookId}"]
      }
    ]
  },
  "labels": {},
  "annotations": {}
}'
```

---

## 通知配置（支持 Webhook）

> **CMS 2.0 通过 CLI 支持 webhook 通知。** 其他通知类型（联系人组、钉钉等）必须在云监控控制台中配置。

### Webhook 流程
1. 调用 `list-alert-webhooks --page-size 50 --workspace "{user_provided_workspace}"` 查询可用 webhook
2. 向用户展示 webhook 列表供其选择
3. 将选择的 webhookId 放入 `notifyConfig`：

```json
"notifyConfig": {
  "type": "DIRECT_NOTIFY",
  "channels": [
    {
      "type": "webhook",
      "identifiers": ["{webhookId_1}", "{webhookId_2}"]
    }
  ]
}
```

### 其他通知类型
> 联系人组、钉钉机器人、邮件、短信等通知类型，请在规则创建后到云监控控制台中配置：
> **中国地域**：`https://cms.console.aliyun.com/`
> 操作路径：告警规则 → 找到对应规则 → 编辑 → 通知设置

### 用户不需要 Webhook 的情况
如果用户明确拒绝 webhook 或没有可用 webhook，则从请求体中省略 `notifyConfig`，并提醒用户在控制台中配置通知。

## ActionIntegrationConfig / ArmsIntegrationConfig

| 配置项 | 字段 | 类型 | 说明 |
|--------|-------|------|-------------|
| ActionIntegrationConfig | `enabled` | boolean | 是否启用行动集成 |
| ActionIntegrationConfig | `actions` | array(string) | 行动集成 ID 列表 |
| ArmsIntegrationConfig | `enabled` | boolean | 是否启用 ARMS 集成 |

---

## 完整示例

### Prometheus CPU 告警

```bash
aliyun cms manage-alert-rules --body '{
  "action": "CREATE",
  "workspace": "{user_provided_workspace}",
  "displayName": "K8s-Node-CPU-High",
  "enabled": true,
  "datasourceConfig": {
    "type": "PROMETHEUS",
    "instanceId": "{user_provided_cluster_id}",
    "regionId": "cn-hangzhou"
  },
  "queryConfig": {
    "type": "PROMETHEUS_SINGLE_QUERY",
    "promQl": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
  },
  "conditionConfig": {
    "type": "PROMETHEUS_SIMPLE_CONDITION",
    "durationSecs": 300,
    "severity": "P2"
  },
  "scheduleConfig": {"type": "FIXED", "intervalSecs": 60},
  "notifyConfig": {
    "type": "DIRECT_NOTIFY",
    "channels": [
      {"type": "webhook", "identifiers": ["my-webhook-id"]}
    ]
  }
}'
```

> ⚠️ 如果用户选择了 webhook，按上述方式包含 `notifyConfig`。其他通知类型请提醒用户在规则创建后到云监控控制台中配置。

### APM 响应时间告警

```bash
aliyun cms manage-alert-rules --body '{
  "action": "CREATE",
  "workspace": "{user_provided_workspace}",
  "displayName": "Order-Service-RT-High",
  "enabled": true,
  "datasourceConfig": {
    "type": "APM",
    "instanceId": "{user_provided_service_id}",
    "regionId": "cn-hangzhou"
  },
  "queryConfig": {
    "type": "APM_MULTI_QUERY",
    "serviceIdList": ["{user_provided_service_id}"],
    "measureList": [{"measureCode": "rt", "windowSecs": 300}]
  },
  "conditionConfig": {
    "type": "APM_SIMPLE_CONDITION",
    "durationSecs": 300,
    "aggregate": "AVG",
    "thresholdList": [
      {"severity": "P1", "threshold": 1000},
      {"severity": "P2", "threshold": 500}
    ]
  },
  "scheduleConfig": {"type": "FIXED", "intervalSecs": 60},
  "notifyConfig": {
    "type": "DIRECT_NOTIFY",
    "channels": [
      {"type": "webhook", "identifiers": ["my-webhook-id"]}
    ]
  }
}'
```

> ⚠️ 如果用户选择了 webhook，按上述方式包含 `notifyConfig`。其他通知类型请提醒用户在规则创建后到云监控控制台中配置。

---

## 响应处理

成功响应：
```json
{
  "data": {
    "alertRule": {
      "uuid": "rule-uuid-xxx",
      "displayName": "...",
      "enabled": true,
      "...": "完整规则对象"
    },
    "deletedCount": 0,
    "deletedUuidList": []
  },
  "code": "",
  "success": true,
  "requestId": "request-id-xxx",
  "message": ""
}
```

> 创建/更新操作返回 `data.alertRule`（完整规则对象）；BATCH_DELETE 操作返回 `data.deletedCount` 和 `data.deletedUuidList`。

保存 `uuid` 用于后续验证和管理。

---

## 下一步
→ 通过 `cms2-step-query.md` 验证规则创建（按 uuid 查询）
→ 如果配置了 webhook，通知即刻生效。其他通知类型请在**云监控控制台**中配置（`https://cms.console.aliyun.com/`）
