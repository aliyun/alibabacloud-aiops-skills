# Consumer-group lag: `consumergroup_log`

Use to identify a consumer group or shard falling behind the latest ingested
logs. The documented reporting interval is two minutes.

| Field | Meaning |
| --- | --- |
| `project`, `LogStore` | Source Project and Logstore being consumed |
| `consumer_group` | Consumer-group name |
| `shard` | Consumed shard ID |
| `fallbehind` | Time lag from the consumption position to the latest written logs, in seconds |

Example filter in the discovered diagnostic Store:

```text
__topic__: consumergroup_log and project: "example-project" and consumer_group: "example-group"
```

Compare lag by group and shard over the incident interval; do not sum shard lag
as if it were a count of unconsumed events. An empty interval can reflect the
reporting cadence, activation or retention and does not establish zero lag.

For location and management, see [service logs](../service-logs.md).
Source: [Service log types — consumer-group lag](https://help.aliyun.com/zh/sls/log-types).
