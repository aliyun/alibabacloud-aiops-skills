# Cloud disk id to guest device name

## Three names for one object

| Layer | Identifier | Example shape |
| --- | --- | --- |
| Control plane | Disk id | `d-` followed by alphanumerics |
| Linux guest, virtio hosts | Block device | `/dev/vda`, `/dev/vdb`, partitions `/dev/vdb1` |
| Linux guest, NVMe based instances | Namespace device | `/dev/nvme0n1`, `/dev/nvme1n1`, partitions `/dev/nvme1n1p1` |
| Windows guest | Disk number plus drive letter | Disk 1, `E:` |

The reason a customer says the disk disappeared is often only this: they searched for one
name and the guest uses another. A disk whose guest device is `/dev/nvme1n1` will never
turn up in a listing of `vd*`, and a person looking for the letter they had before a
reinstall will not find it after volumes were renumbered. See
[NVMe device naming](https://help.aliyun.com/zh/ecs/user-guide/nvme-protocol.md) for which
instance families use which scheme.

## How the scripts build the map

1. `DescribeDisks` supplies, per disk: disk id, size in GiB, whether it is the system disk,
   the instance it is attached to, and the device name the control plane recorded.
2. The guest supplies the devices it actually enumerates, with sizes, filesystem types and
   mount points.
3. The join is done on size, with a tolerance, restricted to whole disks rather than
   partitions. The result is printed as a table in the report.

The map is a proposal, not proof. Two disks of the same size cannot be separated by size
alone, and the control plane's recorded device name is the attachment it handed out, which
the guest may present differently. When two rows could match, the report says so instead of
picking one.

The unambiguous key would be the disk serial number, which the platform exposes on the
disk record and which a wider device listing would print next to each name. That listing
variant is not on the approved command list for this skill, so serial matching is not
performed. If the disambiguation matters, ask the customer to run their own listing and
paste it.

## The one thing the map exists to prevent

Every destructive step in this tier takes a device name as its argument. A customer who
runs an initialisation against the system disk because they mixed up `vdb` and `vda` loses
the instance, not just the volume. So the report always includes the system disk row, and
the agent states which device belongs to the operating system before handing over any
manual command that writes to a device.

## Windows specifics

`Get-Volume` and `Get-PSDrive` report volumes, not disks. A cloud disk that the guest has
not brought online, or that has no drive letter, is invisible to both and to Explorer,
which reproduces the Linux complaint in different words. Bringing a volume online and
assigning a letter are console or Disk Management actions and are never issued here. A
disk-management tool that reports an error about a disk it cannot find is covered in
[error-signatures.md](disk-attach-os-visibility__error-signatures.md); the safe response is a recovery point first,
then the human repair path.

## Size units do not line up exactly

Cloud sizes are whole GiB. A guest reports the usable capacity of the device, slightly
below the purchased figure once a filesystem has taken its metadata, and a raw device
listing may print bytes, blocks or a rounded suffix. Matching therefore uses a tolerance
rather than equality, and a disk whose size does not match anything is reported as
unmatched instead of being snapped to the nearest device.
