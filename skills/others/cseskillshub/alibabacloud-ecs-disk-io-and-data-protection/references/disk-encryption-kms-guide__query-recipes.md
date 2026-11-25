# Read-only query recipes and console checks

Two audiences: the **agent**, which only ever runs `scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py`, and the
**customer**, who may run the equivalents below with their own profile or click through the
console. Nothing on this page changes a resource.

## 1. What the entry script sends, per read

Product `ecs`, API version `2014-05-26`, one `RegionId` per run. These are the exact
permission points and parameters, so an answer can be replayed or checked by hand.

| Purpose | Action | Parameters this skill sends | Fields the report reads back |
|---|---|---|---|
| Instance facts and id sanity | `DescribeInstances` | `RegionId`, optionally `InstanceIds`, `PageNumber`, `PageSize` | `InstanceId`, `Status`, `ZoneId`, `InstanceType`, `OSName`, and any returned field whose name mentions encryption, KMS or an algorithm |
| Disk inventory and encryption state | `DescribeDisks` | `RegionId`, then exactly one scope of `InstanceId` / `DiskIds` / `SnapshotId`, optionally `Encrypted`, plus `PageNumber`, `PageSize` | `DiskId`, `Type`, `Category`, `Size`, `Status`, `InstanceId`, `ZoneId`, `Encrypted`, `KMSKeyId` when present |
| Snapshot chain | `DescribeSnapshots` | `RegionId`, then one scope of `InstanceId` / `DiskId` / `SnapshotIds`, plus `PageNumber`, `PageSize` | `SnapshotId`, `SourceDiskId`, `SourceDiskType`, `CreationTime`, `Status`, `Encrypted`, `KMSKeyId` when present |

Notes:

- The script does not assume the response field names. It surfaces **every** returned field
  whose name mentions encryption, KMS or an algorithm, so a field that this tier has not seen
  yet still appears in the evidence instead of being silently dropped. If the encryption block
  comes back `not-returned`, report the state as **unconfirmed**.
- `Encrypted` as an input is a **filter**, not a conclusion: it narrows the list, it does not
  prove anything about the disks left out of it.
- Cross-region questions need one run per region. There is no all-region read here.

## 2. Manual equivalents for the customer's own profile

```bash
aliyun ecs describe-instances --region-id cn-hangzhou --instance-ids '["i-2ze8xxxxxxxxxxxxxxx"]'
aliyun ecs describe-disks --region-id cn-hangzhou --instance-id i-2ze8xxxxxxxxxxxxxxx
aliyun ecs describe-disks --region-id cn-hangzhou --disk-ids '["d-2zeeop9jdn4n6e2zjzx3"]'
aliyun ecs describe-disks --region-id cn-hangzhou --encrypted true
aliyun ecs describe-snapshots --region-id cn-hangzhou --disk-id d-2zeeop9jdn4n6e2zjzx3
```

The agent uses the entry script instead of building these; they are printed here so a customer
can confirm what was read.

## 3. Console check paths (what the customer looks at)

| Question | Where to look |
|---|---|
| Is this disk encrypted | ECS console -> Storage & Snapshots -> Disks -> the disk's detail pane, the encryption row |
| Which key, service or customer-managed | The same row's key reference, then the key-management console -> the key list and its alias, in the **same region** |
| Is this snapshot encrypted | ECS console -> Storage & Snapshots -> Snapshots -> the snapshot's detail pane |
| Does the instance have a data disk at all | ECS console -> the instance -> the block storage list |
| Can I see an encryption option while provisioning | The disk purchase panel; if the option is greyed out or absent, note the region and the disk category before reporting it |

A missing "Encryption" column in a list view is not evidence: the field lives on the detail
pane. Several customers look only at the list and conclude the feature is absent.

## 4. Guest-side facts: the customer runs these and pastes the output

The cloud reads above cannot see inside the disk. Ask for the output verbatim; label the
conclusion "customer-pasted evidence".

**Windows - is the volume protected by the operating system rather than by disk encryption**:

```powershell
manage-bde -status
Get-BitLockerVolume | Select-Object MountPoint, ProtectionStatus, EncryptionMethod
Get-Disk | Select-Object Number, FriendlyName, Size, PartitionStyle, HealthStatus, IsOffline
```

Use the status forms only. Do not run any key or protection change from this guide, and do
not run a partitioning tool to "have a look".

**Linux - what the kernel actually sees**:

```bash
lsblk -o NAME,SIZE,TYPE,FSTYPE,STATE,MOUNTPOINT
blkid
findmnt -t ext4,xfs,btrfs
df -hT
cryptsetup status <mapper-name>
```

Typical conclusions customers wrongly draw, and the correct next sentence:

| Pasted output | Wrong conclusion | Correct answer |
|---|---|---|
| `manage-bde -status` shows protection off | "So the disk is not encrypted at all." | Guest volume protection and server-side disk encryption are separate layers; read the disk attribute before comparing them |
| `Get-Disk` shows a new disk offline | "The disk was lost." | A freshly provisioned disk is expected to need initialisation - that is Path A step A4 in `encryption-basics.md` |
| `lsblk` shows no mount point | "The data disk is broken." | Mounting and filesystem work belongs to the disk-capacity and remote-access tiers, not here |

## 5. Closing loop after any customer-performed step

Re-run the same read that produced the original finding and diff the encryption block:

```bash
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --instance-id <id> --include-snapshots
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --disk-id <id> --format json
```

Report `STATUS: OK` only when the expected field came back from the read. A step the customer
"finished" without a re-read is `DEGRADED`, not done.
