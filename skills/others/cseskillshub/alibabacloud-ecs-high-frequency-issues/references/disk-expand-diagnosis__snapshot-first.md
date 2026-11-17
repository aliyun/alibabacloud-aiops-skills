# Snapshot First

A snapshot of the target disk is a **precondition** for every change this skill
hands over: partition growth, filesystem growth, filesystem repair, volume
deletion, third party partition work, and any cleanup. Pure inspection is exempt,
because it changes nothing.

The report always carries a snapshot status field. It reads either
`CONFIRMED: <identifier or creation time>` or `NOT_CONFIRMED`, and a change step is
never emitted above an unconfirmed status without the report saying that the
snapshot still has to be taken.

## Why it is not negotiable

Every path in [linux-expand-paths.md](disk-expand-diagnosis__linux-expand-paths.md) and
[windows-expand-paths.md](disk-expand-diagnosis__windows-expand-paths.md) writes to a partition table, a
filesystem or a volume. Those writes are not undoable from inside the guest. The
snapshot is the rollback path, and it is the only one. Where the filesystem is
already carrying errors, the snapshot is what makes a repair attempt safe to make at
all.

## The three things to say every time

Support cases show the same three misconceptions repeatedly, so state all three
before asking for the snapshot rather than after a refusal.

**1. A snapshot does not consume space on the disk being resized.** It is stored in
cloud storage. Customers who decline a snapshot because "there is no room left" are
declining on a false premise, and the resize then proceeds with no rollback path.

**2. It bills separately, by stored capacity and by how long it is kept.** Setting a
retention period stops the billing automatically; leaving it unset means the
snapshot bills until it is deleted. As an order of magnitude, past cases quoted
roughly 0.4 CNY for 100 GiB held for one day. That figure is historical and must be
re-verified against current pricing before being repeated to a customer; the
mechanism, capacity multiplied by duration, is what matters.

**3. It has to be recent.** A snapshot taken before the customer's latest writes
does not protect those writes. When a snapshot is offered as already done, ask when,
and compare that against the last significant change to the data. If there is any
doubt, take a new one.

## Who creates it

This skill can create one through the `CreateSnapshot` action under the `ecs` RAM
code, behind the confirm gate, and because it authenticates with the caller's own
credential chain, that snapshot lands in the customer's own account context. What a human support engineer cannot do is
create it on the customer's behalf from outside that account, which is why cases
that reach a person still end with the customer clicking through the console.

The gated call is `create-snapshot`:

```bash
python3 scripts/areas/disk_expand_diagnosis/disk_expand_diagnosis.py create-snapshot \
  --region-id cn-hangzhou --disk-id d-example0123456789 \
  --retention-days 7 --confirm-cost
```

Without `--confirm-cost` the script refuses the call and prints the disclosure that
still has to be made, plus the console entry point. That refusal is the gate working,
not a failure.

Console route, for a customer doing it themselves: the regional disk list at
`https://ecs.console.aliyun.com/disk/region/<regionId>`, then create a snapshot on
the specific disk identifier. Give the customer the exact disk identifier rather
than "the system disk", because instances commonly have several.

If the create button appears not to respond, that is usually a console state issue;
refreshing and retrying resolves it more often than anything else.

## Auto snapshot fields are not evidence

`DescribeDisks` returns `EnableAutoSnapshot` and `AutoSnapshotPolicyId`. Neither says
that a usable snapshot of the current data exists right now. A policy can be
attached and its last run can be days old, or it can have failed. The script reports
both fields and then explicitly declines to treat them as the pre change backup. Do
not let a policy identifier satisfy the snapshot precondition; ask for a snapshot
identifier or a creation time.

## Deletion is the customer's decision

Remind the customer to delete snapshots once the change is verified and the workload
has run clean for a while, because they keep billing. Never delete one from this
skill: snapshot deletion is on the prohibited list, along with disk release, shrink,
refund and unsubscription. Those are commercial and irreversible actions that belong
to a person.

For a change window where the snapshot must not be removable, snapshot locking is
the supported mechanism:
<https://help.aliyun.com/zh/ecs/user-guide/lock-snapshot.md>

## Rollback, stated in the report

Every change step handed over comes with its rollback path in the same breath:

* Partition or filesystem growth that goes wrong: restore the disk from the
  snapshot taken immediately before. The instance has to be stopped for that, which
  is itself a customer decision this skill does not make.
* A volume deleted to unblock an extension: restore from the same snapshot. Data
  written after the snapshot is gone either way, which is why step 1 of that
  sequence is confirming the contents are disposable.
* A repair attempted on a damaged filesystem: restore from the snapshot, and treat a
  second failure as evidence that recovery needs a specialist rather than another
  attempt.

Where the data is already unrecoverable, say so without softening it and without
promising an outcome, then escalate. For a cloud disk the underlying block storage
keeps three replicas, so a physical hardware cause can be ruled out; for a **local
disk** there is no redundancy at all, and redeploying the instance wipes every local
disk, so backing up first outranks every other step.

## Documentation

* Snapshot locking: <https://help.aliyun.com/zh/ecs/user-guide/lock-snapshot.md>
* Disk resizing and shrinking FAQ, which covers the restart, business impact and
  shrink questions: <https://help.aliyun.com/zh/ecs/disk-resizing-and-shrinking-faqs.md>
* Restoring data on Windows instances:
  <https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-restoring-data-on-windows-instances.md>
* Release protection, relevant when a customer is being told that redeploying wipes
  local disks:
  <https://help.aliyun.com/zh/ecs/user-guide/enable-or-disable-release-protection-for-ecs-instances.md>

**Gap, recorded rather than filled:** the general snapshot creation and snapshot
billing documents were not resolved during the requirements phase. Until they are,
cite the console entry point and the capacity-times-duration mechanism above, and do
not invent a document link.
