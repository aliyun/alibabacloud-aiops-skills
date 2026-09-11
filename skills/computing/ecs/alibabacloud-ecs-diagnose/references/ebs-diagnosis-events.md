# EBS Performance Diagnosis Events Reference

## Overview

This document is the complete reference for all 14 diagnostic event types that the
EBS disk performance diagnosis service (`DescribeDiagnoseReport`) can report. Use it
to interpret the `Events` array in a diagnosis report and to fill the
【Disk Performance Diagnostics】 section of the ECS diagnostic report.

Events are organized into 5 categories:

1. **IOPS/Throughput Limits** — IO operations per second and bandwidth limits
2. **Configuration & Matching** — instance-disk configuration mismatches
3. **IO Quality Issues** — IO latency and quality problems
4. **Cost & Optimization** — cost efficiency and optimization opportunities
5. **Data Protection** — data safety and backup

---

## 1. IOPS/Throughput Limit Events

| EventName | Severity | Meaning | Recommended Action |
|-----------|----------|---------|--------------------|
| `InstanceIOPSExceedInstanceMaxLimit` | Warn | Total IOPS of all disks on the instance reached the instance's IOPS limit | `UpgradeInstance` — monitor business impact; upgrade to a higher instance type or distribute workload across instances |
| `InstanceBPSExceedInstanceMaxLimit` | Warn | Total bandwidth (BPS) of all disks reached the instance's bandwidth limit | `UpgradeInstance` — upgrade instance type or optimize application IO patterns to reduce bandwidth usage |
| `DiskIOPSExceedInstanceMaxLimit` | Warn | This disk's IOPS reached the instance's per-disk IOPS limit | Monitor business impact; upgrade instance type to raise per-disk limits, or distribute IO across multiple disks |
| `DiskBPSExceedInstanceMaxLimit` | Warn | This disk's bandwidth reached the instance's per-disk bandwidth limit | Monitor business impact; upgrade instance type, or use multiple disks to spread bandwidth requirements |
| `DiskIOPSExceedDiskMaxLimit` | Warn | Disk IOPS reached the disk's own specification limit | `UpgradeDisk` / `ExpandDisk` — reduce read/write frequency, upgrade disk type (e.g., ESSD PL0 → PL1/PL2/PL3), or expand capacity for capacity-scaled IOPS |
| `DiskBPSExceedDiskMaxLimit` | Warn | Disk bandwidth reached the disk's own specification limit | `UpgradeDisk` / `ExpandDisk` — batch data transfers, upgrade disk type, or expand capacity |

**Interpretation notes:**
- "Instance*" events indicate the **instance spec** is the bottleneck; "Disk*...DiskMaxLimit"
  events indicate the **disk spec** itself is the bottleneck — the remediation targets differ.
- Disk type IOPS reference: ESSD PL0 up to 10,000; PL1 up to 50,000; PL2 up to 100,000;
  PL3 up to 1,000,000.
- Occasional limit hits may be harmless; sustained or frequent hits with business impact
  warrant an upgrade.

---

## 2. Configuration & Matching Events

| EventName | Severity | Meaning | Recommended Action |
|-----------|----------|---------|--------------------|
| `DiskSpecNotMatchedWithInstance` | Warn | Combined disk specs exceed the instance's capacity, so disk performance is capped by instance specifications | `UpgradeInstance` — upgrade to an instance type matching disk capabilities, or redistribute disks across instances |

**Interpretation notes:** Compare total disk IOPS/bandwidth capability against the
instance's limits. Example: instance limit 20,000 IOPS / 300 MB/s with 3× ESSD PL1
attached (150,000 IOPS total capability) → disks can never reach their potential.

---

## 3. IO Quality Events

| EventName | Severity | Meaning | Recommended Action |
|-----------|----------|---------|--------------------|
| `DiskIOHang` | Warn / Critical | IO hang detected — file system experienced extremely high read/write latency, causing system instability or crashes | `InvestigateIOBottleneck` — check CloudMonitor latency/IOPS/bandwidth metrics; review application IO patterns; at OS level run `iostat -x 1`, check `dmesg`, monitor with `iotop` |
| `SlowIO` | Warn | Slow IO detected (latency ≥ 1 second) | `InvestigateSlowIO` — identify random vs. sequential and read vs. write patterns; check IOPS/bandwidth contention, CPU/memory pressure; review IO scheduler, mount options, queue depth |
| `DiskIONo4kAligned` | Info | Non-4K aligned IO operations detected, degrading disk IO efficiency | `OptimizeIOAlignment` — check alignment with `fdisk -l` / `parted ... align-check optimal 1`; create partitions at 1MiB boundaries; configure database/application block sizes to 4K multiples |

