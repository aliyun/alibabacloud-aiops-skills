# Abnormally High load1m/load5m/load15m

## Confirm Whether It Is a GuestOS Issue

1. Use `DescribeInstances` to obtain the instance type, and use `DescribeInstanceTypes` to obtain the list of shared instance types. Determine whether the current instance type is a shared instance type.
   - Yes: no further troubleshooting is needed because shared instance types do not promise a performance SLA.
   - No: continue.
2. Use `DescribeInstanceHistoryEvents` to check whether there are recent CPU or load related system events, and obtain the event type, frequency, and time distribution.
   - Confirmed as platform-side behavior, such as resource throttling or CPU binding: this is not a GuestOS issue. Provide the conclusion directly and recommend upgrading the instance type.
   - Not platform-side behavior, or no system event exists: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- CPU pressure
- Process scheduler
- Processes and threads, including D state and short-lived processes

### Issue Localization

1. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the load trend and confirm the time window in which load rose abnormally.
2. Run `top -b -n 1 | head -20` or `ps aux --sort=-%cpu | head -10` to view the top processes during the high-load window.
   - The problematic process can be located: provide the conclusion and remediation recommendations.
   - It cannot be located: continue with more detailed investigation.
3. Run `ps aux | awk '$8 ~ /R/'` to check the number of running processes.
   - Too many: this may be caused by a large number of short-lived processes.
   - Not many: continue to the next step.
4. Run `ps aux | awk '$8 ~ /D/'` to check whether there are processes in D state.
   - Yes: recommend running `cat /proc/<pid>/stack` to locate where the call stack is stuck.
   - No: continue investigating other possible causes.
