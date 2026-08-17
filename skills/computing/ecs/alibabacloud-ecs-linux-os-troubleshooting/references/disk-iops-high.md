# Abnormally High Disk IOPS

## Confirm Whether It Is a GuestOS Issue

1. Use `DescribeInstances` to obtain the instance type, and use `DescribeInstanceTypes` to obtain the list of shared instance types. Determine whether the current instance type is a shared instance type.
   - Yes: no further troubleshooting is needed because shared instance types do not promise a performance SLA.
   - No: continue.
2. Use `DescribeInstanceHistoryEvents` to check whether there are recent disk I/O related system events, and obtain the event type, frequency, and time distribution.
   - Confirmed as platform-side throttling, such as reaching the instance type IOPS limit: this is not a GuestOS issue. Provide the conclusion directly and recommend upgrading the instance type.
   - Not platform-side throttling, or no system event exists: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- Disk devices and block layer
- File system and I/O scheduling
- Business process I/O behavior

### Issue Localization

1. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the disk IOPS trend, and confirm the time window and peak of the abnormal increase.
2. Run `iostat 1` to observe disk read/write counts.
   - Too high: provide the conclusion and remediation recommendations.
   - Not high: continue to the next step.
3. Run `pidstat -d 1` to observe per-process disk reads and writes.
   - Too high: provide the conclusion and remediation recommendations.
   - Not high: continue to the next step.
