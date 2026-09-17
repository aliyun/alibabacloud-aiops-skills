# CRR Rule Field Semantics & Official Limits

Cross-region replication (CRR) copies objects from a source bucket in one
region to a target bucket in another region automatically and asynchronously.
This module explains the replication-rule fields this skill reads
(`GetBucketReplication`) and the official limits that cause "replication not
working" configurations.

Sources:
- OSS CRR overview / usage limits / cost & storage-class limits: `https://help.aliyun.com/zh/oss/user-guide/cross-region-replication-overview/`
- Same-account CRR role configuration: `https://help.aliyun.com/zh/oss/user-guide/cross-region-replication-with-the-same-account`
- `GetBucketReplication` field schema (PrefixSet / Action / Status / UserTagging): `https://help.aliyun.com/zh/oss/developer-reference/getbucketreplication`
- RTC bandwidth & QPS ceilings: `https://help.aliyun.com/zh/oss/user-guide/rtc`
- Field semantics measured against `oss2` 2.19.1 `models.ReplicationRule`.

## 1. Replication-rule fields (GetBucketReplication)

`GetBucketReplication` returns a rule list (at most one rule today). Each rule
carries the fields below; this skill reports them verbatim.

| Field | Meaning | Check performed |
|---|---|---|
| `rule_id` | Server-assigned rule identifier | echoed |
| `target_bucket_name` / `target_bucket_location` | Destination bucket and its region | cross-border detection |
| `target_transfer_type` | Data link; `oss_acc` = transfer acceleration | transfer-accel dependency |
| `prefix_list` | Object prefixes in scope (empty = whole bucket) | replication scope |
| `action_list` | Sync actions: `ALL` = PUT+ABORT+DELETE, `PUT` = writes only | delete-marker sync switch |
| `is_enable_historical_object_replication` | Historical-data switch (bool) | "not starting" attribution |
| `sync_role_name` | RAM role OSS assumes to copy (e.g. `AliyunOSSRole`) | authorization role presence — ONLY meaningful for SSE-KMS-encrypted-target rules (GetBucketReplication returns SyncRole conditionally; empty on non-KMS rules is normal) |
| `status` | `starting` / `doing` / `closing` | lifecycle state |

### Delete-marker sync (`action_list`)

- `ALL` (or an explicit `DELETE`) → delete operations in the source ARE
  replicated to the target (delete linkage ON). Under versioning, a
  specific-version delete is not copied but a delete marker is.
- `PUT` only → write operations sync; deletes are NOT replicated (OFF).

### Historical-data switch

- `True` → objects that existed before the rule was created are migrated
  asynchronously (takes minutes to hours depending on volume).
- `False` → only objects written after the rule was created are replicated.
  **This is the single most common cause of "replication not starting".**

## 2. Official limits that break replication

These are enforced by OSS regardless of configuration; check them before
concluding a rule is "wrong":

1. **ColdArchive / DeepColdArchive objects are never replicated**, whether or
   not they are restored. (Source: CRR overview, usage-limits section.)
2. **Cross-border replication requires transfer acceleration.** Replication
   between mainland-China regions (`cn-*`) and non-mainland regions
   (`ap-*`, `us-*`, `eu-*`, ...) MUST enable transfer acceleration.
3. **Versioning must match.** Source and target versioning state must be
   identical and neither may be `Suspended`. Buckets already replicating
   cannot change versioning state. Verify manually (this skill does not call
   GetBucketVersioning).
4. **≤100 replication rules per bucket.**
5. **Already-replicated objects are not re-replicated.** OSS skips objects
   produced by another replication task, so cascading chains (A→B→C) do not
   propagate the second hop.

## 3. Authorization-role attribution (NoPermission)

CRR needs an authorization role when the target is cross-account or when
SSE-KMS objects are replicated. The role must be a **RAM role** (not a RAM
user), and its **trust policy** must let `oss.aliyuncs.com` assume it.

