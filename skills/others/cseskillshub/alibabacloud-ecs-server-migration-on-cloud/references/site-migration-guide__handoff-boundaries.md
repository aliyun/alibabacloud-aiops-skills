# Scope boundaries and handoff wording

This skill owns one axis: planning, pre-checking, and verifying the move of a whole site or
application server between servers. Adjacent symptoms belong to another skill even when they surface
during a migration, because that is exactly when customers notice them.

Hand off the diagnosis, keep the evidence: state the boundary, name the skill or the human path, and
still deliver the migration-side checklist or the cloud evidence already gathered, so nothing has to
be collected twice.

| What the customer reports | Owner | Wording |
|---|---|---|
| Disk size did not change after an expansion; the guest sees less than what was purchased; a partition or file system was not extended | `alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis` | "A capacity that did not grow after an expansion is an expansion-effect question rather than a migration failure, and it is diagnosed by alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis. Here is the migration-side evidence already collected, including the disk sizes recorded before the move." |
| Instance will not start or stop, or is stuck between states after the new server was created | `alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis` | "The destination not reaching the running state is an instance-state question; use alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis. The migration plan stays valid and I will not restart or stop anything as a workaround." |
| Disk latency or throughput below what the specification promises | `alibabacloud-ecs-disk-io-and-data-protection: disk-io-diagnosis` | "Slow disk performance after a move is a performance question for alibabacloud-ecs-disk-io-and-data-protection: disk-io-diagnosis. I can confirm the specification and the disk class recorded for both sides." |
| Designing image-based backup or a recovery capability, rather than moving a site | `alibabacloud-ecs-disaster-recovery-image` | "Building a backup and recovery capability is a different goal from relocating a server; alibabacloud-ecs-disaster-recovery-image covers that. In this skill a snapshot appears only as the protective step taken before a destructive migration step." |
| A specific web server or database configuration fault after the move (virtual host files, database parameters, application errors beyond a recognised string) | Application support, human | "I can point at the environment deployment steps and the recognised error meanings, but repairing the application configuration itself is done by the customer or a human specialist, and it is a change inside the instance." |
| Refund amount, coupon, discount continuity after a transfer, or an extension of an expired instance | Human agent or commercial owner | "The rule can be stated and the console entry point can be given, but the amount, the coupon, and any extension are decided by a human or the commercial owner; I will not promise or compute one." |
| A generic request for an image, a snapshot, or a backup with no move involved | Not this skill | "This skill is for relocating a site between servers. If the goal is a backup or recovery capability rather than a move, say so and it belongs elsewhere." |

## Never automated, whatever the reason

Deleting or emptying files, formatting, file system checks and repairs, partitioning, mount changes,
killing processes, restarting services or instances, deleting snapshots, releasing disks, unsubscribing,
and any commercial action. For these, the output is the documented procedure, the risk, the
snapshot-first gate, and the console entry point. Reporting a refusal is correct behaviour, not a
failure: state the boundary and give the manual route.
