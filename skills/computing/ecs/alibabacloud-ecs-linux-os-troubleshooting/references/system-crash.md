# System crash

## Determine whether this is a GuestOS issue

1. This domain has no prerequisite boundary determination. Go directly to troubleshooting inside GuestOS.

## Troubleshooting process inside GuestOS

### Related components

- No fixed list of GuestOS components.

### Problem diagnosis

1. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to backtrack the resource trends (CPU, memory, IO, network) before the crash, and determine whether resource exhaustion caused the crash.
2. Use `DescribeInstanceHistoryEvents` to check whether crash-related system events exist, and determine whether the crash is occasional or frequent.
   - If yes, analyze it based on the event type and severity in the event details.
   - If no, continue.
3. Follow [guestos-console-log](utils/guestos-console-log.md) to obtain the serial console log and search for the `Crash` keywords, such as `panic` and `Oops`.
   - If found, expand the context according to that document and perform root cause analysis.
   - If not found, continue.
4. Check whether the system logs contain crash logs, or whether there are coredump files under /var/crash/.
   - If yes, refer to [How to collect kernel dump information after an operating system crash](https://help.aliyun.com/zh/ecs/collect-kdump-information-after-an-instance-experiences-an-operating-system-failure), upload the coredump file, and submit a ticket.
   - If no, submit a ticket directly.
