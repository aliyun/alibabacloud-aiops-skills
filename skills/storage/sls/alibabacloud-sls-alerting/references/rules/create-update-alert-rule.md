# Create or update an alert rule

Use this operation to create a rule or change its behavior. To inspect, enable,
disable, or delete a rule, use [rule management](manage-alert-rules.md).

## Prepare the change

For creation, choose the owning Project and a new rule identity. For updates,
read the current rule and prepare a complete replacement schedule and
configuration. Preserve unrelated fields, including optional sinks; do not send
only the changed nested fragment or delete and recreate the rule.

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

Use the defaults below unless the requirement overrides them. Do not ask about
every optional setting. Multi-query, grouping, and cross-account needs can affect
the design before the remaining settings are resolved.

## Rule identity and ownership

| Concept | Create/update parameter | Meaning |
| --- | --- | --- |
| Owning Project | CLI `--project` | Regional Project that stores the rule. It is independent of any Project read by the query. |
| Stable rule ID | Create `--name`; later operations `--alert-name`; document `name` | Unique within the owning Project. Use this ID for get, update, enable, disable, and delete. |
| Display name | `--display-name`; document `displayName` | Human-readable name; it can differ from the stable ID. |
| Description | `--description`; document `description` | Optional explanatory text. |

Do not substitute the display name for `--alert-name`.

`name` must be 4–64 ASCII characters and match
`^[0-9a-z][0-9a-z_-]{0,62}[0-9a-z]$`. The length of `displayName` must be
4–100 bytes. `description` is optional and must not exceed 256 bytes.

## Assemble and verify

Save the complete CLI-oriented document as `SLS_ALERT_FILE`; the
[latency example](../examples/latency-alert.md#complete-configuration) shows one.
Follow [rule verification](verify-alert-rule.md) before submitting it.

## Submit the change

Use `--cli-dry-run` to inspect the generated request before submitting it:

```bash
aliyun sls create-alert \
  --user-agent "$SLS_ALERT_USER_AGENT" \
  --project "$SLS_PROJECT" \
  --name "$(jq -r '.name' "$SLS_ALERT_FILE")" \
  --display-name "$(jq -r '.displayName' "$SLS_ALERT_FILE")" \
  --description "$(jq -r '.description // ""' "$SLS_ALERT_FILE")" \
  --schedule "$(jq -c '.schedule' "$SLS_ALERT_FILE")" \
  --configuration "$(jq -c '.configuration' "$SLS_ALERT_FILE")" \
  --cli-dry-run
```

For updates, use `update-alert` and `--alert-name "$SLS_ALERT_ID"` in place of
`create-alert` and `--name`. A dry run checks request construction, not service
semantics. Remove `--cli-dry-run` to submit the authorized change.

The `create-alert` command has no `--status` option; do not promise creation in a
disabled state. `runImmediately: false` does not disable future checks.

For requested evaluation verification, use
[alert history](../diagnosis/diagnose.md#start-with-the-incident).

## Shared configuration baseline

Apply these defaults to new direct log alerts unless the requirement overrides
one; preserve existing choices during unrelated updates.

| Field | Default |
| --- | --- |
| `schedule` | One `FixedRate` interval selected for the required check frequency |
| `queryList` | One log search/SQL query with an explicit rolling window |
| `version`, `type` | `"2.0"`, `"default"` inside `configuration` |
| `dashboard` | Alert-history dashboard; the example uses `internal-alert-analysis` |
| `severityConfigurations`, `threshold` | One severity branch; `threshold: 1` |
| `groupConfiguration` | `{"type":"no_group","fields":[]}` |
| `autoAnnotation` | `true` |
| `sendResolved`, `noDataFire` | `false`; `noDataSeverity` matters only when no-data firing is enabled |
| `labels`, `annotations` | Omit or leave empty unless needed for routing/context |
| `sinkCms`, `sinkEventStore` | Disabled unless requested |
| `sinkAlerthub`, `policyConfiguration` | Normal notification mode; see [notifications](notifications/connect.md#normal-mode-baseline) |

The CLI rejects `policyConfiguration.useDefault`. Omit it from CLI-bound
payloads.
When adapting a read response, omit this known field only if absent or `false`;
retain the raw snapshot and investigate any other value rather than changing its
meaning. Do not silently delete other unsupported fields to force a write.

For additional fields, consult the
[official rule schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-an-alert-monitoring-rule)
and [creation guide](https://help.aliyun.com/zh/sls/create-an-alert-monitoring-rule-for-logs).
