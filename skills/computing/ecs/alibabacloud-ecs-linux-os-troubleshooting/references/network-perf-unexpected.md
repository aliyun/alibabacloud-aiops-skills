# Network send/receive performance does not meet expectations

## Determine whether this is a GuestOS issue

1. Use `DescribeInstances` to obtain the instance type, and use `DescribeInstanceTypes` to obtain the list of shared instance types. Determine whether the current instance type is a shared type.
   - Yes: no further troubleshooting is required, because shared instance types do not provide a performance SLA.
   - No: continue.
2. Confirm with the user whether the test method uses the [official method recommended by Alibaba Cloud](https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-testing-network-performance).
   - If the official recommended method was not used: retest according to the Help Center best practices for network performance testing.
   - If it was used: continue.
3. Create a test instance with the same instance type and image, and verify whether the performance truly does not meet expectations.
   - New instance meets expectations: this is mostly a customer environment or configuration issue.
   - New instance still does not meet expectations: continue.
4. Confirm whether this is the known issue where performance degrades after updating the kernel on an AMD instance: [AMD instance kernel update performance notice](https://help.aliyun.com/zh/ecs/user-guide/performance-may-degrade-after-the-guest-operating-system-kernel-of-an-amd-instance-is-updated#f664bab6fejjj).
   - Known issue: handle it according to the document.
   - No: continue.
5. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the network rate trend, and use `DescribeInstanceTypes` to obtain the bandwidth and packet-rate limits of the instance type (`InstanceBandwidthRx`, `InstanceBandwidthTx` in Kbit/s, and `InstancePpsRx`, `InstancePpsTx`). Check whether the actual throughput has already reached the instance type limit.
   - Reached the limit: this is not a GuestOS issue. Recommend upgrading the instance type.
   - Not reached: continue.
6. Use `DescribeInstanceHistoryEvents` to check whether there are recent network-related system events, and obtain the event type, frequency, and time distribution.
   - Confirmed as platform-side behavior: this is not a GuestOS issue. Provide the conclusion directly.
   - Not platform-side behavior, or no system event exists: continue.

## Troubleshooting process inside GuestOS

### Related components

- sysctl network parameters
- irqbalance
- ecs_mq
- Interrupt affinity configuration
- TCP memory pressure

### Problem diagnosis

1. Run `sysctl -a` and compare the output with a new instance created from the same image to check whether there are customer-defined network configurations.
   - If yes, clear them and retest.
   - If no, continue to the next step.
2. Run `ps aux | grep irqbalance` or `systemctl status ecs_mq` to check whether irqbalance/ecs_mq is enabled; run `cat /proc/irq/<NIC_IRQ_NUM>/smp_affinity` to check whether interrupt affinity is reasonable.
   - If it is unreasonable, configure it according to the new instance created from the same image, and then retest.
   - If it is reasonable, continue to the next step.
3. Run `dmesg -T` to check whether there are logs indicating that TCP buckets are full or TCP memory is full.
   - If yes: this may indicate memory pressure or a socket leak. Increase parameters such as tcp_mem, tcp_rmem, and tcp_wmem, and then retest.
   - If no: submit a ticket.
