# The attach-and-see-it chain

## Why this tier exists

A disk is not one object with one state. It is two independent planes, and the customer
can only see the second one:

| Plane | What it answers | Where it is observed |
| --- | --- | --- |
| Control plane | Is the disk bought, and is it placed on this instance? | `DescribeDisks`, `DescribeInstances` |
| Guest plane | Does the operating system enumerate the device, does it hold a filesystem, is that filesystem reachable at a path? | Commands executed inside the instance |

Almost every ticket in this tier is one sentence: *the console says attached, so why can
I not use it*. The answer is that placement is only link two of five. The platform does
not partition, format or mount a disk on the customer's behalf, and no control-plane call
can tell whether the customer did.

## The five links

| # | Link | Proved by | Typical break |
| --- | --- | --- | --- |
| 1 | The disk exists in the region queried | a `DescribeDisks` record for that disk id | wrong region; the disk was released |
| 2 | The disk is placed on this instance | the attachment list of the disk names this instance id | placed on another instance; still in progress; never placed |
| 3 | The guest kernel enumerates a block device of that size | `lsblk`, `fdisk -l`, `cat /proc/partitions` | driver or boot-time rescan issue; the device exists under a different naming scheme |
| 4 | That device carries a partition or a filesystem | `lsblk -f` showing a child device or a non-empty `FSTYPE` | a new disk is empty by design; a destroyed filesystem also lands here |
| 5 | That filesystem is mounted where the application looks | `df -h`, `findmnt` | never mounted; mounted elsewhere; mount lost after reboot |

The chain is evaluated in order and reported as the first link that does not hold.
`scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py` builds this verdict; the wording below is what the
agent says about it.

## Findings the scripts can emit

| Finding | Meaning | What the agent does with it |
| --- | --- | --- |
| `INSTANCE_NOT_FOUND` | No instance came back in that region | Ask for the region; do not guess |
| `INSTANCE_NOT_RUNNING` | The instance is stopped or in a transitional state | Explain that several console entries are greyed out by the state, not broken |
| `DISK_NOT_FOUND_IN_REGION` | No disk record in that region | Confirm the region; disk ids do not move between regions |
| `DISK_NOT_ATTACHED_IN_CLOUD` | The disk is not placed on anything | Manual placement guidance |
| `DISK_ATTACHED_TO_OTHER_INSTANCE` | The disk sits on a different instance | Explain the mismatch, then manual detach and re-place guidance |
| `SUBSCRIPTION_DISK_PLACEMENT_LOCKED` | Placement came with the subscription purchase | Explain that the greyed entry is a billing shape, not a failed operation |
| `OS_DOES_NOT_ENUMERATE_DEVICE` | Cloud says attached, the guest has no such device | This is the only genuine "the disk is not there" case; see the naming map |
| `OS_NO_PARTITION_TABLE` | Visible device, nothing inside it | Manual partition step, with the risk statement |
| `OS_NO_FILESYSTEM` | Visible device, empty filesystem column | Manual initialisation; the most common ending in this tier |
| `OS_FILESYSTEM_NOT_MOUNTED` | Filesystem exists, no path reaches it | Manual mount, plus the persistence note below |
| `OS_MOUNTED_AND_READABLE` | Every link holds | Close the case; look elsewhere for the reported symptom |
| `OS_MOUNT_POINT_SHADOWING` | Content of a non-empty directory is hidden by a mount | Explain hiding versus deletion, then manual unmount to confirm |
| `OS_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED` | A Windows volume with no drive letter or offline | Manual online and drive-letter guidance in Disk Management |
| `OS_READINGS_NOT_COLLECTED` | The guest half was not run | Request the confirmation, then run one command |
| `OS_READINGS_UNAVAILABLE` | Cloud Assistant gave nothing back | Fall back to asking the customer to run an approved command and paste it |

## Decision order the agent follows

1. Collect region id and instance id. Without a region, nothing can be judged.
2. Run the entry script. It reports links 1 and 2 from the control plane, whether a
   recovery point exists, and which link the chain currently stops at.
3. If the disk is not placed on this instance, stop: no guest action can help. Hand over
   the console path for placement and stop there.
4. If it is placed, say what is about to be executed, that it changes nothing, and that
   the customer may run it themselves instead. Only after an explicit yes, deliver one
   approved command. Repeat the disclosure per command.
5. Classify with the table above, and give the customer exactly one next step: the manual
   step belonging to the first broken link, plus the matching help document.
6. Before any step that would write to the device, state that a recovery point must exist
   first, and report whether `DescribeSnapshots` found one. The customer creates it; this
   skill does not.

## Two confusions worth settling early

**Grey buttons are not failed operations.** Placement entries are greyed out for disks
that came with a subscription instance, and system-disk replacement is greyed out while
the instance is running. Both are normal. Judge placement from the fields the API
returns, never from which buttons a page happens to show today.

**Hidden is not deleted.** Mounting a filesystem onto a directory that already has
content hides that content while the mount exists. The customer reports it as lost data.
Unmounting the filesystem from that path brings the original listing back. Confirm with
`df -h` or `findmnt` which device owns the path before saying anything about recovery.

## Replacing or reinstalling the system disk

Customers arrive here after an operating-system change and ask what happened to the data
disk. The stable facts:

- The replacement releases the previous system disk, and everything on it is gone and not
  recoverable afterwards. Only a snapshot taken earlier can bring anything back.
- Whether a data disk reappears on its own depends on the guest family. A Linux guest
  remounts only what is recorded for automatic mounting, so an entry that was never added
  means the disk is attached but not mounted after the reboot. A Windows guest of the same
  family picks its data volumes back up by itself.
- The button is available while the instance is stopped. A running instance greyed it out.
- Whether the instance keeps its network attributes is a question about the instance, not
  about a disk. This skill checks no network attribute and points to the official
  replacement document instead of answering from memory.
- Recovering data by building a disk from a snapshot, placing it, and copying the content
  out is disaster-recovery work. This skill only verifies the last part: once that disk is
  attached, does the guest see it and is it mounted.

Do not collapse these into one answer. Ask which guest family is involved before stating
whether a remount is needed; the wrong assumption here is the most common source of a
wrong answer in this tier.

## What this skill never does

It never places or removes a disk, never partitions, never formats or initialises, never
mounts or unmounts, never brings a Windows volume online or offline, never restarts an
instance, never creates or deletes a snapshot, never changes billing. Each of those is a
human action that the agent explains with the risk that belongs to it, because an
initialisation destroys an entire device and the cost of acting on the wrong device name
is a second lost dataset.
