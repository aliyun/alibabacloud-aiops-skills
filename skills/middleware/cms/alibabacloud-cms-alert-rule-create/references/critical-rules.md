# 关键规则 — 详细参考

本文件包含 SKILL.md 中关键规则摘要的展开详情。规则标注有 (CMS 1.0)、(CMS 2.0) 或 (Shared) 适用范围。

---

## 1. 意图路由 (Shared)

根据监控目标将用户请求路由到正确的工作流：

| 用户场景 | 路由至 | API |
|----------|--------|-----|
| 云产品系统指标（ECS、RDS、SLB、OSS、Redis 等） | CMS 1.0 工作流 | `PutResourceMetricRule`, `DescribeMetricRuleList` |
| Prometheus / APM / UModel / 自定义指标 | CMS 2.0 工作流 | `ManageAlertRules`, `QueryAlertRules` |

> **禁止跨版本混用 API。** CMS 1.0 API 无法处理 Prometheus/APM/UModel 数据。CMS 2.0 API 无法处理云资源指标。

---

## 2. 创建前查询联系人/Webhook

### CMS 1.0：联系人查询

> 详细内容参见 `step4-notification.md`。

创建告警规则前，必须先调用 `DescribeContactGroupList` 查询已有的联系人组。

### CMS 2.0：Webhook 查询

**强制要求：在创建任何 CMS 2.0 告警之前，必须调用 `ListAlertWebhooks`。** 跳过此步骤属于严重错误。

在配置通知前，调用 `ListAlertWebhooks` 查询可用的 webhook。

| 操作 | API | CLI |
|------|-----|-----|
| 查询 webhook | `ListAlertWebhooks` | `aliyun cms list-alert-webhooks --page-size 50 --workspace {workspace}` |

- 将 webhook 列表展示给用户供其选择
- 将选中的 webhookId 写入 `notifyConfig.channels`
- 其他通知类型（联系人组、钉钉等）→ 提醒用户在规则创建后前往云监控控制台配置

> **CMS 2.0 不使用联系人或联系人组。** 以下 CMS 1.0 API 在 CMS 2.0 工作流中**禁止使用**：
> - `PutContact`、`PutContactGroup`、`DescribeContactGroupList`
> - **不得**使用 CMS 1.0 通知 API 替代 CMS 2.0 webhook 查询

---

## 3. Resources 参数格式 (CMS 1.0)

`--resources` 参数必须始终显式传递，不可省略。

| 范围 | 格式 |
|------|------|
| 所有资源 | `--resources '[{"resource":"_ALL"}]'` |
| 单个实例 | `--resources '[{"resource":"i-xxx"}]'` |
| 多个实例 | `--resources '[{"resource":"i-xxx"},{"resource":"i-yyy"}]'` |

此规则适用于**所有云产品**（ECS、RDS、SLB、OSS、MongoDB 等）。

---

## 4. Workspace 必填 (CMS 2.0)

所有 CMS 2.0 API 调用均**必须**提供 `workspace` 参数。

| 规则 | 详情 |
|------|------|
| 来源 | 必须使用 AskUser 工具向用户询问 |
| 自动构造 | **禁止** — 不得自行生成或猜测 workspace 值（如 'default'、'default-cms-{accountId}'） |
| 位置 | 包含在所有 CMS 2.0 API 的请求体中 |
| AskUser 失败 | 使用简化选项重试一次，然后报告错误并停止 — 不得使用编造的值继续执行 |

如果用户不清楚自己的 workspace，引导其在云监控控制台中查找。

---

## 5. Prometheus 必填参数 — cluster_id + workspace (CMS 2.0)

> **🔴 必须使用 AskUser 工具向用户询问 — 禁止猜测、禁止省略、禁止自动选择**

