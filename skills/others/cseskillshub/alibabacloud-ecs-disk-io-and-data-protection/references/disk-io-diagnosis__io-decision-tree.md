# I/O diagnosis decision tree

Ordered gates. Work them in sequence and stop at the first one that resolves the case.
Every branch names the evidence it needs; if that evidence is unavailable, say so in the
report instead of guessing.

## Gate 0 - Settle the axis before diagnosing

The customer describes a symptom, not a root cause. Four look-alike axes get routed away,
because diagnosing them here produces the wrong fix:

| What the customer says | What it usually is | Route |
|---|---|---|
| "the disk is full", "no space left", "cannot write, disk is full", "inode exhausted", "help me clean up" | capacity or inode usage, not performance | `alibabacloud-ecs-disk-capacity-diagnosis` |
| "I extended the disk but the size is still the old one", "the partition is smaller than the disk" | the partition or file system was never grown | `alibabacloud-ecs-disk-expand-diagnosis` |
| "the instance will not come up", "it is stuck while going down", "a reboot never finished", "mount entries break the boot" | instance lifecycle and boot configuration | `alibabacloud-ecs-instance-state-diagnosis` |
| "SSH is refused", "port 22 does not answer", "the panel login fails", "wrong password" | connectivity, credentials or security group | manual connectivity handling; this skill only judges whether I/O wedged the machine |
| "the backup job is stuck", "anti-ransomware client", "refund", "downgrade", "why am I billed", "suspected mining or attack" | another product's task or a commercial process | manual support with the owning console |

Two traps seen repeatedly:

- An alert rule **named** "disk space" whose metric is a per-device utilisation series. The
  rule name is a label the customer chose; read the metric identifier before believing the
  name.
- "The disk is full" said by a customer whose real problem is an IOPS ceiling. Space usage
  and I/O load are separate axes and both are checked with `disk-usage` plus the ceiling
  table, never by assumption.

If the complaint mixes both ("the query is slow and the disk says full"), answer capacity
first and hand that part off, then keep the performance part here.

## Gate 1 - Is the instance wedged right now

Signal: SSH, VNC and any management panel are **all** unusable at the same time. That is a
wedged instance, not a login problem.

- Reading cloud data while the guest is wedged produces gaps or stale values; state this.
- The recovery sequence is a manual one and it belongs to the customer: take a snapshot,
  stop the database or any write-heavy service so buffered data reaches the disk, then
  restart from the console. A restart issued while writes are in flight is a data-loss
  path.
- Expect a restart of a busy instance to take several minutes before it is usable again,
  and that a forced stop is a harsher operation than a normal one.
- After recovery, install a history recorder; otherwise the next occurrence is again
  unexplainable.

## Gate 2 - Compute the specification baseline per disk

From `DescribeDisks` take `Category`, `PerformanceLevel`, `Size` for **every** disk of the
instance, then compute the ceiling per `disk-performance-baseline.md`.

- System disk and data disks are judged separately. Never merge them into one sentence.
- The effective ceiling is `min(disk ceiling, instance ceiling)`. When the instance type is
  what binds, raising the disk performance level buys nothing and the instance has to be
  upgraded in the same step. Say which of the two bound.
- Report the ceiling as a number the customer can recompute, e.g.
  `min(10000, 1800 + 12 x 501 GiB) = 7812 IOPS`.

## Gate 3 - Check that the readings are trustworthy

Before comparing anything:

1. **Host agent present?** Empty disk or memory series almost always means the CloudMonitor
   host agent is missing or broken. That is a collection gap, not evidence of a healthy
   instance. Guide the customer through the agent installation page.
2. **Which page?** Basic monitoring and operating-system monitoring carry different series;
   a customer quoting one while you read the other produces a false contradiction.
3. **Aggregation view.** Peaks require the "maximum" view. An average of a 5-minute window
   can hide a saturated minute completely.
4. **Granularity.** The smallest published granularity is 15 seconds. A one-second burst
   that touched the ceiling can be invisible in the charts. So "the console never shows a
   peak" does **not** disprove an alert that fired; it only proves the peak was shorter than
   the granularity.
5. **Under a freeze the agent itself suffers.** When the instance was wedged at the moment of
   interest, the agent was likely unable to report, so the gap in the curve is expected.

## Gate 4 - Compare, then classify into exactly one of three states

