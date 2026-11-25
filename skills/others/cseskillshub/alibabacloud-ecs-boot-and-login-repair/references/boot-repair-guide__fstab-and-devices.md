# fstab, mount points, and device naming

The single most machine-decidable branch in this tier: the kernel comes up, the boot loader is fine, and
the system drops to emergency mode because one line in `/etc/fstab` names something that is not there, or
names it in a way that no longer resolves.

This file is guidance. **Editing `/etc/fstab` is a change and is performed by the customer.** The skill
compares what is recorded against what exists, points at the exact line, and states the consequence.

## Which line, and what happens if it is wrong

| Mount point in the failing line | Severity | Correct action |
|---|---|---|
| `/` (root) | Critical | Never comment this out. A missing or wrong root entry means the boot path must be rebuilt, not the line deleted. |
| `/boot` or `/boot/efi` | Critical | Do not comment out. Repair the identifier; without the EFI system partition a UEFI instance cannot start, and without `/boot` the loader cannot find its files. |
| A data disk mount, e.g. `/data`, `/mnt/xxx` | Recoverable | Comment out the failing line, boot, then re-add it correctly. The system does not need a data disk to start. |
| `swap` | Low | Comment out to boot, then re-add; a missing swap device should not stop a boot but a wrong entry in fstab can. |
| A network or non-block device | Context dependent | Add a dependency or mount option so the unit does not block startup; do not simply delete the record of intent. |

Commenting out a data-disk line is a **temporary** boot unblock and must be reported as such: the disk will
not be mounted after the next start, and the application that expects it will fail in a different way. The
permanent fix is re-adding the entry with a persistent identifier that exists on that instance.

## Identifier choice: why the entry broke

| Form in column 1 | Stable across | Breaks when | Verdict |
|---|---|---|---|
| `UUID=<hex>` | Reboot, restart, re-attach, most migrations | The volume is re-formatted or a snapshot-built volume was never assigned a fresh one | Preferred form |
| `LABEL=<name>` | Device reordering | Two volumes carry the same label, or the label was not copied | Acceptable with a uniqueness check |
| `PARTUUID=<hex>` | Content changes | The disk is rebuilt with a new partition table | Useful on GPT images |
| `/dev/vdb1`, `/dev/nvme0n1p1` | Nothing useful | Any change in attachment order, instance type, or driver | Should not be used for a data disk that must survive |

Two naming families exist for the same physical disk: the virtio style (`/dev/vda`, `/dev/vdb1`) and the
NVMe style (`/dev/nvme0n1p1`). The family that appears depends on the instance generation and its storage
driver, **not** on what the customer typed. An instance moved or restored onto an NVMe-style type will not
resolve a `/dev/vd*` entry, and the reverse is equally true. This is why a repair command copied from a
migration report or from another machine must be re-checked against the devices that exist on the machine
in front of you: run the block-device listing first and use the names it returned.

## The comparison procedure

Run the collector and get the customer's pasted output, then compare:

```
python3 scripts/axes/boot_repair_guide/boot_repair_guide.py fstab-compare --fstab-file <pasted-fstab> --blkid-file <pasted-blkid>
```

The comparison answers, per line:

1. Does the named device resolve to something that exists right now?
2. Does the recorded filesystem type match the type the device actually carries?
3. Is the line syntactically valid, with the required fields, and free of stray leading characters?
4. Is the mount point a critical one (root, boot, EFI) or a candidate for commenting out?
5. Is the entry a false alarm, i.e. correct but unverifiable in the offline state that raised it?

Point 3 matters more than it sounds: a stray character at the start of a line, introduced while someone
edited the file in a hurry, is a real and observed cause of a machine that will not come up, and it is
invisible to the eye when the rest of the line looks right.

## Image and restore semantics, the trap behind most of these tickets

The recurring story: an image or a restore is taken from an instance that had a data disk; a new instance is
created from it; the new instance has no matching data disk; the fstab entry survives; boot goes to emergency
mode. Two statements circulate about images and they are not contradictory once the path is named:

- **Creating a new instance from a custom image** can carry a data disk along with the image, depending on how
  the image was created and what the purchase flow attaches.
- **Replacing the system disk / changing the operating system of an existing instance**, and sharing an image
  across accounts to launch a new instance, does **not** recreate the original data disk on the target. The
  data disk is a separate block-storage resource; to move its content you share the snapshot and build a disk
  from it.

So the correct preventive statement is: before creating an image intended for reuse, remove or comment out
mount entries for disks that the target will not have; and after any restore, expect to have to re-add them.
Both are customer edits, performed with the file backed up.

## False positives: when not to touch the file

An image-scanning service reports a severe fstab risk on an image that boots correctly. The scanner evaluates
the image offline and cannot see whether the mount target directory exists inside the running system, so it
escalates. Where the recorded identifiers match the real volumes and the runtime mount table shows the
volumes mounted, the correct advice is: **leave the file alone**. Editing a working file is how a healthy
instance acquires a genuine boot failure. Report the mismatch between the scanner's view and the runtime
view, and if the customer wants the alert to stop, the answer is to remove entries for disks that were never
intended to travel with the image.

## Writing the corrected entry

The permanent form uses a UUID, the actual filesystem type, and the standard field order; the dump and pass
fields decide whether an integrity check runs at boot, which is where a wrong filesystem type turns a
mountable disk into a startup failure. Follow the published data-disk initialization article for the exact
field set for the filesystem in use, and after any change validate the file **before** the next reboot by
asking the customer to run the mount-table verification command from
`python3 scripts/axes/boot_repair_guide/boot_repair_guide.py evidence-plan --branch fstab-mount` and report the output. A
verification that passes and a reboot that succeeds are two different claims; say which one you have evidence
for.