| 参数 | 映射 | 获取方式 |
|------|------|----------|
| `cluster_id` | `datasourceConfig.instanceId` | **必须通过 AskUser 向用户询问** — 即 Prometheus 实例 ID，用户可在 ARMS 控制台找到 |
| `workspace` | 请求体 `workspace` 字段 | **必须通过 AskUser 向用户询问** — 不可自行构造 |
| AskUser 失败 | — | 向用户报告错误并停止执行 |

**流程：**
1. 使用 AskUser 工具向用户询问 `cluster_id`（Prometheus 实例 ID）和 `workspace`
2. 将 `cluster_id` 用作 `datasourceConfig.instanceId`
3. 根据用户的监控目标（CPU、内存、Pod 重启等），生成对应的 PromQL
4. PromQL 为动态生成，不可硬编码

**CLI 占位符：** `{user_provided_cluster_id}`、`{user_provided_workspace}`

---

## 6. APM 必填参数 — service_id + workspace (CMS 2.0)

> **🔴 必须使用 AskUser 工具向用户询问 — 禁止猜测、禁止省略、禁止自动选择**

| 参数 | 映射 | 获取方式 |
|------|------|----------|
| `service_id` | `datasourceConfig.instanceId` + `queryConfig.serviceIdList[]` | **必须通过 AskUser 向用户询问** — APM 应用的唯一标识，用户可在 ARMS 控制台的应用列表中找到 |
| `workspace` | 请求体 `workspace` 字段 | **必须通过 AskUser 向用户询问** — 不可自行构造 |
| 从发现接口自动选择 | **禁止** — 发现类 API（如 ListTraceApps）仅供参考，最终选择必须由用户输入 |
| AskUser 失败 | — | 向用户报告错误并停止执行 |

**流程：**
1. 使用 AskUser 工具向用户询问 `service_id` 和 `workspace`
2. 将 `service_id` 同时用于 `datasourceConfig.instanceId` 和 `queryConfig.serviceIdList`
3. 不得编造 service_id 或在实际 API 调用中使用占位符值

**CLI 占位符：** `{user_provided_service_id}`、`{user_provided_workspace}`

---

## 7. 必需的 API 调用 (Shared)

### CMS 1.0

| 操作 | API | 用途 |
|------|-----|------|
| namespace 发现 | `DescribeProjectMeta` | 列出云产品 namespace（当产品不明确时） |
| 指标发现 | `DescribeMetricMetaList` | 获取 namespace 下的可用指标（必须调用） |
| 联系人查询 | `DescribeContactGroupList` | 查询已有的联系人组（必须调用） |
| 创建规则 | `PutResourceMetricRule` | 创建告警规则 |
| 查询规则 | `DescribeMetricRuleList` | 查询已有的告警规则 |

### CMS 2.0

| 操作 | API | 用途 |
|------|-----|------|
| Webhook 查询 | `ListAlertWebhooks` | 查询可用的 webhook 以配置通知 |
| 创建/更新规则 | `ManageAlertRules` | 创建或更新 Prometheus/APM/UModel 告警规则 |
| 查询规则 | `QueryAlertRules` | 按类型/名称/状态查询告警规则 |

> 所有 CMS 2.0 API 调用均需在请求体中包含 `workspace` 参数。API 版本：`2024-03-30`，Endpoint：`metrics.{regionId}.aliyuncs.com`。

---

## 8. 动态指标发现 (CMS 1.0)

> 详细内容参见 `step2-query-generation.md`。

关键要点：
1. 调用 `describe-project-meta` 列出所有可用的 namespace（当产品不明确时）
2. 调用 `describe-metric-meta-list --namespace <ns>` 获取可用指标
3. 将返回的指标与用户意图匹配（CPU、内存、磁盘、网络等）
4. 仅在 API 调用失败时回退到 `metrics.md`

---

## 9. CLI 命令超时 (Shared)

所有 `aliyun` CLI 命令必须设置超时以防止挂起：

