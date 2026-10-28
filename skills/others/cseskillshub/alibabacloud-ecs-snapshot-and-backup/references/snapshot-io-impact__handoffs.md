# Boundary map: what this tier does not diagnose

The skill answers one question - whether a performance symptom lines up with
snapshot activity. Everything else is **identified and handed off**, not
attempted. The agent must still run enough of the read chain to justify the
hand-off; a hand-off asserted without evidence is as much a guess as a
diagnosis made without one.

The list below is the same list the entry script prints with its B3 verdict, so
the report and this file cannot drift apart.

## 1. Hand-off table

| Symptom that is *not* this tier's | Route to | Why it belongs there |
|---|---|---|
| Disk full, inode exhaustion, cleanup or space release | `alibabacloud-ecs-disk-capacity-cleanup` | Capacity axis. This tier never proposes deleting anything. |
| Slow disk I/O with no snapshot overlap, performance below spec | `alibabacloud-ecs-disk-io-diagnosis` | General performance axis. This tier only decides whether snapshots are a contributor. |
| A resize that never took effect, partition or file-system growth | `alibabacloud-ecs-disk-expand-diagnosis` | Expansion axis. |
| Instance stuck starting, stopping or rebooting | `alibabacloud-ecs-instance-state-diagnosis` | Instance lifecycle axis; recovery there involves actions this tier must not touch. |
| Snapshot creation failure, stuck progress, policy configuration | `alibabacloud-ecs-snapshot-policy-check` | The snapshot's own health. This tier's subject is a *successful or running* snapshot's effect on the business. |
| Snapshot fees, quota, deletion or cleanup | `alibabacloud-ecs-snapshot-billing-cleanup` | Billing and retention axis. |
| Restoring a disk or rolling the system back to a snapshot | `alibabacloud-ecs-disaster-recovery-snapshot` | Recovery axis, and an irreversible write. |

## 2. Overlapping entry points

Two neighbouring tiers can be reached from the same customer sentence. Settle it
before routing, or one ticket gets three conflicting reports.

**"The server is slow" (no mention of snapshots).** This tier is the wrong first
stop: it looks for snapshot overlap, and with no snapshot running it will return
B3 and hand off anyway. Ask one question - *does the slowdown follow a schedule,
a backup window, or a snapshot you just started?* A yes makes this tier correct.
A no, or "it is always slow", goes to `alibabacloud-ecs-disk-io-diagnosis`.

**"Slow disk I/O."** Both this tier and `alibabacloud-ecs-disk-io-diagnosis`
read disk metrics. The discriminator is the overlap table, and it is objective:

| `DescribeSnapshots` result inside the symptom window | Owner |
|---|---|
| Tasks overlap, and readings sit at the ceiling | This tier concludes B1 and stays |
| Tasks overlap, readings stay low | This tier concludes B2, then hands the residual to the performance tier |
| Nothing overlaps | The performance tier owns it; this tier reports B3 and hands off |

State the overlap result when handing off. It is this tier's whole contribution
to the next one, and repeating the query downstream wastes the customer's time.

## 3. How a hand-off is worded

A hand-off is a finding plus a destination, never a refusal. Use this shape:

> I checked the snapshots on `<instance or disk id>` in `<region>` for
> `<window>`. `<finding: N tasks overlapped / nothing overlapped>`. That puts
> the problem outside this check - the tier for `<axis>` is
> `<target skill name>`, and the evidence above is what it will need first.

Two rules:

1. **Name the evidence you already gathered.** The next tier must not have to
   re-run the reads this one already did.
2. **Do not diagnose the destination tier's subject in passing.** Spotting that
   a volume is 96 per cent full is a legitimate observation while reading disk
   metadata; recommending what to delete is not this tier's call.

## 4. Requests to decline outright

These are outside both the tier's scope and the package's operation classes, and
they stay manual no matter who asks:

- Deleting, rolling back, or overwriting anything - snapshots, disks,
  partitions, or file systems.
- Formatting, partitioning, or resizing a disk.
- Stopping, restarting, or rebooting an instance, including "to make the
  snapshot finish".
- Changing an auto snapshot policy, its schedule, or its retained count. This
  tier reads the resulting tasks; the change is made by the customer in the
  console.
- Anything about billing, invoices, quota increases, or account entitlements.
- Reading a customer's file contents, application logs with business data in
  them, or credentials on disk.

For each, say plainly that this skill will not perform it, name the console
entry point where the customer performs it themselves, and state the risk in one
sentence. Do not generate a command line for the customer to paste, however
harmless that line looks on its own.
