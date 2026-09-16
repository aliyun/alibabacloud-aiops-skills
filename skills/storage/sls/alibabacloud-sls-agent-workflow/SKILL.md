---
name: alibabacloud-sls-agent-workflow
description: Manage Alibaba Cloud Simple Log Service (SLS) resources and analyze logs. Use when users need to integrate applications through SLS SDKs, set up LoongCollector/Logtail collection, manage Projects, Logstores or indexes, query, analyze or visualize logs, or configure and diagnose alerts.
---

# Alibaba Cloud SLS Agent Workflow

## Global Rules

- Never request, read, or expose AccessKey ID or AccessKey Secret values — including in files, logs, and command arguments.
- If a selected skill is unavailable, read [Install specialist skills](references/install-specialist-skills.md) to install and load it before use.
- Use exact full skill names whenever naming, selecting, installing, or handing off to a specialist.

## Observability

Before this skill's first cloud call, read its [manifest](references/manifest.json) and use the top-level non-empty string `version` as `{skill-version}`. Stop and report a missing or invalid file/version; never guess it.

Generate a fresh random 32-character lowercase hexadecimal `{session-id}` for this skill in the conversation:

```bash
python3 -c 'import secrets; print(secrets.token_hex(16))'
```

Reuse this session ID for subsequent operations, pagination, and retries. Every Alibaba Cloud API command and request-only dry run performed by this skill **MUST** include:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sls-agent-workflow/{session-id} skill-version/{skill-version}"
```

Set `SLS_WORKFLOW_USER_AGENT` to the resolved value and pass it double-quoted. This applies to direct CLI calls in the examples, including `create-project`, `create-log-store`, and `put-json-logs`, and to API calls made through scripts or helpers. Local `configure`, `plugin`, `version`, and help commands are exempt. Do not send literal placeholders, credentials, or personal identifiers.

When switching to a specialist, prefer to follow its own observability rules and use its own skill identity, manifest version, prefer to reuse the session ID above.

## SLS resources and relationships

Logs are written to a Logstore within a Project using LoongCollector, an SDK, or the CLI, and can then be queried using an SDK or the CLI with suitable index settings. Alert rules and notification objects are managed through the CLI by the alerting specialist.

| Concept | Role and relationship |
| --- | --- |
| Project | Regional resource container for Logstores, collection configs, machine groups, and alert rules. |
| Logstore | Stores logs within a Project; the destination for writes and collection, and the data source for queries. |
| Index | Logstore configuration for indexed search and analytics. Field names, types, and analytics settings must match the query workload. Creating or updating an index affects only logs written after the configuration takes effect. |
| Query | Reads a Logstore over a time range using search, SQL, or SPL in SLS query syntax. |
| LoongCollector / iLogtail | High-performance log collector for Linux and Windows; runs on hosts to collect and process logs according to collection configs and send them to SLS. |
| Collection config | Defines a collector's inputs, parsing, and destination Logstore; applying it to a machine group selects the hosts that run it. |
| Machine group | Identifies collector hosts and exposes their heartbeat status. Groups and collection configs can have multiple bindings. |
| Alert rule | Belongs to a Project and evaluates configured queries on a schedule. Its data sources can be in a different Project; conditions determine whether it fires. |

## Specialist catalog

| Specialist skill | Capabilities | When to use | When not to use |
| --- | --- | --- | --- |
| `alibabacloud-sls-sdk-guidance` | SDK selection, installation, and usage for SLS resource management and log operations; Producer, Consumer, and Appender integration | Integrate applications or logging frameworks with SLS; use SDKs to manage SLS resources or work with logs programmatically | Prefer CLI for one-shot or simple standalone resource operations. Prefer LoongCollector for collecting log files from many different processes on a host. Collector installation/configuration and query-language work without SDK integration belong to their respective specialists. |
| `alibabacloud-sls-index-config-management` | Independent Logstore index inspection, generation, creation, update, deletion, and optimization | Create, update, or optimize index configurations | A Pipeline or collection-field change requires a coupled index change: keep both with `alibabacloud-loongcollector-ops` |
| `alibabacloud-sls-query` | Index search, SQL, and SPL authoring, explanation, execution, optimization, and troubleshooting | Need a precise statement or reproducible result, including writing only the SQL for an alert; diagnose query syntax, filters, or time ranges | Tasks unrelated to search, SQL, or SPL statements. |
| `alibabacloud-sls-data-agent` | Online analysis agent with long-lived sessions, dependent on the StarOps digital employee; supports data acquisition, multi-step analysis, and visualizations | Only when the user explicitly requests Data Agent to analyze data | Do not trigger for general log analysis, anomaly investigation, or chart requests without an explicit request to use Data Agent. |
| `alibabacloud-sls-alerting` | SLS alert rule and notification management; alert history and alert event diagnosis | Explain or manage alert rules, schedules, thresholds, enable/disable, mute/unmute, recipients, channels, policies, and templates; investigate triggering, notification issues, causes, frequency, or duration using available evidence | SQL-only authoring; general anomaly exploration; collector troubleshooting without SLS alert rule management or alert event diagnosis; generic messaging; alerts from other services such as CloudMonitor/Prometheus |
| `alibabacloud-loongcollector-ops` | LoongCollector installation/upgrade/use on ECS, Linux hosts, ACK, and self-managed Kubernetes; collection onboarding, Pipeline configs, machine groups/bindings, coupled indexes, SLS Lens, and basic diagnosis | Install or upgrade LoongCollector; collect logs; manage logstore collection configs and machine groups; query SLS Lens; diagnose collector no-data or heartbeat issues. | Independent index management not coupled to collection changes; in-application SDK or logging-framework integration, such as Log4j2 Appender. |

## End-to-end examples

Read the matching example for a step-by-step overview of the scenarios below. Adapt the steps to existing resources and the user's goal; use the selected skills and CLI help for operation details.

| Example | Read when |
| --- | --- |
| [Write and query logs](references/examples/write-and-query-logs.md) | Create project and logstore, configure indexes, write sample logs, and query them; or understand why written logs are not queryable. |
| [Collection to alert](references/examples/collection-to-alert.md) | Collect host logs using LoongCollector, including Project and Logstore creation, index configuration, machine group and collection config setup, then configure alerts. |

## References

- [RAM policies](references/ram-policies.md): permissions and resource scopes for direct CLI calls; read when checking access or handling permission errors.
- [Install specialist skills](references/install-specialist-skills.md): install and load a required skill that is unavailable.
- [Write and query logs](references/examples/write-and-query-logs.md): complete example of Project, Logstore, index, log writes, and queries.
- [Collection to alert](references/examples/collection-to-alert.md): complete example of collector setup, collection bindings, query validation, and alert delivery.
