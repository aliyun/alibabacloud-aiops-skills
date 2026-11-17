# Reboot Diagnosis Playbook

The eight failure families this tier sees, in frequency order from the
ticket evidence, with the identification chain, the honest limits of each
conclusion, and the wording that converged in real support work. All
conclusions must cite report evidence; where evidence cannot exist (no
kdump, no atop history, metrics only "latest"), the playbook says so.

## Family A - Platform-recorded crash reboot (event present)

Identify: `diagnose` lists an event of type `InstanceFailure.Reboot` or
`SystemFailure.Reboot` (semantics: [event-codebook.md](unexpected-reboot-diagnosis__event-codebook.md)).

Explain (verified support wording): the platform detected an inside-guest
failure - out-of-memory, blue screen, hang, kernel panic or a serial-log
storm - and issued a protective automatic reboot. The event is the symptom
record; the root cause lives in the guest at that timestamp.

Chain:

1. take the event publish time; confirm the customer's narrative against it
   ("the mail says 05:52, does that match when your site died?");
2. cross-check the monitoring area at that timestamp - console charts for
   the historical window (the report's latest-datapoint readings are
   context, not the incident itself);
3. gated guest verification: `df -h` and `df -i` to exclude capacity;
4. verdict wording: OOM is the single most frequent cause of this family;
   without kdump or atop history, name it as the most probable cause with
   medium confidence, never as a certainty.

Converge: "the machine came back by itself and the event says why it
rebooted; here is what we can and cannot prove about the cause; here is the
manual setup so the next one leaves a trace".

## Family B - Resource exhaustion hang (no event, "froze" narrative)

Identify: no crash event; customer describes unresponsive SSH/VNC,
recovered by a forced console restart; memory/CPU/load readings saturated
when the monitoring agent is present; instance specs small relative to the
workload (the report shows vCPU/memory from the instance-type query).

Reality checks from the tickets:

* "my workload is light" does not survive a spec comparison: a 2 GiB
  instance with containers already at ~1.5 GiB resident dies to any command
  (OOM with effectively no headroom and no swap);
* hung != crashed: without an event, the platform may simply have been
  unable to observe anything;
* php-fpm/mysql-style concurrency and protection-software process storms
  both land here; naming the process needs atop history, which usually does
  not exist yet - say so.

Chain: confirm window -> read the report's saturation evidence -> gated
`df -h` (swap storms hammer the disk too, keep capacity in view) -> advise,
as human actions: reduce concurrency, add memory (spec change is a purchase
decision), configure swap and container limits (guest configuration is
manual), deploy atop and enable kdump for next time.

Confidence rule: with agent metrics at the incident time, medium; without
them, low - "highly suspected memory exhaustion, not fully establishable"
is a good-faith conclusion and the tickets' own ceiling.

## Family C - Storage performance at the instance-spec ceiling

Identify: report shows `DiskReadWriteIOPSUtilization` or
`DiskReadWriteBPSUtilization` near 100%, and/or the customer quotes the
console notice about storage performance reaching the spec upper limit.

