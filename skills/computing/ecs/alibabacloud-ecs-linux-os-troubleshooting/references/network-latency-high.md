# High network packet send/receive latency

## Determine whether this is a GuestOS issue

1. Use `DescribeInstances` to obtain the instance type, and use `DescribeInstanceTypes` to obtain the list of shared instance types. Determine whether the current instance type is a shared type.
   - Yes: no further troubleshooting is required, because shared instance types do not provide a performance SLA.
   - No: continue.
2. Use `DescribeInstanceHistoryEvents` to check whether there are recent network-related system events, and obtain the event type, frequency, and time distribution.
   - Confirmed as platform-side behavior, such as reaching the instance type bandwidth or packet-rate limit: this is not a GuestOS issue. Provide the conclusion directly and recommend upgrading the instance type.
   - Not platform-side behavior, or no system event exists: continue.

## Troubleshooting process inside GuestOS

### Related components

- Network protocol stack
- sysctl network parameters
- CPU pressure
- Soft and hard interrupt load (hard interrupts: NIC/VirtIO; soft interrupts: NET_RX/NET_TX, etc.)
- Memory pressure
- slab pressure

### Problem diagnosis

1. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the network rate trend, and confirm the abnormal time window and whether the bandwidth is saturated.
2. Run `dmesg -T` to check whether there are logs indicating that TCP buckets are full or TCP memory is full.
   - If yes, increase sysctl parameters such as tcp_mem, tcp_rmem, and tcp_wmem, and then retest.
   - If no, continue to the next step.
3. Run `top -b -n 1` to check whether high CPU usage is slowing packet processing.
   - If CPU usage is high, upgrade the instance type or reduce the load, and then retest.
   - If CPU usage is not high, continue to the next step.
4. Check whether excessive soft or hard interrupt load is causing receive-packet or protocol-stack processing congestion.
   - Run `top -b -n 1` and focus on `%hi` (hard interrupts) and `%si` (soft interrupts); or run `mpstat -P ALL 1 1` to check `%irq` and `%soft` for each CPU.
   - Run `cat /proc/softirqs` to check whether counters such as NET_RX and NET_TX are increasing abnormally and whether they remain concentrated on a small number of CPUs for a long time.
   - Run `cat /proc/interrupts` to check whether NIC/VirtIO-related IRQs are concentrated on a small number of CPUs.
   - If the load is high, combine `ethtool -l <NIC_NAME>`/`ethtool -S <NIC_NAME>` with queues, RPS/RSS/XPS, interrupt affinity, `irqbalance`, GRO, and other coalescing/offload parameters to balance the load or reduce interrupts. If necessary, upgrade the instance type or reduce the packet rate, and then retest.
   - If the load is not high, continue to the next step.
5. Run `free -h` to check whether an excessively large slab is slowing protocol-stack memory allocation.
   - If it is too large, run `echo 2 > /proc/sys/vm/drop_caches` to release reclaimable slab and attempt mitigation.
   - If it is not large, continue to the next step.
