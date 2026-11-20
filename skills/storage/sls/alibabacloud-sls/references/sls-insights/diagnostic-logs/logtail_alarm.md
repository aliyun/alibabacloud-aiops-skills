# Collector alarms: `logtail_alarm`

Use to diagnose collector errors such as parsing, file access, configuration or
sending failures. The documented Logtail format reports every 30 seconds,
aggregating repeated occurrences of an error type within the interval and
retaining one sampled message.

| Field | Meaning |
| --- | --- |
| `project`, `LogStore` | Affected source Project and Logstore |
| `source_ip`, `version`, `os` | Collector identity and runtime context |
| `alarm_type` | Error/diagnostic category |
| `alarm_count` | Occurrences recorded in the reporting interval |
| `alarm_message` | Sampled error detail or original-log sample |

Example filter:

```text
__topic__: logtail_alarm and project: "example-project"
```

Return `alarm_message` alongside `alarm_type`; a type alone is insufficient
evidence for the cause. Row count is not the error-occurrence count, and one
sample does not represent every occurrence. A collector alarm does not prove
that an SLS alert rule fired or a notification was delivered; use
[alert history](../alert-history.md) for that evidence.

For collector version routing, query constraints and applicable reporting
behavior, also read [collector contracts](../../loongcollector/sls-lens-contracts.md).
Source: [Service log types — Logtail alarms](https://help.aliyun.com/zh/sls/log-types).
