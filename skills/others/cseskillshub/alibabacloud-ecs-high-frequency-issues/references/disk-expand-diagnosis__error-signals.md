# Error Signals and Symptom Map

Every string in the left column is matched case-insensitively against output the
customer pasted, or against the customer's own description of what they saw. The
verdict names are the constants in `scripts/areas/disk_expand_diagnosis/_constants.py`, so this document and the
decision tree cannot drift apart.

Confidence has two levels. **observed** means the exact string has been seen in
real cases at this tier and the interpretation is settled. **defensive** means the
skill matches the documented shape of the message but the interpretation is
inferred; a defensive match must be reported to the customer with that caveat and
must not be stated as fact.

## Blockers detected from an error string

| String or symptom | Verdict | What it actually means | Disposition |
| --- | --- | --- | --- |
| `InvalidInstanceType.NotSupportDiskCategory`, or the customer's "the order paid but the disk never shows up" with an attach refusal | `TARGET_DISK_NOT_ATTACHED` | observed (verified live 2026-10-20). The instance type does not support that cloud disk category, so the disk never became In_use and no capacity arrived; it is not a billing delay. Example: ecs.t5 economy family refuses cloud_essd_entry and cloud_efficiency but accepts cloud_ssd, and cloud_ssd online resize succeeds. | Explain the instance-type x disk-category support matrix. Check the category with DescribeAvailableResource or the instance family documentation, then re-create/re-attach a supported-category disk or plan an instance-type change. Filesystem-layer commands are irrelevant here because the capacity never reached the instance. |
| `Permission denied to resize filesystem`, or the same refusal worded as "no permission to resize the filesystem" | `FILESYSTEM_HEALTH_BLOCKED` | observed. The kernel refused an online resize because the filesystem carries errors. This is a data integrity guard, not a wrong command and not a privilege problem. | Stop re-running the resize. Snapshot the disk, then a human checks and repairs the filesystem offline, from a detached or rescue disk, or through a controlled reboot where the boot time check performs the repair. Resume the resize only afterwards. Rule out two secondary causes first: the inode table being full, and the command not having been run with sufficient privilege. |
| `Nothing to do!`, as in "the filesystem is already N blocks long" | `PARTITION_LAYER_NOT_ENLARGED` | observed. The filesystem already fills its partition, so the filesystem command correctly had nothing to do. The partition layer is the step that never moved. | Do not repeat the filesystem command. Establish the partition hierarchy from `lsblk -f`, `fdisk -lu` and `blkid` pasted back by the customer. Extended partitions carrying logical partitions, and LVM, each need their own procedure, so this tier escalates rather than emitting a generic partition command. |
| `GPT PMBR size mismatch` | `PARTITION_TABLE_METADATA_INCONSISTENT` | observed. The protective MBR still describes the old, smaller disk size. | Identify and escalate to a human engineer. Published resize walkthroughs do not cover reconciling this, and improvising with a partition table writer here can destroy the table. |
| `The backup GPT table is not at the end of the device` | `PARTITION_TABLE_METADATA_INCONSISTENT` | observed. The backup GPT header sits where the old end of disk used to be. | Same as the PMBR mismatch: escalate, and run no partition table writer. |
| `unknown filesystem type` | `NEW_DISK_INITIALIZATION_AREA` | observed. The block device carries no filesystem yet. This is a new or just-attached disk that needs initialization, not a resize that failed. | Say plainly that this is the initialization area. Formatting erases the device, so this skill never emits a format command even after a confirmation. Hand over the attach and initialize documentation with a data loss warning. |
| `Directory index full` | `FILESYSTEM_HEALTH_BLOCKED` | observed. An ext4 directory index has hit its limit or is damaged. | Filesystem health first: snapshot, then human repair. The resize cannot be trusted until the check passes. |
| `Delayed block allocation failed` | `FILESYSTEM_HEALTH_BLOCKED` | observed. ext4 could not commit delayed allocation, which points at metadata damage. | Snapshot, human repair, and rule out exhausted space or inodes as the trigger before concluding metadata damage. |
| `errors=remount-ro` | `FILESYSTEM_HEALTH_BLOCKED` | observed. The mount options tell the kernel to switch the filesystem into a non-writable state as soon as ext4 reports an error, which is why both writes and resizes fail. | Report the filesystem as unhealthy and pause the resize plan. Repair comes first and is a human operation with the instance in a controlled state. |
| `bad superblock` | `FILESYSTEM_HEALTH_BLOCKED` | observed. The filesystem superblock is unusable. | Human repair only, from a detached disk or rescue environment, after a snapshot. Never suggest a write-mode filesystem tool from this skill. |
| `on-line resizing required` | `FILESYSTEM_HEALTH_BLOCKED` | defensive. The filesystem lacks the feature flags that permit an online grow, so an offline resize is being requested. | Confirm from `tune2fs -l` output pasted by the customer, then plan an offline window. Report with reduced confidence because the match is defensive. |
| `growpart: command not found` | `GUEST_RESIZE_TOOLING_MISSING` | observed. The guest resize helper is not installed. | Installing a package mutates the instance and stays a customer action. The usual underlying cause is an unreachable name resolver or repository, so ask the customer to check resolver configuration and the package manager themselves; neither is auto-executable here. |
| `Cannot find a valid base URL` | `GUEST_RESIZE_TOOLING_MISSING` | defensive. Package installation failed, so the resize helper never arrived. | Name resolution and repositories are outside this tier. Give the manual check and keep the resize blocked until the helper is present. |
| `No space left on device` | `CAPACITY_OR_INODE_BLOCKED` | observed. No free blocks, which blocks the resize tooling itself and is frequently mistaken for a failed expansion. | Free space first, then resize. Hand off to the disk capacity diagnosis and say why. |
| A `df -i` line at 100 percent, matched on the `IUse%` column | `CAPACITY_OR_INODE_BLOCKED` | observed. An exhausted inode table prevents metadata operations, including some resize paths. | Hand off to the disk capacity diagnosis for inode cleanup. This tier records the blocker and refuses to call the resize a command failure. |
| `Entering emergency mode` | `INSTANCE_STATE_BLOCKED` | observed. Boot fell into emergency or maintenance mode. | Stop the resize flow and hand off to the instance state diagnosis. Warn the customer not to touch partitions until boot is healthy. A stale `fstab` entry or a failed boot time filesystem check are the usual causes. |
| `sulogin` | `INSTANCE_STATE_BLOCKED` | observed. The boot process is asking for a maintenance shell login. | Hand off to the instance state diagnosis before any partition work. |
| The startup self-diagnosis code `1662001149` | `INSTANCE_STATE_BLOCKED` | observed. Self-service diagnosis reported a startup or filesystem check fault. | Hand off to the instance state diagnosis. The code belongs to that area; it is recorded here only so this skill recognises it and stops. |
| "Extend Volume" greyed out, or unallocated space that will not merge | `WINDOWS_ADJACENCY_LIMIT` | observed. Disk Management extends a volume only into unallocated space immediately to its right on the same disk. | State the adjacency constraint, show where the unallocated block actually sits, and name the non-native alternatives as manual options carrying real data loss risk plus a mandatory fresh snapshot. |
| A request to move space from one volume to another | `WINDOWS_ADJACENCY_LIMIT` | defensive. Capacity cannot be moved from one cloud disk to another, and the platform cannot shrink or relocate an existing partition. | Say the request is not supported and offer the supported shapes: grow the disk then grow its partition, or pool several disks with LVM. |
| A partition count limit being hit | `SPECIAL_LAYOUT_LVM_OR_EXTENDED_PARTITION` | defensive. An MBR disk holds at most four primary partitions. | Report the limit. A system disk must not be converted to GPT, because that breaks boot. Route any layout redesign to a human plan. |

