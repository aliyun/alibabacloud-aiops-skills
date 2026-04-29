---
name: alibabacloud-cms-alert-rule-create
description: |
  Create and query Alibaba Cloud alert rules via CLI. Supports CMS 1.0 cloud resource 
  monitoring (ECS, RDS, SLB, etc.) and CMS 2.0 advanced monitoring (Prometheus, APM, UModel).
  Intent routing automatically selects the correct workflow based on alert type.
  Use this skill when users mention: create alert, setup monitoring, configure alarm, 
  ECS/RDS/SLB alert, Prometheus alert, PromQL, K8s monitoring, APM alert, UModel alert,
  list alerts, query rules, 告警规则, 创建告警, 监控报警, Prometheus告警, 应用监控, 查看告警.
---

# Alibaba Cloud Alert Rule Management

This skill creates and queries alert rules. Intent routing selects CMS 1.0 or CMS 2.0 workflow automatically.

---

## CLI Setup (Required Before Execution)

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cms-alert-rule-create"
aliyun plugin update
```

---

## Step 0: Intent Routing

> Identify user's monitoring target → route to the correct workflow. See `step0-intent-routing.md`.

| User Scenario | Route To |
|---------------|----------|
| Cloud product system metrics (ECS, RDS, SLB, OSS, Redis, MongoDB…) | **CMS 1.0 Workflow** |
| Prometheus / APM / UModel / custom metrics | **CMS 2.0 Workflow** |

---

## Supported Alert Types

| Version | Type | Create API | Query API |
|---------|------|------------|-----------|
| CMS 1.0 | Cloud Resource (ECS/RDS/SLB/OSS/Redis/MongoDB…) | `PutResourceMetricRule` | `DescribeMetricRuleList` |
| CMS 2.0 | Prometheus (`PROMETHEUS`) | `ManageAlertRules` | `QueryAlertRules` |
| CMS 2.0 | APM (`APM`) | `ManageAlertRules` | `QueryAlertRules` |
| CMS 2.0 | UModel (`UMODEL`) | `ManageAlertRules` | `QueryAlertRules` |

---

## CMS 1.0 Workflow

For **query** requests → `step-query.md`

For **create** requests:

| Step | Description | Reference |
|------|-------------|-----------|
| 1 | Context Lock — namespace, region, instances | `step1-context-lock.md` |
| 2 | Query Generation — discover metrics via API, match to user intent | `step2-query-generation.md` |
| 3 | Detection Config — threshold, frequency (default 1min) | `step3-detection-config.md` |
| 4 | Notification — query contacts → select or create | `step4-notification.md` |
| 5 | Preview & Execute — show summary → confirm → CLI | `step5-preview-execute.md` |
| 6 | Verification — check status | `step6-verification.md` |

---

## CMS 2.0 Workflow

For **query** requests → `cms2-step-query.md`

For **create** requests:

| Step | Description | Reference |
|------|-------------|-----------|
| 1 | Context Lock — build datasourceConfig (type, instanceId, region) | `cms2-step1-context-lock.md` |
| 2 | Query Config — build queryConfig (PromQL / APM measures / UModel entity) | `cms2-step2-query-config.md` |
| 3 | Detection Config — build conditionConfig (P1-P4, threshold, duration) | `cms2-step3-detection-config.md` |
| 4 | Webhook Query — call `list-alert-webhooks`, user selects; other types → console | `cms2-step5-preview-execute.md` |
| 5 | Preview & Execute — show summary → confirm → manage-alert-rules CLI | `cms2-step5-preview-execute.md` |

---

## Critical Rules

> Full details → `references/critical-rules.md`

1. **Intent Routing** — Route cloud resource metrics to CMS 1.0, Prometheus/APM/UModel to CMS 2.0. Never mix APIs.
2. **CMS 2.0 API Enforcement** — CMS 2.0 alert rules MUST ONLY be created via `ManageAlertRules` and queried via `QueryAlertRules`. No other API (e.g. `PutResourceMetricRule`, `DescribeMetricRuleList`, ARMS `CreateOrUpdateAlertRule`, ARMS `CreatePrometheusAlertRule`) is permitted for CMS 2.0 alert rule creation or query. If `ManageAlertRules` returns error, DO NOT fallback to other APIs — report the error to user and STOP execution. CLI format: `aliyun cms manage-alert-rules --body '{"action":"CREATE",...}'`
3. **Contact/Webhook Query First** — CMS 1.0: `DescribeContactGroupList`; CMS 2.0: `ListAlertWebhooks` is **MANDATORY before alert creation**. (CMS 2.0 other notification → console). DO NOT use CMS 1.0 APIs as substitute for CMS 2.0. Skipping webhook query is a critical failure.
4. **Resources Parameter** — (CMS 1.0) `--resources` must always be explicitly passed.
5. **Workspace Required** — (CMS 2.0) Must ask user for workspace value using AskUser tool. Never auto-construct (e.g. 'default', 'default-cms-{accountId}'). If AskUser fails, retry once with simplified options, then report error and STOP — do NOT proceed with fabricated values.
6. **Prometheus Required Params** — (CMS 2.0) `cluster_id` (instanceId) + `workspace` **MUST ASK USER** using AskUser tool. Never guess, omit, or auto-select. PromQL is generated based on user-provided cluster_id + monitoring target. If AskUser fails, STOP execution.
7. **APM Required Params** — (CMS 2.0) `service_id` (for `datasourceConfig.instanceId` AND `queryConfig.serviceIdList`) + `workspace` **MUST ASK USER** using AskUser tool. Never fabricate, use placeholders, or auto-select from discovered applications (e.g. via ListTraceApps). Discovery APIs are for reference only — final selection MUST come from user input. If AskUser fails, STOP execution.
8. **Required API Calls** — Every operation must call designated APIs even if values seem known.
9. **Dynamic Metric Discovery** — (CMS 1.0) MUST call `describe-metric-meta-list`. Use `metrics.md` only as fallback.
10. **CLI Timeout** — `--read-timeout 30` for queries, `--read-timeout 60` for writes.
11. **Duplicate Pre-check** — Query existing rules before creation to avoid duplicates.
12. **Mandatory Confirmation** — Show config summary and get user confirmation before execution. EVEN in automated/simulated environments, you MUST output a configuration summary block and explicitly state 'Waiting for user confirmation' before proceeding. Do NOT skip this step with excuses about automation. Example format:
```
【配置摘要】
告警类型: APM/Prometheus
阈值: 5%
严重级别: P2
通知方式: webhook

