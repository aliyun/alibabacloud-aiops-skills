
## Backup and Recovery

Tair provides RDB, AOF, and Tair-Binlog persistence policies to meet backup and restoration requirements in various scenarios.

### Persistence Policies

| Policy | Mechanism | Characteristics |
|--------|-----------|-----------------|
| RDB | Snapshots of in-memory data at specified intervals | Small file size, easy to migrate, point-in-time backup. Tair optimizes persistence to achieve non-blocking backup without affecting client requests. |
| AOF | Logs all write operations (e.g., SET) | AOF_FSYNC_EVERYSEC by default — asynchronously writes commands to disk every second, minimizing performance impact. AOF rewrite reorganizes the file to reduce disk usage. |
| Tair-Binlog | Incremental AOF archiving (Tair Enterprise Edition DRAM-based only) | Prevents performance degradation from AOF rewrite. Saves each write operation with timestamp, enabling point-in-time recovery (PITR) accurate to the second. |

### Backup

**Example: Automatic backup policy**

By default, Tair instances back up data automatically once a day. You can modify the policy via console or CLI.

```bash
# Modify automatic backup policy via aliyun CLI
aliyun r-kvstore modify-backup-policy \
  --instance-id "$INSTANCE_ID" \
  --preferred-backup-time "03:00Z-04:00Z" \
  --preferred-backup-period "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

**Example: Manual backup**

Create a temporary backup at any time for data verification or before high-risk operations.

```bash
# Create a manual backup
aliyun r-kvstore create-backup \
  --instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

**Example: Download backup files**

Backup files are retained for 7 days by default. Download them for long-term retention due to regulatory or security requirements.

```bash
# Query available backup sets (start-time / end-time are REQUIRED, UTC format yyyy-MM-ddTHH:mmZ)
aliyun r-kvstore describe-backups \
  --instance-id "$INSTANCE_ID" \
  --start-time "2024-01-01T00:00Z" \
  --end-time "2024-01-31T23:59Z" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills

# Download the backup file from the BackupSetDownloadURL field in the response
```

### Recovery

> **⚠️ HIGH-RISK OPERATION — Data will be overwritten**
> `restore-instance` overwrites the current instance data and **cannot be undone**. Before executing any restore operation, you **MUST** complete the following pre-checks:
>
> 1. **Verify current write traffic** — Check whether the instance has active write traffic (monitor QPS in console). If yes, notify the user and confirm before proceeding.
> 2. **Create a latest backup** — Run `aliyun r-kvstore create-backup` to create a backup of the current data before restoring, so you can roll back if the restore goes wrong.
> 3. **Confirm with the user** — Explicitly inform the user that the restore will overwrite current data and obtain confirmation before execution.

**Example: Restore from a backup set**

Restore data from a specified backup set to the current instance. For non-DRAM instances, it is recommended to create a new instance from the backup set instead.

```bash
# [Pre-check] Create a backup of current data before restoring
aliyun r-kvstore create-backup \
  --instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills

# Wait for backup to complete, then proceed with restore
aliyun r-kvstore restore-instance \
  --instance-id "$INSTANCE_ID" \
  --backup-id "$BACKUP_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

**Example: Point-in-time recovery (PITR) via data flashback**

Restore data to a specified point in time accurate to the second. Available only for Tair Enterprise Edition DRAM-based instances with data flashback enabled. Use `RestoreType=1` with `RestoreTime` in UTC format.

```bash
# [Pre-check] Create a backup of current data before restoring
aliyun r-kvstore create-backup \
  --instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills

# Restore instance data to a specific point in time
aliyun r-kvstore restore-instance \
  --instance-id "$INSTANCE_ID" \
  --restore-type 1 \
  --restore-time "2024-01-15T10:30:00Z" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

You can also restore only specific keys using `FilterKey` with regex patterns:

```bash
# [Pre-check] Create a backup of current data before restoring
aliyun r-kvstore create-backup \
  --instance-id "$INSTANCE_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills

# Restore only specific keys matching the regex pattern
aliyun r-kvstore restore-instance \
  --instance-id "$INSTANCE_ID" \
  --restore-type 1 \
  --restore-time "2024-01-15T10:30:00Z" \
  --filter-key "session:*,user:00000007198*" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tair-agent-skills
```

### Backup Data Protection

| Protection | Description |
|-----------|-------------|
| Tamper resistance | RDB and Tair-Binlog data is stored in OSS with WORM (Write Once Read Many) feature |
| Manual deletion | Only manual backup data can be deleted; automatic backup data cannot be deleted |
| Automatic expiration | At least one automatic backup per week, retained for at least 7 days — automatic backup data cannot be completely deleted |

**Reference:** [Data backup and restoration policies and solutions](https://www.alibabacloud.com/help/en/redis/user-guide/backup-and-restoration-solutions)