## Symptoms with no error string

These are what customers actually type, and each one still routes deterministically.

| Customer wording | Verdict | Response |
| --- | --- | --- |
| "I paid for the expansion but I cannot find the option to run it again" | `CLOUD_RESIZED_GUEST_NOT_APPLIED` once `DescribeDisks` confirms the size | The missing console entry point is the expected state after a successful capacity change, not a failed order. Redirect to the guest side partition and filesystem step. |
| "The size is unchanged", "the new capacity is not showing", "the system does not recognise the disk" | `CLOUD_RESIZED_GUEST_NOT_APPLIED` or `CLOUD_SIDE_NOT_RESIZED` | `DescribeDisks` decides which. Never assume; the two need opposite next steps. |
| "Do I have to restart the instance for the expansion to take effect?" | none, a question | Online expansion does not require an instance restart, and the guest side grow does not either. Recommend a low traffic window and a snapshot first. |
| "Will the expansion interrupt my business?" | none, a question | It is a smooth change; a small amount of IO jitter is possible. Low traffic window plus snapshot first. |
| "The snapshot will use up my disk space" | none, a misconception | Snapshots live in cloud storage and never consume space on the disk being resized. They bill separately by stored capacity and retention time. |
| "The operating system shows less than I bought" | none, a units question | Explain binary GiB against decimal GB and the filesystem's own metadata and reserved blocks. See [../SKILL.md](../SKILL.md) workflow step 4 and the capacity note the script emits. It is not missing capacity. |
| "I created a new volume inside the OS but the console does not show it" | none, a concept gap | The console reflects cloud disks, not partitions or drive letters created inside the guest. One cloud disk can hold several of them. |
| "Can you resize it for me, without a snapshot?" | none, a gate | The snapshot cannot be waived and cannot be created on the customer's behalf; it has to exist in their own account context before any change step. |
| "I deleted a volume by mistake" / "can the partition be recovered?" | `SPECIAL_LAYOUT_LVM_OR_EXTENDED_PARTITION` or human | Recovery is a human operation. Snapshot the disk immediately to stop the state changing, then escalate. This skill does not attempt recovery and does not promise an outcome. |
| "The disk is broken, is this a hardware fault?" | depends | For cloud disks, the underlying block storage keeps three replicas, so a physical hardware cause can be ruled out; the evidence points at the filesystem or the IO path instead. For **local disks** there is no redundancy: back up immediately, escalate to a human, and warn that redeploying the instance wipes every local disk. |

## Capacity units, stated once and reused

The console counts binary GiB. Several guest tools print decimal GB, where 1 GiB is
about 1.073741824 GB. On top of that the filesystem keeps capacity for its own
metadata and reserves blocks for the privileged user. A 900 GiB disk therefore
legitimately presents as roughly 886 GB inside the guest before any overhead is
considered. Present this as units and overhead, never as capacity that went missing,
and never as a reason to open a second expansion order.

## Rules for using this map

* Match on what the customer actually produced. If nothing matches, say so and ask
  for the specific readings, rather than picking the closest entry.
* Non-English locales translate these strings. If a customer's paste looks like a
  translated refusal, ask them to re-run the failing command with
  `LC_ALL=en_US.UTF-8` and paste it again before concluding that no signal matched.
* A defensive match is reported as a possibility with its caveat, never as a
  finding.
* Two signals pointing at different verdicts is common, and the blocker order in
  the workflow decides which one governs: instance state, then filesystem health,
  then capacity and inodes, then partition table metadata, then layout, and only
  then the ordinary grow path.
