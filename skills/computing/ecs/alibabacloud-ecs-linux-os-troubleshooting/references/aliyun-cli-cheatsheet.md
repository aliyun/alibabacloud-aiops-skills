# aliyun CLI Quick Reference

Invoke commands in plugin mode with `aliyun ecs <sub-command> --kebab-case-param <value>`. The table below lists the subcommands commonly used in troubleshooting workflows. Full parameters are subject to the output of `aliyun ecs <sub-command> help`. Every command must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/{session-id}`.

CloudMonitor also supports plugin mode through the `aliyun-cli-cms` plugin, as described in [`utils/cloudmonitor-metrics.md`](utils/cloudmonitor-metrics.md).

## Instance and Resource Metadata

| CLI subcommand | OpenAPI | Purpose | Required parameters |
| --- | --- | --- | --- |
| `describe-instances` | `DescribeInstances` | Query instance information, such as status, specification, network, and billing method | `--biz-region-id` (`--instance-ids` JSON array to filter a single instance) |
| `describe-instance-attribute` | `DescribeInstanceAttribute` | Query detailed attributes of a single instance | `--instance-id` |
| `describe-disks` | `DescribeDisks` | Query details of an instance's system disks and data disks | `--biz-region-id` (`--instance-id` or `--disk-ids` filter) |
| `describe-images` | `DescribeImages` | Query image information and tags | `--biz-region-id` (`--image-id` / `--instance-id` filter) |
| `describe-network-interfaces` | `DescribeNetworkInterfaces` | Query instance ENI configuration, including primary and secondary ENIs | `--biz-region-id` (`--instance-id` filter) |
| `describe-security-groups` | `DescribeSecurityGroups` | Query the list of security groups to which the instance belongs | `--biz-region-id` (`--instance-id` filter) |
| `describe-security-group-attribute` | `DescribeSecurityGroupAttribute` | Query security group rule details, including inbound and outbound rules | `--biz-region-id` + `--security-group-id` |
| `describe-user-data` | `DescribeUserData` | Query the instance UserData | `--biz-region-id` + `--instance-id` |
| `get-instance-screenshot` | `GetInstanceScreenshot` | Obtain a real-time screenshot of the instance VNC console | `--biz-region-id` + `--instance-id` |
| `get-instance-console-output` | `GetInstanceConsoleOutput` | Obtain the instance serial console output | `--biz-region-id` + `--instance-id` |
| `describe-instance-history-events` | `DescribeInstanceHistoryEvents` | Query instance system events, such as instance restart, performance throttling, and other platform-side events, to determine whether the abnormality is caused by the platform side | `--biz-region-id` (`--instance-id`, `--instance-event-cycle-status`, and `--instance-event-type` filters) |

Gotchas verified against the live API:

- `describe-instance-history-events` returns only **pending** events by default. To find events that already happened, pass `--instance-event-cycle-status Executed` (values can be repeated), optionally with `--event-publish-time-start` and `--event-publish-time-end`.
- Its `TotalCount` may be `0` even when `InstanceSystemEventSet.InstanceSystemEventType` contains events, so judge by the array, not by `TotalCount`. Each event carries `EventType.Name` (for example `InstanceFailure.Reboot`), `EventCycleStatus.Name`, `EventPublishTime`, `EventFinishTime`, and `Reason`.
- `describe-image-support-instance-types` returns every supported instance type (over ten thousand entries). Always filter, for example `| jq -r '.InstanceTypes.InstanceType[] | select(.InstanceTypeId=="<instance-type>")'`, instead of printing the response.
- `describe-diagnostic-metric-sets` returns only your own sets unless `--type Common` is passed, and its `MetricSets` field is a flat array.

## Instance Type and Image Catalogs

| CLI subcommand | OpenAPI | Purpose | Required parameters |
| --- | --- | --- | --- |
| `describe-instance-types` | `DescribeInstanceTypes` | Query the instance type catalog | Optional filters such as `--instance-type-family` / `--instance-types` |
| `describe-instance-type-families` | `DescribeInstanceTypeFamilies` | Query available instance type families | `--biz-region-id` |
| `describe-image-support-instance-types` | `DescribeImageSupportInstanceTypes` | Query instance types compatible with an image | `--biz-region-id` (`--image-id` filter) |

## ECS Diagnostic Reports

| CLI subcommand | OpenAPI | Purpose | Required parameters |
| --- | --- | --- | --- |
| `create-diagnostic-report` | `CreateDiagnosticReport` | Trigger resource diagnostics. If `--metric-set-id` is not specified, the default set `dms-instancedefault` is used. Returns `ReportId` | `--biz-region-id` + `--resource-id` (instance ID) |
| `describe-diagnostic-report-attributes` | `DescribeDiagnosticReportAttributes` | Poll diagnostic report details and extract abnormal diagnostic items | `--biz-region-id` + `--report-id` |
| `describe-diagnostic-reports` | `DescribeDiagnosticReports` | Query historical diagnostic report list | `--biz-region-id` |
| `describe-diagnostic-metric-sets` | `DescribeDiagnosticMetricSets` | Enumerate the available diagnostic metric sets and their applicable resource types, used to confirm whether a domain-specific metric set exists | `--biz-region-id` (`--type Common` for built-in sets; `--type` defaults to `User`) |

## GuestOS-Internal Data Collection

| CLI subcommand | OpenAPI | Purpose | Required parameters |
| --- | --- | --- | --- |
| `describe-cloud-assistant-status` | `DescribeCloudAssistantStatus` | Query whether the Cloud Assistant Agent is online, as a prerequisite check before calling `RunCommand` | `--biz-region-id` (`--instance-id` filter) |
| `run-command` | `RunCommand` | Execute Shell/PowerShell/Bat scripts on one or more ECS instances | `--biz-region-id` + `--type` (`RunShellScript`) + `--command-content` + `--instance-id` |
| `describe-invocations` | `DescribeInvocations` | Query the Cloud Assistant command execution list and status (`Running` / `Finished` / `Failed`) | `--biz-region-id` (`--invoke-id` / `--instance-id` filter) |
| `describe-invocation-results` | `DescribeInvocationResults` | Query the actual output of Cloud Assistant commands, including stdout and exit code. `Output` is Base64-encoded | `--biz-region-id` (`--invoke-id` / `--instance-id` filter) |
| `stop-invocation` | `StopInvocation` | Stop a Cloud Assistant command in `Running` state | `--biz-region-id` + `--invoke-id` + `--instance-id` |

Gotchas verified against the live API:

- `run-command` accepts `--command-content` as plain text by default, so Base64 encoding of the input is not required. `--instance-id` is a list and maps to `InstanceId.1`. The response returns `InvokeId`.
- Command completion requires two checks: `Invocations.Invocation[0].InvokeStatus` is `Finished`, and `InvokeInstances.InvokeInstance[0].InvocationStatus` is `Success` with `ExitCode` of `0`.
- The command output in `Invocation.InvocationResults.InvocationResult[0].Output` is **Base64-encoded**, so decode it before analysis:
  ```bash
  aliyun ecs describe-invocation-results --biz-region-id <region-id> --invoke-id <invoke-id> \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
    | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' | base64 -d
  ```
- After `stop-invocation`, `InvokeStatus` becomes `Stopped` and `InvocationStatus` becomes `Terminated`, and no `ExitCode` is returned.

## CloudMonitor Metrics

| CLI subcommand | OpenAPI | Purpose | Required parameters |
| --- | --- | --- | --- |
| `cms describe-metric-meta-list` | `DescribeMetricMetaList` | Enumerate the metrics available under a namespace, used to confirm metric names before querying | `--namespace` (`acs_ecs_dashboard`); `--page-size` defaults to 30, page with `--page-number` |
| `cms describe-metric-list` | `DescribeMetricList` | Query the historical trend of a metric to locate the abnormal time window | `--namespace` + `--metric-name` + `--dimensions`; `Datapoints` is a JSON string and must be parsed twice |
| `cms describe-metric-last` | `DescribeMetricLast` | Query the latest value of a metric | `--namespace` + `--metric-name` + `--dimensions` |

These subcommands require the `aliyun-cli-cms` plugin. If it is missing, install it with `aliyun plugin install --names aliyun-cli-cms`.
