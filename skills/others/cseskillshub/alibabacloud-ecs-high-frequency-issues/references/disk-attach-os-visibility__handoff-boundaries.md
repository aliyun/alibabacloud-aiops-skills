# Scope boundary and handoff

This skill answers one question: **is the disk placed on this instance, and does the
operating system see it, hold a filesystem on it, and reach it at a path.** Anything else
that shares the word "disk" leaves immediately, and the faster it leaves, the less the
customer has to explain twice.

## Where each symptom belongs

| Symptom in the customer's words | Destination | What this skill still contributes |
| --- | --- | --- |
| Capacity grew at the console but the partition and filesystem still show the old size; growpart or volume extension | `area:disk-expand-diagnosis` | The placement and device map, proving the disk is attached and visible before the size question |
| The instance will not boot, is stuck between states, the root filesystem came back mounted as `ro`, fstab keeps the boot broken | `area:instance-state-diagnosis` | A statement that placement is fine, so the fault is inside the guest's own startup |
| Throughput or IOPS capped, IO stalls, a disk at its performance ceiling | `area:resource-bottleneck` | Which disk id corresponds to which guest device, so the right one is discussed |
| Filesystem or inode consumption, cleanup, "disk full" | the disk capacity and inode work of this product family | Confirmation that the disk is mounted, since an unmounted disk cannot be full |
| Rollback to a snapshot, building a disk from a snapshot, shared snapshots | `alibabacloud-ecs-disaster-recovery-snapshot` | The last step only: is the recovered disk attached, seen, mounted, and does it list content |
| Replacing or reinstalling the operating system itself, image choice, market images | the instance lifecycle path in the console | Impact facts about the data disk, listed in the state-machine document |
| Refunds, renewal, overdue balance, released instances, buying the wrong thing | billing and lifecycle support | Nothing; state the boundary and stop |
| A mount that is not a block disk: NFS, SMB or CIFS endpoints, shared file storage addresses | the network file storage path | A check that the object in question is not an attached disk, so the customer is not sent in circles |
| Initialising, re-initialising or wiping a disk | human action only | The risk statement, the recovery-point check, and the correct device name |

## The overlap that matters most

The recovery route *snapshot, build a disk, place it, copy the content out* runs through
this tier's symptom space, because the customer's complaint at the end of it is "I still
cannot see my data". The split is by link, not by topic:

- Everything about snapshots and the recovery itself is the disaster-recovery skill's work.
- This skill checks whether the resulting disk is attached, enumerated, carries a
  filesystem and is mounted, and reports where it stops.
- Inside this skill a snapshot has exactly one role: `DescribeSnapshots` says whether a
  recovery point exists before the customer is told to touch a device. Creating one is the
  customer's own decision and action.

## Saying no to the dangerous half of the request

Customers in this tier routinely ask the agent to run the fix. The steps they ask for are
the ones that destroy data when applied to the wrong device: partitioning, formatting,
initialising, unmounting, forcing a volume offline. The answer is a complete manual
instruction with the device name verified, the risk named, and the recovery point checked
first. That is the same boundary a human supporter draws, and it is not negotiable at the
customer's request.

## Handoff wording

Lead with what was proven, then name the destination:

> The disk is attached to this instance and the guest enumerates it, so placement and
> visibility are not the problem. The remaining question is capacity that has not reached
> the partition, which is disk expansion work. Take these readings with you when you
> switch to that diagnosis.

> The disk is attached and mounted at the path you named. The content you expected from
> the previous system is on a volume that was released when the operating system was
> replaced; only a snapshot taken before that can bring it back. That is recovery work,
> and this skill can confirm the recovered disk once it is attached.

Never promise recovery of a released device, and never soften "unrecoverable without a
snapshot" into a maybe.