| 操作类型 | 超时设置 | CMS 1.0 示例 | CMS 2.0 示例 |
|----------|----------|--------------|--------------|
| 查询（读取） | `--read-timeout 30` | describe、list、get | query-alert-rules、list-alert-webhooks |
| 写入（变更） | `--read-timeout 60` | put、create、update | manage-alert-rules |

如果命令在超时时间内未返回，重试一次后再报告失败。

---

## 10. 重复告警预检 (Shared)

创建告警规则前，检查是否已存在相同配置的规则：

**CMS 1.0：** 调用 `describe-metric-rule-list --namespace <ns> --metric-name <metric>` 检查是否有匹配的规则。

**CMS 2.0：** 调用 `query-alert-rules` 并使用适当的过滤条件（类型、名称模式）。

如果存在重复规则，通知用户并询问是跳过还是使用新名称创建。

---

## 11. 执行前强制确认 (Shared)

> CMS 1.0：详细内容参见 `step5-preview-execute.md`。
> CMS 2.0：详细内容参见 `cms2-step5-preview-execute.md`。

执行任何创建命令前，必须：
1. 向用户展示完整的配置摘要
2. 等待用户明确确认
3. 确认后方可执行 CLI 命令

**重要：即使在自动化/模拟环境中，也必须输出配置摘要并明确声明"等待用户确认"后才能继续。不得以自动化为由跳过此步骤。**

输出格式示例：
```
【配置摘要】
告警类型：APM/Prometheus
阈值：5%
严重级别：P2
通知方式：webhook

请确认以上配置是否正确（回复确认或修改意见）：
```

---

## 12. User-Agent 配置 (Shared)

所有 `aliyun` CLI 调用必须包含 User-Agent 请求头：

```bash
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-cms-alert-rule-create"
```

在执行任何命令前设置此环境变量。

---

## 13. 网络访问限制 (Shared)

本技能仅访问阿里云 OpenAPI 端点。允许的域名：

| 域名 | 用途 | 版本 |
|------|------|------|
| `cms.aliyuncs.com` | 云监控 API | CMS 1.0 |
| `metrics.{regionId}.aliyuncs.com` | 云监控 API | CMS 2.0 |
| `sts.aliyuncs.com` | STS API (GetCallerIdentity) | Shared |
| `ecs.aliyuncs.com` | ECS 实例查询 | CMS 1.0 |
| `rds.aliyuncs.com` | RDS 实例查询 | CMS 1.0 |
| `slb.aliyuncs.com` | SLB 实例查询 | CMS 1.0 |

不需要也不允许访问其他外部网络。

---

## 14. CLI 自助发现 (Shared)

当不确定 CLI 命令语法、参数或可用子命令时，使用 `--help`：

```bash
# CMS 1.0
aliyun cms --help
aliyun cms <command> --help

# CMS 2.0
aliyun cms manage-alert-rules --help
aliyun cms query-alert-rules --help
aliyun cms list-alert-webhooks --help
```

这是解决 CLI 不确定性的首选方式，而非猜测参数。

---

## 联系人组模糊匹配 (CMS 1.0)

当用户提到联系人组时，适用以下匹配规则：

| 用户输入 | 匹配策略 | 常见映射 |
|----------|----------|----------|
| "运维组" / "ops" | 包含/关键词匹配 | → `运维组`、`ops-alert-group`、`SRE-Team` |
| "基础设施组" | 包含/关键词匹配 | → `infrastructure`、`infrastructure-team` |
| "DBA团队" | 包含/关键词匹配 | → `DBA-Alert-Group`、`dba-team` |
| "网络组" | 包含/关键词匹配 | → `network-ops`、`network-sre` |
| 精确名称 | 直接匹配 | 如找到则使用精确名称 |

> 完整联系人处理流程另见 `step4-notification.md`。

---

## 严重级别

### CMS 1.0