| State | Signal | What to tell the customer |
|---|---|---|
| Not throttled | measured peak far below the computed ceiling | the disk was not limited by its own specification. Look for a threshold that was never calibrated per disk type and capacity - a self-built monitoring template with one limit for all disks raises constant false alarms |
| Partially loaded | between the two | ceiling limits alone do not explain the symptom; keep investigating |
| Occasional spike | brief touches, otherwise normal | review the business side first and observe with a history recorder; do not start by buying a bigger disk |
| Sustained ceiling | repeated or continuous touches | a higher performance level or a larger instance is justified, with the impact and billing stated |

Never state a single cause while more than one state is open across the disks.

## Gate 5 - Test the memory chain before blaming the disk

The most frequent root cause on this axis is not the disk. Memory exhaustion surfaces as
disk I/O saturation, because the kernel pages out, or a process starts reading straight from
the volume, and IOPS and throughput jump within one sampling interval.

Signals that point here:

- I/O spikes with no matching business action.
- A small instance (low memory) running a database, a PHP or application server pool, a
  Node process or a container runtime.
- A Windows instance where an application cannot even open Task Manager, plus a message that
  the page file is too small. Windows can require a page file of adequate size even when a
  quarter of physical memory is free; "there is RAM left" does not rule the page file in or
  out.
- A customer reporting "the disk is broken" while free space is normal and memory is nearly
  empty.

How to confirm it without a per-process tool:

- Read the memory series on the operating-system monitoring page for the same window as the
  I/O peak.
- Ask whether a swap area exists and how large it is. Absent or tiny swap turns any memory
  spike into disk I/O and, beyond that, into an out-of-memory kill.
- A swap area is a mitigation that trades latency for stability; it is not a substitute for
  enough memory.

Corrections that belong in the reply:

- **Adding IOPS does not fix memory exhaustion.** Upgrading the disk first is the classic
  wasted purchase; several cases came back after an upgrade with the same symptom.
- **A per-process I/O cap is not available** on a normal ECS instance; the practical
  mitigations are swap, fewer concurrent workers, or more memory.
- **Large log files do not saturate IOPS by themselves.** Size on disk is a capacity matter;
  only the write rate is an I/O matter.

## Gate 6 - Look for a scheduled job when the timing repeats

Feed every alarm timestamp to the diagnosis run; clustering at a similar time of day across
days is the signal.

Common owners of a fixed window, in the order they get confirmed:

| Candidate | How it shows | Where it belongs |
|---|---|---|
| Snapshot or backup policy | a burst confined to the policy's start time, often on one specific disk | console policy; this skill can state the correlation |
| Security-centre anti-ransomware host backup | a client path under the agent directory, daily window on one instance only | Security Center console; hand off. Disabling the decoy-capture switch does **not** stop the backup job; the per-host protection policy is what controls it |
| Cloud Backup full-disk job | hours of sustained throughput and IOPS where history shows minutes | Cloud Backup; its server-side task log is not visible here |
| Distribution metadata timer | a package cache refresh at boot or on a systemd timer | hand the customer the manual step to inspect timers |
| Application cron or database job | window aligned with a business schedule | customer side |

Reducing alert noise is legitimate only **after** the window is explained and judged harmless,
by muting that specific alarm through a notification policy. Muting first is not a fix.

## Gate 7 - Benchmarks and "performance does not match what I bought"

- A benchmark that issues one I/O at a time per worker, with a shallow queue and
  synchronous writes, cannot reach a storage ceiling. Measuring a ceiling requires an async,
  deep-queue workload. A low number from such a script says nothing about the disk.
- Before accepting a benchmark result, check whether the benchmark window is the window in
  which the platform reported a ceiling touch. If IOPS never reached the ceiling while
  throughput did, the workload was bound by throughput, and the IOPS figure is simply not
  comparable.
- The catalogue maximum for a disk family applies only at a large capacity. Small volumes sit
  proportionally below it. This mismatch between a headline number and a capacity-derived
  guarantee is the single most common source of "advertised performance is a lie" disputes.
- Snapshots do not degrade the performance of the disk being snapped. That belief comes up
  often enough to be answered directly.
- Some newer local HDD generations publish **no** IOPS guidance figure. Report that honestly.
  Never borrow a previous-generation local SSD number; that substitution was corrected by a
  customer on the spot and it invalidates the whole analysis.
- A benchmark or stress test against a production volume can destroy data if the device name
  is wrong. Never drive it from this skill; state the prerequisites instead: snapshot taken,
  business at low tide, device name verified twice.

## Gate 8 - What the cloud side cannot see

Say these out loud in every report, because a silent gap reads as a clean bill of health:

- Which process issued the I/O. Linux keeps no historical per-process resource record, so a
  recorder has to be installed before the next occurrence.
- Whether swap exists, and its size.
- Application I/O model: sync or async, queue depth, block size.
- Database slow-query content.
- Another product's server-side task log.
