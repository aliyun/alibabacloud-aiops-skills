# Recovery Boundaries: When Data Is Gone For Good (and How to Prove It)

Three situations end in "not recoverable from snapshots". The skill's job is
to produce the **evidence list** behind that verdict, relay it in a
structured way, and check alternative backup sources. The platform has no
hidden recovery capability: NEVER promise "manual backend verification" or
"paid recovery from deleted snapshots" -- no support channel can restore
them, and over-promising here is a known escalation source.

## Decision rules (all from `assess` evidence)

### B1 -- Snapshot expired and was auto-deleted

- Signal: the snapshot the customer names is absent from
  `DescribeSnapshots` output for the source disk, and the retention setting
  that governed it (auto policy retention, or a short manual retention) is
  shorter than the elapsed time since the data was lost.
- Rule: a snapshot past its retention period is deleted automatically and a
  deleted snapshot **cannot be recovered**, by anyone, at any price.
- Say: state the retention window that applied, the snapshot's creation time
  if still visible in history, and that the deletion is final. Recommend
  lengthening the retention on the automatic policy (the policy itself is
  managed through the snapshot-management workflow, see
  [transfer-matrix.md](transfer-matrix.md)).

### B2 -- Instance expired / released and snapshots went with it

- Signal: `assess` reports the instance as NOT_VISIBLE in the region under
  this account, and no snapshot survives for its disks.
- Rule: snapshots configured to release together with the instance are
  deleted on release; released instance data is not retained and not
  recoverable. A support-side wording sometimes quoted in tickets is
  "released for more than 15 days" -- that figure is an agent's phrasing,
  NOT an official documented guarantee; the skill must use the conservative
  wording: "once the instance has been released, its non-retained data and
  co-released snapshots cannot be recovered; there is no documented
  platform-side grace recovery".
- Say: confirm whether any independent snapshot (kept separately from the
  instance), custom image, or file backup still exists before closing the
  case as unrecoverable.

### B3 -- Data was overwritten by a rollback (or by deletion after one)

- Signal: the customer already rolled back; the missing data was written
  BETWEEN the restore point and the rollback moment, and no fallback
  snapshot of the pre-rollback state was taken.
- Rule: the rollback overwrote that window; without a pre-rollback snapshot
  the window is gone. A second rollback "back to the newer state" is
  impossible -- the newer state has no snapshot.
- Say: enumerate the surviving snapshot chain of the disk (from `assess`)
  and show there is no point covering the lost window; then check the
  alternatives below.

## Alternative backup sources to check (before writing "not recoverable")

1. **File backup / Essential Edition** (directory-level restore, separate
   product line): https://help.aliyun.com/zh/ecs/user-guide/configure-automatic-file-backup-and-restoration-for-ecs-instances.md
2. **Custom images** (system disk state captured as an image can rebuild a
   disk on some instance): the customer's image list in the console.
3. **Application-layer trails**: database binlogs / replicas, object storage
   buckets, deploy artifacts. (Reference only -- investigating these is
   outside this skill; hand off per [transfer-matrix.md](transfer-matrix.md).)
4. Selection guide for future planning:
   https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md

## Report shape for a NOT-RECOVERABLE verdict

1. What was looked for (disk, snapshot chain, instance state, region).
2. What was found / not found -- field-level, from the script output.
3. The applicable boundary rule (B1 / B2 / B3) in one sentence.
4. The alternative sources already checked and their state.
5. Prevention: retention length, auto-policy on all business disks,
   snapshot-before-rollback discipline, cross-account copy -- each with the
   hand-off pointer it belongs to.
6. Footnote: if credentials (passwords, access keys) were pasted into the
   ticket or chat during the incident, rotate them now.
