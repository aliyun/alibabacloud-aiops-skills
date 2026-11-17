# Linux Expansion Paths

Everything here is **guidance for a human to execute**. This skill never runs a
partition or filesystem writer, and never wraps one so that something else runs it.
A fresh snapshot of the target disk is a precondition for every path below; see
[snapshot-first.md](disk-expand-diagnosis__snapshot-first.md).

## Step 1: establish the layout

The device form and the filesystem type decide which command is correct, and neither
can be read from a cloud API. Ask the customer to run these inside the instance and
paste the raw output. This skill is not permitted to dispatch them automatically:

```bash
df -Th
lsblk -f
blkid
fdisk -lu
df -i
```

From that output establish four things before writing any command:

1. The disk device name and its naming family.
2. The partition number that holds the target filesystem.
3. The partition table type, MBR (`dos`) or GPT.
4. The filesystem type on that exact partition.

If any of the four is missing, stop and ask. Guessing a device name or a filesystem
type is how a routine expansion turns into a data event.

## Step 2: device naming families

| Family | Whole disk node | Partition node | Notes |
| --- | --- | --- | --- |
| virtio | `/dev/vda`, `/dev/vdb` | `/dev/vda1`, `/dev/vda3`, `/dev/vdb1` | The partition number is appended directly, with no `p`. |
| NVMe | `/dev/nvme0n1`, `/dev/nvme1n1` | `/dev/nvme1n1p1` | A `p` separates the disk from the partition number. |
| SCSI / SATA style | `/dev/sda`, `/dev/sdb` | `/dev/sda1` | Number appended directly. |
| LVM physical volume | `/dev/vdb` | `/dev/mapper/<vg>-<lv>` | The grow target is the logical volume, not the partition. Separate path below. |

Getting the family wrong produces a command that fails harmlessly at best and
targets the wrong object at worst. The script derives the partition node from the
disk node with `partition_device` and refuses to emit a command when the form is
not recognisable.

## Step 3: the ordinary path, MBR or GPT with a numbered partition

Two commands, in this order. The partition grows first; the filesystem then fills
the enlarged partition.

```bash
sudo LC_ALL=en_US.UTF-8 growpart /dev/vda 3
```

* The disk device and the partition number are **two separate arguments with a
  space between them**. Writing `/dev/vda3` in that position is the single most
  common failure at this step, so call the space out explicitly every time.
* `LC_ALL=en_US.UTF-8` keeps the tool's output in English, which matters because
  this skill matches on English error strings and a translated refusal looks like
  no signal at all.
* The partition number comes from the layout established in step 1. A root
  filesystem on `/dev/vda3` takes `3`; on `/dev/vda1` it takes `1`.

Then the filesystem command, chosen by the type observed **on that partition**:

| Filesystem | Command | Grown through |
| --- | --- | --- |
| ext4, ext3, ext2 | `sudo resize2fs /dev/vda3` | the device node |
| xfs | `sudo xfs_growfs /` | the **mount point**, not the device node |
| btrfs | its own resize commands | not automated by this skill |

`resize2fs` must never be emitted against xfs, and `xfs_growfs` must never be
pointed at a device node. If the filesystem type is undetermined, emit no
filesystem command at all and ask for `blkid` output.

Verify afterwards:

```bash
df -h
```

On Linux, `df -h` is the verification step. Console disk pages and any Windows
style "refresh the disk management view" wording are not, and reusing that phrasing
for a Linux customer is a known defect in human handling that this skill avoids.

## Step 4: paths that are not automated here

### LVM

When `lsblk -f` shows `LVM2_member`, a `/dev/mapper/` node, or a "Linux LVM"
partition type, the grow target is a logical volume and the sequence differs:
the physical volume is grown, then the volume group is extended, then the logical
volume, then the filesystem. Every one of those steps is a writer.

This skill reports `SPECIAL_LAYOUT_LVM_OR_EXTENDED_PARTITION`, points the customer
at the LVM extension documentation, and escalates for a human to confirm the exact
target object. Two facts are worth stating to the customer:

* Where an image was created from an LVM instance and used to launch a new one, the
  image specification converts LVM managed partitions to standard partitions, so
  the new instance no longer has LVM even though the source did. That is expected
  and generally harmless, and it means the standard path applies to the new
  instance.
