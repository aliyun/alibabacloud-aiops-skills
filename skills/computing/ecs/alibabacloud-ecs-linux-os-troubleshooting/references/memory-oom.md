# High Memory Utilization

## Confirm Whether It Is a GuestOS Issue

1. Use `DescribeInstances` to obtain the instance type, and use `DescribeInstanceTypes` to obtain the list of shared instance types. Determine whether the current instance type is a shared instance type.
   - Yes: no further troubleshooting is needed because shared instance types do not promise a performance SLA.
   - No: continue.
2. Use `DescribeInstanceHistoryEvents` to check whether there are recent memory-related system events, and obtain the event type, frequency, and time distribution.
   - Confirmed as known platform-side behavior: this is not a GuestOS issue. Provide the conclusion directly and recommend upgrading the instance type.
   - Not platform-side behavior, or no system event exists: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- Memory pressure
- OOM mechanism

### Issue Localization

1. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the memory utilization trend and locate the time window in which memory rose abnormally.
2. **No abnormal scene available**: use the window identified in step 1 to correlate the business processes running at that time, then provide the conclusion and OOM mitigation recommendations.
3. **Abnormal scene available**: run `free -h` to view the memory overview; run `vmstat` or `cat /proc/meminfo` to view memory details; run `top -b -n 1` to view processes with high memory usage.
   - If it can be located: provide the conclusion and remediation recommendations.
   - If it still cannot be located: recommend trying the `procrank` tool.
4. To confirm that an OOM kill occurred, follow [guestos-console-log](utils/guestos-console-log.md) to search the serial console log with the `OOM` keywords, or run `dmesg -T | grep -i -E 'oom-killer|Killed process'` inside the instance to obtain the killed process and its memory usage at that moment.
