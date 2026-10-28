# Transfer Matrix: Recognize the Symptom Axis, Hand Off Cleanly

This skill covers exactly one symptom axis: **restoring an ECS disk / system
disk to a past snapshot point** — eligibility, restore-point selection, the
snapshot-first fallback, manual rollback guidance, and post-rollback
consequence handling. Anything on a neighboring axis is recognized, briefly
explained, and transferred with a ready-to-paste sentence. Do not
half-solve a foreign axis here.

| Customer symptom (typical wording) | Axis it belongs to | Transfer target skill | What this skill still does |
|---|---|---|---|
| "Disk is full", "no space left", inode errors | capacity / inode governance | `alibabacloud-ecs-disk-capacity-cleanup` | nothing beyond noting a rollback would also revert capacity |
| "Expanded the disk but the size did not change"; "after the rollback my capacity shrank back" | disk expansion (grow partition/filesystem) | `alibabacloud-ecs-disk-expand-diagnosis` | explain that rollback restores the snapshot-time partition state; the grow steps themselves are NOT run here |
| "Instance stuck in Stopping / Starting", never reaches the state | instance power state | `alibabacloud-ecs-instance-state-diagnosis` | confirm the stop precondition and hand the stuck state over |
| Disk IO slow / performance below spec after recovery | disk IO performance | `alibabacloud-ecs-disk-io-diagnosis` | schedule the rollback outside busy hours (advice only) |
| Boot hangs, boot screen, broken filesystem / bootloader repair, patch services jamming boot (Windows `wuauserv`/TrustedInstaller style cases) | boot / OS repair | `alibabacloud-ecs-boot-repair-guide` | pick a restore point that predates the breakage; the repair itself is theirs |
| "Automatic snapshot policy did not fire", snapshot creation failed/slow, quota, cross-region copy | snapshot creation & policy | `alibabacloud-ecs-snapshot-policy-check` (policy-not-attached root cause) | the rollback path only uses snapshots that already exist |
| Snapshot fees, deleting old snapshots, capacity cleanup of snapshots | snapshot billing / lifecycle | `alibabacloud-ecs-snapshot-billing-cleanup` or `alibabacloud-ebs-disk-snapshot-management` | relay the billing notice once per created snapshot (mandatory); deletion is never performed here |
| Recovery WITHOUT any snapshot (deleted DB, no backups, ransom where no clean point exists) | recoverability assessment | `alibabacloud-ecs-data-recovery-assessment` | deliver the evidence-based NOT-RECOVERABLE verdict per [recovery-boundaries.md](recovery-boundaries.md) first |
| Malware / ransomware cleanup, revoked keys, security-group hardening, vuln fixing, cron-job purging | incident response | `alibabacloud-ecs-host-intrusion-cleanup`; leaked-credential triage -> `alibabacloud-ecs-ak-leak-forensics` | the clean restore-point shortlist (snapshots created before the incident's first anomaly time via `assess --before`), the snapshot-first gate, and the to-do checklist — never any cleanup execution |
| Resetting a login password / key issues found while preparing a rollback | instance credentials | `alibabacloud-ecs-login-credential-repair` | sequence: fallback snapshot first, then their flow |
| "Restore A's system snapshot onto B", change OS / image flows | images / change-OS | `alibabacloud-ecs-os-replace-risk-check` (change-OS risk) via the image route in [backup-type-comparison.md](backup-type-comparison.md) | explain why direct cross-instance rollback does not exist; hand the image steps over |
| File-level restore of a folder while keeping current data | file backup | `alibabacloud-ecs-hbr-backup-diagnosis` | route choice from the comparison table |

## Handoff sentence template

> "This part (<symptom>) is on the <axis> workflow rather than snapshot
> rollback, so I am handing it to <target>. What I already settled for the
> rollback side: <evidence summary>. The rollback itself stays a manual
> console action you perform after reading the risk statement."

## Hard transfer rules

1. A transfer never includes executing anything from the foreign axis — not
   even a "harmless" restart, security-group edit or cleanup command.
2. Mixed tickets (intrusion + rollback + boot failure + policy gaps, as
   common in this tier) are decomposed one axis per line item; the rollback
   axis is served fully here, every other line item gets its row above.
3. If the target skill is unavailable in the customer's environment, give
   the official document links from [rollback-entry-steps.md](rollback-entry-steps.md)
   / [recovery-boundaries.md](recovery-boundaries.md) and the console entry
   instead of attempting the foreign task.
