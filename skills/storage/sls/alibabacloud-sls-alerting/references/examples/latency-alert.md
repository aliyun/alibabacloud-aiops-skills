# Typical scenario: high read/write latency

## Desired outcome

Evaluate the previous minute of read/write requests every minute. Exclude 403
responses. Notify when a source has average latency at least `100000` and more
than `20000` requests in that window. Use Critical severity, a one-minute repeat
wait, and no recovery notification.

The threshold represents 100 milliseconds only if `Latency` is measured in
microseconds. Confirm the source field's unit before using this threshold.

## Prepare only the required dependencies

1. Follow [Notifications](../rules/notifications/connect.md) to choose a mode. In normal mode,
   reuse an approved action policy whose recipients and channels fit the
   requirement. It can select the built-in `sls.builtin.cn` template. Inspect
   the policy instead of assuming it is suitable based on its name.
2. If no policy fits, resolve/reuse recipients, choose the template, and create
   only the missing resources through [ResourceRecord operations](../notifications/api/resource-records.md).
   If minimal mode is requested, use its [coverage boundary](../rules/notifications/connect.md#minimal-mode-coverage-boundary).
3. Copy the [complete configuration](#complete-configuration) to a separate working
   file, replacing `example-*` identifiers and the data-source region. These
   are substitutions, not environment discovery or resource creation.
4. [Validate the query](../rules/queries/verify-alert-query.md#validate-a-new-or-changed-query)
   against representative logs, then follow [rule creation](../rules/create-update-alert-rule.md#assemble-and-verify)
   for local validation, the create dry run, submission, and readback.

The example has three deliberately explicit durations: check every `1m`, query
from `-1m` to `now`, and repeat notifications after `1m`. Changing one does not
change the others.

## Complete configuration

```json
{
  "name": "example-latency-alert",
  "displayName": "High average read/write latency",
  "description": "Illustrative configuration; resolve the data source and action policy before use.",
  "schedule": {
    "type": "FixedRate",
    "interval": "1m"
  },
  "configuration": {
    "version": "2.0",
    "type": "default",
    "dashboard": "internal-alert-analysis",
    "queryList": [
      {
        "storeType": "log",
        "region": "cn-hangzhou",
        "project": "example-project",
        "store": "example-logstore",
        "query": "(RequestType :read or RequestType :write) and not Status :403 | select __source__, avg(Latency) as t from log group by __source__ having t >= 100000 and count(*) > 20000 order by t desc limit 10",
        "timeSpanType": "Relative",
        "start": "-1m",
        "end": "now",
        "powerSqlMode": "auto"
      }
    ],
    "groupConfiguration": {
      "type": "no_group",
      "fields": []
    },
    "severityConfigurations": [
      {
        "severity": 10,
        "evalCondition": {
          "condition": "",
          "countCondition": ""
        }
      }
    ],
    "threshold": 1,
    "autoAnnotation": true,
    "sendResolved": false,
    "noDataFire": false,
    "noDataSeverity": 6,
    "labels": [],
    "annotations": [
      {
        "key": "title",
        "value": "${alert_name}"
      },
      {
        "key": "desc",
        "value": "Average read/write latency threshold exceeded"
      }
    ],
    "policyConfiguration": {
      "alertPolicyId": "sls.builtin.dynamic",
      "actionPolicyId": "example-action-policy",
      "repeatInterval": "1m"
    },
    "sinkAlerthub": {
      "enabled": true
    },
    "sinkCms": {
      "enabled": false
    },
    "sinkEventStore": {
      "enabled": false
    }
  }
}
```

## Why "any data" is the trigger

The SQL filters problematic source aggregates in its `HAVING` clause. Any
returned row already meets the business condition, so the Critical branch uses
both `condition: ""` and `countCondition: ""`. An empty query result does not
fire, and the separate no-data option remains off.

SQL `GROUP BY __source__` produces source-level rows, but the alert uses
`no_group`: qualifying rows produce one alert per check, not an alert per source.
The query also limits output to ten sources. Load
[Group evaluation](../rules/group-evaluation.md) only if independent
per-source alerts are requested, and reconsider the result limit at that point.

## Console export is not the create request

| Console export field | API-oriented field |
| --- | --- |
| `alertName` | `name`, passed as create's `--name` |
| `alertDisplayName` | `displayName` |
| `scheduleType`, `interval` | `schedule.type`, `schedule.interval` |
| `dashboardName` | `configuration.dashboard` |
| `queryList`, `severityConfigurations`, output/evaluation fields | Children of `configuration` |
| Creation/modification timestamps and console-only fields | Not copied into the new create draft |
| `policyConfiguration.useDefault: false` | Omit it; the CLI rejects this SDK compatibility field |

The configuration uses example Project, rule, and action-policy names. Resolve
these resources before creating the rule; do not fabricate an `alert.simple.*`
policy ID from a console export.
Do not infer disable behavior from the export's `notificationDisabled` field.
Use the dedicated [enable/disable operations](../rules/manage-alert-rules.md#enable-disable-or-delete)
and verify the returned `status` (`ENABLED` or `DISABLED`).
