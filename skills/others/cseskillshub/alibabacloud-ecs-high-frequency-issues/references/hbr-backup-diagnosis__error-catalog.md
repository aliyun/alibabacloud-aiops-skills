# Error and symptom catalogue

Provenance for every row is a real historical support case in this tier, listed
in the last column as a case id. Nothing here is recalled from general product
knowledge, and no row was written before the wording existed in the case record.

## How matching works, and its honest limit

The ECS and Cloud Backup consoles localise their message text. A customer pastes
whatever their console language produces. This skill therefore matches on two
things only:

1. stable ASCII product tokens that survive every locale, such as `EcsReleased`
   or `AliyunServiceRoleForHbrEcsBackup`; and
2. the English wording a customer dictates or translates.

A message that is neither of those is classified `UNKNOWN` and the skill asks for
`--category` instead of guessing. That is the designed behaviour, not a defect.

Priority matters: an alarm reading "the backup task failed because the instance
was released" must land on `ECS_RELEASED`, not on the generic backup-task class,
because the two have different answers. The ordered pattern list lives in
`SYMPTOM_PATTERNS` in `scripts/areas/hbr_backup_diagnosis/_constants.py` and this table is its human form.

## Catalogue

| Customer-visible wording (representative) | Category | Confirmed root cause | First move | Case |
| --- | --- | --- | --- | --- |
| "cannot access Cloud Assistant", "instance internal environment is abnormal", "cloud assistant service is unavailable" while the security group is already open | `CLOUD_ASSISTANT_UNREACHABLE` | A third-party tunnel or mesh client claims the 100.64.0.0/10 or 100.100.0.0/16 range that internal service endpoints use | `triage`, then present the candidate list. Do not probe the guest | T-0DDE6FAC, T-29709FD4 |
| same alarm, and the agent worked yesterday | `CLOUD_ASSISTANT_UNREACHABLE` | The tunnel client rewrites the system resolver, so the Cloud Assistant domain stops resolving | present candidate `dns-overwritten-by-client`; a reboot only fixes it until the client rewrites again | T-4149C679 |
| "cloud assistant is not running", "where do I start Cloud Assistant" | `CLOUD_ASSISTANT_UNREACHABLE` | The Aliyun Assist service is stopped or set to disabled | present candidate `assist-service-stopped`; starting a service is manual | T-9005CD95 |
| daily file-backup failure alarm whose timestamps sit in the busiest hours | `CLOUD_ASSISTANT_UNREACHABLE` | Sustained CPU saturation stops the agent process from being scheduled | `triage`; state that CloudMonitor is not queried by this version, so this stays a hypothesis to test | T-9ED3CF6E |
| "insufficient disk space caused the file backup to fail", and the customer asks how to delete old backups or why the free quota was not enough | `DISK_SPACE_INSUFFICIENT` | The volume inside the instance is full. The backup storage quota is a different thing entirely | `triage`, then `guest-probe --command df_h` after consent, then `snapshot-guard` before any cleanup | T-2E38E856 |
| "no space left on device", "cannot create new file", but free bytes remain | `DISK_SPACE_INSUFFICIENT` | inodes exhausted on a Linux volume | `guest-probe --command df_i`; compare IUsed with IFree | T-2E38E856 |
| same on Windows, drive shows free space | `DISK_SPACE_INSUFFICIENT` | volume genuinely full at the reported path, or a per-directory quota | `guest-probe --command get_volume` then `fsutil_diskfree`; see `guest-commands.md` for the NTFS inode wording | T-2E38E856 |
| "EcsReleased" alarm that keeps arriving after the instance is gone | `ECS_RELEASED` | The alarm is the historical record emitted at the release moment. Deleting a policy does not clear history and the list refreshes lazily | `triage`: `DescribeInstances` proves the instance is gone, then explain history versus current state | T-EF99E331 |
| "the restore finished but the data is still missing", "is this backup feature fake" | `RESTORE_TARGET_OCCUPIED` | The restore reported success while skipping files held open by the running database engine | `triage`, then the Browse check, then the stop-service / overwrite-restore SOP | T-BC432E90 |
| same, and Browse shows the path in no retained point | `RESTORE_TARGET_OCCUPIED` | The deletion predates every retained backup point, so the data was never captured | state plainly that no restore mode can produce data absent from the point. Stop retrying | T-BC432E90 |
| "the bill shows a cloud backup charge but I already have snapshots and an RDS backup" | `ROLE_OR_BILLING_BLOCKED` | Pay-as-you-go disks, burst-capable disks and the File Backup Essential Edition each bill independently of a subscription instance | `billing-attribution`, then map to `billing-map.md` | T-5861B286 |
| "there is a database backup warehouse rental fee but I cannot find any backup instance" | `ROLE_OR_BILLING_BLOCKED` | The console region selector is on a different region from the one holding the resource | ask the region first, then `billing-attribution --region-id <that region>` | T-8E2E6CDC |
| "I get a failure alarm every day, the console shows no task, and I cannot delete or cancel anything" | `ROLE_OR_BILLING_BLOCKED` | A negligible overdue balance blocked automatic creation of `AliyunServiceRoleForHbrEcsBackup`; console functions silently vanish | `triage` plus `billing-attribution`; send the customer to the expense centre. It is not a browser problem | T-9046C4E1 |
| "I want to stop being billed for cloud backup" or "cancel the backup" | `ROLE_OR_BILLING_BLOCKED` | Cloud Backup has no whole-service off switch; billing stops only by deleting plans and then vaults | guidance only, with the permanent-data-loss warning, from `billing-map.md`. Never automated | T-8E2E6CDC, T-95BF88EB |
| "does an OSS resource plan cover this", "what does cross-region replication cost" | `ROLE_OR_BILLING_BLOCKED` | The deduction boundary between snapshot, backup storage and replication traffic is unknown to the customer | answer from the matrix in `billing-map.md` | T-C0611EEE |
| "backup task encountered an exception", no further detail | `BACKUP_TASK_ABNORMAL` | Not determinable from the verified API set; HBR task internals have no verified query action here | collect the alarm text, screenshot, plan id, region and request id, then hand off | T-9046C4E1 |
| an error dialog containing a request id | `BACKUP_TASK_ABNORMAL` | A service-side task error the customer cannot inspect | capture the request id verbatim; that is what support escalated on | T-9046C4E1 |
| "18 versions is too many, does that cost me space" | `BACKUP_TASK_ABNORMAL` | Misunderstanding of the rolling retention policy; versions are not customer-deletable | `explain --topic retention`, and never quote numbers from memory | T-F8E7DE94 |

## Wording to avoid in a reply

- Do not paraphrase a denial as an HTTP status word. This API set returns
  `NoPermission` or `ImplicitDeny` for a denied action; quote whichever came
  back, verbatim.
- Do not say a backup is "corrupt" because a restore skipped files. Skipped is a
  lock, or an absence, and both are readable.
- Do not confirm a free-quota size, a retention day count or a snapshot unit
  price from memory. Two source cases for this tier disagree with each other on
  the quota, so `explain --topic retention` and its linked official pages are
  the only acceptable source.
- Do not promise that deleting a backup policy removes an alarm record. History
  is not a policy.

## Conflicts carried forward from the cases, unresolved on purpose

The following pairs were reported differently by different cases. Neither is
stated as a fact anywhere in this skill; both are routed to the official pages
listed in `billing-map.md`.

1. Free quota and default retention of the File Backup Essential Edition: one
   case stated a day-count-plus-size pair, another stated a remaining gigabyte
   figure and a block-storage-total billing basis. The official benefit and
   billing-basis pages govern.
2. Snapshot unit price: a case quoted a per-GB-per-month figure verbally. The
   official snapshot billing page governs.
