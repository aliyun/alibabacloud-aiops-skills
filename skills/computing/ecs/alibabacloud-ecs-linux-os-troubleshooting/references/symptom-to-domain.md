# Customer symptom → phenomenon domain routing

Narrow the **natural-language symptom** in the user request or ticket to **one phenomenon domain**. All phenomenon domains and unique identifiers are subject to [`phenomenon-domain.md`](phenomenon-domain.md). This document only provides **classification decisions** and does not repeat the full table.

## 1. Clarify the symptom first (then classify it)

At minimum, distinguish the following dimensions (ask follow-up questions first if information is insufficient):

| Dimension | Description |
| --- | --- |
| **Instance status** | Obtain it by calling `DescribeInstances` |
| **Scope** | Single instance / multiple instances; whether it always reproduces; start/end time or whether it is related to changes or restarts |
| **Channel** | Console status (Starting/Running); whether VNC works; whether SSH works; whether Cloud Assistant can execute commands |
| **Network direction** | From outside to the instance service port, from the instance to the Internet/metadata, internal-network connectivity only, etc. |
| **Manifestation** | Original error text, monitoring metrics (CPU/load/memory/disk/network BPS and packet-level symptoms) |

## 2. Phenomenon domain categories

Select the category that is closest to the customer's description, then go to the corresponding subsection to identify the subdomain.

- **The instance is stuck in Starting / system cannot start / black screen / stuck at grub·systemd·emergency** → see **§3 Startup issues**
- **Cannot connect / logon failed / disk damage / clock exception / network unreachable** → see **§4 Usage issues**
- **Crash, panic, automatic restart / hang, soft lockup, unresponsive** → see **§5 Crash or hang issues**
- **High CPU, high load, high memory/OOM, high disk IO, slow network/packet loss/retransmissions/latency/bandwidth saturated** → see **§6 Performance issues**
- **Configuration change does not take effect** (password, key pair, user-data, secondary ENI, cloud disk attach/detach, online expansion) → see **§7 Console instance configuration not taking effect**

If unsure, open [`phenomenon-domain.md`](phenomenon-domain.md) and classify by referring to **Typical symptoms**.

## 3. Startup issues

| What customers often say | Main phenomenon domain document |
| --- | --- |
| The instance has been stuck in Starting for a long time, and the console instance status shows `Starting` | [`instance-stuck-starting.md`](instance-stuck-starting.md) |
| The console instance status is already `Running`, but the system cannot start / black screen / stuck at grub·systemd·emergency | [`guestos-not-running.md`](guestos-not-running.md) |

## 4. Usage issues

| What customers often say | Main phenomenon domain document |
| --- | --- |
| Partition table damage, mount failure, file system errors, abnormal data disk recognition | [`disk-fs-damaged.md`](disk-fs-damaged.md) |
| Time jumps, NTP exceptions | [`clock-abnormal.md`](clock-abnormal.md) |
| Cannot access the Internet from inside the instance / cannot curl 100.100.100.200 | [`internal-network-failed.md`](internal-network-failed.md) |
| VNC black screen / cannot connect | [`vnc-login-failed.md`](vnc-login-failed.md) |
| SSH cannot connect | [`ssh-login-failed.md`](ssh-login-failed.md) |

## 5. Crash or hang issues

| What customers often say | Main phenomenon domain document |
| --- | --- |
| Crash, panic, automatic restart | [`system-crash.md`](system-crash.md) |
| Hang, frozen system, stuck, soft lockup, unresponsive | [`system-hang.md`](system-hang.md) |

## 6. Performance issues

| What customers often say | Main phenomenon domain document |
| --- | --- |
| High CPU usage | [`cpu-high.md`](cpu-high.md) |
| High CPU but the consuming process is not visible, mining or infection suspected | [`cpu-high.md`](cpu-high.md) |
| High load | [`load-high.md`](load-high.md) |
| High memory, OOM | [`memory-oom.md`](memory-oom.md) |
| Abnormally high IOPS, high disk utilization | [`disk-iops-high.md`](disk-iops-high.md) |
| Read/write throughput or IOPS does not reach the expected instance specification | [`disk-perf-unexpected.md`](disk-perf-unexpected.md) |
| Packet loss | [`network-packet-loss.md`](network-packet-loss.md) |
| Many retransmissions | [`retransmit-high.md`](retransmit-high.md) |
| High latency, high RTT | [`network-latency-high.md`](network-latency-high.md) |
| Bandwidth/traffic saturated or throughput below expectations | [`network-perf-unexpected.md`](network-perf-unexpected.md) |

## 7. Console instance configuration not taking effect

| What customers often say | Main phenomenon domain document |
| --- | --- |
| Online password reset in the console does not take effect | [`password-reset-failed.md`](password-reset-failed.md) |
| user-data / initialization script failed | [`userdata-failed.md`](userdata-failed.md) |
| Still using the old key after binding a key pair | [`ssh-keypair-not-applied.md`](ssh-keypair-not-applied.md) |
| Secondary ENI was added but is unreachable/no route inside the instance | [`secondary-eni-unavailable.md`](secondary-eni-unavailable.md) |
| Cloud disk is not visible in the OS after attach/detach, or cannot be detached | [`disk-attach-detach-failed.md`](disk-attach-detach-failed.md) |
| Capacity does not change in the system after console expansion | [`disk-expand-failed.md`](disk-expand-failed.md) |

## 8. When uncertain

1. In [`phenomenon-domain.md`](phenomenon-domain.md), perform a second match by **Typical symptoms** and **Concept explanation**.
