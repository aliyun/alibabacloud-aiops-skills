# M1: Recovery Decision Tree

Recoverability assessment for accidentally deleted OSS objects. All checks
here are read-only; every restore action is manual guidance executed by the
user.

## 1. Deletion-path taxonomy (what actually happened)

| Deletion path | Who/what issues it | Effect without versioning | Effect with versioning enabled |
|---|---|---|---|
| `DeleteObject` | A single delete request (console, SDK, ossutil) | Object permanently removed | A delete marker is inserted as the current version; all historical versions retained and recoverable |
| `DeleteObjects` (batch) | Batch delete API / console bulk delete | All listed objects permanently removed | One delete marker per object; historical versions retained |
| `ExpireObject` (lifecycle) | Lifecycle rule expiration | Object permanently removed when the rule fires | `Expiration` turns the current version into a historical version (recoverable); `NoncurrentVersionExpiration` permanently deletes noncurrent versions (irreversible) |

Customer-side means to attribute a deletion (this skill never queries
server-side logs):

- **Versioning history query**: in a versioning-enabled bucket,
  `GetBucketVersions` / `ListObjectVersions` (console: file list -> show
  historical versions) lists every version including delete markers with
  timestamps — the timestamp of the newest delete marker is the deletion
  time of that object.
- **Recycle bin capability statement**: OSS provides **no recycle bin**;
  versioning is the only built-in mechanism that keeps deleted data
  recoverable (source: help.aliyun.com OSS versioning overview,
  `/zh/oss/user-guide/overview-78/`).
- **Access log delivery guidance**: if real-time log delivery (access logs)
  was enabled before the deletion, the delivered logs can attribute when
  and by which request the object was deleted. They do NOT restore data.
  If not enabled, suggest enabling it for future traceability.
- **Event-notification forensics caveat**: in a versioning-enabled bucket,
  the two delete APIs behave differently regarding event notifications:
  - `DeleteObject` without a version id inserts a delete marker and **DOES
    trigger** an ObjectRemoved:DeleteObject event notification.
  - `DeleteObjects` (batch) without a version id inserts delete markers but
    **does NOT trigger** event notifications; the version id must be
    explicitly specified in the batch request to fire events.
  (source: help.aliyun.com
  `/zh/oss/user-guide/why-does-deleting-a-file-not-trigger-an-event-notification`)
  So the absence of deletion events does not prove no deletion happened —
  three possible causes: (1) batch DeleteObjects was used (official
  exception), (2) the event notification rule does not cover that event
  type, (3) notification delivery failed. Check the version list for delete
  markers as primary evidence. For event-notification configuration issues,
  refer to `alibabacloud-oss-event-notification-diagnosis`.

## 2. Decision tree (implemented in `oss_deletion_recovery_diagnosis.py`)

```
Is the bucket found? (GetBucketInfo / ListBuckets fallback)
├── NO  -> if the bucket itself was deleted, object data is unrecoverable
│          without a backup/replication copy; verify name/owning account.
└── YES -> query versioning status (GetBucketVersioning)
    ├── Enabled        -> RECOVERABLE (yes)
    │     delete only inserted a delete marker.
    │     Restore path (user-executed):
    │       a. list versions, find the version just before the deletion;
    │       b. restore that historical version to current
    │          (console "restore" action, or `ossutil revert
    │          oss://<bucket>/<object> <versionId>`), or delete the
    │          topmost delete marker so the previous version resurfaces.
    ├── Suspended      -> PARTIALLY recoverable
    │     A delete WITHOUT version id creates a delete marker
    │     (versionId=null); historical versions are NOT affected and remain
    │     recoverable via the same restore path as Enabled (list versions,
    │     remove the null delete marker or `ossutil revert`). Only a delete
    │     WITH an explicit version id permanently removes that version.
    │     (source: help.aliyun.com `/zh/oss/user-guide/manage-objects-in-a-
    │     versioning-suspended-bucket`)
    ├── Not configured -> NOT recoverable from OSS
    │     no recycle bin exists; check external copies:
    │       - cross-region replication target bucket
    │       - local/client backups or a backup service copy
    │     then advise prevention (versioning, lifecycle care, backups).
    └── Query degraded -> UNKNOWN — record the error, never conclude.
```

## 3. Recovery boundaries (must be stated explicitly)

- **Deleting WITH a version id is irreversible**: permanently removes that
  specific version even in an enabled bucket.
- **Lifecycle `NoncurrentVersionExpiration` is irreversible**: versions it
  removes cannot be restored.
- **Overdue-payment release is unrecoverable**: if the account was released
  after overdue service suspension without repayment within the official
  retention window, the data was cleaned and cannot be recovered (source:
  help.aliyun.com OSS overdue-payments, `/zh/oss/overdue-payments`; the
  published window is 15 days after service suspension — verify the page
  for the current policy). Do not open a restore investigation in this
  case; state the policy honestly.
- **Released bucket names are locked (cooldown)**: two distinct paths:
  - **Active DeleteBucket**: official documentation states the name requires
    **4-8 hours** cooldown before it can be reused; official recommendation:
    "if you need to preserve the name, only empty the files — do NOT delete
    the Bucket" (source: help.aliyun.com `/zh/oss/user-guide/delete-buckets`).
  - **Overdue-payment release**: the name is also locked but official
    documentation does not specify the cooldown duration for this path.
    Ticket-verified workaround (ticket 000EAR1NT7): create a NEW bucket
    under a different name and bind the original custom domain (CNAME) to
    it, so application endpoints keep working without code changes.
  In both cases the released data itself is unrecoverable.
- **This skill never executes recovery**: restoring a version, removing a
  delete marker, aborting fragments, or any write is performed by the user
  following the guidance; verify the version id before any restore because
  a wrong permanent delete is irreversible.

## 4. Official sources

- **Versioning overview & restore semantics**:
  help.aliyun.com `/zh/oss/user-guide/overview-78/`
- Preventing accidental data loss (four official mechanisms: versioning,
  WORM retention policy, cross-region replication, scheduled Cloud Backup):
  help.aliyun.com `/zh/oss/user-guide/reduce-the-risks-of-data-loss-caused-by-accidental-operations`
- Managing (download/delete/restore) objects in versioning-enabled buckets:
  help.aliyun.com `/zh/oss/user-guide/manage-objects-in-a-versioning-enabled-bucket`
- Delete marker semantics:
  help.aliyun.com `/zh/oss/user-guide/delete-marker`
- Overdue-payment data retention policy:
  help.aliyun.com `/zh/oss/overdue-payments`
