# CloudMonitor Metric Query

This document describes how to obtain resource usage trends of an ECS instance through CloudMonitor (CMS) to determine the abnormal time window and to correlate the abnormality with business peaks. Metric trends are the only way to reconstruct **historical** resource usage after the fact; commands such as `top` and `iostat` show only the current state.

CloudMonitor subcommands are invoked in plugin mode, the same style as `aliyun ecs`, and require the `aliyun-cli-cms` plugin. If the CLI reports that the subcommand is not a valid built-in command, install the plugin with `aliyun plugin install --names aliyun-cli-cms`.

## Step 1: Confirm the Available Metrics

ECS metrics are divided into two categories:

- **Basic metrics**: reported by the platform and always available without any in-instance agent.
- **Host monitoring metrics**: reported by the CloudMonitor agent inside the instance. They are available only when the agent is installed and running.

Because the available metric names depend on the region and agent version, enumerate them first and use only the names that actually exist. `--page-size` defaults to 30, and the response carries no total count, so use a larger page size and page through with `--page-number` until a page returns no metric:

```bash
for p in 1 2 3; do
  aliyun cms describe-metric-meta-list --namespace acs_ecs_dashboard --page-size 200 --page-number $p \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
    | jq -r '.Resources.Resource[]? | "\(.MetricName) | \(.Periods) | \(.Dimensions)"'
done
```

The `Periods` field of each metric lists the `--Period` values that metric actually accepts, and `Dimensions` lists the dimension keys it requires.

If the required host monitoring metric does not exist, the CloudMonitor agent is most likely not installed. In that case, state this to the user, and collect the current-state data inside the instance through `RunCommand` instead.

## Step 2: Query the Metric Trend

`DescribeMetricList` returns `Datapoints` as a **JSON string**, not as an array, so it must be parsed twice. A raw dump of a one-hour window at `--period 60` is thousands of lines, so **always aggregate the datapoints instead of printing them**:

```bash
aliyun cms describe-metric-list \
  --namespace acs_ecs_dashboard \
  --metric-name <metric-name> \
  --period 300 \
  --start-time '<ISO8601-start>' \
  --end-time '<ISO8601-end>' \
  --dimensions '[{"instanceId":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
  | jq -r '.Datapoints' \
  | jq -c '{n:length, max:(map(.Maximum)|max), avg:((map(.Average)|add)/length),
            peak:(max_by(.Maximum)|{timestamp,Maximum})}'
```

Notes:

- `--period` accepts the values listed in the `Periods` field of the metric, typically 60, 300, and 3600 seconds. Use 60 only for a short abnormal window; use 300 or 3600 for a long time span.
- `--start-time` and `--end-time` accept ISO 8601 UTC timestamps such as `2026-01-01T00:00:00Z`. The `timestamp` field of each datapoint is returned as epoch milliseconds.
- Each datapoint carries `Minimum`, `Maximum`, and `Average`. Judge saturation by `Maximum`, because a high peak can be hidden by the average.
- Take a window that covers the abnormality and extends before and after it, so that the trend before the abnormality is visible.
- To view only the latest value, use `aliyun cms describe-metric-last` with the same parameters, including the same double parsing of `Datapoints`.

## Step 3: Select Metrics by Phenomenon Domain

| Phenomenon domain | Recommended metrics | Category |
| --- | --- | --- |
| CPU utilization abnormally high | `CPUUtilization`; `cpu_user`, `cpu_system`, `cpu_wait` for the user/kernel/IO-wait breakdown | Basic; host monitoring |
| load abnormally high | `load_1m`, `load_5m`, `load_15m`, or the per-core variants `load_per_core_1m`, `load_per_core_5m`, `load_per_core_15m` | Host monitoring |
| High memory utilization / OOM | `memory_usedutilization`, `memory_freeutilization`, `memory_actualusedspace` | Host monitoring |
| Disk IOPS abnormally high | `DiskReadIOPS`, `DiskWriteIOPS`; `disk_readiops`, `disk_writeiops` per device | Basic; host monitoring |
| Disk performance below expectations | `DiskReadBPS`, `DiskWriteBPS`, `DiskReadIOPS`, `DiskWriteIOPS`; `diskusage_utilization` for space | Basic; host monitoring |
| Network performance below expectations | `InternetInRate`, `InternetOutRate`, `IntranetInRate`, `IntranetOutRate` | Basic |
| Packet loss, retransmission, latency | `IntranetInRate`, `IntranetOutRate`, and `net_tcpconnection` for the connection count | Basic; host monitoring |
| Crash or hang | Backtrack `CPUUtilization`, `memory_usedutilization`, `DiskReadBPS`, `DiskWriteBPS`, and the network rate metrics together | Basic; host monitoring |

## Step 4: Interpret the Trend

- The abnormal window coincides with a business peak: this is most likely normal behavior under business load. Confirm the business change with the user.
- The metric is saturated at the instance type limit: compare it with the [instance performance SLA](https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families). If the limit is reached, this is not a GuestOS issue, and upgrading the instance type is the recommendation.
- The metric rises abnormally with no business change: continue with the GuestOS-internal localization steps of the phenomenon domain, and use the identified window as the time range for subsequent in-instance data collection.
