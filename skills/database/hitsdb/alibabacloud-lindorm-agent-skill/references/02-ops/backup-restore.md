# Backup and Restore Scenarios

## Trigger Conditions

- "How do I back up Lindorm data?"
- "How can I restore data to yesterday's state?"
- "Can you help me view the backup list?"
- "How can I recover data after accidental deletion?"
- "What is the automatic backup cycle?"

---

## Agent Behavior Principles

**Safety boundary: Query backup information + guide manual operations. Restore operations require user confirmation.**

1. The Agent currently has no API for directly querying the backup list.
2. Provide the console path for configuring automatic backup policies.
3. Provide restore steps, but do not directly execute restore operations.
4. Restore operations overwrite current data and require explicit user confirmation.

---

## Official Documentation

| Scenario | Documentation Link |
|------|---------|
| Enable backup and restore | https://help.aliyun.com/zh/lindorm/user-guide/backup-and-restoration |
| Automatic backup configuration | https://help.aliyun.com/zh/lindorm/user-guide/automatic-backup-of-data-of-lindorm-wide-tables |
| Restore to the current instance | https://help.aliyun.com/zh/lindorm/user-guide/restore-backup-data-to-the-instance-that-corresponds-to-the-original-data |
| Value-added service fees | https://help.aliyun.com/zh/lindorm/product-overview/value-added-services-pricing |

---

## Backup Capabilities by Engine

| Engine | Backup and Restore Capability | Description |
|------|------------|------|
| **Wide table engine** | ✅ Supported | Complete backup and restore capabilities described in this document |
| **Search engine** | ❌ No independent backup | The source data of search indexes is in wide tables. After wide table backup restoration, search indexes must be rebuilt. |
| **Time series engine** | ❌ No independent backup | No official backup and restore documentation is available yet. |
| **Compute engine** | ❌ No backup required | Stateless Spark compute service. Job results are written back to storage engines, and storage engine backup already covers them. |

> Official backup and restore capabilities are provided only for the wide table engine. Other engines currently have no independent backup solution.

| Type | Description | Configuration Method |
|------|------|---------|
| **Full backup** | Backs up complete table data and schemas | Configure the cycle and scope in the console |
| **Incremental backup** | Automatically backs up changed data | Runs automatically after enablement, with no configuration required |

### Configurable Parameters for Full Backup

| Parameter | Description | Optional Range | Recommended Value |
|------|------|---------|--------|
| Backup tables | Specifies the backup scope | `*` for the entire database, or `namespace:table` format. For example, `default:test` indicates tables whose names start with test in the default namespace. | `*`, entire database |
| Full backup cycle | Trigger interval | 3 to 10 days | 7 days |
| Next full backup time | Start time | Off-peak hours are recommended | 02:00 |
| Number of retained full backups | Number of retained backups | 3 to 12 | 7 |

### Backup and Restore Performance Reference (Not Configurable)

| Metric | Description | Reference Value |
|------|------|--------|
| RPO | Maximum acceptable data loss during a failure | < 30 seconds, real-time incremental synchronization |
| Full restore speed | Maximum OSS bandwidth / single LTS node | 1 GB/s / 100 MB/s |
| Incremental restore speed | Single Lindorm destination cluster node / single LTS node | 30 to 40 MB/s / 100 MB/s |

---

## Scenario A: Configure Automatic Backup

### Step 1: Enable Backup and Restore

1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
2. On the instance list page, click the **target instance ID**.
3. In the left-side navigation pane, click **Wide Table Engine** → **Backup and Restore**.
4. Click "Enable Now".
   - If search indexes or data subscription are not enabled: You are redirected to the specification change page. Select the **LTS Core specification** and **number of nodes**. For specification selection, see the value-added service documentation. Then click "Buy Now".
   - If search indexes or data subscription are already enabled: Enable directly without specification change.

⚠️ **Unsupported instance types**: Lindorm new-version instances and single-node instances do not currently support backup and restore.

### Step 2: Configure a Full Backup Policy

1. In the left-side navigation pane, click **Wide Table Engine** → **Backup and Restore** → **Full Backup**.
2. Click "Create".
3. Configure parameters. For recommended values, see the parameter table above:
   - **Backup tables**: `*`, entire database, or a specified table such as `default:user_table`.
   - **Full backup cycle**: 7 days. A cycle that is too short may prevent backup completion, and a cycle that is too long affects restore time.
   - **Next full backup time**: 02:00, during off-peak hours.
   - **Number of retained full backups**: 7.
