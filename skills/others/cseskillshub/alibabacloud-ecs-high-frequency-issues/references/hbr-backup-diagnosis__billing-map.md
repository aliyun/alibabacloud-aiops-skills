# Billing map

Four separate products, four separate billing lines, and the most common first
misconception in this tier. This file is the lookup table; `billing-attribution`
supplies the live resource list that plugs into it.

Every URL below comes from the help search for this tier or from a link a support
engineer actually sent in one of the source cases. Tracking query parameters were
stripped. No number in this file is quoted from a case: two source cases state
conflicting quota figures, so quantities are never reproduced here.

## The four mechanisms

| Mechanism | Product | Console location | Billed for | Switch it off by |
| --- | --- | --- | --- | --- |
| Disk snapshot | ECS snapshot | ECS console -> Storage & Snapshots -> Snapshots, per region | used snapshot capacity, per region | deleting the snapshots ([docs](https://help.aliyun.com/document_detail/128131.html), [console guide](https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1.md)) |
| File-level scheduled backup of instance paths | Cloud Backup (HBR), ECS File Backup Essential Edition | [Cloud Backup console](https://hbr.console.aliyun.com/), and the ECS [file backup page](https://ecs.console.aliyun.com/fileBackup/region/{region_id}) | [billing items](https://help.aliyun.com/zh/cloud-backup/product-overview/billing-methods-and-billable-items); the basis is [attached block storage capacity](https://help.aliyun.com/zh/cloud-backup/support/what-is-the-billing-basis-for-ecs-file-backup-essential-edition) | [official-doc] deleting every backup plan, **uninstalling the backup client**, then deleting every backup vault - and a vault with **backup lock** enabled cannot be deleted at all until its backup data expires ([stop-billing guide](https://help.aliyun.com/zh/cloud-backup/product-overview/how-do-i-stop-being-billed-for-cloud-backup)) |
| Instance-level backup and cross-region copy | Cloud Backup (HBR), whole-instance backup | [Cloud Backup console](https://hbr.console.aliyun.com/) | [official-doc] software licence fee per ECS instance, plus snapshot charges - **the snapshot part is billed by the snapshot service, not by Cloud Backup**; cross-region replication adds target-region snapshot capacity and transfer, also billed by the snapshot service | as above, plus removing replication |
| Database backup | ApsaraDB RDS / Database Backup | its own console, never an ECS backup page | warehouse rental plus storage | its own product controls |
| The disk itself | Block storage | ECS console -> Disks, per region | [capacity, performance and burst](https://help.aliyun.com/zh/ecs/block-storage-devices) | releasing the disk; subscription disks follow the instance |

An instance in subscription does not make any of the above free. A pay-as-you-go
data disk, a burst-capable disk, a snapshot chain and an enabled Cloud Backup
plan each add their own line, and that combination is the exact explanation
support gave in case T-5861B286.

## Resource-plan deduction matrix

Confirm against the linked official page before repeating any row. This is
guidance about scope, not an entitlement guarantee: it records what support
stated in the source cases, cross-checked against the product pages.

| Resource plan | Can offset | Cannot offset |
| --- | --- | --- |
| OSS standard / locally redundant storage plan | snapshot storage in the same area, including a snapshot after it has been replicated | Cloud Backup backup storage, block storage, anything outside its own region scope |
| Cloud Backup plan for the File Backup Essential Edition | the corresponding ECS file backup storage | the underlying disk charge, snapshot charge |
| [Database backup resource plan](https://common-buy.aliyun.com/?commodityCode=hbr_resourceplan_dp_cn) | database backup warehouse rental and its storage | ECS file backup, snapshots |
| Any plan at all | - | cross-region replication transfer. There is no plan for it, in either region |

The row that surprised the customer in case T-C0611EEE is the last one: whole-
instance backup inside one region costs storage only, while cross-region
replication costs storage twice plus transfer, and the transfer part has nothing
that offsets it.

## Stop-billing and cancel-backup path (manual, with the warning)

Cloud Backup cannot be turned off as a service. The only way billing stops is
deleting the objects that generate it.

1. Switch the console to the region that owns the resource. Nothing else on this
   list works if this step is wrong, and the console remembers the last region
   rather than the obvious one.
2. In [Cloud Backup](https://hbr.console.aliyun.com/) or the ECS
   [file backup page](https://ecs.console.aliyun.com/fileBackup/region/{region_id}),
   list the backup plans and note which instances each covers.
3. Delete each backup plan.
4. Delete the backup vaults once empty.

**Deleting a backup plan or a backup vault permanently destroys the data stored
in it. It cannot be recovered afterwards, by this skill, by support or by any
API.** Say this before the customer clicks, not after.

An advanced manual alternative exists for step 3 - calling `DeleteBackupPlan`
through the [OpenAPI page](https://next.api.aliyun.com/api/hbr/2017-09-08/DeleteBackupPlan)
with `RegionId`, `planId`, `sourceType=ECS_FILE` and `edition=BASIC`. This skill
never calls it. It is quoted because in case T-9046C4E1 the console itself was
unusable, and the API was the only remaining customer-side route.

A resource-plan purchase is a commercial action. Point at the purchase entry
above and stop there.

## Arrears and the service-linked role

A negative balance, however small, stops the platform from creating
`AliyunServiceRoleForHbrEcsBackup`. The visible symptom is not a payment error -
it is a backup console with no jobs listed, nothing clickable, and no way to
cancel, which reads as a broken UI. Case T-9046C4E1 was a one-cent balance.

- Ask about the balance before troubleshooting the browser. Incognito mode and
  developer-tools collection were both wasted turns in that case.
- Top-up entry: [expense centre](https://billing-cost.console.aliyun.com/fortune/fund-management/recharge).
- This skill has no verified billing or balance API, so the customer reads the
  balance; the skill never claims to.

## Snapshot-versus-backup confusion, the four recurring shapes

| Customer says | What is true | Where to look |
| --- | --- | --- |
| "I already have snapshots, why is there a cloud backup charge" | Separate products, separate billing. A snapshot is not a file backup and vice versa | [comparison](https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md) |
| "disk space is full, so I must delete old backups to fix it" | The alarm means the volume inside the instance. Backup storage is unrelated and cannot be trimmed point by point in the Essential Edition, whose points are locked | [benefit description](https://help.aliyun.com/zh/ecs/user-guide/file-backup-essential-edition-benefit-description.md) |
| "the RDS backup fee is on my ECS bill, so it is an ECS problem" | Database backup is its own product with its own console | the [billing items](https://help.aliyun.com/zh/cloud-backup/product-overview/billing-methods-and-billable-items) page for which warehouse rental belongs to |
| "no jobs listed, so I am not backed up and not billed" | Either the region is wrong or the service-linked role failed to create. Absence in a console is not absence in a billing system | region check, then balance check |

## What this skill never does

Does not read a bill, a balance or an invoice line. Does not purchase, renew,
unsubscribe or refund. Does not delete a plan, a vault, a snapshot or a file.
Does not state a price from memory. Its output is: the resources that verifiably
exist in a named region, mapped to the billing item that would explain them, with
the official page attached.
