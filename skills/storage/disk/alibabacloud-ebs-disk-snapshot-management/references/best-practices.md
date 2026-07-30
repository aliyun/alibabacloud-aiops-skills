# Snapshot Lifecycle Best Practices

## Planning

### Identify protection requirements

Classify workloads before designing a snapshot strategy:

| Workload type | Snapshot frequency | Retention | Notes |
|---------------|-------------------|-----------|-------|
| Core databases / business-critical | Every 1–2 days | Months or longer | Combine with consistency groups for multi-disk apps. |
| Non-core applications | Every 1–2 weeks | Days or weeks | Balance cost and recovery needs. |
| Pre-upgrade / pre-migration | On demand | Delete after verification | Keep until the change is proven stable. |
| Test / dev environments | On demand | Short | Delete when environment is rebuilt. |

### Choose the right snapshot type

- **Standard snapshots**: Default for active backup and fast recovery.
- **Archive snapshots**: Use only for long-term, infrequently accessed data.
- **Consistency groups**: Use for multi-disk applications that need crash consistency (databases, distributed systems).

## Creating snapshots

### Schedule around business hours

- Create snapshots during low-traffic windows.
- Snapshot creation causes up to 10% I/O performance degradation for a short period.

### Tag consistently

Use a consistent tagging scheme:

- `Environment`: `production`, `staging`, `development`
- `Application`: application name
- `Purpose`: `daily-backup`, `pre-upgrade`, `compliance`
- `Owner`: team or individual
- `Retention`: expected retention in days

### Set retention days

- Use `RetentionDays` to avoid manual cleanup and unexpected long-term costs.
- Align retention with compliance and recovery-point objectives.

### Avoid snapshot name conflicts

- Do not start manual snapshot names with `auto`.
- Use descriptive names including date and purpose, e.g., `prod-db-pre-schema-change-20250715`.

## Before high-risk operations

1. Create a manual snapshot or consistency group immediately before:
   - OS upgrades
   - Major configuration changes
   - Schema migrations
   - Disk expansion
2. Verify the snapshot reaches `accomplished` state before proceeding.
3. Record the `SnapshotId` or `SnapshotGroupId`.

## Rolling back

1. Always create a new snapshot of the current state before rollback.
2. Stop the instance normally (not economical mode for pay-as-you-go VPC).
3. Verify the snapshot belongs to the target disk and encryption matches.
4. Use `DryRun=true` first.
5. Warn users that rollback is irreversible.

## Automatic snapshot policies

### Design policy schedules

- Spread time points across the night to avoid I/O spikes.
- Use fewer weekdays for non-critical disks.
- Set retention according to data importance.

### Policy limits

- 100 policies per region per account.
- 10 policies per disk.
- New applications add to existing policies rather than replacing them.

### Clean up

- Delete policies no longer tied to active disks.
- Enable automatic snapshot deletion with disk release for temporary resources.

## Cost governance

### Monthly audit

1. Run `DescribeSnapshots` for each region.
2. Run `scripts/snapshot_cost_calculator.py`.
3. Review `scripts/snapshot_cleanup_planner.py` output.
4. Delete confirmed-orphaned snapshots.
5. Archive snapshots that meet the 60-day minimum and are rarely accessed.

### Compliance

- Retain snapshots according to legal and regulatory requirements.
- Use encrypted snapshots for sensitive data; encryption is inherited from encrypted disks.

## Common anti-patterns

- **Keeping every snapshot forever**: drives up storage costs; define retention.
- **Creating snapshots during peak traffic**: impacts application latency.
- **Rolling back without a current-state backup**: loses data created after the snapshot.
- **Applying too many auto policies**: reaches the 10-policy-per-disk limit and complicates management.
