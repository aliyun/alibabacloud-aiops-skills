# Event and Metric Codebook

Semantics for every identifier the diagnose report can surface. Event type
names, parameter names and enum values were verified against the official
`DescribeInstanceHistoryEvents` API documentation; metric names were
verified live against the CloudMonitor metadata for the ECS namespace.

## System-event types (EventType.Name)

| Event type | Meaning | Relevance to an "unexpected reboot" |
| --- | --- | --- |
| `InstanceFailure.Reboot` | instance rebooted because of an instance (guest OS) fault | THE protective reboot: the platform detected an inside-guest failure and restarted the instance. Not a platform malfunction. |
| `SystemFailure.Reboot` | instance rebooted because of a system (host/hardware) error | platform-side incident; state the event id and times as evidence, recommend a console check of related notices |
| `SystemMaintenance.Reboot` | reboot scheduled for host maintenance | planned operation; explain "set time, known window", check the maintenance notification switch |
| `SystemMaintenance.Redeploy` | redeployment scheduled for host maintenance | for local-disk instances this means the local disks will be reinitialised and their data erased; see redeploy wording below |
| `SystemFailure.Redeploy` | forced redeployment after a system error | same local-disk data-loss warning applies |
| `SystemFailure.Delete` | instance released because creation failed | lifecycle noise for this tier; explain and route to support |
| `InstanceExpiration.Stop` / `InstanceExpiration.Delete` | subscription expired: stopped, then released | planned lifecycle; renewal guidance (see playbook family E) |
| `AccountUnbalanced.Stop` / `AccountUnbalanced.Delete` | account in arrears: stopped, then released | billing area; route to account/billing handling, this skill does not diagnose charges |

## InstanceFailure.Reboot semantics (verified wording)

The platform sends this system event when it detects an inside-guest
failure, including: out-of-memory conditions, blue-screen style crashes,
system hangs, a kernel panic, or a runaway serial-log storm. The event is a
SYMPTOM RECORD: it proves the OS went down at time T and that the platform
restarted it; it does not by itself name the offending process.

Customer-facing framing that matches the verified support wording:

* The automatic reboot is protective recovery, not damage: the machine was
  already unusable, and the platform brought it back.
* A reboot destroys the fault scene. Without a kernel crash dump (kdump) or
  atop history, "which process did it" may be unanswerable after the fact -
  say so honestly and set up the instruments for next time.

## Event lifecycle statuses (EventCycleStatus.Name)

| Status | Meaning |
| --- | --- |
| `Scheduled` | event published, awaiting execution or user response |
| `Inquiring` | awaiting user authorization/feedback |
| `Executing` | in progress |
| `Executed` | completed |
| `Avoided` | avoided (e.g. instance migrated away) |
| `Failed` | execution failed |
| `Canceled` | cancelled |

The events API defaults to FINISHED events (Avoided / Executed / Canceled /
Failed) only, and finished history is queryable for the last 30 days. The
scripts pass every status explicitly so pending `Scheduled` / `Inquiring`
redeployment events are not missed; report that limitation when the
customer references an incident older than 30 days.

## Redeploy and local-disk wording (verified support wording)

For a redeployment event on an instance with local disks:

* "A hardware risk has been detected on the host carrying your instance;
  the risk may cause a crash and local-disk data loss at any time. The
  migration is completed by redeploying the instance and typically takes
  15-20 minutes. Local SSD/HDD disks will be reinitialised by the system
  during the redeploy: data on them will be erased. The instance id and
  private/public IP addresses remain unchanged."
* Local disks cannot be snapshotted. Backup must happen INSIDE the guest
  before the redeploy window: attach a cloud disk and copy, transfer over
  the private network to another pay-as-you-go instance on the same
  vSwitch, or push to object storage. The vSwitch id is printed by the
  diagnose report.
* Very large local volumes (tens of TB) over small uplinks may not finish
  in the notice window; that sizing conversation belongs to a human
  engineer, not to this skill.

## Maintenance attributes (post-crash recovery behaviour)

`DescribeInstanceMaintenanceAttributes` returns, per instance:

* `ActionOnMaintenance.Value` - what the platform does after a detected
  failure: `AutoRecover` (reboot/repair the instance automatically; the
  supported set on many types also lists `Stop`, meaning "stay stopped and
  wait"). A customer who did not expect a self-reboot may find
  `AutoRecover` here.
* `NotifyOnMaintenance` - whether the customer asked to be notified of
  maintenance events; `false` explains "happened silently".
* Changing either value is a console or API write action and stays manual:
  see the verified console guide
  https://help.aliyun.com/zh/ecs/user-guide/modify-instance-maintenance-attributes.md

## CloudMonitor metric set (namespace `acs_ecs_dashboard`, period 300s)

All names below verified live; the aggregation column is the datapoint field
the scripts read.

| Metric | Aggregation | Meaning | Source |
| --- | --- | --- | --- |
| `CPUUtilization` | Average | vCPU utilisation percent | hypervisor side, always present |
| `memory_usedutilization` | Average | guest memory utilisation percent | requires the in-guest monitoring agent; empty datapoints mean the agent is absent or was not running at that moment |
| `load_1m` | Average | guest 1-minute load average | requires the in-guest monitoring agent |
| `DiskReadIOPS` / `DiskWriteIOPS` | Average | IO operations per second | hypervisor side |
| `DiskReadBPS` / `DiskWriteBPS` | Average | bytes per second | hypervisor side |
| `DiskReadWriteIOPSUtilization` | Value | IOps as percent of the instance-spec ceiling | hypervisor side; the "storage performance reached the spec ceiling" notice area |
| `DiskReadWriteBPSUtilization` | Value | throughput as percent of the instance-spec ceiling | hypervisor side |

Interpretation rules stated for the customer:

* `DescribeMetricLast` answers "what is it now" (the most recent datapoint
  per metric), not "what was it at 09:00". For the incident window itself,
  open the console monitoring charts - the historical window is where
  support engineers looked in real tickets. The report flags this
  limitation; do not back-fit remembered curves.
* A spec-ceiling utilisation near 100% while `df -h`/`df -i` inside the
  guest show free space settles the "hard drive full?" misconception: the
  ceiling is about speed (IOPS/bandwidth vs the instance type limit), not
  about capacity.
* Memory metrics come from the guest agent: on an instance without it,
  `memory_usedutilization` returns no datapoints. That absence must be
  reported as an evidence gap, exactly like a failed query.

## API name vs permission name (the CMS trap)

**The name trap** - the CloudMonitor query action is `DescribeMetricLast`;
its RAM permission point is `cms:QueryMetricLast`. The two differ; granting
the API name would still deny. Verified against the batch permission
checklist and a live call.
