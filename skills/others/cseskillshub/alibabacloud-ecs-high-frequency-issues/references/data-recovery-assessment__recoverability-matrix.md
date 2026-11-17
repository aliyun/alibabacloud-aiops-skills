# Recoverability Matrix (loss event x carrier x backup asset -> verdict)

The entry script `scripts/areas/data_recovery_assessment/ecs_data_recovery_assessment.py --assess` applies
the rules below in strict gate order. The ticket references (IDs like
`T-E1C0F0A5`) mark the reviewed support conversations a cell was calibrated
on; they cite public ticket numbers, not internal annotations.

## Verdict tiers (capability C4)

| Verdict | Meaning | Promise allowed? |
|---|---|---|
| `RECOVERABLE` | A backup asset of the matching class AND point in time exists | Yes, within the guided path; restore is still performed by the customer |
| `DATA-EXTRACTION-ONLY` | Whole-state rollback impossible; files survive inside a snapshot usable as a new disk | Extraction only, never "restore the server" |
| `OLDER-BACKUP-POINT-ONLY` | A backup exists but predates the needed moment | Only the older state; the gap must be stated (`T-4A3B49A8`: only a 2025-04 snapshot while newer data was needed) |
| `NOT-RECOVERABLE` | Customer-confirmed absence of any covering asset, or carrier already cleared/overwritten | Deliver with the expectation-management template, never with blame |
| `INSUFFICIENT-EVIDENCE` | Any required fact still unknown | The ONLY permitted output until the customer self-check comes back; never an optimistic "it should be recoverable" |
| `NOT-A-DATA-LOSS` | Path/mount/service change mimics loss | Guide read-only guest self-checks; do not use recovery wording (`T-8E95EFB2`: app path change, not loss; `T-0ABBCA13`: Redis memory never persisted) |

## Gate order (first match wins)

1. **Evidence gate.** Backup inventory not collected (empty or `unknown`) ->
   `INSUFFICIENT-EVIDENCE`. A hard `NOT-RECOVERABLE` verdict requires the
   customer's explicit "no snapshot / no image / no backup" confirmation.
2. **Not-a-loss gate.** `suspected-loss` -> `NOT-A-DATA-LOSS`.
3. **Cache gate.** Memory-only data without persistence -> `NOT-RECOVERABLE`
   (nothing was ever on disk) unless a dump/log/local copy exists
   (`OLDER-BACKUP-POINT-ONLY`). Basis: `T-0ABBCA13`.
4. **Overwrite gate.** Confirmed post-loss writes and no surviving asset ->
   `NOT-RECOVERABLE`. Possible writes -> safety-net snapshot guidance
   prefixed to any path (`T-78C65840`, `T-8B66E48C` standard practice: take
   a snapshot of the current state BEFORE touching anything else).
5. **No-asset gate.** Customer-confirmed `none` -> `NOT-RECOVERABLE`, with
   mechanism wording chosen per event: release-permanent
   (`T-4831FC61`, `T-983ADBB1`), reinstall-clears-system-disk
   (`T-E1C0F0A5`, `T-AB8510C2`), local-disk retention (`T-4831FC61`
   notification text: cloud disks kept ~15 days after expiry, local disks
   cleared on entering the recycling phase), third-party recovery for
   ransomware (`T-B187FE9E`, `T-6E8163E9`).
6. **Class-match gate.** Asset class must cover the carrier:

   | Carrier | Assets that cover it | Assets that do NOT (typical trap) |
   |---|---|---|
   | System disk | System-disk snapshot, custom image, file-level backup of the lost paths | Data-disk snapshot (`T-C9BD29B6`: a data-disk snapshot cannot be converted into a custom image and cannot replace a system disk wholesale) |
   | Data disk | Data-disk snapshot, auto-snapshot policy producing one, file/logical backups | System-disk snapshot content only |
   | Local disk | File/logical/local copies ONLY (snapshots cannot cover local disks) | Any snapshot expectation |
   | Memory cache | Surviving dumps (RDB/AOF-style) or local copies | Disk backups |

   Mismatch without a confirmed negative for the covering class stays
   `INSUFFICIENT-EVIDENCE` and asks the covering-class question explicitly.
7. **Time gate.** Covering assets exist but their creation times do not
   cover the needed moment -> `OLDER-BACKUP-POINT-ONLY`; times unchecked ->
   `INSUFFICIENT-EVIDENCE`.
8. **Path routing.** With class and time matched:

   | Situation | Path (see `recovery-guides.md`) |
   |---|---|
   | System disk, instance alive, system-disk snapshot of the moment | `snapshot-rollback-system-disk` + rollback semantics notice (`T-C539630C`: rollback restores file-data state, NOT the running state; services without autostart must be started by hand) |
   | Instance released but a SYSTEM-disk snapshot survives | `custom-image-rebuild` via the image built from that system-disk snapshot |
   | Data disk, snapshot exists | `snapshot-new-disk-extraction` (create disk from snapshot, attach, copy out; `T-C9BD29B6` validated route) |
   | Custom image only | `custom-image-rebuild` (`T-983ADBB1` wording: new instance with the same spec; image restores the environment) |
   | ECS file backup history exists | `file-backup-restore`; product operations route to `alibabacloud-cloudbackup-ecs-file-backup-essential-edition` |
   | No covering asset but the disk still exists and writes stopped | `guest-side-recovery-practice` with an explicit "not guaranteed" notice |
   | Nothing survives | `rebuild-from-scratch` + expectation management |

   **Extraction cap.** When the chosen route is `snapshot-new-disk-extraction`
   but the instance itself is gone (`not-visible`, or an `expiry-release`
   event), a `RECOVERABLE` verdict is capped down to
   `DATA-EXTRACTION-ONLY`: only the files inside the snapshot come back, the
   previous system state does not (`T-C9BD29B6` class judgement -- a
   data-disk snapshot cannot become a custom image). While the instance is
   still present, a data-disk snapshot restore remains `RECOVERABLE`.

## Data-boundary caveats to state with every verdict

- The read-only query sees ONLY the current credential's account AND the
  requested region: cross-account resources (agency disputes, migrations)
  stay invisible; the customer must check on the owning account side
  (`T-10B30A66`, `T-8BBF867F` patterns).
- Backup-asset existence, type and point-in-time come from the CUSTOMER's
  console self-check, not from this skill's API calls; the conclusion is as
  strong as the pasted-back evidence.
- Expiry/release timestamps and platform notification records are not
  queryable here; the customer supplies the notification SMS/email.
- Guest-side truth (file really deleted vs path changed, database binlog
  availability, ransomware encryption extent) is confirmed only by
  read-only commands the CUSTOMER runs and pastes back.
