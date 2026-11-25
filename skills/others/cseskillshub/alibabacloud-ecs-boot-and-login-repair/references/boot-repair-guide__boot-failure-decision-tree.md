# Boot-failure decision tree

The symptom this skill owns: **the operating system on the instance does not come up, or comes up into a
state from which the customer cannot reach their system.** Everything else is a different axis and is
routed away in step 0. Do not enter the repair flow on the customer's wording alone; customers routinely
attribute a network, capacity, or performance problem to "the last update".

## Step 0 — gate: is this a boot failure?

Decide this before anything else. In this tier roughly one third of the tickets tagged as boot failures
turn out to be another problem entirely.

| Observed condition | Verdict | Route |
|---|---|---|
| `DescribeInstances` reports `Running`, and VNC shows a logon prompt or desktop | OS is up | Not this skill: connection path (Cloud Assistant reachable? SSH/RDP service? local firewall? account locked?) |
| Remote login fails but VNC shows the desktop and services respond | OS is up | Connection path; the remote-desktop service itself can fail while the system is healthy, because VNC does not depend on it |
| A patch or vulnerability installation action failed, the system still boots | OS is up | `alibabacloud-ecs-patch-management`; a reboot that is slow because updates are being configured belongs here only while the machine has not finished booting |
| Patch failed with an error code while the system boots normally | OS is up | Patch skill, and if the underlying cause is free space, the capacity skill |
| The failure appeared after a disk expansion; a partition or filesystem does not reflect the new size | Not a boot failure | `alibabacloud-ecs-disk-expand-diagnosis`; note that a partition-table conversion is destructive on Windows and usually is not on Linux, and that conversion without handling LVM metadata first can make volumes disappear |
| System or data disk full, or inodes exhausted; the boot symptom is secondary | Capacity axis | Capacity skill; a pending update transaction caused by a nearly full system volume is a capacity problem wearing a patch costume |
| Instance parked in `Starting` or `Stopping` for a long time, especially after a specification downgrade, and a rescue disk shows nothing | Control-plane axis | `alibabacloud-ecs-instance-state-diagnosis`; do not assert a cause, this class is frequently closed without one |
| Every access attempt fails because disk IO is saturated by one workload | Performance axis | `alibabacloud-ecs-disk-io-diagnosis`; the machine is not failing to boot, it is failing to serve |
| Public address unreachable after a traffic attack, instance itself fine | Network/security axis | Security handling; blackhole periods drop all inbound traffic and no in-guest repair will change that |
| Ransomware, encrypted system files, extortion note | Security axis | Security handling first; this skill contributes only the data-rescue ordering |
| OS will not start, stops at firmware/boot loader/kernel/startup screen, or lands in rescue or emergency mode | **This skill** | Step 1 |

Confirm the gate with `python3 scripts/axes/boot_repair_guide/boot_repair_guide.py classify --region-id <region>
--instance-id <id> --text "<screen text>"`, which combines the cloud status with the screen evidence and
prints the gate verdict before any branch.

## Step 1 — snapshot gate

Nothing that can destroy data is discussed before this gate is settled.

- A usable snapshot exists, or the customer states they will take one now.
- The snapshot has reached 100 percent. A snapshot that is still uploading is not a rollback point, and a
  repair environment must not be attached while the only backup is incomplete.
- The customer knows that a rollback discards every change made after the snapshot moment, that rollback
  itself requires a restart, and that automatically created snapshots expire on their retention rule and
  cannot be recovered afterwards.
- Retention and cost of the snapshot are stated, and removal after the work is a customer decision.

The skill does not take snapshots in this release. Snapshot existence and progress are established by
customer confirmation, ideally with the console screenshot or the snapshot identifier.

## Step 2 — evidence gathering

Cloud queries cannot see the boot loader, the EFI system partition, `/etc/fstab`, the update history, or a
crash dump. The report must say which of these are missing and ask for them. Collect, in this order:

1. Screen text as transcribed by the customer, or the console diagnosis verdict.
2. Time of the last start attempt and the triggering change (upgrade, patch, expansion, downgrade,
   password reset, reinstall, reboot after an application install).
3. The `DescribeInstances` profile: OS family and version, image id, instance type family, zone.
4. Whether the instance is `Stopped` — required before a repair disk can be attached.
5. In-guest or offline read-only output that the customer runs and pastes back; see
   `references/boot-repair-guide__evidence-checklist.md` and `scripts/axes/boot_repair_guide/boot_repair_guide.py evidence-plan`.

