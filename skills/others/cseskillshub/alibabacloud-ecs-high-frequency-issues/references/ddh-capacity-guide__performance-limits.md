# Specification Performance Ceilings (Cluster C)

Rule-based answers for "the instance shows Running but is unresponsive", "SSH does
not return a banner", "Cloud Assistant fails", "VNC is not interactive", and "is
this a host problem or my workload". The mechanism is usually I/O throttling at the
specification ceiling, not a host failure.

Verification date: 2026-08 (per the tier requirements document). Per-spec IOPS /
throughput baselines are version-sensitive; re-verify against the official
instance-type and cloud-disk performance documentation before publishing.

## Mechanism: reaching the specification ceiling

- Every instance type and every cloud disk has a specification ceiling for IOPS and
  throughput (BPS). These ceilings are documented per instance type and per disk
  category.
- When a guest workload (for example heavy sequential reads from a batch / AI job)
  reaches the ceiling, I/O is throttled. While throttled, ALL guest processes that
  read or write block - so SSH may not return its banner, Cloud Assistant calls
  fail, VNC becomes unresponsive, and a reboot can hang in "Stopping", while the
  instance still shows as Running.
- This is throttling at the specification ceiling, NOT necessarily a host failure.
  A frequent customer misconception is "my internal monitoring shows nothing wrong,
  so it must be the platform". Guest-side and platform-side observation points
  differ: a guest tool reading `%util` may not reflect the platform's throttle
  decision.

## What this skill can and cannot confirm

- CAN (read-only): confirm the instance is Running via `DescribeInstanceStatus`;
  list the instance's cloud disks via `DescribeDisks`; read real per-disk IOPS /
  BPS / latency samples from `DescribeDiskMonitorData` for a recent window
  (start/end/period are printed with the reading, and only the returned values are
  quoted); explain the ceiling mechanism for the instance type / disk; and point
  the customer to the right CloudMonitor alarm plus the self-install steps for
  deeper guest history.
- NOT AVAILABLE: per-process guest I/O, guest-internal performance history, and any
  reading outside the queried cloud-disk monitor window. The customer reads those
  from the CloudMonitor chart in the console or from the guest's own atop / iostat
  output and can paste or screenshot them for interpretation. This skill never
  invents a reading: when no sample is returned it says so instead of estimating,
  and it does not declare "specification ceiling reached" without a measured
  reading to compare against the documented ceiling.

## Recovery and prevention (customer performs)

Recovery when an instance is unresponsive from throttling:
1. Wait for the burst to subside, or force-reboot from the console to recover.
2. A forced reboot carries the three-point risk notice: do it in a low-traffic
   period, stop applications and let data flush first, and create a snapshot backup
   first (snapshots are a paid feature).

Prevention:
1. Install the CloudMonitor agent to get instance-level metrics.
2. Add a process-level history tool (for example atop, with a higher sampling
   frequency) so the process that drove the I/O can be identified after the fact.
3. Subscribe to a "performance reached the specification ceiling" style alarm in
   CloudMonitor.
4. If the workload legitimately needs more IOPS / throughput, move to a higher
   instance type or a higher-performance disk category (a customer write action).

These are guidance steps only; this skill performs none of them and never enters
the guest.

## Distinguishing throttling from a host event

- If the customer also received a SystemMaintenance.Reboot / SystemFailure.Reboot
  notification, see host-events-and-maintenance.md - that is a host-driven event, a
  different area from a workload-driven ceiling.
- If the instance is Running, no host event was notified, and the symptom coincides
  with a heavy I/O workload, the ceiling mechanism is the most likely explanation.
  State it as the likely rule-based explanation, not as a confirmed host verdict,
  and point to CloudMonitor for evidence.

## Sources

- Official ECS instance-type and cloud-disk performance documentation (per-spec
  IOPS / throughput baselines; Alibaba Cloud Help Center - re-verify before
  publishing).
- Real support tickets in this tier (disk IOPS / BPS reaching the specification
  ceiling, the "Running but unresponsive" symptom, and the CloudMonitor agent plus
  atop prevention advice).
