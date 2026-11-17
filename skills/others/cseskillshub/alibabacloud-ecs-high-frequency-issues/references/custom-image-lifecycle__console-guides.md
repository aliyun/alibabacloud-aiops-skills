# Console Entries and Official Documentation Map

Only links evidenced in real ticket conversations or the tier research are
listed. The agent cites these URLs when guiding a customer; never invent
other documentation URLs.

## Console entries (what a human clicks)

| Purpose | Entry |
|---|---|
| ECS instance list (snapshot/image creation entries live per-instance here) | https://ecs.console.aliyun.com/server/region |
| Custom image list (per region selector!) | https://ecs.console.aliyun.com/image |
| Snapshot list (per region selector!) | https://ecs.console.aliyun.com/snapshot |
| VNC login when SSH into a new instance from a custom image fails | https://ecs.console.aliyun.com/vnc/index.htm |
| Check which instance types are purchasable per region | https://ecs-buy.aliyun.com/ecs#/instanceTypeByRegion |
| Bill detail for snapshot charges | https://usercenter2.aliyun.com/home |

Region-selector note (ticket-proven failure mode): images/snapshots are
per-region resources; the #1 cause of "my image disappeared" is the wrong
region in the console. The script's report mode offers `--all-regions` for
the same question from the API side.

## Documentation map by topic

### Creating images, snapshot dependency (S1/S4)

| Topic | Link |
|---|---|
| Custom image overview | https://help.aliyun.com/zh/ecs/user-guide/overview-36.md |
| Create an image from an instance | https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance |
| Snapshot billing (charged by stored GB, no free tier implied) | https://help.aliyun.com/document_detail/56159.html |
| Data protection scheme comparison (backups vs snapshots) | https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md |
| Shared-responsibility model (platform does not auto-back-up your data) | https://help.aliyun.com/zh/ecs/user-guide/ecs-shared-responsibility-model |
| Community image overview (why publishing changes deletion flow) | https://help.aliyun.com/zh/ecs/user-guide/overview-12.md |

### Sizes, disks, restore targets (S2)

| Topic | Link |
|---|---|
| Replace the OS of an instance | https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance |
| Create an instance using a custom image | https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image |
| Create a disk from a snapshot | https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot |
| Attach / detach / release a data disk (migration follow-ups) | https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk , https://help.aliyun.com/zh/ecs/user-guide/release-a-disk |
| Re-initialize a system disk (blocked after image/snapshot deletion) | https://help.aliyun.com/document_detail/25449.html |
| Shrink a disk path (via SMC-style migration) | https://help.aliyun.com/zh/ecs/user-guide/shrink-a-disk |
| Resize step 1 (extend capacity) / step 2 (partition+fs) | https://help.aliyun.com/zh/ecs/user-guide/step-1-resize-a-disk-to-extend-its-capacity , https://help.aliyun.com/zh/ecs/user-guide/step-2-resize-partitions-and-file-systems/ |
| Instance start/stop state explanation | https://help.aliyun.com/zh/ecs/support/when-an-ecs-instance-is-stopped-or-restarted-in-the |
| Windows image usage rules (RAM floors, no Win10 public image) | https://help.aliyun.com/document_detail/25430.html#section-ajc-kdx-wdb |

### Sharing and cross-region copy (S1/S3/S4)

| Topic | Link |
|---|---|
| Share a custom image with another account | https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image/ |
| Copy an image to another region | https://help.aliyun.com/zh/ecs/user-guide/copy-an-image |
| Transfer an instance to another account (limits; image-based plan instead) | https://help.aliyun.com/document_detail/151401.htm |

### Import / export / image building (S3)

| Topic | Link |
|---|---|
| Instance startup mode (BIOS/UEFI) | https://help.aliyun.com/zh/ecs/user-guide/instance-startup-mode.md |
| Adapt Linux images to NVMe system disks | https://help.aliyun.com/zh/ecs/adapt-linux-custom-images-to-nvme-based-system-disks |
| Build a Linux image locally (VirtualBox path) | https://help.aliyun.com/zh/ecs/user-guide/create-a-virtual-machine-and-install-an-operating-system-1.md |
| SSH "permission denied" on login (guest sshd config) | https://help.aliyun.com/zh/ecs/user-guide/what-do-i-do-if-the-permission-denied-please-try-again-error-message-appears-when-i-log-on-to-a-linux-instance-as-the-root-user-by-using-ssh |

Known documentation gaps (flagged during tier research; do not paper over
them): no dedicated official troubleshooting article for "custom image
creation failing/slow" matched in the evidence set; no dedicated article
for the share-RECEIVE console flow; export format details beyond the API
parameter are thin. For these, the skill sticks to verifiable API evidence
plus console manual paths.

## Import / export specifics evidenced from tickets

- Import flow: upload the image file to an OSS bucket in the target region,
  then ImportImage from the console/API (OSS bucket/object are the API
  inputs). QCOW2 import support was confirmed in a ticket answer; treat
  other formats as "verify in the console first".
- Export flow: ExportImage writes into the customer's OSS bucket and bills
  OSS storage/requests; Windows images are blocked by licensing (never
  downloadable), and snapshots themselves cannot be exported.

## In-guest inspection commands (whitelist)

These are inspection-only commands (they list state; they change nothing).
Run only through a customer-approved channel (Workbench or Cloud Assistant
run with the user's explicit per-command consent); hand the same lines to
the customer to paste output when no channel is available.

| Purpose | Linux | Windows |
|---|---|---|
| Space usage | `df -h` | `Get-Volume` |
| Inode usage | `df -i` | (no equivalent -> confidence note) |
| Mount state after restore | `findmnt` | `Get-PSDrive` |
| Big-directory volume | `du -sh <dir>` | inspection-only folder listing |
| Deleted-but-open space | `lsof +L1` | n/a |
| One file detail | `stat <path>` | n/a |

Out-of-whitelist guest needs (NVMe driver presence, grub/EFI inspection,
sshd configuration) are answered with manual steps + the docs above, never
with a claim that the skill inspected them.