* Online expansion works for both layouts and does not require an instance restart.

### Extended partition carrying logical partitions

An extended partition (type shown as `Extended` in `fdisk -lu`) containing logical
partitions such as `/dev/vdb5` does not respond to the generic pairing: growing the
logical partition and growing its container are separate operations, and the
container must move first.

A `Nothing to do!` from the filesystem command in this layout means the filesystem
already fills its logical partition, and the container is what never moved. This
skill reports `PARTITION_LAYER_NOT_ENLARGED` and escalates; it does not emit a
guessed command.

### Whole-device filesystem, no partition table

A filesystem written directly to `/dev/vdb` with no partition has no partition to
grow. The filesystem command alone is the whole operation, but confirming that this
really is the layout requires `lsblk -f` and `blkid` together. The script refuses to
emit a command for an unnumbered device and asks for confirmation instead.

### Partition table metadata inconsistent with the device size

`GPT PMBR size mismatch` or "the backup GPT table is not at the end of the device"
means the metadata still describes the pre-expansion size. Standard walkthroughs do
not cover reconciling it and a partition table writer applied by guesswork can
destroy the table. Report `PARTITION_TABLE_METADATA_INCONSISTENT` and escalate to a
human engineer. Do not proceed.

### Filesystem carrying errors

A refused online resize, a non-writable remount, or any superblock complaint means
repair comes before growth. Report `FILESYSTEM_HEALTH_BLOCKED`, require a snapshot,
and hand the repair to a human with the disk detached or the instance in a
controlled state. See [error-signals.md](disk-expand-diagnosis__error-signals.md).

## Step 5: environment preconditions that block an otherwise correct command

These are not command errors and must not be reported as such.

| Precondition | How it shows up | Handling |
| --- | --- | --- |
| Resize helper not installed | `growpart: command not found` | Package installation is a customer action. Report and hand over. |
| Name resolution or repository unreachable | The install itself fails with a resolution or mirror error | Outside this tier. Ask the customer to check resolver configuration manually; it is not on the approved command list, so it is never dispatched. |
| Filesystem at 100 percent of its blocks | The grow fails for lack of working space | Hand off to the disk capacity diagnosis, then return. |
| Inode table at 100 percent | `df -i` shows `IUse%` at 100 | Hand off to the disk capacity diagnosis. Snapshot before any cleanup. |
| Insufficient privilege | A permission refusal on a healthy filesystem | Confirm the command was run with `sudo`. Only after that, treat the same string as a filesystem health signal. |

## Official documentation to hand over

Resolved during the requirements phase and quoted as they were returned:

* Offline expansion of a Linux data disk partition and filesystem:
  <https://help.aliyun.com/zh/ecs/user-guide/offline-extend-partitions-and-file-systems-on-a-data-disk-of-a-linux-instance.md>
* Extending a logical volume with LVM:
  <https://help.aliyun.com/zh/ecs/user-guide/extend-an-lv-by-using-lvm.md>
* Creating a logical volume with LVM, the supported way to pool several disks:
  <https://help.aliyun.com/zh/ecs/user-guide/use-lvm-to-create-a-logical-volume.md>
* Disk resizing and shrinking FAQ:
  <https://help.aliyun.com/zh/ecs/disk-resizing-and-shrinking-faqs.md>
* Attaching a data disk:
  <https://help.aliyun.com/zh/ecs/user-guide/attach-a-data-disk.md>
* Initializing a Linux data disk up to 2 TiB:
  <https://help.aliyun.com/zh/ecs/user-guide/initialize-a-data-disk-whose-size-does-not-exceed-2-tib-on-a-linux-instance.md>

### Known documentation gaps

Recorded so that nobody fills them from memory:

* Reconciling a GPT backup table or a protective MBR that disagrees with the device
  size has no published walkthrough. Escalate.
* The extended partition plus logical partition grow sequence is not covered by the
  general expansion documents. Escalate.
* The applicability and operating system limits of the console tool that expands a
  partition and filesystem in one action are not documented in material this skill
  can cite. Mention the tool as a console entry point only, never as a verified
  procedure: <https://ebs.console.aliyun.com/tools/resizeFileSystem>