## Step 3 — branch table

| Branch | Evidence that establishes it | Layer that must be fixed | Detail file |
|---|---|---|---|
| `grub-loader` | `grub>` / `grub rescue>` prompt; `error: unknown filesystem`; `normal.mod not found`; `ls` lists partitions as unknown | Boot loader installation, its module directory, and its configuration file | `references/boot-repair-guide__grub-efi-repair-guidance.md` |
| `efi-boot-entry` | Boot Manager to GRUB to firmware loop; the fallback path exists but has no configuration file; boot entry lost after a distribution upgrade | UEFI boot entries and the fallback path, in addition to the loader | `references/boot-repair-guide__grub-efi-repair-guidance.md` |
| `boot-files-lost` | `/boot` not found; the boot directory or `/etc` listed as empty from rescue; Windows `bootmgr` missing or renamed | Contents lost, not configuration: repair is usually impossible, go to rescue | `references/boot-repair-guide__data-rescue-and-reinstall.md` |
| `fstab-mount` | Emergency mode after the kernel starts; the reported mount point does not exist; a data disk entry survives from an image that never carried the data disk | `/etc/fstab` entries and the devices they name | `references/boot-repair-guide__fstab-and-devices.md` |
| `filesystem-state` | Volume mounted read-only because of recorded errors; boot stops inside early init; the mount options include an error action that remounts read-only | Filesystem consistency; every action here is destructive-capable and stays manual | `references/boot-repair-guide__boot-error-catalog.md` |
| `post-update-normal` | Boot is slow but advancing after a cumulative or feature update; no error text; the machine was interrupted during a first update boot | Patience and a protected maintenance window, not repair | `references/boot-repair-guide__post-update-boot-failure.md` |
| `post-update-kernel` | Failure appears only after a kernel or distribution major-version change; an older entry still boots | Boot loader rebuild and default entry selection | `references/boot-repair-guide__post-update-boot-failure.md` |
| `windows-bsod` | Stop code on screen, automatic repair failure, or repeated crash just before logon; safe mode reachable | Driver, filter, service, or registry at start time | `references/boot-repair-guide__windows-bsod-triage.md` |
| `unknown` | No screen text, no in-guest output, and cloud fields normal | Do not classify; state the gap and the fastest way to close it | `references/boot-repair-guide__evidence-checklist.md` |

Classify by evidence, never by the customer's attribution. A report that says "caused by the update"
without a start-time line, a log entry, or a dump must be labelled as a hypothesis.

## Step 4 — exit decision

**Repairable** — configuration or boot-loader damage with the data intact. Output the manual step list
with its prerequisites, the downtime it consumes, and the reversibility statement. Follow the ladder in
fixed order and record what was attempted; do not loop on one attempt and do not skip to the end.

Windows ladder: repair the boot configuration, then last-known-good configuration, then safe mode, then
restore the registry backup, then stop and move to rescue. Linux ladder: verify the mount and device
identity, correct or comment out the failing entry, rebuild the boot loader configuration, rebuild the
initial RAM disk, then offline repair through a mounted repair environment.

**Not repairable** — the contents themselves are gone or corrupted: the boot directory or `/etc` is empty,
critical system files are encrypted or renamed, the partition table at the start of the disk was
overwritten, the operating system is out of support and no fix exists, or several full repair attempts all
ended in the same crash. Then stop repairing and rescue data. Roll back to an earlier snapshot if one
exists and the customer accepts losing later changes, otherwise build a disk from the newest snapshot,
attach it to a temporary pay-as-you-go instance in the same zone, copy the data out, then rebuild the
original. See `references/boot-repair-guide__data-rescue-and-reinstall.md`.

Stopping the repair ladder is a decision the customer makes with the evidence in hand. The skill's job is
to make the cost of one more attempt explicit: each offline attempt needs downtime, a completed snapshot,
a same-zone repair target, and a working credential.

## Frequency notes from this tier

- The most common Linux cause cluster is a distribution or kernel upgrade that left the boot loader
  configuration and the installed loader version out of sync, including the case where the fallback
  boot path still points at an old loader whose configuration file no longer exists.
- The most common Windows cause cluster is a third-party filter or security product loaded at start time,
  followed by out-of-support images, an old image on a new instance type, and a nearly full system volume
  combined with failed updates.
- Across both, the most common customer misconception is that a boot failure means the data is gone. It
  usually does not: a damaged boot path or a rejected mount entry leaves the data untouched, and that is
  precisely why the rescue path works.
