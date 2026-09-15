# M3: Archive Direct-Read Judgment (Mount Read 403)

Knowledge base for "reading archive objects through a mount returns 403"
and the archive-direct-read feature. The entry script computes the
storage-class-based verdict automatically (`archive_verdict` in the JSON
report); this module explains the rules and the manual follow-ups.

## Sources (official documentation, verified)

| Topic | Official doc |
|---|---|
| Archive direct read (feature, limits, cost, APIs) | https://help.aliyun.com/zh/oss/user-guide/archive-direct-reading |
| Cannot download an archive object (restore vs direct read) | https://help.aliyun.com/zh/oss/unable-to-download-an-archive-object-from-oss |
| ossfs FAQ: touch/read of an archive object returns 403; mv fails on archive objects | https://help.aliyun.com/zh/oss/developer-reference/ossfs-faq |

## Core rules (all from the official docs above)

1. **Default behavior**: Archive storage class objects are NOT readable
   until restored (thawed). GetObject on an unrestored archive object
   fails (403 InvalidObjectState family); through an ossfs/CSI mount this
   surfaces as a 403 / IO error on read, and `touch`/`mv` on such files
   also fails (ossfs FAQ records both).
2. **Archive direct read**: a bucket-level switch that lets clients read
   Archive objects directly without restore (millisecond-level retrieval,
   higher retrieval cost). Covering operations: GetObject, CopyObject,
   UploadPartCopy, ProcessImage, PostProcessTask.
3. **Storage class coverage**: archive direct read applies ONLY to the
   Archive class. ColdArchive and DeepColdArchive objects can never be
   read directly and must always be restored first - for those buckets the
   judgment is "archive direct read not applicable; restore required".
4. **Cost**: direct reads of unrestored archive objects generate
   `RetrievalDataArchiveDirect` retrieval cost; already-restored archive
   objects read directly do not generate this cost item.
5. **Switch management** (manual guidance only - this skill never changes
   it): OSS console -> Bucket -> Data Management -> Archive Direct Read; or
   ossutil `put-bucket-archive-direct-read` /
   `get-bucket-archive-direct-read`; APIs PutBucketArchiveDirectRead /
   GetBucketArchiveDirectRead. A RAM user needs
   `oss:PutBucketArchiveDirectRead` / `oss:GetBucketArchiveDirectRead`
   for the switch operations (the user's own action, not this skill's).

## Judgment table used by the entry script

| GetBucketInfo storage_class | archive_verdict.status | Meaning |
|---|---|---|
| Standard / IA / other non-archive | `no_archive_issue` | No archive direct-read problem for this bucket; truthfully report "no archive direct-read issue" |
| Archive | `archive_check_required` | Archive-read 403 is possible; the direct-read switch state is NOT visible via GetBucketInfo - user must check console / GetBucketArchiveDirectRead, then either enable it or restore objects |
| ColdArchive / DeepColdArchive | `archive_direct_read_not_applicable` | Direct read not available for these classes; restore before any read |
| (query degraded) | `unknown` | Storage class not obtained; risk cannot be judged - say so honestly |

## Attribution flow for "mount read 403"

1. Run the entry script: if `archive_verdict.at_risk` is false, archive is
   RULED OUT - continue with the RAM/endpoint attribution in M1/M2.
2. If the bucket is Archive-class: confirm with the user whether archive
   direct read is enabled (console page or `get-bucket-archive-direct-read`
   - they execute).
   - Disabled -> two manual options: enable archive direct read (cost
     trade-off explained above) or restore the objects first (restore
     procedure details belong to alibabacloud-oss-lifecycle-runtime-diagnosis).
   - Enabled -> the 403 is NOT the archive switch: fall back to RAM
     permission / endpoint / object-level attribution (M1/M2).
3. ColdArchive/DeepColdArchive -> restore is the only path; advise that
   mounting such buckets for on-demand reads is not a supported pattern.

## Out of scope for this module

- Restore job parameters, lifecycle transitions, retention -> skill
  alibabacloud-oss-lifecycle-runtime-diagnosis.
- Retrieval-cost billing disputes -> skill
  alibabacloud-oss-billing-diagnosis.
