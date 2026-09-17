# "Replication Not Starting" Diagnosis Tree

Route a "cross-region replication is not running / no data in the target"
report to a concrete cause. Always run `crr_config_check.py` first and use its
`verdict` / `findings` as evidence; this tree only explains how to interpret
them and what to ask next.

```
Is there a replication rule on the source bucket?
│
├─ verdict = no_replication_configured
│     The rule does not exist. "Not starting" == "never configured".
│     → Guide the user to create a rule in the OSS console
│       (write op, user's own action) and authorize a RAM role.
│     Common confusion: the user set up the rule on the TARGET bucket, or
│       in a different region/account than the source.
│
└─ verdict = replication_configured / replication_starting
      A rule exists. Walk the findings in this order:
      │
      ├─ Historical-data switch DISABLED (is_enable_historical = False)
      │     Only objects written AFTER rule creation replicate. Pre-existing
      │     objects never sync. [Most common cause]
      │     → Advise enabling "replicate historical data" (manual, write op).
      │
      ├─ Prefix scope excludes the objects (prefix_list non-empty)
      │     Objects outside the listed prefixes are never replicated.
      │     → Compare the missing objects' keys against prefix_list.
      │
      ├─ Authorization role missing / NoPermission (403 on replication, or
      │     sync_role empty **while the rule targets SSE-KMS-encrypted objects**
      │     — note: GetBucketReplication returns SyncRole ONLY for SSE-KMS
      │     rules; an empty sync_role on a non-KMS rule is NORMAL, not a defect)
      │     → Attribute via server-log (see replication-rules.md §3):
      │       extra STS RequestId → trust policy; none → RAM policy.
      │
      ├─ ColdArchive / DeepColdArchive objects
      │     These are never replicated regardless of restore state.
      │     → Not fixable by config; change storage class first (manual).
      │
      ├─ Cross-border without transfer acceleration
      │     Mainland ↔ non-mainland pairs require transfer acceleration.
      │     → Enable transfer acceleration on the link (manual, write op).
      │
      ├─ Objects already came from another replication
      │     OSS does not re-replicate replicated objects (no A→B→C cascade).
      │     → Explain the limit; suggest an alternative sync design.
      │
      ├─ status = starting and nothing else wrong
      │     Replication is asynchronous; large datasets take minutes to
      │     hours. → Read GetBucketReplicationProgress (report.
      │     replication_progress): historical_object_progress = backlog %
      │     copied, new_object_progress = watermark. 0% with status 'doing'
      │     usually means the backlog is still queuing OR historical
      │     replication is disabled -- not a broken rule.
      │
      └─ status = doing, no error, but "replication is slow" / lagging
            Capacity limit, not a config defect. → Compare the load against
            the RTC bandwidth/QPS ceilings (replication-rules.md §5.5):
            mainland region-pair 10 Gbps / 10,000 QPS, single mainland
            region 20 Gbps / 20,000 QPS, non-mainland pair 2 Gbps / 5,000
            QPS, single non-mainland region 4 Gbps / 10,000 QPS; the
            SEQUENTIAL-write QPS cap is 2,000 for every scope. Exceeding
            them increases lag -- avoid sequential prefix file names for
            large uploads; higher limits need a ticket.
```

## Post-replication data verification ("is the target complete?")

When the customer asks whether the target bucket actually received all the
data (tickets 0007KS78FF / 000F4RG588), this skill gives the verification
PATH only, never a promise of integrity (full method in
`replication-rules.md` §5.9):

1. Read `GetBucketReplicationProgress` first — it separates the historical
   backlog % from the new-object watermark, which the rule `status` alone
   cannot.
2. For a count/spot-check, run `crr_config_check.py --bucket <source>
   --verify-target` (read-only): it lists source vs target object counts
   (`ListObjectsV2`, `oss:ListObjects`) under the rule prefix and samples
   ETag/Size. A cross-account target that cannot be listed is a LIMIT
   (`target_unreachable`), not an error.
3. For a large bucket the bounded scan reports `truncated=true`; use the
   OSS Inventory on both sides and diff offline instead of trusting
   the partial count.

## Verification ordering

1. Run `crr_config_check.py --bucket <source>`; record `STATUS` + `verdict`.
2. If `DEGRADED`, relay the errors — do not guess the rule.
3. If `no_replication_configured`, confirm with the user which bucket/region
   they configured the rule on (frequently the wrong bucket).
4. If a rule exists, report findings top-to-bottom from the tree above and
   state each as manual guidance (this skill never mutates).

## Region decommission / migration guidance (online migration vs CRR)

Ticket-proven knowledge (region-shutdown migration tickets 00069RRZEY /
00094R5CYX / 000EAR42K7; selection question ticket 000B9R1U8C). The
machine-readable copy lives in `crr_config_check.py`
(`REGION_MIGRATION_GUIDANCE`, emitted when no rule is configured).

- Decommission pattern: when a region is being shut down and data must
  move to another region, enable SAME-ACCOUNT cross-region replication
  from the source-region bucket to a destination-region bucket WITH
  historical-data replication enabled, then switch reads/writes after the
  backlog catches up. If the region is already restricted, opening the
  replication link may require prior approval via a support ticket
  (temporary enablement for migration).
- Selection between the Data Online Migration service and CRR:
  - Continuous / near-real-time sync until cutover, or disaster recovery
    -> cross-region replication (rule-based, incremental).
  - One-time bulk migration, backfill of an existing dataset, or
    source-side filtering -> Data Online Migration service (migration
    task with progress tracking; official doc:
    https://help.aliyun.com/zh/data-online-migration/user-guide/migrate-data-between-oss-buckets).
  - The two combine: migrate the backlog with online migration, then keep
    CRR running for ongoing deltas.

## Deferral boundaries

- Billing / replication-traffic cost questions → billing skill.
- "I deleted the source/target and need the data back" → deletion-recovery
  skill.
- Endpoint / internal-network access errors around the buckets → endpoint
  skill.
- Designing the cross-account RAM role/policy itself → cross-account-auth
  skill.