| 级别 | 参数前缀 | 示例 |
|------|----------|------|
| 紧急（Critical） | `--escalations-critical-*` | `--escalations-critical-threshold 85` |
| 警告（Warn） | `--escalations-warn-*` | `--escalations-warn-threshold 99.9` |
| 信息（Info） | `--escalations-info-*` | `--escalations-info-threshold 50` |

### CMS 2.0

| 级别 | conditionConfig 值 | 说明 |
|------|-------------------|------|
| P1 | `P1` | 紧急（Critical） |
| P2 | `P2` | 警告（Warning） |
| P3 | `P3` | 信息（Info） |
| P4 | `P4` | 低优先级（Low） |

---

## API 版本隔离 (Shared)

> **🔴 强制要求：CMS 2.0 告警规则只能使用以下 API：**
> - **创建/更新/删除**：`ManageAlertRules`（CLI：`aliyun cms manage-alert-rules`）
> - **查询**：`QueryAlertRules`（CLI：`aliyun cms query-alert-rules`）
>
> **CMS 2.0 告警规则的创建或查询不允许使用任何其他 API。这是一条无例外的硬性约束。**
>
> **如果 `ManageAlertRules` 返回错误（如 400 Bad Request），不得回退到 ARMS API（`CreateOrUpdateAlertRule`、`CreatePrometheusAlertRule`）或任何其他 API。应向用户报告错误并停止执行。**

### CMS 2.0 允许使用的 API

| 操作 | API | CLI | 用途 |
|------|-----|-----|------|
| 创建/更新/删除规则 | `ManageAlertRules` | `aliyun cms manage-alert-rules` | CMS 2.0 规则管理的唯一 API |
| 查询规则 | `QueryAlertRules` | `aliyun cms query-alert-rules` | CMS 2.0 规则查询的唯一 API |
| 查询 webhook（通知） | `ListAlertWebhooks` | `aliyun cms list-alert-webhooks` | Webhook 通知配置（不用于规则创建/查询） |

### CMS 2.0 禁止使用的 API（在 CMS 2.0 工作流中）

| API | 类型 | 原因 |
|-----|------|------|
| `PutResourceMetricRule` | 创建 | 仅限 CMS 1.0 — 不支持 Prometheus/APM/UModel |
| `DescribeMetricRuleList` | 查询 | 仅限 CMS 1.0 — 无法查询 CMS 2.0 告警规则 |
| `CreateOrUpdateAlertRule` (ARMS) | 创建 | **禁止** — 这是 ARMS API，不是 CMS 2.0 |
| `CreatePrometheusAlertRule` (ARMS) | 创建 | **禁止** — 这是 ARMS API，不是 CMS 2.0 |
| `PutContact` | 联系人 | 仅限 CMS 1.0 — CMS 2.0 不使用联系人 |
| `PutContactGroup` | 联系人 | 仅限 CMS 1.0 — CMS 2.0 不使用联系人组 |
| `DescribeContactGroupList` | 联系人 | 仅限 CMS 1.0 — CMS 2.0 不使用联系人组 |
| `DescribeProjectMeta` | 发现 | 仅限 CMS 1.0 — 用于云产品 namespace 发现 |
| `DescribeMetricMetaList` | 发现 | 仅限 CMS 1.0 — 用于云产品指标发现 |

> ⚠️ 如果上述任何禁止 API 出现在 CMS 2.0 工作流中，属于**严重错误**，必须立即纠正。

### CMS 1.0 禁止使用的 API（在 CMS 1.0 工作流中）

| API | 类型 | 原因 |
|-----|------|------|
| `ManageAlertRules` | 创建 | 仅限 CMS 2.0 — 用于 Prometheus/APM/UModel 告警 |
| `QueryAlertRules` | 查询 | 仅限 CMS 2.0 — 无法查询 CMS 1.0 告警规则 |
| `ListAlertWebhooks` | 通知 | 仅限 CMS 2.0 — CMS 1.0 使用联系人组 |
