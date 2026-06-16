---
name: alibabacloud-cms-manage
description: |
  Entry skill for the aliyun CLI distribution of CloudMonitor (CMS).
  Use when the user mentions aliyun cms2, CloudMonitor, CMS commands,
  or any CMS module operation such as Integration Policy/Center, APM, RUM,
  Prometheus Service, Recording rule, alert rule, alert template, alert history,
  event hub, SLS event, PromQL, cloud resource, service observability,
  monitoring onboarding, metric query, etc.
license: Apache-2.0
compatibility: aliyun-cli>=3.3.15
metadata:
  domain: aiops
  owner: cms
  contact: cms@alibaba-inc.com
---

# CMS CLI — `aliyun cms2`

## Prerequisite Check

1. **Check `aliyun` exists** — `which aliyun` (macOS/Linux) or `where aliyun` (Windows).
    - Not found → ask the user to install the aliyun CLI first: <https://help.aliyun.com/document_detail/121541.html>. Stop and wait.

2. **Check CLI version** — run `aliyun version`. Minimum required: **3.3.15** (see `compatibility` in frontmatter).

   > ⚠️ Compare version segments as **integers** (semver): 3.3.4 < 3.3.15 because 4 < 15.
   > Shell verification: `printf '%s\n' "3.3.15" "$(aliyun version)" | sort -V | head -1`
   > If the output equals the current version, the requirement is NOT met.

    - Version OK → go to step 3.
    - Version too old or unrecognized →
        1. Run `aliyun upgrade --help` to test whether the `upgrade` subcommand exists.
            - Available → run `aliyun upgrade -y` to update to the latest version automatically, then re-check `aliyun version`.
        2. If `upgrade` not available → ask the user to upgrade manually following the official guide: <https://help.aliyun.com/zh/cli/update-cli>. Wait for the user to confirm the upgrade is complete, then re-check `aliyun version`.
        3. If upgrade succeeded → go to step 3.
        4. If upgrade failed → ask the user to upgrade manually: <https://help.aliyun.com/zh/cli/update-cli>. Stop and exit.

3. **Check `cms2` plugin** — run `aliyun cms2 --help`.
    - Help output OK → continue to **Credentials**.
    - `unknown command` / missing → **stop immediately**, output the error report below (append CLI version, OS, and error message), and make **no further CLI calls**.

---

## Credentials

`aliyun cms2` reuses the aliyun CLI credential system (`aliyun configure`).
Use `--profile <name>` to switch profiles.

## Observability

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once per session...

For every aliyun cms2 command, append:
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cms-manage/{session-id}"

## Global Conventions

**Hard constraint**: fallback to `aliyun cms`, other API versions, or any workaround is strictly prohibited.

> **Run `aliyun cms2 <command> [subcommand] --help` before first use of a subcommand in a session** to get the full flag list and examples. Once the help for the same subcommand has been read in the current session and the command shape has not changed, reuse that knowledge instead of repeating the help call.