Trust-policy template (the role's Principal.Service must include OSS):

```json
{
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": ["oss.aliyuncs.com"]
      }
    }
  ],
  "Version": "1"
}
```

Attribution method for a replication `NoPermission` (from production case
2 — reqid `6A277D0C8A04303130AC897E`, PutBucketReplication 403):

- **server-log contains an extra STS RequestId** (different from the current
  request's reqId) → OSS tried to `AssumeRole` and STS rejected it → the role
  **trust policy** does not allow `oss.aliyuncs.com`. Fix `Principal.Service`.
- **server-log has no STS RequestId** → the caller's **RAM policy** lacks the
  required replication action. Grant the missing permission.

Note: after fixing the trust policy you do not need to re-submit the rule;
OSS picks it up on its next role-assumption attempt.

> **Cross-skill pointer (bidirectional edge, references layer).** Designing
> the cross-account replication RAM role / trust policy itself — the role's
> `Principal.Service` must include `oss.aliyuncs.com`, and for a cross-account
> target account B must additionally grant the SAME role via a Bucket Policy
> (see §5.1) — is owned by the sibling skill
> `alibabacloud-oss-cross-account-auth-diagnosis`; its
> `references/auth-config-templates.md` §1.1 "Service trust (replication /
> migration roles)" carries the identical trust-policy template and cites the
> same official source `introduction-to-data-replication-permissions`. This
> skill only CHECKS whether an existing replication rule is authorized and
> attributes `NoPermission`; defer the authorization DESIGN and the
> AssumeRole/403 attribution to that sibling (SKILL.md route table). The
> reverse edge (cross-account-auth → this skill for CRR rule health / status
> checks) is carried in that skill's scope boundary, so the pair forms a
> closed bidirectional reference.

## 4. What this skill does NOT do

This module is advisory only. This skill never calls
`PutBucketReplication` / `DeleteBucketReplication` and never creates or
changes a rule or a role. All remediation above is manual guidance for the
user to apply.

## 5. Official facts verified against current docs

Sources:
- Replication permissions: `https://help.aliyun.com/zh/oss/user-guide/introduction-to-data-replication-permissions`
- Special-scenario behavior (versioning / lifecycle / encryption / WORM):
  `https://help.aliyun.com/zh/oss/user-guide/crr-in-specific-scenarios`
- Replication FAQ / troubleshooting:
  `https://help.aliyun.com/zh/oss/user-guide/data-replication-troubleshooting`
- CRR overview (region limits, rule quota, cost ownership):
  `https://help.aliyun.com/zh/oss/user-guide/cross-region-replication-overview`
- RTC: `https://help.aliyun.com/zh/oss/user-guide/rtc`
- Error 0028-00000003: `https://help.aliyun.com/zh/oss/user-guide/0028-00000003`

### 5.1 Replication-role minimal permissions (NoPermission attribution)

Each replication operation maps to one dedicated action; OSS assumes the
role to perform it:

| Action | Meaning | Granted on |
|---|---|---|
| `oss:ReplicateList` | list objects to replicate | source bucket |
| `oss:ReplicateGet` | read objects from source | source bucket |
| `oss:ReplicatePut` | write replicas to target | target bucket |
| `oss:ReplicateDelete` | replicate deletes (only for ALL rules) | target bucket |

- Same-account: one RAM policy on the role covers both buckets
  (`acs:oss:*:*:src-bucket`, `src-bucket/*`, and the destination
  equivalents).
- Cross-account: account A (source) grants the role via **RAM Policy**;
  account B (target) additionally grants the SAME role via **Bucket
  Policy**. Missing either side causes NoPermission.
- SSE-KMS replication additionally needs a KMS-capable role: console
  naming `kms-replication-<source>-<target>`, or `AliyunOSSRole`
  (auto-created). A custom role must carry `AliyunOSSFullAccess`,
  otherwise data may fail to replicate.

### 5.2 Special-scenario behavior matrix

Versioning + deletes (versioned source bucket):

| Delete request | Rule action | Effect |
|---|---|---|
| no version ID | PUT or ALL | no object deleted anywhere; the delete MARKER is created on source and synced to target |
| with version ID | PUT only | deleted on source only |
| with version ID | ALL | deleted on source AND target |

Lifecycle interaction:
- Replication syncs the EFFECT of source lifecycle rules, never the rule
  configuration itself; add the same rule on the target manually.
- Replica creation time = the source object's creation time (not arrival
  time) -- lifecycle age on the target counts from the source write.
