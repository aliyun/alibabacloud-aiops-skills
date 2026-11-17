# Windows Expansion Paths

Guidance for a human to execute, like every other path in this skill. Volume
deletion, `diskpart` write operations, third party partition software and instance
restarts are never dispatched from here; they are described, risked, and handed
over. A fresh snapshot of the target disk precedes all of it, per
[snapshot-first.md](disk-expand-diagnosis__snapshot-first.md).

## Step 1: read the current layout

The instance's operating system family comes from `DescribeInstances`, so the
Windows branch is chosen from a returned field rather than from the customer's
wording.

Non-mutating commands this skill may dispatch through the confirm gate, one at a
time:

```powershell
Get-Volume
Get-PSDrive
Get-ChildItem -Directory
fsutil volume diskfree C:
fsutil dirty query C:
```

The commands that would actually settle where the unallocated block sits,
`Get-Partition` and `Get-Disk`, are **not** approved for automated execution at
this tier. When they are needed, ask the customer to run them and paste the output,
or to send a Disk Management screenshot. The Windows branch therefore degrades to
customer-supplied evidence more often than the Linux branch does, and the report
says so instead of implying a measurement that was never taken.

## Step 2: the adjacency constraint

This is the single fact that resolves most Windows cases, and it is a hard
constraint of the operating system, not a limitation of the platform:

> Disk Management can extend a volume only into unallocated space that is
> **immediately to its right**, on the **same disk**.

Consequences to state plainly:

* Unallocated space to the **left** of the target volume cannot be consumed by
  Extend Volume.
* Unallocated space on a **different disk** cannot be consumed, ever.
* A volume sitting **between** the target and the unallocated space blocks the
  path, even if that middle volume is nearly empty.
* Capacity cannot be moved from one cloud disk to another, and the platform cannot
  shrink or relocate an existing partition.

When Extend Volume is greyed out while unallocated space visibly exists, one of the
four is true. Identify which from the evidence, name it, and stop there. Report
`WINDOWS_ADJACENCY_LIMIT`.

## Step 3: the ordinary path

Only when unallocated space is immediately to the right of the target volume on the
same disk:

1. Open Disk Management (`diskmgmt.msc`).
2. Locate the target volume and confirm the Unallocated block is directly to its
   right.
3. Right-click the volume, choose **Extend Volume**, and accept the default that
   consumes all of the unallocated space.
4. Verify with `Get-Volume` or a refreshed Disk Management view.

No instance restart is needed for this, and the data on the volume is not touched by
extending it.

## Step 4: no unallocated space visible at all

The cloud side capacity change landed but the guest has not re-enumerated the disk.
In order of escalation, each step a human decision:

1. In Disk Management choose **Action**, then **Rescan Disks**.
2. The `diskpart` rescan achieves the same re-enumeration. It is a write class
   operation on the disk subsystem and is never dispatched from this skill.
3. On older Windows releases the disk driver can be too old to notice the new
   capacity without an instance restart. Restarting an instance is a business
   decision with an interruption attached; this skill neither makes it nor executes
   it, and it says so explicitly.

> Confidence note: the "older driver needs a restart" branch rests on cases whose
> transcripts are incomplete. Present it as a possibility to check, not as an
> established diagnosis, and confirm the release and driver level first.

A customer who reports that the unallocated block is far smaller than what they
bought is usually seeing this state, or a partition layer that never moved. Get the
numbers from `Get-Volume` and the cloud side size from `DescribeDisks` and compare
them before agreeing that capacity went missing. It almost never did.

## Step 5: paths that require a destructive step

### A blocking volume in the middle

The supported native route is to remove the blocking volume and then extend into
the combined unallocated space. That is destructive. The sequence a human follows,
and the only sequence this skill will describe, is:

1. Confirm what is on the blocking volume, and confirm with the customer that its
   contents are disposable or already copied elsewhere. Do not take "it is mostly
   empty" as an answer.
2. Take a fresh snapshot of the disk. Verify the snapshot finished.
3. Only then delete the volume and extend the target.

If the contents are not disposable, the native route is closed and what remains is
third party partition software, which carries real data loss risk and is entirely a
human operation behind a snapshot. This skill names that category, states the risk,
and does not recommend a specific product or supply a download location.

### Merging a newly bought disk into an existing volume

A customer who buys an additional disk instead of expanding the original one gets a
separate disk, and Windows will not merge across disks. `DescribeDisks` shows this
directly: two disks where the customer expected one enlarged disk. Report
`SUSPECTED_NEW_DISK_INSTEAD_OF_RESIZE`, explain that cross-disk merging is not a
platform capability, and offer the two supported shapes: expand the original disk
and then extend its volume, or plan the layout with pooling in mind from the start.

### Too many primary partitions

An MBR disk holds at most four primary partitions, which is why volumes brought
across by a migration job sometimes cannot be assigned a drive letter. A system
disk must **not** be converted to GPT: converting it breaks boot. Report the limit,
keep the partition count and table type facts for later, and route the layout
redesign to the migration owners. See [handoff-matrix.md](disk-expand-diagnosis__handoff-matrix.md).

## NTFS confidence caveats

NTFS has no equivalent of `df -i`. Any conclusion about file count exhaustion, MFT
health or metadata limits on Windows is **inferred, not measured**, and the report
must carry that caveat explicitly rather than presenting the inference as a
reading. Where the underlying evidence matters, ask for it and mark the verdict
provisional until it arrives.

A damaged NTFS metadata area presents as a volume that will not mount or a drive
letter that cannot be assigned. Repair is a human operation, after a snapshot, and
this skill does not attempt it or promise an outcome.

## Console entry points

* Disk list for the region: `https://ecs.console.aliyun.com/disk/region/<regionId>`
* Partition and filesystem expansion tool:
  <https://ebs.console.aliyun.com/tools/resizeFileSystem>

The expansion tool is cited as a console entry point only. Its operating system and
partition layout limits are not documented in material this skill can cite, so it is
never presented as a verified procedure and never relied on as the recommended path.