- **Prefer `-o text`** (default) to reduce token consumption for list/get; use `-o json` only when indented JSON is needed.
- **Before onboarding concrete resource IDs**, verify them with `entity query --source CloudResource`; do not rely on ID shape alone.
- **`entity query` default time range**: when the user does not specify `--from`/`--to`, default to the last 7 days (`--from` = now − 7d, `--to` = now, both as Unix seconds).
- **CloudResource queries default to all regions**: for `entity query --source CloudResource`, do not derive regions from workspace, policy, CLI defaults, prior commands, or existing policy regions. If the user does not explicitly limit the query to cloud resources in specific regions, omit the region parameter so cloud resources from all regions are queried. Only add a region parameter when the user explicitly provides a region constraint. State the final region coverage in the response.
- **Structured choice presentation**: when the active runtime exposes a structured user-input tool (for example `request_user_input`, select, form, or equivalent), use it for mutually exclusive user choices such as addon selection, workspace selection, resource scope mode, metric candidate selection, and yes/no confirmations. Keep each option decision-useful: concise label plus one sentence describing impact or tradeoff. If the structured tool is unavailable, supports too few choices, or is not callable in the current mode, fall back to a numbered plain-text list and ask the user to reply with the number or exact name. Never claim a select/form was shown unless the tool call actually succeeded.
- **Human confirmation required for writes and high-impact creates**: before any command that creates or changes cloud-side state (`create`, `update`, `delete`, `patch`, `start`, `stop`, etc.), show a concise confirmation summary and the exact command, ask whether the user confirms execution, and wait for a clear affirmative answer. The summary must include the operation, target resource identifiers, expected impact, and notable risks or irreversible effects when applicable. Do not require an exact phrase or long confirmation text; a clear affirmative answer such as "yes", "confirm", "proceed", or "确认" is sufficient approval. Skip confirmation only for dry-run, preview-only, or read-equivalent creates with no cloud-side impact; if uncertain, require confirmation.
- **Uncertain parameters must be explicitly answered by the user**: for any parameter whose value is not explicitly provided or cannot be reliably determined (e.g. `region`/`regionId`, workspace, policy, `resourceGroup`, tag, resource scope, `addonName`, resource type, cloud product/service name, onboarding configuration options, etc.), ask the user for a clear answer before proceeding. The exception is `entity query --source CloudResource` region handling: when the user does not explicitly limit the query to specific regions, omit the region parameter and query all regions. Never fabricate, guess, infer from defaults/history, or arbitrarily choose one value.
- **Name-to-ID lookup must match exactly**: when looking up a region ID, workspace ID, integration policy ID, resource group ID, resource type value, or cloud product/service name/code by name, if no exact match is found in the query results, do **not** silently pick an arbitrary value as a substitute. Instead, report the mismatch to the user and ask them to confirm or provide the correct value.
- **Workspace must be explicitly selected**: before any integration policy or addon release creation, if the user did not explicitly provide a workspace name, list candidate workspaces and wait for the user to choose one. The common name pattern `default-cms-{userId}-{regionId}` is only a discovery hint and is never permission to auto-select that workspace.

## Pagination & Query Failure Handling

- **Truncated results must not be treated as complete**: when a list query response indicates truncation (e.g. `truncated=true`, or returned count < total count), do **not** conclude that an item does not exist based on the partial results alone. Either use filters/search parameters (check `--help` for available options like `--search`, `--name`, `--keyword`, etc.) to narrow the query, or paginate through all results before concluding absence.
- **Paginate to completion**: for every `list` command that supports `--next-token`, keep querying until the result is complete. Completeness is reached when there is no `nextToken`, or when the accumulated item count is greater than or equal to `totalCount`. Do not trust the first page as complete when `totalCount`, `truncated`, or `nextToken` indicates more data.
- **Accumulated count reaches totalCount**: if accumulated item count is already greater than or equal to `totalCount`, stop pagination even if `nextToken` is still non-empty or `truncated=true`; treat `totalCount` as the stronger completion signal and ignore the extra pagination signals.
- **Empty page with satisfied totalCount**: if a page returns no items and the accumulated item count is already greater than or equal to `totalCount`, stop even if a `nextToken` is still present. This pattern can appear in recently changed list results.
- **Token loop protection**: track seen `nextToken` values; stop if a token repeats and report the result as partial or token-anomalous.
- **Page limit**: use a page limit for all pagination loops. A default limit of 20 pages is acceptable; if reached, report that results are partial.
- **Transient query failure**: if a read-only status query fails with a transient server-side error such as `DEADLINE_EXCEEDED` or timeout, retry once before classifying the result.
- **Persistent query failure**: if the retry still fails, mark that dimension as `Unknown` / `QueryFailed`; do not treat query failure as either healthy or unhealthy.

## Error Handling

Error codes and actions are listed in `aliyun cms2 --help`. Additional tips:

- `InvalidJSON` usually means malformed `--body`; validate with `jq . <<<'<value>'` before passing to the CLI.
- `--body and stdin are mutually exclusive; specify only one` — means both `--body` (or `--file`) and stdin data were provided. Fix: keep only one input source. In agent/CI environments where stdin may be a pipe, append `< /dev/null` to the command to ensure stdin is empty.

## Output Language and Terminology

- User-facing explanations, analysis, recommendations, summaries, and conclusions MUST be written in Simplified Chinese.
- Use the Glossary terms below for all user-facing prose. Do not leave mapped domain terms in English when a Chinese term exists.
- CLI command names, flags, API paths, JSON field names, enum values, resource IDs, metric names, and log/error messages MUST remain verbatim English/code.
- On first mention, write mapped terms as `中文（English）` only when it helps disambiguate; after that, use the Chinese term only.
- Before sending a final answer, scan the response for mapped English terms and replace them with the Glossary Chinese term unless they are inside code, commands, JSON fields, IDs, or quoted CLI output.

Examples:
- Good: `接入配置（AddonRelease，CLI 命令为 addon-release）`
- Good: `查询接入配置状态：aliyun cms2 integration addon-release list ...`
- Bad: `all releases are Ready`
- Better: `所有接入配置均 Ready`

## Glossary

| English                                | 中文              |
|----------------------------------------|-----------------|
| Cloud Monitor / CMS                    | 云监控             |
| Workspace                              | 工作空间            |
| Application Monitoring / APM           | 应用监控            |
| RUM                                    | 用户体验监控          |
| Synthetic Monitoring / Synthetic       | 云拨测             |
| CloudResource                          | 云资源             |
| EntityStore                            | 实体仓库            |
| Entity                                 | 实体              |
| Integration Policy / policy            | 接入策略            |
| Addon / addon                          | 组件              |
| Addon Catalog                          | 组件目录            |
| AddonRelease / addon release / release | 接入配置            |
| Collector                              | 采集器             |
| Prometheus View                        | Prometheus 聚合视图 |
| AggTaskGroup                           | 聚合任务            |
| Delivery Task                          | 数据投递任务          |
| Alert Rule                             | 告警规则            |
| Alert Template                         | 告警模板            |
| Alert History                          | 告警历史            |
| Notification Channel                   | 通知渠道            |
| Contact                                | 联系人             |
| Event Hub                              | 事件中心            |
| Metric Meta                            | 指标元数据           |
| ClusterCollector                       | 集群采集器           |
| NodeCollector                          | 节点采集器           |
| Grafana workspace                      | Grafana工作区      |

## Metadata Query Mapping

