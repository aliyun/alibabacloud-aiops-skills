# RAM Permissions

The RAM permissions required by this skill (least-privilege):

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Required Permissions

`ecs:DescribeInstances` — confirm that the instance exists and obtain basic info (status, name, spec, CPU/memory).

`ecs:DescribeInstanceMonitorData` — fetch instance monitoring data (CPU, memory, network, IO) for the fallback path when CloudMonitor is unavailable.

`ecs:DescribeDiskMonitorData` — fetch per-disk monitoring data (IOPS, BPS, latency) for the fallback path when CloudMonitor is unavailable.

`ecs:DescribeDisks` — query disks attached to the instance (size, category, usage).

`cms:DescribeMonitoringAgentStatuses` — check the install/run state of the CloudMonitor agent and decide the data path.

`cms:DescribeMetricLast` — query the latest CloudMonitor metrics (CPU, load, memory, network, disk IO, disk usage).

## Notes

- **Scope**: read-only permissions necessary for inspection only.
- **Write actions**: none (this skill never modifies the instance).
- **Wildcards**: not used (least-privilege principle).
- **Fallback strategy**: when CMS permissions are unavailable, the skill automatically downgrades to ECS native monitoring APIs.

## Custom Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceMonitorData",
        "ecs:DescribeDiskMonitorData",
        "ecs:DescribeDisks"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMonitoringAgentStatuses",
        "cms:DescribeMetricLast"
      ],
      "Resource": "*"
    }
  ]
}
```

## Use Case

This permission set targets ECS instance resource-usage inspection:
- Check instance status and basic info
- Inspect the CloudMonitor agent state and collect metrics
- Fall back to ECS native monitoring APIs when CloudMonitor is unavailable
- Query disk capacity and usage
- Generate the inspection report
