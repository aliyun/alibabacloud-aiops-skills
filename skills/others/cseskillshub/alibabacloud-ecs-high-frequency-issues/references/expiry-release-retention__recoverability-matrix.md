# Recoverability Matrix: what survives a release, and how it can come back

Use this matrix to answer "my instance/disk/data is gone -- can it be
recovered?". Verdicts combine live query results (from
`scripts/areas/expiry_release_retention/ecs_expiry_release_check.py`) with the rules below. Every rule
carries its evidence tag; see `lifecycle-rules.md` for the tag legend.

## 1. Per-resource matrix (after the instance is RELEASED)

| Resource | Recoverable? | Preconditions | Path (all manual -- this skill only judges feasibility) | Still billing after release? | Evidence |
|---|---|---|---|---|---|
| Instance itself (compute) | NO -- permanently deleted; configuration returns to the resource pool. No payment can bring it back. | none | Rebuild a NEW instance (from a custom image if one exists) | no | [ticket:T-B596918B] [ticket:T-C7A684D0] [ticket:T-F829BAC4] |
| System disk | NO (deleted with the instance) | a SYSTEM-disk snapshot taken before release | snapshot -> custom image -> new instance | no | [ticket:T-B596918B] [ticket:T-78D54558] |
| Local disks | NO -- always destroyed, no snapshot possible | none | none | no | [ticket:T-C7A684D0] |
| Data disk with delete-with-instance = true | NO (deleted with the instance) | a data-disk snapshot taken before release | snapshot -> create disk -> attach -> copy files | no | [ticket:T-B596918B] [ticket:T-0DEF60B4] |
| Data disk with delete-with-instance = false | YES -- the disk itself survives | disk not manually released; account not locked | attach to a new instance IN THE SAME ZONE; a retained SYSTEM disk can only be attached as a DATA disk | YES -- it keeps billing until released manually | [ticket:T-0E502AF0] [ticket:T-78D54558] |
| Snapshots | YES -- they survive the instance release | account not overdue > 15 days (otherwise snapshots are released) | usable for image/disk creation as above | YES -- snapshot storage keeps billing | [ticket:T-0E502AF0] |
| Custom images | YES -- they survive | image existed before release | create a new instance from the image | YES -- image/derived snapshot storage bills | [ticket:T-78D54558]; image inventory itself: no verified API in this tier -> check console (UNKNOWN, never "none") |
| Classic public IP | NO -- lost permanently at release | must be converted to an EIP BEFORE release | none after release | no | [ticket:T-5E3EDF72] [ticket:T-8D31E368] |
| EIP | The EIP resource itself survives (separate product) | EIP not released | rebind to a new instance; EIP billing and conversion details are out of scope -> hand off | YES -- EIP bills independently | [ticket:T-C8B6DAEA, low confidence] |

## 2. The two DIFFERENT "15-day" rules (never mix them)

1. **Post-expiry data-retention window**: a subscription instance stopped by
   expiry is retained for 15 days, then released
   ([ticket:T-5E3EDF72] [ticket:T-263837C7]; `[TO VERIFY]` against
   [doc:https://help.aliyun.com/zh/ecs/product-overview/subscription#9bfa29b0407gc]).
2. **Overdue snapshot release**: when the ACCOUNT is overdue for more than
   15 days, existing SNAPSHOTS are released ([ticket:T-0E502AF0]).

Output both with their own labels; conflating them changes the customer's
deadline by an unknown amount.

## 3. Point-in-time recoverability (the strongest automated verdict)

- The set of recoverable points in time is EXACTLY the set of snapshot
  `CreationTime` values returned by the snapshot query. The platform keeps no
  other historical state, and **paying does not unlock arbitrary points in
  time** [ticket:T-F829BAC4].
- "Can I go back to X?" decision:
  - a snapshot exists with CreationTime <= X -> recoverable to the CLOSEST
    such snapshot time (rollback restores exactly that snapshot moment;
    everything written after it is LOST -- take a fresh snapshot first,
    manual action) [ticket:T-F829BAC4];
  - earliest snapshot is after X -> NOT recoverable to X;
  - no snapshots -> nothing recoverable at all.
- Rollback applies ONLY to the snapshot's ORIGINAL disk. A snapshot can
  never be "rolled back" onto a different, newly purchased disk
  [ticket:T-0DEF60B4].

## 4. Two distinct recovery paths (do not conflate)

| Path | When | Steps (ALL manual console/OS actions; skill provides guidance only) | Evidence |
|---|---|---|---|
| Whole-instance rebuild | a SYSTEM-disk snapshot (or custom image) exists | snapshot -> custom image -> create new instance; public IP will CHANGE | [ticket:T-78D54558] [ticket:T-5E3EDF72] |
| Single-file retrieval | only DATA-disk snapshots exist | create a pay-as-you-go disk from the snapshot -> attach to a running instance -> copy the needed files inside the OS -> detach and RELEASE the temporary disk so it stops billing | [ticket:T-0DEF60B4] |

Hands-on execution of either path (rollback, disk creation, attach/detach,
copy, cleanup) belongs to the data-recovery / backup tiers -- this skill
outputs the feasibility verdict, the ordered manual steps and the risk
warnings, then hands off (see `handoff-boundaries.md`). Boundary doc:
[doc:https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md].

## 5. Empty result vs failed query (hard wording discipline)

- Query SUCCEEDED, zero rows -> "Query succeeded: no snapshot / no retained
  disk exists for this target." This is a valid negative conclusion.
- Query FAILED (permission, throttling after retries, network) ->
  "UNKNOWN: could not query (<reason>)." Never phrase a failure as "no data
  exists", and never phrase a miss as "the instance was released".
- Not queryable in this tier (custom images, Cloud Backup / HBR vaults,
  prior-extension history; unpaid orders ARE queryable read-only through
  `bssopenapi QueryOrders` but this area does not call it yet) ->
  "UNKNOWN -- verify in the console",
  with the console path from `console-paths.md`. An UNKNOWN here must NEVER
  be degraded into "no backup exists" [design rule; prevents abandoning a
  recoverable case, cf. ticket:T-C7A684D0 where "how do I check whether I
  have snapshots" went unanswered].

## 6. Prevention checklist to close every recoverability answer

1. Enable an automatic snapshot policy on production disks (manual console
   action) [ticket:T-B596918B].
2. Enable instance release protection on critical instances (manual console
   action) [ticket:T-B596918B] [ticket:T-C7A684D0].
3. Enable auto-renewal or renew well before expiry; the skill can READ the
   auto-renewal state but never changes it [ticket:T-B596918B].
4. Snapshot-first rule: before ANY cleanup / rollback / unsubscribe /
   release, create a snapshot of every disk that matters
   [ticket:T-0DEF60B4] [ticket:T-86768857] [ticket:T-F829BAC4].
5. For spot instances, set the interruption mode to economical stop at
   creation time [ticket:T-7D84AD37].