| What You Need | How to Get It |
|--------------|---------------|
| **Resource metadata & instance details** (entityType, scopes, ID, region, tags, etc.) | `entity query --source CloudResource` (raw cloud resource; infer metadata from properties) |
| **Entity data ingested into a workspace** (workspace-scoped; proves past ingestion, not current onboarding) | `entity query --source EntityStore` |
| **Authoritative addon onboarding status** | For CS/ACK bind-resource scenarios: `integration policy list --bind-resource-id <id>` plus `integration addon-release list --policy-id <policyId>`; for CS/ECS also check collector status (see [Step 4](references/integration.md#determining-onboarding--monitoring-status)). For Cloud sub-types such as RDS/SLB/ALB: `integration policy list --addon-name <addonName>` plus `integration addon-release list --policy-id <policyId> --addon-name <addonName>` and evaluate the release scope. |
| **Policy-scoped Kubernetes resources** | Use `integration resource list --policy-id <policyId> --kind <Kind>`; for Namespace under the first policy, use the first `policyId` from the current `integration policy list` result. Never use `entity query --source CloudResource --entity-type acs.k8s.namespace` for this. |
| **Metric business metadata** (namespaces & product codes via `meta namespaces`; metric name, type, unit, dimensions via `meta metrics`) | `meta namespaces` / `meta metrics` |
| **Prometheus labels, values & series inspection** | `metric promql labels` / `label-values` / `series` |
| **Prometheus instance by policy** | `aliyun cms2 integration storage list --policy-id <policy-id> --storage-type Prometheus` |

## Module Routing

| User Intent Keywords                                                                                                                                                                                                                                                                                                   | Commands | Module |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|--------|
| onboarding, monitoring addon, policy, integration, addon release, integration resource, Kubernetes resource list, Namespace resources under policy, resources managed by policy                                                                                                                          | `integration` `integration resource` | [references/integration.md](references/integration.md) |
| workspace, workspace create, workspace get, workspace list, workspace update, workspace delete                                                                                                                                                                                                                         | `workspace` | `aliyun cms2 workspace --help` |
| entity, entity query, CloudResource, EntityStore, cloud resource query, entity store query, resource metadata, instance details                                                                                                                                                                                        | `entity query` | `aliyun cms2 entity --help` |
| Prometheus instance, Prometheus view, recordingRule, recording rule, AggTaskGroup                                                                                                                                                                                                                                      | `prometheus instance` `prometheus view` `prometheus recording-rule` | `aliyun cms2 prometheus --help` |
| meta, metric metadata, product code, meta-format                                                                                                                                                                                                                                           | `meta metrics` `meta namespaces` | `aliyun cms2 meta --help` |
| metric, metric query, basic metrics, PromQL, promql query, label values, series                                                                                                                                                                                                                                        | `metric basic` `metric promql` | `aliyun cms2 metric --help` |
| alert, rule, alert rule, alert template, alert history, patch, create rule, manage rule                                                                                                                                                                                                                                | `alert rule` `alert template` `alert history` | [references/alerting.md](references/alerting.md) |
| APM measureCode, group/filter/groupBy, baseUnit/displayUnit                                                                                                                                                                                                                                                            | `alert rule` (APM type) | [references/apm-metrics.md](references/apm-metrics.md) |
| UModel metricSet, K8s pod metric, entity-based alert                                                                                                                                                                                                                                                                   | `alert rule` (UModel type) | [references/umodel-metrics.md](references/umodel-metrics.md) |
| notification, contact, robot, webhook, notification recipients, dingTalk, bots, lark, weChat work                                                                                                                                                                                                                      | `notification-channel contact` `notification-channel robot` `notification-channel webhook` | [references/alerting.md](references/alerting.md) |
| event, event-hub, alert event, SLS event, incident                                                                                                                                                                                                                                                                     | `event-hub` | [references/event-hub.md](references/event-hub.md) |
| Grafana, Grafana workspace, managed Grafana instance, create/query/update/delete Grafana workspace                                                                                                                                                                                                                     | `grafana workspace` | `aliyun cms2 grafana workspace --help` |
| APM, application monitoring, agent install, Java agent, Golang agent, Python agent, Node.js agent, PHP agent, .NET agent, ack-onepilot, OpenTelemetry onboarding, K8s/ACK/ACS container onboarding, ECS host application onboarding, LicenseKey, proprietary agent, instgo, aliyun-bootstrap, probe setup, apm onboarding | `apm service` `apm configuration` | [references/apm.md](references/apm.md) |
| AI observability, Dify, LangChain, LangGraph, DashScope, AgentScope, OpenAI, Coze, OpenClaw, CoPaw, Hermes, LLM monitoring, AI tracing, AI agent monitoring, custom instrumentation                                                                                                                                    | `apm service` `apm configuration` `integration addon` | [references/ai.md](references/ai.md) |
| RUM, Real User Monitoring, User Experience Monitoring, frontend monitoring, web monitoring, H5, mobile app monitoring, Android crash, iOS crash, JS error, page performance, miniapp monitoring, create RUM app, RUM SDK, pid, serviceId, endpoint                                                                     | `rum service` `rum configuration` | [references/rum.md](references/rum.md) |
| resource group query                                                                                                                                                                                                                                                                                                   | `resource-group` | `aliyun cms2 resource-group --help` |

Commands not listed above — see `aliyun cms2 --help`.
