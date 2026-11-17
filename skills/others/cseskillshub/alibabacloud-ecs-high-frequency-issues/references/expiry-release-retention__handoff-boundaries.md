# Handoff boundaries — expiry / release / retention

This area answers lifecycle questions and explains manual console paths. It
never performs a change. Route the action (and the question that belongs to
another area) as follows, carrying the facts already verified.

| Ask | Owner |
|---|---|
| Renew, unsubscribe, refund amount or refund destination | `area:unsubscribe-refund` for the refund mechanics; the customer performs the action in the console |
| Price, discount, renewal quote or price-mismatch | `area:renewal-pricing-discount` |
| Stop-mode billing (what is still charged while stopped) | `area:stop-mode-billing-guide` |
| Arrears, overdue balance, account suspension | account and billing support |
| Snapshot or backup restore and retention after release | `alibabacloud-ecs-snapshot-and-backup` (snapshot) or `area:hbr-backup-diagnosis` (Cloud Backup) |
| Custom image lifecycle (who can see or use an image) | `area:custom-image-lifecycle` |
| Instance stuck in a start/stop state rather than expired | `area:instance-state-diagnosis` |
| Disk capacity, partition or file system growth | the disk capacity / disk expand areas in this package |

## Rules

1. The 15-day post-expiry retention window and the separate 15-day overdue
   snapshot-release rule are different rules. Never merge them, and keep the
   `[TO VERIFY: official confirmation pending]` tag on the former.
2. An action the customer must perform is described as their console step,
   with its risk and the snapshot-first rule. The agent never runs it.
3. A handoff carries the instance id, region, expiry timestamp, current status
   and the readings that were actually taken. Do not hand off a bare question.
4. When the receiving area is not installed, state the product and the console
   entry point instead of answering the other area's question here.
