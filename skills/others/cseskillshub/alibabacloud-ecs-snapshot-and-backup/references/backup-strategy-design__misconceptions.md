# Misconceptions Index (Customer-Perception vs Mechanism Reality)

Knowledge module for capability "misconception clearing". Each row: what the
customer believes (usually because the console or a notification looks
self-explanatory), what the mechanism actually does, and how to answer.
Sources follow the date discipline in
[references/backup-mechanisms-and-limits.md](backup-mechanisms-and-limits.md).

## 1. "Disk uses 5.8 GB, snapshot shows 38.8 GB -- snapshots must be full copies every time"

- Reality: snapshots record disk BLOCKS. The first snapshot is full of the
  used blocks; later ones keep only changed blocks; deleted files still
  occupy blocks until every referencing snapshot is deleted. The console
  displays, per snapshot, the FULL restore amount, not the billed
  increment. So both displayed numbers are correct at different meanings.
- Answer path: cite [how do snapshots work](https://help.aliyun.com/zh/ecs/user-guide/how-do-snapshots-work)
  and the billing model in [billing-models.md](billing-models.md).

## 2. "I can switch the policy's snapshot type to 'cold backup' to save money"

- Reality: the automatic snapshot policy has no cold-backup type selection.
  An archived snapshot category exists but cannot be copied across regions,
  so it cannot substitute in an off-site design. Savings levers are fewer
  snapshots, shorter retention, fewer copies.
- Answer path: [automatic snapshot policy](https://help.aliyun.com/zh/ecs/user-guide/automatic-snapshot-policy);
  the script topic `cold-backup-type`.

## 3. "File backup fills up at day 6, then it overwrites the oldest data"

- Reality: the free file-backup basic edition never overwrites; jobs simply
  FAIL once capacity is exhausted, and its retention is fixed at 30 days
  (not customizable to 6). If the desired shape is "keep exactly N days
  with auto-delete", the right mechanism is an automatic snapshot policy
  with N-day retention.
- Answer path: [file-backup FAQ](https://help.aliyun.com/document_detail/2979167.html);
  topic `file-backup-overwrite`.

## 4. "The free file backup is enabled, so the database is backed up"

- Reality: database software installation directories are outside the basic
  edition's coverage. The evidence batch's ransomware ticket turned exactly
  on this: every "file backup" restore point lacked the MSSQL directory.
  Databases need Cloud Backup database backup (paid) and/or snapshots as
  the block-level layer; snapshots alone are crash-consistent.
- Answer path: topic `free-backup-covers-database`; mechanism table in
  [backup-mechanisms-and-limits.md](backup-mechanisms-and-limits.md).

## 5. "My guest reports 62 GB but the download is 110 GB+ -- the backup is broken"

- Reality: download inflation is usually instance-local: (a) unrotated
  service/container logs ballooning; (b) transfer clients FOLLOWING
  SYMLINKS and pulling the same files repeatedly (disable symlink-following
  in the transfer tool's settings); (c) mounted object storage counted as a
  local folder (fetch from the storage console instead).
- Answer path: topic `download-size-inflation`. All three are CUSTOMER
  self-checks: this skill runs nothing inside the instance.

## 6. "Policy created = data safe"

- Reality: protection exists only after the policy is APPLIED to disks AND
  a real automatic snapshot appeared; bindings can silently break after
  disk rebuild/re-init/migration events.
- Answer path: the ladder in [policy-design.md](policy-design.md); topic
  `policy-exists-vs-data-safe`.

## 7. "I pay for the cloud, so the provider keeps my data backed up"

- Reality: shared-responsibility model -- the provider runs the
  infrastructure; in-guest data, application security, and backup
  configuration are the customer's responsibility. With no customer backup
  there is no provider-side recovery of ransomware-encrypted or
  accidentally deleted data.
- Answer path: topic `responsibility-boundary`; keep it factual and brief,
  then pivot to the forward-looking design.

## 8. "Snapshot fee is wrong / should be zero" style billing disputes

- Reality: this skill explains the model; actual amounts, discounts, refunds
  and package purchases are account/commercial processes. Do not attempt
  them; state the boundary and route (see [routing.md](routing.md)).
- Always close a billing answer with the no-commitment statement from
  [billing-models.md](billing-models.md) section 1.

## 9. "The instance console shows my snapshots, so I could have changed them here"

- Reality: visibility is not authorization. This skill's read-only queries
  show instance facts and nothing else; every operation (policy binding,
  copy, cleanup, extension) is performed by the customer in their own
  console session. Never imply the skill could perform an operation it can
  only describe.
