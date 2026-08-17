# Troubleshoot packet loss during network send/receive

## Determine whether this is a GuestOS issue

1. Use `DescribeInstances` to obtain the instance type, and use `DescribeInstanceTypes` to obtain the list of shared instance types. Determine whether the current instance type is a shared type.
   - Yes: no further troubleshooting is required, because shared instance types do not provide a performance SLA.
   - No: continue.
2. Confirm with the user whether packets pass through the GuestOS network stack.
   - Not reached: this is not a GuestOS issue.
   - Reached: continue.
3. Use `DescribeSecurityGroupAttribute` to query security group rules, and confirm with the user whether the security group rules are configured correctly.
   - Incorrect configuration: packets may be blocked. This is not a GuestOS issue.
   - Correct configuration: continue.

## Troubleshooting process inside GuestOS

### Related components

- Firewall (iptables/nftables, firewalld/ufw)
- Soft interrupt load
- sysctl parameter configuration
- Third-party network drivers

### Problem diagnosis

First, confirm with the user whether the packet-loss symptom requires manual reproduction or whether packet loss is continuous. If reproduction is required, ask the user to provide the reproduction command, then run validation to confirm that it is reproducible. If it cannot be reproduced, inform the user and end the process directly. **Note**: the reproduction command may block the shell, so handle that scenario correctly.

Then start troubleshooting:

1. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the network rate trend, confirm whether packet loss occurs continuously, and identify the abnormal time window.
2. Run `dmesg -T` to determine whether there is a call trace for a network queue hang or other network anomalies.
   - If yes, investigate further based on the clues.
   - If no, continue.
3. Run `cat /proc/net/udp` and observe whether the last-column drops value increases.
   - If yes, UDP packet loss exists.
   - If no, continue.
4. Run `tc qdisc show` to check whether any simulated packet-loss rules exist.
   - If yes, provide the conclusion.
   - If no, continue.
5. Run `ip xfrm policy show` and `ip xfrm state show` to check whether any network security policies are blocking traffic.
   - If yes, provide the conclusion.
   - If no, continue.
