# Archive Restore Guide

Restore (unfreeze) behavior of Archive / ColdArchive / DeepColdArchive
objects, error routing, fee composition, and storage tiering advice.
Sources: help.aliyun.com "Restore objects in the frozen state" and
"OSS storage classes" (original Chinese doc titles translated;
fetched 2026-08-27), plus measured ticket root causes.

## 1. Frozen-state semantics

- Archive / ColdArchive / DeepColdArchive objects are FROZEN by
  default: GET on an un-restored object returns **InvalidObjectState**
  (StatusCode=403, ErrorCode=InvalidObjectState, ErrorMessage="The
  operation is not valid for the object's state")
  (source: help.aliyun.com `/zh/oss/the-the-operation-is-not-valid-for-
  the-object-s-state-error-message-is-returned-when-you-access-a-restored-
  archive-object`).
- Standard / IA objects are read in real time - no restore step
  (IA bills a retrieval fee but never blocks reads).
- Archive buckets may enable **Archive Direct Read** as a
  bucket-level switch - reads then work without manual restore but are
  billed separately. ColdArchive / DeepColdArchive have NO direct-
  read option; restore is mandatory.
- **Archive Direct Read details** (source: help.aliyun.com "Archive
  direct reading"): reading an un-restored Archive object bills the
  `RetrievalDataArchiveDirect` capacity fee, sized by the requested
  Range - an early connection abort does NOT shrink the billed
  range; image processing bills by the ORIGINAL image size. Reading
  already-restored objects bills no direct-read fee. Direct reads
  cover GetObject/CopyObject/UploadPartCopy/ProcessImage and are
  logged in the `archive_direct_read_size` access-log field. Pitfall:
  with direct read enabled, a static-website default/error page that
  points to an un-restored Archive object fails with 403.

## 2. Restore tiers & typical duration

| Class | Tier | Completion time (typical, actual may vary) |
|---|---|---|
| Archive | (single mode) | about 1 minute |
| ColdArchive | Expedited | about 1 hour |
| ColdArchive | Standard (default) | about 2-5 hours |
| ColdArchive | Bulk | about 5-12 hours |
| DeepColdArchive | Expedited | about 12 hours |
| DeepColdArchive | Standard | about 48 hours |

> **Duration attribution (dual official sources, do NOT absolutize):**
> - Storage-class overview (`user-guide/overview-53.md`) states for
>   ColdArchive & DeepColdArchive: "restore duration is determined by
>   **data size** and the chosen **restore tier**" (translated from the
>   Chinese original).
> - Restore-objects guide (`user-guide/restore-objects-for-access.md`)
>   gives the per-tier typical table above and adds "actual restore time
>   may vary" (translated from the Chinese original).
>
> Guidance: present the tier-based typical range from the table, note that
> large objects may take longer, and always add "actual completion time may
> vary" - never promise a fixed duration and never assert file size is
> irrelevant.

**Restore quotas** (per account per region, official reference
values): ColdArchive ~500 objects/second and 100-120 TB/day across
all tiers; DeepColdArchive ~100 objects/second and 10-15 TB/day.
Beyond the quota, restore requests are still accepted but QUEUE, and
completion may exceed the tier's nominal duration - relevant for
batch restores of huge directories.

## 3. Restore states & re-request behavior

1. **Frozen** -> 2. **Restoring** after the first RestoreObject (API
   returns 202 Accepted). A same-tier repeat returns **409
   RestoreAlreadyInProgress**; only a HIGHER tier request can speed up
   the running restore. 3. **Restored**: a temporary readable replica
   exists; another restore request now returns 200 and EXTENDS the
   replica validity. 4. **Replica expired**: the replica is deleted;
   re-reading requires a fresh restore (and fresh retrieval fee).

Restoring does NOT change the object's storage class (DeepColdArchive
objects stay DeepColdArchive after restore - batch restore-status
checking is console-limited; judge by the restore request + validity
window instead).

## 4. Replica validity window (how long the restored copy stays readable)

