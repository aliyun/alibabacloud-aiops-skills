# Documentation Index (sources, use, verification status)

Only URLs listed here may be cited in answers. Two source classes:

- **help-search**: surfaced by the official documentation search during
  requirements analysis; safe to cite as-is.
- **support-conversation**: a link that support engineers actually sent to
  customers in reviewed ticket conversations; re-open it to confirm it still
  resolves to the current document before quoting any number from it.

Machine-readable copy lives in `scripts/areas/data_recovery_assessment/_constants.py` (`DOC_INDEX`); run
`python3 scripts/areas/data_recovery_assessment/ecs_data_recovery_assessment.py --docs` for the live list.

## Data-recovery practice (scenario: mistaken deletion / formatting)

| Topic | Document | Source |
|---|---|---|
| Linux in-guest recovery | https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-linux-instance-data-recovery.md | help-search |
| Windows in-guest recovery | https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-restoring-data-on-windows-instances.md | help-search |

Windows note: reviewed tickets did not evidence Windows-side in-guest
equivalents directly; the best-practice document above is the designated
source, with confidence "medium, pending human re-review" for Windows
volume-level specifics.

## Backup mechanics and protection design (scenario: what backup should exist)

| Topic | Document | Source |
|---|---|---|
| Automatic snapshot policies | https://help.aliyun.com/zh/ecs/user-guide/automatically-create-snapshots.md | help-search |
| Application-consistent snapshots (database workloads) | https://help.aliyun.com/zh/ecs/user-guide/create-application-consistent-snapshots-in-the-ecs-console.md | help-search |
| Local disks (why their data cannot be snapshotted and is cleared in recycling) | https://help.aliyun.com/zh/ecs/user-guide/local-disks.md | help-search |

## Irreversible-clear mechanics (scenario: reinstall / system disk)

| Topic | Document | Source |
|---|---|---|
| Replacing the operating system (system disk is cleared) | https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance-1.md | help-search |

## Rebuild carriers (scenario: restore an environment)

| Topic | Document | Source |
|---|---|---|
| Custom image overview | https://help.aliyun.com/zh/ecs/user-guide/overview-36.md | help-search |

## Console operations referenced during recovery guidance (customer-performed)

| Topic | Document | Source |
|---|---|---|
| Snapshot basics | https://help.aliyun.com/document_detail/25455.html | support-conversation |
| Snapshot rollback (recovery path and official limits) | https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot.md | help-search |
| Snapshot billing (safety-net cost statement) | https://help.aliyun.com/document_detail/56159.html | support-conversation |
| Snapshot cleanup after recovery | https://help.aliyun.com/document_detail/128131.html | support-conversation |
| System-disk re-initialization (cited for its irreversibility notice only) | https://help.aliyun.com/document_detail/25449.html | support-conversation |
| Building a disk from a snapshot (extraction path) | https://help.aliyun.com/document_detail/32317.html | support-conversation |
| ECS file backup console entry (self-check item 4) | `ecs.console.aliyun.com/fileBackup/region/<region-id>` | support-conversation |

## Known retrieval gaps (do not fill by guessing)

- The "rollback restores the data state at the snapshot creation time"
  semantics now has a confirmed source:
  `roll-back-a-disk-by-using-a-snapshot.md`, frozen as anchor
  `data-recovery-assessment__snapshot-rollback-limits` (2026-11-12). The
  narrower "not the running state" nuance is still delivered with the reviewed
  support-practice wording in `expectation-management.md`, because the official
  body states the data-state restoration but not the running-state distinction.
- No documentation hit was captured for the post-expiry retention-period
  details; any numeric retention window is attributed to the customer's own
  renewal notice, not to a URL.
- Cross-account data visibility has no document cited here; the boundary is
  stated from the read-only query's scope instead.