4. Click "Confirm".

⚠️ **Space evaluation**: Insufficient backup space causes backup interruption. Full backup space ≈ (number of retained backups + 1) × size of a single full backup. Incremental space ≈ log retention days × daily incremental LOG size. You can view the size of a single full backup in **Wide Table Engine** → **Backup and Restore** → **Full Backup**. The incremental LOG size can be estimated from the write speed obtained through monitoring.

### Verify Backup

After configuration, the system automatically executes backup at the configured time. View path: **Wide Table Engine** → **Backup and Restore** → **Full Backup List**.

### Notes

- The first backup scans the entire table and takes a long time.
- The backup process does not affect business reads and writes.
- Incremental backup runs automatically and requires no configuration.
- Backup storage is billed on a pay-as-you-go basis. For detailed prices, see [Value-added service billing](https://help.aliyun.com/zh/lindorm/product-overview/value-added-services-pricing).

---

## Scenario B: Restore Historical Data

### Prerequisites

1. Backup and restore has been enabled for the instance. ⚠️ Lindorm new-version instances and single-node instances are not currently supported.
2. A backup before the accidental deletion exists. View path: **Wide Table Engine** → **Backup and Restore** → **Full Backup List**.
3. The backup time point is within the retention period.

### Method 1: Restore to the Current Instance

**⚠️ Risk warning: This operation overwrites the specified table data in the current instance, and the table is unavailable during restoration. It is recommended to clear the original table data before restoration or verify the operation in a test instance.**

1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
2. On the instance list page, click the **target instance ID**.
3. In the left-side navigation pane, click **Wide Table Engine** → **Backup and Restore**.
4. In the full backup list, click "Start Data Restoration".
5. Configure parameters:
   - **Restore cluster**: Current instance. ⚠️ After a version upgrade, backup data of the original version cannot be used to restore the new version.
   - **Time point**: Select the backup time point.
   - **Full database restore**: No. Specifying tables is recommended.
   - **Restore tables**: Write one table per line in `namespace:table` format, such as `default:testTable`. To restore to another table name, use `namespace:table/namespace:table2`, such as `default:testTable/default:testTable2`.
6. Click "OK".

### Method 2: Restore to Another Instance

Applicable scenarios: data migration and environment replication.

Notes:
- The destination instance must have sufficient storage space.
- The destination instance version must be the same as the source instance version.
- Cross-version restoration is not supported.

### Query Restore Progress

Console path: **Wide Table Engine** → **Backup and Restore** → **Restore List**.

### Post-restore Verification

```sql
-- Verify the data volume.
SELECT COUNT(*) FROM user_table;

-- View sample data.
SELECT * FROM user_table LIMIT 10;
```

---

## FAQ

| Question | Cause | Solution |
|------|------|---------|
| Restore failed: insufficient storage space | The destination instance does not have enough space | Scale out storage space and retry, or clean up useless data |
| Restore failed: version incompatible | The source and destination instance versions are inconsistent | Make sure the versions are consistent. After a version upgrade, backup data of the original version cannot be used to restore the new version. |
| What is the latest restorable time point? | WAL backup cycle to OSS | Normally, at most 30 seconds of data is lost |
| How long does restoration take? | Depends on the data volume | Full restore is about 100 MB/s on a single LTS node, and incremental restore is about 30 to 40 MB/s |
| Can data be restored to another table name? | Supported | Use the format `namespace:table/namespace:table2` to restore a table to another table with the same data |

---

## Missing Parameter Follow-up Questions

| Missing Parameter | Follow-up Question | Default Strategy |
|---------|---------|----------|
| Instance ID | "Which Lindorm instance needs backup configuration?" | Guide the user to operate in the console |
| Backup cycle | "How often do you want to back up data? The recommended value is 7 days." | Default to 7 days |
| Retention count | "How many backups do you need to retain? The recommended value is 7." | Default to 7 |
| Restore time point | "Which time point do you want to restore data to?" | List recent backups for selection |
| Restore scope | "Do you need to restore all tables or specified tables?" | By default, remind the user that specifying tables is safer |

---

## Related Scenarios

- Data migration after backup → `data-migration.md`
- Performance verification after restoration → `monitoring-guide.md`