The misconception to defuse, in order: that notice is about SPEED (the
instance type's IOPS/bandwidth ceiling), not about the disk being nearly
FULL and not about memory. Prove "not full" with `df -h` / `df -i` (gated,
one call). High-frequency read/write windows (database backups, scheduled
jobs) are the usual trigger; in rare cases the saturation coexists with or
precedes an automatic reboot - tie any reboot claim back to a dated event
(A) rather than asserting causation.

Handoff: persistent IO performance work belongs to
`area:resource-bottleneck`; this skill only answers "did this
explain my reboot".

## Family D - Stuck in a power transition, misreported as a crash

Identify: report Status is `Stopping`/`Starting`/`Pending`; no crash event;
customer narrative "the server died while restarting".

Wording (verified support wording): a shutdown waits on guest processes to
exit; under load this legitimately takes ~8-15 minutes and is not a crash.
This skill stops at the identification; the state-machine itself belongs to
`area:instance-state-diagnosis` (see handoff matrix). If the
underlying story is still "memory was full before I rebooted" - both areas
coexist: state area handoffs, the B-branch stays here.

## Family E - Planned reboots, lifecycle notices and login illusions

Identify in the report:

* `SystemMaintenance.Reboot` / scheduled events / maintenance attributes
  (`ActionOnMaintenance`, `NotifyOnMaintenance=false` explains the silence):
  planned platform behaviour; console paths and the change guide are in
  [event-codebook.md](unexpected-reboot-diagnosis__event-codebook.md) (changing it is a manual write);
* `InstanceExpiration.*` / `AccountUnbalanced.*`: billing lifecycle, route
  to renewal/arrears handling, this skill does not diagnose charges;
* "the reboot happened exactly at the time I configured": scheduled
  restarts configured at purchase or through operations windows - give the
  console modification path (see renewal guidance in
  https://help.aliyun.com/zh/ecs/user-guide/renewal-change.md and flag that
  renewal-triggered and maintenance-triggered reboots are different
  mechanisms if the customer conflates them);
* Windows "rebooted but my program did not start": the desktop session
  never fully unlocked - services-style autostart, group policy for the
  lock screen, power sleep set to Never, and the optional Cloud Assistant
  service-keepalive plugin are documented MANUAL steps
  (https://help.aliyun.com/zh/ecs/user-guide/use-the-cloud-assistant-plugin-for-service-keepalive.md);
  none of these are auto-executed here;
* "cannot connect so it must have crashed": the report's public-IP/EIP
  fields close this cheaply - an instance with no public address cannot be
  reached directly from the internet; fix the access path before believing
  the crash story.

## Family F - Hardware-risk redeploy (crash warning + local-disk risk)

Identify: `SystemMaintenance.Redeploy` / `SystemFailure.Redeploy` in the
report (check ACTIVE statuses - these are easy to miss), and/or the
instance-type and disk queries showing local (ephemeral) storage.

Deliver, in this order: the redeploy mechanics (15-20 minutes, ids and IPs
unchanged, local disks wiped); the backup imperative (local disks cannot be
snapshotted - back up inside the guest first); the concrete backup context
from the report (vSwitch id for same-network transfer targets); and the
hard line that the redeploy/migration itself, and any commercial
adjustments, are human actions through the proper channels.

## Family G - Recoverability and backup gaps (post-crash anxiety)

The skill does not recover data. What it does automatically:

* state plainly what the crash evidence says about the disk's health;
* run the snapshot-first guard before any cleanup the customer plans
  (gated `create-snapshot`; local-disk refusal path);
* deliver the recoverability facts: no snapshot before the incident means
  the pre-crash state is not recoverable from platform copies; snapshots
  past their retention are irreversibly deleted; an auto-snapshot policy
  attached after the incident window would not have helped.

Cross-check the snapshot policy coverage in the console (this skill does not
query snapshot inventories - the API is outside its verified surface).
Restore-to-new-instance and mounted-old-disk rescue remain human procedures.

## Family H - The OS is alive: application faults wearing a crash costume

Identify: Running, health Ok, Cloud Assistant heartbeat fresh, no events -
yet the customer says "the server crashed".

Say it early with the evidence lines from the report, then triad-check:
can you log into the OS (SSH/VNC)? do the service ports listen (manual
`ss -lnt` or `netstat -ano`)? are the security group rules right? A 502 or
500 with a live instance is an application problem (the ticket corpus
includes a Node.js crash on malformed Host headers, a panel listening on a
nonstandard port, and a workload-driven overload that a reboot "fixed"
until it recurred within minutes). This skill does not debug application
code; third-party panels go to their vendor
(https://www.bt.cn/new/index.html), application bugs to the customer's
developers, with the guest evidence this skill can legitimately gather
(capacity, handles) handed over as context.

## Diagnosability readiness (close EVERY report with this)

| Instrument | Status the report can show | Manual setup |
| --- | --- | --- |
| crash event | present/absent via the events query | none needed |
| monitoring agent (memory/load metrics) | inferred from datapoints present/absent | install/enable the CloudMonitor agent (console guidance) |
| kernel crash dump (kdump) | invisible to cloud APIs; ask, or customer runs `systemctl is-enabled kdump` manually | https://help.aliyun.com/zh/ecs/user-guide/enable-or-disable-the-kernel-crash-dump-service-for-an-instance |
| atop history | invisible to cloud APIs; ask, or customer checks `/var/log/atop` presence manually | https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools |
| maintenance notification switch | visible via maintenance attributes | console path in event-codebook |
| backup coverage | disk categories visible; snapshot policies are NOT queried here | console snapshot policy page |

Rule: kdump and atop are ALWAYS delivered as documented manual steps (the
tickets' own standard: engineers advised, never installed, without explicit
on-machine authorization). This skill has no installer capability and must
not pretend otherwise.

## Report discipline

* Confidence is three-valued (high/medium/low) with the reason attached;
  "the evidence chain stops at X" is part of the conclusion.
* Timeline before theory: event times first (UTC, label it), metrics next,
  guest readings last, narrative corrections at the end.
* Misconception responses are scripted, not improvised: crash means the
  OS went down (protective reboot) not that the platform broke it; a
  performance-ceiling notice is not a disk-full notice; "cannot connect"
  is not a crash until the evidence says so; "restart fixed it" is not a
  diagnosis.
* Every auto-filled parameter is declared (query window default, metric
  period 300s, derived UID label).
* Nothing enters the report that did not come from a script call or a
  customer-pasted reading: no remembered instance ids, no invented
  percentages, no assumed regions.
