# Documentation and console entry points

Only the pages and console routes that this problem tier actually relies on are listed.
Quote the canonical link, not a legacy document id, so a customer does not land on a stale
copy of the same content.

## 1. History recording and process attribution

| Topic | Link | When to send it |
|---|---|---|
| Use the atop tool to monitor Linux system metrics | https://help.aliyun.com/zh/ecs/user-guide/use-the-atop-tool-to-monitor-linux-system-metrics | the customer needs to know which process issued the I/O on the next occurrence; also covers tuning the sample interval and log retention |
| How to use the Linux atop monitoring tool | https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools | same subject, the short form |
| Query and analyse the I/O load of a Linux instance | https://help.aliyun.com/zh/ecs/support/query-and-case-analysis-linux-io-load | the customer can still reach the instance through the console and wants to look now |
| Troubleshoot high disk I/O load on Linux | https://help.aliyun.com/zh/ecs/support/troubleshooting-and-solution-for-high-disk-i-o-load-in-linux-system | the load is long term rather than a single spike |

A legacy document id circulates for the atop topic in older material. Use the two links above
so one subject does not produce two competing answers.

Tuning note worth giving together with the link: the default sample interval is coarse enough
that a short spike is never recorded. A one minute interval locates the cause, and the
retention generation count is what keeps the log volume down.

## 2. Memory pressure behind the I/O

| Topic | Link | When to send it |
|---|---|---|
| Configure a swap partition on a Linux instance | https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance | memory exhaustion is pushing paging traffic onto the disk |
| Configure virtual memory for a Windows instance | https://help.aliyun.com/zh/ecs/support/how-to-configure-virtual-memory-for-windows-instances | a Windows instance reports that the page file is too small, or an application cannot start |
| Log on to an instance by using VNC | https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc | to separate a wedged instance from a connectivity problem |

## 3. Disk classes, ceilings and modification

| Topic | Link | When to send it |
|---|---|---|
| Block storage performance | https://help.aliyun.com/zh/ecs/user-guide/block-storage-performance | the authoritative ceiling table; check every figure quoted from `disk-performance-baseline.md` against this page |
| Block storage performance, legacy document id | https://help.aliyun.com/document_detail/25382.html | the same table as quoted by an automated diagnosis card |
| Test the IOPS performance of an ESSD | https://help.aliyun.com/zh/ecs/user-guide/test-the-iops-performance-of-an-essd | the customer benchmarked with a synchronous, shallow-queue script and got a low number |
| Change the category of a disk | https://help.aliyun.com/zh/ecs/user-guide/change-the-category-of-a-disk | an upgrade direction is justified by sustained ceiling touches; the modification limits section is on this page |
| ESSD AutoPL disks | https://help.aliyun.com/zh/ecs/user-guide/essd-autopl-disks.md | capacity and performance need to be configured separately |
| Regional ESSD disks | https://help.aliyun.com/zh/ecs/user-guide/regional-essd-disks.md | a PL1 data disk is being considered for that class |
| ESSD PL-X disks | https://help.aliyun.com/zh/ecs/user-guide/essd-pl-x-cloud-disk.md | a higher class is asked for; state that this class is invitation-based |
| Instance family overview | https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families.md | the instance type, not the disk, binds the storage ceiling |
| Previous-generation local SSDs | https://help.aliyun.com/zh/ecs/user-guide/previous-generation-disks-local-ssds | only when the customer asks about that generation; label the generation explicitly, these numbers are not local HDD figures |
| Change the instance type of a subscription instance | https://help.aliyun.com/zh/ecs/user-guide/change-the-instance-types-of-subscription-instances | memory or the instance-side storage ceiling is the binding limit |

## 4. Monitoring and alerting

| Topic | Link | When to send it |
|---|---|---|
| Install or uninstall the CloudMonitor agent | https://help.aliyun.com/zh/cms/cloudmonitor-1-0/user-guide/install-and-uninstall-the-cloudmonitor-agent-for-cpp | disk or memory series are empty; this is a collection gap, not health |
| Manage notification policies | https://help.aliyun.com/zh/cms/cloudmonitor-1-0/user-guide/manage-notification-policies | a window has been explained and judged harmless; muting comes after that judgement, never instead of it |
| Host monitoring page | https://cloudmonitornext.console.aliyun.com/hostMonitor | where the customer reads the per-disk and per-process values themselves |
| Linux system performance optimisation | https://help.aliyun.com/document_detail/41224.html | a recurring window is confirmed harmless and the customer wants it reduced |
| Windows system performance optimisation | https://help.aliyun.com/document_detail/2879304.html | same, on Windows |

Teach the reading path with the link: instance monitoring, then basic monitoring and
operating-system monitoring, then switch the aggregation view to the maximum, then compare
the window that matches the reported time.

## 5. Restore points and adjacent products

| Topic | Link | When to send it |
|---|---|---|
| Create a snapshot | https://help.aliyun.com/document_detail/25455.html | before a restart, a performance level change or any customer-performed modification |
| Snapshot billing | https://help.aliyun.com/document_detail/56159.html | always together with the previous line; the cost is part of the decision |
| Snapshots overview | https://help.aliyun.com/zh/ecs/product-overview/snapshots-1 | the current form of the same subject |
| Delete a snapshot | https://help.aliyun.com/document_detail/128131.html | after the change succeeded, so unused restore points stop billing |
| Instance stop and restart behaviour | https://help.aliyun.com/zh/ecs/support/when-an-ecs-instance-is-stopped-or-restarted-in-the | the customer thinks a restart is hung; the normal window belongs to `alibabacloud-ecs-instance-state-diagnosis` |
| Anti-ransomware backup consuming resources | https://help.aliyun.com/zh/security-center/user-guide/anti-ransomware-backup-takes-up-high-memory-resources | a fixed daily window matches a backup client path; this belongs to Security Center |
| Cloud Backup console | https://hbr.console.aliyun.com | a full-disk backup job explains the window; the task log belongs to that product |
| Cloud service diagnosis tasks | https://health.console.aliyun.com/diagnosis-task/list?type=scene | the customer received an automated diagnosis card and wants the full report |

## 6. Known gaps in this index

These are open items, not omissions to fill in by guessing. State them when they bound a
conclusion.

1. No published page is carried here for the storage performance alert name and its reason
   codes. The codes were recognised from an event payload supplied by a customer, so the
   skill interprets a pasted payload instead of reading the event store.
2. The per-capacity ceiling formulas and performance level figures have to be re-checked
   against the block storage performance page before being quoted as a commitment; see the
   provenance tags in `disk-performance-baseline.md`.
3. No published page is carried here for the kernel paging thread and out-of-memory
   behaviour behind the memory-to-I-O chain. Present it as practitioner interpretation,
   supported by the readings, not as a cited document.
4. Some local HDD generations publish no IOPS guidance figure. Say that plainly and never
   substitute a previous-generation local SSD number.
5. No Windows command for page file size, disk queue or latency is exposed, because none was
   verified; the Windows readings in this package cover volumes, drives and directory
   listings only.
6. The CloudMonitor namespace and metric names for per-disk IOPS, throughput and latency are
   not carried here, which is why the measurement step needs them explicitly.
7. No API is used to read diagnosis task results; the console link above is the entry point.