- Deleting an object on the source while replication is in flight may
  still leave the replica on the target.
- Warning: synced delete markers demote the target's current version to a
  NONCURRENT version; a target lifecycle rule that cleans noncurrent
  versions can then delete the data unexpectedly.

Server-side encryption:
- SSE-OSS objects always replicate with their encryption.
- SSE-KMS objects replicate ONLY if the rule enables KMS-object
  replication AND specifies the target CMK ID (a KMS key in the target
  bucket's region); otherwise they are skipped silently.

WORM (compliance retention):
- While the TARGET object is inside its WORM retention period, adds,
  overwrites and deletes from the source are NOT synced.

### 5.3 Prefix format and unsupported features

- Prefix entries must NOT end with `*` (e.g. `log/*` is invalid) and must
  not contain the bucket name; an empty prefix list means the whole
  bucket.
- CRR/SRR cannot rewrite the target path: the target key equals the
  source key. Custom target paths are unsupported.
- Syncing only files modified within a time range is unsupported; use
  the online migration service's "file modification time" filter instead.

### 5.4 Region and quota limits (additional)

- Buckets WITHOUT a region attribute can only replicate to/from
  mainland-China regions; replication between two region-less buckets is
  possible only via CRR.
- One bucket may be associated with at most 100 replication rules (as
  source or target combined).
- Per-rule prefix quota: one replication rule's `PrefixSet` accepts AT
  MOST 10 `Prefix` entries (the official `GetBucketReplication` schema
  states each replication rule specifies at most 10 Prefix entries). A rule's tag filter
  (`UserTagging`) likewise accepts at most 10 tags, and `FilterType`
  (`AND` / `OR`) is case-sensitive. If a reported rule shows more than
  10 prefixes it is a malformed/impossible configuration and must be
  flagged, not silently accepted.

### 5.5 RTC (replication time control) numbers

- Without historical data: RTC takes effect within 15 minutes of
  enabling; with historical data: about 1 hour after the historical
  phase completes.
- SLA once effective: 99.99% of NEWLY written objects replicate within
  10 minutes.
- Bandwidth AND QPS ceilings (SLA compensation applies only while the
  actual load stays below them):

  | Scope | Bandwidth | QPS (non-sequential write) |
  |---|---|---|
  | A pair of mainland-China regions (Region Pair) | 10 Gbps | 10,000 |
  | A pair of non-mainland regions | 2 Gbps | 5,000 |
  | A single region within mainland China | 20 Gbps | 20,000 |
  | Single non-mainland region | 4 Gbps | 10,000 |

- Sequential-write QPS ceiling is 2,000 for EVERY scope above; a request
  rate beyond it increases replication lag, so avoid sequential prefix
  file names when uploading large volumes. Higher limits need a ticket.
- "Replication is slow" attribution: when a rule's `status` is `doing`
  with NO error and NO delete-marker/WORM/KMS blocker, treat these
  bandwidth/QPS ceilings (and the sequential-write 2,000 cap) as the
  capacity-planning basis before suspecting a configuration defect.

### 5.6 Related error code

- `0028-00000003`: PutBucketTransferAcceleration DISABLE is rejected on a
  bucket that is the TARGET of a CRR edge depending on transfer
  acceleration -- delete the replication rule first, then disable TA.

### 5.7 Cost ownership (cross-account)

- CRR traffic fee and RTC fee: charged to the SOURCE account.
- Transfer-acceleration fee: charged to the TARGET bucket's account.
- Retrieval (thaw) fee: replicating Infrequent-Access (IA) or
  Archive-class source objects to the target bucket involves NO
  thaw/restore operation and incurs NO data-retrieval capacity fee
  (official wording: replicating Infrequent-Access and Archive-class
  objects involves no data-thaw operation and no data-retrieval capacity
  fee). Cold-Archive and Deep-Cold-Archive objects are NOT
  replicable at all — whether or not already thawed — so replication can
  never produce a retrieval fee for them; a rule that appears to "skip"
  such objects is expected behaviour, not a defect.

### 5.8 Runtime behaviour semantics (AUTHORITATIVE single source)

This section is the authoritative statement of how a RUNNING replication
task behaves. The sibling skill
`alibabacloud-oss-cross-account-auth-diagnosis` points back here (its
SKILL.md scope boundary routes "CRR rule health / status checks" to this
skill) instead of restating it, so the pair cannot drift. Source:
`getbucketreplication.md` Action / HistoricalObjectReplication / Status
schema + tickets 00021R6L5D / 000BSR6M8W.

- **Continuous until closed.** A replication task keeps running
  incrementally until it is explicitly closed/deleted. Objects written to
  the source AFTER the rule takes effect keep syncing; objects already
  synced are NOT re-replicated. It is a live monitoring task, not a
  one-shot copy (ticket 00021R6L5D: files newly produced before the
  replication task is closed keep syncing; already-synced files are never
  re-replicated).
- **Same-name overwrite.** Replication copies by object key: a source
  object whose key already exists on the target OVERWRITES it (subject to
  versioning and WORM). There is NO "only-add-never-overwrite" replication
  mode; a purely additive merge ("do not overwrite identical resources,
  only add the missing ones", ticket 0001ZS1BC6) must use the Data Online
  Migration service, not CRR.
- **Delete-sync semantics (`action_list`).** `ALL` (default) syncs
  PUT + ABORT + DELETE, so a source delete propagates to the target;
  `PUT` syncs writes only, so source deletes do NOT propagate. BEFORE
  deleting the source bucket after a migration, CLOSE the replication task
  first — otherwise a delete-sync (`ALL`) rule can wipe the target too
  (ticket 00021R6L5D: do not select the delete-sync action; if the task is
  not closed, deleting a source file also deletes the target-bucket file).
- **Historical phase.** With historical-data replication ENABLED the rule
  first copies the pre-existing backlog (`status` `starting` → `doing`;
  progress via `GetBucketReplicationProgress.historical_object_progress`),
  then keeps the new-object watermark advancing. With it DISABLED only
  objects written after rule creation ever sync (the single most common
  cause of "target bucket has no data").
- **Status vocabulary.** `starting` = task being prepared after the rule is
  set; `doing` = rule effective, data synchronizing; `closing` = rule
  deleted, OSS finishing cleanup.

### 5.9 Post-replication data verification (read-only)

Customers repeatedly ask "how do I confirm the target actually has all the
data?" (tickets 0007KS78FF / 000F4RG588: without a capacity statistic the
customer cannot confirm whether all the migrated data arrived). This skill
provides the verification PATH only; it never
promises data integrity on the user's behalf.

1. **Progress first (`GetBucketReplicationProgress`).** Read
   `historical_object_progress` (percentage of the pre-existing backlog
   already copied) and `new_object_progress` (an RFC1123 watermark: source
   writes BEFORE this time are already replicated). This distinguishes
   "still copying the backlog" from "historical replication disabled" —
   the two look identical if you only read the rule `status`. The entry
   script fetches this automatically when a rule exists
   (`report.replication_progress`).
2. **Count + spot-check (`ListObjectsV2`, read-only).** Count objects (and
   total size) under the rule's prefix on the source and, when reachable,
   on the target; then spot-check `ETag` / `Size` of a few sampled keys.
   The entry script does this under the opt-in `--verify-target` flag
   (`report.target_verification`). It is strictly read-only
   (`oss:ListObjects`) and never reads object content.
3. **Cross-account target is usually NOT listable** with the source
   credential — that is a verification LIMIT, not a failure. Ask the target
   account to run the same read-only count, or use a cross-account
   Inventory.
4. **Use the OSS Inventory for large buckets.** The script's
   `ListObjectsV2` scan is BOUNDED (caps at a few thousand objects and
   reports `truncated=true`); a truncated count must NOT be trusted as a
   total. For a full authoritative comparison of a large bucket, generate
   inventory manifests on both sides and diff them offline.
5. **Boundary sentence.** "Count match" is necessary but not sufficient:
   equal counts still need an ETag/Size spot-check, and neither proves
   byte-level integrity for multipart objects (whose ETag is not an MD5).
   State the verification result and its limits; never declare the data
   "complete" beyond what the read-only evidence shows.