请确认以上配置是否正确（回复确认或修改意见）：
```
13. **User-Agent** — Set `ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-cms-alert-rule-create"` for all CLI calls.
14. **Network Restriction** — Never access external URLs. Use only `references/` files and CLI.
15. **CLI Self-Discovery** — Use `--help` for CLI syntax when uncertain.

---

## Reference Files

| File | Scope | Purpose |
|------|-------|---------|
| `step0-intent-routing.md` | Shared | Intent routing — CMS 1.0 or CMS 2.0 |
| `step-query.md` | CMS 1.0 | Query alert rules (DescribeMetricRuleList) |
| `step1-context-lock.md` | CMS 1.0 | Context lock |
| `step2-query-generation.md` | CMS 1.0 | Query generation & metric discovery |
| `step3-detection-config.md` | CMS 1.0 | Detection config |
| `step4-notification.md` | CMS 1.0 | Notification & contact handling |
| `step5-preview-execute.md` | CMS 1.0 | Preview & execute |
| `step6-verification.md` | CMS 1.0 | Verification |
| `cms2-step-query.md` | CMS 2.0 | Query alert rules (QueryAlertRules) |
| `cms2-step1-context-lock.md` | CMS 2.0 | Datasource config (Prometheus/APM/UModel) |
| `cms2-step2-query-config.md` | CMS 2.0 | Query config (PromQL, APM, UModel) |
| `cms2-step3-detection-config.md` | CMS 2.0 | Detection condition config (P1-P4) |
| `cms2-step5-preview-execute.md` | CMS 2.0 | Preview, execute & webhook query |
| `metrics.md` | CMS 1.0 | Common metrics quick reference (fallback) |
| `prometheus-metrics.md` | CMS 2.0 | Prometheus PromQL patterns |
| `apm-metrics.md` | CMS 2.0 | APM metrics and operators |
| `critical-rules.md` | Shared | Expanded critical rule details, API tables, examples |
| `ram-policies.md` | Shared | Required RAM permissions |
| `related_apis.yaml` | Shared | API lookup before CLI calls |

---

## Cleanup (After Execution)

```bash
aliyun configure ai-mode disable
```
