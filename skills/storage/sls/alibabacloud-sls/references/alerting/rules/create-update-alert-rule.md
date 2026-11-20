# Create or update an alert rule

Use this operation to create a rule or change its behavior. To inspect, enable,
disable, or delete a rule, use [rule management](manage-alert-rules.md).
For temporary notification pauses, see [mute or unmute a rule](manage-alert-rules.md#mute-or-unmute).

## Updates

Rule updates replace the schedule and configuration. Comparing a diff against the
current rule helps identify unintended changes, including omitted optional sinks.

## Choose the rule settings

The request combines identity fields, `schedule`, and `configuration`.
Resolve only the settings needed for the requested behavior:

- [Scheduling](scheduling.md): when the rule runs.
- [Queries](queries/define-alert-queries.md): sources, time windows, and result fields.
- [Triggering](triggering/define-alert-triggering.md): conditions, severity, and consecutive checks.
- [Group evaluation](group-evaluation.md): independent alerts for each entity.
- [Notification connection](notifications/connect.md): mode, selected policies,
  and repeat wait; [recovery notifications](notifications/recovery.md) when requested.
- [Labels and annotations](labels-annotations.md): routing identity and context.
- [Dashboard design and management](../../dashboard/entry.md): when the request also
  includes creating or editing the associated dashboard.

Use the suggested settings below unless the requirement overrides them. Do not ask about
every optional setting. Multi-query, grouping, and cross-account needs can affect
the design before the remaining settings are resolved.

## Rule identity and ownership

| Concept | Field | Meaning |
| --- | --- | --- |
| Owning Project | Request target (outside the rule document) | Regional Project that stores the rule. It is independent of any Project read by the query. |
| Stable rule ID | `name` | Unique within the owning Project. Use this ID for get, update, enable, disable, and delete. |
| Display name | `displayName` | Human-readable name; it can differ from the stable ID. |
| Description | `description` | Optional explanatory text. |

Use the stable rule ID to select an existing rule.

`name` must be 4–64 ASCII characters and match
`^[0-9a-z][0-9a-z_-]{0,62}[0-9a-z]$`. The length of `displayName` must be
4–100 bytes. `description` is optional and must not exceed 256 bytes.

## Configuration and tools

The [latency example](../examples/latency-alert.md#complete-configuration) shows a complete
rule document. [CLI execution](../cli-execution.md#create-or-update-a-rule) describes file
input and request fields. A [local validator](verify-alert-rule.md) can check configuration
structure; [alert history](../diagnosis/diagnose.md#start-with-the-incident) provides runtime
evaluation and notification context when needed.

## Suggested settings for new rules

These are starting choices for new direct log alerts, not service defaults.
Adjust them to the requested behavior and preserve existing choices on unrelated updates.

| Field | Suggested setting |
| --- | --- |
| `schedule` | One `FixedRate` interval selected for the required check frequency |
| `queryList` | One log search/SQL query with an explicit rolling window |
| `version`, `type` | `"2.0"`, `"default"` inside `configuration` |
| `dashboard` | Select the associated dashboard; `internal-alert-analysis` is the example value |
| `severityConfigurations`, `threshold` | One severity branch; `threshold: 1` |
| `groupConfiguration` | `{"type":"no_group","fields":[]}` |
| `autoAnnotation` | `true` |
| `sendResolved`, `noDataFire` | `false`; `noDataSeverity` matters only when no-data firing is enabled |
| `labels`, `annotations` | Omit or leave empty unless needed for routing/context |
| `sinkCms`, `sinkEventStore` | Disabled unless requested |
| `sinkAlerthub`, `policyConfiguration` | Normal notification mode; see [notifications](notifications/connect.md#normal-mode-baseline) |

For direct rules, `templateConfiguration` may be omitted or `null` when no
template is configured. Preserve it during unrelated updates.

For additional fields, consult the
[official rule schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-an-alert-monitoring-rule)
and [creation guide](https://help.aliyun.com/zh/sls/create-an-alert-monitoring-rule-for-logs).
