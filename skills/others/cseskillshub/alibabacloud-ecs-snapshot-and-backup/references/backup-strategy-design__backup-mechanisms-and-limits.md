# Backup Mechanisms, Coverage and Limits

Knowledge module for capability "mechanism fit / coverage design". Every
rule here carries its official document, under the date discipline below:

> **Verification date discipline:** the document set is distilled from the
> evidence batch through **2026-08-30** and was NOT formally re-verified in
> this build. Re-check each URL before quoting it to a customer.

## 1. First fork: is the source really an ECS instance?

ECS backup mechanisms (snapshot, automatic snapshot policy, custom image,
ECS file backup) exist only for ECS instances. Products such as Web Hosting
classes have no ECS image/snapshot capability, so an ECS plan silently
fails when applied there. Evidence pattern: a customer following an ECS
image guide "cannot find the image feature" because the product is not ECS.

- Decision: identify the product first. Non-ECS → state the boundary and
  route to that product line; only advise application-level separate backups
  (website files + database dumps) as generic practice.

## 2. Mechanism comparison

| Mechanism | Covers | Consistency | Local disk? | Cost class | Key docs |
|---|---|---|---|---|---|
| Manual snapshot | one disk's block data at one moment | crash-consistent | No (cloud disks only) | snapshot storage fee | [create-a-snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot), [snapshot-overview](https://help.aliyun.com/zh/ecs/user-guide/snapshot-overview) |
| Automatic snapshot policy | every disk it is APPLIED to, on schedule | crash-consistent | No | snapshot storage fee (see [billing-models.md](billing-models.md)) | [automatic-snapshot-policy](https://help.aliyun.com/zh/ecs/user-guide/automatic-snapshot-policy) |
| ECS file backup (basic edition, free) | selected file paths | file level | n/a | free with hard limits below | [file-backup FAQ](https://help.aliyun.com/document_detail/2979167.html) |
| Cloud Backup file/database backup | files AND database engines (MySQL / SQL Server ...) | application level for DB | n/a (self-built/on-prem DBs too) | paid per Cloud Backup billing | [getting started](https://help.aliyun.com/zh/cloud-backup/getting-started/get-started-with-on-premises-database-backup), [billing](https://help.aliyun.com/zh/cloud-backup/product-overview/billing-methods-and-billable-items) |
| Custom image → export to OSS → download | system + data disks as an offline copy | image of disks | No | image + OSS storage + egress | search "export a custom image" on the official help site (URL not in the evidence batch; verify before quoting) |
| Snapshot cross-region copy | an off-site duplicate of chosen snapshots | same as source snapshot | No | copy traffic + destination storage | [snapshots billing](https://help.aliyun.com/zh/ecs/snapshots-1) |

## 3. File backup basic edition — hard limits (top mis-selection source)

1. **Database software installation directories are excluded** (e.g. the
   MSSQL data directory). The evidence pattern: ransomware encrypts a SQL
   Server whose data files were never in any restore point because the free
   file backup could not cover that directory.
2. **Retention is fixed at 30 days** and cannot be customized (no "keep 6
   days", no "keep 90 days").
3. **No automatic overwrite**: when backup capacity is exhausted the jobs
   FAIL — the oldest data is not replaced. Capacity planning is the
   customer's job.
4. It is a free service with these limitations by design; broader needs →
   paid Cloud Backup.

## 4. Snapshots and disks

- An automatic snapshot policy protects **only** the disks it is applied to;
  the create/apply distinction is the #1 "policy does nothing" root cause
  (see [policy-design.md](policy-design.md)).
- Single-system-disk instance + policy applied to it ≈ whole-system
  protection **for the state on that disk**; data disks need their own
  binding.
- Local disks cannot be snapshotted. Design for local-disk instances
  (heuristic: instance types starting `ecs.i<N>`/`ecs.d<N>`, confirm on the
  instance-type spec page): copy the needed data to cloud disks, or use
  file/database-level backup off the box. Docs: [backup local disk files](https://help.aliyun.com/zh/ecs/user-guide/backup-local-disk-data.md),
  [local-disk best practices](https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-local-disks.md).
- Releasing an instance destroys its data: with no retained snapshot/image
  there is **no provider-side recovery path** — state this before any
  release/conversion advice.

## 5. What each mechanism cannot see or cover

Read-only cloud APIs (and therefore this skill) never see: in-guest real
file usage, which directories a backup job actually walked, application
consistency of a database, or the guest-side reason of a failed job. Those
conclusions come from **customer self-checks** (coverage checklist in
[references/misconceptions.md](misconceptions.md) and the design report's
gap probes), never from model memory or guesswork.

## 6. Coverage-gap design pattern (the pre-incident value)

For every object the customer names, walk: object → mechanism → limit list
above → residual gap. Typical forced conclusions:

- "Database on the box" → file backup basic edition is NOT a database
  backup → Cloud Backup database backup (+ snapshot safety net).
- "Whole system, cheap" → single system disk + automatic policy with modest
  retention; no cold-backup type exists in the policy.
- "Must survive region loss" → cross-region copy of snapshots, billed per
  copy (see [billing-models.md](billing-models.md)).
- "Must have an offline copy" → image export to OSS + download, or
  application-level dumps; multi-step, customer-performed.
