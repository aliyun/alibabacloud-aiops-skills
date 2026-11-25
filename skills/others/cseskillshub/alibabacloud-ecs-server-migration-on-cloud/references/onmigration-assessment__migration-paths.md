# Choosing a migration path onto Alibaba Cloud ECS

The path is decided by four facts, in this order: what the source is, whether the
source can still be logged into, where the target must live, and what has to move.
Confirm all four before quoting effort to anyone.

## Entry split

| What the customer says | What it is | Where to go |
| --- | --- | --- |
| A machine in our own room, a VMware or hyper-converged host, a physical server, or a server on another cloud must move onto ECS | Migration onto Alibaba Cloud | This skill, path matrix below |
| Two instances that are both already on ECS, same or different account | Migration inside the platform | ECS to ECS path below |
| A region or zone is being retired and the instance is being shut down | Platform-driven move | Snapshot and image path, plus the retirement notice |
| Only files, a database, or one website need to move | Data-only move | SFTP or a rebuild, not whole-server migration |
| "SMC" appears together with RDMA, `tcp2smc`, or `net.smc` | The kernel SMC-R transport, a different feature | See `os-support.md`, homonym section |
| Capacity is full, a disk resize did not apply, the disk is slow, or the instance will not start on its own | Different symptom axis | Hand off; see the boundary table in `SKILL.md` |

## Path matrix

| Situation | Path | Preconditions and warnings |
| --- | --- | --- |
| Source reachable and can log in, whole machine must move | Server Migration Center whole-server migration | Service-linked role exists (RAM must already be activated); snapshot first; low-peak window; in-memory data flushed and applications stopped |
| Cross-account move of an existing instance | Create a custom image, share it with the target account, create instances there | Sharing is same-region only, a shared image cannot be shared again, and marketplace images carry their own limits. Balances are never merged |
| Cross-region move of an existing instance | Create a custom image, copy it to the target region, create instances there | Local-disk data must be backed up first; the public address does not survive the move |
| Source can no longer be logged into (expired and reclaimed elsewhere) | Import a custom image, or rebuild from a backup | Whole-server migration is impossible without log-in. Import costs OSS storage, outbound traffic, and snapshot fees |
| Only an image file exists | Validate it against the import requirements, then import | Boot mode, virtio and cloud-init presence, and the network configuration are what usually fail validation |
| Target disk must be smaller than the source | Migration used to shrink the disk | Feasible only when the target stays above the bytes actually in use; the reading comes from inside the guest, not from the cloud API |
| Only files or one database must move | SFTP upload, or an internal transfer between instances in one VPC | Do not use whole-server migration when the target's disks would be overwritten |
| Windows sources, domain members, or Remote Desktop transfer | Same paths, plus the Windows-specific driver page | NVMe-equipped newer families need the driver present in the image before the instance can boot |

Start here: [Migrate a server onto Alibaba Cloud](https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md)

## Whole-server migration

- [Migrate a source server to an ECS instance](https://help.aliyun.com/zh/smc/user-guide/migrate-the-source-server-to-the-ecs-instance)
- [Migrate between ECS instances](https://help.aliyun.com/zh/smc/user-guide/migrate-servers-between-ecs-instances)
- [Migration configuration across or within accounts](https://help.aliyun.com/document_detail/171197.html)

The migration target can be an existing instance or a new one. When the target is
an existing instance, its disks are overwritten. State that explicitly and confirm
the target holds nothing worth keeping.

## Image-carried paths

- [Create a custom image from an instance](https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance)
- [Copy a custom image](https://help.aliyun.com/zh/ecs/user-guide/copy-an-image)
- [Share a custom image](https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image)
- [Import a custom image](https://help.aliyun.com/zh/ecs/user-guide/import-a-custom-image)
- [Check whether an image meets the import requirements](https://help.aliyun.com/zh/ecs/user-guide/check-whether-an-image-meets-the-import-requirements)
- [Create a virtual machine and install an operating system](https://help.aliyun.com/zh/ecs/user-guide/create-a-virtual-machine-and-install-an-operating-system-1)
- [Create an instance from a custom image](https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image)
- [Migrate instance data with snapshot and image](https://help.aliyun.com/zh/ecs/user-guide/use-the-snapshot-and-image-features-to-migrate-instance-data)

## Size, cost, and protection

- [Shrink a disk](https://help.aliyun.com/zh/ecs/user-guide/shrink-a-disk.md)
- [Public bandwidth billing](https://help.aliyun.com/zh/ecs/public-bandwidth)
- [Snapshots: creation and billing](https://help.aliyun.com/zh/ecs/snapshots-1)
- [Disk encryption overview](https://help.aliyun.com/zh/ecs/user-guide/encryption-overview)
- [Apply an automatic snapshot policy](https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-applyautosnapshotpolicy.md)

The automatic snapshot policy is a write action. It is offered as a manual step for
batch protection before a window; `scripts/` never calls it.

## Matters that always go to a human

Quotation and discounts, refunds, compensation for an interruption, renewal or
expiry handling, ICP filing, and machine-room addresses. This skill identifies them
and hands them over; it does not answer them.
