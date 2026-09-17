# M2: Deletion Residue Checklist

Residue attribution for "bucket cannot be deleted (BucketNotEmpty)" and
"storage capacity / cost did not drop after deletion". All checks here are
read-only; every cleanup action is manual guidance executed by the user.

## 1. The three residue classes

Deleting a bucket fails while ANY of these remains (official precondition,
source: help.aliyun.com `/zh/oss/user-guide/delete-buckets`):

| # | Class | Why it is invisible | Read-only check | User-executed cleanup guidance |
|---|---|---|---|---|
| 1 | Leftover objects | Obvious in the file list, but prefixes/versions may be missed | `GetBucketInfo` (bucket still exists) + console file list | Delete the remaining objects (console / ossutil recursive delete); with huge object counts a lifecycle "expire immediately" rule is the economical way |
| 2 | Multipart fragments | Unfinished/aborted multipart uploads keep their uploaded PARTS stored and billed; they do not appear in the plain file list | `ListMultipartUploads` (this script counts them; `truncated=true` means even more exist) | Abort them: console file list -> fragment management -> delete all; or ossutil `-m -r -f` style fragment removal; or a lifecycle `AbortMultipartUpload` rule to prevent recurrence |
| 3 | Historical versions & delete markers | In a versioning-enabled (or once-enabled) bucket, deleted objects survive as historical versions / delete markers and keep consuming storage | `GetBucketVersioning` status Enabled/Suspended + console historical-version view (`GetBucketVersions`) | Permanently delete the unwanted historical versions and delete markers (console historical-version view, or versioned delete with explicit version id); a lifecycle `NoncurrentVersionExpiration` rule automates it — irreversible, verify before acting |

Additional non-storage items that also block bucket deletion (out of this
skill's read-only checks, relay as guidance only): access points, transfer
accelerator instances, and live/RTMP stream addresses — the console
delete-bucket wizard scans and lists all of them. If OSS-HDFS service is
enabled, HDFS files may also need separate cleanup (refer to OSS-HDFS
documentation).

**Data-safety risk (NOT a deletion blocker):** if cross-region or
same-region replication is enabled, deleting objects in the source bucket
may synchronously remove data in the target bucket. Before any bulk
deletion, check the replication rule's `Action` field — if it includes
DELETE, the deletion will propagate. This is a data-safety concern, not a
bucket-deletion blocker (source: help.aliyun.com
`/zh/oss/user-guide/delete-buckets`).

## 2. Capacity / cost not dropping after deletion — attribution order

When the user deleted data but storage usage or cost did not drop:

1. **Multipart fragments first** — run the script `--scope residue`;
   `ListMultipartUploads` count > 0 means uploaded parts are still stored
   and billed.
2. **Historical versions second** — if versioning is/was active, deleting
   the current version only inserts a delete marker; every historical
   version keeps billing storage. Lifecycle `Expiration` on a versioned
   bucket behaves the same way (current version -> historical version, not
   erased).
3. **Lifecycle semantics check** — if the "deletion" was performed by a
   lifecycle rule, confirm whether the rule uses `Expiration` (versions
   retained, still billed) or true removal.
4. **Billing attribution hand-off** — bill line-item detail (which billing
   item, resource pack deduction) belongs to the billing skill
   (`alibabacloud-oss-billing-diagnosis`); this skill only attributes the
   residual storage itself. Note that storage billing reflects metering
   snapshots, so a drop can lag the cleanup by up to one billing cycle.

## 3. Prevention baseline (always include in the answer)

The official accidental-data-loss prevention guide lists four mechanisms
(source: help.aliyun.com
`/zh/oss/user-guide/reduce-the-risks-of-data-loss-caused-by-accidental-operations`):

- Enable versioning for accidental-deletion protection (historical versions
  are billed, pair with a noncurrent-version lifecycle rule).
- Set a WORM retention policy (BucketWorm) on compliance-critical buckets:
  until the retention period expires, NO user including the bucket owner can
  modify or delete the objects.
- Enable cross-region replication with the add/update-only replication
  policy, so an accidental deletion in the source bucket leaves the data
  recoverable from the target bucket.
- Configure scheduled backup to Cloud Backup (HBR): incremental backups run
  on the chosen schedule and deleted objects can be restored via a Cloud
  Backup restore task. Official limits: Cloud Backup supports only Standard
  and Infrequent Access buckets/objects (NOT Archive / ColdArchive /
  DeepColdArchive), and object ACLs are NOT backed up or restored
  (source: help.aliyun.com `/zh/oss/user-guide/configure-scheduled-backup`).

Additional operational hygiene:

- Add a lifecycle `AbortMultipartUpload` rule so interrupted uploads never
  accumulate fragments again.
- Enable real-time log delivery (access logs) to trace future deletions.
- Least-privilege RAM: do not hand `oss:DeleteObject`/`oss:DeleteBucket`
  to identities that only need read/write.

## 4. Official sources

- Delete a bucket / BucketNotEmpty preconditions and cleanup wizard:
  help.aliyun.com `/zh/oss/user-guide/delete-buckets`
- Lifecycle introduction (Expiration / NoncurrentVersionExpiration /
  AbortMultipartUpload semantics):
  help.aliyun.com `/zh/oss/user-guide/lifecycle-rules-based-on-the-last-modified-time`
  (overview: `/zh/oss/user-guide/lifecycle-rules-1`)
- Accidental-data-loss prevention (versioning / WORM / CRR / scheduled
  backup):
  help.aliyun.com `/zh/oss/user-guide/reduce-the-risks-of-data-loss-caused-by-accidental-operations`
- Scheduled backup to Cloud Backup (limits: Standard/IA only, ACLs not
  restored):
  help.aliyun.com `/zh/oss/user-guide/configure-scheduled-backup`
