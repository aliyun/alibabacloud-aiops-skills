# Retrieval / Minimum-Duration Fee Guide

Fee attribution rules for "high retrieval fee from backup" complaints.
Verified from official billing docs (2026-08):

- Data processing fees (incl. retrieval):
  https://help.aliyun.com/zh/oss/product-overview/data-processing-fees
- Storage fees and minimum storage durations:
  https://help.aliyun.com/zh/oss/product-overview/storage-fees

## Judgment table by storage class

| Class | Retrieval fee | Minimum storage | Key billing facts |
| --- | --- | --- | --- |
| Standard | None | None | Any RetrievalData billing means objects are not Standard (check lifecycle / per-object class) |
| Infrequent Access (IA) | Yes — every read bills RetrievalData | 30 days | Partial reads (HTTP Range / SelectObject) bill the byte range; full reads bill the whole object |
| Archive | Yes — restore bills retrieval by file size | 60 days | Access between restore completion and re-freeze does not bill another restore |
| Cold Archive | Yes — tiered: Standard / High Priority / Bulk | 180 days | High Priority is fastest and most expensive; Bulk slowest and cheapest |
| Deep Cold Archive | Yes — tiered: Standard / High Priority | 180 days | For restore frequency measured in years only |

## Why backup workloads trigger these fees

1. **Restore verification**: backup software that reads objects back after
   writing (verification jobs) bills retrieval on every read for
   non-Standard classes.
2. **Rotation / retention pruning**: overwriting or deleting objects
   before the minimum storage duration bills the remaining days as
   "insufficient-duration capacity" — e.g. an IA backup object deleted
   after 1 day bills ~29 extra days of storage. Rotating backups on IA
   storage are the classic surprise bill (official docs + ticket cluster).
3. **Lifecycle drift**: a lifecycle rule converting Standard backups to
   IA/Archive after N days silently changes the fee profile of the same
   backup job.
4. **Concept confusion**: "restore should be free, only retrieval bills"
   is a misconception — restoring an archive object IS the operation that
   triggers retrieval billing (ticket-verified root cause).
5. **No package coverage**: data retrieval fees are pay-as-you-go only;
   no resource package deducts them (ticket-verified).

## Attribution workflow (mirrors the script)

1. Identify the billing line item: RetrievalData, CAStdRetrievalData,
   CAHighPriorRetrievalData, CABulkRetrievalData, DeepCA*RetrievalData,
   or ArchiveDirect.
2. Identify the storage class of the affected objects/prefix.
3. Apply the judgment table above; if the class is Standard but retrieval
   is billed, find what converted the objects (lifecycle rule or
   per-object storage class set by the backup tool).
4. Recommend per class: Standard for hot restore cycles, larger retention
   windows than the minimum duration, bulk/standard retrieval tiers for
   planned restores, disabling routine restore-verification on cold data.

This skill only attributes the fee and recommends configuration; it never
changes storage classes, lifecycle rules or billing settings.