| Class | Valid days range |
|---|---|
| Archive | 1-7 days |
| ColdArchive | 1-365 days |
| DeepColdArchive | 1-365 days |

Plan the window: one-shot read -> 1 day; a period of frequent reads ->
longer window (avoids repeated retrieval fees).

## 5. Fee composition (source: help.aliyun.com "Restore objects")

- **Data-retrieval capacity fee** (all three classes): billed once by
  the restored GB - the main restore cost. There is no separate "free
  unfreeze step" (ticket misconception).
- **Restore request fee** (all three classes): every RestoreObject
  request bills per count - Archive counts as a Put-type request;
  ColdArchive/DeepColdArchive count as retrieval requests.
- **Temporary storage fee** (ColdArchive/DeepColdArchive only): the
  temporary replica occupies space and bills per day within its
  validity window; storage fees keep billing by the object's own
  class during and after restore.
- Reading WITHIN the replica validity window does not re-bill
  retrieval.
- Retrieval fees cannot be covered by most resource packages - quote
  them separately when advising (billing detail belongs to
  alibabacloud-oss-billing-diagnosis).
- **Minimum storage duration** still applies on early delete /
  re-conversion: IA 30 days, Archive 60 days, ColdArchive 180 days,
  DeepColdArchive 180 days ("insufficient-storage-duration fee"); minimum metering
  unit 64 KB for all archive classes.

## 6. Error routing

| Error | Meaning | Guidance |
|---|---|---|
| `InvalidObjectState` | Object is frozen or still restoring | Restore first (choose tier); re-read after completion |
| `RestoreAlreadyInProgress` | A restore is running; same-tier repeat -> 409 | Wait for the tier window, or submit a HIGHER tier to speed up |
| Restore completed but still failing | Replica expired | Re-restore with a longer validity window |
| `NoSuchKey` | Object absent | Not a restore problem; check lifecycle deletion / the deletion-recovery skill |

## 7. How to restore (USER-EXECUTED - this skill never runs it)

Console: object details -> Unfreeze; ossbrowser: object right-click ->
Restore (supports Archive/ColdArchive/DeepColdArchive); ossutil:
`ossutil restore oss://bucket/key --tier Standard --days N`;
SDK: `bucket.restore_object(key, input=RestoreConfiguration(days=N, tier=...))`.
Batch restore of a directory requires ossutil/SDK/API (the console and
ossbrowser restore single objects only).

## 8. Storage tiering strategy advice

- Ladder: Standard -> IA -> Archive -> ColdArchive -> DeepColdArchive;
  lifecycle conversion is ONE-WAY downward; converting back is manual.
- Threshold heuristics (official access-frequency definitions): IA
  for <1 read/month per file; Archive for <1 read per 90 days;
  ColdArchive / DeepColdArchive for <1 read per year.
- Cost traps to state up front: 64 KB minimum metering (many small
  files balloon), retrieval fee on every cold read, minimum storage
  duration fee on early delete, and the conversion API-request burst
  when a lifecycle rule sweeps a huge object count at once (measured
  ticket: tens of millions of transition requests billed ~thousands of
  CNY).
- Access-time based transition (cold tiering by last access) requires
  access tracking to be enabled (officially a billable item named "Object
  Monitoring Management Fee", which OSS currently does NOT charge - quote
  the item name and "currently not charged" status together; re-verify
  before advising on cost; billing detail belongs to
  `alibabacloud-oss-billing-diagnosis`). Converting Standard/IA ->
  Archive/ColdArchive/DeepColdArchive by access-time rules requires a
  support-ticket whitelist (all three cold targets need it, not just
  ColdArchive/DeepColdArchive) - when unavailable, advise
  last-modified-time rules instead.
  (source: help.aliyun.com `/zh/oss/user-guide/lifecycle-rules-based-on-
  the-last-access-time`; aligned with `lifecycle-playbook.md` sec.1.)
- Bucket default storage class cannot be changed after creation; only
  object-level conversion exists.
