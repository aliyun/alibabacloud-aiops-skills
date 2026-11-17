# Console paths and hand-off wording

Where things actually are in the console, what to say when the console misleads,
and the exact sentence to use when a request leaves this skill's scope.

Replace `<region-id>` and `<instance-id>`. The region placeholder matters more than
it looks: several cases in this tier were only about the console sitting on the
wrong region.

## Region first

The console keeps the last region used, which is frequently not the region the
customer means. Before concluding that a resource does not exist:

1. read the region selector at the top left and set it to the region named in the
   alarm or the bill;
2. re-list;
3. if the bill names several regions, repeat, because backup and snapshot storage
   are per-region and one region's list says nothing about another's.

Case T-8E2E6CDC was closed at step 1. The customer had been searching for weeks.

## Entry points

| Purpose | Path |
| --- | --- |
| An instance's backup tab | [ECS console instance backup page](https://ecs.console.aliyun.com/server/{instance_id}/backup?regionId={region_id}) |
| ECS file backup, by region | [file backup page](https://ecs.console.aliyun.com/fileBackup/region/{region_id}) |
| Snapshots, by region | [snapshot page](https://ecs.console.aliyun.com/snapshot/region/{region_id}) |
| Cloud Backup, all its features | [Cloud Backup console](https://hbr.console.aliyun.com/) |
| Database backup | the same Cloud Backup console, with the region corrected; it is not under ECS |
| Balance, bills, top-up | [expense centre](https://billing-cost.console.aliyun.com/fortune/fund-management/recharge) |
| Buying a database backup resource plan | [purchase page](https://common-buy.aliyun.com/?commodityCode=hbr_resourceplan_dp_cn) |
| Manual advanced path for a stuck plan | [DeleteBackupPlan OpenAPI page](https://next.api.aliyun.com/api/hbr/2017-09-08/DeleteBackupPlan) |

The last row is quoted, never executed. Deleting a plan permanently destroys its
backup data.

## Enabling ECS file backup, step by step

1. Open the [instance backup page](https://ecs.console.aliyun.com/server/{instance_id}/backup?regionId={region_id})
   in the correct region.
2. Activate the File Backup Essential Edition. First activation creates the
   service-linked role `AliyunServiceRoleForHbrEcsBackup`. If it fails, check the
   account balance before anything else; a negligible overdue amount is a
   confirmed cause in this tier.
3. Choose the paths to protect. Then list the excluded directories: caches and
   logs are what later produce a disk-space failure, so excluding them up front is
   the cheapest fix available.
4. Set the schedule. Point it away from the workload's busiest window, which is
   also the mitigation for the CPU-saturation candidate.
5. Save, then run one manual backup before trusting the schedule.
6. Reference walkthrough: [configure automatic file backup and restoration](https://help.aliyun.com/zh/ecs/user-guide/configure-automatic-file-backup-and-restoration-for-ecs-instances.md).

Say out loud that owning a resource plan performed none of these steps. In case
T-2AA47A5E the customer had bought a plan, had no technical staff, and the
remaining work was entirely console navigation.

## Verifying what a backup point contains, before restoring

This is the standard move from the source cases and it costs the customer one
minute.

1. Open the backup plan and its point list.
2. Choose Browse on the point closest to when the data was lost.
3. Expand level by level to the exact directory. Do not search; expand.
4. Two outcomes, and both end the enquiry:
   - the path is present, so a restore should work and a skip means a lock, which
     goes to the SOP below;
   - the path is absent from every retained point, so the data predates retention
     and no restore mode can invent it.

The full restore walkthrough: [configure automatic file backup and restoration](https://help.aliyun.com/zh/ecs/user-guide/configure-automatic-file-backup-and-restoration-for-ecs-instances.md).

## Restore SOP when files are skipped

1. Snapshot the target disk first. Use `snapshot-guard`; it prints the cost notice
   before anything is created.
2. Stop the service holding the files - the database engine in case T-BC432E90.
   Stopping a service is manual, always.
3. Re-run the restore choosing overwrite, not skip. The distinction is the reason
   two attempts in that case did nothing.
4. Restart the service.
5. Verify inside the application, not in the console.

Read the restore result details, including the tooltip behind the result icon,
before concluding a completed restore restored anything.

## Protecting data before a configuration change

1. Snapshot, do not file-back: the risk is at disk level.
   [Create a snapshot](https://help.aliyun.com/document_detail/25455.html).
2. Wait for accomplished. A first snapshot is a full copy and takes minutes to
   hours depending on how much has been written; later ones are incremental.
3. Price it before creating it rather than after: [snapshot billing](https://help.aliyun.com/document_detail/56159.html)
   and the [overview](https://help.aliyun.com/zh/ecs/product-overview/snapshots-1).
4. Delete afterwards by hand if the change went well:
   [delete a snapshot](https://help.aliyun.com/document_detail/128131.html).
5. A manual restart from the console takes effect immediately and voids a
   previously scheduled restart window. [Configuration changes](https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes).
6. State the three reboot risks every time: business interruption, data still in
   the page cache and unwritten, no safety copy taken.

## When the alarm and the console disagree

| Symptom | Explanation to give | Evidence |
| --- | --- | --- |
| `EcsReleased` still arriving after the instance is gone and the policies deleted | The entry is the historical record emitted at the release moment. Deleting a policy does not clear history, and the list refreshes lazily. With zero protected resources no new alarm is produced | `triage` proves absence through `DescribeInstances` |
| Jobs not listed, nothing clickable, nothing deletable | A balance too small to notice stopped the service-linked role from being created, so the console functions are absent. Not a browser problem, so skip incognito mode and developer tools | customer reads the balance; no verified API for it |
| Resource billed but nowhere to be found | Wrong console region | region check above |
| An error dialog carrying a request id | A service-side task error. Collect the id verbatim; that is what escalations moved on | case T-9046C4E1 |
| "I want fewer backup versions" | The Essential Edition locks its points and offers no per-point delete; retention is automatic | [benefit description](https://help.aliyun.com/zh/ecs/user-guide/file-backup-essential-edition-benefit-description.md), and quote nothing from memory |

## Cloud Assistant troubleshooting that stays manual

Reference: [check the status of Cloud Assistant and handle exceptions](https://help.aliyun.com/zh/ecs/user-guide/check-the-status-of-cloud-assistant-and-handle-exceptions).

If the customer needs a remote session and does not have the password, the
self-service reset is [reset the logon password of an instance](https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance).
The skill does not perform it.

For a Windows volume that is full: [handle low disk space on Windows instances](https://help.aliyun.com/zh/ecs/user-guide/handle-low-disk-space-on-windows-instances).

One document is named by an alarm message as a title only, and no URL appeared in
the source material, so none is invented here. If a customer needs it, ask for the
link rather than guessing one: "Configure the RAM permissions used by the Cloud
Assistant agent".

For local instance store disks, where snapshot assumptions differ:
[backup local disk data](https://help.aliyun.com/zh/ecs/user-guide/backup-local-disk-data.md).
For ransomware and repeat intrusion, where a single-region copy is not enough:
[disaster recovery solutions](https://help.aliyun.com/zh/ecs/user-guide/disaster-recovery-solutions.md)
and [ECS data backup and high availability](https://help.aliyun.com/zh/ecs/user-guide/ecs-data-backup-mechanism-and-high-availability-architecture.md).

## Hand-off wording

Say what the request is, name the owner, and stop. Do not half-do it.

| The customer asks | Reply |
| --- | --- |
| "delete these files for me" | Deleting data is not something this skill does, on the instance or in a vault. Here is the candidate list with sizes, here is the snapshot to take first, and here is where deletion is manual. |
| "cancel cloud backup so it stops billing" | Cloud Backup has no whole-service off switch. The steps and the permanent-data-loss warning are in `billing-map.md`. Deleting a plan cannot be undone. |
| "this bill line is wrong, refund it" | Billing amounts, refunds and unsubscribes go to the expense centre and a billing specialist. What can be done here is list what exists in the region, which is usually the start of the explanation. |
| "the disk grew but the filesystem did not" | `area:disk-expand-diagnosis`. |
| "the instance will not start" or "it was stopped for arrears" | `area:instance-state-diagnosis`. For a pay-as-you-go instance stopped by arrears, the urgent part is protecting data once topped up: snapshot first. Note that release timing is a product term to confirm, not something this skill asserts. |
| "the disk is slow" | `area:resource-bottleneck`. |
| "walk me through enabling it" for its own sake | `alibabacloud-cloudbackup-ecs-file-backup-essential-edition` covers enablement; this skill is for when something failed. |
| "why did this backup task fail internally", with no verifiable signal | A Cloud Backup support ticket, with the request id, the plan id, the region and the timestamps. Support could not read task internals either. |

The pay-as-you-go arrears row is included because case T-24BB970B asked for a
free extension to buy time for a backup. Extensions apply to subscription
instances, and a payment request is not this skill's to make; the durable advice
is to snapshot as soon as the balance is cleared.
