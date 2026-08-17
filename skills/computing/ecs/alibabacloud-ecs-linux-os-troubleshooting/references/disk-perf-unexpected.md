# Disk Read/Write Performance Does Not Meet Expectations

## Confirm Whether It Is a GuestOS Issue

1. Use `DescribeInstances` to obtain the instance type, and use `DescribeInstanceTypes` to obtain the list of shared instance types. Determine whether the current instance type is a shared instance type.
   - Yes: no further troubleshooting is needed because shared instance types do not promise a performance SLA.
   - No: continue.
2. Use `DescribeDisks` to obtain the category and size of the disk (`Category`, `Size`, `PerformanceLevel`), look up the IOPS and throughput limit of that disk category and size in the [instance performance SLA](https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families) and the block storage performance documentation, and follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the actual disk I/O load.
   - If it has reached the limit: recommend upgrading the disk category or size.
   - If it has not reached the limit: continue.
3. Use `DescribeInstanceHistoryEvents` to check whether there are recent disk I/O related system events, and obtain the event type, frequency, and time distribution.
   - Confirmed as platform-side throttling, such as reaching the instance type disk performance limit: this is not a GuestOS issue. Provide the conclusion directly and recommend upgrading the instance type.
   - Not platform-side throttling, or no system event exists: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- Block device queue parameters
- I/O scheduler
- CPU affinity configuration

### Issue Localization

1. Run `cat /sys/block/<disk_name>/queue/rq_affinity` to view the CPU affinity policy of the disk request queue. It can be adjusted appropriately.
2. Run `cat /sys/block/<disk_name>/mq/<queue_num>/cpu_list` to view the CPU affinity policy of disk multiqueues. It can be adjusted appropriately.
3. Run `cat /sys/block/<disk_name>/queue/scheduler` to view the disk scheduling algorithm. The default should be NOP. Adjust it appropriately if necessary.
