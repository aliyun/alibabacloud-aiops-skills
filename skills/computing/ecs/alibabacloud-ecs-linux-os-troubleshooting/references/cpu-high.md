# Abnormally High CPU Utilization

## Confirm Whether It Is a GuestOS Issue

1. Use `DescribeInstances` to obtain the instance type, and use `DescribeInstanceTypes` to obtain the list of shared instance types. Determine whether the current instance type is a shared instance type.
   - Yes: no further troubleshooting is needed because shared instance types do not promise a performance SLA.
   - No: continue.
2. Use `DescribeInstanceHistoryEvents` to check whether there are recent CPU-related system events, and obtain the event type, frequency, and time distribution.
   - Confirmed as platform-side behavior, such as resource throttling or CPU binding: this is not a GuestOS issue. Provide the conclusion directly and recommend upgrading the instance type.
   - Not platform-side behavior, or no system event exists: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- CPU pressure
- Process scheduler
- Business processes
- Malicious processes (mining trojans, hidden processes)
- perf tool
- Hardware interrupts
- Software interrupts

### Issue Localization

1. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the CPU utilization trend, locate the time window in which utilization rose abnormally, and determine whether it coincides with a business peak.
   - Yes: this is normal behavior during a business peak.
   - No, or there is no obvious business peak: continue troubleshooting.
2. Run `top -b -n 1 | head -20` or `ps aux --sort=-%cpu | head -10` to view the top CPU-consuming processes.
   - The abnormal process can be located: provide the conclusion and remediation recommendations.
   - It cannot be located: continue with more detailed investigation.
3. **Malicious process investigation**: overall CPU utilization is high but the sum of `%CPU` of the top processes clearly does not add up (that is, the consuming process is not visible). This is a typical characteristic of a mining trojan with hidden processes. Follow [guestos-malware-mining](utils/guestos-malware-mining.md) step by step.
   - Confirmed as a mining trojan: output the result according to the "Conclusion and Handling Recommendations" section of that document.
   - Malicious processes ruled out: continue.
4. Run `top -b -n 1` and check which field is high in the third line, `%Cpu`.
   - High user: user space. Run `perf top -p <pid>` to locate it.
   - High system: run `perf record -g && perf report` to locate kernel hotspots.
   - High hardirq: run `cat /proc/interrupts` to inspect hardware interrupts.
   - High softirq: run `cat /proc/softirqs` to inspect software interrupts.
   - High wait: run `ps aux | awk '$8 ~ /D/'` to view processes in D state, run `strace -p <pid>` to inspect system calls, and run `cat /proc/<pid>/stack` to inspect the call stack.
5. Observe the output of `top -b -n 1`: if CPU utilization is not high but many Tasks are running, frequent `execve`/`fork` may be occurring. Run `pidstat 1 5` to observe it.
