# Handoff Matrix

Recognising that a case belongs elsewhere is a deliverable of this skill, not a
failure of it. When a row below matches, the diagnosis **stops**: no partition
command is emitted, no snapshot is requested, no further cloud query is made. The
reply states the boundary, gives the console entry point where one helps, and uses
the wording in the right-hand column.

The same wordings are constants in `scripts/areas/disk_expand_diagnosis/_constants.py` under `HANDOFFS`, so what
the script prints and what this document says cannot diverge.

## Where each symptom belongs

| Recognised symptom | Owner | Action here |
| --- | --- | --- |
| Disk or partition full, inode table exhausted, `No space left on device`, deleted files that did not free space | Disk capacity and inode usage diagnosis | Confirm from evidence whether it is blocking the resize, then hand off |
| Instance will not start, stuck in a stopping or starting state, emergency or maintenance mode, boot time filesystem check failure, the startup self-diagnosis code `1662001149`, console and SSH both unreachable | `area:instance-state-diagnosis` | Recognise and hand off; warn against touching partitions until boot is healthy |
| Disk IO saturated, reads or writes slow, IOPS below what the disk category specifies, system hung with swap exhausted | `area:resource-bottleneck` | Recognise and hand off |
| Backup strategy, auto snapshot policy design, whole-instance backup coverage, NAS and database backup, image export from an encrypted disk, restorability | `alibabacloud-ecs-disaster-recovery-snapshot` | Recognise and hand off. This skill checks only that a fresh snapshot of the target disk exists before a change |
| New data disk that was never initialized or attached, `unknown filesystem type`, automatic mounting through `fstab` | Data disk initialization and attach documentation | Recognise as the initialization area, hand over the documentation, never emit a format command |
| Filesystem damage so severe the data is unrecoverable, third party data recovery, physical damage to a local disk, compensation or complaint | Human engineer, plus the data recovery marketplace and the customer relations channel | Explain the evidence only: cloud disks keep three replicas at the block storage layer, local disks have no redundancy. Promise nothing |
| Billing, refunds, unsubscription, shrink orders, corporate payment | Human and commercial channels | Recognise as commercial and out of scope |
| Compromise indicators: unexpected keys, reverse shells, unexplained services | Security incident response | Recognise and hand off; do not continue storage work |
| Migration jobs: source to target layout, partition counts after migration, operating system upgrade migration | Migration support | Keep only the partition table type and partition count facts relevant to a later resize |
| Certificates, HTTPS acceleration, and any other non-storage product question | The owning product channel | Recognise as cross-product and stop |
| An "expansion" that is not an ECS cloud disk at all, such as a subscription tier or a quota | The owning product channel | Clarify once and stop |

## Front gate clarification

Roughly a third of the cases that reach this tier on a keyword match are not about a
cloud disk expansion at all. Two questions are asked before any cloud call, because
both change the entire path:

1. **Is the capacity you extended the disk size, or the instance memory?** Customers
   describe a disk expansion as "the upgrade did not take effect" often enough that
   this has to be settled first.
2. **Did you grow an existing disk, or buy an additional one?** An additional disk
   appears in the guest as a separate volume and will never merge into an existing
   one. `DescribeDisks` settles it immediately, and the two cases need opposite
   guidance.

A request that turns out to be about a subscription tier, a quota, or another
product entirely stops at clarification. Do not run a storage diagnosis on it.

## Wording

Use these, adapted to the customer's language, rather than improvising a boundary
statement.

**To the disk capacity and inode usage diagnosis**

> The blocking condition here is exhausted space or inodes, which prevents the
> resize commands from running. Freeing capacity comes first, so this case goes to
> the disk capacity and inode usage diagnosis; return to the resize once usage
> drops.

**To `area:instance-state-diagnosis`**

> The instance will not boot normally or is parked in an intermediate power state,
> and that has to be resolved before any partition work. This case goes to the
> instance state diagnosis; do not continue resizing until boot is healthy.

**To `area:resource-bottleneck`**

> The reported symptom is sustained disk IO saturation or latency rather than
> capacity that failed to appear. This case goes to the disk IO performance
> diagnosis.

**To `alibabacloud-ecs-disaster-recovery-snapshot`**

> The question is about backup coverage, retention or restorability, not about a
> resize. This tier only checks that a fresh snapshot of the target disk exists
> before a change, so the case goes to the snapshot and backup disaster recovery
> diagnosis.

**To a human, commercial**

> Billing, refunds, unsubscription, payment method, unrecoverable data or liability
> judgements are outside an automated diagnosis and need a human engineer to pick
> this up.

**To security incident response**

> The evidence points at compromise rather than storage changes, so this needs the
> security incident response channel.

**To migration support**

> The layout problem came from a migration job, so it belongs to migration support;
> this tier keeps only the partition-table and partition-count facts relevant to a
> later resize.

**To data disk initialization, still adjacent to this tier**

> Attach and initialize the disk first. Formatting a device erases it, so this
> diagnosis never emits a format command; use the attach and initialization
> documentation, and return to resizing only once the disk is attached and mounted.

## Boundary with the snapshot and recovery tier

This skill overlaps that tier in exactly one place, and the overlap is deliberate:
before recommending a partition or filesystem change it checks whether a fresh
snapshot of the target disk exists, and it can create one behind the confirm gate.
Everything past that point, meaning snapshot policy design, retention strategy,
whole instance backup scope, whether NAS or a database is covered, image export from
an encrypted disk, and whether a given backup is actually restorable, belongs to the
recovery tier.

The distinction to hold onto: this skill asks "is there a rollback path for the
change I am about to recommend?" That tier asks "is this workload recoverable?"

## Local disks are not cloud disks

Worth its own row because the answer inverts. A cloud disk keeps three replicas at
the block storage layer, so a physical hardware cause can be ruled out and the
evidence points at the filesystem or the IO path. A local disk has no redundancy:
back it up immediately, escalate to a human, and warn the customer that redeploying
the instance wipes every local disk attached to it. Expansion guidance does not
apply to local disks at all.