**Interpretation notes:**
- `DiskIOHang` at Critical severity requires **immediate** investigation and possible
  emergency intervention.
- These events pair well with the ECS Deep Diagnostics flow (Cloud Assistant) to run
  OS-level checks (`iostat`, `iotop`, `dmesg`).

---

## 4. Cost & Optimization Events

| EventName | Severity | Meaning | Recommended Action |
|-----------|----------|---------|--------------------|
| `CostOptimization` | Info | Provisioned performance exceeds actual workload, causing unnecessary cost | `ModifyDiskPerformance` / `ChangeDiskType` — for ESSD AutoPL reduce provisioned IOPS/bandwidth to actual needs; otherwise downgrade the performance tier; track long-term usage in CloudMonitor |
| `BurstIO` | Info | Burst IO occurred on the disk, potentially incurring burst performance fees (ESSD AutoPL / burst-capable disks) | `ConfirmBurstBehavior` — verify bursts match expected workloads (backups, batch jobs); if frequent, provision higher baseline performance; review burst charges in EBS billing |
| `BurstIOFeeSealing` | Info | Burst IO volume reached the burst performance fee cap; performance may be limited until the next billing cycle | `ReviewBurstCapacity` — check monthly burst usage vs. cap; if the cap affects business, increase provisioned IOPS or upgrade baseline performance |

**Interpretation notes:** These are informational, not failures. Example
cost-optimization signals: ESSD AutoPL provisioned at 50,000 IOPS but using only
5,000 → reduce to ~10,000; ESSD PL2 with minimal IO → downgrade to PL1/PL0.

---

## 5. Data Protection Events

| EventName | Severity | Meaning | Recommended Action |
|-----------|----------|---------|--------------------|
| `NoSnapshot` | Warn | No snapshot created for the disk for an extended period, posing data loss risk | `CreateSnapshot` — create an immediate snapshot and establish an automatic snapshot policy (ECS Console → Snapshots → Automatic Snapshot Policies) |

**Interpretation notes:** Check existing snapshots and create one via CLI if needed
(remember the unified User-Agent from `SKILL.md`).

> **[MUST] Recommend only, never execute:** The commands below are examples for the
> user to run manually. The ECS diagnostics skill MUST NOT execute resource-creation
> commands (e.g. `create-snapshot`) automatically; it may only recommend them. This
> keeps the skill consistent with the "does not create any cloud resources" constraint
> in `SKILL.md`.

```bash
# Example for the user to run manually — do NOT auto-execute in the skill
aliyun ecs describe-snapshots \
  --biz-region-id <region> --disk-id <disk-id> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"

# Example for the user to run manually — do NOT auto-execute in the skill
aliyun ecs create-snapshot \
  --biz-region-id <region> --disk-id <disk-id> \
  --snapshot-name "backup-$(date +%Y%m%d)" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id} skill-version/{skill-version}"
```

Best practices: snapshot before major changes; keep at least a weekly schedule for
important data; test restoration periodically.

---

## Event Response Priority

When multiple events are detected, prioritize as follows:

| Priority | Events | Response |
|----------|--------|----------|
| 1 — Critical (immediate) | `DiskIOHang` (Critical) | Investigate immediately; may require emergency intervention |
| 2 — High (act soon) | `SlowIO`, `DiskIOPSExceedDiskMaxLimit`, `DiskBPSExceedDiskMaxLimit`, `NoSnapshot` | Schedule optimization/remediation within 24–48 hours |
| 3 — Medium (monitor & plan) | `InstanceIOPSExceedInstanceMaxLimit`, `InstanceBPSExceedInstanceMaxLimit`, `DiskIOPSExceedInstanceMaxLimit`, `DiskBPSExceedInstanceMaxLimit`, `DiskSpecNotMatchedWithInstance` | Monitor business impact; plan capacity upgrades if performance is affected |
| 4 — Low (informational) | `CostOptimization`, `DiskIONo4kAligned`, `BurstIO`, `BurstIOFeeSealing` | Review during regular maintenance windows; optimize when convenient |

---

## Related Documentation

- [EBS Performance Optimization Guide](https://www.alibabacloud.com/help/en/ebs/user-guide/performance-optimization)
- [ESSD Performance Specifications](https://www.alibabacloud.com/help/en/ebs/product-overview/essd)
- [CloudMonitor Disk Metrics](https://www.alibabacloud.com/help/en/cloud-monitor/user-guide/disk-monitoring)
- [Snapshot Best Practices](https://www.alibabacloud.com/help/en/ecs/user-guide/snapshot-overview)
