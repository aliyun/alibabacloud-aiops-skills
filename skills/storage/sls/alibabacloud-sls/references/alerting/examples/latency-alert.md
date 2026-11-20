# Typical scenario: high read/write latency

## Desired outcome

Evaluate the previous minute of read/write requests every minute. Exclude 403
responses. Notify when a source has average latency at least `100000` and more
than `20000` requests in that window. Use Critical severity, a one-minute repeat
wait, and no recovery notification.

The threshold represents 100 milliseconds only if `Latency` is measured in
microseconds. Confirm the source field's unit before using this threshold.

## Dependencies and adaptation

In [normal notification mode](../rules/notifications/connect.md), an existing action policy
can supply the intended recipients, channels and `sls.builtin.cn` template. Its configuration
determines suitability, not its name. Missing resources can be created through
[ResourceRecord operations](../notifications/api/resource-records.md); an existing rule-specific
policy can instead use [minimal mode](../rules/notifications/connect.md#minimal-mode).

The [complete configuration](#complete-configuration) uses example IDs and a data-source region
to replace for the target environment. [Query inspection](../rules/queries/verify-alert-query.md#validate-a-new-or-changed-query)
can help assess the window and threshold; [rule configuration and tools](../rules/create-update-alert-rule.md#configuration-and-tools)
describe the available creation and local-validation methods.

The example has three deliberately explicit durations: check every `1m`, query
from `-1m` to `now`, and repeat notifications after `1m`. Changing one does not
change the others.

## Complete configuration

```json
{
  "name": "example-latency-alert",
  "displayName": "High average read/write latency",
  "description": "Alert on high average read/write latency for sources with more than 20000 requests per minute.",
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
