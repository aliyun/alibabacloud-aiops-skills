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

> **Once per session**: perform this prerequisite check only on the **first** invocation of this skill in a conversation. If all checks already passed earlier in the same session, skip directly to the relevant module.

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

Local utility commands (e.g. `version`, `configure`, `plugin`, `--help`) do not support this flag and are excluded.

## Global Conventions

**Hard constraint**: fallback to `aliyun cms`, other API versions, or any workaround is strictly prohibited.

> **Run `aliyun cms2 <command> [subcommand] --help` before first use of a subcommand in a session** to get the full flag list and examples. Once the help for the same subcommand has been read in the current session and the command shape has not changed, reuse that knowledge instead of repeating the help call.

- **Prefer `-o text`** (default) to reduce token consumption for list/get; use `-o json` only when the output is parsed field by field rather than read.
- **Addon-release `values`**: expand each field's `fieldPath` into nested JSON as specified in [Addon Values Defaults](references/integration-common.md#addon-values-defaults-hard-requirement). Do not write a dotted `fieldPath` as one literal key. How to pick `--env-type`, where child fields sit on create vs update, and when a subset is (or is not) a valid body, are in that section.
- **Region parameter required for mutating and detail commands**: unless otherwise specified by a module-specific rule, all `create`, `update`, `delete`, and single-resource `get`/detail commands MUST include the `--region` parameter so the request is routed to the correct backend OpenAPI endpoint. Omitting `--region` on these commands may cause routing failures or operate against an unintended region. This does not apply to `list`/query commands that intentionally span multiple regions (e.g. `entity query --source CloudResource` all-region queries). Requiring the flag is not permission to choose its value — resolve it per [Region Confirmation Gate](#region-confirmation-gate-hard-requirement).
- **Structured choice presentation**: use structured presentation to show choices, collect the answer, and wait for the user to decide on mutually exclusive choices.
    - Use the active runtime's structured user-input tool when available (for example `request_user_input`, select, form, or equivalent).
    - Keep each option decision-useful: concise label plus one sentence describing impact or tradeoff. Each option must show the available Chinese or English display name, description or alias, and relevant stable identifier/code. If a field is unavailable in the query result, state it as unknown instead of omitting all context or showing only a bare ID.
    - Put any recommended value directly in the option label or confirmation line (for example `(Recommended)` or `Recommended:`); do not list recommendations separately from the choices the user must confirm.
    - Recommend a value only when evidence, deterministic defaults, lowest blast radius, or the safest next discovery step supports it; otherwise say no recommendation is available and ask for an exact value.
    - If the structured tool is unavailable, supports too few choices, or is not callable, fall back to a numbered plain-text list using the same inline recommendation format. Never claim a select/form was shown unless the tool call actually succeeded. Recommendations are advisory only and do not permit cloud-side writes unless another rule permits defaulting or the user confirms.
- **Human confirmation required for writes and high-impact creates**: before any command that creates or changes cloud-side state (`create`, `update`, `delete`, `patch`, `start`, `stop`, etc.), show a concise confirmation summary and the exact command, ask whether the user confirms execution, and wait for a clear affirmative answer. The summary must include the operation, target resource identifiers, expected impact, and notable risks or irreversible effects when applicable. Do not require an exact phrase or long confirmation text; a clear affirmative answer such as "yes", "confirm", "proceed", or "确认" is sufficient approval. Skip confirmation only for dry-run, preview-only, or read-equivalent creates with no cloud-side impact; if uncertain, require confirmation.
- **Uncertain parameters must be explicitly answered by the user**: for any parameter whose value is not explicitly provided or cannot be reliably determined (e.g. `region`/`regionId`, workspace, policy, `resourceGroup`, tag, resource scope, `addon`/`addonName`, resource type, cloud product/service name, onboarding configuration options, etc.), ask the user for a clear answer before proceeding. Never fabricate, guess, infer from defaults/history, or arbitrarily choose one value. A module-specific reference may define narrow exceptions — for the integration module they are listed in [references/integration-common.md](references/integration-common.md#general-conventions). Changing an existing addon release's settings is an unrehearsable write: follow [Addon Release Config Update](references/integration-common.md#addon-release-config-update-hard-requirement).
- **A discovery query is not an answer**: a read command (`workspace list`, `entity query`, `policy list`, `sts get-caller-identity`, etc.) only builds the candidate set you present, and its output never becomes the user's answer — not when it returns a single candidate, not when a naming convention makes the value derivable, and not when an earlier turn of the session used one. "Reliably determined" means the user's own words or the resource they named pinned the value, not that the query happened to be unambiguous.
- **Name-to-ID lookup must match exactly**: when looking up a region ID, workspace ID, integration policy ID, resource group ID, resource type value, or cloud product/service name/code by name, if no exact match is found in the query results, do **not** silently pick an arbitrary value as a substitute. Instead, report the mismatch to the user and ask them to confirm or provide the correct value.

### Region Confirmation Gate (Hard Requirement)

Applies to **every** module and to every command that takes `--region` or a `region`/`regionId` body field. Settle the region **before** the workspace, since workspace verification is region-scoped. There are exactly three legitimate sources for the value:

1. The user stated it in the current conversation.
2. The user picked it from a candidate list you presented, and you waited for that answer before running the next command.
3. The environment supplied it as runtime context (e.g. the console session the skill runs inside). Say which region you are operating on before using it.

Anything else is a violation, and the one that slips through is a region you never consciously chose: `--region` taken from the CLI profile / `aliyun configure` default, or left off a command that requires it so the CLI supplies that default. A value that arrives without you selecting it is still none of the three sources above.

Until the user answers, present the region as a choice per [Structured choice presentation](#global-conventions) and stop. Neither the `cn-hangzhou` of the docs and examples nor a region you merely stated in your narration ("Region: cn-hangzhou") is an answer.

A read-only inventory query may instead follow its module's own region-scope rule (e.g. [CloudResource Query Region Handling](references/integration-common.md#cloudresource-query-region-handling)); that rule never authorizes a self-chosen `--region` on a mutating or detail command.

### Workspace Confirmation Gate (Hard Requirement)

Applies to **every** module and to every command that takes `--workspace` or a `workspace` body field. There are exactly three legitimate sources for the value:

1. The user stated it in the current conversation. Verify it exists in the target region by exact `workspaceName` match; no exact match → report and ask, never substitute a near match.
2. The user picked it from a candidate list you presented, and you waited for that answer before running the next command.
3. The environment supplied it as runtime context (e.g. the console session the skill runs inside) and its region matches the target region. Say which workspace you are operating on before using it.

Anything else is a violation: adopting the single row `aliyun cms2 workspace list` returned, picking the `default-cms-{userId}-{regionId}` entry because it looks like the account default, assembling that name from `aliyun sts get-caller-identity` plus a region, or reusing a workspace from an earlier unrelated request in the same session.

So `aliyun cms2 workspace list` remains the right way to gather candidates — only consuming its output instead of presenting it is wrong. Mark the best candidate `(Recommended)` inside the option per [Structured choice presentation](#global-conventions), then stop and wait.

Module references do not loosen this. Where one gives `default-cms-{userId}-{regionId}` as the workspace's "default format" or builds it from an account ID and a region, that describes how the account's default workspace is named — it is the candidate to recommend, never permission to skip the question.

## Pagination & Query Failure Handling

- **Truncated results must not be treated as complete**: when a list query response indicates truncation (e.g. `truncated=true`, or returned count < total count), do **not** conclude that an item does not exist based on the partial results alone. Either use filters/search parameters (check `--help` for available options like `--search`, `--name`, `--keyword`, etc.) to narrow the query, or paginate through all results before concluding absence.
- **Paginate to completion**: for every `list` command that supports `--next-token`, keep querying until the result is complete. Completeness is reached when there is no `nextToken`, or when the accumulated item count is greater than or equal to `totalCount`. Do not trust the first page as complete when `totalCount`, `truncated`, or `nextToken` indicates more data.
- **Page size on paginated `list`**: when the command accepts `--max-results`, pass `100` and then paginate to completion. The 20-page cap times the CLI default page size can truncate a large policy list.
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

- Write user-facing explanations, analysis, recommendations, summaries, and conclusions in the user's language; default to Simplified Chinese when that language is unclear or mixed. Follow a mid-conversation switch from that point on, and let an explicit instruction about output language override both.
- Question prompts, option labels, table headers, and reports are user-facing text too — phrase them in the answer language even where a reference file spells them out in one language.
- CLI command names, flags, API paths, JSON field names, enum values, resource IDs, metric names, and log/error messages MUST remain verbatim English/code, whatever the answer language.
- Answering in English: use the Glossary's English column as the canonical vocabulary rather than inventing synonyms.
- Answering in Chinese: use the Glossary's Chinese terms in all prose, never leaving a mapped term in English. Write `中文（English）` on first mention only when it disambiguates, then the Chinese term alone. Before sending, scan for mapped English terms and replace them, except inside code, commands, JSON fields, IDs, or quoted CLI output.

Examples (Chinese answers):
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
| **Metric business metadata** (namespaces & product codes via `meta namespaces`; metric name, type, unit, dimensions via `meta metrics`) | `meta namespaces` / `meta metrics` |
| **Prometheus labels, values & series inspection** | `metric promql labels` / `label-values` / `series` |

Integration-module lookups (resource metadata, onboarding status, policy-scoped Kubernetes resources, Prometheus instance by policy) live in [references/integration-common.md](references/integration-common.md#metadata-query-mapping).

## Module Routing

| User Intent Keywords                                                                                                                                                                                                                                                                                                   | Commands | Module |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|--------|
| onboarding, monitoring addon, policy, integration, addon release, integration resource, Kubernetes resource list, Namespace resources under policy, resources managed by policy, teardown, offboarding — **common rules, load for every onboarding operation**                                                          | `integration` `integration resource` | [references/integration-common.md](references/integration-common.md) |
| container onboarding, ACK/ACS/ASI cluster onboarding, cluster fleet audit, which clusters are not onboarded                                                                                                                                                                                                            | `integration` `entity query` | [references/cs-onboarding.md](references/cs-onboarding.md) (+ integration-common.md) |
| ECS host onboarding, ECS fleet audit, NodeCollector                                                                                                                                                                                                                                                                    | `integration` `entity query` | [references/ecs-onboarding.md](references/ecs-onboarding.md) (+ integration-common.md) |
| cloud service onboarding, RDS/SLB/ALB/Redis/MongoDB/PolarDB onboarding, cloud resource fleet audit                                                                                                                                                                                                                     | `integration` `entity query` | [references/cloud-onboarding.md](references/cloud-onboarding.md) (+ integration-common.md) |
| batch cloud service metric onboarding, batch onboarding, cloud-batch-metrics                                                                                                                                                                                                                                           | `integration` `meta` `entity query` | [references/batch-onboarding-workflow.md](references/batch-onboarding-workflow.md) (+ integration-common.md) |
| integration policy diagnosis, health-check, troubleshoot policy, scrape config, ServiceMonitor/PodMonitor/custom collection diagnosis, job target                                                                                                                                                                       | `integration check-scrape-config` `integration job-target` `integration check-collector-target` | [references/integration-diagnosis.md](references/integration-diagnosis.md) |
| Prometheus view, Prometheus aggregation view, create Prometheus aggregation view, Prometheus view create, Prometheus aggregation view diagnosis, Prometheus aggregation view health check, sub-instance status                                                                                                                                 | `prometheus view` | [references/prometheus-management.md](references/prometheus-management.md) |
| workspace, workspace create, workspace get, workspace list, workspace update, workspace delete                                                                                                                                                                                                                         | `workspace` | `aliyun cms2 workspace --help` |
| entity, entity query, CloudResource, EntityStore, cloud resource query, entity store query, resource metadata, instance details                                                                                                                                                                                        | `entity query` | `aliyun cms2 entity --help` |
| Prometheus instance, recordingRule, recording rule, AggTaskGroup                                                                                                                                                                                                                                      | `prometheus instance` `prometheus recording-rule` | `aliyun cms2 prometheus --help` |
| meta, metric metadata, product code, meta-format                                                                                                                                                                                                                                           | `meta metrics` `meta namespaces` | `aliyun cms2 meta --help` |
| metric, metric query, basic metrics, PromQL, promql query, label values, series                                                                                                                                                                                                                                        | `metric basic` `metric promql` | `aliyun cms2 metric --help` |
| alert, rule, alert rule, alert template, alert history, patch, create rule, manage rule                                                                                                                                                                                                                                | `alert rule` `alert template` `alert history` | [references/alerting.md](references/alerting.md) |
| APM measureCode, group/filter/groupBy, baseUnit/displayUnit                                                                                                                                                                                                                                                            | `alert rule` (APM type) | [references/apm-metrics.md](references/apm-metrics.md) |
| UModel metricSet, K8s pod metric, entity-based alert                                                                                                                                                                                                                                                                   | `alert rule` (UModel type) | [references/umodel-metrics.md](references/umodel-metrics.md) |
| notification, contact, robot, webhook, notification recipients, dingTalk, bots, lark, weChat work                                                                                                                                                                                                                      | `notification-channel contact` `notification-channel robot` `notification-channel webhook` | [references/alerting.md](references/alerting.md) |
| event, event-hub, alert event, SLS event, incident                                                                                                                                                                                                                                                                     | `event-hub` | [references/event-hub.md](references/event-hub.md) |
| Grafana, Grafana workspace, managed Grafana instance, create/query/update/delete Grafana workspace                                                                                                                                                                                                                     | `grafana workspace` | `aliyun cms2 grafana workspace --help` |
| Grafana dashboard authoring, dashboard JSON, panel, PromQL panel, dashboard variables, data source placeholder                                                                                                                                                                                                         | `meta metrics` `metric promql` `integration storage` | [references/grafana-dashboard-rules.md](references/grafana-dashboard-rules.md) |
| APM, application monitoring, agent install, Java agent, Golang agent, Python agent, Node.js agent, PHP agent, .NET agent, ack-onepilot, OpenTelemetry onboarding, K8s/ACK/ACS container onboarding, ECS host application onboarding, LicenseKey, proprietary agent, instgo, aliyun-bootstrap, probe setup, apm onboarding | `apm service` `apm configuration` | [references/apm.md](references/apm.md) |
| AI observability, Dify, LangChain, LangGraph, DashScope, AgentScope, OpenAI, Coze, OpenClaw, CoPaw, Hermes, LLM monitoring, AI tracing, AI agent monitoring, custom instrumentation                                                                                                                                    | `apm service` `apm configuration` `integration addon` | [references/ai.md](references/ai.md) |
| RUM, Real User Monitoring, User Experience Monitoring, frontend monitoring, web monitoring, H5, mobile app monitoring, Android crash, iOS crash, JS error, page performance, miniapp monitoring, create RUM app, RUM SDK, pid, serviceId, endpoint                                                                     | `rum service` `rum configuration` | [references/rum.md](references/rum.md) |
| resource group query                                                                                                                                                                                                                                                                                                   | `resource-group` | `aliyun cms2 resource-group --help` |

Commands not listed above — see `aliyun cms2 --help`.
